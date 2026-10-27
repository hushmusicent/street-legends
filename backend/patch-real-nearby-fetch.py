"""Street Legends backend: fetch nearby stations even when distant ones exist.
Run from repo root: python3 backend/patch-real-nearby-fetch.py
Idempotent - safe to re-run.

WHY gun shops still don't show near the player: the retry logic only
triggers a background fetch when the result is EMPTY. But at the player's
spot the result is NOT empty — it holds 2 distant stations (3.4 and 3.8 km
away, off-screen) — so no fetch is ever triggered for the nearby stations,
and the area stays stuck with distant-only results forever. The closest
cached station never gets closer, no matter how many times the map loads.

FIX (shops only, the reported problem): after sorting stations
closest-first, if the closest cached station is still farther than the
2 km grid fetch radius, trigger a background fetch for this area anyway.
Distant-only results no longer block nearby fetches. Once the nearby
stations land (6 within 2 km at the test spot), the closest-first sort
picks them and shops appear on the visible map. Also applies the
closest-first sort itself if the nearby patch hasn't been run yet, so
this patch works standalone.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

SORT_OLD = "    random.shuffle(real_locations)"
SORT_NEW = """    # Closest first so shops spawn near the player, not randomly up to 5 km
    # away off-screen. (Squared distance is enough for sorting.)
    _cos = max(0.2, math.cos(math.radians(latitude)))
    real_locations.sort(key=lambda loc: ((loc["latitude"] - latitude) * 111000.0) ** 2 + ((loc["longitude"] - longitude) * 111000.0 * _cos) ** 2)"""

FETCH_OLD = """    # If no gas stations cached here, fill them in the BACKGROUND — never
    # block the map on Overpass. The next refresh picks them up.
    if len(real_locations) == 0:
        gas_area_key = f"store_{round(latitude, 2)}_{round(longitude, 2)}"
        if gas_area_key not in _osm_fetching:
            _osm_fetching.add(gas_area_key)
            asyncio.create_task(_fetch_gas_stations_from_overpass(latitude, longitude, player_level, gas_area_key))

    # Gas stations only — no random fallback."""
FETCH_NEW = """    # If no gas stations cached here, fill them in the BACKGROUND — never
    # block the map on Overpass. The next refresh picks them up.
    if len(real_locations) == 0:
        gas_area_key = f"store_{round(latitude, 2)}_{round(longitude, 2)}"
        if gas_area_key not in _osm_fetching:
            _osm_fetching.add(gas_area_key)
            asyncio.create_task(_fetch_gas_stations_from_overpass(latitude, longitude, player_level, gas_area_key))

    # If the closest cached station is still outside the 2 km grid fetch
    # radius, the nearby stations were never fetched for this area — fetch
    # them even though the result isn't empty. Distant-only results must
    # not block nearby fetches.
    if len(real_locations) > 0:
        _c = real_locations[0]
        _dlat = (_c["latitude"] - latitude) * 111000.0
        _dlng = (_c["longitude"] - longitude) * 111000.0 * max(0.2, math.cos(math.radians(latitude)))
        if _dlat * _dlat + _dlng * _dlng > 2000.0 * 2000.0:
            gas_area_key = f"store_{round(latitude, 2)}_{round(longitude, 2)}"
            if gas_area_key not in _osm_fetching:
                _osm_fetching.add(gas_area_key)
                asyncio.create_task(_fetch_gas_stations_from_overpass(latitude, longitude, player_level, gas_area_key))

    # Gas stations only — no random fallback."""


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "gas_stations" not in src:
        print("ERROR: no gas-station shops found — apply the real-shops patches first.")
        sys.exit(1)

    # Ensure closest-first sort (from the nearby patch) is present.
    if SORT_NEW in src:
        print("SKIP: closest-first sort already present")
    elif src.count(SORT_OLD) >= 1:
        src = src.replace(SORT_OLD, SORT_NEW)
        print(f"OK: closest-first sort applied ({src.count(SORT_NEW)}x)")
    else:
        print("WARNING: neither sort nor shuffle found — continuing anyway")

    if FETCH_NEW in src:
        print("SKIP: distant-only fetch trigger already present")
    elif src.count(FETCH_OLD) == 1:
        src = src.replace(FETCH_OLD, FETCH_NEW, 1)
        print("OK: distant-only areas now trigger a nearby fetch")
    else:
        print(f"WARNING: fetch anchor matched {src.count(FETCH_OLD)}x — skipping")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_NEARBY_FETCH_OK")


if __name__ == "__main__":
    main()
