#!/usr/bin/env python3
"""Regenerate the amplification table in README.md from results/.

Run it and diff against the README. Every figure in that table must come out of
this script; a number in the README that this cannot reproduce is a bug, and one
such number was found and corrected this way.

    python scripts/amplification.py
"""

from __future__ import annotations

import json
import statistics as st
from pathlib import Path

RESULTS = Path(__file__).resolve().parent.parent / "results"

# (file, control arm, treatment arm, label)
CASES = [
    ("position-2026-08-28.json", "pos-none", "pos-ups", "injection position"),
    ("repomap-personalized-2026-08-28.json", "norepomap", "repomap", "RepoMap, personalised"),
    ("repomap-2026-08-27.json", "norepomap", "repomap", "RepoMap, alphabetical"),
    ("crosstool-2026-08-28.json", "off", "on", "session memory"),
]


def billed_delta(path: Path, control: str, treatment: str) -> tuple[float, int]:
    """Mean extra billed input-equivalent tokens, and the number of runs behind it."""
    rows = json.loads(path.read_text())
    c = [r["billed_input_equivalent"] for r in rows if r["arm"] == control]
    t = [r["billed_input_equivalent"] for r in rows if r["arm"] == treatment]
    if not c or not t:
        raise SystemExit(f"{path.name}: arms {control!r}/{treatment!r} not both present")
    return st.fmean(t) - st.fmean(c), len(c) + len(t)


def main() -> int:
    print(f"{'experiment':<24}{'extra billed':>14}{'runs':>7}  file")
    print("-" * 78)
    for name, control, treatment, label in CASES:
        delta, n = billed_delta(RESULTS / name, control, treatment)
        print(f"{label:<24}{delta:>+14,.0f}{n:>7}  {name}")
    print(
        "\nExtra billed input-equivalent tokens, treatment minus control, averaged\n"
        "over every run in the file. This is what the injection cost, not what it\n"
        "contained: a cache read bills at 0.1x and a 1-hour cache write at 2.0x, so\n"
        "injecting anything converts reads into writes for everything after it."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
