#!/usr/bin/env python3
"""Remove the global cooldown from mini-games; settings games get NO cooldown.

User requirements (2026-11-11, confirmed by screenshots + live tests):
  - "None of the setting mini games are supposed to have a cooldown."
    Settings (standalone/practice) games must have NO cooldown at all.
  - "Each game supposed to have they own cooldown" (map games).
    Map games keep their own per-marker cooldown only.

Problem: the global cooldown (minigame_global_cooldown_until, 15 min) is
checked on EVERY mini-game start and set on EVERY completion. So after
playing ONE settings game, the next settings game fails to start a session
("Mini-game cooldown active"), the frontend falls back to a fake gameId
('standalone'), the complete 404s silently, and the player sees local
rewards (+$455, +$60) that never land. The map cash never moves. This is
why the settings games don't pay out (except casino games, which don't use
this system).

This patch SUPERSEDES the earlier per-game-cooldown patch (commit 82a7ee54,
not yet run — do NOT run it). It implements the final state in one pass:
  1. Remove the global-cooldown CHECK from ALL 11 mini-game starts
     (6 map + 5 standalone). Map starts keep their per-marker check.
     Standalone starts check nothing.
  2. Remove the global-cooldown SET from ALL 5 complete handlers, so no
     completion (map or standalone) ever sets the global lock. Map
     completions still set their per-marker cooldown (already the case).
     Standalone completions set no cooldown at all.
  3. Works whether or not the earlier per-game patch was run: it handles
     both the original global-set block and the standalone-gated version.

Result: map games cool down independently per marker; settings games have
no cooldown and always create a real session, so they pay out every time.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: MINIGAME_NO_COOLDOWN_SETTINGS_OK
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# All 11 start functions that currently check the global cooldown.
START_FUNCS = [
    # standalone (settings)
    "start_standalone_castle",
    "start_standalone_car_chase",
    "start_standalone_runaway",
    "start_standalone_package_grab",
    "start_standalone_shootout",
    # map
    "start_castle_minigame",
    "start_random_castle_game",
    "start_car_chase",
    "start_runaway",
    "start_package_grab",
    "start_shootout",
]

GLOBAL_CHECK = (
    "    # Global mini-game cooldown: play once -> all mini-games lock for 15 min\n"
    "    _check_minigame_global_cooldown(player)\n"
)
# Standalone starts have NO comment line above the call, just the call itself.
GLOBAL_CHECK_BARE = "    _check_minigame_global_cooldown(player)\n"

# Original global-set block (in all 5 completes).
GLOBAL_SET_ORIG = (
    "    # Global cooldown: ANY completion (map or practice) locks all mini-games for 15 min\n"
    "    await db.players.update_one(\n"
    "        {\"id\": game[\"player_id\"]},\n"
    "        {\"$set\": {\"minigame_global_cooldown_until\": _minigame_global_cooldown_until()}}\n"
    "    )\n"
)
# Standalone-gated version (if the earlier per-game patch was run).
GLOBAL_SET_GATED = (
    "    # Global cooldown: only standalone (settings) completions set it. Map games\n"
    "    # use their own per-marker cooldown.\n"
    "    if standalone:\n"
    "        await db.players.update_one(\n"
    "            {\"id\": game[\"player_id\"]},\n"
    "            {\"$set\": {\"minigame_global_cooldown_until\": _minigame_global_cooldown_until()}}\n"
    "        )\n"
)

COMPLETE_FUNCS = [
    "complete_castle_game",
    "complete_car_chase",
    "complete_runaway",
    "complete_package_grab",
    "complete_shootout",
]


def func_bounds(lines, func_name):
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"async def %s\(" % re.escape(func_name), ln):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("async def ") or lines[j].startswith("@api_router"):
            end = j
            break
    return (start, end)


def main():
    if not SERVER.exists():
        print("MINIGAME_NO_COOLDOWN_SETTINGS_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    orig = src

    # --- 1. Remove the global-set block from all 5 completes (both variants) ---
    removed_sets = 0
    for variant in (GLOBAL_SET_ORIG, GLOBAL_SET_GATED):
        n = src.count(variant)
        if n:
            src = src.replace(variant, "")
            removed_sets += n
    if removed_sets != 5:
        # If the set is already gone entirely, that's fine (idempotent).
        if "minigame_global_cooldown_until\": _minigame_global_cooldown_until()" not in src and removed_sets == 0:
            pass
        else:
            print("MINIGAME_NO_COOLDOWN_SETTINGS_FAIL expected 5 global-set blocks, removed %d" % removed_sets)
            return 1

    # --- 2. Remove the global check from all 11 start functions ---
    lines = src.split("\n")
    removed_checks = 0
    for func in START_FUNCS:
        b = func_bounds(lines, func)
        if b is None:
            print("MINIGAME_NO_COOLDOWN_SETTINGS_FAIL function not found: %s" % func)
            return 1
        start, end = b
        body = "\n".join(lines[start:end])
        if GLOBAL_CHECK in body:
            body2 = body.replace(GLOBAL_CHECK, "", 1)
        elif GLOBAL_CHECK_BARE in body:
            body2 = body.replace(GLOBAL_CHECK_BARE, "", 1)
        else:
            continue
        lines[start:end] = body2.split("\n")
        removed_checks += 1
    src = "\n".join(lines)

    if src == orig and removed_checks == 0 and removed_sets == 0:
        print("MINIGAME_NO_COOLDOWN_SETTINGS_ALREADY_APPLIED")
        return 0

    # --- Verify ---
    # No global-check calls remain in any start handler.
    calls = len(re.findall(r"^[ ]*_check_minigame_global_cooldown\(player\)$", src, re.M))
    if calls != 0:
        print("MINIGAME_NO_COOLDOWN_SETTINGS_FAIL expected 0 global-check calls left, found %d" % calls)
        return 1
    # No global-set remains.
    if "minigame_global_cooldown_until\": _minigame_global_cooldown_until()" in src:
        print("MINIGAME_NO_COOLDOWN_SETTINGS_FAIL a global-set still remains")
        return 1
    # Per-game cooldown checks/sets must still be present (map games).
    for needle in (
        'player.get("castle_cooldowns"',
        'player.get("carchase_cooldowns"',
        'player.get("runaway_cooldowns"',
        'player.get("packagegrab_cooldowns"',
        'player.get("shootout_cooldowns"',
        "castle_cooldowns.",
        "carchase_cooldowns.",
        "runaway_cooldowns.",
        "packagegrab_cooldowns.",
        "shootout_cooldowns.",
    ):
        if needle not in src:
            print("MINIGAME_NO_COOLDOWN_SETTINGS_FAIL per-game cooldown missing: %s" % needle)
            return 1
    for func in COMPLETE_FUNCS:
        if ("async def %s(" % func) not in src:
            print("MINIGAME_NO_COOLDOWN_SETTINGS_FAIL complete function lost: %s" % func)
            return 1

    SERVER.write_text(src, encoding="utf-8")
    print("MINIGAME_NO_COOLDOWN_SETTINGS_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
