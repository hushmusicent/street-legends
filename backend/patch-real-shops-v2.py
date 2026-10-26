"""Street Legends backend: shops at GAS STATIONS ONLY (no regular stores).
Run from repo root: python3 backend/patch-real-shops-v2.py
Idempotent - safe to re-run. Requires patch-real-shops.py.

WHAT CHANGES:
1. The Overpass query drops shop=* entirely — only amenity=fuel (gas stations).
2. The cache collections switch from store_locations/store_fetches to
   gas_stations/gas_station_fetches, so the regular stores cached by v1 are
   simply never served again (no DB access needed to clear them).
3. Name fallback becomes "Gas Station" instead of "Store".
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

REPLACEMENTS = [
    # 1. Drop regular shops from the Overpass query (gas stations only)
    (
        '''            f'node["shop"](around:5000,{latitude},{longitude});'\n            f'way["shop"](around:5000,{latitude},{longitude});'\n''',
        "",
        "removed shop=* from Overpass query",
    ),
    # 2. Fresh collections so v1's cached regular stores are never served
    ("db.store_locations", "db.gas_stations", "store_locations -> gas_stations"),
    ("db.store_fetches", "db.gas_station_fetches", "store_fetches -> gas_station_fetches"),
    ("_fetch_stores_from_overpass", "_fetch_gas_stations_from_overpass", "renamed fetch helper"),
    ("store_area_key", "gas_area_key", "renamed area key"),
    # 3. Name fallback
    ('or "Store"', 'or "Gas Station"', 'name fallback -> Gas Station'),
    ('(game shop lookup)', '(game gas station lookup)', 'User-Agent updated'),
]


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "_fetch_stores_from_overpass" not in src and "_fetch_gas_stations_from_overpass" not in src:
        print("ERROR: patch-real-shops.py must be applied first. Aborting.")
        sys.exit(1)
    if '"amenity"="fuel"' not in src:
        print("ERROR: shop spawn code not found. Aborting.")
        sys.exit(1)

    for old, new, label in REPLACEMENTS:
        if old == new:
            continue
        if old not in src:
            if new in src:
                print(f"SKIP: {label} (already applied)")
                continue
            print(f"WARNING: anchor not found for: {label}")
            continue
        src = src.replace(old, new)
        print(f"OK: {label}")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_SHOPS_V2_OK")


if __name__ == "__main__":
    main()
