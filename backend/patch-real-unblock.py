"""Street Legends backend: stop blocking the map on Overpass.
Run from repo root: python3 backend/patch-real-unblock.py
Idempotent - safe to re-run.

WHY the map got slow: the blocking patch made restaurant/shop spawns AWAIT
the Overpass fetch (up to 120s each, up to 270s each with the fallback
patch). The frontend loads all 14 marker types in one batch, so the
slowest call stalls the WHOLE marker set — enemies and territories
included. A new area could hang the map for minutes.

FIX: spawns go back to returning cached data instantly and filling empty
areas in the BACKGROUND. The map (enemies, territories, cached places)
loads fast; empty place types fill in over the next minute or two and
appear on the next refresh. The reliability fixes stay in place, so the
background fetches now actually land: 3-instance Overpass fallback, a
concurrency cap so the map can't queue itself out, retry on empty areas,
and a permanent cache once an area is fetched.

Tradeoff to be clear about: first visit to a brand-new area shows places
only after the background fetch lands + a refresh (1-3 min), NOT
instantly. But the map itself never hangs again.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "overpass-api.de" not in src:
        print("ERROR: no Overpass fetchers found — apply the real-location patches first.")
        sys.exit(1)

    # --- Restaurants: blocking -> background ---
    old_rest = '''    for r in restaurants:
        r.pop("_id", None)
    # If nothing cached here, fetch NOW and wait for it. Background tasks
    # proved unreliable on this host, so the first visit waits for the data
    # instead of hoping a background task lands it.
    if len(restaurants) == 0:
        await _fetch_restaurants_from_overpass(latitude, longitude, player_level, f"rest_{round(latitude, 2)}_{round(longitude, 2)}")
        restaurants = await db.restaurants.find({
            "source": "osm",
            "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
            "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
        }).to_list(100)
        for r in restaurants:
            r.pop("_id", None)
    return restaurants'''
    new_rest = '''    for r in restaurants:
        r.pop("_id", None)
    # If nothing cached here, fill it in the BACKGROUND — never block the
    # map on Overpass. The fetch has 3-instance fallback + a concurrency
    # cap, and the next refresh picks up the data.
    if len(restaurants) == 0:
        area_key = f"rest_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_restaurants_from_overpass(latitude, longitude, player_level, area_key))
    return restaurants'''
    if new_rest in src:
        print("SKIP: restaurants already background")
    elif src.count(old_rest) == 1:
        src = src.replace(old_rest, new_rest, 1)
        print("OK: restaurants back to background (map no longer waits)")
    else:
        print(f"WARNING: restaurants blocking anchor matched {src.count(old_rest)}x — skipping")

    # --- Shops/gas: blocking -> background ---
    old_gas = '''    # If no gas stations cached here, fetch NOW and wait for it. Background
    # tasks proved unreliable on this host.
    if len(real_locations) == 0:
        await _fetch_gas_stations_from_overpass(latitude, longitude, player_level, f"store_{round(latitude, 2)}_{round(longitude, 2)}")
        real_locations = await db.gas_stations.find({
            "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
            "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
        }).to_list(100)
        random.shuffle(real_locations)'''
    new_gas = '''    # If no gas stations cached here, fill them in the BACKGROUND — never
    # block the map on Overpass. The next refresh picks them up.
    if len(real_locations) == 0:
        gas_area_key = f"store_{round(latitude, 2)}_{round(longitude, 2)}"
        if gas_area_key not in _osm_fetching:
            _osm_fetching.add(gas_area_key)
            asyncio.create_task(_fetch_gas_stations_from_overpass(latitude, longitude, player_level, gas_area_key))'''
    if new_gas in src:
        print("SKIP: shops/gas already background")
    elif src.count(old_gas) == 1:
        src = src.replace(old_gas, new_gas, 1)
        print("OK: shops/gas back to background (map no longer waits)")
    else:
        print(f"WARNING: shops/gas blocking anchor matched {src.count(old_gas)}x — skipping")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_UNBLOCK_OK")


if __name__ == "__main__":
    main()
