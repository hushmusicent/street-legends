#!/usr/bin/env python3
"""Street Legends frontend: Activity Center dartboard — same treatment
as the pool table v2 (real picture in the scrolling room, tap = darts
menu, hold-drag arrange Veno-only), plus a merged layout save so
neither fixture's position ever wipes the other's.

User request (2026-11-06 11:23 EST): "Do the same with the dart board"
— the same treatment the pool table just got (v2: scrolling room, real
picture, tap for PvC/PvP menu, hold-drag to arrange, Veno only).
NOTE: the user SOLD his house dartboard (2026-11-03) — that does not
matter: the center dartboard is a fixture placed by the center, not
owned, exactly like the center pool table (no ownership gate on the
center card). The dartboard art asset still exists (written by the
house dartboard patch as frontend/assets/houses/items/dartboard.png).

What this does (frontend; the backend patch extends the layout clamp):
  1. REAL DARTBOARD PICTURE IN THE SAME SCENE: the dartboard renders
     as its ACTUAL picture — the house's exact image source, resolved
     at patch time from the HOUSE_ITEMS dartboard entry's image
     (require, already .png — no .jpg/.png swap to trip over, but the
     same fallback chain as v2). 280x187, resizeMode "contain",
     exactly like the house room render. Placed in the SAME horizontal
     ScrollView scene as the pool table, at its own stored fractional
     position. Default {x:0.5, y:0.28} — upper-middle of the scene,
     clear of the pool table's default {0.5, 0.72}. No menu card, no
     "TAP TO PLAY" text, nothing in any shop/item catalog or house
     dropdown.
  2. TAP = DARTS PLAY MENU: tapping the dartboard picture opens the
     SAME DartboardMenuModal the house uses (PLAY VS COMPUTER ->
     DartGameModal 301 PvC; PLAYER VS PLAYER -> DartPvpModal room
     screen with create/join, REJOIN, auto-start, no chat; wager UI
     inside it untouched). MOVE/SELL hidden on the center path only
     via a new optional hideManage prop on DartboardMenuModal (same
     pattern as the pool menu); if the prop cannot land, onMove/onSell
     are inert (close only) — nothing can ever be moved or sold from
     a center. If the house darts PvP is not fully wired in this
     build, the center menu matches the house menu without the PvP
     button (NOTE printed).
  3. HOLD-DRAG = ARRANGE (Veno only): same interaction as the v2 pool
     table — press-and-HOLD (250ms), then drag (gold border while
     dragging, scene scroll disabled while dragging); tap (<12px)
     opens the menu instead. The hint renders only for Mayor Veno;
     for anyone else the board is fixed and hold does nothing (tap
     still opens the menu).
  4. MERGED LAYOUT SAVE (critical): the v2 pool save is replaced by
     ONE shared save that always sends the FULL layout
     {pool_table, dart_board} (both positions, converted at the
     boundary to the backend's integer box). Saving the dartboard
     never wipes the pool table's spot and vice versa. A 403 snaps
     BOTH fixtures back with "Only Mayor Veno can arrange this
     center." The modal loads both stored positions on open.
  5. PanResponder import: if the import-fix patch already landed it,
     ALREADY_APPLIED; otherwise this patch adds it itself (same
     brace-insert strategy as the import-fix patch, never anchoring
     on the last member).

UNCHANGED: pool table (picture, menu, hold-drag, position), "Inside
now" list, LEAVE, presence, the darts menu contents, house dartboard
+ house rules, the layout endpoint + its permission. Backend patch
ONLY extends the layout clamp (the darts room create/join take only
player ids — no house/ownership check — so no room change is needed).

Run from /app: python3 frontend/patch-activity-center-dartboard-frontend.py
Frontend / Expo Go only. Run AFTER the dartboard backend patch is
Published (the merged save needs the extended clamp live first).
Idempotent: a full re-run prints ACTIVITY_CENTER_DARTBOARD_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"
MARKER = "ACTIVITY_CENTER_DARTBOARD_OK"
VENO_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"

POOL_STATE_ANCHOR = "  const [centerPoolDrag, setCenterPoolDrag] = useState(false);"
POOL_SAVE_LINE = "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current) });"
POOL_403_BACK = """        const back = storedToCenterPos((activeCenter as any)?.layout?.pool_table);
        centerPoolPosRef.current = back;
        setCenterPoolPos(back);"""
POOL_RESPONDER_TAIL = """        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""
LOAD_ANCHOR = """    setCenterPoolDrag(false);
  }, [activeCenter?.id]);"""
PRESENCE_EFFECT_CLOSE = "  }, [activeCenter?.id, playerId]);"
POOL_HINT = "Hold the pool table to move it — swipe the room to look around."
DART_PNG_REQUIRE = "require('../../assets/houses/items/dartboard.png')"
DART_JPG_REQUIRE = "require('../../assets/houses/items/dartboard.jpg')"

# PanResponder import (same strategy as the import-fix patch; the brace
# regex is [^}]* so it can never span across an earlier import's brace).
RN_BRACE_RE = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]react-native['\"]\s*;?")
RN_ANY_RE = re.compile(r"import[^\n]*from\s*['\"]react-native['\"]\s*;?")
TOP_IMPORT_RE = re.compile(r"^import[^\n]*;\s*$", re.M)

DART_STATE_BLOCK = """
  // ACTIVITY_CENTER_DARTBOARD: hold-drag arrange (Veno only), tap = darts menu.
  // Default {x:0.5, y:0.28} — upper-middle of the scene, clear of the pool
  // table's default {0.5, 0.72}. Shares the v2 hold/drag refs and the
  // MERGED save (one call sends both fixtures' positions).
  const [centerDartPos, setCenterDartPos] = useState({ x: 0.5, y: 0.28 });
  const [centerDartDrag, setCenterDartDrag] = useState(false);
  const centerDartPosRef = useRef({ x: 0.5, y: 0.28 });
  const centerDartResponder = useRef<any>(null);
  const storedToCenterDartPos = (l: any) => {
    if (!l || typeof l.x !== 'number' || typeof l.y !== 'number') return { x: 0.5, y: 0.28 };
    return storedToCenterPos(l);
  };"""

DART_RESPONDER_BLOCK = """
  if (!centerDartResponder.current) {
    centerDartResponder.current = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        setCenterSceneScrollEnabled(false);
        centerHoldStartRef.current = Date.now();
        centerDragStartRef.current = { ...(centerDartPosRef.current || { x: 0.5, y: 0.28 }) };
        centerDragMovedRef.current = false;
      },
      onPanResponderMove: (evt: any, gesture: any) => {
        if (centerCtxRef.current.playerId !== CENTER_ARRANGE_OWNER_ID) return;
        if (Date.now() - centerHoldStartRef.current < 250) return;
        const s = centerDragStartRef.current || { x: 0.5, y: 0.28 };
        const nx = Math.min(0.94, Math.max(0.06, s.x + gesture.dx / centerSceneWRef.current));
        const ny = Math.min(0.94, Math.max(0.06, s.y + gesture.dy / centerSceneHRef.current));
        centerDragMovedRef.current = true;
        centerDartPosRef.current = { x: nx, y: ny };
        setCenterDartPos({ x: nx, y: ny });
        setCenterDartDrag(true);
        setCenterLayoutDirty(true);
      },
      onPanResponderRelease: (evt: any, gesture: any) => {
        setCenterSceneScrollEnabled(true);
        setCenterDartDrag(false);
        const tapDist = Math.hypot(gesture.dx || 0, gesture.dy || 0);
        if (tapDist < 12) { setDartMenuCenterOpen(true); return; }
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
      onPanResponderTerminate: () => {
        setCenterSceneScrollEnabled(true);
        setCenterDartDrag(false);
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""

DART_LOAD_LINES = """    const posDart = storedToCenterDartPos((activeCenter as any)?.layout?.dart_board);
    centerDartPosRef.current = posDart;
    setCenterDartPos(posDart);
    setCenterDartDrag(false);"""

DART_LOAD_EFFECT = """
  // ACTIVITY_CENTER_DARTBOARD: load this center's stored dartboard spot when it opens.
  useEffect(() => {
    const posDart = storedToCenterDartPos((activeCenter as any)?.layout?.dart_board);
    centerDartPosRef.current = posDart;
    setCenterDartPos(posDart);
    setCenterDartDrag(false);
  }, [activeCenter?.id]);"""

# __DART_ART_REQUIRE__ is replaced with the resolved house image require.
DART_VIEW = """
              <View
                {...(centerDartResponder.current ? centerDartResponder.current.panHandlers : {})}
                style={{ position: 'absolute', left: centerDartPos.x * centerSceneW - 140, top: centerDartPos.y * centerSceneH - 93, width: 280, height: 187, borderWidth: centerDartDrag ? 3 : 0, borderColor: '#ffd54f', borderRadius: 8 }}
              >
                <Image source={__DART_ART_REQUIRE__} style={{ width: 280, height: 187, borderRadius: 8 }} resizeMode="contain" />
              </View>"""


def _balance(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def _resolve_dart_art(src, root):
    """House dartboard picture source, in fallback order. Returns
    (require_expression, source_name). Never a menu card / emoji tile."""
    m = re.search(r"id:\s*'dartboard'[^}]*?image:\s*(require\([^)]+\))", src)
    if m:
        return m.group(1), "house-items-entry"
    m = re.search(r"require\(['\"][^'\"]*dartboard\.png['\"]\)", src)
    if m:
        return m.group(0), "png-require-in-index"
    m = re.search(r"require\(['\"][^'\"]*dartboard\.jpg['\"]\)", src)
    if m:
        return m.group(0), "jpg-require-in-index"
    if (root / "frontend/assets/houses/items/dartboard.png").exists():
        return DART_PNG_REQUIRE, "asset-file-png"
    if (root / "frontend/assets/houses/items/dartboard.jpg").exists():
        return DART_JPG_REQUIRE, "asset-file-jpg"
    return DART_PNG_REQUIRE, "canonical-path"


def _dart_menu_span(src):
    """(start, end) of the DartboardMenuModal component, or None."""
    start = src.find("const DartboardMenuModal = ({")
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
        print("WARNING: index.tsx not found - center dartboard NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore") if API.exists() else ""
    orig = _balance(src)
    landed = []
    warnings = []
    changed = False

    # ---- Idempotency: dartboard already landed. ----
    if "ACTIVITY_CENTER_DARTBOARD" in src and "centerDartPos" in src:
        print("ACTIVITY_CENTER_DARTBOARD_ALREADY_APPLIED")
        return 0

    # ---- Preconditions: the v2 room + the house darts menu must exist. ----
    if "centerSceneScrollEnabled" not in src or "ACTIVITY_CENTER_POOL_V2" not in src:
        print("WARNING: v2 center room not found - run the pool-table v2 patch first, dartboard NOT added")
        return 1
    if "DartboardMenuModal visible={dartMenuOpen}" not in src:
        print("WARNING: house dartboard menu not found - dartboard NOT added")
        return 1
    if "saveCenterLayout" not in src:
        print("WARNING: v2 layout save not found - run the pool-table v2 patch first, dartboard NOT added")
        return 1

    # ---- Piece 0: resolve the house's live dartboard picture (proof line). ----
    art, art_source = _resolve_dart_art(src, ROOT)
    print("DART_V2_ART=%s via %s" % (art, art_source))
    if art_source == "canonical-path":
        print("NOTE: dartboard art require not found in index.tsx and no asset file on disk - using the canonical path (dartboard.png written by the house dartboard patch); if the bundle cannot resolve it, the board will not render")

    # ---- Piece 1: hideManage on DartboardMenuModal (all-or-nothing). ----
    hide_ok = False
    span = _dart_menu_span(src)
    if span is None:
        print("WARNING: DartboardMenuModal component not found - MOVE/SELL stay visible but inert on the center path")
        warnings.append("hidemanage")
    else:
        s0, s1 = span
        body = src[s0:s1]
        new_body = body
        edits = []

        m = re.search(r"const DartboardMenuModal = \(\{\s*([^}]*?)\s*\}:", new_body)
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

        old_sub = ">Play, move, or sell it.</Text>"
        if new_body.count(old_sub) == 1:
            new_body = new_body.replace(old_sub, ">{hideManage ? 'Play a game.' : 'Play, move, or sell it.'}</Text>", 1)
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

        hint_old = "        <Text style={{ color: '#999999', fontSize: 11, textAlign: 'center', marginBottom: 10 }}>Move: close this menu, then drag the board.</Text>"
        hint_new = (
            "        {!hideManage && (\n"
            "        <Text style={{ color: '#999999', fontSize: 11, textAlign: 'center', marginBottom: 10 }}>Move: close this menu, then drag the board.</Text>\n"
            "        )}"
        )
        if new_body.count(hint_old) == 1:
            new_body = new_body.replace(hint_old, hint_new, 1)
            edits.append(("hint", True))
        else:
            edits.append(("hint", False))

        sell_old = (
            "        <TouchableOpacity onPress={onSell} style={{ backgroundColor: '#b7950b', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>SELL ($5,000 back)</Text>\n"
            "        </TouchableOpacity>"
        )
        sell_new = (
            "        {!hideManage && (\n"
            "        <TouchableOpacity onPress={onSell} style={{ backgroundColor: '#b7950b', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>SELL ($5,000 back)</Text>\n"
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
            print("ACTIVITY_CENTER_DARTBOARD_HIDEMANAGE_ALREADY_APPLIED")
            hide_ok = True
            landed.append("hidemanage")
        elif not failed:
            src = src[:s0] + new_body + src[s1:]
            changed = True
            print("ACTIVITY_CENTER_DARTBOARD_HIDEMANAGE_OK")
            hide_ok = True
            landed.append("hidemanage")
        else:
            print("WARNING: DartboardMenuModal hideManage edit failed (%s) - MOVE/SELL stay visible but inert on the center path" % ",".join(failed))
            warnings.append("hidemanage")

    # ---- Piece 2: PanResponder import (own piece; import-fix may have landed it). ----
    if _panresponder_imported(src):
        print("ACTIVITY_CENTER_DARTBOARD_PANRESPONDER_ALREADY_APPLIED")
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
            print("WARNING: PanResponder import could not be added - dartboard hold-drag NOT added (would not compile)")
            return 1
        src = new
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_PANRESPONDER_OK (%s)" % strategy)
        landed.append("panresponder")

    # ---- Piece 3: dart state (positions, refs, dart loader). ----
    if "ACTIVITY_CENTER_DARTBOARD: hold-drag arrange" in src:
        print("ACTIVITY_CENTER_DARTBOARD_STATE_ALREADY_APPLIED")
        landed.append("state")
    elif src.count(POOL_STATE_ANCHOR) == 1:
        src = src.replace(POOL_STATE_ANCHOR, POOL_STATE_ANCHOR + DART_STATE_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_STATE_OK")
        landed.append("state")
    else:
        print("WARNING: pool state anchor matched %dx - dart state NOT added" % src.count(POOL_STATE_ANCHOR))
        return 1

    # ---- Piece 4: MERGED save — one call sends BOTH fixtures (hard gate). ----
    if "{ pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current) }" in src:
        print("ACTIVITY_CENTER_DARTBOARD_SAVE_ALREADY_APPLIED")
        landed.append("save")
    elif src.count(POOL_SAVE_LINE) == 1 and src.count(POOL_403_BACK) == 1:
        src = src.replace(
            POOL_SAVE_LINE,
            "      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current), dart_board: centerPosToStored(centerDartPosRef.current) });",
            1)
        src = src.replace(
            POOL_403_BACK,
            """        const back = storedToCenterPos((activeCenter as any)?.layout?.pool_table);
        const backDart = storedToCenterDartPos((activeCenter as any)?.layout?.dart_board);
        centerPoolPosRef.current = back;
        setCenterPoolPos(back);
        centerDartPosRef.current = backDart;
        setCenterDartPos(backDart);""",
            1)
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_SAVE_OK (merged: pool + dart in one call)")
        landed.append("save")
    else:
        print("WARNING: v2 save lines not matched (save=%dx 403-back=%dx) - merged save NOT wired; dartboard NOT added (a dart save would drop the pool table's spot)" % (src.count(POOL_SAVE_LINE), src.count(POOL_403_BACK)))
        return 1

    # ---- Piece 5: dart responder (hold-drag), after the pool responder. ----
    if "centerDartResponder.current = PanResponder.create" in src:
        print("ACTIVITY_CENTER_DARTBOARD_RESPONDER_ALREADY_APPLIED")
        landed.append("responder")
    elif src.count(POOL_RESPONDER_TAIL) == 1:
        src = src.replace(POOL_RESPONDER_TAIL, POOL_RESPONDER_TAIL + DART_RESPONDER_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_RESPONDER_OK")
        landed.append("responder")
    else:
        print("WARNING: pool responder tail matched %dx - dart responder NOT added" % src.count(POOL_RESPONDER_TAIL))
        return 1

    # ---- Piece 6: load the stored dartboard spot when a center opens. ----
    # NOTE: check for the LOAD line (const posDart), not the bare
    # storedToCenterDartPos(...) call — the 403-back in piece 4 already
    # contains that call, so a bare check would false-positive here.
    if "const posDart = storedToCenterDartPos" in src:
        print("ACTIVITY_CENTER_DARTBOARD_LOAD_ALREADY_APPLIED")
        landed.append("load")
    elif src.count(LOAD_ANCHOR) == 1:
        src = src.replace(LOAD_ANCHOR, "    setCenterPoolDrag(false);\n" + DART_LOAD_LINES + "\n  }, [activeCenter?.id]);", 1)
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_LOAD_OK (v2 load extended)")
        landed.append("load")
    elif src.count(PRESENCE_EFFECT_CLOSE) == 1:
        src = src.replace(PRESENCE_EFFECT_CLOSE, PRESENCE_EFFECT_CLOSE + DART_LOAD_EFFECT, 1)
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_LOAD_OK (standalone load effect)")
        landed.append("load")
    else:
        print("WARNING: load anchors matched 0x - stored dartboard spot NOT loaded (board will sit at the default spot)")
        warnings.append("load")

    # ---- Piece 7: center menu open state. ----
    if "const [dartMenuCenterOpen, setDartMenuCenterOpen]" in src:
        print("ACTIVITY_CENTER_DARTBOARD_MENU_STATE_ALREADY_APPLIED")
        landed.append("menu-state")
    else:
        dart_state_line = None
        for ln in src.split("\n"):
            if "dartMenuOpen" in ln and "useState" in ln:
                dart_state_line = ln
                break
        if dart_state_line is not None:
            src = src.replace(dart_state_line, dart_state_line + "\n  const [dartMenuCenterOpen, setDartMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_DARTBOARD_MENU_STATE_OK")
            landed.append("menu-state")
        elif src.count("const [poolMenuCenterOpen, setPoolMenuCenterOpen]") == 1:
            src = src.replace("const [poolMenuCenterOpen, setPoolMenuCenterOpen]",
                              "const [poolMenuCenterOpen, setPoolMenuCenterOpen]\n  const [dartMenuCenterOpen, setDartMenuCenterOpen] = useState(false);", 1)
            changed = True
            print("ACTIVITY_CENTER_DARTBOARD_MENU_STATE_OK (fallback anchor)")
            landed.append("menu-state")
        else:
            print("WARNING: dart menu state anchor not found - center menu state NOT added")
            return 1

    # ---- Piece 8: center render of the SAME DartboardMenuModal. ----
    # PvP inclusion is decided ONLY from the darts pieces themselves
    # (the pool menu already has onPlayPvp — a global check would lie).
    mspan = _dart_menu_span(src)
    has_pvp_button = mspan is not None and "onPlayPvp" in src[mspan[0]:mspan[1]]
    has_pvp_state = "const [dartPvpOpen, setDartPvpOpen]" in src
    has_pvp_modal = "DartPvpModal visible={dartPvpOpen}" in src
    pvp_ok = has_pvp_button and has_pvp_state and has_pvp_modal
    if not pvp_ok:
        print("NOTE: darts PvP room screen not fully wired in this build (button=%s state=%s modal=%s) - center menu matches the house menu without the PvP button" % (has_pvp_button, has_pvp_state, has_pvp_modal))

    if "DartboardMenuModal visible={dartMenuCenterOpen}" in src:
        print("ACTIVITY_CENTER_DARTBOARD_RENDER_ALREADY_APPLIED")
        landed.append("render")
    else:
        menu_lines = src.split("\n")
        house_idx = None
        for i, ln in enumerate(menu_lines):
            if "DartboardMenuModal visible={dartMenuOpen}" in ln:
                house_idx = i
                break
        close_idx = None
        if house_idx is not None:
            for j in range(house_idx, min(len(menu_lines), house_idx + 6)):
                if menu_lines[j].strip() == ") : null}" or menu_lines[j].strip().endswith(") : null}"):
                    close_idx = j
                    break
        if house_idx is None or close_idx is None:
            print("WARNING: house dart menu render close not found - center menu render NOT added")
            return 1
        pvp_prop = " onPlayPvp={() => { setDartMenuCenterOpen(false); setDartPvpOpen(true); }}" if pvp_ok else ""
        hide_prop = " hideManage" if hide_ok else ""
        render_block = (
            "      {dartMenuCenterOpen ? (\n"
            "        <DartboardMenuModal visible={dartMenuCenterOpen} onClose={() => setDartMenuCenterOpen(false)}"
            " onPlay={() => { setDartMenuCenterOpen(false); setDartGameOpen(true); }}" + pvp_prop +
            " onMove={() => setDartMenuCenterOpen(false)} onSell={() => setDartMenuCenterOpen(false)}" + hide_prop + " />\n"
            "      ) : null}"
        )
        menu_lines = menu_lines[:close_idx + 1] + [render_block] + menu_lines[close_idx + 1:]
        src = "\n".join(menu_lines)
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_RENDER_OK")
        landed.append("render")

    # ---- Piece 9: dartboard picture in the scene, after the pool table. ----
    if "centerDartResponder.current.panHandlers" in src:
        print("ACTIVITY_CENTER_DARTBOARD_PICTURE_ALREADY_APPLIED")
        landed.append("picture")
    else:
        ph = src.find("centerPoolResponder.current.panHandlers")
        if ph == -1:
            print("WARNING: pool table picture not found in scene - dartboard picture NOT added")
            return 1
        view_close = src.find("</View>", ph)
        if view_close == -1:
            print("WARNING: pool table view close not found - dartboard picture NOT added")
            return 1
        view = DART_VIEW.replace("__DART_ART_REQUIRE__", art)
        src = src[:view_close + len("</View>")] + view + src[view_close + len("</View>"):]
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_PICTURE_OK")
        landed.append("picture")

    # ---- Piece 10: hint now names both fixtures (best effort). ----
    if "Hold the pool table or dartboard to move it" in src:
        print("ACTIVITY_CENTER_DARTBOARD_HINT_ALREADY_APPLIED")
        landed.append("hint")
    elif src.count(POOL_HINT) == 1:
        src = src.replace(POOL_HINT, "Hold the pool table or dartboard to move it — swipe the room to look around.", 1)
        changed = True
        print("ACTIVITY_CENTER_DARTBOARD_HINT_OK")
        landed.append("hint")
    else:
        print("NOTE: Veno hint matched %dx - hint stays pool-only" % src.count(POOL_HINT))

    # ---- api.ts sanity: the layout save fn must exist (v2's piece). ----
    if asrc and "export const saveCenterLayout" not in asrc:
        print("WARNING: saveCenterLayout missing in api.ts - drag will move locally only (v2 api piece did not land)")
        warnings.append("api")

    if _balance(src) != orig:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    if not landed:
        print("ACTIVITY_CENTER_DARTBOARD_PARTIAL: nothing landed")
        return 1
    if not changed:
        print("ACTIVITY_CENTER_DARTBOARD_ALREADY_APPLIED")
        return 0
    IDX.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_DARTBOARD_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
