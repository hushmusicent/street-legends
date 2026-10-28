"""Street Legends backend: show only the nearest 8 missions on the map.
Run from repo root: python3 backend/patch-mission-cap.py
Idempotent - safe to re-run.

WHY the map drowns in missions: missions last 24 hours, and every time
the player enters a spot with fewer than 3 missions within 1000m, the
game tops them up to 5 more. After a day of driving around one metro
area, dozens of unexpired, unaccepted missions from many different
spawn points all sit inside the visible map — and generate_missions
returned ALL of them (up to 50) with no cap. Hence 25 phone icons
stacked on one screen.

FIX: sort nearby missions by distance and return only the nearest 8.
The rest still exist in the DB for their full 24h and appear on later
refreshes as the player clears the near ones — gameplay is untouched,
only the clutter is gone. Does NOT change expiry, spawn rates, or
rewards.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OLD = """    if len(nearby) >= 3:
        return nearby"""
NEW = """    def _dist_to_player(doc):
        try:
            return calculate_distance(position, Position(**doc["position"]))
        except Exception:
            return 1e9
    # Show only the nearest 8 so the map doesn't drown in a day's worth of
    # unexpired missions (they last 24h and pile up as you drive around).
    nearby.sort(key=_dist_to_player)
    nearby = nearby[:8]

    if len(nearby) >= 3:
        return nearby"""


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "/missions/generate" not in src:
        print("ERROR: missions endpoint not found.")
        sys.exit(1)
    if "nearby = nearby[:8]" in src:
        print("SKIP: mission display cap already present")
    elif src.count(OLD) == 1:
        src = src.replace(OLD, NEW, 1)
        print("OK: missions capped to nearest 8 on the map")
    else:
        print(f"WARNING: anchor matched {src.count(OLD)}x — skipping")
    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("MISSION_CAP_OK")


if __name__ == "__main__":
    main()
