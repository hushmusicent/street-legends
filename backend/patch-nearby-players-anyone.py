#!/usr/bin/env python3
"""Revert map visibility: anybody can see anybody on the map again.

User (2026-11-12): "put it back where anybody can see any body on the
map." The friends-only patch (NEARBY_FRIENDS_ONLY) hid every stranger, so
only friends showed. Revert it: /players/nearby returns every active
player within radius again, friend or stranger.

Change (backend/server.py, get_nearby_players only):
  - Remove the friends-only restriction ("id": {"$in": friend_ids}).
  - Restore the original exclusion of the requester ("id": {"$ne": ...}).
  - Everything else untouched: still excludes logged-out players, players
    inactive 30+ min, and hidden players.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: NEARBY_ANYONE_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OLD = '''    player_pos = Position(**player["position"])
    # Friends-only map visibility: only players on this player's friends
    # list show up (same rule as nearby houses). No friends = nobody.
    friend_ids = list(player.get("friends", []) or [])
    all_players = await db.players.find(
        {
            "id": {"$in": friend_ids}, '''

NEW = '''    player_pos = Position(**player["position"])
    all_players = await db.players.find(
        {
            "id": {"$ne": player_id}, '''


def main():
    if not SERVER.exists():
        print("NEARBY_ANYONE_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if '"id": {"$ne": player_id}' in src and "Friends-only map visibility" not in src and "NEARBY_ANYONE" not in src:
        # Already reverted (or the friends-only patch was never applied).
        # Only treat as done if the nearby endpoint exists.
        if "async def get_nearby_players" in src:
            print("NEARBY_ANYONE_ALREADY_APPLIED")
            return 0
    if OLD not in src:
        print("NEARBY_ANYONE_FAIL friends-only block not found (file may have changed)")
        return 1
    src = src.replace(OLD, NEW, 1)
    for needle in (
        'async def get_nearby_players(player_id: str, radius: float = 500):',
        '"id": {"$ne": player_id}',
        '"hidden_from_map": {"$ne": True}',
        "return nearby",
    ):
        if needle not in src:
            print("NEARBY_ANYONE_FAIL missing after edit: %s" % needle)
            return 1
    if "Friends-only map visibility" in src:
        print("NEARBY_ANYONE_FAIL friends-only comment still present")
        return 1
    SERVER.write_text(src, encoding="utf-8")
    print("NEARBY_ANYONE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
