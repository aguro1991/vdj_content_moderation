# vdj_content_moderation

Curated word lists and tooling for music content moderation.

Two main capabilities:

1. **Content rating** — reads beets-embedded lyrics, checks them against
   curated word lists, and writes content ratings into music file metadata.
2. **VirtualDJ censor list generation** — produces plain-text swear-word
   lists for VirtualDJ's exact-match lyrics censoring feature.

## WARNING
The purpose of this repo is to do content moderation. Throughout the documentation
and codebase in this repo you will find uncensored swear words, including uncensored
racial slurs. This is necessary in order to serve the function of tagging songs with
these words and enabling VirtualDJ to censor them.

## Word Lists

Curated vocabulary lives in `lists/`:

| File | Category | Rating |
|------|----------|--------|
| `slurs.yaml` | Slurs | X |
| `sexual-content.yaml` | Sexual content | R |
| `severe-swear-words.yaml` | Severe swear words | PG-13 |
| `other-swear-words.yaml` | Other swear words | PG-8 |

Each word is defined with explicit, curated forms rather than blanket suffix
expansion. This avoids nonsense forms like `fuck'll` or `fages` while
ensuring real forms like `fucked` and `cumming` are included.

## Content Rating

Rates songs by reading lyrics embedded in file metadata by the beets lyrics
plugin, checking them against the curated word lists, and writing ratings
into audio file comment tags.

Beets-embedded lyrics are the sole source of truth. No web searching, no
confidence scoring, no comparison with prior ratings.

### Usage

```bash
# Install dependencies
pip install -r requirements.txt

# Ensure beets has embedded lyrics (©lyr / USLT tags)
# Then run the full workflow (rate + generate VirtualDJ lists):
python scripts/rate.py /path/to/your/music

# Dry run (analyze without writing tags, lists still generated):
python scripts/rate.py /path/to/your/music --dry-run --output report.json

# Skip VirtualDJ list generation:
python scripts/rate.py /path/to/your/music --skip-list-generation

# With override logging:
python scripts/rate.py /path/to/your/music --log-file run.log
```

### Rating system

| Rating | Meaning | Trigger |
|--------|---------|---------|
| X | Explicit (slurs) | Contains slurs |
| R | Restricted | Contains sexual content words |
| PG-13 | Parental guidance | Contains severe swear words (fuck, shit, etc.) |
| PG-8 | Mild guidance | Contains other swear words (ass, damn, etc.) |
| G | General | No flagged words found |
| MANUAL REVIEW | Needs human review | No embedded lyrics |

### Override ratings

If a song's comment tag contains `Override Rating: <rating>` (e.g.
`Override Rating: X`), that rating is used regardless of what the lyrics
analysis would produce.

## VirtualDJ Censor List Generation

VirtualDJ's lyrics censoring feature supports **exact string matching only** —
no regex or contextual logic. This tool produces plain-text lists of explicit
terms for import.

### Usage

```bash
# Default: precision policy (omits ambiguous terms like "ho")
python generate.py

# Include ambiguous terms (catches true uses, accepts false positives)
python generate.py --ambiguous-policy recall

# Generate to a staging directory
python generate.py --output-dir ./staging
```

### Output files

Generated cumulatively by severity:

| File | Contains |
|------|----------|
| `no-slurs-no-sex.txt` | Slurs + sexual content |
| `conventions.txt` | Above + severe swear words |
| `child-friendly.txt` | Above + other swear words |

### Ambiguous terms

Some words have multiple meanings in lyrics. The primary example is **ho**:

- **Sexual slur**: "my main ho", "Mustard on the beat, ho"
- **Vocalization**: "ho-oh-oh", "hey ho", "whoa, ho"

The `--ambiguous-policy` flag controls the tradeoff:

| Policy | Behavior | Tradeoff |
|--------|----------|----------|
| `precision` (default) | Omit `ho` from output | No false censorship; 2 true uses uncensored |
| `recall` | Include `ho` in output | True uses censored; vocalizations in ~12 songs falsely censored |

Context rules for the content rating system are stored in the YAML under
`moderation.skip_patterns` but are **not** used by the generator, since
VirtualDJ cannot enforce them.

## YAML schema

```yaml
words:
  - term: fuck                    # canonical term (for reference)
    forms: [fuck, fucks, fucked,  # exact strings for VirtualDJ output
            fuckin, "fuckin'",
            fucking, fucker]
    virtualdj:
      include: true               # default; set false to exclude from VDJ output

  - term: ho
    forms: [ho, hos, "ho's"]
    moderation:                   # used by content rating, NOT by generate.py
      context: person_reference
      skip_patterns:
        - '\bho[- ]oh\b'
    virtualdj:
      ambiguous: true             # subject to --ambiguous-policy

  - term: nigga (censored)
    forms: ["n-", "n*gga"]
    virtualdj:
      include: false              # affects rating but not VDJ censor lists
```
