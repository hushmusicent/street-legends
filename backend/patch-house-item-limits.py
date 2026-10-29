"""Street Legends backend: house item limits per tier.
Run from repo root: python3 backend/patch-house-item-limits.py
Idempotent - safe to re-run.

RULE (user spec):
  Street Apartment ($100k) -> holds 2 items
  Country Cabin ($500k)    -> holds 3 items
  Luxury Mansion ($1M)     -> holds 6 items

CHANGES:
1. HOUSE_TIERS gains item_limit per tier.
2. New houses store item_limit on the house doc at buy time, so the
   future furniture endpoint can enforce len(items) >= item_limit.
   (Furniture buying itself is a separate future step.)
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

TIER_OLD = '''    "apartment": {"name": "Street Apartment", "price": 100000, "image": "house-apartment"},
    "cabin": {"name": "Country Cabin", "price": 500000, "image": "house-cabin"},
    "mansion": {"name": "Luxury Mansion", "price": 1000000, "image": "house-mansion"},'''
TIER_NEW = '''    "apartment": {"name": "Street Apartment", "price": 100000, "image": "house-apartment", "item_limit": 2},
    "cabin": {"name": "Country Cabin", "price": 500000, "image": "house-cabin", "item_limit": 3},
    "mansion": {"name": "Luxury Mansion", "price": 1000000, "image": "house-mansion", "item_limit": 6},'''

DOC_OLD = '''        "items": [],
        "created_at": datetime.utcnow().isoformat(),'''
DOC_NEW = '''        "items": [],
        "item_limit": tier_info["item_limit"],
        "created_at": datetime.utcnow().isoformat(),'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "item_limit" in src:
        print("SKIP: item limits already present")
    else:
        if src.count(TIER_OLD) == 1:
            src = src.replace(TIER_OLD, TIER_NEW, 1)
            print("OK: item limits added to HOUSE_TIERS (2 / 3 / 6)")
        else:
            print(f"WARNING: tier anchor matched {src.count(TIER_OLD)}x")
        if src.count(DOC_OLD) == 1:
            src = src.replace(DOC_OLD, DOC_NEW, 1)
            print("OK: new houses store item_limit")
        else:
            print(f"WARNING: doc anchor matched {src.count(DOC_OLD)}x")
        SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("HOUSE_ITEM_LIMITS_OK")


if __name__ == "__main__":
    main()
