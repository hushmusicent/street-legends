"""Street Legends backend: move a house into inventory, place it again.
Run from repo root: python3 backend/patch-house-move.py
Idempotent - safe to re-run.

FEATURE (user 2026-10-29):
- House popup (where Sell / Hide are) gains a MOVE option.
- Moving takes the house off the map and stores it in the player's
  inventory. It sits there until the player selects it (Shop House
  tab -> PLACE HERE), which drops it at their current position.
- The house keeps its tier, items, and item_limit while stored.

IMPLEMENTATION: one flag on the house doc, "stored": True.
- /houses/nearby skips stored houses, so a moved house vanishes
  from the map.
- /houses/player returns only the PLACED house (stored != True),
  so the Shop shows BUY cards + the inventory section, not a
  phantom "YOUR HOUSE".
- Buying still replaces everything (delete_many by player_id), so
  the one-house rule holds with stored houses too.
- Placing is refused if another house is already placed.

BACKEND only: run + Emergent Deploy.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# 1. Nearby map query: skip stored houses.
NEARBY_OLD = '''async def get_nearby_houses(latitude: float, longitude: float, radius: float = 2000):
    """Houses within radius (meters) for the map."""
    center = Position(latitude=latitude, longitude=longitude)
    houses = await db.houses.find().to_list(200)
    nearby = []
    for h in houses:'''
NEARBY_NEW = '''async def get_nearby_houses(latitude: float, longitude: float, radius: float = 2000):
    """Houses within radius (meters) for the map."""
    center = Position(latitude=latitude, longitude=longitude)
    houses = await db.houses.find().to_list(200)
    nearby = []
    for h in houses:
        if h.get("stored"):
            continue'''

# 2. Player house: placed house only.
PLAYER_OLD = '''async def get_player_house(player_id: str):
    """The player's current house, or null."""
    house = await db.houses.find_one({"player_id": player_id})'''
PLAYER_NEW = '''async def get_player_house(player_id: str):
    """The player's current house, or null."""
    house = await db.houses.find_one({"player_id": player_id, "stored": {"$ne": True}})'''

# 3. New endpoints (before the mission anchor).
BLOCK = '''
@api_router.post("/houses/{house_id}/move-to-inventory")
async def move_house_to_inventory(house_id: str, payload: dict):
    """Owner only: take the house off the map into inventory."""
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if payload.get("player_id") != house.get("player_id"):
        raise HTTPException(status_code=403, detail="Only the owner can move this house")
    await db.houses.update_one({"id": house_id}, {"$set": {"stored": True}})
    updated = await db.houses.find_one({"id": house_id})
    return {"house": serialize_doc(updated)}


@api_router.get("/houses/inventory/{player_id}")
async def get_house_inventory(player_id: str):
    """Houses the player has stored (not on the map)."""
    houses = await db.houses.find({"player_id": player_id, "stored": True}).to_list(20)
    return {"houses": [serialize_doc(h) for h in houses]}


@api_router.post("/houses/{house_id}/place")
async def place_house(house_id: str, payload: dict):
    """Owner only: drop a stored house at a new location."""
    latitude = payload.get("latitude")
    longitude = payload.get("longitude")
    if latitude is None or longitude is None:
        raise HTTPException(status_code=400, detail="Location required")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if payload.get("player_id") != house.get("player_id"):
        raise HTTPException(status_code=403, detail="Only the owner can place this house")
    if not house.get("stored"):
        raise HTTPException(status_code=400, detail="House is already placed")
    placed = await db.houses.find_one({"player_id": payload.get("player_id"), "stored": {"$ne": True}, "id": {"$ne": house_id}})
    if placed:
        raise HTTPException(status_code=400, detail="You already have a house placed - move or sell it first")
    await db.houses.update_one({"id": house_id}, {"$set": {"stored": False, "latitude": float(latitude), "longitude": float(longitude)}})
    updated = await db.houses.find_one({"id": house_id})
    return {"house": serialize_doc(updated)}

'''
MISSION = "# ============ MISSIONS ============"


def main():
    if not SERVER.exists():
        print("ERROR: backend/server.py not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    if NEARBY_NEW in src:
        print("SKIP: nearby already skips stored houses")
    elif src.count(NEARBY_OLD) == 1:
        src = src.replace(NEARBY_OLD, NEARBY_NEW, 1)
        print("OK: nearby skips stored houses")
    else:
        print(f"WARNING: nearby anchor matched {src.count(NEARBY_OLD)}x")

    if PLAYER_NEW in src:
        print("SKIP: player house already placed-only")
    elif src.count(PLAYER_OLD) == 1:
        src = src.replace(PLAYER_OLD, PLAYER_NEW, 1)
        print("OK: player house is placed-only")
    else:
        print(f"WARNING: player anchor matched {src.count(PLAYER_OLD)}x")

    if "move_house_to_inventory" in src:
        print("SKIP: move/place endpoints already present")
    elif MISSION not in src:
        print("ERROR: mission anchor not found")
        sys.exit(1)
    else:
        src = src.replace(MISSION, BLOCK + MISSION, 1)
        print("OK: move-to-inventory / inventory / place endpoints added")

    SERVER.write_text(src)
    print("HOUSE_MOVE_OK")


if __name__ == "__main__":
    main()
