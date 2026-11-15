#!/usr/bin/env python3
"""Street Legends frontend: fix Chess & Checkers menu (buttons dead, no level picker).

ROOT CAUSE (verified on the live file): the center-prize patch duplicated
the showResult function header inside ChessCheckersHtml.ts:

    function showResult(msg){
      gameOver = true;
    function showResult(msg){      <- duplicate, never closed
      gameOver = true;
      if (curMode === "cpu" ...) ...postMessage(center_prize_win)...
      ...
    }

The outer copy is never closed, so the whole script has one unclosed
brace and fails to parse ("Unexpected end of input"). Nothing in the
script runs: the level grid (#lvlGrid) is never populated (so there are
no level buttons, only the static "Level 5 - Medium" text), and the
START GAME / Chess / Checkers button handlers are never attached (so
nothing starts the game).

This patch removes the duplicated inner header (the second
"function showResult(msg){" + its "gameOver = true;"), leaving one
correct showResult that keeps the center-prize post. It verifies the
script parses clean (node --check) before writing, and aborts changing
nothing on failure.

Run from /app: python3 frontend/patch-chess-checkers-showresult-fix.py
Frontend only: reload Expo Go after running, then open Chess & Checkers
- the 1-10 level buttons must appear and START GAME must open the board.
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

TARGET = Path("frontend/components/ChessCheckersHtml.ts")
MARKER = "CHESS_CHECKERS_FIX_OK"

DUP = (
    'function showResult(msg){\n'
    '  gameOver = true;\n'
    'function showResult(msg){\n'
    '  gameOver = true;\n'
)
FIXED = (
    'function showResult(msg){\n'
    '  gameOver = true;\n'
)


def extract_js(src):
    m = re.search(r"<script>([\s\S]*?)</script>", src)
    return m.group(1) if m else None


def js_parses(js):
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as f:
        f.write(js)
        tmp = f.name
    try:
        r = subprocess.run(["node", "--check", tmp], capture_output=True, text=True, timeout=30)
        return r.returncode == 0, (r.stderr or "").strip()
    except Exception as e:
        return False, str(e)
    finally:
        Path(tmp).unlink(missing_ok=True)


def main():
    if not TARGET.exists():
        print("WARNING: ChessCheckersHtml.ts not found - NOT fixed")
        return 1
    src = TARGET.read_text(errors="ignore")
    orig = src
    if DUP not in src:
        # Already fixed (or a different shape) — verify it parses.
        js = extract_js(src)
        if js is None:
            print("WARNING: <script> block not found - NOT fixed")
            return 1
        ok, err = js_parses(js)
        if ok:
            print("CHESS_CHECKERS_FIX_ALREADY_APPLIED")
            print(MARKER)
            return 0
        print("CHESS_CHECKERS_FIX_SHAPE_FAIL: duplicate header not found and script still does not parse: %s" % err)
        return 1
    src2 = src.replace(DUP, FIXED, 1)
    if src2.count("function showResult(msg){") != 1:
        print("CHESS_CHECKERS_FIX_COUNT_FAIL: showResult count != 1 after fix (nothing written)")
        return 1
    js = extract_js(src2)
    if js is None:
        print("CHESS_CHECKERS_FIX_SCRIPT_FAIL: <script> block not found after fix (nothing written)")
        return 1
    ok, err = js_parses(js)
    if not ok:
        print("CHESS_CHECKERS_FIX_PARSE_FAIL: %s (nothing written)" % err)
        return 1
    if src2 != orig:
        TARGET.write_text(src2)
    print("OK: removed duplicated showResult header; script parses clean")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
