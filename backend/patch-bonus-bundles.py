#!/usr/bin/env python3
"""Street Legends Bonus Bundles backend (real-money IAP).

Adds the Bonus tab bundles to the backend. Same pattern as the God
Potions (POST /api/iap/grant-godmode): the app buys via Google Play
Billing, then POSTs here with player_id, product_id, purchase_token
and this endpoint grants the bundle.

Bundles (product IDs must be created in Play Console first, same as
the God Potions, before they can be bought):
  bonus_cash_100k  ($10)  : +$100,000 cash
  bonus_cash_250k  ($25)  : +$250,000 cash
  bonus_pack_500k  ($50)  : +$500,000 cash + 5 Health MK1 + 5 Energy MK1
  bonus_pack_1m    ($100) : +$1,000,000 cash + 5 Health MK1 + 5 Energy MK1
                           + 1h Infinite Health + 1h Infinite Energy

Health MK1 = full HP restore on use. Energy MK1 = full Energy restore
on use. Counts live on player.bonus_items {health_mk1, energy_mk1}.
Infinite Health/Energy reuse the God Potion 1-hour godmode buff.

Endpoints added:
  POST /api/iap/grant-bonus          {player_id, product_id, purchase_token}
  GET  /api/players/{id}/bonus-items
  POST /api/iap/use-mk1             {player_id, item: health_mk1|energy_mk1}

TODO (production): verify purchase_token with Google Play Developer API
(purchases.products.get) before granting, same as the God Potions
endpoint. This endpoint currently trusts the caller for testing.

Run from /app: python3 backend/patch-bonus-bundles.py
Idempotent: a full re-run prints BONUS_BUNDLES_ALREADY_APPLIED.
"""
import sys
from pathlib import Path

SRV = Path("backend/server.py")
MARKER = "BONUS_BUNDLES_OK"
ANCHOR = "# === END GOD_POTION_IAP_v2 ==="

NEW_CODE = '''
# === BONUS_BUNDLES_IAP ===
# Bonus tab bundles - real money via Google Play Billing.
#   bonus_cash_100k -> $100,000 cash ($10)
#   bonus_cash_250k -> $250,000 cash ($25)
#   bonus_pack_500k -> $500,000 cash + 5 Health MK1 + 5 Energy MK1 ($50)
#   bonus_pack_1m   -> $1,000,000 cash + 5 Health MK1 + 5 Energy MK1
#                      + 1h Infinite Health + 1h Infinite Energy ($100)
BONUS_BUNDLE_PRODUCTS = {
    "bonus_cash_100k": {"cash": 100000, "health_mk1": 0, "energy_mk1": 0, "god_health": False, "god_energy": False, "price_usd": 10.00},
    "bonus_cash_250k": {"cash": 250000, "health_mk1": 0, "energy_mk1": 0, "god_health": False, "god_energy": False, "price_usd": 25.00},
    "bonus_pack_500k": {"cash": 500000, "health_mk1": 5, "energy_mk1": 5, "god_health": False, "god_energy": False, "price_usd": 50.00},
    "bonus_pack_1m": {"cash": 1000000, "health_mk1": 5, "energy_mk1": 5, "god_health": True, "god_energy": True, "price_usd": 100.00},
}

class BonusGrant(BaseModel):
    player_id: str
    product_id: str
    purchase_token: str = ""

@api_router.post("/iap/grant-bonus")
async def iap_grant_bonus(data: BonusGrant):
    """Grant a Bonus bundle after a Play Billing purchase.

    Frontend flow:
      1. Launch Google Play Billing for one of the bonus_* SKUs.
      2. On success, POST here with player_id, product_id, purchase_token.
    TODO (production): verify purchase_token with Google Play Developer
    API (purchases.products.get) before granting. Do NOT grant on
    product_id alone in production - this endpoint currently trusts
    the caller for testing.
    """
    bundle = BONUS_BUNDLE_PRODUCTS.get(data.product_id)
    if not bundle:
        raise HTTPException(status_code=400, detail=f"Unknown product: {data.product_id}")
    player = await db.players.find_one({"id": data.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    # TODO: verify data.purchase_token with Play Developer API here.
    # For now we log it for audit.
    now = datetime.utcnow()
    update_ops: dict = {"$inc": {"cash": bundle["cash"]}, "$set": {}}
    if bundle["health_mk1"]:
        update_ops["$inc"]["bonus_items.health_mk1"] = bundle["health_mk1"]
    if bundle["energy_mk1"]:
        update_ops["$inc"]["bonus_items.energy_mk1"] = bundle["energy_mk1"]
    if bundle["god_health"]:
        until = (now + timedelta(seconds=GOD_POTION_DURATION_SECONDS)).isoformat()
        update_ops["$set"]["godmode.infinite_health_until"] = until
    if bundle["god_energy"]:
        until = (now + timedelta(seconds=GOD_POTION_DURATION_SECONDS)).isoformat()
        update_ops["$set"]["godmode.infinite_energy_until"] = until
    update_ops["$set"]["bonus.last_product_id"] = data.product_id
    update_ops["$set"]["bonus.last_purchase_token"] = data.purchase_token
    update_ops["$set"]["bonus.granted_at"] = now.isoformat()
    await db.players.update_one({"id": data.player_id}, update_ops)
    updated = await db.players.find_one({"id": data.player_id})
    parts = [f"${bundle['cash']:,} cash"]
    if bundle["health_mk1"]:
        parts.append(f"{bundle['health_mk1']}x Health MK1")
    if bundle["energy_mk1"]:
        parts.append(f"{bundle['energy_mk1']}x Energy MK1")
    if bundle["god_health"]:
        parts.append("Infinite Health (1h)")
    if bundle["god_energy"]:
        parts.append("Infinite Energy (1h)")
    return {
        "message": "Bonus granted! " + ", ".join(parts) + ".",
        "product_id": data.product_id,
        "price_usd": bundle["price_usd"],
        "cash": updated.get("cash", 0),
        "bonus_items": updated.get("bonus_items", {"health_mk1": 0, "energy_mk1": 0}),
    }

@api_router.get("/players/{player_id}/bonus-items")
async def get_bonus_items(player_id: str):
    """MK1 counts the player holds (for the Bonus tab)."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    b = player.get("bonus_items", {}) or {}
    return {
        "health_mk1": int(b.get("health_mk1", 0) or 0),
        "energy_mk1": int(b.get("energy_mk1", 0) or 0),
    }

class Mk1Use(BaseModel):
    player_id: str
    item: str

@api_router.post("/iap/use-mk1")
async def iap_use_mk1(data: Mk1Use):
    """Use one MK1 item: full HP restore (health_mk1) or full Energy
    restore (energy_mk1). Decrements the held count by 1."""
    if data.item not in ("health_mk1", "energy_mk1"):
        raise HTTPException(status_code=400, detail=f"Unknown item: {data.item}")
    player = await db.players.find_one({"id": data.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    b = player.get("bonus_items", {}) or {}
    count = int(b.get(data.item, 0) or 0)
    if count <= 0:
        raise HTTPException(status_code=400, detail=f"No {data.item.replace('_', ' ').title()} left")
    stats = player.get("stats", {}) or {}
    if data.item == "health_mk1":
        max_hp = stats.get("max_health", 100)
        await db.players.update_one(
            {"id": data.player_id},
            {"$inc": {"bonus_items.health_mk1": -1}, "$set": {"stats.health": max_hp}},
        )
        return {"message": "Health MK1 used! HP fully restored.", "health_mk1": count - 1}
    max_en = stats.get("max_energy", 100)
    await db.players.update_one(
        {"id": data.player_id},
        {"$inc": {"bonus_items.energy_mk1": -1}, "$set": {"stats.energy": max_en}},
    )
    return {"message": "Energy MK1 used! Energy fully restored.", "energy_mk1": count - 1}
# === END BONUS_BUNDLES_IAP ===
'''

def main():
    if not SRV.exists():
        print("ERROR: backend/server.py not found (run from /app)")
        sys.exit(1)
    src = SRV.read_text()
    if "BONUS_BUNDLES_IAP" in src:
        print("BONUS_BUNDLES_ALREADY_APPLIED")
        return
    if ANCHOR not in src:
        print("ERROR: God Potion anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src.replace(ANCHOR, ANCHOR + NEW_CODE, 1)
    SRV.write_text(src)
    cur = SRV.read_text()
    if "BONUS_BUNDLES_IAP" not in cur or "/iap/grant-bonus" not in cur:
        print("ERROR: Bonus Bundles patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
