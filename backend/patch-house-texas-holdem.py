#!/usr/bin/env python3
"""Street Legends backend: Texas Hold'em Table house item + PvP rooms.

PRICE = 20000 (buy), SELL = PRICE // 2 (10000 back, via the generic
half-refund remove endpoint). Price confirmed by the user ("Make it 20k").

Part 1 - catalog: adds "texas_holdem" {"name": "Texas Hold'em Table",
"category": "games", "price": PRICE} to HOUSE_ITEM_CATALOG. The generic
items/add|remove|move endpoints already handle any catalog item.

Part 2 - rooms: texas_holdem PvP rooms. The backend stores + filters +
merges state; it does NOT implement poker rules (no dealing, no hand
evaluation, no betting logic — the frontend engines do that):
  POST /api/texas_holdem/rooms/create   {player_id, player_name} -> room + code (host deals via a state post after create)
  POST /api/texas_holdem/rooms/join     {code, player_id, player_name} -> room (guest joins)
  GET  /api/texas_holdem/rooms/{code}?player_id=... -> FILTERED room (see below) or 404 "Room not found"
  POST /api/texas_holdem/rooms/{code}/state {player_id, state, status?, winner?, new_hand?} -> MERGED state
  POST /api/texas_holdem/rooms/{code}/chat {player_id, player_name, text} -> append message
  POST /api/texas_holdem/rooms/{code}/leave {player_id} -> delete (waiting) or finish (playing)

HIDDEN HANDS (poker differs from chess/checkers, where the board is public):
- GET returns a FILTERED view: the requesting player's own hole cards +
  community + public fields (pot, bets, turn, status, chat). The opponent's
  hole cards are replaced with [{"hidden": true}, {"hidden": true}] so the
  page renders 2 card backs. A player fetching the room JSON directly must
  NOT see the opponent's cards.
- Exception: when the room status is "finished" AND the stored state has
  showdown=true (a real showdown, not a fold), GET returns the FULL state
  to members (both hands revealed — official showdown reveal). A finish
  via FOLD (showdown=false) stays filtered (the folder mucks, no reveal).
- Missing player_id -> public view (both hands hidden, any status).
  Non-member player_id -> 403. Members only get the finished full reveal.
- POST /state MERGES (does not blindly overwrite): public fields + the
  sender's player object come from the posted state; the NON-sender's
  player object (including their hole cards) is preserved exactly from
  storage, since the sender's filtered view does not contain them.
  new_hand=true replaces the whole state (the dealer dealt both hands).
- The shared deck IS stored and returned (both apps need it to deal
  streets peer-to-peer with a dumb backend). Hole cards are the hidden
  information; the deck order is visible in the room JSON to a determined
  inspector. True server-dealt hidden deck would need backend dealing,
  which this port deliberately does not do (same trust level as the
  pool/dominoes state-store rooms).

Routes are defined WITHOUT the "/api" prefix: api_router is mounted at /api,
so "/api/..." on api_router becomes "/api/api/..." and 404s (the bug that
broke the pool/darts/card/dominoes rooms). Every Motor DB call is awaited.

Run from /app: python3 backend/patch-house-texas-holdem.py
Idempotent: re-running prints SKIP lines and changes nothing.
Backend only: Deploy after running. Frontend patch comes separately.
"""
import re
import sys
import py_compile
import tempfile
import os

PATH = "backend/server.py"
MARKER = "# TEXAS_HOLDEM_ROOMS_V1"
PRICE = 20000
SELL = PRICE // 2
ENTRY = '"texas_holdem": {"name": "Texas Hold\'em Table", "category": "games", "price": %d},' % PRICE

BLOCK = """# TEXAS_HOLDEM_ROOMS_V1
class TexasHoldemRoomCreate(BaseModel):
    player_id: str
    player_name: str = "Player"


class TexasHoldemRoomJoin(BaseModel):
    code: str
    player_id: str
    player_name: str = "Player"


class TexasHoldemRoomState(BaseModel):
    player_id: str
    state: dict
    status: str = ""
    winner: str = ""
    new_hand: bool = False


class TexasHoldemRoomChat(BaseModel):
    player_id: str
    player_name: str = "Player"
    text: str


class TexasHoldemRoomLeave(BaseModel):
    player_id: str


def _th_filter_room(room, player_id):
    # Return a copy of room with hole cards filtered for player_id.
    # Members get their own cards. Finished + showdown rooms reveal both
    # hands to members (official showdown). Finished via fold stays
    # filtered (the folder mucks). Missing player_id -> public view.
    # Callers check non-member player_id (403) before calling this.
    out = copy.deepcopy(room)
    out["_id"] = str(out["_id"])
    st = out.get("state")
    if not isinstance(st, dict):
        return out
    status = out.get("status", "")
    host_id = out.get("host_id")
    guest_id = out.get("guest_id")
    is_member = player_id in (host_id, guest_id)
    if status == "finished" and st.get("showdown") and is_member:
        return out
    my_idx = None
    if player_id == host_id:
        my_idx = 0
    elif player_id == guest_id:
        my_idx = 1
    players = st.get("p")
    if not isinstance(players, list):
        return out
    new_p = []
    for i, pl in enumerate(players):
        if not isinstance(pl, dict):
            new_p.append(pl)
            continue
        pl2 = dict(pl)
        if i != my_idx:
            hole = pl2.get("hole")
            if isinstance(hole, list) and len(hole) > 0:
                pl2["hole"] = [{"hidden": True} for _ in hole]
        new_p.append(pl2)
    st["p"] = new_p
    out["state"] = st
    return out


async def _th_room_code():
    for _ in range(50):
        code = str(random.randint(1000, 9999))
        if await __DB__.texas_holdem_rooms.count_documents({"code": code}) == 0:
            return code
    return str(random.randint(1000, 9999))


@__ROUTER__.post("/texas_holdem/rooms/create")
async def texas_holdem_room_create(body: TexasHoldemRoomCreate):
    code = await _th_room_code()
    now = datetime.now(timezone.utc).isoformat()
    room = {"code": code, "host_id": body.player_id, "host_name": body.player_name,
            "guest_id": None, "guest_name": None,
            "status": "waiting",
            "state": {}, "chat": [], "created_at": now, "updated_at": now}
    await __DB__.texas_holdem_rooms.insert_one(room)
    room["_id"] = str(room["_id"])
    return _th_filter_room(room, body.player_id)


@__ROUTER__.post("/texas_holdem/rooms/join")
async def texas_holdem_room_join(body: TexasHoldemRoomJoin):
    room = await __DB__.texas_holdem_rooms.find_one({"code": body.code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["host_id"] == body.player_id or room.get("guest_id") == body.player_id:
        return _th_filter_room(room, body.player_id)
    if room["status"] != "waiting":
        raise HTTPException(status_code=400, detail="Room is not waiting")
    await __DB__.texas_holdem_rooms.update_one({"code": body.code}, {"$set": {"guest_id": body.player_id, "guest_name": body.player_name, "status": "playing", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await __DB__.texas_holdem_rooms.find_one({"code": body.code})
    return _th_filter_room(room, body.player_id)


@__ROUTER__.get("/texas_holdem/rooms/{code}")
async def texas_holdem_room_get(code: str, player_id: str = ""):
    room = await __DB__.texas_holdem_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if player_id and player_id not in (room["host_id"], room.get("guest_id")):
        raise HTTPException(status_code=403, detail="Not in this room")
    return _th_filter_room(room, player_id)


@__ROUTER__.post("/texas_holdem/rooms/{code}/state")
async def texas_holdem_room_state(code: str, body: TexasHoldemRoomState):
    room = await __DB__.texas_holdem_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room.get("guest_id")):
        raise HTTPException(status_code=403, detail="Not in this room")
    stored = room.get("state") or {}
    posted = body.state or {}
    if body.new_hand:
        new_state = copy.deepcopy(posted)
    elif body.status == "finished" and posted.get("showdown") and posted.get("awarded"):
        # Showdown award post: the sender received the FULL state (finished
        # + showdown reveals both hands), so a wholesale replace is safe
        # and required — a merge would drop the non-sender's awarded
        # stack, since merge only writes the sender's player object.
        # (The completer's showdownPending post has awarded unset, so it
        # still takes the merge path and cannot clobber real cards with
        # hidden placeholders.)
        new_state = copy.deepcopy(posted)
    else:
        new_state = copy.deepcopy(stored) if isinstance(stored, dict) else {}
        s_idx = 0 if body.player_id == room["host_id"] else 1
        for k, v in posted.items():
            if k != "p":
                new_state[k] = v
        posted_p = posted.get("p")
        if isinstance(posted_p, list) and len(posted_p) > s_idx:
            stored_p = new_state.get("p")
            if not isinstance(stored_p, list):
                stored_p = []
            while len(stored_p) <= s_idx:
                stored_p.append({})
            stored_p[s_idx] = copy.deepcopy(posted_p[s_idx])
            new_state["p"] = stored_p
    update = {"state": new_state, "updated_at": datetime.now(timezone.utc).isoformat()}
    if body.status:
        update["status"] = body.status
    if body.winner:
        update["winner"] = body.winner
    await __DB__.texas_holdem_rooms.update_one({"code": code}, {"$set": update})
    room = await __DB__.texas_holdem_rooms.find_one({"code": code})
    return _th_filter_room(room, body.player_id)


@__ROUTER__.post("/texas_holdem/rooms/{code}/chat")
async def texas_holdem_room_chat(code: str, body: TexasHoldemRoomChat):
    room = await __DB__.texas_holdem_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if body.player_id not in (room["host_id"], room.get("guest_id")):
        raise HTTPException(status_code=403, detail="Not in this room")
    msg = {"sender_id": body.player_id, "sender_name": body.player_name, "text": body.text[:500], "ts": datetime.now(timezone.utc).isoformat()}
    await __DB__.texas_holdem_rooms.update_one({"code": code}, {"$push": {"chat": msg}, "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await __DB__.texas_holdem_rooms.find_one({"code": code})
    if room and len(room.get("chat", [])) > 100:
        await __DB__.texas_holdem_rooms.update_one({"code": code}, {"$set": {"chat": room["chat"][-100:]}})
        room = await __DB__.texas_holdem_rooms.find_one({"code": code})
    return _th_filter_room(room, body.player_id)


@__ROUTER__.post("/texas_holdem/rooms/{code}/leave")
async def texas_holdem_room_leave(code: str, body: TexasHoldemRoomLeave):
    room = await __DB__.texas_holdem_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room["status"] == "waiting":
        await __DB__.texas_holdem_rooms.delete_one({"code": code})
        return {"ok": True, "deleted": True}
    winner = room["guest_id"] if body.player_id == room["host_id"] else room["host_id"]
    await __DB__.texas_holdem_rooms.update_one({"code": code}, {"$set": {"status": "finished", "winner": winner, "updated_at": datetime.now(timezone.utc).isoformat()}})
    return {"ok": True, "finished": True, "winner": winner}

"""


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("TEXAS_HOLDEM_BACKEND_ERROR: backend/server.py not found (run from /app)")
        return 1
    catalog_ok = False
    m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{([\s\S]*?)\n\}", src)
    if m and '"texas_holdem"' in m.group(1):
        print("SKIP: Texas Hold'em Table already in HOUSE_ITEM_CATALOG")
        catalog_ok = True
    else:
        m2 = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
        if not m2:
            print("TEXAS_HOLDEM_BACKEND_ERROR: HOUSE_ITEM_CATALOG not found")
            return 1
        anchor = None
        for key in ("chess_checkers", "scrabble", "dominoes", "cardtable", "dartboard", "pool-table"):
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
        print("OK: Texas Hold'em Table added to HOUSE_ITEM_CATALOG (price %d)" % PRICE)
        catalog_ok = True
    rooms_ok = False
    if MARKER in src or "texas_holdem/rooms" in src:
        print("SKIP: texas_holdem rooms already present")
        rooms_ok = True
    else:
        if "@api_router." in src:
            router = "api_router"
        elif "@app." in src:
            router = "app"
        else:
            print("TEXAS_HOLDEM_BACKEND_ERROR: NO_ROUTER (no @api_router or @app decorator found)")
            return 1
        mdb = re.search(r"(\w+)\.(?:houses|players|missions)\b", src)
        if not mdb:
            print("TEXAS_HOLDEM_BACKEND_ERROR: NO_DB_HANDLE (no db.houses/players/missions usage found)")
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
        if not re.search(r"^import copy\b", src, re.M):
            need.append("import copy")
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
        print("OK: texas_holdem rooms block added (router=%s db=%s)" % (router, dbhandle))
        rooms_ok = True
    if not (catalog_ok and rooms_ok):
        print("TEXAS_HOLDEM_BACKEND_ERROR: patch incomplete")
        return 1
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("TEXAS_HOLDEM_BACKEND_ERROR: syntax check failed: %s" % e)
        return 1
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print("TEXAS_HOLDEM_BACKEND_OK")


if __name__ == "__main__":
    sys.exit(main())
