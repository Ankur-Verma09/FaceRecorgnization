import os
import shutil
import json
from pathlib import Path
from typing import Dict, Any
from backend.db.database import DatabaseManager

class ManifestUndoService:
    def __init__(self, db: DatabaseManager):
        self.db = db

    def undo_manifest(self, manifest_id: str) -> Dict[str, Any]:
        conn = self.db.get_connection()
        cur = conn.execute("SELECT * FROM sort_manifests WHERE manifest_id = ?", (manifest_id,))
        row = cur.fetchone()
        conn.close()

        if not row:
            return {"success": False, "error": f"Manifest {manifest_id} not found."}

        records = json.loads(row["manifest_json"])
        restored_count = 0

        for r in records:
            src = Path(r["source"])
            dest = Path(r["destination"])
            op = r["operation"]

            if op == "move":
                if dest.exists():
                    src.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(dest), str(src))
                    restored_count += 1
            elif op in ("copy", "symlink"):
                if dest.exists():
                    dest.unlink()
                    restored_count += 1

        return {
            "success": True,
            "manifest_id": manifest_id,
            "restored_count": restored_count
        }
