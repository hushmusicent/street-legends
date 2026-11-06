#!/usr/bin/env python3
"""Street Legends backend: Activity Center dartboard layout storage.

Extends the arrange layout endpoint (backend/patch-activity-center-arrange.py)
so a center's layout can hold BOTH fixtures:
layout: {pool_table: {x, y}, dart_board: {x, y}}. Two changes:
  1. _activity_center_clamp_layout now clamps dart_board with the same
     integer box (x -16..120, y -8..120) and returns it alongside
     pool_table.
  2. The layout endpoint MERGES the incoming layout with the center's
     stored layout before clamping, so an old pool-only save can never
     wipe a stored dart_board (and vice versa) in a mixed-version window.

Why a backend patch is REQUIRED (proven from the code): the arrange
clamp builds its return dict from pool_table ONLY — any dart_board in
the request body is dropped before the $set, so the frontend's merged
save would silently lose the dartboard position on every call. The
darts ROOM endpoints need no change: POST /api/darts/rooms/create and
/join take only {player_id, player_name} / {code, player_id,
player_name} — no house lookup, no ownership check (same as pool) —
so center PvP works with no backend change.

Run from /app: python3 backend/patch-activity-center-dartboard.py
Backend only: Publish after running. Run BEFORE the dartboard frontend
patch (the frontend's merged save needs this clamp live first).
Idempotent: re-run prints ACTIVITY_CENTER_DARTBOARD_BACKEND_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "ACTIVITY_CENTER_DARTBOARD_BACKEND_OK"

# Verbatim from backend/patch-activity-center-arrange.py.
CLAMP_OLD = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)}}'''

CLAMP_NEW = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}
    dart = (layout or {}).get("dart_board") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)},
            "dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)}}'''

SAVE_OLD = '    layout = _activity_center_clamp_layout(data.get("layout") or {})'
SAVE_NEW = '''    incoming_layout = data.get("layout") or {}
    stored_layout = center.get("layout") or {}
    merged_layout = dict(stored_layout)
    merged_layout.update(incoming_layout)
    layout = _activity_center_clamp_layout(merged_layout)'''


def _clamp_span(src):
    """(start, end) of the _activity_center_clamp_layout def, or None."""
    m = re.search(r"def _activity_center_clamp_layout\(layout\):", src)
    if not m:
        return None
    start = m.start()
    nxt = re.search(r"\ndef ", src[m.end():])
    end = m.end() + nxt.start() + 1 if nxt else len(src)
    return (start, end)


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - dartboard layout NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    landed = []
    warnings = []

    if "def activity_center_layout" not in src:
        print("WARNING: layout endpoint not found - run the arrange backend patch first, dartboard layout NOT added")
        return 1

    # ---- Idempotency: dart_board already in the clamp. ----
    span = _clamp_span(src)
    if span is not None and "dart_board" in src[span[0]:span[1]]:
        print("ACTIVITY_CENTER_DARTBOARD_BACKEND_ALREADY_APPLIED")
        return 0

    # ---- Piece 1: extend the clamp to dart_board. ----
    if CLAMP_OLD in src:
        src = src.replace(CLAMP_OLD, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_DARTBOARD_BACKEND_CLAMP_OK")
        landed.append("clamp")
    elif span is not None:
        body = src[span[0]:span[1]]
        new_body = body
        ok = True
        if body.count('pool = (layout or {}).get("pool_table") or {}') == 1:
            new_body = new_body.replace(
                'pool = (layout or {}).get("pool_table") or {}',
                'pool = (layout or {}).get("pool_table") or {}\n    dart = (layout or {}).get("dart_board") or {}', 1)
        else:
            ok = False
        m = re.search(r'return \{"pool_table": \{"x": num\(pool\.get\("x"\), -16, 120\), "y": num\(pool\.get\("y"\), -8, 120\)\}', new_body)
        if m:
            # m ends right after the pool dict's closing } — insert the dart
            # entry inside the outer dict; the outer } still follows.
            new_body = new_body[:m.end()] + ',\n            "dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)}' + new_body[m.end():]
        else:
            ok = False
        if ok and "dart_board" in new_body:
            src = src[:span[0]] + new_body + src[span[1]:]
            print("ACTIVITY_CENTER_DARTBOARD_BACKEND_CLAMP_OK (regex fallback)")
            landed.append("clamp")
        else:
            print("WARNING: clamp shape not matched verbatim or by regex - dartboard layout NOT added")
            return 1
    else:
        print("WARNING: _activity_center_clamp_layout not found - dartboard layout NOT added")
        return 1

    # ---- Piece 2: merge incoming layout with the stored one. ----
    if "merged_layout = dict(stored_layout)" in src:
        print("ACTIVITY_CENTER_DARTBOARD_BACKEND_MERGE_ALREADY_APPLIED")
        landed.append("merge")
    elif src.count(SAVE_OLD) == 1:
        src = src.replace(SAVE_OLD, SAVE_NEW, 1)
        print("ACTIVITY_CENTER_DARTBOARD_BACKEND_MERGE_OK")
        landed.append("merge")
    else:
        print("WARNING: layout save line matched %dx - merge NOT added (old pool-only saves could wipe a stored dart_board)" % src.count(SAVE_OLD))
        warnings.append("merge")

    if src == orig:
        print("ACTIVITY_CENTER_DARTBOARD_BACKEND_PARTIAL: nothing landed")
        return 1

    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("ACTIVITY_CENTER_DARTBOARD_BACKEND_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_DARTBOARD_BACKEND_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
