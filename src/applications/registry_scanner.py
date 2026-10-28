import winreg
import os
from typing import Set, Dict, List, Any

class WindowsInstalledAppsScanner:
    """
    Read-only Windows registry scanner to extract officially installed applications.
    Queries both 64-bit and 32-bit uninstall keys in HKLM and HKCU.
    """

    UNINSTALL_KEYS = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", winreg.KEY_WOW64_32KEY),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall", 0),
    ]

    @classmethod
    def get_installed_applications(cls) -> List[Dict[str, Any]]:
        apps = []
        seen_names = set()

        for hive, subkey_path, flags in cls.UNINSTALL_KEYS:
            try:
                access = winreg.KEY_READ | flags if flags else winreg.KEY_READ
                with winreg.OpenKey(hive, subkey_path, 0, access) as root_key:
                    num_subkeys = winreg.QueryInfoKey(root_key)[0]
                    for i in range(num_subkeys):
                        try:
                            subkey_name = winreg.EnumKey(root_key, i)
                            with winreg.OpenKey(root_key, subkey_name) as app_key:
                                display_name = cls._get_reg_val(app_key, "DisplayName")
                                if display_name and display_name not in seen_names:
                                    seen_names.add(display_name)
                                    install_loc = cls._get_reg_val(app_key, "InstallLocation")
                                    publisher = cls._get_reg_val(app_key, "Publisher")
                                    display_version = cls._get_reg_val(app_key, "DisplayVersion")
                                    apps.append({
                                        "name": display_name,
                                        "install_location": install_loc or "",
                                        "publisher": publisher or "",
                                        "version": display_version or "",
                                    })
                        except Exception:
                            continue
            except Exception:
                continue

        return apps

    @classmethod
    def get_installed_app_tokens(cls) -> Set[str]:
        """
        Tokenizes installed application names and publishers into lowercase words
        for fuzzy matching against AppData folder names.
        """
        tokens = set()
        for app in cls.get_installed_applications():
            # Add full name lower
            name = app["name"].lower().strip()
            tokens.add(name)
            # Add alphanumeric words
            words = "".join(ch if ch.isalnum() else " " for ch in name).split()
            for w in words:
                if len(w) > 2:
                    tokens.add(w)

            # Also add publisher tokens
            pub = app["publisher"].lower().strip()
            if pub:
                for w in "".join(ch if ch.isalnum() else " " for ch in pub).split():
                    if len(w) > 2:
                        tokens.add(w)
        return tokens

    @staticmethod
    def _get_reg_val(key, val_name: str) -> str:
        try:
            val, _ = winreg.QueryValueEx(key, val_name)
            return str(val).strip() if val else ""
        except Exception:
            return ""
