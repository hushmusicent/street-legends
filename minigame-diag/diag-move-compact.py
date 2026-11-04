#!/usr/bin/env python3
"""READ-ONLY compact check: which item-move controls exist, and are they
guest-gated? Run in /app: python3 minigame-diag/diag-move-compact.py
Output is meant to fit ONE phone screenshot."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
FRONT = [ROOT / "frontend/app/(tabs)/index.tsx",
         ROOT / "frontend/app/(tabs)/shop.tsx"]
SRV = ROOT / "backend/server.py"

def grep_file(path, patterns, cap=15, label=""):
    print(f"--- {label} ---")
    if not path.exists():
        print(f"WARNING: missing {path}")
        return []
    lines = path.read_text(errors="ignore").splitlines()
    hits = []
    for i, ln in enumerate(lines, 1):
        if any(re.search(p, ln, re.I) for p in patterns):
            print(f"{path.name}:{i}: {ln.strip()[:150]}")
            hits.append((i, ln))
            if len(hits) >= cap:
                print(f"(capped at {cap} hits)")
                break
    if not hits:
        print("NONE FOUND")
    return hits

for f in FRONT:
    grep_file(f, [r"moveHouseItem", r"handleMove", r"onMove", r"reorder",
                   r"drag", r"MOVE ITEM", r"Move item", r"moveItem"],
              label=f"FRONT move controls in {f.name}")

print("--- FRONT guest gates ---")
for f in FRONT:
    grep_file(f, [r"isGuestVisit"], cap=8, label=f"guest gate in {f.name}")

grep_file(SRV, [r"def .*move", r"move-to-inventory", r"move_house_item"],
          label="BACKEND move endpoints")

# NOTE: no automatic GATED/UNGATED verdict here — a nearby isGuestVisit line
# in a DIFFERENT function is not a gate. Compare the move-handler lines
# above with the guest-gate lines: a move handler whose own body has no
# isGuestVisit check is ungated.
print("MOVE_DIAG_COMPACT_OK")
