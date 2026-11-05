#!/usr/bin/env python3
"""Street Legends backend: Activity Centers at universities and colleges.

Phase 1 only — NO items, NO games, NO shop. Presence + map spawn only.

Why this shape: the snapshot has NO real university/college data source
(no Overpass/OSM/places API, no universities table — grep finds zero
university/college references). Real-world places in this game are already
seeded fakes: restaurants/banks/nightclubs are grid-seeded RNG names
persisted in DB collections (see spawn_restaurants). Activity centers
follow that exact pattern: one center per ~500m grid cell, EVERY cell
(no 40%-of-areas gate, so a center is always nearby), deterministic
grid-seeded id + name so every phone sees the SAME center at the SAME
place. Center id: "activity_center_{lat:.3f}_{lng:.3f}" of the grid cell.

Presence mirrors the house pattern (house_presence) but in a SEPARATE
collection activity_presence, and entry is OPEN TO EVERYONE — no
friends-only check anywhere on the backend. The friends+self filter for
the interior list lives on the frontend.

Run from /app: python3 backend/patch-activity-center.py
Backend only: Publish after running. Frontend patch is separate.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "ACTIVITY_CENTER_OK"

CENTER_NAMES = [
    "Riverside University", "Grandview College", "Cedar Hall University",
    "Northgate College", "Elmwood University", "Harborview College",
    "Maple State University", "Brookfield College", "Summit University",
    "Lakeside College", "Westfield University", "Oakridge College",
    "Hillcrest University", "Bayview College",
]


def _spawn_block(db):
    names = ",\n    ".join('"%s"' % n for n in CENTER_NAMES)
    return ('''
# ACTIVITY_CENTER: Activity Center spawn (universities/colleges).
# Seeded per grid cell like restaurants, but in EVERY cell, so a center
# is always nearby. Id is deterministic from the grid cell, so all
# phones agree on the same center (and the same presence room).
ACTIVITY_CENTER_NAMES = [
    %s,
]


@api_router.get("/activity-centers/spawn")
async def spawn_activity_centers(latitude: float, longitude: float, player_level: int = 1):
    """Spawn the Activity Center for this area — one per grid cell, always present."""
    grid_lat = round(latitude * 200) / 200  # ~500m grid cells
    grid_lng = round(longitude * 200) / 200
    center_id = "activity_center_{:.3f}_{:.3f}".format(grid_lat, grid_lng)
    existing = await DB.activity_centers.find_one({"id": center_id})
    if existing:
        existing.pop("_id", None)
        return [existing]
    area_seed = hash("activity_center_{}_{}".format(grid_lat, grid_lng))
    rng = random.Random(area_seed)
    center = {
        "id": center_id,
        "name": rng.choice(ACTIVITY_CENTER_NAMES),
        "kind": rng.choice(["university", "college"]),
        "latitude": latitude + rng.uniform(-0.002, 0.002),
        "longitude": longitude + rng.uniform(-0.002, 0.002),
        "created_at": datetime.utcnow().isoformat(),
    }
    await DB.activity_centers.insert_one(center)
    center.pop("_id", None)
    return [center]

''' % names).replace("DB.", db + ".")


def _presence_block(db):
    return '''
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
    await %(db)s.activity_presence.delete_many({"center_id": center_id, "last_seen": {"$lt": cutoff}})


async def _activity_center_occupants(center_id):
    await _activity_center_prune(center_id)
    rows = await %(db)s.activity_presence.find({"center_id": center_id}).to_list(100)
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
    center = await %(db)s.activity_centers.find_one({"id": center_id})
    if not center:
        raise HTTPException(status_code=404, detail="Activity Center not found")
    now = _activity_center_now()
    await %(db)s.activity_presence.update_one(
        {"center_id": center_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _activity_center_occupants(center_id)}


@api_router.post("/activity-centers/{center_id}/leave")
async def activity_center_leave(center_id: str, data: dict):
    player_id = data.get("player_id")
    await %(db)s.activity_presence.delete_one({"center_id": center_id, "player_id": player_id})
    return {"occupants": await _activity_center_occupants(center_id)}


@api_router.post("/activity-centers/{center_id}/heartbeat")
async def activity_center_heartbeat(center_id: str, data: dict):
    player_id = data.get("player_id")
    player_name = data.get("player_name") or "Player"
    center = await %(db)s.activity_centers.find_one({"id": center_id})
    if not center:
        raise HTTPException(status_code=404, detail="Activity Center not found")
    now = _activity_center_now()
    await %(db)s.activity_presence.update_one(
        {"center_id": center_id, "player_id": player_id},
        {"$set": {"player_name": player_name, "last_seen": now}, "$setOnInsert": {"entered_at": now}},
        upsert=True,
    )
    return {"occupants": await _activity_center_occupants(center_id)}


@api_router.get("/activity-centers/{center_id}/presence")
async def activity_center_presence(center_id: str):
    return {"occupants": await _activity_center_occupants(center_id)}

''' % {"db": db}


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

    # Part 1: spawn endpoint + names (before the restaurants spawn endpoint).
    if "/activity-centers/spawn" in src:
        print("ACTIVITY_CENTER_SPAWN_ALREADY_APPLIED")
        landed.append("spawn")
    else:
        anchor = '@api_router.get("/restaurants/spawn")'
        if anchor not in src:
            print("WARNING: restaurants spawn anchor not found - Activity Center spawn NOT added (no map source for centers)")
        else:
            src = src.replace(anchor, _spawn_block(db) + anchor, 1)
            print("ACTIVITY_CENTER_SPAWN_OK")
            landed.append("spawn")

    # Part 2: presence endpoints (before the router include).
    if "activity_presence" in src:
        print("ACTIVITY_CENTER_PRESENCE_ALREADY_APPLIED")
        landed.append("presence")
    else:
        inc = re.search(r"^.*include_router\(api_router\).*$", src, re.M)
        if not inc:
            print("WARNING: router include anchor not found - presence endpoints SKIPPED")
        else:
            src = src[:inc.start()] + _presence_block(db) + "\n" + src[inc.start():]
            print("ACTIVITY_CENTER_PRESENCE_OK")
            landed.append("presence")

    if src == orig:
        if "activity_center_enter" in src and "/activity-centers/spawn" in src:
            print("ACTIVITY_CENTER_ALREADY_APPLIED")
        else:
            print("ACTIVITY_CENTER_PARTIAL: " + ",".join(landed))
        return 0

    # Syntax check before writing; restore on failure.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("ACTIVITY_CENTER_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if len(landed) == 2:
        print(MARKER)
    else:
        print("ACTIVITY_CENTER_PARTIAL: " + ",".join(landed))
    return 0


if __name__ == "__main__":
    sys.exit(main())
