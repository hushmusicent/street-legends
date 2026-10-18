"""Street Legends - God Potion (Infinite Health + Infinite Energy, 1 hour, $1 IAP).
Run from repo root: python3 patch-god-potion.py
Idempotent - safe to re-run. Aborts on anchor mismatch.

Adds:
- GOD_POTION_PRODUCT_ID = "god_potion_1h" ($1.00, 3600s)
- helpers: _godmode_active(), _godmode_remaining()
- POST /api/iap/grant-godmode  {player_id, product_id, purchase_token?}
- GET  /api/players/{player_id}/godmode
- battle_action respects infinite health/energy

REAL-MONEY NOTE: Play policy requires the $1 charge to go through
Google Play Billing, not a custom card charge. This patch grants the
buff; the frontend must launch the Play billing flow for product
"god_potion_1h" and then call grant-godmode with the purchase token.
Server-side token verification with the Play Developer API is a TODO.
"""
import sys
import py_compile

PATH = "backend/server.py"
MARKER = "# === GOD_POTION_IAP_v1 ==="

GOD_CODE = '''
# === GOD_POTION_IAP_v1 ===
# Infinite Health + Infinite Energy potion - 1 hour - $1 real money (via Play Billing)
GOD_POTION_PRODUCT_ID = "god_potion_1h"
GOD_POTION_DURATION_SECONDS = 3600
GOD_POTION_PRICE_USD = 1.00

class GodPotionGrant(BaseModel):
    player_id: str
    product_id: str
    purchase_token: Optional[str] = None

def _godmode_active(player: dict, kind: str) -> bool:
    """kind: 'infinite_health' or 'infinite_energy' - checks expiry."""
    try:
        god = player.get("godmode", {}) or {}
        until_str = god.get(kind + "_until")
        if not until_str:
            return False
        until = datetime.fromisoformat(until_str)
        return datetime.utcnow() < until
    except Exception:
        return False

def _godmode_remaining(player: dict) -> dict:
    """Returns remaining seconds for each godmode buff."""
    out = {"infinite_health": 0, "infinite_energy": 0}
    try:
        god = player.get("godmode", {}) or {}
        now = datetime.utcnow()
        for kind in ("infinite_health", "infinite_energy"):
            until_str = god.get(kind + "_until")
            if until_str:
                until = datetime.fromisoformat(until_str)
                rem = int((until - now).total_seconds())
                out[kind] = max(0, rem)
    except Exception:
        pass
    return out

@api_router.post("/iap/grant-godmode")
async def iap_grant_godmode(data: GodPotionGrant):
    """Grant 1-hour infinite health+energy after a $1 Play Billing purchase.

    Frontend flow:
      1. Launch Google Play Billing for product "god_potion_1h" ($1.00).
      2. On success, POST here with player_id, product_id, purchase_token.
    TODO (production): verify purchase_token with Google Play Developer API
    (purchases.products.get) before granting. Do NOT grant on product_id alone
    in production - this endpoint currently trusts the caller for testing.
    """
    if data.product_id != GOD_POTION_PRODUCT_ID:
        raise HTTPException(status_code=400, detail=f"Unknown product: {data.product_id}")
    player = await db.players.find_one({"id": data.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    # TODO: verify data.purchase_token with Play Developer API here.
    # For now we log it for audit.
    now = datetime.utcnow()
    until = now + timedelta(seconds=GOD_POTION_DURATION_SECONDS)
    until_str = until.isoformat()
    await db.players.update_one(
        {"id": data.player_id},
        {"$set": {
            "godmode.infinite_health_until": until_str,
            "godmode.infinite_energy_until": until_str,
            "godmode.last_product_id": data.product_id,
            "godmode.last_purchase_token": data.purchase_token,
            "godmode.granted_at": now.isoformat(),
        }}
    )
    updated = await db.players.find_one({"id": data.player_id})
    remaining = _godmode_remaining(updated)
    return {
        "message": "God Potion activated! Infinite Health + Infinite Energy for 1 hour.",
        "product_id": GOD_POTION_PRODUCT_ID,
        "price_usd": GOD_POTION_PRICE_USD,
        "duration_seconds": GOD_POTION_DURATION_SECONDS,
        "expires_at": until_str,
        "remaining": remaining,
    }

@api_router.get("/players/{player_id}/godmode")
async def get_godmode_status(player_id: str):
    """Check if infinite health/energy potion is active."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    remaining = _godmode_remaining(player)
    return {
        "infinite_health_active": remaining["infinite_health"] > 0,
        "infinite_energy_active": remaining["infinite_energy"] > 0,
        "remaining_seconds": remaining,
        "product_id": GOD_POTION_PRODUCT_ID,
        "price_usd": GOD_POTION_PRICE_USD,
    }
# === END GOD_POTION_IAP_v1 ===
'''

# Battle patches: make battle_action respect godmode
BATTLE_PATCHES = [
    (
        "godmode flags in battle_action",
        '    player_health = battle["player_health"]\n    enemy_health = battle["enemy_health"]\n    player_energy = battle["player_energy"]',
        '    player_health = battle["player_health"]\n    enemy_health = battle["enemy_health"]\n    player_energy = battle["player_energy"]\n    # GOD_POTION: infinite health/energy check\n    _god_inf_health = _godmode_active(player, "infinite_health")\n    _god_inf_energy = _godmode_active(player, "infinite_energy")\n    if _god_inf_health:\n        player_health = battle.get("player_max_health", player_health)\n    if _god_inf_energy:\n        player_energy = battle.get("player_max_energy", player_energy)',
    ),
    (
        "godmode skill energy check",
        '        if skill["cost"] > player_energy:\n            raise HTTPException(status_code=400, detail="Not enough energy")\n        \n        player_energy -= skill["cost"]',
        '        if skill["cost"] > player_energy and not _god_inf_energy:\n            raise HTTPException(status_code=400, detail="Not enough energy")\n        \n        if not _god_inf_energy:\n            player_energy -= skill["cost"]\n        else:\n            player_energy = battle.get("player_max_energy", player_energy)',
    ),
    (
        "godmode enemy damage absorb",
        '            player_health -= enemy_damage',
        '            if _god_inf_health:\n                combat_log.append("🛡️ God Potion absorbs the damage! (Infinite Health)")\n            else:\n                player_health -= enemy_damage',
    ),
]

def main():
    try:
        with open(PATH) as f:
            src = f.read()
    except FileNotFoundError:
        print(f"ERROR: {PATH} not found. Run from repo root.")
        sys.exit(1)

    changed = 0

    # 1. Insert GOD_CODE before app.include_router
    if MARKER in src:
        print("SKIP: godmode API block already present")
    else:
        anchor = "app.include_router(api_router)"
        if src.count(anchor) != 1:
            print(f"ERROR: anchor '{anchor}' matched {src.count(anchor)}x. Aborting.")
            sys.exit(1)
        src = src.replace(anchor, GOD_CODE + "\n" + anchor, 1)
        changed += 1
        print("OK: godmode API block inserted")

    # 2. Battle patches
    for name, old, new in BATTLE_PATCHES:
        if new.strip() in src:
            print(f"SKIP (already applied): {name}")
            continue
        # old may appear more than once for damage line - handle carefully
        count = src.count(old)
        if name == "godmode enemy damage absorb":
            # This line appears in battle_action enemy turn; ensure single replacement in that function
            # We replace only the first occurrence inside battle_action's enemy loop
            if count < 1:
                print(f"ERROR: anchor for '{name}' not found. Aborting.")
                sys.exit(1)
            # Replace first occurrence only (battle_action is the first battle function)
            src = src.replace(old, new, 1)
            changed += 1
            print(f"OK: {name} (first occurrence)")
        else:
            if count != 1:
                print(f"ERROR: anchor for '{name}' matched {count}x. Aborting.")
                sys.exit(1)
            src = src.replace(old, new, 1)
            changed += 1
            print(f"OK: {name}")

    if changed:
        with open(PATH, "w") as f:
            f.write(src)
        print(f"\nDone. {changed} patch(es) applied.")
        try:
            py_compile.compile(PATH, doraise=True)
            print("Python syntax OK.")
        except Exception as e:
            print(f"SYNTAX WARNING: {e}")
    else:
        print("\nNothing to do - all patches already applied.")
    print("GOD_POTION_OK")

if __name__ == "__main__":
    main()
