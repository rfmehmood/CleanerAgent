import sqlite3
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

class DatabaseManager:
    """Handles local SQLite database for scan records, quarantine, audit logs, and settings."""

    def __init__(self, db_path: Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Audit log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    action TEXT NOT NULL,
                    target_path TEXT,
                    status TEXT NOT NULL,
                    details TEXT,
                    user_approved INTEGER DEFAULT 0
                )
            """)

            # Scan history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS scan_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    scan_type TEXT,
                    total_items INTEGER,
                    total_bytes INTEGER,
                    categories_summary TEXT,
                    duration_seconds REAL
                )
            """)

            # Quarantine table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quarantine (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    original_path TEXT NOT NULL,
                    quarantine_path TEXT NOT NULL,
                    file_size INTEGER,
                    file_hash TEXT,
                    original_mtime REAL,
                    cleanup_reason TEXT,
                    category TEXT,
                    timestamp REAL,
                    restored_status INTEGER DEFAULT 0,
                    restored_timestamp REAL,
                    notes TEXT
                )
            """)

            # Cleanup history table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cleanup_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    action_type TEXT,
                    items_count INTEGER,
                    bytes_freed INTEGER,
                    status TEXT,
                    details TEXT
                )
            """)
            conn.commit()

    # --- Audit Log Operations ---
    def log_audit(self, action: str, target_path: str, status: str, details: str = "", user_approved: bool = False):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO audit_logs (timestamp, action, target_path, status, details, user_approved) VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), action, str(target_path), status, details, 1 if user_approved else 0)
            )
            conn.commit()

    def get_audit_logs(self, limit: int = 200) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    # --- Scan History Operations ---
    def record_scan(self, scan_type: str, total_items: int, total_bytes: int, categories_summary: Dict[str, Any], duration: float) -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "INSERT INTO scan_history (timestamp, scan_type, total_items, total_bytes, categories_summary, duration_seconds) VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), scan_type, total_items, total_bytes, json.dumps(categories_summary), duration)
            )
            conn.commit()
            return cursor.lastrowid

    def get_recent_scans(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM scan_history ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = []
            for row in cursor.fetchall():
                d = dict(row)
                try:
                    d["categories_summary"] = json.loads(d.get("categories_summary") or "{}")
                except Exception:
                    d["categories_summary"] = {}
                rows.append(d)
            return rows

    def get_last_scan(self) -> Optional[Dict[str, Any]]:
        scans = self.get_recent_scans(limit=1)
        return scans[0] if scans else None

    # --- Quarantine Operations ---
    def add_quarantine_record(self, original_path: str, quarantine_path: str, file_size: int, 
                              original_mtime: float, cleanup_reason: str, category: str, 
                              file_hash: str = "", notes: str = "") -> int:
        with self._get_connection() as conn:
            cursor = conn.execute(
                """INSERT INTO quarantine 
                   (original_path, quarantine_path, file_size, file_hash, original_mtime, cleanup_reason, category, timestamp, restored_status, notes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                (str(original_path), str(quarantine_path), file_size, file_hash, original_mtime, cleanup_reason, category, time.time(), notes)
            )
            conn.commit()
            return cursor.lastrowid

    def get_quarantined_items(self, include_restored: bool = False) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            query = "SELECT * FROM quarantine"
            if not include_restored:
                query += " WHERE restored_status = 0"
            query += " ORDER BY timestamp DESC"
            cursor = conn.execute(query)
            return [dict(row) for row in cursor.fetchall()]

    def mark_quarantine_restored(self, record_id: int):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE quarantine SET restored_status = 1, restored_timestamp = ? WHERE id = ?",
                (time.time(), record_id)
            )
            conn.commit()

    def remove_quarantine_record(self, record_id: int):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM quarantine WHERE id = ?", (record_id,))
            conn.commit()

    # --- Cleanup History Operations ---
    def record_cleanup(self, action_type: str, items_count: int, bytes_freed: int, status: str, details: str = ""):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO cleanup_history (timestamp, action_type, items_count, bytes_freed, status, details) VALUES (?, ?, ?, ?, ?, ?)",
                (time.time(), action_type, items_count, bytes_freed, status, details)
            )
            conn.commit()

    def get_cleanup_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM cleanup_history ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]

    def clear_history(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM scan_history")
            conn.execute("DELETE FROM cleanup_history")
            conn.execute("DELETE FROM audit_logs")
            conn.commit()
