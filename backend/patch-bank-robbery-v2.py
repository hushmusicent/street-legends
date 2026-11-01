"""Street Legends backend: bank robbery luck drops FASTER with health.
Run from repo root: python3 backend/patch-bank-robbery-v2.py
Idempotent - safe to re-run.

CHANGE: v1 scaled luck linearly with health (half HP = half luck =
only ~9 points off at Luck 11). Now the health factor is SQUARED, so
luck falls off much harder as health drops:
  Full HP  -> full luck (70% at Luck 11, unchanged)
  75% HP   -> ~62% (was ~66%)
  50% HP   -> ~55% (was ~61%)
  25% HP   -> ~51% (was ~55%)
  Near 0   -> ~50% base, hitting the 20% floor at 0 luck.
Works whether v1 was already applied or not.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# Case A: v1 already applied (linear line present) -> square it.
V1_LINE = "    luck_val = luck_val * health_factor"
V2_LINE = "    luck_val = luck_val * health_factor * health_factor  # Squared: luck falls off faster as health drops"

# Case B: v1 never applied -> insert the full squared version.
LUCK_OLD = """    # Get effective stats (luck affects success chance)
    effective_stats = await get_effective_stats(player)
    luck_val = effective_stats.get("luck", 5)"""
LUCK_NEW = """    # Get effective stats (luck affects success chance)
    effective_stats = await get_effective_stats(player)
    luck_val = effective_stats.get("luck", 5)
    # Luck drops with health, SQUARED so it falls off fast: full HP =
    # full luck, half HP = quarter luck.
    stats = player.get("stats", {}) or {}
    max_hp = stats.get("max_health", 100) or 100
    cur_hp = stats.get("health", max_hp)
    health_factor = max(0.0, min(1.0, cur_hp / max_hp)) if max_hp > 0 else 1.0
    luck_val = luck_val * health_factor * health_factor"""


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "health_factor * health_factor" in src:
        print("SKIP: squared health scaling already present")
    elif src.count(V1_LINE) == 1:
        src = src.replace(V1_LINE, V2_LINE, 1)
        print("OK: health scaling squared (drops faster)")
    elif src.count(LUCK_OLD) == 1:
        src = src.replace(LUCK_OLD, LUCK_NEW, 1)
        print("OK: squared health-scaled luck added (v1 was not present)")
    else:
        print("WARNING: no matching anchor — check if already patched")
    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("BANK_ROBBERY_V2_OK")


if __name__ == "__main__":
    main()
