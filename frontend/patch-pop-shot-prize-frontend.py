#!/usr/bin/env python3
"""Street Legends frontend: Activity Center Pop Shot cash prize wiring.

Pop Shot (activity center only) now pays a cash prize at the end of
the 60 seconds: $10 per basket made, $15 per ON FIRE basket (3rd
straight make and beyond), +10% per level (5 levels: Rookie 1,
Amateur 2, Pro 3, All-Star 4, Legend 5). The game posts
{type:'pop_shot_prize', makes, onfire, level} to the app when TIME!
hits; the app calls POST /api/center-prize/award (server computes
the prize — the client never sends an amount) and shows a gold
"+$X PRIZE!" banner under the modal header. Quitting early via MENU
forfeits the prize (the game only posts at TIME!).

Requires (run first): backend/patch-center-prize.py (Publish) and
frontend/patch-activity-center-pop-shot-html.py (prize game in
PopShotHtml.ts). The Pop Shot center frontend patch must already
have run (PopShotCenterModal exists).

What this does (frontend only; Expo Go):
  1. services/api.ts: add awardCenterPrize(playerId, game, level,
     won, makes, onfireMakes) -> POST /center-prize/award.
  2. PopShotCenterModal: accept a playerId prop, add a prizeMsg
     state + handlePopShotMsg (parses the prize JSON, calls the
     endpoint, shows the banner), wire onMessage to it, and render
     the gold prize banner under the header.
  3. Render call site: pass playerId={playerId} to the modal.

Run from /app: python3 frontend/patch-pop-shot-prize-frontend.py
Idempotent: a full re-run prints POP_SHOT_PRIZE_FRONTEND_ALREADY_APPLIED.
"""
import sys
import tempfile
import py_compile
from pathlib import Path

IDX = Path("frontend/screens/MapScreen/index.tsx")
API = Path("frontend/services/api.ts")
MARKER = "POP_SHOT_PRIZE_FRONTEND_OK"

API_FN = """export const awardCenterPrize = async (playerId: string, game: string, level: number, won: boolean, makes: number, onfireMakes: number): Promise<any> => {
  const response = await api.post(`/center-prize/award`, { player_id: playerId, game, level, won, makes, onfire_makes: onfireMakes });
  return response.data;
};"""

MODAL_SIG_OLD = "const PopShotCenterModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {"
MODAL_SIG_NEW = """const PopShotCenterModal = ({ visible, onClose, playerId }: { visible: boolean; onClose: () => void; playerId: string }) => {
  const [prizeMsg, setPrizeMsg] = useState('');
  const handlePopShotMsg = async (event: any) => {
    const data = event?.nativeEvent?.data;
    if (data === 'close') { onClose(); return; }
    try {
      const msg = JSON.parse(data);
      if (msg && msg.type === 'pop_shot_prize' && playerId) {
        const res: any = await awardCenterPrize(playerId, 'pop_shot', msg.level || 1, false, msg.makes || 0, msg.onfire || 0);
        const prize = res?.prize;
        if (typeof prize === 'number' && prize > 0) setPrizeMsg('+$' + prize + ' PRIZE!');
      }
    } catch (e) { /* not JSON — ignore */ }
  };"""

ONMSG_OLD = "            onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}"
ONMSG_NEW = "            onMessage={handlePopShotMsg}"

BANNER_OLD = """          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>"""
BANNER_NEW = """          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {prizeMsg ? (<Text style={{ color: '#ffd54f', fontWeight: '800', fontSize: 16, textAlign: 'center', paddingVertical: 6 }}>{prizeMsg}</Text>) : null}"""

RENDER_OLD = "<PopShotCenterModal visible={popShotCenterOpen}"
RENDER_NEW = "<PopShotCenterModal visible={popShotCenterOpen} playerId={playerId}"


def _balance(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"), s.count("["), s.count("]"))


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - Pop Shot prize wiring NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore") if API.exists() else ""
    orig = src
    orig_a = asrc
    landed = []
    warnings = []

    # ---- Idempotency: prize wiring already landed. ----
    if "pop_shot_prize" in src and "awardCenterPrize" in src and "handlePopShotMsg" in src:
        print("POP_SHOT_PRIZE_FRONTEND_ALREADY_APPLIED")
        return 0

    # ---- Preconditions. ----
    if "const PopShotCenterModal" not in src:
        print("WARNING: PopShotCenterModal not found - run the Pop Shot center frontend patch first, prize wiring NOT added")
        return 1
    if "awardCenterPrize" not in asrc:
        if "export const saveCenterLayout" in asrc:
            asrc = asrc.replace("export const saveCenterLayout", API_FN + "\n\nexport const saveCenterLayout", 1)
            print("OK: awardCenterPrize added to api.ts")
            landed.append("api")
        else:
            warnings.append("awardCenterPrize missing in api.ts (saveCenterLayout anchor not found) - prize calls will fail at runtime")

    # ---- Piece 1: modal signature + handler. ----
    if MODAL_SIG_OLD in src:
        src = src.replace(MODAL_SIG_OLD, MODAL_SIG_NEW, 1)
        print("OK: PopShotCenterModal takes playerId + prize handler")
        landed.append("modal")
    elif "handlePopShotMsg" in src:
        print("POP_SHOT_PRIZE_MODAL_ALREADY_APPLIED")
        landed.append("modal")
    else:
        warnings.append("PopShotCenterModal signature not matched verbatim - prize handler NOT added")

    # ---- Piece 2: onMessage -> handler. ----
    if ONMSG_OLD in src:
        src = src.replace(ONMSG_OLD, ONMSG_NEW, 1)
        print("OK: Pop Shot onMessage wired to prize handler")
        landed.append("onmessage")
    elif "onMessage={handlePopShotMsg}" in src:
        print("POP_SHOT_PRIZE_ONMESSAGE_ALREADY_APPLIED")
        landed.append("onmessage")
    else:
        warnings.append("Pop Shot onMessage line not matched verbatim - prize handler NOT wired")

    # ---- Piece 3: prize banner under the header. ----
    if BANNER_OLD in src:
        src = src.replace(BANNER_OLD, BANNER_NEW, 1)
        print("OK: prize banner added under the Pop Shot header")
        landed.append("banner")
    elif "prizeMsg" in src and "PRIZE!" in src:
        print("POP_SHOT_PRIZE_BANNER_ALREADY_APPLIED")
        landed.append("banner")
    else:
        warnings.append("Pop Shot header block not matched verbatim - prize banner NOT added")

    # ---- Piece 4: render call site passes playerId. ----
    if "playerId={playerId}" in src and "PopShotCenterModal visible={popShotCenterOpen} playerId={playerId}" in src:
        print("POP_SHOT_PRIZE_RENDER_ALREADY_APPLIED")
        landed.append("render")
    elif RENDER_OLD in src:
        src = src.replace(RENDER_OLD, RENDER_NEW, 1)
        print("OK: Pop Shot modal render passes playerId")
        landed.append("render")
    else:
        warnings.append("PopShotCenterModal render call not found - playerId NOT passed")

    if src == orig and asrc == orig_a:
        print("POP_SHOT_PRIZE_FRONTEND_PARTIAL: nothing landed")
        return 1
    # TSX is not Python: validate by bracket balance, not py_compile.
    # The check is that each bracket type is balanced WITHIN the new
    # file (counts legitimately grow — the patch adds code).
    after = _balance(src)
    if after[0] != after[1] or after[2] != after[3] or after[4] != after[5]:
        print("POP_SHOT_PRIZE_FRONTEND_BALANCE_FAIL: brackets unbalanced %s (index.tsx NOT written)" % (after,))
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
