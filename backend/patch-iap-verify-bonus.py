"""Street Legends backend: verify Bonus bundle purchases with Google Play
before granting. Run from /app: python3 backend/patch-iap-verify-bonus.py
Idempotent - safe to re-run.

Same hole as God Potions (fixed by patch-iap-verify-godmode-v2.py):
POST /api/iap/grant-bonus trusted the caller. It accepted player_id +
product_id + purchase_token and granted cash / MK1s / godmode WITHOUT
checking with Google that a purchase actually happened. Anyone who
found the endpoint could call it directly and get the $100 pack free.
The code carried the same TODO: "verify purchase_token with Google
Play Developer API (purchases.products.get) before granting."

FIX: verify every purchase_token against the Google Play Developer API
before granting, and consume the token after a successful grant so it
cannot be replayed. Duplicate tokens are rejected. Reuses the
_verify_play_purchase() / _consume_play_purchase() helpers installed
by the God Potion patch (run that patch first - it is already live in
/app). Same service-account secret: GOOGLE_PLAY_SERVICE_ACCOUNT_JSON.
Until that secret is set, grants still go through but log a warning
and return purchase_verified=false, so sales do not break during
setup. Once the secret is present, verification is strict.

CHANGES (backend/server.py, grant-bonus only):
1. Requires purchase_token; verifies it with Play (when configured);
   rejects duplicates (same token already granted for that product).
2. Consumes the token after granting; returns purchase_verified.
3. No change to the bundle prices, contents, or the frontend (it
   already sends purchase_token).

BACKEND change: run the curl, then Deploy. Bonus products still
return 0/4 from Play (ticket 2-3610000041585), so no Bonus purchases
are happening yet - this locks the door before Google fixes it.
"""
import sys
from pathlib import Path

PATH = Path("backend/server.py")

# ---- Grant verification (anchor unique to grant-bonus) ----
GRANT_ANCHOR = '''    bundle = BONUS_BUNDLE_PRODUCTS.get(data.product_id)
    if not bundle:
        raise HTTPException(status_code=400, detail=f"Unknown product: {data.product_id}")
    player = await db.players.find_one({"id": data.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    # TODO: verify data.purchase_token with Play Developer API here.
    # For now we log it for audit.
    now = datetime.utcnow()'''

GRANT_NEW = '''    bundle = BONUS_BUNDLE_PRODUCTS.get(data.product_id)
    if not bundle:
        raise HTTPException(status_code=400, detail=f"Unknown product: {data.product_id}")
    player = await db.players.find_one({"id": data.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    # IAP_VERIFY: a purchase token is required, and it must verify with
    # Google Play before anything is granted. Duplicate tokens (already
    # granted) are rejected so one purchase cannot be replayed.
    if not data.purchase_token:
        raise HTTPException(status_code=400, detail="purchase_token is required")
    _dup = await db.players.find_one({
        "bonus.last_purchase_token": data.purchase_token,
        "bonus.last_product_id": data.product_id,
    })
    if _dup:
        raise HTTPException(status_code=400, detail="This purchase was already granted")
    _verified, _reason = await _verify_play_purchase(data.product_id, data.purchase_token)
    if _verified is False:
        raise HTTPException(status_code=400, detail=f"Purchase could not be verified with Google Play: {_reason}")
    if _verified is None:
        logging.warning(
            "IAP_VERIFY: granting %s to %s WITHOUT Play verification "
            "(GOOGLE_PLAY_SERVICE_ACCOUNT_JSON not set) - set the secret to enforce verification",
            data.product_id, data.player_id,
        )
    now = datetime.utcnow()'''

# ---- Response: consume after grant + purchase_verified ----
RESPONSE_ANCHOR = '''    return {
        "message": "Bonus granted! " + ", ".join(parts) + ".",
        "product_id": data.product_id,
        "price_usd": bundle["price_usd"],
        "cash": updated.get("cash", 0),
        "bonus_items": updated.get("bonus_items", {"health_mk1": 0, "energy_mk1": 0}),
    }'''

RESPONSE_NEW = '''    # Consume the token so it cannot be replayed for a second grant.
    # Best effort: a consume failure does not revoke the verified grant.
    if _verified is True:
        _consumed = await _consume_play_purchase(data.product_id, data.purchase_token)
        if not _consumed:
            logging.warning("IAP_VERIFY: consume failed for %s token %s", data.product_id, (data.purchase_token or "")[:12])
    return {
        "message": "Bonus granted! " + ", ".join(parts) + ".",
        "product_id": data.product_id,
        "price_usd": bundle["price_usd"],
        "cash": updated.get("cash", 0),
        "bonus_items": updated.get("bonus_items", {"health_mk1": 0, "energy_mk1": 0}),
        "purchase_verified": bool(_verified is True),
    }'''


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from /app.")
        sys.exit(1)
    src = PATH.read_text()
    # Guard: the Play verify helpers come from the God Potion patch.
    if "_verify_play_purchase" not in src or "_consume_play_purchase" not in src:
        print("ERROR: Play verify helpers not found. Run patch-iap-verify-godmode-v2.py first.")
        sys.exit(1)
    steps = [
        ("bonus grant verification", GRANT_ANCHOR, GRANT_NEW),
        ("bonus grant response + consume", RESPONSE_ANCHOR, RESPONSE_NEW),
    ]
    for desc, old, new in steps:
        if new in src:
            print(f"SKIP: {desc} (already applied)")
        elif src.count(old) == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {desc}")
        else:
            print(f"WARNING: anchor matched {src.count(old)}x — {desc}")
    PATH.write_text(src)
    print("IAP_VERIFY_BONUS_OK")


if __name__ == "__main__":
    main()
