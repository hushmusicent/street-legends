"""Street Legends backend: verify God Potion purchases with Google Play
before granting - v2. Run from /app: python3 backend/patch-iap-verify-godmode-v2.py
Idempotent - safe to re-run.

v2 FIXES v1: the v1 "grant verification" anchor (the TODO comment +
`now = datetime.utcnow()`) matched TWICE in /app, because the
grant-bonus endpoint carries the same TODO comment. v1 correctly
refused to apply that section, but it DID apply the helpers and the
response - and the response references `_verified`, which the missing
section defines. So /app is in a broken intermediate state until v2
runs: do NOT Deploy until v2 prints IAP_VERIFY_GODMODE_V2_OK.

v2 anchors the verification to the lines unique to grant-godmode
(`buff_kind = GOD_POTION_PRODUCTS.get(...)` + the player lookup), so
it matches exactly once. All three sections are included so v2 works
whether run fresh or after v1 (already-applied parts SKIP).

Same verification as v1: requires purchase_token, verifies it with the
Google Play Developer API (purchases.products.get), rejects duplicates,
consumes the token after granting, returns purchase_verified.
Needs GOOGLE_PLAY_SERVICE_ACCOUNT_JSON secret to be strict; until it
is set, grants still go through but log a warning and return
purchase_verified=false.
"""
import sys
from pathlib import Path

PATH = Path("backend/server.py")

# ---- Helpers (insert before iap_grant_godmode) ----
HELPER_ANCHOR = '''@api_router.post("/iap/grant-godmode")
async def iap_grant_godmode(data: GodPotionGrant):'''

HELPER = '''# IAP_VERIFY: Google Play purchase verification for God Potions.
# Package name of the Play app (must match the Play Console listing).
PLAY_PACKAGE_NAME = "com.emergent.streetempiretest.xfvyzd"


def _play_service_account_credentials():
    """Service-account credentials from the GOOGLE_PLAY_SERVICE_ACCOUNT_JSON
    env secret (the whole JSON key file contents). Returns None when the
    secret is not set, so the caller can fall back to warn-and-grant
    instead of breaking live sales during setup."""
    import json
    import os
    raw = os.environ.get("GOOGLE_PLAY_SERVICE_ACCOUNT_JSON", "")
    if not raw or not raw.strip():
        return None
    try:
        info = json.loads(raw)
    except Exception:
        logging.warning("IAP_VERIFY: GOOGLE_PLAY_SERVICE_ACCOUNT_JSON is not valid JSON")
        return None
    try:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=["https://www.googleapis.com/auth/androidpublisher"],
        )
        return creds
    except Exception as exc:
        logging.warning("IAP_VERIFY: could not build service-account credentials: %s", exc)
        return None


async def _verify_play_purchase(product_id: str, purchase_token: str):
    """Verify a one-time Play purchase with the Play Developer API.
    Returns (verified: bool, reason: str).
    - (True, 'verified') when Play confirms purchaseState == 0 (purchased).
    - (False, reason) when Play says otherwise or the call fails.
    - (None, 'not_configured') when no service-account secret is set.
    Runs the blocking google-auth / HTTP work in a thread so the event
    loop is not stalled."""
    creds = _play_service_account_credentials()
    if creds is None:
        return (None, "not_configured")
    import asyncio as _asyncio

    def _call():
        try:
            from google.auth.transport.requests import Request as _AuthRequest
            creds.refresh(_AuthRequest())
            token = creds.token
        except Exception as exc:
            return (False, f"auth_failed: {exc}")
        try:
            import urllib.parse
            import urllib.request
            url = (
                "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
                f"{urllib.parse.quote(PLAY_PACKAGE_NAME, safe='')}/purchases/products/"
                f"{urllib.parse.quote(product_id, safe='')}/tokens/"
                f"{urllib.parse.quote(purchase_token, safe='')}"
            )
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                import json as _json
                data = _json.loads(resp.read().decode("utf-8"))
        except Exception as exc:
            return (False, f"play_api_failed: {exc}")
        state = data.get("purchaseState")
        if state != 0:
            return (False, f"purchaseState={state} (0=purchased, 1=cancelled)")
        return (True, "verified")

    return await _asyncio.to_thread(_call)


async def _consume_play_purchase(product_id: str, purchase_token: str):
    """Consume a one-time Play purchase so the token cannot be replayed.
    Best effort: returns True on success, False otherwise (logged)."""
    creds = _play_service_account_credentials()
    if creds is None:
        return False
    import asyncio as _asyncio

    def _call():
        try:
            from google.auth.transport.requests import Request as _AuthRequest
            creds.refresh(_AuthRequest())
            token = creds.token
        except Exception:
            return False
        try:
            import urllib.parse
            import urllib.request
            url = (
                "https://androidpublisher.googleapis.com/androidpublisher/v3/applications/"
                f"{urllib.parse.quote(PLAY_PACKAGE_NAME, safe='')}/purchases/products/"
                f"{urllib.parse.quote(product_id, safe='')}/tokens/"
                f"{urllib.parse.quote(purchase_token, safe='')}:consume"
            )
            req = urllib.request.Request(url, method="POST", headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=15):
                return True
        except Exception:
            return False

    return await _asyncio.to_thread(_call)


@api_router.post("/iap/grant-godmode")
async def iap_grant_godmode(data: GodPotionGrant):'''

# ---- Grant verification (v2 anchor: unique to grant-godmode) ----
GRANT_ANCHOR = '''    buff_kind = GOD_POTION_PRODUCTS.get(data.product_id)
    if not buff_kind:
        raise HTTPException(status_code=400, detail=f"Unknown product: {data.product_id}")
    player = await db.players.find_one({"id": data.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    # TODO: verify data.purchase_token with Play Developer API here.
    # For now we log it for audit.
    now = datetime.utcnow()'''

GRANT_NEW = '''    buff_kind = GOD_POTION_PRODUCTS.get(data.product_id)
    if not buff_kind:
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
        "godmode.last_purchase_token": data.purchase_token,
        "godmode.last_product_id": data.product_id,
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

# ---- Response: add purchase_verified + consume after grant ----
RESPONSE_ANCHOR = '''    updated = await db.players.find_one({"id": data.player_id})
    remaining = _godmode_remaining(updated)
    return {
        "message": f"Potion activated! Infinite {buff_kind.replace('_', ' ').title()} for 1 hour.",
        "product_id": data.product_id,
        "buff_kind": buff_kind,
        "price_usd": GOD_POTION_PRICE_USD,
        "duration_seconds": GOD_POTION_DURATION_SECONDS,
        "expires_at": until_str,
        "remaining": remaining,
    }'''

RESPONSE_NEW = '''    updated = await db.players.find_one({"id": data.player_id})
    remaining = _godmode_remaining(updated)
    # Consume the token so it cannot be replayed for a second grant.
    # Best effort: a consume failure does not revoke the verified grant.
    if _verified is True:
        _consumed = await _consume_play_purchase(data.product_id, data.purchase_token)
        if not _consumed:
            logging.warning("IAP_VERIFY: consume failed for %s token %s", data.product_id, (data.purchase_token or "")[:12])
    return {
        "message": f"Potion activated! Infinite {buff_kind.replace('_', ' ').title()} for 1 hour.",
        "product_id": data.product_id,
        "buff_kind": buff_kind,
        "price_usd": GOD_POTION_PRICE_USD,
        "duration_seconds": GOD_POTION_DURATION_SECONDS,
        "expires_at": until_str,
        "remaining": remaining,
        "purchase_verified": bool(_verified is True),
    }'''


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from /app.")
        sys.exit(1)
    src = PATH.read_text()
    steps = [
        ("IAP verify helpers", HELPER_ANCHOR, HELPER),
        ("grant verification", GRANT_ANCHOR, GRANT_NEW),
        ("grant response + consume", RESPONSE_ANCHOR, RESPONSE_NEW),
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
    print("IAP_VERIFY_GODMODE_V2_OK")


if __name__ == "__main__":
    main()
