import os
import cv2
import uuid
import numpy as np
from PIL import Image, ExifTags
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from backend.config import SUPPORTED_EXTENSIONS, THUMBNAILS_DIR, DEFAULT_COSINE_THRESHOLD
from backend.ai.detector import FaceDetectorEngine, read_image_unicode, write_image_unicode, calculate_sharpness
from backend.ai.embedder import FaceEmbedderEngine
from backend.ai.clusterer import FaceClusterer
from backend.db.database import DatabaseManager

class PhotoScannerService:
    def __init__(self, db: DatabaseManager):
        self.db = db
        self.detector = FaceDetectorEngine()
        self.embedder = FaceEmbedderEngine()
        self.clusterer = FaceClusterer()
        self.cancel_requested = False

    def request_cancel(self):
        self.cancel_requested = True

    def reset_cancel(self):
        self.cancel_requested = False

    def get_photo_files(self, source_dir: str) -> List[Path]:
        path = Path(source_dir)
        photo_files = []
        if not path.exists():
            return []
        for p in path.rglob("*"):
            if self.cancel_requested:
                break
            # Skip symlinks to avoid duplicates and loops
            if p.is_symlink():
                continue
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
                photo_files.append(p)
        return photo_files

    def extract_datetime_taken(self, file_path: Path) -> Optional[str]:
        try:
            image = Image.open(file_path)
            exif = image._getexif()
            if exif:
                for tag, value in exif.items():
                    tag_name = ExifTags.TAGS.get(tag, tag)
                    if tag_name in ("DateTimeOriginal", "DateTime"):
                        return str(value)
        except Exception:
            pass
        return None

    def scan_directory(self, source_dir: str, progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        self.reset_cancel()
        self.db.clear_cache()
        files = self.get_photo_files(source_dir)
        total_files = len(files)

        if total_files == 0:
            if progress_callback:
                progress_callback({
                    "status": "completed",
                    "scanned_count": 0,
                    "total_files": 0,
                    "total_faces_found": 0,
                    "persons_count": 0,
                    "message": "No supported photo files found in source folder."
                })
            return {"total_files": 0, "faces_found": 0, "persons_count": 0}

        all_extracted_faces = []

        try:
            for idx, file_path in enumerate(files, 1):
                # Cancellation Check
                if self.cancel_requested:
                    if progress_callback:
                        progress_callback({
                            "status": "cancelled",
                            "scanned_count": idx - 1,
                            "total_files": total_files,
                            "total_faces_found": len(all_extracted_faces),
                            "persons_count": len(self.db.get_all_persons()),
                            "message": "Scan process stopped by user."
                        })
                    return {"status": "cancelled", "scanned_count": idx - 1, "faces_found": len(all_extracted_faces)}

                file_str = str(file_path)
                image_id = str(uuid.uuid4())[:8]

                image_bgr = read_image_unicode(file_str)
                if image_bgr is None:
                    continue

                h, w, _ = image_bgr.shape
                file_size = file_path.stat().st_size
                dt_taken = self.extract_datetime_taken(file_path)
                sharpness = calculate_sharpness(image_bgr)

                detected_faces = self.detector.detect_faces(image_bgr)
                face_count = len(detected_faces)

                image_record = {
                    "image_id": image_id,
                    "file_path": file_str,
                    "file_name": file_path.name,
                    "width": w,
                    "height": h,
                    "file_size": file_size,
                    "datetime_taken": dt_taken,
                    "face_count": face_count,
                    "sharpness": sharpness
                }
                self.db.save_image(image_record)

                face_records_for_db = []
                for f_idx, face in enumerate(detected_faces):
                    face_id = f"f_{image_id}_{f_idx}"
                    bbox = face['bbox']
                    raw = face['raw']

                    try:
                        aligned_face = self.embedder.align_and_crop(image_bgr, raw)
                        embedding = self.embedder.extract_embedding(aligned_face)

                        # Compute per-face sharpness on the aligned crop
                        face_sharpness = calculate_sharpness(aligned_face)

                        thumb_filename = f"{face_id}.jpg"
                        thumb_path = THUMBNAILS_DIR / thumb_filename
                        write_image_unicode(str(thumb_path), aligned_face)

                        face_rec = {
                            "face_id": face_id,
                            "image_id": image_id,
                            "bbox_x": bbox[0],
                            "bbox_y": bbox[1],
                            "bbox_w": bbox[2],
                            "bbox_h": bbox[3],
                            "confidence": face['confidence'],
                            "embedding": embedding,
                            "person_id": None,
                            "thumbnail_path": str(thumb_path),
                            "is_primary": face.get('is_primary', True),
                            "area_ratio": face.get('area_ratio', 0.01),
                            "sharpness": face_sharpness
                        }
                        face_records_for_db.append(face_rec)
                        all_extracted_faces.append(face_rec)
                    except Exception as e:
                        print(f"Error processing face {face_id}: {e}")

                if face_records_for_db:
                    self.db.save_faces(face_records_for_db)

                if progress_callback:
                    progress_callback({
                        "scanned_count": idx,
                        "total_files": total_files,
                        "current_file": file_path.name,
                        "total_faces_found": len(all_extracted_faces),
                        "status": "scanning"
                    })

            # Check Cancellation before Clustering
            if self.cancel_requested:
                if progress_callback:
                    progress_callback({
                        "status": "cancelled",
                        "scanned_count": total_files,
                        "total_files": total_files,
                        "total_faces_found": len(all_extracted_faces),
                        "message": "Scan process stopped by user."
                    })
                return {"status": "cancelled"}

            # Step 2: Cluster all extracted faces into person groups
            if progress_callback:
                progress_callback({
                    "status": "clustering",
                    "scanned_count": total_files,
                    "total_files": total_files,
                    "total_faces_found": len(all_extracted_faces),
                    "message": f"Clustering {len(all_extracted_faces)} detected faces into individual persons..."
                })

            self.recluster(DEFAULT_COSINE_THRESHOLD)

            persons_count = len(self.db.get_all_persons())
            if progress_callback:
                progress_callback({
                    "status": "completed",
                    "scanned_count": total_files,
                    "total_files": total_files,
                    "total_faces_found": len(all_extracted_faces),
                    "persons_count": persons_count
                })

            return {
                "total_files": total_files,
                "faces_found": len(all_extracted_faces),
                "persons_count": persons_count
            }

        except Exception as e:
            print(f"Unhandled error in scan_directory: {e}")
            if progress_callback:
                progress_callback({
                    "status": "error",
                    "message": f"Scan failed: {str(e)}"
                })
            raise e

    def recluster(self, distance_threshold: float = DEFAULT_COSINE_THRESHOLD) -> Dict[str, Any]:
        """
        Globally re-cluster all stored face embeddings using two-stage agglomerative clustering.
        Ensures 100% of detected faces are assigned to a person profile (no unassigned faces left behind).
        Picks the sharpest face as representative thumbnail.
        """
        all_faces = self.db.get_all_faces_with_images()
        if not all_faces:
            return {"persons_count": 0}

        # Filter faces with valid non-empty embeddings
        valid_faces = [f for f in all_faces if isinstance(f.get('embedding'), np.ndarray) and f['embedding'].size > 0]
        if not valid_faces:
            valid_faces = all_faces

        # Find target feature dimension (most common, e.g. 512D)
        shapes = [f['embedding'].size for f in valid_faces if isinstance(f.get('embedding'), np.ndarray)]
        target_dim = max(set(shapes), key=shapes.count) if shapes else 512

        # Retain faces matching target dimension for clustering
        clean_faces = [f for f in valid_faces if isinstance(f.get('embedding'), np.ndarray) and f['embedding'].size == target_dim]
        embeddings = [f['embedding'] for f in clean_faces]

        labels = self.clusterer.cluster(embeddings, distance_threshold=distance_threshold) if clean_faces else []

        # Clear existing foreign key references first
        conn = self.db.get_connection()
        with conn:
            conn.execute("UPDATE faces SET person_id = NULL;")
            conn.execute("DELETE FROM merge_groups;")
            conn.execute("DELETE FROM persons;")
        conn.close()

        # Group faces by cluster label
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for face_rec, label in zip(clean_faces, labels):
            clusters.setdefault(label, []).append(face_rec)

        # Ensure any unassigned / fallback faces get standalone person profiles (zero faces dropped)
        clustered_face_ids = {f['face_id'] for f in clean_faces}
        unclustered_faces = [f for f in all_faces if f['face_id'] not in clustered_face_ids]

        next_label = max(clusters.keys()) + 1 if clusters else 0
        for f in unclustered_faces:
            clusters[next_label] = [f]
            next_label += 1

        persons_summary = []
        for cluster_label, face_list in clusters.items():
            person_id = f"Person_{cluster_label + 1}"
            display_name = f"Person {cluster_label + 1}"

            # Pick sharpest face as representative thumbnail
            def face_score(f):
                sharpness = f.get('sharpness') or f.get('img_sharpness') or 0.0
                confidence = f.get('confidence', 0.0)
                is_primary = 1 if f.get('is_primary') else 0
                return (is_primary * 1000) + (sharpness * 0.5) + (confidence * 100)

            best_face = max(face_list, key=face_score)
            rep_thumbnail = best_face['thumbnail_path']
            face_count = len(face_list)

            # Insert person record FIRST to satisfy Foreign Key constraint
            self.db.save_person(person_id, display_name, rep_thumbnail, face_count)

            # Update faces to reference the newly saved person
            for f in face_list:
                self.db.update_face_person(f['face_id'], person_id)

            persons_summary.append({
                "person_id": person_id,
                "display_name": display_name,
                "thumbnail_path": rep_thumbnail,
                "face_count": face_count
            })

        return {"persons_count": len(persons_summary)}
