#!/usr/bin/env python3
"""READ-ONLY compact check: pool room routes live in /app vs what the
frontend calls. Run in /app: python3 minigame-diag/diag-pool-compact.py
Output is meant to fit ONE phone screenshot."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SRV = ROOT / "backend/server.py"

def show(title, path, patterns, cap=20):
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

show("SERVER pool route decorators", SRV,
     [r"@api_router\.(post|get).*pool", r"@app\.(post|get).*pool"])
show("SERVER pool room defs", SRV,
     [r"def .*pool.*room", r"def .*create.*pool", r"pool_rooms"])
show("SERVER pool create/join signatures", SRV,
     [r"def (create|join)_pool_room", r"def pool_room"])
show("FRONTEND pool create/join calls", ROOT / "frontend/app/(tabs)/index.tsx",
     [r"/api/pool/rooms/create", r"/api/pool/rooms/join",
      r"showNotLive", r"res\.status === 404"])
print("POOL_COMPACT_OK")
