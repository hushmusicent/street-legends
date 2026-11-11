#!/usr/bin/env python3
"""Street Legends backend: Activity Center Pop Shot cabinet layout storage.

Extends the arrange layout endpoint so a center's layout can hold the
7th fixture, pop_shot (the arcade cabinet):
layout: {pool_table, dart_board, card_table, dominoes, scrabble,
chess_checkers, pop_shot}.
One change: _activity_center_clamp_layout now clamps pop_shot with the
same integer box (x -16..120, y -8..120) and returns it alongside the
other six. The merge (incoming + stored layout) already landed with
the chess backend patch — this patch does not touch it.

Why a backend patch is REQUIRED: the clamp builds its return dict
from the fixtures it knows; any pop_shot in the request body is
dropped before the $set, so the frontend's merged save would silently
lose the cabinet position on every call.

Robustness: the final state must clamp all seven keys, WHICHEVER
prior backend patches ran. So this patch handles all six live clamp
shapes — arrange-only (pool), dartboard (pool + dart), cardtable
(pool + dart + card), dominoes (pool + dart + card + dominoes),
Scrabble (pool + dart + card + dominoes + scrabble), chess
(pool + dart + card + dominoes + scrabble + chess) — verbatim, plus
a regex fallback on the clamp span that adds whichever getter lines /
return entries are missing. The clamp span scan ends at the first
non-blank column-0 line (the next top-level statement).

Run from /app: python3 backend/patch-activity-center-pop-shot.py
Backend only: Publish after running. Run BEFORE the Pop Shot frontend
patch (the frontend's merged save needs this clamp live first).
Idempotent: re-running prints ACTIVITY_CENTER_POP_SHOT_BACKEND_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "ACTIVITY_CENTER_POP_SHOT_BACKEND_OK"

CLAMP_ARRANGE = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}

    def num(v, lo, hi):
        try:
            n = float(v)
        except (TypeError, ValueError):
            return 0
        return int(max(lo, min(hi, round(n))))

    return {"pool_table": {"x": num(pool.get("x"), -16, 120), "y": num(pool.get("y"), -8, 120)}}'''

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

CLAMP_CHESS = '''def _activity_center_clamp_layout(layout):
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

CLAMP_NEW = '''def _activity_center_clamp_layout(layout):
    pool = (layout or {}).get("pool_table") or {}
    dart = (layout or {}).get("dart_board") or {}
    card = (layout or {}).get("card_table") or {}
    dom = (layout or {}).get("dominoes") or {}
    scr = (layout or {}).get("scrabble") or {}
    cc = (layout or {}).get("chess_checkers") or {}
    ps = (layout or {}).get("pop_shot") or {}

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
            "chess_checkers": {"x": num(cc.get("x"), -16, 120), "y": num(cc.get("y"), -8, 120)},
            "pop_shot": {"x": num(ps.get("x"), -16, 120), "y": num(ps.get("y"), -8, 120)}}'''

POOL_GETTER = 'pool = (layout or {}).get("pool_table") or {}'
DART_GETTER = 'dart = (layout or {}).get("dart_board") or {}'
CARD_GETTER = 'card = (layout or {}).get("card_table") or {}'
DOM_GETTER = 'dom = (layout or {}).get("dominoes") or {}'
SCR_GETTER = 'scr = (layout or {}).get("scrabble") or {}'
CC_GETTER = 'cc = (layout or {}).get("chess_checkers") or {}'
PS_GETTER = 'ps = (layout or {}).get("pop_shot") or {}'
DART_ENTRY = '"dart_board": {"x": num(dart.get("x"), -16, 120), "y": num(dart.get("y"), -8, 120)}'
CARD_ENTRY = '"card_table": {"x": num(card.get("x"), -16, 120), "y": num(card.get("y"), -8, 120)}'
DOM_ENTRY = '"dominoes": {"x": num(dom.get("x"), -16, 120), "y": num(dom.get("y"), -8, 120)}'
SCR_ENTRY = '"scrabble": {"x": num(scr.get("x"), -16, 120), "y": num(scr.get("y"), -8, 120)}'
CC_ENTRY = '"chess_checkers": {"x": num(cc.get("x"), -16, 120), "y": num(cc.get("y"), -8, 120)}'
PS_ENTRY = '"pop_shot": {"x": num(ps.get("x"), -16, 120), "y": num(ps.get("y"), -8, 120)}'


def _clamp_span(src):
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
    new_body = body
    getters = [(DART_GETTER, POOL_GETTER), (CARD_GETTER, DART_GETTER),
               (DOM_GETTER, CARD_GETTER), (SCR_GETTER, DOM_GETTER),
               (CC_GETTER, SCR_GETTER), (PS_GETTER, CC_GETTER)]
    for getter, anchor in getters:
        if getter not in new_body:
            if new_body.count(anchor) != 1:
                return None
            new_body = new_body.replace(anchor, anchor + "\n    " + getter, 1)
    if "return {" not in new_body:
        return None
    ret_end = new_body.rfind("}}")
    if ret_end == -1:
        return None
    missing = []
    for entry in (DART_ENTRY, CARD_ENTRY, DOM_ENTRY, SCR_ENTRY, CC_ENTRY, PS_ENTRY):
        if entry not in new_body:
            missing.append(entry)
    if missing:
        new_body = (new_body[:ret_end + 1] + ",\n            " +
                    ",\n            ".join(missing) + new_body[ret_end + 1:])
    for key in ('"dart_board"', '"card_table"', '"dominoes"', '"scrabble"',
                '"chess_checkers"', '"pop_shot"'):
        if key not in new_body:
            return None
    for getter in (DART_GETTER, CARD_GETTER, DOM_GETTER, SCR_GETTER, CC_GETTER, PS_GETTER):
        if getter not in new_body:
            return None
    return new_body


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - pop shot layout NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    if "def activity_center_layout" not in src:
        print("WARNING: layout endpoint not found - run the arrange backend patch first, pop shot layout NOT added")
        return 1
    span = _clamp_span(src)
    if span is None:
        print("WARNING: _activity_center_clamp_layout not found - pop shot layout NOT added")
        return 1
    if '"pop_shot"' in src[span[0]:span[1]]:
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_ALREADY_APPLIED")
        landed = ["clamp"]
    elif CLAMP_ARRANGE in src:
        src = src.replace(CLAMP_ARRANGE, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_OK (from arrange-only clamp)")
        landed = ["clamp"]
    elif CLAMP_DART in src:
        src = src.replace(CLAMP_DART, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_OK (from dartboard clamp)")
        landed = ["clamp"]
    elif CLAMP_CARD in src:
        src = src.replace(CLAMP_CARD, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_OK (from cardtable clamp)")
        landed = ["clamp"]
    elif CLAMP_DOM in src:
        src = src.replace(CLAMP_DOM, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_OK (from dominoes clamp)")
        landed = ["clamp"]
    elif CLAMP_SCR in src:
        src = src.replace(CLAMP_SCR, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_OK (from Scrabble clamp)")
        landed = ["clamp"]
    elif CLAMP_CHESS in src:
        src = src.replace(CLAMP_CHESS, CLAMP_NEW, 1)
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_OK (from chess clamp)")
        landed = ["clamp"]
    else:
        body = src[span[0]:span[1]]
        new_body = _clamp_regex_fallback(body)
        if new_body is not None and new_body != body and '"pop_shot"' in new_body:
            src = src[:span[0]] + new_body + src[span[1]:]
            print("ACTIVITY_CENTER_POP_SHOT_BACKEND_CLAMP_OK (regex fallback)")
            landed = ["clamp"]
        else:
            print("WARNING: clamp shape not matched verbatim or by regex - pop shot layout NOT added")
            return 1
    if src == orig:
        span2 = _clamp_span(src)
        if span2 is not None and '"pop_shot"' in src[span2[0]:span2[1]]:
            print("ACTIVITY_CENTER_POP_SHOT_BACKEND_ALREADY_APPLIED")
            return 0
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_PARTIAL: nothing landed")
        return 1
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("ACTIVITY_CENTER_POP_SHOT_BACKEND_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
