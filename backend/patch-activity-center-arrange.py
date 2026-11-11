#!/usr/bin/env python3
"""Street Legends backend: Activity Center arrange permission.

User rule (2026-11-06 05:57 EST): "And only give me permission to move
and arrange things around in the activity center."

What this does:
  * Layout storage: a `layout` field on the activity_centers doc, e.g.
    {"pool_table": {"x": 24, "y": -8}}. It is stored PER CENTER (keyed by
    the center's osm id) — arranging one center never moves another's
    table. The nearby endpoint returns the full doc, so the layout rides
    along on the center object the frontend already holds. The refresh
    upsert only $sets fetched OSM fields (id/name/kind/lat/lng/source/
    updated_at), so a stored layout is never clobbered by a re-fetch.
  * Endpoint POST /activity-centers/{center_id}/layout with body
    {player_id, layout}. The ONLY player who may save is Mayor Veno
    (player_id 3872dca3-bf7d-4807-8fc5-47c22ba67620); anyone else gets
    HTTP 403 "Only Mayor Veno can arrange this center." The backend
    check is the real enforcement — the frontend only hides the control.
    Missing center -> 404. Values are clamped server-side
    (x -16..120, y -8..120) so a crafted body cannot push the table
    off the modal.
  * Nothing else changes: enter/leave/heartbeat/presence, the nearby
    endpoint, the pool game, and the house rules are untouched.

Run from /app: python3 backend/patch-activity-center-arrange.py
Backend only: Publish after running. Frontend patch is separate.
Idempotent: presence checks; a full re-run prints
ACTIVITY_CENTER_ARRANGE_BACKEND_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "ACTIVITY_CENTER_ARRANGE_BACKEND_OK"
VENO_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"

_LAYOUT_BLOCK = '''
# ACTIVITY_CENTER_ARRANGE: per-center fixture layout. ONLY Mayor Veno may
# arrange a center — every other player gets 403. Layout lives on the
# activity_centers doc so the nearby endpoint returns it with the center
# (the refresh upsert only $sets fetched OSM fields, so layout survives).
ACTIVITY_CENTER_ARRANGE_OWNER_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"


def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)}}


@api_router.post("/activity-centers/{center_id}/layout")
async def activity_center_layout(center_id: str, data: dict):
    center = await __DB__.activity_centers.find_one({"id": center_id})
    if not center:
        raise HTTPException(status_code=404, detail="Activity Center not found")
    player_id = data.get("player_id")
    if player_id != ACTIVITY_CENTER_ARRANGE_OWNER_ID:
        raise HTTPException(status_code=403, detail="Only Mayor Veno can arrange this center.")
    layout = _activity_center_clamp_layout(data.get("layout") or {})
    await __DB__.activity_centers.update_one(
        {"id": center_id},
        {"$set": {"layout": layout}},
    )
    return {"id": center_id, "layout": layout}

'''

PRESENCE_GET = '''@api_router.get("/activity-centers/{center_id}/presence")
async def activity_center_presence(center_id: str):
    return {"occupants": await _activity_center_occupants(center_id)}'''


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - center layout endpoint NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    landed = []
    warnings = []

    # DB handle detection (live code uses db; never guess silently).
    dm = re.search(r"\b(\w+)\.activity_centers\.", src)
    db = dm.group(1) if dm else None
    if not dm:
        print("WARNING: db handle anchor not found - center layout endpoint NOT added")
        return 1

    if "def activity_center_layout" in src and "ACTIVITY_CENTER_ARRANGE_OWNER_ID" in src:
        print("ACTIVITY_CENTER_ARRANGE_BACKEND_ALREADY_APPLIED")
        return 0

    if PRESENCE_GET not in src:
        print("WARNING: activity center presence GET endpoint not found - center layout endpoint NOT added")
        return 1
    if src.count(PRESENCE_GET) != 1:
        print("WARNING: presence GET endpoint matched %dx - center layout endpoint NOT added" % src.count(PRESENCE_GET))
        return 1

    block = _LAYOUT_BLOCK.replace("__DB__", db)
    src = src.replace(PRESENCE_GET, PRESENCE_GET + "\n" + block, 1)
    landed.append("layout-endpoint")
    print("ACTIVITY_CENTER_ARRANGE_BACKEND_LAYOUT_OK")

    # Safety: the 403 guard must name exactly the Veno id, and the endpoint
    # must not delete or upsert center docs.
    if VENO_ID not in src:
        print("WARNING: Veno owner id missing after edit - server.py NOT written")
        return 1
    if "delete_many" in block or "delete_one" in block:
        print("WARNING: layout block contains a delete - server.py NOT written")
        return 1

    if src == orig:
        print("ACTIVITY_CENTER_ARRANGE_BACKEND_PARTIAL: nothing landed")
        return 1

    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("ACTIVITY_CENTER_ARRANGE_BACKEND_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_ARRANGE_BACKEND_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
