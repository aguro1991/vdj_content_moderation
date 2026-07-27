"""Tests for rate.py — workflow orchestration (read → analyze → write)."""
import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

import rate
from rate import _write_log_line, _print_summary


# ---------------------------------------------------------------------------
# _write_log_line
# ---------------------------------------------------------------------------

def test_write_log_line_writes_override():
    """_write_log_line writes the expected OVERRIDE line."""
    mock_file = MagicMock()
    analysis = {
        "filename": "song.m4a",
        "computed_rating": "G",
        "override_rating": "X",
    }
    _write_log_line(mock_file, analysis)
    mock_file.write.assert_called_once()
    written = mock_file.write.call_args[0][0]
    assert "OVERRIDE" in written
    assert "song.m4a" in written
    assert "computed: G" in written
    assert "override: X" in written
    assert written.endswith("\n")


# ---------------------------------------------------------------------------
# _print_summary
# ---------------------------------------------------------------------------

def test_print_summary_counts(capsys):
    """_print_summary prints correct rating counts."""
    results = [
        {"rating": "G", "overridden": False},
        {"rating": "G", "overridden": False},
        {"rating": "X", "overridden": True},
        {"rating": "MANUAL REVIEW", "overridden": False},
    ]
    _print_summary(results)
    captured = capsys.readouterr()
    assert "Total: 4" in captured.err
    assert "G: 2" in captured.err
    assert "X: 1" in captured.err
    assert "MANUAL REVIEW: 1" in captured.err
    assert "Overrides applied: 1" in captured.err


def test_print_summary_dry_run(capsys):
    """_print_summary notes dry-run mode."""
    _print_summary([], dry_run=True)
    captured = capsys.readouterr()
    assert "Dry run" in captured.err


def test_print_summary_write_stats(capsys):
    """_print_summary reports write success/failure counts."""
    _print_summary([], dry_run=False, write_success=5, write_fail=1)
    captured = capsys.readouterr()
    assert "5 succeeded" in captured.err
    assert "1 failed" in captured.err


# ---------------------------------------------------------------------------
# main() — workflow integration with mocks
# ---------------------------------------------------------------------------

def test_main_dry_run_writes_no_tags(tmp_path, monkeypatch):
    """main() in dry-run mode analyzes but does not write tags."""
    fake_files = ["/fake/song1.m4a", "/fake/song2.m4a"]
    monkeypatch.setattr("rate.find_music_files", lambda d: fake_files)
    monkeypatch.setattr("rate.load_word_lists", lambda d: [])
    monkeypatch.setattr("rate.analyze_file", lambda fp, wl: {
        "path": fp,
        "filename": os.path.basename(fp),
        "rating": "G",
        "computed_rating": "G",
        "override_rating": None,
        "overridden": False,
        "has_lyrics": True,
        "lyrics_length": 100,
        "matched_words": {},
        "matched_terms": [],
    })
    mock_write = MagicMock()
    monkeypatch.setattr("rate.write_rating", mock_write)
    monkeypatch.setattr(sys, "argv", ["rate.py", str(tmp_path), "--dry-run"])

    rate.main()

    mock_write.assert_not_called()


def test_main_writes_tags(tmp_path, monkeypatch):
    """main() without --dry-run writes tags for each file."""
    fake_files = ["/fake/song1.m4a", "/fake/song2.m4a"]
    monkeypatch.setattr("rate.find_music_files", lambda d: fake_files)
    monkeypatch.setattr("rate.load_word_lists", lambda d: [])
    monkeypatch.setattr("rate.analyze_file", lambda fp, wl: {
        "path": fp,
        "filename": os.path.basename(fp),
        "rating": "G",
        "computed_rating": "G",
        "override_rating": None,
        "overridden": False,
        "has_lyrics": True,
        "lyrics_length": 100,
        "matched_words": {},
        "matched_terms": [],
    })
    mock_write = MagicMock()
    monkeypatch.setattr("rate.write_rating", mock_write)
    monkeypatch.setattr(sys, "argv", ["rate.py", str(tmp_path)])

    rate.main()

    assert mock_write.call_count == 2
    mock_write.assert_any_call("/fake/song1.m4a", "G")
    mock_write.assert_any_call("/fake/song2.m4a", "G")


def test_main_output_writes_json(tmp_path, monkeypatch):
    """main() writes a JSON report when --output is provided."""
    output_path = str(tmp_path / "report.json")
    fake_files = ["/fake/song1.m4a"]
    monkeypatch.setattr("rate.find_music_files", lambda d: fake_files)
    monkeypatch.setattr("rate.load_word_lists", lambda d: [])
    monkeypatch.setattr("rate.analyze_file", lambda fp, wl: {
        "path": fp,
        "filename": os.path.basename(fp),
        "rating": "PG-13",
        "computed_rating": "PG-13",
        "override_rating": None,
        "overridden": False,
        "has_lyrics": True,
        "lyrics_length": 100,
        "matched_words": {},
        "matched_terms": [],
    })
    monkeypatch.setattr("rate.write_rating", MagicMock())
    monkeypatch.setattr(sys, "argv", [
        "rate.py", str(tmp_path), "--dry-run", "--output", output_path,
    ])

    rate.main()

    with open(output_path) as f:
        report = json.load(f)
    assert len(report) == 1
    assert report[0]["rating"] == "PG-13"


def test_main_log_file_written(tmp_path, monkeypatch):
    """main() writes override entries to the log file."""
    log_path = str(tmp_path / "run.log")
    fake_files = ["/fake/song1.m4a", "/fake/song2.m4a"]
    monkeypatch.setattr("rate.find_music_files", lambda d: fake_files)
    monkeypatch.setattr("rate.load_word_lists", lambda d: [])

    analyses = {
        "/fake/song1.m4a": {
            "path": "/fake/song1.m4a",
            "filename": "song1.m4a",
            "rating": "X",
            "computed_rating": "G",
            "override_rating": "X",
            "overridden": True,
            "has_lyrics": True,
            "lyrics_length": 100,
            "matched_words": {},
            "matched_terms": [],
        },
        "/fake/song2.m4a": {
            "path": "/fake/song2.m4a",
            "filename": "song2.m4a",
            "rating": "G",
            "computed_rating": "G",
            "override_rating": None,
            "overridden": False,
            "has_lyrics": True,
            "lyrics_length": 100,
            "matched_words": {},
            "matched_terms": [],
        },
    }
    monkeypatch.setattr("rate.analyze_file", lambda fp, wl: analyses[fp])
    monkeypatch.setattr("rate.write_rating", MagicMock())
    monkeypatch.setattr(sys, "argv", [
        "rate.py", str(tmp_path), "--dry-run", "--log-file", log_path,
    ])

    rate.main()

    with open(log_path) as f:
        lines = f.readlines()
    assert len(lines) == 1
    assert "song1.m4a" in lines[0]
    assert "computed: G" in lines[0]
    assert "override: X" in lines[0]


def test_main_log_file_no_overrides(tmp_path, monkeypatch):
    """main() creates an empty log file when no overrides are applied."""
    log_path = str(tmp_path / "run.log")
    fake_files = ["/fake/song1.m4a"]
    monkeypatch.setattr("rate.find_music_files", lambda d: fake_files)
    monkeypatch.setattr("rate.load_word_lists", lambda d: [])
    monkeypatch.setattr("rate.analyze_file", lambda fp, wl: {
        "path": fp,
        "filename": os.path.basename(fp),
        "rating": "G",
        "computed_rating": "G",
        "override_rating": None,
        "overridden": False,
        "has_lyrics": True,
        "lyrics_length": 100,
        "matched_words": {},
        "matched_terms": [],
    })
    monkeypatch.setattr("rate.write_rating", MagicMock())
    monkeypatch.setattr(sys, "argv", [
        "rate.py", str(tmp_path), "--dry-run", "--log-file", log_path,
    ])

    rate.main()

    assert os.path.exists(log_path)
    with open(log_path) as f:
        content = f.read()
    assert content == ""


def test_main_write_failure_counted(tmp_path, monkeypatch):
    """main() counts write failures without crashing."""
    fake_files = ["/fake/song1.m4a", "/fake/song2.m4a"]
    monkeypatch.setattr("rate.find_music_files", lambda d: fake_files)
    monkeypatch.setattr("rate.load_word_lists", lambda d: [])
    monkeypatch.setattr("rate.analyze_file", lambda fp, wl: {
        "path": fp,
        "filename": os.path.basename(fp),
        "rating": "G",
        "computed_rating": "G",
        "override_rating": None,
        "overridden": False,
        "has_lyrics": True,
        "lyrics_length": 100,
        "matched_words": {},
        "matched_terms": [],
    })

    def failing_write(path, rating):
        if "song2" in path:
            raise IOError("disk full")
    monkeypatch.setattr("rate.write_rating", failing_write)
    monkeypatch.setattr(sys, "argv", ["rate.py", str(tmp_path)])

    rate.main()  # should not raise
