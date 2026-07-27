#!/usr/bin/env python3
"""Analyze embedded lyrics against word lists to compute content ratings.

Beets-embedded lyrics are the sole source of truth. No web searching,
no confidence scoring, no comparison with prior ratings, and no clean-version
detection — the embedded lyrics are trusted as authoritative.

Uses the same curated YAML word lists as vdj_content_moderation, with
context-aware matching: terms marked with moderation.skip_patterns (e.g. "ho"
used as a vocalization) are skipped when the context matches a skip pattern.

This module is a library imported by main.py; it is not run directly.
"""
import os
import re
import sys
from pathlib import Path

import yaml

from read_lyrics import read_lyrics, read_song_info, find_music_files, read_override_rating

# Map YAML filename → rating
YAML_TO_RATING = {
    "slurs.yaml": "X",
    "sexual-content.yaml": "R",
    "severe-swear-words.yaml": "PG-13",
    "other-swear-words.yaml": "PG-8",
}

# Default lists directory (from vdj_content_moderation)
DEFAULT_LISTS_DIR = str(Path(__file__).parent.parent / "lists")


def load_word_lists(lists_dir):
    """Load all word lists from structured YAML files.

    Returns a list of (rating, forms, moderation_config) tuples where
    moderation_config is a dict with context/skip_patterns or None.
    """
    word_lists = []
    for yaml_file, rating in YAML_TO_RATING.items():
        path = Path(lists_dir) / yaml_file
        if not path.exists():
            print(f"Warning: {path} not found, skipping", file=sys.stderr)
            continue
        data = yaml.safe_load(path.read_text())
        for entry in data["words"]:
            forms = entry["forms"]
            mod = entry.get("moderation")
            word_lists.append((rating, forms, mod))
    return word_lists


def find_matches(text, forms, moderation=None):
    """Find word-boundary matches of forms in text, applying context rules.

    Returns a list of (form, position, context_snippet) tuples for matches
    that pass the context filters.
    """
    matches = []
    text_lower = text.lower()

    for form in forms:
        form_lower = form.lower()
        # Build a word-boundary regex for this form.
        # For forms ending in a non-word character (e.g. "n-", "f-"), \b won't
        # match after the hyphen since both the hyphen and following space are
        # non-word characters. Use a lookahead for whitespace/punctuation/EOL
        # instead in that case.
        escaped = re.escape(form_lower)
        last_char = form_lower[-1]
        if not last_char.isalnum() and last_char != "'":
            # Form ends in non-word, non-apostrophe char (e.g. hyphen censor "n-")
            pattern = re.compile(r'\b' + escaped + r'(?=\s|[,.!?;:"\']|$)', re.IGNORECASE)
        else:
            pattern = re.compile(r'\b' + escaped + r'\b', re.IGNORECASE)

        for m in pattern.finditer(text_lower):
            start, end = m.span()

            # Get surrounding context (50 chars each side)
            ctx_start = max(0, start - 50)
            ctx_end = min(len(text), end + 50)
            context = text[ctx_start:ctx_end]

            # Check skip patterns if moderation config exists
            if moderation and "skip_patterns" in moderation:
                skipped = False
                for skip_pattern in moderation["skip_patterns"]:
                    # Use finditer to check ALL skip pattern matches, not just first
                    for skip_m in re.finditer(skip_pattern, text_lower, re.IGNORECASE):
                        if skip_m.start() <= start < skip_m.end():
                            skipped = True
                            break
                    if skipped:
                        break
                if skipped:
                    continue

            matches.append((form, start, context.strip()))

    return matches


def compute_rating(lyrics, word_lists):
    """Compute content rating from lyrics text.

    Returns a dict with:
      - rating: computed rating (X, R, PG-13, PG-8, G, or MANUAL REVIEW)
      - matched_words: dict of rating → list of (form, position, context)
      - matched_terms: set of unique matched forms
    """
    if not lyrics or len(lyrics.strip()) < 10:
        return {
            "rating": "MANUAL REVIEW",
            "matched_words": {},
            "matched_terms": set(),
        }

    matched_by_rating = {}
    all_terms = set()

    for rating, forms, moderation in word_lists:
        matches = find_matches(lyrics, forms, moderation)
        if matches:
            if rating not in matched_by_rating:
                matched_by_rating[rating] = []
            matched_by_rating[rating].extend(matches)
            for form, _, _ in matches:
                all_terms.add(form)

    # Determine rating by priority
    for rating in ["X", "R", "PG-13", "PG-8"]:
        if rating in matched_by_rating and matched_by_rating[rating]:
            return {
                "rating": rating,
                "matched_words": matched_by_rating,
                "matched_terms": all_terms,
            }

    return {
        "rating": "G",
        "matched_words": {},
        "matched_terms": set(),
    }


def analyze_file(filepath, word_lists):
    """Analyze a single file: read embedded lyrics and compute rating.

    If the file's comment tag contains "Override Rating: X", that rating
    is used instead of the lyrics-computed one.

    Returns a dict with analysis results. Does NOT write any tags.
    """
    info = read_song_info(filepath)
    lyrics = info["lyrics"]

    result = compute_rating(lyrics, word_lists)
    computed_rating = result["rating"]

    # Check for manual override in comment tag
    override_rating = read_override_rating(filepath)
    if override_rating:
        final_rating = override_rating
        overridden = True
    else:
        final_rating = computed_rating
        overridden = False

    # Convert matched_terms set to sorted list for JSON serialization
    matched_words_serializable = {}
    for rating, matches in result["matched_words"].items():
        matched_words_serializable[rating] = [
            {"form": form, "context": ctx}
            for form, _, ctx in matches
        ]

    return {
        "path": filepath,
        "filename": info["filename"],
        "rating": final_rating,
        "computed_rating": computed_rating,
        "override_rating": override_rating,
        "overridden": overridden,
        "has_lyrics": info["has_lyrics"],
        "lyrics_length": info["lyrics_length"],
        "matched_words": matched_words_serializable,
        "matched_terms": sorted(result["matched_terms"]),
    }
