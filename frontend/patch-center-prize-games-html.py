#!/usr/bin/env python3
"""Street Legends frontend: Activity Center cash prizes — table-game HTML.

Adds a win postMessage to each PvC table-game HTML file so the app can
pay the $500 win prize (Chess & Checkers: $500 + 10% per level, 1-10).
Each game posts {type:'center_prize_win', game, level} to the app the
moment the local player wins vs the CPU; the game modal's onMessage
(frontend/patch-center-prize-games-frontend.py) calls
POST /api/center-prize/award and shows a gold "+$X PRIZE!" banner.

The games are the SAME components in the house and the activity
center, so the prize pays on a win in either place. (Center-only
would need an isCenter flag threaded through all six games.)

Files + win points (all PvC; PvP uses separate *_PvpHtml.ts files):
  PoolGameHtml.ts      endGame('you')  -> 'YOU WIN! Table cleared!'
  DartGameHtml.ts      endGame('you')  -> 'YOU WIN! 301 cleared!'
  CardSpadesHtml.ts    SP.us > SP.them -> 'YOU WIN THE GAME!'
  CardGinHtml.ts       G.us > G.them   -> 'YOU WIN THE GAME!'
  DominoHtml.ts        S.youScore >= 100 -> 'YOU WIN THE MATCH!'
  ScrabbleHtml.ts      endByEmpty/endByPasses, win === 'you' -> 'YOU WIN!'
  ChessCheckersHtml.ts showResult, PvC 'Checkmate! You win!' / 'You win!'

Surgical edits: each file is read, the win anchor is found, and the
prize post is inserted right after it. Nothing else in the file is
touched, so PvP and later fixes are preserved. Idempotent per file:
a file already holding 'center_prize_win' is skipped.

Run from /app: python3 frontend/patch-center-prize-games-html.py
Frontend only: reload Expo Go after running.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
MARKER = "CENTER_PRIZE_GAMES_HTML_OK"

POST = "if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'center_prize_win', game: '%s', level: %s }));"

# (ts file, game, level expr, anchor, insertion) — insertion is the
# full line(s) to add right after the anchor. `all` replaces every
# occurrence of the anchor (Scrabble has two end functions).
EDITS = [
    (
        "frontend/components/PoolGameHtml.ts", "pool", "1",
        "    setMsg('YOU WIN! Table cleared!');",
        "    " + (POST % ("pool", "1")),
        False,
    ),
    (
        "frontend/components/DartGameHtml.ts", "dartboard", "1",
        "  setMsg(w === 'you' ? 'YOU WIN! 301 cleared!' : 'CPU WINS!');",
        "  if (w === 'you') " + (POST % ("dartboard", "1")),
        False,
    ),
    (
        "frontend/components/CardSpadesHtml.ts", "card_table", "1",
        "    SP.msg = (SP.us > SP.them ? 'YOU WIN THE GAME!' : SP.them > SP.us ? 'OPPONENTS WIN THE GAME.' : 'TIE GAME!') + ' Final: You ' + SP.us + ' - Opponents ' + SP.them + '.';",
        "    if (SP.us > SP.them) " + (POST % ("card_table", "1")),
        False,
    ),
    (
        "frontend/components/CardGinHtml.ts", "card_table", "1",
        "    G.msg = (G.us > G.them ? 'YOU WIN THE GAME!' : 'CPU WINS THE GAME.') + ' Final: You ' + G.us + ' - CPU ' + G.them + '.';",
        "    if (G.us > G.them) " + (POST % ("card_table", "1")),
        False,
    ),
    (
        "frontend/components/DominoHtml.ts", "dominoes", "1",
        '    el("overText").textContent = (S.youScore >= 100 ? "YOU WIN THE MATCH!" : "CPU WINS THE MATCH.") + " Final: You " + S.youScore + " - CPU " + S.cpuScore + ".";',
        "    if (S.youScore >= 100) " + (POST % ("dominoes", "1")),
        False,
    ),
    (
        "frontend/components/ScrabbleHtml.ts", "scrabble", "1",
        '  el("overText").textContent = (win === "tie" ? "Tie game! " : (win === "you" ? "YOU WIN! " : "CPU WINS. ")) + "Final: You " + S.youScore + " - CPU " + S.cpuScore + ".";',
        "  if (win === \"you\") " + (POST % ("scrabble", "1")),
        True,
    ),
    (
        "frontend/components/ChessCheckersHtml.ts", "chess_checkers", "curLevel",
        "function showResult(msg){\n  gameOver = true;",
        "function showResult(msg){\n  gameOver = true;\n  if (curMode === \"cpu\" && (msg === \"Checkmate! You win!\" || msg === \"You win!\")) " + (POST % ("chess_checkers", "curLevel")),
        False,
    ),
]


def main():
    landed = []
    skipped = []
    warnings = []
    for rel, game, level, anchor, insertion, replace_all in EDITS:
        ts = ROOT / rel
        if not ts.exists():
            warnings.append("%s not found - %s prize NOT added" % (rel, game))
            continue
        src = ts.read_text(errors="ignore")
        if "center_prize_win" in src and ("game: '%s'" % game) in src:
            print("%s_ALREADY_APPLIED (%s)" % (game.upper(), rel))
            skipped.append(game)
            continue
        if anchor not in src:
            warnings.append("%s win anchor not found in %s - prize NOT added" % (game, rel))
            continue
        if replace_all:
            n = src.count(anchor)
            src = src.replace(anchor, anchor + "\n" + insertion)
            print("OK: %s prize added (%d win paths)" % (game, n))
        else:
            src = src.replace(anchor, anchor + "\n" + insertion, 1)
            print("OK: %s prize added" % game)
        ts.write_text(src, encoding="utf-8")
        landed.append(game)
    if warnings:
        for w in warnings:
            print("WARNING: " + w)
    if not landed and not skipped:
        print("CENTER_PRIZE_GAMES_HTML_PARTIAL: nothing landed")
        return 1
    if landed:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
