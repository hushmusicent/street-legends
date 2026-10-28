"""Street Legends backend: fetch restaurants/gas stations NOW when empty.
Run from repo root: python3 backend/patch-real-blocking.py
Idempotent - safe to re-run.

WHY: background Overpass fetches are not landing data for restaurants and
gas stations (live test: triggered + waited 5 min, still 0, while OSM has
79 restaurants and 21 gas stations at the spot). Banks worked earlier via
BLOCKING fetches, so this patch goes back to that proven route for the two
broken types: when the cache is empty, the spawn AWAITS the Overpass fetch
and returns the fresh data in the same response. First visit to a new area
takes ~a minute; every later visit is instant from cache. Works whether or
not the retry patch is already applied.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

REST_QUERY = '''        restaurants = await db.restaurants.find({
            "source": "osm",
            "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
            "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
        }).to_list(100)'''

REST_BLOCKING = '''    # If nothing cached here, fetch NOW and wait for it. Background tasks
    # proved unreliable on this host, so the first visit waits for the data
    # instead of hoping a background task lands it.
    if len(restaurants) == 0:
        await _fetch_restaurants_from_overpass(latitude, longitude, player_level, f"rest_{round(latitude, 2)}_{round(longitude, 2)}")
''' + REST_QUERY + '''
        for r in restaurants:
            r.pop("_id", None)'''

GAS_QUERY = '''        real_locations = await db.gas_stations.find({
            "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
            "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
        }).to_list(100)'''

GAS_BLOCKING = '''    # If no gas stations cached here, fetch NOW and wait for it. Background
    # tasks proved unreliable on this host.
    if len(real_locations) == 0:
        await _fetch_gas_stations_from_overpass(latitude, longitude, player_level, f"store_{round(latitude, 2)}_{round(longitude, 2)}")
''' + GAS_QUERY + '''
        random.shuffle(real_locations)'''


def replace_rest(src):
    # Case A: retry block already present — replace it with blocking fetch.
    old_a = '''    for r in restaurants:
        r.pop("_id", None)
    # If nothing cached here, retry even if a (possibly empty) fetch record
    # exists — a previous fetch may have come back empty.
    if len(restaurants) == 0:
        area_key = f"rest_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_restaurants_from_overpass(latitude, longitude, player_level, area_key))
    return restaurants'''
    new_a = '''    for r in restaurants:
        r.pop("_id", None)
''' + REST_BLOCKING + '''
    return restaurants'''
    if src.count(old_a) == 1:
        return src.replace(old_a, new_a, 1), "restaurants (retry block -> blocking)"
    # Case B: no retry block — insert blocking fetch before the return.
    old_b = '''    for r in restaurants:
        r.pop("_id", None)
    return restaurants'''
    new_b = '''    for r in restaurants:
        r.pop("_id", None)
''' + REST_BLOCKING + '''
    return restaurants'''
    if src.count(old_b) == 1:
        return src.replace(old_b, new_b, 1), "restaurants (blocking fetch inserted)"
    return src, None


def replace_gas(src):
    # Case A: retry block already present — replace it with blocking fetch.
    old_a = '''    # If no gas stations cached here, retry even if a (possibly empty) fetch
    # record exists — a previous fetch may have come back empty.
    if len(real_locations) == 0:
        gas_area_key = f"store_{round(latitude, 2)}_{round(longitude, 2)}"
        if gas_area_key not in _osm_fetching:
            _osm_fetching.add(gas_area_key)
            asyncio.create_task(_fetch_gas_stations_from_overpass(latitude, longitude, player_level, gas_area_key))

    # Gas stations only — no random fallback. If the area hasn't been fetched yet,
    # the background fetch fills the cache and shops appear on the next refresh.'''
    new_a = GAS_BLOCKING + '''

    # Gas stations only — no random fallback.'''
    if src.count(old_a) == 1:
        return src.replace(old_a, new_a, 1), "shops/gas (retry block -> blocking)"
    # Case B: no retry block — insert blocking fetch before num_shops.
    old_b = '''    random.shuffle(real_locations)

    # Gas stations only — no random fallback. If the area hasn't been fetched yet,
    # the background fetch fills the cache and shops appear on the next refresh.
    num_shops = min(num_shops, len(real_locations))'''
    new_b = '''    random.shuffle(real_locations)

''' + GAS_BLOCKING + '''

    # Gas stations only — no random fallback.
    num_shops = min(num_shops, len(real_locations))'''
    if src.count(old_b) == 1:
        return src.replace(old_b, new_b, 1), "shops/gas (blocking fetch inserted)"
    return src, None


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "overpass-api.de" not in src:
        print("ERROR: no Overpass fetchers found — apply the real-location patches first.")
        sys.exit(1)
    if "fetch NOW and wait for it" in src:
        print("SKIP: blocking fetch already installed")
    else:
        src, msg = replace_rest(src)
        print(f"OK: {msg}" if msg else "WARNING: restaurants anchor not found — skipping")
        src, msg = replace_gas(src)
        print(f"OK: {msg}" if msg else "WARNING: shops/gas anchor not found — skipping")
    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_BLOCKING_OK")


if __name__ == "__main__":
    main()
