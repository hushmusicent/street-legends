#!/usr/bin/env python3
"""Street Legends backend FRESH patch: Scrabble + vehicle travel damage,
verified piece by piece (not "already applied").

Why a fresh patch: the old backend patches printed "already applied"
(SKIP) because the code is already in /app/server.py, but the RUNNING
backend still serves old code (rooms return generic Not Found). This
fresh patch checks every piece and prints FOUND (already there, kept)
or ADDED (was missing, fixed now), so the output proves what is in
the file. It covers BOTH features in one file, one marker:

  Scrabble:
    - HOUSE_ITEM_CATALOG entry: "scrabble" Scrabble Table, games, $20,000
    - Scrabble PvP rooms: /api/scrabble/rooms/ (create/join/get/shot/chat/leave,
      seeded bag, collection scrabble_rooms)
  Vehicle travel damage (confirmed spec):
    - DURABILITY_LOSS["vehicle"] per_km = 1
    - apply_vehicle_durability_loss takes distance_km + travel-aware ternary
    - update_player_position fetches player, computes travel km via
      calculate_distance, carries remainder (vehicle_travel_remainder_km),
      calls travel loss on whole km (guarded so it can never break moves)
    - Combat NOT touched (enemy_double already exists; printed for confirmation)

After running: RESTART the backend so the running process reloads this
file (a Deploy that says success but leaves old code running is not
enough):
  sudo supervisorctl restart backend
Then GET /api/scrabble/rooms/9999 must return "Room not found"
(not generic Not Found), and the Games list shows Scrabble $20k.

Run from /app: python3 backend/patch-scrabble-vehicle-backend-fresh.py
Idempotent: re-running prints FOUND for everything and changes nothing.
Backend only.
"""
import py_compile
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")
ROOMS_MARKER = "# SCRABBLE_ROOMS_V1"
CATALOG_ENTRY = '"scrabble": {"name": "Scrabble Table", "category": "games", "price": 20000},'

ROOMS_BLOCK = """# SCRABBLE_ROOMS_V1
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

HOOK_CODE = '''    player = await db.players.find_one({"_id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    _vehicle_remainder_km = float(player.get("vehicle_travel_remainder_km", 0.0) or 0.0)
    _vehicle_whole_km = 0
    try:
        _prev = player.get("position") or {}
        if _prev.get("latitude") is not None and _prev.get("longitude") is not None:
            _dist_m = calculate_distance(Position(latitude=_prev["latitude"], longitude=_prev["longitude"]), position)
            _total_km = _vehicle_remainder_km + (_dist_m / 1000.0)
            _vehicle_whole_km = int(_total_km)
            _vehicle_remainder_km = _total_km - _vehicle_whole_km
    except Exception:
        pass
'''

CALL_CODE = '''    if _vehicle_whole_km >= 1:
        try:
            await apply_vehicle_durability_loss(player_id, "travel", distance_km=_vehicle_whole_km)
        except Exception:
            pass
'''


def main():
    if not SERVER.exists():
        print("ERROR: backend/server.py not found. Run from /app.")
        return 1
    src = SERVER.read_text()
    all_ok = True

    # --- Scrabble catalog ---
    m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{([\s\S]*?)\n\}", src)
    if m and '"scrabble"' in m.group(1):
        print("FOUND: Scrabble Table already in HOUSE_ITEM_CATALOG")
    else:
        m2 = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
        if not m2:
            print("WARNING: HOUSE_ITEM_CATALOG not found")
            all_ok = False
        else:
            anchor = None
            for key in ("dominoes", "cardtable", "dartboard", "pool-table"):
                anchor = re.search(r'\n(\s*)"%s":\s*\{[^}]*\},' % key, src[m2.end():])
                if anchor:
                    break
            if anchor:
                ins_at = m2.end() + anchor.end()
                src = src[:ins_at] + "\n" + anchor.group(1) + CATALOG_ENTRY + src[ins_at:]
            else:
                src = src[:m2.end()] + "\n    " + CATALOG_ENTRY + src[m2.end():]
            print("ADDED: Scrabble Table to HOUSE_ITEM_CATALOG")

    # --- Scrabble rooms ---
    if ROOMS_MARKER in src:
        print("FOUND: scrabble rooms block already present")
    else:
        if "@api_router." in src:
            router = "api_router"
        elif "@app." in src:
            router = "app"
        else:
            print("WARNING: no router (@api_router or @app) found; rooms not added")
            all_ok = False
            router = None
        if router:
            mdb = re.search(r"(\w+)\.(?:houses|players|missions)\b", src)
            if not mdb:
                print("WARNING: no db handle found; rooms not added")
                all_ok = False
            else:
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
                block = ROOMS_BLOCK.replace("__ROUTER__", router).replace("__DB__", dbhandle)
                if module_dt:
                    block = block.replace("datetime.now(timezone.utc)", "datetime.datetime.now(datetime.timezone.utc)")
                idx = -1
                for a in ["include_router(api_router)", "app.include_router", 'if __name__ == "__main__"']:
                    pos = src.find(a)
                    if pos != -1:
                        idx = src.rfind("\n", 0, pos) + 1
                        break
                if idx == -1:
                    src = src.rstrip("\n") + "\n\n" + block
                else:
                    src = src[:idx] + block + "\n" + src[idx:]
                print("ADDED: scrabble rooms block (router=%s db=%s)" % (router, dbhandle))

    # --- Vehicle: per_km ---
    m = re.search(r'"vehicle":\s*\{[^}]*"per_use"[^}]*"per_territory"[^}]*\}', src)
    if not m:
        print("WARNING: DURABILITY_LOSS vehicle dict not found")
        all_ok = False
    elif '"per_km"' in m.group(0):
        print("FOUND: DURABILITY_LOSS vehicle per_km already present")
    else:
        seg = m.group(0)
        seg2 = seg[:-1].rstrip() + ', "per_km": 1}'
        src = src[:m.start()] + seg2 + src[m.end():]
        print("ADDED: DURABILITY_LOSS vehicle per_km = 1")

    # --- Vehicle: signature + ternary ---
    sig_ok = False
    m = re.search(r"async def apply_vehicle_durability_loss\([^)]*\)", src)
    if not m:
        print("WARNING: apply_vehicle_durability_loss def not found")
        all_ok = False
    elif "distance_km" in m.group(0):
        print("FOUND: apply_vehicle_durability_loss already takes distance_km")
        sig_ok = True
    else:
        old = m.group(0)
        new = old[:-1] + ', distance_km: float = 0)'
        src = src[:m.start()] + new + src[m.end():]
        print("ADDED: apply_vehicle_durability_loss takes distance_km")
        sig_ok = True
    old_loss = 'loss = DURABILITY_LOSS["vehicle"]["per_use"]'
    ternary_lines = [ln for ln in src.split("\n")
                     if 'action_type == "travel"' in ln and 'DURABILITY_LOSS["vehicle"]["per_use"]' in ln]
    loss_lines = [ln for ln in src.split("\n") if old_loss in ln]
    travel_ok = False
    if ternary_lines:
        print("FOUND: per_use loss already travel-aware")
        travel_ok = True
    elif not loss_lines:
        print("WARNING: per_use loss assignment not found")
        all_ok = False
    else:
        indent = loss_lines[0][:len(loss_lines[0]) - len(loss_lines[0].lstrip())]
        new_line = indent + 'loss = int(distance_km) if action_type == "travel" else DURABILITY_LOSS["vehicle"]["per_use"]'
        src = src.replace(loss_lines[0], new_line, 1)
        print("ADDED: per_use loss is now travel-aware (travel = whole km)")
        travel_ok = True
    travel_ok = travel_ok and sig_ok

    # --- Vehicle: position hook ---
    if not travel_ok:
        print("WARNING: travel branch not wired; position hook skipped")
        all_ok = False
    else:
        lines = src.split("\n")
        didx = None
        for i, ln in enumerate(lines):
            if "def update_player_position" in ln:
                didx = i
                break
        if didx is None:
            print("WARNING: update_player_position def not found")
            all_ok = False
        elif "vehicle_travel_remainder_km" in src:
            print("FOUND: update_player_position travel hook already present")
        else:
            ins = didx + 1
            if ins < len(lines) and lines[ins].strip().startswith('"""'):
                ins += 1
            hook_lines = HOOK_CODE.rstrip("\n").split("\n")
            lines[ins:ins] = hook_lines
            src = "\n".join(lines)
            print("ADDED: update_player_position fetches player + computes travel km")
            lines = src.split("\n")
            set_idx = None
            for i in range(didx, min(len(lines), didx + 40)):
                if '"position": position.dict()' in lines[i] and '"last_active"' in lines[i]:
                    set_idx = i
                    break
            if set_idx is None:
                print("WARNING: position $set line not found; remainder not saved")
                all_ok = False
            else:
                ln = lines[set_idx]
                ln2 = ln.replace('"last_active": datetime.utcnow()',
                                 '"last_active": datetime.utcnow(), "vehicle_travel_remainder_km": _vehicle_remainder_km', 1)
                if ln2 != ln:
                    lines[set_idx] = ln2
                    src = "\n".join(lines)
                    print("ADDED: position save stores vehicle_travel_remainder_km")
                else:
                    print("WARNING: position $set edit did not apply")
                    all_ok = False
            lines = src.split("\n")
            call_idx = None
            for i in range(didx, min(len(lines), didx + 60)):
                if "if result.modified_count" in lines[i]:
                    call_idx = i
                    break
            if call_idx is None:
                print("WARNING: modified_count check not found; travel-loss call skipped")
                all_ok = False
            else:
                call_lines = CALL_CODE.rstrip("\n").split("\n")
                lines[call_idx:call_idx] = call_lines
                src = "\n".join(lines)
                print("ADDED: update_player_position calls travel durability loss")

    # Diagnostic: enemy_double assignments (no change).
    print("--- enemy_double assignments (for wiring confirmation) ---")
    shown = 0
    for i, ln in enumerate(src.split("\n")):
        if re.search(r"""["']enemy_double["']\s*\]\s*=(?!=)""", ln):
            print("server.py:%d: %s" % (i + 1, ln.strip()[:140]))
            shown += 1
            if shown >= 3:
                break
    if shown == 0:
        print("(no enemy_double assignment found)")

    SERVER.write_text(src)
    try:
        py_compile.compile(str(SERVER), doraise=True)
    except Exception as e:
        print("FRESH_SYNTAX_FAIL: %s" % e)
        return 1
    if all_ok:
        print("SCRABBLE_VEHICLE_BACKEND_FRESH_OK (restart the backend to go live)")
    else:
        print("SCRABBLE_VEHICLE_BACKEND_FRESH_WARNING: some pieces were not wired (see above)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
