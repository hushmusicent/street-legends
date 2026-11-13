#!/usr/bin/env python3
"""Street Legends Basketball title v3: modal title shows opponent name.

v1 and v2 both failed in /app with "Basketball onMessage anchor not
found". The grep showed why (index.tsx line 2428): /app passes a 5th
argument, playerId, to handleParkGameMessage:

  onMessage={(event: any) => handleParkGameMessage(event?.nativeEvent?.data, onClose, 'Basketball', onCashChange, playerId)}

GitHub only has 4 args, so v1/v2 (which expected the call to end after
onCashChange) never matched. Both were atomic, so nothing applied.

v3 matches the Basketball onMessage with any optional extra arguments
after onCashChange and PRESERVES them in the replacement call, so it
works on both the 4-arg GitHub copy and the 5-arg /app copy.

Fix (frontend only):
  1. BasketballGameModal keeps a foeName state (null = vs CPU).
  2. Its WebView onMessage intercepts a pvp_opponent JSON message and
     sets foeName; every other message still goes to
     handleParkGameMessage as before (with its original arguments).
  3. The title becomes "BASKETBALL - YOU vs <foeName>" when foeName is
     set, otherwise "BASKETBALL - YOU vs CPU".
  The modal unmounts when closed, so foeName resets on every fresh
  open -- a PvC game always shows "YOU vs CPU" again.

Run from /app: python3 frontend/patch-basketball-title-pvp-v3.py
Idempotent: a full re-run prints BASKETBALL_TITLE_PVP_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

IDX = Path("frontend/app/(tabs)/index.tsx")
MARKER = "BASKETBALL_TITLE_PVP_OK"

# 1. Give the Basketball modal a foeName state.
MODAL_RE = re.compile(
    r"(const BasketballGameModal = \(\{\s*visible, onClose, playerId, playerName, onCashChange\s*\}.*?\}\) => \{\s*)"
    r"(return \()",
    re.DOTALL,
)
MODAL_NEW = (
    "\\1"
    "  // PVP TITLE: the opponent's name in a PvP room (null = vs CPU).\n"
    "  const [foeName, setFoeName] = useState<string | null>(null);\n"
    "  \\2"
)

# 2. Dynamic title.
TITLE_RE = re.compile(
    r"<Text style=\{\{ color: '#ffffff', fontWeight: '800', fontSize: 16 \}\}>BASKETBALL - YOU vs CPU</Text>",
    re.DOTALL,
)
TITLE_NEW = (
    "<Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>{foeName ? `BASKETBALL - YOU vs ${foeName}` : 'BASKETBALL - YOU vs CPU'}</Text>"
)

# 3. Intercept pvp_opponent in the Basketball WebView onMessage.
# Matches the 4-arg GitHub call AND the 5-arg /app call (extra
# playerId); group 1 captures any extra args and keeps them.
MSG_RE = re.compile(
    r"onMessage=\{\s*\(event:\s*any\)\s*=>\s*handleParkGameMessage\(\s*event\?\.nativeEvent\?\.data,\s*onClose,\s*'Basketball',\s*onCashChange(\s*,\s*[^)]*)?\)\s*\}",
    re.DOTALL,
)
MSG_NEW = (
    "onMessage={(event: any) => { const d = event?.nativeEvent?.data; if (typeof d === 'string' && d.indexOf('pvp_opponent') !== -1) { try { const m = JSON.parse(d); if (m && m.type === 'pvp_opponent' && m.name) { setFoeName(String(m.name)); return; } } catch (e) {} } handleParkGameMessage(d, onClose, 'Basketball', onCashChange\\1); }}"
)

def main():
    if not IDX.exists():
        print("ERROR: index.tsx not found (run from /app)")
        sys.exit(1)
    src = IDX.read_text()
    if "PVP TITLE: the opponent's name" in src:
        print("BASKETBALL_TITLE_PVP_ALREADY_APPLIED")
        return
    m = MODAL_RE.search(src)
    if not m:
        print("ERROR: BasketballGameModal anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m.start()] + m.expand(MODAL_NEW) + src[m.end():]
    m2 = TITLE_RE.search(src)
    if not m2:
        print("ERROR: Basketball title anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m2.start()] + TITLE_NEW + src[m2.end():]
    m3 = MSG_RE.search(src)
    if not m3:
        print("ERROR: Basketball onMessage anchor not found (file changed in an unexpected way)")
        sys.exit(1)
    src = src[:m3.start()] + m3.expand(MSG_NEW) + src[m3.end():]
    IDX.write_text(src)
    cur = IDX.read_text()
    if "PVP TITLE: the opponent's name" not in cur or "foeName ? `BASKETBALL - YOU vs" not in cur:
        print("ERROR: Basketball title patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
