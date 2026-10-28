import os
import json
from pathlib import Path
from typing import List, Dict, Any

DEFAULT_CONFIG: Dict[str, Any] = {
    "ollama_host": "http://localhost:11434",
    "model_name": "qwen3.5:4b",
    "scan_depth": 6,
    "min_file_age_days": 0,
    "min_file_size_mb": 0,
    "theme": "dark",
    "background_monitoring_enabled": False,
    "monitor_interval_minutes": 60,
    "custom_exclusions": [],
    "custom_protected_paths": [],
    "quarantine_retention_days": 30,
    "max_display_items": 1000,
}

class SettingsManager:
    """Manages local persistent configuration in %LOCALAPPDATA%/AIPCCleanupAgent/config.json"""
    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
            self.config_dir = Path(base) / "AIPCCleanupAgent"
        else:
            self.config_dir = Path(config_dir)
        
        self.config_file = self.config_dir / "config.json"
        self.quarantine_dir = self.config_dir / "quarantine"
        self.db_path = self.config_dir / "pc_cleanup.db"
        
        self._ensure_dirs()
        self.config = self._load()

    def _ensure_dirs(self):
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            # Fallback to local directory if permissions fail
            self.config_dir = Path("./data").resolve()
            self.quarantine_dir = self.config_dir / "quarantine"
            self.db_path = self.config_dir / "pc_cleanup.db"
            self.config_file = self.config_dir / "config.json"
            self.config_dir.mkdir(parents=True, exist_ok=True)
            self.quarantine_dir.mkdir(parents=True, exist_ok=True)

    def _load(self) -> Dict[str, Any]:
        cfg = DEFAULT_CONFIG.copy()
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        cfg.update(data)
            except Exception:
                pass
        return cfg

    def save(self):
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        self.config[key] = value
        self.save()

    def get_ollama_host(self) -> str:
        return self.config.get("ollama_host", "http://localhost:11434")

    def get_model_name(self) -> str:
        return self.config.get("model_name", "qwen3.5:4b")

    def get_exclusions(self) -> List[str]:
        return self.config.get("custom_exclusions", [])

    def add_exclusion(self, path_str: str):
        ex = self.get_exclusions()
        if path_str not in ex:
            ex.append(path_str)
            self.set("custom_exclusions", ex)

    def remove_exclusion(self, path_str: str):
        ex = self.get_exclusions()
        if path_str in ex:
            ex.remove(path_str)
            self.set("custom_exclusions", ex)

    def get_custom_protected_paths(self) -> List[str]:
        return self.config.get("custom_protected_paths", [])

    def add_custom_protected_path(self, path_str: str):
        paths = self.get_custom_protected_paths()
        if path_str not in paths:
            paths.append(path_str)
            self.set("custom_protected_paths", paths)
