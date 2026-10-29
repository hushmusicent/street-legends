"""Street Legends backend: place/remove items in a house.
Run from repo root: python3 backend/patch-house-items.py
Idempotent - safe to re-run.

ADDS:
1. HOUSE_ITEM_CATALOG — known placeable items (starts with the pool
   table in Games; more items join the catalog in later steps).
2. POST /houses/{house_id}/items/add {player_id, item_id} — owner-only.
   Rejects unknown items, duplicates, and houses already at their
   item_limit (apartment 2 / cabin 3 / mansion 6).
3. POST /houses/{house_id}/items/remove {player_id, item_id} —
   owner-only, takes the item back out of the house.
Both return {"house": <updated house doc>}. Placement is free (no
price mechanic yet — prices can be added in a later step).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

ANCHOR = "# ============== MISSION ENDPOINTS =============="

NEW_CODE = '''# ============== HOUSE ITEMS ==============

HOUSE_ITEM_CATALOG = {
    "pool-table": {"name": "Pool Table", "category": "games"},
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
        raise HTTPException(status_code=403, detail="Only the owner can place items")
    items = house.get("items", []) or []
    if any(it.get("item_id") == item_id for it in items):
        raise HTTPException(status_code=400, detail="Item already placed")
    limit = house.get("item_limit") or HOUSE_TIERS.get(house.get("tier"), {}).get("item_limit", 2)
    if len(items) >= limit:
        raise HTTPException(status_code=400, detail="House is full")
    info = HOUSE_ITEM_CATALOG[item_id]
    items.append({"item_id": item_id, "name": info["name"], "category": info["category"], "placed_at": datetime.utcnow().isoformat()})
    await db.houses.update_one({"id": house_id}, {"$set": {"items": items}})
    updated = await db.houses.find_one({"id": house_id})
    return {"house": serialize_doc(updated)}


@api_router.post("/houses/{house_id}/items/remove")
async def remove_house_item(house_id: str, payload: dict):
    item_id = payload.get("item_id")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if payload.get("player_id") != house.get("player_id"):
        raise HTTPException(status_code=403, detail="Only the owner can remove items")
    items = [it for it in (house.get("items", []) or []) if it.get("item_id") != item_id]
    await db.houses.update_one({"id": house_id}, {"$set": {"items": items}})
    updated = await db.houses.find_one({"id": house_id})
    return {"house": serialize_doc(updated)}


'''


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "HOUSE_ITEM_CATALOG" in src:
        print("SKIP: house item endpoints already present")
    elif src.count(ANCHOR) == 1:
        src = src.replace(ANCHOR, NEW_CODE + ANCHOR, 1)
        SERVER.write_text(src)
        print("OK: house item add/remove endpoints added")
    else:
        print(f"WARNING: mission anchor matched {src.count(ANCHOR)}x")
        sys.exit(1)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("HOUSE_ITEMS_OK")


if __name__ == "__main__":
    main()
