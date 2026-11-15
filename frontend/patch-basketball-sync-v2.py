#!/usr/bin/env python3
"""Street Legends Basketball PvP sync fix v2.

Problem: in a 2v2 game, the player moves on their phone but the opponent
does not move on the other phone. The backend state flow is proven live
(create/join/state/get all work), so the break is in the game. The game
posts its position every 0.1s and polls every 100ms, but the post's reply
(the full room, including the opponent's latest state) is thrown away,
so each phone only learns the opponent's position on the next poll --
a full round trip behind. On a slow connection the poll also skips while
one is in flight, so updates stack up and the opponent appears frozen.

Fix (sync-only; does NOT touch room create/join/leave, the code format,
or the states structure):
  1. In pvpPostState, use the returned room to apply the opponent's state
     immediately (reply-as-poll). Every position post now also carries
     the opponent's latest position back, halving the delay.
  2. In pvpPollOnce, allow up to 2 polls in flight instead of skipping,
     so a slow poll cannot starve updates.

v2: regex anchors, so it applies whether or not the Emergent agent's
earlier sync edit is still present, and regardless of line-split
formatting (e.g. a lone ';' on its own line).

Run from /app: python3 frontend/patch-basketball-sync-v2.py
Idempotent: a full re-run prints BASKETBALL_SYNC_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_SYNC_OK"

# --- 1. reply-as-poll in pvpPostState ---
# Matches the plain return (GitHub version and the line-split variant),
# but NOT a version that already applies the reply.
POST_RE = re.compile(
    r"return pvpPost\('/'\+G\.pvp\.code\+'/state',\{player_id:who\.id,state:st\}\)"
    r"\.then\(function\(r\)\{\s*pv\.posting=false;\s*return r;\s*\}\);",
    re.DOTALL,
)
POST_NEW = (
    "return pvpPost('/'+G.pvp.code+'/state',{player_id:who.id,state:st}).then(function(r){\n"
    "    pv.posting=false;\n"
    "    // SYNC: the backend returns the full room. Use it right away to apply\n"
    "    // the opponent's latest state instead of waiting for the next poll.\n"
    "    try {\n"
    "      if (r && r.states) {\n"
    "        var oRole = G.pvp.role === 'host' ? 'guest' : 'host';\n"
    "        var oSt = r.states[oRole] || null;\n"
    "        if (oSt && typeof oSt.seq === 'number' && (oSt.seq > G.pvp.oppSeq || oSt.seq < G.pvp.oppSeq - 50)) {\n"
    "          G.pvp.oppSeq = oSt.seq;\n"
    "          pvpApplyState(oSt);\n"
    "        }\n"
    "        if (r.status === 'finished' && G.mode !== 'over') { pvpStopPoll(); G.mode = 'over'; }\n"
    "      }\n"
    "    } catch (e) {}\n"
    "    return r;\n"
    "  });"
)

# --- 2. allow up to 2 polls in parallel ---
POLL_RE = re.compile(
    r"function pvpPollOnce\(\)\{\s*if\(!pvpIsOn\(\)\) return;\s*"
    r"if\(G\.pvp\.polling\) return; // previous poll still in flight\s*"
    r"var code=G\.pvp\.code;\s*"
    r"var pv=G\.pvp; pv\.polling=true;\s*"
    r"pvpGet\(code\)\.then\(function\(room\)\{\s*"
    r"pv\.polling=false;",
    re.DOTALL,
)
POLL_NEW = (
    "function pvpPollOnce(){\n"
    "  if(!pvpIsOn()) return;\n"
    "  // SYNC: allow up to 2 polls in flight so a slow poll cannot starve\n"
    "  // updates (a single in-flight poll used to make every later poll skip).\n"
    "  if((G.pvp.pollCount || 0) >= 2) return;\n"
    "  var code=G.pvp.code;\n"
    "  var pv=G.pvp; pv.pollCount=(pv.pollCount || 0)+1;\n"
    "  pvpGet(code).then(function(room){\n"
    "    pv.pollCount=Math.max(0,(pv.pollCount || 1)-1);"
)

def main():
    if not BB.exists():
        print("ERROR: BasketballHtml.ts not found (run from /app)")
        sys.exit(1)
    src = BB.read_text()
    if "pollCount" in src and "pvpApplyState(oSt)" in src:
        print("BASKETBALL_SYNC_ALREADY_APPLIED")
        return
    # If the agent's pvpApplyFromRoom is present, it already does the
    # reply-as-poll; only add the parallel-poll part.
    agent_present = "pvpApplyFromRoom" in src
    changed = False
    if not agent_present:
        m = POST_RE.search(src)
        if not m:
            print("ERROR: pvpPostState return anchor not found (file changed in an unexpected way)")
            sys.exit(1)
        src = src[:m.start()] + POST_NEW + src[m.end():]
        changed = True
    else:
        print("NOTE: agent reply-as-poll (pvpApplyFromRoom) already present; keeping it, adding parallel polls only")
    m2 = POLL_RE.search(src)
    if not m2:
        if "pollCount" in src:
            print("NOTE: parallel-poll part already present")
        else:
            print("ERROR: pvpPollOnce anchor not found (file changed in an unexpected way)")
            sys.exit(1)
    else:
        src = src[:m2.start()] + POLL_NEW + src[m2.end():]
        changed = True
    if not changed:
        print("BASKETBALL_SYNC_ALREADY_APPLIED")
        return
    BB.write_text(src)
    cur = BB.read_text()
    if "pollCount" not in cur:
        print("ERROR: sync patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
