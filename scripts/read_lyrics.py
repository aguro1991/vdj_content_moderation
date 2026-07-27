#!/usr/bin/env python3
"""Read embedded lyrics from music file metadata tags.

Supports M4A/MP4 (©lyr atom), MP3 (USLT ID3 frame), and AIFF (USLT ID3 frame).
Beets-embedded lyrics are the sole source of truth for content moderation.

This module is a library imported by main.py; it is not run directly.
"""
import os
import re
from pathlib import Path

from mutagen.mp4 import MP4
from mutagen.mp3 import MP3
from mutagen.aiff import AIFF

# Supported file extensions (case-insensitive)
SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".aiff"}

# Matches "Override Rating: X" in a comment tag.
# Only known ratings are captured; invalid values are ignored.
OVERRIDE_RATING_RE = re.compile(
    r'Override Rating: (MANUAL REVIEW|PG-13|PG-8|X|R|G)(?=\s|,|$)'
)


def read_lyrics(filepath):
    """Read embedded lyrics from a music file.

    Returns the lyrics text (str) or None if no lyrics tag is found.
    Returns empty string if the tag exists but is empty.
    """
    ext = Path(filepath).suffix.lower()

    if ext == ".m4a":
        audio = MP4(filepath)
        if audio.tags and "\xa9lyr" in audio.tags:
            lyrics = audio.tags["\xa9lyr"]
            if isinstance(lyrics, list):
                lyrics = lyrics[0] if lyrics else ""
            return str(lyrics) if lyrics else ""
        return None

    elif ext == ".mp3":
        audio = MP3(filepath)
        if audio.tags:
            for key in audio.tags.keys():
                if key.startswith("USLT"):
                    frame = audio.tags[key]
                    if frame.text:
                        # In mutagen >= 1.47, USLT.text is a str (the full
                        # lyrics text). In older versions it may be a list.
                        text = frame.text
                        if isinstance(text, list):
                            text = text[0] if text else ""
                        return str(text)
                    return ""
        return None

    elif ext == ".aiff":
        audio = AIFF(filepath)
        if audio.tags:
            for frame in audio.tags.getall("USLT"):
                if frame.text:
                    text = frame.text
                    if isinstance(text, list):
                        text = text[0] if text else ""
                    return str(text)
                return ""
        return None

    else:
        return None


def read_comment(filepath):
    """Read the comment tag from a music file.

    Returns the comment text (str) or "" if no comment tag exists.
    """
    ext = Path(filepath).suffix.lower()

    if ext == ".m4a":
        audio = MP4(filepath)
        if audio.tags and "\xa9cmt" in audio.tags:
            existing = audio.tags["\xa9cmt"]
            return str(existing[0]) if existing else ""
        return ""

    elif ext == ".mp3":
        audio = MP3(filepath)
        if audio.tags:
            for key in list(audio.tags.keys()):
                if key.startswith("COMM"):
                    frame = audio.tags[key]
                    if frame.desc == "" or frame.desc == "comment":
                        return str(frame.text[0]) if frame.text else ""
        return ""

    elif ext == ".aiff":
        audio = AIFF(filepath)
        if audio.tags:
            for frame in audio.tags.getall("COMM"):
                if hasattr(frame, 'text') and frame.text:
                    return str(frame.text[0]) if frame.text else ""
        return ""

    else:
        return ""


def read_override_rating(filepath):
    """Check if a file has an override rating in its comment tag.

    Returns the override rating string (e.g. "X") or None.
    """
    comment = read_comment(filepath)
    if not comment:
        return None
    match = OVERRIDE_RATING_RE.search(comment)
    return match.group(1) if match else None


def read_song_info(filepath):
    """Read lyrics and basic metadata from a file.

    Returns a dict with keys: path, filename, lyrics, lyrics_length, has_lyrics.
    """
    lyrics = read_lyrics(filepath)

    # Treat effectively-empty lyrics (e.g. MP3 USLT frames with just a newline)
    # as having no lyrics. Some MP3 files have empty USLT frames containing
    # a single whitespace character, which is not real lyrics.
    has_lyrics = lyrics is not None and len(lyrics.strip()) >= 10

    return {
        "path": filepath,
        "filename": os.path.basename(filepath),
        "lyrics": lyrics,
        "lyrics_length": len(lyrics) if lyrics else 0,
        "has_lyrics": has_lyrics,
    }


def find_music_files(music_dir):
    """Find all supported music files in a directory, recursively."""
    root = Path(music_dir)
    files = [
        str(f) for f in root.rglob("*")
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)
