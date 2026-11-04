#!/usr/bin/env python3
"""Street Legends backend: pool room rejoin lookup.

Adds GET /pool/rooms/active/{player_id} (prefix mirrored from the live
GET-by-code route, same rule as the rooms wiring patch): the most
recently updated room where the player is host or guest and the status
is 'waiting' or 'playing', or 404 'No active room'. This is what lets a
player who was booted out (app closed, crash, network drop — no leave
call is made in those cases, so the room stays live) find their room
again without remembering the code. Join itself already allows a member
to re-enter a playing room and the game resumes from the saved state,
so no join/leave change is needed here. Backend / Publish only."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SRV = ROOT / "backend/server.py"
MARKER = "POOL_REJOIN_OK"

ROUTE_TMPL = '''
@{ROUTER}.get("{PREFIX}/pool/rooms/active/{{player_id}}")
async def pool_room_active(player_id: str):
    # POOL_REJOIN_OK: latest live room for this player, if any.
    room = await {DB}.pool_rooms.find_one({{"$or": [{{"host_id": player_id}}, {{"guest_id": player_id}}], "status": {{"$in": ["waiting", "playing"]}}}}, sort=[("updated_at", -1)])
    if not room:
        raise HTTPException(status_code=404, detail="No active room")
    room["_id"] = str(room["_id"])
    return room
'''

def main():
    if not SRV.exists():
        print("POOL_REJOIN_ERROR: backend/server.py not found (run from /app)")
        return 1
    src = SRV.read_text(errors="ignore")
    if MARKER in src:
        print("POOL_REJOIN_ALREADY_APPLIED")
        return 0
    m = re.search(r"@(\w+)\.get\(\s*[\"']([^\"']*)/pool/rooms/\{code\}\s*[\"']", src)
    if not m:
        print("WARNING: live pool GET route not found - active route NOT added")
        return 1
    router, prefix = m.group(1), m.group(2)
    dbm = re.search(r"(\w+)\.pool_rooms\.", src)
    if not dbm:
        print("WARNING: pool_rooms db handle not found - active route NOT added")
        return 1
    if "HTTPException" not in src:
        print("WARNING: HTTPException not imported - active route NOT added")
        return 1
    route = ROUTE_TMPL.format(ROUTER=router, PREFIX=prefix, DB=dbm.group(1))
    inc = src.find("include_router(")
    if inc != -1:
        line_start = src.rfind("\n", 0, inc) + 1
        src = src[:line_start] + route.strip() + "\n\n" + src[line_start:]
    elif "\nif __name__" in src:
        i = src.find("\nif __name__")
        src = src[:i] + "\n" + route.strip() + "\n" + src[i:]
    else:
        src = src.rstrip() + "\n" + route
    try:
        compile(src, "server.py", "exec")
    except SyntaxError as e:
        print("POOL_REJOIN_SYNTAX_FAIL: %s (file NOT written)" % e)
        return 1
    SRV.write_text(src)
    print("POOL_REJOIN_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
