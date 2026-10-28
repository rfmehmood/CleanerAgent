import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Callable, Optional, Set
from .categories import ScanCategory
from ..cleanup.safety import SafetyPolicy
from ..classifier.engine import FileClassifier
from ..applications.leftover_detector import LeftoverDetector
from ..applications.dev_cleaner import DevEnvironmentCleaner

class ScannerEngine:
    """
    High-performance, read-only filesystem scanner.
    Traverses defined safe target paths, gathers file metadata without altering anything,
    classifies candidates using deterministic rules, and provides real-time progress callbacks.
    """

    def __init__(self, exclusions: Optional[List[str]] = None, max_depth: int = 5):
        self.exclusions: Set[str] = {Path(ex).resolve().as_posix().lower() for ex in (exclusions or [])}
        self.max_depth = max_depth
        self.is_cancelled = False
        self.leftover_detector = LeftoverDetector()

    def cancel(self):
        self.is_cancelled = True

    def scan_categories(
        self,
        categories: List[str],
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes a multi-category scan.
        progress_callback(current_item_str, total_items_found, current_category)
        """
        self.is_cancelled = False
        candidates: List[Dict[str, Any]] = []
        seen_paths: Set[str] = set()

        # 1. Dev Environment & AI Models Scan
        if any(cat in categories for cat in [ScanCategory.PYTHON_CONDA, ScanCategory.NODE_JS, ScanCategory.AI_MODELS]):
            if progress_callback:
                progress_callback("Scanning development caches & AI models...", len(candidates), "Development")
            
            dev_items = DevEnvironmentCleaner.scan_all_dev_targets()
            for item in dev_items:
                if self.is_cancelled:
                    return candidates
                if item["category"] in categories and item["path"] not in seen_paths:
                    seen_paths.add(item["path"])
                    candidates.append(item)

        # 2. Suspected Application Leftovers
        if ScanCategory.LEFTOVERS in categories and not self.is_cancelled:
            if progress_callback:
                progress_callback("Analyzing application leftover directories...", len(candidates), ScanCategory.LEFTOVERS)
            
            leftovers = self.leftover_detector.scan_suspected_leftovers()
            for item in leftovers:
                if self.is_cancelled:
                    return candidates
                if item["path"] not in seen_paths:
                    seen_paths.add(item["path"])
                    candidates.append(item)

        # 3. Standard Filesystem Scan Targets
        scan_targets = self._get_scan_targets_for_categories(categories)
        for target_root, cat_hint in scan_targets:
            if self.is_cancelled:
                break
            
            if not target_root.exists():
                continue

            self._traverse_directory(
                root_path=target_root,
                category_hint=cat_hint,
                candidates=candidates,
                seen_paths=seen_paths,
                current_depth=0,
                progress_callback=progress_callback
            )

        return candidates

    def _get_scan_targets_for_categories(self, categories: List[str]) -> List[tuple[Path, str]]:
        targets = []
        home = Path(os.path.expanduser("~")).resolve()
        local_app = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")).resolve()
        app_data = Path(os.environ.get("APPDATA", home / "AppData/Roaming")).resolve()
        win_dir = SafetyPolicy.get_windows_dir()

        # Temp files
        if ScanCategory.TEMP_FILES in categories:
            user_temp = Path(os.environ.get("TEMP", local_app / "Temp")).resolve()
            if user_temp.exists():
                targets.append((user_temp, ScanCategory.TEMP_FILES))

        # Browser caches
        if ScanCategory.BROWSER_CACHE in categories:
            chrome_cache = local_app / "Google/Chrome/User Data/Default/Cache"
            edge_cache = local_app / "Microsoft/Edge/User Data/Default/Cache"
            brave_cache = local_app / "BraveSoftware/Brave-Browser/User Data/Default/Cache"
            firefox_profiles = app_data / "Mozilla/Firefox/Profiles"

            for b_cache in [chrome_cache, edge_cache, brave_cache, firefox_profiles]:
                if b_cache.exists():
                    targets.append((b_cache, ScanCategory.BROWSER_CACHE))

        # Application caches
        if ScanCategory.APP_CACHE in categories:
            for p in [local_app, app_data]:
                if p.exists():
                    try:
                        for entry in os.scandir(p):
                            if entry.is_dir(follow_symlinks=False):
                                # Look for sub-caches
                                for sub in ["Cache", "Caches", "Code Cache", "GPUCache"]:
                                    cache_sub = Path(entry.path) / sub
                                    if cache_sub.exists():
                                        targets.append((cache_sub, ScanCategory.APP_CACHE))
                    except Exception:
                        pass

        # Logs & crash dumps
        if ScanCategory.LOGS_CRASH in categories:
            for log_target in [local_app / "CrashDumps", local_app / "Crashpad", home / "AppData/Local/Microsoft/Windows/WER"]:
                if log_target.exists():
                    targets.append((log_target, ScanCategory.LOGS_CRASH))

        return targets

    def _traverse_directory(
        self,
        root_path: Path,
        category_hint: str,
        candidates: List[Dict[str, Any]],
        seen_paths: Set[str],
        current_depth: int,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ):
        if self.is_cancelled or current_depth > self.max_depth:
            return

        try:
            for entry in os.scandir(root_path):
                if self.is_cancelled:
                    return

                # STRICT RULE: Never follow symlinks, junctions, or reparse points
                try:
                    if entry.is_symlink():
                        continue
                except Exception:
                    continue

                full_path_str = Path(entry.path).resolve().as_posix().lower()

                # User exclusions check
                if any(full_path_str.startswith(ex) for ex in self.exclusions):
                    continue

                # Safety check
                is_prot, _ = SafetyPolicy.is_protected(entry.path)
                if is_prot:
                    continue

                try:
                    stat_info = entry.stat(follow_symlinks=False)
                    is_dir = entry.is_dir(follow_symlinks=False)

                    if entry.path in seen_paths:
                        continue

                    # If it's a file, classify directly (skip trivial <1KB zero-sized files)
                    if not is_dir:
                        size = stat_info.st_size
                        if size < 4096: # Skip trivial <4KB files that produce 0.0 MB clutter
                            continue
                        mtime = stat_info.st_mtime
                        item_info = FileClassifier.classify(entry.path, is_dir=False, size_bytes=size, mtime=mtime)
                        
                        if item_info.get("safety_tier") != "PROTECTED":
                            seen_paths.add(entry.path)
                            candidates.append(item_info)
                            if progress_callback and len(candidates) % 25 == 0:
                                progress_callback(entry.name, len(candidates), category_hint)

                    # If it's a directory, check if directory should be aggregated as a single candidate
                    elif is_dir:
                        dir_name_lower = entry.name.lower()
                        is_cache_dir = dir_name_lower in ["cache", "caches", "cache_data", "code cache", "gpucache", "pip\\cache", "crashpad", "crashdumps"]
                        is_temp_subfolder = "temp" in root_path.name.lower() and current_depth <= 1

                        if is_cache_dir or is_temp_subfolder:
                            # Aggregate directory item
                            dir_size = 0
                            try:
                                for f in Path(entry.path).rglob('*'):
                                    if f.is_file(follow_symlinks=False):
                                        dir_size += f.stat().st_size
                            except Exception:
                                pass
                            
                            if dir_size >= 4096: # Only keep if directory has measurable content
                                item_info = FileClassifier.classify(entry.path, is_dir=True, size_bytes=dir_size, mtime=stat_info.st_mtime)
                                if item_info.get("safety_tier") != "PROTECTED":
                                    seen_paths.add(entry.path)
                                    candidates.append(item_info)
                        else:
                            # Recurse deeper
                            self._traverse_directory(
                                root_path=Path(entry.path),
                                category_hint=category_hint,
                                candidates=candidates,
                                seen_paths=seen_paths,
                                current_depth=current_depth + 1,
                                progress_callback=progress_callback
                            )

                except (PermissionError, FileNotFoundError):
                    continue
                except Exception:
                    continue

        except (PermissionError, FileNotFoundError):
            return
        except Exception:
            return
