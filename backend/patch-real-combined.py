"""Street Legends backend: ONE Overpass query for all place types.
Run from repo root: python3 backend/patch-real-combined.py
Idempotent - safe to re-run.

WHY new areas are slow: the game fires FOUR separate Overpass queries
(banks, restaurants, clubs, gas stations) and Overpass only runs ~2 per IP
at once, so they queue behind each other — 2 rounds of 40-90s each before
all types land. The combined query grabs every place type in a SINGLE
Overpass call (~40-60s total), so a new area fills in one shot instead of
four queued rounds. Also keeps the 3-instance fallback + semaphore, the
2 km grid radius, and per-type fetch records (only for types that
actually returned data, so a missing type still retries).

HOW: adds _fetch_all_places_from_overpass (one query, routes each element
to its collection by amenity tag) and repoints all four spawns' triggers
at it under a shared all_<lat>_<lng> key, so the first spawn to need data
fires the one combined fetch and the other three dedupe onto it. The old
individual fetchers stay defined but unused (harmless).
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

DEFINITIONS_TAIL = '''# Overpass instances to try in order + cap on concurrent calls, so one map
# load firing banks/restaurants/clubs/shops at once can't queue itself out.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OVERPASS_SEMAPHORE = asyncio.Semaphore(2)'''

COMBINED = '''
async def _fetch_all_places_from_overpass(latitude: float, longitude: float, player_level: int, area_key: str):
    """ONE Overpass query for banks + restaurants + clubs + gas stations.
    Routes each element to its collection by amenity tag. Per-type fetch
    records only for types that actually returned data."""
    try:
        query = (
            "[out:json][timeout:80];"
            "("
            f'node["amenity"="bank"](around:2000,{latitude},{longitude});'
            f'way["amenity"="bank"](around:2000,{latitude},{longitude});'
            f'node["amenity"="restaurant"](around:2000,{latitude},{longitude});'
            f'way["amenity"="restaurant"](around:2000,{latitude},{longitude});'
            f'node["amenity"="fast_food"](around:2000,{latitude},{longitude});'
            f'way["amenity"="fast_food"](around:2000,{latitude},{longitude});'
            f'node["amenity"="nightclub"](around:2000,{latitude},{longitude});'
            f'way["amenity"="nightclub"](around:2000,{latitude},{longitude});'
            f'node["amenity"="bar"](around:2000,{latitude},{longitude});'
            f'way["amenity"="bar"](around:2000,{latitude},{longitude});'
            f'node["amenity"="pub"](around:2000,{latitude},{longitude});'
            f'way["amenity"="pub"](around:2000,{latitude},{longitude});'
            f'node["amenity"="fuel"](around:2000,{latitude},{longitude});'
            f'way["amenity"="fuel"](around:2000,{latitude},{longitude});'
            ");"
            "out center 200;"
        )
        elements = []
        async with OVERPASS_SEMAPHORE:
            for overpass_url in OVERPASS_URLS:
                try:
                    async with httpx.AsyncClient(timeout=90) as client:
                        resp = await client.post(
                            overpass_url,
                            data={"data": query},
                            headers={"User-Agent": "StreetLegends/1.0 (game places lookup)"},
                        )
                    if resp.status_code == 200:
                        elements = resp.json().get("elements", [])
                        break
                except Exception:
                    continue
        base_reward = int((500 + (player_level * 100)) * 0.5)
        found = set()
        for el in elements:
            osm_id = f"{el.get('type')}/{el.get('id')}"
            tags = el.get("tags", {}) or {}
            amenity = tags.get("amenity")
            if el.get("type") == "node":
                plat, plng = el.get("lat"), el.get("lon")
            else:
                center = el.get("center") or {}
                plat, plng = center.get("lat"), center.get("lon")
            if plat is None or plng is None:
                continue
            name = tags.get("name") or tags.get("brand")
            if amenity == "bank":
                if not name:
                    name = "Bank"
                if not await db.banks.find_one({"osm_id": osm_id}):
                    await db.banks.insert_one({
                        "id": str(uuid.uuid4()),
                        "osm_id": osm_id,
                        "name": name,
                        "icon": "🏦",
                        "latitude": plat,
                        "longitude": plng,
                        "min_reward": int(base_reward * 0.5),
                        "max_reward": int(base_reward * 1.5),
                        "source": "osm",
                        "created_at": datetime.utcnow().isoformat(),
                    })
                found.add("bank")
            elif amenity in ("restaurant", "fast_food"):
                if not name:
                    name = "Restaurant"
                if not await db.restaurants.find_one({"osm_id": osm_id}):
                    await db.restaurants.insert_one({
                        "id": str(uuid.uuid4()),
                        "osm_id": osm_id,
                        "name": name,
                        "icon": "🍔",
                        "latitude": plat,
                        "longitude": plng,
                        "heal_percent": 25,
                        "source": "osm",
                        "created_at": datetime.utcnow().isoformat(),
                    })
                found.add("restaurant")
            elif amenity in ("nightclub", "bar", "pub"):
                if not name:
                    name = "Nightclub"
                if not await db.nightclubs.find_one({"osm_id": osm_id}):
                    await db.nightclubs.insert_one({
                        "id": str(uuid.uuid4()),
                        "osm_id": osm_id,
                        "name": name,
                        "icon": "🎵",
                        "latitude": plat,
                        "longitude": plng,
                        "energy_percent": 25,
                        "source": "osm",
                        "created_at": datetime.utcnow().isoformat(),
                    })
                found.add("nightclub")
            elif amenity == "fuel":
                if not name:
                    name = "Gas Station"
                if not await db.gas_stations.find_one({"osm_id": osm_id}):
                    await db.gas_stations.insert_one({
                        "id": str(uuid.uuid4()),
                        "osm_id": osm_id,
                        "name": name,
                        "latitude": plat,
                        "longitude": plng,
                        "source": "osm",
                        "created_at": datetime.utcnow().isoformat(),
                    })
                found.add("fuel")
        now = datetime.utcnow().isoformat()
        if "bank" in found:
            await db.bank_fetches.insert_one({"latitude": latitude, "longitude": longitude, "fetched_at": now})
        if "restaurant" in found:
            await db.restaurant_fetches.insert_one({"latitude": latitude, "longitude": longitude, "fetched_at": now})
        if "nightclub" in found:
            await db.nightclub_fetches.insert_one({"latitude": latitude, "longitude": longitude, "fetched_at": now})
        if "fuel" in found:
            await db.gas_station_fetches.insert_one({"latitude": latitude, "longitude": longitude, "fetched_at": now})
    except Exception as e:
        logging.warning(f"Overpass combined places fetch failed: {e}")
    finally:
        _osm_fetching.discard(area_key)

'''

CALL_REPLACEMENTS = [
    ("asyncio.create_task(_fetch_banks_from_overpass(", "asyncio.create_task(_fetch_all_places_from_overpass("),
    ("asyncio.create_task(_fetch_restaurants_from_overpass(", "asyncio.create_task(_fetch_all_places_from_overpass("),
    ("asyncio.create_task(_fetch_nightclubs_from_overpass(", "asyncio.create_task(_fetch_all_places_from_overpass("),
    ("asyncio.create_task(_fetch_gas_stations_from_overpass(", "asyncio.create_task(_fetch_all_places_from_overpass("),
]

KEY_REPLACEMENTS = [
    ('f"bank_', 'f"all_'),
    ('f"rest_', 'f"all_'),
    ('f"club_', 'f"all_'),
    ('f"store_', 'f"all_'),
]


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "gas_stations" not in src:
        print("ERROR: no gas-station shops found — apply the real-shops patches first.")
        sys.exit(1)

    # 1. Ensure fallback definitions exist (combined fetcher needs them).
    if "OVERPASS_SEMAPHORE" in src:
        print("SKIP: Overpass URL list + semaphore already defined")
    elif "_osm_fetching = set()" in src:
        src = src.replace("_osm_fetching = set()", "_osm_fetching = set()\n" + DEFINITIONS_TAIL, 1)
        print("OK: Overpass URL list + semaphore defined")
    else:
        m = re.search(r"async def _fetch_\w+_from_overpass", src)
        if not m:
            print("ERROR: no _osm_fetching line and no fetcher found.")
            sys.exit(1)
        src = src[:m.start()] + "_osm_fetching = set()\n" + DEFINITIONS_TAIL + "\n\n" + src[m.start():]
        print("OK: _osm_fetching + Overpass URL list + semaphore defined")

    # 2. Add the combined fetcher (before the first individual fetcher).
    if "_fetch_all_places_from_overpass" in src:
        print("SKIP: combined fetcher already present")
    else:
        m = re.search(r"async def _fetch_\w+_from_overpass", src)
        if not m:
            print("ERROR: no individual fetcher found to anchor the combined fetcher.")
            sys.exit(1)
        src = src[:m.start()] + COMBINED.lstrip("\n") + src[m.start():]
        print("OK: combined fetcher added (one query for all place types)")

    # 3. Repoint all spawn triggers at the combined fetcher.
    for old, new in CALL_REPLACEMENTS:
        n = src.count(old)
        fname = old.split("create_task(")[1].split("(")[0]
        if n > 0:
            src = src.replace(old, new)
            print(f"OK: {n} trigger(s) repointed from {fname} to combined fetcher")
        else:
            print(f"SKIP: no trigger found for {fname} (already repointed?)")

    # 4. Unify all trigger keys to the shared all_<lat>_<lng> key so the
    # first spawn's combined fetch dedupes the other three.
    for old, new in KEY_REPLACEMENTS:
        n = src.count(old)
        if n > 0:
            src = src.replace(old, new)
            print(f"OK: {n} trigger key(s) unified to shared all_ key ({old})")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_COMBINED_OK")


if __name__ == "__main__":
    main()
