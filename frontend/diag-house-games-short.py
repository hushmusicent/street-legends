#!/usr/bin/env python3
"""Street Legends READ-ONLY diagnostic (short output, fits on a phone
screenshot): which file renders the house interior Games list, and
is Scrabble in it?

Prints ONLY one line per file: the file path, the line numbers where
"scrabble" appears (or NONE), and the line number of the Dominoes
Table entry. No long context, so the whole output fits on screen.

Changes NOTHING. Run from repo root:
  python3 frontend/diag-house-games-short.py
Prints DIAG_HOUSE_GAMES_SHORT_OK at the end.
"""
import glob
import sys


def main():
    files = sorted(glob.glob("frontend/app/**/*.tsx", recursive=True) +
                   glob.glob("frontend/components/*.tsx"))
    found = False
    for path in files:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.read().split("\n")
        except FileNotFoundError:
            continue
        if "Dominoes Table" not in "\n".join(lines) and not (
            "dominoes" in "\n".join(lines).lower() and "PLACED" in "\n".join(lines)
        ):
            continue
        found = True
        scrabble = [i + 1 for i, ln in enumerate(lines) if "scrabble" in ln.lower()]
        dom = next((i + 1 for i, ln in enumerate(lines) if "Dominoes Table" in ln), None)
        print("FILE: %s | scrabble: %s | dominoes line: %s" % (
            path, scrabble if scrabble else "NONE", dom if dom else "?"))
    if not found:
        print("No Games-list file found.")
    print("DIAG_HOUSE_GAMES_SHORT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
