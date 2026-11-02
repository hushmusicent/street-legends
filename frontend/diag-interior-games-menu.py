#!/usr/bin/env python3
"""Street Legends diagnostic (READ-ONLY, no writes): the interior
Games menu's actual rows (PLACED/BUY), and what list renders them.

Why: buying happens ON this menu (user correction 2026-11-02).
The menu shows owned items as PLACED and unowned items as BUY
$price rows. The games array (line ~1627) HAS Scrabble and the
Scrabble modals are wired, yet this menu shows only 4 rows, no
Scrabble BUY $20k row. So this menu's row list is a SEPARATE list
from the 1627 array (hardcoded cards, a different array, or a
FlatList/state list). The previous diagnostics did not capture
this menu's rows (they anchored on the sell handler / modals /
interior modal start). This one prints just the menu rows.

What this prints (no writes):
  1. The file (first file with PLACED + Pool Table).
  2. The tab bar (Games/Appliances/Utilities) with +/-10 context,
     to confirm this is the interior menu.
  3. Every "PLACED" occurrence with +/-25 context (the row JSX:
     image, name, PLACED/BUY button, and whether the rows are
     hardcoded cards vs a .map over an array vs a FlatList).
  4. Whether "Scrabble" appears in any PLACED row context.

Run from /app: python3 frontend/diag-interior-games-menu.py
Read-only. Prints DIAG_INTERIOR_GAMES_MENU_OK at the end.
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
        print("DIAG_INTERIOR_GAMES_MENU_OK")
        return 0
    path, src = hits[0]
    lines = src.split("\n")
    print("FILE: %s" % path)
    # Tab bar: a line with Games + Appliances, or Utilities nearby.
    tab_idx = None
    for i, ln in enumerate(lines):
        if "Games" in ln and "Appliances" in ln:
            tab_idx = i
            break
    if tab_idx is None:
        for i, ln in enumerate(lines):
            if "Appliances" in ln and "Utilities" in ln:
                tab_idx = i
                break
    if tab_idx is not None:
        start = max(0, tab_idx - 10)
        end = min(len(lines), tab_idx + 11)
        print("--- Tab bar around line %d (lines %d-%d) ---" % (tab_idx + 1, start + 1, end))
        for k in range(start, end):
            print("%d: %s" % (k + 1, lines[k]))
    else:
        print("TAB BAR: not found (no line with Games+Appliances or Appliances+Utilities)")
    placed = [i for i, ln in enumerate(lines) if "PLACED" in ln]
    print("PLACED OCCURRENCES: %d (lines %s)" % (len(placed), ", ".join(str(i + 1) for i in placed) if placed else "(none)"))
    scrabble_in_rows = False
    for idx in placed:
        start = max(0, idx - 25)
        end = min(len(lines), idx + 26)
        ctx = "\n".join(lines[start:end])
        if "Scrabble" in ctx or "scrabble" in ctx:
            scrabble_in_rows = True
        print("--- PLACED at line %d (context lines %d-%d) ---" % (idx + 1, start + 1, end))
        for k in range(start, end):
            print("%d: %s" % (k + 1, lines[k]))
    print("SCRABBLE IN ANY PLACED ROW CONTEXT: %s" % ("YES" if scrabble_in_rows else "NO"))
    print("DIAG_INTERIOR_GAMES_MENU_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
