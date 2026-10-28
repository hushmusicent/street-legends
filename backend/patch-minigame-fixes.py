"""Street Legends backend: mini-game fixes.
Run from repo root: python3 backend/patch-minigame-fixes.py
Idempotent - safe to re-run.

FIX 1 - Practice-mode (standalone) games never awarded cash:
  car-chase / runaway / package-grab practice mode set game_id='standalone'
  and called the regular complete endpoints, which 404'd ("Game session not
  found") so winnings never reached the player's total. (Shootout already had
  a dedicated standalone start endpoint; castle practice never called the
  backend at all.)
  -> Adds POST /castles/standalone/start, /car-chases/standalone/start,
     /runaways/standalone/start, /package-grabs/standalone/start which create
     real game sessions, so the existing complete endpoints award the normal
     50% practice rewards. (Frontend must call these instead of skipping the
     start call - see the companion frontend patch.)

FIX 2 - Global mini-game cooldown (15 minutes):
  Previously cooldowns were per map marker, so a player could chain castle ->
  car chase -> shootout -> ... with no wait. Now, completing ANY mini-game
  (map or practice) locks ALL mini-games for 15 minutes, per the spec:
  "players should only be able to play once then 15 minute cool down".
  -> Adds minigame_global_cooldown_until on the player, checked in every
     start endpoint (map + standalone) and set in every complete endpoint.
     Also reported by GET /minigames/cooldowns/{player_id} as the "global" key.
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

GLOBAL_SECONDS = 900

HELPER_CODE = '''
# ============== GLOBAL MINI-GAME COOLDOWN ==============
# Play ANY mini-game once -> ALL mini-games lock for 15 minutes.
MINIGAME_GLOBAL_COOLDOWN_SECONDS = 900

def _check_minigame_global_cooldown(player):
    """Raise 400 if the player is inside the global mini-game cooldown window."""
    until = (player or {}).get("minigame_global_cooldown_until")
    if not until:
        return
    try:
        until_dt = datetime.fromisoformat(until)
    except (ValueError, TypeError):
        return
    now = datetime.utcnow()
    if now < until_dt:
        remaining = int((until_dt - now).total_seconds())
        mins, secs = remaining // 60, remaining % 60
        raise HTTPException(
            status_code=400,
            detail=f"Mini-game cooldown active! Wait {mins}m {secs}s before playing again.",
        )

def _minigame_global_cooldown_until():
    """ISO timestamp 15 minutes in the future."""
    return (datetime.utcnow() + timedelta(seconds=MINIGAME_GLOBAL_COOLDOWN_SECONDS)).isoformat()


# ============== STANDALONE (PRACTICE MODE) START ENDPOINTS ==============
# Practice games launched from the options panel previously used
# game_id='standalone', so the complete endpoints 404'd and no cash was ever
# awarded. These create real sessions so completions award the 50% practice
# rewards via the existing logic.

@api_router.post("/castles/standalone/start")
async def start_standalone_castle(player_id: str, level: int = 1):
    """Start a standalone castle practice game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    _check_minigame_global_cooldown(player)
    level = max(1, min(level, 10))
    level_rewards = {
        1: {"min": 25, "max": 50, "xp": 12, "rep": 2},
        2: {"min": 35, "max": 70, "xp": 18, "rep": 3},
        3: {"min": 50, "max": 100, "xp": 25, "rep": 4},
        4: {"min": 75, "max": 150, "xp": 35, "rep": 5},
        5: {"min": 100, "max": 200, "xp": 50, "rep": 6},
        6: {"min": 125, "max": 250, "xp": 75, "rep": 7},
        7: {"min": 175, "max": 350, "xp": 100, "rep": 8},
        8: {"min": 225, "max": 450, "xp": 125, "rep": 9},
        9: {"min": 300, "max": 600, "xp": 185, "rep": 10},
        10: {"min": 500, "max": 1000, "xp": 250, "rep": 15},
    }
    rewards = level_rewards[level]
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "castle_id": "standalone",
        "player_id": player_id,
        "castle_name": f"Training Fortress Lv.{level}",
        "difficulty": level,
        "total_members": level + 2,
        "status": "active",
        "min_reward": rewards["min"],
        "max_reward": rewards["max"],
        "xp_reward": rewards["xp"],
        "rep_reward": rewards["rep"],
        "standalone": True,
        "created_at": datetime.utcnow().isoformat(),
    }
    await db.castle_games.insert_one(game)
    return {"game_id": game_id, "castle_name": game["castle_name"]}


@api_router.post("/car-chases/standalone/start")
async def start_standalone_car_chase(player_id: str, level: int = 1):
    """Start a standalone car chase practice game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    _check_minigame_global_cooldown(player)
    level = max(1, min(level, 10))
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "player_id": player_id,
        "chase_id": "standalone",
        "chase_name": f"Training Run Lv.{level}",
        "difficulty": level,
        "county_line_distance": 5000,
        "min_reward": 100 + level * 20,
        "max_reward": 250 + level * 50,
        "xp_reward": 20 + level * 5,
        "rep_reward": 3 + level,
        "status": "active",
        "standalone": True,
        "started_at": datetime.utcnow().isoformat(),
    }
    await db.car_chase_games.insert_one(game)
    return {"game_id": game_id, "chase_name": game["chase_name"]}


@api_router.post("/runaways/standalone/start")
async def start_standalone_runaway(player_id: str, level: int = 1):
    """Start a standalone runaway practice game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    _check_minigame_global_cooldown(player)
    level = max(1, min(level, 20))
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "player_id": player_id,
        "runaway_id": "standalone",
        "runaway_name": f"Training Hideout Lv.{level}",
        "difficulty": level,
        "hideout_distance": 3000 + level * 200,
        "min_reward": 80 + level * 10,
        "max_reward": 200 + level * 25,
        "xp_reward": 20 + level * 3,
        "rep_reward": 2 + level // 2,
        "status": "active",
        "standalone": True,
        "started_at": datetime.utcnow().isoformat(),
    }
    await db.runaway_games.insert_one(game)
    return {"game_id": game_id, "runaway_name": game["runaway_name"]}


@api_router.post("/package-grabs/standalone/start")
async def start_standalone_package_grab(player_id: str, level: int = 1):
    """Start a standalone package grab practice game"""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    _check_minigame_global_cooldown(player)
    level = max(1, min(level, 20))
    game_id = str(uuid.uuid4())
    game = {
        "id": game_id,
        "player_id": player_id,
        "grab_id": "standalone",
        "grab_name": f"Training Route Lv.{level}",
        "status": "active",
        "standalone": True,
        "started_at": datetime.utcnow().isoformat(),
    }
    await db.packagegrab_games.insert_one(game)
    return {"game_id": game_id, "grab_name": game["grab_name"]}

'''

# Start endpoints that must enforce the global cooldown (map + existing standalone)
START_FUNCS = [
    "start_castle_minigame",
    "start_random_castle_game",
    "start_car_chase",
    "start_runaway",
    "start_package_grab",
    "start_shootout",
    "start_standalone_shootout",
]

# Per-marker cooldown $set lines -> add the global timestamp alongside each
COMPLETION_SETS = [
    ('{"$set": {f"castle_cooldowns.{castle_id}": datetime.utcnow().isoformat()}}',
     '{"$set": {f"castle_cooldowns.{castle_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}'),
    ('{"$set": {f"carchase_cooldowns.{chase_id}": datetime.utcnow().isoformat()}}',
     '{"$set": {f"carchase_cooldowns.{chase_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}'),
    ('{"$set": {f"runaway_cooldowns.{runaway_id}": datetime.utcnow().isoformat()}}',
     '{"$set": {f"runaway_cooldowns.{runaway_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}'),
    ('{"$set": {f"packagegrab_cooldowns.{grab_id}": datetime.utcnow().isoformat()}}',
     '{"$set": {f"packagegrab_cooldowns.{grab_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}'),
    ('{"$set": {f"shootout_cooldowns.{shootout_id}": datetime.utcnow().isoformat()}}',
     '{"$set": {f"shootout_cooldowns.{shootout_id}": datetime.utcnow().isoformat(), "minigame_global_cooldown_until": _minigame_global_cooldown_until()}}'),
]

PLAYER_CHECK = '    if not player:\n        raise HTTPException(status_code=404, detail="Player not found")\n'
GLOBAL_CHECK_CALL = "\n    # Global mini-game cooldown: play once -> all mini-games lock for 15 min\n    _check_minigame_global_cooldown(player)\n"


def patch_helpers(src: str):
    """Insert helper + standalone endpoints before the minigames cooldowns route."""
    marker = "MINIGAME_GLOBAL_COOLDOWN_SECONDS = 900"
    if marker in src:
        print("SKIP: helpers/standalone endpoints already present")
        return src, 0
    anchor = '@api_router.get("/minigames/cooldowns/{player_id}")'
    if src.count(anchor) != 1:
        print(f"ERROR: cooldowns route anchor matched {src.count(anchor)}x. Aborting.")
        sys.exit(1)
    src = src.replace(anchor, HELPER_CODE + anchor, 1)
    print("OK: global-cooldown helpers + 4 standalone start endpoints added")
    return src, 1


def patch_start_checks(src: str):
    """Insert the global cooldown check into each start endpoint (function-scoped)."""
    changed = 0
    for func in START_FUNCS:
        func_def = f"async def {func}("
        start = src.find(func_def)
        if start == -1:
            print(f"ERROR: function {func} not found. Aborting.")
            sys.exit(1)
        next_def = src.find("\nasync def ", start + 1)
        end = next_def if next_def != -1 else len(src)
        body = src[start:end]
        if "_check_minigame_global_cooldown(player)" in body:
            print(f"SKIP: global check already in {func}")
            continue
        idx = body.find(PLAYER_CHECK)
        if idx == -1:
            print(f"ERROR: player-check anchor not found in {func}. Aborting.")
            sys.exit(1)
        insert_at = start + idx + len(PLAYER_CHECK)
        src = src[:insert_at] + GLOBAL_CHECK_CALL + src[insert_at:]
        changed += 1
        print(f"OK: global cooldown check added to {func}")
    return src, changed


def patch_completion_sets(src: str):
    """Add the global cooldown timestamp to each per-marker cooldown write."""
    changed = 0
    for old, new in COMPLETION_SETS:
        if new in src:
            print(f"SKIP: global timestamp already alongside {old[:40]}...")
            continue
        if src.count(old) != 1:
            print(f"ERROR: completion $set anchor matched {src.count(old)}x: {old[:60]}. Aborting.")
            sys.exit(1)
        src = src.replace(old, new, 1)
        changed += 1
        print(f"OK: global cooldown timestamp added ({old[9:40]}...)")
    return src, changed


def patch_cooldowns_reporting(src: str):
    """Report the global cooldown from GET /minigames/cooldowns/{player_id}."""
    marker = 'cooldowns["global"] = {'
    if marker in src:
        print("SKIP: global cooldown already reported by cooldowns endpoint")
        return src, 0
    anchor = "    return cooldowns"
    # scope to get_minigame_cooldowns
    func_def = "async def get_minigame_cooldowns("
    start = src.find(func_def)
    if start == -1:
        print("ERROR: get_minigame_cooldowns not found. Aborting.")
        sys.exit(1)
    next_def = src.find("\nasync def ", start + 1)
    end = next_def if next_def != -1 else len(src)
    body = src[start:end]
    idx = body.rfind(anchor)
    if idx == -1:
        print("ERROR: 'return cooldowns' not found. Aborting.")
        sys.exit(1)
    block = '''
    # Global mini-game cooldown (applies to all map mini-games)
    _global_until = player.get("minigame_global_cooldown_until")
    if _global_until:
        try:
            _until_dt = datetime.fromisoformat(_global_until)
            _secs_left = (_until_dt - now).total_seconds()
            if _secs_left > 0:
                cooldowns["global"] = {
                    "type": "global",
                    "marker_id": None,
                    "remaining_seconds": int(_secs_left),
                    "expires_at": _until_dt.isoformat(),
                }
        except (ValueError, TypeError):
            pass

'''
    insert_at = start + idx
    src = src[:insert_at] + block + src[insert_at:]
    print("OK: global cooldown reported by /minigames/cooldowns")
    return src, 1


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    total = 0
    src, c = patch_helpers(src); total += c
    src, c = patch_start_checks(src); total += c
    src, c = patch_completion_sets(src); total += c
    src, c = patch_cooldowns_reporting(src); total += c
    if total:
        SERVER.write_text(src)
        print(f"\nDone. {total} patch(es) applied.")
    else:
        print("\nNothing to do - all patches already applied.")
    # syntax check
    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    print("MINIGAME_FIXES_OK")


if __name__ == "__main__":
    main()
