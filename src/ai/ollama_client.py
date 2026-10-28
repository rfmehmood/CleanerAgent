import json
import requests
from typing import Dict, Any, List, Optional, Tuple

class OllamaClient:
    """
    Local Ollama API adapter for Qwen3.5 4B model inference.
    Strictly local: never connects to any external cloud or telemetry services.
    """

    def __init__(self, host: str = "http://localhost:11434", model_name: str = "qwen3.5:4b"):
        self.host = host.rstrip("/")
        self.model_name = model_name
        self.is_connected = False
        self.available_models: List[str] = []

    def check_connection(self) -> Tuple[bool, str]:
        """
        Tests whether the local Ollama daemon is reachable.
        Returns: (is_available: bool, status_message: str)
        """
        try:
            resp = requests.get(f"{self.host}/api/tags", timeout=2.0)
            if resp.status_code == 200:
                self.is_connected = True
                data = resp.json()
                models = data.get("models", [])
                self.available_models = [m.get("name", "") for m in models]
                return True, f"Ollama is running. {len(self.available_models)} model(s) installed."
            return False, f"Ollama responded with status code {resp.status_code}."
        except requests.exceptions.ConnectionError:
            self.is_connected = False
            return False, "Ollama service is not running on localhost:11434."
        except Exception as e:
            self.is_connected = False
            return False, f"Ollama connection check failed: {e}"

    def is_model_available(self) -> bool:
        """Checks if the configured model (e.g. qwen3.5:4b) is already downloaded locally."""
        if not self.is_connected:
            ok, _ = self.check_connection()
            if not ok:
                return False

        # Match either exact name or model name prefix
        for m in self.available_models:
            if m == self.model_name or m.startswith(f"{self.model_name}:") or self.model_name in m:
                return True
        return False

    def generate_chat(self, prompt: str, system_prompt: str = "") -> Optional[str]:
        """
        Sends chat prompt to local Ollama instance and returns response text.
        Returns None if Ollama is unreachable or model not downloaded.
        """
        if not self.check_connection()[0]:
            return None

        url = f"{self.host}/api/chat"
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.2, # Low temperature for factual consistency
            }
        }

        try:
            resp = requests.post(url, json=payload, timeout=45.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "").strip()
            return None
        except Exception:
            return None

    @staticmethod
    def get_setup_instructions() -> str:
        return (
            "To enable Local AI features:\n"
            "1. Download and install Ollama from https://ollama.com\n"
            "2. Start Ollama and open PowerShell or Terminal\n"
            "3. Run: ollama run qwen3.5:4b\n"
            "4. Return here and click 'Verify Ollama Connection' in Settings.\n\n"
            "The application works 100% offline using Deterministic Rule-Based Analysis until Ollama is configured."
        )
