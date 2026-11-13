#!/usr/bin/env python3
"""Street Legends frontend: park games cash prize handler ($500 per PvC win).

Wires the 6 park game modals (Basketball, Football, Baseball, Soccer,
Tennis, 1-on-1) to the prize endpoint. Each park game posts
{type:'park_prize_win', game, level:1} when the player beats the CPU
(PvC only; PvP wins use the existing cash-bet flow and never post
this). This patch:
  1. Imports awardCenterPrize in index.tsx (adds it if missing).
  2. handleParkGameMessage takes playerId and, on a park_prize_win,
     calls awardCenterPrize(playerId, game, 1, true, 0, 0) then
     refreshes the cash shown on the map.
  3. Passes playerId at all 6 park modal onMessage call sites.

Requires: backend/patch-park-prize.py (Deploy) and
frontend/patch-park-prize-html.py (the win posts in the 6 game HTMLs).
The center prize v3 patch is NOT required — this patch adds the
awardCenterPrize import itself.

Run from /app: python3 frontend/patch-park-prize-frontend.py
Idempotent: a full re-run prints PARK_PRIZE_FRONTEND_ALREADY_APPLIED.
"""
import re
import sys
import py_compile
from pathlib import Path

IDX = Path("frontend/app/(tabs)/index.tsx")
if not IDX.exists():
    IDX = Path("frontend/app/index.tsx")
API = Path("frontend/services/api.ts")
MARKER = "PARK_PRIZE_FRONTEND_OK"

OLD_HANDLER = """const handleParkGameMessage = (data: string | undefined, onClose: () => void, game: string, onCashChange?: () => void) => {
  if (data === 'close') { onClose(); return; }
  // A park bet was taken, won, lost or refunded: refresh the cash shown on the map.
  if (data === 'cash') { onCashChange?.(); return; }
  if (typeof data === 'string' && data.startsWith('share:')) {
    const code = data.slice(6);
    Share.share({ message: `Play ${game} with me in Street Legends! Go to the park, open ${game}, tap PLAYER VS PLAYER and join room code ${code}` }).catch(() => {});
  }
};"""

NEW_HANDLER = """const handleParkGameMessage = (data: string | undefined, onClose: () => void, game: string, onCashChange?: () => void, playerId?: string) => {
  if (data === 'close') { onClose(); return; }
  // A park bet was taken, won, lost or refunded: refresh the cash shown on the map.
  if (data === 'cash') { onCashChange?.(); return; }
  // Park PvC win: the game posts {type:'park_prize_win', game, level} when
  // the player beats the CPU. Pay the $500 prize, then refresh cash.
  if (typeof data === 'string' && data.indexOf('park_prize_win') !== -1) {
    try {
      const msg = JSON.parse(data);
      if (msg && msg.type === 'park_prize_win' && playerId) {
        awardCenterPrize(playerId, msg.game || game.toLowerCase(), msg.level || 1, true, 0, 0)
          .then(() => { onCashChange?.(); })
          .catch(() => {});
      }
    } catch (e) {}
    return;
  }
  if (typeof data === 'string' && data.startsWith('share:')) {
    const code = data.slice(6);
    Share.share({ message: `Play ${game} with me in Street Legends! Go to the park, open ${game}, tap PLAYER VS PLAYER and join room code ${code}` }).catch(() => {});
  }
};"""

# game label -> onMessage call site (each passes playerId after this patch)
CALL_SITES = [
    ("Basketball", "handleParkGameMessage(event?.nativeEvent?.data, onClose, 'Basketball', onCashChange)"),
    ("Football", "handleParkGameMessage(event?.nativeEvent?.data, onClose, 'Football', onCashChange)"),
    ("Baseball", "handleParkGameMessage(event?.nativeEvent?.data, onClose, 'Baseball', onCashChange)"),
    ("Soccer", "handleParkGameMessage(event?.nativeEvent?.data, onClose, 'Soccer', onCashChange)"),
    ("Tennis", "handleParkGameMessage(event?.nativeEvent?.data, onClose, 'Tennis', onCashChange)"),
    ("1-on-1", "handleParkGameMessage(event?.nativeEvent?.data, onClose, '1-on-1', onCashChange)"),
]

def _add_import(src):
    """Add awardCenterPrize to the services/api import. Returns (src, added)."""
    if "awardCenterPrize" in src:
        return src, False
    m = re.search(r"\n\} from '\.\./\.\./services/api';", src)
    if not m:
        return src, False
    src = src[:m.start()] + "\n  awardCenterPrize," + src[m.start():]
    return src, True

def main():
    if not IDX.exists():
        print("ERROR: index.tsx not found (run from /app)")
        sys.exit(1)
    src = IDX.read_text()
    warnings = []

    # Already applied?
    if "park_prize_win" in src and OLD_HANDLER not in src:
        # handler already replaced; check call sites pass playerId
        if all("onCashChange, playerId)" in src for _, cs in CALL_SITES):
            print("PARK_PRIZE_FRONTEND_ALREADY_APPLIED")
            return

    # 1. import awardCenterPrize
    src, imp_added = _add_import(src)
    if imp_added:
        print("OK: awardCenterPrize imported in index.tsx")
    elif "awardCenterPrize" in src:
        print("OK: awardCenterPrize already imported")
    else:
        warnings.append("awardCenterPrize import NOT added (no services/api import found) - prize calls will fail at runtime")

    # 2. replace handler
    if OLD_HANDLER in src:
        src = src.replace(OLD_HANDLER, NEW_HANDLER, 1)
        print("OK: handleParkGameMessage handles park_prize_win")
    elif "park_prize_win" in src:
        print("OK: handleParkGameMessage already handles park_prize_win")
    else:
        print("ERROR: handleParkGameMessage anchor not found")
        sys.exit(1)

    # 3. pass playerId at the 6 call sites
    done = 0
    for label, cs in CALL_SITES:
        new_cs = cs[:-1] + ", playerId)"
        if new_cs in src:
            done += 1
        elif cs in src:
            src = src.replace(cs, new_cs, 1)
            done += 1
            print(f"OK: {label} modal passes playerId")
    if done < len(CALL_SITES):
        warnings.append(f"only {done}/6 park modal call sites updated")

    IDX.write_text(src)
    py_compile.compile(str(IDX), doraise=True) if False else None
    # TSX isn't Python; verify by re-reading instead.
    cur = IDX.read_text()
    checks = [
        ("awardCenterPrize imported", "awardCenterPrize" in cur),
        ("park_prize_win handler", "park_prize_win" in cur),
        ("all 6 call sites pass playerId", all("onCashChange, playerId)" in cur for _, cs in CALL_SITES)),
    ]
    for name, ok in checks:
        if not ok:
            print(f"ERROR: check failed: {name}")
            sys.exit(1)
    for w in warnings:
        print("WARN:", w)
    print(MARKER)

if __name__ == "__main__":
    main()
