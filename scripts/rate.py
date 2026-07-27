#!/usr/bin/env python3
"""Content moderation workflow: read lyrics → analyze → write tags.

Assumes beets has already been run to embed lyrics in the music files.
This is the single entry point for the content moderation pipeline.

Usage:
  python scripts/rate.py /media/jbod/WCS
  python scripts/rate.py /media/jbod/WCS --dry-run --output report.json
  python scripts/rate.py /media/jbod/WCS --log-file run.log
"""
import argparse
import json
import os
import sys

from read_lyrics import find_music_files
from analyze_lyrics import load_word_lists, analyze_file, DEFAULT_LISTS_DIR
from write_tags import write_rating


def _write_log_line(log_file, analysis):
    """Write a log entry for an overridden rating."""
    log_file.write(
        f"OVERRIDE | {analysis['filename']} | "
        f"computed: {analysis['computed_rating']} | "
        f"override: {analysis['override_rating']}\n"
    )


def _print_summary(results, log_path=None, dry_run=False, write_success=0, write_fail=0):
    """Print rating distribution and workflow stats to stderr."""
    rating_counts = {}
    override_count = 0
    for r in results:
        rating_counts[r["rating"]] = rating_counts.get(r["rating"], 0) + 1
        if r.get("overridden"):
            override_count += 1

    print(f"Total: {len(results)}", file=sys.stderr)
    for rating in ["X", "R", "PG-13", "PG-8", "G", "MANUAL REVIEW"]:
        count = rating_counts.get(rating, 0)
        if count:
            print(f"  {rating}: {count}", file=sys.stderr)
    if override_count:
        print(f"  Overrides applied: {override_count}", file=sys.stderr)
    if log_path:
        print(f"  Log file: {log_path}", file=sys.stderr)
    if dry_run:
        print("Dry run — no tags written", file=sys.stderr)
    else:
        print(f"Tags written: {write_success} succeeded, {write_fail} failed",
              file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Run content moderation workflow on a music directory. "
                    "Assumes beets has already embedded lyrics.")
    parser.add_argument("music_dir",
                        help="Directory containing music files with embedded lyrics")
    parser.add_argument("--lists-dir", default=DEFAULT_LISTS_DIR,
                        help="Directory containing word list YAML files")
    parser.add_argument("--output", "-o",
                        help="Write JSON report to this file")
    parser.add_argument("--log-file",
                        help="General-purpose log file for this run (truncated on open)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Analyze without writing tags to files")
    args = parser.parse_args()

    music_dir = os.path.expanduser(args.music_dir)
    word_lists = load_word_lists(args.lists_dir)
    files = find_music_files(music_dir)

    print(f"Found {len(files)} music files in {music_dir}", file=sys.stderr)

    log_file = open(args.log_file, "w") if args.log_file else None
    results = []
    write_success = 0
    write_fail = 0

    try:
        for i, filepath in enumerate(files):
            analysis = analyze_file(filepath, word_lists)
            results.append(analysis)

            if analysis.get("overridden") and log_file:
                _write_log_line(log_file, analysis)

            if not args.dry_run:
                try:
                    write_rating(filepath, analysis["rating"])
                    write_success += 1
                except Exception as e:
                    print(f"  FAIL (write): {analysis['filename']} -> {e}",
                          file=sys.stderr)
                    write_fail += 1

            if (i + 1) % 100 == 0:
                print(f"  Processed {i+1}/{len(files)}...", file=sys.stderr)

        _print_summary(results, args.log_file if log_file else None,
                       args.dry_run, write_success, write_fail)

        if args.output:
            with open(args.output, "w") as f:
                json.dump(results, f, indent=2)
            print(f"Report written to {args.output}", file=sys.stderr)

    finally:
        if log_file:
            log_file.close()


if __name__ == "__main__":
    main()
