#!/usr/bin/env python3
"""Street Legends backend: Billboards on REAL highways / main roads.

Mirrors the Parks pattern (patch-park.py): real OSM data, ~0.05-degree
grid-cell cache for 24h, NO seeded/fictional fallback. The frontend
for this feature is built in parallel against the contract below —
this patch implements that contract exactly.

CONTRACT
  GET  /billboards/nearby?bbox=minLng,minLat,maxLng,maxLat
       (or ?latitude=..&longitude=..&radius_km=2.0, default 2.0)
       -> [{"id", "name", "road", "latitude", "longitude", "osm_type",
            "osm_id", "kind": "billboard", "source": "osm",
            "updated_at"}]
       id is "billboard_<osm way id>_<node index>" (stable across
       phones). Name/road from the OSM name tag, else the ref tag
       (e.g. "I-75"), else "Highway".

PLACEMENT — random places on REAL highways and main roads only:
  Overpass query: way["highway"~"^(motorway|trunk|primary|secondary)$"]
  with `out geom`, so a point can be picked ALONG the road (a plain
  `out center` would only give the way midpoint, which may sit outside
  the cell for a long highway). Residential / service / footway /
  cycleway / path ways are never queried, so no billboard can land on
  them. At most ONE billboard per way per cell, at most 5 per cell,
  and the endpoint thins a bbox's cached rows to 5, spread across
  roads. Placement is DETERMINISTIC per grid cell + way (sha256 seed),
  so the same billboard stays in the same spot across refetches and
  phones; the 5-per-fetch thinning is seeded by the bbox-center cell.

REAL DATA SOURCE — OpenStreetMap Overpass (free, no key, no billing):
  https://overpass-api.de/api/interpreter
Ways without geometry inside the cell are skipped; deduped by
billboard id. Rows live in a `billboards` collection, grid-cell
freshness in `billboard_cache` (24h). Failures are NOT cached.

NO-FALLBACK RULE: on Overpass error/timeout/empty, the endpoint
returns whatever real billboards are already cached in the DB for
that bbox (possibly an empty list). It NEVER invents seeded/fictional
billboards. Zero seeded names anywhere in this patch.

Run from /app:  python3 backend/patch-billboard.py
   or:  python3 backend/patch-billboard.py /path/to/app
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
MARKER = "BILLBOARD_BACKEND_OK"
ANCHOR = '@api_router.get("/missions/active/{player_id}")'

_BILLBOARD_BLOCK = '''
# BILLBOARD_NEARBY: billboards on real highways / main roads (OSM).
# NO seeded/fictional fallback: on Overpass error/timeout the endpoint
# returns what is cached in the DB for the bbox (possibly empty) — never
# fake billboards. Each ~0.05-degree grid cell is cached for 24h.
# Placement is DETERMINISTIC per grid cell + way (sha256 seed).
BILLBOARD_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
BILLBOARD_CACHE_SECONDS = 86400  # 24h per grid cell
BILLBOARD_CELL_DEG = 0.05
BILLBOARD_MAX_PER_FETCH = 5
BILLBOARD_HIGHWAYS = {"motorway", "trunk", "primary", "secondary"}


def _billboard_cells(min_lat, min_lng, max_lat, max_lng):
    import math
    cells = []
    i0 = math.floor(min_lat / BILLBOARD_CELL_DEG)
    i1 = math.floor(max_lat / BILLBOARD_CELL_DEG)
    j0 = math.floor(min_lng / BILLBOARD_CELL_DEG)
    j1 = math.floor(max_lng / BILLBOARD_CELL_DEG)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            cells.append((f"{i}_{j}", i * BILLBOARD_CELL_DEG, j * BILLBOARD_CELL_DEG,
                          (i + 1) * BILLBOARD_CELL_DEG, (j + 1) * BILLBOARD_CELL_DEG))
    return cells


def _billboard_overpass_query(s, w, n, e):
    # Overpass bbox order is (south, west, north, east). `out geom`
    # returns every way's node geometry so a point can be picked ALONG
    # the road (a plain `out center` would only give the way midpoint,
    # which may sit outside the cell for a long highway).
    return (
        "[out:json][timeout:25];\\n"
        "(\\n"
        f'  way["highway"~"^(motorway|trunk|primary|secondary)$"]({s},{w},{n},{e});\\n'
        ");\\n"
        "out geom;\\n"
    )


def _billboard_points_for_way(el, cell_key, cs, cw, cn, ce):
    """One deterministic billboard point along one OSM way, or None.
    Only highway=motorway/trunk/primary/secondary ways with geometry
    inside this cell qualify. The node index is seeded by cell + way
    id, so the same billboard lands in the same spot on every phone."""
    import hashlib
    import random
    if el.get("type") != "way":
        return None
    tags = el.get("tags") or {}
    if tags.get("highway") not in BILLBOARD_HIGHWAYS:
        return None
    geom = el.get("geometry") or []
    inside = [g for g in geom
              if g.get("lat") is not None and g.get("lon") is not None
              and cs <= g["lat"] <= cn and cw <= g["lon"] <= ce]
    if len(inside) < 2:
        return None
    way_id = el.get("id")
    seed = hashlib.sha256(f"{cell_key}:{way_id}".encode()).hexdigest()
    rng = random.Random(seed)
    idx = rng.randrange(len(inside))
    node = inside[idx]
    road = tags.get("name") or tags.get("ref") or "Highway"
    return {
        "id": "billboard_%s_%s" % (way_id, idx),
        "name": road,
        "road": road,
        "kind": "billboard",
        "latitude": float(node["lat"]),
        "longitude": float(node["lon"]),
        "osm_type": "way",
        "osm_id": way_id,
        "source": "osm",
        "updated_at": datetime.utcnow().isoformat(),
    }


def _billboard_select(rows, seed_key, limit=BILLBOARD_MAX_PER_FETCH):
    """Deterministically thin a bbox's cached rows to `limit`, spread
    across roads: one billboard per way first (rows are already at most
    one per way per cell, but a fetch can span cells and the same way
    can hold a point in each), then a seeded shuffle of the survivors.
    The seed is the bbox-center grid cell, so the same 5 stay put
    across refetches at the same spot."""
    import hashlib
    import random
    by_way = {}
    for r in rows:
        by_way.setdefault(r.get("osm_id"), r)
    pool = sorted(by_way.values(), key=lambda r: r["id"])
    if len(pool) <= limit:
        return pool
    seed = hashlib.sha256(str(seed_key).encode()).hexdigest()
    rng = random.Random(seed)
    rng.shuffle(pool)
    return sorted(pool[:limit], key=lambda r: r["id"])


async def _billboard_fetch_cell(cell_key, s, w, n, e):
    """Query Overpass for one grid cell. Returns a list of billboard
    dicts (at most one per way, up to 5), or None on any error (so the
    cell is NOT cached and retries next call)."""
    import hashlib
    import random
    query = _billboard_overpass_query(s, w, n, e)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(BILLBOARD_OVERPASS_URL, data={"data": query})
        if resp.status_code != 200:
            logging.warning("Overpass HTTP %s for billboard cell %s", resp.status_code, cell_key)
            return None
        payload = resp.json()
    except Exception as exc:
        logging.warning("Overpass error for billboard cell %s: %s", cell_key, exc)
        return None
    points = []
    seen = set()
    for el in payload.get("elements", []) or []:
        pt = _billboard_points_for_way(el, cell_key, s, w, n, e)
        if pt is None or pt["id"] in seen:
            continue
        seen.add(pt["id"])
        points.append(pt)
    # Spread: seeded shuffle of the cell's ways, keep at most 5.
    seed = hashlib.sha256(cell_key.encode()).hexdigest()
    rng = random.Random(seed)
    rng.shuffle(points)
    return points[:BILLBOARD_MAX_PER_FETCH]


@api_router.get("/billboards/nearby")
async def nearby_billboards(bbox: str = None, latitude: float = None, longitude: float = None, radius_km: float = 2.0):
    """Billboards on real highways/main roads near a bbox or a point."""
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
    for cell_key, cs, cw, cn, ce in _billboard_cells(min_lat, min_lng, max_lat, max_lng):
        cached = await __DB__.billboard_cache.find_one({"cell": cell_key})
        fresh = False
        if cached and cached.get("fetched_at"):
            try:
                fetched = cached["fetched_at"]
                if isinstance(fetched, str):
                    fetched = datetime.fromisoformat(fetched)
                fresh = (now - fetched).total_seconds() < BILLBOARD_CACHE_SECONDS
            except Exception:
                fresh = False
        if fresh:
            continue
        boards = await _billboard_fetch_cell(cell_key, cs, cw, cn, ce)
        if boards is None:
            continue
        for c in boards:
            await __DB__.billboards.update_one(
                {"id": c["id"]},
                {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                upsert=True,
            )
        await __DB__.billboard_cache.update_one(
            {"cell": cell_key},
            {"$set": {"fetched_at": now.isoformat()}},
            upsert=True,
        )
    rows = await __DB__.billboards.find({
        "id": {"$regex": "^billboard_"},
        "latitude": {"$gte": min_lat, "$lte": max_lat},
        "longitude": {"$gte": min_lng, "$lte": max_lng},
    }).to_list(500)
    for r in rows:
        r.pop("_id", None)
    center_key = "%s_%s" % (math.floor(((min_lat + max_lat) / 2) / BILLBOARD_CELL_DEG),
                            math.floor(((min_lng + max_lng) / 2) / BILLBOARD_CELL_DEG))
    return _billboard_select(rows, center_key)

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
        print("BILLBOARD_HTTPX_OK")
    else:
        print("WARNING: httpx import anchor not found - Overpass calls may fail (add 'import httpx' manually)")
        warned.append("httpx")

    if "import math" not in src:
        print("WARNING: 'import math' not found in server.py - billboard bbox math may fail at runtime")
        warned.append("math")

    # Part 1: nearby endpoint (before the missions/active anchor).
    if "/billboards/nearby" in src:
        print("BILLBOARD_NEARBY_ALREADY_APPLIED")
        landed.append("nearby")
    elif ANCHOR not in src:
        print("WARNING: missions/active anchor not found - billboard nearby NOT added")
        warned.append("nearby")
    else:
        src = src.replace(ANCHOR, _BILLBOARD_BLOCK.replace("__DB__", db) + ANCHOR, 1)
        print("BILLBOARD_NEARBY_OK")
        landed.append("nearby")

    if src == orig:
        if len(landed) == 1:
            print("BILLBOARD_BACKEND_ALREADY_APPLIED")
        else:
            print("BILLBOARD_BACKEND_PARTIAL: " + ",".join(landed))
        return 0

    # Syntax check before writing; restore on failure.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("BILLBOARD_BACKEND_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if len(landed) == 1 and not warned:
        print(MARKER)
    else:
        print("BILLBOARD_BACKEND_PARTIAL: " + ",".join(landed) + (" (warnings: " + ",".join(warned) + ")" if warned else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
