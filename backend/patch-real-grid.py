"""Street Legends backend: search only the territory grid, not the whole city.
Run from repo root: python3 backend/patch-real-grid.py
Idempotent - safe to re-run.

WHY: Overpass fetches used a 5 km radius around the player — about 78 sq km
of city to scan on every new area, which is a big reason the queries take
40-120s+ and time out. But the territory grid the player actually sees is
~5x5 cells of 338 m each, about 1.7 km across. Searching 27x more ground
than the player can see buys nothing and costs everything in speed.

FIX: all four place fetchers (banks, restaurants, nightclubs, gas
stations) now search a 2 km radius (~12.6 sq km, 6x smaller) — comfortably
covering the visible grid plus a margin for places just outside it. The
database return radius stays at 5 km, so places cached from nearby areas
the player already drove through still show up; only NEW fetches get
smaller and faster. Combined with the permanent cache, each area is
fetched once, quickly, and never again.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "overpass-api.de" not in src and "overpass.kumi.systems" not in src:
        print("ERROR: no Overpass fetchers found — apply the real-location patches first.")
        sys.exit(1)
    old_count = src.count("around:5000")
    new_count = src.count("around:2000")
    if old_count == 0 and new_count > 0:
        print(f"SKIP: already searching 2 km radius ({new_count} queries)")
    elif old_count == 0:
        print("WARNING: no around:5000 queries found — nothing to shrink")
    else:
        src = src.replace("around:5000", "around:2000")
        print(f"OK: shrank {old_count} Overpass queries from 5 km to 2 km radius (grid-sized)")
    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_GRID_OK")


if __name__ == "__main__":
    main()
