from typing import Dict, Any, List, Optional

class AIIntent:
    START_SCAN = "start_scan"
    EXPLAIN_STORAGE = "explain_storage"
    LEFTOVER_ANALYSIS = "leftover_analysis"
    DEV_CLEANUP = "dev_cleanup"
    AI_MODELS_ANALYSIS = "ai_models_analysis"
    DUPLICATE_SEARCH = "duplicate_search"
    RISK_EXPLANATION = "risk_explanation"
    COMPARE_SCANS = "compare_scans"
    GENERAL_QUERY = "general_query"

AI_RESPONSE_SCHEMA = {
    "intent": str,
    "confidence": float,
    "response_text": str,
    "suggested_actions": List[str],
    "grounded_data": Optional[Dict[str, Any]],
}
