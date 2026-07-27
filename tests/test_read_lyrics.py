"""Tests for read_lyrics.py — embedded lyrics reader.

These tests use mocking to avoid needing real audio files, except for
one integration test that reads from the actual music library if available.
"""
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

import read_lyrics
from read_lyrics import (
    read_lyrics as read_lyrics_func,
    read_song_info,
    read_comment,
    read_override_rating,
)


# ---------------------------------------------------------------------------
# read_lyrics — format dispatching
# ---------------------------------------------------------------------------

def test_read_lyrics_unsupported_format(tmp_path):
    """Unsupported file extension returns None."""
    fake = tmp_path / "song.wav"
    fake.write_bytes(b"\x00" * 100)
    assert read_lyrics_func(str(fake)) is None


def test_read_lyrics_nonexistent_file():
    """Nonexistent file raises an error (mutagen behavior)."""
    with pytest.raises(Exception):
        read_lyrics_func("/nonexistent/path/song.m4a")


# ---------------------------------------------------------------------------
# read_song_info
# ---------------------------------------------------------------------------

def test_read_song_info_no_lyrics(tmp_path):
    """read_song_info returns has_lyrics=False for file without lyrics."""
    fake_path = str(tmp_path / "test.m4a")
    Path(fake_path).write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_lyrics", return_value=None):
        info = read_song_info(fake_path)

    assert info["has_lyrics"] is False
    assert info["lyrics_length"] == 0
    assert info["filename"] == "test.m4a"
    assert "existing_rating" not in info


def test_read_song_info_with_lyrics(tmp_path):
    """read_song_info returns has_lyrics=True for file with real lyrics."""
    fake_path = str(tmp_path / "test.m4a")
    Path(fake_path).write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_lyrics", return_value="la la la la la la"):
        info = read_song_info(fake_path)

    assert info["has_lyrics"] is True
    assert info["lyrics_length"] == 17


def test_read_song_info_empty_lyrics(tmp_path):
    """read_song_info returns has_lyrics=False for effectively-empty lyrics.

    Some MP3 files have empty USLT frames with just a newline character.
    These should not be treated as having lyrics.
    """
    fake_path = str(tmp_path / "test.mp3")
    Path(fake_path).write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_lyrics", return_value="\n"):
        info = read_song_info(fake_path)

    assert info["has_lyrics"] is False
    assert info["lyrics_length"] == 1  # raw length is 1, but stripped is 0


def test_read_song_info_short_lyrics(tmp_path):
    """read_song_info returns has_lyrics=False for lyrics under 10 chars."""
    fake_path = str(tmp_path / "test.m4a")
    Path(fake_path).write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_lyrics", return_value="short"):
        info = read_song_info(fake_path)

    assert info["has_lyrics"] is False


# ---------------------------------------------------------------------------
# read_comment — format dispatching
# ---------------------------------------------------------------------------

def test_read_comment_m4a(tmp_path):
    """read_comment returns the ©cmt tag for M4A files."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    mock_audio = MagicMock()
    mock_audio.tags = {"\xa9cmt": ["Content Rating: G, Override Rating: X"]}
    with patch("read_lyrics.MP4", return_value=mock_audio):
        result = read_comment(str(fake))
    assert result == "Content Rating: G, Override Rating: X"


def test_read_comment_m4a_no_comment(tmp_path):
    """read_comment returns empty string for M4A with no comment tag."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    mock_audio = MagicMock()
    mock_audio.tags = {"\xa9nam": ["Song"]}
    with patch("read_lyrics.MP4", return_value=mock_audio):
        result = read_comment(str(fake))
    assert result == ""


def test_read_comment_m4a_no_tags(tmp_path):
    """read_comment returns empty string for M4A with no tags at all."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    mock_audio = MagicMock()
    mock_audio.tags = None
    with patch("read_lyrics.MP4", return_value=mock_audio):
        result = read_comment(str(fake))
    assert result == ""


def test_read_comment_mp3(tmp_path):
    """read_comment returns the COMM frame text for MP3 files."""
    fake = tmp_path / "test.mp3"
    fake.write_bytes(b"\x00" * 100)

    mock_frame = MagicMock()
    mock_frame.desc = ""
    mock_frame.text = ["Content Rating: R"]
    mock_audio = MagicMock()
    mock_audio.tags = MagicMock()
    mock_audio.tags.keys.return_value = ["COMM::eng"]
    mock_audio.tags.__getitem__ = MagicMock(return_value=mock_frame)
    mock_audio.tags.__contains__ = MagicMock(return_value=True)
    with patch("read_lyrics.MP3", return_value=mock_audio):
        result = read_comment(str(fake))
    assert result == "Content Rating: R"


def test_read_comment_mp3_no_comment(tmp_path):
    """read_comment returns empty string for MP3 with no COMM frame."""
    fake = tmp_path / "test.mp3"
    fake.write_bytes(b"\x00" * 100)

    mock_audio = MagicMock()
    mock_audio.tags = MagicMock()
    mock_audio.tags.keys.return_value = ["TIT2::eng"]
    mock_audio.tags.__contains__ = MagicMock(return_value=False)
    with patch("read_lyrics.MP3", return_value=mock_audio):
        result = read_comment(str(fake))
    assert result == ""


def test_read_comment_aiff(tmp_path):
    """read_comment returns the COMM frame text for AIFF files."""
    fake = tmp_path / "test.aiff"
    fake.write_bytes(b"\x00" * 100)

    mock_frame = MagicMock()
    mock_frame.text = ["Content Rating: PG-13"]
    mock_audio = MagicMock()
    mock_audio.tags = MagicMock()
    mock_audio.tags.getall.return_value = [mock_frame]
    with patch("read_lyrics.AIFF", return_value=mock_audio):
        result = read_comment(str(fake))
    assert result == "Content Rating: PG-13"


def test_read_comment_aiff_no_tags(tmp_path):
    """read_comment returns empty string for AIFF with no tags."""
    fake = tmp_path / "test.aiff"
    fake.write_bytes(b"\x00" * 100)

    mock_audio = MagicMock()
    mock_audio.tags = None
    with patch("read_lyrics.AIFF", return_value=mock_audio):
        result = read_comment(str(fake))
    assert result == ""


def test_read_comment_unsupported_format(tmp_path):
    """read_comment returns empty string for unsupported formats."""
    fake = tmp_path / "test.wav"
    fake.write_bytes(b"\x00" * 100)
    assert read_comment(str(fake)) == ""


# ---------------------------------------------------------------------------
# read_override_rating
# ---------------------------------------------------------------------------

def test_read_override_rating_found(tmp_path):
    """read_override_rating returns the rating when Override Rating: is present."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value="Content Rating: G, Override Rating: X"):
        assert read_override_rating(str(fake)) == "X"


def test_read_override_rating_pg13(tmp_path):
    """read_override_rating handles PG-13."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value="Override Rating: PG-13"):
        assert read_override_rating(str(fake)) == "PG-13"


def test_read_override_rating_pg8(tmp_path):
    """read_override_rating handles PG-8."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value="Override Rating: PG-8"):
        assert read_override_rating(str(fake)) == "PG-8"


def test_read_override_rating_manual_review(tmp_path):
    """read_override_rating handles MANUAL REVIEW."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value="Override Rating: MANUAL REVIEW"):
        assert read_override_rating(str(fake)) == "MANUAL REVIEW"


def test_read_override_rating_absent(tmp_path):
    """read_override_rating returns None when no override is present."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value="Content Rating: G"):
        assert read_override_rating(str(fake)) is None


def test_read_override_rating_empty_comment(tmp_path):
    """read_override_rating returns None for empty comment."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value=""):
        assert read_override_rating(str(fake)) is None


def test_read_override_rating_invalid_value(tmp_path):
    """read_override_rating returns None for unrecognized rating values."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value="Override Rating: Z"):
        assert read_override_rating(str(fake)) is None


def test_read_override_rating_case_sensitive(tmp_path):
    """read_override_rating does not match lowercase ratings."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    with patch("read_lyrics.read_comment", return_value="Override Rating: x"):
        assert read_override_rating(str(fake)) is None


def test_read_override_rating_embedded_in_text(tmp_path):
    """read_override_rating finds the override within a longer comment."""
    fake = tmp_path / "test.m4a"
    fake.write_bytes(b"\x00" * 100)

    comment = "Some note, Content Rating: G, Override Rating: R, more text"
    with patch("read_lyrics.read_comment", return_value=comment):
        assert read_override_rating(str(fake)) == "R"


# ---------------------------------------------------------------------------
# Integration: read from actual music library (if available)
# ---------------------------------------------------------------------------

MUSIC_DIR = "/media/jbod/WCS"
LATTO_FILE = os.path.join(MUSIC_DIR,
    "Latto - Big Energy (Big Energy - Single).m4a")


@pytest.mark.skipif(not os.path.exists(LATTO_FILE),
                    reason="Latto - Big Energy not found in music library")
def test_integration_latto_big_energy():
    """Integration test: read embedded lyrics from the actual Latto file."""
    lyrics = read_lyrics_func(LATTO_FILE)
    assert lyrics is not None
    assert len(lyrics) > 100
    # The embedded lyrics are the clean version
    assert "big energy" in lyrics.lower()


@pytest.mark.skipif(not os.path.exists(LATTO_FILE),
                    reason="Latto - Big Energy not found in music library")
def test_integration_latto_big_energy_song_info():
    """Integration test: read_song_info from the actual Latto file."""
    info = read_song_info(LATTO_FILE)
    assert info["has_lyrics"] is True
    assert info["lyrics_length"] > 100
