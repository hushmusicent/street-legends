#!/usr/bin/env python3
"""Street Legends backend: park-games PvP rooms v3 — make JOIN fail loudly.

Why v3 exists (live evidence, 2026-11-11):
  Room 3207 (basketball, host Mayor Veno 3872dca3-bf7d-4807-8fc5-47c22ba67620)
  was created 2026-11-11T08:34:26Z and was STILL {"status": "waiting",
  "guest_id": null} when re-checked ~16:00Z the same day. No distinct-id
  join ever reached the backend for that room.

  v2's join handler has a silent trap for exactly this symptom. When the
  joining phone sends the SAME player_id as the host, v2 returns the room
  unchanged with HTTP 200 — the guest phone then shows "Joined! You are
  AWAY" and polls forever, the room never flips to "playing", and the host
  never starts. No error appears on either phone. That happens when the
  friend phone's identity injection never landed (both phones fall back
  to the shared 'local-player' id in the game HTML), or when both phones
  are signed in as the same player. The Nov 4 house-pool bug was the
  same pattern: window.POOL_PVP never reached the page, both phones ran
  the placeholder identity.

  v3 changes ONLY the join path (and the game allow-list):
  - a join from the host's own player_id now returns HTTP 400 with
    detail "host_cannot_join: ..." instead of the room. The guest phone
    must show that instead of faking a successful join. (The frontend
    currently swallows non-OK as null and prints "Room not found", so
    the frontend half of this fix — surfacing the real detail on the
    PvP panel — is still needed; see the handoff note below.)
  - rejoin by the recorded guest still returns the room (unchanged).
  - a second, different guest on a non-waiting room still gets 400.
  - football is added to the allowed games. v2's allow-list had only
    the original five, so a football CREATE stored game="baseball".
    Football PvP was approved 2026-11-11 and must not be mislabelled.

  This does NOT by itself make a join request that never arrives
  succeed. What it does: it removes the one server-side path that
  produces "joined, but nothing ever starts" with no error, so the
  next failed join tells the truth about why. The matching frontend
  half — a per-device fallback id (localStorage-generated, distinct
  per phone) instead of the shared 'local-player', plus showing the
  real join error on the panel — is a separate patch; do not call
  JOIN fixed until a fresh two-phone room flips to playing.

  Scope: backend only. Removes the v2 block first, so there is exactly
  one park_pvp block. Publish after running.
  Idempotent: re-running prints PARK_PVP_ROOMS_V3_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "PARK_PVP_ROOMS_V3_OK"
GAMES = ("baseball", "soccer", "tennis", "one_on_one", "basketball", "football")

PATCH_CODE = '''
# ---- PARK_PVP_ROOMS (park-games PvP rooms, all 6 games) ----
class ParkPvpRoomCreate(BaseModel):
    player_id: str
    player_name: str = ""
    game: str = "baseball"


class ParkPvpRoomJoin(BaseModel):
    code: str
    player_id: str
    player_name: str = ""


class ParkPvpRoomState(BaseModel):
    player_id: str
    state: dict = {}
    status: str = ""
    winner: str = ""


class ParkPvpRoomLeave(BaseModel):
    player_id: str


async def _park_pvp_room_code():
    for _ in range(50):
        code = str(random.randint(1000, 9999))
        if await __DB__.park_pvp_rooms.count_documents({"code": code}) == 0:
            return code
    return str(random.randint(1000, 9999))


@__ROUTER__.post("/api/park_pvp/rooms/create")
async def park_pvp_room_create(body: ParkPvpRoomCreate):
    game = body.game if body.game in ("baseball", "soccer", "tennis", "one_on_one", "basketball", "football") else "baseball"
    code = await _park_pvp_room_code()
    now = datetime.now(timezone.utc).isoformat()
    room = {"code": code, "host_id": body.player_id, "host_name": body.player_name,
            "guest_id": None, "guest_name": None, "game": game,
            "status": "waiting",
            "state": {}, "chat": [], "created_at": now, "updated_at": now}
    await __DB__.park_pvp_rooms.insert_one(room)
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/park_pvp/rooms/join")
async def park_pvp_room_join(body: ParkPvpRoomJoin):
    room = await __DB__.park_pvp_rooms.find_one({"code": body.code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["host_id"] == body.player_id:
        # v3: never silently return the waiting room to the host's own id.
        # That made the guest phone show "Joined!" while the room stayed
        # waiting forever (same player id on both phones, or the shared
        # 'local-player' fallback when identity injection never landed).
        raise HTTPException(status_code=400, detail="host_cannot_join: you are the host - join from the other phone/account")
    if room.get("guest_id") == body.player_id:
        room["_id"] = str(room["_id"])
        return room
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Room is not waiting")
    await __DB__.park_pvp_rooms.update_one({"code": code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await __DB__.park_pvp_rooms.find_one({"code": body.code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.get("/api/park_pvp/rooms/{code}")
async def park_pvp_room_get(code: str):
    room = await __DB__.park_pvp_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/park_pvp/rooms/{code}/state")
async def park_pvp_room_state(code: str, body: ParkPvpRoomState):
    room = await __DB__.park_pvp_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room["guest_id"]):
        raise HTTPException(status_code=403, detail="Not in this room")
    update = {"state": body.state, "updated_at": datetime.now(timezone.utc).isoformat()}
    if body.status:
        update["status"] = body.status
    if body.winner:
        update["winner"] = body.winner
    await __DB__.park_pvp_rooms.update_one({"code": code}, {"$set": update})
    room = await __DB__.park_pvp_rooms.find_one({"code": code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/park_pvp/rooms/{code}/leave")
async def park_pvp_room_leave(code: str, body: ParkPvpRoomLeave):
    room = await __DB__.park_pvp_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] == "waiting":
        await __DB__.park_pvp_rooms.delete_one({"code": code})
        return {"ok": True, "deleted": True}
    winner = room["guest_id"] if body.player_id == room["host_id"] else room["host_id"]
    await __DB__.park_pvp_rooms.update_one({"code": code}, {"$set": {"status": "finished", "winner": winner, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "finished": True, "winner": winner}
'''

# Matches the v2 block (header says "all 5 games"; v3's own header says
# "all 6 games") from its header through the end of the leave handler.
OLD_BLOCK_RE = re.compile(
    r"# ---- PARK_PVP_ROOMS \(park-games PvP rooms, all \d+ games\) ----"
    r".*?return \{\"ok\": True, \"finished\": True, \"winner\": winner\}\n",
    re.S,
)


def _db_name(src):
    if "__DB__" in src:
        return "__DB__"
    m = re.search(r"(\w+)\.chess_checkers_rooms", src)
    if m:
        return m.group(1)
    m = re.search(r"(\w+)\.\w+_rooms", src)
    if m:
        return m.group(1)
    return None


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - park PvP rooms v3 NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    if "host_cannot_join" in src and '"/api/park_pvp/rooms/create"' in src:
        print("PARK_PVP_ROOMS_V3_ALREADY_APPLIED")
        return 0
    if "@api_router." in src:
        router = "api_router"
    elif "@app." in src:
        router = "app"
    else:
        print("WARNING: no router decorator found - park PvP rooms v3 NOT added")
        return 1
    db = _db_name(src)
    if not db:
        print("WARNING: no MongoDB variable found - park PvP rooms v3 NOT added")
        return 1
    removed = False
    m = OLD_BLOCK_RE.search(src)
    if m:
        src = src[:m.start()] + src[m.end():]
        removed = True
        print("OK: old park PvP block removed")
    code = PATCH_CODE.replace("__ROUTER__", router).replace("__DB__", db)
    new_src = src.rstrip() + "\n" + code
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(new_src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("PARK_PVP_ROOMS_V3_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(new_src)
    if removed:
        print("OK: park PvP routes now use v3 join (host-id join is a 400, football in the game list)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
