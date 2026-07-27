#!/usr/bin/env python3
"""Write Content Rating metadata to music files.

Each run is a fresh iteration: the rating replaces whatever Content Rating
currently exists in the file's comment tag. No confidence scores, no CSV
history, no preservation of prior ratings.

This module is a library imported by main.py; it is not run directly.

MANUAL REVIEW is written to the tag (not skipped) so that missing-lyrics
state is visible rather than silently preserving stale ratings.
"""
import os
import re

from mutagen.mp3 import MP3
from mutagen.id3 import COMM
from mutagen.mp4 import MP4
from mutagen.aiff import AIFF

# Matches both the current format and the legacy "AI Content Rating" format
# so that old comments are cleaned up when a file is re-rated.
RATING_REGEX = r',?\s*(?:AI )?Content Rating: [A-Z0-9-]+(?:,?\s*AI Content Rating Date: [0-9-]+)?\s*,?'


def build_comment(rating, existing_comment=""):
    cleaned = re.sub(RATING_REGEX, '', existing_comment).strip().strip(',').strip()
    new_prefix = f"Content Rating: {rating}"
    if cleaned:
        return f"{new_prefix}, {cleaned}"
    return new_prefix


def write_mp3_metadata(path, rating):
    audio = MP3(path)
    if audio.tags is None:
        audio.add_tags()
    existing = ""
    for key in list(audio.tags.keys()):
        if key.startswith("COMM"):
            frame = audio.tags[key]
            if frame.desc == "" or frame.desc == "comment":
                existing = frame.text[0] if frame.text else ""
                del audio.tags[key]
    comment = build_comment(rating, existing)
    audio.tags.add(COMM(encoding=3, lang='eng', desc='', text=comment))
    audio.save(v1=0, v2_version=4)
    return comment


def write_m4a_metadata(path, rating):
    audio = MP4(path)
    existing = ""
    if audio.tags and "\xa9cmt" in audio.tags:
        existing = audio.tags["\xa9cmt"][0] if audio.tags["\xa9cmt"] else ""
    comment = build_comment(rating, existing)
    audio.tags["\xa9cmt"] = [comment]
    audio.save()
    return comment


def write_aiff_metadata(path, rating):
    audio = AIFF(path)
    existing = ""
    if audio.tags and "COMM" in audio.tags:
        frames = audio.tags.getall("COMM")
        for frame in frames:
            if hasattr(frame, 'text') and frame.text:
                existing = str(frame.text[0]) if frame.text else ""
                break
    comment = build_comment(rating, existing)
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(COMM(encoding=3, lang='eng', desc='', text=comment))
    audio.save()
    return comment


def write_rating(path, rating):
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    extension = os.path.splitext(path)[1].lower()
    if extension == ".mp3":
        return write_mp3_metadata(path, rating)
    if extension == ".m4a":
        return write_m4a_metadata(path, rating)
    if extension == ".aiff":
        return write_aiff_metadata(path, rating)
    raise ValueError(f"Unsupported file format: {extension}")
