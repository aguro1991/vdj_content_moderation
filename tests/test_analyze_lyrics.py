"""Tests for context-aware lyrics analysis.

Covers:
- ho vocalization skip patterns
- ho as person-reference detected
- confirmed explicit terms detected
- no tag writes during analysis (dry-run by design)
- beets-embedded lyrics are authoritative (no version detection)
"""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import analyze_lyrics
from analyze_lyrics import (
    compute_rating,
    find_matches,
    load_word_lists,
)

import read_lyrics

LISTS_DIR = str(Path(__file__).parent.parent / "lists")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def word_lists():
    """Load the real curated word lists."""
    return load_word_lists(LISTS_DIR)


# ---------------------------------------------------------------------------
# ho context-aware matching
# ---------------------------------------------------------------------------

def test_ho_vocalization_ho_oh_skipped(word_lists):
    """'ho-oh-oh' vocalization should NOT trigger a ho match."""
    lyrics = "Oh, ho-oh-oh, ho-oh-oh, got that real big energy"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in vocalization: {result['matched_terms']}"


def test_ho_vocalization_hey_ho_skipped(word_lists):
    """'Hey ho' (RHCP Snow) should NOT trigger a ho match."""
    lyrics = "Hey, oh, I hear the wind call your name\nHey, ho, let's go"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'hey ho': {result['matched_terms']}"


def test_ho_vocalization_whoa_ho_skipped(word_lists):
    """'Whoa, ho' exclamation should NOT trigger a ho match."""
    lyrics = "Whoa, ho, hold back the river"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'whoa, ho': {result['matched_terms']}"


def test_ho_vocalization_ho_ee_skipped(word_lists):
    """'ho-ee-oh-ee-ome' (Sam Smith Unholy) should NOT trigger a ho match."""
    lyrics = "Ho-ee-oh-ee-ome, ho-ee-oh-ee-ome"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'ho-ee': {result['matched_terms']}"


def test_ho_vocalization_oh_comma_ho_skipped(word_lists):
    """'Oh, ho' exclamation should NOT trigger a ho match."""
    lyrics = "Oh, ho, let me tell you about it"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'Oh, ho': {result['matched_terms']}"


def test_ho_standalone_exclamation_skipped(word_lists):
    """Standalone 'Ho!' on its own line (RHCP Snow) should NOT trigger a ho match."""
    lyrics = "And there's nowhere to go\n\nHo!\n\nWent to descend"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in standalone 'Ho!': {result['matched_terms']}"


def test_ho_oh_ho_vocalization_skipped(word_lists):
    """'oh-ho' reversed vocalization (James Bay) should NOT trigger a ho match."""
    lyrics = "Oh, oh-ho, oh-oh, oh-oh\nOh-oh, ho-oh, oh-whoa-ho"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'oh-ho/whoa-ho': {result['matched_terms']}"


def test_ho_ooh_ho_skipped(word_lists):
    """'ooh ho' (James Gillespie) should NOT trigger a ho match."""
    lyrics = "ooh ooh ooh ho ooh ho"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'ooh ho': {result['matched_terms']}"


def test_ho_yo_ho_skipped(word_lists):
    """'yo-ho' (Rick James) should NOT trigger a ho match."""
    lyrics = "(yo-ho, ow!)"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'yo-ho': {result['matched_terms']}"


def test_ho_comma_ho_skipped(word_lists):
    """'ho, ho' (Jack Jones) should NOT trigger a ho match."""
    lyrics = "Jenny Diver, ho, ho, yeah"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in 'ho, ho': {result['matched_terms']}"


def test_ho_hindi_na_ho_skipped(word_lists):
    """Hindi 'na ho' (Dorwin John) should NOT trigger a ho match."""
    lyrics = "na ho parinaam"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in Hindi 'na ho': {result['matched_terms']}"


def test_ho_hindi_ho_raha_skipped(word_lists):
    """Hindi 'ho raha' (Dorwin John) should NOT trigger a ho match."""
    lyrics = "ye ho raha"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in Hindi 'ho raha': {result['matched_terms']}"


def test_ho_hindi_ho_gaya_skipped(word_lists):
    """Hindi 'ho gaya' (Dorwin John) should NOT trigger a ho match."""
    lyrics = "pyaar ho gaya"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in Hindi 'ho gaya': {result['matched_terms']}"


def test_ho_person_reference_still_detected(word_lists):
    """Direct person-reference 'ho' not covered by skip rules SHOULD match.

    'my main ho' is the canonical sexual-slur usage and must still be detected
    after all skip patterns are applied.
    """
    lyrics = "She's my main ho, yeah that's my ho"
    result = compute_rating(lyrics, word_lists)
    assert "ho" in result["matched_terms"], \
        f"'ho' should match person reference but didn't: {result['matched_terms']}"
    assert result["rating"] == "R", \
        f"Person-reference 'ho' should give R rating, got {result['rating']}"


def test_ho_catchy_ho_detected(word_lists):
    """'that's my ho' in a non-vocalization context SHOULD trigger a ho match."""
    lyrics = "I got my money and that's my ho right there"
    result = compute_rating(lyrics, word_lists)
    assert "ho" in result["matched_terms"], \
        f"'ho' should match person reference 'that's my ho': {result['matched_terms']}"


def test_ho_mustard_on_beat_skipped(word_lists):
    """'Mustard on the beat, ho' (Ella Mai) should NOT trigger a ho match.

    This is a DJ Mustard producer tag, not a sexual-content usage of 'ho'.
    Identified as a false positive in Bug 4 analysis.
    """
    lyrics = "Mustard on the beat, ho"
    result = compute_rating(lyrics, word_lists)
    assert "ho" not in result["matched_terms"], \
        f"'ho' falsely matched in producer tag: {result['matched_terms']}"


# ---------------------------------------------------------------------------
# Confirmed explicit terms detected
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("term,expected_rating", [
    ("fuck", "PG-13"),
    ("shit", "PG-13"),
    ("bitch", "R"),
    ("nigga", "X"),
    ("nigger", "X"),
    ("ass", "PG-8"),
    ("fucked", "PG-13"),
    ("fucking", "PG-13"),
    ("fuckin", "PG-13"),
    ("cumming", "R"),
    ("asshole", "R"),
    ("pissed", "PG-13"),
    ("whoring", "R"),
])
def test_explicit_terms_detected(word_lists, term, expected_rating):
    """Each flagged term in lyrics should produce the correct rating."""
    lyrics = f"This song contains the word {term} in it"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == expected_rating, \
        f"'{term}' should give {expected_rating}, got {result['rating']}"


def test_clean_lyrics_give_g(word_lists):
    """Lyrics with no flagged words should give G rating."""
    lyrics = "Just a nice clean song about love and happiness"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "G"
    assert len(result["matched_terms"]) == 0


def test_no_lyrics_give_manual_review(word_lists):
    """No lyrics should give MANUAL REVIEW."""
    result = compute_rating(None, word_lists)
    assert result["rating"] == "MANUAL REVIEW"

    result = compute_rating("", word_lists)
    assert result["rating"] == "MANUAL REVIEW"


def test_empty_whitespace_lyrics_give_manual_review(word_lists):
    """Effectively empty lyrics (e.g. MP3 USLT with just newline) → MANUAL REVIEW.

    Bug 2a: Some MP3 files have empty USLT frames containing only whitespace
    characters like a single newline. These should be treated as no lyrics.
    """
    result = compute_rating("\n", word_lists)
    assert result["rating"] == "MANUAL REVIEW"


def test_short_lyrics_give_manual_review(word_lists):
    """Lyrics under 10 stripped characters → MANUAL REVIEW (Bug 2a)."""
    result = compute_rating("short", word_lists)
    assert result["rating"] == "MANUAL REVIEW"

    result = compute_rating("   \n\t  \n  ", word_lists)
    assert result["rating"] == "MANUAL REVIEW"


def test_slur_overrides_sexual(word_lists):
    """Slurs should override sexual content (X > R)."""
    lyrics = "bitch and nigger in the same song"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "X"


# ---------------------------------------------------------------------------
# Censored forms in word lists (hyphen and asterisk markers)
# ---------------------------------------------------------------------------

def test_hyphen_censor_n_treated_as_slur(word_lists):
    """'n-' in lyrics should match the censored form → X rating."""
    lyrics = "How n-? My last album was The Chronic, so make sure to listen"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "X"
    assert "n-" in result["matched_terms"]


def test_hyphen_censor_f_treated_as_severe_swear(word_lists):
    """'f-' in lyrics should match the censored form → PG-13 rating."""
    lyrics = "Still f- with the beats, yeah that's what I'm saying to you"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "PG-13"
    assert "f-" in result["matched_terms"]


def test_hyphen_censor_b_treated_as_sexual_content(word_lists):
    """'b-' in lyrics should match the censored form → R rating."""
    lyrics = "Whether you're coolin' on a corner with your fly b- right now"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "R"
    assert "b-" in result["matched_terms"]


def test_hyphen_censor_s_treated_as_severe_swear(word_lists):
    """'s-' in lyrics should match the censored form → PG-13 rating."""
    lyrics = "I don't give a s- about what you think of me anymore today"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "PG-13"
    assert "s-" in result["matched_terms"]


def test_hyphen_censor_capital_f_treated_as_swear(word_lists):
    """'F-' (capital) in lyrics should match the censored form → PG-13."""
    lyrics = "F- naw, I'm not going to let you down today my friend"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "PG-13"
    assert "F-" in result["matched_terms"]


def test_hyphen_censor_multiple_in_lyrics(word_lists):
    """Multiple censored markers in one song should all be detected."""
    lyrics = "y'all n- know me to fail? F- naw, my b- is right here"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "X"  # n- (slur) is highest severity
    assert "n-" in result["matched_terms"]
    assert "F-" in result["matched_terms"]
    assert "b-" in result["matched_terms"]


def test_hyphen_censor_at_end_of_line(word_lists):
    """'n-' at end of line should match the censored form."""
    lyrics = "All my n-\nLocked down in the house, controllin' the sound"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "X"
    assert "n-" in result["matched_terms"]


def test_hyphen_censor_not_triggered_by_compound_words(word_lists):
    """'b-side' should NOT be treated as a censored 'bitch' — it's a compound word."""
    lyrics = "Check out the b-side of this record, it's a great track today"
    result = compute_rating(lyrics, word_lists)
    assert "b-" not in result["matched_terms"]
    assert result["rating"] == "G"


def test_asterisk_censor_fck_treated_as_swear(word_lists):
    """'f*ck' in lyrics should match the censored form → PG-13."""
    lyrics = "I don't give a f*ck about what you think of me anymore"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "PG-13"
    assert "f*ck" in result["matched_terms"]


def test_asterisk_censor_ngga_treated_as_slur(word_lists):
    """'n*gga' in lyrics should match the censored form → X."""
    lyrics = "My n*gga, we been through a lot together over the years"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "X"
    assert "n*gga" in result["matched_terms"]


def test_asterisk_censor_btch_treated_as_sexual(word_lists):
    """'b*tch' in lyrics should match the censored form → R."""
    lyrics = "You acting like a b*tch right now, settle down and listen"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "R"
    assert "b*tch" in result["matched_terms"]


def test_asterisk_censor_sit_treated_as_swear(word_lists):
    """'s*it' in lyrics should match the censored form → PG-13."""
    lyrics = "I don't give a s*it about what you think of me anymore"
    result = compute_rating(lyrics, word_lists)
    assert result["rating"] == "PG-13"
    assert "s*it" in result["matched_terms"]


# ---------------------------------------------------------------------------
# No tag writes (dry-run by design)
# ---------------------------------------------------------------------------

def test_analyze_file_does_not_write(tmp_path, word_lists):
    """analyze_file must not modify the input file in any way."""
    # Create a minimal fake M4A file — we'll mock read_lyrics
    fake_path = str(tmp_path / "test.m4a")
    Path(fake_path).write_bytes(b"\x00" * 100)

    # Mock the lyrics reading to avoid needing a real audio file
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value=None):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "test.m4a",
            "lyrics": "This is a clean song",
            "lyrics_length": 21,
            "has_lyrics": True,
        }
        original_mtime = os.path.getmtime(fake_path)
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    # Verify file was not modified
    assert os.path.getmtime(fake_path) == original_mtime
    assert result["rating"] == "G"
    assert result["matched_terms"] == []
    assert "existing_rating" not in result
    assert "version" not in result
    assert "final_rating" not in result


# ---------------------------------------------------------------------------
# find_matches with context
# ---------------------------------------------------------------------------

def test_find_matches_basic(word_lists):
    """find_matches locates terms in lyrics text."""
    # Get the sexual-content forms for 'ho'
    ho_entry = None
    for rating, forms, mod in word_lists:
        if "ho" in forms and mod:
            ho_entry = (rating, forms, mod)
            break

    assert ho_entry is not None, "ho entry with moderation not found"
    rating, forms, mod = ho_entry

    # Person reference should match
    matches = find_matches("my main ho", forms, mod)
    ho_matches = [m for m in matches if m[0] == "ho"]
    assert len(ho_matches) > 0, "Person-reference 'ho' should match"

    # Vocalization should not match
    matches = find_matches("ho-oh-oh everywhere", forms, mod)
    ho_matches = [m for m in matches if m[0] == "ho"]
    assert len(ho_matches) == 0, "Vocalization 'ho-oh' should not match"


# ---------------------------------------------------------------------------
# Word list loading
# ---------------------------------------------------------------------------

def test_load_word_lists_structure():
    """load_word_lists returns properly structured data."""
    word_lists = load_word_lists(LISTS_DIR)
    assert len(word_lists) > 0
    for rating, forms, mod in word_lists:
        assert rating in ["X", "R", "PG-13", "PG-8"]
        assert isinstance(forms, list)
        assert len(forms) > 0


def test_load_word_lists_has_ho_with_moderation():
    """The ho entry should have moderation config with skip_patterns."""
    word_lists = load_word_lists(LISTS_DIR)
    ho_entries = [(r, f, m) for r, f, m in word_lists if "ho" in f and m]
    assert len(ho_entries) > 0, "ho entry with moderation not found"
    _, _, mod = ho_entries[0]
    assert "skip_patterns" in mod
    assert len(mod["skip_patterns"]) > 0


# ---------------------------------------------------------------------------
# Integration: analyze_file with mocked lyrics
# ---------------------------------------------------------------------------

def test_analyze_file_clean_song(word_lists, tmp_path):
    """analyze_file returns G for clean lyrics."""
    fake_path = str(tmp_path / "clean.m4a")
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value=None):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "clean.m4a",
            "lyrics": "La la la, just a happy song",
            "lyrics_length": 26,
            "has_lyrics": True,
        }
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    assert result["rating"] == "G"
    assert result["matched_terms"] == []
    assert "existing_rating" not in result


def test_analyze_file_explicit_song(word_lists, tmp_path):
    """analyze_file returns PG-13 for lyrics containing 'shit'."""
    fake_path = str(tmp_path / "explicit.m4a")
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value=None):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "explicit.m4a",
            "lyrics": "I don't give a shit about it",
            "lyrics_length": 28,
            "has_lyrics": True,
        }
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    assert result["rating"] == "PG-13"
    assert "shit" in result["matched_terms"]


def test_analyze_file_no_lyrics(word_lists, tmp_path):
    """analyze_file returns MANUAL REVIEW for files without lyrics."""
    fake_path = str(tmp_path / "nolyrics.m4a")
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value=None):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "nolyrics.m4a",
            "lyrics": None,
            "lyrics_length": 0,
            "has_lyrics": False,
        }
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    assert result["rating"] == "MANUAL REVIEW"
    assert result["has_lyrics"] is False


# ---------------------------------------------------------------------------
# Override rating system
# ---------------------------------------------------------------------------

def test_override_applied(word_lists, tmp_path):
    """Override rating takes precedence over computed rating."""
    fake_path = str(tmp_path / "song.m4a")
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value="X"):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "song.m4a",
            "lyrics": "La la la, just a happy song",
            "lyrics_length": 26,
            "has_lyrics": True,
        }
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    assert result["rating"] == "X"
    assert result["computed_rating"] == "G"
    assert result["override_rating"] == "X"
    assert result["overridden"] is True


def test_no_override(word_lists, tmp_path):
    """Without an override, computed rating is used."""
    fake_path = str(tmp_path / "song.m4a")
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value=None):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "song.m4a",
            "lyrics": "I don't give a shit about it",
            "lyrics_length": 28,
            "has_lyrics": True,
        }
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    assert result["rating"] == "PG-13"
    assert result["computed_rating"] == "PG-13"
    assert result["override_rating"] is None
    assert result["overridden"] is False


def test_override_overrides_manual_review(word_lists, tmp_path):
    """Override applies even when lyrics are missing (MANUAL REVIEW)."""
    fake_path = str(tmp_path / "song.m4a")
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value="G"):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "song.m4a",
            "lyrics": None,
            "lyrics_length": 0,
            "has_lyrics": False,
        }
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    assert result["rating"] == "G"
    assert result["computed_rating"] == "MANUAL REVIEW"
    assert result["override_rating"] == "G"
    assert result["overridden"] is True


def test_override_lower_rating(word_lists, tmp_path):
    """Override can lower the rating (e.g. computed X, override G)."""
    fake_path = str(tmp_path / "song.m4a")
    with patch("analyze_lyrics.read_song_info") as mock_read, \
         patch("analyze_lyrics.read_override_rating", return_value="G"):
        mock_read.return_value = {
            "path": fake_path,
            "filename": "song.m4a",
            "lyrics": "bitch and nigger in the same song",
            "lyrics_length": 33,
            "has_lyrics": True,
        }
        result = analyze_lyrics.analyze_file(fake_path, word_lists)

    assert result["rating"] == "G"
    assert result["computed_rating"] == "X"
    assert result["override_rating"] == "G"
    assert result["overridden"] is True


# ---------------------------------------------------------------------------
# Integration: analyze_file against actual music library files
# ---------------------------------------------------------------------------

_MUSIC_DIR = os.environ.get("MUSIC_DIR", "/path/to/your/music")
LATTO_FILE = os.path.join(_MUSIC_DIR,
    "Latto - Big Energy (Big Energy - Single).m4a")


@pytest.mark.skipif(not os.path.exists(LATTO_FILE),
                    reason="Latto - Big Energy not found in music library")
def test_integration_latto_big_energy(word_lists):
    """Integration: Latto - Big Energy embedded lyrics are trusted as authoritative.

    The embedded lyrics are a clean transcription (censored markers like 'b-'),
    but under the new policy beets-embedded lyrics are the sole source of truth.
    The rating is computed directly from the embedded lyrics without version
    detection or comparison with prior ratings.
    """
    result = analyze_lyrics.analyze_file(LATTO_FILE, word_lists)

    # The embedded lyrics contain "foreplay" (sexual-content) and "hell"
    # (other-swear-words). Under the new policy, beets-embedded lyrics are
    # trusted as authoritative, so the rating is computed directly from them.
    assert result["rating"] == "R"
    assert "foreplay" in result["matched_terms"]
    assert result["has_lyrics"] is True
    assert "existing_rating" not in result
    assert "version" not in result
    assert "final_rating" not in result
