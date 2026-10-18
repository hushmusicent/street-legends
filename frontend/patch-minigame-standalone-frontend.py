"""Street Legends frontend: wire practice-mode mini-games to the backend.
Run from repo root: python3 frontend/patch-minigame-standalone-frontend.py
Idempotent - safe to re-run.

Practice-mode (options panel) mini-games used game_id='standalone', so the
complete endpoints 404'd and winnings never reached the player's total.
The backend now has real standalone start endpoints; this patch makes the
frontend call them so practice games award the normal 50% rewards.

Changes:
  frontend/services/api.ts - add startStandaloneCastle/CarChase/Runaway/PackageGrab
  frontend/app/car-chase.tsx - standalone init creates a backend session
  frontend/app/runaway-simulator.tsx - same
  frontend/app/package-grab.tsx - same
  frontend/app/castle-levels.tsx - standalone level start creates a session,
    and results are submitted when a session exists (map or standalone)
"""
import sys
from pathlib import Path

API = Path("frontend/services/api.ts")
CAR = Path("frontend/app/car-chase.tsx")
RUN = Path("frontend/app/runaway-simulator.tsx")
PKG = Path("frontend/app/package-grab.tsx")
CASTLE = Path("frontend/app/castle-levels.tsx")

API_ADDITION = '''
// Standalone (practice mode) start endpoints - create real sessions so
// practice games award the 50% rewards via the normal complete endpoints.
export const startStandaloneCastle = async (playerId: string, level: number = 1) => {
  const response = await api.post(`/castles/standalone/start?player_id=${playerId}&level=${level}`);
  return response.data;
};

export const startStandaloneCarChase = async (playerId: string, level: number = 1) => {
  const response = await api.post(`/car-chases/standalone/start?player_id=${playerId}&level=${level}`);
  return response.data;
};

export const startStandaloneRunaway = async (playerId: string, level: number = 1) => {
  const response = await api.post(`/runaways/standalone/start?player_id=${playerId}&level=${level}`);
  return response.data;
};

export const startStandalonePackageGrab = async (playerId: string, level: number = 1) => {
  const response = await api.post(`/package-grabs/standalone/start?player_id=${playerId}&level=${level}`);
  return response.data;
};
'''


def replace_once(src: str, old: str, new: str, name: str) -> str:
    if new in src:
        print(f"SKIP: {name} already applied")
        return src
    if src.count(old) != 1:
        print(f"ERROR: anchor for '{name}' matched {src.count(old)}x. Aborting.")
        sys.exit(1)
    print(f"OK: {name}")
    return src.replace(old, new, 1)


def patch_api() -> int:
    if not API.exists():
        print(f"ERROR: {API} not found. Run from repo root.")
        sys.exit(1)
    src = API.read_text()
    before = src
    anchor = "export const completeShootout = async (gameId: string, hits: number, standalone: boolean = false) => {"
    if "startStandaloneCastle" not in src:
        if src.count(anchor) != 1:
            print(f"ERROR: api.ts anchor matched {src.count(anchor)}x. Aborting.")
            sys.exit(1)
        # insert the new functions BEFORE completeShootout
        src = src.replace(anchor, API_ADDITION.strip() + "\n\n" + anchor, 1)
        print("OK: standalone start functions added to api.ts")
    else:
        print("SKIP: standalone start functions already in api.ts")
    if src != before:
        API.write_text(src)
        return 1
    return 0


def patch_game_screen(path: Path, old_import: str, new_import: str,
                      start_fn: str, game_name: str) -> int:
    """Patch car-chase / runaway / package-grab standalone init."""
    if not path.exists():
        print(f"ERROR: {path} not found. Run from repo root.")
        sys.exit(1)
    src = path.read_text()
    before = src

    # 1. extend the api import
    src = replace_once(src, old_import, new_import, f"{game_name} api import")

    # 2. standalone init: create a real backend session instead of gameId='standalone'
    # (car-chase has an extra comment line; try both variants)
    old_init = """    if (isStandalone) {
      setGameId('standalone');
      setLoading(false);
      return;
    }"""
    old_init_alt = """    if (isStandalone) {
      // Standalone mode - no API call needed
      setGameId('standalone');
      setLoading(false);
      return;
    }"""
    new_init = """    if (isStandalone) {
      // Practice mode: create a real backend session so winnings are awarded (50%)
      try {
        if (playerId) {
          const session = await __START_FN__(playerId, difficulty);
          setGameId(session.game_id);
        } else {
          setGameId('standalone');
        }
      } catch (e: any) {
        console.log('Standalone start failed:', e?.response?.data?.detail || e?.message);
        setGameId('standalone');
      }
      setLoading(false);
      return;
    }""".replace("__START_FN__", start_fn)
    if old_init in src:
        src = replace_once(src, old_init, new_init, f"{game_name} standalone session")
    else:
        src = replace_once(src, old_init_alt, new_init, f"{game_name} standalone session")

    if src != before:
        path.write_text(src)
        return 1
    return 0


def patch_castle() -> int:
    if not CASTLE.exists():
        print(f"ERROR: {CASTLE} not found. Run from repo root.")
        sys.exit(1)
    src = CASTLE.read_text()
    before = src

    # 1. extend the api import
    src = replace_once(
        src,
        "import { API_URL, startRandomCastleGame, completeCastleGame } from '../services/api';",
        "import { API_URL, startRandomCastleGame, completeCastleGame, startStandaloneCastle } from '../services/api';",
        "castle api import",
    )

    # 2. startLevel: create a backend session for standalone practice levels
    old_start = """  const startLevel = (level: number) => {
    setCurrentLevel(level);
    generateLevel(level);
    setShowLevelSelect(false);
    structureHitRef.current = false; // Ensure reset on level start
  };"""
    new_start = """  const startLevel = (level: number) => {
    setCurrentLevel(level);
    generateLevel(level);
    setShowLevelSelect(false);
    structureHitRef.current = false; // Ensure reset on level start
    // Practice mode: create a backend session so winnings are awarded (50%)
    if (isStandalone && playerId) {
      startStandaloneCastle(playerId, level)
        .then((s) => setGameSessionId(s.game_id))
        .catch(() => setGameSessionId(null));
    } else if (!isRandomMode) {
      setGameSessionId(null);
    }
  };"""
    src = replace_once(src, old_start, new_start, "castle standalone session")

    # 3. submit results whenever a session exists (map OR standalone practice)
    old_win = """          // If from map, submit result to backend for rewards
          if (isFromMap && gameSessionId) {
            submitGameResult(true, eliminatedCount);"""
    new_win = """          // Submit result to backend for rewards (map or practice session)
          if (gameSessionId) {
            submitGameResult(true, eliminatedCount);"""
    src = replace_once(src, old_win, new_win, "castle win submit")

    old_lose = """          // If from map, submit result to backend (cooldown still applies)
          if (isFromMap && gameSessionId) {
            submitGameResult(false, eliminatedCount);"""
    new_lose = """          // Submit result to backend (cooldown still applies)
          if (gameSessionId) {
            submitGameResult(false, eliminatedCount);"""
    src = replace_once(src, old_lose, new_lose, "castle lose submit")

    if src != before:
        CASTLE.write_text(src)
        return 1
    return 0


def main():
    total = 0
    total += patch_api()
    total += patch_game_screen(
        CAR,
        "import { startCarChase, completeCarChase } from '../services/api';",
        "import { startCarChase, completeCarChase, startStandaloneCarChase } from '../services/api';",
        "startStandaloneCarChase", "car-chase",
    )
    total += patch_game_screen(
        RUN,
        "import { startRunaway, completeRunaway } from '../services/api';",
        "import { startRunaway, completeRunaway, startStandaloneRunaway } from '../services/api';",
        "startStandaloneRunaway", "runaway",
    )
    total += patch_game_screen(
        PKG,
        "import { startPackageGrab, completePackageGrab } from '../services/api';",
        "import { startPackageGrab, completePackageGrab, startStandalonePackageGrab } from '../services/api';",
        "startStandalonePackageGrab", "package-grab",
    )
    total += patch_castle()
    if total:
        print(f"\nDone. {total} file(s) updated.")
    else:
        print("\nNothing to do - all patches already applied.")
    print("MINIGAME_STANDALONE_FRONTEND_OK")


if __name__ == "__main__":
    main()
