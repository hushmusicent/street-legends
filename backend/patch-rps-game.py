#!/usr/bin/env python3
"""Rock Paper Scissors PvP — one round, no betting, no score.

User (2026-11-12): "Put it to the game." (Approved the simple design:
no start menu, single round. A taps RPS on B's player menu -> A waits
for B to respond -> B says YES -> a small popup opens on BOTH phones
to pick Rock/Paper/Scissors -> result shows on BOTH screens with the
winner/loser.)

Adds (backend/server.py), all under db.rps_games:
  POST /api/rps/challenge  body {challenger_id, opponent_id}
       Validates two different existing players. Creates a pending game.
  GET  /api/rps/pending/{player_id}
       -> {incoming: [...], outgoing: [...]} — incoming = pending games
       the player must answer; outgoing = games they challenged. Only
       pending games; stale (>10 min) ones are marked expired and excluded.
  POST /api/rps/respond  body {game_id, player_id, accept}
       Only the OPPONENT may respond (challenger gets 400). accept=false
       -> "declined". accept=true -> "accepted".
  POST /api/rps/throw  body {game_id, player_id, throw}
       throw must be rock/paper/scissors; only a party to the game; only
       when status is "accepted"; one throw per player (second throw 400).
       When BOTH have thrown -> winner is computed (rock beats scissors,
       scissors beats paper, paper beats rock; same throw = draw), status
       "finished", winner_id set (null on draw). The opponent's throw is
       NEVER revealed before both have thrown.
  GET  /api/rps/game/{game_id}?player_id=...
       Game state for that player: status, both names, your_throw,
       opponent_has_thrown, and when finished also both throws + winner_id
       + result from that player's perspective.
  POST /api/rps/cancel  body {game_id, player_id}
       Only the challenger may cancel a pending game -> "cancelled".

No cash, no betting, no XP — just the game. Games expire after 10 min.

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: RPS_GAME_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

ANCHOR = "# PARK_NEARBY: real parks from OpenStreetMap."

BLOCK = '''# RPS_GAME: Rock Paper Scissors PvP — single round, no betting. A
# challenges B from the player menu; B says yes/no; both pick in a popup;
# the result shows on both screens. Games live in db.rps_games and expire
# after 10 minutes.
RPS_TTL_SECONDS = 600
RPS_THROWS = ("rock", "paper", "scissors")
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}


def _rps_age_seconds(game):
    """Seconds since the game was created (huge number if unparseable)."""
    try:
        created = datetime.fromisoformat(str(game.get("created_at", "")))
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - created).total_seconds()
    except Exception:
        return 10 ** 9


def _rps_result_for(game, viewer_id):
    """'win' / 'lose' / 'draw' from the viewer's side — None until finished."""
    if game.get("status") != "finished":
        return None
    winner_id = game.get("winner_id")
    if winner_id is None:
        return "draw"
    return "win" if winner_id == viewer_id else "lose"


def _rps_public(game, viewer_id):
    """Game shaped for the API. The opponent's throw is only included once
    the game is finished — never reveal it early."""
    finished = game.get("status") == "finished"
    viewer_is_challenger = viewer_id == game.get("challenger_id")
    other_id = game.get("opponent_id") if viewer_is_challenger else game.get("challenger_id")
    other_name = game.get("opponent_name") if viewer_is_challenger else game.get("challenger_name")
    your_throw = game.get("challenger_throw") if viewer_is_challenger else game.get("opponent_throw")
    opp_throw = game.get("opponent_throw") if viewer_is_challenger else game.get("challenger_throw")
    return {
        "game_id": game.get("game_id"),
        "challenger_id": game.get("challenger_id"),
        "challenger_name": game.get("challenger_name"),
        "opponent_id": game.get("opponent_id"),
        "opponent_name": game.get("opponent_name"),
        "other_id": other_id,
        "other_name": other_name,
        "status": game.get("status"),
        "your_throw": your_throw,
        "opponent_has_thrown": opp_throw is not None,
        "opponent_throw": opp_throw if finished else None,
        "throws": (
            {"challenger_throw": game.get("challenger_throw"), "opponent_throw": game.get("opponent_throw")}
            if finished else None
        ),
        "winner_id": game.get("winner_id") if finished else None,
        "result": _rps_result_for(game, viewer_id),
        "summary": f"{game.get('challenger_name', 'A player')} challenged you to Rock Paper Scissors",
        "created_at": game.get("created_at"),
    }


async def _rps_expire_stale(game):
    """Mark a pending game expired if it is older than the TTL. True if expired."""
    if game.get("status") == "pending" and _rps_age_seconds(game) > RPS_TTL_SECONDS:
        await db.rps_games.update_one({"game_id": game.get("game_id")}, {"$set": {"status": "expired"}})
        return True
    return False


@api_router.post("/rps/challenge")
async def rps_challenge(data: dict):
    """Challenge another player to Rock Paper Scissors. Creates a pending game."""
    challenger_id = data.get("challenger_id")
    opponent_id = data.get("opponent_id")
    if not challenger_id or not opponent_id or challenger_id == opponent_id:
        raise HTTPException(status_code=400, detail="challenger_id and opponent_id must be two different players")
    challenger = await db.players.find_one({"id": challenger_id})
    if not challenger:
        raise HTTPException(status_code=404, detail="Challenger not found")
    opponent = await db.players.find_one({"id": opponent_id})
    if not opponent:
        raise HTTPException(status_code=404, detail="Opponent not found")
    game = {
        "game_id": str(uuid.uuid4()),
        "challenger_id": challenger_id,
        "challenger_name": challenger.get("name", "a player"),
        "opponent_id": opponent_id,
        "opponent_name": opponent.get("name", "a player"),
        "status": "pending",
        "challenger_throw": None,
        "opponent_throw": None,
        "winner_id": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.rps_games.insert_one(game)
    return _rps_public(game, challenger_id)


@api_router.get("/rps/pending/{player_id}")
async def rps_pending(player_id: str):
    """Pending RPS games for a player: incoming (they must answer) + outgoing."""
    player = await db.players.find_one({"id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    games = await db.rps_games.find({"status": "pending"}).to_list(200)
    incoming = []
    outgoing = []
    for game in games:
        if player_id not in (game.get("challenger_id"), game.get("opponent_id")):
            continue
        if await _rps_expire_stale(game):
            continue
        public = _rps_public(game, player_id)
        if game.get("challenger_id") == player_id:
            outgoing.append(public)
        else:
            incoming.append(public)
    return {"incoming": incoming, "outgoing": outgoing}


@api_router.post("/rps/respond")
async def rps_respond(data: dict):
    """Answer a challenge. Only the OPPONENT may respond."""
    game_id = data.get("game_id")
    player_id = data.get("player_id")
    accept = data.get("accept")
    if not isinstance(accept, bool):
        raise HTTPException(status_code=400, detail="accept must be true or false")
    game = await db.rps_games.find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Game is " + str(game.get("status")) + " - no longer pending")
    if await _rps_expire_stale(game):
        raise HTTPException(status_code=400, detail="Game expired - it was over 10 minutes old")
    if player_id == game.get("challenger_id"):
        raise HTTPException(status_code=400, detail="The challenger cannot answer their own challenge - the other player must answer")
    if player_id != game.get("opponent_id"):
        raise HTTPException(status_code=400, detail="You are not a party to this game")
    new_status = "accepted" if accept else "declined"
    await db.rps_games.update_one({"game_id": game_id}, {"$set": {"status": new_status}})
    game["status"] = new_status
    return _rps_public(game, player_id)


@api_router.post("/rps/throw")
async def rps_throw(data: dict):
    """Throw rock / paper / scissors. One throw per player; when both have
    thrown the winner is computed and the game finishes."""
    game_id = data.get("game_id")
    player_id = data.get("player_id")
    throw = data.get("throw")
    if throw not in RPS_THROWS:
        raise HTTPException(status_code=400, detail="throw must be rock, paper or scissors")
    game = await db.rps_games.find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.get("status") != "accepted":
        raise HTTPException(status_code=400, detail="Game is " + str(game.get("status")) + " - not accepting throws")
    is_challenger = player_id == game.get("challenger_id")
    is_opponent = player_id == game.get("opponent_id")
    if not is_challenger and not is_opponent:
        raise HTTPException(status_code=400, detail="You are not a party to this game")
    field = "challenger_throw" if is_challenger else "opponent_throw"
    if game.get(field) is not None:
        raise HTTPException(status_code=400, detail="You already threw - one throw per player")
    await db.rps_games.update_one({"game_id": game_id}, {"$set": {field: throw}})
    game[field] = throw
    # Both thrown? Finish the game and compute the winner.
    if game.get("challenger_throw") is not None and game.get("opponent_throw") is not None:
        c = game.get("challenger_throw")
        o = game.get("opponent_throw")
        if c == o:
            winner_id = None
        elif RPS_BEATS[c] == o:
            winner_id = game.get("challenger_id")
        else:
            winner_id = game.get("opponent_id")
        await db.rps_games.update_one(
            {"game_id": game_id},
            {"$set": {"status": "finished", "winner_id": winner_id}},
        )
        game["status"] = "finished"
        game["winner_id"] = winner_id
    return _rps_public(game, player_id)


@api_router.get("/rps/game/{game_id}")
async def rps_get_game(game_id: str, player_id: str = ""):
    """Game state for one player. The opponent's throw stays hidden until
    both have thrown."""
    game = await db.rps_games.find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if player_id and player_id not in (game.get("challenger_id"), game.get("opponent_id")):
        raise HTTPException(status_code=400, detail="You are not a party to this game")
    return _rps_public(game, player_id or game.get("challenger_id"))


@api_router.post("/rps/cancel")
async def rps_cancel(data: dict):
    """Cancel my own pending challenge. Only the challenger may cancel."""
    game_id = data.get("game_id")
    player_id = data.get("player_id")
    game = await db.rps_games.find_one({"game_id": game_id})
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    if game.get("status") != "pending":
        raise HTTPException(status_code=400, detail="Game is " + str(game.get("status")) + " - no longer pending")
    if player_id != game.get("challenger_id"):
        raise HTTPException(status_code=400, detail="Only the challenger can cancel this challenge")
    await db.rps_games.update_one({"game_id": game_id}, {"$set": {"status": "cancelled"}})
    return {"ok": True, "status": "cancelled", "game_id": game_id}


'''


def main():
    if not SERVER.exists():
        print("RPS_GAME_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if ("async def rps_challenge(" in src and "async def rps_pending(" in src
            and "async def rps_respond(" in src and "async def rps_throw(" in src
            and "async def rps_get_game(" in src and "async def rps_cancel(" in src):
        print("RPS_GAME_ALREADY_APPLIED")
        return 0
    if ANCHOR not in src:
        print("RPS_GAME_FAIL anchor not found (file may have changed)")
        return 1
    src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
    for needle in (
        "async def rps_challenge(",
        "async def rps_pending(",
        "async def rps_respond(",
        "async def rps_throw(",
        "async def rps_get_game(",
        "async def rps_cancel(",
        "def _rps_public(",
        "def _rps_result_for(",
        "RPS_TTL_SECONDS = 600",
        "RPS_BEATS = ",
    ):
        if needle not in src:
            print("RPS_GAME_FAIL missing after edit: %s" % needle)
            return 1
    SERVER.write_text(src, encoding="utf-8")
    print("RPS_GAME_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
