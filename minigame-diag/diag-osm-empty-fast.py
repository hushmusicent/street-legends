#!/usr/bin/env python3
"""Street Legends diag: WHY do all OSM endpoints return [] FAST?

Read-only probe. Runs in the Emergent terminal at /app. Never edits a
file, never restarts anything, never calls a state-changing endpoint.

LIVE FACTS (parent, 2026-11-06 02:42 EST — user at 41.66308,-83.61536
by the University of Toledo, sees no activity-center marker):
  - GET /api/activity-centers/nearby at his spot -> [] in ~1.2s
    (was 11.2s with count 0 on 2026-11-05).
  - Same endpoint at Ohio State (40.0067,-83.0305, a FRESH grid cell,
    huge campus) -> [] in ~1.7s.
  - Same endpoint one cell over (41.72,-83.61) -> [] in ~1.5s.
  - GET /api/pharmacies/nearby at his spot -> [] in ~0.6s.
So it is NOT his location, NOT a stale cache for his cell, and NOT a
slow timeout anymore -- everything OSM returns empty FAST. The OSM
mirror fix (backend/patch-osm-mirror-osmch.py, inserts
https://overpass.osm.ch/api/interpreter FIRST in OSM_OVERPASS_MIRRORS)
was handed off 2026-11-05 23:07 EST and its run status is UNKNOWN.
Earlier diags proved: overpass-api.de UNREACHABLE (connection refused,
persistent), overpass.kumi.systems UNREACHABLE (10.7s read timeout),
ONLY overpass.osm.ch reachable from /app (1 of 6 mirrors). The four
OSM fetch functions loop over OSM_OVERPASS_MIRRORS. The parallel-fetch
fix IS live in the handler.

This probe answers, in order:
  1. MIRRORS LIVE: the live value of OSM_OVERPASS_MIRRORS exactly as
     defined in server.py (in order). Does it start with osm.ch
     (mirror fix RAN) or is it still [.de, kumi] (fix NEVER RAN)?
  2. DIRECT FETCH PER MIRROR: for EACH mirror in the live list, the
     REAL Overpass query the centers handler uses for his cell
     (41.66308,-83.61536), 10s timeout each -- HTTP status (or the
     exact exception + seconds), response byte length, element count,
     and usable-center count after the handler's own filter. Plus a
     wide-bbox sanity query on the first mirror only (whole UT area)
     to tell "this cell is empty" apart from "the query returns
     nothing anywhere".
  3. HANDLER PATH: the grid cells for his 2km bbox, whether each cell
     is already cached and what the cached value holds (fetched_at +
     age + fresh?), the activity_centers rows already in the DB for
     his bbox, the handler's own fetch called for his cell (via a
     guarded subprocess import of server.py), and a live read-only GET
     of the endpoint at diag time. If the handler's fetch returns
     elements but the endpoint returns [], that is printed explicitly.
  4. CONTROL: the same direct-fetch test for the PHARMACY query
     (amenity=pharmacy) against the first mirror only -- to show
     whether the problem is centers-specific or all OSM queries.

Verdict, exactly one of:
  (a) mirror fix never ran -- mirrors still [.de, kumi]
  (b) osm.ch first but osm.ch now fails -- status/exception given
  (c) mirrors answer with data but the handler/cache returns [] --
      cell + cached value + fetched count given
  (d) the query/bbox itself returns 0 elements everywhere -- bbox +
      element counts given (wide-bbox + pharmacy control included)
  undetermined -- not enough evidence (see which checks skipped)

Budget: every network call capped at 10s, subprocess import capped at
25s, total runtime under 60s (a global deadline skips late calls and
says so). Every check prints usable output even if pieces are missing.

Run from /app:  python3 minigame-diag/diag-osm-empty-fast.py
Test hooks (env): OSM_EMPTY_FAST_ENDPOINT (public base for the live
endpoint GET; default https://gta-quest-map.emergent.host).
Harness hooks: the module-level _post_overpass / _get_endpoint /
_cache_read functions can be monkeypatched after import; main(root)
accepts a root path (default: argv[1] or /app).
"""
import asyncio  # noqa: F401  (kept for parity with the handler's world)
import json
import math
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

LAT, LNG = 41.66308, -83.61536   # user's spot, University of Toledo
RADIUS_KM = 2.0                  # endpoint default radius_km
OSMCH_URL = "https://overpass.osm.ch/api/interpreter"
CELL_DEG_DEFAULT = 0.05
CACHE_SECONDS_DEFAULT = 86400
PER_CALL_TIMEOUT = 10.0          # seconds per network call
IMPORT_TIMEOUT = 25.0            # seconds for the subprocess import
TOTAL_BUDGET = 55.0              # seconds for the whole probe
ENDPOINT_BASE = os.environ.get(
    "OSM_EMPTY_FAST_ENDPOINT", "https://gta-quest-map.emergent.host")
MARKER = "OSM_EMPTY_FAST_DIAG_OK"
PARTIAL = "OSM_EMPTY_FAST_DIAG_PARTIAL"

# Known query templates (from backend/patch-activity-center-real.py and
# backend/patch-pharmacy.py). Used only if the live template lines cannot
# be found in server.py -- the probe prints which source it used.
KNOWN_CENTERS_QUERY = (
    "[out:json][timeout:25];\n(\n"
    '  nwr["amenity"="university"]({s},{w},{n},{e});\n'
    '  nwr["amenity"="college"]({s},{w},{n},{e});\n'
    ");\n out center;\n"
)
KNOWN_PHARMACY_QUERY = (
    "[out:json][timeout:25];(nwr[\"amenity\"=\"pharmacy\"]({s},{w},{n},{e}););"
    "out center;\n"
)

_deadline = None


def _remaining():
    if _deadline is None:
        return PER_CALL_TIMEOUT
    return max(0.0, _deadline - time.time())


def _call_timeout():
    return max(0.5, min(PER_CALL_TIMEOUT, _remaining()))


def _bbox(lat, lng, radius_km=RADIUS_KM):
    dlat = radius_km / 111.0
    dlng = radius_km / (111.0 * max(0.2, math.cos(math.radians(lat))))
    return (lat - dlat, lng - dlng, lat + dlat, lng + dlng)


def _cells(min_lat, min_lng, max_lat, max_lng, cell_deg):
    cells = []
    i0 = math.floor(min_lat / cell_deg)
    i1 = math.floor(max_lat / cell_deg)
    j0 = math.floor(min_lng / cell_deg)
    j1 = math.floor(max_lng / cell_deg)
    for i in range(i0, i1 + 1):
        for j in range(j0, j1 + 1):
            cells.append((f"{i}_{j}", i * cell_deg, j * cell_deg,
                          (i + 1) * cell_deg, (j + 1) * cell_deg))
    return cells


def _his_cell(lat, lng, cell_deg):
    i = math.floor(lat / cell_deg)
    j = math.floor(lng / cell_deg)
    return (f"{i}_{j}", i * cell_deg, j * cell_deg,
            (i + 1) * cell_deg, (j + 1) * cell_deg)


def _usable(payload, amenities):
    """Elements that survive the handler's own filter (amenity + a point).
    Returns (raw_count, usable_list). Never raises."""
    try:
        els = (payload or {}).get("elements", []) or []
    except Exception:
        return 0, []
    out = []
    for el in els:
        if not isinstance(el, dict):
            continue
        tags = el.get("tags") or {}
        if tags.get("amenity") not in amenities:
            continue
        if el.get("type") == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            c = el.get("center") or {}
            lat, lng = c.get("lat"), c.get("lon")
        if lat is None or lng is None:
            continue
        out.append({"id": "osm_%s_%s" % (el.get("type"), el.get("id")),
                    "name": tags.get("name"), "lat": lat, "lng": lng})
    return len(els), out


def _post_overpass(url, query, timeout):
    """Timed POST to one Overpass mirror. httpx if available (same client
    family as the handler), else stdlib urllib with a User-Agent
    (Overpass's nginx 406s requests with none). Returns
    (status, elapsed, payload_or_None, byte_len, error_or_None, client).
    Never raises."""
    t0 = time.time()
    try:
        import httpx  # type: ignore
        try:
            with httpx.Client(timeout=timeout) as c:
                r = c.post(url, data={"data": query})
            el = time.time() - t0
            raw = r.content or b""
            try:
                payload = r.json()
            except Exception:
                payload = None
            return r.status_code, el, payload, len(raw), None, "httpx"
        except Exception as e:  # noqa: BLE001
            return None, time.time() - t0, None, 0, "httpx: %s" % e, "httpx"
    except ImportError:
        pass
    body = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "User-Agent": "StreetLegends-diag/1.0",
        "Accept": "application/json",
        "Content-Type": "application/x-www-form-urlencoded",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
        el = time.time() - t0
        try:
            payload = json.loads(raw.decode("utf-8", "ignore"))
        except Exception:
            payload = None
        return r.status, el, payload, len(raw), None, "urllib"
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "ignore")[:200].replace("\n", " ")
        except Exception:
            detail = ""
        return e.code, time.time() - t0, None, 0, "HTTPError: HTTP %s %s" % (e.code, detail), "urllib"
    except Exception as e:  # noqa: BLE001
        return None, time.time() - t0, None, 0, "%s: %s" % (type(e).__name__, e), "urllib"


def _get_endpoint(path, timeout):
    """Read-only GET of one nearby endpoint. Tries the /app-local backend
    first (localhost:8000), then the public host. Returns
    (count_or_None, elapsed, used_url_or_error, sample_names).
    Never raises."""
    bases = ["http://localhost:8000", ENDPOINT_BASE.rstrip("/")]
    last_err = None
    for base in bases:
        url = base + path
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "StreetLegends-diag/1.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            el = time.time() - t0
            try:
                data = json.loads(raw.decode("utf-8", "ignore"))
            except Exception:
                return None, el, "%s: non-JSON response (status %s)" % (base, r.status), []
            items = data if isinstance(data, list) else []
            names = [it.get("name") for it in items[:3] if isinstance(it, dict)]
            return len(items), el, url, names
        except urllib.error.HTTPError as e:
            return None, time.time() - t0, "%s: HTTP %s" % (base, e.code), []
        except Exception as e:  # noqa: BLE001
            last_err = "%s: %s: %s" % (base, type(e).__name__, e)
            continue
    return None, None, last_err, []


def _mongo_url(root):
    """Find the Mongo URL from the environment (or a .env file) without
    writing anything. Returns (url_or_None, source_or_reason)."""
    for key in ("MONGO_URL", "DB_URL", "MONGODB_URL", "MONGO_URI"):
        v = os.environ.get(key)
        if v:
            return v, "env %s" % key
    for rel in ("backend/.env", ".env"):
        p = root / rel
        if p.exists():
            try:
                for line in p.read_text(errors="ignore").splitlines():
                    m = re.match(r"\s*(MONGO_URL|DB_URL|MONGODB_URL|MONGO_URI)\s*=\s*(.+)", line)
                    if m:
                        return m.group(2).strip().strip('"').strip("'"), "%s %s" % (rel, m.group(1))
            except Exception:
                pass
    return None, "no MONGO_URL/DB_URL in env or .env"


def _cache_read(root, cell_keys, bbox, cache_seconds):
    """Read-only cache + rows check for the centers cells. Returns a dict
    or None (skipped -- reason printed). Never raises."""
    url, source = _mongo_url(root)
    if not url:
        print("cache: SKIPPED -- %s" % source)
        return None
    try:
        import pymongo  # type: ignore
    except ImportError:
        print("cache: SKIPPED -- pymongo not importable in this terminal "
              "(MONGO_URL present via %s, but no driver to read it)" % source)
        return None
    min_lat, min_lng, max_lat, max_lng = bbox
    try:
        client = pymongo.MongoClient(url, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
        if db is None:
            print("cache: SKIPPED -- MONGO_URL has no default database")
            return None
        print("cache: source=%s db=%s" % (source, db.name))
        out = {"cells": {}, "rows_in_bbox": None, "row_names": []}
        import datetime
        now = datetime.datetime.utcnow()
        for key in cell_keys:
            doc = db["activity_center_cache"].find_one({"cell": key})
            if not doc:
                print("cache: cell %s NOT CACHED (no fetched_at row)" % key)
                out["cells"][key] = {"cached": False}
                continue
            fetched = doc.get("fetched_at")
            age = None
            fresh = False
            try:
                f = fetched
                if isinstance(f, str):
                    f = datetime.datetime.fromisoformat(f)
                if f is not None:
                    age = (now - f).total_seconds()
                    fresh = age < cache_seconds
            except Exception:
                pass
            age_txt = ("%.1fh" % (age / 3600.0)) if age is not None else "unknown"
            print("cache: cell %s CACHED fetched_at=%s age=%s fresh(<%.0fh)=%s"
                  % (key, fetched, age_txt, cache_seconds / 3600.0, fresh))
            out["cells"][key] = {"cached": True, "fetched_at": str(fetched),
                                 "age_s": age, "fresh": fresh}
        rows = list(db["activity_centers"].find({
            "id": {"$regex": "^osm_"},
            "latitude": {"$gte": min_lat, "$lte": max_lat},
            "longitude": {"$gte": min_lng, "$lte": max_lng},
        }).limit(10))
        out["rows_in_bbox"] = len(rows)
        out["row_names"] = [r.get("name") for r in rows[:3]]
        print("cache: activity_centers rows in bbox (id ^osm_): %d sample=%s"
              % (len(rows), out["row_names"]))
        client.close()
        return out
    except Exception as e:  # noqa: BLE001
        print("cache: SKIPPED -- mongo read failed (%s: %s)" % (type(e).__name__, e))
        return None


def _handler_fetch_via_import(root, cell_key, s, w, n, e, timeout):
    """Call the handler's own _activity_center_fetch_cell for one cell, in
    a guarded subprocess (importing server.py must never hang this probe).
    Returns ("ok", count) / ("none", None) / ("error", detail).
    Never raises."""
    if timeout < 5:
        print("handler fetch: SKIPPED -- time budget left (%.1fs)" % timeout)
        return ("skipped", None)
    code = (
        "import sys, asyncio\n"
        "sys.path.insert(0, 'backend')\n"
        "import server\n"
        "res = asyncio.run(server._activity_center_fetch_cell(%r, %r, %r, %r, %r))\n"
        "print('HANDLER_FETCH_RESULT count=' + ('None' if res is None else str(len(res))))\n"
        % (cell_key, s, w, n, e)
    )
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code], cwd=str(root),
            capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        print("handler fetch: TIMEOUT after %.1fs (subprocess import/call hung)"
              % timeout)
        return ("error", "subprocess timeout %.1fs" % timeout)
    except Exception as exc:  # noqa: BLE001
        print("handler fetch: FAILED to launch subprocess (%s: %s)"
              % (type(exc).__name__, exc))
        return ("error", "%s: %s" % (type(exc).__name__, exc))
    out = proc.stdout or ""
    m = re.search(r"HANDLER_FETCH_RESULT count=(\S+)", out)
    if m:
        if m.group(1) == "None":
            print("handler fetch: _activity_center_fetch_cell returned None "
                  "(all mirrors failed for this cell)")
            return ("none", None)
        print("handler fetch: _activity_center_fetch_cell returned %s center(s)"
              % m.group(1))
        return ("ok", int(m.group(1)))
    err = (proc.stderr or "").strip().splitlines()
    tail = " | ".join(err[-3:])[:300] if err else "no output"
    print("handler fetch: import/call FAILED (exit %s): %s" % (proc.returncode, tail))
    return ("error", tail)


def _extract_mirrors(src):
    """Live OSM_OVERPASS_MIRRORS list, in order, or None."""
    m = re.search(r"OSM_OVERPASS_MIRRORS\s*=\s*\[(.*?)\]", src, re.S)
    if not m:
        return None
    listed = re.findall(r'"([^"]+)"', m.group(1))
    if not listed:
        listed = re.findall(r"'([^']+)'", m.group(1))
    return listed


def _extract_const(src, name, default):
    m = re.search(re.escape(name) + r"\s*=\s*([0-9.]+)", src)
    if not m:
        return default, False
    try:
        return float(m.group(1)), True
    except Exception:
        return default, False


def _extract_query(src):
    """Return (centers_query_template, pharmacy_query_template, found_live).
    The template is rebuilt from the live amenity lines + timeout when
    they are present; otherwise the known templates are used."""
    tm = re.search(r"\[out:json\]\[timeout:(\d+)\]", src)
    timeout = tm.group(1) if tm else "25"
    has_uni = '"amenity"="university"' in src or "'amenity'='university'" in src
    has_col = '"amenity"="college"' in src or "'amenity'='college'" in src
    has_pharm = '"amenity"="pharmacy"' in src or "'amenity'='pharmacy'" in src
    found_live = bool(has_uni and has_col)
    if found_live:
        centers = (
            "[out:json][timeout:%s];\n(\n" % timeout
            + '  nwr["amenity"="university"]({s},{w},{n},{e});\n'
            + '  nwr["amenity"="college"]({s},{w},{n},{e});\n'
            + ");\n out center;\n"
        )
    else:
        centers = KNOWN_CENTERS_QUERY
    if has_pharm:
        pharmacy = (
            "[out:json][timeout:%s];(nwr[\"amenity\"=\"pharmacy\"]({s},{w},{n},{e}););"
            "out center;\n" % timeout
        )
    else:
        pharmacy = KNOWN_PHARMACY_QUERY
    return centers, pharmacy, found_live, has_pharm


def main(root=None):
    global _deadline
    _deadline = time.time() + TOTAL_BUDGET
    if root is None:
        root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
    root = Path(root)
    skipped = []

    print("=== OSM empty-fast diag (why all OSM endpoints return [] fast) ===")
    print("reference point: lat=%s lng=%s (University of Toledo)" % (LAT, LNG))

    # ---------- locate server.py ----------
    srv = None
    srv_rel = None
    for rel in ("backend/server.py", "server.py"):
        p = root / rel
        if p.exists():
            try:
                srv = p.read_text(errors="ignore")
                srv_rel = rel
                break
            except Exception as exc:  # noqa: BLE001
                print("WARNING: could not read %s (%s)" % (rel, exc))
    if srv is None:
        print("backend/server.py MISSING under %s - code checks skipped" % root)
        skipped.append("server-file")

    # ---------- check 1: mirrors live ----------
    print("=== 1. mirrors live (OSM_OVERPASS_MIRRORS in server.py) ===")
    mirrors = None
    cell_deg = CELL_DEG_DEFAULT
    cache_seconds = CACHE_SECONDS_DEFAULT
    if srv is None:
        print("OSM_OVERPASS_MIRRORS: UNKNOWN (no server.py)")
        skipped.append("mirrors")
    else:
        mirrors = _extract_mirrors(srv)
        if mirrors is None:
            print("OSM_OVERPASS_MIRRORS: NOT FOUND in %s" % srv_rel)
            skipped.append("mirrors")
        else:
            print("OSM_OVERPASS_MIRRORS live (in order): %s" % mirrors)
            if mirrors and mirrors[0] == OSMCH_URL:
                print("mirrors: FIRST is osm.ch -> mirror fix RAN")
            else:
                print("mirrors: FIRST is NOT osm.ch -> mirror fix NEVER RAN "
                      "(or was reverted)")
        cell_deg, ok_cd = _extract_const(srv, "ACTIVITY_CENTER_CELL_DEG", CELL_DEG_DEFAULT)
        cache_seconds, ok_cs = _extract_const(srv, "ACTIVITY_CENTER_CACHE_SECONDS", CACHE_SECONDS_DEFAULT)
        cell_to, _ = _extract_const(srv, "OSM_CELL_TIMEOUT", 8.0)
        total_b, _ = _extract_const(srv, "OSM_TOTAL_BUDGET", 10.0)
        print("cell deg=%s (found live: %s) cache seconds=%s (found live: %s) "
              "OSM_CELL_TIMEOUT=%s OSM_TOTAL_BUDGET=%s gather helper=%s"
              % (cell_deg, ok_cd, cache_seconds, ok_cs, cell_to, total_b,
                 ("YES" if "_osm_gather_cells" in srv else "NO")))

    # ---------- cells / bbox / queries ----------
    bbox = _bbox(LAT, LNG)
    min_lat, min_lng, max_lat, max_lng = bbox
    cells = _cells(min_lat, min_lng, max_lat, max_lng, cell_deg)
    his_key, hs, hw, hn, he = _his_cell(LAT, LNG, cell_deg)
    print("2km bbox: min_lat=%.5f min_lng=%.5f max_lat=%.5f max_lng=%.5f"
          % (min_lat, min_lng, max_lat, max_lng))
    print("grid cells for bbox (%d): %s"
          % (len(cells), [(c[0], c[1], c[2], c[3], c[4]) for c in cells]))
    print("his cell (contains lat/lng): key=%s bbox s=%.2f w=%.2f n=%.2f e=%.2f"
          % (his_key, hs, hw, hn, he))
    centers_tpl, pharmacy_tpl, q_live, pharm_live = _extract_query(srv or "")
    print("centers query template found live in server.py: %s ; "
          "pharmacy template found live: %s" % (q_live, pharm_live))
    centers_query = centers_tpl.format(s=hs, w=hw, n=hn, e=he)
    print("centers query used for his cell:\n%s" % centers_query)

    # ---------- check 2: direct fetch per mirror ----------
    print("=== 2. direct fetch per mirror (centers query, his cell) ===")
    fetch_results = {}   # mirror -> (status, elapsed, raw, usable_list, error)
    wide_result = None
    if not mirrors:
        print("SKIPPED -- no live mirror list (see check 1)")
        skipped.append("direct-fetch")
    else:
        for url in mirrors:
            if _remaining() < 2:
                print("mirror %s: SKIPPED (time budget)" % url)
                skipped.append("direct-fetch-%s" % url)
                continue
            to = _call_timeout()
            status, el, payload, nbytes, err, client = _post_overpass(
                url, centers_query, to)
            if status == 200 and isinstance(payload, dict):
                raw, usable = _usable(payload, ("university", "college"))
                print("mirror %s: 200 in %.1fs (%s) bytes=%d elements=%d "
                      "usable centers=%d %s"
                      % (url, el, client, nbytes, raw, len(usable),
                         [u["name"] for u in usable[:3]]))
                fetch_results[url] = (status, el, raw, usable, None)
            elif status is not None:
                print("mirror %s: HTTP %s in %.1fs (%s) bytes=%d err=%s"
                      % (url, status, el, client, nbytes, err))
                fetch_results[url] = (status, el, 0, [], err)
            else:
                print("mirror %s: FAILED in %.1fs (%s) err=%s"
                      % (url, el, client, err))
                fetch_results[url] = (None, el, 0, [], err)
        # wide-bbox sanity on the first mirror only
        if mirrors and _remaining() >= 2:
            wide_q = centers_tpl.format(s=41.60, w=-83.70, n=41.70, e=-83.50)
            to = _call_timeout()
            status, el, payload, nbytes, err, client = _post_overpass(
                mirrors[0], wide_q, to)
            if status == 200 and isinstance(payload, dict):
                raw, usable = _usable(payload, ("university", "college"))
                print("wide-bbox sanity (first mirror %s, 41.60,-83.70 to "
                      "41.70,-83.50): 200 in %.1fs bytes=%d elements=%d usable=%d %s"
                      % (mirrors[0], el, nbytes, raw, len(usable),
                         [u["name"] for u in usable[:3]]))
                wide_result = (raw, usable)
            else:
                print("wide-bbox sanity (first mirror %s): status=%s in %.1fs err=%s"
                      % (mirrors[0], status, el, err))
                wide_result = (0, [])
        elif mirrors:
            print("wide-bbox sanity: SKIPPED (time budget)")
            skipped.append("wide-bbox")

    # ---------- check 3: handler path ----------
    print("=== 3. handler path (cells, cache, handler fetch, live endpoint) ===")
    cell_keys = [c[0] for c in cells]
    cache_info = None
    if srv is None:
        print("cells/cache: server.py missing, cell math used defaults above")
    cache_info = _cache_read(root, cell_keys, bbox, cache_seconds)
    if cache_info is None:
        skipped.append("cache")
    handler_fetch = ("skipped", None)
    if srv is not None and "def _activity_center_fetch_cell" in srv:
        handler_fetch = _handler_fetch_via_import(
            root, his_key, hs, hw, hn, he, min(IMPORT_TIMEOUT, max(5.0, _remaining())))
    elif srv is not None:
        print("handler fetch: _activity_center_fetch_cell NOT FOUND in server.py")
        skipped.append("handler-fetch")
    else:
        print("handler fetch: SKIPPED (no server.py)")
        skipped.append("handler-fetch")
    endpoint_count = None
    endpoint_used = None
    if _remaining() >= 2:
        path = ("/api/activity-centers/nearby?latitude=%s&longitude=%s"
                % (LAT, LNG))
        endpoint_count, el, endpoint_used, names = _get_endpoint(
            path, _call_timeout())
        if endpoint_count is None:
            print("live endpoint GET: FAILED -- %s" % endpoint_used)
        else:
            print("live endpoint GET %s -> %d center(s) in %.1fs sample=%s"
                  % (endpoint_used, endpoint_count, el, names))
    else:
        print("live endpoint GET: SKIPPED (time budget)")
        skipped.append("endpoint-get")
    if handler_fetch[0] == "ok" and handler_fetch[1] is not None \
            and handler_fetch[1] > 0 and endpoint_count == 0:
        print("HANDLER MISMATCH: handler fetch returns %d center(s) for his "
              "cell but the live endpoint returns [] -- the break is in the "
              "handler's cache-write / rows-query / response mapping, NOT "
              "in Overpass" % handler_fetch[1])

    # ---------- check 4: pharmacy control ----------
    print("=== 4. control: pharmacy query, first mirror only, his cell ===")
    pharmacy_result = None
    if not mirrors:
        print("SKIPPED -- no live mirror list (see check 1)")
        skipped.append("pharmacy-control")
    elif _remaining() < 2:
        print("SKIPPED (time budget)")
        skipped.append("pharmacy-control")
    else:
        pharm_q = pharmacy_tpl.format(s=hs, w=hw, n=hn, e=he)
        to = _call_timeout()
        status, el, payload, nbytes, err, client = _post_overpass(
            mirrors[0], pharm_q, to)
        if status == 200 and isinstance(payload, dict):
            raw, usable = _usable(payload, ("pharmacy",))
            print("pharmacy control (%s): 200 in %.1fs bytes=%d elements=%d "
                  "usable pharmacies=%d %s"
                  % (mirrors[0], el, nbytes, raw, len(usable),
                     [u["name"] for u in usable[:3]]))
            pharmacy_result = (raw, usable)
        elif status is not None:
            print("pharmacy control (%s): HTTP %s in %.1fs err=%s"
                  % (mirrors[0], status, el, err))
            pharmacy_result = (0, [])
        else:
            print("pharmacy control (%s): FAILED in %.1fs err=%s"
                  % (mirrors[0], el, err))
            pharmacy_result = (0, [])

    # ---------- verdict ----------
    print("=== VERDICT ===")
    verdict = "undetermined"
    detail = ""
    any_usable = 0
    osmch_failed = False
    osmch_status = None
    osmch_err = None
    if mirrors:
        first = fetch_results.get(mirrors[0])
        if first is not None:
            osmch_status, _el, _raw, osmch_usable, osmch_err = first
            any_usable = max(any_usable, len(osmch_usable))
            if osmch_status != 200:
                osmch_failed = True
        for url, res in fetch_results.items():
            any_usable = max(any_usable, len(res[3]))
    cache_fresh_zero = False
    cache_note = "cache check skipped"
    if cache_info is not None:
        fresh_cells = [k for k, v in cache_info["cells"].items()
                       if v.get("fresh")]
        rows = cache_info.get("rows_in_bbox")
        cache_note = ("cells cached fresh=%s rows in bbox=%s"
                      % (fresh_cells, rows))
        if fresh_cells and (rows == 0):
            cache_fresh_zero = True
    if mirrors is None or not mirrors:
        verdict = "undetermined"
        detail = ("OSM_OVERPASS_MIRRORS not found -- rerun with server.py "
                  "present (see check 1)")
    elif mirrors[0] != OSMCH_URL:
        verdict = "(a)"
        detail = ("mirror fix never ran -- mirrors still %s (osm.ch not "
                  "first; .de refuses and kumi times out, so every fetch "
                  "fails and the cache stays empty)" % (mirrors,))
    elif handler_fetch[0] == "ok" and handler_fetch[1] is not None \
            and handler_fetch[1] > 0 and endpoint_count == 0:
        verdict = "(c)"
        detail = ("mirrors answer with data: handler fetch returns %d "
                  "center(s) for his cell %s but the live endpoint returns "
                  "[] -- break is handler/cache/mapping, not Overpass; %s"
                  % (handler_fetch[1], his_key, cache_note))
    elif any_usable > 0 and endpoint_count == 0:
        verdict = "(c)"
        detail = ("mirrors answer with data: direct fetch returns %d usable "
                  "center(s) for his cell %s but the live endpoint returns "
                  "[]; %s; handler fetch=%s"
                  % (any_usable, his_key, cache_note, handler_fetch))
    elif any_usable > 0 and cache_fresh_zero:
        verdict = "(c)"
        detail = ("mirrors answer with data (%d usable for his cell %s) but "
                  "the cells are cached FRESH with 0 rows in the bbox -- a "
                  "previous empty fetch stamped the cache, so the handler "
                  "never re-fetches; %s" % (any_usable, his_key, cache_note))
    elif osmch_failed and not any(
            res[0] == 200 for res in fetch_results.values()):
        verdict = "(b)"
        detail = ("osm.ch is first but now fails: status=%s err=%s "
                  "(direct fetch, his cell %s); no mirror answered 200"
                  % (osmch_status, osmch_err, his_key))
    elif fetch_results and any(res[0] == 200 for res in fetch_results.values()) \
            and all(len(res[3]) == 0 for res in fetch_results.values()
                    if res[0] == 200):
        wide_txt = ""
        if wide_result is not None:
            wide_txt = (" wide-bbox sanity: %d elements / %d usable"
                        % (wide_result[0], len(wide_result[1])))
        pharm_txt = ""
        if pharmacy_result is not None:
            pharm_txt = (" pharmacy control: %d elements / %d usable"
                         % (pharmacy_result[0], len(pharmacy_result[1])))
        verdict = "(d)"
        detail = ("every answering mirror returned 0 elements for the "
                  "centers query in his cell bbox s=%.2f w=%.2f n=%.2f e=%.2f;"
                  "%s%s" % (hs, hw, hn, he, wide_txt, pharm_txt))
    else:
        verdict = "undetermined"
        detail = ("not enough evidence: mirrors=%s fetch_results=%s "
                  "handler_fetch=%s endpoint=%s"
                  % (mirrors, {u: (r[0], len(r[3])) for u, r in fetch_results.items()},
                     handler_fetch, endpoint_count))
    print("VERDICT: %s %s" % (verdict, detail))
    if skipped:
        print("skipped checks: %s" % ", ".join(skipped))
    partial = (verdict == "undetermined") or (srv is None) or (not mirrors)
    print((PARTIAL if partial else MARKER) + " verdict=%s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
