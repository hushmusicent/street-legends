#!/usr/bin/env python3
"""Street Legends backend: Pharmacies on REAL OpenStreetMap locations.

Mirrors the Activity Centers v2 pattern (patch-activity-center-real.py):
real OSM data, ~0.05-degree grid-cell cache for 24h, NO seeded/fictional
fallback. The frontend for this feature is built in parallel against the
contract below — this patch implements that contract exactly.

CONTRACT
  GET  /pharmacies/nearby?bbox=minLng,minLat,maxLng,maxLat
       (or ?latitude=..&longitude=..&radius_km=2.0, default 2.0)
       -> [{"id", "name", "kind": "pharmacy", "latitude", "longitude",
            "source": "osm", "updated_at"}]
       id is "pharm_<osm type>_<osm id>" (stable across phones).
       Name from the OSM name tag, fallback "Pharmacy".
  POST /pharmacies/buy  {player_id, item_id, qty=1, request_id}
       -> {"message", "item_id", "name", "qty", "unit_price" (regular),
           "price_paid", "cash", "oz_held"}
  POST /pharmacies/sell {player_id, item_id, qty=1, request_id}
       -> {"message", "item_id", "name", "qty", "unit_price" (half price),
           "cash_gained", "cash", "oz_left"}

PRICES (regular / pharmacy sell = 50% less, per oz):
  Grass $100/$50, Pills $200/$100, Rock Candy $300/$150,
  Flake $400/$200, Brown Sugar $500/$250.

REAL DATA SOURCE — OpenStreetMap Overpass (free, no key, no billing):
  https://overpass-api.de/api/interpreter
  [out:json][timeout:25];(nwr["amenity"="pharmacy"](s,w,n,e););out center;
Ways/relations without a center point are skipped; deduped by OSM
type+id. Rows live in a `pharmacies` collection, grid-cell freshness in
`pharmacy_cache` (24h). Failures are NOT cached.

NO-FALLBACK RULE: on Overpass error/timeout/empty, the endpoint returns
whatever real pharmacies are already cached in the DB for that bbox
(possibly an empty list). It NEVER invents seeded/fictional pharmacies.
Zero seeded names anywhere in this patch.

IDEMPOTENCY (buy and sell): the client MUST send `request_id` (a uuid
string). A missing request_id is rejected with HTTP 400 — the server
never auto-generates one, or a retry would double-charge. Design is
claim -> apply -> mark-complete, all in the `pharmacy_tx` collection:
  1. CLAIM: atomic upsert update_one({"request_id": ...},
     {"$setOnInsert": {full request + status "processing" + created_at}},
     upsert=True). Only the first call for a request_id inserts
     (upserted_id is not None); a later call finds the existing record.
  2. APPLY: the winner applies the cash/inventory effect exactly once.
  3. MARK COMPLETE: the tx record is updated to status "complete"
     with the stored result dict.
  Retry of a COMPLETED tx returns the STORED result with no cash or
  inventory movement. Retry of a CLAIMED-BUT-INCOMPLETE tx (process
  died between claim and apply) returns HTTP 409 "already processing"
  and does NOT re-apply — it can never double-charge or double-pay.
  A stuck "processing" record (crashed mid-apply) stays 409 until it
  is cleared manually or expires; it is never auto-retried into a
  second apply. Validation (bad item, bad qty, missing player,
  insufficient cash/holdings) happens BEFORE the claim, so a 400 does
  not consume the request_id — the client may retry the same
  request_id after fixing the problem.
  Known limit (same as the fiend pattern): there is no multi-document
  transaction, so two DIFFERENT request_ids racing the same player
  could both pass the pre-claim cash/holdings check; the claim only
  dedupes identical request_ids.

Run from /app:  python3 backend/patch-pharmacy.py
   or:  python3 backend/patch-pharmacy.py /path/to/app
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
MARKER = "PHARMACY_BACKEND_OK"
ANCHOR = '@api_router.get("/missions/active/{player_id}")'

_DEFS_BLOCK = '''
# PHARMACY: real-world pharmacies from OpenStreetMap (Overpass).
# Prices are (display name, regular buy price, pharmacy sell price
# = 50% of regular), per oz. Same five enemy-drop items as the Fiends.
PHARMACY_ITEMS = {
    "grass": ("Grass", 100, 50),
    "pills": ("Pills", 200, 100),
    "rock_candy": ("Rock Candy", 300, 150),
    "flake": ("Flake", 400, 200),
    "brown_sugar": ("Brown Sugar", 500, 250),
}
PHARMACY_ITEM_IDS = ["grass", "pills", "rock_candy", "flake", "brown_sugar"]
PHARMACY_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
PHARMACY_CACHE_SECONDS = 86400  # 24h per grid cell
PHARMACY_CELL_DEG = 0.05


def _pharmacy_inventory_qty(inv, item_id):
    """Oz of item_id in a stacked inventory (dicts or bare strings)."""
    for _it in inv:
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            return _it.get("qty", 1)
        if isinstance(_it, str) and _it == item_id:
            return 1
    return 0


def _pharmacy_deduct(inv, item_id, qty):
    """Deduct qty oz of item_id from inv in place; returns oz left."""
    for _i, _it in enumerate(inv):
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            have = _it.get("qty", 1)
            if have <= qty:
                inv.pop(_i)
                return 0
            inv[_i]["qty"] = have - qty
            return have - qty
        if isinstance(_it, str) and _it == item_id:
            inv.pop(_i)
            return 0
    return 0


def _pharmacy_add(inv, item_id, qty):
    """Add qty oz of item_id to the stacked inventory; returns oz held."""
    for _i, _it in enumerate(inv):
        if isinstance(_it, dict) and _it.get("item_id") == item_id:
            inv[_i]["qty"] = _it.get("qty", 1) + qty
            return inv[_i]["qty"]
        if isinstance(_it, str) and _it == item_id:
            # Bare-string entry holds 1 oz; convert to a stacked dict.
            inv[_i] = {"item_id": item_id, "qty": 1 + qty, "unit": "oz"}
            return 1 + qty
    inv.append({"item_id": item_id, "qty": qty, "unit": "oz"})
    return qty


async def _pharmacy_claim(request_id, kind, player_id, item_id, qty):
    """Idempotency claim for one buy/sell request.

    Returns None if this call won the claim and may apply the effect.
    Returns the stored result dict if the tx already completed.
    Raises HTTP 409 if the tx exists but is still processing (claimed
    by an earlier call that has not marked complete yet) — the caller
    must retry with the SAME request_id, never a new one.
    """
    _now = datetime.utcnow().isoformat()
    claim = await __DB__.pharmacy_tx.update_one(
        {"request_id": request_id},
        {"$setOnInsert": {
            "request_id": request_id, "kind": kind, "player_id": player_id,
            "item_id": item_id, "qty": qty, "status": "processing",
            "created_at": _now,
        }},
        upsert=True,
    )
    if claim.upserted_id is not None:
        return None
    existing = await __DB__.pharmacy_tx.find_one({"request_id": request_id})
    if existing and existing.get("status") == "complete" and existing.get("result") is not None:
        return existing["result"]
    raise HTTPException(
        status_code=409,
        detail="This request_id is already being processed - retry with the same request_id, do not create a new one",
    )


async def _pharmacy_complete(request_id, result):
    """Mark a claimed tx complete and store its result for replays."""
    await __DB__.pharmacy_tx.update_one(
        {"request_id": request_id},
        {"$set": {"status": "complete", "result": result}},
    )

'''

_NEARBY_BLOCK = '''
# PHARMACY_NEARBY: real pharmacies from OpenStreetMap.
# NO seeded/fictional fallback: on Overpass error/timeout the endpoint
# returns what is cached in the DB for the bbox (possibly empty) — never
# fake pharmacies. Each ~0.05-degree grid cell is cached for 24h.
def _pharmacy_cells(min_lat, min_lng, max_lat, max_lng):
    import math
    cells = []
    i0 = math.floor(min_lat / PHARMACY_CELL_DEG)
    i1 = math.floor(max_lat / PHARMACY_CELL_DEG)
    j0 = math.floor(min_lng / PHARMACY_CELL_DEG)
    j1 = math.floor(max_lng / PHARMACY_CELL_DEG)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            cells.append((f"{i}_{j}", i * PHARMACY_CELL_DEG, j * PHARMACY_CELL_DEG,
                          (i + 1) * PHARMACY_CELL_DEG, (j + 1) * PHARMACY_CELL_DEG))
    return cells


def _pharmacy_overpass_query(s, w, n, e):
    # Overpass bbox order is (south, west, north, east).
    return (
        "[out:json][timeout:25];\\n"
        "(\\n"
        f'  nwr["amenity"="pharmacy"]({s},{w},{n},{e});\\n'
        ");\\n"
        "out center;\\n"
    )


async def _pharmacy_fetch_cell(cell_key, s, w, n, e):
    """Query Overpass for one grid cell. Returns a list of pharmacy
    dicts, or None on any error (so the cell is NOT cached and retries
    next call)."""
    query = _pharmacy_overpass_query(s, w, n, e)
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(PHARMACY_OVERPASS_URL, data={"data": query})
        if resp.status_code != 200:
            logging.warning("Overpass HTTP %s for pharmacy cell %s", resp.status_code, cell_key)
            return None
        payload = resp.json()
    except Exception as exc:
        logging.warning("Overpass error for pharmacy cell %s: %s", cell_key, exc)
        return None
    pharmacies = []
    seen = set()
    for el in payload.get("elements", []) or []:
        etype = el.get("type")
        oid = el.get("id")
        tags = el.get("tags") or {}
        if etype not in ("node", "way", "relation") or oid is None:
            continue
        if tags.get("amenity") != "pharmacy":
            continue
        if etype == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lng = center.get("lat"), center.get("lon")
        if lat is None or lng is None:
            continue
        pid = "pharm_%s_%s" % (etype, oid)
        if pid in seen:
            continue
        seen.add(pid)
        pharmacies.append({
            "id": pid,
            "name": tags.get("name") or "Pharmacy",
            "kind": "pharmacy",
            "latitude": float(lat),
            "longitude": float(lng),
            "source": "osm",
            "updated_at": datetime.utcnow().isoformat(),
        })
    return pharmacies


@api_router.get("/pharmacies/nearby")
async def nearby_pharmacies(bbox: str = None, latitude: float = None, longitude: float = None, radius_km: float = 2.0):
    """Real pharmacies near a bbox or a point (OpenStreetMap)."""
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
    for cell_key, cs, cw, cn, ce in _pharmacy_cells(min_lat, min_lng, max_lat, max_lng):
        cached = await __DB__.pharmacy_cache.find_one({"cell": cell_key})
        fresh = False
        if cached and cached.get("fetched_at"):
            try:
                fetched = cached["fetched_at"]
                if isinstance(fetched, str):
                    fetched = datetime.fromisoformat(fetched)
                fresh = (now - fetched).total_seconds() < PHARMACY_CACHE_SECONDS
            except Exception:
                fresh = False
        if fresh:
            continue
        pharmacies = await _pharmacy_fetch_cell(cell_key, cs, cw, cn, ce)
        if pharmacies is None:
            continue
        for c in pharmacies:
            await __DB__.pharmacies.update_one(
                {"id": c["id"]},
                {"$set": c, "$setOnInsert": {"created_at": now.isoformat()}},
                upsert=True,
            )
        await __DB__.pharmacy_cache.update_one(
            {"cell": cell_key},
            {"$set": {"fetched_at": now.isoformat()}},
            upsert=True,
        )
    rows = await __DB__.pharmacies.find({
        "id": {"$regex": "^pharm_"},
        "latitude": {"$gte": min_lat, "$lte": max_lat},
        "longitude": {"$gte": min_lng, "$lte": max_lng},
    }).to_list(500)
    for r in rows:
        r.pop("_id", None)
    return rows

'''

_BUY_BLOCK = '''
# PHARMACY_BUY: buy the five enemy-drop items at the regular price.
# Idempotent on request_id (claim -> apply -> mark-complete; see
# _pharmacy_claim). Validation happens BEFORE the claim, so a 400
# does not consume the request_id.
@api_router.post("/pharmacies/buy")
async def pharmacy_buy(data: dict):
    """Buy qty oz of an item at a pharmacy for the regular price."""
    player_id = data.get("player_id")
    item_id = data.get("item_id")
    qty = data.get("qty", 1)
    request_id = data.get("request_id")
    if not request_id or not isinstance(request_id, str):
        raise HTTPException(status_code=400, detail="request_id is required (client-generated uuid) - retries must reuse the same request_id")
    if item_id not in PHARMACY_ITEMS:
        raise HTTPException(status_code=400, detail="Unknown item_id - pharmacies only sell grass, pills, rock_candy, flake, brown_sugar")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1:
        raise HTTPException(status_code=400, detail="Quantity must be an integer of at least 1")
    player = await __DB__.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    name, regular_price, _sell_price = PHARMACY_ITEMS[item_id]
    price_paid = regular_price * qty
    if player.get("cash", 0) < price_paid:
        raise HTTPException(status_code=400, detail=f"Not enough cash - need ${price_paid}")
    stored = await _pharmacy_claim(request_id, "buy", player_id, item_id, qty)
    if stored is not None:
        return stored
    inv = player.get("inventory", [])
    oz_held = _pharmacy_add(inv, item_id, qty)
    new_cash = player.get("cash", 0) - price_paid
    await __DB__.players.update_one(
        {"id": player_id},
        {"$set": {"inventory": inv}, "$inc": {"cash": -price_paid}},
    )
    result = {
        "message": f"Bought {qty} oz of {name} for ${price_paid}",
        "item_id": item_id, "name": name, "qty": qty,
        "unit_price": regular_price, "price_paid": price_paid,
        "cash": new_cash, "oz_held": oz_held,
    }
    await _pharmacy_complete(request_id, result)
    return result

'''

_SELL_BLOCK = '''
# PHARMACY_SELL: sell the five enemy-drop items at 50% of regular price.
# Idempotent on request_id (claim -> apply -> mark-complete; see
# _pharmacy_claim). Validation happens BEFORE the claim, so a 400
# does not consume the request_id.
@api_router.post("/pharmacies/sell")
async def pharmacy_sell(data: dict):
    """Sell qty oz of an item at a pharmacy for half the regular price."""
    player_id = data.get("player_id")
    item_id = data.get("item_id")
    qty = data.get("qty", 1)
    request_id = data.get("request_id")
    if not request_id or not isinstance(request_id, str):
        raise HTTPException(status_code=400, detail="request_id is required (client-generated uuid) - retries must reuse the same request_id")
    if item_id not in PHARMACY_ITEMS:
        raise HTTPException(status_code=400, detail="Unknown item_id - pharmacies only buy grass, pills, rock_candy, flake, brown_sugar")
    if not isinstance(qty, int) or isinstance(qty, bool) or qty < 1:
        raise HTTPException(status_code=400, detail="Quantity must be an integer of at least 1")
    player = await __DB__.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    name, _regular_price, sell_price = PHARMACY_ITEMS[item_id]
    inv = player.get("inventory", [])
    held = _pharmacy_inventory_qty(inv, item_id)
    if held < qty:
        raise HTTPException(status_code=400, detail=f"Not enough {name} in inventory - need {qty} oz")
    stored = await _pharmacy_claim(request_id, "sell", player_id, item_id, qty)
    if stored is not None:
        return stored
    oz_left = _pharmacy_deduct(inv, item_id, qty)
    cash_gained = sell_price * qty
    new_cash = player.get("cash", 0) + cash_gained
    await __DB__.players.update_one(
        {"id": player_id},
        {"$set": {"inventory": inv}, "$inc": {"cash": cash_gained}},
    )
    result = {
        "message": f"Sold {qty} oz of {name} for ${cash_gained}",
        "item_id": item_id, "name": name, "qty": qty,
        "unit_price": sell_price, "cash_gained": cash_gained,
        "cash": new_cash, "oz_left": oz_left,
    }
    await _pharmacy_complete(request_id, result)
    return result

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
        print("PHARMACY_HTTPX_OK")
    else:
        print("WARNING: httpx import anchor not found - Overpass calls may fail (add 'import httpx' manually)")
        warned.append("httpx")

    if "import math" not in src:
        print("WARNING: 'import math' not found in server.py - pharmacy bbox math may fail at runtime")
        warned.append("math")

    # Part 1: shared price table + inventory/idempotency helpers.
    if "PHARMACY_ITEMS" in src and "def _pharmacy_claim" in src:
        print("PHARMACY_DEFS_ALREADY_APPLIED")
        landed.append("defs")
    elif ANCHOR not in src:
        print("WARNING: missions/active anchor not found - pharmacy defs NOT added")
        warned.append("defs")
    else:
        src = src.replace(ANCHOR, _DEFS_BLOCK.replace("__DB__", db) + ANCHOR, 1)
        print("PHARMACY_DEFS_OK")
        landed.append("defs")

    # Part 2: nearby endpoint.
    if "/pharmacies/nearby" in src:
        print("PHARMACY_NEARBY_ALREADY_APPLIED")
        landed.append("nearby")
    elif ANCHOR not in src:
        print("WARNING: missions/active anchor not found - pharmacy nearby NOT added")
        warned.append("nearby")
    else:
        src = src.replace(ANCHOR, _NEARBY_BLOCK.replace("__DB__", db) + ANCHOR, 1)
        print("PHARMACY_NEARBY_OK")
        landed.append("nearby")

    # Part 3: buy endpoint.
    if "/pharmacies/buy" in src:
        print("PHARMACY_BUY_ALREADY_APPLIED")
        landed.append("buy")
    elif ANCHOR not in src:
        print("WARNING: missions/active anchor not found - pharmacy buy NOT added")
        warned.append("buy")
    else:
        src = src.replace(ANCHOR, _BUY_BLOCK.replace("__DB__", db) + ANCHOR, 1)
        print("PHARMACY_BUY_OK")
        landed.append("buy")

    # Part 4: sell endpoint.
    if "/pharmacies/sell" in src:
        print("PHARMACY_SELL_ALREADY_APPLIED")
        landed.append("sell")
    elif ANCHOR not in src:
        print("WARNING: missions/active anchor not found - pharmacy sell NOT added")
        warned.append("sell")
    else:
        src = src.replace(ANCHOR, _SELL_BLOCK.replace("__DB__", db) + ANCHOR, 1)
        print("PHARMACY_SELL_OK")
        landed.append("sell")

    if src == orig:
        if len(landed) == 4:
            print("PHARMACY_BACKEND_ALREADY_APPLIED")
        else:
            print("PHARMACY_BACKEND_PARTIAL: " + ",".join(landed))
        return 0

    # Syntax check before writing; restore on failure.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("PHARMACY_BACKEND_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if len(landed) == 4 and not warned:
        print(MARKER)
    else:
        print("PHARMACY_BACKEND_PARTIAL: " + ",".join(landed) + (" (warnings: " + ",".join(warned) + ")" if warned else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
