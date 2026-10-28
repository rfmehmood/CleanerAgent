import pytest
import time
from pathlib import Path
from src.classifier.engine import FileClassifier
from src.scanner.categories import ScanCategory

def test_temp_file_classification(tmp_path):
    temp_dir = tmp_path / "AppData" / "Local" / "Temp"
    temp_dir.mkdir(parents=True)
    temp_file = temp_dir / "cache_123.tmp"
    temp_file.write_text("temporary data")
    
    res = FileClassifier.classify(str(temp_file), is_dir=False, size_bytes=14, mtime=time.time())
    assert res["category"] == ScanCategory.TEMP_FILES
    assert res["safety_tier"] == "SAFE"
    assert res["confidence"] == "High"
    assert res["quarantine_available"] is True

def test_log_file_classification(tmp_path):
    log_file = tmp_path / "app_debug.log"
    log_file.write_text("2026-10-28 ERROR something")
    
    res = FileClassifier.classify(str(log_file), is_dir=False, size_bytes=26, mtime=time.time())
    assert res["category"] == ScanCategory.LOGS_CRASH
    assert res["safety_tier"] == "SAFE"

def test_node_modules_safety_tier(tmp_path):
    nm_dir = tmp_path / "my_project" / "node_modules"
    nm_dir.mkdir(parents=True)
    
    res = FileClassifier.classify(str(nm_dir), is_dir=True, size_bytes=5000000, mtime=time.time())
    assert res["category"] == ScanCategory.NODE_JS
    assert res["safety_tier"] == "RISKY" # Must require explicit review

def test_python_cache_classification(tmp_path):
    pyc_file = tmp_path / "__pycache__" / "module.cpython-314.pyc"
    pyc_file.parent.mkdir(parents=True)
    pyc_file.write_bytes(b"dummy bytecode")

    res = FileClassifier.classify(str(pyc_file), is_dir=False, size_bytes=14, mtime=time.time())
    assert res["category"] == ScanCategory.PYTHON_CONDA
    assert res["safety_tier"] == "SAFE"

def test_large_file_classification(tmp_path):
    large_file = tmp_path / "big_archive.iso"
    large_file.write_text("dummy")
    # Simulate size > 500 MB
    res = FileClassifier.classify(str(large_file), is_dir=False, size_bytes=600 * 1024 * 1024, mtime=time.time())
    assert res["category"] == ScanCategory.LARGE_FILES
    assert res["safety_tier"] == "RISKY"
