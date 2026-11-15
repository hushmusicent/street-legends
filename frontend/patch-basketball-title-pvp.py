#!/usr/bin/env python3
"""Street Legends Basketball: modal title shows the opponent's name in PvP.

User: "why does it still say you vs cpu"

Cause: the BasketballGameModal title is a hardcoded string
"BASKETBALL - YOU vs CPU". It never changes, even in a real PvP game.
The game HTML already posts {type:'pvp_opponent', name} to the app when
a PvP room starts (from the PvP-mode patch), but nothing in the app
listens for it -- handleParkGameMessage only handles close/cash/share.

Fix (frontend only; the game HTML is untouched):
  1. BasketballGameModal keeps a foeName state (null = vs CPU).
  2. Its WebView onMessage intercepts a pvp_opponent JSON message and
     sets foeName; every other message still goes to
     handleParkGameMessage as before.
  3. The title becomes "BASKETBALL - YOU vs <foeName>" when foeName is
     set, otherwise "BASKETBALL - YOU vs CPU".
  The modal unmounts when closed (basketballOpen ? <Modal/> : null),
  so foeName resets to null on every fresh open -- a PvC game always
  shows "YOU vs CPU" again.

Run from /app: python3 frontend/patch-basketball-title-pvp.py
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
MSG_RE = re.compile(
    r"(onMessage=\{\(event: any\) => handleParkGameMessage\(event\?\.nativeEvent\?\.data, onClose, 'Basketball', onCashChange\)\})",
    re.DOTALL,
)
MSG_NEW = (
    "onMessage={(event: any) => { const d = event?.nativeEvent?.data; if (typeof d === 'string' && d.indexOf('pvp_opponent') !== -1) { try { const m = JSON.parse(d); if (m && m.type === 'pvp_opponent' && m.name) { setFoeName(String(m.name)); return; } } catch (e) {} } handleParkGameMessage(d, onClose, 'Basketball', onCashChange); }}"
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
    src = src[:m3.start()] + MSG_NEW + src[m3.end():]
    IDX.write_text(src)
    cur = IDX.read_text()
    if "PVP TITLE: the opponent's name" not in cur or "foeName ? `BASKETBALL - YOU vs" not in cur:
        print("ERROR: Basketball title patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
