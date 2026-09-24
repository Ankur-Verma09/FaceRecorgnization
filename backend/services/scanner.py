import os
import cv2
import uuid
import numpy as np
from PIL import Image, ExifTags
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional
from backend.config import (
    SUPPORTED_EXTENSIONS, THUMBNAILS_DIR, DEFAULT_COSINE_THRESHOLD,
    MIN_FACE_SIZE_FOR_EMBEDDING, MIN_CONFIDENCE_FOR_CLUSTERING, MIN_SHARPNESS_FOR_CLUSTERING
)
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

    def _determine_cluster_eligibility(self, face_rec: Dict[str, Any]) -> bool:
        """
        Phase 1: Quality Gate — determine if a face embedding is clean enough
        to participate in automated clustering. Low-quality faces are still saved
        to the DB (for display/manual assignment) but excluded from clustering.
        """
        # Check bounding box size in original image pixels
        bbox_w = face_rec.get('bbox_w', 0)
        bbox_h = face_rec.get('bbox_h', 0)
        if bbox_w < MIN_FACE_SIZE_FOR_EMBEDDING or bbox_h < MIN_FACE_SIZE_FOR_EMBEDDING:
            return False

        # Check detection confidence
        confidence = face_rec.get('confidence', 0.0)
        if confidence < MIN_CONFIDENCE_FOR_CLUSTERING:
            return False

        # Check face crop sharpness
        sharpness = face_rec.get('sharpness', 0.0)
        if sharpness < MIN_SHARPNESS_FOR_CLUSTERING:
            return False

        return True

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
                
                max_dim = max(h, w)
                if max_dim > 1024:
                    scale_proxy = 1024.0 / max_dim
                    proxy = cv2.resize(image_bgr, (int(w * scale_proxy), int(h * scale_proxy)))
                    sharpness = calculate_sharpness(proxy)
                else:
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
                            "sharpness": face_sharpness,
                            "cluster_eligible": 1  # Will be re-evaluated below
                        }

                        # Phase 1: Quality Gate — determine cluster eligibility
                        face_rec["cluster_eligible"] = 1 if self._determine_cluster_eligibility(face_rec) else 0

                        face_records_for_db.append(face_rec)
                        all_extracted_faces.append(face_rec)
                    except Exception as e:
                        print(f"Error processing face {face_id}: {e}")

                if face_records_for_db:
                    self.db.save_faces(face_records_for_db)

                if progress_callback and (idx % 10 == 0 or idx == total_files):
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
        Globally re-cluster all stored face embeddings using adaptive multi-pass clustering.
        
        Phase 1: Only cluster_eligible faces participate in automated clustering.
        Phase 4: After clustering, re-apply saved manual merges so user corrections survive recluster.
        
        Ensures 100% of detected faces are assigned to a person profile (no unassigned faces left behind).
        Picks the sharpest face as representative thumbnail.
        """
        all_faces = self.db.get_all_faces_with_images()
        if not all_faces:
            return {"persons_count": 0}

        # ── Phase 1: Separate cluster-eligible vs ineligible faces ──
        eligible_faces = []
        ineligible_faces = []
        for f in all_faces:
            is_valid_emb = isinstance(f.get('embedding'), np.ndarray) and f['embedding'].size > 0
            is_eligible = f.get('cluster_eligible', 1) == 1
            if is_valid_emb and is_eligible:
                eligible_faces.append(f)
            else:
                ineligible_faces.append(f)

        # Find target feature dimension (most common, e.g. 512D)
        shapes = [f['embedding'].size for f in eligible_faces if isinstance(f.get('embedding'), np.ndarray)]
        target_dim = max(set(shapes), key=shapes.count) if shapes else 512

        # Retain faces matching target dimension for clustering
        clean_faces = [f for f in eligible_faces if isinstance(f.get('embedding'), np.ndarray) and f['embedding'].size == target_dim]
        embeddings = [f['embedding'] for f in clean_faces]

        labels = self.clusterer.cluster(embeddings, distance_threshold=distance_threshold) if clean_faces else []

        # ── Phase 4: Save existing manual merges BEFORE wiping ──
        saved_merge_groups = self.db.get_merge_groups()

        existing_persons = self.db.get_all_persons()
        person_to_faces_old = {}
        person_to_name_old = {}
        for p in existing_persons:
            person_to_name_old[p['person_id']] = p['display_name']
            person_to_faces_old[p['person_id']] = set()
        for f in all_faces:
            if f.get('person_id'):
                if f['person_id'] not in person_to_faces_old:
                    person_to_faces_old[f['person_id']] = set()
                person_to_faces_old[f['person_id']].add(f['face_id'])

        # Clear existing foreign key references
        conn = self.db.get_connection()
        with conn:
            conn.execute("UPDATE faces SET person_id = NULL;")
            conn.execute("DELETE FROM persons;")
            # NOTE: We do NOT delete merge_groups — we preserve them for re-application
        conn.close()

        # Group faces by cluster label
        clusters: Dict[int, List[Dict[str, Any]]] = {}
        for face_rec, label in zip(clean_faces, labels):
            if label < 0:
                # Clusterer returned -1 for invalid/filtered faces — treat as unclustered
                ineligible_faces.append(face_rec)
                continue
            clusters.setdefault(label, []).append(face_rec)

        # Also add eligible faces that didn't make it into clean_faces (dimension mismatch)
        clustered_face_ids = {f['face_id'] for f_list in clusters.values() for f in f_list}
        for f in eligible_faces:
            if f['face_id'] not in clustered_face_ids and f not in ineligible_faces:
                ineligible_faces.append(f)

        # Create person profiles from clusters
        next_label = max(clusters.keys()) + 1 if clusters else 0
        persons_summary = []
        face_to_person: Dict[str, str] = {}  # face_id -> person_id mapping

        for cluster_label, face_list in clusters.items():
            person_id = f"Person_{cluster_label + 1}"
            display_name = f"Person {cluster_label + 1}"

            new_face_ids = set(f['face_id'] for f in face_list)
            best_overlap = 0.0
            best_prev_name = None
            for prev_pid, prev_faces in person_to_faces_old.items():
                if not prev_faces:
                    continue
                intersection = new_face_ids.intersection(prev_faces)
                union = new_face_ids.union(prev_faces)
                overlap = len(intersection) / len(union) if union else 0
                if overlap > best_overlap:
                    best_overlap = overlap
                    best_prev_name = person_to_name_old.get(prev_pid)
                    
            if best_overlap > 0.30 and best_prev_name:
                display_name = best_prev_name

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
                face_to_person[f['face_id']] = person_id

            persons_summary.append({
                "person_id": person_id,
                "display_name": display_name,
                "thumbnail_path": rep_thumbnail,
                "face_count": face_count
            })

        # ── Assign ineligible faces to nearest cluster centroid or to Crowd ──
        if ineligible_faces:
            crowd_person_id = "Person_Crowd"
            crowd_display_name = "Unassigned / Crowd"
            crowd_faces = []

            cluster_centroids = {}
            if clusters:
                for cluster_label, face_list in clusters.items():
                    person_id = f"Person_{cluster_label + 1}"
                    embs = [f['embedding'].flatten() for f in face_list if isinstance(f.get('embedding'), np.ndarray) and f['embedding'].size == target_dim]
                    if embs:
                        c = np.mean(embs, axis=0).astype(np.float32)
                        c_norm = np.linalg.norm(c)
                        if c_norm > 0:
                            c = c / c_norm
                        cluster_centroids[person_id] = c

            for f in ineligible_faces:
                if not isinstance(f.get('embedding'), np.ndarray) or f['embedding'].size != target_dim:
                    crowd_faces.append(f)
                    continue

                emb = f['embedding'].flatten().astype(np.float32)
                emb_norm = np.linalg.norm(emb)
                if emb_norm > 0:
                    emb = emb / emb_norm

                best_person = None
                best_dist = float('inf')
                for person_id, centroid in cluster_centroids.items():
                    dist = 1.0 - float(np.dot(emb, centroid))
                    if dist < best_dist:
                        best_dist = dist
                        best_person = person_id

                # Only assign if within a reasonable distance (use the user threshold)
                if best_person and best_dist <= distance_threshold:
                    self.db.update_face_person(f['face_id'], best_person)
                    face_to_person[f['face_id']] = best_person
                    # Update person face count
                    conn = self.db.get_connection()
                    with conn:
                        cur = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (best_person,))
                        cnt = cur.fetchone()[0]
                        conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (cnt, best_person))
                    conn.close()
                else:
                    crowd_faces.append(f)

            if crowd_faces:
                crowd_thumbnail = crowd_faces[0].get('thumbnail_path', '')
                self.db.save_person(crowd_person_id, crowd_display_name, crowd_thumbnail, len(crowd_faces))
                for f in crowd_faces:
                    self.db.update_face_person(f['face_id'], crowd_person_id)
                    face_to_person[f['face_id']] = crowd_person_id

        # ── Phase 4: Re-apply saved manual merges ──
        if saved_merge_groups:
            import json
            for mg in saved_merge_groups:
                target_pid = mg.get('target_person_id')
                source_pid = mg.get('source_person_id')
                face_ids_json = mg.get('face_ids_json', '[]')

                try:
                    face_ids = json.loads(face_ids_json) if face_ids_json else []
                except Exception:
                    face_ids = []

                if not target_pid or not face_ids:
                    continue

                # Check if the target person still exists after re-clustering
                conn = self.db.get_connection()
                cur = conn.execute("SELECT person_id FROM persons WHERE person_id = ?", (target_pid,))
                target_exists = cur.fetchone() is not None
                conn.close()

                if not target_exists:
                    # The target person may have been renumbered — try to find by checking
                    # which person currently owns most of target's original faces
                    # Skip this merge if we can't find the target
                    continue

                # Move the faces back to the merge target
                for fid in face_ids:
                    conn = self.db.get_connection()
                    cur = conn.execute("SELECT person_id FROM faces WHERE face_id = ?", (fid,))
                    row = cur.fetchone()
                    conn.close()

                    if row and row['person_id'] and row['person_id'] != target_pid:
                        old_pid = row['person_id']
                        self.db.update_face_person(fid, target_pid)

                        # Clean up the old person if it's now empty
                        conn = self.db.get_connection()
                        with conn:
                            cur = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (old_pid,))
                            cnt = cur.fetchone()[0]
                            if cnt == 0:
                                conn.execute("DELETE FROM persons WHERE person_id = ?", (old_pid,))
                            else:
                                conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (cnt, old_pid))
                        conn.close()

                # Update target person face count
                conn = self.db.get_connection()
                with conn:
                    cur = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (target_pid,))
                    cnt = cur.fetchone()[0]
                    conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (cnt, target_pid))
                conn.close()

        return {"persons_count": len(self.db.get_all_persons())}
