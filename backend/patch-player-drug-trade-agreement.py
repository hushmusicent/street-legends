#!/usr/bin/env python3
"""Two-step drug trade: BOTH players must agree before a trade completes.

User (2026-11-12): "both players have to agree with the trade before it's
complete."

The v1 trade (POST /api/trade/drugs) executed instantly. Now a trade is a
proposal: player A proposes (SELL: "I sell you X oz of Y for $Z" or BUY:
"I buy X oz of Y from you for $Z"), player B must ACCEPT before anything
moves. Decline or cancel moves nothing. Accept re-validates RIGHT THEN that
the seller still holds >= qty oz and the buyer still has >= qty x regular
price cash — either side may have spent or sold since the proposal. If
validation fails at accept time the offer is voided and nothing moves.
Offers expire after 10 minutes.

Adds (backend/server.py), all under db.trade_offers:
  POST /api/trade/drugs/propose  body {proposer_id, other_id, item_id, qty, direction}
       direction "sell" = proposer sells to other; "buy" = proposer buys
       from other. Validates item, qty 1-10, two different existing players,
       seller holds >= qty oz, buyer has >= total cash. Creates a pending
       offer. Moves NOTHING. -> the offer (with a plain summary).
  GET  /api/trade/drugs/pending/{player_id}
       -> {incoming: [...], outgoing: [...]} — incoming = pending offers
       the player must answer; outgoing = offers they proposed. Only
       pending offers; stale (>10 min) ones are marked expired and excluded.
  POST /api/trade/drugs/respond  body {offer_id, player_id, accept}
       Only the NON-proposer party may respond (proposer gets 400).
       accept=false -> "declined", nothing moves. accept=true -> re-validate
       seller oz + buyer cash right now; on failure the offer is voided
       ("expired") with a 400 and nothing moves; on success the SAME
       transfer as v1 executes and the offer is "accepted".
  POST /api/trade/drugs/cancel  body {offer_id, player_id}
       Only the proposer may cancel a pending offer -> "cancelled".

The v1 direct endpoint POST /api/trade/drugs is left untouched (the app
just stops calling it directly).

Requires the v1 trade patch (patch-player-drug-trade.py) to have run first
— it reuses _trade_inventory_qty, _trade_deduct, _pharmacy_add and
FIEND_ITEM_PRICES.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: TRADE_AGREEMENT_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

ANCHOR = "# PARK_NEARBY: real parks from OpenStreetMap."

BLOCK = '''# TRADE_AGREEMENT: two-step drug trade — a proposal must be ACCEPTED by the
# other player before anything moves. Offers live in db.trade_offers and
# expire after 10 minutes. The v1 direct POST /api/trade/drugs stays as-is
# (the app no longer calls it directly).
TRADE_OFFER_TTL_SECONDS = 600


def _trade_offer_age_seconds(offer):
    """Seconds since the offer was created (huge number if unparseable)."""
    try:
        created = datetime.fromisoformat(str(offer.get("created_at", "")))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - created).total_seconds()
    except Exception:
        return 10 ** 9


def _trade_offer_public(offer, viewer_id):
    """Offer shaped for the API: the other player's name + a plain summary
    written from the viewer's side of the deal."""
    proposer_id = offer.get("proposer_id")
    other_id = offer.get("other_id")
    viewer_is_proposer = viewer_id == proposer_id
    other_player_id = other_id if viewer_is_proposer else proposer_id
    other_name = offer.get("other_name") if viewer_is_proposer else offer.get("proposer_name")
    viewer_is_buyer = viewer_id == offer.get("buyer_id")
    item_id = offer.get("item_id")
    name, _regular, _fiend = FIEND_ITEM_PRICES.get(item_id, (item_id, offer.get("unit_price", 0), 0))
    qty = offer.get("qty", 0)
    total = offer.get("total", 0)
    if viewer_is_buyer:
        summary = f"{other_name} wants to sell you {qty} oz of {name} for ${total}"
    else:
        summary = f"{other_name} wants to buy {qty} oz of {name} from you for ${total}"
    return {
        "offer_id": offer.get("offer_id"),
        "seller_id": offer.get("seller_id"),
        "buyer_id": offer.get("buyer_id"),
        "proposer_id": proposer_id,
        "other_id": other_player_id,
        "other_name": other_name,
        "item_id": item_id,
        "item_name": name,
        "qty": qty,
        "unit_price": offer.get("unit_price", 0),
        "total": total,
        "viewer_role": "buyer" if viewer_is_buyer else "seller",
        "summary": summary,
        "status": offer.get("status"),
        "created_at": offer.get("created_at"),
    }


async def _trade_offer_expire_stale(offer):
    """Mark a pending offer expired if it is older than the TTL. True if expired."""
    if offer.get("status") == "pending" and _trade_offer_age_seconds(offer) > TRADE_OFFER_TTL_SECONDS:
        await db.trade_offers.update_one({"offer_id": offer.get("offer_id")}, {"$set": {"status": "expired"}})
        return True
    return False


@api_router.post("/trade/drugs/propose")
async def propose_trade_drugs(data: dict):
    """Propose a trade. Nothing moves — the other player must accept first."""
    proposer_id = data.get("proposer_id")
    other_id = data.get("other_id")
    item_id = data.get("item_id")
    qty = data.get("qty", 1)
    direction = data.get("direction")
    if item_id not in FIEND_ITEM_IDS:
        raise HTTPException(status_code=400, detail="Unknown item_id - only grass, pills, rock_candy, flake, brown_sugar can be traded")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1 or qty > 10:
        raise HTTPException(status_code=400, detail="Quantity must be an integer from 1 to 10 oz")
    if direction not in ("sell", "buy"):
        raise HTTPException(status_code=400, detail="direction must be 'sell' or 'buy'")
    if not proposer_id or not other_id or proposer_id == other_id:
        raise HTTPException(status_code=400, detail="proposer_id and other_id must be two different players")
    proposer = await db.players.find_one({"id": proposer_id})
    if not proposer:
        raise HTTPException(status_code=404, detail="Proposer not found")
    other = await db.players.find_one({"id": other_id})
    if not other:
        raise HTTPException(status_code=404, detail="Other player not found")
    if direction == "sell":
        seller_id, buyer_id = proposer_id, other_id
        seller, buyer = proposer, other
    else:
        seller_id, buyer_id = other_id, proposer_id
        seller, buyer = other, proposer
    name, regular_price, _fiend_price = FIEND_ITEM_PRICES[item_id]
    held = _trade_inventory_qty(seller.get("inventory", []), item_id)
    if held < qty:
        raise HTTPException(status_code=400, detail=f"Seller only holds {held} oz of {name} - need {qty} oz")
    total = regular_price * qty
    if buyer.get("cash", 0) < total:
        raise HTTPException(status_code=400, detail=f"Buyer needs ${total} cash for {qty} oz of {name}")
    offer = {
        "offer_id": str(uuid.uuid4()),
        "seller_id": seller_id,
        "buyer_id": buyer_id,
        "proposer_id": proposer_id,
        "proposer_name": proposer.get("name", "a player"),
        "other_id": other_id,
        "other_name": other.get("name", "a player"),
        "item_id": item_id,
        "qty": qty,
        "unit_price": regular_price,
        "total": total,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.trade_offers.insert_one(offer)
    return _trade_offer_public(offer, proposer_id)


@api_router.get("/trade/drugs/pending/{player_id}")
async def get_pending_trade_offers(player_id: str):
    """Pending offers for a player: incoming (they must answer) + outgoing."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    offers = await db.trade_offers.find({"status": "pending"}).to_list(200)
    incoming = []
    outgoing = []
    for offer in offers:
        if player_id not in (offer.get("seller_id"), offer.get("buyer_id")):
            continue
        if await _trade_offer_expire_stale(offer):
            continue
        public = _trade_offer_public(offer, player_id)
        if offer.get("proposer_id") == player_id:
            outgoing.append(public)
        else:
            incoming.append(public)
    return {"incoming": incoming, "outgoing": outgoing}


@api_router.post("/trade/drugs/respond")
async def respond_trade_drugs(data: dict):
    """Accept or decline an offer. Only the NON-proposer party may respond.
    Accept re-validates seller oz + buyer cash right now, then executes."""
    offer_id = data.get("offer_id")
    player_id = data.get("player_id")
    accept = data.get("accept")
    if not isinstance(accept, bool):
        raise HTTPException(status_code=400, detail="accept must be true or false")
    offer = await db.trade_offers.find_one({"offer_id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Offer is " + str(offer.get("status")) + " - no longer pending")
    if await _trade_offer_expire_stale(offer):
        raise HTTPException(status_code=400, detail="Offer expired - it was over 10 minutes old")
    if player_id == offer.get("proposer_id"):
        raise HTTPException(status_code=400, detail="The proposer cannot accept their own offer - the other player must answer")
    if player_id not in (offer.get("seller_id"), offer.get("buyer_id")):
        raise HTTPException(status_code=400, detail="You are not a party to this offer")
    if not accept:
        await db.trade_offers.update_one({"offer_id": offer_id}, {"$set": {"status": "declined"}})
        return {"ok": True, "status": "declined", "offer_id": offer_id}
    # Accept: re-validate RIGHT NOW, then execute the same transfer as v1.
    seller_id = offer.get("seller_id")
    buyer_id = offer.get("buyer_id")
    item_id = offer.get("item_id")
    qty = offer.get("qty")
    seller = await db.players.find_one({"id": seller_id})
    if not seller:
        raise HTTPException(status_code=404, detail="Seller not found")
    buyer = await db.players.find_one({"id": buyer_id})
    if not buyer:
        raise HTTPException(status_code=404, detail="Buyer not found")
    name, regular_price, _fiend_price = FIEND_ITEM_PRICES[item_id]
    held = _trade_inventory_qty(seller.get("inventory", []), item_id)
    if held < qty:
        await db.trade_offers.update_one({"offer_id": offer_id}, {"$set": {"status": "expired"}})
        raise HTTPException(status_code=400, detail=f"Offer void - seller only holds {held} oz of {name} now")
    total = regular_price * qty
    if buyer.get("cash", 0) < total:
        await db.trade_offers.update_one({"offer_id": offer_id}, {"$set": {"status": "expired"}})
        raise HTTPException(status_code=400, detail=f"Offer void - buyer only has ${buyer.get('cash', 0)} cash now, needs ${total}")
    seller_inv = seller.get("inventory", [])
    _trade_deduct(seller_inv, item_id, qty)
    buyer_inv = buyer.get("inventory", [])
    _pharmacy_add(buyer_inv, item_id, qty)
    await db.players.update_one({"id": seller_id}, {"$set": {"inventory": seller_inv}, "$inc": {"cash": total}})
    await db.players.update_one({"id": buyer_id}, {"$set": {"inventory": buyer_inv}, "$inc": {"cash": -total}})
    await db.trade_offers.update_one({"offer_id": offer_id}, {"$set": {"status": "accepted"}})
    return {
        "ok": True, "status": "accepted",
        "item_id": item_id, "name": name, "qty": qty,
        "unit_price": regular_price, "total": total,
        "seller_cash": seller.get("cash", 0) + total,
        "buyer_cash": buyer.get("cash", 0) - total,
        "message": f"Traded {qty} oz of {name} for ${total}",
    }


@api_router.post("/trade/drugs/cancel")
async def cancel_trade_drugs(data: dict):
    """Cancel my own pending offer. Only the proposer may cancel."""
    offer_id = data.get("offer_id")
    player_id = data.get("player_id")
    offer = await db.trade_offers.find_one({"offer_id": offer_id})
    if not offer:
        raise HTTPException(status_code=404, detail="Offer not found")
    if offer.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Offer is " + str(offer.get("status")) + " - no longer pending")
    if player_id != offer.get("proposer_id"):
        raise HTTPException(status_code=400, detail="Only the proposer can cancel this offer")
    await db.trade_offers.update_one({"offer_id": offer_id}, {"$set": {"status": "cancelled"}})
    return {"ok": True, "status": "cancelled", "offer_id": offer_id}


'''


def main():
    if not SERVER.exists():
        print("TRADE_AGREEMENT_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if "async def propose_trade_drugs(" in src and "async def respond_trade_drugs(" in src and "async def cancel_trade_drugs(" in src and "async def get_pending_trade_offers(" in src:
        print("TRADE_AGREEMENT_ALREADY_APPLIED")
        return 0
    if "async def trade_drugs(" not in src or "def _trade_inventory_qty(" not in src:
        print("TRADE_AGREEMENT_FAIL v1 trade patch not present — run patch-player-drug-trade.py first")
        return 1
    if ANCHOR not in src:
        print("TRADE_AGREEMENT_FAIL anchor not found (file may have changed)")
        return 1
    src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
    for needle in (
        "async def propose_trade_drugs(",
        "async def get_pending_trade_offers(",
        "async def respond_trade_drugs(",
        "async def cancel_trade_drugs(",
        "def _trade_offer_public(",
        "def _trade_offer_age_seconds(",
        "TRADE_OFFER_TTL_SECONDS = 600",
    ):
        if needle not in src:
            print("TRADE_AGREEMENT_FAIL missing after edit: %s" % needle)
            return 1
    SERVER.write_text(src, encoding="utf-8")
    print("TRADE_AGREEMENT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
