#!/usr/bin/env python3
"""Street Legends backend: Activity Center cash prizes (v2).

v2 fixes the v1 insertion anchor. v1 looked for a literal
"\\nif __name__ ==" line, but the live server.py no longer has that
guard, so v1 printed "server.py end anchor not found" and added
nothing. v2 inserts before the __main__ guard when it exists (any
quote style) and otherwise appends the endpoint at the end of the
file, where module-level code still registers on import.

User (2026-11-10/11): cash prizes on the activity center games.
  * Table games (Pool, Dartboard, Card Table, Dominoes, Scrabble,
    Chess & Checkers): $500 when the player WINS (PvC or PvP).
    Games with levels pay 10% more per level (compounding, rounded
    to whole dollars): Chess & Checkers has levels 1-10, so a
    level-10 win pays $500 x 1.1^9 = $1,179. The other table games
    have no levels and pay a flat $500.
  * Pop Shot (solo, no opponent): $10 per basket made, $15 per
    ON FIRE basket (3rd straight make and beyond), +10% per level
    (5 levels: Rookie 1, Amateur 2, Pro 3, All-Star 4, Legend 5).
    Level 1: $10 / $15. Level 5: $15 / $22 (rounded).

The server computes the prize from the game + level + result — the
client never sends an amount, so a crafted request cannot award
arbitrary cash. The endpoint validates the game, the level range
for that game, and sane caps on the Pop Shot counts, then $inc's
the player's cash and returns the prize + new balance.

ENDPOINT:
  POST /api/center-prize/award
    {player_id, game, level, won, makes, onfire_makes}
    game: pool | dartboard | card_table | dominoes | scrabble |
          chess_checkers | pop_shot
    level: 1-5 for pop_shot, 1-10 for chess_checkers, 1 otherwise
    won: true for a table-game win (ignored for pop_shot)
    makes / onfire_makes: Pop Shot baskets (onfire <= makes, each <= 100)
  -> {game, level, prize, cash}

Run from /app: python3 backend/patch-center-prize-v2.py
Backend only: Publish after running.
Idempotent: a full re-run prints CENTER_PRIZE_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "CENTER_PRIZE_OK"

ENDPOINT = '''
# ============== ACTIVITY CENTER CASH PRIZES ==============
# $500 per table-game win (+10% compounding per level on Chess,
# levels 1-10). Pop Shot: $10 per make, $15 per ON FIRE make,
# +10% compounding per level (5 levels). The server computes the
# prize from game + level + result; the client never sends an amount.
CENTER_PRIZE_GAMES = {
    "pool": {"max_level": 1},
    "dartboard": {"max_level": 1},
    "card_table": {"max_level": 1},
    "dominoes": {"max_level": 1},
    "scrabble": {"max_level": 1},
    "chess_checkers": {"max_level": 10},
    "pop_shot": {"max_level": 5},
}


def _center_prize_amount(game, level, won, makes, onfire_makes):
    """Prize in whole dollars, or None if the result pays nothing."""
    if game == "pop_shot":
        if makes <= 0 and onfire_makes <= 0:
            return 0
        mult = 1.1 ** (level - 1)
        raw = (makes * 10 + onfire_makes * 15) * mult
        return int(raw + 0.5)
    if not won:
        return 0
    mult = 1.1 ** (level - 1)
    return int(500 * mult + 0.5)


@api_router.post("/center-prize/award")
async def center_prize_award(data: dict):
    player_id = data.get("player_id")
    game = data.get("game")
    if game not in CENTER_PRIZE_GAMES:
        raise HTTPException(status_code=400, detail="Unknown center game")
    try:
        level = int(data.get("level", 1))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid level")
    if level < 1 or level > CENTER_PRIZE_GAMES[game]["max_level"]:
        raise HTTPException(status_code=400, detail="Level out of range for this game")
    won = bool(data.get("won", False))
    try:
        makes = int(data.get("makes", 0))
        onfire_makes = int(data.get("onfire_makes", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid shot counts")
    if makes < 0 or makes > 100 or onfire_makes < 0 or onfire_makes > makes:
        raise HTTPException(status_code=400, detail="Shot counts out of range")
    prize = _center_prize_amount(game, level, won, makes, onfire_makes)
    if prize <= 0:
        return {"game": game, "level": level, "prize": 0, "cash": None}
    player = await __DB__.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    await __DB__.players.update_one({"id": player_id}, {"$inc": {"cash": prize}})
    updated = await __DB__.players.find_one({"id": player_id})
    return {"game": game, "level": level, "prize": prize, "cash": updated.get("cash", 0)}


'''


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - center prize endpoint NOT added")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src

    if "def center_prize_award" in src and "CENTER_PRIZE_GAMES" in src:
        print("CENTER_PRIZE_ALREADY_APPLIED")
        return 0

    # DB handle detection (live code uses db; never guess silently).
    dm = re.search(r"\b(\w+)\.players\.", src)
    db = dm.group(1) if dm else None
    if not dm:
        print("WARNING: db handle anchor not found - center prize endpoint NOT added")
        return 1

    block = ENDPOINT.replace("__DB__", db)
    # Insertion point: before the __main__ guard when it exists (any
    # quote style), otherwise append at the end of the file. v1 only
    # tried a literal "\nif __name__ ==" and failed on the live file.
    m = re.search(r"\nif __name__ ==\s*[\"']__main__[\"']:", src)
    if m:
        src = src[:m.start()] + "\n" + block + src[m.start():]
        print("OK: center prize endpoint added (before __main__ guard)")
    else:
        src = src.rstrip() + "\n\n" + block
        print("OK: center prize endpoint added (appended at end of server.py)")

    if src == orig:
        print("CENTER_PRIZE_PARTIAL: nothing landed")
        return 1
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("CENTER_PRIZE_SYNTAX_FAIL: %s (server.py NOT written)" % e)
        return 1
    SERVER.write_text(src)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
