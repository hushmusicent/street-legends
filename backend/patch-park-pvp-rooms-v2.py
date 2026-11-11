#!/usr/bin/env python3
"""Street Legends backend: park-games PvP rooms v2 — mirror the house games.

v1 (backend/patch-park-pvp-rooms.py) defined the routes WITHOUT the /api
prefix in the decorator (\"/park_pvp/rooms/create\"), following the chess
pattern. The house games that work (pool, darts, cards, dominoes,
scrabble) all define their room routes WITH the /api prefix
(\"/api/pool/rooms/create\"), and the park frontend calls
\"/api/park_pvp/rooms/create\". v1's routes therefore never matched what
the app calls, and CREATE ROOM failed with \"Could not create a room\".

v2 fixes it by doing exactly what the house pool patch does:
  - decorators carry the full \"/api/park_pvp/rooms/...\" path
  - router detection is the pool patch's: prefer `api_router` when the
    file uses @api_router decorators, else `app`
  - the old v1 block (no /api) is removed first, so there is exactly
    one park_pvp block and no duplicate routes

Run from /app: python3 backend/patch-park-pvp-rooms-v2.py
Backend only: Publish after running.
Idempotent: re-running prints PARK_PVP_ROOMS_V2_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "PARK_PVP_ROOMS_V2_OK"
GAMES = ("baseball", "soccer", "tennis", "one_on_one", "basketball")

PATCH_CODE = '''
# ---- PARK_PVP_ROOMS (park-games PvP rooms, all 5 games) ----
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
    game = body.game if body.game in ("baseball", "soccer", "tennis", "one_on_one", "basketball") else "baseball"
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
    if room["host_id"] == body.player_id or room.get("guest_id") == body.player_id:
        room["_id"] = str(room["_id"])
        return room
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Room is not waiting")
    await __DB__.park_pvp_rooms.update_one({"code": body.code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})
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

# Matches the v1 block (no /api) from its header through the end of the
# leave handler, so v2 can replace it instead of duplicating it.
OLD_BLOCK_RE = re.compile(
    r"# ---- PARK_PVP_ROOMS \(park-games PvP rooms, all 5 games\) ----"
    r".*?return \{\"ok\": True, \"finished\": True, \"winner\": winner\}\n",
    re.S,
)


def _db_name(src):
    """The Motor database variable."""
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
        print("WARNING: backend/server.py not found - park PvP rooms v2 NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    # Already v2: the corrected /api routes are present.
    if '"/api/park_pvp/rooms/create"' in src and "park_pvp_room_create" in src:
        print("PARK_PVP_ROOMS_V2_ALREADY_APPLIED")
        return 0
    # Router detection — same as the house pool patch: prefer api_router,
    # fall back to app. This puts the park routes on the same router the
    # working house room endpoints use.
    if "@api_router." in src:
        router = "api_router"
    elif "@app." in src:
        router = "app"
    else:
        print("WARNING: no router decorator found - park PvP rooms v2 NOT added")
        return 1
    db = _db_name(src)
    if not db:
        print("WARNING: no MongoDB variable found - park PvP rooms v2 NOT added")
        return 1
    # Remove the v1 block (no /api) if present, so there is exactly one
    # park_pvp block. If it is absent (fresh file), nothing to remove.
    removed = False
    m = OLD_BLOCK_RE.search(src)
    if m:
        src = src[:m.start()] + src[m.end():]
        removed = True
        print("OK: old park PvP block (no /api) removed")
    code = PATCH_CODE.replace("__ROUTER__", router).replace("__DB__", db)
    # Anchor: append at end of file (live server.py has no __main__ guard).
    new_src = src.rstrip() + "\n" + code
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(new_src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("PARK_PVP_ROOMS_V2_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(new_src)
    if removed:
        print("OK: park PvP routes now use /api (like the house games)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
