import sys
import pytest
from PySide6.QtWidgets import QApplication
from src.ui.deep_view import CATEGORIES_CONFIG, DeepView
from src.scanner.categories import ScanCategory

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_deep_view_categories_count():
    # Verify exactly 10 distinct categories are configured
    assert len(CATEGORIES_CONFIG) == 10
    titles = [c["title"] for c in CATEGORIES_CONFIG]
    assert "Large Files" in titles
    assert "Duplicate Files" in titles
    assert "Temporary Files" in titles
    assert "Application Cache" in titles
    assert "Uninstalled App Leftovers" in titles
    assert "Browser Cache" in titles
    assert "Python & Node.js Caches" in titles
    assert "AI Models & Storage" in titles
    assert "Logs & Crash Reports" in titles
    assert "Other Cleanup Candidates" in titles

def test_deep_view_category_matching():
    sample_candidates = [
        {"path": r"C:\Temp\large.iso", "size": 600 * 1024 * 1024, "category": ScanCategory.LARGE_FILES},
        {"path": r"C:\Downloads\dup.zip", "size": 1000, "category": ScanCategory.DUPLICATES},
        {"path": r"C:\AppData\Local\Temp\cache.tmp", "size": 2000, "category": ScanCategory.TEMP_FILES},
        {"path": r"C:\AppData\Roaming\Discord\Cache", "size": 3000, "category": ScanCategory.APP_CACHE},
        {"path": r"C:\AppData\Local\OldApp", "size": 4000, "category": ScanCategory.LEFTOVERS},
        {"path": r"C:\AppData\Local\Chrome\User Data\Cache", "size": 5000, "category": ScanCategory.BROWSER_CACHE},
        {"path": r"C:\Users\User\.pip\cache", "size": 6000, "category": ScanCategory.PYTHON_CONDA},
        {"path": r"C:\Users\User\.ollama\models", "size": 7000, "category": ScanCategory.AI_MODELS, "app_name": "Ollama"},
        {"path": r"C:\Windows\Logs\cbs.log", "size": 8000, "category": ScanCategory.LOGS_CRASH},
        {"path": r"C:\$Recycle.Bin\item", "size": 9000, "category": ScanCategory.RECYCLE_BIN},
    ]

    for cfg in CATEGORIES_CONFIG:
        matches = [c for c in sample_candidates if cfg["match"](c)]
        assert len(matches) >= 1, f"Category {cfg['title']} should match at least 1 sample candidate"

def test_deep_view_unique_storage_calculation(qapp):
    # An item might match both Large Files and AI Model Storage, but must not be double counted in unique total
    shared_path = r"C:\Users\User\.ollama\large_model.bin"
    candidates = [
        {"path": shared_path, "size": 800 * 1024 * 1024, "category": ScanCategory.AI_MODELS, "app_name": "Ollama"},
        {"path": r"C:\Temp\foo.tmp", "size": 100 * 1024 * 1024, "category": ScanCategory.TEMP_FILES, "app_name": "System"}
    ]

    view = DeepView()
    view.set_candidates(candidates)

    # Unique items must be 2, and unique size must be 900 MB
    unique_items = {c.get("path"): c for c in view.all_candidates if c.get("path")}
    assert len(unique_items) == 2
    assert sum(c.get("size", 0) for c in unique_items.values()) == 900 * 1024 * 1024

    # Both Large Files and AI Models will count this item individually
    large_cfg = next(c for c in CATEGORIES_CONFIG if c["id"] == "large_files")
    ai_cfg = next(c for c in CATEGORIES_CONFIG if c["id"] == "ai_models")

    assert large_cfg["match"](candidates[0]) is True
    assert ai_cfg["match"](candidates[0]) is True
