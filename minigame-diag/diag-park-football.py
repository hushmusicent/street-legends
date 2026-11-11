#!/usr/bin/env python3
"""Park football probe: print the LIVE park interior on /app so the football
port can be built against what is actually there.

CONTEXT (parent, 2026-11-07): the user approved the park football preview
(~/workspace/street-legends/park-football-preview.html, 78,221 bytes, smoke
68/68) and said "Now wire it to the parks. Put the option under the
basketball game." The basketball port ran clean (HTML 01:49 EST, interior
re-run 02:28 EST, PARK_BASKETBALL_HTML_OK + PARK_BASKETBALL_INTERIOR_OK),
but the Deploy that succeeded (01:55 EST) predates the interior re-run, so
this probe confirms the basketball interior is actually IN /app's index.tsx
before the football patch anchors on it.

This probe is READ-ONLY: it never edits a file, never restarts anything,
and makes no network calls -- it only reads the frontend code under <root>.
It prints:
  0. which files exist (index.tsx / BasketballHtml.ts) + line counts
  1. basketball interior markers (BasketballGameModal, PARK_BASKETBALL_INTERIOR,
     basketballOpen, parkSceneH, PLAYABLE ACTIVITIES, PoolWebView, import)
  2. the PLAYABLE ACTIVITIES block VERBATIM (the Basketball row the football
     row goes under) + the LEAVE button + the modal onRequestClose
  3. anchors the football patch will use (MapScreen anchor, parkFriendIds
     state line, park modal comment, Basketball row end)
  4. VERDICT: (a) basketball interior fully live -> straight football port,
     (b) partially live (list what is missing), (c) not live at all

Run:  python3 minigame-diag/diag-park-football.py [--root /app]
"""
import argparse
import sys
from pathlib import Path

MARKER = "PARK_FOOTBALL_DIAG_OK"

INDEX_CANDIDATES = [
    "frontend/app/(tabs)/index.tsx",
    "frontend/app/index.tsx",
]
BBALL_TS = "frontend/components/BasketballHtml.ts"


def read_file(path):
    try:
        return Path(path).read_text(errors="ignore").splitlines()
    except OSError:
        return None


def count(lines, needle):
    return sum(1 for ln in lines if needle in ln) if lines else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    print("=== 0. files ===")
    idx_lines = None
    idx_path = None
    for cand in INDEX_CANDIDATES:
        p = root / cand
        if p.exists():
            idx_lines = read_file(p)
            idx_path = str(p)
            print("index.tsx: %s (%d lines)" % (p, len(idx_lines)))
            break
    if idx_lines is None:
        print("index.tsx: NOT FOUND under %s" % root)
        print("VERDICT: (c) not live - index.tsx missing")
        print(MARKER)
        return 1
    bb = root / BBALL_TS
    print("BasketballHtml.ts: %s" % ("EXISTS (%d lines)" % len(read_file(bb)) if bb.exists() else "MISSING"))
    src = "\n".join(idx_lines)

    print("=== 1. basketball interior markers ===")
    checks = {
        "BasketballGameModal component": "const BasketballGameModal" in src,
        "PARK_BASKETBALL_INTERIOR marker": "PARK_BASKETBALL_INTERIOR" in src,
        "basketballOpen state": "basketballOpen" in src,
        "parkSceneH state": "parkSceneH" in src,
        "PLAYABLE ACTIVITIES heading": "PLAYABLE ACTIVITIES" in src,
        "Basketball row (TAP TO PLAY)": "Basketball" in src and "TAP TO PLAY" in src,
        "More activities coming soon": "More activities coming soon" in src,
        "PoolWebView lazy require": "let PoolWebView" in src,
        "BASKETBALL_HTML import": "BasketballHtml" in src,
        "park modal comment": "{/* PARK interior" in src,
        "MapScreen anchor": "export default function MapScreen() {" in src,
        "parkFriendIds state": "parkFriendIds" in src,
    }
    for name, ok in checks.items():
        print("  %s: %s" % ("OK  " if ok else "MISS", name))
    for needle in ("BasketballGameModal", "basketballOpen", "PARK_BASKETBALL_INTERIOR"):
        print("  count %r: %d" % (needle, count(idx_lines, needle)))

    print("=== 2. PLAYABLE ACTIVITIES block (verbatim) ===")
    act = [i for i, ln in enumerate(idx_lines) if "PLAYABLE ACTIVITIES" in ln]
    if len(act) == 1:
        s = act[0]
        # print from the heading down to the LEAVE button
        leave = [i for i in range(s, len(idx_lines)) if "LEAVE" in idx_lines[i]]
        e = leave[0] if leave else min(len(idx_lines), s + 60)
        for i in range(s, e + 1):
            print("  %d: %r" % (i + 1, idx_lines[i]))
    else:
        print("  PLAYABLE ACTIVITIES anchor count=%d (want 1)" % len(act))

    print("=== 3. anchors the football patch will use ===")
    print("  MapScreen anchor count: %d" % count(idx_lines, "export default function MapScreen() {"))
    print("  park modal comment count: %d" % count(idx_lines, "{/* PARK interior"))
    print("  parkFriendIds useState lines:")
    for i, ln in enumerate(idx_lines):
        if "parkFriendIds" in ln and "useState" in ln:
            print("    %d: %r" % (i + 1, ln))
    print("  LEAVE onPress lines:")
    for i, ln in enumerate(idx_lines):
        if "LEAVE" in ln:
            print("    %d: %r" % (i + 1, ln))
    print("  modal onRequestClose lines (park modal):")
    for i, ln in enumerate(idx_lines):
        if "onRequestClose" in ln and "setActivePark" in ln:
            print("    %d: %r" % (i + 1, ln))
    print("  BasketballGameModal render line:")
    for i, ln in enumerate(idx_lines):
        if "BasketballGameModal visible=" in ln:
            print("    %d: %r" % (i + 1, ln))

    print("=== 4. VERDICT ===")
    missing = [n for n, ok in checks.items() if not ok]
    if not missing:
        print("VERDICT: (a) basketball interior fully live - straight football port")
        print("  (add Football row under Basketball + FootballGameModal + footballOpen state)")
    elif len(missing) <= 3:
        print("VERDICT: (b) partially live - missing: %s" % ", ".join(missing))
    else:
        print("VERDICT: (c) not live - missing: %s" % ", ".join(missing))
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
