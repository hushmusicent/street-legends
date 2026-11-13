#!/usr/bin/env python3
"""Street Legends Basketball PvP: no computer at all in PvP mode.

User: "A little better but computer still takes over. Computer should
not be there."

The earlier AI-skip patch only protected the opponent's controlled
player. The AI still drives the other players (teammates, and the
opponent's teammate), so a computer is still in the game and can take
a player over. In PvP both teams are human -- there should be no AI
driving anyone.

Fix (PvP only; PvC is untouched): at the top of updateAI, return
immediately when pvpIsOn(). updateAI only moves/decides for AI
players (shoot/dunk/steal/defend targets); it does no ball physics,
score, or timer work, so skipping it in PvP is safe. The human
controls their player and switches to their teammate as needed; the
opponent does the same. No computer anywhere in PvP.

Run from /app: python3 frontend/patch-basketball-pvp-no-ai.py
Idempotent: a full re-run prints BASKETBALL_PVP_NO_AI_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_PVP_NO_AI_OK"

AI_TOP_RE = re.compile(
    r"(function updateAI\(dt\)\{\s*)"
    r"(const bh=holder\(\);)",
    re.DOTALL,
)
AI_TOP_NEW = (
    "\\1"
    "  // PVP NO AI: in PvP both teams are human -- the computer must not\n"
    "  // drive any player. (PvC is untouched; this only fires in PvP.)\n"
    "  if(pvpIsOn()) return;\n"
    "  \\2"
)

def main():
    if not BB.exists():
        print("ERROR: BasketballHtml.ts not found (run from /app)")
        sys.exit(1)
    src = BB.read_text()
    if "PVP NO AI: in PvP both teams are human" in src:
        print("BASKETBALL_PVP_NO_AI_ALREADY_APPLIED")
        return
    m = AI_TOP_RE.search(src)
    if not m:
        print("ERROR: updateAI top anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m.start()] + m.expand(AI_TOP_NEW) + src[m.end():]
    BB.write_text(src)
    cur = BB.read_text()
    if "PVP NO AI: in PvP both teams are human" not in cur:
        print("ERROR: PvP no-AI patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
