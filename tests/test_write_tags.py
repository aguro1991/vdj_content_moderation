"""Tests for write_tags.py — comment building, override preservation, and write_rating dispatch."""
import os
from unittest.mock import patch, MagicMock

import pytest

from write_tags import build_comment, write_rating


def test_build_comment_simple():
    """build_comment creates a new comment when none exists."""
    assert build_comment("G") == "Content Rating: G"


def test_build_comment_replaces_existing_rating():
    """build_comment replaces an existing Content Rating."""
    result = build_comment("R", "Content Rating: G, some note")
    assert result == "Content Rating: R, some note"


def test_build_comment_removes_legacy_ai_rating():
    """build_comment removes legacy 'AI Content Rating' format."""
    result = build_comment("G", "AI Content Rating: R, AI Content Rating Date: 2024-01-01")
    assert result == "Content Rating: G"


def test_build_comment_preserves_override_rating():
    """build_comment preserves 'Override Rating: X' when updating Content Rating."""
    existing = "Content Rating: G, Override Rating: X"
    result = build_comment("R", existing)
    assert "Override Rating: X" in result
    assert "Content Rating: R" in result
    # The old Content Rating: G should be gone
    assert "Content Rating: G" not in result


def test_build_comment_preserves_override_with_manual_review():
    """build_comment preserves 'Override Rating: MANUAL REVIEW'."""
    existing = "Content Rating: PG-13, Override Rating: MANUAL REVIEW"
    result = build_comment("G", existing)
    assert "Override Rating: MANUAL REVIEW" in result
    assert "Content Rating: G" in result


def test_build_comment_override_only():
    """build_comment handles a comment with only an override and no content rating."""
    existing = "Override Rating: X"
    result = build_comment("G", existing)
    assert "Override Rating: X" in result
    assert "Content Rating: G" in result


# ---------------------------------------------------------------------------
# write_rating — format dispatch
# ---------------------------------------------------------------------------

def test_write_rating_file_not_found():
    """write_rating raises FileNotFoundError for missing files."""
    with pytest.raises(FileNotFoundError):
        write_rating("/nonexistent/song.m4a", "G")


def test_write_rating_unsupported_format(tmp_path):
    """write_rating raises ValueError for unsupported file extensions."""
    fake = tmp_path / "test.wav"
    fake.write_bytes(b"\x00" * 100)
    with pytest.raises(ValueError, match="Unsupported file format"):
        write_rating(str(fake), "G")


def test_write_rating_dispatches_m4a(tmp_path):
    """write_rating dispatches to write_m4a_metadata for .m4a files."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)
    with patch("write_tags.write_m4a_metadata", return_value="Content Rating: G") as mock:
        result = write_rating(str(fake), "G")
    assert result == "Content Rating: G"
    mock.assert_called_once_with(str(fake), "G")


def test_write_rating_dispatches_mp3(tmp_path):
    """write_rating dispatches to write_mp3_metadata for .mp3 files."""
    fake = tmp_path / "test.mp3"
    fake.write_bytes(b"\x00" * 100)
    with patch("write_tags.write_mp3_metadata", return_value="Content Rating: R") as mock:
        result = write_rating(str(fake), "R")
    assert result == "Content Rating: R"
    mock.assert_called_once_with(str(fake), "R")


def test_write_rating_dispatches_aiff(tmp_path):
    """write_rating dispatches to write_aiff_metadata for .aiff files."""
    fake = tmp_path / "test.aiff"
    fake.write_bytes(b"\x00" * 100)
    with patch("write_tags.write_aiff_metadata", return_value="Content Rating: PG-13") as mock:
        result = write_rating(str(fake), "PG-13")
    assert result == "Content Rating: PG-13"
    mock.assert_called_once_with(str(fake), "PG-13")
