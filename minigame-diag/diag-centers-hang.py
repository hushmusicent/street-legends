#!/usr/bin/env python3
"""Street Legends Activity Centers HANG diag (prints only; never edits files).

SYMPTOM (2026-11-05 16:11 EST, measured from this VM):
  GET /api/activity-centers/nearby?latitude=41.65431&longitude=-83.62055
  &radius_km=2 hangs -- two attempts (60s and 45s timeouts) returned ZERO
  bytes, HTTP 000 -- while GET /api/players/<id> returns 200 in 0.7s.
  The user sees NO activity center (University of Toledo is ~0.5 km east,
  well inside the 2 km radius), but the rest of the map loads (5 enemies,
  3 missions, a Fiend), so the centers call specifically never resolves.

WHAT THIS DIAG CHECKS (in order), run from /app:
  python3 minigame-diag/diag-centers-hang.py
  0. The bbox + grid cells for his position, and the worst-case latency
     implied by the handler's own per-cell timeout (cells x timeout).
  1. The nearby handler's exact lines in live backend/server.py: route,
     Overpass fetch block (URL, timeout, await, exception path), and whether
     the cell loop awaits each fetch SEQUENTIALLY (the prime hang shape:
     N cells x 30s each = up to ~120s, longer than the 45s/60s probes).
     Also flags any other unbounded construct (while True, a second HTTP
     call without timeout, a blocking time.sleep in async code).
  2. Whether the live handler IS the patched v2 code (marker strings).
  3. Overpass reachability FROM /app: a timed POST with the exact query the
     handler uses for his bbox (status + elapsed + element count), plus a
     tiny probe if that is slow/failing, to tell "Overpass is slow" apart
     from "this query is slow".
  4. Cache state for his grid cells (activity_center_cache + cached
     osm_* rows) -- read-only finds.
  5. A direct in-process call of the handler (import backend/server.py and
     call nearby_activity_centers with his lat/lng under a 35s budget).
     Importing the module only defines the app; it does NOT start the
     server. The handler call itself is the same call the game makes on
     every map load -- it writes only the endpoint's normal cache rows
     (no cash, no inventory, no player data). If the import is unsafe or
     fails, this check is SKIPPED with the reason -- never a crash.

VERDICT (printed at the end, one of):
  (a) Overpass unreachable/slow from /app
  (b) handler code hangs (exact line/construct named)
  (c) handler is not the patched v2 code
  (d) cache empty + Overpass failing -- endpoint answers [] fast
      (explains no marker, NOT a hang)
  (e) something else found (or: could not determine -- see skips)
  healthy -- handler answers with centers inside the budget.
The diag ALWAYS finishes and prints CENTERS_HANG_DIAG_OK or
CENTERS_HANG_DIAG_PARTIAL, even if individual checks fail. It never hangs
itself: every network/handler step has its own time budget.
"""
import asyncio
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
LAT, LNG, RADIUS_KM = 41.65431, -83.62055, 2.0
OVERPASS_DEFAULT = "https://overpass-api.de/api/interpreter"
OVERPASS_BUDGET = 35.0   # seconds for the real-query probe
TINY_BUDGET = 15.0       # seconds for the tiny probe
HANDLER_BUDGET = 35.0    # seconds for the in-process handler call
CELL_DEG = 0.05
MARKER = "CENTERS_HANG_DIAG_OK"
PARTIAL = "CENTERS_HANG_DIAG_PARTIAL"

findings = []   # (check, text) for the verdict section


def note(check, text):
    findings.append((check, text))
    print(text)


def read(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return p.read_text(errors="ignore")
    except Exception as e:  # noqa: BLE001 - diag must never crash
        print("WARNING: could not read %s (%s)" % (rel, e))
        return None


def bbox_for(lat, lng, radius_km):
    dlat = radius_km / 111.0
    dlng = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    return lat - dlat, lng - dlng, lat + dlat, lng + dlng


def cells_for(min_lat, min_lng, max_lat, max_lng):
    i0, i1 = math.floor(min_lat / CELL_DEG), math.floor(max_lat / CELL_DEG)
    j0, j1 = math.floor(min_lng / CELL_DEG), math.floor(max_lng / CELL_DEG)
    return ["%d_%d" % (i, j) for i in range(i0, i1 + 1) for j in range(j0, j1 + 1)]


def overpass_query(s, w, n, e):
    return (
        "[out:json][timeout:25];\n"
        "(\n"
        + '  nwr["amenity"="university"](%s,%s,%s,%s);\n' % (s, w, n, e)
        + '  nwr["amenity"="college"](%s,%s,%s,%s);\n' % (s, w, n, e)
        + ");\n"
        "out center;\n"
    )


def post_overpass(url, query, budget):
    """Timed POST to Overpass. httpx if available (same client family as the
    handler), else stdlib urllib. Returns (status, elapsed, payload_or_None,
    error_or_None, client_name). Never raises."""
    body = urllib.parse.urlencode({"data": query}).encode()
    t0 = time.time()
    try:
        import httpx  # type: ignore
        try:
            with httpx.Client(timeout=budget) as c:
                r = c.post(url, data={"data": query})
            el = time.time() - t0
            try:
                payload = r.json()
            except Exception:
                payload = None
            return r.status_code, el, payload, None, "httpx"
        except Exception as e:  # noqa: BLE001
            return None, time.time() - t0, None, "httpx: %s" % e, "httpx"
    except ImportError:
        pass
    req = urllib.request.Request(url, data=body, headers={
        # Overpass's nginx 406s requests with no User-Agent (urllib/curl
        # defaults). httpx -- what the handler uses -- always sends one,
        # so the diag must too, or check 3 would falsely report failure.
        "User-Agent": "StreetLegends-diag/1.0",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=budget) as r:
            raw = r.read()
        el = time.time() - t0
        try:
            payload = json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            payload = None
        return r.status, el, payload, None, "urllib"
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "ignore")[:200].replace("\n", " ")
        except Exception:
            detail = ""
        return e.code, time.time() - t0, None, "HTTPError: HTTP %s %s" % (e.code, detail), "urllib"
    except Exception as e:  # noqa: BLE001
        return None, time.time() - t0, None, "%s: %s" % (type(e).__name__, e), "urllib"


def main():
    skipped = []
    verdict = None
    verdict_detail = ""

    min_lat, min_lng, max_lat, max_lng = bbox_for(LAT, LNG, RADIUS_KM)
    cell_keys = cells_for(min_lat, min_lng, max_lat, max_lng)

    print("=== activity-centers hang diag ===")
    print("position: lat=%s lng=%s radius_km=%s" % (LAT, LNG, RADIUS_KM))
    print("bbox: s=%s w=%s n=%s e=%s (lat %.4f..%.4f, lng %.4f..%.4f)"
          % (round(min_lat, 5), round(min_lng, 5), round(max_lat, 5), round(max_lng, 5),
             min_lat, max_lat, min_lng, max_lng))
    print("grid cells (%s deg): %d cells %s" % (CELL_DEG, len(cell_keys), cell_keys))

    # ---------- check 1: handler shape in live server.py ----------
    print("=== 1. handler shape in live backend/server.py ===")
    srv = read("backend/server.py")
    handler_found = False
    fetch_timeout = None
    sequential = None
    handler_region = ""
    fetch_region = ""
    if srv is None:
        print("backend/server.py MISSING - checks 1, 2, 4, 5 cannot run")
        skipped += ["server-file"]
    else:
        lines = srv.splitlines()
        # Fetch function block.
        fstart = next((i for i, l in enumerate(lines)
                       if l.startswith("async def _activity_center_fetch_cell")), None)
        if fstart is not None:
            fend = next((i for i in range(fstart + 1, len(lines))
                         if re.match(r"^(async def |def |@api_router|class )", lines[i])), len(lines))
            fetch_region = "\n".join(lines[fstart:fend])
            print("-- _activity_center_fetch_cell (lines %d-%d) --" % (fstart + 1, fend))
            print(fetch_region)
            m = re.search(r"timeout\s*=\s*([\d.]+)", fetch_region)
            fetch_timeout = float(m.group(1)) if m else None
            print("per-cell timeout: %s" % (("%ss" % fetch_timeout) if fetch_timeout is not None
                                            else "NONE FOUND - fetch may wait forever"))
            if fetch_timeout is None:
                note("1", "HANG-CANDIDATE: Overpass fetch has NO timeout value in the file")
            if "await client.post" not in fetch_region and "await client.get" not in fetch_region:
                note("1", "HANG-CANDIDATE: no awaited Overpass call found in the fetch block")
            if "except" not in fetch_region:
                note("1", "HANG-CANDIDATE: fetch block has no exception handler")
        else:
            print("_activity_center_fetch_cell NOT FOUND in live server.py")
            note("1", "fetch function missing from live server.py")
        # Nearby handler block.
        hstart = next((i for i, l in enumerate(lines)
                       if '@api_router.get("/activity-centers/nearby")' in l), None)
        if hstart is not None:
            handler_found = True
            hend = next((i for i in range(hstart + 1, len(lines))
                         if re.match(r"^(async def |def |@api_router|class )", lines[i])), len(lines))
            handler_region = "\n".join(lines[hstart:hend])
            print("-- nearby handler (lines %d-%d), signature + cell loop --" % (hstart + 1, hend))
            sig = [l for l in lines[hstart:hstart + 3]]
            print("\n".join(sig))
            loop = [l for l in lines[hstart:hend] if "for cell_key" in l or "_activity_center_fetch_cell" in l]
            print("\n".join(loop) if loop else "(no cell loop / fetch call lines found)")
            sequential = any("await _activity_center_fetch_cell" in l for l in lines[hstart:hend])
            print("cell fetches sequential (await inside the loop): %s" % sequential)
            if sequential:
                note("1", "SEQUENTIAL cells: each cell fetch is awaited before the next starts")
            # Other unbounded constructs in handler + fetch regions.
            blob = handler_region + "\n" + fetch_region
            http_calls = len(re.findall(r"client\.(post|get|request)\(", blob))
            print("HTTP calls in handler+fetch regions: %d" % http_calls)
            if re.search(r"while\s+True", blob):
                note("1", "HANG-CANDIDATE: 'while True' in handler/fetch region")
            if "time.sleep(" in blob:
                note("1", "HANG-CANDIDATE: blocking time.sleep in async handler/fetch region")
            if http_calls > len(cell_keys) and http_calls > 1:
                note("1", "NOTE: %d HTTP calls for %d cells - more than one call per cell" % (http_calls, len(cell_keys)))
        else:
            print('nearby route @api_router.get("/activity-centers/nearby") NOT FOUND')
            note("1", "nearby route missing from live server.py")
        if fetch_timeout is not None:
            worst = len(cell_keys) * fetch_timeout
            print("WORST-CASE endpoint latency (cells x per-cell timeout): %d x %ss = %ss"
                  % (len(cell_keys), fetch_timeout, worst))
            print("Parent's probes used 45s and 60s timeouts -- both SHORTER than %ss" % worst)
            note("0", "worst-case sequential latency: %ss (%d cells x %ss)" % (worst, len(cell_keys), fetch_timeout))

    # ---------- check 2: is the live handler the patched v2 code? ----------
    print("=== 2. is the live handler the patched v2 code? ===")
    v2_ok = True
    if srv is None:
        v2_ok = False
    else:
        checks = [
            ("v2-marker", "ACTIVITY_CENTER_REAL", True),
            ("overpass-url", "https://overpass-api.de/api/interpreter", True),
            ("cache-collection", "activity_center_cache", True),
            ("centers-collection", "activity_centers", True),
            ("osm-id", '"osm_%s_%s"', True),
            ("fictional-cleanup", '"$regex": "^activity_center_"', True),
            ("no-fallback-comment", "never\n# fake centers", False),  # informational only
            ("v1-spawn-absent", "/activity-centers/spawn", False),
        ]
        for name, needle, want in checks:
            n = srv.count(needle)
            if want:
                print("%-22s %s (x%d)" % (name, "FOUND" if n else "MISSING", n))
                if not n:
                    v2_ok = False
                    note("2", "v2 marker missing: %s" % name)
            else:
                print("%-22s %s (x%d)" % (name, "ABSENT - good" if n == 0 else "PRESENT - bad", n))
                if name == "v1-spawn-absent" and n:
                    v2_ok = False
                    note("2", "v1 fictional spawn endpoint STILL PRESENT in live server.py")
        print("live handler is v2: %s" % v2_ok)

    # ---------- check 3: Overpass reachability from /app ----------
    print("=== 3. Overpass reachability from this machine ===")
    overpass_url = os.environ.get("CENTERS_DIAG_OVERPASS_URL")
    url_source = "env CENTERS_DIAG_OVERPASS_URL"
    if not overpass_url:
        m = re.search(r'ACTIVITY_CENTER_OVERPASS_URL\s*=\s*"([^"]+)"', srv or "")
        overpass_url = m.group(1) if m else OVERPASS_DEFAULT
        url_source = "live server.py" if m else "default"
    print("Overpass URL (%s): %s" % (url_source, overpass_url))
    query = overpass_query(round(min_lat, 5), round(min_lng, 5), round(max_lat, 5), round(max_lng, 5))
    print("exact query sent:\n%s" % query)
    status, el, payload, err, client = post_overpass(overpass_url, query, OVERPASS_BUDGET)
    overpass_slow = False
    overpass_failed = False
    el_count = None
    if err is not None:
        print("Overpass probe (%s): FAILED after %.1fs -- %s" % (client, el, err))
        overpass_failed = True
        note("3", "Overpass probe FAILED after %.1fs: %s" % (el, err))
    else:
        el_count = len(payload.get("elements", [])) if isinstance(payload, dict) else None
        names = []
        if isinstance(payload, dict):
            for e in payload.get("elements", []) or []:
                tags = e.get("tags") or {}
                names.append("%s (%s)" % (tags.get("name") or "?", tags.get("amenity")))
        print("Overpass probe (%s): HTTP %s in %.1fs, elements=%s" % (client, status, el, el_count))
        if names:
            print("elements found: %s" % "; ".join(names[:10]))
        if status != 200:
            overpass_failed = True
            note("3", "Overpass probe HTTP %s (not 200)" % status)
        elif el > 10:
            overpass_slow = True
            note("3", "Overpass probe SLOW: %.1fs for one cell query" % el)
        else:
            print("Overpass answers fast from this machine (%.1fs)" % el)
    if overpass_slow or overpass_failed:
        tiny_q = "[out:json][timeout:10];node(41.65,-83.62,41.66,-83.61);out 5;"
        print("tiny probe (small node query, %ss budget) to tell 'Overpass down' from 'this query slow'..." % TINY_BUDGET)
        s2, el2, p2, err2, c2 = post_overpass(overpass_url, tiny_q, TINY_BUDGET)
        if err2 is not None:
            print("tiny probe (%s): FAILED after %.1fs -- %s" % (c2, el2, err2))
            note("3", "tiny probe also FAILED: Overpass unreachable/slow from this machine")
        else:
            print("tiny probe (%s): HTTP %s in %.1fs" % (c2, s2, el2))
            if s2 == 200 and el2 <= 10:
                note("3", "tiny probe FAST (%.1fs) but the real query is slow/failing -- query-side or rate-limit, not a dead Overpass" % el2)
            else:
                note("3", "tiny probe also slow/bad (HTTP %s, %.1fs) -- Overpass itself is slow from here" % (s2, el2))

    # ---------- checks 4 + 5: import the live module, read cache, call handler ----------
    print("=== 4+5. import live backend/server.py, read cache, call handler ===")
    server_mod = None
    import_err = None
    backend_dir = str(ROOT / "backend")
    if backend_dir not in sys.path:
        sys.path.insert(0, backend_dir)
    try:
        import importlib
        server_mod = importlib.import_module("server")
        print("import server: OK")
    except Exception as e:  # noqa: BLE001
        import_err = "%s: %s" % (type(e).__name__, e)
        print("import server: FAILED (%s) -- checks 4 and 5 SKIPPED" % import_err)
        print("  (import needs the app env: MONGO_URL + DB_NAME set, and fastapi/motor installed)")
        skipped += ["import-server"]

    cache_rows = None
    cache_cells = {}
    if server_mod is not None:
        db = getattr(server_mod, "db", None)
        if db is None:
            print("no module-level 'db' handle found -- cache check SKIPPED")
            skipped += ["db-handle"]
        else:
            async def _read_cache():
                out = {}
                for key in cell_keys:
                    try:
                        row = await db.activity_center_cache.find_one({"cell": key})
                    except Exception as e:  # noqa: BLE001
                        row = {"_error": "%s: %s" % (type(e).__name__, e)}
                    out[key] = row
                try:
                    rows = await db.activity_centers.find({
                        "id": {"$regex": "^osm_"},
                        "latitude": {"$gte": min_lat, "$lte": max_lat},
                        "longitude": {"$gte": min_lng, "$lte": max_lng},
                    }).to_list(500)
                except Exception as e:  # noqa: BLE001
                    rows = {"_error": "%s: %s" % (type(e).__name__, e)}
                return out, rows
            try:
                cache_cells, cache_rows = asyncio.run(_read_cache())
            except Exception as e:  # noqa: BLE001
                print("cache read FAILED: %s: %s" % (type(e).__name__, e))
                skipped += ["cache-read"]
            if cache_rows is not None:
                if isinstance(cache_rows, dict) and "_error" in cache_rows:
                    print("cached osm_* rows in bbox: READ ERROR %s" % cache_rows["_error"])
                else:
                    print("cached osm_* rows in bbox: %d" % len(cache_rows))
                    for r in cache_rows[:5]:
                        print("  - %s | %s" % (r.get("id"), r.get("name")))
                for key, row in cache_cells.items():
                    if row is None:
                        print("cache cell %s: EMPTY (never fetched)" % key)
                    elif isinstance(row, dict) and "_error" in row:
                        print("cache cell %s: READ ERROR %s" % (key, row["_error"]))
                    else:
                        print("cache cell %s: fetched_at=%s" % (key, row.get("fetched_at")))

    handler_result = "skipped"
    handler_elapsed = None
    handler_err = None
    if server_mod is not None:
        fn = getattr(server_mod, "nearby_activity_centers", None)
        if fn is None:
            print("nearby_activity_centers function NOT FOUND in imported module -- check 5 SKIPPED")
            skipped += ["handler-fn"]
        else:
            print("calling nearby_activity_centers(lat=%s, lng=%s, radius_km=%s) with a %ss budget..."
                  % (LAT, LNG, RADIUS_KM, HANDLER_BUDGET))
            t0 = time.time()

            async def _call():
                return await asyncio.wait_for(
                    fn(latitude=LAT, longitude=LNG, radius_km=RADIUS_KM),
                    timeout=HANDLER_BUDGET)

            try:
                handler_result = asyncio.run(_call())
                handler_elapsed = time.time() - t0
                if isinstance(handler_result, list):
                    print("handler RETURNED in %.1fs: %d center(s)" % (handler_elapsed, len(handler_result)))
                    for r in handler_result[:10]:
                        print("  - %s | %s | %s,%s" % (r.get("id"), r.get("name"),
                                                        r.get("latitude"), r.get("longitude")))
                else:
                    print("handler RETURNED in %.1fs: %r" % (handler_elapsed, handler_result))
            except asyncio.TimeoutError:
                handler_result = "timeout"
                handler_elapsed = time.time() - t0
                print("handler TIMED OUT after %.1fs (budget %ss) -- it never answered" % (handler_elapsed, HANDLER_BUDGET))
                note("5", "in-process handler call TIMED OUT after %.1fs" % handler_elapsed)
            except Exception as e:  # noqa: BLE001
                handler_result = "error"
                handler_elapsed = time.time() - t0
                handler_err = "%s: %s" % (type(e).__name__, e)
                print("handler RAISED after %.1fs: %s" % (handler_elapsed, handler_err))
                note("5", "in-process handler call RAISED: %s" % handler_err)

    # ---------- verdict ----------
    print("=== verdict ===")
    worst = None
    if fetch_timeout is not None:
        worst = len(cell_keys) * fetch_timeout
    if not handler_found or not v2_ok:
        verdict, verdict_detail = "c", "the live handler is NOT the patched v2 code (see check 2)"
    elif handler_result == "timeout":
        if overpass_slow or overpass_failed:
            verdict = "a+b"
            verdict_detail = ("Overpass is slow/unreachable from /app AND the handler awaits "
                              "each of the %d cells SEQUENTIALLY with a %ss timeout each "
                              "(worst case %ss) -- the endpoint only answers after the "
                              "slowest cell gives up, longer than the 45s/60s probes. "
                              "Fix direction: fetch cells concurrently and/or cap the "
                              "whole endpoint with one short budget." % (len(cell_keys), fetch_timeout, worst))
        else:
            verdict = "b"
            verdict_detail = ("Overpass answers fast, but the handler still never returns -- "
                              "the stall is inside the handler itself (see check 1 for the "
                              "flagged construct, or a DB/cache await that never resolves).")
    elif handler_result == "error":
        verdict, verdict_detail = "e", "handler raises instead of answering: %s" % handler_err
    elif isinstance(handler_result, list):
        if len(handler_result) > 0:
            verdict = "healthy"
            verdict_detail = ("handler returned %d center(s) in %.1fs -- the endpoint works "
                              "from /app right now; the earlier hang was transient (or "
                              "Overpass was slow at that moment). Re-test on device." % (len(handler_result), handler_elapsed))
        else:
            verdict = "d"
            verdict_detail = ("handler answers FAST with [] (%.1fs): cache is empty and "
                              "Overpass returned no university/college in this bbox -- "
                              "no marker, but NO hang either. If the device still shows "
                              "nothing, the bbox has no tagged campus, not a hung call." % handler_elapsed)
    elif handler_result == "skipped":
        if fetch_timeout is None:
            verdict, verdict_detail = "b", ("no per-cell timeout found in the fetch code -- "
                                            "a stalled Overpass call can wait forever (see check 1).")
        elif overpass_slow or overpass_failed:
            verdict = "a"
            verdict_detail = ("Overpass is slow/unreachable from /app; with %d sequential "
                              "cells x %ss the endpoint can take up to %ss to answer "
                              "(in-process call could not be run to confirm -- import "
                              "failed: %s)." % (len(cell_keys), fetch_timeout, worst, import_err))
        else:
            verdict, verdict_detail = "e", ("could not determine live: in-process call skipped "
                                            "(import failed: %s); file shape + Overpass look "
                                            "normal." % import_err)
    else:
        verdict, verdict_detail = "e", "unexpected handler result state: %r" % (handler_result,)

    print("VERDICT: (%s) %s" % (verdict, verdict_detail))
    if findings:
        print("findings:")
        for check, text in findings:
            print("  [%s] %s" % (check, text))
    summary = MARKER if not skipped else PARTIAL
    print("%s verdict=%s skipped=%s" % (summary, verdict, ",".join(skipped) if skipped else "none"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
