#!/usr/bin/env python3
"""Street Legends frontend: Activity Center card table — same v2
treatment as the pool table and dartboard (real picture in the
scrolling room, tap = card menu, hold-drag arrange Veno-only), PLUS
the dartboard shrinks to half size.

User request (2026-11-06 12:08 EST): "Do the same thing for the card
table and make the dart board smaller" — two parts: (1) the card
table gets the pool/dart treatment; (2) the dartboard picture gets
SMALLER (it renders 280x187, same as the big furniture — it should be
clearly smaller than the pool table and card table).

What this does (frontend; the backend patch extends the layout clamp):
  1. REAL CARD TABLE PICTURE IN THE SAME SCENE: the card table renders
     as its ACTUAL picture — the house's exact image source, resolved
     at patch time from the HOUSE_ITEMS cardtable entry's image
     (require, already .png — no .jpg/.png swap to trip over, but the
     same fallback chain as v2). 280x187, resizeMode "contain",
     exactly like the house room render. Placed in the SAME horizontal
     ScrollView scene as the pool table and dartboard, at its own
     stored fractional position. Default {x:0.85, y:0.5} — right side,
     middle height of the wide scene, clear of the pool table's
     default {0.5, 0.72} and the dartboard's {0.5, 0.28}. No menu
     card, no "TAP TO PLAY" text, nothing in any shop/item catalog
     or house dropdown.
  2. DARTBOARD SMALLER: the dartboard picture goes from 280x187 to
     140x94 — about half, clearly smaller than the pool table and
     card table while still tappable. Its position, tap, and
     hold-drag are otherwise untouched.
  3. TAP = CARD PLAY MENU: tapping the card table picture opens the
     SAME CardTableMenuModal the house uses (SPADES and GIN RUMMY
     each -> CardGameModal PvC; PLAYER VS PLAYER -> CardPvpModal room
     screen with create/join, REJOIN, auto-start, no chat; wager UI
     inside it untouched). MOVE/SELL hidden on the center path only
     via a new optional hideManage prop on CardTableMenuModal (same
     pattern as the pool/darts menus); if the prop cannot land,
     onMove/onSell are inert (close only) — nothing can ever be
     moved or sold from a center. If the house card PvP is not fully
     wired in this build, the center menu matches the house menu
     without the PvP button (NOTE printed).
  4. HOLD-DRAG = ARRANGE (Veno only): same interaction as the pool
     table and dartboard — press-and-HOLD (250ms), then drag (gold
     border while dragging, scene scroll disabled while dragging);
     tap (<12px) opens the menu instead. The hint renders only for
     Mayor Veno; for anyone else all three fixtures are fixed and
     hold does nothing (tap still opens the menus).
  5. MERGED LAYOUT SAVE (critical): the dartboard merged save is
     replaced by ONE shared save that always sends the FULL layout
     {pool_table, dart_board, card_table} (all three positions,
     converted at the boundary to the backend's integer box).
     Saving any one fixture never wipes the others' spots. A 403
     snaps ALL THREE fixtures back with "Only Mayor Veno can
     arrange this center." The modal loads all three stored
     positions on open.
  6. PanResponder import: if the import-fix / dartboard patch
     already landed it, ALREADY_APPLIED; otherwise this patch adds
     it itself (same brace-insert strategy, never anchoring on the
     last member).

UNCHANGED: pool table (picture, menu, hold-drag, position),
dartboard (picture except the size, menu, hold-drag, position),
"Inside now" list, LEAVE, presence, the card menu contents, house
card table + house rules, the layout endpoint + its permission.
The card ROOM endpoints need no change: POST /api/cards/rooms/create
takes only {player_id, player_name, game, seed} and /join only
{code, player_id, player_name} — no house lookup, no ownership
check (same as pool/darts) — so center PvP works with no room change.

Run from /app: python3 frontend/patch-activity-center-cardtable-frontend.py
Frontend / Expo Go only. Run AFTER the dartboard frontend patch is
live (the merged save needs the dartboard pieces first) and after
the cardtable backend patch is Published (the merged save needs the
three-key clamp live first).
Idempotent: a full re-run prints ACTIVITY_CENTER_CARDTABLE_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"
MARKER = "ACTIVITY_CENTER_CARDTABLE_OK"
VENO_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"

DART_STATE_ANCHOR = "  const [centerDartDrag, setCenterDartDrag] = useState(false);"
PRESENCE_EFFECT_CLOSE = "  }, [activeCenter?.id, playerId]);"
# Merged save after the dartboard patch (two fixtures); extended to three.
SAVE_2 = "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current) });"
SAVE_3 = "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current) });"
BACK_2 = """        const back = storedToCenterPos((activeCenter as any)?.layout?.pool_table);
        const backDart = storedToCenterDartPos((activeCenter as any)?.layout?.dart_board);
        centerPoolPosRef.current = back;
        setCenterPoolPos(back);
        centerDartPosRef.current = backDart;
        setCenterDartPos(backDart);"""
RESPONDER_TAIL = """        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""
DART_LOAD_BLOCK = """    const posDart = storedToCenterDartPos((activeCenter as any)?.layout?.dart_board);
    centerDartPosRef.current = posDart;
    setCenterDartPos(posDart);
    setCenterDartDrag(false);"""
HINT_2 = "Hold the pool table or dartboard to move it — swipe the room to look around."
HINT_1 = "Hold the pool table to move it — swipe the room to look around."
HINT_3 = "Hold the pool table, dartboard, or card table to move it — swipe the room to look around."
CARD_PNG_REQUIRE = "require('../../assets/houses/items/cardtable.png')"
CARD_JPG_REQUIRE = "require('../../assets/houses/items/cardtable.jpg')"

# PanResponder import (same strategy as the import-fix / dartboard
# patches; the brace regex is [^}]* so it can never span across an
# earlier import's closing brace to reach the react-native one).
RN_BRACE_RE = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]react-native['\"]\s*;?")
RN_ANY_RE = re.compile(r"import[^\n]*from\s*['\"]react-native['\"]\s*;?")
TOP_IMPORT_RE = re.compile(r"^import[^\n]*;\s*$", re.M)

CARD_STATE_BLOCK = """
  // ACTIVITY_CENTER_CARDTABLE: hold-drag arrange (Veno only), tap = card menu.
  // Default {x:0.85, y:0.5} — right side, middle height of the wide scene,
  // clear of the pool table's default {0.5, 0.72} and the dartboard's {0.5, 0.28}.
  // Shares the v2 hold/drag refs and the MERGED save (one call sends all
  // three fixtures' positions).
  const [centerCardPos, setCenterCardPos] = useState({ x: 0.85, y: 0.5 });
  const [centerCardDrag, setCenterCardDrag] = useState(false);
  const centerCardPosRef = useRef({ x: 0.85, y: 0.5 });
  const centerCardResponder = useRef<any>(null);
  const storedToCenterCardPos = (l: any) => {
    if (!l || typeof l.x !== 'number' || typeof l.y !== 'number') return { x: 0.85, y: 0.5 };
    return storedToCenterPos(l);
  };"""

CARD_RESPONDER_BLOCK = """
  if (!centerCardResponder.current) {
    centerCardResponder.current = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        setCenterSceneScrollEnabled(false);
        centerHoldStartRef.current = Date.now();
        centerDragStartRef.current = { ...(centerCardPosRef.current || { x: 0.85, y: 0.5 }) };
        centerDragMovedRef.current = false;
      },
      onPanResponderMove: (evt: any, gesture: any) => {
        if (centerCtxRef.current.playerId !== CENTER_ARRANGE_OWNER_ID) return;
        if (Date.now() - centerHoldStartRef.current < 250) return;
        const s = centerDragStartRef.current || { x: 0.85, y: 0.5 };
        const nx = Math.min(0.94, Math.max(0.06, s.x + gesture.dx / centerSceneWRef.current));
        const ny = Math.min(0.94, Math.max(0.06, s.y + gesture.dy / centerSceneHRef.current));
        centerDragMovedRef.current = true;
        centerCardPosRef.current = { x: nx, y: ny };
        setCenterCardPos({ x: nx, y: ny });
        setCenterCardDrag(true);
        setCenterLayoutDirty(true);
      },
      onPanResponderRelease: (evt: any, gesture: any) => {
        setCenterSceneScrollEnabled(true);
        setCenterCardDrag(false);
        const tapDist = Math.hypot(gesture.dx || 0, gesture.dy || 0);
        if (tapDist < 12) { setCardMenuCenterOpen(true); return; }
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
      onPanResponderTerminate: () => {
        setCenterSceneScrollEnabled(true);
        setCenterCardDrag(false);
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""

CARD_LOAD_LINES = """    const posCard = storedToCenterCardPos((activeCenter as any)?.layout?.card_table);
    centerCardPosRef.current = posCard;
    setCenterCardPos(posCard);
    setCenterCardDrag(false);"""

CARD_LOAD_EFFECT = """
  // ACTIVITY_CENTER_CARDTABLE: load this center's stored card table spot when it opens.
  useEffect(() => {
    const posCard = storedToCenterCardPos((activeCenter as any)?.layout?.card_table);
    centerCardPosRef.current = posCard;
    setCenterCardPos(posCard);
    setCenterCardDrag(false);
  }, [activeCenter?.id]);"""

# __CARD_ART_REQUIRE__ is replaced with the resolved house image require.
CARD_VIEW = """
              <View
                {...(centerCardResponder.current ? centerCardResponder.current.panHandlers : {})}
                style={{ position: 'absolute', left: centerCardPos.x * centerSceneW - 140, top: centerCardPos.y * centerSceneH - 93, width: 280, height: 187, borderWidth: centerCardDrag ? 3 : 0, borderColor: '#ffd54f', borderRadius: 8 }}
              >
                <Image source={__CARD_ART_REQUIRE__} style={{ width: 280, height: 187, borderRadius: 8 }} resizeMode="contain" />
              </View>"""


def _balance(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def _resolve_card_art(src, root):
    """House card table picture source, in fallback order. Returns
    (require_expression, source_name). Never a menu card / emoji tile."""
    m = re.search(r"id:\s*'cardtable'[^}]*?image:\s*(require\([^)]+\))", src)
    if m:
        return m.group(1), "house-items-entry"
    m = re.search(r"require\(['\"][^'\"]*cardtable\.png['\"]\)", src)
    if m:
        return m.group(0), "png-require-in-index"
    m = re.search(r"require\(['\"][^'\"]*cardtable\.jpg['\"]\)", src)
    if m:
        return m.group(0), "jpg-require-in-index"
    if (root / "frontend/assets/houses/items/cardtable.png").exists():
        return CARD_PNG_REQUIRE, "asset-file-png"
    if (root / "frontend/assets/houses/items/cardtable.jpg").exists():
        return CARD_JPG_REQUIRE, "asset-file-jpg"
    return CARD_PNG_REQUIRE, "canonical-path"


def _card_menu_span(src):
    """(start, end) of the CardTableMenuModal component, or None."""
    start = src.find("const CardTableMenuModal = ({")
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
        print("WARNING: index.tsx not found - center card table NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore") if API.exists() else ""
    orig = _balance(src)
    landed = []
    warnings = []
    changed = False

    # ---- Idempotency: card table already landed. ----
    if "ACTIVITY_CENTER_CARDTABLE" in src and "centerCardPos" in src:
        print("ACTIVITY_CENTER_CARDTABLE_ALREADY_APPLIED")
        return 0

    # ---- Preconditions: the v2 room + dartboard + the house card menu. ----
    if "centerSceneScrollEnabled" not in src or "ACTIVITY_CENTER_POOL_V2" not in src:
        print("WARNING: v2 center room not found - run the pool-table v2 patch first, card table NOT added")
        return 1
    if "centerDartPos" not in src or "ACTIVITY_CENTER_DARTBOARD" not in src:
        print("WARNING: dartboard not found - run the dartboard frontend patch first, card table NOT added")
        return 1
    if "CardTableMenuModal visible={cardMenuOpen}" not in src:
        print("WARNING: house card table menu not found - card table NOT added")
        return 1
    if "saveCenterLayout" not in src:
        print("WARNING: v2 layout save not found - run the pool-table v2 patch first, card table NOT added")
        return 1

    # ---- Piece 0: resolve the house's live card table picture (proof line). ----
    art, art_source = _resolve_card_art(src, ROOT)
    print("CARD_V2_ART=%s via %s" % (art, art_source))
    if art_source == "canonical-path":
        print("NOTE: card table art require not found in index.tsx and no asset file on disk - using the canonical path (cardtable.png written by the house card table patch); if the bundle cannot resolve it, the table will not render")

    # ---- Piece 1: hideManage on CardTableMenuModal (all-or-nothing). ----
    hide_ok = False
    span = _card_menu_span(src)
    if span is None:
        print("WARNING: CardTableMenuModal component not found - MOVE/SELL stay visible but inert on the center path")
        warnings.append("hidemanage")
    else:
        s0, s1 = span
        body = src[s0:s1]
        new_body = body
        edits = []

        m = re.search(r"const CardTableMenuModal = \(\{\s*([^}]*?)\s*\}:", new_body)
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

        old_sub = ">Play Spades or Gin Rummy, move it, or sell it.</Text>"
        if new_body.count(old_sub) == 1:
            new_body = new_body.replace(old_sub, ">{hideManage ? 'Play a game.' : 'Play Spades or Gin Rummy, move it, or sell it.'}</Text>", 1)
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
            print("ACTIVITY_CENTER_CARDTABLE_HIDEMANAGE_ALREADY_APPLIED")
            hide_ok = True
            landed.append("hidemanage")
        elif not failed:
            src = src[:s0] + new_body + src[s1:]
            changed = True
            print("ACTIVITY_CENTER_CARDTABLE_HIDEMANAGE_OK")
            hide_ok = True
            landed.append("hidemanage")
        else:
            print("WARNING: CardTableMenuModal hideManage edit failed (%s) - MOVE/SELL stay visible but inert on the center path" % ",".join(failed))
            warnings.append("hidemanage")

    # ---- Piece 2: PanResponder import (own piece; import-fix / dartboard may have landed it). ----
    if _panresponder_imported(src):
        print("ACTIVITY_CENTER_CARDTABLE_PANRESPONDER_ALREADY_APPLIED")
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
            print("WARNING: PanResponder import could not be added - card table hold-drag NOT added (would not compile)")
            return 1
        src = new
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_PANRESPONDER_OK (%s)" % strategy)
        landed.append("panresponder")

    # ---- Piece 3: card state (positions, refs, card loader). ----
    if "ACTIVITY_CENTER_CARDTABLE: hold-drag arrange" in src:
        print("ACTIVITY_CENTER_CARDTABLE_STATE_ALREADY_APPLIED")
        landed.append("state")
    elif src.count(DART_STATE_ANCHOR) == 1:
        src = src.replace(DART_STATE_ANCHOR, DART_STATE_ANCHOR + CARD_STATE_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_STATE_OK")
        landed.append("state")
    else:
        print("WARNING: dart state anchor matched %dx - card state NOT added" % src.count(DART_STATE_ANCHOR))
        return 1

    # ---- Piece 4: MERGED save — one call sends ALL THREE fixtures (hard gate). ----
    if "{ pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current) }" in src:
        print("ACTIVITY_CENTER_CARDTABLE_SAVE_ALREADY_APPLIED")
        landed.append("save")
    elif src.count(SAVE_2) == 1 and src.count(BACK_2) == 1:
        src = src.replace(SAVE_2, SAVE_3, 1)
        src = src.replace(
            BACK_2,
            BACK_2 + "\n" + """        const backCard = storedToCenterCardPos((activeCenter as any)?.layout?.card_table);
        centerCardPosRef.current = backCard;
        setCenterCardPos(backCard);""",
            1)
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_SAVE_OK (merged: pool + dart + card in one call)")
        landed.append("save")
    else:
        print("WARNING: merged save lines not matched (save=%dx 403-back=%dx) - merged save NOT wired; card table NOT added (a card save would drop the pool/dart spots)" % (src.count(SAVE_2), src.count(BACK_2)))
        return 1

    # ---- Piece 5: card responder (hold-drag), after the LAST responder (the dart one). ----
    if "centerCardResponder.current = PanResponder.create" in src:
        print("ACTIVITY_CENTER_CARDTABLE_RESPONDER_ALREADY_APPLIED")
        landed.append("responder")
    else:
        tail_idx = src.rfind(RESPONDER_TAIL)
        if tail_idx == -1:
            print("WARNING: responder tail not found - card responder NOT added")
            return 1
        tail_end = tail_idx + len(RESPONDER_TAIL)
        src = src[:tail_end] + CARD_RESPONDER_BLOCK + src[tail_end:]
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_RESPONDER_OK")
        landed.append("responder")

    # ---- Piece 6: load the stored card table spot when a center opens. ----
    # NOTE: check for the LOAD line (const posCard), not the bare
    # storedToCenterCardPos(...) call — the 403-back in piece 4 already
    # contains that call, so a bare check would false-positive here.
    if "const posCard = storedToCenterCardPos" in src:
        print("ACTIVITY_CENTER_CARDTABLE_LOAD_ALREADY_APPLIED")
        landed.append("load")
    elif src.count(DART_LOAD_BLOCK) == 1:
        src = src.replace(DART_LOAD_BLOCK, DART_LOAD_BLOCK + "\n" + CARD_LOAD_LINES, 1)
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_LOAD_OK (dart load extended)")
        landed.append("load")
    elif src.count(PRESENCE_EFFECT_CLOSE) == 1:
        src = src.replace(PRESENCE_EFFECT_CLOSE, PRESENCE_EFFECT_CLOSE + CARD_LOAD_EFFECT, 1)
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_LOAD_OK (standalone load effect)")
        landed.append("load")
    else:
        print("WARNING: load anchors matched 0x - stored card table spot NOT loaded (table will sit at the default spot)")
        warnings.append("load")

    # ---- Piece 7: center menu open state. ----
    if "const [cardMenuCenterOpen, setCardMenuCenterOpen]" in src:
        print("ACTIVITY_CENTER_CARDTABLE_MENU_STATE_ALREADY_APPLIED")
        landed.append("menu-state")
    else:
        card_state_line = None
        for ln in src.split("\n"):
            if "cardMenuOpen" in ln and "useState" in ln:
                card_state_line = ln
                break
        if card_state_line is not None:
            src = src.replace(card_state_line, card_state_line + "\n  const [cardMenuCenterOpen, setCardMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_CARDTABLE_MENU_STATE_OK")
            landed.append("menu-state")
        elif src.count("const [poolMenuCenterOpen, setPoolMenuCenterOpen]") == 1:
            src = src.replace("const [poolMenuCenterOpen, setPoolMenuCenterOpen]",
                              "const [poolMenuCenterOpen, setPoolMenuCenterOpen]\n  const [cardMenuCenterOpen, setCardMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_CARDTABLE_MENU_STATE_OK (fallback anchor)")
            landed.append("menu-state")
        else:
            print("WARNING: card menu state anchor not found - center menu state NOT added")
            return 1

    # ---- Piece 8: center render of the SAME CardTableMenuModal. ----
    # PvP inclusion is decided ONLY from the card pieces themselves
    # (the pool/darts menus already have onPlayPvp — a global check would lie).
    house_render_line = None
    for ln in src.split("\n"):
        if "CardTableMenuModal visible={cardMenuOpen}" in ln:
            house_render_line = ln
            break
    has_pvp_render = house_render_line is not None and "onPlayPvp" in house_render_line
    has_pvp_state = "const [cardPvpOpen, setCardPvpOpen]" in src
    has_pvp_modal = "CardPvpModal visible={cardPvpOpen}" in src
    pvp_ok = has_pvp_render and has_pvp_state and has_pvp_modal
    if not pvp_ok:
        print("NOTE: card PvP room screen not fully wired in this build (render=%s state=%s modal=%s) - center menu matches the house menu without the PvP button" % (has_pvp_render, has_pvp_state, has_pvp_modal))

    if "CardTableMenuModal visible={cardMenuCenterOpen}" in src:
        print("ACTIVITY_CENTER_CARDTABLE_RENDER_ALREADY_APPLIED")
        landed.append("render")
    else:
        menu_lines = src.split("\n")
        house_idx = None
        for i, ln in enumerate(menu_lines):
            if "CardTableMenuModal visible={cardMenuOpen}" in ln:
                house_idx = i
                break
        close_idx = None
        if house_idx is not None:
            for j in range(house_idx, min(len(menu_lines), house_idx + 6)):
                if menu_lines[j].strip() == ") : null}" or menu_lines[j].strip().endswith(") : null}"):
                    close_idx = j
                    break
        if house_idx is None or close_idx is None:
            print("WARNING: house card menu render close not found - center menu render NOT added")
            return 1
        pvp_prop = " onPlayPvp={() => { setCardMenuCenterOpen(false); setCardPvpOpen(true); }}" if pvp_ok else ""
        hide_prop = " hideManage" if hide_ok else ""
        render_block = (
            "      {cardMenuCenterOpen ? (<CardTableMenuModal visible={cardMenuCenterOpen} onClose={() => setCardMenuCenterOpen(false)}"
            " onPlaySpades={() => { setCardMenuCenterOpen(false); setCardGame('spades'); setCardGameOpen(true); }}"
            " onPlayGin={() => { setCardMenuCenterOpen(false); setCardGame('gin'); setCardGameOpen(true); }}" + pvp_prop +
            " onMove={() => setCardMenuCenterOpen(false)} onSell={() => setCardMenuCenterOpen(false)}" + hide_prop + " />) : null}"
        )
        menu_lines = menu_lines[:close_idx + 1] + [render_block] + menu_lines[close_idx + 1:]
        src = "\n".join(menu_lines)
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_RENDER_OK")
        landed.append("render")

    # ---- Piece 9: card table picture in the scene, after the dartboard. ----
    if "centerCardResponder.current.panHandlers" in src:
        print("ACTIVITY_CENTER_CARDTABLE_PICTURE_ALREADY_APPLIED")
        landed.append("picture")
    else:
        ph = src.find("centerDartResponder.current.panHandlers")
        if ph == -1:
            print("WARNING: dartboard picture not found in scene - card table picture NOT added")
            return 1
        view_close = src.find("</View>", ph)
        if view_close == -1:
            print("WARNING: dartboard view close not found - card table picture NOT added")
            return 1
        view = CARD_VIEW.replace("__CARD_ART_REQUIRE__", art)
        src = src[:view_close + len("</View>")] + view + src[view_close + len("</View>"):]
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_PICTURE_OK")
        landed.append("picture")

    # ---- Piece 10: dartboard SMALLER — 280x187 -> 140x94 (offsets halved too). ----
    if "centerDartPos.x * centerSceneW - 70" in src and "width: 140, height: 94" in src:
        print("ACTIVITY_CENTER_CARDTABLE_DART_SMALL_ALREADY_APPLIED")
        landed.append("dart-small")
    else:
        dh = src.find("centerDartResponder.current.panHandlers")
        if dh == -1:
            print("WARNING: dartboard picture not found - dartboard size NOT changed")
            warnings.append("dart-small")
        else:
            v_start = src.rfind("<View", 0, dh)
            v_end = src.find("</View>", dh)
            if v_start == -1 or v_end == -1:
                print("WARNING: dartboard view boundaries not found - dartboard size NOT changed")
                warnings.append("dart-small")
            else:
                dview = src[v_start:v_end + len("</View>")]
                new_dview = dview
                if dview.count("centerSceneW - 140") == 1:
                    new_dview = new_dview.replace("centerSceneW - 140", "centerSceneW - 70", 1)
                if dview.count("centerSceneH - 93") == 1:
                    new_dview = new_dview.replace("centerSceneH - 93", "centerSceneH - 47", 1)
                if dview.count("width: 280, height: 187") == 2:
                    new_dview = new_dview.replace("width: 280, height: 187", "width: 140, height: 94")
                if new_dview != dview and "width: 140, height: 94" in new_dview:
                    src = src[:v_start] + new_dview + src[v_end + len("</View>"):]
                    changed = True
                    print("ACTIVITY_CENTER_CARDTABLE_DART_SMALL_OK (280x187 -> 140x94)")
                    landed.append("dart-small")
                else:
                    print("WARNING: dartboard size pattern not matched - dartboard size NOT changed")
                    warnings.append("dart-small")

    # ---- Piece 11: hint now names all three fixtures (best effort). ----
    if HINT_3 in src:
        print("ACTIVITY_CENTER_CARDTABLE_HINT_ALREADY_APPLIED")
        landed.append("hint")
    elif src.count(HINT_2) == 1:
        src = src.replace(HINT_2, HINT_3, 1)
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_HINT_OK")
        landed.append("hint")
    elif src.count(HINT_1) == 1:
        src = src.replace(HINT_1, HINT_3, 1)
        changed = True
        print("ACTIVITY_CENTER_CARDTABLE_HINT_OK (from pool-only hint)")
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
        print("ACTIVITY_CENTER_CARDTABLE_PARTIAL: nothing landed")
        return 1
    if not changed:
        print("ACTIVITY_CENTER_CARDTABLE_ALREADY_APPLIED")
        return 0
    IDX.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_CARDTABLE_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
