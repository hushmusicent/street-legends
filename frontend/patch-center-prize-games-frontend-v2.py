#!/usr/bin/env python3
"""Street Legends frontend: Activity Center cash prizes — table-game modals.

Wires the six PvC table-game modals (Pool, Dartboard, Card Table,
Dominoes, Scrabble, Chess & Checkers) to the center prize endpoint.
Each game's HTML posts {type:'center_prize_win', game, level} on a
win vs the CPU (frontend/patch-center-prize-games-html.py); this
patch makes each modal's onMessage parse it, call
POST /api/center-prize/award (server computes the $500, or
$500 + 10% per level on Chess), and show a gold "+$X PRIZE!" banner
under the modal header.

The games are the SAME components in the house and the activity
center, so the prize pays on a win in either place.

What this does per modal (frontend only; Expo Go).

v2: index.tsx lives at frontend/app/(tabs)/index.tsx in /app, not
frontend/screens/MapScreen/index.tsx (v1 looked there and found
nothing). Same wiring, corrected path.
  1. Signature: add a playerId prop + a prizeMsg state + a
     handlePrizeMsg (parses the win JSON, calls awardCenterPrize,
     sets the banner). awardCenterPrize lives in services/api.ts
     (added by frontend/patch-pop-shot-prize-frontend.py; this patch
     adds it too if it is missing).
  2. onMessage: the WebView's onMessage (which only handled
     'close') is replaced with handlePrizeMsg, scoped to the modal
     by its unique source={{ html: ... }} line.
  3. Banner: a gold "+$X PRIZE!" line under the header, inserted
     after the header row's closing </View> (found from the modal's
     title line).
  4. Render call site: pass playerId={playerId}.

Run from /app: python3 frontend/patch-center-prize-games-frontend.py
Idempotent per modal: a modal already holding handlePrizeMsg is skipped.
"""
import re
import sys
from pathlib import Path

IDX = Path("frontend/app/(tabs)/index.tsx")
if not IDX.exists():
    IDX = Path("frontend/app/index.tsx")
API = Path("frontend/services/api.ts")
MARKER = "CENTER_PRIZE_GAMES_FRONTEND_OK"

API_FN = """export const awardCenterPrize = async (playerId: string, game: string, level: number, won: boolean, makes: number, onfireMakes: number): Promise<any> => {
  const response = await api.post(`/center-prize/award`, { player_id: playerId, game, level, won, makes, onfire_makes: onfireMakes });
  return response.data;
};"""

HANDLER = """  const [prizeMsg, setPrizeMsg] = useState('');
  const handlePrizeMsg = async (event: any) => {
    const data = event?.nativeEvent?.data;
    if (data === 'close') { onClose(); return; }
    try {
      const msg = JSON.parse(data);
      if (msg && msg.type === 'center_prize_win' && playerId) {
        const res: any = await awardCenterPrize(playerId, msg.game || 'pool', msg.level || 1, true, 0, 0);
        const prize = res?.prize;
        if (typeof prize === 'number' && prize > 0) setPrizeMsg('+$' + prize + ' PRIZE!');
      }
    } catch (e) { /* not JSON — ignore */ }
  };"""

BANNER = "        {prizeMsg ? (<Text style={{ color: '#ffd54f', fontWeight: '800', fontSize: 16, textAlign: 'center', paddingVertical: 6 }}>{prizeMsg}</Text>) : null}"

# (modal name, signature old, signature new, source html var, title anchor, render old, render new)
MODALS = [
    (
        "PoolGameModal",
        "const PoolGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
        "const PoolGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {\n" + HANDLER,
        "POOL_GAME_HTML",
        "POOL TABLE - YOU vs CPU",
        "<PoolGameModal visible={poolGameOpen} onClose={() => setPoolGameOpen(false)} />",
        "<PoolGameModal visible={poolGameOpen} onClose={() => setPoolGameOpen(false)} playerId={playerId} />",
    ),
    (
        "DartGameModal",
        "const DartGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
        "const DartGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {\n" + HANDLER,
        "DART_GAME_HTML",
        "DARTBOARD - YOU vs CPU",
        "<DartGameModal visible={dartGameOpen} onClose={() => setDartGameOpen(false)} />",
        "<DartGameModal visible={dartGameOpen} onClose={() => setDartGameOpen(false)} playerId={playerId} />",
    ),
    (
        "CardGameModal",
        "const CardGameModal = ({ visible, onClose, game }: { visible: boolean; onClose: () => void; game: string }) => {",
        "const CardGameModal = ({ visible, onClose, game, playerId }: { visible: boolean; onClose: () => void; game: string; playerId: string }) => {\n" + HANDLER,
        "html",
        "{title}</Text>",
        "<CardGameModal visible={cardGameOpen} onClose={() => setCardGameOpen(false)} game={cardGame} />",
        "<CardGameModal visible={cardGameOpen} onClose={() => setCardGameOpen(false)} game={cardGame} playerId={playerId} />",
    ),
    (
        "DominoGameModal",
        "const DominoGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
        "const DominoGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {\n" + HANDLER,
        "DOMINO_HTML",
        "DOMINOES - YOU vs CPU",
        "<DominoGameModal visible={dominoGameOpen} onClose={() => setDominoGameOpen(false)} />",
        "<DominoGameModal visible={dominoGameOpen} onClose={() => setDominoGameOpen(false)} playerId={playerId} />",
    ),
    (
        "ScrabbleGameModal",
        "const ScrabbleGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
        "const ScrabbleGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {\n" + HANDLER,
        "SCRABBLE_HTML",
        "SCRABBLE - YOU vs CPU",
        "<ScrabbleGameModal visible={scrabbleGameOpen} onClose={() => setScrabbleGameOpen(false)} />",
        "<ScrabbleGameModal visible={scrabbleGameOpen} onClose={() => setScrabbleGameOpen(false)} playerId={playerId} />",
    ),
    (
        "ChessCheckersGameModal",
        "const ChessCheckersGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {",
        "const ChessCheckersGameModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {\n" + HANDLER,
        "CHESS_CHECKERS_HTML",
        "CHESS &amp; CHECKERS - YOU vs CPU",
        "<ChessCheckersGameModal visible={chessCheckersGameOpen} onClose={() => setChessCheckersGameOpen(false)} />",
        "<ChessCheckersGameModal visible={chessCheckersGameOpen} onClose={() => setChessCheckersGameOpen(false)} playerId={playerId} />",
    ),
]

ONMSG_OLD = "onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}"
ONMSG_NEW = "onMessage={handlePrizeMsg}"


def _balance(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"), s.count("["), s.count("]"))


def _insert_banner(src, sig_idx, title):
    """Insert the prize banner after the header row's closing </View>,
    found from the modal's title line (search starts at the modal's
    signature so a shared title cannot match another modal)."""
    t = src.find(title, sig_idx)
    if t == -1:
        return src, False
    close = src.find("</View>", t)
    if close == -1:
        return src, False
    after = close + len("</View>")
    return src[:after] + "\n" + BANNER + src[after:], True


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - table-game prize wiring NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore") if API.exists() else ""
    orig = src
    orig_a = asrc
    landed = []
    warnings = []

    if "awardCenterPrize" not in asrc:
        if "export const saveCenterLayout" in asrc:
            asrc = asrc.replace("export const saveCenterLayout", API_FN + "\n\nexport const saveCenterLayout", 1)
            print("OK: awardCenterPrize added to api.ts")
            landed.append("api")
        else:
            warnings.append("awardCenterPrize missing in api.ts (saveCenterLayout anchor not found) - prize calls will fail at runtime")

    for name, sig_old, sig_new, html_var, title, render_old, render_new in MODALS:
        # ---- Find the modal and check idempotency per modal. ----
        sig_pos = src.find("const %s = ({" % name)
        if sig_pos == -1:
            warnings.append("%s signature not found - prize wiring NOT added" % name)
            continue
        sig_end = src.find("=> {", sig_pos)
        # Already wired: the signature carries playerId and the handler
        # follows it within the modal body.
        if sig_end != -1 and "playerId" in src[sig_pos:sig_end] and "handlePrizeMsg" in src[sig_end:sig_end + 1200]:
            print("%s_ALREADY_APPLIED" % name.upper())
            landed.append(name)
            continue
        sig_idx = src.find(sig_old, sig_pos)
        if sig_idx == -1:
            warnings.append("%s signature not matched verbatim - prize wiring NOT added" % name)
            continue
        # ---- Piece 1: signature + handler. ----
        src = src[:sig_idx] + sig_new + src[sig_idx + len(sig_old):]
        # ---- Piece 2: onMessage, scoped by the modal's source line. ----
        src_pat = re.compile(
            r"(source=\{\{ html: " + re.escape(html_var) + r" \}\}[\s\S]*?)" + re.escape(ONMSG_OLD),
            re.M,
        )
        src2, n = src_pat.subn(r"\1" + ONMSG_NEW, src, count=1)
        if n == 1:
            src = src2
        else:
            warnings.append("%s onMessage not wired (source anchor not matched)" % name)
        # ---- Piece 3: banner under the header. ----
        sig2 = src.find("const %s" % name)
        src, ok = _insert_banner(src, sig2, title)
        if not ok:
            warnings.append("%s prize banner NOT added (title/header not matched)" % name)
        # ---- Piece 4: render call site passes playerId. ----
        if render_new in src:
            pass
        elif render_old in src:
            src = src.replace(render_old, render_new, 1)
        else:
            warnings.append("%s render call not found - playerId NOT passed" % name)
        print("OK: %s prize wired" % name)
        landed.append(name)

    if not landed:
        print("CENTER_PRIZE_GAMES_FRONTEND_PARTIAL: nothing landed")
        return 1
    after = _balance(src)
    if after[0] != after[1] or after[2] != after[3] or after[4] != after[5]:
        print("CENTER_PRIZE_GAMES_FRONTEND_BALANCE_FAIL: brackets unbalanced %s (index.tsx NOT written)" % (after,))
        return 1
    if src != orig:
        IDX.write_text(src)
    if asrc != orig_a and API.exists():
        API.write_text(asrc)
    for w in warnings:
        print("WARNING: " + w)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
