#!/usr/bin/env python3
"""Park markers diag: the user reports the park markers disappeared
from the map right after the basketball interior patch ran
(2026-11-07 ~01:58 EST). Read-only: prints the LIVE parks pipeline
so we can see which piece is gone instead of guessing.

Prints:
  0. which files exist (index.tsx / useMapQueries.ts / GameMap.tsx)
  1. useMapQueries.ts: getParksNearby call sites (with context, so we
     see if it is in the fetch array), the parks results[N] mapping
  2. index.tsx: park marker type, nearbyParks memo, mapMarkers park
     spread, popup park branch, ENTER -> setActivePark, old park
     modal comment vs new interior (PLAYABLE ACTIVITIES /
     BasketballGameModal / basketballOpen)
  3. GameMap.tsx: park type / color / icon branch (markers render
     through GameMap; a missing branch hides them even if data flows)
  4. VERDICT: (a) pipeline intact, (b) list of missing pieces

Run:  python3 minigame-diag/diag-park-markers.py
Works on Python < 3.12: no f-string expression spans lines.
"""
import re
from pathlib import Path

MARKER = "PARK_MARKERS_DIAG_OK"

INDEX_CANDIDATES = [
    "frontend/app/(tabs)/index.tsx",
    "frontend/app/index.tsx",
]
QUERIES_PATH = "frontend/hooks/useMapQueries.ts"
GAMEMAP_PATH = "frontend/components/GameMap.tsx"


def read_file(path):
    try:
        return Path(path).read_text(errors="ignore").splitlines()
    except OSError:
        return None


def find_lines(lines, needle):
    return [(i, l) for i, l in enumerate(lines) if needle in l]


def show_context(lines, idx, before=4, after=4):
    for j in range(max(0, idx - before), min(len(lines), idx + after + 1)):
        mark = ">>>" if j == idx else "   "
        print("  " + mark + " " + str(j + 1) + ": " + lines[j][:170])


def main():
    missing = []
    print("=== 0. files ===")
    index_lines = None
    index_path = None
    for cand in INDEX_CANDIDATES:
        got = read_file(cand)
        if got is not None:
            index_lines = got
            index_path = cand
            break
    print("index.tsx: " + (index_path or "NOT FOUND"))
    if index_lines is not None:
        print("  lines: " + str(len(index_lines)))
    queries_lines = read_file(QUERIES_PATH)
    print("useMapQueries.ts: " + ("found" if queries_lines is not None else "NOT FOUND"))
    if queries_lines is not None:
        print("  lines: " + str(len(queries_lines)))
    gamemap_lines = read_file(GAMEMAP_PATH)
    print("GameMap.tsx: " + ("found" if gamemap_lines is not None else "NOT FOUND"))

    print()
    print("=== 1. useMapQueries.ts: parks call + mapping ===")
    if queries_lines is None:
        missing.append("queries:file")
    else:
        calls = find_lines(queries_lines, "getParksNearby")
        print("getParksNearby mentions: " + str(len(calls)))
        for i, l in calls:
            print("  line " + str(i + 1) + ": " + l.strip()[:160])
            show_context(queries_lines, i, before=3, after=3)
        if not calls:
            missing.append("queries:parks-call")
        maps = find_lines(queries_lines, "results[18]")
        print("results[18] mentions: " + str(len(maps)))
        for i, l in maps:
            print("  line " + str(i + 1) + ": " + l.strip()[:160])
        park_maps = [i for i, l in maps if "park" in l.lower()]
        if not park_maps:
            missing.append("queries:parks-mapping")
        allsets = find_lines(queries_lines, "Promise.all")
        print("Promise.all mentions: " + str(len(allsets)))
        for i, l in allsets:
            print("  line " + str(i + 1) + ": " + l.strip()[:160])

    print()
    print("=== 2. index.tsx: park marker wiring + interior state ===")
    if index_lines is None:
        missing.append("index:file")
    else:
        checks = [
            ("park marker type", "'park'", "index:park-marker-type"),
            ("nearbyParks memo", "nearbyParks", "index:nearbyParks"),
            ("mapMarkers park spread", "mapMarkers", "index:markers-spread"),
            ("popup park branch", "selectedMarker.type === 'park'", "index:popup-branch"),
            ("ENTER setActivePark", "setActivePark(p)", "index:enter"),
            ("BASKETBALL_HTML import", "BasketballHtml", "index:basketball-import"),
            ("BasketballGameModal", "BasketballGameModal", "index:basketball-modal"),
            ("basketballOpen state", "basketballOpen", "index:basketball-state"),
            ("PLAYABLE ACTIVITIES", "PLAYABLE ACTIVITIES", "index:activities"),
        ]
        for label, needle, key in checks:
            hits = find_lines(index_lines, needle)
            print(label + ": " + str(len(hits)) + "x")
            if not hits:
                missing.append(key)
        old = find_lines(index_lines, "no menu, just who is inside")
        print("OLD park modal comment (should be 0 after interior patch): " + str(len(old)))
        new = find_lines(index_lines, "PARK_BASKETBALL_INTERIOR")
        print("NEW interior marker: " + str(len(new)) + "x")
        park_modal = find_lines(index_lines, "PARK interior")
        print("PARK interior comment lines: " + str(len(park_modal)))
        for i, l in park_modal:
            print("  line " + str(i + 1) + ": " + l.strip()[:160])

    print()
    print("=== 3. GameMap.tsx: park render branch ===")
    if gamemap_lines is None:
        missing.append("gamemap:file")
    else:
        for label, needle, key in [
            ("park mentions", "park", "gamemap:park"),
            ("park pink color", "#E91E63", "gamemap:color"),
        ]:
            hits = find_lines(gamemap_lines, needle)
            print(label + ": " + str(len(hits)) + "x")
            for i, l in hits[:6]:
                print("  line " + str(i + 1) + ": " + l.strip()[:160])
            if not hits:
                missing.append(key)

    print()
    print("=== 4. VERDICT ===")
    if not missing:
        print("VERDICT: (a) parks pipeline INTACT in code (call + mapping + "
              "marker wiring + GameMap branch all present). The markers "
              "are not missing from the code - check the live data / "
              "zoom / stale Expo Go bundle next.")
    else:
        print("VERDICT: (b) parks pipeline BROKEN - missing pieces:")
        for m in sorted(set(missing)):
            print("  - " + m)
    print("missing count: " + str(len(set(missing))))
    if missing:
        print("PARK_MARKERS_DIAG_PARTIAL missing=" + ",".join(sorted(set(missing))))
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    main()
