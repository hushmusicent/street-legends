"""Street Legends backend: AdMob rewarded-ad cash grant.
Run from /app: python3 backend/patch-admob-rewarded-grant.py
Idempotent - safe to re-run.

What it adds:
- POST /api/ads/rewarded-grant: grants +$1,000 in-game cash to a player
  for a completed AdMob rewarded ad view, and returns the new balance.
  Uses the same player-document cash pattern as the center-prize award
  (find_one by {"id": player_id}, $inc cash, re-fetch, return cash).

- Daily anti-farm cap: max 20 grants per player per day (max $20,000/day),
  tracked on the player doc as ads_rewarded: {date: "YYYY-MM-DD",
  count: N}. The count resets when the stored date is not today.

TRUST WARNING: this endpoint trusts the app's call. There is NO AdMob
server-side verification of the view (no SSV callback check). A
determined player could call the endpoint directly. The 20/day cap is
the mitigation, not proof of a real ad view.

Run order: backend patch + Deploy first, then the frontend patch.
"""
import sys
from pathlib import Path

SERVER_PATH = Path("backend/server.py")

ENDPOINT = '''
# === ADMOB REWARDED ADS ===
REWARDED_AD_CASH = 1000
REWARDED_AD_DAILY_LIMIT = 20


@api_router.post("/ads/rewarded-grant")
async def ads_rewarded_grant(data: dict):
    """Grant $1,000 in-game cash for a completed AdMob rewarded ad view.

    Trusts the app's call (no AdMob server-side verification); the
    20/day cap below is the anti-farm mitigation, not proof of a view.
    Cap is tracked on the player doc as ads_rewarded: {date, count}.
    """
    player_id = data.get("player_id")
    if not player_id:
        raise HTTPException(status_code=400, detail="player_id is required")
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    today = datetime.utcnow().strftime("%Y-%m-%d")
    ads = player.get("ads_rewarded", {}) or {}
    count = int(ads.get("count", 0) or 0) if ads.get("date") == today else 0
    if count >= REWARDED_AD_DAILY_LIMIT:
        raise HTTPException(status_code=429, detail="Daily rewarded-ad limit reached (20/day)")
    new_count = count + 1
    await db.players.update_one(
        {"id": player_id},
        {"$inc": {"cash": REWARDED_AD_CASH}, "$set": {"ads_rewarded": {"date": today, "count": new_count}}},
    )
    updated = await db.players.find_one({"id": player_id})
    return {
        "ok": True,
        "granted": REWARDED_AD_CASH,
        "cash": updated.get("cash", 0),
        "ads_today": new_count,
        "ads_limit": REWARDED_AD_DAILY_LIMIT,
    }

'''

# Anchor: end of the IAP/bonus section (live server.py, unique line).
# The new endpoint goes right before it, beside the other grant endpoints.
ANCHOR = """# === END BONUS_BUNDLES_IAP ==="""


def main():
    if not SERVER_PATH.exists():
        print(f"ERROR: {SERVER_PATH} not found. Run from /app.")
        sys.exit(1)
    text = SERVER_PATH.read_text()
    if "/ads/rewarded-grant" in text:
        print("SKIP: rewarded-grant endpoint (already applied)")
    elif text.count(ANCHOR) == 1:
        text = text.replace(ANCHOR, ENDPOINT.strip("\n") + "\n\n" + ANCHOR, 1)
        SERVER_PATH.write_text(text)
        print("OK: rewarded-grant endpoint")
    else:
        print(f"WARNING: anchor matched {text.count(ANCHOR)}x — rewarded-grant endpoint")
    print("ADMOB_REWARDED_GRANT_OK")


if __name__ == "__main__":
    main()
