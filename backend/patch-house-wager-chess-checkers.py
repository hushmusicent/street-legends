#!/usr/bin/env python3
"""Street Legends backend: PvP cash wager for Chess & Checkers (SECOND patch).

Runs AFTER the base Chess & Checkers port patch. Adds, on top of the existing
chess_checkers/rooms rooms:
  POST /api/chess_checkers/rooms/{code}/wager/propose {player_id, amount} -> host proposes
  POST /api/chess_checkers/rooms/{code}/wager/agree   {player_id} -> guest agrees (both cash balances checked)
  POST /api/chess_checkers/rooms/{code}/wager/decline {player_id} -> guest declines, play unwagered
  POST /api/chess_checkers/rooms/{code}/wager/start   {player_id} -> re-checks both balances, deducts both, holds pot
  POST /api/chess_checkers/rooms/{code}/wager/settle  {player_id, outcome, winner_id} -> win: winner +2x; draw: refund both; forfeit: winner +2x
IN-GAME Street Legends cash only. NOT real money, NOT play chips.
Also, scoped to this game's room block only: strips any "/api" prefix the old
room patches left on api_router routes, and adds missing await to this game's
room DB calls (both bugs 404/broke the old pool/darts/card/dominoes rooms).
And, when the exact leave-handler anchor is found, leaving a PLAYING room
with a held wager pays the remaining player 2x on the server side.
If any section prints WARNING, send the full output before re-running: that
section did not land even if the OK marker prints.

Run from /app: python3 backend/patch-house-wager-chess-checkers.py
Idempotent: re-running prints ALREADY_APPLIED and changes nothing.
Backend only: Deploy after running.
"""
import re
import sys
import py_compile

PATH = "backend/server.py"
MARKER = "# WAGER_CHESS_CHECKERS_V1"

BLOCK = """# WAGER_CHESS_CHECKERS_V1
class ChessCheckersWagerPropose(BaseModel):
    player_id: str
    amount: int


class ChessCheckersWagerAction(BaseModel):
    player_id: str


class ChessCheckersWagerSettle(BaseModel):
    player_id: str
    outcome: str
    winner_id: str = ""


async def chesscheckers_wager_get_room(code):
    room = await __DB__.chess_checkers_rooms.find_one({"code": code})
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


def chesscheckers_wager_out(room, player_id):
    out = dict(room)
    if "_id" in out:
        out["_id"] = str(out["_id"])

    return out


async def chesscheckers_wager_check_funds(room, amount):
    host = await __DB__.players.find_one({"id": room["host_id"]})
    guest = await __DB__.players.find_one({"id": room.get("guest_id")})
    if not host or not guest:
        return False, "Both players must be in the room before a wager can be agreed"
    if host.get("cash", 0) < amount or guest.get("cash", 0) < amount:
        return False, "Not enough cash for this wager (needs $" + format(amount, ",") + ")"
    return True, ""


@__ROUTER__.post("/chess_checkers/rooms/{code}/wager/propose")
async def chesscheckers_wager_propose(code: str, body: ChessCheckersWagerPropose):
    room = await chesscheckers_wager_get_room(code)
    if body.player_id != room["host_id"]:
        raise HTTPException(status_code=403, detail="Only the host proposes the wager")
    if isinstance(body.amount, bool) or body.amount <= 0:
        raise HTTPException(status_code=400, detail="Wager amount must be a positive cash amount")
    status = room.get("wager_status", "none")
    if status not in ("none", "declined", "proposed"):
        raise HTTPException(status_code=400, detail="A wager is already agreed or held for this room")
    await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"wager_amount": int(body.amount), "wager_status": "proposed", "wager_proposer_id": body.player_id, "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await chesscheckers_wager_get_room(code)
    return chesscheckers_wager_out(room, body.player_id)


@__ROUTER__.post("/chess_checkers/rooms/{code}/wager/agree")
async def chesscheckers_wager_agree(code: str, body: ChessCheckersWagerAction):
    room = await chesscheckers_wager_get_room(code)
    if body.player_id != room.get("guest_id"):
        raise HTTPException(status_code=403, detail="Only the guest agrees to the wager")
    if room.get("wager_status", "none") != "proposed":
        raise HTTPException(status_code=400, detail="No wager proposal to agree to")
    amount = int(room.get("wager_amount", 0))
    ok, detail = await chesscheckers_wager_check_funds(room, amount)
    if not ok:
        raise HTTPException(status_code=400, detail=detail)
    await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"wager_status": "agreed", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await chesscheckers_wager_get_room(code)
    return chesscheckers_wager_out(room, body.player_id)


@__ROUTER__.post("/chess_checkers/rooms/{code}/wager/decline")
async def chesscheckers_wager_decline(code: str, body: ChessCheckersWagerAction):
    room = await chesscheckers_wager_get_room(code)
    if body.player_id != room.get("guest_id"):
        raise HTTPException(status_code=403, detail="Only the guest declines the wager")
    if room.get("wager_status", "none") != "proposed":
        raise HTTPException(status_code=400, detail="No wager proposal to decline")
    await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"wager_status": "declined", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await chesscheckers_wager_get_room(code)
    return chesscheckers_wager_out(room, body.player_id)


@__ROUTER__.post("/chess_checkers/rooms/{code}/wager/start")
async def chesscheckers_wager_start(code: str, body: ChessCheckersWagerAction):
    room = await chesscheckers_wager_get_room(code)
    if body.player_id not in (room["host_id"], room.get("guest_id")):
        raise HTTPException(status_code=403, detail="Not in this room")
    status = room.get("wager_status", "none")
    if status == "held":
        return chesscheckers_wager_out(room, body.player_id)
    if status != "agreed":
        raise HTTPException(status_code=400, detail="No agreed wager to start")
    amount = int(room.get("wager_amount", 0))
    ok, detail = await chesscheckers_wager_check_funds(room, amount)
    if not ok:
        raise HTTPException(status_code=400, detail=detail)
    await __DB__.players.update_one({"id": room["host_id"]}, {"$inc": {"cash": -amount}})
    await __DB__.players.update_one({"id": room.get("guest_id")}, {"$inc": {"cash": -amount}})
    await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"wager_status": "held", "updated_at": datetime.now(timezone.utc).isoformat()}})
    room = await chesscheckers_wager_get_room(code)
    return chesscheckers_wager_out(room, body.player_id)


@__ROUTER__.post("/chess_checkers/rooms/{code}/wager/settle")
async def chesscheckers_wager_settle(code: str, body: ChessCheckersWagerSettle):
    room = await chesscheckers_wager_get_room(code)
    if body.player_id not in (room["host_id"], room.get("guest_id")):
        raise HTTPException(status_code=403, detail="Not in this room")
    if room.get("wager_status", "none") != "held":
        raise HTTPException(status_code=400, detail="No held wager to settle")
    amount = int(room.get("wager_amount", 0))
    members = (room["host_id"], room.get("guest_id"))
    if body.outcome == "win" or body.outcome == "forfeit":
        if body.winner_id not in members:
            raise HTTPException(status_code=400, detail="Wager winner must be a player in this room")
        await __DB__.players.update_one({"id": body.winner_id}, {"$inc": {"cash": 2 * amount}})
        await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"wager_status": "paid", "wager_winner_id": body.winner_id, "wager_forfeit": body.outcome == "forfeit", "updated_at": datetime.now(timezone.utc).isoformat()}})
    elif body.outcome == "draw":
        await __DB__.players.update_one({"id": room["host_id"]}, {"$inc": {"cash": amount}})
        await __DB__.players.update_one({"id": room.get("guest_id")}, {"$inc": {"cash": amount}})
        await __DB__.chess_checkers_rooms.update_one({"code": code}, {"$set": {"wager_status": "refunded", "updated_at": datetime.now(timezone.utc).isoformat()}})
    else:
        raise HTTPException(status_code=400, detail="Unknown wager outcome")
    room = await chesscheckers_wager_get_room(code)
    return chesscheckers_wager_out(room, body.player_id)


"""


def main():
    warnings = []
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("CHESS_CHECKERS_WAGER_ERROR: backend/server.py not found (run from /app)")
        return 1
    if MARKER in src:
        print("CHESS_CHECKERS_WAGER_ALREADY_APPLIED")
        return 0
    if "@api_router." in src:
        router = "api_router"
    elif "@app." in src:
        router = "app"
    else:
        print("CHESS_CHECKERS_WAGER_ERROR: NO_ROUTER (no @api_router or @app decorator found)")
        return 1
    mdb = re.search(r"(\w+)\.(?:houses|players|missions)\b", src)
    if not mdb:
        print("CHESS_CHECKERS_WAGER_ERROR: NO_DB_HANDLE (no db.houses/players/missions usage found)")
        return 1
    dbhandle = mdb.group(1)
    # --- timezone import (wager block uses datetime.now(timezone.utc)) ---
    module_dt = re.search(r"^import datetime\b", src, re.M) and not re.search(r"from datetime import", src)
    if not module_dt:
        dt_lines = [ln for ln in src.split("\n") if ln.strip().startswith("from datetime import")]
        if not dt_lines:
            lines = src.split("\n")
            last_import = -1
            for i, ln in enumerate(lines[:80]):
                if ln.strip().startswith("import ") or ln.strip().startswith("from "):
                    last_import = i
            lines.insert(last_import + 1, "from datetime import datetime, timezone")
            src = "\n".join(lines)
            print("OK: datetime+timezone import added")
        elif not any("timezone" in ln for ln in dt_lines):
            lines = src.split("\n")
            last_import = -1
            for i, ln in enumerate(lines[:80]):
                if ln.strip().startswith("import ") or ln.strip().startswith("from "):
                    last_import = i
            lines.insert(last_import + 1, "from datetime import timezone")
            src = "\n".join(lines)
            print("OK: timezone import added")
    # --- scoped route-prefix strip: "/api/chess_checkers/rooms" -> "/chess_checkers/rooms" ---
    n_strip = len(re.findall(r'"/api/chess_checkers/rooms', src))
    if n_strip:
        src = src.replace('"/api/chess_checkers/rooms', '"/chess_checkers/rooms')
        print("OK: stripped /api prefix from %d Chess & Checkers room routes" % n_strip)
    # --- scoped await fix for this game's collection only ---
    coll = "chess_checkers_rooms"
    await_pat = re.compile(r"(?<!await )" + re.escape(dbhandle) + r"\." + re.escape(coll) + r"\.(insert_one|find_one|update_one|delete_one|count_documents)\(")
    n_await = len(await_pat.findall(src))
    if n_await:
        src = await_pat.sub(lambda m: "await " + dbhandle + "." + coll + "." + m.group(1) + "(", src)
        print("OK: added await to %d Chess & Checkers room DB calls" % n_await)
    helper = "_cc_room_code"
    if re.search(r"^def " + re.escape(helper) + r"\(", src, re.M):
        src = re.sub(r"^def " + re.escape(helper) + r"\(", "async def " + helper + "(", src, flags=re.M)
        src = re.sub(r"(?<!await )(?<!def )" + re.escape(helper) + r"\(\)", "await " + helper + "()", src)
        print("OK: room-code helper made async")
    # --- base rooms presence check (wager endpoints need the room docs) ---
    if not re.search(r'"/chess_checkers/rooms', src) and not re.search(r'"/api/chess_checkers/rooms', src):
        warnings.append("WARNING: base Chess & Checkers room routes not found in server.py - wager endpoints added but rooms endpoints are missing")
    # --- server-side forfeit payout on leave (exact anchor only) ---
    leave_pat = re.compile(
        r"(winner = room\[\"guest_id\"\] if body\.player_id == room\[\"host_id\"\] else room\[\"host_id\"\]\n)"
        r"(\s*)await " + re.escape(dbhandle) + r"\." + re.escape(coll) +
        r"\.update_one\(\{\"code\": code\}, \{\"\$set\": \{\"status\": \"finished\", \"winner\": winner,")
    lm = leave_pat.search(src)
    if lm:
        indent = lm.group(2)
        payout = (
            lm.group(1)
            + indent + "if room.get(\"status\") == \"playing\" and room.get(\"wager_status\") == \"held\" and room.get(\"wager_amount\"):\n"
            + indent + "    await " + dbhandle + ".players.update_one({\"id\": winner}, {\"$inc\": {\"cash\": 2 * int(room[\"wager_amount\"])}})\n"
            + indent + "    await " + dbhandle + "." + coll + ".update_one({\"code\": code}, {\"$set\": {\"wager_status\": \"paid\", \"wager_winner_id\": winner}})\n"
            + indent + "await " + dbhandle + "." + coll + ".update_one({\"code\": code}, {\"$set\": {\"status\": \"finished\", \"winner\": winner,")
        src = src[:lm.start()] + payout + src[lm.end():]
        print("OK: leave-handler wager payout wired (remaining player wins a held pot)")
    else:
        warnings.append("WARNING: leave-handler wager payout NOT wired for Chess & Checkers (anchor not found) - the wager/settle forfeit endpoint still covers explicit forfeit claims")
    # --- append wager block ---
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
    try:
        compile(src, PATH, "exec")
    except SyntaxError as e:
        print("CHESS_CHECKERS_WAGER_SYNTAX_FAIL: %s (server.py left unchanged)" % e)
        return 1
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    try:
        py_compile.compile(PATH, doraise=True)
        print("Python syntax OK.")
    except Exception as e:
        print("CHESS_CHECKERS_WAGER_SYNTAX_FAIL: %s" % e)
        return 1
    for w in warnings:
        print(w)
    print("WAGER_CHESS_CHECKERS_BACKEND_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
