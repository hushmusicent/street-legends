"""Street Legends backend: Overpass fallback + concurrency limit.
Run from repo root: python3 backend/patch-overpass-fallback.py
Idempotent - safe to re-run.

WHY gun shops (and sometimes other types) stay empty: Overpass is flaky
under load — it rate-limits (instant empty error) or queues requests past
the 120s timeout. The game fires banks + restaurants + clubs + shops at
once per map load, so 4 concurrent Overpass queries from one IP trip its
per-IP concurrency limit and the queued ones time out. Live proof: the
game's fuel fetch timed out at 120s three times in a row while the same
query from elsewhere answered in 42-56s, and a tiny probe showed Overpass
up but rate-limiting other queries.

FIX, applied to all four place fetchers (banks, restaurants, nightclubs,
gas stations):
1. A shared semaphore caps concurrent Overpass calls at 2, so the game's
   own map load can't queue itself past the timeout.
2. Each fetch tries three Overpass instances in order (main + two public
   mirrors) at 90s each, instead of betting everything on one 120s call.
   First success wins; all-fail leaves the cache empty for the next
   refresh to retry (the blocking spawn already re-fetches on empty).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

DEFINITIONS = '''_osm_fetching = set()
# Overpass instances to try in order + cap on concurrent calls, so one map
# load firing banks/restaurants/clubs/shops at once can't queue itself out.
OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]
OVERPASS_SEMAPHORE = asyncio.Semaphore(2)'''

# Each fetcher has a distinct User-Agent; replace its single-shot fetch
# preamble with a semaphore-guarded multi-instance loop. The processing
# loop that follows stays untouched (it sits under `if True:` now).
FETCHERS = [
    ("game gas station lookup", "gas stations"),
    ("game restaurant lookup", "restaurants"),
    ("game nightclub lookup", "nightclubs"),
    ("game bank lookup", "banks"),
]


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "overpass-api.de" not in src:
        print("ERROR: no Overpass fetchers found — apply the real-location patches first.")
        sys.exit(1)

    if "OVERPASS_SEMAPHORE" not in src:
        if src.count("_osm_fetching = set()") != 1:
            print("ERROR: _osm_fetching definition anchor not found exactly once.")
            sys.exit(1)
        src = src.replace("_osm_fetching = set()", DEFINITIONS, 1)
        print("OK: Overpass URL list + semaphore defined")
    else:
        print("SKIP: Overpass URL list + semaphore already defined")

    for ua, label in FETCHERS:
        old = f'''        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={{"data": query}},
                headers={{"User-Agent": "StreetLegends/1.0 ({ua})"}},
            )
        if resp.status_code == 200:
            elements = resp.json().get("elements", [])'''
        new = f'''        elements = []
        async with OVERPASS_SEMAPHORE:
            for overpass_url in OVERPASS_URLS:
                try:
                    async with httpx.AsyncClient(timeout=90) as client:
                        resp = await client.post(
                            overpass_url,
                            data={{"data": query}},
                            headers={{"User-Agent": "StreetLegends/1.0 ({ua})"}},
                        )
                    if resp.status_code == 200:
                        elements = resp.json().get("elements", [])
                        break
                except Exception:
                    continue
        if True:'''
        if new in src:
            print(f"SKIP: {label} fetcher already uses fallback")
        elif src.count(old) != 1:
            print(f"WARNING: {label} fetch anchor matched {src.count(old)}x — skipping")
        else:
            src = src.replace(old, new, 1)
            print(f"OK: {label} fetcher tries 3 Overpass instances under semaphore")

    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("OVERPASS_FALLBACK_OK")


if __name__ == "__main__":
    main()
