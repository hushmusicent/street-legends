#!/usr/bin/env python3
"""Only friends can see each other on the map.

User rule (2026-11-12): "Only friends can see each other on the map."
The /players/nearby endpoint currently returns EVERY active player within
radius (friend or stranger). Houses already use friends-only visibility;
players did not.

Change (backend/server.py, get_nearby_players only):
  - Load the requester's friends list (player["friends"], mutual IDs).
  - Restrict the query to those IDs ("id": {"$in": friend_ids}).
  - If the player has no friends, no other players show on the map.
  - Everything else is untouched: still excludes the requester, logged-out
    players, players inactive 30+ min, and hidden players.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: NEARBY_FRIENDS_ONLY_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OLD = '''    player_pos = Position(**player["position"])
    all_players = await db.players.find(
        {
            "id": {"$ne": player_id}, '''

NEW = '''    player_pos = Position(**player["position"])
    # Friends-only map visibility: only players on this player's friends
    # list show up (same rule as nearby houses). No friends = nobody.
    friend_ids = list(player.get("friends", []) or [])
    all_players = await db.players.find(
        {
            "id": {"$in": friend_ids}, '''


def main():
    if not SERVER.exists():
        print("NEARBY_FRIENDS_ONLY_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if '"id": {"$in": friend_ids}' in src and "Friends-only map visibility" in src:
        print("NEARBY_FRIENDS_ONLY_ALREADY_APPLIED")
        return 0
    if OLD not in src:
        print("NEARBY_FRIENDS_ONLY_FAIL nearby-players query not found (file may have changed)")
        return 1
    src = src.replace(OLD, NEW, 1)
    # sanity: the endpoint and its other filters are still intact
    for needle in (
        'async def get_nearby_players(player_id: str, radius: float = 500):',
        '"hidden_from_map": {"$ne": True}',
        '"last_active": {"$gte": inactivity_threshold}',
        "return nearby",
    ):
        if needle not in src:
            print("NEARBY_FRIENDS_ONLY_FAIL missing after edit: %s" % needle)
            return 1
    SERVER.write_text(src, encoding="utf-8")
    print("NEARBY_FRIENDS_ONLY_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
