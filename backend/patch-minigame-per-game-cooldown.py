#!/usr/bin/env python3
"""Give each MAP mini-game its own cooldown (remove the global lock from map games).

Problem (found by live test 2026-11-11): after completing ONE map shootout,
starting a DIFFERENT shootout is blocked with "Mini-game cooldown active!
Wait 14m 51s" — the global cooldown (minigame_global_cooldown_until) locks
ALL mini-games for 15 min after any single game. The per-game cooldowns
(shootout_cooldowns.{id}, castle_cooldowns.{id}, ...) are set but never get
a chance to matter, because the global one is broader and covers the same
15-minute window. Each map game is supposed to have its OWN cooldown, so
playing one must not lock the others.

Fix (backend only, server.py):
  1. Map starts: remove the global-cooldown check from the 6 map start
     handlers (castle, random castle, car chase, runaway, package grab,
     shootout). They keep their per-marker cooldown check. Standalone
     (settings) starts still check the global cooldown.
  2. Map completes: the global cooldown is now only SET for standalone
     (settings) completions. Map completions set only their per-marker
     cooldown (already the case). Standalone games have no per-marker
     cooldown, so the global one still stops them being farmed back-to-back.

Result: map games cool down independently per marker; settings games share
one 15-min global cooldown; neither blocks the other.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: MINIGAME_PER_GAME_COOLDOWN_OK
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# Map start functions: remove the global check from inside these only.
MAP_START_FUNCS = [
    "start_castle_minigame",
    "start_random_castle_game",
    "start_car_chase",
    "start_runaway",
    "start_package_grab",
    "start_shootout",
]

# The two lines to remove from a map start (comment + call).
GLOBAL_CHECK = (
    "    # Global mini-game cooldown: play once -> all mini-games lock for 15 min\n"
    "    _check_minigame_global_cooldown(player)\n"
)
MAP_CHECK_REPLACEMENT = (
    "    # Map games use their own per-marker cooldown (checked below), not the global one.\n"
)

# The global-set block in the 5 complete handlers (identical in all 5).
GLOBAL_SET_OLD = (
    "    # Global cooldown: ANY completion (map or practice) locks all mini-games for 15 min\n"
    "    await db.players.update_one(\n"
    "        {\"id\": game[\"player_id\"]},\n"
    "        {\"$set\": {\"minigame_global_cooldown_until\": _minigame_global_cooldown_until()}}\n"
    "    )\n"
)
GLOBAL_SET_NEW = (
    "    # Global cooldown: only standalone (settings) completions set it. Map games\n"
    "    # use their own per-marker cooldown.\n"
    "    if standalone:\n"
    "        await db.players.update_one(\n"
    "            {\"id\": game[\"player_id\"]},\n"
    "            {\"$set\": {\"minigame_global_cooldown_until\": _minigame_global_cooldown_until()}}\n"
    "        )\n"
)

# Complete functions that must contain the standalone-gated global set.
COMPLETE_FUNCS = [
    "complete_castle_game",
    "complete_car_chase",
    "complete_runaway",
    "complete_package_grab",
    "complete_shootout",
]


def func_bounds(lines, func_name):
    """Return (start_idx, end_idx) line range of `async def <func_name>(`."""
    start = None
    for i, ln in enumerate(lines):
        if re.match(r"async def %s\(" % re.escape(func_name), ln):
            start = i
            break
    if start is None:
        return None
    # End at the next top-level def/decorator, or EOF.
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].startswith("async def ") or lines[j].startswith("@api_router"):
            end = j
            break
    return (start, end)


def main():
    if not SERVER.exists():
        print("MINIGAME_PER_GAME_COOLDOWN_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    orig = src

    # --- 1. Completes: gate the global set on standalone (all 5, identical text) ---
    count_old = src.count(GLOBAL_SET_OLD)
    if count_old == 0:
        # Maybe already applied.
        if "if standalone:" in src and src.count(GLOBAL_SET_NEW) >= 5:
            pass
        else:
            print("MINIGAME_PER_GAME_COOLDOWN_FAIL global-set block not found")
            return 1
    else:
        if count_old != 5:
            print("MINIGAME_PER_GAME_COOLDOWN_FAIL expected 5 global-set blocks, found %d" % count_old)
            return 1
        src = src.replace(GLOBAL_SET_OLD, GLOBAL_SET_NEW)

    # --- 2. Map starts: remove the global check from the 6 map start functions ---
    lines = src.split("\n")
    removed = 0
    for func in MAP_START_FUNCS:
        b = func_bounds(lines, func)
        if b is None:
            print("MINIGAME_PER_GAME_COOLDOWN_FAIL function not found: %s" % func)
            return 1
        start, end = b
        body = "\n".join(lines[start:end])
        if GLOBAL_CHECK not in body:
            # Already removed in this function; keep going.
            continue
        body2 = body.replace(GLOBAL_CHECK, MAP_CHECK_REPLACEMENT, 1)
        new_lines = body2.split("\n")
        lines[start:end] = new_lines
        removed += 1
    src = "\n".join(lines)

    if src == orig and removed == 0 and count_old == 0:
        print("MINIGAME_PER_GAME_COOLDOWN_ALREADY_APPLIED")
        return 0

    # --- Verify ---
    # Standalone starts must still check the global cooldown (5 of them).
    calls = len(re.findall(r"^[ ]*_check_minigame_global_cooldown\(player\)$", src, re.M))
    if calls != 5:
        print("MINIGAME_PER_GAME_COOLDOWN_FAIL expected 5 global-check calls left (standalone), found %d" % calls)
        return 1
    # The gated global set must appear 5 times (one per complete).
    if src.count(GLOBAL_SET_NEW) != 5:
        print("MINIGAME_PER_GAME_COOLDOWN_FAIL expected 5 gated global sets, found %d" % src.count(GLOBAL_SET_NEW))
        return 1
    # Per-game cooldown checks/sets must still be present in every game.
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
            print("MINIGAME_PER_GAME_COOLDOWN_FAIL per-game cooldown missing: %s" % needle)
            return 1
    # All complete functions still present.
    for func in COMPLETE_FUNCS:
        if ("async def %s(" % func) not in src:
            print("MINIGAME_PER_GAME_COOLDOWN_FAIL complete function lost: %s" % func)
            return 1

    SERVER.write_text(src, encoding="utf-8")
    print("MINIGAME_PER_GAME_COOLDOWN_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
