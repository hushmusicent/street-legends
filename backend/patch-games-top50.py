#!/usr/bin/env python3
"""Street Legends backend: Top 50 leaderboard for park + center games.

The user asked for a Top 50 page for all park and activity-center
games: who won the most, and each player's highest (best) score.

13 games tracked:
  Park:   baseball, soccer, tennis, one_on_one, basketball, football
  Center: pool, dartboard, card_table, dominoes, scrabble, chess_checkers, pop_shot

What this patch does to backend/server.py (5 sections, each idempotent):
  S1  Adds GAMES_TOP50 / GAMES_TOP50_SET and the _record_game_win()
      helper (wins +1, best = max(best, score)) before CENTER_PRIZE_GAMES.
  S2  center_prize_award(): after it awards cash (prize > 0), records
      the win. Score is (makes + onfire_makes) for pop_shot, else the
      "score" field from the request (defaults to 0).
  S3  ParkPvpRoomState gains an optional score field (default 0).
  S4  park_pvp_room_state(): the first time a winner is set on a room
      (room had no winner yet), records a win for that player in the
      room's game, with body.score. The winner must be host or guest.
  S5  New endpoints:
        POST /api/games/record-win {player_id, game, score}
          Direct recording path (for park PvC wins from the frontend).
        GET  /api/games/top50?game=all|<game>
          game=all totals wins across all 13 games and takes the max
          best; a single game ranks by that game's wins/best only.
          Sorted by wins desc, then best desc. Top 50 only, wins > 0.
          Returns [{rank, id, name, level, wins, best, profile_pic}].

Run from /app: python3 backend/patch-games-top50.py
Then Deploy (backend). The frontend patch is separate
(frontend/patch-games-top50-frontend.py).
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "GAMES_TOP50_OK"

# ---- S1: helper + game set, inserted before CENTER_PRIZE_GAMES ----
HELPER = '''# ============== GAMES TOP 50 LEADERBOARD ==============
# Wins + best scores for the 13 park + activity-center games.
# Park games: baseball, soccer, tennis, one_on_one, basketball, football.
# Center games: pool, dartboard, card_table, dominoes, scrabble, chess_checkers, pop_shot.
# Stored per player as game_stats.<game>.wins / game_stats.<game>.best.
GAMES_TOP50 = ["baseball", "soccer", "tennis", "one_on_one", "basketball", "football",
               "pool", "dartboard", "card_table", "dominoes", "scrabble", "chess_checkers", "pop_shot"]
GAMES_TOP50_SET = set(GAMES_TOP50)


async def _record_game_win(player_id, game, score):
    """Record one win for a game: wins +1, best = max(best, score)."""
    if game not in GAMES_TOP50_SET:
        return
    try:
        score = int(score)
    except (TypeError, ValueError):
        score = 0
    if score < 0:
        score = 0
    await db.players.update_one(
        {"id": player_id},
        {"$inc": {f"game_stats.{game}.wins": 1},
         "$max": {f"game_stats.{game}.best": score}},
    )


'''
HELPER_ANCHOR = "CENTER_PRIZE_GAMES = {"
HELPER_SENTINEL = "GAMES_TOP50_SET = set(GAMES_TOP50)"

# ---- S2: center_prize_award() win recording ----
CENTER_ANCHOR = '''    await db.players.update_one({"id": player_id}, {"$inc": {"cash": prize}})
    updated = await db.players.find_one({"id": player_id})'''
CENTER_NEW = '''    await db.players.update_one({"id": player_id}, {"$inc": {"cash": prize}})
    # Top 50: record the win. Pop Shot scores by makes; other center games
    # send no score, so best stays 0 and only the win counts.
    if game == "pop_shot":
        _top50_score = makes + onfire_makes
    else:
        try:
            _top50_score = int(data.get("score", 0))
        except (TypeError, ValueError):
            _top50_score = 0
    await _record_game_win(player_id, game, _top50_score)
    updated = await db.players.find_one({"id": player_id})'''
CENTER_SENTINEL = "_record_game_win(player_id, game, _top50_score)"

# ---- S3: ParkPvpRoomState.score field ----
MODEL_ANCHOR = '''class ParkPvpRoomState(BaseModel):
    player_id: str
    state: dict = {}
    status: str = ""
    winner: str = ""'''
MODEL_NEW = '''class ParkPvpRoomState(BaseModel):
    player_id: str
    state: dict = {}
    status: str = ""
    winner: str = ""
    score: int = 0'''
MODEL_SENTINEL = "    score: int = 0"

# ---- S4: park_pvp_room_state() win recording ----
STATE_ANCHOR = '''    await db.park_pvp_rooms.update_one({"code": code}, {"$set": update})
    room = await db.park_pvp_rooms.find_one({"code": code})'''
STATE_NEW = '''    await db.park_pvp_rooms.update_one({"code": code}, {"$set": update})
    # Top 50: the first winner set on a room records one win for that player.
    # room here is still the pre-update doc, so room.get("winner") is empty
    # only when no winner was set before this post.
    if body.winner and not room.get("winner") and body.winner in (room["host_id"], room["guest_id"]):
        await _record_game_win(body.winner, room.get("game", "baseball"), body.score)
    room = await db.park_pvp_rooms.find_one({"code": code})'''
STATE_SENTINEL = '_record_game_win(body.winner, room.get("game", "baseball"), body.score)'

# ---- S5: record-win + top50 endpoints, after center_prize_award ----
ENDPOINTS_ANCHOR = '''    return {"game": game, "level": level, "prize": prize, "cash": updated.get("cash", 0)}'''
ENDPOINTS = '''    return {"game": game, "level": level, "prize": prize, "cash": updated.get("cash", 0)}


class GamesRecordWin(BaseModel):
    player_id: str
    game: str
    score: int = 0


@api_router.post("/games/record-win")
async def games_record_win(body: GamesRecordWin):
    """Direct Top 50 win recording (used by park PvC wins)."""
    if body.game not in GAMES_TOP50_SET:
        raise HTTPException(status_code=400, detail="Unknown game")
    player = await db.players.find_one({"id": body.player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    await _record_game_win(body.player_id, body.game, body.score)
    return {"ok": True, "game": body.game}


@api_router.get("/games/top50")
async def games_top50(game: str = "all"):
    """Top 50 players by wins (then best score) for park + center games.

    game=all totals wins across all 13 games and takes the max best;
    a single game name ranks by that game's wins/best only.
    """
    if game != "all" and game not in GAMES_TOP50_SET:
        raise HTTPException(status_code=400, detail="Unknown game")
    players = await db.players.find(
        {},
        {"id": 1, "name": 1, "level": 1, "profile_pic": 1, "game_stats": 1},
    ).to_list(10000)
    rows = []
    for p in players:
        stats = p.get("game_stats") or {}
        if game == "all":
            wins = 0
            best = 0
            for g in GAMES_TOP50:
                entry = stats.get(g) or {}
                wins += int(entry.get("wins", 0) or 0)
                best = max(best, int(entry.get("best", 0) or 0))
        else:
            entry = stats.get(game) or {}
            wins = int(entry.get("wins", 0) or 0)
            best = int(entry.get("best", 0) or 0)
        if wins <= 0:
            continue
        rows.append({
            "id": p["id"],
            "name": p.get("name", "Player"),
            "level": p.get("level", 1),
            "wins": wins,
            "best": best,
            "profile_pic": p.get("profile_pic"),
        })
    rows.sort(key=lambda r: (-r["wins"], -r["best"]))
    return [{"rank": i + 1, **r} for i, r in enumerate(rows[:50])]'''
ENDPOINTS_SENTINEL = '"/games/top50"'


def replace_once(src, anchor, new, section):
    """Replace anchor exactly once; return (new_src, status)."""
    n = src.count(anchor)
    if n == 0:
        print(f"GAMES_TOP50_{section}_ANCHOR_FAIL: anchor not found (nothing changed for this section)")
        return src, False
    if n > 1:
        print(f"GAMES_TOP50_{section}_ANCHOR_FAIL: anchor occurs {n} times, expected 1 (nothing changed for this section)")
        return src, False
    return src.replace(anchor, new, 1), True


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - NOT fixed")
        return 1
    src = SERVER.read_text(errors="ignore")
    orig = src
    ok = True

    # S1: helper + game set
    if HELPER_SENTINEL in src:
        print("GAMES_TOP50_HELPER_ALREADY_APPLIED")
    else:
        src, good = replace_once(src, HELPER_ANCHOR, HELPER + HELPER_ANCHOR, "HELPER")
        ok = ok and good
        if good:
            print("OK: _record_game_win helper + 13-game set added")

    # S2: center_prize_award hook
    if CENTER_SENTINEL in src:
        print("GAMES_TOP50_CENTER_ALREADY_APPLIED")
    else:
        src, good = replace_once(src, CENTER_ANCHOR, CENTER_NEW, "CENTER")
        ok = ok and good
        if good:
            print("OK: center_prize_award now records Top 50 wins")

    # S3: ParkPvpRoomState.score
    if MODEL_SENTINEL in src:
        print("GAMES_TOP50_MODEL_ALREADY_APPLIED")
    else:
        src, good = replace_once(src, MODEL_ANCHOR, MODEL_NEW, "MODEL")
        ok = ok and good
        if good:
            print("OK: ParkPvpRoomState gained score field")

    # S4: park_pvp_room_state hook
    if STATE_SENTINEL in src:
        print("GAMES_TOP50_STATE_ALREADY_APPLIED")
    else:
        src, good = replace_once(src, STATE_ANCHOR, STATE_NEW, "STATE")
        ok = ok and good
        if good:
            print("OK: park PvP winner now records a Top 50 win (first winner only)")

    # S5: endpoints
    if ENDPOINTS_SENTINEL in src:
        print("GAMES_TOP50_ENDPOINTS_ALREADY_APPLIED")
    else:
        src, good = replace_once(src, ENDPOINTS_ANCHOR, ENDPOINTS, "ENDPOINTS")
        ok = ok and good
        if good:
            print("OK: POST /games/record-win + GET /games/top50 added")

    if src == orig:
        print("GAMES_TOP50_NOOP (nothing changed)")
        return 0 if ok else 1

    # Safety: the patched file must still be valid Python.
    try:
        compile(src, "server.py", "exec")
    except SyntaxError as e:
        print(f"GAMES_TOP50_VERIFY_FAIL: patched server.py does not compile: {e} (nothing written)")
        return 1
    if "_record_game_win" not in src or '"/games/top50"' not in src or '"/games/record-win"' not in src:
        print("GAMES_TOP50_VERIFY_FAIL: helper or endpoints missing after edit (nothing written)")
        return 1

    SERVER.write_text(src)
    if ok:
        print(MARKER)
        return 0
    print("GAMES_TOP50_PARTIAL: some sections failed (see above) - applied sections were written")
    return 1


if __name__ == "__main__":
    sys.exit(main())
