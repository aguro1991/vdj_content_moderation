#!/usr/bin/env python3
"""Generate VirtualDJ swear-word censor lists from curated YAML vocabulary.

VirtualDJ's lyrics censoring feature supports only exact string matching —
no regex, no contextual logic. This generator produces plain-text lists of
exact terms for import into VirtualDJ.

Output files (cumulative severity):
  no-slurs-no-sex.txt  — slurs + sexual content
  conventions.txt      — above + severe swear words
  child-friendly.txt   — above + other swear words

Ambiguous terms (e.g. "ho" which can be a vocalization or a sexual slur)
are controlled by --ambiguous-policy:
  precision  — omit ambiguous tokens (avoids false censorship)
  recall     — include them (catches true uses, accepts false positives)
"""

import argparse
import sys
from pathlib import Path

import yaml

LISTS_DIR = Path(__file__).parent / "lists"

# (output filename, [yaml files to include cumulatively])
OUTPUTS = [
    ("no-slurs-no-sex.txt", ["slurs.yaml", "sexual-content.yaml"]),
    ("conventions.txt", ["slurs.yaml", "sexual-content.yaml",
                         "severe-swear-words.yaml"]),
    ("child-friendly.txt", ["slurs.yaml", "sexual-content.yaml",
                            "severe-swear-words.yaml", "other-swear-words.yaml",
                            "drug-references.yaml"]),
]


def load_terms(yaml_path, ambiguous_policy):
    """Load curated forms from a structured YAML file.

    Returns (terms, omitted) where omitted is a list of
    (term, reason) tuples for terms skipped by the policy.
    """
    data = yaml.safe_load(yaml_path.read_text())
    terms = []
    omitted = []

    for entry in data["words"]:
        vj = entry.get("virtualdj", {})

        if not vj.get("include", True):
            # Explicitly excluded from VirtualDJ output (e.g. censored forms
            # like "n-", "f*" that are useful for moderation but not for
            # VirtualDJ's exact-match censoring)
            continue

        if vj.get("ambiguous"):
            if ambiguous_policy == "precision":
                omitted.append((entry["term"], "ambiguous (precision policy)"))
                continue
            # recall: include it

        terms.extend(entry["forms"])

    return terms, omitted


def generate(ambiguous_policy, output_dir):
    """Generate all three output files."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    all_omitted = []

    for filename, yaml_files in OUTPUTS:
        terms = []
        for yf in yaml_files:
            t, omitted = load_terms(LISTS_DIR / yf, ambiguous_policy)
            terms.extend(t)
            all_omitted.extend([(yf, term, reason) for term, reason in omitted])

        # Deduplicate and sort for deterministic output
        unique = sorted(set(terms))

        out_path = output_dir / filename
        # Space-separated to match existing VirtualDJ import format.
        # NOTE: If VirtualDJ supports newline-separated, switch to
        # "\n".join(unique) + "\n" for cleaner diffs and easier review.
        out_path.write_text(" ".join(unique))
        print(f"{filename}: {len(unique)} terms", file=sys.stderr)

    if all_omitted:
        # Deduplicate — a term appears once per cumulative file that includes it
        seen = set()
        unique_omitted = []
        for yf, term, reason in all_omitted:
            key = (yf, term)
            if key not in seen:
                seen.add(key)
                unique_omitted.append((yf, term, reason))

        print(f"\nOmitted ambiguous terms ({ambiguous_policy} policy):",
              file=sys.stderr)
        for yf, term, reason in unique_omitted:
            print(f"  [{yf}] {term} — {reason}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--ambiguous-policy", choices=["precision", "recall"],
                        default="precision",
                        help="How to handle ambiguous exact-match tokens like 'ho'. "
                             "precision: omit (avoid false censorship). "
                             "recall: include (catch true uses, accept false positives). "
                             "Default: precision")
    parser.add_argument("--output-dir", type=Path,
                        default=Path(__file__).parent,
                        help="Directory for generated .txt files. "
                             "Default: same directory as this script")
    args = parser.parse_args()
    generate(args.ambiguous_policy, args.output_dir)


if __name__ == "__main__":
    main()
