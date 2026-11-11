#!/usr/bin/env python3
"""Street Legends diag: find an Overpass/map-data mirror the game server
CAN reach, and check which host the working restaurant/bank spawns use.

Verdict already established (minigame-diag/diag-centers-empty.py, run
2026-11-05 22:54 EST -- CENTERS_EMPTY_DIAG_OK verdict=(a)):
  - Overpass is unreachable from /app on BOTH mirrors in
    OSM_OVERPASS_MIRRORS: overpass-api.de -> UNREACHABLE in 0.5s,
    URLError [Errno 111] Connection refused (PERSISTENT);
    overpass.kumi.systems -> UNREACHABLE in 10.7s, read timeout
    (TRANSIENT/saturation). Reachable mirrors 0/2. Exact centers query
    SKIPPED (no mirror). DB cache SKIPPED (pymongo not importable in
    that terminal; MONGO_URL present via backend/.env).
  - The centers handler shape is CORRECT live: OSM_FAST shared block
    YES, OSM_CELL_TIMEOUT 8.0s, OSM_TOTAL_BUDGET 10.0s, query
    amenity=university/college + out center, fetch loops over
    OSM_OVERPASS_MIRRORS with kumi mentioned, parallel gather
    (_osm_gather_cells) YES, no await-in-for-loop. The OSM parallel
    fix DID run and is live. The endpoint GET returns 0 centers in
    10.6s. The problem is purely that /app cannot reach Overpass.

PUZZLE: the restaurant/bank/nightclub spawns WORK from /app -- a live
probe from the parent (22:25 EST) hit the /app backend for Swanton OH
(41.5867,-83.8917) and got 7 restaurants + 1 bank instantly. If those
spawns also use Overpass, either they use a different host, serve
cached rows, or use a different path. This probe finds out which.

This diag runs in the Emergent terminal at /app and checks, in order:
  1. Mirror reachability FROM /app for 6 candidate Overpass mirrors
     (tiny probe, 8s budget each): REACHABLE/UNREACHABLE + elapsed +
     failure class (TRANSIENT 502/503/504/429/timeout vs PERSISTENT
     refused/DNS).
  2. Which host the working spawns use: the fetch/URL code for
     spawn_restaurants, spawn_banks, spawn_nightclubs as they exist
     live in backend/server.py -- which HTTP host/URL each posts to
     (Overpass mirror? a different host? no HTTP at all -- cached DB
     rows only?), plus whether each has a cache.
  3. Which hosts the four OSM endpoints use: whether the
     activity-centers, pharmacies, parks, and billboards fetch
     functions all use OSM_OVERPASS_MIRRORS (the mirror list as defined
     live) or if any uses a different host.
  4. Read-only DB counts (same pattern as diag-centers-empty): the
     restaurants/banks/nightclubs collections -- totals + rows near
     Swanton -- so a spawn serving cached rows is visible.
  5. A live read-only GET of the three spawn endpoints for Swanton
     (the known reference point) plus restaurants for the player's UT
     spot, with elapsed time, proving the spawn path works at diag
     time.

Verdict, one of:
  (a) at least one mirror reachable -- name it (the fix is to add it
      to OSM_OVERPASS_MIRRORS).
  (b) no mirror reachable BUT a spawn uses a different working host --
      name that host (the fix is to point the OSM fetches at it). A
      host counts as proven working only if the spawn that uses it
      returned rows in check 5 at diag time.
  (c) no mirror reachable AND the spawns are DB-only / serve cached
      rows -- the spawns work from cache while centers never had a
      successful fetch (the fix is to seed/populate the centers cache
      from a reachable source or to find any reachable host).
  (d) nothing reachable and no working host found -- no OSM path from
      /app (the fix must be a different data source or a seeded cache
      of real places).
  undetermined -- not enough evidence (see which checks skipped).

Read-only: never edits a file, never restarts anything, never calls a
state-changing endpoint. Only network calls are Overpass POSTs, a few
read-only GETs of the spawn endpoints, and (if the app env is
available) a read-only pymongo read of the spawn collections. Every
network call has its own short timeout, so the diag never hangs.

Run from /app:  python3 minigame-diag/diag-osm-mirrors.py
Test hooks (env, defaults are the production values): OSM_MIRRORS_DIAG_MIRRORS
(comma-separated mirror URLs), OSM_MIRRORS_DIAG_ENDPOINT (base URL for the
spawn GETs), OSM_MIRRORS_DIAG_MONGO_JSON (path to a JSON file the fake-pymongo
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
from urllib.parse import urlparse

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SWANTON_LAT, SWANTON_LNG = 41.5867, -83.8917
UT_LAT, UT_LNG = 41.65414, -83.62081
PLAYER_LEVEL = 14
MIRRORS = os.environ.get("OSM_MIRRORS_DIAG_MIRRORS", "").split(",") \
    if os.environ.get("OSM_MIRRORS_DIAG_MIRRORS") else [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass.private.coffee/api/interpreter",
        "https://overpass.nchc.org.tw/api/interpreter",
        "https://overpass.osm.ch/api/interpreter",
        "https://overpass.openstreetmap.ru/api/interpreter",
    ]
MIRRORS = [m.strip() for m in MIRRORS if m.strip()]
ENDPOINT_BASE = os.environ.get("OSM_MIRRORS_DIAG_ENDPOINT",
                               "https://gta-quest-map.emergent.host")
MIRROR_BUDGET = 8.0     # seconds per mirror for the tiny probe
ENDPOINT_BUDGET = 15.0  # seconds per spawn GET
MARKER = "OSM_MIRRORS_DIAG_OK"
PARTIAL = "OSM_MIRRORS_DIAG_PARTIAL"

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


def span(lines, start_pat, end_pat=r"^(async def |def |@api_router|class )"):
    """Return (start_line_1based, end_line_1based_exclusive, text) of the
    function starting at the first line matching start_pat, or None."""
    s = next((i for i, l in enumerate(lines) if re.search(start_pat, l)), None)
    if s is None:
        return None
    e = next((i for i in range(s + 1, len(lines)) if re.match(end_pat, lines[i])), len(lines))
    return s + 1, e, "\n".join(lines[s:e])


def host_of(url):
    try:
        return urlparse(url).netloc or url
    except Exception:
        return url


def classify_spawn(name, body):
    """How does this spawn get its rows? Returns (class, urls, collections).
    Classes: LIVE_OVERPASS / LIVE_OTHER_HOST / LIVE_HTTP_NO_LITERAL /
    MIXED (DB first, live fetch on miss) / DB_ONLY / UNKNOWN."""
    urls = sorted(set(re.findall(r'https?://[^\s"\'\)\],]+', body)))
    has_http_client = bool(re.search(
        r"httpx|requests\.|urlopen|aiohttp|client\.post|client\.get|session\.post",
        body))
    db_colls = sorted(set(re.findall(
        r"db\.([A-Za-z_][A-Za-z0-9_]*)\.(find|find_one|insert_one|update_one|count_documents)",
        body)))
    db_colls = [c for c, _ in db_colls]
    has_db = bool(db_colls)
    overpass_urls = [u for u in urls if "overpass" in u.lower()]
    other_urls = [u for u in urls if "overpass" not in u.lower()]
    if overpass_urls and has_db:
        cls = "MIXED (DB first, live Overpass fetch on miss)"
    elif overpass_urls:
        cls = "LIVE_OVERPASS"
    elif other_urls and has_db:
        cls = "MIXED (DB first, live fetch on miss)"
    elif other_urls:
        cls = "LIVE_OTHER_HOST"
    elif has_http_client:
        cls = "LIVE_HTTP_NO_LITERAL (http client used but no URL literal found)"
    elif has_db:
        cls = "DB_ONLY (no HTTP -- serves cached/seeded DB rows)"
    else:
        cls = "UNKNOWN (no HTTP and no DB read found)"
    return cls, urls, db_colls


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


def spawn_db_check():
    """Read-only counts + Swanton sample of the spawn collections
    (restaurants, banks, nightclubs) plus activity_centers for contrast.
    Returns a dict, or None (skipped + reason printed). Never raises."""
    url, source = _mongo_url()
    if not url:
        print("db: SKIPPED -- %s (read-only DB check needs the app env)" % source)
        return None
    try:
        import pymongo  # type: ignore
    except ImportError:
        print("db: SKIPPED -- pymongo not importable in this terminal "
              "(MONGO_URL present via %s, but no driver to read it)" % source)
        return None
    try:
        client = pymongo.MongoClient(url, serverSelectionTimeoutMS=5000)
        db = client.get_default_database()
        if db is None:
            print("db: SKIPPED -- MONGO_URL has no default database")
            return None
        out = {}
        print("db: source=%s db=%s" % (source, db.name))
        for coll, label in (("restaurants", "restaurants"),
                            ("banks", "banks"),
                            ("nightclubs", "nightclubs"),
                            ("activity_centers", "activity_centers")):
            total = db[coll].count_documents({})
            near = list(db[coll].find({
                "latitude": {"$gte": SWANTON_LAT - 0.02, "$lte": SWANTON_LAT + 0.02},
                "longitude": {"$gte": SWANTON_LNG - 0.02, "$lte": SWANTON_LNG + 0.02},
            }).limit(10))
            print("db: %s total=%d near Swanton=%d" % (label, total, len(near)))
            for r in near:
                print("db:   %s row id=%s name=%r lat=%s lng=%s"
                      % (label, r.get("id"), r.get("name"),
                         r.get("latitude"), r.get("longitude")))
            out[coll] = {"total": total, "near": near}
        return out
    except Exception as e:  # noqa: BLE001
        print("db: SKIPPED -- mongo read failed (%s: %s)" % (type(e).__name__, e))
        return None


def get_spawn(kind, lat, lng):
    """Read-only GET of one spawn endpoint. Tries the /app-local backend
    first (localhost:8000), then the public host. Returns
    (count_or_None, elapsed, used_url_or_error, sample_names). Never raises."""
    path = ("/api/%s/spawn?latitude=%s&longitude=%s&player_level=%s"
            % (kind, lat, lng, PLAYER_LEVEL))
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
            with urllib.request.urlopen(req, timeout=ENDPOINT_BUDGET) as r:
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


def main():
    skipped = []

    print("=== Overpass mirrors diag (why centers are empty but spawns work) ===")
    print("reference point: Swanton lat=%s lng=%s ; player UT lat=%s lng=%s"
          % (SWANTON_LAT, SWANTON_LNG, UT_LAT, UT_LNG))

    # ---------- check 1: mirror reachability from /app ----------
    print("=== 1. Overpass mirror reachability from /app (tiny probe: node(1), 8s each) ===")
    reachable = []
    failures = {}
    for url in MIRRORS:
        status, el, payload, err, client = post_overpass(url, TINY_QUERY, MIRROR_BUDGET)
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

    # ---------- check 2: which host the working spawns use ----------
    print("=== 2. which host do the working spawns use? (backend/server.py) ===")
    srv = read("backend/server.py")
    spawns = {}
    if srv is None:
        print("backend/server.py MISSING - spawn code cannot be checked")
        skipped.append("server-file")
    else:
        lines = srv.splitlines()
        for fn in ("spawn_restaurants", "spawn_banks", "spawn_nightclubs"):
            sp = span(lines, r"(async )?def %s" % fn)
            if not sp:
                print("spawn %s: NOT FOUND in backend/server.py" % fn)
                spawns[fn] = {"class": "NOT FOUND", "urls": [], "collections": []}
                continue
            print("-- %s (lines %d-%d) --" % (fn, sp[0], sp[1]))
            body = sp[2]
            for i, l in enumerate(body.splitlines()[:60]):
                print("  %d: %s" % (sp[0] + i, l))
            if len(body.splitlines()) > 60:
                print("  ... (%d more lines, truncated)"
                      % (len(body.splitlines()) - 60))
            cls, urls, colls = classify_spawn(fn, body)
            print("spawn %s: class=%s" % (fn, cls))
            print("spawn %s: URL literals=%s" % (fn, urls if urls else "NONE"))
            print("spawn %s: DB collections=%s" % (fn, colls if colls else "NONE"))
            spawns[fn] = {"class": cls, "urls": urls, "collections": colls}

    # ---------- check 3: which hosts the four OSM endpoints use ----------
    print("=== 3. which hosts do the four OSM endpoints use? ===")
    if srv is None:
        print("SKIPPED -- backend/server.py missing")
        skipped.append("server-file")
    else:
        lines = srv.splitlines()
        m = re.search(r"OSM_OVERPASS_MIRRORS\s*=\s*\[(.*?)\]", srv, re.S)
        if m:
            listed = re.findall(r'"([^"]+)"', m.group(1)) or \
                re.findall(r"'([^']+)'", m.group(1))
            print("OSM_OVERPASS_MIRRORS defined live: %s" % listed)
        else:
            print("OSM_OVERPASS_MIRRORS: NOT FOUND in backend/server.py")
            listed = []
        for const in re.findall(r"([A-Za-z_][A-Za-z0-9_]*OVERPASS_URL)\s*=\s*\"([^\"]+)\"",
                                srv):
            print("other Overpass URL const live: %s = %s" % (const[0], const[1]))
        for fetch_fn in ("_activity_center_fetch_cell", "_pharmacy_fetch_cell",
                         "_park_fetch_cell", "_billboard_fetch_cell"):
            ff = span(lines, r"(async )?def %s" % fetch_fn)
            if not ff:
                print("fetch %s: NOT FOUND" % fetch_fn)
                continue
            urls = sorted(set(re.findall(r'https?://[^\s"\'\)\],]+', ff[2])))
            print("fetch %s: lines %d-%d uses OSM_OVERPASS_MIRRORS=%s URL literals=%s"
                  % (fetch_fn, ff[0], ff[1],
                     "YES" if "OSM_OVERPASS_MIRRORS" in ff[2] else "NO",
                     urls if urls else "NONE"))

    # ---------- check 4: spawn DB counts ----------
    print("=== 4. spawn DB collections (read-only) ===")
    dbinfo = spawn_db_check()
    if dbinfo is None:
        skipped.append("db")

    # ---------- check 5: live spawn GETs ----------
    print("=== 5. live spawn GETs (read-only) ===")
    gets = {}
    for kind in ("restaurants", "banks", "nightclubs"):
        count, el, used, names = get_spawn(kind, SWANTON_LAT, SWANTON_LNG)
        if count is None:
            print("GET %s/spawn Swanton: FAILED -- %s" % (kind, used))
            gets[("swanton", kind)] = None
        else:
            print("GET %s -> %d item(s) in %.1fs (Swanton) sample=%s"
                  % (used, count, el, names))
            gets[("swanton", kind)] = count
    count, el, used, names = get_spawn("restaurants", UT_LAT, UT_LNG)
    if count is None:
        print("GET restaurants/spawn UT: FAILED -- %s" % used)
        gets[("ut", "restaurants")] = None
    else:
        print("GET %s -> %d item(s) in %.1fs (UT) sample=%s" % (used, count, el, names))
        gets[("ut", "restaurants")] = count

    # ---------- verdict ----------
    print("=== VERDICT ===")
    mirror_hosts = {host_of(u) for u in MIRRORS}
    spawn_hosts = {}
    for fn, info in spawns.items():
        for u in info.get("urls", []):
            spawn_hosts.setdefault(host_of(u), []).append(fn)
    working_other = []
    for host, fns in spawn_hosts.items():
        if host in mirror_hosts:
            continue
        for fn in fns:
            kind = fn.replace("spawn_", "")
            if gets.get(("swanton", kind)) and gets[("swanton", kind)] > 0:
                working_other.append((host, fn))
    print("[0] mirrors reachable=%d/%d %s; spawn hosts=%s; working other hosts=%s; "
          "spawn GETs Swanton=%s"
          % (len(reachable), len(MIRRORS), reachable, spawn_hosts, working_other,
             {k[1]: v for k, v in gets.items() if k[0] == "swanton"}))
    verdict = None
    detail = ""
    if reachable:
        verdict = "(a)"
        detail = ("at least one mirror reachable from /app: %s -- the fix is to "
                  "add it to OSM_OVERPASS_MIRRORS" % ", ".join(reachable))
    elif working_other:
        verdict = "(b)"
        detail = ("no tested mirror reachable, but the spawn code posts to a "
                  "different host that works at diag time: %s -- the fix is to "
                  "point the OSM fetches at it"
                  % ", ".join(sorted(set("%s (via %s)" % (h, f)
                                        for h, f in working_other))))
    elif any(v is not None and v > 0 for v in gets.values()):
        verdict = "(c)"
        db_note = ""
        if dbinfo is not None:
            db_note = (" spawn DB totals: restaurants=%d banks=%d nightclubs=%d "
                       "activity_centers=%d"
                       % (dbinfo["restaurants"]["total"], dbinfo["banks"]["total"],
                          dbinfo["nightclubs"]["total"],
                          dbinfo["activity_centers"]["total"]))
        detail = ("no mirror reachable, but the spawn GETs returned rows -- the "
                  "spawns serve cached/seeded DB rows (spawn classes: %s) while "
                  "the centers never had a successful fetch.%s The fix is to "
                  "seed/populate the centers cache from a reachable source or "
                  "find any reachable host."
                  % (", ".join("%s=%s" % (f, spawns[f]["class"]) for f in spawns),
                     db_note))
    else:
        verdict = "(d)"
        detail = ("no mirror reachable and no working host found -- no OSM path "
                  "from /app. The fix must be a different data source or a "
                  "seeded cache of real places.")
    if srv is None and not reachable and all(v is None for v in gets.values()):
        verdict = "undetermined"
        detail = ("server.py is missing and no mirror or spawn endpoint could "
                  "be reached -- rerun with the code present")
    print("VERDICT: %s %s" % (verdict, detail))
    if skipped:
        print("skipped checks: %s" % ", ".join(skipped))
    partial = (srv is None) or (not reachable
                                and all(v is None for v in gets.values())
                                and dbinfo is None)
    print((PARTIAL if partial else MARKER) + " verdict=%s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
