from typing import Dict, Any, List, Optional
from ..scanner.categories import ScanCategory
from ..storage.disk_analyzer import DiskStorageAnalyzer

class RuleBasedAssistant:
    """
    Deterministic rule-based conversational assistant.
    Answers user queries grounded strictly in real local filesystem measurements and scan results.
    Never hallucinates or invents file paths, sizes, or savings.
    """

    @classmethod
    def handle_query(
        cls,
        user_text: str,
        current_candidates: List[Dict[str, Any]],
        recent_scans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        text = user_text.lower().strip()

        # 1. Trigger or recommend scan
        if any(w in text for w in ["scan my pc", "start scan", "run scan", "find unnecessary files", "analyze my pc"]):
            return {
                "mode": "Rule-Based Engine",
                "intent": "start_scan",
                "response": "I can run a full local scan across your temporary files, browser caches, development caches, and application leftovers. Would you like me to initiate the scan now?",
                "suggested_actions": ["Start Full Scan", "Scan Only Dev Caches", "Search Duplicates"],
                "data": None
            }

        # 2. Why is C drive full / Storage explanation
        if any(w in text for w in ["c drive", "almost full", "drive full", "low disk space", "storage breakdown"]):
            drives = DiskStorageAnalyzer.get_drive_summary()
            c_drive = next((d for d in drives if d["letter"] == "C"), None)
            if c_drive:
                total_gb = c_drive["total_bytes"] / (1024**3)
                free_gb = c_drive["free_bytes"] / (1024**3)
                used_gb = c_drive["used_bytes"] / (1024**3)
                
                resp = (
                    f"**Drive C: Storage Breakdown**\n"
                    f"- Total Capacity: {total_gb:.1f} GB\n"
                    f"- Used Space: {used_gb:.1f} GB ({c_drive['percent_used']}%)\n"
                    f"- Available Free Space: {free_gb:.1f} GB\n\n"
                )
                if current_candidates:
                    c_candidates = [c for c in current_candidates if c.get("path", "").upper().startswith("C:")]
                    c_potential = sum(c.get("size", 0) for c in c_candidates) / (1024**3)
                    resp += f"Based on your latest scan, there are **{len(c_candidates)} potential cleanup candidates** identified on Drive C, representing an estimated **{c_potential:.2f} GB** of recoverable storage."
                else:
                    resp += "Run a **Deep Scan** to identify temporary files, app caches, and uninstalled leftovers consuming space on Drive C."

                return {
                    "mode": "Rule-Based Engine",
                    "intent": "explain_storage",
                    "response": resp,
                    "suggested_actions": ["Scan Drive C", "Open Storage Explorer"],
                    "data": c_drive
                }

        # 3. Leftover applications
        if any(w in text for w in ["leftover", "uninstalled", "orphaned"]):
            leftovers = [c for c in current_candidates if c.get("category") == ScanCategory.LEFTOVERS]
            if leftovers:
                total_leftover_bytes = sum(c.get("size", 0) for c in leftovers)
                mb = total_leftover_bytes / (1024**2)
                resp = f"Found **{len(leftovers)} suspected leftover folder(s)** totaling **{mb:.1f} MB**:\n\n"
                for item in leftovers[:5]:
                    size_str = f"{item['size'] / (1024*1024):.1f} MB"
                    resp += f"- **{item['app_name']}** ({size_str}): `{item['path']}`\n"
                if len(leftovers) > 5:
                    resp += f"\n...and {len(leftovers) - 5} more in the Cleanup Center."
            else:
                resp = "No application leftovers are currently loaded in your scan candidates. Initiate a scan with 'Application Leftovers' enabled to inspect %LOCALAPPDATA% and %APPDATA%."

            return {
                "mode": "Rule-Based Engine",
                "intent": "leftover_analysis",
                "response": resp,
                "suggested_actions": ["Review in Cleanup Center", "Scan Leftovers"],
                "data": {"count": len(leftovers)}
            }

        # 4. Dev Caches (Python & Node.js)
        if any(w in text for w in ["python", "node", "npm", "pip", "cache", "dev"]):
            dev_items = [c for c in current_candidates if c.get("category") in [ScanCategory.PYTHON_CONDA, ScanCategory.NODE_JS]]
            if dev_items:
                total_mb = sum(c.get("size", 0) for c in dev_items) / (1024**2)
                resp = f"Identified **{len(dev_items)} development package caches** totaling **{total_mb:.1f} MB**:\n\n"
                for item in dev_items:
                    resp += f"- **{item['app_name']}**: {item['size'] / (1024*1024):.1f} MB (`{item['path']}`)\n"
                resp += "\n*Note: Package caches can be cleared safely; packages will re-download when you run install commands.*"
            else:
                resp = "No Python or Node.js development caches found in the current scan results. Run a Deep Scan to check pip, conda, npm, and yarn cache directories."

            return {
                "mode": "Rule-Based Engine",
                "intent": "dev_cleanup",
                "response": resp,
                "suggested_actions": ["Scan Dev Caches", "View Cleanup Center"],
                "data": {"count": len(dev_items)}
            }

        # 5. AI Models
        if any(w in text for w in ["ai model", "ollama", "huggingface", "llm", "weights"]):
            ai_items = [c for c in current_candidates if c.get("category") == ScanCategory.AI_MODELS]
            if ai_items:
                total_gb = sum(c.get("size", 0) for c in ai_items) / (1024**3)
                resp = f"Detected **{len(ai_items)} AI model storage location(s)** totaling **{total_gb:.2f} GB**:\n\n"
                for item in ai_items:
                    resp += f"- **{item['app_name']}** ({item['size'] / (1024**3):.2f} GB): `{item['path']}`\n"
                resp += "\n*Caution: AI models are marked as CAUTION. We recommend removing models using the application CLI (e.g., 'ollama rm <model>') or reviewing carefully.*"
            else:
                resp = "No AI model caches currently loaded. Run a scan with 'AI Model Storage' enabled to locate Ollama and Hugging Face repositories."

            return {
                "mode": "Rule-Based Engine",
                "intent": "ai_models_analysis",
                "response": resp,
                "suggested_actions": ["Scan AI Models"],
                "data": {"count": len(ai_items)}
            }

        # 6. Risky recommendations
        if any(w in text for w in ["risky", "safe", "dangerous", "consequence"]):
            risky_items = [c for c in current_candidates if c.get("safety_tier") in ["RISKY", "CAUTION"]]
            if risky_items:
                resp = f"There are **{len(risky_items)} item(s)** marked as requiring caution:\n\n"
                for item in risky_items[:5]:
                    resp += f"- **{item['app_name']}** ({item['safety_tier']}): {item.get('consequences', 'Requires manual review')}\n"
                resp += "\nProtected files and system files are completely excluded from deletion."
            else:
                resp = "All currently identified cleanup candidates are in the SAFE category (temporary files, caches, and logs)."

            return {
                "mode": "Rule-Based Engine",
                "intent": "risk_explanation",
                "response": resp,
                "suggested_actions": ["Review Cleanup Center"],
                "data": {"count": len(risky_items)}
            }

        # 7. Compare scans
        if any(w in text for w in ["compare", "previous scan", "history"]):
            if len(recent_scans) >= 2:
                latest = recent_scans[0]
                prev = recent_scans[1]
                diff_items = latest.get("total_items", 0) - prev.get("total_items", 0)
                diff_bytes = latest.get("total_bytes", 0) - prev.get("total_bytes", 0)
                diff_mb = diff_bytes / (1024*1024)

                resp = (
                    f"**Scan Comparison**\n"
                    f"- Latest Scan: {latest.get('total_items', 0)} items ({latest.get('total_bytes', 0)/(1024**2):.1f} MB)\n"
                    f"- Previous Scan: {prev.get('total_items', 0)} items ({prev.get('total_bytes', 0)/(1024**2):.1f} MB)\n"
                    f"- Net Change: {'+' if diff_items >= 0 else ''}{diff_items} items ({'+' if diff_mb >= 0 else ''}{diff_mb:.1f} MB)"
                )
            elif len(recent_scans) == 1:
                resp = "Only 1 scan is recorded in history. Run another scan in the future to compare differences."
            else:
                resp = "No scan history records found yet."

            return {
                "mode": "Rule-Based Engine",
                "intent": "compare_scans",
                "response": resp,
                "suggested_actions": ["Start New Scan"],
                "data": None
            }

        # Default fallback response
        return {
            "mode": "Rule-Based Engine",
            "intent": "general_query",
            "response": (
                "I am your local AI PC Cleanup Assistant. I analyze your storage and help you recover disk space safely.\n\n"
                "You can ask me to:\n"
                "- *'Scan my PC for unnecessary files'*\n"
                "- *'Why is my C drive almost full?'*\n"
                "- *'Find leftovers from uninstalled applications'*\n"
                "- *'Find large Python and Node.js caches'*\n"
                "- *'Analyze my AI tools and downloaded models'*\n"
                "- *'Explain which cleanup recommendations are risky'*\n"
                "- *'Compare this scan with my previous scan'*"
            ),
            "suggested_actions": ["Scan PC", "Check C: Drive", "Explain Risks"],
            "data": None
        }
