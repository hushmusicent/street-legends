"""Street Legends backend: hide old fake banks/restaurants/clubs + no random shops.
Run from repo root: python3 backend/patch-real-cleanup.py
Idempotent - safe to re-run.

ROOT CAUSE of "still looks random": the real-location patches return EVERYTHING
in the DB within the radius — including the old fake banks/restaurants/clubs
spawned before the patches (they have no source/osm_id). Those fakes never
expire, so they keep showing up next to (or instead of) the real ones.
Shops had a second problem: when the gas-station cache was empty, they fell
back to random positions + fake names.

FIX:
1. Banks, restaurants, nightclubs spawn queries now filter to source="osm"
   only — old fakes are never served again (no DB wipe needed).
2. Shops: the random fallback is gone. If no gas stations are cached yet for
   the area, no shops appear until the background fetch fills the cache
   (they show up on the next map refresh) — gas stations only, never random.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# 1. Source filter for the three stored collections (new-code radius queries)
SOURCE_FILTERS = [
    ('db.banks.find({\n        "latitude"', 'db.banks.find({\n        "source": "osm",\n        "latitude"', "banks"),
    ('db.restaurants.find({\n        "latitude"', 'db.restaurants.find({\n        "source": "osm",\n        "latitude"', "restaurants"),
    ('db.nightclubs.find({\n        "latitude"', 'db.nightclubs.find({\n        "source": "osm",\n        "latitude"', "nightclubs"),
]

# 2. Shops: cap to available gas stations, drop the random fallback
OLD_SHOP_LOOP = '''    for i in range(num_shops):
        # Real store/gas station when available, else random offset within ~500m
        if i < len(real_locations):
            shop_lat = real_locations[i]["latitude"]
            shop_lng = real_locations[i]["longitude"]
            real_name = real_locations[i]["name"]
        else:
            shop_lat = latitude + random.uniform(-0.004, 0.004)
            shop_lng = longitude + random.uniform(-0.004, 0.004)
            real_name = None
'''
NEW_SHOP_LOOP = '''    # Gas stations only — no random fallback. If the area hasn't been fetched yet,
    # the background fetch fills the cache and shops appear on the next refresh.
    num_shops = min(num_shops, len(real_locations))
    for i in range(num_shops):
        shop_lat = real_locations[i]["latitude"]
        shop_lng = real_locations[i]["longitude"]
        real_name = real_locations[i]["name"]
'''

OLD_SHOP_NAME = "shop_name = real_name or random.choice(SHOP_NAMES)"
NEW_SHOP_NAME = "shop_name = real_name"


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    # 1. Source filters
    for old, new, label in SOURCE_FILTERS:
        if new in src:
            print(f"SKIP: {label} already filtered to real (osm) records")
        elif src.count(old) != 1:
            print(f"WARNING: {label} spawn query anchor matched {src.count(old)}x — skipping")
        else:
            src = src.replace(old, new, 1)
            print(f"OK: {label} spawn now serves real (osm) records only, old fakes hidden")

    # 2. Shops: no random fallback
    if NEW_SHOP_LOOP.strip() in src:
        print("SKIP: shops already gas-stations-only (no fallback)")
    elif src.count(OLD_SHOP_LOOP) != 1:
        print(f"WARNING: shop loop anchor matched {src.count(OLD_SHOP_LOOP)}x — skipping")
    else:
        src = src.replace(OLD_SHOP_LOOP, NEW_SHOP_LOOP, 1)
        print("OK: shops no longer fall back to random positions")

    if ("\n        " + NEW_SHOP_NAME + "\n") in src:
        print("SKIP: shop name already real-only")
    elif src.count(OLD_SHOP_NAME) != 1:
        print(f"WARNING: shop name anchor matched {src.count(OLD_SHOP_NAME)}x — skipping")
    else:
        src = src.replace(OLD_SHOP_NAME, NEW_SHOP_NAME, 1)
        print("OK: shop names are real gas station names only")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_CLEANUP_OK")


if __name__ == "__main__":
    main()
