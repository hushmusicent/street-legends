#!/usr/bin/env python3
"""Street Legends shootout timer stale-closure fix (frontend, Expo Go first).

Bug (live-proven shape, shootout-simulator.tsx):
  - The map handler passes gameId: gameData.game_id to /shootout-simulator,
    but the simulator's route params do NOT read gameId, so it starts a
    SECOND backend game and ignores the handler's game.
  - startGame awaits apiStartShootout, calls setGameId, and THEN creates the
    countdown timer interval. That interval captures endGame from BEFORE
    setGameId, so a timer-expired game ends with gameId=null and the
    `if (gameId && playerId)` guard SKIPS complete() silently: local rewards
    display, no cash, no rep, no cooldown, no toast.

Fix (this patch, shootout-simulator.tsx only, plus a pattern check of the
other simulator screens):
  1. Read the route gameId param; when present, use it once and do NOT
     start a second backend game. A later start (rematch) starts fresh.
  2. Mirror hitsRef: add gameIdRef, keep it in sync with every setGameId
     call and with the route gameId; endGame completes with
     gameIdRef.current (falling back to routeGameId, then state).
  3. No more silent skip: endGame with no gameId at all shows the same
     'Rewards may not have saved' error toast as a failed complete.
  4. Other simulator screens (car-chase, runaway, package-grab, castle) are
     checked for the SAME pattern only. A file that does not match is left
     byte-unchanged and reported SKIPPED; a file that matches exactly is
     fixed with the same ref edits.

Idempotent: a second run prints SHOOTOUT_TIMER_FIX_FRONTEND_ALREADY_APPLIED
and changes nothing. Required anchors missed -> WARNING lines, exit 1, and
the shootout file is NOT written (all-or-nothing, no half-applied fix).
No emoji anywhere; literal characters only.
"""
import re
import sys
from pathlib import Path

MARKER = "SHOOTOUT_TIMER_FIX"
OK = "SHOOTOUT_TIMER_FIX_FRONTEND_OK"
ALREADY = "SHOOTOUT_TIMER_FIX_FRONTEND_ALREADY_APPLIED"

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
FRONTEND = ROOT / "frontend" / "app"
SIM = FRONTEND / "shootout-simulator.tsx"
OTHER_SIMS = [
    "car-chase.tsx",
    "runaway-simulator.tsx",
    "package-grab.tsx",
    "castle-levels.tsx",
]

warnings = []


def warn(msg):
    warnings.append(msg)
    print(f"WARNING: {msg}")


def replace_once(text, old, new, label):
    """Replace exactly one occurrence; return (new_text, ok)."""
    if old not in text:
        warn(f"{label} anchor not matched - edit SKIPPED")
        return text, False
    if text.count(old) != 1:
        warn(f"{label} anchor not unique ({text.count(old)} hits) - edit SKIPPED")
        return text, False
    return text.replace(old, new, 1), True


def fix_shootout(src):
    """Apply edits E1-E7 to the shootout simulator. Returns (text, ok)."""
    ok = True
    text = src

    # --- E1: read the route gameId param ---
    old_params = (
        "const { shootoutId, shootoutName, difficulty, standalone } = useLocalSearchParams<{"
    )
    new_params = (
        "const { shootoutId, shootoutName, difficulty, standalone, gameId: routeGameId } = useLocalSearchParams<{"
    )
    if "routeGameId" in text:
        print("params: route gameId already read (SKIP)")
    else:
        text, good = replace_once(text, old_params, new_params, "params destructure")
        ok = ok and good
        old_type = "    standalone?: string;\n  }>();"
        new_type = "    standalone?: string;\n    gameId?: string;\n  }>();"
        text, good = replace_once(text, old_type, new_type, "params type")
        ok = ok and good

    # --- E2: gameIdRef + consumed ref, right after the gameId state line ---
    old_state = "  const [gameId, setGameId] = useState<string | null>(null);"
    new_state = (
        old_state
        + "\n  const gameIdRef = useRef<string | null>(null); // SHOOTOUT_TIMER_FIX: mirrors gameId so timer callbacks never see a stale null"
        + "\n  const routeGameIdConsumedRef = useRef(false); // SHOOTOUT_TIMER_FIX: route gameId is used once only, so a rematch starts a fresh game"
    )
    if "gameIdRef" in text:
        print("refs: gameIdRef already present (SKIP)")
    else:
        text, good = replace_once(text, old_state, new_state, "gameIdRef declaration")
        ok = ok and good

    # --- E3+E4: route-gameId branch + ref sync, scoped to startGame ---
    start_at = text.find("const startGame")
    end_at = text.find("const endGame", start_at) if start_at != -1 else -1
    if start_at == -1 or end_at == -1:
        warn("startGame/endGame region not found - route-branch and ref-sync SKIPPED")
        ok = False
    else:
        region = text[start_at:end_at]
        old_first_if = "    if (!isStandalone && playerId && shootoutId) {"
        new_first_if = (
            "    // SHOOTOUT_TIMER_FIX: the map handler already created this game - use its gameId, do not start a second game\n"
            "    if (routeGameId && !routeGameIdConsumedRef.current) {\n"
            "      routeGameIdConsumedRef.current = true;\n"
            "      newGameId = routeGameId;\n"
            "      setGameId(routeGameId);\n"
            "      gameIdRef.current = routeGameId;\n"
            "    } else if (!isStandalone && playerId && shootoutId) {"
        )
        if "routeGameIdConsumedRef.current = true" in region:
            print("startGame: route branch already present (SKIP)")
        elif old_first_if not in region:
            warn("startGame first-if anchor not matched - route branch SKIPPED")
            ok = False
        else:
            region = region.replace(old_first_if, new_first_if, 1)
        # Sync the ref at every setGameId(newGameId) inside startGame.
        if region.count("setGameId(newGameId);") == 0:
            warn("startGame setGameId sites not found - ref sync SKIPPED")
            ok = False
        else:
            region = region.replace(
                "setGameId(newGameId);",
                "setGameId(newGameId);\n        gameIdRef.current = newGameId;",
            )
        text = text[:start_at] + region + text[end_at:]

    # --- E5: endGame reads the ref, not stale state ---
    old_guard = (
        "    if (gameId && playerId) {\n"
        "      try {\n"
        "        const result = await apiCompleteShootout(gameId, currentHits, isStandalone);"
    )
    new_guard = (
        "    // SHOOTOUT_TIMER_FIX: read the ref, not state - the timer interval captures endGame from before setGameId\n"
        "    const effectiveGameId = gameIdRef.current || routeGameId || gameId;\n"
        "    if (effectiveGameId && playerId) {\n"
        "      try {\n"
        "        const result = await apiCompleteShootout(effectiveGameId, currentHits, isStandalone);"
    )
    if "effectiveGameId" in text:
        print("endGame: ref guard already present (SKIP)")
    else:
        text, good = replace_once(text, old_guard, new_guard, "endGame guard + complete call")
        ok = ok and good

    # --- E6: no more silent skip ---
    old_tail = (
        "        showGameToast('Rewards may not have saved. Check your balance.', 'error');\n"
        "      }\n"
        "    }\n"
        "\n"
        "    // Show results after a short delay"
    )
    new_tail = (
        "        showGameToast('Rewards may not have saved. Check your balance.', 'error');\n"
        "      }\n"
        "    } else {\n"
        "      // SHOOTOUT_TIMER_FIX: never present local rewards as paid when no game session exists\n"
        "      showGameToast('Rewards may not have saved. Check your balance.', 'error');\n"
        "    }\n"
        "\n"
        "    // Show results after a short delay"
    )
    if text.count(old_tail) == 1:
        text = text.replace(old_tail, new_tail, 1)
    elif "never present local rewards as paid" in text:
        print("endGame: silent-skip toast already present (SKIP)")
    else:
        warn("endGame silent-skip tail anchor not matched - toast SKIPPED")
        ok = False

    # --- E7 (optional): endGame deps include routeGameId ---
    old_deps = "}, [level, isStandalone, playerId, gameId, setPlayer, invalidateMapQueries, activePopups]);"
    new_deps = "}, [level, isStandalone, playerId, gameId, routeGameId, setPlayer, invalidateMapQueries, activePopups]);"
    if new_deps in text or old_deps not in text:
        print("endGame deps: already current or anchor absent (optional, SKIP)")
    else:
        text = text.replace(old_deps, new_deps, 1)

    return text, ok


def check_other_sim(path):
    """Report FIXED/SKIPPED for one other simulator screen.

    The shootout pattern is ALL of: a gameId state value, a setInterval
    timer that calls endGame(), an endGame guarded on the gameId state
    value, and no gameIdRef. Anything else is SKIPPED and left unchanged.
    """
    if not path.exists():
        print(f"OTHER_SIM {path.name}: SKIPPED: file not found")
        return path.read_text(errors="ignore") if False else None
    src = path.read_text(errors="ignore")
    has_state = "const [gameId, setGameId] = useState<string | null>(null);" in src
    has_timer_end = bool(re.search(r"setInterval\([\s\S]{0,400}?endGame\(\)", src))
    has_guard = "if (gameId && playerId) {" in src
    has_ref = "gameIdRef" in src
    if not (has_state and has_timer_end and has_guard):
        print(
            f"OTHER_SIM {path.name}: SKIPPED: no matching pattern "
            f"(state={has_state} timer_end={has_timer_end} guard={has_guard})"
        )
        return src
    if has_ref:
        print(f"OTHER_SIM {path.name}: SKIPPED: gameIdRef already present")
        return src
    # Exact-shape match: apply the same mechanical ref edits.
    text = src.replace(
        "const [gameId, setGameId] = useState<string | null>(null);",
        "const [gameId, setGameId] = useState<string | null>(null);\n"
        "  const gameIdRef = useRef<string | null>(null); // SHOOTOUT_TIMER_FIX",
        1,
    )
    text = re.sub(
        r"setGameId\(([^)]+)\);",
        lambda m: f"setGameId({m.group(1)});\n        gameIdRef.current = {m.group(1)};",
        text,
    )
    m = re.search(r"await (\w+)\(gameId, ", text)
    if m:
        text = text.replace(
            "if (gameId && playerId) {",
            "const effectiveGameId = gameIdRef.current || gameId;\n    if (effectiveGameId && playerId) {",
            1,
        )
        text = text.replace(f"await {m.group(1)}(gameId, ", f"await {m.group(1)}(effectiveGameId, ", 1)
        path.write_text(text)
        print(f"OTHER_SIM {path.name}: FIXED: ref guard applied")
        return text
    print(f"OTHER_SIM {path.name}: SKIPPED: complete-call shape differs - left unchanged, needs manual review")
    warn(f"{path.name} matches timer pattern but complete-call shape differs - NOT modified")
    return src


def main():
    if not SIM.exists():
        warn(f"shootout-simulator.tsx not found at {SIM} - nothing changed")
        return 1
    src = SIM.read_text(errors="ignore")
    if MARKER in src:
        print(ALREADY)
        return 0
    new_src, ok = fix_shootout(src)
    if not ok:
        print("SHOOTOUT_TIMER_FIX_FRONTEND_NOT_APPLIED: see WARNING lines above; file NOT written")
        return 1
    SIM.write_text(new_src)
    print(f"shootout-simulator.tsx: FIXED (params + ref + route branch + ref guard + silent-skip toast)")
    for name in OTHER_SIMS:
        check_other_sim(FRONTEND / name)
    print(OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
