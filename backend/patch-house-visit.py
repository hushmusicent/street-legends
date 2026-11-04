#!/usr/bin/env python3
"""Street Legends backend: friend house visiting + presence.

APPROVED SPEC (user-confirmed 2026-11-03, do not expand):
- A friend taps a friend's house marker -> ENTER -> that friend's
  interior, in guest mode. Guests can play games / radio / TV.
- Guests CANNOT buy/sell/add/remove/place items, sell the house,
  move it to inventory, or hide it.
- Presence list shows INSIDE the house only: "In this house now:"
  with live occupant names. Leaving removes you; a closed app drops
  off after the stale timeout (180s).

LIVE DIAGNOSTIC FACTS (diag-house-visit.py on /app):
- Items endpoints (add/remove/place-from-inventory) are ALREADY
  owner-checked (guest gets 403). Do NOT touch them.
- House owner field is player_id. Player docs are keyed by {"id": ...}
  and carry friends as a list of player IDs.
- Presence did NOT exist anywhere. This patch builds it new.
- House sell / move-to-inventory / toggle-hide endpoints may or may
  not already be owner-checked (the diagnostic did not cover them),
  so this patch adds a 403 guard ONLY where one is not present
  (detect-and-skip), and WARNINGs when an endpoint anchor is missed.

Presence store: a NEW collection house_presence (never embedded in
the house doc). Docs: {house_id, player_id, player_name,
entered_at, last_seen}. Names come from the client-sent player_name;
the backend never invents a name lookup.

Routes are defined WITHOUT an /api prefix (api_router already has
prefix="/api"); every Motor call is awaited.

Run from /app: python3 backend/patch-house-visit.py
Backend only: Deploy (Publish) after running.
Idempotent: re-running prints HOUSE_VISIT_BACKEND_ALREADY_APPLIED
and changes nothing.
"""
import os
import re
import sys
import py_compile
import tempfile

SERVER = "backend/server.py"
MARKER = "HOUSE_VISIT_BACKEND_OK"
CODE_MARKER = "# HOUSE_VISIT_PRESENCE"
TTL_SECONDS = 180


def _presence_block(db):
    return '''
# HOUSE_VISIT_PRESENCE: friend house presence (inside the house only).
# New collection house_presence; never embedded in the house doc.
HOUSE_VISIT_PRESENCE_TTL_SECONDS = 180


def _house_visit_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


async def _house_visit_prune(house_id):
    from datetime import timedelta
    cutoff = _house_visit_now() - timedelta(seconds=HOUSE_VISIT_PRESENCE_TTL_SECONDS)
    await %(db)s.house_presence.delete_many({"house_id": house_id, "last_seen": {"$lt": cutoff}})


async def _house_visit_occupants(house_id):
    await _house_visit_prune(house_id)
    rows = await %(db)s.house_presence.find({"house_id": house_id}).to_list(100)
    occupants = []
    for r in rows:
        occupants.append({
            "player_id": r.get("player_id"),
            "player_name": r.get("player_name") or "Player",
            "entered_at": r.get("entered_at").isoformat() if r.get("entered_at") else None,
            "last_seen": r.get("last_seen").isoformat() if r.get("last_seen") else None,
        })
    return occupants


async def _house_visit_allowed(house, player_id):
    if not house or not player_id:
        return False
    if house.get("player_id") == player_id:
        return True
    owner = await %(db)s.players.find_one({"id": house.get("player_id")})
    if not owner:
        return False
    return player_id in (owner.get("friends") or [])


@api_router.post("/houses/{house_id}/enter")
async def house_visit_enter(house_id: str, data: dict):
    player_id = data.get("player_id")
    player_name = data.get("player_name") or "Player"
    house = await %(db)s.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if not await _house_visit_allowed(house, player_id):
        raise HTTPException(status_code=403, detail="Not your friend's house")
    now = _house_visit_now()
    await %(db)s.house_presence.update_one(
        {"house_id": house_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _house_visit_occupants(house_id)}


@api_router.post("/houses/{house_id}/leave")
async def house_visit_leave(house_id: str, data: dict):
    player_id = data.get("player_id")
    await %(db)s.house_presence.delete_one({"house_id": house_id, "player_id": player_id})
    return {"occupants": await _house_visit_occupants(house_id)}


@api_router.post("/houses/{house_id}/heartbeat")
async def house_visit_heartbeat(house_id: str, data: dict):
    player_id = data.get("player_id")
    player_name = data.get("player_name") or "Player"
    house = await %(db)s.houses.find_one({"id": house_id})
    if not house:
        raise HTTPException(status_code=404, detail="House not found")
    if not await _house_visit_allowed(house, player_id):
        raise HTTPException(status_code=403, detail="Not your friend's house")
    now = _house_visit_now()
    await %(db)s.house_presence.update_one(
        {"house_id": house_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _house_visit_occupants(house_id)}


@api_router.get("/houses/{house_id}/presence")
async def house_visit_presence(house_id: str):
    return {"occupants": await _house_visit_occupants(house_id)}

''' % {"db": db}


def _endpoint_segment(src, route):
    """Return (start, end) of the endpoint block for a route, or None."""
    m = re.search(r'@api_router\.(post|get|put|delete)\("' + re.escape(route) + r'"', src)
    if not m:
        return None
    start = m.start()
    nxt = re.search(r'\n@api_router\.', src[m.end():])
    end = m.end() + nxt.start() + 1 if nxt else len(src)
    return (start, end)


def _guard_house_action(src, route, label):
    """Add a 403 owner guard to one house-action endpoint, if missing.

    Returns (new_src, status) where status is OK / SKIP / WARNING.
    Never touches items endpoints (handled by the caller only passing
    sell / move-to-inventory / toggle-hide routes).
    """
    seg = _endpoint_segment(src, route)
    if seg is None:
        return src, "WARNING: %s endpoint anchor not found - owner guard SKIPPED" % label
    start, end = seg
    block = src[start:end]
    if "status_code=403" in block:
        return src, "SKIP: %s already owner-guarded" % label
    # Player expression used by this endpoint: explicit assignment first,
    # else the endpoint's own second parameter (data/payload) name.
    if re.search(r'player_id\s*=\s*data\.get\("player_id"\)', block):
        expr = "player_id"
    elif re.search(r'player_id\s*=\s*payload\.get\("player_id"\)', block):
        expr = "player_id"
    elif 'payload.get("player_id")' in block:
        expr = 'payload.get("player_id")'
    elif 'data.get("player_id")' in block:
        expr = 'data.get("player_id")'
    else:
        pm = re.search(r'async def \w+\(house_id[^)]*,\s*(\w+)\s*:', block)
        if pm:
            expr = '%s.get("player_id")' % pm.group(1)
        else:
            return src, "WARNING: %s player expression not found - owner guard SKIPPED" % label
    # House variable used by this endpoint (default: house).
    hm = re.search(r'(\w+)\s*=\s*await\s+\w+\.houses\.find_one', block)
    house_var = hm.group(1) if hm else "house"
    # Insert after the 404-not-found raise, else after the find_one line.
    m404 = re.search(r'raise HTTPException\(status_code=404[^\n]*\n', block)
    if m404:
        ins = m404.end()
        guard = ('    if %s.get("player_id") != %s:\n'
                 '        raise HTTPException(status_code=403, detail="Not your house")\n'
                 % (house_var, expr))
        block = block[:ins] + guard + block[ins:]
    else:
        mfind = re.search(r'[^\n]*\.houses\.find_one[^\n]*\n', block)
        if not mfind:
            return src, "WARNING: %s house lookup not found - owner guard SKIPPED" % label
        ins = mfind.end()
        guard = ('    if %s.get("player_id") != %s:\n'
                 '        raise HTTPException(status_code=403, detail="Not your house")\n'
                 % (house_var, expr))
        block = block[:ins] + guard + block[ins:]
    return src[:start] + block + src[end:], "OK: %s owner guard added" % label


def main():
    try:
        with open(SERVER, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("HOUSE_VISIT_BACKEND_ERROR: backend/server.py not found (run from /app)")
        return 1
    if CODE_MARKER in src or "house_visit_enter" in src:
        print("HOUSE_VISIT_BACKEND_ALREADY_APPLIED")
        return 0
    # DB handle detection (live code uses db; never guess silently).
    dm = re.search(r'\b(\w+)\.houses\.find_one', src)
    db = dm.group(1) if dm else "db"
    if not dm:
        print("WARNING: db handle anchor not found - assuming 'db'")
    if '"friends"' not in src and "'friends'" not in src:
        print("WARNING: friends field anchor not found - entry enforcement reads owner.get('friends') and falls back to owner-only")
    # House-action guards (detect-and-skip; items endpoints untouched).
    for route, label in [
        ("/houses/{house_id}/sell", "house sell"),
        ("/houses/{house_id}/move-to-inventory", "house move-to-inventory"),
        ("/houses/{house_id}/toggle-hide", "house toggle-hide"),
    ]:
        src, note = _guard_house_action(src, route, label)
        print(note)
    # Presence block: insert before the router include (routes must be
    # defined before include_router copies them).
    inc = re.search(r'^.*include_router\(api_router\).*$', src, re.M)
    if not inc:
        print("WARNING: router include anchor not found - presence endpoints SKIPPED (file unchanged)")
        return 1
    block = _presence_block(db)
    src = src[:inc.start()] + block + "\n" + src[inc.start():]
    print("OK: house presence endpoints added (enter/leave/heartbeat/presence, 180s stale prune)")
    # Syntax check before writing.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("HOUSE_VISIT_BACKEND_ERROR: syntax check failed: %s" % e)
        return 1
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    with open(SERVER, "w", encoding="utf-8") as f:
        f.write(src)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
