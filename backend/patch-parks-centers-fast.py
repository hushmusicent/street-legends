"""Street Legends backend: parks + activity centers return cached rows
immediately and refresh stale Overpass cells in the BACKGROUND.
Run from /app: python3 backend/patch-parks-centers-fast.py
Idempotent - safe to re-run.

ROOT CAUSE (verified live 2026-11-18): GET /api/parks/nearby and
GET /api/activity-centers/nearby BLOCK on Overpass for up to 10s
(OSM_TOTAL_BUDGET) whenever any grid cell is stale. The app's
ENTITY_TIMEOUT_MS is 5s, so the map query times out and returns []
- the park/center markers never load and tapping does nothing.
Measured at the user's location (Toledo 41.68226,-83.49344):
parks/nearby = 10.0s (7 parks exist), activity-centers/nearby = 10.4s
(and [] - no universities within the 2km radius; nearest are 5-10km).

FIX (same pattern the restaurants endpoint already uses): return the
cached DB rows immediately and kick off the Overpass refresh with
asyncio.create_task (deduped per cell via _osm_fetching). The next
map refresh picks up the fresh data. The endpoint becomes a plain
DB read (<1s) instead of a 10s Overpass wait.

CHANGES (backend/server.py):
1. New _refresh_park_cells_bg() helper + nearby_parks() kicks it off
   in the background instead of awaiting _osm_gather_cells.
2. New _refresh_center_cells_bg() helper + nearby_activity_centers()
   kicks it off in the background instead of awaiting
   _osm_gather_cells.
3. No change to the cache TTLs, the cell layout, or the response
   shape. No change to the 2km radius (centers genuinely have none
   within 2km of the user right now; nearest universities are 5-10km).

BACKEND change: run the curl, then Deploy (free). No new app build.
"""
import sys
from pathlib import Path

PATH = Path("backend/server.py")

# ---- Parks: background refresh helper (insert before nearby_parks) ----
PARK_HELPER_ANCHOR = '''@api_router.get("/parks/nearby")
async def nearby_parks('''

PARK_HELPER = '''async def _refresh_park_cells_bg(stale_cells):
    """Background Overpass refresh for stale park cells. Never blocks a
    map call: the endpoint returns cached rows immediately and this
    task warms the cache for the next refresh. Failures are swallowed
    (the cell stays stale and retries on a later call)."""
    try:
        results = await _osm_gather_cells(stale_cells, _park_fetch_cell)
        now = datetime.utcnow()
        for (cell_key, cs, cw, cn, ce), parks in zip(stale_cells, results):
            if not parks:
                continue
            for c in parks:
                await db.parks.update_one(
                    {"id": c["id"]},
                    {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                    upsert=True,
                )
            await db.park_cache.update_one(
                {"cell": cell_key},
                {"$set": {"fetched_at": now.isoformat(), "osm_epoch": OSM_CACHE_EPOCH}},
                upsert=True,
            )
    except Exception:
        pass
    finally:
        for cell_key, *_ in stale_cells:
            _osm_fetching.discard(f"park_{cell_key}")


@api_router.get("/parks/nearby")
async def nearby_parks('''

# ---- Parks: replace the blocking fetch with a background kick-off ----
PARK_BLOCK_ANCHOR = """    # OSM_PARALLEL: fetch stale cells in PARALLEL under the shared 10s
    # budget (was sequential await-in-loop: 4 cells x 8s = 32s worst case).
    _osm_results = await _osm_gather_cells(_osm_stale, _park_fetch_cell)
    for (cell_key, cs, cw, cn, ce), parks in zip(_osm_stale, _osm_results):
        if not parks:
            continue
        for c in parks:
            await db.parks.update_one(
                {"id": c["id"]},
                {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                upsert=True,
            )
        await db.park_cache.update_one(
            {"cell": cell_key},
            {"$set": {"fetched_at": now.isoformat(), "osm_epoch": OSM_CACHE_EPOCH}},
            upsert=True,
        )
"""

PARK_BLOCK_NEW = """    # PARKS_FAST: never block the map on Overpass (the app times out at
    # 5s, Overpass takes up to 10s). Return cached rows immediately and
    # refresh stale cells in the background; the next refresh picks
    # them up. Same pattern as the restaurants endpoint.
    if _osm_stale:
        _park_todo = []
        for _cell in _osm_stale:
            _key = f"park_{_cell[0]}"
            if _key not in _osm_fetching:
                _osm_fetching.add(_key)
                _park_todo.append(_cell)
        if _park_todo:
            asyncio.create_task(_refresh_park_cells_bg(_park_todo))
"""

# ---- Centers: background refresh helper (insert before nearby_activity_centers) ----
CENTER_HELPER_ANCHOR = '''@api_router.get("/activity-centers/nearby")
async def nearby_activity_centers('''

CENTER_HELPER = '''async def _refresh_center_cells_bg(stale_cells):
    """Background Overpass refresh for stale activity-center cells.
    Same pattern as parks: never blocks a map call."""
    try:
        results = await _osm_gather_cells(stale_cells, _activity_center_fetch_cell)
        now = datetime.utcnow()
        for (cell_key, cs, cw, cn, ce), centers in zip(stale_cells, results):
            if not centers:
                continue
            for c in centers:
                await db.activity_centers.update_one(
                    {"id": c["id"]},
                    {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                    upsert=True,
                )
            await db.activity_center_cache.update_one(
                {"cell": cell_key},
                {"$set": {"fetched_at": now.isoformat(), "osm_epoch": OSM_CACHE_EPOCH}},
                upsert=True,
            )
    except Exception:
        pass
    finally:
        for cell_key, *_ in stale_cells:
            _osm_fetching.discard(f"center_{cell_key}")


@api_router.get("/activity-centers/nearby")
async def nearby_activity_centers('''

# ---- Centers: replace the blocking fetch with a background kick-off ----
CENTER_BLOCK_ANCHOR = """    # OSM_PARALLEL: fetch stale cells in PARALLEL under the shared 10s
    # budget (was sequential await-in-loop: 4 cells x 8s = 32s worst case).
    _osm_results = await _osm_gather_cells(_osm_stale, _activity_center_fetch_cell)
    for (cell_key, cs, cw, cn, ce), centers in zip(_osm_stale, _osm_results):
        if not centers:
            continue
        for c in centers:
            await db.activity_centers.update_one(
                {"id": c["id"]},
                {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                upsert=True,
            )
        await db.activity_center_cache.update_one(
            {"cell": cell_key},
            {"$set": {"fetched_at": now.isoformat(), "osm_epoch": OSM_CACHE_EPOCH}},
            upsert=True,
        )
"""

CENTER_BLOCK_NEW = """    # CENTERS_FAST: never block the map on Overpass (same 10s vs 5s
    # timeout problem as parks). Return cached rows immediately and
    # refresh stale cells in the background.
    if _osm_stale:
        _center_todo = []
        for _cell in _osm_stale:
            _key = f"center_{_cell[0]}"
            if _key not in _osm_fetching:
                _osm_fetching.add(_key)
                _center_todo.append(_cell)
        if _center_todo:
            asyncio.create_task(_refresh_center_cells_bg(_center_todo))
"""


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from /app.")
        sys.exit(1)
    src = PATH.read_text()
    steps = [
        ("park helper", PARK_HELPER_ANCHOR, PARK_HELPER),
        ("park background kick-off", PARK_BLOCK_ANCHOR, PARK_BLOCK_NEW),
        ("center helper", CENTER_HELPER_ANCHOR, CENTER_HELPER),
        ("center background kick-off", CENTER_BLOCK_ANCHOR, CENTER_BLOCK_NEW),
    ]
    for desc, old, new in steps:
        if new in src:
            print(f"SKIP: {desc} (already applied)")
        elif src.count(old) == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {desc}")
        else:
            print(f"WARNING: anchor matched {src.count(old)}x — {desc}")
    PATH.write_text(src)
    print("PARKS_CENTERS_FAST_OK")


if __name__ == "__main__":
    main()
