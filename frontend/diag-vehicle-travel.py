#!/usr/bin/env python3
"""Street Legends READ-ONLY diagnostic for the vehicle travel-damage
feature (confirmed spec 2026-11-01):
  - Vehicle loses 1 durability per km traveled.
  - At 0 durability it needs repairs.
  - At 0 durability, enemies attack 2x before the player attacks.

Finds the code this feature must touch, so the patch anchors on the
real names instead of guessing:
  1. Vehicle durability / equipped vehicle slot.
  2. Travel / distance tracking (how movement is measured).
  3. Combat attack order (where the enemy / player attack turns run).
  4. Repair (existing repair endpoints / UI for gear).

Prints file:line plus the matching line itself (truncated), capped
per category so the output fits on a phone screenshot.

Changes NOTHING. Run from repo root:
  python3 frontend/diag-vehicle-travel.py
Prints DIAG_VEHICLE_TRAVEL_OK at the end.
"""
import glob
import sys

CATEGORIES = [
    ("VEHICLE", ["stolen motorcycle", "vehicle_durability", "vehicle durability",
                 "equipped_vehicle", "vehicle\":", "'vehicle'", '"vehicle"']),
    ("TRAVEL", ["haversine", "distance_km", "distance_m", "total_distance",
                "distance_traveled", "location_update", "onLocationUpdate"]),
    ("COMBAT", ["enemy_attack", "enemy attacks", "player_attack", "player attacks",
                "attack_order", "turn_order", "enemy_turn", "player_turn"]),
    ("REPAIR", ["repair", "Repair"]),
]


def main():
    files = sorted(glob.glob("backend/*.py") +
                   glob.glob("frontend/app/**/*.tsx", recursive=True) +
                   glob.glob("frontend/components/*.tsx") +
                   glob.glob("frontend/services/*.ts"))
    for title, terms in CATEGORIES:
        print("=" * 60)
        print(title)
        shown = 0
        for path in files:
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.read().split("\n")
            except FileNotFoundError:
                continue
            for i, ln in enumerate(lines):
                low = ln.lower()
                if any(t.lower() in low for t in terms):
                    print("%s:%d: %s" % (path, i + 1, ln.strip()[:120]))
                    shown += 1
                    if shown >= 15:
                        break
            if shown >= 15:
                break
        if shown == 0:
            print("(no matches)")
    print("DIAG_VEHICLE_TRAVEL_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
