"""One-time grant: add $1,000,000 in-game cash to Mayor Veno (to test the
$1M Luxury Mansion). Run from repo root: python3 backend/grant-test-cash.py

Connects to MongoDB using MONGO_URL + DB_NAME (from the environment, or
from backend/.env if the env vars aren't set), finds the player by name,
and adds the cash. Changes NO server code — it only updates one player
document. Prints the old and new balance.

WARNING: it adds $1M EVERY time it runs, so run it ONCE. (Running it
again just adds another $1M — harmless for testing, but don't run it
on accident.)
"""
import os
import re
import sys
from pathlib import Path

PLAYER_NAME = "Mayor Veno"
AMOUNT = 1_000_000


def load_env():
    env = dict(os.environ)
    env_file = Path("backend/.env")
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            env.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    return env


def main():
    env = load_env()
    mongo_url = env.get("MONGO_URL")
    db_name = env.get("DB_NAME")
    if not mongo_url or not db_name:
        print("ERROR: MONGO_URL and DB_NAME not found in env or backend/.env.")
        print("Run this from the Emergent terminal (repo root) where the backend env is set.")
        sys.exit(1)
    try:
        from pymongo import MongoClient
    except ImportError:
        print("pymongo not installed — installing it now...")
        import subprocess
        installed = False
        for cmd in (["pip", "install", "pymongo"], ["pip3", "install", "pymongo"], [sys.executable, "-m", "pip", "install", "pymongo"]):
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=120)
                installed = True
                break
            except Exception:
                continue
        if not installed:
            print("ERROR: could not install pymongo. Run 'pip install pymongo' first, then re-run this script.")
            sys.exit(1)
        from pymongo import MongoClient
    client = MongoClient(mongo_url, serverSelectionTimeoutMS=15000)
    db = client[db_name]
    player = db.players.find_one({"name": {"$regex": f"^{re.escape(PLAYER_NAME)}$", "$options": "i"}})
    if not player:
        # Fall back to a partial match (e.g. the stored name may differ
        # slightly from the display name).
        player = db.players.find_one({"name": {"$regex": "Veno", "$options": "i"}})
    if not player:
        print(f"ERROR: no player named '{PLAYER_NAME}' found.")
        print("Players in this database:")
        found_any = False
        for p in db.players.find({}, {"name": 1, "level": 1, "cash": 1}).limit(30):
            found_any = True
            print(f"  - {p.get('name')} (Lv.{p.get('level')}) cash ${p.get('cash', 0):,}")
        if not found_any:
            print("  (no players at all — check DB_NAME)")
        sys.exit(1)
    old_cash = player.get("cash", 0)
    db.players.update_one({"id": player["id"]}, {"$inc": {"cash": AMOUNT}})
    updated = db.players.find_one({"id": player["id"]})
    new_cash = updated.get("cash", 0)
    print(f"Player: {player.get('name')} (Lv.{player.get('level')})")
    print(f"Cash: ${old_cash:,} -> ${new_cash:,}")
    print(f"Granted: ${AMOUNT:,}")
    print("GRANT_OK")


if __name__ == "__main__":
    main()
