#!/usr/bin/env python3
"""Street Legends backend: Activity Center chess and checkers table layout storage.

Extends the arrange layout endpoint (backend/patch-activity-center-arrange.py)
so a center's layout can hold ALL SIX fixtures:
layout: {pool_table: {x, y}, dart_board: {x, y}, card_table: {x, y},
dominoes: {x, y}, scrabble: {x, y}, chess_checkers: {x, y}}.
Two changes:
  1. _activity_center_clamp_layout now clamps chess_checkers with the
     same integer box (x -16..120, y -8..120) and returns it alongside
     pool_table, dart_board, card_table, dominoes, and scrabble.
  2. The layout endpoint MERGES the incoming layout with the center's
     stored layout before clamping, so an old one- through
     five-fixture save can never wipe a stored fixture in a
     mixed-version window.

Why a backend patch is REQUIRED (proven from the code): the arrange
clamp builds its return dict from pool_table ONLY, the dartboard
patch's clamp from pool_table + dart_board ONLY, the cardtable
patch's clamp from pool_table + dart_board + card_table ONLY, the
dominoes patch's clamp from pool_table + dart_board + card_table +
dominoes ONLY, and the Scrabble patch's clamp from pool_table +
dart_board + card_table + dominoes + scrabble ONLY — any
chess_checkers in the request body is dropped before the $set, so the
frontend's merged save would silently lose the chess position on
every call.

Robustness: the final state must clamp all six keys + merge,
WHICHEVER prior backend patches ran. So this patch handles all five
live clamp shapes — arrange-only (pool), dartboard-extended
(pool + dart), cardtable-extended (pool + dart + card),
dominoes-extended (pool + dart + card + dominoes), Scrabble-extended
(pool + dart + card + dominoes + scrabble) — verbatim, plus a regex
fallback on the clamp span that adds whichever getter lines / return
entries are missing. The clamp span scan ends at the first non-blank
column-0 line (the next top-level statement) — a naive `\\ndef `
search does NOT stop at `async def` or `@decorator` lines, so the
span would run into the layout endpoint and the fallback's
rfind("}}") could hit the endpoint's {"$set": {"layout": layout}}
and corrupt it (the cardtable patch's span has that bug; its fallback
was never exercised — this one does not).

The chess/checkers ROOM endpoints need no change: POST
/api/chess_checkers/rooms/create takes only {player_id, player_name,
game} and /join only {code, player_id, player_name} — no house
lookup, no ownership check (same as pool/darts/cards/dominoes/
Scrabble) — so center PvP works with no backend change.

Run from /app: python3 backend/patch-activity-center-chess.py
Backend only: Publish after running. Run BEFORE the chess frontend
patch (the frontend's merged save needs this clamp live first).
Idempotent: re-running prints ACTIVITY_CENTER_CHESS_BACKEND_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "ACTIVITY_CENTER_CHESS_BACKEND_OK"

# Verbatim from backend/patch-activity-center-arrange.py.
CLAMP_ARRANGE = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)}}'''

# Verbatim from backend/patch-activity-center-dartboard.py (CLAMP_NEW).
CLAMP_DART = '''def _activity_center_clamp_layout(layout):
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

# Verbatim from backend/patch-activity-center-cardtable.py (CLAMP_NEW).
CLAMP_CARD = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}
    dart = (layout or {}).get("dart_board") or {}
    card = (layout or {}).get("card_table") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)},
            "dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)},
            "card_table": {"x": num(card.get("x"), -16, 120), "y": num(card.get("y"), -8, 120)}}'''

# Verbatim from backend/patch-activity-center-dominoes.py (CLAMP_NEW).
CLAMP_DOM = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}
    dart = (layout or {}).get("dart_board") or {}
    card = (layout or {}).get("card_table") or {}
    dom = (layout or {}).get("dominoes") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)},
            "dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)},
            "card_table": {"x": num(card.get("x"), -16, 120), "y": num(card.get("y"), -8, 120)},
            "dominoes": {"x": num(dom.get("x"), -16, 120), "y": num(dom.get("y"), -8, 120)}}'''

# Verbatim from backend/patch-activity-center-scrabble.py (CLAMP_NEW).
CLAMP_SCR = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}
    dart = (layout or {}).get("dart_board") or {}
    card = (layout or {}).get("card_table") or {}
    dom = (layout or {}).get("dominoes") or {}
    scr = (layout or {}).get("scrabble") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)},
            "dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)},
            "card_table": {"x": num(card.get("x"), -16, 120), "y": num(card.get("y"), -8, 120)},
            "dominoes": {"x": num(dom.get("x"), -16, 120), "y": num(dom.get("y"), -8, 120)},
            "scrabble": {"x": num(scr.get("x"), -16, 120), "y": num(scr.get("y"), -8, 120)}}'''

CLAMP_NEW = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}
    dart = (layout or {}).get("dart_board") or {}
    card = (layout or {}).get("card_table") or {}
    dom = (layout or {}).get("dominoes") or {}
    scr = (layout or {}).get("scrabble") or {}
    cc = (layout or {}).get("chess_checkers") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)},
            "dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)},
            "card_table": {"x": num(card.get("x"), -16, 120), "y": num(card.get("y"), -8, 120)},
            "dominoes": {"x": num(dom.get("x"), -16, 120), "y": num(dom.get("y"), -8, 120)},
            "scrabble": {"x": num(scr.get("x"), -16, 120), "y": num(scr.get("y"), -8, 120)},
            "chess_checkers": {"x": num(cc.get("x"), -16, 120), "y": num(cc.get("y"), -8, 120)}}'''

SAVE_OLD = '    layout = _activity_center_clamp_layout(data.get("layout") or {})'
SAVE_NEW = '''    incoming_layout = data.get("layout") or {}
    stored_layout = center.get("layout") or {}
    merged_layout = dict(stored_layout)
    merged_layout.update(incoming_layout)
    layout = _activity_center_clamp_layout(merged_layout)'''

POOL_GETTER = 'pool = (layout or {}).get("pool_table") or {}'
DART_GETTER = 'dart = (layout or {}).get("dart_board") or {}'
CARD_GETTER = 'card = (layout or {}).get("card_table") or {}'
DOM_GETTER = 'dom = (layout or {}).get("dominoes") or {}'
SCR_GETTER = 'scr = (layout or {}).get("scrabble") or {}'
CC_GETTER = 'cc = (layout or {}).get("chess_checkers") or {}'
DART_ENTRY = '"dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)}'
CARD_ENTRY = '"card_table": {"x": num(card.get("x"), -16, 120), "y": num(card.get("y"), -8, 120)}'
DOM_ENTRY = '"dominoes": {"x": num(dom.get("x"), -16, 120), "y": num(dom.get("y"), -8, 120)}'
SCR_ENTRY = '"scrabble": {"x": num(scr.get("x"), -16, 120), "y": num(scr.get("y"), -8, 120)}'
CC_ENTRY = '"chess_checkers": {"x": num(cc.get("x"), -16, 120), "y": num(cc.get("y"), -8, 120)}'


def _clamp_span(src):
    """(start, end) of the _activity_center_clamp_layout def, or None.
    Ends at the first non-blank column-0 line after the def — i.e. the
    next top-level statement (def / async def / @decorator / class)."""
    m = re.search(r"def _activity_center_clamp_layout\(layout\):", src)
    if not m:
        return None
    start = m.start()
    lines = src[m.start():].split("\n")
    end_lines = 1
    for ln in lines[1:]:
        if ln.strip() == "":
            end_lines += 1
            continue
        if ln[0] not in " \t":
            break
        end_lines += 1
    end = m.start() + len("\n".join(lines[:end_lines]))
    return (start, end)


def _clamp_regex_fallback(body):
    """Add whichever getter lines / return entries are missing from a
    clamp body that matches no verbatim variant. Returns the new
    body, or None if the shape cannot be handled safely."""
    new_body = body
    # Getters: insert each missing one after the previous getter line.
    if DART_GETTER not in new_body:
        if new_body.count(POOL_GETTER) != 1:
            return None
        new_body = new_body.replace(POOL_GETTER, POOL_GETTER + "\n    " + DART_GETTER, 1)
    if CARD_GETTER not in new_body:
        anchor = DART_GETTER if DART_GETTER in new_body else POOL_GETTER
        if new_body.count(anchor) != 1:
            return None
        new_body = new_body.replace(anchor, anchor + "\n    " + CARD_GETTER, 1)
    if DOM_GETTER not in new_body:
        anchor = CARD_GETTER if CARD_GETTER in new_body else (DART_GETTER if DART_GETTER in new_body else POOL_GETTER)
        if new_body.count(anchor) != 1:
            return None
        new_body = new_body.replace(anchor, anchor + "\n    " + DOM_GETTER, 1)
    if SCR_GETTER not in new_body:
        anchor = DOM_GETTER if DOM_GETTER in new_body else (CARD_GETTER if CARD_GETTER in new_body else (DART_GETTER if DART_GETTER in new_body else POOL_GETTER))
        if new_body.count(anchor) != 1:
            return None
        new_body = new_body.replace(anchor, anchor + "\n    " + SCR_GETTER, 1)
    if CC_GETTER not in new_body:
        anchor = SCR_GETTER if SCR_GETTER in new_body else (DOM_GETTER if DOM_GETTER in new_body else (CARD_GETTER if CARD_GETTER in new_body else (DART_GETTER if DART_GETTER in new_body else POOL_GETTER)))
        if new_body.count(anchor) != 1:
            return None
        new_body = new_body.replace(anchor, anchor + "\n    " + CC_GETTER, 1)
    # Return dict: the statement ends with `}}` — the first `}` closes
    # the last fixture dict, the second closes the outer dict. Insert
    # each missing entry after the inner dict's close (at ret_end + 1).
    if "return {" not in new_body:
        return None
    ret_end = new_body.rfind("}}")
    if ret_end == -1:
        return None
    missing = []
    if DART_ENTRY not in new_body:
        missing.append(DART_ENTRY)
    if CARD_ENTRY not in new_body:
        missing.append(CARD_ENTRY)
    if DOM_ENTRY not in new_body:
        missing.append(DOM_ENTRY)
    if SCR_ENTRY not in new_body:
        missing.append(SCR_ENTRY)
    if CC_ENTRY not in new_body:
        missing.append(CC_ENTRY)
    if missing:
        new_body = (new_body[:ret_end + 1] + ",\n            " +
                    ",\n            ".join(missing) + new_body[ret_end + 1:])
    if '"dart_board"' not in new_body or '"card_table"' not in new_body or '"dominoes"' not in new_body or '"scrabble"' not in new_body or '"chess_checkers"' not in new_body:
        return None
    if DART_GETTER not in new_body or CARD_GETTER not in new_body or DOM_GETTER not in new_body or SCR_GETTER not in new_body or CC_GETTER not in new_body:
        return None
    return new_body


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - chess layout NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    landed = []
    warnings = []

    if "def activity_center_layout" not in src:
        print("WARNING: layout endpoint not found - run the arrange backend patch first, chess layout NOT added")
        return 1

    # ---- Piece 1: extend the clamp to chess_checkers (and any absent fixtures). ----
    span = _clamp_span(src)
    if span is None:
        print("WARNING: _activity_center_clamp_layout not found - chess layout NOT added")
        return 1
    if "chess_checkers" in src[span[0]:span[1]]:
        print("ACTIVITY_CENTER_CHESS_BACKEND_CLAMP_ALREADY_APPLIED")
        landed.append("clamp")
    elif CLAMP_ARRANGE in src:
        src = src.replace(CLAMP_ARRANGE, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_CHESS_BACKEND_CLAMP_OK (from arrange-only clamp)")
        landed.append("clamp")
    elif CLAMP_DART in src:
        src = src.replace(CLAMP_DART, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_CHESS_BACKEND_CLAMP_OK (from dartboard clamp)")
        landed.append("clamp")
    elif CLAMP_CARD in src:
        src = src.replace(CLAMP_CARD, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_CHESS_BACKEND_CLAMP_OK (from cardtable clamp)")
        landed.append("clamp")
    elif CLAMP_DOM in src:
        src = src.replace(CLAMP_DOM, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_CHESS_BACKEND_CLAMP_OK (from dominoes clamp)")
        landed.append("clamp")
    elif CLAMP_SCR in src:
        src = src.replace(CLAMP_SCR, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_CHESS_BACKEND_CLAMP_OK (from Scrabble clamp)")
        landed.append("clamp")
    else:
        body = src[span[0]:span[1]]
        new_body = _clamp_regex_fallback(body)
        if new_body is not None and new_body != body and '"chess_checkers"' in new_body:
            src = src[:span[0]] + new_body + src[span[1]:]
            print("ACTIVITY_CENTER_CHESS_BACKEND_CLAMP_OK (regex fallback)")
            landed.append("clamp")
        else:
            print("WARNING: clamp shape not matched verbatim or by regex - chess layout NOT added")
            return 1

    # ---- Piece 2: merge incoming layout with the stored one. ----
    if "merged_layout = dict(stored_layout)" in src:
        print("ACTIVITY_CENTER_CHESS_BACKEND_MERGE_ALREADY_APPLIED")
        landed.append("merge")
    elif src.count(SAVE_OLD) == 1:
        src = src.replace(SAVE_OLD, SAVE_NEW, 1)
        print("ACTIVITY_CENTER_CHESS_BACKEND_MERGE_OK")
        landed.append("merge")
    else:
        print("WARNING: layout save line matched %dx - merge NOT added (old one-fixture saves could wipe a stored fixture)" % src.count(SAVE_OLD))
        warnings.append("merge")

    if src == orig:
        # Nothing changed: a clean re-run only if both pieces are already there.
        span2 = _clamp_span(src)
        if span2 is not None and "chess_checkers" in src[span2[0]:span2[1]] and "merged_layout = dict(stored_layout)" in src:
            print("ACTIVITY_CENTER_CHESS_BACKEND_ALREADY_APPLIED")
            return 0
        print("ACTIVITY_CENTER_CHESS_BACKEND_PARTIAL: nothing landed")
        return 1

    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("ACTIVITY_CENTER_CHESS_BACKEND_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_CHESS_BACKEND_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
