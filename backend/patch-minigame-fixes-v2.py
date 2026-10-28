"""Street Legends backend: global cooldown also triggers on practice games.
Run from repo root: python3 backend/patch-minigame-fixes-v2.py
Idempotent - safe to re-run. Requires patch-minigame-fixes.py (v1) applied first.

v1 put the global cooldown timestamp inside the `if not standalone:` blocks,
so practice-mode completions never triggered it. Per the spec ("play once ->
15 min cooldown"), ANY mini-game completion must lock all mini-games.
This moves the global timestamp write outside the standalone check.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# (per-marker $set with global inside) -> (per-marker $set alone + separate global write)
FIXES = [
    (
        '{"$set": {f"castle_cooldowns.{castle_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n        )',
        '{"$set": {f"castle_cooldowns.{castle_id}": datetime.utcnow().isoformat()}}\n        )\n    # Global cooldown: ANY completion (map or practice) locks all mini-games for 15 min\n    await db.players.update_one(\n        {"id": game["player_id"]},\n        {"$set": {"minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n    )',
        "castle",
    ),
    (
        '{"$set": {f"carchase_cooldowns.{chase_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n        )',
        '{"$set": {f"carchase_cooldowns.{chase_id}": datetime.utcnow().isoformat()}}\n        )\n    # Global cooldown: ANY completion (map or practice) locks all mini-games for 15 min\n    await db.players.update_one(\n        {"id": game["player_id"]},\n        {"$set": {"minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n    )',
        "car-chase",
    ),
    (
        '{"$set": {f"runaway_cooldowns.{runaway_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n        )',
        '{"$set": {f"runaway_cooldowns.{runaway_id}": datetime.utcnow().isoformat()}}\n        )\n    # Global cooldown: ANY completion (map or practice) locks all mini-games for 15 min\n    await db.players.update_one(\n        {"id": game["player_id"]},\n        {"$set": {"minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n    )',
        "runaway",
    ),
    (
        '{"$set": {f"packagegrab_cooldowns.{grab_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n        )',
        '{"$set": {f"packagegrab_cooldowns.{grab_id}": datetime.utcnow().isoformat()}}\n        )\n    # Global cooldown: ANY completion (map or practice) locks all mini-games for 15 min\n    await db.players.update_one(\n        {"id": game["player_id"]},\n        {"$set": {"minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n    )',
        "package-grab",
    ),
    (
        '{"$set": {f"shootout_cooldowns.{shootout_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n        )',
        '{"$set": {f"shootout_cooldowns.{shootout_id}": datetime.utcnow().isoformat()}}\n        )\n    # Global cooldown: ANY completion (map or practice) locks all mini-games for 15 min\n    await db.players.update_one(\n        {"id": game["player_id"]},\n        {"$set": {"minigame_global_cooldown_until": _minigame_global_cooldown_until()}}\n    )',
        "shootout",
    ),
]


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    if "MINIGAME_GLOBAL_COOLDOWN_SECONDS = 900" not in SERVER.read_text():
        print("ERROR: patch-minigame-fixes.py (v1) must be applied first. Aborting.")
        sys.exit(1)
    src = SERVER.read_text()
    changed = 0
    for old, new, name in FIXES:
        if new in src:
            print(f"SKIP: global cooldown already outside standalone check ({name})")
            continue
        if src.count(old) != 1:
            print(f"ERROR: anchor for '{name}' matched {src.count(old)}x. Aborting.")
            sys.exit(1)
        src = src.replace(old, new, 1)
        changed += 1
        print(f"OK: global cooldown now triggers on practice completions ({name})")
    if changed:
        SERVER.write_text(src)
        print(f"\nDone. {changed} patch(es) applied.")
    else:
        print("\nNothing to do - all patches already applied.")
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("MINIGAME_FIXES_V2_OK")


if __name__ == "__main__":
    main()
