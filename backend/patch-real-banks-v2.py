"""Street Legends backend: non-blocking real banks + restaurants (driving fix).
Run from repo root: python3 backend/patch-real-banks-v2.py
Idempotent - safe to re-run. Requires patch-real-banks.py + patch-real-restaurants.py.

PROBLEM: /banks/spawn and /restaurants/spawn wait on the Overpass API (30-60s
on first visit to an area). The map query waits for ALL 14 entity calls, so one
slow Overpass call freezes the whole map — worst while driving, when every new
500m grid cell triggers a refetch.

FIX: the Overpass fetch moves to a background asyncio task. The spawn endpoint
returns whatever is already cached INSTANTLY (possibly empty on a first visit),
and the background task fills the cache. Banks/restaurants then appear on the
next map refresh instead of stalling the map. An in-flight set dedupes fetches
so a driving player doesn't spam Overpass.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

BANK_HELPER = '''
# In-flight Overpass fetches (dedupe so a driving player doesn't spam Overpass)
_osm_fetching = set()

async def _fetch_banks_from_overpass(latitude: float, longitude: float, player_level: int, area_key: str):
    """Background fill of real banks for an area. Never blocks the map response."""
    try:
        query = (
            "[out:json][timeout:50];"
            "("
            f'node["amenity"="bank"](around:5000,{latitude},{longitude});'
            f'way["amenity"="bank"](around:5000,{latitude},{longitude});'
            ");"
            "out center 100;"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"User-Agent": "StreetLegends/1.0 (game bank lookup)"},
            )
        if resp.status_code == 200:
            elements = resp.json().get("elements", [])
            base_reward = int((500 + (player_level * 100)) * 0.5)
            for el in elements:
                osm_id = f"{el.get('type')}/{el.get('id')}"
                tags = el.get("tags", {}) or {}
                if el.get("type") == "node":
                    blat, blng = el.get("lat"), el.get("lon")
                else:
                    center = el.get("center") or {}
                    blat, blng = center.get("lat"), center.get("lon")
                if blat is None or blng is None:
                    continue
                name = tags.get("name") or tags.get("brand") or "Bank"
                existing = await db.banks.find_one({"osm_id": osm_id})
                if existing:
                    continue
                bank = {
                    "id": str(uuid.uuid4()),
                    "osm_id": osm_id,
                    "name": name,
                    "icon": "🏦",
                    "latitude": blat,
                    "longitude": blng,
                    "min_reward": int(base_reward * 0.5),
                    "max_reward": int(base_reward * 1.5),
                    "source": "osm",
                    "created_at": datetime.utcnow().isoformat(),
                }
                await db.banks.insert_one(bank)
            await db.bank_fetches.insert_one({
                "latitude": latitude,
                "longitude": longitude,
                "fetched_at": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        logging.warning(f"Overpass bank fetch failed: {e}")
    finally:
        _osm_fetching.discard(area_key)

'''

RESTAURANT_HELPER = '''
async def _fetch_restaurants_from_overpass(latitude: float, longitude: float, player_level: int, area_key: str):
    """Background fill of real restaurants for an area. Never blocks the map response."""
    try:
        query = (
            "[out:json][timeout:50];"
            "("
            f'node["amenity"="restaurant"](around:5000,{latitude},{longitude});'
            f'way["amenity"="restaurant"](around:5000,{latitude},{longitude});'
            f'node["amenity"="fast_food"](around:5000,{latitude},{longitude});'
            f'way["amenity"="fast_food"](around:5000,{latitude},{longitude});'
            ");"
            "out center 100;"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"User-Agent": "StreetLegends/1.0 (game restaurant lookup)"},
            )
        if resp.status_code == 200:
            elements = resp.json().get("elements", [])
            for el in elements:
                osm_id = f"{el.get('type')}/{el.get('id')}"
                tags = el.get("tags", {}) or {}
                if el.get("type") == "node":
                    rlat, rlng = el.get("lat"), el.get("lon")
                else:
                    center = el.get("center") or {}
                    rlat, rlng = center.get("lat"), center.get("lon")
                if rlat is None or rlng is None:
                    continue
                name = tags.get("name") or tags.get("brand") or "Restaurant"
                existing = await db.restaurants.find_one({"osm_id": osm_id})
                if existing:
                    continue
                restaurant = {
                    "id": str(uuid.uuid4()),
                    "osm_id": osm_id,
                    "name": name,
                    "icon": "🍔",
                    "latitude": rlat,
                    "longitude": rlng,
                    "heal_percent": 25,
                    "source": "osm",
                    "created_at": datetime.utcnow().isoformat(),
                }
                await db.restaurants.insert_one(restaurant)
            await db.restaurant_fetches.insert_one({
                "latitude": latitude,
                "longitude": longitude,
                "fetched_at": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        logging.warning(f"Overpass restaurant fetch failed: {e}")
    finally:
        _osm_fetching.discard(area_key)

'''

BANK_TRIGGER = '''    if not recent:
        # 2. Fetch real banks in the BACKGROUND — never block the map on Overpass
        area_key = f"bank_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_banks_from_overpass(latitude, longitude, player_level, area_key))
'''

RESTAURANT_TRIGGER = '''    if not recent:
        # 2. Fetch real restaurants in the BACKGROUND — never block the map on Overpass
        area_key = f"rest_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_restaurants_from_overpass(latitude, longitude, player_level, area_key))
'''


def replace_block(src, entity, singular):
    """Replace the synchronous `if not recent:` Overpass block for one entity.
    Comment uses the plural (banks/restaurants), warning message the singular."""
    pattern = re.compile(
        r"    if not recent:\n"
        r"        # 2\. Query Overpass for real " + entity + r" around the player\n"
        r".*?"
        r"logging\.warning\(f\"Overpass " + singular + r" fetch failed, using cache: \{e\}\"\)\n",
        re.DOTALL,
    )
    m = pattern.search(src)
    if not m:
        return src, False
    trigger = BANK_TRIGGER if entity == "banks" else RESTAURANT_TRIGGER
    return src[: m.start()] + trigger + src[m.end():], True


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "bank_fetches" not in src or "restaurant_fetches" not in src:
        print("ERROR: patch-real-banks.py + patch-real-restaurants.py must be applied first.")
        sys.exit(1)

    # 1. asyncio import
    if "import asyncio" not in src:
        anchor = "import uuid\n"
        if src.count(anchor) != 1:
            print("ERROR: uuid import anchor not found. Aborting.")
            sys.exit(1)
        src = src.replace(anchor, anchor + "import asyncio\n", 1)
        print("OK: added import asyncio")

    # 2. Helpers before the banks spawn decorator
    if "_fetch_banks_from_overpass" not in src:
        marker = '@api_router.get("/banks/spawn")'
        if src.count(marker) != 1:
            print("ERROR: banks spawn marker not found. Aborting.")
            sys.exit(1)
        src = src.replace(marker, BANK_HELPER + marker, 1)
        print("OK: added background bank fetch helper")
    else:
        print("SKIP: bank helper already present")
    if "_fetch_restaurants_from_overpass" not in src:
        marker = '@api_router.get("/restaurants/spawn")'
        if src.count(marker) != 1:
            print("ERROR: restaurants spawn marker not found. Aborting.")
            sys.exit(1)
        src = src.replace(marker, RESTAURANT_HELPER + marker, 1)
        print("OK: added background restaurant fetch helper")
    else:
        print("SKIP: restaurant helper already present")

    # 3. Swap the blocking blocks for background triggers
    src, changed_b = replace_block(src, "banks", "bank")
    print("OK: banks spawn now returns cache instantly, fetches in background" if changed_b else "SKIP: banks spawn already non-blocking")
    src, changed_r = replace_block(src, "restaurants", "restaurant")
    print("OK: restaurants spawn now returns cache instantly, fetches in background" if changed_r else "SKIP: restaurants spawn already non-blocking")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_BANKS_V2_OK")


if __name__ == "__main__":
    main()
