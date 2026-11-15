#!/usr/bin/env python3
"""Street Legends Basketball PvP: sync the out-of-bounds reset.

User: "No when I go out of bounds it goes off sync."

Cause: outOfBounds() is purely local. It sets G.nextPoss and, after a
0.9s pause, resetPositions() teleports every player and the ball. But
each phone detects the ball crossing the line at a slightly different
moment (sync lag), so one phone resets while the other has not yet --
or one never resets because the ball was synced back inbounds first.
The two games then diverge (different positions/possession).

Fix (PvP only; PvC untouched): broadcast the out-of-bounds as an event.
  1. outOfBounds() now posts {ev:{k:'oob', team}} via pvpPostState, so
     the other phone learns about it at once.
  2. pvpReceiveEv() handles k==='oob' BEFORE the team filter (this is a
     game event, not a player action) by applying the same pause +
     nextPoss locally. The receiver does NOT re-post, so there is no
     event loop. If both phones detect it locally, both set the same
     nextPoss -- harmless and idempotent.

Run from /app: python3 frontend/patch-basketball-pvp-oob.py
Idempotent: a full re-run prints BASKETBALL_PVP_OOB_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_PVP_OOB_OK"

# 1. outOfBounds() posts the event after setting pause/nextPoss.
OOB_RE = re.compile(
    r"(function outOfBounds\(team\)\{\s*"
    r"callout\('OUT OF BOUNDS',''\);\s*"
    r"G\.pause=0\.9; G\.afterPause=true; G\.nextPoss=team;\s*)"
    r"(\})",
    re.DOTALL,
)
OOB_NEW = (
    "\\1"
    "  // PVP OOB: broadcast so the other phone resets to the same possession.\n"
    "  if(pvpIsOn()) pvpPostState({ev:{k:'oob',team:team}});\n"
    "\\2"
)

# 2. pvpReceiveEv() handles 'oob' before the team filter.
EV_RE = re.compile(
    r"(function pvpReceiveEv\(ev\)\{\s*"
    r"// Apply one event posted by the opponent\. Only events from the OTHER\s*"
    r"// team are applied \(my own events are already applied locally\)\.\s*"
    r"if\(!ev\|\|typeof ev\.team!=='number'\|\|ev\.team===G\.myTeam\) return;)",
    re.DOTALL,
)
EV_NEW = (
    "\\1\n"
    "  // PVP OOB: out of bounds is a game event, not a player action --\n"
    "  // apply it on both phones (before the team filter) so both reset\n"
    "  // to the same possession. No re-post, so no event loop.\n"
    "  if(ev&&ev.k==='oob'&&typeof ev.team==='number'){ callout('OUT OF BOUNDS',''); G.pause=0.9; G.afterPause=true; G.nextPoss=ev.team; return; }"
)

def main():
    if not BB.exists():
        print("ERROR: BasketballHtml.ts not found (run from /app)")
        sys.exit(1)
    src = BB.read_text()
    if "PVP OOB: broadcast" in src and "PVP OOB: out of bounds is a game event" in src:
        print("BASKETBALL_PVP_OOB_ALREADY_APPLIED")
        return
    m = OOB_RE.search(src)
    if not m:
        print("ERROR: outOfBounds anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m.start()] + m.expand(OOB_NEW) + src[m.end():]
    m2 = EV_RE.search(src)
    if not m2:
        print("ERROR: pvpReceiveEv anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m2.start()] + m2.expand(EV_NEW) + src[m2.end():]
    BB.write_text(src)
    cur = BB.read_text()
    if "PVP OOB: broadcast" not in cur or "PVP OOB: out of bounds is a game event" not in cur:
        print("ERROR: PvP OOB patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
