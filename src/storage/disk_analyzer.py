import os
import shutil
from pathlib import Path
from typing import List, Dict, Any

class DiskStorageAnalyzer:
    """
    Analyzes physical and logical storage across Windows disk drives.
    Provides storage breakdowns, available capacity, and folder size calculations.
    """

    @classmethod
    def get_drive_summary(cls) -> List[Dict[str, Any]]:
        drives = []
        # On Windows, check available drive letters
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            drive_root = f"{letter}:\\"
            if os.path.exists(drive_root):
                try:
                    usage = shutil.disk_usage(drive_root)
                    drives.append({
                        "drive": drive_root,
                        "letter": letter,
                        "total_bytes": usage.total,
                        "used_bytes": usage.used,
                        "free_bytes": usage.free,
                        "percent_used": round((usage.used / usage.total) * 100, 1) if usage.total > 0 else 0,
                    })
                except Exception:
                    continue
        return drives

    @classmethod
    def analyze_folder_breakdown(cls, target_dir: str, max_depth: int = 2) -> Dict[str, Any]:
        """
        Calculates size breakdown of subdirectories within a given folder up to max_depth.
        Gracefully handles permission errors without crashing.
        """
        p = Path(target_dir).resolve()
        if not p.exists() or not p.is_dir():
            return {"error": "Target directory does not exist or is not a directory."}

        subfolders = []
        total_folder_size = 0
        inaccessible_items = 0

        try:
            for entry in os.scandir(p):
                try:
                    if entry.is_symlink():
                        continue

                    if entry.is_dir(follow_symlinks=False):
                        dir_size, file_count, inacc = cls._calculate_dir_stats(Path(entry.path), max_depth=max_depth-1)
                        inaccessible_items += inacc
                        total_folder_size += dir_size
                        subfolders.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": True,
                            "size": dir_size,
                            "file_count": file_count,
                            "mtime": entry.stat().st_mtime,
                        })
                    elif entry.is_file(follow_symlinks=False):
                        size = entry.stat().st_size
                        total_folder_size += size
                        subfolders.append({
                            "name": entry.name,
                            "path": entry.path,
                            "is_dir": False,
                            "size": size,
                            "file_count": 1,
                            "mtime": entry.stat().st_mtime,
                        })
                except PermissionError:
                    inaccessible_items += 1
                except Exception:
                    continue
        except PermissionError:
            return {"error": "Access denied to directory.", "inaccessible": True}

        # Sort subfolders by size descending
        subfolders.sort(key=lambda x: x["size"], reverse=True)

        return {
            "root_path": str(p),
            "total_size": total_folder_size,
            "children": subfolders,
            "inaccessible_count": inaccessible_items
        }

    @classmethod
    def _calculate_dir_stats(cls, path: Path, max_depth: int) -> tuple[int, int, int]:
        total_size = 0
        file_count = 0
        inaccessible = 0

        try:
            for entry in os.scandir(path):
                try:
                    if entry.is_symlink():
                        continue
                    if entry.is_file(follow_symlinks=False):
                        total_size += entry.stat().st_size
                        file_count += 1
                    elif entry.is_dir(follow_symlinks=False) and max_depth > 0:
                        s, c, inacc = cls._calculate_dir_stats(Path(entry.path), max_depth - 1)
                        total_size += s
                        file_count += c
                        inaccessible += inacc
                except (PermissionError, FileNotFoundError):
                    inaccessible += 1
                except Exception:
                    continue
        except PermissionError:
            inaccessible += 1
        except Exception:
            pass

        return total_size, file_count, inaccessible
