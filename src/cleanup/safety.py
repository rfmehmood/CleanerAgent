import os
import sys
from pathlib import Path
from typing import Tuple, List, Set

class SafetyPolicy:
    """
    Strict Deny-By-Default safety policy engine.
    Ensures Windows system critical paths, user personal files, credentials,
    and active development source code are protected from accidental deletion.
    """

    CRITICAL_SYSTEM_DIRS: Set[str] = {
        "windows",
        "system32",
        "syswow64",
        "winsxs",
        "boot",
        "recovery",
        "system volume information",
        "$recycle.bin",
        "program files\\windowsapps",
        "program files\\windows defender",
    }

    CRITICAL_SYSTEM_FILES: Set[str] = {
        "bootmgr",
        "bootnxt",
        "pagefile.sys",
        "hiberfil.sys",
        "swapfile.sys",
        "dumpstack.log",
        "ntuser.dat",
        "usrclass.dat",
    }

    USER_PERSONAL_FOLDERS: Set[str] = {
        "desktop",
        "documents",
        "pictures",
        "videos",
        "music",
        "contacts",
        "favorites",
        "links",
        "saved games",
        "searches",
        "onedrive",
    }

    CRITICAL_USER_CONFIGS: Set[str] = {
        ".ssh",
        ".gnupg",
        ".aws",
        ".azure",
        ".kube",
        ".gitconfig",
        ".bash_history",
        "credentials",
        "id_rsa",
        "id_ed25519",
        "known_hosts",
    }

    # Browser profile critical files that MUST NOT be deleted even inside cache scanning
    BROWSER_PROFILE_PROTECTED: Set[str] = {
        "login data",
        "login data-journal",
        "web data",
        "web data-journal",
        "cookies",
        "cookies-journal",
        "history",
        "history-journal",
        "bookmarks",
        "bookmarks.bak",
        "preferences",
        "secure preferences",
        "sessions",
        "session storage",
        "places.sqlite",
        "key4.db",
        "logins.json",
        "cert9.db",
    }

    SOURCE_CODE_EXTENSIONS: Set[str] = {
        ".py", ".rs", ".go", ".c", ".cpp", ".h", ".hpp", ".cs", ".java",
        ".ts", ".tsx", ".jsx", ".swift", ".kt", ".sql", ".sh", ".ps1",
        ".env", ".key", ".pem", ".cert", ".pfx", ".kdbx"
    }

    @classmethod
    def get_windows_dir(cls) -> Path:
        win = os.environ.get("WINDIR") or os.environ.get("SYSTEMROOT") or "C:\\Windows"
        return Path(win).resolve()

    @classmethod
    def get_user_home(cls) -> Path:
        return Path(os.path.expanduser("~")).resolve()

    @classmethod
    def is_protected(cls, target_path: str, custom_protected: List[str] = None) -> Tuple[bool, str]:
        """
        Validates whether a path is strictly protected from cleanup.
        Returns: (is_protected: bool, reason: str)
        """
        try:
            p = Path(target_path).resolve()
        except Exception as e:
            return True, f"Invalid or malformed path: {e}"

        # Check path existence
        if not p.exists():
            return True, "Target path does not exist on filesystem."

        path_str = str(p).lower()
        parts = [part.lower() for part in p.parts]

        # 1. Drive Root check (e.g., C:\, D:\)
        if len(p.parts) <= 1 or p == p.parent:
            return True, "Cannot target a drive root."

        # 2. Check System Files & Root Windows Files
        filename = p.name.lower()
        if filename in cls.CRITICAL_SYSTEM_FILES:
            return True, f"Critical Windows system file protected: {filename}"

        # 3. Check Windows System Directories
        win_dir = cls.get_windows_dir()
        try:
            if p == win_dir or win_dir in p.parents:
                # Only explicit temp inside C:\Windows\Temp might be scanned under elevated check,
                # but standard deny-by-default blocks C:\Windows entirely for safety!
                if "temp" not in parts:
                    return True, "System Windows directory is strictly protected."
        except Exception:
            pass

        for crit in cls.CRITICAL_SYSTEM_DIRS:
            if crit in path_str:
                if not (crit == "temp" and "windows" not in path_str):
                    return True, f"Critical system folder hierarchy protected: {crit}"

        # 4. Check Root User Personal Folders
        home = cls.get_user_home()
        for personal in cls.USER_PERSONAL_FOLDERS:
            personal_dir = (home / personal).resolve()
            if p == personal_dir:
                return True, f"User personal folder protected: {personal}"
            # Protect directly inside personal folder unless it's explicitly inside an app's cache
            if personal_dir in p.parents and len(p.relative_to(personal_dir).parts) <= 1:
                return True, f"Root item in user's {personal} folder is protected."

        # 5. Check Critical Security / Credentials Folders
        for crit_conf in cls.CRITICAL_USER_CONFIGS:
            if crit_conf in parts or filename == crit_conf:
                return True, f"Security credentials / config protected: {crit_conf}"

        # 6. Check Browser Profiles and Password Stores
        if filename in cls.BROWSER_PROFILE_PROTECTED:
            return True, f"Browser identity, history, or credential database protected: {filename}"

        # 7. Check Source Code protection
        if p.is_file() and p.suffix.lower() in cls.SOURCE_CODE_EXTENSIONS:
            # Don't delete individual source files directly
            return True, f"Source code / secret key file protected: {p.suffix}"

        # 8. Check Git Repository Metadata
        if ".git" in parts:
            return True, "Git repository internals (.git) are strictly protected."

        # 9. Check Symlinks and Junctions
        if p.is_symlink():
            return True, "Filesystem symbolic link is protected to avoid target traversal."

        # 10. Check Custom User-Defined Protected Paths
        if custom_protected:
            for cp in custom_protected:
                try:
                    cp_path = Path(cp).resolve()
                    if p == cp_path or cp_path in p.parents:
                        return True, f"Protected by user preference: {cp}"
                except Exception:
                    continue

        return False, ""

    @classmethod
    def evaluate_safety_tier(cls, category: str, is_dir: bool, path_str: str) -> str:
        """
        Assigns qualitative safety classification:
        - 'SAFE': Recognized temporary or cache items easily regenerable.
        - 'CAUTION': Leftover folder, log file, old cache.
        - 'RISKY': Development dependencies, node_modules, large archives, requires explicit user awareness.
        - 'PROTECTED': Blocked from any cleanup.
        """
        prot, _ = cls.is_protected(path_str)
        if prot:
            return "PROTECTED"

        cat = category.lower()
        if "temp" in cat or "browser_cache" in cat or "app_cache" in cat or "log" in cat or "recycle_bin" in cat:
            return "SAFE"
        elif "leftover" in cat or "duplicate" in cat or "ai_model" in cat or "old_cache" in cat:
            return "CAUTION"
        elif "dev_env" in cat or "node_modules" in cat or "venv" in cat or "build_artifact" in cat or "large_file" in cat:
            return "RISKY"
        
        return "CAUTION"
