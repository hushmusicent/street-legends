"""Street Legends backend: bank robbery fine + health-scaled luck.
Run from repo root: python3 backend/patch-bank-robbery.py
Idempotent - safe to re-run.

CHANGES (robbery only, other luck uses untouched):
1. Fine is now a flat $450-$1000 (was level-scaled $225-$450 at Lv.13).
2. Luck drops with health: effective luck = base luck x (current HP /
   max HP). Full health = full luck; half health = half luck; near
   death = near-zero luck (which also hits the 20% floor when luck
   reaches 0). So going into a heist hurt genuinely lowers your odds.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

LUCK_OLD = """    # Get effective stats (luck affects success chance)
    effective_stats = await get_effective_stats(player)
    luck_val = effective_stats.get("luck", 5)"""
LUCK_NEW = """    # Get effective stats (luck affects success chance)
    effective_stats = await get_effective_stats(player)
    luck_val = effective_stats.get("luck", 5)
    # Luck drops with health: full HP = full luck, half HP = half luck.
    stats = player.get("stats", {}) or {}
    max_hp = stats.get("max_health", 100) or 100
    cur_hp = stats.get("health", max_hp)
    health_factor = max(0.0, min(1.0, cur_hp / max_hp)) if max_hp > 0 else 1.0
    luck_val = luck_val * health_factor"""

FINE_OLD = "        fine = random.randint(min_reward // 2, min_reward)"
FINE_NEW = "        fine = random.randint(450, 1000)"


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    if "health_factor" in src:
        print("SKIP: health-scaled luck already present")
    elif src.count(LUCK_OLD) == 1:
        src = src.replace(LUCK_OLD, LUCK_NEW, 1)
        print("OK: luck now scales with health in robberies")
    else:
        print(f"WARNING: luck anchor matched {src.count(LUCK_OLD)}x — skipping")
    if FINE_NEW in src:
        print("SKIP: flat fine already present")
    elif src.count(FINE_OLD) == 1:
        src = src.replace(FINE_OLD, FINE_NEW, 1)
        print("OK: fine now flat $450-$1000")
    else:
        print(f"WARNING: fine anchor matched {src.count(FINE_OLD)}x — skipping")
    SERVER.write_text(src)
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("BANK_ROBBERY_OK")


if __name__ == "__main__":
    main()
