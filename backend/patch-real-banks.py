"""Street Legends backend: real-world banks from OpenStreetMap + proximity robbery.
Run from repo root: python3 backend/patch-real-banks.py
Idempotent - safe to re-run.

WHAT CHANGES:
1. /banks/spawn no longer invents random fake banks. It queries the OpenStreetMap
   Overpass API for real amenity=bank locations within 5 km of the player, caches
   them in the banks collection (7-day area cache so Overpass isn't hammered),
   and returns the real banks. Names are the real bank names (Chase, HSBC, ...).
2. /banks/{bank_id}/rob now requires the player's stored GPS position to be
   within 100 m of the bank. No more robbing from across town.

FALLBACKS: if Overpass is unreachable, whatever banks are already cached in the
DB are returned (possibly empty). If a player has no stored position, the rob
is allowed (edge case - the game normally always stores one).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

NEW_SPAWN = '''@api_router.get("/banks/spawn")
async def spawn_banks(latitude: float, longitude: float, player_level: int = 1):
    """Real banks from OpenStreetMap near the player — rob only when physically near."""
    RADIUS_M = 5000  # 5 km search radius
    CACHE_DAYS = 7
    # Bounding box for the DB lookup (approx, 1 deg lat ~ 111 km)
    dlat = RADIUS_M / 111000.0
    dlng = RADIUS_M / (111000.0 * max(0.2, math.cos(math.radians(latitude))))

    # 1. Area cache check: was this area fetched recently? (within 2 km, last 7 days)
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_DAYS)).isoformat()
    recent = await db.bank_fetches.find_one({
        "latitude": {"$gte": latitude - 0.02, "$lte": latitude + 0.02},
        "longitude": {"$gte": longitude - 0.02, "$lte": longitude + 0.02},
        "fetched_at": {"$gte": cutoff},
    })
    if not recent:
        # 2. Query Overpass for real banks around the player
        query = (
            "[out:json][timeout:50];"
            "("
            f'node["amenity"="bank"](around:{RADIUS_M},{latitude},{longitude});'
            f'way["amenity"="bank"](around:{RADIUS_M},{latitude},{longitude});'
            ");"
            "out center 100;"
        )
        try:
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
            logging.warning(f"Overpass bank fetch failed, using cache: {e}")

    # 3. Return real banks in the DB within the radius
    banks = await db.banks.find({
        "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
        "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
    }).to_list(100)
    for bank in banks:
        bank.pop("_id", None)
    return banks
'''

ROB_ANCHOR = '''    bank = await db.banks.find_one({"id": bank_id})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")
'''
ROB_NEW = '''    bank = await db.banks.find_one({"id": bank_id})
    if not bank:
        raise HTTPException(status_code=404, detail="Bank not found")

    # Real-world proximity: you must be physically at the bank to rob it
    player_pos = player.get("position")
    if player_pos and player_pos.get("latitude") is not None:
        dist_m = calculate_distance(
            Position(latitude=player_pos["latitude"], longitude=player_pos["longitude"]),
            Position(latitude=bank["latitude"], longitude=bank["longitude"]),
        )
        if dist_m > 100:
            raise HTTPException(
                status_code=400,
                detail=f"You're {int(dist_m)}m away — get within 100m of {bank['name']} to rob it!",
            )
'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    # 1. Replace spawn_banks wholesale (anchor: from its decorator to the next router)
    start_marker = '@api_router.get("/banks/spawn")'
    end_marker = '@api_router.post("/banks/{bank_id}/rob")'
    if "REAL_BANKS_OSM_OK" in src or 'source": "osm"' in src or '"source": "osm"' in src:
        print("SKIP: real-bank spawn already installed")
    else:
        s = src.find(start_marker)
        e = src.find(end_marker)
        if s == -1 or e == -1 or e <= s:
            print("ERROR: could not locate spawn_banks function. Aborting.")
            sys.exit(1)
        src = src[:s] + NEW_SPAWN + "\n\n" + src[e:]
        print("OK: /banks/spawn now serves real OpenStreetMap banks (5 km, 7-day cache)")

    # 2. Proximity check in rob_bank
    if "get within 100m of" in src:
        print("SKIP: rob proximity check already installed")
    else:
        if src.count(ROB_ANCHOR) != 1:
            print(f"ERROR: rob anchor matched {src.count(ROB_ANCHOR)}x. Aborting.")
            sys.exit(1)
        src = src.replace(ROB_ANCHOR, ROB_NEW, 1)
        print("OK: /banks rob now requires being within 100m of the bank")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_BANKS_OK")


if __name__ == "__main__":
    main()
