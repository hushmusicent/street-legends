#!/usr/bin/env python3
"""Street Legends frontend: Activity Center dominoes table — same v2
treatment as the pool table, dartboard, and card table (real picture
in the scrolling room, tap = dominoes menu, hold-drag arrange
Veno-only), PLUS the card table shrinks to 180x120.

User request (2026-11-06 14:42 EST): "Do the same thing with the
dominoes table and make the card table smaller" — two parts: (1) the
dominoes table gets the pool/dart/card treatment; (2) the card table
picture gets SMALLER (it renders 280x187, same as the pool table —
it should be clearly smaller than the pool table but still bigger
than the 140x94 dartboard).

What this does (frontend; the backend patch extends the layout clamp):
  1. REAL DOMINOES PICTURE IN THE SAME SCENE: the dominoes table
     renders as its ACTUAL picture — the house's exact image source,
     resolved at patch time from the HOUSE_ITEMS dominoes entry's
     image (require, already .png — no .jpg/.png swap to trip over,
     but the same fallback chain as v2). 280x187, resizeMode
     "contain", exactly like the house room render. Placed in the
     SAME horizontal ScrollView scene as the other three fixtures,
     at its own stored fractional position. Default {x:0.15, y:0.5}
     — left side, middle height of the wide scene, clear of the pool
     table's default {0.5, 0.72}, the dartboard's {0.5, 0.28}, and
     the card table's {0.85, 0.5}. No menu card, no "TAP TO PLAY"
     text, nothing in any shop/item catalog or house dropdown.
  2. CARD TABLE SMALLER: the card table picture goes from 280x187
     to 180x120 — between the pool table (280x187) and the dartboard
     (140x94), still tappable. Its position, tap, and hold-drag are
     otherwise untouched.
  3. TAP = DOMINOES PLAY MENU: tapping the dominoes picture opens
     the SAME DominoTableMenuModal the house uses (PLAY VS COMPUTER
     -> DominoGameModal PvC; PLAYER VS PLAYER -> DominoPvpModal room
     screen with create/join, REJOIN, auto-start, no chat; wager UI
     inside it untouched). MOVE/SELL hidden on the center path only
     via a new optional hideManage prop on DominoTableMenuModal (same
     pattern as the pool/darts/card menus); if the prop cannot land,
     onMove/onSell are inert (close only) — nothing can ever be
     moved or sold from a center. If the house dominoes PvP is not
     fully wired in this build, the center menu matches the house
     menu without the PvP button (NOTE printed).
  4. HOLD-DRAG = ARRANGE (Veno only): same interaction as the other
     three fixtures — press-and-HOLD (250ms), then drag (gold border
     while dragging, scene scroll disabled while dragging); tap
     (<12px) opens the menu instead. The hint renders only for
     Mayor Veno; for anyone else all four fixtures are fixed and
     hold does nothing (tap still opens the menus).
  5. MERGED LAYOUT SAVE (critical): the card-table merged save is
     replaced by ONE shared save that always sends the FULL layout
     {pool_table, dart_board, card_table, dominoes} (all four
     positions, converted at the boundary to the backend's integer
     box). Saving any one fixture never wipes the others' spots. A
     403 snaps ALL FOUR fixtures back with "Only Mayor Veno can
     arrange this center." The modal loads all four stored positions
     on open.
  6. PanResponder import: if the import-fix / dartboard / cardtable
     patch already landed it, ALREADY_APPLIED; otherwise this patch
     adds it itself (same brace-insert strategy, never anchoring on
     the last member).

UNCHANGED: pool table (picture, menu, hold-drag, position),
dartboard (picture, menu, hold-drag, position), card table (picture
except the size, menu, hold-drag, position), "Inside now" list,
LEAVE, presence, the dominoes menu contents, house dominoes table +
house rules, the layout endpoint + its permission. The dominoes ROOM
endpoints need no change: POST /api/dominoes/rooms/create takes only
{player_id, player_name, seed} and /join only {code, player_id,
player_name} — no house lookup, no ownership check (same as
pool/darts/cards) — so center PvP works with no room change.

Run from /app: python3 frontend/patch-activity-center-dominoes-frontend.py
Frontend / Expo Go only. Run AFTER the cardtable frontend patch is
live (the merged save needs the card pieces first) and after the
dominoes backend patch is Published (the merged save needs the
four-key clamp live first).
Idempotent: a full re-run prints ACTIVITY_CENTER_DOMINOES_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"
MARKER = "ACTIVITY_CENTER_DOMINOES_OK"
VENO_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"

CARD_STATE_ANCHOR = "  const [centerCardDrag, setCenterCardDrag] = useState(false);"
PRESENCE_EFFECT_CLOSE = "  }, [activeCenter?.id, playerId]);"
# Merged save after the cardtable patch (three fixtures); extended to four.
SAVE_3 = "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current) });"
SAVE_4 = "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current), dominoes: centerPosToStored(centerDomPosRef.current) });"
BACK_3 = """        const back = storedToCenterPos((activeCenter as any)?.layout?.pool_table);
        const backDart = storedToCenterDartPos((activeCenter as any)?.layout?.dart_board);
        centerPoolPosRef.current = back;
        setCenterPoolPos(back);
        centerDartPosRef.current = backDart;
        setCenterDartPos(backDart);
        const backCard = storedToCenterCardPos((activeCenter as any)?.layout?.card_table);
        centerCardPosRef.current = backCard;
        setCenterCardPos(backCard);"""
RESPONDER_TAIL = """        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""
CARD_LOAD_BLOCK = """    const posCard = storedToCenterCardPos((activeCenter as any)?.layout?.card_table);
    centerCardPosRef.current = posCard;
    setCenterCardPos(posCard);
    setCenterCardDrag(false);"""
HINT_3 = "Hold the pool table, dartboard, or card table to move it — swipe the room to look around."
HINT_2 = "Hold the pool table or dartboard to move it — swipe the room to look around."
HINT_1 = "Hold the pool table to move it — swipe the room to look around."
HINT_4 = "Hold the pool table, dartboard, card table, or dominoes table to move it — swipe the room to look around."
DOM_PNG_REQUIRE = "require('../../assets/houses/items/dominoes.png')"
DOM_JPG_REQUIRE = "require('../../assets/houses/items/dominoes.jpg')"

# PanResponder import (same strategy as the import-fix / dartboard /
# cardtable patches; the brace regex is [^}]* so it can never span
# across an earlier import's closing brace to reach the react-native one).
RN_BRACE_RE = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]react-native['\"]\s*;?")
RN_ANY_RE = re.compile(r"import[^\n]*from\s*['\"]react-native['\"]\s*;?")
TOP_IMPORT_RE = re.compile(r"^import[^\n]*;\s*$", re.M)

DOM_STATE_BLOCK = """
  // ACTIVITY_CENTER_DOMINOES: hold-drag arrange (Veno only), tap = dominoes menu.
  // Default {x:0.15, y:0.5} — left side, middle height of the wide scene,
  // clear of the pool table's default {0.5, 0.72}, the dartboard's {0.5, 0.28},
  // and the card table's {0.85, 0.5}. Shares the v2 hold/drag refs and the
  // MERGED save (one call sends all four fixtures' positions).
  const [centerDomPos, setCenterDomPos] = useState({ x: 0.15, y: 0.5 });
  const [centerDomDrag, setCenterDomDrag] = useState(false);
  const centerDomPosRef = useRef({ x: 0.15, y: 0.5 });
  const centerDomResponder = useRef<any>(null);
  const storedToCenterDomPos = (l: any) => {
    if (!l || typeof l.x !== 'number' || typeof l.y !== 'number') return { x: 0.15, y: 0.5 };
    return storedToCenterPos(l);
  };"""

DOM_RESPONDER_BLOCK = """
  if (!centerDomResponder.current) {
    centerDomResponder.current = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        setCenterSceneScrollEnabled(false);
        centerHoldStartRef.current = Date.now();
        centerDragStartRef.current = { ...(centerDomPosRef.current || { x: 0.15, y: 0.5 }) };
        centerDragMovedRef.current = false;
      },
      onPanResponderMove: (evt: any, gesture: any) => {
        if (centerCtxRef.current.playerId !== CENTER_ARRANGE_OWNER_ID) return;
        if (Date.now() - centerHoldStartRef.current < 250) return;
        const s = centerDragStartRef.current || { x: 0.15, y: 0.5 };
        const nx = Math.min(0.94, Math.max(0.06, s.x + gesture.dx / centerSceneWRef.current));
        const ny = Math.min(0.94, Math.max(0.06, s.y + gesture.dy / centerSceneHRef.current));
        centerDragMovedRef.current = true;
        centerDomPosRef.current = { x: nx, y: ny };
        setCenterDomPos({ x: nx, y: ny });
        setCenterDomDrag(true);
        setCenterLayoutDirty(true);
      },
      onPanResponderRelease: (evt: any, gesture: any) => {
        setCenterSceneScrollEnabled(true);
        setCenterDomDrag(false);
        const tapDist = Math.hypot(gesture.dx || 0, gesture.dy || 0);
        if (tapDist < 12) { setDominoMenuCenterOpen(true); return; }
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
      onPanResponderTerminate: () => {
        setCenterSceneScrollEnabled(true);
        setCenterDomDrag(false);
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""

DOM_LOAD_LINES = """    const posDom = storedToCenterDomPos((activeCenter as any)?.layout?.dominoes);
    centerDomPosRef.current = posDom;
    setCenterDomPos(posDom);
    setCenterDomDrag(false);"""

DOM_LOAD_EFFECT = """
  // ACTIVITY_CENTER_DOMINOES: load this center's stored dominoes spot when it opens.
  useEffect(() => {
    const posDom = storedToCenterDomPos((activeCenter as any)?.layout?.dominoes);
    centerDomPosRef.current = posDom;
    setCenterDomPos(posDom);
    setCenterDomDrag(false);
  }, [activeCenter?.id]);"""

# __DOM_ART_REQUIRE__ is replaced with the resolved house image require.
DOM_VIEW = """
              <View
                {...(centerDomResponder.current ? centerDomResponder.current.panHandlers : {})}
                style={{ position: 'absolute', left: centerDomPos.x * centerSceneW - 140, top: centerDomPos.y * centerSceneH - 93, width: 280, height: 187, borderWidth: centerDomDrag ? 3 : 0, borderColor: '#ffd54f', borderRadius: 8 }}
              >
                <Image source={__DOM_ART_REQUIRE__} style={{ width: 280, height: 187, borderRadius: 8 }} resizeMode="contain" />
              </View>"""


def _balance(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def _resolve_dom_art(src, root):
    """House dominoes table picture source, in fallback order. Returns
    (require_expression, source_name). Never a menu card / emoji tile."""
    m = re.search(r"id:\s*'dominoes'[^}]*?image:\s*(require\([^)]+\))", src)
    if m:
        return m.group(1), "house-items-entry"
    m = re.search(r"require\(['\"][^'\"]*dominoes\.png['\"]\)", src)
    if m:
        return m.group(0), "png-require-in-index"
    m = re.search(r"require\(['\"][^'\"]*dominoes\.jpg['\"]\)", src)
    if m:
        return m.group(0), "jpg-require-in-index"
    if (root / "frontend/assets/houses/items/dominoes.png").exists():
        return DOM_PNG_REQUIRE, "asset-file-png"
    if (root / "frontend/assets/houses/items/dominoes.jpg").exists():
        return DOM_JPG_REQUIRE, "asset-file-jpg"
    return DOM_PNG_REQUIRE, "canonical-path"


def _dom_menu_span(src):
    """(start, end) of the DominoTableMenuModal component, or None."""
    start = src.find("const DominoTableMenuModal = ({")
    if start == -1:
        return None
    end = src.find("\n};", start)
    if end == -1:
        return None
    return (start, end + len("\n};"))


def _panresponder_imported(src):
    """True iff PanResponder is imported FROM react-native (brace list
    or a standalone line). A bare PanResponder.create usage is NOT one."""
    m = RN_BRACE_RE.search(src)
    if m and re.search(r"\bPanResponder\b", m.group(1)):
        return True
    if re.search(r"import\s*\{\s*PanResponder\s*\}\s*from\s*['\"]react-native['\"]", src):
        return True
    return False


def _panresponder_usable(src):
    """PanResponder imported from react-native AND at least one
    PanResponder. usage (the responder code) exists."""
    return _panresponder_imported(src) and src.count("PanResponder.") >= 1


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - center dominoes table NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore") if API.exists() else ""
    orig = _balance(src)
    landed = []
    warnings = []
    changed = False

    # ---- Idempotency: dominoes table already landed. ----
    if "ACTIVITY_CENTER_DOMINOES" in src and "centerDomPos" in src:
        print("ACTIVITY_CENTER_DOMINOES_ALREADY_APPLIED")
        return 0

    # ---- Preconditions: the v2 room + card table + the house dominoes menu. ----
    if "centerSceneScrollEnabled" not in src or "ACTIVITY_CENTER_POOL_V2" not in src:
        print("WARNING: v2 center room not found - run the pool-table v2 patch first, dominoes table NOT added")
        return 1
    if "centerCardPos" not in src or "ACTIVITY_CENTER_CARDTABLE" not in src:
        print("WARNING: card table not found - run the cardtable frontend patch first, dominoes table NOT added")
        return 1
    if "DominoTableMenuModal visible={dominoMenuOpen}" not in src:
        print("WARNING: house dominoes table menu not found - dominoes table NOT added")
        return 1
    if "saveCenterLayout" not in src:
        print("WARNING: v2 layout save not found - run the pool-table v2 patch first, dominoes table NOT added")
        return 1

    # ---- Piece 0: resolve the house's live dominoes picture (proof line). ----
    art, art_source = _resolve_dom_art(src, ROOT)
    print("DOMINOES_V2_ART=%s via %s" % (art, art_source))
    if art_source == "canonical-path":
        print("NOTE: dominoes art require not found in index.tsx and no asset file on disk - using the canonical path (dominoes.png written by the house dominoes patch); if the bundle cannot resolve it, the table will not render")

    # ---- Piece 1: hideManage on DominoTableMenuModal (all-or-nothing). ----
    hide_ok = False
    span = _dom_menu_span(src)
    if span is None:
        print("WARNING: DominoTableMenuModal component not found - MOVE/SELL stay visible but inert on the center path")
        warnings.append("hidemanage")
    else:
        s0, s1 = span
        body = src[s0:s1]
        new_body = body
        edits = []

        m = re.search(r"const DominoTableMenuModal = \(\{\s*([^}]*?)\s*\}:", new_body)
        if not m or "hideManage" in m.group(1):
            edits.append(("destructure", False))
        else:
            props = m.group(1).rstrip()
            new_body = new_body[:m.start(1)] + props + ", hideManage" + new_body[m.end(1):]
            edits.append(("destructure", True))

        if new_body.count("onSell: () => void })") == 1:
            new_body = new_body.replace("onSell: () => void })", "onSell: () => void; hideManage?: boolean })", 1)
            edits.append(("type", True))
        elif re.search(r"onSell: \(\) => void;?\s*\}\)", new_body):
            new_body = re.sub(r"onSell: \(\) => void;?\s*\}\)",
                              "onSell: () => void; hideManage?: boolean })", new_body, count=1)
            edits.append(("type", True))
        else:
            edits.append(("type", False))

        old_sub = ">Play Dominoes, move it, or sell it.</Text>"
        if new_body.count(old_sub) == 1:
            new_body = new_body.replace(old_sub, ">{hideManage ? 'Play a game.' : 'Play Dominoes, move it, or sell it.'}</Text>", 1)
            edits.append(("subtitle", True))
        else:
            edits.append(("subtitle", False))

        move_old = (
            "        <TouchableOpacity onPress={onMove} style={{ backgroundColor: '#666666', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>MOVE</Text>\n"
            "        </TouchableOpacity>"
        )
        move_new = (
            "        {!hideManage && (\n"
            "        <TouchableOpacity onPress={onMove} style={{ backgroundColor: '#666666', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>MOVE</Text>\n"
            "        </TouchableOpacity>\n"
            "        )}"
        )
        if new_body.count(move_old) == 1:
            new_body = new_body.replace(move_old, move_new, 1)
            edits.append(("move", True))
        else:
            edits.append(("move", False))

        hint_old = "        <Text style={{ color: '#999999', fontSize: 11, textAlign: 'center', marginBottom: 10 }}>Move: close this menu, then drag the table.</Text>"
        hint_new = (
            "        {!hideManage && (\n"
            "        <Text style={{ color: '#999999', fontSize: 11, textAlign: 'center', marginBottom: 10 }}>Move: close this menu, then drag the table.</Text>\n"
            "        )}"
        )
        if new_body.count(hint_old) == 1:
            new_body = new_body.replace(hint_old, hint_new, 1)
            edits.append(("hint", True))
        else:
            edits.append(("hint", False))

        sell_old = (
            "        <TouchableOpacity onPress={onSell} style={{ backgroundColor: '#b7950b', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>SELL ($10,000 back)</Text>\n"
            "        </TouchableOpacity>"
        )
        sell_new = (
            "        {!hideManage && (\n"
            "        <TouchableOpacity onPress={onSell} style={{ backgroundColor: '#b7950b', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>SELL ($10,000 back)</Text>\n"
            "        </TouchableOpacity>\n"
            "        )}"
        )
        if new_body.count(sell_old) == 1:
            new_body = new_body.replace(sell_old, sell_new, 1)
            edits.append(("sell", True))
        else:
            edits.append(("sell", False))

        failed = [name for name, ok in edits if not ok]
        if "hideManage" in body:
            print("ACTIVITY_CENTER_DOMINOES_HIDEMANAGE_ALREADY_APPLIED")
            hide_ok = True
            landed.append("hidemanage")
        elif not failed:
            src = src[:s0] + new_body + src[s1:]
            changed = True
            print("ACTIVITY_CENTER_DOMINOES_HIDEMANAGE_OK")
            hide_ok = True
            landed.append("hidemanage")
        else:
            print("WARNING: DominoTableMenuModal hideManage edit failed (%s) - MOVE/SELL stay visible but inert on the center path" % ",".join(failed))
            warnings.append("hidemanage")

    # ---- Piece 2: PanResponder import (own piece; earlier patches may have landed it). ----
    if _panresponder_imported(src):
        print("ACTIVITY_CENTER_DOMINOES_PANRESPONDER_ALREADY_APPLIED")
        landed.append("panresponder")
    else:
        m = RN_BRACE_RE.search(src)
        new = None
        strategy = None
        if m:
            inner = m.group(1)
            if "\n" in inner:
                ind = re.search(r"\n(\s*)\S", inner)
                indent = ind.group(1) if ind else "  "
                new = src[:m.start(1)] + "\n" + indent + "PanResponder," + inner + src[m.end(1):]
                strategy = "a-multi-line-brace-insert"
            else:
                new = src[:m.start(1)] + " PanResponder," + inner + src[m.end(1):]
                strategy = "b-single-line-brace-insert"
        else:
            m2 = RN_ANY_RE.search(src)
            if m2:
                quote = "'" if "'" in m2.group(0) else '"'
                line = "import { PanResponder } from %sreact-native%s;" % (quote, quote)
                new = src[:m2.end()] + "\n" + line + src[m2.end():]
                strategy = "c-standalone-line-after-rn-import"
            else:
                head = src[:4000]
                imports = list(TOP_IMPORT_RE.finditer(head))
                if imports:
                    last = imports[-1]
                    new = src[:last.end()] + "\nimport { PanResponder } from 'react-native';" + src[last.end():]
                    strategy = "d-standalone-line-after-last-import"
        if new is None or not _panresponder_usable(new):
            print("WARNING: PanResponder import could not be added - dominoes hold-drag NOT added (would not compile)")
            return 1
        src = new
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_PANRESPONDER_OK (%s)" % strategy)
        landed.append("panresponder")

    # ---- Piece 3: dominoes state (positions, refs, dominoes loader). ----
    if "ACTIVITY_CENTER_DOMINOES: hold-drag arrange" in src:
        print("ACTIVITY_CENTER_DOMINOES_STATE_ALREADY_APPLIED")
        landed.append("state")
    elif src.count(CARD_STATE_ANCHOR) == 1:
        src = src.replace(CARD_STATE_ANCHOR, CARD_STATE_ANCHOR + DOM_STATE_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_STATE_OK")
        landed.append("state")
    else:
        print("WARNING: card state anchor matched %dx - dominoes state NOT added" % src.count(CARD_STATE_ANCHOR))
        return 1

    # ---- Piece 4: MERGED save — one call sends ALL FOUR fixtures (hard gate). ----
    if "{ pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current), dominoes: centerPosToStored(centerDomPosRef.current) }" in src:
        print("ACTIVITY_CENTER_DOMINOES_SAVE_ALREADY_APPLIED")
        landed.append("save")
    elif src.count(SAVE_3) == 1 and src.count(BACK_3) == 1:
        src = src.replace(SAVE_3, SAVE_4, 1)
        src = src.replace(
            BACK_3,
            BACK_3 + "\n" + """        const backDom = storedToCenterDomPos((activeCenter as any)?.layout?.dominoes);
        centerDomPosRef.current = backDom;
        setCenterDomPos(backDom);""",
            1)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_SAVE_OK (merged: pool + dart + card + dominoes in one call)")
        landed.append("save")
    else:
        print("WARNING: merged save lines not matched (save=%dx 403-back=%dx) - merged save NOT wired; dominoes table NOT added (a dominoes save would drop the pool/dart/card spots)" % (src.count(SAVE_3), src.count(BACK_3)))
        return 1

    # ---- Piece 5: dominoes responder (hold-drag), after the LAST responder (the card one). ----
    if "centerDomResponder.current = PanResponder.create" in src:
        print("ACTIVITY_CENTER_DOMINOES_RESPONDER_ALREADY_APPLIED")
        landed.append("responder")
    else:
        tail_idx = src.rfind(RESPONDER_TAIL)
        if tail_idx == -1:
            print("WARNING: responder tail not found - dominoes responder NOT added")
            return 1
        tail_end = tail_idx + len(RESPONDER_TAIL)
        src = src[:tail_end] + DOM_RESPONDER_BLOCK + src[tail_end:]
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_RESPONDER_OK")
        landed.append("responder")

    # ---- Piece 6: load the stored dominoes spot when a center opens. ----
    # NOTE: check for the LOAD line (const posDom), not the bare
    # storedToCenterDomPos(...) call — the 403-back in piece 4 already
    # contains that call, so a bare check would false-positive here.
    if "const posDom = storedToCenterDomPos" in src:
        print("ACTIVITY_CENTER_DOMINOES_LOAD_ALREADY_APPLIED")
        landed.append("load")
    elif src.count(CARD_LOAD_BLOCK) == 1:
        src = src.replace(CARD_LOAD_BLOCK, CARD_LOAD_BLOCK + "\n" + DOM_LOAD_LINES, 1)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_LOAD_OK (card load extended)")
        landed.append("load")
    elif src.count(PRESENCE_EFFECT_CLOSE) == 1:
        src = src.replace(PRESENCE_EFFECT_CLOSE, PRESENCE_EFFECT_CLOSE + DOM_LOAD_EFFECT, 1)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_LOAD_OK (standalone load effect)")
        landed.append("load")
    else:
        print("WARNING: load anchors matched 0x - stored dominoes spot NOT loaded (table will sit at the default spot)")
        warnings.append("load")

    # ---- Piece 7: center menu open state. ----
    if "const [dominoMenuCenterOpen, setDominoMenuCenterOpen]" in src:
        print("ACTIVITY_CENTER_DOMINOES_MENU_STATE_ALREADY_APPLIED")
        landed.append("menu-state")
    else:
        dom_state_line = None
        for ln in src.split("\n"):
            if "dominoMenuOpen" in ln and "useState" in ln:
                dom_state_line = ln
                break
        if dom_state_line is not None:
            src = src.replace(dom_state_line, dom_state_line + "\n  const [dominoMenuCenterOpen, setDominoMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_DOMINOES_MENU_STATE_OK")
            landed.append("menu-state")
        elif src.count("const [poolMenuCenterOpen, setPoolMenuCenterOpen]") == 1:
            src = src.replace("const [poolMenuCenterOpen, setPoolMenuCenterOpen]",
                              "const [poolMenuCenterOpen, setPoolMenuCenterOpen]\n  const [dominoMenuCenterOpen, setDominoMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_DOMINOES_MENU_STATE_OK (fallback anchor)")
            landed.append("menu-state")
        else:
            print("WARNING: dominoes menu state anchor not found - center menu state NOT added")
            return 1

    # ---- Piece 8: center render of the SAME DominoTableMenuModal. ----
    # PvP inclusion is decided ONLY from the dominoes pieces themselves
    # (the pool/darts/card menus already have onPlayPvp — a global check would lie).
    house_render_line = None
    for ln in src.split("\n"):
        if "DominoTableMenuModal visible={dominoMenuOpen}" in ln:
            house_render_line = ln
            break
    has_pvp_render = house_render_line is not None and "onPlayPvp" in house_render_line
    has_pvp_state = "const [dominoPvpOpen, setDominoPvpOpen]" in src
    has_pvp_modal = "DominoPvpModal visible={dominoPvpOpen}" in src
    pvp_ok = has_pvp_render and has_pvp_state and has_pvp_modal
    if not pvp_ok:
        print("NOTE: dominoes PvP room screen not fully wired in this build (render=%s state=%s modal=%s) - center menu matches the house menu without the PvP button" % (has_pvp_render, has_pvp_state, has_pvp_modal))

    if "DominoTableMenuModal visible={dominoMenuCenterOpen}" in src:
        print("ACTIVITY_CENTER_DOMINOES_RENDER_ALREADY_APPLIED")
        landed.append("render")
    else:
        menu_lines = src.split("\n")
        house_idx = None
        for i, ln in enumerate(menu_lines):
            if "DominoTableMenuModal visible={dominoMenuOpen}" in ln:
                house_idx = i
                break
        close_idx = None
        if house_idx is not None:
            for j in range(house_idx, min(len(menu_lines), house_idx + 6)):
                if menu_lines[j].strip() == ") : null}" or menu_lines[j].strip().endswith(") : null}"):
                    close_idx = j
                    break
        if house_idx is None or close_idx is None:
            print("WARNING: house dominoes menu render close not found - center menu render NOT added")
            return 1
        pvp_prop = " onPlayPvp={() => { setDominoMenuCenterOpen(false); setDominoPvpOpen(true); }}" if pvp_ok else ""
        hide_prop = " hideManage" if hide_ok else ""
        render_block = (
            "      {dominoMenuCenterOpen ? (<DominoTableMenuModal visible={dominoMenuCenterOpen} onClose={() => setDominoMenuCenterOpen(false)}"
            " onPlay={() => { setDominoMenuCenterOpen(false); setDominoGameOpen(true); }}" + pvp_prop +
            " onMove={() => setDominoMenuCenterOpen(false)} onSell={() => setDominoMenuCenterOpen(false)}" + hide_prop + " />) : null}"
        )
        menu_lines = menu_lines[:close_idx + 1] + [render_block] + menu_lines[close_idx + 1:]
        src = "\n".join(menu_lines)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_RENDER_OK")
        landed.append("render")

    # ---- Piece 9: dominoes picture in the scene, after the card table. ----
    if "centerDomResponder.current.panHandlers" in src:
        print("ACTIVITY_CENTER_DOMINOES_PICTURE_ALREADY_APPLIED")
        landed.append("picture")
    else:
        ph = src.find("centerCardResponder.current.panHandlers")
        if ph == -1:
            print("WARNING: card table picture not found in scene - dominoes picture NOT added")
            return 1
        view_close = src.find("</View>", ph)
        if view_close == -1:
            print("WARNING: card table view close not found - dominoes picture NOT added")
            return 1
        view = DOM_VIEW.replace("__DOM_ART_REQUIRE__", art)
        src = src[:view_close + len("</View>")] + view + src[view_close + len("</View>"):]
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_PICTURE_OK")
        landed.append("picture")

    # ---- Piece 10: card table SMALLER — 280x187 -> 180x120 (offsets adjusted too). ----
    if "centerCardPos.x * centerSceneW - 90" in src and "width: 180, height: 120" in src:
        print("ACTIVITY_CENTER_DOMINOES_CARD_SMALL_ALREADY_APPLIED")
        landed.append("card-small")
    else:
        ch = src.find("centerCardResponder.current.panHandlers")
        if ch == -1:
            print("WARNING: card table picture not found - card table size NOT changed")
            warnings.append("card-small")
        else:
            v_start = src.rfind("<View", 0, ch)
            v_end = src.find("</View>", ch)
            if v_start == -1 or v_end == -1:
                print("WARNING: card table view boundaries not found - card table size NOT changed")
                warnings.append("card-small")
            else:
                cview = src[v_start:v_end + len("</View>")]
                new_cview = cview
                if cview.count("centerSceneW - 140") == 1:
                    new_cview = new_cview.replace("centerSceneW - 140", "centerSceneW - 90", 1)
                if cview.count("centerSceneH - 93") == 1:
                    new_cview = new_cview.replace("centerSceneH - 93", "centerSceneH - 60", 1)
                if cview.count("width: 280, height: 187") == 2:
                    new_cview = new_cview.replace("width: 280, height: 187", "width: 180, height: 120")
                if new_cview != cview and "width: 180, height: 120" in new_cview:
                    src = src[:v_start] + new_cview + src[v_end + len("</View>"):]
                    changed = True
                    print("ACTIVITY_CENTER_DOMINOES_CARD_SMALL_OK (280x187 -> 180x120)")
                    landed.append("card-small")
                else:
                    print("WARNING: card table size pattern not matched - card table size NOT changed")
                    warnings.append("card-small")

    # ---- Piece 11: hint now names all four fixtures (best effort). ----
    if HINT_4 in src:
        print("ACTIVITY_CENTER_DOMINOES_HINT_ALREADY_APPLIED")
        landed.append("hint")
    elif src.count(HINT_3) == 1:
        src = src.replace(HINT_3, HINT_4, 1)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_HINT_OK")
        landed.append("hint")
    elif src.count(HINT_2) == 1:
        src = src.replace(HINT_2, HINT_4, 1)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_HINT_OK (from two-fixture hint)")
        landed.append("hint")
    elif src.count(HINT_1) == 1:
        src = src.replace(HINT_1, HINT_4, 1)
        changed = True
        print("ACTIVITY_CENTER_DOMINOES_HINT_OK (from pool-only hint)")
        landed.append("hint")
    else:
        print("NOTE: Veno hint matched 0x - hint stays as-is")

    # ---- api.ts sanity: the layout save fn must exist (v2's piece). ----
    if asrc and "export const saveCenterLayout" not in asrc:
        print("WARNING: saveCenterLayout missing in api.ts - drag will move locally only (v2 api piece did not land)")
        warnings.append("api")

    if _balance(src) != orig:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    if not landed:
        print("ACTIVITY_CENTER_DOMINOES_PARTIAL: nothing landed")
        return 1
    if not changed:
        print("ACTIVITY_CENTER_DOMINOES_ALREADY_APPLIED")
        return 0
    IDX.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_DOMINOES_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
