#!/usr/bin/env python3
"""Street Legends backend: Parks on REAL OpenStreetMap locations.

Mirrors the Activity Centers v2 pattern (patch-activity-center-real.py)
and the Pharmacy pattern (patch-pharmacy.py): real OSM data,
~0.05-degree grid-cell cache for 24h, NO seeded/fictional fallback.
The frontend for this feature is built in parallel against the
contract below — this patch implements that contract exactly.

CONTRACT
  GET  /parks/nearby?bbox=minLng,minLat,maxLng,maxLat
       (or ?latitude=..&longitude=..&radius_km=2.0, default 2.0)
       -> [{"id", "name", "latitude", "longitude", "osm_type", "osm_id",
            "kind": "park", "source": "osm", "updated_at"}]
       id is "park_<osm type>_<osm id>" (stable across phones).
       Name from the OSM name tag, fallback "Park".
  POST /parks/{park_id}/enter     {player_id, player_name}
       -> {"occupants": [{player_id, player_name, name, entered_at, last_seen}]}
  POST /parks/{park_id}/leave     {player_id}
       -> {"occupants": [...]}
  POST /parks/{park_id}/heartbeat {player_id, player_name}
       -> {"occupants": [...]}
  GET  /parks/{park_id}/presence
       -> {"occupants": [...]}
  Presence collection: park_presence. Entry is OPEN TO EVERYONE —
  no friends check (like activity centers, unlike houses).
  Stale presence entries (>180s since last_seen) are pruned on read.

REAL DATA SOURCE — OpenStreetMap Overpass (free, no key, no billing):
  https://overpass-api.de/api/interpreter
  [out:json][timeout:25];(nwr["leisure"="park"](s,w,n,e););out center;
Ways/relations without a center point are skipped; deduped by OSM
type+id. Rows live in a `parks` collection, grid-cell freshness in
`park_cache` (24h). Failures are NOT cached.

NO-FALLBACK RULE: on Overpass error/timeout/empty, the endpoint returns
whatever real parks are already cached in the DB for that bbox
(possibly an empty list). It NEVER invents seeded/fictional parks.
Zero seeded names anywhere in this patch.

Run from /app:  python3 backend/patch-park.py
   or:  python3 backend/patch-park.py /path/to/app
Backend only: Publish after running. Frontend patch is separate.
Idempotent: rerun prints ALREADY_APPLIED per part, file unchanged.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
SERVER = ROOT / "backend" / "server.py"
MARKER = "PARK_BACKEND_OK"
ANCHOR = '@api_router.get("/missions/active/{player_id}")'

_NEARBY_BLOCK = '''
# PARK_NEARBY: real parks from OpenStreetMap.
# NO seeded/fictional fallback: on Overpass error/timeout the endpoint
# returns what is cached in the DB for the bbox (possibly empty) — never
# fake parks. Each ~0.05-degree grid cell is cached for 24h.
PARK_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
PARK_CACHE_SECONDS = 86400  # 24h per grid cell
PARK_CELL_DEG = 0.05


def _park_cells(min_lat, min_lng, max_lat, max_lng):
    import math
    cells = []
    i0 = math.floor(min_lat / PARK_CELL_DEG)
    i1 = math.floor(max_lat / PARK_CELL_DEG)
    j0 = math.floor(min_lng / PARK_CELL_DEG)
    j1 = math.floor(max_lng / PARK_CELL_DEG)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            cells.append((f"{i}_{j}", i * PARK_CELL_DEG, j * PARK_CELL_DEG,
                          (i + 1) * PARK_CELL_DEG, (j + 1) * PARK_CELL_DEG))
    return cells


def _park_overpass_query(s, w, n, e):
    # Overpass bbox order is (south, west, north, east).
    return (
        "[out:json][timeout:25];\\n"
        "(\\n"
        f'  nwr["leisure"="park"]({s},{w},{n},{e});\\n'
        ");\\n"
        "out center;\\n"
    )


async def _park_fetch_cell(cell_key, s, w, n, e):
    """Query Overpass for one grid cell. Returns a list of park dicts,
    or None on any error (so the cell is NOT cached and retries next call)."""
    query = _park_overpass_query(s, w, n, e)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(PARK_OVERPASS_URL, data={"data": query})
        if resp.status_code != 200:
            logging.warning("Overpass HTTP %s for park cell %s", resp.status_code, cell_key)
            return None
        payload = resp.json()
    except Exception as exc:
        logging.warning("Overpass error for park cell %s: %s", cell_key, exc)
        return None
    parks = []
    seen = set()
    for el in payload.get("elements", []) or []:
        etype = el.get("type")
        oid = el.get("id")
        tags = el.get("tags") or {}
        if etype not in ("node", "way", "relation") or oid is None:
            continue
        if tags.get("leisure") != "park":
            continue
        if etype == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lng = center.get("lat"), center.get("lon")
        if lat is None or lng is None:
            continue
        pid = "park_%s_%s" % (etype, oid)
        if pid in seen:
            continue
        seen.add(pid)
        parks.append({
            "id": pid,
            "name": tags.get("name") or "Park",
            "kind": "park",
            "latitude": float(lat),
            "longitude": float(lng),
            "osm_type": etype,
            "osm_id": oid,
            "source": "osm",
            "updated_at": datetime.utcnow().isoformat(),
        })
    return parks


@api_router.get("/parks/nearby")
async def nearby_parks(bbox: str = None, latitude: float = None, longitude: float = None, radius_km: float = 2.0):
    """Real parks near a bbox or a point (OpenStreetMap)."""
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
    for cell_key, cs, cw, cn, ce in _park_cells(min_lat, min_lng, max_lat, max_lng):
        cached = await __DB__.park_cache.find_one({"cell": cell_key})
        fresh = False
        if cached and cached.get("fetched_at"):
            try:
                fetched = cached["fetched_at"]
                if isinstance(fetched, str):
                    fetched = datetime.fromisoformat(fetched)
                fresh = (now - fetched).total_seconds() < PARK_CACHE_SECONDS
            except Exception:
                fresh = False
        if fresh:
            continue
        parks = await _park_fetch_cell(cell_key, cs, cw, cn, ce)
        if parks is None:
            continue
        for c in parks:
            await __DB__.parks.update_one(
                {"id": c["id"]},
                {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                upsert=True,
            )
        await __DB__.park_cache.update_one(
            {"cell": cell_key},
            {"$set": {"fetched_at": now.isoformat()}},
            upsert=True,
        )
    rows = await __DB__.parks.find({
        "id": {"$regex": "^park_"},
        "latitude": {"$gte": min_lat, "$lte": max_lat},
        "longitude": {"$gte": min_lng, "$lte": max_lng},
    }).to_list(500)
    for r in rows:
        r.pop("_id", None)
    return rows

'''

_PRESENCE_BLOCK = '''
# PARK_PRESENCE: park presence (inside only).
# New collection park_presence; never mixed with house_presence or
# activity_presence. Entry is OPEN TO EVERYONE — no friends check.
# Mirrors the activity-center presence endpoints exactly (same
# request/response shapes, same 180s stale prune).
PARK_PRESENCE_TTL_SECONDS = 180


def _park_now():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


async def _park_prune(park_id):
    from datetime import timedelta
    cutoff = _park_now() - timedelta(seconds=PARK_PRESENCE_TTL_SECONDS)
    await __DB__.park_presence.delete_many({"park_id": park_id, "last_seen": {"$lt": cutoff}})


async def _park_occupants(park_id):
    await _park_prune(park_id)
    rows = await __DB__.park_presence.find({"park_id": park_id}).to_list(100)
    occupants = []
    for r in rows:
        occupants.append({
            "player_id": r.get("player_id"),
            "player_name": r.get("player_name") or "Player",
            "name": r.get("player_name") or "Player",
            "entered_at": r.get("entered_at").isoformat() if r.get("entered_at") else None,
            "last_seen": r.get("last_seen").isoformat() if r.get("last_seen") else None,
        })
    return occupants


@api_router.post("/parks/{park_id}/enter")
async def park_enter(park_id: str, data: dict):
    player_id = data.get("player_id")
    player_name = data.get("player_name") or data.get("name") or "Player"
    park = await __DB__.parks.find_one({"id": park_id})
    if not park:
        raise HTTPException(status_code=404, detail="Park not found")
    now = _park_now()
    await __DB__.park_presence.update_one(
        {"park_id": park_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _park_occupants(park_id)}


@api_router.post("/parks/{park_id}/leave")
async def park_leave(park_id: str, data: dict):
    player_id = data.get("player_id")
    await __DB__.park_presence.delete_one({"park_id": park_id, "player_id": player_id})
    return {"occupants": await _park_occupants(park_id)}


@api_router.post("/parks/{park_id}/heartbeat")
async def park_heartbeat(park_id: str, data: dict):
    player_id = data.get("player_id")
    player_name = data.get("player_name") or data.get("name") or "Player"
    park = await __DB__.parks.find_one({"id": park_id})
    if not park:
        raise HTTPException(status_code=404, detail="Park not found")
    now = _park_now()
    await __DB__.park_presence.update_one(
        {"park_id": park_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _park_occupants(park_id)}


@api_router.get("/parks/{park_id}/presence")
async def park_presence(park_id: str):
    return {"occupants": await _park_occupants(park_id)}

'''


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - nothing changed")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    landed = []
    warned = []

    # DB handle detection (live code uses db; never guess silently).
    dm = re.search(r"\b(\w+)\.restaurants\.find", src)
    db = dm.group(1) if dm else "db"
    if not dm:
        print("WARNING: db handle anchor not found - assuming 'db'")
        warned.append("db-handle")

    # Part 0: httpx import (needed for the Overpass call).
    if "import httpx" in src:
        pass
    elif "import re\n" in src:
        src = src.replace("import re\n", "import re\nimport httpx\n", 1)
        print("PARK_HTTPX_OK")
    else:
        print("WARNING: httpx import anchor not found - Overpass calls may fail (add 'import httpx' manually)")
        warned.append("httpx")

    if "import math" not in src:
        print("WARNING: 'import math' not found in server.py - park bbox math may fail at runtime")
        warned.append("math")

    # Part 1: nearby endpoint (before the missions/active anchor).
    if "/parks/nearby" in src:
        print("PARK_NEARBY_ALREADY_APPLIED")
        landed.append("nearby")
    elif ANCHOR not in src:
        print("WARNING: missions/active anchor not found - park nearby NOT added")
        warned.append("nearby")
    else:
        src = src.replace(ANCHOR, _NEARBY_BLOCK.replace("__DB__", db) + ANCHOR, 1)
        print("PARK_NEARBY_OK")
        landed.append("nearby")

    # Part 2: presence endpoints (before the missions/active anchor).
    # NOTE: check for the enter function, NOT "park_presence" — the
    # nearby block above already mentions park_presence nowhere, but
    # the function-name check is the precise guard either way.
    if "def park_enter" in src:
        print("PARK_PRESENCE_ALREADY_APPLIED")
        landed.append("presence")
    elif ANCHOR not in src:
        print("WARNING: missions/active anchor not found - park presence NOT added")
        warned.append("presence")
    else:
        src = src.replace(ANCHOR, _PRESENCE_BLOCK.replace("__DB__", db) + ANCHOR, 1)
        print("PARK_PRESENCE_OK")
        landed.append("presence")

    if src == orig:
        if len(landed) == 2:
            print("PARK_BACKEND_ALREADY_APPLIED")
        else:
            print("PARK_BACKEND_PARTIAL: " + ",".join(landed))
        return 0

    # Syntax check before writing; restore on failure.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("PARK_BACKEND_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if len(landed) == 2 and not warned:
        print(MARKER)
    else:
        print("PARK_BACKEND_PARTIAL: " + ",".join(landed) + (" (warnings: " + ",".join(warned) + ")" if warned else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
