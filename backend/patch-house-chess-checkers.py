#!/usr/bin/env python3
"""Street Legends backend: Chess & Checkers Table house item ($30,000) + rooms for PvP.

Part 1 - catalog: adds "chess_checkers" {"name": "Chess & Checkers Table", "category": "games",
price 30000} to HOUSE_ITEM_CATALOG. The generic items/add|remove|move
endpoints already handle any catalog item: buy deducts $30,000, remove
refunds half ($15,000 back), move saves x/y.

Part 2 - rooms: chess_checkers PvP rooms (state-store only, like pool/dominoes -
the backend stores + returns state + chat, it does NOT validate moves):
  POST /api/chess_checkers/rooms/create   {player_id, player_name, game} -> room + code + initial board
  POST /api/chess_checkers/rooms/join     {code, player_id, player_name} -> room (guest joins)
  GET  /api/chess_checkers/rooms/{code}   -> room (full state + chat; polled)
  POST /api/chess_checkers/rooms/{code}/state {player_id, state, status?, winner?} -> store full game state
  POST /api/chess_checkers/rooms/{code}/chat {player_id, player_name, text} -> append message
  POST /api/chess_checkers/rooms/{code}/leave {player_id} -> delete (waiting) or finish (playing)

Routes are defined WITHOUT the "/api" prefix: api_router is mounted at /api,
so "/api/..." on api_router becomes "/api/api/..." and 404s (the bug that
broke the pool/darts/card/dominoes rooms). Every Motor DB call is awaited.

Run from /app: python3 backend/patch-house-chess-checkers.py
Idempotent: re-running prints SKIP lines and changes nothing.
Backend only: Deploy after running. Frontend patch comes separately.
"""
import re
import sys
import py_compile
import tempfile
import os

PATH = "backend/server.py"
MARKER = "# CHESS_CHECKERS_ROOMS_V1"
ENTRY = '"chess_checkers": {"name": "Chess & Checkers Table", "category": "games", "price": 30000},'

BLOCK = """# CHESS_CHECKERS_ROOMS_V1
class ChessCheckersRoomCreate(BaseModel):
    player_id: str
    player_name: str = "Player"
    game: str = "chess"


class ChessCheckersRoomJoin(BaseModel):
    code: str
    player_id: str
    player_name: str = "Player"


class ChessCheckersRoomState(BaseModel):
    player_id: str
    state: dict
    status: str = ""
    winner: str = ""


class ChessCheckersRoomChat(BaseModel):
    player_id: str
    player_name: str = "Player"
    text: str


class ChessCheckersRoomLeave(BaseModel):
    player_id: str


def _cc_chess_initial():
    back = ["r", "n", "b", "q", "k", "b", "n", "r"]
    board = [[None for _ in range(8)] for _ in range(8)]
    for c in range(8):
        board[0][c] = {"t": back[c], "c": "b"}
        board[1][c] = {"t": "p", "c": "b"}
        board[6][c] = {"t": "p", "c": "w"}
        board[7][c] = {"t": back[c], "c": "w"}
    return {"game": "chess", "board": board, "turn": "w",
            "castling": {"wK": True, "wQ": True, "bK": True, "bQ": True},
            "ep": None, "status": "waiting", "winner": None}


def _cc_checkers_initial():
    board = [[None for _ in range(8)] for _ in range(8)]
    for r in range(8):
        for c in range(8):
            if (r + c) % 2 != 1:
                continue
            if r <= 2:
                board[r][c] = {"c": "b", "k": False}
            if r >= 5:
                board[r][c] = {"c": "r", "k": False}
    return {"game": "checkers", "board": board, "turn": "r",
            "status": "waiting", "winner": None}


async def _cc_room_code():
    for _ in range(50):
        code = str(random.randint(1000, 9999))
        if await __DB__.chess_checkers_rooms.count_documents({"code": code}) == 0:
            return code
    return str(random.randint(1000, 9999))


@__ROUTER__.post("/chess_checkers/rooms/create")
async def chess_checkers_room_create(body: ChessCheckersRoomCreate):
    game = body.game if body.game in ("chess", "checkers") else "chess"
    code = await _cc_room_code()
    now = datetime.now(timezone.utc).isoformat()
    state = _cc_chess_initial() if game == "chess" else _cc_checkers_initial()
    room = {"code": code, "host_id": body.player_id, "host_name": body.player_name,
            "guest_id": None, "guest_name": None, "game": game,
            "status": "waiting",
            "state": state, "chat": [], "created_at": now, "updated_at": now}
    await __DB__.chess_checkers_rooms.insert_one(room)
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/chess_checkers/rooms/join")
async def chess_checkers_room_join(body: ChessCheckersRoomJoin):
    room = await __DB__.chess_checkers_rooms.find_one({"code": body.code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["host_id"] == body.player_id or room.get("guest_id") == body.player_id:
        room["_id"] = str(room["_id"])
        return room
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Room is not waiting")
    await __DB__.chess_checkers_rooms.update_one({"code": body.code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await __DB__.chess_checkers_rooms.find_one({"code": body.code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.get("/chess_checkers/rooms/{code}")
async def chess_checkers_room_get(code: str):
    room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/chess_checkers/rooms/{code}/state")
async def chess_checkers_room_state(code: str, body: ChessCheckersRoomState):
    room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room["guest_id"]):
        raise HTTPException(status_code=403, detail="Not in this room")
    update = {"state": body.state, "updated_at": datetime.now(timezone.utc).isoformat()}
    if body.status:
        update["status"] = body.status
    if body.winner:
        update["winner"] = body.winner
    await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": update})
    room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/chess_checkers/rooms/{code}/chat")
async def chess_checkers_room_chat(code: str, body: ChessCheckersRoomChat):
    room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room["guest_id"]):
        raise HTTPException(status_code=403, detail="Not in this room")
    msg = {"sender_id": body.player_id, "sender_name": body.player_name, "text": body.text[:500], "ts": datetime.now(timezone.utc).isoformat()}
    await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    if room and len(room.get("chat", [])) > 100:
        await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"chat": room["chat"][-100:]}})
        room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    room["_id"] = str(room["_id"])
    return room


@__ROUTER__.post("/chess_checkers/rooms/{code}/leave")
async def chess_checkers_room_leave(code: str, body: ChessCheckersRoomLeave):
    room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] == "waiting":
        await __DB__.chess_checkers_rooms.delete_one({"code": code})
        return {"ok": True, "deleted": True}
    winner = room["guest_id"] if body.player_id == room["host_id"] else room["host_id"]
    await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"status": "finished", "winner": winner, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "finished": True, "winner": winner}

"""


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("CHESS_CHECKERS_BACKEND_ERROR: backend/server.py not found (run from /app)")
        return 1
    catalog_ok = False
    m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{([\s\S]*?)\n\}", src)
    if m and '"chess_checkers"' in m.group(1):
        print("SKIP: Chess & Checkers Table already in HOUSE_ITEM_CATALOG")
        catalog_ok = True
    else:
        m2 = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
        if not m2:
            print("CHESS_CHECKERS_BACKEND_ERROR: HOUSE_ITEM_CATALOG not found")
            return 1
        anchor = None
        for key in ("scrabble", "dominoes", "cardtable", "dartboard", "pool-table"):
            anchor = re.search(r'\n(\s*)"' + key + r'":\s*\{[^}]*\},', src[m2.end():])
            if anchor:
                break
        if anchor:
            indent = anchor.group(1)
            ins_at = m2.end() + anchor.end()
            src = src[:ins_at] + "\n" + indent + ENTRY + src[ins_at:]
        else:
            ins_at = m2.end()
            src = src[:ins_at] + "\n    " + ENTRY + src[ins_at:]
        print("OK: Chess & Checkers Table added to HOUSE_ITEM_CATALOG")
        catalog_ok = True
    rooms_ok = False
    if MARKER in src or "chess_checkers/rooms" in src:
        print("SKIP: chess_checkers rooms already present")
        rooms_ok = True
    else:
        if "@api_router." in src:
            router = "api_router"
        elif "@app." in src:
            router = "app"
        else:
            print("CHESS_CHECKERS_BACKEND_ERROR: NO_ROUTER (no @api_router or @app decorator found)")
            return 1
        mdb = re.search(r"(\w+)\.(?:houses|players|missions)\b", src)
        if not mdb:
            print("CHESS_CHECKERS_BACKEND_ERROR: NO_DB_HANDLE (no db.houses/players/missions usage found)")
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
        dt_lines = [ln for ln in src.split("\n") if ln.strip().startswith("from datetime import")]
        if module_dt:
            pass
        elif not dt_lines:
            need.append("from datetime import datetime, timezone")
        elif not any("timezone" in ln for ln in dt_lines):
            need.append("from datetime import timezone")
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
        print("OK: chess_checkers rooms block added (router=%s db=%s)" % (router, dbhandle))
        rooms_ok = True
    if not (catalog_ok and rooms_ok):
        print("CHESS_CHECKERS_BACKEND_ERROR: patch incomplete")
        return 1
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("CHESS_CHECKERS_BACKEND_ERROR: syntax check failed: %s" % e)
        return 1
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print("CHESS_CHECKERS_BACKEND_OK")


if __name__ == "__main__":
    sys.exit(main())
