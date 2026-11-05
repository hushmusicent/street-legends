#!/usr/bin/env python3
"""Street Legends Activity Centers v2 diag (READ-ONLY).

The user asked to "check the activity center codes": are the real-location
(OpenStreetMap) Activity Centers actually in place in the live /app tree?
This script prints only, writes nothing. Run: python3 minigame-diag/diag-activity-center.py

What it checks, per live file:
- backend/server.py: nearby + 4 presence routes, Overpass URL/query,
  24h grid cache, fictional-center cleanup, v1 spawn endpoint absent.
- frontend/services/api.ts: the six center functions (nearby + 4 presence
  + getFriendsList the interior effect needs).
- frontend/components/GameMap.tsx: activityCenter marker branch (the
  primary render path), color '#7b1fa2', literal game-controller icon,
  isLocationMarker sizing.
- frontend/app/(tabs)/index.tsx: ImageBackground imported (checked INSIDE
  the react-native import, NOT file-wide — the interior modal USES the
  name, so a file-wide check would lie), each of the six center names
  imported INSIDE the services/api import, state/memo/marker/press/
  popup/interior/presence-effect, hall-picture const, type union.
- frontend/hooks/useMapQueries.ts: center fetch wired, AND the
  Promise.allSettled index of the getActivityCentersNearby call matches the
  results[N] index the return reads (a positional mismatch would silently
  serve another entity's data as centers).
- Whether the white-screen repair's additions are present (imports +
  color/icon), summarized REPAIR_PRESENT / REPAIR_MISSING per item.

Verdict: ACTIVITY_CENTER_DIAG_OK + a count of failed checks + the exact
list of what failed. A failed check means that piece is missing in the
live file — it does NOT by itself prove what the user sees on device.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
MARKER = "ACTIVITY_CENTER_DIAG_OK"

FILES = [
    "backend/server.py",
    "frontend/services/api.ts",
    "frontend/components/GameMap.tsx",
    "frontend/app/(tabs)/index.tsx",
    "frontend/hooks/useMapQueries.ts",
]

CENTER_API_FNS = [
    "getActivityCentersNearby",
    "centerEnterPresence",
    "centerLeavePresence",
    "centerHeartbeatPresence",
    "getCenterPresence",
    "getFriendsList",
]


def read(rel):
    p = ROOT / rel
    if not p.exists():
        return None
    try:
        return p.read_text(errors="ignore")
    except Exception as e:  # noqa: BLE001 - diag must never crash
        print("WARNING: could not read %s (%s)" % (rel, e))
        return None


def count(src, needle):
    return src.count(needle) if src is not None else 0


def import_inner(src, module_substr):
    """Return the text inside the named import from a module containing
    module_substr, or None if no such import statement exists."""
    if src is None:
        return None
    pat = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]*" +
                     re.escape(module_substr) + r"[^'\"]*)['\"]", re.DOTALL)
    m = pat.search(src)
    return m.group(1) if m else None


def main():
    failed = []

    print("=== files (size + mtime, newest first) ===")
    rows = []
    for f in FILES:
        p = ROOT / f
        if p.exists():
            st = p.stat()
            rows.append((st.st_mtime, f, st.st_size))
        else:
            print("%s MISSING" % f)
            rows.append((0, f, 0))
    for _, f, size in sorted(rows, reverse=True):
        p = ROOT / f
        mt = ""
        if p.exists():
            import datetime
            mt = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        print("%-40s %10d bytes  %s" % (f, size, mt))

    # ---------- backend/server.py ----------
    print("=== backend/server.py (Activity Centers v2) ===")
    srv = read("backend/server.py")
    if srv is None:
        print("backend/server.py MISSING - all backend checks failed")
        failed += ["backend-file"]
    else:
        backend_checks = [
            ("nearby-route", '@api_router.get("/activity-centers/nearby")', True),
            ("enter-route", '@api_router.post("/activity-centers/{center_id}/enter")', True),
            ("leave-route", '@api_router.post("/activity-centers/{center_id}/leave")', True),
            ("heartbeat-route", '@api_router.post("/activity-centers/{center_id}/heartbeat")', True),
            ("presence-route", '@api_router.get("/activity-centers/{center_id}/presence")', True),
            ("overpass-url", "https://overpass-api.de/api/interpreter", True),
            ("overpass-university", 'nwr["amenity"="university"]', True),
            ("overpass-college", 'nwr["amenity"="college"]', True),
            ("overpass-out-center", "out center;", True),
            ("cache-24h", "ACTIVITY_CENTER_CACHE_SECONDS = 86400", True),
            ("cache-collection", "activity_center_cache", True),
            ("fictional-cleanup", '"$regex": "^activity_center_"', True),
            ("osm-id", '"osm_%s_%s"', True),
            ("v1-spawn-absent", "/activity-centers/spawn", False),
        ]
        for name, needle, want_present in backend_checks:
            n = count(srv, needle)
            if want_present:
                print("%-22s %s (x%d)" % (name, "FOUND" if n else "missing", n))
                if not n:
                    failed.append("backend:" + name)
            else:
                print("%-22s %s (x%d) - should be absent" % (name, "ABSENT - good" if n == 0 else "PRESENT - v1 spawn still there", n))
                if n:
                    failed.append("backend:" + name)
        # Motor awaits: every DB call in the center blocks should be awaited.
        unawaited = len(re.findall(r"(?<!await )__DB__\.", srv)) + len(re.findall(r"(?<!await )db\.activity_", srv))
        print("%-22s %s" % ("db-calls-awaited", "OK (no bare db./__DB__. call found)" if unawaited == 0 else "CHECK: %d DB call(s) not preceded by await" % unawaited))
        if unawaited:
            failed.append("backend:db-calls-awaited")

    # ---------- frontend/services/api.ts ----------
    print("=== frontend/services/api.ts (six center functions) ===")
    api = read("frontend/services/api.ts")
    if api is None:
        print("frontend/services/api.ts MISSING - all api checks failed")
        failed += ["api-file"]
    else:
        for fn in CENTER_API_FNS:
            n = len(re.findall(r"export\s+const\s+" + re.escape(fn) + r"\b", api))
            print("%-28s %s (exports x%d)" % (fn, "FOUND" if n == 1 else ("missing" if n == 0 else "DUPLICATE x%d" % n), n))
            if n != 1:
                failed.append("api:" + fn)
        # v1 spawn client should be gone (v2 replaces it).
        n = count(api, "spawnActivityCenters")
        print("%-28s %s (x%d) - should be absent" % ("v1-spawn-client", "ABSENT - good" if n == 0 else "PRESENT - v1 client still there", n))
        if n:
            failed.append("api:v1-spawn-client")

    # ---------- frontend/components/GameMap.tsx ----------
    print("=== frontend/components/GameMap.tsx (marker) ===")
    gm = read("frontend/components/GameMap.tsx")
    if gm is None:
        print("frontend/components/GameMap.tsx MISSING - all map checks failed")
        failed += ["gamemap-file"]
    else:
        branch = count(gm, "m.type === 'activityCenter'")
        print("%-28s %s (x%d) - primary render path" % ("marker-branch", "FOUND" if branch else "missing", branch))
        if not branch:
            failed.append("gamemap:marker-branch")
        color = count(gm, "activityCenter: '#7b1fa2'")
        print("%-28s %s (x%d)" % ("marker-color-#7b1fa2", "FOUND" if color else "missing", color))
        if not color:
            failed.append("gamemap:marker-color")
        icon = count(gm, "activityCenter: '🎮'")
        print("%-28s %s (x%d) - literal icon" % ("marker-icon", "FOUND" if icon else "missing", icon))
        if not icon:
            failed.append("gamemap:marker-icon")
        size = count(gm, "m.type === 'activityCenter'")  # sizing line shares the same test
        sized = "activityCenter" in (re.search(r"var isLocationMarker = \(([^;]*)\);", gm).group(1) if re.search(r"var isLocationMarker = \(([^;]*)\);", gm) else "")
        print("%-28s %s" % ("isLocationMarker-sizing", "FOUND" if sized else "missing - 48x62 marker may render in a 32x32 box"))
        if not sized:
            failed.append("gamemap:isLocationMarker-sizing")
        _ = size

    # ---------- frontend/app/(tabs)/index.tsx ----------
    print("=== frontend/app/(tabs)/index.tsx (imports checked INSIDE the import) ===")
    idx = read("frontend/app/(tabs)/index.tsx")
    if idx is None:
        print("frontend/app/(tabs)/index.tsx MISSING - all index checks failed")
        failed += ["index-file"]
    else:
        rn = import_inner(idx, "react-native")
        if rn is None:
            print("react-native import: NOT FOUND - cannot check ImageBackground import")
            failed.append("index:rn-import")
        else:
            ok = "ImageBackground" in rn
            print("%-28s %s (inside react-native import)" % ("ImageBackground-import", "FOUND" if ok else "missing - interior background will fail"))
            if not ok:
                failed.append("index:ImageBackground-import")
        sapi = import_inner(idx, "services/api")
        if sapi is None:
            print("services/api import: NOT FOUND - cannot check center api imports")
            failed.append("index:api-import")
        else:
            for fn in CENTER_API_FNS:
                ok = fn in sapi
                print("%-28s %s (inside services/api import)" % (fn + "-import", "FOUND" if ok else "missing"))
                if not ok:
                    failed.append("index:" + fn + "-import")
        index_checks = [
            ("bg-const", "ACTIVITY_CENTER_BG"),
            ("type-union", "'activityCenter'"),
            ("state", "activeCenter"),
            ("occupants-state", "centerOccupants"),
            ("memo", "nearbyActivityCenters"),
            ("marker-spread", "type: 'activityCenter' as const"),
            ("press-branch", "marker.type === 'activityCenter'"),
            ("popup", "Activity Center • Everyone welcome"),
            ("popup-enter", ">ENTER<"),
            ("interior-modal", "ACTIVITY_CENTER interior"),
            ("inside-now", "Inside now:"),
            ("presence-effect", "centerEnterPresence(activeCenter.id"),
            ("presence-poll-15s", "15000"),
            ("presence-heartbeat-30s", "30000"),
            ("presence-leave", "centerLeavePresence(activeCenter.id"),
        ]
        for name, needle in index_checks:
            n = count(idx, needle)
            print("%-28s %s (x%d)" % (name, "FOUND" if n else "missing", n))
            if not n:
                failed.append("index:" + name)

    # ---------- frontend/hooks/useMapQueries.ts ----------
    print("=== frontend/hooks/useMapQueries.ts (center fetch wiring) ===")
    q = read("frontend/hooks/useMapQueries.ts")
    if q is None:
        print("frontend/hooks/useMapQueries.ts MISSING - all queries checks failed")
        failed += ["queries-file"]
    else:
        imp = count(q, "getActivityCentersNearby")
        print("%-28s %s (x%d)" % ("import-getActivityCentersNearby", "FOUND" if imp else "missing", imp))
        if not imp:
            failed.append("queries:import")
        field = count(q, "activityCenters: any[];")
        print("%-28s %s (x%d)" % ("MapEntitiesData-field", "FOUND" if field else "missing", field))
        if not field:
            failed.append("queries:field")
        call = "getActivityCentersNearby(latitude" in q
        print("%-28s %s" % ("fetch-call", "FOUND" if call else "missing"))
        if not call:
            failed.append("queries:fetch-call")
        mret = re.search(r"activityCenters:\s*results\[(\d+)\]", q)
        if not mret:
            print("%-28s missing - centers never returned to the map" % "return-results[N]")
            failed.append("queries:return")
        else:
            ret_idx = int(mret.group(1))
            # Positional check: which index is the call inside Promise.allSettled?
            marr = re.search(r"Promise\.allSettled\(\[(.*?)\]\);", q, re.DOTALL)
            call_idx = None
            if marr:
                calls = [ln.strip() for ln in marr.group(1).split("\n") if ln.strip() and "(" in ln]
                for i, ln in enumerate(calls):
                    if "getActivityCentersNearby" in ln:
                        call_idx = i
                        break
                print("fetch-call index in Promise.allSettled: %s (of %d promises); return reads results[%d]"
                      % (call_idx if call_idx is not None else "NOT FOUND", len(calls), ret_idx))
                if call_idx is None:
                    failed.append("queries:call-index")
                elif call_idx != ret_idx:
                    print("MISMATCH: call is results[%d] but return reads results[%d] - centers would get another entity's data" % (call_idx, ret_idx))
                    failed.append("queries:index-mismatch")
                else:
                    print("index-match: OK (call and return agree on results[%d])" % ret_idx)
            else:
                print("Promise.allSettled array anchor not found - index check skipped")
                failed.append("queries:array-anchor")

    # ---------- white-screen repair presence ----------
    print("=== white-screen repair additions present? ===")
    repair_items = []
    if idx is not None:
        rn = import_inner(idx, "react-native")
        repair_items.append(("rn-import-ImageBackground", rn is not None and "ImageBackground" in rn))
        sapi = import_inner(idx, "services/api")
        all6 = sapi is not None and all(fn in sapi for fn in CENTER_API_FNS)
        repair_items.append(("api-import-six-center-fns", all6))
    else:
        repair_items.append(("rn-import-ImageBackground", False))
        repair_items.append(("api-import-six-center-fns", False))
    if gm is not None:
        repair_items.append(("gamemap-color", "activityCenter: '#7b1fa2'" in gm))
        repair_items.append(("gamemap-icon", "activityCenter: '🎮'" in gm))
    else:
        repair_items.append(("gamemap-color", False))
        repair_items.append(("gamemap-icon", False))
    for name, ok in repair_items:
        print("%-32s %s" % (name, "REPAIR_PRESENT" if ok else "REPAIR_MISSING"))
        if not ok:
            failed.append("repair:" + name)

    # ---------- verdict ----------
    print("=== verdict ===")
    print("%s missing=%d" % (MARKER, len(failed)))
    if failed:
        print("FAILED CHECKS:")
        for f in failed:
            print(" - " + f)
    else:
        print("All Activity Center checks FOUND - code is in place (live behavior still needs a device test).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
