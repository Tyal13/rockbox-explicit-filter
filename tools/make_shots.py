#!/usr/bin/env python3
"""Render real explicit_tagger output to SVG for the README.

These are genuine program output captured from an actual run, not mockups, so
they cannot drift away from what the tool really prints.

Regenerate with:  python3 tools/make_shots.py <music_dir>

The directory should hold a handful of throwaway tracks. Never point this at a
library you care about without --dry-run: the tagger writes tags.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.text import Text

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "images"
TAGGER = ROOT / "scripts" / "explicit_tagger.py"
WIDTH = 96

# Only tokens the tagger genuinely emits are styled. Nothing is invented.
STYLES = {
    "EXPLICIT:": "bold red",
    "CLEAN:": "green",
    "RESULTS:": "bold",
    "(DRY RUN": "dim italic",
}


def styled(line: str) -> Text:
    text = Text(line)
    for token, style in STYLES.items():
        idx = line.find(token)
        if idx >= 0:
            text.stylize(style, idx, idx + len(token))
    if line.startswith("=" * 10):
        text.stylize("dim")
    return text


def shot(name: str, lines: list[str], title: str) -> Path:
    console = Console(record=True, width=WIDTH, force_terminal=True)
    for line in lines:
        console.print(styled(line))
    path = OUT / f"{name}.svg"
    OUT.mkdir(parents=True, exist_ok=True)
    console.save_svg(str(path), title=title)
    return path


def run_tagger(music_dir: str, *flags: str) -> list[str]:
    proc = subprocess.run(
        [sys.executable, str(TAGGER), music_dir, *flags],
        capture_output=True, text=True,
    )
    out = (proc.stdout or "").splitlines()
    if not out:
        raise SystemExit(f"tagger produced no output:\n{proc.stderr}")
    # The report path is machine-specific; it would leak a local path into a
    # committed image and change on every run.
    return [ln for ln in out if not ln.startswith("Report saved:")]


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    music_dir = sys.argv[1]
    path = shot("tagger-run", run_tagger(music_dir, "--dry-run"),
                "explicit_tagger.py --dry-run")
    print(f"  wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
