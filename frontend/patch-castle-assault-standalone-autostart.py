#!/usr/bin/env python3
"""Fix Castle Assault (settings): Level 1 has no enemies + no payout, and
Level 2 (and any level) can also silently pay nothing.

Root causes (found from the user's screenshots + live code read 2026-11-11):
1. NO AUTO-START: Castle Assault is launched from settings with params
   {standalone: 'true'}. In standalone mode the level select is skipped
   (showLevelSelect=false), but there is NO auto-start — the only auto-start
   is for random/map mode. So startLevel() is never called on mount:
     - generateLevel() never runs, so blocks=[] and enemies=[] stay empty.
       Level 1 "Training Ground" shows a cannon with NO enemies and NO blocks.
       Firing once makes remainingEnemies===0, so it counts as a WIN.
     - startStandaloneCastle() is only called inside startLevel(), so no
       backend session is created and gameSessionId stays null. On win, the
       code only submits to the backend if gameSessionId is set; otherwise it
       just shows the local config rewards (+$25 / +12 XP) and never calls
       completeCastleGame. The map cash never moves ($1,813,412 before/after).
2. SILENT SESSION FAILURE (why Level 2 also didn't pay): startLevel() calls
   startStandaloneCastle(), but if that fails — e.g. the 15-min global
   cooldown is active because the player just played another mini-game —
   the .catch() quietly sets gameSessionId=null and the level plays on with
   NO session. The win shows the local +$35 / +18 XP but nothing is ever
   submitted, so nothing lands. The player gets no warning. (Confirmed live:
   Mayor Veno had an active global cooldown when he played Level 2.)

Fix (frontend, castle-levels.tsx):
  1. Auto-start Level 1 when the screen mounts in standalone mode (ref
     guard, once). This mirrors the random-mode auto-start. startLevel()
     generates the level (1 enemy, 3 blocks for Level 1) and creates the
     backend session, so the win submits and the 50% practice payout lands.
  2. When startStandaloneCastle() fails, show a clear error toast with the
     server's reason (e.g. "Mini-game cooldown active! Wait 14m...") so the
     player knows this level will NOT pay out, instead of silently playing
     for fake rewards.

This is a FRONTEND patch: run in /app, then check in Expo Go first.
Marker: CASTLE_ASSAULT_AUTOSTART_OK
"""
import sys
from pathlib import Path

FILE = Path("frontend/app/castle-levels.tsx")

ANCHOR_AUTOSTART = """    } else if (!isRandomMode) {
      setGameSessionId(null);
    }
  };

  // Pan responder for aiming
"""

REPLACEMENT_AUTOSTART = """    } else if (!isRandomMode) {
      setGameSessionId(null);
    }
  };

  // Auto-start Level 1 when launched from settings (standalone mode).
  // The level select is skipped in standalone mode, but without this no
  // level is ever started: Level 1 has no enemies/blocks and no backend
  // session, so the win shows local rewards but never pays out.
  const standaloneStartedRef = useRef(false);
  useEffect(() => {
    if (isStandalone && playerId && !isRandomMode && !standaloneStartedRef.current) {
      standaloneStartedRef.current = true;
      startLevel(1);
    }
  }, [isStandalone, playerId]);

  // Pan responder for aiming
"""

# Show a clear error when the rewards session cannot be created (e.g. the
# 15-min global cooldown is active), instead of silently playing for nothing.
OLD_CATCH = """      startStandaloneCastle(playerId, level)
        .then((s) => setGameSessionId(s.game_id))
        .catch(() => setGameSessionId(null));"""

NEW_CATCH = """      startStandaloneCastle(playerId, level)
        .then((s) => setGameSessionId(s.game_id))
        .catch((err: any) => {
          setGameSessionId(null);
          const msg = err?.response?.data?.detail || 'Could not start a rewards session - this level will not pay out.';
          showGameToast({ type: 'error', title: 'No Rewards Session', message: msg, duration: 4000 });
        });"""


def main():
    if not FILE.exists():
        print("CASTLE_ASSAULT_AUTOSTART_FAIL frontend/app/castle-levels.tsx not found")
        return 1
    src = FILE.read_text(encoding="utf-8")

    if "standaloneStartedRef" in src and "No Rewards Session" in src:
        print("CASTLE_ASSAULT_AUTOSTART_ALREADY_APPLIED")
        return 0

    if ANCHOR_AUTOSTART not in src:
        print("CASTLE_ASSAULT_AUTOSTART_FAIL autostart anchor not found (file may have changed)")
        return 1
    if OLD_CATCH not in src:
        print("CASTLE_ASSAULT_AUTOSTART_FAIL session catch block not found (file may have changed)")
        return 1

    src = src.replace(ANCHOR_AUTOSTART, REPLACEMENT_AUTOSTART, 1)
    src = src.replace(OLD_CATCH, NEW_CATCH, 1)

    # Verify: both changes present, core flows intact.
    checks = [
        "standaloneStartedRef",
        "startLevel(1);",
        "No Rewards Session",
        "const startLevel = (level: number) => {",
        "if (isRandomMode && playerId) {",
        "startStandaloneCastle(playerId, level)",
        "completeCastleGame(gameSessionId, eliminatedCount, didWin, isStandalone)",
    ]
    for needle in checks:
        if needle not in src:
            print("CASTLE_ASSAULT_AUTOSTART_FAIL missing after edit: %s" % needle)
            return 1
    if src.count("standaloneStartedRef") != 3:
        print("CASTLE_ASSAULT_AUTOSTART_FAIL unexpected standaloneStartedRef count")
        return 1

    FILE.write_text(src, encoding="utf-8")
    print("CASTLE_ASSAULT_AUTOSTART_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
