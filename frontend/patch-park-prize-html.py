#!/usr/bin/env python3
"""Street Legends frontend: Park games PvC win prize signal.

Adds a one-time win postMessage to each of the 6 park game HTML
components so the app can pay the $500 PvC prize (POST
/api/center-prize/award, game registered in CENTER_PRIZE_GAMES)
when the player beats the CPU. PvP wins do NOT post here -- PvP
already has cash bets, and every hook below is guarded by
!pvpIsOn().

Per game, the hook is the game's own PvC end condition:
  basketball  endGame(team)        -- first to 21; YOU are HOME (team 0)
  football    endGame(team)        -- first to 10 TDs; YOU are HOME (team 0)
  baseball    endGame()            -- after 6 innings; YOU are HOME (Bombers)
  soccer      endHalf() 2nd half   -- full time; YOU are HOME (Bombers)
  tennis      endSet(winner)       -- set won; YOU are HOME (DANTE)
  one_on_one  endGame(winner)      -- first to 21; YOU are HOME (DANTE)

Each hook posts exactly once per game (G.prizePosted flag, reset in
newGame/startGame so a rematch can pay again) and only when the
player's side won (not a CPU win, not a draw/tie).

What this does (frontend only; Expo Go). Run from /app:
  python3 frontend/patch-park-prize-html.py
Idempotent: a full re-run prints PARK_PRIZE_HTML_ALREADY_APPLIED.
"""
import sys
from pathlib import Path

MARKER = "PARK_PRIZE_HTML_OK"
POST_TYPE = "park_prize_win"

# Per game: file, game name for the post, and the three exact anchors.
#   flag_anchor  -- a line inside the G state object; the flag is added after it
#   reset_anchor -- a line inside newGame/startGame; the flag reset is added after it
#   win_anchor   -- the win-point line(s); the guarded post is added after them
#   win_post     -- the guarded postMessage line (indentation matches the file)
GAMES = [
    {
        "file": "frontend/components/BasketballHtml.ts",
        "game": "basketball",
        "flag_anchor": "  pvp:null, // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT}",
        "flag_line": "  prizePosted:false, // park prize: posted once per game when YOU beat the CPU",
        "reset_anchor": "  G.score=[0,0]; G.elapsed=0; G.fire=null; G.turbo=100; G.pause=0; G.afterPause=false; G.shake=0;",
        "reset_line": "  G.prizePosted=false;",
        "win_anchor": "function endGame(team){\n  G.mode='over';",
        "win_post": "  if(!pvpIsOn()&&team===G.myTeam&&!G.prizePosted){G.prizePosted=true;if(window.ReactNativeWebView)window.ReactNativeWebView.postMessage(JSON.stringify({type:'park_prize_win',game:'basketball',level:1}));}",
    },
    {
        "file": "frontend/components/FootballHtml.ts",
        "game": "football",
        "flag_anchor": "  pvp:null, // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT, playOver}",
        "flag_line": "  prizePosted:false, // park prize: posted once per game when YOU beat the CPU",
        "reset_anchor": "  G.score=[0,0]; G.elapsed=0; G.turbo=100; G.pause=0; G.afterPause=false;",
        "reset_line": "  G.prizePosted=false;",
        "win_anchor": "function endGame(team){\n  G.mode='over'; G.phase='dead';",
        "win_post": "  if(!pvpIsOn()&&team===G.myTeam&&!G.prizePosted){G.prizePosted=true;if(window.ReactNativeWebView)window.ReactNativeWebView.postMessage(JSON.stringify({type:'park_prize_win',game:'football',level:1}));}",
    },
    {
        "file": "frontend/components/BaseballHtml.ts",
        "game": "baseball",
        "flag_anchor": "  pvp: null,    // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer}",
        "flag_line": "  prizePosted: false, // park prize: posted once per game when YOU beat the CPU",
        "reset_anchor": "function startGame(){\n  G.started = true;\n  G.over = false;",
        "reset_line": "  G.prizePosted = false;",
        "win_anchor": "function endGame(){\n  G.mode = 'over'; G.over = true;",
        "win_post": "  if(!pvpIsOn()&&G.score[HOME]>G.score[AWAY]&&!G.prizePosted){G.prizePosted=true;if(window.ReactNativeWebView)window.ReactNativeWebView.postMessage(JSON.stringify({type:'park_prize_win',game:'baseball',level:1}));}",
    },
    {
        "file": "frontend/components/SoccerHtml.ts",
        "game": "soccer",
        "flag_anchor": "  pvp: null,    // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT}",
        "flag_line": "  prizePosted: false, // park prize: posted once per game when YOU beat the CPU",
        "reset_anchor": "function startGame(){\n  G.started = true; G.over = false; G.half = 1; G.clock = HALF_LEN;",
        "reset_line": "  G.prizePosted = false;",
        "win_anchor": "    const w = G.score[HOME] > G.score[AWAY] ? 'YOU WIN!' : (G.score[HOME] < G.score[AWAY] ? 'MELONHEADS WIN' : 'DRAW!');",
        "win_post": "    if(!pvpIsOn()&&G.score[HOME]>G.score[AWAY]&&!G.prizePosted){G.prizePosted=true;if(window.ReactNativeWebView)window.ReactNativeWebView.postMessage(JSON.stringify({type:'park_prize_win',game:'soccer',level:1}));}",
    },
    {
        "file": "frontend/components/TennisHtml.ts",
        "game": "tennis",
        "flag_anchor": "  pvp: null,    // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer}",
        "flag_line": "  prizePosted: false, // park prize: posted once per game when YOU beat the CPU",
        "reset_anchor": "function startGame(){\n  G.started = true; G.over = false;",
        "reset_line": "  G.prizePosted = false;",
        "win_anchor": "function endSet(winner){\n  SFX.set(); // the big fanfare + applause when the set is won\n  G.over = true;",
        "win_post": "  if(!pvpIsOn()&&winner===HOME&&!G.prizePosted){G.prizePosted=true;if(window.ReactNativeWebView)window.ReactNativeWebView.postMessage(JSON.stringify({type:'park_prize_win',game:'tennis',level:1}));}",
    },
    {
        "file": "frontend/components/OneOnOneHtml.ts",
        "game": "one_on_one",
        "flag_anchor": "  pvp: null,    // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT}",
        "flag_line": "  prizePosted: false, // park prize: posted once per game when YOU beat the CPU",
        "reset_anchor": "function startGame(){\n  G.score = [0, 0];\n  G.over = false;",
        "reset_line": "  G.prizePosted = false;",
        "win_anchor": "function endGame(winner){\n  G.over = true;\n  G.phase = 'over';",
        "win_post": "  if(!pvpIsOn()&&winner===HOME&&!G.prizePosted){G.prizePosted=true;if(window.ReactNativeWebView)window.ReactNativeWebView.postMessage(JSON.stringify({type:'park_prize_win',game:'one_on_one',level:1}));}",
    },
]


def post_marker(game):
    # Full post signature -- the bare game:'x' string also appears in the
    # PvP room-create call, so the type must be part of the match.
    return "type:'park_prize_win',game:'%s'" % game


def patch_game(spec):
    path = Path(spec["file"])
    if not path.exists():
        print("FAIL: %s not found" % spec["file"])
        return False
    src = path.read_text(encoding="utf-8")

    # Already fully applied? Skip this file.
    if POST_TYPE in src and post_marker(spec["game"]) in src:
        print("SKIP: %s already has the park prize post" % spec["game"])
        return "skip"

    # 1. Flag in the G state object.
    if "prizePosted" not in src:
        if src.count(spec["flag_anchor"]) != 1:
            print("FAIL: %s flag anchor not found exactly once" % spec["game"])
            return False
        src = src.replace(spec["flag_anchor"],
                          spec["flag_anchor"] + "\n" + spec["flag_line"], 1)
        print("OK: %s prizePosted flag added to G" % spec["game"])
    else:
        print("OK: %s prizePosted flag already present" % spec["game"])

    # 2. Reset in newGame/startGame so a rematch can pay again.
    if src.count(spec["reset_line"]) != 1:
        if src.count(spec["reset_anchor"]) != 1:
            print("FAIL: %s reset anchor not found exactly once" % spec["game"])
            return False
        src = src.replace(spec["reset_anchor"],
                          spec["reset_anchor"] + "\n" + spec["reset_line"], 1)
        print("OK: %s prizePosted reset added" % spec["game"])
    else:
        print("OK: %s prizePosted reset already present" % spec["game"])

    # 3. Guarded win post at the PvC win point.
    if post_marker(spec["game"]) not in src:
        if src.count(spec["win_anchor"]) != 1:
            print("FAIL: %s win anchor not found exactly once" % spec["game"])
            return False
        src = src.replace(spec["win_anchor"],
                          spec["win_anchor"] + "\n" + spec["win_post"], 1)
        print("OK: %s win post added" % spec["game"])
    else:
        print("OK: %s win post already present" % spec["game"])

    # Verify before writing.
    if post_marker(spec["game"]) not in src or "prizePosted" not in src:
        print("FAIL: %s verification failed after patch" % spec["game"])
        return False
    path.write_text(src, encoding="utf-8")
    return True


def main():
    results = []
    for spec in GAMES:
        results.append(patch_game(spec))
    if all(r == "skip" for r in results):
        print("PARK_PRIZE_HTML_ALREADY_APPLIED")
        return 0
    if all(r is True or r == "skip" for r in results):
        print(MARKER)
        return 0
    print("PARK_PRIZE_HTML_FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
