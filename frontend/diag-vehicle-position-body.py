#!/usr/bin/env python3
"""Street Legends READ-ONLY diagnostic (last piece before the vehicle
travel-damage patch): the full body of update_player_position, so
the 1/km vehicle durability hook lands in the right place.

Prints backend/server.py from the update_player_position def
(around line 2488) through to the next top-level def, with line
numbers. Scroll and screenshot it in parts if it does not fit.

Changes NOTHING. Run from repo root:
  python3 frontend/diag-vehicle-position-body.py
Prints DIAG_VEHICLE_POSITION_BODY_OK at the end.
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
    start = None
    for i, ln in enumerate(lines):
        if "def update_player_position" in ln:
            start = i
            break
    if start is None:
        print("update_player_position not found in backend/server.py")
        print("DIAG_VEHICLE_POSITION_BODY_OK")
        return 0
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if re.match(r"^(async def |def |@)", lines[j]):
            end = j
            break
    print("update_player_position lines %d-%d:" % (start + 1, end))
    for k in range(start, min(end, start + 120)):
        print("%5d: %s" % (k + 1, lines[k]))
    print("DIAG_VEHICLE_POSITION_BODY_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
