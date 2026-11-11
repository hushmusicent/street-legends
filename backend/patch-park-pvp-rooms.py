#!/usr/bin/env python3
"""Street Legends backend: park-games PvP rooms (one system, all 5 games).

User request (2026-11-10 17:26 EST): "Put the PvP on all the park
games" — Baseball '97, Soccer '98, Tennis '84, 1-on-1 '21, and the
2v2 Basketball. (Pop Shot is NOT a park game — activity centers only.)

Design (mirrors the house PvP rooms, e.g. chess_checkers):
  One MongoDB collection, park_pvp_rooms, with a `game` field so a
  single patch covers all five games. The room holds the full game
  state; clients post state, opponents poll GET. State-sync model —
  the backend stores whatever state the game posts, it does not
  simulate the game.

  POST /api/park_pvp/rooms/create {player_id, player_name, game}
      -> room with a 4-digit code, host set, status "waiting",
         state {} (the game posts its initial state after creating).
  POST /api/park_pvp/rooms/join {code, player_id, player_name}
      -> guest joins, status becomes "playing".
  GET  /api/park_pvp/rooms/{code} -> room (poll for opponent + state).
  POST /api/park_pvp/rooms/{code}/state {player_id, state, status?, winner?}
      -> store the caller's state (either player may post).
  POST /api/park_pvp/rooms/{code}/leave {player_id}
      -> waiting: delete the room; playing: finish, other player wins.

  `game` must be one of: baseball, soccer, tennis, one_on_one,
  basketball. Roles: the host is player 1 (HOME / first), the guest
  is player 2 (AWAY / second) — each game maps that to its own teams.

Run from /app: python3 backend/patch-park-pvp-rooms.py
Backend only: Publish after running.
Idempotent: re-running prints PARK_PVP_ROOMS_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "PARK_PVP_ROOMS_OK"
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


@__ROUTER__.post("/park_pvp/rooms/create")
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


@__ROUTER__.post("/park_pvp/rooms/join")
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


@__ROUTER__.get("/park_pvp/rooms/{code}")
async def park_pvp_room_get(code: str):
    room = await __DB__.park_pvp_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/park_pvp/rooms/{code}/state")
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


@__ROUTER__.post("/park_pvp/rooms/{code}/leave")
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


def _router_name(src):
    """The router variable used by @...post decorators in server.py."""
    m = re.search(r"@(\w+)\.post\(\"/chess_checkers/rooms/create\"\)", src)
    if m:
        return m.group(1)
    m = re.search(r"@(\w+)\.post\(\"/darts/rooms/create\"\)", src)
    if m:
        return m.group(1)
    m = re.search(r"@(\w+)\.post\(", src)
    if m:
        return m.group(1)
    return None


def _db_name(src):
    """The Motor database variable (the chess patch uses __DB__)."""
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
        print("WARNING: backend/server.py not found - park PvP rooms NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    if "park_pvp_rooms" in src and "PARK_PVP_ROOMS" in src:
        print("PARK_PVP_ROOMS_ALREADY_APPLIED")
        return 0
    router = _router_name(src)
    db = _db_name(src)
    if not router:
        print("WARNING: no router decorator found - park PvP rooms NOT added")
        return 1
    if not db:
        print("WARNING: no MongoDB variable found - park PvP rooms NOT added")
        return 1
    code = PATCH_CODE.replace("__ROUTER__", router).replace("__DB__", db)
    # Anchor: append after the last room endpoint block (or at end of file).
    # Find a safe insertion point: right before the final `if __name__` or
    # at the end of the file if there is none.
    anchor = src.rfind("\nif __name__ ==")
    if anchor == -1:
        new_src = src.rstrip() + "\n" + code
    else:
        new_src = src[:anchor] + "\n" + code + src[anchor:]
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(new_src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("PARK_PVP_ROOMS_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(new_src)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
