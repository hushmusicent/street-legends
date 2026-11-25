"""Street Legends backend: push notifications via Expo Push API.
Run from /app: python3 backend/patch-push-notifications.py
Idempotent - safe to re-run.

What it adds:
- POST /api/players/{id}/push-token: store a player's Expo push token.
- Helpers _push_send_expo / _push_to_player / _push_to_players / _push_tokens
  that send via https://exp.host/--/api/v2/push/send and NEVER raise, so a
  failing push can never break the game endpoint that triggered it.
- Hooks (fire-and-forget via asyncio.create_task):
  (a) park PvP room JOIN -> notify the host the opponent joined / room ready
  (b) RPS challenge created -> notify the challenged player
  (c) RPS respond (accept/decline) -> notify the challenger
  (d) guild chat message -> notify the other guild members
  (e) pool room chat -> notify the other room member
  (f) darts room chat -> notify the other room member
- POST /api/admin/push-comeback?days=3&admin_key=... : re-engagement.
  Finds players inactive for >= days (player.last_active, already recorded
  on login + position update) with a stored push token and sends each one
  a single "come back" push. Skips anyone nudged within the same window
  (last_comeback_push_at). Admin-key protected, same pattern as the other
  /admin endpoints. Trigger it from a scheduled job or by hand; nothing
  in this patch runs it automatically.
- Park PvP has NO direct challenge endpoint to hook: a challenge is just
  a room + a 4-digit code shared out of band, so the JOIN hook (a) is the
  notifiable moment. Global /chat is NOT hooked: it is a public channel
  and notifying every player per message would spam everyone.
"""
import sys
from pathlib import Path

PATH = Path("backend/server.py")

# ---- Section 1: helpers + push-token endpoint + comeback endpoint ----
HELPERS_ANCHOR = '''app.include_router(api_router)'''

HELPERS = '''# PUSH_NOTIFICATIONS: Expo push tokens + send helper.
# Players store their Expo push token on the player doc (push_token).
# Game events fire-and-forget a push via asyncio.create_task so a slow
# or failing Expo call can never break the game endpoint that triggered it.
EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"
PUSH_COMEBACK_DAYS_DEFAULT = 3


async def _push_send_expo(token, title, body, data=None):
    """Send one push via the Expo Push API. Never raises."""
    if not token or not isinstance(token, str) or not token.startswith("ExponentPushToken["):
        return False
    try:
        payload = {"to": token, "title": title, "body": body, "sound": "default"}
        if data:
            payload["data"] = data
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(EXPO_PUSH_URL, json=payload)
            return resp.status_code == 200
    except Exception:
        return False


async def _push_to_player(player_id, title, body, data=None):
    """Push to one player by id (looks up their stored token). Never raises."""
    try:
        player = await db.players.find_one({"id": player_id}, {"push_token": 1})
        if not player:
            return False
        return await _push_send_expo(player.get("push_token"), title, body, data)
    except Exception:
        return False


async def _push_tokens(tokens, title, body, data=None):
    """Push to a list of raw Expo tokens. Never raises."""
    for token in tokens or []:
        try:
            await _push_send_expo(token, title, body, data)
        except Exception:
            continue
    return True


async def _push_to_players(player_ids, title, body, data=None):
    """Push to several players by id. Never raises."""
    for pid in player_ids or []:
        try:
            await _push_to_player(pid, title, body, data)
        except Exception:
            continue
    return True


class PushTokenBody(BaseModel):
    push_token: str
    platform: str = "android"


@api_router.post("/players/{player_id}/push-token")
async def set_push_token(player_id: str, body: PushTokenBody):
    """Store a player's Expo push token so game events can notify them."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    token = (body.push_token or "").strip()
    if not token.startswith("ExponentPushToken["):
        raise HTTPException(status_code=400, detail="Not a valid Expo push token")
    await db.players.update_one(
        {"id": player_id},
        {"$set": {"push_token": token, "push_platform": body.platform,
                  "push_token_updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return {"ok": True}


def _push_parse_dt(value):
    """Parse a last_active / last_comeback_push_at value that may be a
    datetime or an ISO string. Returns an aware datetime or None."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value
    return None


async def _push_comeback_run(days=3):
    """Find players inactive for >= days with a stored push token and send
    each one a single 'come back' push. Skips anyone already nudged within
    the same window (last_comeback_push_at). Returns counts. Never raises."""
    try:
        days = int(days)
    except Exception:
        days = PUSH_COMEBACK_DAYS_DEFAULT
    if days < 1:
        days = 1
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    sent = 0
    skipped = 0
    try:
        players = await db.players.find(
            {"push_token": {"$exists": True, "$ne": None, "$ne": ""}},
            {"id": 1, "name": 1, "push_token": 1, "last_active": 1, "last_comeback_push_at": 1},
        ).to_list(1000)
    except Exception:
        return {"ok": False, "sent": 0, "skipped": 0}
    for p in players:
        try:
            last_active = _push_parse_dt(p.get("last_active"))
            if last_active is not None and last_active >= cutoff:
                skipped += 1
                continue
            last_nudge = _push_parse_dt(p.get("last_comeback_push_at"))
            if last_nudge is not None and last_nudge >= cutoff:
                skipped += 1
                continue
            ok = await _push_send_expo(
                p.get("push_token"),
                "Street Legends misses you!",
                f"{p.get('name', 'Player')}, your crew is still running the streets. Come back and play!",
                {"type": "comeback"},
            )
            await db.players.update_one(
                {"id": p["id"]},
                {"$set": {"last_comeback_push_at": datetime.now(timezone.utc).isoformat()}},
            )
            if ok:
                sent += 1
            else:
                skipped += 1
        except Exception:
            skipped += 1
            continue
    return {"ok": True, "sent": sent, "skipped": skipped}


@api_router.post("/admin/push-comeback")
async def push_comeback(
    days: int = Query(PUSH_COMEBACK_DAYS_DEFAULT, description="Inactive for at least this many days"),
    admin_key: str = Query(..., description="Admin secret key for authorization"),
):
    """Send 'come back' pushes to players inactive for >= days. Admin only.
    Trigger it from a scheduled job (cron) or by hand; it is not automatic."""
    if not ADMIN_SECRET_KEY or admin_key != ADMIN_SECRET_KEY:
        raise HTTPException(status_code=403, detail="Invalid admin key")
    return await _push_comeback_run(days)


# Register router last so every route defined above is included
app.include_router(api_router)'''

# ---- Section 2: park PvP JOIN -> notify the host (room ready) ----
PARK_JOIN_ANCHOR = '''    await db.park_pvp_rooms.update_one({"code": body.code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})'''

PARK_JOIN_NEW = '''    await db.park_pvp_rooms.update_one({"code": body.code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})
    # PUSH_NOTIFICATIONS: guest joined -> host gets "room ready".
    asyncio.create_task(_push_to_player(room["host_id"], "Opponent joined!", f"{body.player_name or 'A player'} joined your {room.get('game', 'park')} match - room {body.code} is ready!", {"type": "park_pvp_ready", "code": body.code, "game": room.get("game", "")}))'''

# ---- Section 3: RPS challenge created -> notify the opponent ----
RPS_CHALLENGE_ANCHOR = '''    await db.rps_games.insert_one(game)'''

RPS_CHALLENGE_NEW = '''    await db.rps_games.insert_one(game)
    # PUSH_NOTIFICATIONS: challenge created -> challenged player gets pinged.
    asyncio.create_task(_push_to_player(opponent_id, "Rock Paper Scissors challenge!", f"{challenger.get('name', 'A player')} challenged you to Rock Paper Scissors. Open the game to answer!", {"type": "rps_challenge", "game_id": game["game_id"]}))'''

# ---- Section 4: RPS respond -> notify the challenger ----
RPS_RESPOND_ANCHOR = '''    await db.rps_games.update_one({"game_id": game_id}, {"$set": {"status": new_status}})'''

RPS_RESPOND_NEW = '''    await db.rps_games.update_one({"game_id": game_id}, {"$set": {"status": new_status}})
    # PUSH_NOTIFICATIONS: opponent answered -> challenger gets the verdict.
    asyncio.create_task(_push_to_player(game.get("challenger_id"), "RPS challenge " + new_status + "!", f"{game.get('opponent_name', 'Your opponent')} {new_status} your Rock Paper Scissors challenge.", {"type": "rps_respond", "game_id": game_id, "status": new_status}))'''

# ---- Section 5: guild chat -> notify the other guild members ----
GUILD_CHAT_ANCHOR = '''    await db.guild_chat.insert_one(chat_message)'''

GUILD_CHAT_NEW = '''    await db.guild_chat.insert_one(chat_message)
    # PUSH_NOTIFICATIONS: guild message -> other members get pinged.
    try:
        _members = await db.players.find({"guild_id": guild_id, "id": {"$ne": player_id}}, {"id": 1, "push_token": 1}).to_list(200)
        _tokens = [m.get("push_token") for m in _members if m.get("push_token")]
        if _tokens:
            asyncio.create_task(_push_tokens(_tokens, f"{player.get('name', 'Someone')} in guild chat", message.strip()[:120], {"type": "guild_chat", "guild_id": guild_id}))
    except Exception:
        pass'''

# ---- Section 6: pool room chat -> notify the other room member ----
POOL_CHAT_ANCHOR = '''    await db.pool_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})'''

POOL_CHAT_NEW = '''    await db.pool_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
    # PUSH_NOTIFICATIONS: pool chat -> the other player in the room gets pinged.
    _other = room["guest_id"] if body.player_id == room["host_id"] else room["host_id"]
    if _other:
        asyncio.create_task(_push_to_player(_other, f"{body.player_name} in Pool", body.text[:120], {"type": "room_chat", "game": "pool", "code": code}))'''

# ---- Section 7: darts room chat -> notify the other room member ----
DARTS_CHAT_ANCHOR = '''    await db.dart_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})'''

DARTS_CHAT_NEW = '''    await db.dart_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
    # PUSH_NOTIFICATIONS: darts chat -> the other player in the room gets pinged.
    _other = room["guest_id"] if body.player_id == room["host_id"] else room["host_id"]
    if _other:
        asyncio.create_task(_push_to_player(_other, f"{body.player_name} in Darts", body.text[:120], {"type": "room_chat", "game": "darts", "code": code}))'''


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from /app.")
        sys.exit(1)
    src = PATH.read_text()
    steps = [
        ("push helpers + token endpoint + comeback", HELPERS_ANCHOR, HELPERS),
        ("park pvp join notify host", PARK_JOIN_ANCHOR, PARK_JOIN_NEW),
        ("rps challenge notify opponent", RPS_CHALLENGE_ANCHOR, RPS_CHALLENGE_NEW),
        ("rps respond notify challenger", RPS_RESPOND_ANCHOR, RPS_RESPOND_NEW),
        ("guild chat notify members", GUILD_CHAT_ANCHOR, GUILD_CHAT_NEW),
        ("pool chat notify other", POOL_CHAT_ANCHOR, POOL_CHAT_NEW),
        ("darts chat notify other", DARTS_CHAT_ANCHOR, DARTS_CHAT_NEW),
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
    print("PUSH_NOTIFICATIONS_OK")


if __name__ == "__main__":
    main()
