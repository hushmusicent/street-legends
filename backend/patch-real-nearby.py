"""Street Legends backend: spawn gun shops at the NEAREST gas stations.
Run from repo root: python3 backend/patch-real-nearby.py
Idempotent - safe to re-run.

WHY the user never SEES gun shops even when the backend returns them: the
shops spawn shuffled ALL gas stations within 5 km and picked 2-3 at
random. With 20+ stations in that circle, the picks usually landed 4-5 km
away — off-screen — while the stations right next to the player were
ignored. Live proof at 41.61613, -83.70050: the backend returned shops
4.3-4.5 km away even though OSM has 6 stations within 2 km of the player.

FIX: replace the random shuffle with a closest-first sort. Shops now
spawn at the nearest cached gas stations, so they appear on the player's
visible map (and the guaranteed gun_shop is among them). As the player
drives and nearer stations get cached, shops keep hugging the player
instead of jumping to random far corners of the 5 km circle. The shop
TYPES stay shuffled (gun/armor/general mix unchanged); only the
LOCATIONS stop being random.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OLD = "    random.shuffle(real_locations)"
NEW = """    # Closest first so shops spawn near the player, not randomly up to 5 km
    # away off-screen. (Squared distance is enough for sorting.)
    _cos = max(0.2, math.cos(math.radians(latitude)))
    real_locations.sort(key=lambda loc: ((loc["latitude"] - latitude) * 111000.0) ** 2 + ((loc["longitude"] - longitude) * 111000.0 * _cos) ** 2)"""


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "gas_stations" not in src:
        print("ERROR: no gas-station shops found — apply the real-shops patches first.")
        sys.exit(1)
    if NEW in src and OLD not in src:
        print("SKIP: shops already spawn nearest-first")
    elif OLD not in src:
        print("WARNING: random.shuffle(real_locations) not found — nothing to change")
    else:
        count = src.count(OLD)
        src = src.replace(OLD, NEW)
        print(f"OK: {count} location shuffle(s) replaced with closest-first sort")
    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("REAL_NEARBY_OK")


if __name__ == "__main__":
    main()
