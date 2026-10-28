"""Street Legends backend: real-world nightclubs/bars/pubs from OpenStreetMap.
Run from repo root: python3 backend/patch-real-nightclubs.py
Idempotent - safe to re-run. Mirrors patch-real-banks.py + patch-real-banks-v2.py.

WHAT CHANGES:
1. /nightclubs/spawn no longer invents random fake clubs. It serves real
   amenity=nightclub + amenity=bar + amenity=pub locations from OpenStreetMap
   within 5 km of the player, with real names. First visit to an area triggers
   a BACKGROUND Overpass fetch (never blocks the map — same fix as banks v2);
   cached results return instantly, 7-day area cache.
2. /nightclubs/{nightclub_id}/visit now requires the player's stored GPS
   position to be within 100 m of the club.

FALLBACKS: if Overpass is unreachable, whatever clubs are already cached in the
DB are returned (possibly empty). If a player has no stored position, the visit
is allowed (edge case - the game normally always stores one).
Works whether or not patch-real-banks-v2.py was applied (adds asyncio import
and the _osm_fetching set if missing).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

HELPER = '''
async def _fetch_nightclubs_from_overpass(latitude: float, longitude: float, player_level: int, area_key: str):
    """Background fill of real nightclubs/bars/pubs for an area. Never blocks the map response."""
    try:
        query = (
            "[out:json][timeout:50];"
            "("
            f'node["amenity"="nightclub"](around:5000,{latitude},{longitude});'
            f'way["amenity"="nightclub"](around:5000,{latitude},{longitude});'
            f'node["amenity"="bar"](around:5000,{latitude},{longitude});'
            f'way["amenity"="bar"](around:5000,{latitude},{longitude});'
            f'node["amenity"="pub"](around:5000,{latitude},{longitude});'
            f'way["amenity"="pub"](around:5000,{latitude},{longitude});'
            ");"
            "out center 100;"
        )
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={"data": query},
                headers={"User-Agent": "StreetLegends/1.0 (game nightclub lookup)"},
            )
        if resp.status_code == 200:
            elements = resp.json().get("elements", [])
            for el in elements:
                osm_id = f"{el.get('type')}/{el.get('id')}"
                tags = el.get("tags", {}) or {}
                if el.get("type") == "node":
                    clat, clng = el.get("lat"), el.get("lon")
                else:
                    center = el.get("center") or {}
                    clat, clng = center.get("lat"), center.get("lon")
                if clat is None or clng is None:
                    continue
                name = tags.get("name") or tags.get("brand") or "Nightclub"
                existing = await db.nightclubs.find_one({"osm_id": osm_id})
                if existing:
                    continue
                nightclub = {
                    "id": str(uuid.uuid4()),
                    "osm_id": osm_id,
                    "name": name,
                    "icon": "🎵",
                    "latitude": clat,
                    "longitude": clng,
                    "energy_percent": 25,
                    "source": "osm",
                    "created_at": datetime.utcnow().isoformat(),
                }
                await db.nightclubs.insert_one(nightclub)
            await db.nightclub_fetches.insert_one({
                "latitude": latitude,
                "longitude": longitude,
                "fetched_at": datetime.utcnow().isoformat(),
            })
    except Exception as e:
        logging.warning(f"Overpass nightclub fetch failed: {e}")
    finally:
        _osm_fetching.discard(area_key)

'''

NEW_SPAWN = '''@api_router.get("/nightclubs/spawn")
async def spawn_nightclubs(latitude: float, longitude: float, player_level: int = 1):
    """Real nightclubs/bars/pubs from OpenStreetMap near the player — visit only when physically near."""
    RADIUS_M = 5000  # 5 km search radius
    CACHE_DAYS = 7
    # Bounding box for the DB lookup (approx, 1 deg lat ~ 111 km)
    dlat = RADIUS_M / 111000.0
    dlng = RADIUS_M / (111000.0 * max(0.2, math.cos(math.radians(latitude))))

    # Area cache check: was this area fetched recently? (within 2 km, last 7 days)
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_DAYS)).isoformat()
    recent = await db.nightclub_fetches.find_one({
        "latitude": {"$gte": latitude - 0.02, "$lte": latitude + 0.02},
        "longitude": {"$gte": longitude - 0.02, "$lte": longitude + 0.02},
        "fetched_at": {"$gte": cutoff},
    })
    if not recent:
        # Fetch real clubs in the BACKGROUND — never block the map on Overpass
        area_key = f"club_{round(latitude, 2)}_{round(longitude, 2)}"
        if area_key not in _osm_fetching:
            _osm_fetching.add(area_key)
            asyncio.create_task(_fetch_nightclubs_from_overpass(latitude, longitude, player_level, area_key))

    # Return real clubs in the DB within the radius (instant, possibly empty on first visit)
    nightclubs = await db.nightclubs.find({
        "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
        "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
    }).to_list(100)
    for nc in nightclubs:
        nc.pop("_id", None)
    return nightclubs
'''

VISIT_ANCHOR = '''    nightclub = await db.nightclubs.find_one({"id": nightclub_id})
    if not nightclub:
        raise HTTPException(status_code=404, detail="Nightclub not found")
'''
VISIT_NEW = '''    nightclub = await db.nightclubs.find_one({"id": nightclub_id})
    if not nightclub:
        raise HTTPException(status_code=404, detail="Nightclub not found")

    # Real-world proximity: you must be physically at the club to party there
    player_pos = player.get("position")
    if player_pos and player_pos.get("latitude") is not None:
        dist_m = calculate_distance(
            Position(latitude=player_pos["latitude"], longitude=player_pos["longitude"]),
            Position(latitude=nightclub["latitude"], longitude=nightclub["longitude"]),
        )
        if dist_m > 100:
            raise HTTPException(
                status_code=400,
                detail=f"You're {int(dist_m)}m away — get within 100m of {nightclub['name']} to party there!",
            )
'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    # 1. asyncio import (if v2 wasn't applied yet)
    if "import asyncio" not in src:
        anchor = "import uuid\n"
        if src.count(anchor) != 1:
            print("ERROR: uuid import anchor not found. Aborting.")
            sys.exit(1)
        src = src.replace(anchor, anchor + "import asyncio\n", 1)
        print("OK: added import asyncio")

    # 2. _osm_fetching set (if v2 wasn't applied yet)
    if "_osm_fetching = set()" not in src:
        marker = '@api_router.get("/nightclubs/spawn")'
        if src.count(marker) != 1:
            print("ERROR: nightclubs spawn marker not found. Aborting.")
            sys.exit(1)
        src = src.replace(marker, "# In-flight Overpass fetches (dedupe so a driving player doesn't spam Overpass)\n_osm_fetching = set()\n\n" + marker, 1)
        print("OK: added _osm_fetching set")

    # 3. Helper + spawn replacement
    start_marker = '@api_router.get("/nightclubs/spawn")'
    end_marker = '@api_router.post("/nightclubs/{nightclub_id}/visit")'
    if "_fetch_nightclubs_from_overpass" in src and "nightclub_fetches" in src:
        print("SKIP: real-nightclub spawn already installed")
    else:
        s = src.find(start_marker)
        e = src.find(end_marker)
        if s == -1 or e == -1 or e <= s:
            print("ERROR: could not locate spawn_nightclubs function. Aborting.")
            sys.exit(1)
        src = src[:s] + HELPER + NEW_SPAWN + "\n\n" + src[e:]
        print("OK: /nightclubs/spawn now serves real OpenStreetMap clubs/bars/pubs (5 km, background fetch)")

    # 4. Proximity check in visit_nightclub
    if "to party there" in src:
        print("SKIP: visit proximity check already installed")
    else:
        if src.count(VISIT_ANCHOR) != 1:
            print(f"ERROR: visit anchor matched {src.count(VISIT_ANCHOR)}x. Aborting.")
            sys.exit(1)
        src = src.replace(VISIT_ANCHOR, VISIT_NEW, 1)
        print("OK: /nightclubs visit now requires being within 100m of the club")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_NIGHTCLUBS_OK")


if __name__ == "__main__":
    main()
