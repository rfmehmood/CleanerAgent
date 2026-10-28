import os
import json
from pathlib import Path
from typing import List, Dict, Any
from ..scanner.categories import ScanCategory

class DevEnvironmentCleaner:
    """
    Identifies development caches (pip, conda, npm, pnpm, yarn),
    build artifacts, and AI model storage (Ollama, HuggingFace).
    Protects active project source code.
    """

    @classmethod
    def scan_all_dev_targets(cls) -> List[Dict[str, Any]]:
        results = []
        results.extend(cls.scan_python_caches())
        results.extend(cls.scan_node_caches())
        results.extend(cls.scan_ai_models())
        return results

    @classmethod
    def scan_python_caches(cls) -> List[Dict[str, Any]]:
        items = []
        home = Path(os.path.expanduser("~")).resolve()
        local_app = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")).resolve()

        # Pip Cache
        pip_cache = local_app / "pip/cache"
        if pip_cache.exists():
            size = cls._get_dir_size(pip_cache)
            if size > 0:
                items.append({
                    "path": str(pip_cache),
                    "is_dir": True,
                    "size": size,
                    "category": ScanCategory.PYTHON_CONDA,
                    "app_name": "Python Pip",
                    "confidence": "High",
                    "safety_tier": "SAFE",
                    "explanation": f"Cached Python wheel and tarball download files ({cls._format_size(size)}).",
                    "consequences": "None. Wheels will be re-downloaded if pip install is executed again.",
                    "recommendation": "Safe to clear cache.",
                    "quarantine_available": True,
                })

        # Conda package cache
        conda_pkgs = home / ".conda/pkgs"
        if conda_pkgs.exists():
            size = cls._get_dir_size(conda_pkgs)
            if size > 0:
                items.append({
                    "path": str(conda_pkgs),
                    "is_dir": True,
                    "size": size,
                    "category": ScanCategory.PYTHON_CONDA,
                    "app_name": "Conda",
                    "confidence": "High",
                    "safety_tier": "SAFE",
                    "explanation": f"Conda downloaded tarballs cache ({cls._format_size(size)}).",
                    "consequences": "Can be cleaned safely; active environments are located in envs/.",
                    "recommendation": "Safe to clean with quarantine or 'conda clean --all'.",
                    "quarantine_available": True,
                })

        return items

    @classmethod
    def scan_node_caches(cls) -> List[Dict[str, Any]]:
        items = []
        home = Path(os.path.expanduser("~")).resolve()
        local_app = Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")).resolve()
        app_data = Path(os.environ.get("APPDATA", home / "AppData/Roaming")).resolve()

        # NPM cache
        for npm_path in [local_app / "npm-cache", app_data / "npm-cache", home / ".npm"]:
            if npm_path.exists():
                size = cls._get_dir_size(npm_path)
                if size > 0:
                    items.append({
                        "path": str(npm_path),
                        "is_dir": True,
                        "size": size,
                        "category": ScanCategory.NODE_JS,
                        "app_name": "Node.js (npm)",
                        "confidence": "High",
                        "safety_tier": "SAFE",
                        "explanation": f"NPM global package download cache ({cls._format_size(size)}).",
                        "consequences": "NPM will fetch packages from npmjs.com if requested.",
                        "recommendation": "Safe to clear.",
                        "quarantine_available": True,
                    })

        # Yarn cache
        for yarn_path in [local_app / "Yarn/Cache", home / ".cache/yarn"]:
            if yarn_path.exists():
                size = cls._get_dir_size(yarn_path)
                if size > 0:
                    items.append({
                        "path": str(yarn_path),
                        "is_dir": True,
                        "size": size,
                        "category": ScanCategory.NODE_JS,
                        "app_name": "Yarn",
                        "confidence": "High",
                        "safety_tier": "SAFE",
                        "explanation": f"Yarn global cache ({cls._format_size(size)}).",
                        "consequences": "Tarballs can be re-downloaded upon running yarn.",
                        "recommendation": "Safe to clear.",
                        "quarantine_available": True,
                    })

        # pnpm store
        for pnpm_path in [local_app / "pnpm/store", home / ".local/share/pnpm/store"]:
            if pnpm_path.exists():
                size = cls._get_dir_size(pnpm_path)
                if size > 0:
                    items.append({
                        "path": str(pnpm_path),
                        "is_dir": True,
                        "size": size,
                        "category": ScanCategory.NODE_JS,
                        "app_name": "pnpm Store",
                        "confidence": "High",
                        "safety_tier": "CAUTION",
                        "explanation": f"pnpm content-addressable package store ({cls._format_size(size)}).",
                        "consequences": "Hard links in pnpm projects may be affected if pruned manually.",
                        "recommendation": "Review pnpm projects or use 'pnpm store prune'.",
                        "quarantine_available": True,
                    })

        return items

    @classmethod
    def scan_ai_models(cls) -> List[Dict[str, Any]]:
        items = []
        home = Path(os.path.expanduser("~")).resolve()

        # Ollama models
        ollama_models = home / ".ollama/models"
        if ollama_models.exists():
            size = cls._get_dir_size(ollama_models)
            if size > 0:
                # Inspect manifests to detect actual installed model names
                manifest_dir = ollama_models / "manifests/registry.ollama.ai/library"
                model_names = []
                if manifest_dir.exists():
                    for m in manifest_dir.rglob('*'):
                        if m.is_file():
                            model_names.append(f"{m.parent.name}:{m.name}" if m.parent != manifest_dir else m.name)

                models_str = ", ".join(model_names) if model_names else "Installed models"
                items.append({
                    "path": str(ollama_models),
                    "is_dir": True,
                    "size": size,
                    "category": ScanCategory.AI_MODELS,
                    "app_name": "Ollama",
                    "confidence": "High",
                    "safety_tier": "CAUTION",
                    "explanation": f"Ollama local LLM weights [{models_str}] ({cls._format_size(size)}).",
                    "consequences": "Downloaded models will need to be pulled again with 'ollama run <model>'.",
                    "recommendation": "Prefer managing models via 'ollama rm <model>' or review carefully.",
                    "quarantine_available": True,
                })

        # Hugging Face Hub
        hf_cache = home / ".cache/huggingface/hub"
        if hf_cache.exists():
            size = cls._get_dir_size(hf_cache)
            if size > 0:
                repos = [d.name.replace("models--", "").replace("--", "/") for d in hf_cache.iterdir() if d.is_dir() and d.name.startswith("models--")]
                repo_str = ", ".join(repos[:5]) if repos else "Cached model snapshots"
                if len(repos) > 5:
                    repo_str += f" (+{len(repos)-5} more)"

                items.append({
                    "path": str(hf_cache),
                    "is_dir": True,
                    "size": size,
                    "category": ScanCategory.AI_MODELS,
                    "app_name": "Hugging Face Hub",
                    "confidence": "High",
                    "safety_tier": "CAUTION",
                    "explanation": f"Hugging Face Hub model snapshots [{repo_str}] ({cls._format_size(size)}).",
                    "consequences": "Transformers / Diffusers will re-download model weights on next script run.",
                    "recommendation": "Review repositories before deletion.",
                    "quarantine_available": True,
                })

        return items

    @staticmethod
    def _get_dir_size(path: Path) -> int:
        total = 0
        try:
            for entry in path.rglob('*'):
                try:
                    if entry.is_file(follow_symlinks=False):
                        total += entry.stat().st_size
                except Exception:
                    continue
        except Exception:
            pass
        return total

    @staticmethod
    def _format_size(bytes_val: int) -> str:
        if bytes_val >= 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
        elif bytes_val >= 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.1f} MB"
        elif bytes_val >= 1024:
            return f"{bytes_val / 1024:.1f} KB"
        return f"{bytes_val} B"
