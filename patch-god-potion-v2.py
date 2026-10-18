"""Street Legends - God Potions v2: TWO separate potions, $1 each (real money).
- god_potion_health_1h: infinite health for 1 hour - $1
- god_potion_energy_1h: infinite energy for 1 hour - $1

Run from repo root: python3 patch-god-potion-v2.py
Idempotent - safe to re-run. Upgrades a v1 install (single combined potion)
to v2, or installs fresh. Aborts on anchor mismatch.

REAL-MONEY NOTE: Play policy requires the $1 charges to go through
Google Play Billing, not a custom card charge. This patch grants the
buffs; the frontend must launch the Play billing flow for each product
and then call grant-godmode with the purchase token.
Server-side token verification with the Play Developer API is a TODO.
"""
import sys
import py_compile

PATH = "backend/server.py"
V1_MARKER = "# === GOD_POTION_IAP_v1 ==="
V2_MARKER = "# === GOD_POTION_IAP_v2 ==="

GOD_CODE_V2 = '''
# === GOD_POTION_IAP_v2 ===
# Two separate potions - 1 hour each - $1 real money each (via Play Billing)
#   god_potion_health_1h -> infinite health
#   god_potion_energy_1h -> infinite energy
GOD_POTION_HEALTH_PRODUCT_ID = "god_potion_health_1h"
GOD_POTION_ENERGY_PRODUCT_ID = "god_potion_energy_1h"
GOD_POTION_PRODUCTS = {
    GOD_POTION_HEALTH_PRODUCT_ID: "infinite_health",
    GOD_POTION_ENERGY_PRODUCT_ID: "infinite_energy",
}
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
    """Grant 1-hour infinite health OR infinite energy after a $1 Play Billing purchase.

    Frontend flow:
      1. Launch Google Play Billing for "god_potion_health_1h" or
         "god_potion_energy_1h" ($1.00 each).
      2. On success, POST here with player_id, product_id, purchase_token.
    TODO (production): verify purchase_token with Google Play Developer API
    (purchases.products.get) before granting. Do NOT grant on product_id alone
    in production - this endpoint currently trusts the caller for testing.
    """
    buff_kind = GOD_POTION_PRODUCTS.get(data.product_id)
    if not buff_kind:
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
            f"godmode.{buff_kind}_until": until_str,
            "godmode.last_product_id": data.product_id,
            "godmode.last_purchase_token": data.purchase_token,
            "godmode.granted_at": now.isoformat(),
        }}
    )
    updated = await db.players.find_one({"id": data.player_id})
    remaining = _godmode_remaining(updated)
    return {
        "message": f"Potion activated! Infinite {buff_kind.replace('_', ' ').title()} for 1 hour.",
        "product_id": data.product_id,
        "buff_kind": buff_kind,
        "price_usd": GOD_POTION_PRICE_USD,
        "duration_seconds": GOD_POTION_DURATION_SECONDS,
        "expires_at": until_str,
        "remaining": remaining,
    }

@api_router.get("/players/{player_id}/godmode")
async def get_godmode_status(player_id: str):
    """Check if infinite health/energy potions are active."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    remaining = _godmode_remaining(player)
    return {
        "infinite_health_active": remaining["infinite_health"] > 0,
        "infinite_energy_active": remaining["infinite_energy"] > 0,
        "remaining_seconds": remaining,
        "products": {
            "infinite_health": GOD_POTION_HEALTH_PRODUCT_ID,
            "infinite_energy": GOD_POTION_ENERGY_PRODUCT_ID,
        },
        "price_usd": GOD_POTION_PRICE_USD,
    }
# === END GOD_POTION_IAP_v2 ===
'''

# v1 -> v2 upgrades (applied only when the v1 block is present)
V1_TO_V2 = [
    (
        "v2 product constants",
        '# Infinite Health + Infinite Energy potion - 1 hour - $1 real money (via Play Billing)\n'
        'GOD_POTION_PRODUCT_ID = "god_potion_1h"\n'
        'GOD_POTION_DURATION_SECONDS = 3600\n'
        'GOD_POTION_PRICE_USD = 1.00',
        '# Two separate potions - 1 hour each - $1 real money each (via Play Billing)\n'
        '#   god_potion_health_1h -> infinite health\n'
        '#   god_potion_energy_1h -> infinite energy\n'
        'GOD_POTION_HEALTH_PRODUCT_ID = "god_potion_health_1h"\n'
        'GOD_POTION_ENERGY_PRODUCT_ID = "god_potion_energy_1h"\n'
        'GOD_POTION_PRODUCTS = {\n'
        '    GOD_POTION_HEALTH_PRODUCT_ID: "infinite_health",\n'
        '    GOD_POTION_ENERGY_PRODUCT_ID: "infinite_energy",\n'
        '}\n'
        'GOD_POTION_DURATION_SECONDS = 3600\n'
        'GOD_POTION_PRICE_USD = 1.00',
    ),
    (
        "v2 grant docstring",
        '"""Grant 1-hour infinite health+energy after a $1 Play Billing purchase.\n'
        '\n'
        '    Frontend flow:\n'
        '      1. Launch Google Play Billing for product "god_potion_1h" ($1.00).\n'
        '      2. On success, POST here with player_id, product_id, purchase_token.',
        '"""Grant 1-hour infinite health OR infinite energy after a $1 Play Billing purchase.\n'
        '\n'
        '    Frontend flow:\n'
        '      1. Launch Google Play Billing for "god_potion_health_1h" or\n'
        '         "god_potion_energy_1h" ($1.00 each).\n'
        '      2. On success, POST here with player_id, product_id, purchase_token.',
    ),
    (
        "v2 grant validation",
        '    if data.product_id != GOD_POTION_PRODUCT_ID:\n'
        '        raise HTTPException(status_code=400, detail=f"Unknown product: {data.product_id}")',
        '    buff_kind = GOD_POTION_PRODUCTS.get(data.product_id)\n'
        '    if not buff_kind:\n'
        '        raise HTTPException(status_code=400, detail=f"Unknown product: {data.product_id}")',
    ),
    (
        "v2 grant single buff",
        '{"$set": {\n'
        '            "godmode.infinite_health_until": until_str,\n'
        '            "godmode.infinite_energy_until": until_str,\n'
        '            "godmode.last_product_id": data.product_id,',
        '{"$set": {\n'
        '            f"godmode.{buff_kind}_until": until_str,\n'
        '            "godmode.last_product_id": data.product_id,',
    ),
    (
        "v2 grant response",
        '        "message": "God Potion activated! Infinite Health + Infinite Energy for 1 hour.",\n'
        '        "product_id": GOD_POTION_PRODUCT_ID,',
        '        "message": f"Potion activated! Infinite {buff_kind.replace(\'_\', \' \').title()} for 1 hour.",\n'
        '        "product_id": data.product_id,\n'
        '        "buff_kind": buff_kind,',
    ),
    (
        "v2 status products",
        '        "remaining_seconds": remaining,\n'
        '        "product_id": GOD_POTION_PRODUCT_ID,\n'
        '        "price_usd": GOD_POTION_PRICE_USD,\n'
        '    }\n'
        '# === END GOD_POTION_IAP_v1 ===',
        '        "remaining_seconds": remaining,\n'
        '        "products": {\n'
        '            "infinite_health": GOD_POTION_HEALTH_PRODUCT_ID,\n'
        '            "infinite_energy": GOD_POTION_ENERGY_PRODUCT_ID,\n'
        '        },\n'
        '        "price_usd": GOD_POTION_PRICE_USD,\n'
        '    }\n'
        '# === END GOD_POTION_IAP_v2 ===',
    ),
    (
        "v2 opening marker",
        '# === GOD_POTION_IAP_v1 ===',
        '# === GOD_POTION_IAP_v2 ===',
    ),
]

# Battle patches (same as v1 - make battle_action respect godmode)
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
        '            if _god_inf_health:\n                combat_log.append("\U0001f6e1\ufe0f God Potion absorbs the damage! (Infinite Health)")\n            else:\n                player_health -= enemy_damage',
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

    if V2_MARKER in src:
        print("SKIP: v2 godmode API block already present")
    elif V1_MARKER in src:
        for name, old, new in V1_TO_V2:
            if new.strip() in src:
                print(f"SKIP (already applied): {name}")
                continue
            if src.count(old) != 1:
                print(f"ERROR: anchor for '{name}' matched {src.count(old)}x. Aborting.")
                sys.exit(1)
            src = src.replace(old, new, 1)
            changed += 1
            print(f"OK: {name}")
    else:
        anchor = "app.include_router(api_router)"
        if src.count(anchor) != 1:
            print(f"ERROR: anchor '{anchor}' matched {src.count(anchor)}x. Aborting.")
            sys.exit(1)
        src = src.replace(anchor, GOD_CODE_V2 + "\n" + anchor, 1)
        changed += 1
        print("OK: v2 godmode API block inserted (fresh)")

    for name, old, new in BATTLE_PATCHES:
        if new.strip() in src:
            print(f"SKIP (already applied): {name}")
            continue
        count = src.count(old)
        if name == "godmode enemy damage absorb":
            if count < 1:
                print(f"ERROR: anchor for '{name}' not found. Aborting.")
                sys.exit(1)
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
    print("GOD_POTION_V2_OK")

if __name__ == "__main__":
    main()
