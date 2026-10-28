"""Street Legends backend: gun/general shops placed at real stores + gas stations.
Run from repo root: python3 backend/patch-real-shops.py
Idempotent - safe to re-run. Mirrors patch-real-nightclubs.py.

WHAT CHANGES:
1. /shops/spawn no longer drops shops at random offsets. It anchors them to real
   OpenStreetMap locations: any shop=* store plus amenity=fuel gas stations
   within 5 km of the player, with the real store names (Walmart, Shell, ...).
   First visit to an area triggers a BACKGROUND Overpass fetch (never blocks
   the map); cached locations return instantly, 7-day area cache. If no real
   locations are cached yet (first visit, fetch still running), it falls back
   to the old random offsets so shops still appear.
2. Shop types, stock, prices, and gun-shop skills are UNCHANGED — only the
   positions (and names, when a real location is used) change.
3. NOTE: /shops/buy takes no shop id, so no proximity check is added here —
   that would need a frontend change to pass the shop being bought from.

FALLBACKS: if Overpass is unreachable, cached locations are used (possibly
none → random offsets). Works whether or not patch-real-banks-v2.py was
applied (adds asyncio import and the _osm_fetching set if missing).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

HELPER = '''
async def _fetch_stores_from_overpass(latitude: float, longitude: float, player_level: int, area_key: str):
    """Background fill of real stores + gas stations for an area. Never blocks the map response."""
    try:
        query = (
            "[out:json][timeout:50];"
            "("
            f'node["shop"](around:5000,{latitude},{longitude});'
            f'way["shop"](around:5000,{latitude},{longitude});'
            f'node["amenity"="fuel"](around:5000,{latitude},{longitude});'
            f'way["amenity"="fuel"](around:5000,{latitude},{longitude});'
            ");"
            "out center 100;"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"User-Agent": "StreetLegends/1.0 (game shop lookup)"},
            )
        if resp.status_code == 200:
            elements = resp.json().get("elements", [])
            for el in elements:
                osm_id = f"{el.get('type')}/{el.get('id')}"
                tags = el.get("tags", {}) or {}
                if el.get("type") == "node":
                    slat, slng = el.get("lat"), el.get("lon")
                else:
                    center = el.get("center") or {}
                    slat, slng = center.get("lat"), center.get("lon")
                if slat is None or slng is None:
                    continue
                name = tags.get("name") or tags.get("brand") or "Store"
                existing = await db.store_locations.find_one({"osm_id": osm_id})
                if existing:
                    continue
                await db.store_locations.insert_one({
                    "id": str(uuid.uuid4()),
                    "osm_id": osm_id,
                    "name": name,
                    "latitude": slat,
                    "longitude": slng,
                    "source": "osm",
                    "created_at": datetime.utcnow().isoformat(),
                })
            await db.store_fetches.insert_one({
                "latitude": latitude,
                "longitude": longitude,
                "fetched_at": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        logging.warning(f"Overpass store fetch failed: {e}")
    finally:
        _osm_fetching.discard(area_key)

'''

# Replace the position-picking part of spawn_shops: real locations first, random fallback.
OLD_POS = '''    for i in range(num_shops):
        # Random offset within ~500m
        lat_offset = random.uniform(-0.004, 0.004)
        lng_offset = random.uniform(-0.004, 0.004)
        
        shop_type = shop_types_to_spawn[i] if i < len(shop_types_to_spawn) else random.choice(list(SHOP_TYPES.keys()))
        shop_config = SHOP_TYPES[shop_type]
        shop_name = random.choice(SHOP_NAMES)
'''
NEW_POS = '''    # Real store/gas-station locations (background-filled cache) — fall back to
    # random offsets when the area hasn't been fetched yet.
    dlat = 5000 / 111000.0
    dlng = 5000 / (111000.0 * max(0.2, math.cos(math.radians(latitude))))
    cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
    recent_store_fetch = await db.store_fetches.find_one({
        "latitude": {"$gte": latitude - 0.02, "$lte": latitude + 0.02},
        "longitude": {"$gte": longitude - 0.02, "$lte": longitude + 0.02},
        "fetched_at": {"$gte": cutoff},
    })
    if not recent_store_fetch:
        store_area_key = f"store_{round(latitude, 2)}_{round(longitude, 2)}"
        if store_area_key not in _osm_fetching:
            _osm_fetching.add(store_area_key)
            asyncio.create_task(_fetch_stores_from_overpass(latitude, longitude, player_level, store_area_key))
    real_locations = await db.store_locations.find({
        "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
        "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
    }).to_list(100)
    random.shuffle(real_locations)

    for i in range(num_shops):
        # Real store/gas station when available, else random offset within ~500m
        if i < len(real_locations):
            shop_lat = real_locations[i]["latitude"]
            shop_lng = real_locations[i]["longitude"]
            real_name = real_locations[i]["name"]
        else:
            shop_lat = latitude + random.uniform(-0.004, 0.004)
            shop_lng = longitude + random.uniform(-0.004, 0.004)
            real_name = None

        shop_type = shop_types_to_spawn[i] if i < len(shop_types_to_spawn) else random.choice(list(SHOP_TYPES.keys()))
        shop_config = SHOP_TYPES[shop_type]
        shop_name = real_name or random.choice(SHOP_NAMES)
'''

OLD_SHOP_DICT = '''        shop = {
            "id": str(uuid.uuid4()),
            "name": shop_name,
            "shop_type": shop_type,
            "latitude": latitude + lat_offset,
            "longitude": longitude + lng_offset,
'''
NEW_SHOP_DICT = '''        shop = {
            "id": str(uuid.uuid4()),
            "name": shop_name,
            "shop_type": shop_type,
            "latitude": shop_lat,
            "longitude": shop_lng,
'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    # 1. asyncio import (if v2/nightclubs patch wasn't applied yet)
    if "import asyncio" not in src:
        anchor = "import uuid\n"
        if src.count(anchor) != 1:
            print("ERROR: uuid import anchor not found. Aborting.")
            sys.exit(1)
        src = src.replace(anchor, anchor + "import asyncio\n", 1)
        print("OK: added import asyncio")

    # 2. _osm_fetching set (if v2/nightclubs patch wasn't applied yet)
    if "_osm_fetching = set()" not in src:
        marker = '@api_router.get("/shops/spawn")'
        if src.count(marker) != 1:
            print("ERROR: shops spawn marker not found. Aborting.")
            sys.exit(1)
        src = src.replace(marker, "# In-flight Overpass fetches (dedupe so a driving player doesn't spam Overpass)\n_osm_fetching = set()\n" + HELPER + marker, 1)
        print("OK: added _osm_fetching set + store fetch helper")
    elif "_fetch_stores_from_overpass" not in src:
        marker = '@api_router.get("/shops/spawn")'
        src = src.replace(marker, HELPER + marker, 1)
        print("OK: added store fetch helper")
    else:
        print("SKIP: store fetch helper already present")

    # 3. Position picking: real locations first, random fallback
    if "real_locations" in src and "store_fetches" in src:
        print("SKIP: real shop positions already installed")
    else:
        if src.count(OLD_POS) != 1:
            print(f"ERROR: shop position anchor matched {src.count(OLD_POS)}x. Aborting.")
            sys.exit(1)
        src = src.replace(OLD_POS, NEW_POS, 1)
        print("OK: shops now anchor to real stores/gas stations (random fallback)")

    # 4. Shop dict uses the picked coordinates
    if '"latitude": shop_lat' in src:
        print("SKIP: shop dict already uses picked coordinates")
    else:
        if src.count(OLD_SHOP_DICT) != 1:
            print(f"ERROR: shop dict anchor matched {src.count(OLD_SHOP_DICT)}x. Aborting.")
            sys.exit(1)
        src = src.replace(OLD_SHOP_DICT, NEW_SHOP_DICT, 1)
        print("OK: shop dict uses picked coordinates")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_SHOPS_OK")


if __name__ == "__main__":
    main()
