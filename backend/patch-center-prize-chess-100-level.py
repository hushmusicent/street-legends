#!/usr/bin/env python3
"""Street Legends backend: Chess & Checkers prize is $100 per level.

The user corrected the payout: Chess & Checkers is supposed to pay
$100 a level ($100 x level: Level 1 = $100, Level 5 = $500, Level 10 =
$1000). The current formula pays $500 x 1.1^(level-1) for every table
game, so a Level 1 chess win paid $500 (the banner showed +$500 PRIZE!
for a Level 1 win, which is wrong per the rule).

This patch changes _center_prize_amount ONLY for game == "chess_checkers"
to return 100 * level. All other table games stay at the flat $500
(+10% compounding per level is gone for chess only), Pop Shot is
untouched ($10/make, $15 ON FIRE). It re-reads the live server.py and
only touches the chess branch; if the anchor is not found it changes
nothing and exits non-zero.

Run from /app: python3 backend/patch-center-prize-chess-100-level.py
Then Deploy (backend). No frontend change needed - the banner shows
whatever the server returns, so a Level 1 chess win will now show
+$100 PRIZE! and Level 5 will show +$500 PRIZE!
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "CENTER_PRIZE_CHESS_100_OK"

# Current chess branch (from patch-center-prize.py / v2):
#     mult = 1.1 ** (level - 1)
#     return int(500 * mult + 0.5)
# That return is shared by all non-pop-shot table games. We split it so
# chess_checkers gets its own branch.
OLD = """    mult = 1.1 ** (level - 1)
    return int(500 * mult + 0.5)"""

NEW = """    if game == "chess_checkers":
        return int(100 * level)
    mult = 1.1 ** (level - 1)
    return int(500 * mult + 0.5)"""


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - NOT fixed")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    if 'if game == "chess_checkers":\n        return int(100 * level)' in src:
        print("CENTER_PRIZE_CHESS_100_ALREADY_APPLIED")
        print(MARKER)
        return 0
    if OLD not in src:
        print("CENTER_PRIZE_CHESS_100_ANCHOR_FAIL: _center_prize_amount return not found (nothing changed)")
        return 1
    src2 = src.replace(OLD, NEW, 1)
    if src2 == orig:
        print("CENTER_PRIZE_CHESS_100_NOOP (nothing changed)")
        return 1
    # Sanity: the function must still exist and the chess branch must be present.
    if "_center_prize_amount" not in src2 or 'return int(100 * level)' not in src2:
        print("CENTER_PRIZE_CHESS_100_VERIFY_FAIL (nothing written)")
        return 1
    SERVER.write_text(src2)
    print("OK: chess_checkers now pays $100 x level (L1=$100, L5=$500, L10=$1000); other table games still $500")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
