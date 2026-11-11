#!/usr/bin/env python3
"""Street Legends backend: Stash Box (house Utilities).

User spec (2026-11-06, preview approved, "Wire it to the house
inventory"): a wooden chest in the house inventory under Utilities,
$5,000 buy / $2,500 sell. Tap it and it opens 20 slots, 3 free,
$5,000 PER slot to unlock the other 17 ($85k total). Holds the 5
fiend/enemy-drop items ONLY (Grass $100, Pills $200, Rock Candy $300,
Flake $400, Brown Sugar $500 per oz). Each slot holds a stack of ONE
item type. Deposit from the player inventory, withdraw back. STORE
buttons on the 5 item rows ask HOW MANY first (frontend).

HOUSE FULL — READ THIS: his Luxury Mansion is 6/6 full. The Stash Box
is a UTILITY and must NOT count toward the 6-item limit and must NOT
be blocked by a full house. The dedicated buy endpoint below NEVER
checks the house item_limit and NEVER touches house.items — ownership
is a separate `stash_box: true` flag on the house doc plus a doc in
the `stash_boxes` collection. The generic items/add endpoint is
guarded to REJECT stash-box so it can never enter the counted items
list; the generic items/remove endpoint is guarded so a sell can
never drop stashed items (sell goes through /stash-box/sell, which
returns every stashed item to the inventory first).

What this patch does (run order: this patch, then Publish, then the
frontend patch):
  1. "stash-box" entry in HOUSE_ITEM_CATALOG (category "utilities",
     price 5000) — same place radio/TV registered. The catalog entry
     alone never places the box: the generic add/remove endpoints
     below reject it.
  2. GET /stash-box?player_id= — {owned, unlocked, unlocked_count,
     slots, slot_count}. owned=false + defaults when never bought.
  3. POST /stash-box/buy?player_id= — needs an owned house (any
     tier); cash >= $5,000; not already owned (re-buy is a no-op,
     no double charge). Deducts $5,000, creates the box doc
     (unlocked [0,1,2], empty slots), sets house stash_box flag.
     NO item_limit check, NO house.items touch — works on a full 6/6.
  4. POST /stash-box/sell?player_id= — needs owned; FIRST returns
     every stashed item to the player inventory, then refunds $2,500,
     deletes the box doc, clears the house flag. Never deletes items.
  5. POST /stash-box/unlock?player_id=&slot= — slot 3..19 only
     (0-2 are free and already open); cash >= $5,000; deducts;
     unlock is per-slot (stored as a list); re-unlocking an open
     slot charges NOTHING and returns current state.
  6. POST /stash-box/deposit?player_id=&slot=&item=&qty= — box
     owned; slot unlocked; qty >= 1; player holds >= qty; slot
     empty OR holds the same item (different item -> 400, nothing
     moves). Only the 5 item ids accepted. Moves inventory -> slot.
  7. POST /stash-box/withdraw?player_id=&slot=&qty= — box owned;
     slot holds an item; 1 <= qty <= stored. Moves slot ->
     inventory; the slot entry is deleted when qty reaches 0.
  All failures are HTTP 400 with a plain message and NOTHING moves.
  Cash never goes below $0 (every deduction is cash-checked first).

Run:  python3 backend/patch-stash-box.py
   or:  python3 backend/patch-stash-box.py /path/to/app
Idempotent: rerun prints ALREADY_APPLIED per part, files unchanged.
"""
import re
import sys
import py_compile
import tempfile
import os
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SERVER = ROOT / "backend" / "server.py"

STASH_BOX_PRICE = 5000
STASH_BOX_SELL = 2500
STASH_SLOT_PRICE = 5000
STASH_SLOT_COUNT = 20
STASH_FREE_SLOTS = [0, 1, 2]

STASH_CODE = '''
# ============== STASH BOX ==============
# Stash Box (house Utilities, $5,000 buy / $2,500 sell): 20 slots, 3 free,
# $5,000 per extra slot. Holds the 5 enemy-drop items only, one item type
# per slot (stacks). A UTILITY: never counts toward the house item_limit
# and buying it is never blocked by a full house - the dedicated buy
# endpoint below never checks the limit and never touches house.items.
STASH_BOX_PRICE = 5000
STASH_BOX_SELL = 2500
STASH_SLOT_PRICE = 5000
STASH_SLOT_COUNT = 20
STASH_FREE_SLOTS = [0, 1, 2]
STASH_ITEM_IDS = ["grass", "pills", "rock_candy", "flake", "brown_sugar"]
STASH_ITEM_NAMES = {
    "grass": "Grass",
    "pills": "Pills",
    "rock_candy": "Rock Candy",
    "flake": "Flake",
    "brown_sugar": "Brown Sugar",
}


def _stash_qty(inv, item_id):
    """Oz of item_id in a stacked inventory (dicts or bare strings)."""
    for _it in inv:
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            return _it.get("qty", 1)
        if isinstance(_it, str) and _it == item_id:
            return 1
    return 0


def _stash_deduct(inv, item_id, qty):
    """Deduct qty oz of item_id from inv in place."""
    for _i, _it in enumerate(inv):
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            have = _it.get("qty", 1)
            if have <= qty:
                inv.pop(_i)
            else:
                inv[_i]["qty"] = have - qty
            return
        if isinstance(_it, str) and _it == item_id:
            inv.pop(_i)
            return


def _stash_add(inv, item_id, qty):
    """Add qty oz of item_id to inv in place (stacks onto an entry)."""
    for _i, _it in enumerate(inv):
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            inv[_i]["qty"] = _it.get("qty", 1) + qty
            return
        if isinstance(_it, str) and _it == item_id:
            inv[_i] = {"item_id": item_id, "qty": 1 + qty}
            return
    inv.append({"item_id": item_id, "qty": qty})


async def _stash_player_house(player_id):
    """The player's house (any tier), preferring one that is not stored."""
    houses = await db.houses.find({"player_id": player_id}).to_list(10)
    for _h in houses:
        if not _h.get("stored"):
            return _h
    return houses[0] if houses else None


def _stash_box_state(box):
    unlocked = sorted(box.get("unlocked", list(STASH_FREE_SLOTS)))
    return {
        "owned": True,
        "house_id": box.get("house_id"),
        "unlocked": unlocked,
        "unlocked_count": len(unlocked),
        "slots": box.get("slots", {}) or {},
        "slot_count": STASH_SLOT_COUNT,
    }


def _stash_box_empty_state():
    return {
        "owned": False,
        "unlocked": list(STASH_FREE_SLOTS),
        "unlocked_count": len(STASH_FREE_SLOTS),
        "slots": {},
        "slot_count": STASH_SLOT_COUNT,
    }


@api_router.get("/stash-box")
async def stash_box_get(player_id: str = ""):
    """Stash Box state: {owned, unlocked, unlocked_count, slots, slot_count}."""
    box = await db.stash_boxes.find_one({"player_id": player_id}) if player_id else None
    if not box or not box.get("owned"):
        return _stash_box_empty_state()
    return _stash_box_state(box)


@api_router.post("/stash-box/buy")
async def stash_box_buy(player_id: str):
    """Buy the Stash Box for $5,000. Works on a FULL house: no item_limit
    check, no house.items touch - ownership is a house-doc flag + a
    stash_boxes doc. Re-buy is a no-op (no double charge)."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    house = await _stash_player_house(player_id)
    if not house:
        raise HTTPException(status_code=400, detail="You need a house first - buy one from the shop")
    box = await db.stash_boxes.find_one({"player_id": player_id})
    if box and box.get("owned"):
        return {"box": _stash_box_state(box), "cash": player.get("cash", 0), "message": "You already own the Stash Box."}
    if player.get("cash", 0) < STASH_BOX_PRICE:
        raise HTTPException(status_code=400, detail=f"Not enough cash - the Stash Box costs ${STASH_BOX_PRICE:,}")
    new_cash = player.get("cash", 0) - STASH_BOX_PRICE
    await db.players.update_one({"id": player_id}, {"$set": {"cash": new_cash}})
    if box:
        await db.stash_boxes.update_one(
            {"player_id": player_id},
            {"$set": {"house_id": house.get("id"), "owned": True}},
        )
        box = await db.stash_boxes.find_one({"player_id": player_id})
    else:
        box = {
            "id": "stash_" + player_id,
            "player_id": player_id,
            "house_id": house.get("id"),
            "owned": True,
            "unlocked": list(STASH_FREE_SLOTS),
            "slots": {},
        }
        await db.stash_boxes.insert_one(box)
    await db.houses.update_one({"id": house.get("id")}, {"$set": {"stash_box": True}})
    return {"box": _stash_box_state(box), "cash": new_cash, "message": "Stash Box bought! 3 slots open - unlock more for $5,000 each."}


@api_router.post("/stash-box/sell")
async def stash_box_sell(player_id: str):
    """Sell the Stash Box for $2,500. FIRST returns every stashed item to
    the player inventory, then refunds - stashed items are never deleted."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    box = await db.stash_boxes.find_one({"player_id": player_id})
    if not box or not box.get("owned"):
        raise HTTPException(status_code=400, detail="You don't own a Stash Box")
    inv = player.get("inventory", []) or []
    returned = []
    total_oz = 0
    for _slot_key in sorted(box.get("slots", {}) or {}):
        _entry = box["slots"][_slot_key]
        _stash_add(inv, _entry["item"], _entry["qty"])
        returned.append({"item_id": _entry["item"], "name": STASH_ITEM_NAMES.get(_entry["item"], _entry["item"]), "qty": _entry["qty"]})
        total_oz += _entry["qty"]
    new_cash = player.get("cash", 0) + STASH_BOX_SELL
    await db.players.update_one({"id": player_id}, {"$set": {"cash": new_cash, "inventory": inv}})
    await db.stash_boxes.delete_one({"player_id": player_id})
    if box.get("house_id"):
        await db.houses.update_one({"id": box.get("house_id")}, {"$unset": {"stash_box": ""}})
    return {
        "box": _stash_box_empty_state(),
        "cash": new_cash,
        "returned": returned,
        "message": f"Stash Box sold for ${STASH_BOX_SELL:,} - {total_oz} oz returned to your inventory.",
    }


@api_router.post("/stash-box/unlock")
async def stash_box_unlock(player_id: str, slot: int):
    """Unlock one slot for $5,000. Slots 0-2 are free (already open).
    Re-unlocking an open slot charges NOTHING and returns current state."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    box = await db.stash_boxes.find_one({"player_id": player_id})
    if not box or not box.get("owned"):
        raise HTTPException(status_code=400, detail="You don't own a Stash Box")
    if slot < 0 or slot >= STASH_SLOT_COUNT:
        raise HTTPException(status_code=400, detail="Slot must be 0-19")
    unlocked = list(box.get("unlocked", list(STASH_FREE_SLOTS)))
    if slot in unlocked:
        return {"box": _stash_box_state(box), "cash": player.get("cash", 0), "message": "That slot is already open."}
    if player.get("cash", 0) < STASH_SLOT_PRICE:
        raise HTTPException(status_code=400, detail=f"Not enough cash - unlocking a slot costs ${STASH_SLOT_PRICE:,}")
    new_cash = player.get("cash", 0) - STASH_SLOT_PRICE
    unlocked.append(slot)
    unlocked.sort()
    await db.players.update_one({"id": player_id}, {"$set": {"cash": new_cash}})
    await db.stash_boxes.update_one({"player_id": player_id}, {"$set": {"unlocked": unlocked}})
    box["unlocked"] = unlocked
    return {"box": _stash_box_state(box), "cash": new_cash, "message": f"Slot {slot + 1} unlocked!"}


@api_router.post("/stash-box/deposit")
async def stash_box_deposit(player_id: str, slot: int, item: str = "", qty: int = 1):
    """Store qty oz of one of the 5 items in a slot. The slot must be
    unlocked, and either empty or already holding the SAME item (a
    different item -> 400, nothing moves)."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    box = await db.stash_boxes.find_one({"player_id": player_id})
    if not box or not box.get("owned"):
        raise HTTPException(status_code=400, detail="You don't own a Stash Box")
    if item not in STASH_ITEM_IDS:
        raise HTTPException(status_code=400, detail="That item can't go in the Stash Box")
    if slot < 0 or slot >= STASH_SLOT_COUNT:
        raise HTTPException(status_code=400, detail="Slot must be 0-19")
    if slot not in box.get("unlocked", list(STASH_FREE_SLOTS)):
        raise HTTPException(status_code=400, detail="That slot is locked - unlock it for $5,000 first")
    if qty < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1")
    inv = player.get("inventory", []) or []
    held = _stash_qty(inv, item)
    if held < qty:
        raise HTTPException(status_code=400, detail=f"Not enough {STASH_ITEM_NAMES[item]} - you hold {held} oz")
    slots = dict(box.get("slots", {}) or {})
    entry = slots.get(str(slot))
    if entry and entry.get("item") != item:
        raise HTTPException(status_code=400, detail=f"That slot already holds {STASH_ITEM_NAMES.get(entry.get('item'), entry.get('item'))} - pick another slot")
    _stash_deduct(inv, item, qty)
    if entry:
        entry["qty"] = entry.get("qty", 0) + qty
    else:
        slots[str(slot)] = {"item": item, "qty": qty}
    await db.players.update_one({"id": player_id}, {"$set": {"inventory": inv}})
    await db.stash_boxes.update_one({"player_id": player_id}, {"$set": {"slots": slots}})
    box["slots"] = slots
    return {"box": _stash_box_state(box), "cash": player.get("cash", 0), "message": f"Stored {qty} oz {STASH_ITEM_NAMES[item]} in slot {slot + 1}."}


@api_router.post("/stash-box/withdraw")
async def stash_box_withdraw(player_id: str, slot: int, qty: int = 1):
    """Take qty oz out of a slot, back to the inventory. The slot entry
    is deleted when qty reaches 0."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    box = await db.stash_boxes.find_one({"player_id": player_id})
    if not box or not box.get("owned"):
        raise HTTPException(status_code=400, detail="You don't own a Stash Box")
    if slot < 0 or slot >= STASH_SLOT_COUNT:
        raise HTTPException(status_code=400, detail="Slot must be 0-19")
    slots = dict(box.get("slots", {}) or {})
    entry = slots.get(str(slot))
    if not entry:
        raise HTTPException(status_code=400, detail="That slot is empty")
    stored = entry.get("qty", 0)
    if qty < 1 or qty > stored:
        raise HTTPException(status_code=400, detail=f"You only have {stored} oz in that slot")
    inv = player.get("inventory", []) or []
    _stash_add(inv, entry["item"], qty)
    entry["qty"] = stored - qty
    if entry["qty"] <= 0:
        del slots[str(slot)]
    await db.players.update_one({"id": player_id}, {"$set": {"inventory": inv}})
    await db.stash_boxes.update_one({"player_id": player_id}, {"$set": {"slots": slots}})
    box["slots"] = slots
    return {"box": _stash_box_state(box), "cash": player.get("cash", 0), "message": f"Took {qty} oz {STASH_ITEM_NAMES.get(entry['item'], entry['item'])} out of slot {slot + 1}."}

'''

CATALOG_ENTRY = '"stash-box": {"name": "Stash Box", "category": "utilities", "price": 5000},'
ADD_GUARD = '''    if item_id == "stash-box":
        raise HTTPException(status_code=400, detail="The Stash Box is bought from House > Utilities - it never counts toward the 6 item slots.")'''
REMOVE_GUARD = '''    if item_id == "stash-box":
        raise HTTPException(status_code=400, detail="Sell the Stash Box from inside it - stashed items return to your inventory first.")'''


def delta(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"), s.count("["), s.count("]"))


def main():
    landed = []
    warned = []
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - Stash Box NOT added")
        return
    src = SERVER.read_text(errors="ignore")
    orig = src
    d0 = delta(src)

    # --- Part 1: stash endpoints + helpers (before the missions/active anchor) ---
    if "def stash_box_buy" in src and "def stash_box_deposit" in src and "def stash_box_withdraw" in src:
        print("STASH_BOX_ROUTES_ALREADY_APPLIED")
        landed.append("routes")
    else:
        anchor = '@api_router.get("/missions/active/{player_id}")'
        if anchor in src:
            src = src.replace(anchor, STASH_CODE.strip("\n") + "\n\n\n" + anchor, 1)
            print("STASH_BOX_ROUTES_OK")
            landed.append("routes")
        else:
            print("WARNING: missions/active anchor not found - Stash Box routes NOT added")
            warned.append("routes")

    # --- Part 2: catalog entry (same place radio/TV registered) ---
    if '"stash-box"' in src:
        print("STASH_BOX_CATALOG_ALREADY_APPLIED")
        landed.append("catalog")
    else:
        m2 = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
        if not m2:
            print("WARNING: HOUSE_ITEM_CATALOG not found - Stash Box catalog entry NOT added")
            warned.append("catalog")
        else:
            anchor = None
            for key in ("tv", "radio", "texas_holdem", "chess_checkers", "scrabble", "dominoes", "cardtable", "dartboard", "pool-table"):
                anchor = re.search(r'\n(\s*)"' + key + r'":\s*\{[^}]*\},', src[m2.end():])
                if anchor:
                    break
            if anchor:
                indent = anchor.group(1)
                ins_at = m2.end() + anchor.end()
                src = src[:ins_at] + "\n" + indent + CATALOG_ENTRY + src[ins_at:]
                print("STASH_BOX_CATALOG_OK")
                landed.append("catalog")
            else:
                print("WARNING: no catalog entry anchor found - Stash Box catalog entry NOT added")
                warned.append("catalog")

    # --- Part 3: generic items/add must reject stash-box (never counted) ---
    if ADD_GUARD in src:
        print("STASH_BOX_ADD_GUARD_ALREADY_APPLIED")
        landed.append("add-guard")
    else:
        add_anchor = ('    if item_id not in HOUSE_ITEM_CATALOG:\n'
                      '        raise HTTPException(status_code=400, detail="Unknown item")')
        if src.count(add_anchor) == 1:
            src = src.replace(add_anchor, add_anchor + "\n" + ADD_GUARD, 1)
            print("STASH_BOX_ADD_GUARD_OK")
            landed.append("add-guard")
        else:
            print(f"WARNING: generic add anchor matched {src.count(add_anchor)}x - add guard NOT added (stash-box could enter the counted items list)")
            warned.append("add-guard")

    # --- Part 4: generic items/remove must reject stash-box (sell returns items first) ---
    if REMOVE_GUARD in src:
        print("STASH_BOX_REMOVE_GUARD_ALREADY_APPLIED")
        landed.append("remove-guard")
    else:
        rem_anchor = '        raise HTTPException(status_code=403, detail="Only the owner can remove items")'
        if src.count(rem_anchor) == 1:
            src = src.replace(rem_anchor, rem_anchor + "\n" + REMOVE_GUARD, 1)
            print("STASH_BOX_REMOVE_GUARD_OK")
            landed.append("remove-guard")
        else:
            print(f"WARNING: generic remove anchor matched {src.count(rem_anchor)}x - remove guard NOT added (a generic sell could drop stashed items)")
            warned.append("remove-guard")

    d = delta(src)
    if (d[0] - d[1]) != (d0[0] - d0[1]) or (d[2] - d[3]) != (d0[2] - d0[3]) or (d[4] - d[5]) != (d0[4] - d0[5]):
        print("WARNING: unbalanced brackets - server.py NOT written")
        return
    if src != orig:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
        try:
            tmp.write(src)
            tmp.close()
            py_compile.compile(tmp.name, doraise=True)
        except Exception as e:
            print("WARNING: syntax check failed: %s - server.py NOT written" % e)
            return
        finally:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
        SERVER.write_text(src)
    print("NOTE: Stash Box buy does NOT check the house item_limit and does NOT touch house.items - it works on a full 6/6 house.")
    if warned:
        print("STASH_BOX_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warned) + ")")
    else:
        print("STASH_BOX_OK")


if __name__ == "__main__":
    main()
