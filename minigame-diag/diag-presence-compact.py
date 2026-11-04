#!/usr/bin/env python3
"""READ-ONLY compact check: is the presence code actually in live /app?
Run in /app: python3 minigame-diag/diag-presence-compact.py
Output is meant to fit ONE phone screenshot."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"
SRV = ROOT / "backend/server.py"

def show(title, path, patterns, cap=10):
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
            if n >= cap:
                print(f"(capped at {cap})")
                break
    if n == 0:
        print("NONE FOUND")

show("INDEX presence state/effect", IDX,
     [r"houseOccupants", r"houseEnterPresence", r"houseLeavePresence",
      r"houseHeartbeatPresence", r"getHousePresence"])
show("INDEX presence row", IDX, [r"In this house now"])
show("INDEX guest flag", IDX, [r"isGuestVisit"])
show("API presence functions", API,
     [r"houseEnterPresence", r"houseLeavePresence",
      r"houseHeartbeatPresence", r"getHousePresence"])
show("SERVER presence endpoints", SRV,
     [r"houses/.*enter", r"houses/.*leave", r"houses/.*heartbeat",
      r"houses/.*presence", r"house_presence"])
print("PRESENCE_COMPACT_OK")
