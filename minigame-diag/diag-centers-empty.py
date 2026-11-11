#!/usr/bin/env python3
"""Street Legends diag: why does /activity-centers/nearby return ZERO centers
at the University of Toledo?

Symptom (user screenshot 2026-11-05 22:43 EST): player standing at
41.65414,-83.62081 -- right by the UT campus (Secor Rd / W Bancroft) --
sees restaurants, banks, a Fiend, enemies, missions, but NO activity-center
marker. Live probe from the parent: the endpoint answers in ~11s with
count 0 (no longer hanging), while both Overpass mirrors are unreachable
from the parent VM (saturation: 502 + timeouts).

This diag runs in the Emergent terminal at /app and checks, in order:
  1. Overpass reachability FROM /app (both mirrors, tiny probe).
  2. The backend's EXACT centers query around UT, against whichever
     mirror answers (plus a tagging probe if it returns nothing: what
     does OSM actually have for UT -- relation without center,
     landuse=education, a different tag?).
  3. The DB cache (read-only): activity_center_cache + activity_centers
     totals, rows within 2km of the player, per-cell freshness.
  4. The live handler shape in backend/server.py (query string, fetch
     mirrors/timeout, parallel gather present or not, final read query).
  5. A live GET of the endpoint itself (read-only) for the same spot.

Verdict, one of:
  (a) Overpass unreachable from /app (both mirrors) + cache empty --
      centers can never load until Overpass is reachable. The probe
      classifies the failure as transient (502/503/504/429/timeout =
      saturation, a retry may succeed) or persistent (connection
      refused / DNS = unreachable from this host).
  (b) Overpass reachable but the exact query returns nothing for UT --
      the query misses UT in OSM (tagging/shape; the tagging probe
      names what OSM actually has).
  (c) Query returns UT but the endpoint still returns [] -- the handler
      drops it (the diag replays the handler's own parse filters over
      the probe payload and names which filter drops what).
  (d) Cache HAS centers for the player's cells but the endpoint
      returns [] -- the read path is broken.
  (e) Healthy -- the endpoint returns centers now.
  undetermined -- not enough evidence (see which checks skipped).

Read-only: never edits a file, never restarts anything, never calls a
state-changing endpoint. Only network calls are Overpass POSTs, one
read-only GET of the nearby endpoint, and (if the app env is available)
a read-only pymongo read of the two cache collections. Every network
call has its own short timeout, so the diag never hangs.

Run from /app:  python3 minigame-diag/diag-centers-empty.py
Test hooks (env, defaults are the production values): CENTERS_DIAG_MIRRORS
(comma-separated mirror URLs), CENTERS_DIAG_ENDPOINT (base URL for the
nearby GET), CENTERS_DIAG_MONGO_JSON (path to a JSON file the fake-pymongo
stub reads -- harness use only).
"""
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
LAT, LNG, RADIUS_KM = 41.65414, -83.62081, 2.0
MIRRORS = os.environ.get("CENTERS_DIAG_MIRRORS", "").split(",") \
    if os.environ.get("CENTERS_DIAG_MIRRORS") else [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]
MIRRORS = [m.strip() for m in MIRRORS if m.strip()]
ENDPOINT_BASE = os.environ.get("CENTERS_DIAG_ENDPOINT",
                               "https://gta-quest-map.emergent.host")
CELL_DEG = 0.05
TINY_BUDGET = 10.0    # seconds per mirror for the tiny probe
QUERY_BUDGET = 15.0   # seconds per mirror for the exact query
TAG_BUDGET = 12.0     # seconds for the tagging probe
ENDPOINT_BUDGET = 30.0
MARKER = "CENTERS_EMPTY_DIAG_OK"
PARTIAL = "CENTERS_EMPTY_DIAG_PARTIAL"

findings = []


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
    return ["%d_%d" % (i, j) for i in range(i0, i1 + 1)
            for j in range(j0, j1 + 1)]


def overpass_query(s, w, n, e):
    """The v2 handler's exact query (patch-activity-center-real.py)."""
    return (
        "[out:json][timeout:25];\n"
        "(\n"
        + '  nwr["amenity"="university"](%s,%s,%s,%s);\n' % (s, w, n, e)
        + '  nwr["amenity"="college"](%s,%s,%s,%s);\n' % (s, w, n, e)
        + ");\n"
        "out center;\n"
    )


def tagging_query(s, w, n, e):
    """What does OSM actually have for UT under OTHER tags? A campus
    mapped as landuse=education, or named without amenity=university /
    amenity=college, is invisible to the v2 query."""
    return (
        "[out:json][timeout:10];\n"
        "(\n"
        + '  nwr["landuse"="education"](%s,%s,%s,%s);\n' % (s, w, n, e)
        + '  nwr["name"~"University of Toledo",i](%s,%s,%s,%s);\n' % (s, w, n, e)
        + '  nwr["name"~"Toledo",i]["amenity"](%s,%s,%s,%s);\n' % (s, w, n, e)
        + ");\n"
        "out center;\n"
    )


TINY_QUERY = "[out:json][timeout:5];\nnode(1);\nout;\n"


def post_overpass(url, query, budget):
    """Timed POST to Overpass. httpx if available (same client family as
    the handler), else stdlib urllib. Returns (status, elapsed,
    payload_or_None, error_or_None, client_name). Never raises."""
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
    body = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(url, data=body, headers={
        # Overpass's nginx 406s requests with no User-Agent (urllib/curl
        # defaults). httpx -- what the handler uses -- always sends one,
        # so the diag must too, or it would falsely report failure.
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


def parse_like_handler(payload):
    """Replay the v2 fetch function's own parse filters over a probe
    payload. Returns (kept, dropped) where dropped is a list of
    (element, reason). Reasons mirror the live code exactly."""
    kept, dropped = [], []
    seen = set()
    for el in (payload or {}).get("elements", []) or []:
        etype = el.get("type")
        oid = el.get("id")
        tags = el.get("tags") or {}
        amenity = tags.get("amenity")
        if etype not in ("node", "way", "relation") or oid is None:
            dropped.append((el, "type/id not nwr"))
            continue
        if amenity not in ("university", "college"):
            dropped.append((el, "amenity=%r not university/college" % amenity))
            continue
        if etype == "node":
            lat, lng = el.get("lat"), el.get("lon")
        else:
            center = el.get("center") or {}
            lat, lng = center.get("lat"), center.get("lon")
        if lat is None or lng is None:
            dropped.append((el, "no center (way/relation without center)"))
            continue
        cid = "osm_%s_%s" % (etype, oid)
        if cid in seen:
            dropped.append((el, "duplicate id %s" % cid))
            continue
        seen.add(cid)
        kept.append({
            "id": cid,
            "name": tags.get("name") or ("University" if amenity == "university" else "College"),
            "kind": amenity, "latitude": float(lat), "longitude": float(lng),
        })
    return kept, dropped


def describe_element(el):
    tags = el.get("tags") or {}
    center = el.get("center") or {}
    lat = el.get("lat") if el.get("type") == "node" else center.get("lat")
    lng = el.get("lon") if el.get("type") == "node" else center.get("lon")
    return ("type=%s id=%s name=%r amenity=%r lat=%s lng=%s center=%s"
            % (el.get("type"), el.get("id"), tags.get("name"),
               tags.get("amenity"), lat, lng,
               "yes" if (lat is not None and lng is not None) else "NO"))


def classify_failure(error):
    """Transient (saturation -- a retry may succeed) vs persistent
    (unreachable from this host)."""
    if not error:
        return "unknown"
    e = error.lower()
    if any(t in e for t in ("502", "503", "504", "429", "timeout", "timed out",
                            "server at capacity", "too many requests")):
        return "TRANSIENT (saturation/overload -- retry may succeed)"
    if any(t in e for t in ("refused", "dns", "name or service not known",
                            "name resolution", "network is unreachable",
                            "no route to host")):
        return "PERSISTENT (unreachable from this host)"
    return "unknown (%s)" % error[:80]


def get_endpoint(lat, lng, radius_km):
    """Read-only GET of the live nearby endpoint. Tries the /app-local
    backend first (localhost:8000), then the public host. Returns
    (count_or_None, elapsed, used_url_or_error). Never raises."""
    path = ("/api/activity-centers/nearby?latitude=%s&longitude=%s&radius_km=%s"
            % (lat, lng, radius_km))
    bases = ["http://localhost:8000", ENDPOINT_BASE.rstrip("/")]
    for base in bases:
        url = base + path
        t0 = time.time()
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "StreetLegends-diag/1.0",
                "Accept": "application/json",
            })
            with urllib.request.urlopen(req, timeout=ENDPOINT_BUDGET) as r:
                raw = r.read()
            el = time.time() - t0
            try:
                data = json.loads(raw.decode("utf-8", "ignore"))
            except Exception:
                return None, el, "%s: non-JSON response (status %s)" % (base, r.status)
            if isinstance(data, list):
                return len(data), el, url
            if isinstance(data, dict):
                return data.get("count", len(data.get("rows", data.get("centers", [])))), el, url
            return None, el, "%s: unexpected payload type" % base
        except urllib.error.HTTPError as e:
            return None, time.time() - t0, "%s: HTTP %s" % (base, e.code)
        except Exception as e:  # noqa: BLE001
            last_err = "%s: %s: %s" % (base, type(e).__name__, e)
            continue
    return None, None, last_err


def _mongo_url():
    """Find the Mongo URL from the environment (or a .env file) without
    writing anything. Returns (url_or_None, source_or_reason)."""
    for key in ("MONGO_URL", "DB_URL", "MONGODB_URL", "MONGO_URI"):
        v = os.environ.get(key)
        if v:
            return v, "env %s" % key
    for rel in ("backend/.env", ".env"):
        p = ROOT / rel
        if p.exists():
            try:
                for line in p.read_text(errors="ignore").splitlines():
                    m = re.match(r"\s*(MONGO_URL|DB_URL|MONGODB_URL|MONGO_URI)\s*=\s*(.+)", line)
                    if m:
                        return m.group(2).strip().strip('"').strip("'"), "%s %s" % (rel, m.group(1))
            except Exception:
                pass
    return None, "no MONGO_URL/DB_URL in env or .env"


def cache_check(cell_keys, min_lat, min_lng, max_lat, max_lng):
    """Read-only counts + sample of activity_center_cache and
    activity_centers. Returns a dict, or None (skipped + reason printed).
    Never raises."""
    url, source = _mongo_url()
    if not url:
        print("cache: SKIPPED -- %s (read-only DB check needs the app env)" % source)
        return None
    try:
        import pymongo  # type: ignore
    except ImportError:
        print("cache: SKIPPED -- pymongo not importable in this terminal "
              "(MONGO_URL present via %s, but no driver to read it)" % source)
        return None
    try:
        client = pymongo.MongoClient(url, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
        if db is None:
            print("cache: SKIPPED -- MONGO_URL has no default database")
            return None
        total_centers = db.activity_centers.count_documents({})
        osm_centers = db.activity_centers.count_documents({"id": {"$regex": "^osm_"}})
        near = list(db.activity_centers.find({
            "id": {"$regex": "^osm_"},
            "latitude": {"$gte": min_lat, "$lte": max_lat},
            "longitude": {"$gte": min_lng, "$lte": max_lng},
        }).limit(10))
        total_cache = db.activity_center_cache.count_documents({})
        cells = {}
        for ck in cell_keys:
            row = db.activity_center_cache.find_one({"cell": ck})
            cells[ck] = row.get("fetched_at") if row else None
        print("cache: source=%s db=%s" % (source, db.name))
        print("cache: activity_centers total=%d osm_*=%d within 2km of player=%d"
              % (total_centers, osm_centers, len(near)))
        print("cache: activity_center_cache total cells=%d" % total_cache)
        for ck in cell_keys:
            fa = cells[ck]
            print("cache: cell %s fetched_at=%s" % (ck, fa if fa else "NEVER (cell never fetched)"))
        for r in near:
            print("cache: near row id=%s name=%r lat=%s lng=%s"
                  % (r.get("id"), r.get("name"), r.get("latitude"), r.get("longitude")))
        return {
            "total": total_centers, "osm_total": osm_centers,
            "near": len(near), "near_rows": near,
            "cache_cells": total_cache, "cells": cells,
        }
    except Exception as e:  # noqa: BLE001
        print("cache: SKIPPED -- mongo read failed (%s: %s)" % (type(e).__name__, e))
        return None


def span(lines, start_pat, end_pat=r"^(async def |def |@api_router|class )"):
    """Return (start_line_1based, end_line_1based_exclusive, text) of the
    function starting at the first line matching start_pat, or None."""
    s = next((i for i, l in enumerate(lines) if re.search(start_pat, l)), None)
    if s is None:
        return None
    e = next((i for i in range(s + 1, len(lines)) if re.match(end_pat, lines[i])), len(lines))
    return s + 1, e, "\n".join(lines[s:e])


def main():
    skipped = []
    min_lat, min_lng, max_lat, max_lng = bbox_for(LAT, LNG, RADIUS_KM)
    cell_keys = cells_for(min_lat, min_lng, max_lat, max_lng)

    print("=== activity-centers EMPTY diag (UT) ===")
    print("position: lat=%s lng=%s radius_km=%s" % (LAT, LNG, RADIUS_KM))
    print("bbox: s=%.5f w=%.5f n=%.5f e=%.5f" % (min_lat, min_lng, max_lat, max_lng))
    print("grid cells (%.2f deg): %d cells %s" % (CELL_DEG, len(cell_keys), cell_keys))

    # ---------- check 1: Overpass reachability from /app ----------
    print("=== 1. Overpass reachability from /app (tiny probe: node(1)) ===")
    reachable = []
    failures = {}
    for url in MIRRORS:
        status, el, payload, err, client = post_overpass(url, TINY_QUERY, TINY_BUDGET)
        if status == 200 and isinstance(payload, dict):
            n = len(payload.get("elements", []) or [])
            print("mirror %s: REACHABLE in %.1fs (%s) -- 200 JSON, %d element(s)"
                  % (url, el, client, n))
            reachable.append(url)
        else:
            print("mirror %s: UNREACHABLE in %.1fs (%s) -- status=%s err=%s"
                  % (url, el if el is not None else -1, client, status, err))
            failures[url] = err or ("HTTP %s" % status)
    print("reachable mirrors: %d/%d %s" % (len(reachable), len(MIRRORS), reachable))
    for url, err in failures.items():
        print("failure class %s: %s" % (url, classify_failure(err)))

    # ---------- check 2: the exact centers query around UT ----------
    print("=== 2. exact centers query around UT (amenity=university/college, out center) ===")
    q_raw, q_kept, q_dropped = [], [], []
    if not reachable:
        print("SKIPPED -- no mirror reachable (see check 1)")
        skipped.append("exact-query")
    else:
        query = overpass_query(min_lat, min_lng, max_lat, max_lng)
        for url in reachable:
            status, el, payload, err, client = post_overpass(url, query, QUERY_BUDGET)
            if status != 200 or not isinstance(payload, dict):
                print("mirror %s: query FAILED in %.1fs -- status=%s err=%s"
                      % (url, el if el is not None else -1, status, err))
                continue
            els = payload.get("elements", []) or []
            kept, dropped = parse_like_handler(payload)
            print("mirror %s: 200 in %.1fs -- %d element(s) returned, %d pass the "
                  "handler's parse, %d dropped"
                  % (url, el, len(els), len(kept), len(dropped)))
            for el in els:
                print("  element: %s" % describe_element(el))
            for el, reason in dropped:
                print("  dropped: id=%s (%s) -- %s" % (el.get("id"), el.get("type"), reason))
            q_raw.extend(els)
            q_kept.extend(kept)
            q_dropped.extend(dropped)
            if els:
                break  # one answering mirror with data is enough
        if not q_raw:
            print("exact query returned 0 elements on every reachable mirror")

    # ---------- check 2b: tagging probe (only if the exact query found nothing) ----------
    tag_found = []
    if reachable and not q_raw:
        print("=== 2b. tagging probe: what does OSM have for UT under OTHER tags? ===")
        tq = tagging_query(min_lat, min_lng, max_lat, max_lng)
        for url in reachable:
            status, el, payload, err, client = post_overpass(url, tq, TAG_BUDGET)
            if status != 200 or not isinstance(payload, dict):
                print("mirror %s: tagging probe FAILED -- status=%s err=%s" % (url, status, err))
                continue
            els = payload.get("elements", []) or []
            print("mirror %s: 200 in %.1fs -- %d element(s)" % (url, el, len(els)))
            for el in els:
                print("  tag-hit: %s tags=%s" % (describe_element(el), el.get("tags") or {}))
            tag_found.extend(els)
            if els:
                break
        if not tag_found:
            print("tagging probe: OSM has NO landuse=education / 'University of Toledo' / "
                  "'Toledo'+amenity object in this bbox under any checked tag")

    # ---------- check 3: the cache ----------
    print("=== 3. DB cache (read-only) ===")
    cache = cache_check(cell_keys, min_lat, min_lng, max_lat, max_lng)
    if cache is None:
        skipped.append("cache")

    # ---------- check 4: live handler shape ----------
    print("=== 4. live handler shape in backend/server.py ===")
    srv = read("backend/server.py")
    handler_ok = False
    if srv is None:
        print("backend/server.py MISSING - handler shape cannot be checked")
        skipped.append("server-file")
    else:
        lines = srv.splitlines()
        # Shared OSM_FAST block.
        print("OSM_FAST shared block present: %s"
              % ("YES" if "OSM_OVERPASS_MIRRORS" in srv else "NO"))
        m = re.search(r"OSM_CELL_TIMEOUT\s*=\s*([\d.]+)", srv)
        print("OSM_CELL_TIMEOUT: %s" % (m.group(1) + "s" if m else "NOT FOUND"))
        m = re.search(r"OSM_TOTAL_BUDGET\s*=\s*([\d.]+)", srv)
        print("OSM_TOTAL_BUDGET: %s" % (m.group(1) + "s" if m else "NOT FOUND"))
        # Query function.
        qf = span(lines, r"def _activity_center_overpass_query")
        if qf:
            print("-- _activity_center_overpass_query (lines %d-%d) --" % (qf[0], qf[1]))
            print(qf[2])
            print("query has amenity=university: %s / amenity=college: %s / out center: %s"
                  % ('"university"' in qf[2], '"college"' in qf[2], "out center" in qf[2]))
        else:
            print("_activity_center_overpass_query NOT FOUND")
        # Fetch function.
        ff = span(lines, r"async def _activity_center_fetch_cell")
        if ff:
            print("fetch fn _activity_center_fetch_cell: lines %d-%d" % (ff[0], ff[1]))
            print("fetch loops over OSM_OVERPASS_MIRRORS: %s"
                  % ("YES" if "OSM_OVERPASS_MIRRORS" in ff[2] else "NO"))
            print("fetch mentions kumi: %s" % ("YES" if "kumi" in ff[2] else "NO"))
            mm = re.search(r"timeout\s*=\s*([A-Za-z_0-9.]+)", ff[2])
            print("fetch timeout: %s" % (mm.group(1) if mm else "NOT FOUND"))
            print("fetch drops way/relation without center: %s"
                  % ("YES" if "if lat is None or lng is None" in ff[2] else "NOT FOUND"))
        else:
            print("_activity_center_fetch_cell NOT FOUND")
        # Handler.
        hf = span(lines, r"async def nearby_activity_centers")
        if hf:
            handler_ok = True
            print("handler nearby_activity_centers: lines %d-%d" % (hf[0], hf[1]))
            print("handler uses parallel gather (_osm_gather_cells): %s"
                  % ("YES" if "_osm_gather_cells" in hf[2] else "NO"))
            print("handler still awaits fetch inside a for loop: %s"
                  % ("YES" if re.search(r"for .* in .*_cells\(.*\):", hf[2])
                     and "await _activity_center_fetch_cell" in hf[2] else "NO"))
            print("handler final read filters id ^osm_ + bbox: %s"
                  % ("YES" if '"^osm_"' in hf[2] else "NOT FOUND"))
            print("handler deletes v1 fictional rows on every call: %s"
                  % ("YES" if "activity_center_" in hf[2] else "NO"))
        else:
            print("handler nearby_activity_centers NOT FOUND")

    # ---------- check 5: live endpoint GET ----------
    print("=== 5. live endpoint GET (read-only) ===")
    ep_count, ep_el, ep_used = get_endpoint(LAT, LNG, RADIUS_KM)
    if ep_count is None:
        print("endpoint GET failed: %s" % ep_used)
        skipped.append("endpoint")
    else:
        print("GET %s -> %d center(s) in %.1fs" % (ep_used, ep_count, ep_el))

    # ---------- verdict ----------
    print("=== VERDICT ===")
    print("[0] player at %.5f,%.5f; endpoint returned %s; cache near=%s; "
          "exact query kept=%d raw=%d; mirrors reachable=%d/%d"
          % (LAT, LNG,
             ("%d" % ep_count) if ep_count is not None else "UNKNOWN (GET failed)",
             ("%d" % cache["near"]) if cache else "UNKNOWN (skipped)",
             len(q_kept), len(q_raw), len(reachable), len(MIRRORS)))
    verdict = None
    detail = ""
    if ep_count is not None and ep_count > 0:
        verdict, detail = "(e)", "healthy -- the endpoint returns %d center(s) now" % ep_count
    elif cache is not None and cache["near"] > 0 and ep_count == 0:
        verdict = "(d)"
        detail = ("cache HAS %d center(s) within 2km but the endpoint returns [] -- "
                  "the read path is broken (final find query / ^osm_ filter / "
                  "bbox filter in nearby_activity_centers)" % cache["near"])
    elif q_kept and ep_count == 0:
        verdict = "(c)"
        detail = ("the exact query returns %d UT center(s) that pass the handler's "
                  "own parse, but the endpoint returns [] and the cache has %s -- "
                  "the handler drops them between fetch and read (fetch failing "
                  "at call time, cache stamp, or upsert)" % (
                      len(q_kept),
                      ("%d near" % cache["near"]) if cache else "unknown (cache skipped)"))
    elif reachable and not q_raw and ep_count == 0:
        verdict = "(b)"
        if tag_found:
            detail = ("Overpass answers but the exact query returns nothing for UT, "
                      "while the tagging probe found %d object(s) under other tags "
                      "-- the v2 query misses UT in OSM (see 2b)" % len(tag_found))
        else:
            detail = ("Overpass answers but the exact query returns nothing and the "
                      "tagging probe found nothing either -- OSM has no "
                      "amenity=university/college object for UT in this bbox at all")
    elif not reachable and ep_count == 0:
        verdict = "(a)"
        classes = sorted(set(classify_failure(failures.get(u, "")) for u in MIRRORS))
        detail = ("Overpass unreachable from /app on both mirrors (%s) and the "
                  "cache has %s -- centers can never load until Overpass is "
                  "reachable. Failure class: %s"
                  % ("; ".join("%s: %s" % (u.split("/")[2], failures.get(u, "?"))
                                for u in MIRRORS),
                     ("%d near" % cache["near"]) if cache else "unknown (cache skipped)",
                     "; ".join(classes)))
    elif ep_count is None:
        verdict = "undetermined"
        if cache is not None and cache["near"] > 0:
            detail = ("endpoint GET failed so the read path could not be confirmed, "
                      "but the cache HAS %d center(s) near the player -- likely "
                      "healthy; rerun when the endpoint is reachable" % cache["near"])
        elif q_kept:
            detail = ("endpoint GET failed; the exact query returns %d UT center(s) "
                      "that pass the parse -- points at (c) but unconfirmed without "
                      "the endpoint" % len(q_kept))
        elif not reachable:
            detail = ("endpoint GET failed and Overpass is unreachable from /app -- "
                      "points at (a) but unconfirmed without the endpoint")
        else:
            detail = "endpoint GET failed and no other check decides it -- see skips"
    else:
        verdict = "undetermined"
        detail = "no check combination decides it -- see the checks above"
    print("VERDICT: %s %s" % (verdict, detail))
    if q_dropped:
        print("dropped by the handler's parse during the probe: %d element(s) "
              "(see check 2 for reasons)" % len(q_dropped))
    if skipped:
        print("skipped checks: %s" % ", ".join(skipped))
    partial = (srv is None) or ("endpoint" in skipped and "cache" in skipped
                                and not reachable)
    print((PARTIAL if partial else MARKER) + " verdict=%s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
