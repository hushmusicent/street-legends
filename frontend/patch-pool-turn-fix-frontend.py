#!/usr/bin/env python3
"""Street Legends frontend: fix pool PvP turn deadlock after the first shot.

Root cause: the host's game screen opens with the CREATE-time room, where
guest_id is still null, so the host's game computes foeId as '' (empty).
When the host breaks and pockets nothing, the game passes the turn to
FOE = '' — to nobody. It posts that turn to the server, so the guest's
phone also shows 'Waiting for FRIEND...' and neither phone can ever move:
the guest's turn check (turn !== ME) blocks its input, and the host waits
for a guest that can never play. Both tables stay synced, both wait — the
exact 'freeze after first play, no turns' report.

Fix (game modal's existing 2s poll, no new timers, no layout change):
inside PoolPvpGameModal's poll, right after the room fetch, if the polled
room now has a guest_id that the game does not know yet, inject JS that
teaches the game who the friend is (FOE/FOENAME) and, if the current turn
is empty or is neither player's id, repairs it to the friend's turn and
re-posts the corrected state so the friend's phone picks it up on its
next poll. Once FOE matches, the block is a no-op, so it cannot repeat.
Frontend / Expo Go only."""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "// POOL_TURN_FIX"
ANCHOR = "        const st = data?.state;"
BLOCK = """        // POOL_TURN_FIX: learn the guest once they join (the host's game
        // opened with the create-time room, where guest_id was null, so its
        // FOE was '' and the first shot passed the turn to nobody).
        const __gId = data?.guest_id;
        const __gName = data?.guest_name || 'Player';
        if (__gId && webRef.current) {
          const __fixJs = 'try { var __g = ' + JSON.stringify(__gId) + '; var __gn = ' + JSON.stringify(__gName) + '; if (typeof FOE !== "undefined" && FOE !== __g) { FOE = __g; FOENAME = __gn; try { window.POOL_PVP.foe = __g; window.POOL_PVP.foeName = __gn; } catch (e) {} if (turn === "" || (turn !== ME && turn !== FOE)) { turn = FOE; } updateHeader(); if (turn === FOE) { setMsg("Waiting for " + FOENAME + "..."); } postPvpState(); } } catch (e) {} true;';
          webRef.current.injectJavaScript(__fixJs);
        }
"""

def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - nothing changed")
        return 1
    src = IDX.read_text(errors="ignore")
    if MARKER in src:
        print("POOL_TURN_FIX_ALREADY_APPLIED")
        return 0
    if ANCHOR not in src:
        print("WARNING: game-modal poll anchor not matched - index.tsx NOT changed")
        return 1
    new_src = src.replace(ANCHOR, BLOCK + ANCHOR, 1)
    if new_src.count("{") != src.count("{") or new_src.count("}") != src.count("}"):
        print("WARNING: brace balance changed - index.tsx NOT written")
        return 1
    IDX.write_text(new_src)
    print("POOL_TURN_FIX_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
