#!/usr/bin/env python3
"""Street Legends diagnostic (READ-ONLY, no writes): every place
"Pool Table" appears in the house interior file, plus the Scrabble
line context, so the actual Games menu JSX can be told apart from
the sell handler and other uses.

Why: the previous diagnostic anchored on the first "Pool Table"
(line 1475), which is the sellPoolTable Alert, not the Games menu.
The interior state (lines 1465-1534) shows items are dynamic from
interiorHouse.items, but the Games menu JSX (cards with images +
PLACED/BUY) is later in the file, in the return JSX. Guessing its
structure would miss like v1/v2. This prints every occurrence with
context so the menu block is visible directly.

What this prints (no writes):
  1. The file (first file with PLACED + Pool Table).
  2. Every line containing "Pool Table", with line numbers, and
     +/-12 lines of context for each, flagged with whether the
     context contains PLACED, BUY, or an image source (hints for
     which occurrence is the menu JSX).
  3. The Scrabble line(s) with +/-20 lines of context, so it is
     clear which block/array line 1627 belongs to.

Run from /app: python3 frontend/diag-games-menu-occurrences.py
Read-only. Prints DIAG_GAMES_MENU_OCCURRENCES_OK at the end.
"""
import glob
import sys


def main():
    hits = []
    for path in sorted(glob.glob("frontend/**/*.tsx", recursive=True) +
                       glob.glob("frontend/**/*.ts", recursive=True)):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except FileNotFoundError:
            continue
        if "PLACED" in src and "Pool Table" in src:
            hits.append((path, src))
    if not hits:
        print("WARNING: no frontend file contains both PLACED and Pool Table")
        print("DIAG_GAMES_MENU_OCCURRENCES_OK")
        return 0
    path, src = hits[0]
    lines = src.split("\n")
    print("FILE: %s" % path)
    pool_lines = [i for i, ln in enumerate(lines) if "Pool Table" in ln]
    print("POOL TABLE OCCURRENCES: %d (lines %s)" % (len(pool_lines), ", ".join(str(i + 1) for i in pool_lines)))
    for idx in pool_lines:
        start = max(0, idx - 12)
        end = min(len(lines), idx + 13)
        ctx = "\n".join(lines[start:end])
        flags = []
        if "PLACED" in ctx:
            flags.append("PLACED")
        if "BUY" in ctx.upper():
            flags.append("BUY")
        if "source=" in ctx or "require(" in ctx:
            flags.append("IMAGE")
        print("--- Pool Table at line %d (flags: %s) ---" % (idx + 1, ", ".join(flags) if flags else "none"))
        for k in range(start, end):
            print("%d: %s" % (k + 1, lines[k]))
    scrabble_lines = [i for i, ln in enumerate(lines)
                      if "Scrabble Table" in ln or "scrabble" in ln.lower()]
    print("SCRABBLE LINES: %s" % (", ".join(str(i + 1) for i in scrabble_lines) if scrabble_lines else "(none)"))
    for idx in scrabble_lines:
        start = max(0, idx - 20)
        end = min(len(lines), idx + 21)
        print("--- Scrabble at line %d (context lines %d-%d) ---" % (idx + 1, start + 1, end))
        for k in range(start, end):
            print("%d: %s" % (k + 1, lines[k]))
    print("DIAG_GAMES_MENU_OCCURRENCES_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
