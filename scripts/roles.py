"""Run a fresh native role against the shared architecture workflow."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.codex_role import _main

if __name__ == "__main__":
    _main()
