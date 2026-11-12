#!/usr/bin/env python3
"""Fix the settings shootout (standalone) route being shadowed by the map route.

Problem (found by live health check 2026-11-11): POST
/api/shootouts/standalone/start returns "Shootout location not found"
because FastAPI matches routes in definition order, and the map route
@api_router.post("/shootouts/{shootout_id}/start") is defined BEFORE the
literal @api_router.post("/shootouts/standalone/start"). So a request to
/shootouts/standalone/start matches the map route with shootout_id="standalone",
which finds no shootout location and 404s. The settings shootout can never
start a real session, so the app falls back to local-only play and no cash,
rep, or cooldown is ever recorded.

Fix: move the whole standalone route block (decorator + start_standalone_shootout
function) to BEFORE the map route, so the literal route wins. No logic changes.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: SHOOTOUT_STANDALONE_ROUTE_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")
MAP_DECORATOR = '@api_router.post("/shootouts/{shootout_id}/start")'
STANDALONE_DECORATOR = '@api_router.post("/shootouts/standalone/start")'
COMPLETE_DECORATOR = '@api_router.post("/shootouts/game/{game_id}/complete")'


def main():
    if not SERVER.exists():
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")

    map_idx = src.find(MAP_DECORATOR)
    standalone_idx = src.find(STANDALONE_DECORATOR)
    complete_idx = src.find(COMPLETE_DECORATOR)
    if map_idx < 0 or standalone_idx < 0 or complete_idx < 0:
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL one of the shootout routes is missing")
        return 1

    # Already fixed if the standalone route comes first.
    if standalone_idx < map_idx:
        print("SHOOTOUT_STANDALONE_ROUTE_ALREADY_APPLIED")
        return 0

    # The standalone block runs from its decorator to just before the complete
    # decorator (it is the last block before complete). Keep the block text
    # exactly as-is, including its trailing blank lines.
    block = src[standalone_idx:complete_idx]
    if "async def start_standalone_shootout" not in block:
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL standalone function not inside block")
        return 1

    # Remove the block from its old position, then insert it before the map route.
    src2 = src[:standalone_idx] + src[complete_idx:]
    map_idx2 = src2.find(MAP_DECORATOR)
    if map_idx2 < 0:
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL map route lost after removal")
        return 1
    src2 = src2[:map_idx2] + block + src2[map_idx2:]

    # Verify: standalone now before map, both functions intact, no duplication.
    s_idx = src2.find(STANDALONE_DECORATOR)
    m_idx = src2.find(MAP_DECORATOR)
    if not (0 <= s_idx < m_idx):
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL reorder did not take")
        return 1
    if src2.count(STANDALONE_DECORATOR) != 1 or src2.count(MAP_DECORATOR) != 1:
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL duplicate route decorator")
        return 1
    if "async def start_standalone_shootout" not in src2:
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL standalone function lost")
        return 1
    if "async def start_shootout" not in src2:
        print("SHOOTOUT_STANDALONE_ROUTE_FAIL map function lost")
        return 1

    SERVER.write_text(src2, encoding="utf-8")
    print("SHOOTOUT_STANDALONE_ROUTE_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
