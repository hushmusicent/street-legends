"""Street Legends backend: house visibility + items survive replacement.
Run from repo root: python3 backend/patch-house-visibility-items.py
Idempotent - safe to re-run.

USER RULES (2026-10-29):
1. A house is visible ONLY to its owner and the owner's friends.
   Strangers no longer see it on the map.
   - /houses/nearby takes an optional player_id. With it, only
     houses owned by the requester or their friends (player doc
     `friends` array) are returned.
   - Without player_id (old app versions), the old behavior is kept
     so houses don't vanish mid-transition.
   - Hide still works on top: a hidden owner's house is hidden from
     friends too (owner still sees it). Hide is a player-level flag,
     so the endpoint loads hidden owners in one query.
2. Buying a new house no longer deletes the old house's items.
   They move into the player's item inventory (player doc
   `inventory_items`, a list of item ids) and sit there until the
   player places them in a house.
   - buy_house collects items from ALL replaced houses (placed +
     stored) into inventory_items before delete_many.
   - New endpoint POST /houses/{id}/items/place-from-inventory:
     owner-only, item must be in inventory, house must have a free
     slot, item not already in the house. Moves one copy from
     inventory into the house (center position, draggable after).
     Removing exactly one copy matters when the player owns two of
     the same item, so it edits the array in Python, not $pull
     (which would remove every copy).
   - Sell is UNCHANGED (items are lost on sell) — user scoped this
     rule to buying; say so if sell should preserve items too.

BACKEND only: run + Emergent Deploy. Pair with the frontend patch
(nearby player_id + inventory rows in the interior dropdown).
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

NEARBY_SIG_OLD = "async def get_nearby_houses(latitude: float, longitude: float, radius: float = 2000):"
NEARBY_SIG_NEW = "async def get_nearby_houses(latitude: float, longitude: float, radius: float = 2000, player_id: str = None):"

VIS_BLOCK = '''    # Visibility: owner + friends only (when the requester is known).
    # No requester (old app) keeps the old behavior so houses don't
    # vanish mid-transition. Hidden owners' houses stay hidden from
    # friends (owner still sees their own).
    visible_owners = None
    hidden_owners = set()
    if player_id:
        requester = await db.players.find_one({"id": player_id})
        friend_ids = set(requester.get("friends", [])) if requester else set()
        visible_owners = friend_ids | {player_id}
        hidden_docs = await db.players.find({"hidden_from_map": True}, {"id": 1}).to_list(10000)
        hidden_owners = {d["id"] for d in hidden_docs}
'''

VIS_CHECKS = '''        if visible_owners is not None:
            if h.get("player_id") not in visible_owners:
                continue
            if h.get("player_id") in hidden_owners and h.get("player_id") != player_id:
                continue
'''

# Nearby variants: with the move-v2 stored check, or without it.
NEARBY_WITH_STORED_OLD = '''    houses = await db.houses.find().to_list(200)
    nearby = []
    for h in houses:
        if h.get("stored"):
            continue'''
NEARBY_WITH_STORED_NEW = '''    houses = await db.houses.find().to_list(200)
''' + VIS_BLOCK + '''    nearby = []
    for h in houses:
        if h.get("stored"):
            continue
''' + VIS_CHECKS

NEARBY_PLAIN_OLD = '''    houses = await db.houses.find().to_list(200)
    nearby = []
    for h in houses:'''
NEARBY_PLAIN_NEW = '''    houses = await db.houses.find().to_list(200)
''' + VIS_BLOCK + '''    nearby = []
    for h in houses:
        if h.get("stored"):
            continue
''' + VIS_CHECKS

BUY_OLD = '''    # One house only: replace any existing house.
    replaced = await db.houses.find_one({"player_id": player_id})
    await db.houses.delete_many({"player_id": player_id})'''
BUY_NEW = '''    # One house only: replace any existing house. Items in the old
    # house(s) go back into the player's item inventory instead of
    # being deleted — they sit there until placed in a new house.
    replaced = await db.houses.find_one({"player_id": player_id})
    old_houses = await db.houses.find({"player_id": player_id}).to_list(20)
    old_item_ids = []
    for oh in old_houses:
        for it in oh.get("items", []) or []:
            if it.get("item_id"):
                old_item_ids.append(it.get("item_id"))
    if old_item_ids:
        await db.players.update_one({"id": player_id}, {"$push": {"inventory_items": {"$each": old_item_ids}}})
    await db.houses.delete_many({"player_id": player_id})'''

BUY_RETURN_OLD = '''        "replaced": serialize_doc(replaced) if replaced else None,'''
BUY_RETURN_NEW = '''        "replaced": serialize_doc(replaced) if replaced else None,
        "inventory_items": updated.get("inventory_items", []),'''

BLOCK = '''
@api_router.post("/houses/{house_id}/items/place-from-inventory")
async def place_house_item_from_inventory(house_id: str, payload: dict):
    """Owner only: place an item from the player's item inventory
    into this house. Free — the item was already bought once."""
    player_id = payload.get("player_id")
    item_id = payload.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="Item required")
    house = await db.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if player_id != house.get("player_id"):
        raise HTTPException(status_code=403, detail="Only the owner can place items")
    if house.get("stored"):
        raise HTTPException(status_code=400, detail="House is in inventory - place the house first")
    player = await db.players.find_one({"id": player_id})
    if not player or item_id not in (player.get("inventory_items", []) or []):
        raise HTTPException(status_code=400, detail="Item is not in your inventory")
    items = house.get("items", []) or []
    if any(i.get("item_id") == item_id for i in items):
        raise HTTPException(status_code=400, detail="Item is already in this house")
    if len(items) >= house.get("item_limit", 6):
        raise HTTPException(status_code=400, detail="House is full")
    await db.houses.update_one({"id": house_id}, {"$push": {"items": {"item_id": item_id, "x": 0.5, "y": 0.5}}})
    inv = list(player.get("inventory_items", []) or [])
    inv.remove(item_id)
    await db.players.update_one({"id": player_id}, {"$set": {"inventory_items": inv}})
    updated_house = await db.houses.find_one({"id": house_id})
    updated_player = await db.players.find_one({"id": player_id})
    return {"house": serialize_doc(updated_house), "inventory_items": updated_player.get("inventory_items", [])}

'''
MISSION = "# ============ MISSIONS ============"


def main():
    if not SERVER.exists():
        print("ERROR: backend/server.py not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()

    # 1. Nearby signature.
    if NEARBY_SIG_NEW in src:
        print("SKIP: nearby already takes player_id")
    elif src.count(NEARBY_SIG_OLD) == 1:
        src = src.replace(NEARBY_SIG_OLD, NEARBY_SIG_NEW, 1)
        print("OK: nearby takes player_id")
    else:
        print(f"WARNING: nearby signature matched {src.count(NEARBY_SIG_OLD)}x")

    # 2. Visibility filter (either nearby variant).
    if "visible_owners" in src:
        print("SKIP: visibility filter already present")
    elif src.count(NEARBY_WITH_STORED_OLD) == 1:
        src = src.replace(NEARBY_WITH_STORED_OLD, NEARBY_WITH_STORED_NEW, 1)
        print("OK: visibility filter added (stored variant)")
    elif src.count(NEARBY_PLAIN_OLD) == 1:
        src = src.replace(NEARBY_PLAIN_OLD, NEARBY_PLAIN_NEW, 1)
        print("OK: visibility filter added (plain variant, stored check included)")
    else:
        print("WARNING: nearby body anchor not found")

    # 3. Buy moves items to inventory.
    if '"inventory_items": {"$each"' in src:
        print("SKIP: buy already preserves items")
    elif src.count(BUY_OLD) == 1:
        src = src.replace(BUY_OLD, BUY_NEW, 1)
        print("OK: buy moves old items to inventory")
    else:
        print(f"WARNING: buy anchor matched {src.count(BUY_OLD)}x")
    if BUY_RETURN_NEW in src:
        print("SKIP: buy return already has inventory_items")
    elif src.count(BUY_RETURN_OLD) == 1:
        src = src.replace(BUY_RETURN_OLD, BUY_RETURN_NEW, 1)
        print("OK: buy return includes inventory_items")
    else:
        print(f"WARNING: buy return anchor matched {src.count(BUY_RETURN_OLD)}x")

    # 4. Place-from-inventory endpoint (mission anchor, else router include).
    if "place_house_item_from_inventory" in src:
        print("SKIP: place-from-inventory endpoint already present")
    elif MISSION in src:
        src = src.replace(MISSION, BLOCK + MISSION, 1)
        print("OK: place-from-inventory endpoint added")
    else:
        m = re.search(r"^.*include_router\(api_router\).*$", src, re.MULTILINE)
        if m:
            src = src[:m.start()] + BLOCK + src[m.start():]
            print("OK: place-from-inventory endpoint added before router include")
        else:
            print("WARNING: no anchor for endpoint - other changes still saved")

    # ALWAYS write (move-v1 lesson: never exit before saving).
    SERVER.write_text(src)
    print("HOUSE_VISIBILITY_ITEMS_OK")


if __name__ == "__main__":
    main()
