"""Move the God Potions section below the shop filter tabs.
Run from repo root: python3 frontend/patch-god-potions-move.py
Idempotent - safe to re-run.

The God Potions section was rendered above the filter tabs, burying the
filter menu. This moves it to sit between the filter tabs and the items list.
"""
import sys
from pathlib import Path

SHOP = Path("frontend/app/(tabs)/shop.tsx")

OLD_TOP = """      <GodPotions playerId={playerId} />

      {/* Filter Tabs */}"""
NEW_TOP = """      {/* Filter Tabs */}"""

OLD_ITEMS = """      {/* Items List */}"""
NEW_ITEMS = """      <GodPotions playerId={playerId} />

      {/* Items List */}"""


def main():
    if not SHOP.exists():
        print(f"ERROR: {SHOP} not found. Run from repo root.")
        sys.exit(1)
    src = SHOP.read_text()

    if NEW_ITEMS in src and OLD_TOP not in src:
        print("SKIP: God Potions already below filter tabs")
    else:
        if src.count(OLD_TOP) != 1:
            print(f"ERROR: top anchor matched {src.count(OLD_TOP)}x. Aborting.")
            sys.exit(1)
        src = src.replace(OLD_TOP, NEW_TOP, 1)
        print("OK: removed God Potions from above filter tabs")
        if src.count(OLD_ITEMS) != 1:
            print(f"ERROR: items anchor matched {src.count(OLD_ITEMS)}x. Aborting.")
            sys.exit(1)
        src = src.replace(OLD_ITEMS, NEW_ITEMS, 1)
        print("OK: God Potions moved below filter tabs")
        SHOP.write_text(src)

    print("GOD_POTIONS_MOVE_OK")


if __name__ == "__main__":
    main()
