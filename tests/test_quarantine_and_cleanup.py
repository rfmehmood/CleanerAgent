import pytest
from pathlib import Path
from src.database.db import DatabaseManager
from src.quarantine.manager import QuarantineManager
from src.cleanup.executor import CleanupExecutor

@pytest.fixture
def temp_env(tmp_path):
    db_path = tmp_path / "test.db"
    quarantine_dir = tmp_path / "quarantine"
    db = DatabaseManager(db_path)
    quar_mgr = QuarantineManager(quarantine_dir, db)
    executor = CleanupExecutor(quar_mgr, db)
    return db, quar_mgr, executor, tmp_path

def test_quarantine_and_restore_file(temp_env):
    db, quar_mgr, executor, tmp_path = temp_env
    
    # Create synthetic candidate file
    candidate_file = tmp_path / "app_temp_data.tmp"
    original_content = "some temporary cache payload"
    candidate_file.write_text(original_content)
    
    assert candidate_file.exists()

    # Quarantine item
    ok, msg, record_id = quar_mgr.quarantine_item(
        target_path=str(candidate_file),
        category="Temporary Files",
        reason="Test cleanup"
    )
    assert ok is True
    assert record_id is not None
    assert not candidate_file.exists() # original file moved

    # Verify quarantine db entry
    records = db.get_quarantined_items()
    assert len(records) == 1
    assert records[0]["original_path"] == str(candidate_file)
    assert records[0]["restored_status"] == 0

    # Restore item
    ok_restore, msg_restore = quar_mgr.restore_item(record_id)
    assert ok_restore is True
    assert candidate_file.exists()
    assert candidate_file.read_text() == original_content

    # Verify db status marked restored
    active_records = db.get_quarantined_items(include_restored=False)
    assert len(active_records) == 0

def test_restore_conflict_prevention(temp_env):
    db, quar_mgr, executor, tmp_path = temp_env
    
    candidate_file = tmp_path / "cache.tmp"
    candidate_file.write_text("initial")
    
    ok, _, rec_id = quar_mgr.quarantine_item(str(candidate_file), "Temp", "reason")
    assert ok is True

    # Recreate file at destination to simulate external recreation
    candidate_file.write_text("new content created by another app")

    # Attempt restore: must NOT overwrite!
    ok_restore, err_msg = quar_mgr.restore_item(rec_id)
    assert ok_restore is False
    assert "already contains" in err_msg.lower()

def test_cleanup_requires_explicit_user_approval(temp_env):
    db, quar_mgr, executor, tmp_path = temp_env
    
    file_p = tmp_path / "unapproved.tmp"
    file_p.write_text("dummy")

    # Call executor without user_confirmed
    res = executor.execute_cleanup(
        target_items=[{"path": str(file_p), "category": "Temp", "size": 5}],
        use_quarantine=True,
        user_confirmed=False
    )
    assert res["success"] is False
    assert "explicit user approval" in res["error"].lower()
    assert file_p.exists() # File remains untouched!

def test_cleanup_rejects_protected_path(temp_env):
    db, quar_mgr, executor, tmp_path = temp_env
    
    # Try to clean system directory with user_confirmed=True
    res = executor.execute_cleanup(
        target_items=[{"path": "C:\\Windows\\System32", "category": "System", "size": 1000}],
        use_quarantine=True,
        user_confirmed=True
    )
    assert res["success_count"] == 0
    assert res["failure_count"] == 1
    assert res["results"][0]["status"] == "BLOCKED"
