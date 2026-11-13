#!/usr/bin/env python3
"""Fix position updates: they 404 for every player, so nobody's location
ever reaches the server and friends never appear on the map.

Root cause (backend/server.py, update_player_position):
  player = await db.players.find_one({"_id": player_id})
The lookup uses MongoDB's _id (an ObjectId), but the player's id is a UUID
string stored in the `id` field. The lookup never matches, so the endpoint
always raises 404 "Player not found" — even though the player exists.
Verified live 2026-11-12: PUT /api/players/<HealthCheck>/position returned
404 while a GET of the same player works fine. That is why AppSolutGroup
has position None and Mayor Veno's position is frozen at 2026-11-05, and
why the nearby endpoint returns nobody.

Change: look the player up by {"id": player_id}, matching the update
further down in the same function (which already uses {"id": ...}).

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: POSITION_PUT_ID_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OLD = '''async def update_player_position(player_id: str, position: Position):
    """Update player's GPS position"""
    player = await db.players.find_one({"_id": player_id})'''

NEW = '''async def update_player_position(player_id: str, position: Position):
    """Update player's GPS position"""
    player = await db.players.find_one({"id": player_id})'''


def main():
    if not SERVER.exists():
        print("POSITION_PUT_ID_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if 'async def update_player_position(player_id: str, position: Position):\n    """Update player\'s GPS position"""\n    player = await db.players.find_one({"id": player_id})' in src:
        print("POSITION_PUT_ID_ALREADY_APPLIED")
        return 0
    if OLD not in src:
        print("POSITION_PUT_ID_FAIL position endpoint not found (file may have changed)")
        return 1
    src = src.replace(OLD, NEW, 1)
    if 'player = await db.players.find_one({"id": player_id})' not in src:
        print("POSITION_PUT_ID_FAIL edit did not land")
        return 1
    SERVER.write_text(src, encoding="utf-8")
    print("POSITION_PUT_ID_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
