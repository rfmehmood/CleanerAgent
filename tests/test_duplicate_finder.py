import pytest
from pathlib import Path
from src.storage.duplicate_finder import DuplicateFinder

def test_duplicate_file_detection(tmp_path):
    finder = DuplicateFinder(min_size_bytes=10)

    # File 1 & File 2: Exact duplicate contents
    f1 = tmp_path / "report_2026.docx"
    f2 = tmp_path / "report_2026_copy.docx"
    payload = "Identical document content for duplication testing " * 50
    f1.write_text(payload)
    f2.write_text(payload)

    # File 3: Same size, different content
    f3 = tmp_path / "other_file.docx"
    different_payload = "Different document content with exactly equal bytes" * 50
    # adjust length to match exactly
    f3.write_text(different_payload[:len(payload)])

    # File 4: Different size
    f4 = tmp_path / "tiny.txt"
    f4.write_text("small")

    groups = finder.find_duplicates([str(tmp_path)])
    
    assert len(groups) == 1
    grp = groups[0]
    assert grp["file_size"] == len(payload)
    assert len(grp["duplicates"]) == 1
    assert grp["duplicates"][0]["path"] == str(f2) or grp["duplicates"][0]["path"] == str(f1)
