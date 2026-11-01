#!/usr/bin/env python3
"""Street Legends READ-ONLY diagnostic: which file renders the house
interior Games list, and is Scrabble in it?

The Scrabble frontend patch printed "Scrabble Table added to Games
list (after Dominoes Table)" but the interior Games list still shows
only Pool / Dartboard / Card / Dominoes. This finds the file(s) that
actually render that list (by searching for the Dominoes Table entry)
and reports whether "scrabble" appears in each, plus the Dominoes
entry context so the real entry format is visible.

Changes NOTHING. Run from repo root:
  python3 frontend/diag-house-games.py
Prints DIAG_HOUSE_GAMES_OK at the end.
"""
import glob
import re
import sys


def main():
    files = sorted(glob.glob("frontend/app/**/*.tsx", recursive=True) +
                   glob.glob("frontend/components/*.tsx"))
    hits = []
    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except FileNotFoundError:
            continue
        if "Dominoes Table" in src or ("dominoes" in src.lower() and "PLACED" in src):
            lines = src.split("\n")
            scrabble_lines = [i + 1 for i, ln in enumerate(lines) if "scrabble" in ln.lower()]
            hits.append((path, scrabble_lines, lines))
    if not hits:
        print("No file containing a Dominoes Table / PLACED games entry was found.")
        print("DIAG_HOUSE_GAMES_OK")
        return 0
    for path, scrabble_lines, lines in hits:
        print("=" * 70)
        print("FILE: %s" % path)
        print("scrabble lines: %s" % (scrabble_lines if scrabble_lines else "NONE"))
        # Print the Dominoes Table entry context (first occurrence).
        idx = None
        for i, ln in enumerate(lines):
            if "Dominoes Table" in ln:
                idx = i
                break
        if idx is None:
            for i, ln in enumerate(lines):
                if "dominoes" in ln.lower():
                    idx = i
                    break
        if idx is not None:
            print("--- Dominoes entry context (lines %d-%d) ---" % (max(1, idx - 5), min(len(lines), idx + 25)))
            for j in range(max(0, idx - 5), min(len(lines), idx + 25)):
                print("%5d: %s" % (j + 1, lines[j]))
    print("DIAG_HOUSE_GAMES_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
