#!/usr/bin/env python3
"""Fix Castle Assault (settings) Level 1: no enemies + no payout.

Root cause (found from the user's screenshots + live code read 2026-11-11):
Castle Assault is launched from settings with params {standalone: 'true'}.
In standalone mode the level select is skipped (showLevelSelect=false), but
there is NO auto-start for standalone mode — the only auto-start is for
random/map mode. So startLevel() is never called on mount:
  - generateLevel() never runs, so blocks=[] and enemies=[] stay empty.
    Level 1 "Training Ground" shows a cannon with NO enemies and NO blocks.
    Firing once makes remainingEnemies===0, so it counts as a WIN.
  - startStandaloneCastle() is only called inside startLevel(), so no
    backend session is created and gameSessionId stays null. On win, the
    code only submits to the backend if gameSessionId is set; otherwise it
    just shows the local config rewards (+$25 / +12 XP) and never calls
    completeCastleGame. The map cash never moves ($1,813,412 before and after).

Fix: auto-start Level 1 when the screen mounts in standalone mode (with a
ref guard so it only starts once). This mirrors the existing random-mode
auto-start. startLevel() generates the level (1 enemy, 3 blocks for Level 1)
and creates the backend session, so the win then submits to the backend and
the 50% practice payout lands in the player total.

This is a FRONTEND patch: run in /app, then check in Expo Go first.
Marker: CASTLE_ASSAULT_AUTOSTART_OK
"""
import sys
from pathlib import Path

FILE = Path("frontend/app/castle-levels.tsx")

ANCHOR = """    } else if (!isRandomMode) {
      setGameSessionId(null);
    }
  };

  // Pan responder for aiming
"""

REPLACEMENT = """    } else if (!isRandomMode) {
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


def main():
    if not FILE.exists():
        print("CASTLE_ASSAULT_AUTOSTART_FAIL frontend/app/castle-levels.tsx not found")
        return 1
    src = FILE.read_text(encoding="utf-8")

    if "standaloneStartedRef" in src:
        print("CASTLE_ASSAULT_AUTOSTART_ALREADY_APPLIED")
        return 0

    if ANCHOR not in src:
        print("CASTLE_ASSAULT_AUTOSTART_FAIL anchor not found (file may have changed)")
        return 1

    src = src.replace(ANCHOR, REPLACEMENT, 1)

    # Verify: the auto-start is present, startLevel still intact, and the
    # random-mode auto-start was not touched.
    checks = [
        "standaloneStartedRef",
        "startLevel(1);",
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
