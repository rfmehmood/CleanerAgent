import os
import time
from pathlib import Path
from typing import List, Dict, Any, Set
from .registry_scanner import WindowsInstalledAppsScanner
from ..scanner.categories import ScanCategory
from ..cleanup.safety import SafetyPolicy

# Whitelist of standard Windows / System vendors that must NEVER be flagged as leftovers
SYSTEM_VENDORS: Set[str] = {
    "microsoft",
    "windows",
    "windows defender",
    "windowspowershell",
    "dotnet",
    "nvidia",
    "intel",
    "amd",
    "realtek",
    "packages",
    "connecteddevicesplatform",
    "programs",
    "temp",
    "assembly",
    "comms",
    "crypto",
    "publishers",
    "adobe",
    "google",
    "mozilla",
    "apple",
}

class LeftoverDetector:
    """
    Scans %LOCALAPPDATA%, %APPDATA%, and %PROGRAMDATA% to detect suspected leftover folders
    from uninstalled applications by cross-referencing with registry uninstall records.
    """

    def __init__(self):
        self.installed_tokens = WindowsInstalledAppsScanner.get_installed_app_tokens()

    def scan_suspected_leftovers(self, max_items: int = 150) -> List[Dict[str, Any]]:
        leftovers = []
        search_roots = []

        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data and Path(local_app_data).exists():
            search_roots.append(Path(local_app_data))

        app_data = os.environ.get("APPDATA")
        if app_data and Path(app_data).exists():
            search_roots.append(Path(app_data))

        program_data = os.environ.get("PROGRAMDATA")
        if program_data and Path(program_data).exists():
            search_roots.append(Path(program_data))

        now = time.time()
        one_hundred_eighty_days = 180 * 86400

        for root in search_roots:
            try:
                for entry in os.scandir(root):
                    if len(leftovers) >= max_items:
                        break

                    if not entry.is_dir(follow_symlinks=False):
                        continue

                    folder_name = entry.name
                    folder_lower = folder_name.lower().strip()

                    # Ignore system vendors and protected paths
                    if folder_lower in SYSTEM_VENDORS or any(sv in folder_lower for sv in SYSTEM_VENDORS):
                        continue

                    prot, _ = SafetyPolicy.is_protected(entry.path)
                    if prot:
                        continue

                    # Check if token exists in installed apps
                    name_words = "".join(c if c.isalnum() else " " for c in folder_lower).split()
                    is_installed_match = False
                    for w in name_words:
                        if len(w) > 2 and w in self.installed_tokens:
                            is_installed_match = True
                            break

                    if is_installed_match:
                        continue

                    # If not matching any installed app, inspect folder age and contents
                    try:
                        stat = entry.stat()
                        age_days = (now - stat.st_mtime) / 86400
                        
                        # Calculate folder size (safe shallow calculation)
                        total_size = 0
                        file_count = 0
                        latest_mtime = stat.st_mtime

                        for f in Path(entry.path).rglob('*'):
                            try:
                                if f.is_file():
                                    st = f.stat()
                                    total_size += st.st_size
                                    file_count += 1
                                    if st.st_mtime > latest_mtime:
                                        latest_mtime = st.st_mtime
                            except Exception:
                                continue

                        latest_age_days = (now - latest_mtime) / 86400

                        # Evidence collection
                        evidence = []
                        confidence = "Low"

                        evidence.append(f"No corresponding entry found in Windows uninstall registry.")
                        if latest_age_days > 90:
                            evidence.append(f"No files modified in {int(latest_age_days)} days.")
                            confidence = "Medium"
                        else:
                            evidence.append(f"Recently modified ({int(latest_age_days)} days ago), may be portable or package-managed.")

                        leftovers.append({
                            "path": entry.path,
                            "is_dir": True,
                            "size": total_size,
                            "category": ScanCategory.LEFTOVERS,
                            "app_name": folder_name,
                            "confidence": confidence,
                            "safety_tier": "CAUTION",
                            "explanation": f"Suspected leftover folder '{folder_name}'. " + " ".join(evidence),
                            "consequences": "If this application was intentionally uninstalled, removing this will free disk space without issue. If it is a portable app, settings will be deleted.",
                            "recommendation": "Review folder contents before cleaning. Quarantine is recommended.",
                            "quarantine_available": True,
                            "evidence": evidence
                        })

                    except PermissionError:
                        continue
                    except Exception:
                        continue

            except Exception:
                continue

        return leftovers
