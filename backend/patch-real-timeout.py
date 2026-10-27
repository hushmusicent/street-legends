"""Street Legends backend: give Overpass background fetches more time to finish.
Run from repo root: python3 backend/patch-real-timeout.py
Idempotent - safe to re-run.

ROOT CAUSE of empty maps in new areas: the background Overpass fetches used a
60s HTTP timeout, but Overpass regularly takes 60s+ to answer from Emergent's
network (a live blocking call measured 61s). The background task timed out
just before the data arrived, wrote no cache record, and the next refresh
retried — forever empty. Bumping the Overpass query timeout to 100s and the
HTTP client timeout to 120s gives it room to complete.

ONLY touches the Overpass fetchers (banks, restaurants, nightclubs, shops).
The unrelated storage timeout=60 is left alone.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

REPLACEMENTS = [
    ('"[out:json][timeout:50];"', '"[out:json][timeout:100];"', "Overpass query timeout 50s -> 100s"),
    ("httpx.AsyncClient(timeout=60)", "httpx.AsyncClient(timeout=120)", "HTTP client timeout 60s -> 120s"),
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
                print(f"SKIP: {label} (already applied)")
            else:
                print(f"WARNING: anchor not found: {label}")
            continue
        src = src.replace(old, new)
        print(f"OK: {label} ({count} places)")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_TIMEOUT_OK")


if __name__ == "__main__":
    main()
