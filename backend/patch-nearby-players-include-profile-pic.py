#!/usr/bin/env python3
"""Nearby players: include profile_pic in the response.

User correction (2026-11-12): both players DO have profile pictures, and
each phone still shows the other as the generic blue person.

Verified live: GET /api/players/{id}/profile-pic returns a real base64
JPEG for BOTH Mayor Veno and AppSolutGroup — the pictures exist in the
database. But get_nearby_players fetches profile_pic in its MongoDB
projection and then DROPS it when building the response dict (it returns
only id, name, level, character_class, position, distance, guild_id).
So the app never receives the picture for nearby players, and no
frontend change can show it. The leaderboard endpoint already includes
profile_pic in its response — nearby was the only one that forgot it.

Change (backend/server.py, get_nearby_players only): add
"profile_pic": p.get("profile_pic") to the nearby dict. Nothing else
changes. The frontend profile-pic patch (PLAYER_PROFILE_PIC_OK) then
receives the picture and renders it on the map marker + popup.

BACKEND — run, then Deploy. Marker: NEARBY_PROFILE_PIC_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OLD = '''                nearby.append({
                    "id": p["id"],
                    "name": p["name"],
                    "level": p["level"],
                    "character_class": p["character_class"],
                    "position": p["position"],
                    "distance": round(distance, 1),
                    "guild_id": p.get("guild_id")
                })'''

NEW = '''                nearby.append({
                    "id": p["id"],
                    "name": p["name"],
                    "level": p["level"],
                    "character_class": p["character_class"],
                    "position": p["position"],
                    "distance": round(distance, 1),
                    "guild_id": p.get("guild_id"),
                    "profile_pic": p.get("profile_pic")
                })'''


def main():
    if not SERVER.exists():
        print("NEARBY_PROFILE_PIC_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if '"profile_pic": p.get("profile_pic")' in src and "async def get_nearby_players" in src:
        # Already applied (check it is inside the nearby builder, not only leaderboard).
        idx = src.find("async def get_nearby_players")
        seg = src[idx:idx + 2000]
        if '"profile_pic": p.get("profile_pic")' in seg:
            print("NEARBY_PROFILE_PIC_ALREADY_APPLIED")
            return 0
    if OLD not in src:
        print("NEARBY_PROFILE_PIC_FAIL nearby response block not found (file may have changed)")
        return 1
    src = src.replace(OLD, NEW, 1)
    idx = src.find("async def get_nearby_players")
    seg = src[idx:idx + 2000]
    if '"profile_pic": p.get("profile_pic")' not in seg:
        print("NEARBY_PROFILE_PIC_FAIL missing after edit")
        return 1
    SERVER.write_text(src, encoding="utf-8")
    print("NEARBY_PROFILE_PIC_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
