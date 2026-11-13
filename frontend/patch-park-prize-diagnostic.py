#!/usr/bin/env python3
"""Street Legends frontend DIAGNOSTIC: show the park prize result on screen.

The park payout files are all verified in place and the backend pays,
but no prize lands on device even after a Metro cache clear. The award
call silently swallows errors, so nothing is visible. This patch makes
the flow VISIBLE: when a park game posts park_prize_win, the app shows
an Alert with exactly what happened:
  - "Win received: <game> / player: <first 8 of playerId or NONE>"
  - then either "Prize $500! Cash now $X" or "Prize FAILED: <reason>".
This is a DIAGNOSTIC, not a fix. Run it, win one PvC park game, and
report the exact Alert text. Remove it once the cause is known.

Requires: frontend/patch-park-prize-frontend.py already applied
(handleParkGameMessage handles park_prize_win).

Run from /app: python3 frontend/patch-park-prize-diagnostic.py
Idempotent: a full re-run prints PARK_PRIZE_DIAG_ALREADY_APPLIED.
"""
import sys
from pathlib import Path

IDX = Path("frontend/app/(tabs)/index.tsx")
if not IDX.exists():
    IDX = Path("frontend/app/index.tsx")
MARKER = "PARK_PRIZE_DIAG_OK"

OLD = """  // Park PvC win: the game posts {type:'park_prize_win', game, level} when
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
  }"""

NEW = """  // Park PvC win: the game posts {type:'park_prize_win', game, level} when
  // the player beats the CPU. Pay the $500 prize, then refresh cash.
  // DIAGNOSTIC: show an Alert with exactly what happened so a silent
  // failure is visible instead of swallowed.
  if (typeof data === 'string' && data.indexOf('park_prize_win') !== -1) {
    try {
      const msg = JSON.parse(data);
      const pidShort = playerId ? String(playerId).slice(0, 8) : 'NONE';
      if (msg && msg.type === 'park_prize_win') {
        if (!playerId) {
          Alert.alert('Park prize', 'Win received: ' + (msg.game || game) + ' / player: NONE - no playerId, prize NOT called');
          return;
        }
        awardCenterPrize(playerId, msg.game || game.toLowerCase(), msg.level || 1, true, 0, 0)
          .then((res: any) => {
            onCashChange?.();
            Alert.alert('Park prize', 'Win received: ' + (msg.game || game) + ' / player: ' + pidShort + ' / Prize $' + (res && res.prize !== undefined ? res.prize : '?') + '! Cash now $' + (res && res.cash !== undefined ? res.cash : '?'));
          })
          .catch((e: any) => {
            Alert.alert('Park prize', 'Win received: ' + (msg.game || game) + ' / player: ' + pidShort + ' / Prize FAILED: ' + (e && (e.message || (e.response && e.response.data && e.response.data.detail) || JSON.stringify(e))) || 'unknown'));
          });
      }
    } catch (e) {
      Alert.alert('Park prize', 'Win message parse FAILED: ' + String(e));
    }
    return;
  }"""

def main():
    if not IDX.exists():
        print("ERROR: index.tsx not found (run from /app)")
        sys.exit(1)
    src = IDX.read_text()
    if "PARK_PRIZE_DIAG" in src or "Win received:" in src:
        print("PARK_PRIZE_DIAG_ALREADY_APPLIED")
        return
    if OLD not in src:
        print("ERROR: park_prize_win handler anchor not found (run patch-park-prize-frontend.py first)")
        sys.exit(1)
    # Alert must be imported. It usually is (Alert is used elsewhere in index.tsx).
    if "Alert" not in src:
        print("ERROR: Alert not imported in index.tsx")
        sys.exit(1)
    src = src.replace(OLD, NEW, 1)
    IDX.write_text(src)
    cur = IDX.read_text()
    if "Win received:" not in cur or "Prize FAILED" not in cur:
        print("ERROR: diagnostic not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
