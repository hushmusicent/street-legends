#!/usr/bin/env python3
"""Street Legends diag: test the RUNNING BACKEND itself, not the terminal.

Why this probe exists: the mirror-fr patch RAN CLEAN on /app at 04:01 EST
2026-11-06 (OSM_MIRROR_FR_OK: openstreetmap.fr first, OSM_CACHE_EPOCH = 2,
all four endpoints' freshness/stamp/empty-guard edits OK) and the user
Published, but the live endpoints still return [] -- and a FRESH area
(downtown Toledo, 41.6520,-83.5370, grid cells never cached) burns the
full ~10s OSM_TOTAL_BUDGET. Timings so far:

  - his spot (41.66308,-83.61536) -> [] in ~2.2s (twice): consistent with
    EITHER old code serving cached-empty cells OR new code re-fetching
    and failing fast.
  - downtown Toledo (fresh cells) -> [] in ~10.5s (twice): NOT consistent
    with working new code (.fr first should answer in ~1s with data) and
    NOT consistent with old code IF the loop stopped at osm.ch's fast
    empty 200. It IS consistent with (a) old code still running AND the
    loop burning the budget on kumi timeouts, or (b) new code live but
    the BACKEND's own network calls reaching no mirror at all.
  - The terminal's urllib reaches .fr fine (200 in 0.9s, 2 centers) --
    but the terminal and the backend process may have DIFFERENT egress.
    Every earlier mirror probe ran in the terminal; NONE tested the
    backend process's own httpx path. This probe does that.

Live code facts (from the patch files): mirrors should now be
[.fr, osm.ch, .de, kumi]; OSM_CACHE_EPOCH = 2; per-cell timeout 8s,
total budget 10s, parallel gather (_osm_gather_cells); fetches use
httpx.AsyncClient; the four handlers each have their own freshness
gate + stamp + empty guard (no shared cache path). The mirror loop
breaks on the FIRST 200 response, even if its payload has 0 elements.

This probe runs in the Emergent terminal at /app and checks, in order:
  1. PATCH IN FILE: 'openstreetmap.fr' + 'OSM_CACHE_EPOCH' in
     backend/server.py, mirrors list in order as it stands on disk.
  2. BACKEND PROCESS: the running backend (uvicorn / python server.py)
     via /proc scan -- PID, start time, backend python path -- vs the
     patch run time (04:01 EST 2026-11-06) and the mtime of
     backend/server.py. Process started BEFORE the patch = old code
     still running, Publish did not restart it.
  3. BACKEND'S OWN PYTHON: the interpreter the backend actually runs
     under (from the process exe/cmdline, else venv/supervisor search),
     used to import server.py in a guarded 25s subprocess and call the
     live centers fetch for his cell -- mirrors seen, per-mirror
     outcome, final list returned.
  4. HTTPX vs URLLIB from the backend env: one httpx POST and one
     urllib POST to .fr with the centers query (10s each), plus the
     backend python's proxy env vars. This isolates "httpx broken in
     the backend env" from "the backend container reaches nothing".
  5. ENDPOINT SANITY (read-only GETs only): centers nearby at his spot
     + downtown, counts + seconds.

Verdict, exactly one of:
  (a) patch NOT in server.py on disk;
  (b) patch in file but backend process started BEFORE the patch --
      old code running, needs a restart / re-Publish;
  (c) new code running but the backend's own calls cannot reach .fr
      (httpx/urllib outcomes + proxy vars given);
  (d) backend's calls DO reach .fr and return centers, but the
      endpoint still returns [] (fetch result vs endpoint result --
      mapping/DB mismatch);
  (ok) the endpoint returns centers -- the fix is live and working;
  undetermined -- not enough evidence (see which checks skipped).

Read-only: never edits a file, never restarts anything, never kills
any process (the only kill is the probe's own diagnostic subprocess
if it exceeds its 25s cap). Only network calls are the Overpass POSTs
from the backend python, and read-only endpoint GETs. Global deadline
~85s; late steps are skipped with a note instead of hanging.

Run from /app:  python3 minigame-diag/diag-osm-backend-runtime.py
Test hooks (env): OSM_RT_ROOT (default /app, or argv[1]),
OSM_RT_PATCH_TIME_ISO (default 2026-11-06T04:01:00-05:00),
OSM_RT_BACKEND_PY (force the backend python path),
OSM_RT_PROC_JSON (harness: fake /proc results),
OSM_RT_PROC_NOT_VISIBLE (harness: simulate no process),
OSM_RT_MOCK_FETCH_JSON (harness: canned backend-subprocess results),
OSM_RT_ENDPOINT_JSON (harness: canned endpoint GET results),
OSM_RT_ENDPOINT (default https://gta-quest-map.emergent.host).
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
    os.environ.get("OSM_RT_ROOT", "/app"))
PATCH_TIME_ISO = os.environ.get("OSM_RT_PATCH_TIME_ISO",
                                "2026-11-06T04:01:00-05:00")
ENDPOINT_BASE = os.environ.get(
    "OSM_RT_ENDPOINT", "https://gta-quest-map.emergent.host").rstrip("/")
FR_URL = "https://overpass.openstreetmap.fr/api/interpreter"
LAT, LNG = 41.66308, -83.61536          # his spot (UT)
DT_LAT, DT_LNG = 41.6520, -83.5370      # downtown Toledo (fresh cells)
CELL = (41.65, -83.65, 41.70, -83.60)   # his cell bbox s,w,n,e
MARKER = "OSM_BACKEND_RUNTIME_DIAG_OK"
PARTIAL = "OSM_BACKEND_RUNTIME_DIAG_PARTIAL"
START = time.time()
DEADLINE = START + 85.0

try:
    PATCH_EPOCH = datetime.fromisoformat(PATCH_TIME_ISO).timestamp()
except Exception:
    PATCH_EPOCH = datetime(2026, 11, 6, 4, 1,
                           tzinfo=timezone.utc).timestamp()
    print("WARNING: bad OSM_RT_PATCH_TIME_ISO %r, using 2026-11-06 04:01 EST"
          % PATCH_TIME_ISO)

skipped = []


def left():
    return DEADLINE - time.time()


def read(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return p.read_text(errors="ignore")
    except Exception as e:  # noqa: BLE001
        print("WARNING: could not read %s (%s)" % (rel, e))
        return None


def fmt_ts(epoch):
    try:
        return datetime.fromtimestamp(epoch).astimezone().strftime(
            "%Y-%m-%d %H:%M:%S %Z")
    except Exception:
        return "epoch %s" % epoch


# ---------------------------------------------------------------- check 1
def check_patch_in_file():
    print("=== 1. patch in file? (backend/server.py on disk) ===")
    srv = read("backend/server.py")
    if srv is None:
        print("backend/server.py MISSING on disk")
        return None, None, None
    has_fr = "openstreetmap.fr" in srv
    m_epoch = re.search(r"OSM_CACHE_EPOCH\s*=\s*(\d+)", srv)
    epoch = int(m_epoch.group(1)) if m_epoch else None
    m = re.search(r"OSM_OVERPASS_MIRRORS\s*=\s*\[(.*?)\]", srv, re.S)
    mirrors = []
    if m:
        mirrors = re.findall(r'"([^"]+)"', m.group(1)) or \
            re.findall(r"'([^']+)'", m.group(1))
    print("openstreetmap.fr in server.py: %s" % ("YES" if has_fr else "NO"))
    print("OSM_CACHE_EPOCH in server.py: %s" % (epoch if epoch is not None else "NO"))
    print("OSM_OVERPASS_MIRRORS on disk (in order): %s" % (mirrors or "NOT FOUND"))
    try:
        mt = (ROOT / "backend/server.py").stat().st_mtime
        print("backend/server.py mtime: %s (patch ran %s)"
              % (fmt_ts(mt), fmt_ts(PATCH_EPOCH)))
    except Exception as e:  # noqa: BLE001
        print("backend/server.py mtime: unreadable (%s)" % e)
    in_file = bool(has_fr and epoch is not None and mirrors
                   and mirrors[0] == FR_URL)
    print("patch in file (fr first + epoch present): %s" % ("YES" if in_file else "NO"))
    return in_file, mirrors, epoch


# ---------------------------------------------------------------- check 2
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


def find_backend_procs():
    """Scan /proc for the backend worker. Returns list of proc dicts."""
    mock = os.environ.get("OSM_RT_PROC_JSON")
    if mock:
        try:
            return json.load(open(mock))
        except Exception as e:  # noqa: BLE001
            print("WARNING: bad OSM_RT_PROC_JSON (%s)" % e)
            return []
    if os.environ.get("OSM_RT_PROC_NOT_VISIBLE"):
        return []
    procs = []
    try:
        pids = [int(n) for n in os.listdir("/proc") if n.isdigit()]
    except Exception:
        pids = []
    for pid in pids:
        info = _proc_info(pid)
        cmd = info["cmd"]
        if not cmd:
            continue
        if "server.py" in cmd or ("uvicorn" in cmd and
                                  ("server" in cmd or "backend" in cmd)):
            procs.append(info)
    if procs:
        return procs
    # Fallback: ps, in case /proc is restricted.
    try:
        out = subprocess.run(["ps", "-eo", "pid,etimes,args"],
                             capture_output=True, text=True, timeout=10).stdout
        for line in out.splitlines()[1:]:
            parts = line.strip().split(None, 2)
            if len(parts) < 3:
                continue
            pid, etimes, cmd = int(parts[0]), int(parts[1]), parts[2]
            if "server.py" in cmd or ("uvicorn" in cmd and
                                      ("server" in cmd or "backend" in cmd)):
                procs.append({"pid": pid, "cmd": cmd, "exe": "",
                              "start": time.time() - etimes})
    except Exception as e:  # noqa: BLE001
        print("WARNING: ps fallback failed (%s)" % e)
    return procs


def check_backend_process():
    print("=== 2. backend process (is the running code old or new?) ===")
    print("patch ran at: %s" % fmt_ts(PATCH_EPOCH))
    procs = find_backend_procs()
    if not procs:
        print("backend process: PROCESS-NOT-VISIBLE from this terminal "
              "(no uvicorn / server.py process found via /proc or ps)")
        skipped.append("process")
        return None
    starts = [p["start"] for p in procs if p.get("start")]
    oldest = min(starts) if starts else None
    for p in procs:
        print("backend process: pid=%s exe=%s start=%s cmd=%s"
              % (p["pid"], p.get("exe") or "?",
                 fmt_ts(p["start"]) if p.get("start") else "?",
                 (p.get("cmd") or "")[:160]))
    if oldest is None:
        print("backend process: start time unreadable -- cannot compare "
              "with patch time")
        skipped.append("process-start")
        return {"procs": procs, "oldest_start": None, "old_code": None}
    old_code = oldest < PATCH_EPOCH
    print("oldest backend process started: %s -- %s patch time "
          "(%s = old code still running)"
          % (fmt_ts(oldest), "BEFORE" if old_code else "AFTER",
             "OLD CODE" if old_code else "NEW CODE"))
    return {"procs": procs, "oldest_start": oldest, "old_code": old_code}


# ------------------------------------------------- backend-python discovery
def find_backend_python(proc_info):
    """The interpreter the backend actually runs under. Returns (path,
    how-found) or (None, reason)."""
    forced = os.environ.get("OSM_RT_BACKEND_PY")
    if forced:
        return forced, "env OSM_RT_BACKEND_PY"
    if proc_info:
        for p in proc_info.get("procs", []):
            exe = p.get("exe") or ""
            if exe and "python" in exe:
                return exe, "process exe (pid %s)" % p["pid"]
            cmd = p.get("cmd") or ""
            m = re.match(r"(\S*python\S*)", cmd)
            if m:
                return m.group(1), "process cmdline argv[0] (pid %s)" % p["pid"]
    for rel in (".venv/bin/python", "venv/bin/python",
                "backend/.venv/bin/python", "backend/venv/bin/python"):
        cand = ROOT / rel
        if cand.exists():
            return str(cand), "venv found at %s" % rel
    for rel in ("supervisord.conf", "backend/supervisord.conf",
                "/etc/supervisor/conf.d/street-legends.conf",
                "/etc/supervisor/conf.d/backend.conf"):
        p = Path(rel) if rel.startswith("/") else ROOT / rel
        if p.exists():
            try:
                txt = p.read_text(errors="ignore")
            except Exception:
                continue
            m = re.search(r"command\s*=\s*(\S*python\S*)", txt)
            if m:
                return m.group(1), "supervisor config %s" % rel
    return None, ("no backend python found (no process exe, no venv at "
                  ".venv/venv/backend/.venv/backend/venv, no supervisor "
                  "command)")


BACKEND_SUB = r'''
import asyncio, json, os, sys, time, urllib.request, urllib.parse, urllib.error
MOCK = os.environ.get("OSM_RT_MOCK_FETCH_JSON")
FR = "https://overpass.openstreetmap.fr/api/interpreter"
S, W, N, E = 41.65, -83.65, 41.70, -83.60
def emit(kind, **kw):
    d = {"kind": kind}; d.update(kw)
    print("SUBJSON " + json.dumps(d))
def names_of(els):
    return [e.get("tags", {}).get("name") for e in (els or [])[:5]]
if MOCK:
    data = json.load(open(MOCK))
    for line in data.get("lines", []):
        print(line)
    for k, v in data.get("emit", {}).items():
        emit(k, **v)
    sys.exit(0)
sys.path.insert(0, os.environ.get("OSM_RT_BACKEND_DIR", "backend"))
try:
    import server as srv
except Exception as e:
    print("import server.py FAILED: %s: %s" % (type(e).__name__, e))
    emit("import_error", error="%s: %s" % (type(e).__name__, e))
    sys.exit(0)
mirrors = list(getattr(srv, "OSM_OVERPASS_MIRRORS", []) or [])
print("imported server.py mirrors: %s" % mirrors)
emit("mirrors", mirrors=mirrors)
try:
    query = srv._activity_center_overpass_query(S, W, N, E)
except Exception as e:
    print("query builder FAILED: %s: %s" % (type(e).__name__, e))
    emit("import_error", error="query builder: %s: %s" % (type(e).__name__, e))
    sys.exit(0)
per = []
try:
    import httpx
    for url in mirrors:
        t0 = time.time()
        try:
            async def _one(u):
                async with httpx.AsyncClient(timeout=8.0) as c:
                    return await c.post(u, data={"data": query})
            r = asyncio.run(_one(url))
            els = r.json().get("elements", []) if r.status_code == 200 else []
            print("mirror %s: %s in %.1fs elements=%d names=%s" % (url, r.status_code, time.time() - t0, len(els), names_of(els)))
            per.append({"url": url, "status": r.status_code, "seconds": round(time.time() - t0, 1), "elements": len(els), "names": names_of(els)})
        except Exception as e:
            print("mirror %s: FAILED in %.1fs %s: %s" % (url, time.time() - t0, type(e).__name__, e))
            per.append({"url": url, "status": None, "seconds": round(time.time() - t0, 1), "elements": 0, "error": "%s: %s" % (type(e).__name__, e)})
    emit("per_mirror", results=per)
except ImportError:
    print("httpx NOT importable in backend python")
    emit("per_mirror", results=[], error="httpx missing")
try:
    res = asyncio.run(asyncio.wait_for(srv._activity_center_fetch_cell("833_-1673", S, W, N, E), timeout=20))
    names = [c.get("name") for c in (res or [])]
    print("fetch _activity_center_fetch_cell -> %s center(s): %s" % (len(res or []), names))
    emit("fetch_result", count=len(res or []), names=names)
except Exception as e:
    print("fetch FAILED: %s: %s" % (type(e).__name__, e))
    emit("fetch_result", count=None, error="%s: %s" % (type(e).__name__, e))
t0 = time.time()
try:
    import httpx
    with httpx.Client(timeout=10.0) as c:
        r = c.post(FR, data={"data": query})
    els = r.json().get("elements", []) if r.status_code == 200 else []
    print("httpx direct to .fr: %s in %.1fs elements=%d names=%s" % (r.status_code, time.time() - t0, len(els), names_of(els)))
    emit("httpx_direct", status=r.status_code, seconds=round(time.time() - t0, 1), elements=len(els), names=names_of(els))
except Exception as e:
    print("httpx direct to .fr FAILED in %.1fs %s: %s" % (time.time() - t0, type(e).__name__, e))
    emit("httpx_direct", status=None, seconds=round(time.time() - t0, 1), elements=0, error="%s: %s" % (type(e).__name__, e))
t0 = time.time()
try:
    body = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(FR, data=body, headers={"User-Agent": "StreetLegends-diag/1.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        raw = r.read()
    els = json.loads(raw.decode("utf-8", "ignore")).get("elements", [])
    print("urllib direct to .fr: %s in %.1fs elements=%d names=%s" % (r.status, time.time() - t0, len(els), names_of(els)))
    emit("urllib_direct", status=r.status, seconds=round(time.time() - t0, 1), elements=len(els), names=names_of(els))
except Exception as e:
    print("urllib direct to .fr FAILED in %.1fs %s: %s" % (time.time() - t0, type(e).__name__, e))
    emit("urllib_direct", status=None, seconds=round(time.time() - t0, 1), elements=0, error="%s: %s" % (type(e).__name__, e))
proxies = {k: os.environ[k] for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "NO_PROXY", "no_proxy") if os.environ.get(k)}
print("proxy env in backend python: %s" % (proxies if proxies else "none set"))
emit("proxies", proxies=proxies)
'''


def run_backend_sub(py_path):
    """Run BACKEND_SUB under the backend python (25s cap). Returns the
    parsed SUBJSON dict, or None (with a printed reason). Never raises."""
    import tempfile
    sub = {}
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                         dir="/tmp") as f:
            f.write(BACKEND_SUB)
            tmp = f.name
        env = dict(os.environ)
        env["OSM_RT_BACKEND_DIR"] = str(ROOT / "backend")
        r = subprocess.run([py_path, tmp], capture_output=True, text=True,
                           timeout=25, env=env)
        print("--- backend python subprocess output (%s) ---" % py_path)
        print(r.stdout.rstrip() or "(no stdout)")
        if r.stderr.strip():
            print("--- subprocess stderr (last 5 lines) ---")
            print("\n".join(r.stderr.strip().splitlines()[-5:]))
        for line in r.stdout.splitlines():
            if line.startswith("SUBJSON "):
                try:
                    d = json.loads(line[len("SUBJSON "):])
                    sub[d.get("kind")] = d
                except Exception:
                    pass
        os.unlink(tmp)
        return sub
    except subprocess.TimeoutExpired:
        print("backend python subprocess: TIMEOUT after 25s (killed by probe)")
        return None
    except Exception as e:  # noqa: BLE001
        print("backend python subprocess: FAILED to run (%s: %s)"
              % (type(e).__name__, e))
        return None


def check_backend_runtime(proc_info):
    print("=== 3+4. backend's own python: import + fetch + httpx vs urllib ===")
    if left() < 30:
        print("SKIPPED -- global deadline near (backend subprocess needs 25s)")
        skipped.append("backend-sub")
        return None, None
    py_path, how = find_backend_python(proc_info)
    print("backend python: %s (found via: %s)"
          % (py_path if py_path else "NOT FOUND", how))
    if not py_path:
        skipped.append("backend-python")
        return None, None
    sub = run_backend_sub(py_path)
    if sub is None:
        skipped.append("backend-sub")
        return None, py_path
    return sub, py_path


# ---------------------------------------------------------------- check 5
def get_centers(lat, lng):
    mock = os.environ.get("OSM_RT_ENDPOINT_JSON")
    if mock:
        try:
            data = json.load(open(mock))
            key = "his" if (lat, lng) == (LAT, LNG) else "downtown"
            d = data.get(key, {})
            return d.get("count"), d.get("seconds"), "mock"
        except Exception as e:  # noqa: BLE001
            return None, None, "bad OSM_RT_ENDPOINT_JSON (%s)" % e
    url = ("%s/api/activity-centers/nearby?latitude=%s&longitude=%s"
           % (ENDPOINT_BASE, lat, lng))
    t0 = time.time()
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "StreetLegends-diag/1.0",
            "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=15) as r:
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
        if left() < 18:
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
    print("=== OSM backend-runtime diag (test the RUNNING backend, not the terminal) ===")
    print("reference: his spot lat=%s lng=%s ; downtown lat=%s lng=%s ; "
          "patch ran %s" % (LAT, LNG, DT_LAT, DT_LNG, fmt_ts(PATCH_EPOCH)))

    in_file, mirrors, epoch = check_patch_in_file()
    proc_info = check_backend_process()
    sub, py_path = check_backend_runtime(proc_info)
    endpoints = check_endpoints()

    # ---------- verdict ----------
    print("=== VERDICT ===")
    his_count = endpoints.get("his spot", (None, None))[0]
    dt_count = endpoints.get("downtown", (None, None))[0]
    fetch = (sub or {}).get("fetch_result", {}) if sub else {}
    fetch_count = fetch.get("count")
    httpx_d = (sub or {}).get("httpx_direct", {}) if sub else {}
    urllib_d = (sub or {}).get("urllib_direct", {}) if sub else {}
    per = (sub or {}).get("per_mirror", {}) if sub else {}
    verdict, detail = None, ""
    if in_file is None:
        verdict, detail = "undetermined", \
            "backend/server.py is missing on disk -- rerun with the code present"
    elif not in_file:
        verdict, detail = "(a)", \
            ("patch NOT in backend/server.py on disk (fr present=%s, epoch=%s, "
             "mirrors=%s) -- the deployed file does not have the fix; "
             "re-run the mirror-fr patch" % (
                 "openstreetmap.fr" in (read("backend/server.py") or ""),
                 epoch, mirrors))
    elif proc_info and proc_info.get("old_code"):
        verdict, detail = "(b)", \
            ("patch IS in server.py, but the oldest backend process started "
             "%s, BEFORE the patch ran at %s -- old code is still running; "
             "the Publish did not restart the backend, it needs a restart "
             "or re-Publish" % (fmt_ts(proc_info["oldest_start"]),
                                fmt_ts(PATCH_EPOCH)))
    elif his_count is not None and his_count > 0:
        verdict, detail = "(ok)", \
            ("the endpoint returns %d center(s) at his spot -- the fix is "
             "live and working" % his_count)
    elif sub is None:
        verdict, detail = "undetermined", \
            ("patch is in the file and the process looks new, but the "
             "backend-python subprocess could not run -- rerun with the "
             "backend python reachable")
    elif sub is not None and "import_error" in sub and fetch_count is None:
        verdict, detail = "undetermined", \
            ("patch is in the file, but the backend python could not import "
             "server.py (%s) -- the backend fetch could not be tested; "
             "check which python the backend really runs under"
             % (sub.get("import_error") or {}).get("error"))
    elif fetch_count is not None and fetch_count > 0 and his_count == 0:
        verdict, detail = "(d)", \
            ("the backend's own fetch returns %d center(s) (%s) via %s, but "
             "the endpoint still returns %s at his spot -- mapping/DB "
             "mismatch: the fetch works, the endpoint does not serve it"
             % (fetch_count, fetch.get("names"), py_path, his_count))
    else:
        verdict, detail = "(c)", \
            ("new code running, but the backend's own calls cannot reach "
             ".fr: httpx direct status=%s elements=%s err=%s; urllib direct "
             "status=%s elements=%s err=%s; per-mirror httpx=%s; fetch "
             "result=%s; proxies=%s; backend python=%s"
             % (httpx_d.get("status"), httpx_d.get("elements"),
                httpx_d.get("error"), urllib_d.get("status"),
                urllib_d.get("elements"), urllib_d.get("error"),
                [(r.get("url"), r.get("status"), r.get("elements"),
                  r.get("error")) for r in per.get("results", [])],
                fetch, (sub or {}).get("proxies"), py_path))
    print("VERDICT: %s %s" % (verdict, detail))
    if skipped:
        print("skipped checks: %s" % ", ".join(skipped))
    print("endpoint record: his spot=%s downtown=%s ; backend fetch=%s"
          % (his_count, dt_count, fetch_count))
    partial = verdict in ("undetermined",)
    print((PARTIAL if partial else MARKER) + " verdict=%s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
