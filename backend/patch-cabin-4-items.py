"""Street Legends backend: Country Cabin holds 4 items (was 3).
Run from /app: python3 backend/patch-cabin-4-items.py
Idempotent - safe to re-run.

CHANGES (backend/server.py):
1. HOUSE_TIERS cabin item_limit 3 -> 4 (new cabins bought after this hold 4).
2. BOTH place-item enforcement points now derive the limit from
   HOUSE_TIERS by tier instead of the house document's stored
   item_limit, so cabins ALREADY bought (stored item_limit 3) also
   hold 4 without a database migration.
   - buy-item path: limit = HOUSE_TIERS[tier].item_limit
   - place-from-inventory path: same derivation.

BACKEND change: run the curl, then Deploy (free). No new app build
needed - the limit is enforced server-side.
"""
import sys
from pathlib import Path

PATH = Path("backend/server.py")

REPLACEMENTS = [
    (
        '    "cabin": {"name": "Country Cabin", "price": 500000, "image": "house-cabin", "item_limit": 3},',
        '    "cabin": {"name": "Country Cabin", "price": 500000, "image": "house-cabin", "item_limit": 4},',
        "cabin item_limit 3 -> 4 in HOUSE_TIERS",
    ),
    (
        '    limit = house.get("item_limit") or HOUSE_TIERS.get(house.get("tier"), {}).get("item_limit", 2)',
        '    limit = HOUSE_TIERS.get(house.get("tier"), {}).get("item_limit", 2)',
        "buy-item path derives limit from HOUSE_TIERS by tier",
    ),
    (
        '    if len(items) >= house.get("item_limit", 6):',
        '    limit = HOUSE_TIERS.get(house.get("tier"), {}).get("item_limit", 6)\n    if len(items) >= limit:',
        "place-from-inventory path derives limit from HOUSE_TIERS by tier",
    ),
]


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from /app.")
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
    print("CABIN_4_ITEMS_OK")


if __name__ == "__main__":
    main()
