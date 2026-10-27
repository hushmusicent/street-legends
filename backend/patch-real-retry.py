"""Street Legends backend: empty areas retry instead of staying empty forever.
Run from repo root: python3 backend/patch-real-retry.py
Idempotent - safe to re-run.

ROOT CAUSE of missing restaurants/shops in areas that HAVE them: a previous
Overpass fetch could come back empty (timeout, hiccup) yet still write its
"fetched" record. Combined with the permanent cache, that area was then
marked done forever — every later visit returned [] and never retried.
Banks/nightclubs worked in the same spot because their fetches had succeeded.

FIX (two parts, all four place types):
1. Helpers only write their "fetched" record when Overpass actually returned
   elements — an empty response no longer poisons the cache.
2. Spawn endpoints retry the background fetch whenever their radius query
   comes back empty, even if a fetch record exists — this heals areas that
   were already poisoned, and genuinely empty areas just retry (bounded by
   the in-flight dedupe set).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# Part 1: only mark an area fetched when Overpass returned something.
# Each helper has: await db.<X>_fetches.insert_one({\n "latitude"... \n "fetched_at"... \n })
FETCH_INSERTS = [
    ("db.gas_station_fetches", "gas stations"),
    ("db.restaurant_fetches", "restaurants"),
    ("db.nightclub_fetches", "nightclubs"),
    ("db.bank_fetches", "banks"),
]

# Part 2: retry blocks inserted before each spawn's return.
RETRY_BLOCKS = [
    (
        '''    for bank in banks:
        bank.pop("_id", None)
    return banks''',
        '''    for bank in banks:
        bank.pop("_id", None)
    # If nothing cached here, retry even if a (possibly empty) fetch record
    # exists — a previous fetch may have come back empty.
    if len(banks) == 0:
        area_key = f"bank_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_banks_from_overpass(latitude, longitude, player_level, area_key))
    return banks''',
        "banks",
    ),
    (
        '''    for r in restaurants:
        r.pop("_id", None)
    return restaurants''',
        '''    for r in restaurants:
        r.pop("_id", None)
    # If nothing cached here, retry even if a (possibly empty) fetch record
    # exists — a previous fetch may have come back empty.
    if len(restaurants) == 0:
        area_key = f"rest_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_restaurants_from_overpass(latitude, longitude, player_level, area_key))
    return restaurants''',
        "restaurants",
    ),
    (
        '''    for nc in nightclubs:
        nc.pop("_id", None)
    return nightclubs''',
        '''    for nc in nightclubs:
        nc.pop("_id", None)
    # If nothing cached here, retry even if a (possibly empty) fetch record
    # exists — a previous fetch may have come back empty.
    if len(nightclubs) == 0:
        area_key = f"club_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_nightclubs_from_overpass(latitude, longitude, player_level, area_key))
    return nightclubs''',
        "nightclubs",
    ),
    (
        '''    random.shuffle(real_locations)
''',
        '''    random.shuffle(real_locations)

    # If no gas stations cached here, retry even if a (possibly empty) fetch
    # record exists — a previous fetch may have come back empty.
    if len(real_locations) == 0:
        gas_area_key = f"store_{round(latitude, 2)}_{round(longitude, 2)}"
        if gas_area_key not in _osm_fetching:
            _osm_fetching.add(gas_area_key)
            asyncio.create_task(_fetch_gas_stations_from_overpass(latitude, longitude, player_level, gas_area_key))
''',
        "shops (gas stations)",
    ),
]


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "overpass-api.de" not in src:
        print("ERROR: no Overpass fetchers found — apply the real-location patches first.")
        sys.exit(1)

    # Part 1: guard each fetch-record insert with `if elements:`
    for coll, label in FETCH_INSERTS:
        old_block = (
            f"            await {coll}.insert_one({{\n"
            f"                \"latitude\": latitude,\n"
            f"                \"longitude\": longitude,\n"
            f"                \"fetched_at\": datetime.utcnow().isoformat(),\n"
            f"            }})"
        )
        new_block = (
            f"            if elements:\n"
            f"                await {coll}.insert_one({{\n"
            f"                    \"latitude\": latitude,\n"
            f"                    \"longitude\": longitude,\n"
            f"                    \"fetched_at\": datetime.utcnow().isoformat(),\n"
            f"                }})"
        )
        if new_block in src:
            print(f"SKIP: {label} fetch record already guarded")
        elif src.count(old_block) != 1:
            print(f"WARNING: {label} fetch-record anchor matched {src.count(old_block)}x — skipping")
        else:
            src = src.replace(old_block, new_block, 1)
            print(f"OK: {label} fetch record only written when Overpass returned data")

    # Part 2: retry blocks
    for old, new, label in RETRY_BLOCKS:
        if new.strip() in src:
            print(f"SKIP: {label} retry already installed")
        elif src.count(old) != 1:
            print(f"WARNING: {label} anchor matched {src.count(old)}x — skipping")
        else:
            src = src.replace(old, new, 1)
            print(f"OK: {label} retry empty areas instead of staying empty")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_RETRY_OK")


if __name__ == "__main__":
    main()
