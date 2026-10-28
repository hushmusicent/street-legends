"""Street Legends frontend: cash amounts never wrap mid-number.
Run from repo root: python3 frontend/patch-cash-format.py
Idempotent - safe to re-run.

BUG: cash is rendered as a raw number (e.g. $1029476) with no commas
and no wrap protection. Once the balance hits 7 digits, the profile
Resources card breaks it across two lines ("$10294" / "76"), which
looks tacky. The shop header and map header badges have the same risk.

FIX: format cash with thousand separators ($1,029,476) and force a
single line that shrinks to fit (numberOfLines + adjustsFontSizeToFit)
in the profile card, shop header badge, and map header badge, so a big
balance stays on one clean line instead of wrapping. Exact value is
kept (no compact $1.03M rounding) so buying decisions stay precise.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

EDITS = [
    (
        Path("frontend/app/(tabs)/character.tsx"),
        "<Text style={styles.resourceValue}>${player.cash}</Text>",
        "<Text style={styles.resourceValue} numberOfLines={1} adjustsFontSizeToFit>${(player.cash || 0).toLocaleString()}</Text>",
        "profile cash: commas + never wraps",
    ),
    (
        Path("frontend/app/(tabs)/shop.tsx"),
        "<Text style={styles.cashText}>${player?.cash || 0}</Text>",
        "<Text style={styles.cashText} numberOfLines={1} adjustsFontSizeToFit>${(player?.cash || 0).toLocaleString()}</Text>",
        "shop header cash: commas + never wraps",
    ),
    (
        Path("frontend/app/(tabs)/index.tsx"),
        "<Text style={styles.shopCash}>${player?.cash || 0}</Text>",
        "<Text style={styles.shopCash} numberOfLines={1} adjustsFontSizeToFit>${(player?.cash || 0).toLocaleString()}</Text>",
        "map header cash: commas + never wraps",
    ),
    (
        Path("frontend/app/(tabs)/index.tsx"),
        "<Text style={styles.rewardText}>Your cash: ${player?.cash || 0}</Text>",
        "<Text style={styles.rewardText}>Your cash: ${(player?.cash || 0).toLocaleString()}</Text>",
        "popup cash: commas for readability",
    ),
]


def main():
    for path, old, new, desc in EDITS:
        if not path.exists():
            print(f"SKIP: {path} not found — {desc}")
            continue
        src = path.read_text()
        if new in src:
            print(f"SKIP ({path.name}): {desc} (already applied)")
        elif src.count(old) >= 1:
            src = src.replace(old, new, 1)
            path.write_text(src)
            print(f"OK ({path.name}): {desc}")
        else:
            print(f"WARNING ({path.name}): anchor not found — {desc}")
    print("CASH_FORMAT_OK")


if __name__ == "__main__":
    main()
