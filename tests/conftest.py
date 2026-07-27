"""Pytest configuration — make repo modules importable from tests."""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent

# Repo root: for importing generate.py
sys.path.insert(0, str(REPO_ROOT))

# Scripts directory: for importing read_lyrics, analyze_lyrics, write_tags, rate
sys.path.insert(0, str(REPO_ROOT / "scripts"))
