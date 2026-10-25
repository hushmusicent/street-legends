"""Street Legends backend: real-world restaurants from OpenStreetMap + proximity eating.
Run from repo root: python3 backend/patch-real-restaurants.py
Idempotent - safe to re-run. Mirrors patch-real-banks.py.

WHAT CHANGES:
1. /restaurants/spawn no longer invents random fake restaurants. It queries the
   OpenStreetMap Overpass API for real amenity=restaurant + amenity=fast_food
   locations within 5 km of the player, caches them in the restaurants
   collection (7-day area cache), and returns the real restaurants with their
   real names (McDonald's, Olive Garden, ...).
2. /restaurants/{restaurant_id}/eat now requires the player's stored GPS
   position to be within 100 m of the restaurant.

FALLBACKS: if Overpass is unreachable, whatever restaurants are already cached
in the DB are returned (possibly empty). If a player has no stored position,
the eat is allowed (edge case - the game normally always stores one).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

NEW_SPAWN = '''@api_router.get("/restaurants/spawn")
async def spawn_restaurants(latitude: float, longitude: float, player_level: int = 1):
    """Real restaurants from OpenStreetMap near the player — eat only when physically near."""
    RADIUS_M = 5000  # 5 km search radius
    CACHE_DAYS = 7
    # Bounding box for the DB lookup (approx, 1 deg lat ~ 111 km)
    dlat = RADIUS_M / 111000.0
    dlng = RADIUS_M / (111000.0 * max(0.2, math.cos(math.radians(latitude))))

    # 1. Area cache check: was this area fetched recently? (within 2 km, last 7 days)
    cutoff = (datetime.utcnow() - timedelta(days=CACHE_DAYS)).isoformat()
    recent = await db.restaurant_fetches.find_one({
        "latitude": {"$gte": latitude - 0.02, "$lte": latitude + 0.02},
        "longitude": {"$gte": longitude - 0.02, "$lte": longitude + 0.02},
        "fetched_at": {"$gte": cutoff},
    })
    if not recent:
        # 2. Query Overpass for real restaurants around the player
        query = (
            "[out:json][timeout:50];"
            "("
            f'node["amenity"="restaurant"](around:{RADIUS_M},{latitude},{longitude});'
            f'way["amenity"="restaurant"](around:{RADIUS_M},{latitude},{longitude});'
            f'node["amenity"="fast_food"](around:{RADIUS_M},{latitude},{longitude});'
            f'way["amenity"="fast_food"](around:{RADIUS_M},{latitude},{longitude});'
            ");"
            "out center 100;"
        )
        try:
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
            logging.warning(f"Overpass restaurant fetch failed, using cache: {e}")

    # 3. Return real restaurants in the DB within the radius
    restaurants = await db.restaurants.find({
        "latitude": {"$gte": latitude - dlat, "$lte": latitude + dlat},
        "longitude": {"$gte": longitude - dlng, "$lte": longitude + dlng},
    }).to_list(100)
    for r in restaurants:
        r.pop("_id", None)
    return restaurants
'''

EAT_ANCHOR = '''    restaurant = await db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
'''
EAT_NEW = '''    restaurant = await db.restaurants.find_one({"id": restaurant_id})
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Real-world proximity: you must be physically at the restaurant to eat there
    player_pos = player.get("position")
    if player_pos and player_pos.get("latitude") is not None:
        dist_m = calculate_distance(
            Position(latitude=player_pos["latitude"], longitude=player_pos["longitude"]),
            Position(latitude=restaurant["latitude"], longitude=restaurant["longitude"]),
        )
        if dist_m > 100:
            raise HTTPException(
                status_code=400,
                detail=f"You're {int(dist_m)}m away — get within 100m of {restaurant['name']} to eat there!",
            )
'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    # 1. Replace spawn_restaurants wholesale (anchor: from its decorator to the next router)
    start_marker = '@api_router.get("/restaurants/spawn")'
    end_marker = '@api_router.post("/restaurants/{restaurant_id}/eat")'
    if '"source": "osm"' in src and "restaurant_fetches" in src:
        print("SKIP: real-restaurant spawn already installed")
    else:
        s = src.find(start_marker)
        e = src.find(end_marker)
        if s == -1 or e == -1 or e <= s:
            print("ERROR: could not locate spawn_restaurants function. Aborting.")
            sys.exit(1)
        src = src[:s] + NEW_SPAWN + "\n\n" + src[e:]
        print("OK: /restaurants/spawn now serves real OpenStreetMap restaurants (5 km, 7-day cache)")

    # 2. Proximity check in eat_at_restaurant
    if "get within 100m of" in src and "to eat there" in src:
        print("SKIP: eat proximity check already installed")
    else:
        if src.count(EAT_ANCHOR) != 1:
            print(f"ERROR: eat anchor matched {src.count(EAT_ANCHOR)}x. Aborting.")
            sys.exit(1)
        src = src.replace(EAT_ANCHOR, EAT_NEW, 1)
        print("OK: /restaurants eat now requires being within 100m of the restaurant")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_RESTAURANTS_OK")


if __name__ == "__main__":
    main()
