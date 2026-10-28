import os
import pytest
from pathlib import Path
from src.cleanup.safety import SafetyPolicy

def test_drive_root_protection():
    # Root of drive must be protected
    prot, reason = SafetyPolicy.is_protected("C:\\")
    assert prot is True
    assert "drive root" in reason.lower()

def test_critical_system_folder_protection(tmp_path):
    # Simulated Windows path
    prot, reason = SafetyPolicy.is_protected("C:\\Windows\\System32")
    assert prot is True
    assert "protected" in reason.lower()

def test_security_credentials_protection(tmp_path):
    ssh_file = tmp_path / "id_rsa"
    ssh_file.write_text("dummy key")
    prot, reason = SafetyPolicy.is_protected(str(ssh_file))
    assert prot is True
    assert "credentials" in reason.lower() or "protected" in reason.lower()

def test_git_repository_protection(tmp_path):
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    git_head = git_dir / "HEAD"
    git_head.write_text("ref: refs/heads/main")
    prot, reason = SafetyPolicy.is_protected(str(git_head))
    assert prot is True
    assert ".git" in reason.lower()

def test_source_code_protection(tmp_path):
    source_file = tmp_path / "main.py"
    source_file.write_text("print('hello')")
    prot, reason = SafetyPolicy.is_protected(str(source_file))
    assert prot is True
    assert "source code" in reason.lower()

def test_custom_user_protection(tmp_path):
    custom_dir = tmp_path / "MyImportantData"
    custom_dir.mkdir()
    child = custom_dir / "file.txt"
    child.write_text("important")
    
    # Without custom protection
    prot, _ = SafetyPolicy.is_protected(str(child))
    assert prot is False

    # With custom protection
    prot, reason = SafetyPolicy.is_protected(str(child), custom_protected=[str(custom_dir)])
    assert prot is True
    assert "user preference" in reason.lower()

def test_path_traversal_rejection(tmp_path):
    # Path with invalid or non-existent traversal
    prot, _ = SafetyPolicy.is_protected("C:\\Windows\\..\\Windows\\System32\\cmd.exe")
    assert prot is True
