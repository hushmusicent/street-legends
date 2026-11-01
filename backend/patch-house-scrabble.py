#!/usr/bin/env python3
"""Street Legends backend: Scrabble Table house item ($20,000) + scrabble rooms for PvP.

Part 1 - catalog: adds "scrabble" {"name": "Scrabble Table", "category": "games",
price 20000} to HOUSE_ITEM_CATALOG. The generic items/add|remove|move
endpoints already handle any catalog item: buy deducts $20,000, remove
refunds half ($10,000 back), move saves x/y.

Part 2 - rooms: scrabble PvP rooms (same shape as pool/darts/card/domino
rooms, plus the shared deal seed, because scrabble racks and the bag are
hidden - both devices derive the same seeded bag and only show their
own rack):
  POST /api/scrabble/rooms/create   {player_id, player_name, seed} -> room + code
  POST /api/scrabble/rooms/join     {code, player_id, player_name} -> room (guest joins)
  GET  /api/scrabble/rooms/{code}   -> room (full public state + chat; polled)
  POST /api/scrabble/rooms/{code}/shot {player_id, state} -> store public game state
  POST /api/scrabble/rooms/{code}/chat {player_id, player_name, text} -> append message
  POST /api/scrabble/rooms/{code}/leave {player_id} -> delete (waiting) or finish (playing)

Run from /app: python3 backend/patch-house-scrabble.py
Idempotent: re-running prints ALREADY lines and changes nothing.
Backend only: Deploy after running. Frontend patch comes separately.
"""
import re
import sys
import py_compile

PATH = "backend/server.py"
MARKER = "# SCRABBLE_ROOMS_V1"
ENTRY = '"scrabble": {"name": "Scrabble Table", "category": "games", "price": 20000},'

BLOCK = """# SCRABBLE_ROOMS_V1
class ScrabbleRoomCreate(BaseModel):
    player_id: str
    player_name: str = "Player"
    seed: int = 0


class ScrabbleRoomJoin(BaseModel):
    code: str
    player_id: str
    player_name: str = "Player"


class ScrabbleRoomShot(BaseModel):
    player_id: str
    state: dict


class ScrabbleRoomChat(BaseModel):
    player_id: str
    player_name: str = "Player"
    text: str


class ScrabbleRoomLeave(BaseModel):
    player_id: str


def _scrabble_room_code():
    for _ in range(50):
        code = str(random.randint(1000, 9999))
        if __DB__.scrabble_rooms.count_documents({"code": code}) == 0:
            return code
    return str(random.randint(1000, 9999))


@__ROUTER__.post("/api/scrabble/rooms/create")
async def scrabble_room_create(body: ScrabbleRoomCreate):
    code = _scrabble_room_code()
    seed = body.seed if body.seed else random.randint(1, 2147483647)
    now = datetime.now(timezone.utc).isoformat()
    room = {"code": code, "host_id": body.player_id, "host_name": body.player_name,
            "guest_id": None, "guest_name": None, "seed": seed,
            "status": "waiting",
            "state": None, "chat": [], "created_at": now, "updated_at": now}
    __DB__.scrabble_rooms.insert_one(room)
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/scrabble/rooms/join")
async def scrabble_room_join(body: ScrabbleRoomJoin):
    room = __DB__.scrabble_rooms.find_one({"code": body.code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["host_id"] == body.player_id or room.get("guest_id") == body.player_id:
        room["_id"] = str(room["_id"])
        return room
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Room is not waiting")
    __DB__.scrabble_rooms.update_one({"code": body.code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = __DB__.scrabble_rooms.find_one({"code": body.code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.get("/api/scrabble/rooms/{code}")
async def scrabble_room_get(code: str):
    room = __DB__.scrabble_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/scrabble/rooms/{code}/shot")
async def scrabble_room_shot(code: str, body: ScrabbleRoomShot):
    room = __DB__.scrabble_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room["guest_id"]):
        raise HTTPException(status_code=403, detail="Not in this room")
    __DB__.scrabble_rooms.update_one({"code": code}, {"$set": {"state": body.state, "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = __DB__.scrabble_rooms.find_one({"code": code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/scrabble/rooms/{code}/chat")
async def scrabble_room_chat(code: str, body: ScrabbleRoomChat):
    room = __DB__.scrabble_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room["guest_id"]):
        raise HTTPException(status_code=403, detail="Not in this room")
    msg = {"sender_id": body.player_id, "sender_name": body.player_name, "text": body.text[:500], "ts": datetime.now(timezone.utc).isoformat()}
    __DB__.scrabble_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
    room = __DB__.scrabble_rooms.find_one({"code": code})
    if room and len(room.get("chat", [])) > 100:
        __DB__.scrabble_rooms.update_one({"code": code}, {"$set": {"chat": room["chat"][-100:]}})
        room = __DB__.scrabble_rooms.find_one({"code": code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/api/scrabble/rooms/{code}/leave")
async def scrabble_room_leave(code: str, body: ScrabbleRoomLeave):
    room = __DB__.scrabble_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] == "waiting":
        __DB__.scrabble_rooms.delete_one({"code": code})
        return {"ok": True, "deleted": True}
    winner = room["guest_id"] if body.player_id == room["host_id"] else room["host_id"]
    __DB__.scrabble_rooms.update_one({"code": code}, {"$set": {"status": "finished", "winner": winner, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "finished": True, "winner": winner}

"""


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("SCRABBLE_ERROR: backend/server.py not found (run from /app)")
        return 1
    catalog_ok = False
    m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{([\s\S]*?)\n\}", src)
    if m and '"scrabble"' in m.group(1):
        print("SKIP: Scrabble Table already in HOUSE_ITEM_CATALOG")
        catalog_ok = True
    else:
        m2 = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
        if not m2:
            print("SCRABBLE_ERROR: HOUSE_ITEM_CATALOG not found")
            return 1
        anchor = re.search(r'\n(\s*)"dominoes":\s*\{[^}]*\},', src[m2.end():])
        if not anchor:
            anchor = re.search(r'\n(\s*)"cardtable":\s*\{[^}]*\},', src[m2.end():])
        if not anchor:
            anchor = re.search(r'\n(\s*)"dartboard":\s*\{[^}]*\},', src[m2.end():])
        if not anchor:
            anchor = re.search(r'\n(\s*)"pool-table":\s*\{[^}]*\},', src[m2.end():])
        if anchor:
            indent = anchor.group(1)
            ins_at = m2.end() + anchor.end()
            src = src[:ins_at] + "\n" + indent + ENTRY + src[ins_at:]
            print("OK: Scrabble Table added to HOUSE_ITEM_CATALOG")
        else:
            ins_at = m2.end()
            src = src[:ins_at] + "\n    " + ENTRY + src[ins_at:]
            print("OK: Scrabble Table added to HOUSE_ITEM_CATALOG")
        catalog_ok = True
    rooms_ok = False
    if MARKER in src:
        print("SCRABBLE_ROOMS_ALREADY_APPLIED")
        rooms_ok = True
    else:
        if "@api_router." in src:
            router = "api_router"
        elif "@app." in src:
            router = "app"
        else:
            print("SCRABBLE_ROOMS_ERROR: NO_ROUTER (no @api_router or @app decorator found)")
            return 1
        mdb = re.search(r"(\w+)\.(?:houses|players|missions)\b", src)
        if not mdb:
            print("SCRABBLE_ROOMS_ERROR: NO_DB_HANDLE (no db.houses/players/missions usage found)")
            return 1
        dbhandle = mdb.group(1)
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
        print("OK: scrabble rooms block added (router=%s db=%s)" % (router, dbhandle))
        rooms_ok = True
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    try:
        py_compile.compile(PATH, doraise=True)
    except Exception as e:
        print("SCRABBLE_SYNTAX_FAIL: %s" % e)
        return 1
    if catalog_ok:
        print("SCRABBLE_CATALOG_OK")
    if rooms_ok:
        print("SCRABBLE_ROOMS_OK")
    if catalog_ok and rooms_ok:
        print("HOUSE_SCRABBLE_BACKEND_OK (Deploy the backend to go live)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
