#!/usr/bin/env python3
"""Street Legends backend: Activity Centers on REAL university/college locations.

This REPLACES the phase-1 seeded-fictional version (patch-activity-center.py).
Do NOT run the v1 backend/frontend patches — v2 supersedes them entirely.

What changes vs v1: ONLY where centers come from. The presence system
(activity_presence, enter/leave/heartbeat/GET, 180s prune), the Enter-only
popup, the hall interior, the friends+self list, and the no-menu rule are
unchanged. Center identity is now stable OpenStreetMap ids (osm_<type>_<id>),
so every phone shares the same center and the same presence room.

REAL DATA SOURCE — OpenStreetMap Overpass (free, no key, no billing):
  GET /activity-centers/nearby?bbox=minLng,minLat,maxLng,maxLat
  (or ?latitude=..&longitude=..&radius_km=2 — bbox computed server-side)
The backend queries https://overpass-api.de/api/interpreter for nodes,
ways, and relations tagged amenity=university OR amenity=college inside
the bbox, with `out center;` so ways/relations yield a center point.
Deduped by (osm type + osm id). Name from the name tag, falling back to
"University"/"College" by amenity value.

NO-FALLBACK RULE: if Overpass errors, times out, or returns nothing, the
endpoint returns whatever real centers are already cached in the DB for
that bbox (possibly an empty list). It NEVER invents seeded/fictional
centers. Fair use: the public Overpass instance is rate-limited, so each
~0.05-degree grid cell is cached for 24h and only missing/stale cells
are re-queried — a map move never hammers Overpass.

CLEANUP: every nearby call deletes any activity_centers rows whose id
starts with "activity_center_" (the v1 fictional grid ids) and any
activity_presence rows for those ids, so a v1 run cannot leave fictional
centers on the map. Real osm_* rows are never deleted. The v1
/activity-centers/spawn endpoint is also removed from server.py by
this patch when present.

KNOWN LIMIT: a campus appears only where OpenStreetMap tags it
amenity=university or amenity=college. A campus mapped without those
tags will not appear.

Run from /app: python3 backend/patch-activity-center-real.py
Backend only: Publish after running. Frontend patch is separate.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "ACTIVITY_CENTER_REAL_OK"

_NEARBY_BLOCK = '''
# ACTIVITY_CENTER_REAL: real university/college centers from OpenStreetMap.
# NO seeded/fictional fallback: on Overpass error/timeout the endpoint
# returns what is cached in the DB for the bbox (possibly empty) — never
# fake centers. Each ~0.05-degree grid cell is cached for 24h.
ACTIVITY_CENTER_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ACTIVITY_CENTER_CACHE_SECONDS = 86400  # 24h per grid cell
ACTIVITY_CENTER_CELL_DEG = 0.05


def _activity_center_cells(min_lat, min_lng, max_lat, max_lng):
    import math
    cells = []
    i0 = math.floor(min_lat / ACTIVITY_CENTER_CELL_DEG)
    i1 = math.floor(max_lat / ACTIVITY_CENTER_CELL_DEG)
    j0 = math.floor(min_lng / ACTIVITY_CENTER_CELL_DEG)
    j1 = math.floor(max_lng / ACTIVITY_CENTER_CELL_DEG)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            cells.append((f"{i}_{j}", i * ACTIVITY_CENTER_CELL_DEG, j * ACTIVITY_CENTER_CELL_DEG,
                          (i + 1) * ACTIVITY_CENTER_CELL_DEG, (j + 1) * ACTIVITY_CENTER_CELL_DEG))
    return cells


def _activity_center_overpass_query(s, w, n, e):
    # Overpass bbox order is (south, west, north, east).
    return (
        "[out:json][timeout:25];\\n"
        "(\\n"
        f'  nwr["amenity"="university"]({s},{w},{n},{e});\\n'
        f'  nwr["amenity"="college"]({s},{w},{n},{e});\\n'
        ");\\n"
        "out center;\\n"
    )


async def _activity_center_fetch_cell(cell_key, s, w, n, e):
    """Query Overpass for one grid cell. Returns a list of center dicts,
    or None on any error (so the cell is NOT cached and retries next call)."""
    query = _activity_center_overpass_query(s, w, n, e)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(ACTIVITY_CENTER_OVERPASS_URL, data={"data": query})
        if resp.status_code != 200:
            logging.warning("Overpass HTTP %s for cell %s", resp.status_code, cell_key)
            return None
        payload = resp.json()
    except Exception as exc:
        logging.warning("Overpass error for cell %s: %s", cell_key, exc)
        return None
    centers = []
    seen = set()
    for el in payload.get("elements", []) or []:
        etype = el.get("type")
        oid = el.get("id")
        tags = el.get("tags") or {}
        amenity = tags.get("amenity")
        if etype not in ("node", "way", "relation") or oid is None:
            continue
        if amenity not in ("university", "college"):
            continue
        if etype == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lng = center.get("lat"), center.get("lon")
        if lat is None or lng is None:
            continue
        cid = "osm_%s_%s" % (etype, oid)
        if cid in seen:
            continue
        seen.add(cid)
        centers.append({
            "id": cid,
            "name": tags.get("name") or ("University" if amenity == "university" else "College"),
            "kind": amenity,
            "latitude": float(lat),
            "longitude": float(lng),
            "source": "osm",
            "updated_at": datetime.utcnow().isoformat(),
        })
    return centers


@api_router.get("/activity-centers/nearby")
async def nearby_activity_centers(bbox: str = None, latitude: float = None, longitude: float = None, radius_km: float = 2.0):
    """Real university/college Activity Centers near a bbox or a point."""
    # Cleanup v1 fictional centers on every call (idempotent, cheap).
    await __DB__.activity_centers.delete_many({"id": {"$regex": "^activity_center_"}})
    await __DB__.activity_presence.delete_many({"center_id": {"$regex": "^activity_center_"}})
    if bbox:
        try:
            parts = [float(x) for x in bbox.split(",")]
            min_lng, min_lat, max_lng, max_lat = parts
        except Exception:
            raise HTTPException(status_code=400, detail="bbox must be minLng,minLat,maxLng,maxLat")
    elif latitude is not None and longitude is not None:
        dlat = radius_km / 111.0
        dlng = radius_km / (111.0 * max(0.2, math.cos(math.radians(latitude))))
        min_lat, max_lat = latitude - dlat, latitude + dlat
        min_lng, max_lng = longitude - dlng, longitude + dlng
    else:
        raise HTTPException(status_code=400, detail="Provide bbox or latitude/longitude")
    # Clamp absurd bboxes so one call cannot fan out over the planet.
    if max_lat - min_lat > 0.5 or max_lng - min_lng > 0.5:
        mid_lat = (min_lat + max_lat) / 2
        mid_lng = (min_lng + max_lng) / 2
        min_lat, max_lat = mid_lat - 0.25, mid_lat + 0.25
        min_lng, max_lng = mid_lng - 0.25, mid_lng + 0.25
    now = datetime.utcnow()
    for cell_key, cs, cw, cn, ce in _activity_center_cells(min_lat, min_lng, max_lat, max_lng):
        cached = await __DB__.activity_center_cache.find_one({"cell": cell_key})
        fresh = False
        if cached and cached.get("fetched_at"):
            try:
                fetched = cached["fetched_at"]
                if isinstance(fetched, str):
                    fetched = datetime.fromisoformat(fetched)
                fresh = (now - fetched).total_seconds() < ACTIVITY_CENTER_CACHE_SECONDS
            except Exception:
                fresh = False
        if fresh:
            continue
        centers = await _activity_center_fetch_cell(cell_key, cs, cw, cn, ce)
        if centers is None:
            continue
        for c in centers:
            await __DB__.activity_centers.update_one(
                {"id": c["id"]},
                {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                upsert=True,
            )
        await __DB__.activity_center_cache.update_one(
            {"cell": cell_key},
            {"$set": {"fetched_at": now.isoformat()}},
            upsert=True,
        )
    rows = await __DB__.activity_centers.find({
        "id": {"$regex": "^osm_"},
        "latitude": {"$gte": min_lat, "$lte": max_lat},
        "longitude": {"$gte": min_lng, "$lte": max_lng},
    }).to_list(500)
    for r in rows:
        r.pop("_id", None)
    return rows

'''

_PRESENCE_BLOCK = '''
# ACTIVITY_CENTER_PRESENCE: activity center presence (inside only).
# New collection activity_presence; never mixed with house_presence.
# Entry is OPEN TO EVERYONE — no friends check (unlike houses).
ACTIVITY_CENTER_PRESENCE_TTL_SECONDS = 180


def _activity_center_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


async def _activity_center_prune(center_id):
    from datetime import timedelta
    cutoff = _activity_center_now() - timedelta(seconds=ACTIVITY_CENTER_PRESENCE_TTL_SECONDS)
    await __DB__.activity_presence.delete_many({"center_id": center_id, "last_seen": {"$lt": cutoff}})


async def _activity_center_occupants(center_id):
    await _activity_center_prune(center_id)
    rows = await __DB__.activity_presence.find({"center_id": center_id}).to_list(100)
    occupants = []
    for r in rows:
        occupants.append({
            "player_id": r.get("player_id"),
            "player_name": r.get("player_name") or "Player",
            "entered_at": r.get("entered_at").isoformat() if r.get("entered_at") else None,
            "last_seen": r.get("last_seen").isoformat() if r.get("last_seen") else None,
        })
    return occupants


@api_router.post("/activity-centers/{center_id}/enter")
async def activity_center_enter(center_id: str, data: dict):
    player_id = data.get("player_id")
    player_name = data.get("player_name") or "Player"
    center = await __DB__.activity_centers.find_one({"id": center_id})
    if not center:
        raise HTTPException(status_code=404, detail="Activity Center not found")
    now = _activity_center_now()
    await __DB__.activity_presence.update_one(
        {"center_id": center_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _activity_center_occupants(center_id)}


@api_router.post("/activity-centers/{center_id}/leave")
async def activity_center_leave(center_id: str, data: dict):
    player_id = data.get("player_id")
    await __DB__.activity_presence.delete_one({"center_id": center_id, "player_id": player_id})
    return {"occupants": await _activity_center_occupants(center_id)}


@api_router.post("/activity-centers/{center_id}/heartbeat")
async def activity_center_heartbeat(center_id: str, data: dict):
    player_id = data.get("player_id")
    player_name = data.get("player_name") or "Player"
    center = await __DB__.activity_centers.find_one({"id": center_id})
    if not center:
        raise HTTPException(status_code=404, detail="Activity Center not found")
    now = _activity_center_now()
    await __DB__.activity_presence.update_one(
        {"center_id": center_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _activity_center_occupants(center_id)}


@api_router.get("/activity-centers/{center_id}/presence")
async def activity_center_presence(center_id: str):
    return {"occupants": await _activity_center_occupants(center_id)}

'''


def _remove_v1_spawn(src):
    """Remove the v1 fictional spawn endpoint block. Returns (new_src, ok)."""
    if "/activity-centers/spawn" not in src:
        return src, True
    # Primary: the v1 block sits directly before the restaurants spawn decorator.
    start = src.find("# ACTIVITY_CENTER: Activity Center spawn")
    rest_anchor = '@api_router.get("/restaurants/spawn")'
    end = src.find(rest_anchor)
    if start != -1 and end != -1 and start < end:
        return src[:start] + src[end:], True
    # Fallback: cut from the names list through the end of the spawn function.
    ns = src.find("ACTIVITY_CENTER_NAMES = [")
    if ns != -1:
        fe = src.find("return [center]", ns)
        if fe != -1:
            line_end = src.find("\n", fe)
            j = line_end + 1
            while j < len(src) and src[j] == "\n":
                j += 1
            cs = src.rfind("# ACTIVITY_CENTER: Activity Center spawn", 0, ns)
            start2 = cs if cs != -1 else ns
            return src[:start2] + src[j:], True
    return src, False


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - nothing changed")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    landed = []

    # DB handle detection (live code uses db; never guess silently).
    dm = re.search(r"\b(\w+)\.restaurants\.find", src)
    db = dm.group(1) if dm else "db"
    if not dm:
        print("WARNING: db handle anchor not found - assuming 'db'")

    # Part 0: httpx import (needed for the Overpass call).
    if "import httpx" in src:
        pass
    elif "import re\n" in src:
        src = src.replace("import re\n", "import re\nimport httpx\n", 1)
        print("ACTIVITY_CENTER_REAL_HTTPX_OK")
    else:
        print("WARNING: httpx import anchor not found - Overpass calls may fail (add 'import httpx' manually)")

    # Part 1: remove the v1 fictional spawn endpoint (cleanup).
    if "/activity-centers/spawn" not in src:
        print("ACTIVITY_CENTER_REAL_CLEANUP_NOT_NEEDED")
        landed.append("cleanup")
    else:
        new_src, ok = _remove_v1_spawn(src)
        if ok:
            src = new_src
            print("ACTIVITY_CENTER_REAL_CLEANUP_OK")
            landed.append("cleanup")
        else:
            print("WARNING: v1 spawn endpoint found but removal failed - fictional spawn stays (frontend no longer calls it)")

    # Part 2: nearby endpoint (before the restaurants spawn endpoint).
    if "/activity-centers/nearby" in src:
        print("ACTIVITY_CENTER_REAL_NEARBY_ALREADY_APPLIED")
        landed.append("nearby")
    else:
        anchor = '@api_router.get("/restaurants/spawn")'
        if anchor not in src:
            print("WARNING: restaurants spawn anchor not found - Activity Center nearby NOT added (no map source anchor)")
        else:
            src = src.replace(anchor, _NEARBY_BLOCK.replace("__DB__", db) + anchor, 1)
            print("ACTIVITY_CENTER_REAL_NEARBY_OK")
            landed.append("nearby")

    # Part 3: presence endpoints (before the router include).
    # NOTE: check for the enter function, NOT "activity_presence" — the
    # nearby block above already mentions activity_presence (cleanup),
    # which would falsely read as "already applied" on a pristine file.
    if "def activity_center_enter" in src:
        print("ACTIVITY_CENTER_REAL_PRESENCE_ALREADY_APPLIED")
        landed.append("presence")
    else:
        inc = re.search(r"^.*include_router\(api_router\).*$", src, re.M)
        if not inc:
            print("WARNING: router include anchor not found - presence endpoints SKIPPED")
        else:
            src = src[:inc.start()] + _PRESENCE_BLOCK.replace("__DB__", db) + "\n" + src[inc.start():]
            print("ACTIVITY_CENTER_REAL_PRESENCE_OK")
            landed.append("presence")

    if src == orig:
        if "activity_center_enter" in src and "/activity-centers/nearby" in src:
            print("ACTIVITY_CENTER_REAL_ALREADY_APPLIED")
        else:
            print("ACTIVITY_CENTER_REAL_PARTIAL: " + ",".join(landed))
        return 0

    # Syntax check before writing; restore on failure.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("ACTIVITY_CENTER_REAL_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if len(landed) == 3:
        print(MARKER)
    else:
        print("ACTIVITY_CENTER_REAL_PARTIAL: " + ",".join(landed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
