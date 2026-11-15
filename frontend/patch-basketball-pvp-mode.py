#!/usr/bin/env python3
"""Street Legends Basketball PvP mode fix.

Bug: the room create/join works (the code works), but the game starts as
"YOU vs CPU" in PvC mode instead of PvP. The poll auto-start only fires
when G.mode is not 'play', so if the game was already started (PvC) before
the guest joined, it never switches to PvP. Both phones then play separate
PvC games (different scores/clocks) and the "opponent" is the CPU on both.

Fix (sync/mode only; does NOT touch room create/join/leave, the code
format, or the states structure):
  1. In startGame(), remember that the game was started in PvP mode
     (G.pvp.started = true) when pvpIsOn().
  2. In pvpPollOnce, the host auto-start now also fires when the guest
     has joined but the game was started in PvC mode (mode is 'play'
     but G.pvp.started is not set), restarting it in PvP mode.
  3. When PvP starts, post the opponent's name to the app so the modal
     title can show "YOU vs <name>" instead of "YOU vs CPU".

Run from /app: python3 frontend/patch-basketball-pvp-mode.py
Idempotent: a full re-run prints BASKETBALL_PVP_MODE_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_PVP_MODE_OK"

# --- 1. remember PvP start in startGame() ---
START_RE = re.compile(
    r"(function startGame\(\)\{\s*"
    r"\$\('startOverlay'\)\.classList\.add\('hidden'\);\s*"
    r"\$\('endOverlay'\)\.classList\.add\('hidden'\);\s*)",
    re.DOTALL,
)
START_NEW = (
    "\\1"
    "  if(pvpIsOn()&&G.pvp) G.pvp.started=true; // PVP MODE: remember this start was PvP\n"
)

# --- 2. host auto-start: also restart if game is playing but not in PvP ---
HOST_RE = re.compile(
    r"(if \(pvpWagerReady\(room, G\.pvp\.round \|\| 0\) && G\.pvp\.role==='host'&&room\.guest_id&&)"
    r"G\.mode!=='play'&&G\.mode!=='over'\)\{",
    re.DOTALL,
)
HOST_NEW = (
    "\\1"
    "(G.mode!=='play'||!G.pvp.started)&&G.mode!=='over'){ // PVP MODE: restart if it started as PvC\n"
    "      if(G.mode==='play'&&!G.pvp.started){ G.pvp.syncStart=true; }"
)

# --- 3. post opponent name when PvP starts (host) ---
# After the host sets oppName and before startGame(), post it to the app.
HOST_NAME_RE = re.compile(
    r"(G\.pvp\.oppName=room\.guest_name\|\|'Opponent';\s*)",
    re.DOTALL,
)
HOST_NAME_NEW = (
    "\\1"
    "      if(window.ReactNativeWebView) window.ReactNativeWebView.postMessage(JSON.stringify({type:'pvp_opponent',name:G.pvp.oppName}));\n"
)

def main():
    if not BB.exists():
        print("ERROR: BasketballHtml.ts not found (run from /app)")
        sys.exit(1)
    src = BB.read_text()
    if "G.pvp.started" in src and "pvp_opponent" in src:
        print("BASKETBALL_PVP_MODE_ALREADY_APPLIED")
        return
    changed = False
    m = START_RE.search(src)
    if not m:
        print("ERROR: startGame anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m.start()] + m.expand(START_NEW) + src[m.end():]
    changed = True
    m2 = HOST_RE.search(src)
    if not m2:
        print("ERROR: host auto-start anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m2.start()] + m2.expand(HOST_NEW) + src[m2.end():]
    changed = True
    m3 = HOST_NAME_RE.search(src)
    if m3:
        src = src[:m3.start()] + m3.expand(HOST_NAME_NEW) + src[m3.end():]
        changed = True
    else:
        print("NOTE: oppName anchor not found; skipping title post (mode fix still applied)")
    BB.write_text(src)
    cur = BB.read_text()
    if "G.pvp.started" not in cur:
        print("ERROR: PvP mode patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
