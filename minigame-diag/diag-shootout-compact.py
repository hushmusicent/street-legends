#!/usr/bin/env python3
"""READ-ONLY compact shootout check: prints ONLY the decisive lines.
Run: python3 minigame-diag/diag-shootout-compact.py  (in /app)
Output is meant to fit ONE phone screenshot."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SIM = ROOT / "frontend/app/shootout-simulator.tsx"
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
SRV = ROOT / "backend/server.py"

def show(title, path, patterns, max_hits=12):
    print(f"--- {title} ---")
    if not path.exists():
        print(f"WARNING: missing {path}")
        return
    lines = path.read_text(errors="ignore").splitlines()
    n = 0
    for i, ln in enumerate(lines, 1):
        if any(re.search(p, ln) for p in patterns):
            print(f"{path.name}:{i}: {ln.strip()[:150]}")
            n += 1
            if n >= max_hits:
                break
    if n == 0:
        print("NONE FOUND")

show("SIM params (does it read gameId?)", SIM,
     [r"useLocalSearchParams", r"gameId[?:]"])
show("SIM start: setGameId + timer", SIM,
     [r"setGameId\(", r"setInterval", r"endGame\(\)", r"startGame"])
show("SIM endGame guard + complete + refresh", SIM,
     [r"if \(gameId", r"apiCompleteShootout", r"getPlayer\(playerId\)", r"setPlayer\(updatedPlayer\)"])
show("MAP handler passes gameId?", IDX,
     [r"handleStartShootout", r"gameId: gameData", r"shootout-simulator"])
show("SERVER complete: cooldown set + global", SRV,
     [r"shootout_cooldowns", r"minigame_global_cooldown"])
show("SERVER start: global check", SRV,
     [r"def start_shootout", r"def complete_shootout", r"def start_standalone_shootout"])
print("SHOOTOUT_COMPACT_OK")
