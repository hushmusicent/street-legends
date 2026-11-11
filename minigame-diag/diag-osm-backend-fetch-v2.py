#!/usr/bin/env python3
"""Street Legends diag v2: test the backend fetch with the backend's REAL
interpreter.

Why v2 exists: the v1 probe (diag-osm-backend-runtime.py) established two
solid facts and then failed on its own flaw:

  - Patch IS in backend/server.py on disk: openstreetmap.fr first,
    OSM_CACHE_EPOCH present, mirrors [.fr, osm.ch, .de, kumi].
  - The backend DID restart after patch + Publish: uvicorn workers
    started 09:55:59 and 09:56:02 UTC, both after the patch run
    (09:01 UTC). New code is running.
  - The endpoint STILL returns []: his spot 0 centers in 2.6s,
    downtown 0 centers in 10.3s (full budget burned).
  - THE FLAW: v1 picked the backend python from a process's /proc exe,
    which resolves symlinks and landed on the plugins python -- the
    interpreter that does NOT have fastapi -- so `import server.py`
    FAILED (ModuleNotFoundError: No module named 'fastapi') and the
    backend fetch + httpx-vs-urllib checks never ran.

The REAL backend python is the server:app worker's interpreter:
its cmdline argv[0] is the venv python (the worker runs as
`<venv>/bin/python <venv>/bin/uvicorn server:app ...`). The venv
python binary may itself be a symlink to the system python -- what
makes it the backend python is the venv path (sys.prefix), so v2
resolves argv[0] from the server:app process cmdline and NEVER uses
a process exe path, NEVER the terminal's bare python3, and NEVER the
plugins python (the other uvicorn worker, port 8010). If no venv
python can be found, v2 prints VENV-PYTHON-NOT-FOUND and stops the
fetch checks instead of faking them.

This probe runs in the Emergent terminal at /app and checks, in order:
  1. INTERPRETER: resolve the venv python from the live server:app
     process cmdline (pid + cmdline printed), then verify it really
     has the backend deps (`import fastapi, httpx`). Missing module
     stops the run (verdict undetermined).
  2. IMPORT: import server.py with THAT python in a guarded
     subprocess (25s cap). Prints the mirrors list the imported code
     sees, OSM_CACHE_EPOCH, OSM_CELL_TIMEOUT, OSM_TOTAL_BUDGET.
  3. BACKEND FETCH: with the imported code, run the live per-mirror
     fetch for his cell (bbox s=41.65 w=-83.65 n=41.70 e=-83.60) AND
     for the downtown cell (center 41.6520,-83.5370, 2km bbox computed
     the handler's way), per mirror: status/seconds/elements or the
     exact error. Then call the real _activity_center_fetch_cell for
     his cell and print the final list it returns.
  4. HTTPX vs URLLIB: from the SAME venv python, one httpx POST and
     one urllib POST to openstreetmap.fr with the centers query for
     his cell (8s cap each). Prints the venv python's proxy env vars
     too. This isolates "httpx broken in the backend env" from
     "the backend container reaches nothing".
  5. ENDPOINT SANITY (read-only GETs): centers nearby at his spot +
     downtown, counts + seconds.

Verdict, exactly one of:
  (a) the venv python's fetch returns the 2 centers (Davis College +
      The University of Toledo) but the endpoint still returns [] --
      mapping/DB mismatch (both results given);
  (b) the venv python's httpx fails/hangs on .fr while urllib works
      -- httpx/proxy problem (both outcomes + proxy vars given);
  (c) the venv python cannot reach ANY mirror (per-mirror outcomes
      given) -- backend-container egress problem;
  (d) the endpoint returns centers now -- the fix is live;
  (e) undetermined -- venv python not found, or deps/import failed
      (exact error given).

Read-only: never edits a file, never restarts or kills anything (the
only kill is the probe's own diagnostic subprocess if it exceeds its
cap). Only network calls are the Overpass POSTs from the venv python
and read-only endpoint GETs. Global deadline ~85s; late steps are
skipped with a note instead of hanging.

Run from /app:  python3 minigame-diag/diag-osm-backend-fetch-v2.py
Test hooks (env): OSM_BF2_ROOT (default /app, or argv[1]),
OSM_BF2_ENDPOINT (default https://gta-quest-map.emergent.host),
OSM_BF2_PROC_JSON (harness: fake /proc results),
OSM_BF2_PROC_NOT_VISIBLE (harness: simulate no process),
OSM_BF2_DEPS_MOCK (harness: "ok" or "missing:<module>"),
OSM_BF2_MOCK_SUB_JSON (harness: canned import/fetch subprocess),
OSM_BF2_MOCK_DIRECT_JSON (harness: canned httpx/urllib subprocess),
OSM_BF2_ENDPOINT_JSON (harness: canned endpoint GET results),
OSM_BF2_VENV_PY (harness: force the venv python path).
"""
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
    os.environ.get("OSM_BF2_ROOT", "/app"))
ENDPOINT_BASE = os.environ.get(
    "OSM_BF2_ENDPOINT", "https://gta-quest-map.emergent.host").rstrip("/")
FR_URL = "https://overpass.openstreetmap.fr/api/interpreter"
LAT, LNG = 41.66308, -83.61536          # his spot (UT)
DT_LAT, DT_LNG = 41.6520, -83.5370      # downtown Toledo (fresh cells)
CELL = (41.65, -83.65, 41.70, -83.60)   # his cell bbox s,w,n,e
CELL_KEY = "833_-1673"
MARKER = "OSM_BACKEND_FETCH_V2_OK"
PARTIAL = "OSM_BACKEND_FETCH_V2_PARTIAL"
START = time.time()
DEADLINE = START + 85.0

skipped = []


def left():
    return DEADLINE - time.time()


def fmt_ts(epoch):
    try:
        return datetime.fromtimestamp(epoch).astimezone().strftime(
            "%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return "epoch %s" % epoch


def centers_query(s, w, n, e):
    return ("[out:json][timeout:25];\n(\n"
            '  nwr["amenity"="university"](%s,%s,%s,%s);\n'
            '  nwr["amenity"="college"](%s,%s,%s,%s);\n'
            ");\n out center;\n" % (s, w, n, e, s, w, n, e))


# ------------------------------------------------------------ process scan
def _proc_start_epoch(pid):
    """Start epoch of a pid via /proc/stat btime + stat starttime ticks."""
    try:
        btime = None
        for line in open("/proc/stat").read().splitlines():
            if line.startswith("btime "):
                btime = int(line.split()[1])
                break
        parts = open("/proc/%d/stat" % pid).read().split()
        ticks = int(parts[21])
        clk = os.sysconf("SC_CLK_TCK")
        if btime is None:
            return None
        return btime + ticks / clk
    except Exception:
        return None


def _proc_info(pid):
    try:
        cmd = open("/proc/%d/cmdline" % pid, "rb").read().decode(
            "utf-8", "ignore").replace("\0", " ").strip()
    except Exception:
        cmd = ""
    try:
        exe = os.readlink("/proc/%d/exe" % pid)
    except Exception:
        exe = ""
    start = _proc_start_epoch(pid)
    return {"pid": pid, "cmd": cmd, "exe": exe, "start": start}


def find_procs():
    """All processes (mockable). Returns list of proc dicts."""
    mock = os.environ.get("OSM_BF2_PROC_JSON")
    if mock:
        try:
            return json.load(open(mock))
        except Exception as e:  # noqa: BLE001
            print("WARNING: bad OSM_BF2_PROC_JSON (%s)" % e)
            return []
    if os.environ.get("OSM_BF2_PROC_NOT_VISIBLE"):
        return []
    procs = []
    try:
        pids = [int(n) for n in os.listdir("/proc") if n.isdigit()]
    except Exception:
        pids = []
    for pid in pids:
        info = _proc_info(pid)
        if info["cmd"]:
            procs.append(info)
    if procs:
        return procs
    try:
        out = subprocess.run(["ps", "-eo", "pid,etimes,args"],
                             capture_output=True, text=True, timeout=10).stdout
        for line in out.splitlines()[1:]:
            parts = line.strip().split(None, 2)
            if len(parts) < 3:
                continue
            pid, etimes, cmd = int(parts[0]), int(parts[1]), parts[2]
            procs.append({"pid": pid, "cmd": cmd, "exe": "",
                          "start": time.time() - etimes})
    except Exception as e:  # noqa: BLE001
        print("WARNING: ps fallback failed (%s)" % e)
    return procs


def resolve_venv_python():
    """The backend's REAL interpreter, from the live server:app worker.

    Returns (path, pid, cmdline) or (None, reason). The path is argv[0]
    of the server:app uvicorn process -- a venv python -- and is never
    a /proc exe path (symlinks resolve away the venv), never the
    terminal's bare python3, and never the other (plugins) worker's
    interpreter. Candidates whose argv[0] is not a venv python are
    rejected and reported.
    """
    forced = os.environ.get("OSM_BF2_VENV_PY")
    if forced:
        return forced, None, "env OSM_BF2_VENV_PY (harness)"
    procs = find_procs()
    server_app = [p for p in procs if "server:app" in (p.get("cmd") or "")]
    rejected = []
    for p in server_app:
        argv0 = (p.get("cmd") or "").split()[0] if p.get("cmd") else ""
        if argv0 and "venv" in argv0.lower():
            return argv0, p["pid"], \
                "server:app process cmdline argv[0] (pid %s)" % p["pid"]
        if argv0:
            rejected.append("pid %s argv[0]=%s (not a venv python)"
                            % (p["pid"], argv0))
    if rejected:
        print("rejected non-venv server:app candidates: %s"
              % "; ".join(rejected))
    # Fallbacks: known venv locations (checked for existence only).
    for rel in ("/root/.venv/bin/python", ".venv/bin/python",
                "venv/bin/python", "backend/.venv/bin/python",
                "backend/venv/bin/python"):
        cand = Path(rel) if rel.startswith("/") else ROOT / rel
        if cand.exists():
            return str(cand), None, "venv found at %s" % rel
    if not server_app and not rejected:
        reason = ("no server:app process visible from this terminal and "
                  "no venv found at the known paths")
    else:
        reason = ("no venv python found: server:app candidates were "
                  "rejected (see above) and no venv exists at the known "
                  "paths")
    return None, None, reason


def check_deps(py_path):
    """Verify the venv python really has the backend deps."""
    mock = os.environ.get("OSM_BF2_DEPS_MOCK")
    if mock:
        if mock == "ok":
            print("deps check (mocked): fastapi + httpx import OK")
            return True, None
        if mock.startswith("missing:"):
            mod = mock.split(":", 1)[1]
            print("deps check (mocked): MISSING module '%s'" % mod)
            return False, mod
    try:
        r = subprocess.run(
            [py_path, "-c", "import fastapi, httpx; print('deps OK')"],
            capture_output=True, text=True, timeout=15)
        if r.returncode == 0:
            print("deps check: %s" % (r.stdout.strip() or "deps OK"))
            return True, None
        m = re.search(r"No module named '([^']+)'", r.stderr or "")
        mod = m.group(1) if m else None
        print("deps check FAILED: returncode=%d stderr=%s"
              % (r.returncode, (r.stderr or "").strip().splitlines()[-1:]
                  or "(none)"))
        return False, mod
    except subprocess.TimeoutExpired:
        print("deps check: TIMEOUT after 15s")
        return False, None
    except Exception as e:  # noqa: BLE001
        print("deps check: could not run %s (%s: %s)"
              % (py_path, type(e).__name__, e))
        return False, None


# ------------------------------------------- subprocess 1: import + fetch
SUB_FETCH = r'''
import asyncio, json, math, os, sys, time
MOCK = os.environ.get("OSM_BF2_MOCK_SUB_JSON")
def emit(kind, **kw):
    d = {"kind": kind}; d.update(kw)
    print("SUBJSON " + json.dumps(d), flush=True)
def names_of(els):
    return [e.get("tags", {}).get("name") for e in (els or [])[:5]]
T0 = time.time()
if MOCK:
    data = json.load(open(MOCK))
    for line in data.get("lines", []):
        print(line, flush=True)
    for k, v in data.get("emit", {}).items():
        emit(k, **v)
    sys.exit(0)
sys.path.insert(0, os.environ.get("OSM_BF2_BACKEND_DIR", "backend"))
try:
    import server as srv
except Exception as e:
    print("import server.py FAILED: %s: %s" % (type(e).__name__, e), flush=True)
    emit("import_error", error="%s: %s" % (type(e).__name__, e))
    sys.exit(0)
mirrors = list(getattr(srv, "OSM_OVERPASS_MIRRORS", []) or [])
epoch = getattr(srv, "OSM_CACHE_EPOCH", None)
cell_timeout = getattr(srv, "OSM_CELL_TIMEOUT", None)
total_budget = getattr(srv, "OSM_TOTAL_BUDGET", None)
print("imported server.py mirrors: %s" % mirrors, flush=True)
print("OSM_CACHE_EPOCH=%s OSM_CELL_TIMEOUT=%s OSM_TOTAL_BUDGET=%s" % (epoch, cell_timeout, total_budget), flush=True)
emit("code", mirrors=mirrors, epoch=epoch, cell_timeout=cell_timeout, total_budget=total_budget)
S, W, N, E = 41.65, -83.65, 41.70, -83.60
try:
    query = srv._activity_center_overpass_query(S, W, N, E)
except Exception as e:
    print("query builder missing/failed (%s) -- using inline template" % e, flush=True)
    query = ("[out:json][timeout:25];\n(\n"
             '  nwr["amenity"="university"](%s,%s,%s,%s);\n'
             '  nwr["amenity"="college"](%s,%s,%s,%s);\n'
             ");\n out center;\n" % (S, W, N, E, S, W, N, E))
async def per_mirror(q, timeout=3.0):
    import httpx
    out = []
    for url in mirrors:
        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout) as c:
                r = await c.post(url, data={"data": q})
            els = r.json().get("elements", []) if r.status_code == 200 else []
            print("mirror %s: %s in %.1fs elements=%d names=%s" % (url, r.status_code, time.time() - t0, len(els), names_of(els)), flush=True)
            out.append({"url": url, "status": r.status_code, "seconds": round(time.time() - t0, 1), "elements": len(els), "names": names_of(els)})
        except Exception as e:
            print("mirror %s: FAILED in %.1fs %s: %s" % (url, time.time() - t0, type(e).__name__, e), flush=True)
            out.append({"url": url, "status": None, "seconds": round(time.time() - t0, 1), "elements": 0, "error": "%s: %s" % (type(e).__name__, e)})
    return out
per_his = asyncio.run(per_mirror(query))
emit("per_mirror_his", results=per_his)
try:
    res = asyncio.run(asyncio.wait_for(srv._activity_center_fetch_cell("833_-1673", S, W, N, E), timeout=8))
    names = [c.get("name") for c in (res or [])]
    print("fetch _activity_center_fetch_cell (his cell) -> %s center(s): %s" % (len(res or []), names), flush=True)
    emit("fetch_result", count=len(res or []), names=names)
except Exception as e:
    print("fetch his cell FAILED: %s: %s" % (type(e).__name__, e), flush=True)
    emit("fetch_result", count=None, error="%s: %s" % (type(e).__name__, e))
if time.time() - T0 < 15:
    try:
        import math as _m
        dlat = 2.0 / 111.0
        dlng = 2.0 / (111.0 * max(0.2, _m.cos(_m.radians(41.6520))))
        i = _m.floor(41.6520 / 0.05); j = _m.floor(-83.5370 / 0.05)
        ds, dw, dn, de = i * 0.05, j * 0.05, (i + 1) * 0.05, (j + 1) * 0.05
        print("downtown cell: key=%s_%s bbox s=%.2f w=%.2f n=%.2f e=%.2f" % (i, j, ds, dw, dn, de), flush=True)
        try:
            q_dt = srv._activity_center_overpass_query(ds, dw, dn, de)
        except Exception:
            q_dt = ("[out:json][timeout:25];\n(\n"
                    '  nwr["amenity"="university"](%s,%s,%s,%s);\n'
                    '  nwr["amenity"="college"](%s,%s,%s,%s);\n'
                    ");\n out center;\n" % (ds, dw, dn, de, ds, dw, dn, de))
        per_dt = asyncio.run(per_mirror(q_dt))
        emit("per_mirror_downtown", results=per_dt)
    except Exception as e:
        print("downtown per-mirror FAILED: %s: %s" % (type(e).__name__, e), flush=True)
        emit("per_mirror_downtown", results=[], error="%s: %s" % (type(e).__name__, e))
else:
    print("downtown per-mirror SKIPPED (subprocess time budget)", flush=True)
    emit("per_mirror_downtown", results=[], error="skipped: time budget")
'''

# -------------------------------------- subprocess 2: httpx vs urllib (.fr)
SUB_DIRECT = r'''
import json, os, sys, time, urllib.request, urllib.parse
MOCK = os.environ.get("OSM_BF2_MOCK_DIRECT_JSON")
FR = "https://overpass.openstreetmap.fr/api/interpreter"
def emit(kind, **kw):
    d = {"kind": kind}; d.update(kw)
    print("SUBJSON " + json.dumps(d), flush=True)
def names_of(els):
    return [e.get("tags", {}).get("name") for e in (els or [])[:5]]
if MOCK:
    data = json.load(open(MOCK))
    for line in data.get("lines", []):
        print(line, flush=True)
    for k, v in data.get("emit", {}).items():
        emit(k, **v)
    sys.exit(0)
query = os.environ.get("OSM_BF2_QUERY", "")
t0 = time.time()
try:
    import httpx
    with httpx.Client(timeout=8.0) as c:
        r = c.post(FR, data={"data": query})
    els = r.json().get("elements", []) if r.status_code == 200 else []
    print("httpx direct to .fr: %s in %.1fs elements=%d names=%s" % (r.status_code, time.time() - t0, len(els), names_of(els)), flush=True)
    emit("httpx_direct", status=r.status_code, seconds=round(time.time() - t0, 1), elements=len(els), names=names_of(els))
except Exception as e:
    print("httpx direct to .fr FAILED in %.1fs %s: %s" % (time.time() - t0, type(e).__name__, e), flush=True)
    emit("httpx_direct", status=None, seconds=round(time.time() - t0, 1), elements=0, error="%s: %s" % (type(e).__name__, e))
t0 = time.time()
try:
    body = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(FR, data=body, headers={"User-Agent": "StreetLegends-diag/1.0"})
    with urllib.request.urlopen(req, timeout=8) as r:
        raw = r.read()
    els = json.loads(raw.decode("utf-8", "ignore")).get("elements", [])
    print("urllib direct to .fr: %s in %.1fs elements=%d names=%s" % (r.status, time.time() - t0, len(els), names_of(els)), flush=True)
    emit("urllib_direct", status=r.status, seconds=round(time.time() - t0, 1), elements=len(els), names=names_of(els))
except Exception as e:
    print("urllib direct to .fr FAILED in %.1fs %s: %s" % (time.time() - t0, type(e).__name__, e), flush=True)
    emit("urllib_direct", status=None, seconds=round(time.time() - t0, 1), elements=0, error="%s: %s" % (type(e).__name__, e))
proxies = {k: os.environ[k] for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy") if os.environ.get(k)}
print("proxy env in venv python: %s" % (proxies if proxies else "none set"), flush=True)
emit("proxies", proxies=proxies)
'''


def run_sub(py_path, script, cap, label, extra_env=None):
    """Run a diagnostic script under the venv python. Returns the parsed
    SUBJSON dict (possibly partial on timeout) or None if it could not
    run at all. Never raises."""
    import tempfile
    sub = {}
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         dir="/tmp") as f:
            f.write(script)
            tmp = f.name
        env = dict(os.environ)
        env["OSM_BF2_BACKEND_DIR"] = str(ROOT / "backend")
        if extra_env:
            env.update(extra_env)
        try:
            r = subprocess.run([py_path, tmp], capture_output=True,
                               text=True, timeout=cap, env=env)
            out, err = r.stdout, r.stderr
        except subprocess.TimeoutExpired as e:
            print("%s: TIMEOUT after %ds (killed by probe) -- "
                  "using partial output" % (label, cap))
            out = e.stdout.decode() if isinstance(e.stdout, bytes) \
                else (e.stdout or "")
            err = e.stderr.decode() if isinstance(e.stderr, bytes) \
                else (e.stderr or "")
        print("--- %s output (%s) ---" % (label, py_path))
        print((out or "").rstrip() or "(no stdout)")
        if (err or "").strip():
            print("--- subprocess stderr (last 5 lines) ---")
            print("\n".join(err.strip().splitlines()[-5:]))
        for line in (out or "").splitlines():
            if line.startswith("SUBJSON "):
                try:
                    d = json.loads(line[len("SUBJSON "):])
                    sub[d.get("kind")] = d
                except Exception:
                    pass
        os.unlink(tmp)
        return sub
    except Exception as e:  # noqa: BLE001
        print("%s: FAILED to run (%s: %s)" % (label, type(e).__name__, e))
        return None


# ---------------------------------------------------------------- check 5
def get_centers(lat, lng):
    mock = os.environ.get("OSM_BF2_ENDPOINT_JSON")
    if mock:
        try:
            data = json.load(open(mock))
            key = "his" if (lat, lng) == (LAT, LNG) else "downtown"
            d = data.get(key, {})
            return d.get("count"), d.get("seconds"), "mock"
        except Exception as e:  # noqa: BLE001
            return None, None, "bad OSM_BF2_ENDPOINT_JSON (%s)" % e
    url = ("%s/api/activity-centers/nearby?latitude=%s&longitude=%s"
           % (ENDPOINT_BASE, lat, lng))
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "StreetLegends-diag/1.0",
            "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=12) as r:
            raw = r.read()
        el = time.time() - t0
        try:
            data = json.loads(raw.decode("utf-8", "ignore"))
            items = data if isinstance(data, list) else []
            names = [it.get("name") for it in items[:3]
                     if isinstance(it, dict)]
            return len(items), el, "%s names=%s" % (url, names)
        except Exception:
            return None, el, "%s: non-JSON" % url
    except Exception as e:  # noqa: BLE001
        return None, time.time() - t0, "%s: %s: %s" % (url, type(e).__name__, e)


def check_endpoints():
    print("=== 5. endpoint sanity (read-only GETs) ===")
    out = {}
    for label, (lat, lng) in (("his spot", (LAT, LNG)),
                              ("downtown", (DT_LAT, DT_LNG))):
        if left() < 14:
            print("GET centers %s: SKIPPED -- global deadline near" % label)
            skipped.append("endpoint-%s" % label)
            out[label] = (None, None)
            continue
        count, el, used = get_centers(lat, lng)
        if count is None:
            print("GET centers %s: FAILED -- %s" % (label, used))
        else:
            print("GET centers %s -> %d center(s) in %.1fs -- %s"
                  % (label, count, el, used))
        out[label] = (count, el)
    return out


def main():
    print("=== OSM backend-fetch diag v2 (the backend's REAL python) ===")
    print("reference: his spot lat=%s lng=%s ; downtown lat=%s lng=%s ; "
          "his cell bbox s,w,n,e=%s" % (LAT, LNG, DT_LAT, DT_LNG, CELL))

    # ---- check 1: interpreter --------------------------------------
    print("=== 1. interpreter (resolved from the server:app process) ===")
    py_path, pid, how = resolve_venv_python()
    if not py_path:
        print("VENV-PYTHON-NOT-FOUND: %s" % how)
        print("fetch checks STOPPED -- no venv python to run them under")
        skipped.append("venv-python")
        sub_fetch = sub_direct = None
        deps_ok, deps_missing = False, None
    else:
        print("backend python: %s" % py_path)
        print("resolved via: %s" % how)
        if pid:
            print("source process pid: %s" % pid)
        deps_ok, deps_missing = check_deps(py_path)

    # ---- checks 2+3: import + fetch under the venv python ------------
    sub_fetch = None
    if py_path and deps_ok:
        if left() < 30:
            print("=== 2+3. import + backend fetch: SKIPPED -- deadline ===")
            skipped.append("backend-fetch-sub")
        else:
            print("=== 2+3. import server.py + live fetch (venv python) ===")
            sub_fetch = run_sub(py_path, SUB_FETCH, 25,
                                "backend import+fetch subprocess")
            if sub_fetch is None:
                skipped.append("backend-fetch-sub")
    elif py_path and not deps_ok:
        print("=== 2+3. import + backend fetch: SKIPPED -- deps missing "
              "(%s) ===" % (deps_missing or "unknown module"))

    # ---- check 4: httpx vs urllib under the same venv python ---------
    sub_direct = None
    if py_path and deps_ok:
        if left() < 22:
            print("=== 4. httpx vs urllib: SKIPPED -- deadline near ===")
            skipped.append("httpx-vs-urllib")
        else:
            print("=== 4. httpx vs urllib direct to .fr (venv python) ===")
            sub_direct = run_sub(
                py_path, SUB_DIRECT, 20, "httpx-vs-urllib subprocess",
                extra_env={"OSM_BF2_QUERY": centers_query(*CELL)})
            if sub_direct is None:
                skipped.append("httpx-vs-urllib")

    endpoints = check_endpoints()

    # ---------- verdict ----------
    print("=== VERDICT ===")
    his_count = endpoints.get("his spot", (None, None))[0]
    dt_count = endpoints.get("downtown", (None, None))[0]
    fetch = (sub_fetch or {}).get("fetch_result", {}) if sub_fetch else {}
    fetch_count = fetch.get("count")
    httpx_d = (sub_direct or {}).get("httpx_direct", {}) if sub_direct else {}
    urllib_d = (sub_direct or {}).get("urllib_direct", {}) if sub_direct else {}
    per_his = (sub_fetch or {}).get("per_mirror_his", {}) if sub_fetch else {}
    per_dt = (sub_fetch or {}).get("per_mirror_downtown", {}) \
        if sub_fetch else {}
    import_err = (sub_fetch or {}).get("import_error") if sub_fetch else None

    def per_summary(per):
        return [(r.get("url"), r.get("status"), r.get("elements"),
                 r.get("error")) for r in per.get("results", [])]

    verdict, detail = None, ""
    if not py_path:
        verdict, detail = "(e)", \
            "VENV-PYTHON-NOT-FOUND: %s -- the fetch checks could not run" % how
    elif not deps_ok:
        verdict, detail = "(e)", \
            ("the venv python %s is missing module '%s' (deps check "
             "failed) -- the backend fetch could not be tested; check "
             "which python the backend really runs under"
             % (py_path, deps_missing or "?"))
    elif sub_fetch is None:
        verdict, detail = "(e)", \
            "the import+fetch subprocess could not run under %s -- no " \
            "backend fetch evidence" % py_path
    elif import_err:
        verdict, detail = "(e)", \
            ("the venv python %s could not import server.py (%s) -- the "
             "backend fetch could not be tested"
             % (py_path, import_err.get("error")))
    elif his_count is not None and his_count > 0:
        verdict, detail = "(d)", \
            ("the endpoint returns %d center(s) at his spot -- the fix is "
             "live and working" % his_count)
    elif fetch_count is not None and fetch_count > 0 and his_count == 0:
        verdict, detail = "(a)", \
            ("the backend's own fetch returns %d center(s) (%s) via %s, "
             "but the endpoint still returns %s at his spot -- mapping/DB "
             "mismatch: the fetch works, the endpoint does not serve it"
             % (fetch_count, fetch.get("names"), py_path, his_count))
    elif (httpx_d.get("status") is None and httpx_d.get("error")
          and urllib_d.get("elements")):
        verdict, detail = "(b)", \
            ("the venv python's httpx FAILS on .fr (%s) while urllib "
             "returns %d elements (%s) -- httpx/proxy problem in the "
             "backend env; proxies=%s; backend python=%s"
             % (httpx_d.get("error"), urllib_d.get("elements"),
                urllib_d.get("names"),
                (sub_direct or {}).get("proxies"), py_path))
    elif per_his and all(r.get("elements", 0) == 0
                         for r in per_his.get("results", [])) \
            and not urllib_d.get("elements"):
        verdict, detail = "(c)", \
            ("the venv python cannot reach ANY mirror: per-mirror his "
             "cell=%s; downtown=%s; httpx direct=%s; urllib direct=%s; "
             "proxies=%s; backend python=%s -- backend-container egress "
             "problem" % (per_summary(per_his), per_summary(per_dt),
                          (httpx_d.get("status"), httpx_d.get("elements"),
                           httpx_d.get("error")),
                          (urllib_d.get("status"), urllib_d.get("elements"),
                           urllib_d.get("error")),
                          (sub_direct or {}).get("proxies"), py_path))
    else:
        verdict, detail = "(e)", \
            ("undetermined: fetch=%s endpoint his=%s downtown=%s "
             "per-mirror his=%s httpx=%s urllib=%s"
             % (fetch, his_count, dt_count, per_summary(per_his),
                (httpx_d.get("status"), httpx_d.get("elements")),
                (urllib_d.get("status"), urllib_d.get("elements"))))
    print("VERDICT: %s %s" % (verdict, detail))
    if skipped:
        print("skipped checks: %s" % ", ".join(skipped))
    print("endpoint record: his spot=%s downtown=%s ; backend fetch=%s ; "
          "interpreter=%s" % (his_count, dt_count, fetch_count, py_path))
    partial = verdict in ("(e)",)
    print((PARTIAL if partial else MARKER) + " verdict=%s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
