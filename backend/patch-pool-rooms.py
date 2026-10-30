#!/usr/bin/env python3
"""Pool PvP rooms backend patch (POOL_ROOMS_V1).

Adds turn-based pool room endpoints to the Emergent FastAPI backend:
  POST /api/pool/rooms/create   {player_id, player_name} -> room with 4-digit code
  POST /api/pool/rooms/join     {code, player_id, player_name} -> room (guest joins)
  GET  /api/pool/rooms/{code}   -> room (full state + chat; polled by both players)
  POST /api/pool/rooms/{code}/shot {player_id, state} -> store full game state
  POST /api/pool/rooms/{code}/chat {player_id, player_name, text} -> append message
  POST /api/pool/rooms/{code}/leave {player_id} -> delete (waiting) or finish (playing)

Run from /app: python3 backend/patch-pool-rooms.py
Idempotent: re-running prints POOL_ROOMS_ALREADY_APPLIED and changes nothing.
Backend only: Deploy after running. Frontend patch comes separately.
"""
import re
import sys
import py_compile

PATH = "backend/server.py"
MARKER = "# POOL_ROOMS_V1"

BLOCK = """# POOL_ROOMS_V1
class PoolRoomCreate(BaseModel):
    player_id: str
    player_name: str = "Player"


class PoolRoomJoin(BaseModel):
    code: str
    player_id: str
    player_name: str = "Player"


class PoolRoomShot(BaseModel):
    player_id: str
    state: dict


class PoolRoomChat(BaseModel):
    player_id: str
    player_name: str = "Player"
    text: str


class PoolRoomLeave(BaseModel):
    player_id: str


def _pool_room_code():
    for _ in range(50):
        code = str(random.randint(1000, 9999))
        if __DB__.pool_rooms.count_documents({"code": code}) == 0:
            return code
    return str(random.randint(1000, 9999))


@__ROUTER__.post("/api/pool/rooms/create")
async def pool_room_create(body: PoolRoomCreate):
    code = _pool_room_code()
    now = datetime.now(timezone.utc).isoformat()
    room = {"code": code, "host_id": body.player_id, "host_name": body.player_name,
            "guest_id": None, "guest_name": None, "status": "waiting",
            "state": None, "chat": [], "created_at": now, "updated_at": now}
    __DB__.pool_rooms.insert_one(room)
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/pool/rooms/join")
async def pool_room_join(body: PoolRoomJoin):
    room = __DB__.pool_rooms.find_one({"code": body.code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["host_id"] == body.player_id or room.get("guest_id") == body.player_id:
        room["_id"] = str(room["_id"])
        return room
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Room is not waiting")
    __DB__.pool_rooms.update_one({"code": body.code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = __DB__.pool_rooms.find_one({"code": body.code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.get("/api/pool/rooms/{code}")
async def pool_room_get(code: str):
    room = __DB__.pool_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/pool/rooms/{code}/shot")
async def pool_room_shot(code: str, body: PoolRoomShot):
    room = __DB__.pool_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room["guest_id"]):
        raise HTTPException(status_code=403, detail="Not in this room")
    __DB__.pool_rooms.update_one({"code": code}, {"$set": {"state": body.state, "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = __DB__.pool_rooms.find_one({"code": code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/pool/rooms/{code}/chat")
async def pool_room_chat(code: str, body: PoolRoomChat):
    room = __DB__.pool_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room["guest_id"]):
        raise HTTPException(status_code=403, detail="Not in this room")
    msg = {"sender_id": body.player_id, "sender_name": body.player_name, "text": body.text[:500], "ts": datetime.now(timezone.utc).isoformat()}
    __DB__.pool_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
    room = __DB__.pool_rooms.find_one({"code": code})
    if room and len(room.get("chat", [])) > 100:
        __DB__.pool_rooms.update_one({"code": code}, {"$set": {"chat": room["chat"][-100:]}})
        room = __DB__.pool_rooms.find_one({"code": code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/pool/rooms/{code}/leave")
async def pool_room_leave(code: str, body: PoolRoomLeave):
    room = __DB__.pool_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] == "waiting":
        __DB__.pool_rooms.delete_one({"code": code})
        return {"ok": True, "deleted": True}
    winner = room["guest_id"] if body.player_id == room["host_id"] else room["host_id"]
    __DB__.pool_rooms.update_one({"code": code}, {"$set": {"status": "finished", "winner": winner, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "finished": True, "winner": winner}

"""


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("POOL_ROOMS_ERROR: backend/server.py not found (run from /app)")
        return 1
    if MARKER in src:
        print("POOL_ROOMS_ALREADY_APPLIED")
        return 0
    if "@api_router." in src:
        router = "api_router"
    elif "@app." in src:
        router = "app"
    else:
        print("POOL_ROOMS_ERROR: NO_ROUTER (no @api_router or @app decorator found)")
        return 1
    m = re.search(r"(\w+)\.(?:houses|players|missions)\b", src)
    if not m:
        print("POOL_ROOMS_ERROR: NO_DB_HANDLE (no db.houses/players/missions usage found)")
        return 1
    dbhandle = m.group(1)
    lines = src.split("\n")
    last_import = -1
    for i, ln in enumerate(lines[:80]):
        s = ln.strip()
        if s.startswith("import ") or s.startswith("from "):
            last_import = i
    need = []
    if not re.search(r"^import random\b", src, re.M):
        need.append("import random")
    if "BaseModel" not in src:
        need.append("from pydantic import BaseModel")
    if "HTTPException" not in src:
        need.append("from fastapi import HTTPException")
    module_dt = re.search(r"^import datetime\b", src, re.M) and not re.search(r"from datetime import", src)
    if not module_dt and not re.search(r"from datetime import", src):
        need.append("from datetime import datetime, timezone")
    if need:
        insert_at = last_import + 1
        for j, imp in enumerate(need):
            lines.insert(insert_at + j, imp)
        src = "\n".join(lines)
    block = BLOCK.replace("__ROUTER__", router).replace("__DB__", dbhandle)
    if module_dt:
        block = block.replace("datetime.now(timezone.utc)", "datetime.datetime.now(datetime.timezone.utc)")
    anchors = ["include_router(api_router)", "app.include_router", 'if __name__ == "__main__"']
    idx = -1
    for a in anchors:
        pos = src.find(a)
        if pos != -1:
            idx = src.rfind("\n", 0, pos) + 1
            break
    if idx == -1:
        src = src.rstrip("\n") + "\n\n" + block
    else:
        src = src[:idx] + block + "\n" + src[idx:]
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    try:
        py_compile.compile(PATH, doraise=True)
        print("POOL_ROOMS_OK router=%s db=%s (Deploy the backend to go live)" % (router, dbhandle))
    except Exception as e:
        print("POOL_ROOMS_SYNTAX_FAIL: %s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
