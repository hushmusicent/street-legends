#!/usr/bin/env python3
"""Repair the Bonus tab shop.tsx syntax error (my bug).

The Bonus tab patch chained the ternary wrong:
  ) : {filter === 'house' ? (
That extra "{" after the ":" makes the parser read an object literal
("expected ','" at shop.tsx 409:18) and the build fails.

Fix: drop the "{" so the ternary chains cleanly:
  ) : filter === 'house' ? (

Run from /app: python3 frontend/patch-bonus-tab-repair.py
Idempotent: a full re-run prints BONUS_TAB_REPAIR_ALREADY_APPLIED.
"""
import sys
from pathlib import Path

SHOP = Path("frontend/app/(tabs)/shop.tsx")
MARKER = "BONUS_TAB_REPAIR_OK"
BROKEN = ") : {filter === 'house' ? ("
FIXED = ") : filter === 'house' ? ("

def main():
    if not SHOP.exists():
        print("ERROR: shop.tsx not found (run from /app)")
        sys.exit(1)
    src = SHOP.read_text()
    if BROKEN not in src:
        if FIXED in src and "BonusBundles" in src:
            print("BONUS_TAB_REPAIR_ALREADY_APPLIED")
            return
        print("ERROR: broken ternary not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src.replace(BROKEN, FIXED, 1)
    SHOP.write_text(src)
    cur = SHOP.read_text()
    if BROKEN in cur:
        print("ERROR: repair did not apply")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
