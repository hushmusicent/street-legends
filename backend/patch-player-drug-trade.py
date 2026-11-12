#!/usr/bin/env python3
"""Player-to-player drug trading at the regular price.

User (2026-11-12): trade drugs to other players at regular price, from the
player popup on the map, with a menu showing what you have and what they
have.

Adds (backend/server.py):
  GET  /api/players/{player_id}/drugs
       -> {player_id, name, cash, drugs: [{item_id, name, qty, price}]}
       All five items, qty 0 when not held, price = regular price.
  POST /api/trade/drugs  body {seller_id, buyer_id, item_id, qty}
       One direction per call, qty 1-10 oz. Buyer pays qty x regular price
       in cash; seller receives it; oz move seller -> buyer.
       -> {ok, item_id, name, qty, unit_price, total, seller_cash, buyer_cash}

Rules: item must be one of the 5 drugs; qty integer 1-10; seller and buyer
must be two different existing players; seller must hold >= qty oz (summed
across ALL inventory entries); buyer must have cash >= qty x regular price.
Reuses FIEND_ITEM_PRICES (names + regular prices) and _pharmacy_add for the
buyer's inventory. 400s for unknown item / bad qty / same player / not
enough oz / not enough cash; 404s for unknown seller/buyer.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: TRADE_DRUGS_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

ANCHOR = "# PARK_NEARBY: real parks from OpenStreetMap."

BLOCK = '''# PLAYER_DRUG_TRADE: trade the five enemy-drop items between two players
# at the REGULAR price (same price the pharmacy charges). One direction per
# call: seller -> buyer, qty oz. Buyer pays qty x regular price in cash.
def _trade_inventory_qty(inv, item_id):
    """Total oz of item_id across ALL inventory entries."""
    total = 0
    for _it in inv:
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            total += _it.get("qty", 1)
        elif isinstance(_it, str) and _it == item_id:
            total += 1
    return total


def _trade_deduct(inv, item_id, qty):
    """Deduct qty oz of item_id across all entries, in place."""
    left = qty
    for _i in range(len(inv) - 1, -1, -1):
        if left <= 0:
            break
        _it = inv[_i]
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            have = _it.get("qty", 1)
            if have <= left:
                inv.pop(_i)
                left -= have
            else:
                inv[_i]["qty"] = have - left
                left = 0
        elif isinstance(_it, str) and _it == item_id:
            inv.pop(_i)
            left -= 1
    return qty - left


@api_router.get("/players/{player_id}/drugs")
async def get_player_drugs(player_id: str):
    """The five drug items a player holds, with oz and regular price each."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    inv = player.get("inventory", [])
    drugs = []
    for item_id in FIEND_ITEM_IDS:
        name, regular_price, _fiend_price = FIEND_ITEM_PRICES[item_id]
        drugs.append({
            "item_id": item_id,
            "name": name,
            "qty": _trade_inventory_qty(inv, item_id),
            "price": regular_price,
        })
    return {"player_id": player_id, "name": player.get("name", ""), "cash": player.get("cash", 0), "drugs": drugs}


@api_router.post("/trade/drugs")
async def trade_drugs(data: dict):
    """Trade qty oz of one drug from seller to buyer at the regular price."""
    seller_id = data.get("seller_id")
    buyer_id = data.get("buyer_id")
    item_id = data.get("item_id")
    qty = data.get("qty", 1)
    if item_id not in FIEND_ITEM_IDS:
        raise HTTPException(status_code=400, detail="Unknown item_id - only grass, pills, rock_candy, flake, brown_sugar can be traded")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1 or qty > 10:
        raise HTTPException(status_code=400, detail="Quantity must be an integer from 1 to 10 oz")
    if not seller_id or not buyer_id or seller_id == buyer_id:
        raise HTTPException(status_code=400, detail="seller_id and buyer_id must be two different players")
    seller = await db.players.find_one({"id": seller_id})
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    buyer = await db.players.find_one({"id": buyer_id})
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    name, regular_price, _fiend_price = FIEND_ITEM_PRICES[item_id]
    seller_inv = seller.get("inventory", [])
    held = _trade_inventory_qty(seller_inv, item_id)
    if held < qty:
        raise HTTPException(status_code=400, detail=f"Seller only holds {held} oz of {name} - need {qty} oz")
    total = regular_price * qty
    if buyer.get("cash", 0) < total:
        raise HTTPException(status_code=400, detail=f"Buyer needs ${total} cash for {qty} oz of {name}")
    _trade_deduct(seller_inv, item_id, qty)
    buyer_inv = buyer.get("inventory", [])
    _pharmacy_add(buyer_inv, item_id, qty)
    await db.players.update_one(
        {"id": seller_id},
        {"$set": {"inventory": seller_inv}, "$inc": {"cash": total}},
    )
    await db.players.update_one(
        {"id": buyer_id},
        {"$set": {"inventory": buyer_inv}, "$inc": {"cash": -total}},
    )
    return {
        "ok": True,
        "item_id": item_id, "name": name, "qty": qty,
        "unit_price": regular_price, "total": total,
        "seller_cash": seller.get("cash", 0) + total,
        "buyer_cash": buyer.get("cash", 0) - total,
        "message": f"Traded {qty} oz of {name} for ${total}",
    }


'''


def main():
    if not SERVER.exists():
        print("TRADE_DRUGS_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if "async def trade_drugs(" in src and "async def get_player_drugs(" in src:
        print("TRADE_DRUGS_ALREADY_APPLIED")
        return 0
    if ANCHOR not in src:
        print("TRADE_DRUGS_FAIL anchor not found (file may have changed)")
        return 1
    src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
    for needle in (
        "async def trade_drugs(",
        "async def get_player_drugs(",
        "def _trade_inventory_qty(",
        "def _trade_deduct(",
        '"id": seller_id}',
        '"id": buyer_id}',
    ):
        if needle not in src:
            print("TRADE_DRUGS_FAIL missing after edit: %s" % needle)
            return 1
    SERVER.write_text(src, encoding="utf-8")
    print("TRADE_DRUGS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
