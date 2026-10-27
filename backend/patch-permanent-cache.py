"""Street Legends backend: real places cache PERMANENTLY (never re-fetch an area).
Run from repo root: python3 backend/patch-permanent-cache.py
Idempotent - safe to re-run.

CONTEXT: once an area's real banks/restaurants/clubs/gas stations load, the
records already stay in the DB forever and serve instantly. The only repeat
work was the 7-day area-cache expiry, which re-queried Overpass once a week
per area to catch newly opened/closed places.

CHANGE: the area cache becomes permanent (100 years, effectively forever).
Once an area is fetched, it is never searched again. First visit to a NEW
area still takes a minute to load (one-time — the game can't know places it
has never looked up), but every visit after that is instant.

Covers all four: banks, restaurants, nightclubs, shops (gas stations).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

REPLACEMENTS = [
    ("CACHE_DAYS = 7", "CACHE_DAYS = 36500  # effectively permanent: once fetched, never re-searched", "banks/restaurants/nightclubs cache"),
    ("timedelta(days=7)", "timedelta(days=36500)", "shops (gas stations) cache"),
]


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "overpass-api.de" not in src:
        print("ERROR: no Overpass fetchers found — apply the real-location patches first.")
        sys.exit(1)

    for old, new, label in REPLACEMENTS:
        count = src.count(old)
        if count == 0:
            if new in src:
                print(f"SKIP: {label} (already permanent)")
            else:
                print(f"WARNING: anchor not found: {label}")
            continue
        src = src.replace(old, new)
        print(f"OK: {label} now permanent ({count} places)")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("PERMANENT_CACHE_OK")


if __name__ == "__main__":
    main()
