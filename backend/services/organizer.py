import os
import shutil
import uuid
import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from backend.db.database import DatabaseManager
from backend.config import DEFAULT_GROUP_THRESHOLD

class PhotoOrganizerService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def execute_organization(
        self,
        target_dir: str,
        library_name: str = "",
        operation_mode: str = "copy", # "copy", "move", "symlink"
        couple_pair: Optional[List[str]] = None, # e.g. ["Person_1", "Person_2"] (e.g. Groom & Bride)
        couple_folder_name: str = "Groom_and_Bride",
        group_folder_name: str = "Group_Photos",
        scenery_folder_name: str = "Scenery_and_Objects",
        group_threshold: int = DEFAULT_GROUP_THRESHOLD,
        progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
    ) -> Dict[str, Any]:
        """
        Professional File Organizer Engine with Primary Subject Scoring:
        When couple_pair is provided: ONLY exports photos featuring Person 1 and/or Person 2.
        All photos of other people, scenery, or unrelated groups are strictly filtered out.
        """
        if not target_dir:
            raise ValueError("Target directory must be provided.")

        safe_lib_name = "".join([c for c in library_name if c.isalnum() or c in (' ', '_', '-')]).strip()
        if safe_lib_name:
            target_base = Path(target_dir) / safe_lib_name
        else:
            target_base = Path(target_dir)

        target_base.mkdir(parents=True, exist_ok=True)

        faces_data = self.db.get_all_faces_with_images()
        all_images = self.db.get_all_images()
        all_persons = {p['person_id']: p['display_name'] for p in self.db.get_all_persons()}

        # Map each image_id to the list of PRIMARY person_ids present in that image
        image_to_primary_persons: Dict[str, List[str]] = {}
        image_to_all_persons: Dict[str, List[str]] = {}

        for f in faces_data:
            img_id = f['image_id']
            p_id = f['person_id']
            is_prim = f.get('is_primary', 1) == 1
            if p_id:
                image_to_all_persons.setdefault(img_id, []).append(p_id)
                if is_prim:
                    image_to_primary_persons.setdefault(img_id, []).append(p_id)

        manifest_records = []
        couple_set = set(couple_pair) if couple_pair and len(couple_pair) >= 2 else None

        total_to_process = len(all_images)
        processed_images = 0

        for idx, img in enumerate(all_images, 1):
            img_id = img['image_id']
            src_path = Path(img['file_path'])
            if not src_path.exists():
                continue

            # Primary Subject faces vs Total faces
            primary_persons = list(set(image_to_primary_persons.get(img_id, [])))
            all_persons_in_img = list(set(image_to_all_persons.get(img_id, [])))
            primary_count = len(primary_persons)
            total_face_count = img['face_count']

            dest_folder = None

            # ── MODE A: COUPLE FILTER MODE (Selected 2 Persons) ──
            if couple_set:
                active_set = set(primary_persons) if primary_persons else set(all_persons_in_img)
                all_set = set(all_persons_in_img)

                # Check if photo contains Person 1 or Person 2
                couple_overlap = active_set.intersection(couple_set)
                if not couple_overlap:
                    couple_overlap = all_set.intersection(couple_set)

                # STRICT FILTER: If neither Person 1 nor Person 2 is in this photo, SKIP IT!
                if not couple_overlap:
                    continue

                safe_couple_folder = "".join([c for c in couple_folder_name if c.isalnum() or c in (' ', '_', '-')]).strip() or "Groom_and_Bride"
                couple_root = target_base / safe_couple_folder

                # Case A1: Both Person 1 and Person 2 are present in the photo
                if couple_set.issubset(active_set) or couple_set.issubset(all_set):
                    if len(active_set) == 2:
                        dest_folder = couple_root / "Couple_Photos"
                    else:
                        dest_folder = couple_root / "Couple_With_Guests"

                # Case A2: Only 1 of the couple members is present in the photo
                else:
                    p_id = list(couple_overlap)[0]
                    p_name = all_persons.get(p_id, p_id)
                    safe_p_name = "".join([c for c in p_name if c.isalnum() or c in (' ', '_', '-')]).strip()

                    if len(active_set) == 1:
                        dest_folder = couple_root / f"Solo_{safe_p_name}"
                    else:
                        dest_folder = couple_root / f"Solo_{safe_p_name}_With_Guests"

            # ── MODE B: FULL GENERAL ORGANIZATION (No couple filter active) ──
            else:
                safe_scenery_folder = "".join([c for c in scenery_folder_name if c.isalnum() or c in (' ', '_', '-')]).strip() or "Scenery_and_Objects"
                safe_group_folder = "".join([c for c in group_folder_name if c.isalnum() or c in (' ', '_', '-')]).strip() or "Group_Photos"

                # RULE 1: Scenery / Objects (0 faces)
                if total_face_count == 0:
                    dest_folder = target_base / safe_scenery_folder

                # RULE 2: Group Photos (Primary faces >= group_threshold)
                elif primary_count >= group_threshold or (primary_count == 0 and total_face_count >= group_threshold):
                    dest_folder = target_base / safe_group_folder

                # RULE 3: Individual Person Solo Folder (Uses Primary Subject)
                elif len(primary_persons) == 1:
                    p_id = primary_persons[0]
                    p_name = all_persons.get(p_id, p_id)
                    safe_name = "".join([c for c in p_name if c.isalnum() or c in (' ', '_', '-')]).strip()
                    dest_folder = target_base / safe_name

                # RULE 4: Fallback to All Persons in Image if Primary is unassigned
                elif len(all_persons_in_img) == 1:
                    p_id = all_persons_in_img[0]
                    p_name = all_persons.get(p_id, p_id)
                    safe_name = "".join([c for c in p_name if c.isalnum() or c in (' ', '_', '-')]).strip()
                    dest_folder = target_base / safe_name

                # RULE 5: Other Multi-Person / Mixed Pairs
                else:
                    dest_folder = target_base / "Other_Photos"

            if dest_folder is None:
                continue

            dest_folder.mkdir(parents=True, exist_ok=True)

            # Preserve 2nd shooter / parent directory prefix to prevent filename collision across multiple camera bodies
            parent_prefix = src_path.parent.name
            dest_file_path = dest_folder / f"{parent_prefix}_{src_path.name}" if parent_prefix and parent_prefix != src_path.stem else dest_folder / src_path.name

            counter = 1
            while dest_file_path.exists():
                dest_file_path = dest_folder / f"{src_path.stem}_{counter}{src_path.suffix}"
                counter += 1

            # Perform file operation
            try:
                if operation_mode == "move":
                    shutil.move(str(src_path), str(dest_file_path))
                    conn = self.db.get_connection()
                    with conn:
                        conn.execute("UPDATE images SET file_path = ? WHERE image_id = ?", (str(dest_file_path), img_id))
                    conn.close()
                elif operation_mode == "symlink":
                    try:
                        os.symlink(str(src_path), str(dest_file_path))
                    except OSError as e:
                        print(f"Symlink failed for {src_path}: {e}. Falling back to copy2.")
                        shutil.copy2(str(src_path), str(dest_file_path))
                else: # "copy" default
                    shutil.copy2(str(src_path), str(dest_file_path))

                manifest_records.append({
                    "source": str(src_path),
                    "destination": str(dest_file_path),
                    "operation": operation_mode
                })
                processed_images += 1
            except Exception as e:
                print(f"Error organizing file {src_path} -> {dest_file_path}: {e}")

            if progress_callback and (idx % 5 == 0 or idx == total_to_process):
                progress_callback({
                    "status": "exporting",
                    "exported_count": idx,
                    "total_files": total_to_process,
                    "current_file": src_path.name,
                    "target_dir": str(target_base)
                })

        # Save manifest record
        manifest_id = str(uuid.uuid4())[:8]
        manifest_json = json.dumps(manifest_records, indent=2)

        conn = self.db.get_connection()
        with conn:
            conn.execute("""
                INSERT INTO sort_manifests (manifest_id, source_dir, target_dir, operation_mode, manifest_json)
                VALUES (?, ?, ?, ?, ?)
            """, (manifest_id, target_dir, str(target_base), operation_mode, manifest_json))
        conn.close()

        if progress_callback:
            progress_callback({
                "status": "export_completed",
                "exported_count": total_to_process,
                "total_files": total_to_process,
                "target_dir": str(target_base),
                "manifest_id": manifest_id
            })

        return {
            "manifest_id": manifest_id,
            "processed_count": processed_images,
            "library_name": safe_lib_name,
            "target_dir": str(target_base),
            "mode": operation_mode
        }
