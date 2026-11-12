#!/usr/bin/env python3
"""Car Chase (settings) pays 50% less + no silent fake session.

User (2026-11-11): "Not the cargo run the car chase" — the CAR CHASE (not
Package Grab) needs to pay 50% less. His screenshot showed +$455 cash,
+190 XP, +15 rep for an 8003m escape at 30s. That is the FULL local
calculation; the backend already halves standalone payouts, but the results
modal shows the un-halved frontend number, so the player sees $455 while
the server would only ever pay about half that.

Fix (frontend, car-chase.tsx):
  1. Halve the displayed rewards when isStandalone is true, right after
     calculateRewards() and before setGameRewards(). Cash, XP and rep are
     all halved (rep floored at 1), so the modal shows the real 50% amount
     (~$227 instead of $455) and matches what the backend pays.
     Map (non-standalone) games are untouched and keep full rewards.
  2. Stop masking a failed session with the fake gameId 'standalone'.
     When startStandaloneCarChase() fails (or there is no playerId), set
     gameId to null (so the complete call is skipped cleanly) and show a
     clear error toast with the server's reason, instead of letting the
     level play on and the complete 404 silently on the fake id.

This is a FRONTEND patch: run in /app, then check in Expo Go first.
Marker: CAR_CHASE_PAY_HALF_OK
"""
import sys
from pathlib import Path

FILE = Path("frontend/app/car-chase.tsx")

OLD_REWARDS = """    // Calculate rewards based on performance
    const rewards = calculateRewards(
      gameState.distance,
      timePlayedSeconds,
      difficulty,
      countyLineDistance,
      gameState.won
    );
    
    setGameRewards(rewards);"""

NEW_REWARDS = """    // Calculate rewards based on performance
    const rewards = calculateRewards(
      gameState.distance,
      timePlayedSeconds,
      difficulty,
      countyLineDistance,
      gameState.won
    );

    // Settings (standalone) games pay 50% — halve the displayed rewards so
    // the modal shows what the backend actually pays (~$227, not $455).
    if (isStandalone && gameState.won) {
      rewards.totalCash = Math.floor(rewards.totalCash / 2);
      rewards.totalXP = Math.floor(rewards.totalXP / 2);
      rewards.reputation = Math.max(1, Math.floor(rewards.reputation / 2));
    }
    
    setGameRewards(rewards);"""

OLD_START = """      try {
        if (playerId) {
          const session = await startStandaloneCarChase(playerId, difficulty);
          setGameId(session.game_id);
        } else {
          setGameId('standalone');
        }
      } catch (e: any) {
        console.log('Standalone start failed:', e?.response?.data?.detail || e?.message);
        setGameId('standalone');
      }"""

NEW_START = """      try {
        if (playerId) {
          const session = await startStandaloneCarChase(playerId, difficulty);
          setGameId(session.game_id);
        } else {
          setGameId(null);
          showGameToast({ type: 'error', title: 'No Rewards Session', message: 'Could not start a rewards session - this chase will not pay out.', duration: 4000 });
        }
      } catch (e: any) {
        console.log('Standalone start failed:', e?.response?.data?.detail || e?.message);
        setGameId(null);
        const msg = e?.response?.data?.detail || 'Could not start a rewards session - this chase will not pay out.';
        showGameToast({ type: 'error', title: 'No Rewards Session', message: msg, duration: 4000 });
      }"""


def main():
    if not FILE.exists():
        print("CAR_CHASE_PAY_HALF_FAIL frontend/app/car-chase.tsx not found")
        return 1
    src = FILE.read_text(encoding="utf-8")

    if "CAR_CHASE_PAY_HALF" in src or ("rewards.totalCash = Math.floor(rewards.totalCash / 2)" in src and "No Rewards Session" in src):
        print("CAR_CHASE_PAY_HALF_ALREADY_APPLIED")
        return 0

    if OLD_REWARDS not in src:
        print("CAR_CHASE_PAY_HALF_FAIL rewards block not found (file may have changed)")
        return 1
    if OLD_START not in src:
        print("CAR_CHASE_PAY_HALF_FAIL standalone start block not found (file may have changed)")
        return 1

    src = src.replace(OLD_REWARDS, NEW_REWARDS, 1)
    src = src.replace(OLD_START, NEW_START, 1)

    checks = [
        "rewards.totalCash = Math.floor(rewards.totalCash / 2)",
        "No Rewards Session",
        "const rewards = calculateRewards(",
        "startStandaloneCarChase(playerId, difficulty)",
        "completeCarChase(gameId, gameState.won",
    ]
    for needle in checks:
        if needle not in src:
            print("CAR_CHASE_PAY_HALF_FAIL missing after edit: %s" % needle)
            return 1
    if "setGameId('standalone')" in src:
        print("CAR_CHASE_PAY_HALF_FAIL fake gameId 'standalone' still present")
        return 1

    FILE.write_text(src, encoding="utf-8")
    print("CAR_CHASE_PAY_HALF_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
