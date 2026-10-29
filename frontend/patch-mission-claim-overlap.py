"""Street Legends frontend: mission claim pill no longer overlaps rewards.
Run from repo root: python3 frontend/patch-mission-claim-overlap.py
Idempotent - safe to re-run.

BUG: on a completed mission card, the rewards row ($2600 + 975 XP +
7 REP) plus the TAP TO CLAIM pill plus CANCEL is wider than the card.
Nothing wraps or shrinks, so the claim pill lands on top of the REP
text ("7 REP TO CLAIM" jumbled together).

FIX: let the bottom row wrap cleanly instead of overlapping:
1. cardBottom gets flexWrap + gap, so the actions drop to their own
   line rather than overlapping when the row is too wide.
2. cardRewards gets flexShrink + flexWrap, so long reward lists wrap
   inside their own area.
3. cardActions gets flexShrink: 0, so the claim/cancel buttons are
   never compressed or overlapped.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

PATH = Path("frontend/app/(tabs)/missions.tsx")

REPLACEMENTS = [
    (
        "  cardBottom: {\n    flexDirection: 'row',\n    alignItems: 'center',\n    justifyContent: 'space-between',\n  },",
        "  cardBottom: {\n    flexDirection: 'row',\n    alignItems: 'center',\n    justifyContent: 'space-between',\n    flexWrap: 'wrap',\n    gap: 8,\n  },",
        "cardBottom wraps instead of overlapping",
    ),
    (
        "  cardRewards: {\n    flexDirection: 'row',\n    alignItems: 'center',\n    gap: 12,\n    flex: 1,\n  },",
        "  cardRewards: {\n    flexDirection: 'row',\n    alignItems: 'center',\n    gap: 12,\n    flex: 1,\n    flexShrink: 1,\n    flexWrap: 'wrap',\n  },",
        "cardRewards shrinks and wraps",
    ),
    (
        "  cardActions: {\n    flexDirection: 'row',\n    alignItems: 'center',\n    gap: 8,\n  },",
        "  cardActions: {\n    flexDirection: 'row',\n    alignItems: 'center',\n    gap: 8,\n    flexShrink: 0,\n  },",
        "cardActions never compresses or overlaps",
    ),
]


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from repo root.")
        sys.exit(1)
    src = PATH.read_text()
    for old, new, desc in REPLACEMENTS:
        if new in src:
            print(f"SKIP: {desc} (already applied)")
        elif src.count(old) == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {desc}")
        else:
            print(f"WARNING: anchor matched {src.count(old)}x — {desc}")
    PATH.write_text(src)
    print("MISSION_CLAIM_OVERLAP_OK")


if __name__ == "__main__":
    main()
