#!/usr/bin/env python3
"""Street Legends white-screen diag (READ-ONLY).

The app (Expo Go) loads, then sticks on a white "Street Legends" screen
and never reaches the map. It worked earlier and survives a force-close
+ reopen, so the prime suspect is a bad JS/TSX bundle from a recent
frontend patch run (a syntax error in any imported module kills the
whole bundle at startup) — but which patches actually ran is unknown,
so this script establishes that first, then syntax-checks the bundle
files. It writes nothing. Run: python3 minigame-diag/diag-white-screen.py
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")

FILES = [
    "frontend/app/(tabs)/index.tsx",
    "frontend/app/(tabs)/character.tsx",
    "frontend/components/GameMap.tsx",
    "frontend/services/api.ts",
    "frontend/hooks/useMapQueries.ts",
]

MARKERS = [
    ("grass-frontend", "frontend/app/(tabs)/character.tsx", "GRASS_ITEM_FRONTEND_OK"),
    ("grass-row", "frontend/app/(tabs)/character.tsx", "item.id === 'grass'"),
    ("pills-frontend", "frontend/app/(tabs)/character.tsx", "PILLS_ITEM_FRONTEND_OK"),
    ("pills-row", "frontend/app/(tabs)/character.tsx", "item.id === 'pills'"),
    ("rock-frontend-v1", "frontend/app/(tabs)/character.tsx", "ROCK_CANDY_ITEM_FRONTEND_OK"),
    ("rock-row-v1", "frontend/app/(tabs)/character.tsx", "ROCK_CANDY_ITEM_FRONTEND_ROW"),
    ("rock-frontend-v2", "frontend/app/(tabs)/character.tsx", "ROCK_CANDY_ITEM_FRONTEND_ROW_V2"),
    ("flake-frontend", "frontend/app/(tabs)/character.tsx", "FLAKE_ITEM_FRONTEND_OK"),
    ("flake-row", "frontend/app/(tabs)/character.tsx", "item.id === 'flake'"),
    ("activity-v1-frontend", "frontend/app/(tabs)/index.tsx", "ACTIVITY_CENTER_FRONTEND_OK"),
    ("activity-v2-frontend", "frontend/app/(tabs)/index.tsx", "ACTIVITY_CENTER_REAL_FRONTEND_OK"),
    ("activity-marker", "frontend/components/GameMap.tsx", "activityCenter"),
    ("grass-api", "frontend/services/api.ts", "useGrassItem"),
    ("pills-api", "frontend/services/api.ts", "usePillsItem"),
    ("rock-api", "frontend/services/api.ts", "useRockCandyItem"),
    ("flake-api", "frontend/services/api.ts", "useFlakeItem"),
    ("activity-api", "frontend/services/api.ts", "getActivityCentersNearby"),
]

def run(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, cwd=str(ROOT), capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)[:4000]
    except subprocess.TimeoutExpired:
        return None, "TIMEOUT after %ss" % timeout
    except Exception as e:  # noqa: BLE001 - diag must never crash
        return None, "ERROR: %s" % e

def main():
    print("=== files (size + mtime, newest first) ===")
    rows = []
    for f in FILES:
        p = ROOT / f
        if p.exists():
            st = p.stat()
            rows.append((st.st_mtime, f, st.st_size))
        else:
            print("MISSING: %s" % f)
    for _, f, size in sorted(rows, reverse=True):
        import datetime
        mt = datetime.datetime.fromtimestamp(_).strftime("%Y-%m-%d %H:%M:%S")
        print("%s  %d bytes  %s" % (mt, size, f))
    print("=== patch markers in live files ===")
    for label, f, needle in MARKERS:
        p = ROOT / f
        if not p.exists():
            print("%-24s %s: FILE MISSING" % (label, f))
            continue
        txt = p.read_text(errors="ignore")
        print("%-24s %s: %s (x%d)" % (label, f, "FOUND" if needle in txt else "missing",
                                      txt.count(needle)))
    print("=== eslint on the bundle files (syntax errors kill Expo Go at startup) ===")
    if not (ROOT / "node_modules/.bin/eslint").exists():
        print("SKIPPED: no node_modules/.bin/eslint in this project")
    else:
        rc, out = run("npx eslint frontend/app/\\(tabs\\)/index.tsx frontend/app/\\(tabs\\)/character.tsx frontend/components/GameMap.tsx frontend/services/api.ts frontend/hooks/useMapQueries.ts 2>&1 | head -60", timeout=180)
        print("eslint exit: %s" % rc)
        print(out if out.strip() else "(clean / no output)")
    print("=== tsc --noEmit (first 40 lines) ===")
    if not (ROOT / "node_modules/.bin/tsc").exists():
        print("SKIPPED: no node_modules/.bin/tsc in this project")
    else:
        rc, out = run("npx tsc --noEmit --pretty false 2>&1 | head -40", timeout=240)
        print("tsc exit: %s" % rc)
        print(out if out.strip() else "(clean / no output)")
    print("=== expo/metro processes ===")
    rc, out = run("ps aux | grep -i -E 'expo|metro' | grep -v grep | head -10")
    print(out if out.strip() else "(none visible)")
    print("WHITE_SCREEN_DIAG_OK")

if __name__ == "__main__":
    main()
