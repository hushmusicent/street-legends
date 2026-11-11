#!/usr/bin/env python3
"""Revert the center-prize frontend wiring (v2 patches) from index.tsx.

Restores the 6 PvC table-game modals (Pool, Dart, Card, Domino, Scrabble,
Chess & Checkers) and the PopShotCenterModal to their pre-prize state:
  - modal signature: drop the playerId prop + the prizeMsg/handlePrizeMsg block
  - onMessage: back to the plain 'close' handler
  - banner: remove the gold +$ PRIZE! line
  - render call site: drop playerId={playerId}

The game HTML prize posts stay in the .ts files (harmless: the restored
onMessage ignores any message that is not 'close'). The backend endpoint
stays live. The prize wiring will be re-applied later with the
awardCenterPrize import fixed.

Run from /app:
  cd /app && curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/patch-center-prize-revert-frontend.py" -o frontend/patch-center-prize-revert-frontend.py && python3 frontend/patch-center-prize-revert-frontend.py
"""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
IDX = ROOT / "frontend" / "app" / "(tabs)" / "index.tsx"
if not IDX.exists():
    IDX = ROOT / "frontend" / "app" / "index.tsx"
if not IDX.exists():
    print("WARNING: index.tsx not found")
    sys.exit(0)
src = IDX.read_text(encoding="utf-8")
orig = src
ok = []
warnings = []

ONMSG_OLD = "onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}"
ONMSG_NEW = "onMessage={handlePrizeMsg}"
ONMSG_NEW_POP = "onMessage={handlePopShotMsg}"

# The prize handler block: starts with the prizeMsg useState and ends with
# the handler's closing "  };" immediately before "  return (".
# Table games use handlePrizeMsg; Pop Shot uses handlePopShotMsg.
HANDLER_RE = re.compile(
    r"  const \[prizeMsg, setPrizeMsg\] = useState\(''\);\n"
    r"  const handle(?:Prize|PopShot)Msg = async \(event: any\) => \{[\s\S]*?\n  \};\n",
    re.M,
)

# Modal signatures as the v2 patches wrote them -> original.
MODALS = [
    ("PoolGameModal",
     "const PoolGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {",
     "const PoolGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
     "<PoolGameModal visible={poolGameOpen} onClose={() => setPoolGameOpen(false)} playerId={playerId} />",
     "<PoolGameModal visible={poolGameOpen} onClose={() => setPoolGameOpen(false)} />"),
    ("DartGameModal",
     "const DartGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {",
     "const DartGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
     "<DartGameModal visible={dartGameOpen} onClose={() => setDartGameOpen(false)} playerId={playerId} />",
     "<DartGameModal visible={dartGameOpen} onClose={() => setDartGameOpen(false)} />"),
    ("CardGameModal",
     "const CardGameModal = ({ visible, onClose, game, playerId }: { visible: boolean; onClose: () => void; game: string; playerId: string }) => {",
     "const CardGameModal = ({ visible, onClose, game }: { visible: boolean; onClose: () => void; game: string }) => {",
     "<CardGameModal visible={cardGameOpen} onClose={() => setCardGameOpen(false)} game={cardGame} playerId={playerId} />",
     "<CardGameModal visible={cardGameOpen} onClose={() => setCardGameOpen(false)} game={cardGame} />"),
    ("DominoGameModal",
     "const DominoGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {",
     "const DominoGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
     "<DominoGameModal visible={dominoGameOpen} onClose={() => setDominoGameOpen(false)} playerId={playerId} />",
     "<DominoGameModal visible={dominoGameOpen} onClose={() => setDominoGameOpen(false)} />"),
    ("ScrabbleGameModal",
     "const ScrabbleGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {",
     "const ScrabbleGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
     "<ScrabbleGameModal visible={scrabbleGameOpen} onClose={() => setScrabbleGameOpen(false)} playerId={playerId} />",
     "<ScrabbleGameModal visible={scrabbleGameOpen} onClose={() => setScrabbleGameOpen(false)} />"),
    ("ChessCheckersGameModal",
     "const ChessCheckersGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {",
     "const ChessCheckersGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
     "<ChessCheckersGameModal visible={chessCheckersGameOpen} onClose={() => setChessCheckersGameOpen(false)} playerId={playerId} />",
     "<ChessCheckersGameModal visible={chessCheckersGameOpen} onClose={() => setChessCheckersGameOpen(false)} />"),
]

for name, new_sig, old_sig, new_render, old_render in MODALS:
    changed = False
    # 1. Signature + handler block: find the v2 signature, then strip the
    #    handler block that follows it.
    if new_sig in src:
        src = src.replace(new_sig, old_sig, 1)
        changed = True
        # The handler block sits right after the signature line.
        # Remove it (it starts with the prizeMsg useState).
        sig_pos = src.find(old_sig)
        m = HANDLER_RE.search(src, sig_pos)
        if m:
            src = src[:m.start()] + src[m.end():]
        else:
            warnings.append(name + ": signature restored but prize handler block not found")
    # 2. onMessage back to plain close handler (only the one in this modal:
    #    do it globally per-modal by counting — the v2 patch wired exactly
    #    one onMessage per modal, so replace one occurrence).
    if ONMSG_NEW in src:
        src = src.replace(ONMSG_NEW, ONMSG_OLD, 1)
        changed = True
    if ONMSG_NEW_POP in src:
        src = src.replace(ONMSG_NEW_POP, ONMSG_OLD, 1)
        changed = True
    # 3. Banner line is removed by the global pass below (all banners at once).
    # 4. Render call site.
    if new_render in src:
        src = src.replace(new_render, old_render, 1)
        changed = True
    if changed:
        ok.append(name + " prize wiring reverted")
    else:
        warnings.append(name + ": no prize wiring found (already reverted?)")

# Pop Shot center modal: same four steps. Its signature carries playerId and
# its handler posts pop_shot_prize; the revert is identical in shape.
POP_NEW_SIG = "const PopShotCenterModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {"
POP_OLD_SIG = "const PopShotCenterModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {"
POP_NEW_RENDER = "<PopShotCenterModal visible={popShotCenterOpen} playerId={playerId} onClose={() => setPopShotCenterOpen(false)} />"
POP_OLD_RENDER = "<PopShotCenterModal visible={popShotCenterOpen} onClose={() => setPopShotCenterOpen(false)} />"
changed = False
if POP_NEW_SIG in src:
    src = src.replace(POP_NEW_SIG, POP_OLD_SIG, 1)
    changed = True
    sig_pos = src.find(POP_OLD_SIG)
    m = HANDLER_RE.search(src, sig_pos)
    if m:
        src = src[:m.start()] + src[m.end():]
    else:
        warnings.append("PopShotCenterModal: signature restored but prize handler block not found")
if ONMSG_NEW in src:
    src = src.replace(ONMSG_NEW, ONMSG_OLD, 1)
    changed = True
if ONMSG_NEW_POP in src:
    src = src.replace(ONMSG_NEW_POP, ONMSG_OLD, 1)
    changed = True
# Banner lines are removed by the global pass below (all banners at once).
if POP_NEW_RENDER in src:
    src = src.replace(POP_NEW_RENDER, POP_OLD_RENDER, 1)
    changed = True
if changed:
    ok.append("PopShotCenterModal prize wiring reverted")
else:
    warnings.append("PopShotCenterModal: no prize wiring found (already reverted?)")

# Global pass: remove every gold prize banner line. The pattern matches the
# newline before the banner plus the banner text (but NOT the newline after
# it), so the surrounding lines stay on their own lines.
BANNER_RE = re.compile(r"\n[ \t]*\{prizeMsg \? \(\<Text[^\n]*")
src, n_banner = BANNER_RE.subn("", src)
if n_banner:
    ok.append("%d prize banner line(s) removed" % n_banner)

if src != orig:
    IDX.write_text(src, encoding="utf-8")
    # Bracket balance sanity check.
    assert src.count("{") == src.count("}"), "unbalanced {} after revert"
    assert src.count("(") == src.count(")"), "unbalanced () after revert"
    assert src.count("[") == src.count("]"), "unbalanced [] after revert"
    for line in ok:
        print("OK: " + line)
    for line in warnings:
        print("WARNING: " + line)
    print("CENTER_PRIZE_REVERT_OK")
else:
    print("WARNING: nothing changed - prize wiring already absent?")
    for line in warnings:
        print("WARNING: " + line)
    print("CENTER_PRIZE_REVERT_OK")
