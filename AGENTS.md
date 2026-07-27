# vdj_content_moderation

Curated word lists and tooling for music content moderation. Two main
capabilities live in this repo:

1. **Content rating** — reads beets-embedded lyrics, checks them against
   curated word lists, and writes content ratings into music file metadata.
2. **VirtualDJ censor list generation** — produces plain-text swear-word
   lists for VirtualDJ's exact-match lyrics censoring feature.

Beets-embedded lyrics are the sole source of truth. No web searching, no
confidence scoring, no comparison with prior ratings.

## Quick start

```bash
pip install -r requirements.txt
```

### Rate songs (assumes beets has already embedded lyrics)

```bash
# Full workflow: analyze + write tags + generate VirtualDJ lists
python scripts/rate.py /path/to/your/music

# Dry run: analyze only, no tag writes (lists still generated)
python scripts/rate.py /path/to/your/music --dry-run --output report.json

# Skip VirtualDJ list generation
python scripts/rate.py /path/to/your/music --skip-list-generation

# With override logging
python scripts/rate.py /path/to/your/music --log-file run.log
```

The log file is created fresh (truncated) on each run and is general-purpose —
future event types may also be written there.

### Generate VirtualDJ censor lists

```bash
# Default: precision policy (omits ambiguous terms like "ho")
python generate.py

# Include ambiguous terms
python generate.py --ambiguous-policy recall

# Generate to a staging directory
python generate.py --output-dir ./staging
```

## Override ratings

If a song's comment tag contains `Override Rating: <rating>` (e.g.
`Override Rating: X`), that rating is used regardless of what the lyrics
analysis would produce. Supported override values: `G`, `PG-8`, `PG-13`,
`R`, `X`, `MANUAL REVIEW`. The match is case-sensitive (uppercase only).

When an override is applied, the analysis report includes:
- `rating` — the final rating (the override value)
- `computed_rating` — what the lyrics analysis would have produced
- `override_rating` — the override value from the comment
- `overridden` — `true` when an override was applied

`write_tags.py` preserves `Override Rating:` text when updating
`Content Rating:` in the comment tag.

## Scripts

- `scripts/rate.py` — CLI entry point for the content rating workflow:
  finds music files, analyzes each against word lists, writes ratings to
  file tags, then generates VirtualDJ censor lists. Supports `--dry-run`,
  `--output` (JSON report), `--log-file`, and `--skip-list-generation`.
- `scripts/read_lyrics.py` — library: reads embedded lyrics (M4A ©lyr, MP3/AIFF
  USLT) and comment tags. Lyrics with fewer than 10 stripped characters are
  treated as absent.
- `scripts/analyze_lyrics.py` — library: applies curated word lists to
  embedded lyrics, with context-aware matching that skips vocalization false
  positives (e.g. "ho" in "ho-oh-oh", "hey ho").
- `scripts/write_tags.py` — library: writes Content Rating to file comment
  tags. Each run replaces the existing rating. MANUAL REVIEW is written for
  files with no embedded lyrics. `write_rating()` dispatches by file extension.
- `generate.py` — CLI: generates VirtualDJ censor lists from the YAML word
  lists. VirtualDJ supports exact string matching only.

## Word Lists

Curated vocabulary lives in `lists/`:

| File | Category | Rating |
|------|----------|--------|
| `slurs.yaml` | Slurs | X |
| `sexual-content.yaml` | Sexual content | R |
| `severe-swear-words.yaml` | Severe swear words | PG-13 |
| `other-swear-words.yaml` | Other swear words | PG-8 |

Each word is defined with explicit, curated forms rather than blanket suffix
expansion. Censored forms (e.g. `n-`, `f*ck`) are marked `virtualdj.include: false`
so they affect content rating but not VirtualDJ output.

## Rating system

Ratings are assigned in priority order (highest severity wins):

| Rating | Trigger | Word list |
|--------|---------|-----------|
| X | Slurs | `slurs.yaml` |
| R | Sexual content | `sexual-content.yaml` |
| PG-13 | Severe swear words | `severe-swear-words.yaml` |
| PG-8 | Other swear words | `other-swear-words.yaml` |
| G | Default (clean) | — |
| MANUAL REVIEW | No embedded lyrics | — |

## VirtualDJ output files

Generated cumulatively by severity:

| File | Contains |
|------|----------|
| `no-slurs-no-sex.txt` | Slurs + sexual content |
| `conventions.txt` | Above + severe swear words |
| `child-friendly.txt` | Above + other swear words |

## Key rules

- Check for slurs FIRST — they result in an X rating
- Rate based on embedded lyrics text only
- Trust beets-embedded lyrics as authoritative — no version detection
- Every run is a fresh iteration — no reading or preserving prior results
- VirtualDJ can only do exact string matching — no regex or context logic
- Ambiguous terms (e.g. "ho") are controlled by `--ambiguous-policy`

Process all songs in a single thread. Do not break out new threads.
