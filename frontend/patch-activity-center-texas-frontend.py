#!/usr/bin/env python3
"""Street Legends frontend: Activity Center Texas Hold'em table —
same v2 treatment as the pool table, dartboard, card table, dominoes,
Scrabble, and chess (real picture in the scrolling room, tap = Texas
Hold'em menu, hold-drag arrange Veno-only), PLUS the chess and
checkers table shrinks to 140x94.

User request (2026-11-06 17:44 EST): "Do the same thing for Texas
holdem table and make the chess and checkers table smaller" — two
parts: (1) the Texas Hold'em table gets the pool/dart/card/dominoes/
Scrabble/chess treatment; (2) the chess and checkers table picture
gets SMALLER (it renders 180x120 — it should be 140x94, the same
size as the dartboard).

What this does (frontend; the backend patch extends the layout clamp):
  1. REAL TEXAS HOLD'EM PICTURE IN THE SAME SCENE: the Texas table
     renders as its ACTUAL picture — the house's exact image source,
     resolved at patch time from the HOUSE_ITEMS texas_holdem entry's
     image (require, already .png — the entry is { id:
     'texas_holdem', name: "Texas Hold'em Table", image:
     require('../../assets/houses/items/texas-holdem.png'), price:
     20000 }, written by the house Texas Hold'em frontend patch; the
     user sold his Texas table, but the HOUSE_ITEMS entry and its
     asset exist, so the picture is proven, not assumed — same
     fallback chain as v2). 180x120, resizeMode "contain", the same
     size as the other board-game tables (card, dominoes, Scrabble);
     the pool table alone stays 280x187. Placed in the SAME
     horizontal ScrollView scene as the other six fixtures, at its
     own stored fractional position. Default {x:0.15, y:0.175} —
     top-left corner of the wide scene, above the dominoes table
     {0.15, 0.5} (180x120, top edge ~0.35 vs the Texas bottom edge
     ~0.325 at a 400px scene height: 10px clear) and clear of the
     dartboard {0.5, 0.28} (140x94, left edge ~0.383 vs the Texas
     right edge ~0.30: 50px clear); farthest from the card table
     {0.85, 0.5} and the chess table {0.85, 0.85}; the pool table
     {0.5, 0.72} is 64px below the Texas bottom edge. No menu card,
     no "TAP TO PLAY" text, nothing in any shop/item catalog or house
     dropdown.
  2. CHESS AND CHECKERS TABLE SMALLER: the chess picture goes from
     180x120 to 140x94 — the same size as the dartboard, the
     smallest fixture. Its position, tap, and hold-drag are otherwise
     untouched.
  3. TAP = TEXAS HOLD'EM PLAY MENU: tapping the Texas picture opens
     the SAME TexasHoldemTableMenuModal the house uses (PLAY VS
     COMPUTER -> TexasHoldemGameModal PvC; PLAYER VS PLAYER ->
     TexasHoldemPvpModal room screen with create/join, REJOIN,
     auto-start, no chat; wager UI and play-chip stacks inside it
     untouched). MOVE/SELL hidden on the center path only via a new
     optional hideManage prop on TexasHoldemTableMenuModal (same
     pattern as the pool/darts/card/dominoes/Scrabble/chess menus);
     if the prop cannot land, onMove/onSell are inert (close only) —
     nothing can ever be moved or sold from a center. The center
     menu inherits the house menu's PvP behavior verbatim — including
     the Texas identity re-apply (the pvp-all patch SKIPPED a baked
     Texas identity; fixing Texas identity is a SEPARATE item, not
     attempted here). If the house Texas PvP is not fully wired in
     this build, the center menu matches the house menu without the
     PvP button (NOTE printed).
  4. HOLD-DRAG = ARRANGE (Veno only): same interaction as the other
     six fixtures — press-and-HOLD (250ms), then drag (gold border
     while dragging, scene scroll disabled while dragging); tap
     (<12px) opens the menu instead. The hint renders only for
     Mayor Veno; for anyone else all seven fixtures are fixed and
     hold does nothing (tap still opens the menus).
  5. MERGED LAYOUT SAVE (critical): the chess merged save is
     replaced by ONE shared save that always sends the FULL layout
     {pool_table, dart_board, card_table, dominoes, scrabble,
     chess_checkers, texas_holdem} (all seven positions, converted
     at the boundary to the backend's integer box). Saving any one
     fixture never wipes the others' spots. A 403 snaps ALL SEVEN
     fixtures back with "Only Mayor Veno can arrange this center."
     The modal loads all seven stored positions on open.
  6. PanResponder import: if the import-fix / dartboard / cardtable /
     dominoes / Scrabble / chess patch already landed it,
     ALREADY_APPLIED; otherwise this patch adds it itself (same
     brace-insert strategy, never anchoring on the last member).

UNCHANGED: pool table (picture, menu, hold-drag, position),
dartboard (picture, menu, hold-drag, position), card table
(picture, menu, hold-drag, position), dominoes table (picture, menu,
hold-drag, position), Scrabble table (picture, menu, hold-drag,
position), chess and checkers table (picture except the size, menu,
hold-drag, position), "Inside now" list, LEAVE, presence, the
Texas Hold'em menu contents, house Texas Hold'em + house rules, the
layout endpoint + its permission. The Texas Hold'em ROOM endpoints
need no change: POST /api/texas_holdem/rooms/create takes only
{player_id, player_name} and /join only {code, player_id,
player_name} — no house lookup, no ownership check (same as
pool/darts/cards/dominoes/Scrabble/chess) — so center PvP works
with no room change.

Run from /app: python3 frontend/patch-activity-center-texas-frontend.py
Frontend / Expo Go only. Run AFTER the chess frontend patch is
live (the merged save needs the chess pieces first) and after the
Texas backend patch is Published (the merged save needs the
seven-key clamp live first).
Idempotent: a full re-run prints ACTIVITY_CENTER_TEXAS_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"
MARKER = "ACTIVITY_CENTER_TEXAS_OK"
VENO_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"

CHESS_STATE_ANCHOR = "  const [centerChessDrag, setCenterChessDrag] = useState(false);"
PRESENCE_EFFECT_CLOSE = "  }, [activeCenter?.id, playerId]);"
# Merged save after the chess patch (six fixtures); extended to seven.
SAVE_6 = "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current), dominoes: centerPosToStored(centerDomPosRef.current), scrabble: centerPosToStored(centerScrPosRef.current), chess_checkers: centerPosToStored(centerChessPosRef.current) });"
SAVE_7 = "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current), dominoes: centerPosToStored(centerDomPosRef.current), scrabble: centerPosToStored(centerScrPosRef.current), chess_checkers: centerPosToStored(centerChessPosRef.current), texas_holdem: centerPosToStored(centerTexasPosRef.current) });"
BACK_6 = """        const back = storedToCenterPos((activeCenter as any)?.layout?.pool_table);
        const backDart = storedToCenterDartPos((activeCenter as any)?.layout?.dart_board);
        centerPoolPosRef.current = back;
        setCenterPoolPos(back);
        centerDartPosRef.current = backDart;
        setCenterDartPos(backDart);
        const backCard = storedToCenterCardPos((activeCenter as any)?.layout?.card_table);
        centerCardPosRef.current = backCard;
        setCenterCardPos(backCard);
        const backDom = storedToCenterDomPos((activeCenter as any)?.layout?.dominoes);
        centerDomPosRef.current = backDom;
        setCenterDomPos(backDom);
        const backScr = storedToCenterScrPos((activeCenter as any)?.layout?.scrabble);
        centerScrPosRef.current = backScr;
        setCenterScrPos(backScr);
        const backChess = storedToCenterChessPos((activeCenter as any)?.layout?.chess_checkers);
        centerChessPosRef.current = backChess;
        setCenterChessPos(backChess);"""
RESPONDER_TAIL = """        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""
CHESS_LOAD_BLOCK = """    const posChess = storedToCenterChessPos((activeCenter as any)?.layout?.chess_checkers);
    centerChessPosRef.current = posChess;
    setCenterChessPos(posChess);
    setCenterChessDrag(false);"""
HINT_6 = "Hold the pool table, dartboard, card table, dominoes table, Scrabble table, or chess and checkers table to move it — swipe the room to look around."
HINT_5 = "Hold the pool table, dartboard, card table, dominoes table, or Scrabble table to move it — swipe the room to look around."
HINT_4 = "Hold the pool table, dartboard, card table, or dominoes table to move it — swipe the room to look around."
HINT_3 = "Hold the pool table, dartboard, or card table to move it — swipe the room to look around."
HINT_2 = "Hold the pool table or dartboard to move it — swipe the room to look around."
HINT_1 = "Hold the pool table to move it — swipe the room to look around."
HINT_7 = "Hold the pool table, dartboard, card table, dominoes table, Scrabble table, chess and checkers table, or Texas Hold'em table to move it — swipe the room to look around."
TH_PNG_REQUIRE = "require('../../assets/houses/items/texas-holdem.png')"
TH_JPG_REQUIRE = "require('../../assets/houses/items/texas-holdem.jpg')"

# PanResponder import (same strategy as the import-fix / dartboard /
# cardtable / dominoes / Scrabble / chess patches; the brace regex is
# [^}]* so it can never span across an earlier import's closing brace
# to reach the react-native one).
RN_BRACE_RE = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]react-native['\"]\s*;?")
RN_ANY_RE = re.compile(r"import[^\n]*from\s*['\"]react-native['\"]\s*;?")
TOP_IMPORT_RE = re.compile(r"^import[^\n]*;\s*$", re.M)

TEXAS_STATE_BLOCK = """
  // ACTIVITY_CENTER_TEXAS: hold-drag arrange (Veno only), tap = Texas Hold'em menu.
  // Default {x:0.15, y:0.175} — top-left corner of the wide scene, above the
  // dominoes table {0.15, 0.5} (180x120, top edge ~0.35 vs the Texas bottom
  // edge ~0.325 at a 400px scene height: 10px clear) and clear of the
  // dartboard {0.5, 0.28} (140x94, left edge ~0.383 vs the Texas right edge
  // ~0.30: 50px clear); farthest from the card table {0.85, 0.5} and the
  // chess table {0.85, 0.85}; the pool table {0.5, 0.72} sits 64px below
  // the Texas bottom edge. Shares the v2 hold/drag refs and the MERGED
  // save (one call sends all seven fixtures' positions). Size 180x120
  // like the other board-game tables; the pool table alone stays 280x187.
  const [centerTexasPos, setCenterTexasPos] = useState({ x: 0.15, y: 0.175 });
  const [centerTexasDrag, setCenterTexasDrag] = useState(false);
  const centerTexasPosRef = useRef({ x: 0.15, y: 0.175 });
  const centerTexasResponder = useRef<any>(null);
  const storedToCenterTexasPos = (l: any) => {
    if (!l || typeof l.x !== 'number' || typeof l.y !== 'number') return { x: 0.15, y: 0.175 };
    return storedToCenterPos(l);
  };"""

TEXAS_RESPONDER_BLOCK = """
  if (!centerTexasResponder.current) {
    centerTexasResponder.current = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        setCenterSceneScrollEnabled(false);
        centerHoldStartRef.current = Date.now();
        centerDragStartRef.current = { ...(centerTexasPosRef.current || { x: 0.15, y: 0.175 }) };
        centerDragMovedRef.current = false;
      },
      onPanResponderMove: (evt: any, gesture: any) => {
        if (centerCtxRef.current.playerId !== CENTER_ARRANGE_OWNER_ID) return;
        if (Date.now() - centerHoldStartRef.current < 250) return;
        const s = centerDragStartRef.current || { x: 0.15, y: 0.175 };
        const nx = Math.min(0.94, Math.max(0.06, s.x + gesture.dx / centerSceneWRef.current));
        const ny = Math.min(0.94, Math.max(0.06, s.y + gesture.dy / centerSceneHRef.current));
        centerDragMovedRef.current = true;
        centerTexasPosRef.current = { x: nx, y: ny };
        setCenterTexasPos({ x: nx, y: ny });
        setCenterTexasDrag(true);
        setCenterLayoutDirty(true);
      },
      onPanResponderRelease: (evt: any, gesture: any) => {
        setCenterSceneScrollEnabled(true);
        setCenterTexasDrag(false);
        const tapDist = Math.hypot(gesture.dx || 0, gesture.dy || 0);
        if (tapDist < 12) { setTexasMenuCenterOpen(true); return; }
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
      onPanResponderTerminate: () => {
        setCenterSceneScrollEnabled(true);
        setCenterTexasDrag(false);
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""

TEXAS_LOAD_LINES = """    const posTexas = storedToCenterTexasPos((activeCenter as any)?.layout?.texas_holdem);
    centerTexasPosRef.current = posTexas;
    setCenterTexasPos(posTexas);
    setCenterTexasDrag(false);"""

TEXAS_LOAD_EFFECT = """
  // ACTIVITY_CENTER_TEXAS: load this center's stored Texas spot when it opens.
  useEffect(() => {
    const posTexas = storedToCenterTexasPos((activeCenter as any)?.layout?.texas_holdem);
    centerTexasPosRef.current = posTexas;
    setCenterTexasPos(posTexas);
    setCenterTexasDrag(false);
  }, [activeCenter?.id]);"""

# __TH_ART_REQUIRE__ is replaced with the resolved house image require.
TEXAS_VIEW = """
              <View
                {...(centerTexasResponder.current ? centerTexasResponder.current.panHandlers : {})}
                style={{ position: 'absolute', left: centerTexasPos.x * centerSceneW - 90, top: centerTexasPos.y * centerSceneH - 60, width: 180, height: 120, borderWidth: centerTexasDrag ? 3 : 0, borderColor: '#ffd54f', borderRadius: 8 }}
              >
                <Image source={__TH_ART_REQUIRE__} style={{ width: 180, height: 120, borderRadius: 8 }} resizeMode="contain" />
              </View>"""


def _balance(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def _resolve_texas_art(src, root):
    """House Texas Hold'em table picture source, in fallback order.
    Returns (require_expression, source_name). Never a menu card /
    emoji tile. The HOUSE_ITEMS entry exists (written by the house
    Texas Hold'em frontend patch) even though the user sold his Texas
    table — the entry + asset are the proof."""
    m = re.search(r"id:\s*'texas_holdem'[^}]*?image:\s*(require\([^)]+\))", src)
    if m:
        return m.group(1), "house-items-entry"
    m = re.search(r"require\(['\"][^'\"]*texas-holdem\.png['\"]\)", src)
    if m:
        return m.group(0), "png-require-in-index"
    m = re.search(r"require\(['\"][^'\"]*texas-holdem\.jpg['\"]\)", src)
    if m:
        return m.group(0), "jpg-require-in-index"
    if (root / "frontend/assets/houses/items/texas-holdem.png").exists():
        return TH_PNG_REQUIRE, "asset-file-png"
    if (root / "frontend/assets/houses/items/texas-holdem.jpg").exists():
        return TH_JPG_REQUIRE, "asset-file-jpg"
    return TH_PNG_REQUIRE, "canonical-path"


def _texas_menu_span(src):
    """(start, end) of the TexasHoldemTableMenuModal component, or None."""
    start = src.find("const TexasHoldemTableMenuModal = ({")
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
        print("WARNING: index.tsx not found - center Texas table NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore") if API.exists() else ""
    orig = _balance(src)
    landed = []
    warnings = []
    changed = False

    # ---- Idempotency: Texas table already landed. ----
    if "ACTIVITY_CENTER_TEXAS" in src and "centerTexasPos" in src:
        print("ACTIVITY_CENTER_TEXAS_ALREADY_APPLIED")
        return 0

    # ---- Preconditions: the v2 room + chess table + the house Texas menu. ----
    if "centerSceneScrollEnabled" not in src or "ACTIVITY_CENTER_POOL_V2" not in src:
        print("WARNING: v2 center room not found - run the pool-table v2 patch first, Texas table NOT added")
        return 1
    if "centerChessPos" not in src or "ACTIVITY_CENTER_CHESS" not in src:
        print("WARNING: chess table not found - run the chess frontend patch first, Texas table NOT added")
        return 1
    if "TexasHoldemTableMenuModal visible={texasHoldemMenuOpen}" not in src:
        print("WARNING: house Texas Hold'em table menu not found - Texas table NOT added")
        return 1
    if "saveCenterLayout" not in src:
        print("WARNING: v2 layout save not found - run the pool-table v2 patch first, Texas table NOT added")
        return 1

    # ---- Piece 0: resolve the house's live Texas picture (proof line). ----
    art, art_source = _resolve_texas_art(src, ROOT)
    print("TEXAS_V2_ART=%s via %s" % (art, art_source))
    if art_source == "canonical-path":
        print("NOTE: Texas art require not found in index.tsx and no asset file on disk - using the canonical path (texas-holdem.png written by the house Texas Hold'em frontend patch); if the bundle cannot resolve it, the table will not render")

    # ---- Piece 1: hideManage on TexasHoldemTableMenuModal (all-or-nothing). ----
    hide_ok = False
    span = _texas_menu_span(src)
    if span is None:
        print("WARNING: TexasHoldemTableMenuModal component not found - MOVE/SELL stay visible but inert on the center path")
        warnings.append("hidemanage")
    else:
        s0, s1 = span
        body = src[s0:s1]
        new_body = body
        edits = []

        m = re.search(r"const TexasHoldemTableMenuModal = \(\{\s*([^}]*?)\s*\}:", new_body)
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

        old_sub = ">Play Texas Hold'em, move it, or sell it.</Text>"
        if new_body.count(old_sub) == 1:
            new_body = new_body.replace(old_sub, ">{hideManage ? 'Play a game.' : 'Play Texas Hold\\'em, move it, or sell it.'}</Text>", 1)
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
            print("ACTIVITY_CENTER_TEXAS_HIDEMANAGE_ALREADY_APPLIED")
            hide_ok = True
            landed.append("hidemanage")
        elif not failed:
            src = src[:s0] + new_body + src[s1:]
            changed = True
            print("ACTIVITY_CENTER_TEXAS_HIDEMANAGE_OK")
            hide_ok = True
            landed.append("hidemanage")
        else:
            print("WARNING: TexasHoldemTableMenuModal hideManage edit failed (%s) - MOVE/SELL stay visible but inert on the center path" % ",".join(failed))
            warnings.append("hidemanage")

    # ---- Piece 2: PanResponder import (own piece; earlier patches may have landed it). ----
    if _panresponder_imported(src):
        print("ACTIVITY_CENTER_TEXAS_PANRESPONDER_ALREADY_APPLIED")
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
            print("WARNING: PanResponder import could not be added - Texas hold-drag NOT added (would not compile)")
            return 1
        src = new
        changed = True
        print("ACTIVITY_CENTER_TEXAS_PANRESPONDER_OK (%s)" % strategy)
        landed.append("panresponder")

    # ---- Piece 3: Texas state (positions, refs, Texas loader). ----
    if "ACTIVITY_CENTER_TEXAS: hold-drag arrange" in src:
        print("ACTIVITY_CENTER_TEXAS_STATE_ALREADY_APPLIED")
        landed.append("state")
    elif src.count(CHESS_STATE_ANCHOR) == 1:
        src = src.replace(CHESS_STATE_ANCHOR, CHESS_STATE_ANCHOR + TEXAS_STATE_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_STATE_OK")
        landed.append("state")
    else:
        print("WARNING: chess state anchor matched %dx - Texas state NOT added" % src.count(CHESS_STATE_ANCHOR))
        return 1

    # ---- Piece 4: MERGED save — one call sends ALL SEVEN fixtures (hard gate). ----
    if "{ pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current), card_table: centerPosToStored(centerCardPosRef.current), dominoes: centerPosToStored(centerDomPosRef.current), scrabble: centerPosToStored(centerScrPosRef.current), chess_checkers: centerPosToStored(centerChessPosRef.current), texas_holdem: centerPosToStored(centerTexasPosRef.current) }" in src:
        print("ACTIVITY_CENTER_TEXAS_SAVE_ALREADY_APPLIED")
        landed.append("save")
    elif src.count(SAVE_6) == 1 and src.count(BACK_6) == 1:
        src = src.replace(SAVE_6, SAVE_7, 1)
        src = src.replace(
            BACK_6,
            BACK_6 + "\n" + """        const backTexas = storedToCenterTexasPos((activeCenter as any)?.layout?.texas_holdem);
        centerTexasPosRef.current = backTexas;
        setCenterTexasPos(backTexas);""",
            1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_SAVE_OK (merged: pool + dart + card + dominoes + scrabble + chess + Texas in one call)")
        landed.append("save")
    else:
        print("WARNING: merged save lines not matched (save=%dx 403-back=%dx) - merged save NOT wired; Texas table NOT added (a Texas save would drop the pool/dart/card/dominoes/Scrabble/chess spots)" % (src.count(SAVE_6), src.count(BACK_6)))
        return 1

    # ---- Piece 5: Texas responder (hold-drag), after the LAST responder (the chess one). ----
    if "centerTexasResponder.current = PanResponder.create" in src:
        print("ACTIVITY_CENTER_TEXAS_RESPONDER_ALREADY_APPLIED")
        landed.append("responder")
    else:
        tail_idx = src.rfind(RESPONDER_TAIL)
        if tail_idx == -1:
            print("WARNING: responder tail not found - Texas responder NOT added")
            return 1
        tail_end = tail_idx + len(RESPONDER_TAIL)
        src = src[:tail_end] + TEXAS_RESPONDER_BLOCK + src[tail_end:]
        changed = True
        print("ACTIVITY_CENTER_TEXAS_RESPONDER_OK")
        landed.append("responder")

    # ---- Piece 6: load the stored Texas spot when a center opens. ----
    # NOTE: check for the LOAD line (const posTexas), not the bare
    # storedToCenterTexasPos(...) call — the 403-back in piece 4 already
    # contains that call, so a bare check would false-positive here.
    if "const posTexas = storedToCenterTexasPos" in src:
        print("ACTIVITY_CENTER_TEXAS_LOAD_ALREADY_APPLIED")
        landed.append("load")
    elif src.count(CHESS_LOAD_BLOCK) == 1:
        src = src.replace(CHESS_LOAD_BLOCK, CHESS_LOAD_BLOCK + "\n" + TEXAS_LOAD_LINES, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_LOAD_OK (chess load extended)")
        landed.append("load")
    elif src.count(PRESENCE_EFFECT_CLOSE) == 1:
        src = src.replace(PRESENCE_EFFECT_CLOSE, PRESENCE_EFFECT_CLOSE + TEXAS_LOAD_EFFECT, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_LOAD_OK (standalone load effect)")
        landed.append("load")
    else:
        print("WARNING: load anchors matched 0x - stored Texas spot NOT loaded (table will sit at the default spot)")
        warnings.append("load")

    # ---- Piece 7: center menu open state. ----
    if "const [texasMenuCenterOpen, setTexasMenuCenterOpen]" in src:
        print("ACTIVITY_CENTER_TEXAS_MENU_STATE_ALREADY_APPLIED")
        landed.append("menu-state")
    else:
        chess_center_line = None
        for ln in src.split("\n"):
            if "chessMenuCenterOpen" in ln and "useState" in ln:
                chess_center_line = ln
                break
        if chess_center_line is not None:
            src = src.replace(chess_center_line, chess_center_line + "\n  const [texasMenuCenterOpen, setTexasMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_TEXAS_MENU_STATE_OK")
            landed.append("menu-state")
        elif src.count("const [poolMenuCenterOpen, setPoolMenuCenterOpen]") == 1:
            src = src.replace("const [poolMenuCenterOpen, setPoolMenuCenterOpen]",
                              "const [poolMenuCenterOpen, setPoolMenuCenterOpen]\n  const [texasMenuCenterOpen, setTexasMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_TEXAS_MENU_STATE_OK (fallback anchor)")
            landed.append("menu-state")
        else:
            print("WARNING: Texas menu state anchor not found - center menu state NOT added")
            return 1

    # ---- Piece 8: center render of the SAME TexasHoldemTableMenuModal. ----
    # PvP inclusion is decided ONLY from the Texas pieces themselves
    # (the pool/darts/card/dominoes/Scrabble/chess menus already have
    # onPlayPvp — a global check would lie). The center menu inherits
    # the house menu's PvP behavior verbatim, including the Texas
    # identity re-apply (fixing Texas identity is a SEPARATE item).
    house_render_line = None
    for ln in src.split("\n"):
        if "TexasHoldemTableMenuModal visible={texasHoldemMenuOpen}" in ln:
            house_render_line = ln
            break
    has_pvp_render = house_render_line is not None and "onPlayPvp" in house_render_line
    has_pvp_state = "const [texasHoldemPvpOpen, setTexasHoldemPvpOpen]" in src
    has_pvp_modal = "TexasHoldemPvpModal visible={texasHoldemPvpOpen}" in src
    pvp_ok = has_pvp_render and has_pvp_state and has_pvp_modal
    if not pvp_ok:
        print("NOTE: Texas Hold'em PvP room screen not fully wired in this build (render=%s state=%s modal=%s) - center menu matches the house menu without the PvP button" % (has_pvp_render, has_pvp_state, has_pvp_modal))

    if "TexasHoldemTableMenuModal visible={texasMenuCenterOpen}" in src:
        print("ACTIVITY_CENTER_TEXAS_RENDER_ALREADY_APPLIED")
        landed.append("render")
    else:
        menu_lines = src.split("\n")
        house_idx = None
        for i, ln in enumerate(menu_lines):
            if "TexasHoldemTableMenuModal visible={texasHoldemMenuOpen}" in ln:
                house_idx = i
                break
        close_idx = None
        if house_idx is not None:
            for j in range(house_idx, min(len(menu_lines), house_idx + 6)):
                if menu_lines[j].strip() == ") : null}" or menu_lines[j].strip().endswith(") : null}"):
                    close_idx = j
                    break
        if house_idx is None or close_idx is None:
            print("WARNING: house Texas menu render close not found - center menu render NOT added")
            return 1
        pvp_prop = " onPlayPvp={() => { setTexasMenuCenterOpen(false); setTexasHoldemPvpOpen(true); }}" if pvp_ok else ""
        hide_prop = " hideManage" if hide_ok else ""
        render_block = (
            "      {texasMenuCenterOpen ? (<TexasHoldemTableMenuModal visible={texasMenuCenterOpen} onClose={() => setTexasMenuCenterOpen(false)}"
            " onPlay={() => { setTexasMenuCenterOpen(false); setTexasHoldemGameOpen(true); }}" + pvp_prop +
            " onMove={() => setTexasMenuCenterOpen(false)} onSell={() => setTexasMenuCenterOpen(false)}" + hide_prop + " />) : null}"
        )
        menu_lines = menu_lines[:close_idx + 1] + [render_block] + menu_lines[close_idx + 1:]
        src = "\n".join(menu_lines)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_RENDER_OK")
        landed.append("render")

    # ---- Piece 9: Texas picture in the scene, after the chess table. ----
    if "centerTexasResponder.current.panHandlers" in src:
        print("ACTIVITY_CENTER_TEXAS_PICTURE_ALREADY_APPLIED")
        landed.append("picture")
    else:
        ph = src.find("centerChessResponder.current.panHandlers")
        if ph == -1:
            print("WARNING: chess table picture not found in scene - Texas picture NOT added")
            return 1
        view_close = src.find("</View>", ph)
        if view_close == -1:
            print("WARNING: chess table view close not found - Texas picture NOT added")
            return 1
        view = TEXAS_VIEW.replace("__TH_ART_REQUIRE__", art)
        src = src[:view_close + len("</View>")] + view + src[view_close + len("</View>"):]
        changed = True
        print("ACTIVITY_CENTER_TEXAS_PICTURE_OK")
        landed.append("picture")

    # ---- Piece 10: chess and checkers table SMALLER — 180x120 -> 140x94 (offsets adjusted too). ----
    if "centerChessPos.x * centerSceneW - 70" in src and "width: 140, height: 94" in src:
        print("ACTIVITY_CENTER_TEXAS_CHESS_SMALL_ALREADY_APPLIED")
        landed.append("chess-small")
    else:
        ch = src.find("centerChessResponder.current.panHandlers")
        if ch == -1:
            print("WARNING: chess table picture not found - chess table size NOT changed")
            warnings.append("chess-small")
        else:
            v_start = src.rfind("<View", 0, ch)
            v_end = src.find("</View>", ch)
            if v_start == -1 or v_end == -1:
                print("WARNING: chess table view boundaries not found - chess table size NOT changed")
                warnings.append("chess-small")
            else:
                sview = src[v_start:v_end + len("</View>")]
                new_sview = sview
                if sview.count("centerSceneW - 90") == 1:
                    new_sview = new_sview.replace("centerSceneW - 90", "centerSceneW - 70", 1)
                if sview.count("centerSceneH - 60") == 1:
                    new_sview = new_sview.replace("centerSceneH - 60", "centerSceneH - 47", 1)
                if sview.count("width: 180, height: 120") == 2:
                    new_sview = new_sview.replace("width: 180, height: 120", "width: 140, height: 94")
                if new_sview != sview and "width: 140, height: 94" in new_sview:
                    src = src[:v_start] + new_sview + src[v_end + len("</View>"):]
                    changed = True
                    print("ACTIVITY_CENTER_TEXAS_CHESS_SMALL_OK (180x120 -> 140x94)")
                    landed.append("chess-small")
                else:
                    print("WARNING: chess table size pattern not matched - chess table size NOT changed")
                    warnings.append("chess-small")

    # ---- Piece 11: hint now names all seven fixtures (best effort). ----
    if HINT_7 in src:
        print("ACTIVITY_CENTER_TEXAS_HINT_ALREADY_APPLIED")
        landed.append("hint")
    elif src.count(HINT_6) == 1:
        src = src.replace(HINT_6, HINT_7, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_HINT_OK")
        landed.append("hint")
    elif src.count(HINT_5) == 1:
        src = src.replace(HINT_5, HINT_7, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_HINT_OK (from five-fixture hint)")
        landed.append("hint")
    elif src.count(HINT_4) == 1:
        src = src.replace(HINT_4, HINT_7, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_HINT_OK (from four-fixture hint)")
        landed.append("hint")
    elif src.count(HINT_3) == 1:
        src = src.replace(HINT_3, HINT_7, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_HINT_OK (from three-fixture hint)")
        landed.append("hint")
    elif src.count(HINT_2) == 1:
        src = src.replace(HINT_2, HINT_7, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_HINT_OK (from two-fixture hint)")
        landed.append("hint")
    elif src.count(HINT_1) == 1:
        src = src.replace(HINT_1, HINT_7, 1)
        changed = True
        print("ACTIVITY_CENTER_TEXAS_HINT_OK (from pool-only hint)")
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
        print("ACTIVITY_CENTER_TEXAS_PARTIAL: nothing landed")
        return 1
    if not changed:
        print("ACTIVITY_CENTER_TEXAS_ALREADY_APPLIED")
        return 0
    IDX.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_TEXAS_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
