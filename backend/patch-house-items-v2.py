"""Street Legends backend: house items cost money + can be moved.
Run from repo root: python3 backend/patch-house-items-v2.py
Idempotent - safe to re-run.

CHANGES (replaces v1's house-items block entirely, or inserts it if
v1 was never applied):
1. Pool Table now costs $50,000. Buying checks the player's cash and
   deducts it; returns {"house": ..., "cash": <new cash>}.
2. Items carry an x/y position (fractions 0-1 of the room image).
   New items start at center (0.5, 0.5).
3. POST /houses/{house_id}/items/move {player_id, item_id, x, y} —
   owner-only, clamps x/y to 0-1, saves the dragged position.
4. Removing an item refunds HALF its price ($25,000 for the pool
   table) — same rule as selling a house. Returns updated cash.
All endpoints stay owner-only.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

HEADER = "# ============== HOUSE ITEMS =============="
MISSION = "# ============== MISSION ENDPOINTS =============="

V2_CODE = '''# ============== HOUSE ITEMS ==============

HOUSE_ITEM_CATALOG = {
    "pool-table": {"name": "Pool Table", "category": "games", "price": 50000},
}


@api_router.post("/houses/{house_id}/items/add")
async def add_house_item(house_id: str, payload: dict):
    item_id = payload.get("item_id")
    if item_id not in HOUSE_ITEM_CATALOG:
        raise HTTPException(status_code=400, detail="Unknown item")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if payload.get("player_id") != house.get("player_id"):
        raise HTTPException(status_code=403, detail="Only the owner can buy items")
    items = house.get("items", []) or []
    if any(it.get("item_id") == item_id for it in items):
        raise HTTPException(status_code=400, detail="Item already placed")
    limit = house.get("item_limit") or HOUSE_TIERS.get(house.get("tier"), {}).get("item_limit", 2)
    if len(items) >= limit:
        raise HTTPException(status_code=400, detail="House is full")
    info = HOUSE_ITEM_CATALOG[item_id]
    price = info.get("price", 0)
    player = await db.players.find_one({"id": payload.get("player_id")})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    if player.get("cash", 0) < price:
        raise HTTPException(status_code=400, detail=f"Not enough cash — the {info['name']} costs ${price:,}")
    new_cash = player.get("cash", 0) - price
    await db.players.update_one({"id": player["id"]}, {"$set": {"cash": new_cash}})
    items.append({"item_id": item_id, "name": info["name"], "category": info["category"], "x": 0.5, "y": 0.5, "placed_at": datetime.utcnow().isoformat()})
    await db.houses.update_one({"id": house_id}, {"$set": {"items": items}})
    updated = await db.houses.find_one({"id": house_id})
    return {"house": serialize_doc(updated), "cash": new_cash}


@api_router.post("/houses/{house_id}/items/remove")
async def remove_house_item(house_id: str, payload: dict):
    item_id = payload.get("item_id")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if payload.get("player_id") != house.get("player_id"):
        raise HTTPException(status_code=403, detail="Only the owner can remove items")
    items = house.get("items", []) or []
    if not any(it.get("item_id") == item_id for it in items):
        raise HTTPException(status_code=400, detail="Item not placed")
    items = [it for it in items if it.get("item_id") != item_id]
    await db.houses.update_one({"id": house_id}, {"$set": {"items": items}})
    refund = HOUSE_ITEM_CATALOG.get(item_id, {}).get("price", 0) // 2
    player = await db.players.find_one({"id": payload.get("player_id")})
    new_cash = None
    if player and refund:
        new_cash = player.get("cash", 0) + refund
        await db.players.update_one({"id": player["id"]}, {"$set": {"cash": new_cash}})
    updated = await db.houses.find_one({"id": house_id})
    return {"house": serialize_doc(updated), "cash": new_cash}


@api_router.post("/houses/{house_id}/items/move")
async def move_house_item(house_id: str, payload: dict):
    item_id = payload.get("item_id")
    try:
        x = max(0.0, min(1.0, float(payload.get("x", 0.5))))
        y = max(0.0, min(1.0, float(payload.get("y", 0.5))))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Bad position")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if payload.get("player_id") != house.get("player_id"):
        raise HTTPException(status_code=403, detail="Only the owner can move items")
    items = house.get("items", []) or []
    found = False
    for it in items:
        if it.get("item_id") == item_id:
            it["x"] = x
            it["y"] = y
            found = True
    if not found:
        raise HTTPException(status_code=400, detail="Item not placed")
    await db.houses.update_one({"id": house_id}, {"$set": {"items": items}})
    updated = await db.houses.find_one({"id": house_id})
    return {"house": serialize_doc(updated)}


'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if '"price": 50000' in src and "/items/move" in src:
        print("SKIP: house items v2 already present")
    elif HEADER in src and MISSION in src:
        start = src.index(HEADER)
        end = src.index(MISSION)
        src = src[:start] + V2_CODE + src[end:]
        SERVER.write_text(src)
        print("OK: house items block replaced with v2 (price + move)")
    elif MISSION in src:
        src = src.replace(MISSION, V2_CODE + MISSION, 1)
        SERVER.write_text(src)
        print("OK: house items v2 inserted (v1 was absent)")
    else:
        print("ERROR: mission anchor not found")
        sys.exit(1)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("HOUSE_ITEMS_V2_OK")


if __name__ == "__main__":
    main()
