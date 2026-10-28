import json
from typing import Dict, Any, List, Optional
from .ollama_client import OllamaClient
from .rule_fallback import RuleBasedAssistant
from ..storage.disk_analyzer import DiskStorageAnalyzer

class IntentParser:
    """
    Coordinates local AI inference (via Qwen3.5 4B in Ollama) with deterministic rule fallback.
    Ensures answers are grounded in real filesystem measurements and never claims AI is running
    unless verified.
    """

    def __init__(self, ollama_client: OllamaClient):
        self.ollama = ollama_client

    def process_user_query(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        recent_scans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Processes user query.
        Returns response dict: {mode: str, response: str, suggested_actions: list, intent: str}
        """
        # Step 1: Check if Ollama is connected and model is available
        ai_available = self.ollama.check_connection()[0] and self.ollama.is_model_available()

        if ai_available:
            try:
                ai_resp = self._query_qwen(query, candidates, recent_scans)
                if ai_resp:
                    return {
                        "mode": f"Local AI ({self.ollama.model_name})",
                        "intent": "ai_response",
                        "response": ai_resp,
                        "suggested_actions": ["Review Cleanup Center", "Start Deep Scan"],
                        "data": None
                    }
            except Exception:
                pass # Gracefully fall back to deterministic engine on any inference error

        # Step 2: Deterministic Rule-Based Fallback
        return RuleBasedAssistant.handle_query(query, candidates, recent_scans)

    def _query_qwen(self, query: str, candidates: List[Dict[str, Any]], recent_scans: List[Dict[str, Any]]) -> Optional[str]:
        # Build factual grounded context
        drives = DiskStorageAnalyzer.get_drive_summary()
        drives_summary = "\n".join([f"Drive {d['letter']}: Total {d['total_bytes']/(1024**3):.1f} GB, Used {d['used_bytes']/(1024**3):.1f} GB ({d['percent_used']}%), Free {d['free_bytes']/(1024**3):.1f} GB" for d in drives])

        candidates_summary = f"Total identified cleanup candidates: {len(candidates)}.\n"
        if candidates:
            total_size_mb = sum(c.get("size", 0) for c in candidates) / (1024*1024)
            candidates_summary += f"Total estimated recoverable space: {total_size_mb:.1f} MB.\nTop items:\n"
            for c in sorted(candidates, key=lambda x: x.get("size", 0), reverse=True)[:5]:
                candidates_summary += f"- {c.get('app_name', 'App')} ({c.get('category')}): {c.get('size', 0)/(1024*1024):.1f} MB [{c.get('safety_tier')} tier]\n"

        system_prompt = (
            "You are the Local AI PC Cleanup Agent on Windows.\n"
            "STRICT RULES:\n"
            "1. Answer ONLY using the factual ground truth data provided below.\n"
            "2. NEVER invent file paths, software names, disk sizes, or savings.\n"
            "3. If information is not in the scan data, tell the user to run a scan.\n"
            "4. NEVER output or propose code, shell scripts, or arbitrary deletion commands.\n"
            "5. Be concise, professional, privacy-conscious, and safety-focused.\n\n"
            f"--- DISK STORAGE DATA ---\n{drives_summary}\n\n"
            f"--- SCAN CANDIDATES DATA ---\n{candidates_summary}\n"
        )

        return self.ollama.generate_chat(prompt=query, system_prompt=system_prompt)
