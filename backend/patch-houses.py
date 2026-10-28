"""Street Legends backend: player houses.
Run from repo root: python3 backend/patch-houses.py
Idempotent - safe to re-run.

FEATURE:
- 3 houses: Street Apartment $100,000 / Country Cabin $500,000 /
  Luxury Mansion $1,000,000. One house per player; buying a new one
  replaces the old one (frontend shows the warning + Are You Sure).
- House is placed at the player's location at purchase time and shows
  as a house icon on the map.
- Owner actions (via the house icon): Enter (client shows the house
  picture), Hide (player disappears from other players' maps), Sell
  (refunds HALF the price paid).
- Houses live in a `houses` collection; hide is a `hidden_from_map`
  flag on the player doc, respected by /players/nearby.
- Interior items (furniture) come later: the house doc carries an
  `items` list (empty for now) so furniture can attach without a
  migration.

ENDPOINTS:
  POST /api/houses/buy            {player_id, tier, latitude, longitude}
  GET  /api/houses/player/{player_id}
  GET  /api/houses/nearby?latitude=&longitude=&radius=
  POST /api/houses/{house_id}/toggle-hide  {player_id}
  POST /api/houses/{house_id}/sell         {player_id}
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

HOUSE_TIERS = '''# ============== PLAYER HOUSES ==============
HOUSE_TIERS = {
    "apartment": {"name": "Street Apartment", "price": 100000, "image": "house-apartment"},
    "cabin": {"name": "Country Cabin", "price": 500000, "image": "house-cabin"},
    "mansion": {"name": "Luxury Mansion", "price": 1000000, "image": "house-mansion"},
}

'''

HOUSE_ENDPOINTS = '''# ============== HOUSE ENDPOINTS ==============
@api_router.post("/houses/buy")
async def buy_house(data: dict):
    """Buy a house at the player's current location. One house per
    player — buying a new one replaces the old one."""
    player_id = data.get("player_id")
    tier = data.get("tier")
    latitude = data.get("latitude")
    longitude = data.get("longitude")
    if tier not in HOUSE_TIERS:
        raise HTTPException(status_code=400, detail="Invalid house tier")
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Location required")
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    tier_info = HOUSE_TIERS[tier]
    price = tier_info["price"]
    if player.get("cash", 0) < price:
        raise HTTPException(status_code=400, detail="Not enough cash")
    # One house only: replace any existing house.
    replaced = await db.houses.find_one({"player_id": player_id})
    await db.houses.delete_many({"player_id": player_id})
    await db.players.update_one(
        {"id": player_id},
        {"$inc": {"cash": -price}, "$set": {"hidden_from_map": False}},
    )
    house = {
        "id": str(uuid.uuid4()),
        "player_id": player_id,
        "player_name": player.get("name", "Player"),
        "tier": tier,
        "name": tier_info["name"],
        "price": price,
        "image": tier_info["image"],
        "latitude": float(latitude),
        "longitude": float(longitude),
        "items": [],
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.houses.insert_one(house)
    updated = await db.players.find_one({"id": player_id})
    return {
        "house": serialize_doc(house),
        "cash": updated.get("cash", 0),
        "replaced": serialize_doc(replaced) if replaced else None,
    }


@api_router.get("/houses/player/{player_id}")
async def get_player_house(player_id: str):
    """The player's current house, or null."""
    house = await db.houses.find_one({"player_id": player_id})
    return {"house": serialize_doc(house) if house else None}


@api_router.get("/houses/nearby")
async def get_nearby_houses(latitude: float, longitude: float, radius: float = 2000):
    """Houses within radius (meters) for the map."""
    center = Position(latitude=latitude, longitude=longitude)
    houses = await db.houses.find().to_list(200)
    nearby = []
    for h in houses:
        try:
            d = calculate_distance(center, Position(latitude=h["latitude"], longitude=h["longitude"]))
        except Exception:
            continue
        if d <= radius:
            doc = serialize_doc(h)
            doc["distance"] = round(d)
            nearby.append(doc)
    nearby.sort(key=lambda x: x["distance"])
    return nearby


@api_router.post("/houses/{house_id}/toggle-hide")
async def toggle_house_hide(house_id: str, data: dict):
    """Hide / unhide the player from other players' maps. Only the
    owner can toggle it."""
    player_id = data.get("player_id")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if house.get("player_id") != player_id:
        raise HTTPException(status_code=403, detail="Not your house")
    player = await db.players.find_one({"id": player_id})
    new_hidden = not player.get("hidden_from_map", False)
    await db.players.update_one({"id": player_id}, {"$set": {"hidden_from_map": new_hidden}})
    return {"hidden": new_hidden}


@api_router.post("/houses/{house_id}/sell")
async def sell_house(house_id: str, data: dict):
    """Sell for HALF the price paid. Only the owner can sell."""
    player_id = data.get("player_id")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if house.get("player_id") != player_id:
        raise HTTPException(status_code=403, detail="Not your house")
    refund = int(house.get("price", 0) // 2)
    await db.houses.delete_one({"id": house_id})
    await db.players.update_one(
        {"id": player_id},
        {"$inc": {"cash": refund}, "$set": {"hidden_from_map": False}},
    )
    updated = await db.players.find_one({"id": player_id})
    return {"refund": refund, "cash": updated.get("cash", 0)}


'''

# In /players/nearby, hidden players must not appear on others' maps.
NEARBY_OLD = '''            # Must have been active in last 30 minutes
            "last_active": {"$gte": inactivity_threshold}'''
NEARBY_NEW = '''            # Must have been active in last 30 minutes
            "last_active": {"$gte": inactivity_threshold},
            # Hidden players (via Hide on their house) don't appear
            "hidden_from_map": {"$ne": True}'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    if "HOUSE_TIERS" not in src:
        anchor = "# ============== MISSION ENDPOINTS =============="
        if anchor not in src:
            print("ERROR: MISSION ENDPOINTS anchor not found.")
            sys.exit(1)
        src = src.replace(anchor, HOUSE_TIERS + HOUSE_ENDPOINTS + anchor, 1)
        print("OK: house tiers + endpoints added")
    else:
        print("SKIP: house endpoints already present")

    if '"hidden_from_map": {"$ne": True}' not in src:
        if src.count(NEARBY_OLD) == 1:
            src = src.replace(NEARBY_OLD, NEARBY_NEW, 1)
            print("OK: nearby-players now excludes hidden players")
        else:
            print(f"WARNING: nearby-players anchor matched {src.count(NEARBY_OLD)}x — skipping hide filter")
    else:
        print("SKIP: nearby-players hide filter already present")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("HOUSES_OK")


if __name__ == "__main__":
    main()
