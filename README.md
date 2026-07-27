# vdj_content_moderation

Generates swear-word censor lists for VirtualDJ's lyrics censoring feature.

VirtualDJ supports **exact string matching only** — no regex or contextual
logic. This tool produces plain-text lists of explicit terms for import.

This repo only owns vocabulary/list generation. It does not fetch or rate
lyrics — that is handled by [ai-tools](../ai-tools), which reads
beets-embedded lyrics and classifies them against these same YAML word lists.

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

## Output Files

Generated cumulatively by severity:

| File | Contains |
|------|----------|
| `no-slurs-no-sex.txt` | Slurs + sexual content |
| `conventions.txt` | Above + severe swear words |
| `child-friendly.txt` | Above + other swear words |

## Usage

```bash
# Default: precision policy (omits ambiguous terms like "ho")
python main.py

# Include ambiguous terms (catches true uses, accepts false positives)
python main.py --ambiguous-policy recall

# Generate to a staging directory
python main.py --output-dir ./staging
```

## Ambiguous Terms

Some words have multiple meanings in lyrics. The primary example is **ho**:

- **Sexual slur**: "my main ho", "Mustard on the beat, ho"
- **Vocalization**: "ho-oh-oh", "hey ho", "whoa, ho"

VirtualDJ's exact matcher cannot distinguish these. The `--ambiguous-policy`
flag controls the tradeoff:

| Policy | Behavior | Tradeoff |
|--------|----------|----------|
| `precision` (default) | Omit `ho` from output | No false censorship of vocalizations; 2 true uses uncensored |
| `recall` | Include `ho` in output | True uses censored; vocalizations in ~12 songs falsely censored |

Context rules for the AI moderation system (in `ai-tools`) are stored in the
YAML under `moderation.skip_patterns` but are **not** used by this generator,
since VirtualDJ cannot enforce them.

## YAML Schema

```yaml
words:
  - term: fuck                    # canonical term (for reference)
    forms: [fuck, fucks, fucked,  # exact strings for VirtualDJ output
            fuckin, "fuckin'",
            fucking, fucker]      # quoted strings needed for apostrophes
    virtualdj:
      include: true               # default; omit to exclude from VirtualDJ

  - term: ho
    forms: [ho, hos, "ho's"]
    moderation:                   # used by ai-tools, NOT by main.py
      context: person_reference
      skip_patterns:
        - '\bho[- ]oh\b'
    virtualdj:
      ambiguous: true             # subject to --ambiguous-policy
```
