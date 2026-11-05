"""Street Legends backend: make the four OSM nearby endpoints fast + resilient.
Run from repo root: python3 backend/patch-osm-fast.py
Idempotent - safe to re-run.

DIAGNOSIS (2026-11-05, confirmed live by minigame-diag/diag-centers-hang.py):
  - GET /activity-centers/nearby hangs: 45s and 60s probes returned zero
    bytes while the player endpoint answered 200 in 0.7s.
  - Overpass probe from the Emergent terminal FAILED after 0.5s:
    URLError [Errno 111] Connection refused. Overpass is also saturated
    (502 "server at capacity" + 35s read timeouts seen from this VM).
  - STRUCTURAL CAUSE: each nearby handler awaits its grid cells
    SEQUENTIALLY, each with its own httpx timeout=30.0s -- worst case
    4 cells x 30s = 120s before the endpoint answers. Every map-entity
    refetch waits on that call, so the whole map stalls at 0 enemies.

FIX (this patch, backend only -- no frontend change; the frontend's 5s
per-call timeout already bounds the client side):
  1. PARALLEL cell fetches: asyncio.gather over the stale cells instead
     of await-in-loop. Same per-cell fetch function, same dedupe/merge,
     same cache collections, same response shapes/ids.
  2. SHORT timeouts + TOTAL BUDGET: per-cell httpx timeout 8s (was 30s);
     the gather is wrapped in asyncio.wait_for(10s) so the endpoint
     answers within ~10s worst case even if every mirror is down. A cell
     that times out/errors returns None (its cached rows are still served
     below); the endpoint NEVER hangs past the budget.
  3. MIRROR FALLBACK: each cell fetch tries overpass-api.de first, then
     overpass.kumi.systems on failure/timeout. First success wins.
     No other host is added.

SCOPE: all four nearby endpoints built on this template --
  activity-centers, pharmacies, parks, billboards. Each endpoint's
  fetch helper is duplicated (no shared helper exists), so each copy
  is patched. Presence/buy/sell endpoints, the OSM queries themselves,
  the response shapes/ids, the cache collections, the no-fallback rule
  (errors/empty return cached real rows or [], never fictional), the
  fine/cooldown/robbery code, and every frontend file are untouched.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OSM_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OSM_CELL_TIMEOUT = 8.0
OSM_TOTAL_BUDGET = 10.0

_SHARED_BLOCK = """
# OSM_FAST: parallel cell fetches + mirror fallback + total budget.
# Overpass (overpass-api.de) is refused/slow from this host and saturates
# under load; a sequential 4-cell x 30s loop took up to 120s per call.
# Per-cell httpx timeout is OSM_CELL_TIMEOUT; the gather for one nearby
# call is capped at OSM_TOTAL_BUDGET, so the endpoint answers in ~10s
# worst case. A cell that fails on every mirror returns None and is NOT
# cached (retries next call); cached rows are still served below.
OSM_OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OSM_CELL_TIMEOUT = 8.0    # seconds per cell fetch, per mirror
OSM_TOTAL_BUDGET = 10.0   # seconds for all cells of one nearby call


async def _osm_gather_cells(cells, fetch_fn):
    \"\"\"Fetch Overpass cells in parallel under a total budget.
    Returns a list aligned with `cells`; a cell that times out or
    errors yields None (its cached rows are still served below).\"\"\"
    import asyncio
    if not cells:
        return []
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *[fetch_fn(ck, cs, cw, cn, ce) for ck, cs, cw, cn, ce in cells],
                return_exceptions=True,
            ),
            timeout=OSM_TOTAL_BUDGET,
        )
    except asyncio.TimeoutError:
        logging.warning("OSM total budget %.1fs exceeded for %d cells",
                        OSM_TOTAL_BUDGET, len(cells))
        return [None] * len(cells)
    return [r if not isinstance(r, BaseException) else None for r in results]

"""

# Per-endpoint facts. `log` is the short label used in that endpoint's
# existing Overpass log lines (kept verbatim in the new mirror loop).
ENDPOINTS = [
    {
        "name": "activity-centers",
        "fetch_fn": "_activity_center_fetch_cell",
        "cells_fn": "_activity_center_cells",
        "handler_fn": "nearby_activity_centers",
        "url_const": "ACTIVITY_CENTER_OVERPASS_URL",
        "cache_coll": "activity_center_cache",
        "cache_seconds": "ACTIVITY_CENTER_CACHE_SECONDS",
        "rows_coll": "activity_centers",
        "result_var": "centers",
        "log": "cell",
    },
    {
        "name": "pharmacies",
        "fetch_fn": "_pharmacy_fetch_cell",
        "cells_fn": "_pharmacy_cells",
        "handler_fn": "nearby_pharmacies",
        "url_const": "PHARMACY_OVERPASS_URL",
        "cache_coll": "pharmacy_cache",
        "cache_seconds": "PHARMACY_CACHE_SECONDS",
        "rows_coll": "pharmacies",
        "result_var": "pharmacies",
        "log": "pharmacy cell",
    },
    {
        "name": "parks",
        "fetch_fn": "_park_fetch_cell",
        "cells_fn": "_park_cells",
        "handler_fn": "nearby_parks",
        "url_const": "PARK_OVERPASS_URL",
        "cache_coll": "park_cache",
        "cache_seconds": "PARK_CACHE_SECONDS",
        "rows_coll": "parks",
        "result_var": "parks",
        "log": "park cell",
    },
    {
        "name": "billboards",
        "fetch_fn": "_billboard_fetch_cell",
        "cells_fn": "_billboard_cells",
        "handler_fn": "nearby_billboards",
        "url_const": "BILLBOARD_OVERPASS_URL",
        "cache_coll": "billboard_cache",
        "cache_seconds": "BILLBOARD_CACHE_SECONDS",
        "rows_coll": "billboards",
        "result_var": "boards",
        "log": "billboard cell",
    },
]


def _fetch_replacement(ep):
    """Mirror-loop replacement for the try/except block inside a fetch cell."""
    log = ep["log"]
    return (
        "    # OSM_FAST: mirror fallback (primary, then kumi.systems).\n"
        "    payload = None\n"
        "    for _osm_url in OSM_OVERPASS_MIRRORS:\n"
        "        try:\n"
        "            async with httpx.AsyncClient(timeout=OSM_CELL_TIMEOUT) as client:\n"
        "                resp = await client.post(_osm_url, data={\"data\": query})\n"
        "            if resp.status_code != 200:\n"
        f"                logging.warning(\"Overpass HTTP %s for {log} %s via %s\", resp.status_code, cell_key, _osm_url)\n"
        "                continue\n"
        "            payload = resp.json()\n"
        "            break\n"
        "        except Exception as exc:\n"
        f"            logging.warning(\"Overpass error for {log} %s via %s: %s\", cell_key, _osm_url, exc)\n"
        "            continue\n"
        "    if payload is None:\n"
        "        return None\n"
    )


def _fetch_pattern(ep):
    """Regex for the original single-URL try/except block in a fetch cell."""
    url = re.escape(ep["url_const"])
    return re.compile(
        r"    try:\n"
        r"        async with httpx\.AsyncClient\(timeout=[0-9.]+\) as client:\n"
        r"            resp = await client\.post\(" + url + r", data=\{\"data\": query\}\)\n"
        r"        if resp\.status_code != 200:\n"
        r"            logging\.warning\([^\n]*\)\n"
        r"            return None\n"
        r"        payload = resp\.json\(\)\n"
        r"    except Exception as exc:\n"
        r"        logging\.warning\([^\n]*\)\n"
        r"        return None"
    )


def _loop_replacement(ep):
    """Two-phase replacement for the sequential cell loop in a handler."""
    cache_coll = ep["cache_coll"]
    cache_seconds = ep["cache_seconds"]
    rows_coll = ep["rows_coll"]
    result_var = ep["result_var"]
    cells_fn = ep["cells_fn"]
    fetch_fn = ep["fetch_fn"]
    return (
        "    _osm_stale = []\n"
        f"    for cell_key, cs, cw, cn, ce in {cells_fn}(min_lat, min_lng, max_lat, max_lng):\n"
        f"        cached = await __DB__.{cache_coll}.find_one({{\"cell\": cell_key}})\n"
        "        fresh = False\n"
        "        if cached and cached.get(\"fetched_at\"):\n"
        "            try:\n"
        "                fetched = cached[\"fetched_at\"]\n"
        "                if isinstance(fetched, str):\n"
        "                    fetched = datetime.fromisoformat(fetched)\n"
        f"                fresh = (now - fetched).total_seconds() < {cache_seconds}\n"
        "            except Exception:\n"
        "                fresh = False\n"
        "        if not fresh:\n"
        "            _osm_stale.append((cell_key, cs, cw, cn, ce))\n"
        "    # OSM_FAST: fetch stale cells in PARALLEL under a total budget\n"
        "    # (was sequential await-in-loop: 4 cells x 30s = 120s worst case).\n"
        f"    _osm_results = await _osm_gather_cells(_osm_stale, {fetch_fn})\n"
        f"    for (cell_key, cs, cw, cn, ce), {result_var} in zip(_osm_stale, _osm_results):\n"
        f"        if {result_var} is None:\n"
        "            continue\n"
        f"        for c in {result_var}:\n"
        f"            await __DB__.{rows_coll}.update_one(\n"
        "                {\"id\": c[\"id\"]},\n"
        "                {\"$set\": c, \"$setOnInsert\": {\"created_at\": now.isoformat()}},\n"
        "                upsert=True,\n"
        "            )\n"
        f"        await __DB__.{cache_coll}.update_one(\n"
        "            {\"cell\": cell_key},\n"
        "            {\"$set\": {\"fetched_at\": now.isoformat()}},\n"
        "            upsert=True,\n"
        "        )\n"
    )


def _loop_pattern(ep):
    """Regex for the sequential cell loop in a handler, from the loop
    header through the cache-stamp update_one. Checkpoints keep it
    anchored to this endpoint's own names."""
    cells_fn = re.escape(ep["cells_fn"])
    cache_coll = re.escape(ep["cache_coll"])
    cache_seconds = re.escape(ep["cache_seconds"])
    fetch_fn = re.escape(ep["fetch_fn"])
    result_var = re.escape(ep["result_var"])
    rows_coll = re.escape(ep["rows_coll"])
    return re.compile(
        r"    for cell_key, cs, cw, cn, ce in " + cells_fn + r"\(min_lat, min_lng, max_lat, max_lng\):"
        r"[\s\S]*?cached = await __DB__\." + cache_coll + r"\.find_one\(\{\"cell\": cell_key\}\)"
        r"[\s\S]*?fresh = \(now - fetched\)\.total_seconds\(\) < " + cache_seconds +
        r"[\s\S]*?" + result_var + r" = await " + fetch_fn + r"\(cell_key, cs, cw, cn, ce\)"
        r"[\s\S]*?for c in " + result_var + r":"
        r"[\s\S]*?await __DB__\." + rows_coll + r"\.update_one\("
        r"[\s\S]*?await __DB__\." + cache_coll + r"\.update_one\("
        r"[\s\S]*?upsert=True,\s*\)"
    )


def _scoped_has(src, def_line, needle, window=6000):
    """True if `needle` appears within `window` chars after `def_line`
    (scoped to one function -- never a file-wide ALREADY_APPLIED check)."""
    idx = src.find(def_line)
    if idx == -1:
        return None  # function not found at all
    return needle in src[idx:idx + window]


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    changed = []
    warnings = []

    # --- Shared block (once): mirrors + timeouts + gather helper --------
    if "OSM_OVERPASS_MIRRORS = [" in src:
        print("ALREADY_APPLIED: shared OSM_FAST block")
        shared_ok = True
    else:
        url_re = re.compile(
            r"^(ACTIVITY_CENTER_OVERPASS_URL|PHARMACY_OVERPASS_URL|PARK_OVERPASS_URL|BILLBOARD_OVERPASS_URL)"
            r' = "https://overpass-api\.de/api/interpreter"$',
            re.MULTILINE,
        )
        m = url_re.search(src)
        if not m:
            print("WARNING: shared OSM_FAST block anchor not found - no endpoint "
                  "was changed (looked for an *_OVERPASS_URL = "
                  "\"https://overpass-api.de/api/interpreter\" line)")
            warnings.append("shared-anchor")
            shared_ok = False
        else:
            src = src[:m.start()] + _SHARED_BLOCK.lstrip("\n") + "\n" + src[m.start():]
            changed.append("shared block")
            print("OK: shared OSM_FAST block added (mirrors, timeouts, gather)")
            shared_ok = True

    # --- Per endpoint: mirror fetch (A) + parallel loop (B) --------------
    for ep in ENDPOINTS:
        name = ep["name"]
        if not shared_ok:
            print(f"SKIPPED: {name} (shared block missing)")
            continue

        # Part A: mirror loop inside the fetch cell.
        already_a = _scoped_has(src, f"async def {ep['fetch_fn']}", "OSM_OVERPASS_MIRRORS", 2500)
        if already_a:
            print(f"ALREADY_APPLIED: {name} fetch mirror")
        elif already_a is None:
            print(f"WARNING: {name} fetch function not found - mirror NOT added "
                  f"(looked for 'async def {ep['fetch_fn']}')")
            warnings.append(f"{name}-fetch-fn")
        else:
            pat = _fetch_pattern(ep)
            if not pat.search(src):
                print(f"WARNING: {name} fetch try/except anchor not found - mirror NOT added "
                      f"(looked for the single-URL httpx post in {ep['fetch_fn']})")
                warnings.append(f"{name}-fetch-anchor")
            else:
                src = pat.sub(_fetch_replacement(ep), src, count=1)
                changed.append(f"{name} fetch")
                print(f"OK: {name} fetch mirror added (8s/cell, kumi fallback)")

        # Part B: parallel gather in the nearby handler.
        already_b = _scoped_has(src, f"async def {ep['handler_fn']}", "_osm_gather_cells", 6000)
        if already_b:
            print(f"ALREADY_APPLIED: {name} parallel loop")
        elif already_b is None:
            print(f"WARNING: {name} handler not found - parallel loop NOT added "
                  f"(looked for 'async def {ep['handler_fn']}')")
            warnings.append(f"{name}-handler")
        else:
            pat = _loop_pattern(ep)
            if not pat.search(src):
                print(f"WARNING: {name} sequential loop anchor not found - parallel loop NOT added "
                      f"(looked for the cell loop in {ep['handler_fn']})")
                warnings.append(f"{name}-loop-anchor")
            else:
                src = pat.sub(_loop_replacement(ep), src, count=1)
                changed.append(f"{name} loop")
                print(f"OK: {name} loop parallelized (gather, 10s total budget)")

    if changed:
        SERVER.write_text(src)
        import py_compile
        py_compile.compile(str(SERVER), doraise=True)
        print("Python syntax OK.")
    else:
        print("No changes (already applied or anchors missing).")
    if warnings:
        print("OSM_FAST_PARTIAL: " + ", ".join(changed) +
              ("" if changed else "nothing changed") +
              " (warnings: " + ", ".join(warnings) + ")")
    else:
        print("OSM_FAST_OK")


if __name__ == "__main__":
    main()
