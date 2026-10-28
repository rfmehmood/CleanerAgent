import os
import hashlib
from pathlib import Path
from typing import Dict, List, Any, Callable, Optional
from ..cleanup.safety import SafetyPolicy
from ..scanner.categories import ScanCategory

class DuplicateFinder:
    """
    Multi-stage high-efficiency duplicate file detection engine:
    1. Size grouping (eliminates impossible matches instantly)
    2. Fast header hash (reads first 4KB to eliminate false matches quickly)
    3. Full SHA-256 hash confirmation
    Respects safety policies and skips protected files/directories.
    """

    def __init__(self, min_size_bytes: int = 1024):
        self.min_size_bytes = min_size_bytes
        self.is_cancelled = False

    def cancel(self):
        self.is_cancelled = True

    def find_duplicates(
        self,
        directories: List[str],
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> List[Dict[str, Any]]:
        self.is_cancelled = False
        files_by_size: Dict[int, List[Path]] = {}
        total_scanned = 0

        # Step 1: Collect all files and group by size
        for dir_path in directories:
            if self.is_cancelled:
                break
            try:
                p = Path(dir_path).resolve()
                if not p.exists():
                    continue

                for root, _, files in os.walk(str(p)):
                    if self.is_cancelled:
                        break
                    
                    root_path = Path(root)
                    prot, _ = SafetyPolicy.is_protected(str(root_path))
                    if prot:
                        continue

                    for f in files:
                        file_p = root_path / f
                        try:
                            # Skip symlinks and junctions
                            if file_p.is_symlink():
                                continue
                            
                            prot_f, _ = SafetyPolicy.is_protected(str(file_p))
                            if prot_f:
                                continue

                            size = file_p.stat().st_size
                            if size >= self.min_size_bytes:
                                files_by_size.setdefault(size, []).append(file_p)
                                total_scanned += 1
                                if progress_callback and total_scanned % 100 == 0:
                                    progress_callback(f"Cataloging: {file_p.name}", total_scanned)
                        except (PermissionError, FileNotFoundError):
                            continue
            except Exception:
                continue

        # Filter sizes with at least 2 files
        potential_sizes = {s: paths for s, paths in files_by_size.items() if len(paths) >= 2}
        duplicate_groups = []
        group_idx = 1

        # Step 2 & 3: Fast hash then Full hash
        for size, paths in potential_sizes.items():
            if self.is_cancelled:
                break

            # Fast 4KB hash grouping
            fast_hashes: Dict[str, List[Path]] = {}
            for path in paths:
                if self.is_cancelled:
                    break
                h_fast = self._hash_chunk(path, chunk_size=4096)
                if h_fast:
                    fast_hashes.setdefault(h_fast, []).append(path)

            # Full hash for buckets with >= 2 items
            for h_fast, fast_paths in fast_hashes.items():
                if len(fast_paths) < 2 or self.is_cancelled:
                    continue

                full_hashes: Dict[str, List[Path]] = {}
                for path in fast_paths:
                    if self.is_cancelled:
                        break
                    h_full = self._hash_full(path)
                    if h_full:
                        full_hashes.setdefault(h_full, []).append(path)

                for h_full, matching_paths in full_hashes.items():
                    if len(matching_paths) >= 2:
                        # Sort by modification time: keep the oldest file by default
                        sorted_paths = sorted(matching_paths, key=lambda p: p.stat().st_mtime)
                        keep_path = sorted_paths[0]
                        duplicate_paths = sorted_paths[1:]

                        duplicate_groups.append({
                            "group_id": group_idx,
                            "file_size": size,
                            "hash": h_full,
                            "keep_candidate": str(keep_path),
                            "duplicates": [
                                {
                                    "path": str(dp),
                                    "is_dir": False,
                                    "size": size,
                                    "category": ScanCategory.DUPLICATES,
                                    "app_name": "Duplicate File",
                                    "confidence": "High",
                                    "safety_tier": "CAUTION",
                                    "explanation": f"Identical file content matching {keep_path.name} (SHA-256 verified).",
                                    "consequences": "Original copy at {keep_path} will remain preserved.",
                                    "recommendation": "Safe to delete duplicate copy if not required in multiple project folders.",
                                    "quarantine_available": True,
                                    "group_id": group_idx
                                }
                                for dp in duplicate_paths
                            ]
                        })
                        group_idx += 1

        return duplicate_groups

    @staticmethod
    def _hash_chunk(file_path: Path, chunk_size: int = 4096) -> str:
        try:
            with open(file_path, "rb") as f:
                data = f.read(chunk_size)
                return hashlib.md5(data).hexdigest()
        except Exception:
            return ""

    @staticmethod
    def _hash_full(file_path: Path) -> str:
        sha = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    sha.update(chunk)
            return sha.hexdigest()
        except Exception:
            return ""
