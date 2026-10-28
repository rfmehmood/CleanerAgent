import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
from .safety import SafetyPolicy
from ..quarantine.manager import QuarantineManager
from ..database.db import DatabaseManager

class CleanupExecutor:
    """
    Executes validated cleanup operations strictly after explicit approval and safety checks.
    Supports:
    - Quarantine-first cleanup (default & recommended)
    - Permanent deletion (only when specifically requested and re-validated)
    - Re-validation of targets right before modification
    - Audit logging of every outcome
    """

    def __init__(self, quarantine_mgr: QuarantineManager, db: DatabaseManager, custom_protected_paths: List[str] = None):
        self.quarantine_mgr = quarantine_mgr
        self.db = db
        self.custom_protected_paths = custom_protected_paths or []

    def execute_cleanup(
        self,
        target_items: List[Dict[str, Any]],
        use_quarantine: bool = True,
        user_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Executes cleanup for a list of candidate dictionaries.
        Each candidate dict must include:
        - path: str
        - category: str
        - size: int
        - safety_tier: str (optional)
        
        Requires user_confirmed == True.
        Returns execution summary: total_items, successful_items, failed_items, bytes_freed, details.
        """
        if not user_confirmed:
            return {
                "success": False,
                "error": "Explicit user approval is strictly required before cleanup execution.",
                "items_processed": 0,
                "bytes_freed": 0,
                "results": []
            }

        total_freed = 0
        success_count = 0
        failure_count = 0
        results = []

        for item in target_items:
            path_str = item.get("path", "")
            category = item.get("category", "General")
            item_size = item.get("size", 0)

            # Step 1: Validate path
            try:
                target_p = Path(path_str).resolve()
            except Exception as e:
                results.append({"path": path_str, "status": "FAILED", "reason": f"Invalid path: {e}"})
                failure_count += 1
                continue

            # Step 2: Check existence immediately before operation
            if not target_p.exists():
                results.append({"path": path_str, "status": "SKIPPED", "reason": "Target no longer exists on disk."})
                continue

            # Step 3: Revalidate protected path policy right before action
            is_prot, prot_reason = SafetyPolicy.is_protected(str(target_p), self.custom_protected_paths)
            if is_prot:
                results.append({"path": path_str, "status": "BLOCKED", "reason": f"Safety policy blocked: {prot_reason}"})
                self.db.log_audit("cleanup_blocked", str(target_p), "BLOCKED", prot_reason, user_approved=True)
                failure_count += 1
                continue

            # Step 4: Perform cleanup
            if use_quarantine:
                ok, msg, q_id = self.quarantine_mgr.quarantine_item(
                    target_path=str(target_p),
                    category=category,
                    reason=f"Approved cleanup ({category})"
                )
                if ok:
                    success_count += 1
                    total_freed += item_size
                    results.append({"path": path_str, "status": "QUARANTINED", "record_id": q_id, "size": item_size})
                else:
                    failure_count += 1
                    results.append({"path": path_str, "status": "FAILED", "reason": msg})
            else:
                # Permanent direct deletion
                try:
                    if target_p.is_file() or target_p.is_symlink():
                        target_p.unlink()
                    elif target_p.is_dir():
                        shutil.rmtree(str(target_p))
                    
                    success_count += 1
                    total_freed += item_size
                    self.db.log_audit("permanently_deleted", str(target_p), "SUCCESS", f"Freed {item_size} bytes", user_approved=True)
                    results.append({"path": path_str, "status": "DELETED", "size": item_size})
                except PermissionError as pe:
                    failure_count += 1
                    msg = f"Access denied or file in use: {pe}"
                    self.db.log_audit("delete_failed", str(target_p), "PERMISSION_DENIED", msg, user_approved=True)
                    results.append({"path": path_str, "status": "FAILED", "reason": msg})
                except Exception as e:
                    failure_count += 1
                    msg = f"Deletion error: {e}"
                    self.db.log_audit("delete_failed", str(target_p), "ERROR", msg, user_approved=True)
                    results.append({"path": path_str, "status": "FAILED", "reason": msg})

        # Record cleanup summary in SQLite
        action_name = "Quarantine Cleanup" if use_quarantine else "Permanent Cleanup"
        self.db.record_cleanup(
            action_type=action_name,
            items_count=success_count,
            bytes_freed=total_freed,
            status="COMPLETED" if failure_count == 0 else "PARTIAL",
            details=f"Processed: {len(target_items)}, Succeeded: {success_count}, Failed: {failure_count}"
        )

        return {
            "success": True,
            "items_processed": len(target_items),
            "success_count": success_count,
            "failure_count": failure_count,
            "bytes_freed": total_freed,
            "results": results
        }
