#!/usr/bin/env python3
"""Read-only PvP audit diag for ALL house games. Prints only, changes
nothing. Run from /app (or pass the root).

For each game (darts, cards, dominoes, chess_checkers, texas_holdem,
scrabble, plus pool as a control) it prints:
 1. live server.py room route decorators for that game + whether its
    active-room lookup exists yet,
 2. whether const API_BASE / CC_API_BASE / TH_API_BASE exists in
    frontend/app/(tabs)/index.tsx,
 3. each game's page-config fallback literal (the line the identity fix
    must replace at render),
 4. counts: REJOIN ROOM buttons and CHAT headers in index.tsx.
This settles, before any frontend patching, whether live stripped /api,
whether pool's API_BASE const already covers the other modals, and the
exact fallback strings to bake over."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SRV = ROOT / "backend/server.py"
IDX = ROOT / "frontend/app/(tabs)/index.tsx"

GAMES = [
    ("pool", "pool", "POOL_PVP"),
    ("darts", "dart", "DART_PVP"),
    ("cards", "card", "CARD_PVP"),
    ("dominoes", "domino", "DOMINO_PVP"),
    ("chess_checkers", "chess_checkers", "CHESS_CHECKERS_PVP"),
    ("texas_holdem", "texas_holdem", "TEXAS_HOLDEM_ROOM"),
    ("scrabble", "scrabble", "SCRABBLE_PVP"),
]

def main():
    print("PVP_ALL_DIAG_OK")
    if SRV.exists():
        slines = SRV.read_text(errors="ignore").split("\n")
        for name, key, _ in GAMES:
            routes = ["%d: %s" % (i + 1, ln.strip()[:150]) for i, ln in enumerate(slines)
                      if re.search(r"@\w+\.(get|post)\(", ln) and "rooms" in ln and key in ln]
            active = any("rooms/active" in ln and key in ln for ln in slines)
            print("--- server %s: routes=%d active_lookup=%s ---" % (name, len(routes), active))
            for r in routes[:8]:
                print("  " + r)
    else:
        print("backend/server.py NOT FOUND")
    if not IDX.exists():
        print("frontend/app/(tabs)/index.tsx NOT FOUND")
        return 0
    ilines = IDX.read_text(errors="ignore").split("\n")
    for const in ("API_BASE", "CC_API_BASE", "TH_API_BASE"):
        found = ["%d: %s" % (i + 1, ln.strip()[:150]) for i, ln in enumerate(ilines)
                 if re.search(r"(const|let|var)\s+%s\s*=" % const, ln)]
        print("--- const %s: %s ---" % (const, found[0] if found else "NOT FOUND"))
    for name, _, cfg in GAMES:
        fb = ["%d: %s" % (i + 1, ln.strip()[:200]) for i, ln in enumerate(ilines)
              if ("window.%s" % cfg) in ln and "||" in ln]
        print("--- %s fallback: %s ---" % (name, fb[0] if fb else "NOT FOUND"))
    src = "\n".join(ilines)
    print("--- REJOIN ROOM buttons in index.tsx: %d ---" % src.count("REJOIN ROOM"))
    print("--- CHAT headers in index.tsx: %d ---" % src.count("}}>CHAT</Text>"))
    return 0

if __name__ == "__main__":
    sys.exit(main())
