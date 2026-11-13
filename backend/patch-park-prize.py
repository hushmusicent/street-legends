#!/usr/bin/env python3
"""Street Legends backend: park games cash prize ($500 per PvC win).

Registers the 6 park games in CENTER_PRIZE_GAMES so the existing
POST /api/center-prize/award endpoint accepts them. The existing
_center_prize_amount already pays $500 * 1.1^(level-1) for any won
non-pop_shot game, so with max_level 1 every park PvC win pays a
flat $500. PvP wins do NOT use this endpoint (PvP already has cash
bets); the frontend only posts park_prize_win from PvC mode.

Games: basketball, football, baseball, soccer, tennis, one_on_one.

Run from /app: python3 backend/patch-park-prize.py
Idempotent: a full re-run prints PARK_PRIZE_ALREADY_APPLIED.
"""
import re
import sys
import py_compile
from pathlib import Path

SRV = Path("backend/server.py")
MARKER = "PARK_PRIZE_OK"

PARK_GAMES = {
    "basketball": 1,
    "football": 1,
    "baseball": 1,
    "soccer": 1,
    "tennis": 1,
    "one_on_one": 1,
}

def main():
    if not SRV.exists():
        print("ERROR: backend/server.py not found (run from /app)")
        sys.exit(1)
    src = SRV.read_text()

    # Already applied? (check first — the anchor changes after insertion)
    if all(f'"{g}": {{"max_level": 1}}' in src for g in PARK_GAMES):
        print("PARK_PRIZE_ALREADY_APPLIED")
        return
    # Anchor on the CENTER_PRIZE_GAMES dict. Insert park games before
    # the closing brace, after pop_shot.
    anchor = '    "pop_shot": {"max_level": 5},\n}'
    if anchor not in src:
        print("ERROR: CENTER_PRIZE_GAMES anchor not found")
        sys.exit(1)
    lines = "".join(f'    "{g}": {{"max_level": 1}},\n' for g in PARK_GAMES)
    new_anchor = '    "pop_shot": {"max_level": 5},\n' + lines + "}"
    src = src.replace(anchor, new_anchor, 1)
    SRV.write_text(src)
    # Syntax check
    py_compile.compile(str(SRV), doraise=True)
    # Verify
    cur = SRV.read_text()
    missing = [g for g in PARK_GAMES if f'"{g}": {{"max_level": 1}}' not in cur]
    if missing:
        print("ERROR: not all park games registered:", missing)
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
