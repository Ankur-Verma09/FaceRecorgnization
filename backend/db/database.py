import sqlite3
import json
import base64
import numpy as np
from typing import List, Dict, Any, Optional
from backend.config import DB_PATH

def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-64000;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_connection()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS images (
            image_id TEXT PRIMARY KEY,
            file_path TEXT UNIQUE,
            file_name TEXT,
            width INTEGER,
            height INTEGER,
            file_size INTEGER,
            datetime_taken TEXT,
            face_count INTEGER DEFAULT 0,
            sharpness REAL DEFAULT 100.0
        );

        CREATE TABLE IF NOT EXISTS persons (
            person_id TEXT PRIMARY KEY,
            display_name TEXT,
            thumbnail_path TEXT,
            face_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS faces (
            face_id TEXT PRIMARY KEY,
            image_id TEXT,
            bbox_x INTEGER,
            bbox_y INTEGER,
            bbox_w INTEGER,
            bbox_h INTEGER,
            confidence REAL,
            embedding BLOB,
            person_id TEXT,
            thumbnail_path TEXT,
            is_primary INTEGER DEFAULT 1,
            area_ratio REAL DEFAULT 0.01,
            sharpness REAL DEFAULT 100.0,
            cluster_eligible INTEGER DEFAULT 1,
            FOREIGN KEY (image_id) REFERENCES images(image_id),
            FOREIGN KEY (person_id) REFERENCES persons(person_id)
        );

        CREATE TABLE IF NOT EXISTS sort_manifests (
            manifest_id TEXT PRIMARY KEY,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_dir TEXT,
            target_dir TEXT,
            operation_mode TEXT,
            manifest_json TEXT
        );

        CREATE TABLE IF NOT EXISTS scan_sessions (
            session_id TEXT PRIMARY KEY,
            source_dir TEXT,
            target_dir TEXT,
            library_name TEXT,
            photos_count INTEGER DEFAULT 0,
            faces_count INTEGER DEFAULT 0,
            persons_count INTEGER DEFAULT 0,
            scanned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'completed'
        );

        CREATE TABLE IF NOT EXISTS merge_groups (
            group_id TEXT PRIMARY KEY,
            target_person_id TEXT NOT NULL,
            target_display_name TEXT,
            source_person_id TEXT NOT NULL,
            source_display_name TEXT,
            face_ids_json TEXT,
            merged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Migration: add missing columns to existing databases
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(images);")
        img_cols = [row[1] for row in cursor.fetchall()]
        if 'sharpness' not in img_cols:
            cursor.execute("ALTER TABLE images ADD COLUMN sharpness REAL DEFAULT 100.0;")

        cursor.execute("PRAGMA table_info(faces);")
        face_cols = [row[1] for row in cursor.fetchall()]
        if 'is_primary' not in face_cols:
            cursor.execute("ALTER TABLE faces ADD COLUMN is_primary INTEGER DEFAULT 1;")
        if 'area_ratio' not in face_cols:
            cursor.execute("ALTER TABLE faces ADD COLUMN area_ratio REAL DEFAULT 0.01;")
        if 'sharpness' not in face_cols:
            cursor.execute("ALTER TABLE faces ADD COLUMN sharpness REAL DEFAULT 100.0;")
        if 'cluster_eligible' not in face_cols:
            cursor.execute("ALTER TABLE faces ADD COLUMN cluster_eligible INTEGER DEFAULT 1;")

        # Ensure merge_groups table exists (for older DBs)
        cursor.execute("PRAGMA table_info(merge_groups);")
        mg_cols = [row[1] for row in cursor.fetchall()]
        if not mg_cols:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS merge_groups (
                    group_id TEXT PRIMARY KEY,
                    target_person_id TEXT NOT NULL,
                    target_display_name TEXT,
                    source_person_id TEXT NOT NULL,
                    source_display_name TEXT,
                    face_ids_json TEXT,
                    merged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_person_id ON faces(person_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_image_id ON faces(image_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_faces_cluster_eligible ON faces(cluster_eligible);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_images_dimensions ON images(file_size, width, height);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_scanned_at ON scan_sessions(scanned_at DESC);")
        
        cursor.execute("PRAGMA table_info(sort_manifests);")
        sm_cols = [row[1] for row in cursor.fetchall()]
        if 'is_undone' not in sm_cols:
            cursor.execute("ALTER TABLE sort_manifests ADD COLUMN is_undone INTEGER DEFAULT 0;")

    conn.close()

class DatabaseManager:
    def __init__(self):
        init_db()

    def get_connection(self):
        return get_connection()

    def clear_cache(self):
        conn = get_connection()
        with conn:
            conn.execute("DELETE FROM merge_groups;")
            conn.execute("DELETE FROM faces;")
            conn.execute("DELETE FROM persons;")
            conn.execute("DELETE FROM images;")
        conn.close()

    def save_image(self, image_data: Dict[str, Any]):
        conn = get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO images (image_id, file_path, file_name, width, height, file_size, datetime_taken, face_count, sharpness)
                VALUES (:image_id, :file_path, :file_name, :width, :height, :file_size, :datetime_taken, :face_count, :sharpness)
            """, image_data)
        conn.close()

    def save_faces(self, faces_data: List[Dict[str, Any]]):
        conn = get_connection()
        with conn:
            for f in faces_data:
                emb_blob = f['embedding'].tobytes() if isinstance(f['embedding'], np.ndarray) else f['embedding']
                conn.execute("""
                    INSERT OR REPLACE INTO faces (face_id, image_id, bbox_x, bbox_y, bbox_w, bbox_h, confidence, embedding, person_id, thumbnail_path, is_primary, area_ratio, sharpness, cluster_eligible)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    f['face_id'], f['image_id'], f['bbox_x'], f['bbox_y'], f['bbox_w'], f['bbox_h'],
                    f['confidence'], emb_blob, f.get('person_id'), f.get('thumbnail_path'),
                    1 if f.get('is_primary', True) else 0, f.get('area_ratio', 0.01),
                    f.get('sharpness', 100.0), f.get('cluster_eligible', 1)
                ))
        conn.close()

    def update_face_person(self, face_id: str, person_id: str):
        conn = get_connection()
        with conn:
            conn.execute("UPDATE faces SET person_id = ? WHERE face_id = ?", (person_id, face_id))
        conn.close()

    def delete_face(self, face_id: str):
        conn = get_connection()
        with conn:
            cur = conn.execute("SELECT person_id, image_id FROM faces WHERE face_id = ?", (face_id,))
            row = cur.fetchone()
            if row:
                person_id = row['person_id']
                img_id = row['image_id']
                conn.execute("DELETE FROM faces WHERE face_id = ?", (face_id,))

                if person_id:
                    cur = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (person_id,))
                    cnt = cur.fetchone()[0]
                    if cnt == 0:
                        conn.execute("DELETE FROM persons WHERE person_id = ?", (person_id,))
                    else:
                        conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (cnt, person_id))

                if img_id:
                    cur = conn.execute("SELECT COUNT(*) FROM faces WHERE image_id = ?", (img_id,))
                    cnt = cur.fetchone()[0]
                    conn.execute("UPDATE images SET face_count = ? WHERE image_id = ?", (cnt, img_id))
        conn.close()

    def reassign_face(self, face_id: str, target_person_id: str):
        conn = get_connection()
        with conn:
            cur = conn.execute("SELECT person_id FROM faces WHERE face_id = ?", (face_id,))
            row = cur.fetchone()
            if row:
                old_person_id = row['person_id']
                conn.execute("UPDATE faces SET person_id = ? WHERE face_id = ?", (target_person_id, face_id))

                if old_person_id:
                    cur = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (old_person_id,))
                    cnt = cur.fetchone()[0]
                    if cnt == 0:
                        conn.execute("DELETE FROM persons WHERE person_id = ?", (old_person_id,))
                    else:
                        conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (cnt, old_person_id))

                cur = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (target_person_id,))
                cnt = cur.fetchone()[0]
                conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (cnt, target_person_id))
        conn.close()

    def save_person(self, person_id: str, display_name: str, thumbnail_path: str, face_count: int):
        conn = get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO persons (person_id, display_name, thumbnail_path, face_count)
                VALUES (?, ?, ?, ?)
            """, (person_id, display_name, thumbnail_path, face_count))
        conn.close()

    def rename_person(self, person_id: str, new_name: str):
        conn = get_connection()
        with conn:
            conn.execute("UPDATE persons SET display_name = ? WHERE person_id = ?", (new_name, person_id))
        conn.close()

    def delete_person(self, person_id: str):
        conn = get_connection()
        with conn:
            conn.execute("DELETE FROM merge_groups WHERE target_person_id = ? OR source_person_id = ?", (person_id, person_id))
            conn.execute("UPDATE faces SET person_id = NULL WHERE person_id = ?", (person_id,))
            conn.execute("DELETE FROM persons WHERE person_id = ?", (person_id,))
        conn.close()

    def get_images_for_person(self, person_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("""
            SELECT DISTINCT i.*
            FROM images i
            JOIN faces f ON i.image_id = f.image_id
            WHERE f.person_id = ?
        """, (person_id,))
        images = [dict(row) for row in cur.fetchall()]
        conn.close()
        return images

    def merge_persons(self, source_person_id: str, target_person_id: str) -> str:
        """Merge source person into target, recording full history for unmerge."""
        import uuid as _uuid
        conn = get_connection()
        with conn:
            # Fetch names before deletion
            cur = conn.execute("SELECT display_name FROM persons WHERE person_id = ?", (source_person_id,))
            src_row = cur.fetchone()
            source_name = src_row['display_name'] if src_row else source_person_id

            cur = conn.execute("SELECT display_name FROM persons WHERE person_id = ?", (target_person_id,))
            tgt_row = cur.fetchone()
            target_name = tgt_row['display_name'] if tgt_row else target_person_id

            # Collect face_ids being transferred
            cur = conn.execute("SELECT face_id FROM faces WHERE person_id = ?", (source_person_id,))
            face_ids = [r['face_id'] for r in cur.fetchall()]

            # Move faces
            conn.execute("UPDATE faces SET person_id = ? WHERE person_id = ?", (target_person_id, source_person_id))
            conn.execute("DELETE FROM persons WHERE person_id = ?", (source_person_id,))

            # Update face count on target
            cur = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (target_person_id,))
            count = cur.fetchone()[0]
            conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (count, target_person_id))

            # Record merge in history
            group_id = str(_uuid.uuid4())[:12]
            conn.execute("""
                INSERT INTO merge_groups (group_id, target_person_id, target_display_name, source_person_id, source_display_name, face_ids_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (group_id, target_person_id, target_name, source_person_id, source_name, json.dumps(face_ids)))

        conn.close()
        return group_id

    def get_merge_groups(self) -> List[Dict[str, Any]]:
        """Return all merge history records, newest first."""
        conn = get_connection()
        cur = conn.execute("""
            SELECT mg.group_id, mg.target_person_id, mg.target_display_name,
                   mg.source_person_id, mg.source_display_name, mg.face_ids_json, mg.merged_at,
                   p.display_name as current_target_name, p.thumbnail_path as target_thumbnail
            FROM merge_groups mg
            LEFT JOIN persons p ON mg.target_person_id = p.person_id
            ORDER BY mg.merged_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def unmerge_group(self, group_id: str) -> bool:
        """
        Reverse a single merge operation:
        - Restore the source person record
        - Reassign the transferred face_ids back to the restored source person
        - Delete the merge_groups entry
        """
        import uuid as _uuid
        conn = get_connection()
        try:
            with conn:
                cur = conn.execute("SELECT * FROM merge_groups WHERE group_id = ?", (group_id,))
                row = cur.fetchone()
                if not row:
                    return False

                source_person_id = row['source_person_id']
                source_name = row['source_display_name'] or row['source_person_id']
                target_person_id = row['target_person_id']
                face_ids = json.loads(row['face_ids_json'] or '[]')

                # Find a thumbnail for the restored person (first face thumbnail)
                thumb = None
                if face_ids:
                    cur2 = conn.execute("SELECT thumbnail_path FROM faces WHERE face_id = ? LIMIT 1", (face_ids[0],))
                    r2 = cur2.fetchone()
                    if r2:
                        thumb = r2['thumbnail_path']

                # Restore source person record
                conn.execute("""
                    INSERT OR REPLACE INTO persons (person_id, display_name, thumbnail_path, face_count)
                    VALUES (?, ?, ?, ?)
                """, (source_person_id, source_name, thumb, len(face_ids)))

                # Reassign faces back to restored person
                if face_ids:
                    for i in range(0, len(face_ids), 500):
                        chunk = face_ids[i:i+500]
                        placeholders = ','.join('?' * len(chunk))
                        conn.execute(
                            f"UPDATE faces SET person_id = ? WHERE face_id IN ({placeholders})",
                            [source_person_id] + chunk
                        )

                # Update target person face count
                cur2 = conn.execute("SELECT COUNT(*) FROM faces WHERE person_id = ?", (target_person_id,))
                tgt_count = cur2.fetchone()[0]
                if tgt_count == 0:
                    conn.execute("DELETE FROM persons WHERE person_id = ?", (target_person_id,))
                else:
                    conn.execute("UPDATE persons SET face_count = ? WHERE person_id = ?", (tgt_count, target_person_id))

                # Remove the merge history record
                conn.execute("DELETE FROM merge_groups WHERE group_id = ?", (group_id,))

            return True
        except Exception as e:
            print(f"Unmerge error: {e}")
            return False
        finally:
            conn.close()

    def get_all_persons(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("""
            SELECT p.person_id, p.display_name, p.thumbnail_path, p.created_at,
                   COUNT(f.face_id) as face_count,
                   COUNT(DISTINCT f.image_id) as photo_count
            FROM persons p
            LEFT JOIN faces f ON p.person_id = f.person_id
            GROUP BY p.person_id
            ORDER BY photo_count DESC, face_count DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_all_faces_with_images(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("""
            SELECT f.face_id, f.image_id, f.bbox_x, f.bbox_y, f.bbox_w, f.bbox_h, f.confidence,
                   f.person_id, f.thumbnail_path, f.embedding, f.is_primary, f.area_ratio, f.sharpness, f.cluster_eligible,
                   i.file_path, i.file_name, i.width, i.height, i.datetime_taken, i.face_count, i.sharpness as img_sharpness
            FROM faces f
            JOIN images i ON f.image_id = i.image_id
        """)
        rows = []
        for r in cur.fetchall():
            d = dict(r)
            d['embedding'] = np.frombuffer(d['embedding'], dtype=np.float32)
            rows.append(d)
        conn.close()
        return rows

    def get_faces_for_image(self, image_id: str) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("SELECT * FROM faces WHERE image_id = ?", (image_id,))
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_all_images(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("SELECT * FROM images ORDER BY face_count DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_duplicate_images(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("""
            SELECT file_size, width, height, COUNT(*) as dup_count
            FROM images
            GROUP BY file_size, width, height
            HAVING dup_count > 1
        """)
        dup_groups = [dict(r) for r in cur.fetchall()]
        duplicates = []
        for g in dup_groups:
            cur_dups = conn.execute("""
                SELECT * FROM images
                WHERE file_size = ? AND width = ? AND height = ?
            """, (g['file_size'], g['width'], g['height']))
            duplicates.extend([dict(r) for r in cur_dups.fetchall()])
        conn.close()
        return duplicates

    def record_scan_session(self, session_data: Dict[str, Any]):
        conn = get_connection()
        with conn:
            conn.execute("""
                INSERT OR REPLACE INTO scan_sessions (session_id, source_dir, target_dir, library_name, photos_count, faces_count, persons_count, status)
                VALUES (:session_id, :source_dir, :target_dir, :library_name, :photos_count, :faces_count, :persons_count, :status)
            """, session_data)
        conn.close()

    def get_scan_sessions(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("SELECT * FROM scan_sessions ORDER BY scanned_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows

    def get_dashboard_insights(self) -> Dict[str, Any]:
        conn = get_connection()

        cur = conn.execute("SELECT COUNT(DISTINCT source_dir) FROM scan_sessions")
        total_folders = cur.fetchone()[0] or 0

        cur = conn.execute("SELECT COUNT(*) FROM images")
        total_photos = cur.fetchone()[0] or 0

        cur = conn.execute("SELECT COUNT(*) FROM faces")
        total_faces = cur.fetchone()[0] or 0

        cur = conn.execute("SELECT COUNT(*) FROM persons")
        total_persons = cur.fetchone()[0] or 0

        cur = conn.execute("""
            SELECT
                library_name,
                COUNT(*) as session_count,
                MAX(scanned_at) as last_scanned,
                MAX(source_dir) as source_dir,
                MAX(target_dir) as target_dir,
                SUM(photos_count) as total_photos,
                SUM(faces_count) as total_faces,
                SUM(persons_count) as total_persons
            FROM scan_sessions
            WHERE library_name IS NOT NULL AND library_name != ''
            GROUP BY library_name
            ORDER BY last_scanned DESC
        """)
        libraries = [dict(r) for r in cur.fetchall()]

        cur = conn.execute("SELECT * FROM scan_sessions ORDER BY scanned_at DESC LIMIT 20")
        sessions = [dict(r) for r in cur.fetchall()]

        cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(photos_count), 0) FROM scan_sessions WHERE scanned_at >= datetime('now', '-7 days')")
        r7 = cur.fetchone()
        last_7_days = {"sessions": r7[0], "photos": r7[1]}

        cur = conn.execute("SELECT COUNT(*), COALESCE(SUM(photos_count), 0) FROM scan_sessions WHERE scanned_at >= datetime('now', '-15 days')")
        r15 = cur.fetchone()
        last_15_days = {"sessions": r15[0], "photos": r15[1]}

        cur = conn.execute("SELECT strftime('%Y-%m', scanned_at) as month, COUNT(*) as sessions, COALESCE(SUM(photos_count), 0) as photos FROM scan_sessions GROUP BY month ORDER BY month DESC")
        monthly_data = [dict(r) for r in cur.fetchall()]

        cur = conn.execute("SELECT strftime('%Y', scanned_at) as year, COUNT(*) as sessions, COALESCE(SUM(photos_count), 0) as photos FROM scan_sessions GROUP BY year ORDER BY year DESC")
        yearly_data = [dict(r) for r in cur.fetchall()]

        conn.close()

        return {
            "total_folders_scanned": total_folders,
            "total_photos": total_photos,
            "total_faces": total_faces,
            "total_persons": total_persons,
            "libraries": libraries,
            "sessions": sessions,
            "time_filtered": {
                "last_7_days": last_7_days,
                "last_15_days": last_15_days,
                "monthly": monthly_data,
                "yearly": yearly_data
            }
        }

    def get_all_manifests(self) -> List[Dict[str, Any]]:
        conn = get_connection()
        cur = conn.execute("SELECT * FROM sort_manifests ORDER BY created_at DESC")
        rows = [dict(r) for r in cur.fetchall()]
        conn.close()
        return rows
