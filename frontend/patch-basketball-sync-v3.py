#!/usr/bin/env python3
"""Street Legends Basketball PvP sync fix v3 -- parallel polls only.

Line 299 of /app BasketballHtml.ts already calls pvpApplyFromRoom(r) on
every state-post reply (the agent's reply-as-poll is in and wired), so
that part is DONE and this patch does not touch it. What is still missing
is the second half: pvpPollOnce still skips whenever one poll is in
flight, so on a slow connection updates stack up and the opponent
appears frozen.

Fix (sync-only; does NOT touch room create/join/leave, the code format,
or the states structure): allow up to 2 polls in flight instead of
skipping, so a slow poll cannot starve updates.

Run from /app: python3 frontend/patch-basketball-sync-v3.py
Idempotent: a full re-run prints BASKETBALL_SYNC_V3_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_SYNC_V3_OK"

# Matches the single-poll guard + poll start, tolerating the agent's
# formatting and any pvpApplyFromRoom wiring elsewhere in the file.
POLL_RE = re.compile(
    r"if\(G\.pvp\.polling\) return;[^\n]*\n"
    r"\s*var code=G\.pvp\.code;\s*\n"
    r"\s*var pv=G\.pvp; pv\.polling=true;\s*\n"
    r"\s*pvpGet\(code\)\.then\(function\(room\)\{\s*\n"
    r"\s*pv\.polling=false;",
    re.DOTALL,
)
POLL_NEW = (
    "if((G.pvp.pollCount || 0) >= 2) return; // SYNC: allow 2 polls in flight\n"
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
    if "pollCount" in src:
        print("BASKETBALL_SYNC_V3_ALREADY_APPLIED")
        return
    m = POLL_RE.search(src)
    if not m:
        print("ERROR: pvpPollOnce anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m.start()] + POLL_NEW + src[m.end():]
    BB.write_text(src)
    cur = BB.read_text()
    if "pollCount" not in cur:
        print("ERROR: sync patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
