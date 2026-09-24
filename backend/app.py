import asyncio
import os
import shutil
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.config import THUMBNAILS_DIR, CACHE_DIR
from backend.models_downloader import ensure_models_exist
from backend.db.database import DatabaseManager
from backend.services.scanner import PhotoScannerService
from backend.services.organizer import PhotoOrganizerService
from backend.services.manifest_service import ManifestUndoService

# Ensure ONNX models exist locally
ensure_models_exist()

db_manager = DatabaseManager()
scanner_service = PhotoScannerService(db_manager)
organizer_service = PhotoOrganizerService(db_manager)
undo_service = ManifestUndoService(db_manager)

app = FastAPI(title="Offline AI Face Recognition & Photo Organizer API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:3000", "http://127.0.0.1:5173", "http://localhost", "http://127.0.0.1"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

ws_manager = ConnectionManager()

import uuid

job_lock = asyncio.Lock()

# Pydantic Schemas
class ScanRequest(BaseModel):
    source_dir: str
    library_name: Optional[str] = ""

class RenamePersonRequest(BaseModel):
    person_id: str
    new_name: str

class DeletePersonRequest(BaseModel):
    person_id: str

class MergePersonsRequest(BaseModel):
    source_person_id: str
    target_person_id: str

class ReclusterRequest(BaseModel):
    distance_threshold: float = 0.48

class ReassignFaceRequest(BaseModel):
    face_id: str
    target_person_id: str

class DeleteFaceRequest(BaseModel):
    face_id: str

class OrganizeRequest(BaseModel):
    target_dir: str
    library_name: str = ""
    operation_mode: str = "copy" # "copy", "move", "symlink"
    couple_pair: Optional[List[str]] = None
    couple_folder_name: str = "Groom_and_Bride"
    group_folder_name: str = "Group_Photos"
    scenery_folder_name: str = "Scenery_and_Objects"
    group_threshold: int = 3

class UndoRequest(BaseModel):
    manifest_id: str

class UnmergeRequest(BaseModel):
    group_id: str

scan_status_state = {
    "status": "idle",
    "scanned_count": 0,
    "total_files": 0,
    "current_file": "",
    "total_faces_found": 0,
    "persons_count": 0,
    "message": ""
}

export_status_state = {
    "status": "idle",
    "exported_count": 0,
    "total_files": 0,
    "current_file": "",
    "target_dir": "",
    "manifest_id": None
}

@app.websocket("/ws/progress")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)

def run_scan_job(source_dir: str, library_name: str, loop):
    def progress_callback(data: dict):
        scan_status_state.update(data)
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)

    try:
        scanner_service.scan_directory(source_dir, progress_callback)
        # Record scan session upon completion
        db_manager.record_scan_session({
            "session_id": str(uuid.uuid4()),
            "source_dir": source_dir,
            "target_dir": "",
            "library_name": library_name or os.path.basename(source_dir.rstrip("/\\")),
            "photos_count": scan_status_state.get("total_files", 0),
            "faces_count": scan_status_state.get("total_faces_found", 0),
            "persons_count": scan_status_state.get("persons_count", 0),
            "status": "completed"
        })
    except Exception as e:
        scan_status_state["status"] = "error"
        scan_status_state["message"] = str(e)
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(scan_status_state), loop)

def run_export_job(req: OrganizeRequest, loop):
    def progress_callback(data: dict):
        export_status_state.update(data)
        asyncio.run_coroutine_threadsafe(ws_manager.broadcast(data), loop)

    res = organizer_service.execute_organization(
        target_dir=req.target_dir,
        library_name=req.library_name,
        operation_mode=req.operation_mode,
        couple_pair=req.couple_pair,
        couple_folder_name=req.couple_folder_name,
        group_folder_name=req.group_folder_name,
        scenery_folder_name=req.scenery_folder_name,
        group_threshold=req.group_threshold,
        progress_callback=progress_callback
    )
    export_status_state["manifest_id"] = res.get("manifest_id")

async def _async_scan_job(source_dir, library_name, loop):
    async with job_lock:
        await loop.run_in_executor(None, run_scan_job, source_dir, library_name, loop)

@app.post("/api/scan/start")
async def start_scan(req: ScanRequest, background_tasks: BackgroundTasks):
    if job_lock.locked():
        raise HTTPException(status_code=409, detail="A scan or export job is currently in progress.")
        
    if not os.path.exists(req.source_dir):
        raise HTTPException(status_code=400, detail=f"Source directory '{req.source_dir}' does not exist.")

    scanner_service.reset_cancel()
    scan_status_state["status"] = "scanning"
    scan_status_state["scanned_count"] = 0
    scan_status_state["message"] = ""

    loop = asyncio.get_event_loop()
    background_tasks.add_task(_async_scan_job, req.source_dir, req.library_name or "", loop)
    return {"status": "started", "source_dir": req.source_dir}

@app.get("/api/dashboard/insights")
async def get_dashboard_insights():
    """Retrieve comprehensive dashboard insights including scan statistics, library breakdowns, and time filters."""
    insights = db_manager.get_dashboard_insights()
    return insights

@app.post("/api/scan/cancel")
async def cancel_scan():
    """Cancel any ongoing folder scan background job immediately."""
    scanner_service.request_cancel()
    scan_status_state["status"] = "cancelled"
    scan_status_state["message"] = "Scan process cancelled by user."
    await ws_manager.broadcast(scan_status_state)
    return {"status": "cancelled"}

@app.get("/api/scan/status")
async def get_scan_status():
    return scan_status_state

@app.get("/api/persons")
async def list_persons():
    persons = db_manager.get_all_persons()
    return persons

from pydantic import BaseModel
class CreatePersonReq(BaseModel):
    display_name: str

import uuid
@app.post("/api/persons/create")
async def create_person(req: CreatePersonReq):
    new_id = str(uuid.uuid4())
    db_manager.save_person(new_id, req.display_name, "", 0)
    return {"person_id": new_id, "display_name": req.display_name}

@app.get("/api/persons/{person_id}/images")
async def get_person_images(person_id: str):
    images = db_manager.get_images_for_person(person_id)
    return images

@app.get("/api/images")
async def list_images():
    images = db_manager.get_all_images()
    return images

@app.get("/api/images/{image_id}/faces")
async def get_image_faces(image_id: str):
    faces = db_manager.get_faces_for_image(image_id)
    return faces

@app.get("/api/duplicates")
async def get_duplicates():
    dups = db_manager.get_duplicate_images()
    return dups

@app.post("/api/persons/rename")
async def rename_person(req: RenamePersonRequest):
    db_manager.rename_person(req.person_id, req.new_name)
    return {"success": True}

@app.post("/api/persons/delete")
async def delete_person(req: DeletePersonRequest):
    db_manager.delete_person(req.person_id)
    return {"success": True}

@app.post("/api/persons/merge")
async def merge_persons(req: MergePersonsRequest):
    group_id = db_manager.merge_persons(req.source_person_id, req.target_person_id)
    return {"success": True, "group_id": group_id}

@app.get("/api/persons/merge_groups")
async def get_merge_groups():
    """Return all recorded merge group history."""
    groups = db_manager.get_merge_groups()
    return groups

@app.post("/api/persons/unmerge")
async def unmerge_persons(req: UnmergeRequest):
    """Reverse a merge: restore the source person and reassign their faces."""
    success = db_manager.unmerge_group(req.group_id)
    if not success:
        raise HTTPException(status_code=404, detail="Merge group not found or already reversed.")
    return {"success": True}

@app.post("/api/persons/recluster")
async def recluster_persons(req: ReclusterRequest):
    res = scanner_service.recluster(req.distance_threshold)
    return res

@app.post("/api/workspace/reset")
async def reset_workspace():
    """Reset all cached photos, faces, persons, thumbnails, and scan status."""
    scanner_service.request_cancel()
    db_manager.clear_cache()

    if THUMBNAILS_DIR.exists():
        for f in THUMBNAILS_DIR.iterdir():
            if f.is_file():
                try:
                    f.unlink()
                except Exception:
                    pass

    scan_status_state.update({
        "status": "idle",
        "scanned_count": 0,
        "total_files": 0,
        "current_file": "",
        "total_faces_found": 0,
        "persons_count": 0,
        "message": ""
    })

    export_status_state.update({
        "status": "idle",
        "exported_count": 0,
        "total_files": 0,
        "current_file": "",
        "target_dir": "",
        "manifest_id": None
    })

    await ws_manager.broadcast(scan_status_state)
    return {"success": True, "message": "Workspace reset complete."}

@app.post("/api/faces/reassign")
async def reassign_face(req: ReassignFaceRequest):
    db_manager.reassign_face(req.face_id, req.target_person_id)
    return {"success": True}

@app.post("/api/faces/delete")
async def delete_face(req: DeleteFaceRequest):
    db_manager.delete_face(req.face_id)
    return {"success": True}

async def _async_export_job(req, loop):
    async with job_lock:
        await loop.run_in_executor(None, run_export_job, req, loop)

@app.post("/api/organize/execute")
async def execute_organize(req: OrganizeRequest, background_tasks: BackgroundTasks):
    if job_lock.locked():
        raise HTTPException(status_code=409, detail="A scan or export job is currently in progress.")

    export_status_state["status"] = "exporting"
    export_status_state["exported_count"] = 0

    loop = asyncio.get_event_loop()
    background_tasks.add_task(_async_export_job, req, loop)
    return {"status": "started", "target_dir": req.target_dir}

@app.get("/api/organize/status")
async def get_export_status():
    return export_status_state

@app.get("/api/organize/manifests")
async def get_manifests():
    return db_manager.get_all_manifests()

@app.post("/api/organize/undo")
async def undo_organize(req: UndoRequest):
    res = undo_service.undo_manifest(req.manifest_id)
    return res

def choose_folder_dialog(title="Select Directory"):
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        selected_path = filedialog.askdirectory(title=title)
        root.destroy()
        return selected_path or ""
    except Exception as e:
        print(f"Error opening folder picker dialog: {e}")
        return ""

@app.post("/api/utils/select_folder")
async def select_folder_api(title: str = "Select Directory"):
    loop = asyncio.get_event_loop()
    selected_path = await loop.run_in_executor(None, choose_folder_dialog, title)
    return {"path": selected_path}

@app.post("/api/utils/open_folder")
async def open_folder_api(req: Dict[str, str]):
    folder_path = req.get("path", "")
    if folder_path and os.path.isdir(folder_path):
        try:
            os.startfile(folder_path)
            return {"success": True}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=400, detail="Folder path does not exist or is not a directory.")

@app.get("/api/person_thumbnail/{person_id}")
async def get_person_thumbnail(person_id: str):
    conn = db_manager.get_connection()
    cur = conn.execute("SELECT thumbnail_path FROM persons WHERE person_id = ?", (person_id,))
    row = cur.fetchone()
    conn.close()

    if row and row['thumbnail_path']:
        p = Path(row['thumbnail_path'])
        if p.exists():
            return FileResponse(str(p))

    conn = db_manager.get_connection()
    cur = conn.execute("SELECT thumbnail_path FROM faces WHERE person_id = ? LIMIT 1", (person_id,))
    row = cur.fetchone()
    conn.close()

    if row and row['thumbnail_path']:
        p = Path(row['thumbnail_path'])
        if p.exists():
            return FileResponse(str(p))

    raise HTTPException(status_code=404, detail="Thumbnail not found")

@app.get("/api/thumbnail/{face_id}")
async def get_thumbnail(face_id: str):
    thumb_path = THUMBNAILS_DIR / f"{face_id}.jpg"
    if thumb_path.exists():
        return FileResponse(str(thumb_path))
    raise HTTPException(status_code=404, detail="Thumbnail not found")

@app.get("/api/image")
async def get_image(path: str):
    p = Path(path).resolve()
    
    is_valid = False
    try:
        if CACHE_DIR.resolve() in p.parents or THUMBNAILS_DIR.resolve() in p.parents:
            is_valid = True
    except Exception:
        pass
        
    if not is_valid:
        conn = db_manager.get_connection()
        cur = conn.execute("SELECT 1 FROM images WHERE file_path = ?", (str(p),))
        if cur.fetchone():
            is_valid = True
        conn.close()
        
    if not is_valid:
        raise HTTPException(status_code=403, detail="Forbidden")

    if p.exists() and p.is_file():
        return FileResponse(str(p))
    raise HTTPException(status_code=404, detail="Image file not found")

# Serve React static frontend build if present
DIST_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        if full_path.startswith("api") or full_path.startswith("ws"):
            raise HTTPException(status_code=404, detail="Not Found")
        target_file = DIST_DIR / full_path
        if target_file.exists() and target_file.is_file():
            return FileResponse(str(target_file))
        return FileResponse(str(DIST_DIR / "index.html"))
