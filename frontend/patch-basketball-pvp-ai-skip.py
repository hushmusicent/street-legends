#!/usr/bin/env python3
"""Street Legends Basketball PvP: never let the AI drive a synced opponent.

Progress so far: scores now match on both phones (2-2), so the state IS
flowing. What remains is flapping: the sync connects, then the computer
takes over the other team, then it tries to sync again.

Cause: updateAI only skips the ONE player named by pvpOppCtrl(), which
reads G.pvp.oppMe. When the opponent switches control (e.g. after a pass)
the new oppMe has not arrived yet, so oppMe still points at the OLD
player and the AI drives the NEW controlled player for a beat -- the
"computer takes over". If oppMe is ever cleared, the fallback (nearest
the ball) can pick the wrong player too.

Fix (sync only; does NOT touch room create/join/leave, the code format,
or the states structure): in updateAI, ALSO skip any opponent-team player
that has a sync target (tx/tz). pvpApplyState sets tx/tz ONLY on the
opponent's controlled player (from st.me), never on their teammate, so
this protects the human-driven player even when oppMe is stale, while
the AI still drives the opponent's teammate (no tx/tz) as before.

Run from /app: python3 frontend/patch-basketball-pvp-ai-skip.py
Idempotent: a full re-run prints BASKETBALL_PVP_AI_SKIP_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_PVP_AI_SKIP_OK"

# The AI skip inside updateAI -- loose on spacing, anchored on the exact
# two lines that already exist.
AI_SKIP_RE = re.compile(
    r"(var oppCtrl\s*=\s*pvpIsOn\(\)\s*\?\s*pvpOppCtrl\(\)\s*:\s*null;\s*"
    r"G\.players\.forEach\(function\(p,i\)\{\s*"
    r"if\(i===G\.user\) return;\s*"
    r"if\(oppCtrl&&p===oppCtrl\) return;)",
    re.DOTALL,
)
AI_SKIP_NEW = (
    "\\1\n"
    "    // PVP SYNC: never let the AI drive an opponent player that has a\n"
    "    // sync target -- pvpApplyState sets tx/tz only on the human-driven\n"
    "    // player, so this holds even when oppMe is stale after a switch.\n"
    "    if(pvpIsOn()&&G.players[G.user]&&p.team!==G.players[G.user].team&&typeof p.tx==='number'&&typeof p.tz==='number') return;"
)

def main():
    if not BB.exists():
        print("ERROR: BasketballHtml.ts not found (run from /app)")
        sys.exit(1)
    src = BB.read_text()
    if "PVP SYNC: never let the AI drive" in src:
        print("BASKETBALL_PVP_AI_SKIP_ALREADY_APPLIED")
        return
    m = AI_SKIP_RE.search(src)
    if not m:
        print("ERROR: updateAI skip anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m.start()] + m.expand(AI_SKIP_NEW) + src[m.end():]
    BB.write_text(src)
    cur = BB.read_text()
    if "PVP SYNC: never let the AI drive" not in cur:
        print("ERROR: PvP AI-skip patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
