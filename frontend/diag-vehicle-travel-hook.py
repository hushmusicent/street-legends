#!/usr/bin/env python3
"""Street Legends READ-ONLY follow-up diagnostic: WHERE does the app
compute travel distance, so vehicle durability loss (1/km) can hook
there?

Already known (from diag-vehicle-travel.py):
  - DURABILITY_LOSS["vehicle"] = per_use 20, per_territory 30.
  - apply_vehicle_durability_loss(player_id, action_type) exists.
  - equipment_durability["vehicle"] holds current durability.
  - Haversine distance helper is at backend/server.py:1854.
  - Steps -> distance_km is at backend/server.py:10024.

Still needed: the haversine helper's name + who calls it (the GPS
location-update path), and the location-update endpoint itself.
This prints exactly that, and nothing else, so it fits on screen.

Changes NOTHING. Run from repo root:
  python3 frontend/diag-vehicle-travel-hook.py
Prints DIAG_VEHICLE_TRAVEL_HOOK_OK at the end.
"""
import re
import sys
from pathlib import Path


def main():
    p = Path("backend/server.py")
    if not p.exists():
        print("ERROR: backend/server.py not found. Run from repo root.")
        return 1
    lines = p.read_text().split("\n")
    # 1. Haversine def: search backwards from line 1854 for "def ".
    def_idx = None
    for i in range(1853, max(0, 1853 - 15), -1):
        if lines[i].lstrip().startswith("def "):
            def_idx = i
            break
    name = None
    if def_idx is not None:
        m = re.match(r"\s*def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", lines[def_idx])
        name = m.group(1) if m else None
        print("HAVERSINE DEF line %d: %s" % (def_idx + 1, lines[def_idx].strip()))
        print("HAVERSINE NAME: %s" % name)
    else:
        print("HAVERSINE DEF: not found near line 1854")
    # 2. Callers of the haversine helper (skip its own def line).
    if name:
        print("--- callers of %s ---" % name)
        shown = 0
        for i, ln in enumerate(lines):
            if i == def_idx:
                continue
            if re.search(r"\b%s\s*\(" % re.escape(name), ln):
                print("server.py:%d: %s" % (i + 1, ln.strip()[:120]))
                shown += 1
                if shown >= 10:
                    break
        if shown == 0:
            print("(no callers found)")
    # 3. Location-update endpoints / handlers.
    print("--- location update endpoints ---")
    shown = 0
    for i, ln in enumerate(lines):
        low = ln.lower()
        if ("location" in low or "position" in low) and (
            "router.post" in low or "router.put" in low or "router.patch" in low
            or "def update" in low or "def set_" in low
        ):
            print("server.py:%d: %s" % (i + 1, ln.strip()[:120]))
            shown += 1
            if shown >= 10:
                break
    if shown == 0:
        print("(no location-update endpoint lines found)")
    print("DIAG_VEHICLE_TRAVEL_HOOK_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
