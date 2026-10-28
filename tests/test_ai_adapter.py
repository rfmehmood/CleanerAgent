import pytest
from src.ai.ollama_client import OllamaClient
from src.ai.rule_fallback import RuleBasedAssistant
from src.ai.intent_parser import IntentParser
from src.scanner.categories import ScanCategory

def test_ollama_offline_handling():
    # Test with non-existent local port to simulate offline Ollama daemon
    client = OllamaClient(host="http://localhost:59999")
    ok, msg = client.check_connection()
    assert ok is False
    assert "not running" in msg.lower() or "failed" in msg.lower()
    assert client.is_model_available() is False

def test_intent_parser_switches_to_rule_fallback_when_offline():
    client = OllamaClient(host="http://localhost:59999")
    parser = IntentParser(client)
    
    query = "Why is my C drive almost full?"
    res = parser.process_user_query(
        query=query,
        candidates=[],
        recent_scans=[]
    )
    assert res["mode"] == "Rule-Based Engine"
    assert res["intent"] == "explain_storage"
    assert "Drive C" in res["response"]

def test_rule_based_assistant_leftover_query():
    candidates = [
        {
            "path": "C:\\Users\\user\\AppData\\Local\\OldProgram",
            "size": 52428800, # 50 MB
            "category": ScanCategory.LEFTOVERS,
            "app_name": "OldProgram",
            "safety_tier": "CAUTION"
        }
    ]
    res = RuleBasedAssistant.handle_query("Find uninstalled leftovers", candidates, [])
    assert res["intent"] == "leftover_analysis"
    assert "OldProgram" in res["response"]
    assert "50.0 MB" in res["response"]

def test_rule_based_assistant_dev_caches_query():
    candidates = [
        {
            "path": "C:\\Users\\user\\AppData\\Local\\pip\\cache",
            "size": 104857600, # 100 MB
            "category": ScanCategory.PYTHON_CONDA,
            "app_name": "Python Pip",
            "safety_tier": "SAFE"
        }
    ]
    res = RuleBasedAssistant.handle_query("Find Python and Node caches", candidates, [])
    assert res["intent"] == "dev_cleanup"
    assert "Python Pip" in res["response"]
    assert "100.0 MB" in res["response"]

def test_rule_based_assistant_scan_comparison():
    recent_scans = [
        {"total_items": 150, "total_bytes": 500 * 1024 * 1024},
        {"total_items": 100, "total_bytes": 300 * 1024 * 1024}
    ]
    res = RuleBasedAssistant.handle_query("Compare this scan with previous scan", [], recent_scans)
    assert res["intent"] == "compare_scans"
    assert "Net Change" in res["response"]
    assert "+50 items" in res["response"]
