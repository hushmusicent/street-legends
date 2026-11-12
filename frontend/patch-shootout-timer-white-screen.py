#!/usr/bin/env python3
"""Fix Shootout white 'Street Legends' screen when the timer runs out.

User (2026-11-11): "the shout out game still goes to this screen right
after the timer counts down before it shows the payout." The white screen
appears the moment the timer hits 0, BEFORE the results/payout modal ever
shows. This is a different spot from the DONE-button back-navigation (fixed
by the earlier patch-shootout-white-screen.py).

Root cause: endGame() is called TWICE when the timer ends.
  1. The timer interval's setTimeLeft updater calls endGame() directly
     when prev <= 1, AND sets timeLeft to 0.
  2. The useEffect watching timeLeft then sees timeLeft <= 0 and calls
     endGame() AGAIN (gameOver is still false in that closure because the
     state update is async).
The second endGame() re-submits the same game session to the backend
("Game already completed"), and the two overlapping async runs fight over
the same state. The results modal (setShowResults after a 500ms timeout)
never reliably appears, and the screen drops to the blank white root.

Fix (frontend, shootout-simulator.tsx):
  1. Remove the endGame() call from the timer interval's setTimeLeft
     updater. The interval only counts down to 0; the useEffect is the
     single place that calls endGame().
  2. Add an endGameCalledRef guard inside endGame() so it can only run
     once per game, even if the effect fires twice. Reset the guard in
     startGame().

This is a FRONTEND patch: run in /app, then check in Expo Go first.
Marker: SHOOTOUT_TIMER_WHITE_SCREEN_OK
"""
import sys
from pathlib import Path

FILE = Path("frontend/app/shootout-simulator.tsx")

# 1. Timer interval: stop calling endGame() from inside setTimeLeft.
OLD_TIMER = """    // Start timer
    timerIntervalRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          endGame();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);"""

NEW_TIMER = """    // Start timer — only count down to 0. The useEffect watching
    // timeLeft is the single place that calls endGame(), so it runs once.
    timerIntervalRef.current = setInterval(() => {
      setTimeLeft(prev => {
        if (prev <= 1) {
          return 0;
        }
        return prev - 1;
      });
    }, 1000);"""

# 2a. Add the once-per-game guard ref next to gameIdRef.
OLD_REF = """  const gameIdRef = useRef<string | null>(null); // SHOOTOUT_TIMER_FIX: mirrors gameId so timer callbacks never see a stale null"""

NEW_REF = """  const gameIdRef = useRef<string | null>(null); // SHOOTOUT_TIMER_FIX: mirrors gameId so timer callbacks never see a stale null
  const endGameCalledRef = useRef(false); // guards endGame so the timer-end effect can never run it twice"""

# 2b. Guard endGame() itself.
OLD_ENDGAME = """  // End game
  const endGame = useCallback(async () => {
    setGameOver(true);"""

NEW_ENDGAME = """  // End game
  const endGame = useCallback(async () => {
    if (endGameCalledRef.current) return;
    endGameCalledRef.current = true;
    setGameOver(true);"""

# 2c. Reset the guard when a new game starts (startGame sets gameOver false).
OLD_START = """    setGameStarted(true);
    setGameOver(false);
    setHits(0);"""

NEW_START = """    endGameCalledRef.current = false;
    setGameStarted(true);
    setGameOver(false);
    setHits(0);"""


def main():
    if not FILE.exists():
        print("SHOOTOUT_TIMER_WHITE_SCREEN_FAIL frontend/app/shootout-simulator.tsx not found")
        return 1
    src = FILE.read_text(encoding="utf-8")

    if "endGameCalledRef" in src:
        print("SHOOTOUT_TIMER_WHITE_SCREEN_ALREADY_APPLIED")
        return 0

    for label, old in (
        ("timer", OLD_TIMER),
        ("ref", OLD_REF),
        ("endgame", OLD_ENDGAME),
        ("start", OLD_START),
    ):
        if old not in src:
            print("SHOOTOUT_TIMER_WHITE_SCREEN_FAIL %s block not found (file may have changed)" % label)
            return 1

    src = src.replace(OLD_TIMER, NEW_TIMER, 1)
    src = src.replace(OLD_REF, NEW_REF, 1)
    src = src.replace(OLD_ENDGAME, NEW_ENDGAME, 1)
    src = src.replace(OLD_START, NEW_START, 1)

    checks = [
        "endGameCalledRef",
        "if (endGameCalledRef.current) return;",
        "endGameCalledRef.current = false;",
        "setShowResults(true)",
        "apiCompleteShootout(effectiveGameId, currentHits, isStandalone)",
    ]
    for needle in checks:
        if needle not in src:
            print("SHOOTOUT_TIMER_WHITE_SCREEN_FAIL missing after edit: %s" % needle)
            return 1
    # The interval must no longer call endGame directly.
    if "endGame();\n          return 0;" in src:
        print("SHOOTOUT_TIMER_WHITE_SCREEN_FAIL timer still calls endGame directly")
        return 1

    FILE.write_text(src, encoding="utf-8")
    print("SHOOTOUT_TIMER_WHITE_SCREEN_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
