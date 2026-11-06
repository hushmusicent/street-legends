#!/usr/bin/env python3
"""Street Legends frontend: Activity Center pool table v2 — a real room, not a menu card.

User rejection (2026-11-06 10:35 EST, live center interior on screen):
"No. Not like this. It needs to scroll lady and right. And I don't want
the menu with games. I want them wired like the house I want the actual
picture of the pool table like the house you can press it for the pvc and
pvp menu and hold drag and move to arrange the table" ("lady" = "left").

What v2 does (frontend only — the layout endpoint is REUSED untouched):
  1. HORIZONTALLY SCROLLABLE ROOM: the center interior modal becomes a
     real room. Center name + "Inside now" list stay FIXED at the top,
     LEAVE stays FIXED at the bottom; only the SCENE (hall picture +
     pool table) pans left/right in a horizontal ScrollView. The hall
     renders wide inside the scene (scene width = scene height x 1.5,
     the hall art's true 1920x1280 aspect), measured by onLayout.
  2. REAL TABLE PICTURE: the green "POOL TABLE - TAP TO PLAY" menu card
     is REMOVED entirely. The table renders as its ACTUAL picture — the
     house's exact image source, resolved at patch time from the
     HOUSE_ITEMS pool entry's image: require (the cutout patch swapped
     it to pool-table.png; v1 checked for the .jpg, which is why the
     card fell back to the 8-ball tile). Rendered 280x187, resizeMode
     "contain", exactly like the house room render. Never a menu card.
  3. TAP = PLAY MENU: tapping the table picture opens the SAME
     PoolTableMenuModal the house uses (PvC -> PoolGameModal, PvP ->
     PoolPvpModal; hideManage still hiding MOVE/SELL on the center
     path). Unchanged for every player inside.
  4. HOLD-DRAG = ARRANGE (Veno only): press-and-HOLD the table picture
     (250ms), then drag to move it within the scene. While dragging,
     scene scrolling is disabled so the gestures do not fight (same
     pattern as the house room drag). The ARRANGE hint ("Hold the pool
     table to move it - swipe the room to look around.") renders ONLY
     for Mayor Veno (player_id 3872dca3-bf7d-4807-8fc5-47c22ba67620);
     for anyone else the table is fixed and hold does nothing (tap
     still opens the play menu). On release (or LEAVE/close) the new
     position saves via the EXISTING POST /activity-centers/{id}/layout
     endpoint; a 403 snaps the table back and shows "Only Mayor Veno
     can arrange this center." The superseded NUDGE-BUTTON arrange UI
     (ARRANGE button + MOVE THE POOL TABLE arrow row + its state) is
     REMOVED if present; hold-drag is the only arrange path.
  5. POSITIONS: fractional, house-style (0.06..0.94, default
     {x:0.5, y:0.72}). The layout endpoint stores INTEGER PIXELS —
     its clamp rounds to int (x -16..120, y -8..120) — so v2 converts
     at the boundary: storedToCenterPos / centerPosToStored map the
     full fractional box onto the backend's storable pixel box,
     round-trip exact. NO backend change needed; the endpoint is
     reused as-is. Legacy pixel layouts (from the nudge patch) load
     through the same conversion, so a table Veno nudged before v2
     keeps its relative spot.

UNCHANGED: center name, "Inside now" list (own name first), LEAVE,
presence enter/leave/heartbeat, the play menu contents, house pool
table + house move rules, the layout endpoint + its permission.
Nothing is added to any shop/item catalog or house menu. Emoji are
literal characters, never unicode escapes.

Run from /app: python3 frontend/patch-activity-center-pool-table-v2-frontend.py
Frontend / Expo Go only. Idempotent: a full re-run prints
ACTIVITY_CENTER_POOL_V2_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"
MARKER = "ACTIVITY_CENTER_POOL_V2_OK"
VENO_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"
HOLD_MS = 250
TAP_DIST = 12

MODAL_ANCHOR = "{/* ACTIVITY_CENTER interior — no menu, just who is inside. */}"
STATE_ANCHOR = "  const [centerFriendIds, setCenterFriendIds] = useState<string[]>([]);"
PRESENCE_EFFECT_CLOSE = "  }, [activeCenter?.id, playerId]);"
CARD_LABEL = "🎱 POOL TABLE — TAP TO PLAY</Text>"
POOL_MENU_STATE = "const [poolMenuCenterOpen, setPoolMenuCenterOpen]"
API_FN_ANCHOR = """export const getCenterPresence = async (centerId: string): Promise<any> => {
  const response = await api.get(`/activity-centers/${centerId}/presence`);
  return response.data;
};"""
API_FN = """export const saveCenterLayout = async (centerId: string, playerId: string, layout: any): Promise<any> => {
  const response = await api.post(`/activity-centers/${centerId}/layout`, { player_id: playerId, layout });
  return response.data;
};"""
POOL_PNG_REQUIRE = "require('../../assets/houses/items/pool-table.png')"
POOL_JPG_REQUIRE = "require('../../assets/houses/items/pool-table.jpg')"

# Verbatim arrange-patch blocks (for removal): copied from
# frontend/patch-activity-center-arrange-frontend.py.
ARRANGE_STATE_BLOCK = """
  // ACTIVITY_CENTER_ARRANGE: only Mayor Veno may move/arrange center fixtures.
  const CENTER_ARRANGE_OWNER_ID = '3872dca3-bf7d-4807-8fc5-47c22ba67620';
  const [centerArrange, setCenterArrange] = useState(false);
  const [centerPoolPos, setCenterPoolPos] = useState({ x: 0, y: 0 });
  const [centerLayoutDirty, setCenterLayoutDirty] = useState(false);
  const [centerArrangeMsg, setCenterArrangeMsg] = useState('');
  const clampCenterPoolPos = (p: any) => ({ x: Math.max(-16, Math.min(120, Math.round(Number(p?.x) || 0))), y: Math.max(-8, Math.min(120, Math.round(Number(p?.y) || 0))) });
  const nudgeCenterPool = (dx: number, dy: number) => { setCenterPoolPos((p: any) => clampCenterPoolPos({ x: p.x + dx, y: p.y + dy })); setCenterLayoutDirty(true); };
  const resetCenterPoolPos = () => { setCenterPoolPos({ x: 0, y: 0 }); setCenterLayoutDirty(true); };
  const saveCenterLayoutNow = async () => {
    if (!activeCenter || !centerLayoutDirty) return;
    if (playerId !== CENTER_ARRANGE_OWNER_ID) { setCenterArrangeMsg('Only Mayor Veno can arrange this center.'); return; }
    try {
      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPoolPos });
      setCenterLayoutDirty(false);
      setCenterArrangeMsg('');
    } catch (e: any) {
      if (e?.response?.status === 403) {
        const l = (activeCenter as any)?.layout?.pool_table;
        setCenterPoolPos(clampCenterPoolPos(l || { x: 0, y: 0 }));
        setCenterLayoutDirty(false);
        setCenterArrangeMsg('Only Mayor Veno can arrange this center.');
      }
    }
  };
  const closeActiveCenter = async () => {
    if (centerArrange && centerLayoutDirty) { await saveCenterLayoutNow(); }
    setCenterArrange(false);
    setActiveCenter(null);
  };"""

ARRANGE_LOAD_EFFECT = """
  // ACTIVITY_CENTER_ARRANGE: load this center's stored layout when it opens.
  useEffect(() => {
    const l = (activeCenter as any)?.layout?.pool_table;
    setCenterPoolPos(clampCenterPoolPos(l || { x: 0, y: 0 }));
    setCenterLayoutDirty(false);
    setCenterArrange(false);
    setCenterArrangeMsg('');
  }, [activeCenter?.id]);"""


def _balance(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def _modal_span(src):
    """(start, end) of the center interior modal, or None."""
    start = src.find(MODAL_ANCHOR)
    if start == -1:
        return None
    end = src.find("</Modal>", start)
    if end == -1:
        return None
    return (start, end + len("</Modal>"))


def _iife_end(s, start):
    """Index just past the final } of the {(() => {...})()} block at start."""
    depth = 0
    i = start
    while i < len(s):
        c = s[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return -1


def _resolve_pool_art(src, root):
    """House pool table picture source, in fallback order. Returns
    (require_expression, source_name). Never a menu card / emoji tile."""
    m = re.search(r"id:\s*'pool-table'[^}]*?image:\s*(require\([^)]+\))", src)
    if m:
        return m.group(1), "house-items-entry"
    m = re.search(r"require\(['\"][^'\"]*pool-table\.png['\"]\)", src)
    if m:
        return m.group(0), "png-require-in-index"
    m = re.search(r"require\(['\"][^'\"]*pool-table\.jpg['\"]\)", src)
    if m:
        return m.group(0), "jpg-require-in-index"
    if (root / "frontend/assets/houses/items/pool-table.png").exists():
        return POOL_PNG_REQUIRE, "asset-file-png"
    if (root / "frontend/assets/houses/items/pool-table.jpg").exists():
        return POOL_JPG_REQUIRE, "asset-file-jpg"
    return POOL_PNG_REQUIRE, "canonical-cutout-path"

V2_STATE_BLOCK = """
  // ACTIVITY_CENTER_POOL_V2: hold-drag arrange (Veno only), tap = play menu.
  // Positions are FRACTIONAL, house-style (0.06..0.94, default {x:0.5, y:0.72}).
  // The layout endpoint stores INTEGER PIXELS (backend clamps x -16..120,
  // y -8..120 and rounds), so storedToCenterPos / centerPosToStored convert
  // at the boundary: the full fractional box maps onto the backend's
  // storable pixel box, round-trip exact. The endpoint is reused untouched.
  const CENTER_ARRANGE_OWNER_ID = '3872dca3-bf7d-4807-8fc5-47c22ba67620';
  const [centerPoolPos, setCenterPoolPos] = useState({ x: 0.5, y: 0.72 });
  const [centerPoolDrag, setCenterPoolDrag] = useState(false);
  const [centerLayoutDirty, setCenterLayoutDirty] = useState(false);
  const [centerArrangeMsg, setCenterArrangeMsg] = useState('');
  const [centerSceneH, setCenterSceneH] = useState(400);
  const [centerSceneScrollEnabled, setCenterSceneScrollEnabled] = useState(true);
  const centerPoolPosRef = useRef({ x: 0.5, y: 0.72 });
  const centerDragStartRef = useRef({ x: 0.5, y: 0.72 });
  const centerHoldStartRef = useRef(0);
  const centerDragMovedRef = useRef(false);
  const centerSceneHRef = useRef(400);
  const centerSceneWRef = useRef(600);
  const centerPoolResponder = useRef<any>(null);
  const centerCtxRef = useRef<any>({ playerId, activeCenter });
  const saveCenterLayoutNowRef = useRef<any>(() => {});
  const centerSceneW = centerSceneH * 1.5;
  const storedToCenterPos = (l: any) => {
    const d = { x: 0.5, y: 0.72 };
    if (!l || typeof l.x !== 'number' || typeof l.y !== 'number') return d;
    if (!Number.isInteger(l.x) || !Number.isInteger(l.y)) {
      return { x: Math.min(0.94, Math.max(0.06, l.x)), y: Math.min(0.94, Math.max(0.06, l.y)) };
    }
    const px = Math.max(-16, Math.min(120, Math.round(l.x)));
    const py = Math.max(-8, Math.min(120, Math.round(l.y)));
    return { x: 0.06 + ((px + 16) / 136) * 0.88, y: 0.06 + ((py + 8) / 128) * 0.88 };
  };
  const centerPosToStored = (p: any) => {
    const fx = Math.min(0.94, Math.max(0.06, Number(p?.x) || 0.5));
    const fy = Math.min(0.94, Math.max(0.06, Number(p?.y) || 0.72));
    return { x: Math.round(-16 + ((fx - 0.06) / 0.88) * 136), y: Math.round(-8 + ((fy - 0.06) / 0.88) * 128) };
  };
  const saveCenterLayoutNow = async () => {
    if (!activeCenter || !centerLayoutDirty) return;
    if (playerId !== CENTER_ARRANGE_OWNER_ID) { setCenterArrangeMsg('Only Mayor Veno can arrange this center.'); return; }
    try {
      await saveCenterLayout(activeCenter.id, playerId, { pool_table: centerPosToStored(centerPoolPosRef.current) });
      setCenterLayoutDirty(false);
      setCenterArrangeMsg('');
    } catch (e: any) {
      if (e?.response?.status === 403) {
        const back = storedToCenterPos((activeCenter as any)?.layout?.pool_table);
        centerPoolPosRef.current = back;
        setCenterPoolPos(back);
        setCenterLayoutDirty(false);
        setCenterArrangeMsg('Only Mayor Veno can arrange this center.');
      }
    }
  };
  const closeActiveCenter = async () => {
    if (centerLayoutDirty) { await saveCenterLayoutNow(); }
    setActiveCenter(null);
  };
  useEffect(() => {
    centerCtxRef.current = { playerId, activeCenter };
    saveCenterLayoutNowRef.current = saveCenterLayoutNow;
  });
  if (!centerPoolResponder.current) {
    centerPoolResponder.current = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        setCenterSceneScrollEnabled(false);
        centerHoldStartRef.current = Date.now();
        centerDragStartRef.current = { ...(centerPoolPosRef.current || { x: 0.5, y: 0.72 }) };
        centerDragMovedRef.current = false;
      },
      onPanResponderMove: (evt: any, gesture: any) => {
        if (centerCtxRef.current.playerId !== CENTER_ARRANGE_OWNER_ID) return;
        if (Date.now() - centerHoldStartRef.current < 250) return;
        const s = centerDragStartRef.current || { x: 0.5, y: 0.72 };
        const nx = Math.min(0.94, Math.max(0.06, s.x + gesture.dx / centerSceneWRef.current));
        const ny = Math.min(0.94, Math.max(0.06, s.y + gesture.dy / centerSceneHRef.current));
        centerDragMovedRef.current = true;
        centerPoolPosRef.current = { x: nx, y: ny };
        setCenterPoolPos({ x: nx, y: ny });
        setCenterPoolDrag(true);
        setCenterLayoutDirty(true);
      },
      onPanResponderRelease: (evt: any, gesture: any) => {
        setCenterSceneScrollEnabled(true);
        setCenterPoolDrag(false);
        const tapDist = Math.hypot(gesture.dx || 0, gesture.dy || 0);
        if (tapDist < 12) { setPoolMenuCenterOpen(true); return; }
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
      onPanResponderTerminate: () => {
        setCenterSceneScrollEnabled(true);
        setCenterPoolDrag(false);
        if (centerDragMovedRef.current) { saveCenterLayoutNowRef.current(); }
      },
    });
  }"""

V2_LOAD_EFFECT = """
  // ACTIVITY_CENTER_POOL_V2: load this center's stored layout (backend pixels) when it opens.
  useEffect(() => {
    const pos = storedToCenterPos((activeCenter as any)?.layout?.pool_table);
    centerPoolPosRef.current = pos;
    setCenterPoolPos(pos);
    setCenterLayoutDirty(false);
    setCenterArrangeMsg('');
    setCenterPoolDrag(false);
  }, [activeCenter?.id]);"""

# Inserted after the "Inside now" occupants IIFE, inside the modal.
# __POOL_ART_REQUIRE__ is replaced with the resolved house image require.
# The header View closes here; the ScrollView scene follows; LEAVE stays
# after the scene, fixed at the bottom.
SCENE_BLOCK = """
            {playerId === CENTER_ARRANGE_OWNER_ID && (
              <Text style={{ fontSize: 13, color: '#ffd54f', marginTop: 10 }}>Hold the pool table to move it — swipe the room to look around.</Text>
            )}
            {centerArrangeMsg ? (<Text style={{ fontSize: 13, color: '#ff8a80', marginTop: 6 }}>{centerArrangeMsg}</Text>) : null}
          </View>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={{ flex: 1 }}
            scrollEnabled={centerSceneScrollEnabled}
            onLayout={(e: any) => { const h = e?.nativeEvent?.layout?.height || 0; if (h > 0 && h !== centerSceneHRef.current) { centerSceneHRef.current = h; centerSceneWRef.current = h * 1.5; setCenterSceneH(h); } }}
          >
            <View style={{ width: centerSceneW, height: centerSceneH }}>
              <Image source={{ uri: ACTIVITY_CENTER_BG }} style={{ width: centerSceneW, height: centerSceneH }} resizeMode="cover" />
              <View
                {...(centerPoolResponder.current ? centerPoolResponder.current.panHandlers : {})}
                style={{ position: 'absolute', left: centerPoolPos.x * centerSceneW - 140, top: centerPoolPos.y * centerSceneH - 93, width: 280, height: 187, borderWidth: centerPoolDrag ? 3 : 0, borderColor: '#ffd54f', borderRadius: 8 }}
              >
                <Image source={__POOL_ART_REQUIRE__} style={{ width: 280, height: 187, borderRadius: 8 }} resizeMode="contain" />
              </View>
            </View>
          </ScrollView>"""


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - center pool v2 NOT added")
        return 1
    if not API.exists():
        print("WARNING: services/api.ts not found - center pool v2 NOT added (layout save needs the api function)")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore")
    orig = _balance(src)
    landed = []
    warnings = []
    changed = False
    achanged = False

    # ---- Idempotency: v2 already landed. ----
    if "ACTIVITY_CENTER_POOL_V2" in src and "centerSceneScrollEnabled" in src:
        print("ACTIVITY_CENTER_POOL_V2_ALREADY_APPLIED")
        return 0

    # ---- Preconditions: the center modal + the v1 pool menu must exist. ----
    if MODAL_ANCHOR not in src:
        print("WARNING: activity center interior modal not found - center pool v2 NOT added")
        return 1
    if "setPoolMenuCenterOpen(true)" not in src or "PoolTableMenuModal visible={poolMenuCenterOpen}" not in src:
        print("WARNING: center pool menu not found - run the pool-table patch first, center pool v2 NOT added")
        return 1
    if CARD_LABEL not in src:
        print("WARNING: center pool table card not found - run the pool-table patch first, center pool v2 NOT added")
        return 1

    # ---- Piece 0: resolve the house's live table picture (proof line). ----
    art, art_source = _resolve_pool_art(src, ROOT)
    print("POOL_V2_ART=%s via %s" % (art, art_source))
    if art_source == "canonical-cutout-path":
        print("NOTE: pool table art require not found in index.tsx and no asset file on disk - using the canonical cutout path (pool-table.png written by the cutout patch); if the bundle cannot resolve it, the table will not render")

    # ---- Piece 1: api.ts saveCenterLayout (reuse; add only if missing). ----
    if "export const saveCenterLayout" in asrc:
        print("ACTIVITY_CENTER_POOL_V2_API_ALREADY_APPLIED")
        landed.append("api")
    elif asrc.count(API_FN_ANCHOR) == 1:
        asrc = asrc.replace(API_FN_ANCHOR, API_FN_ANCHOR + "\n" + API_FN, 1)
        achanged = True
        print("ACTIVITY_CENTER_POOL_V2_API_OK")
        landed.append("api")
    else:
        print("WARNING: getCenterPresence anchor matched %dx in api.ts - layout save NOT wired (drag will move locally only)" % asrc.count(API_FN_ANCHOR))
        warnings.append("api")

    # ---- Piece 2: import saveCenterLayout in index.tsx. ----
    # NOTE: check the import ENTRY, not the bare name — the arrange state
    # block already calls saveCenterLayout, so a bare-name check would
    # false-positive when the import itself is missing (partial arrange run).
    if "  saveCenterLayout,\n" in src:
        print("ACTIVITY_CENTER_POOL_V2_IMPORT_ALREADY_APPLIED")
        landed.append("import")
    elif src.count("  getCenterPresence,\n") == 1:
        src = src.replace("  getCenterPresence,\n", "  getCenterPresence,\n  saveCenterLayout,\n", 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_V2_IMPORT_OK")
        landed.append("import")
    else:
        print("WARNING: api import block matched %dx - layout save NOT wired (drag will move locally only)" % src.count("  getCenterPresence,\n"))
        warnings.append("import")

    # ---- Piece 3: PanResponder import (house drag already uses it live). ----
    # Check the import ENTRY, not the bare name (same partial-run trap as above).
    if "  PanResponder,\n" in src:
        print("ACTIVITY_CENTER_POOL_V2_PANRESPONDER_ALREADY_APPLIED")
        landed.append("panresponder")
    elif src.count("  Dimensions,\n} from 'react-native';") == 1:
        src = src.replace("  Dimensions,\n} from 'react-native';", "  Dimensions,\n  PanResponder,\n} from 'react-native';", 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_V2_PANRESPONDER_OK")
        landed.append("panresponder")
    elif src.count("  Image,\n} from 'react-native';") == 1:
        src = src.replace("  Image,\n} from 'react-native';", "  Image,\n  PanResponder,\n} from 'react-native';", 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_V2_PANRESPONDER_OK")
        landed.append("panresponder")
    else:
        print("WARNING: react-native import anchor not found - PanResponder NOT imported (hold-drag will fail to compile)")
        warnings.append("panresponder")

    # ---- Piece 4: v2 state + hold-drag responder (replaces arrange nudge state). ----
    if "ACTIVITY_CENTER_POOL_V2: hold-drag arrange" in src:
        print("ACTIVITY_CENTER_POOL_V2_STATE_ALREADY_APPLIED")
        landed.append("state")
    elif ARRANGE_STATE_BLOCK in src:
        src = src.replace(ARRANGE_STATE_BLOCK, V2_STATE_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_V2_STATE_OK (arrange nudge state replaced)")
        landed.append("state")
    elif "const [centerArrange, setCenterArrange]" in src:
        mstart = src.find("// ACTIVITY_CENTER_ARRANGE: only Mayor Veno")
        mend = src.find("setActiveCenter(null);\n  };", mstart) if mstart != -1 else -1
        seg = src[mstart:mend + len("setActiveCenter(null);\n  };")] if mstart != -1 and mend != -1 else ""
        if seg and "centerArrange" in seg and "saveCenterLayoutNow" in seg and "closeActiveCenter" in seg:
            src = src[:mstart] + src[mend + len("setActiveCenter(null);\n  };"):]
            if src.count(STATE_ANCHOR) == 1:
                src = src.replace(STATE_ANCHOR, STATE_ANCHOR + V2_STATE_BLOCK, 1)
                changed = True
                print("ACTIVITY_CENTER_POOL_V2_STATE_OK (arrange nudge state removed by markers)")
                landed.append("state")
            else:
                print("WARNING: center state anchor matched %dx after arrange removal - v2 state NOT added" % src.count(STATE_ANCHOR))
                return 1
        else:
            print("WARNING: arrange state block not matched verbatim or by markers - v2 state NOT added")
            return 1
    elif src.count(STATE_ANCHOR) == 1:
        src = src.replace(STATE_ANCHOR, STATE_ANCHOR + V2_STATE_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_V2_STATE_OK")
        landed.append("state")
    else:
        print("WARNING: center state anchor matched %dx - v2 state NOT added" % src.count(STATE_ANCHOR))
        return 1

    # ---- Piece 5: load stored layout when a center opens (replaces arrange load). ----
    if "ACTIVITY_CENTER_POOL_V2: load this center's stored layout" in src:
        print("ACTIVITY_CENTER_POOL_V2_LOAD_ALREADY_APPLIED")
        landed.append("load")
    elif ARRANGE_LOAD_EFFECT in src:
        src = src.replace(ARRANGE_LOAD_EFFECT, V2_LOAD_EFFECT, 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_V2_LOAD_OK (arrange load replaced)")
        landed.append("load")
    elif src.count(PRESENCE_EFFECT_CLOSE) == 1:
        src = src.replace(PRESENCE_EFFECT_CLOSE, PRESENCE_EFFECT_CLOSE + V2_LOAD_EFFECT, 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_V2_LOAD_OK")
        landed.append("load")
    else:
        print("WARNING: presence effect close matched %dx - stored layout load NOT added (table will sit at the default spot)" % src.count(PRESENCE_EFFECT_CLOSE))
        warnings.append("load")

    # ---- Piece 6: restructure the center interior modal into a room. ----
    span = _modal_span(src)
    if span is None:
        print("WARNING: center modal span not found - room restructure NOT done")
        return 1
    s0, s1 = span
    body = src[s0:s1]

    # 6a. Remove the v1 green menu card (both the plain and arrange-styled forms).
    if CARD_LABEL in body:
        li = body.find(CARD_LABEL)
        t_start = body.rfind("<TouchableOpacity", 0, li)
        t_end = body.find("</TouchableOpacity>", li)
        if t_start != -1 and t_end != -1 and "#1b5e20" in body[t_start:li]:
            body = body[:t_start] + body[t_end + len("</TouchableOpacity>"):]
            print("ACTIVITY_CENTER_POOL_V2_CARD_REMOVED")
            landed.append("card-removed")
        else:
            print("WARNING: pool card boundaries not found - green menu card NOT removed")
            warnings.append("card")
    else:
        print("WARNING: pool card label not found in modal - green menu card NOT removed")
        warnings.append("card")

    # 6b. Remove the superseded ARRANGE button (Veno-only nudge toggle).
    if "DONE ARRANGING" in body:
        di = body.find("DONE ARRANGING")
        b_start = body.rfind("{playerId === CENTER_ARRANGE_OWNER_ID && (", 0, di)
        b_end = body.find("\n            )}", di)
        if b_start != -1 and b_end != -1:
            body = body[:b_start] + body[b_end + len("\n            )}"):]
            print("ACTIVITY_CENTER_POOL_V2_ARRANGE_BUTTON_REMOVED")
            landed.append("arrange-button-removed")
        else:
            print("WARNING: ARRANGE button boundaries not found - nudge toggle NOT removed")
            warnings.append("arrange-button")
    else:
        print("NOTE: ARRANGE button absent - nothing to remove")

    # 6c. Remove the superseded nudge-button row (MOVE THE POOL TABLE).
    if "MOVE THE POOL TABLE" in body:
        mi = body.find("MOVE THE POOL TABLE")
        n_start = body.rfind("{centerArrange && playerId === CENTER_ARRANGE_OWNER_ID && (", 0, mi)
        n_end = body.find("\n            )}", mi)
        if n_start != -1 and n_end != -1:
            body = body[:n_start] + body[n_end + len("\n            )}"):]
            print("ACTIVITY_CENTER_POOL_V2_NUDGE_REMOVED")
            landed.append("nudge-removed")
        else:
            print("WARNING: nudge row boundaries not found - nudge controls NOT removed")
            warnings.append("nudge")
    else:
        print("NOTE: nudge controls absent - nothing to remove")

    # 6d. Replace the ImageBackground + dark overlay with a plain root View
    #     + a fixed header View (name / subtitle / Inside now stay inside it).
    img_start = body.find("<ImageBackground")
    pt = body.find("paddingTop: 60", img_start) if img_start != -1 else -1
    open_end = body.find("}}>", pt) if pt != -1 else -1
    if img_start == -1 or pt == -1 or open_end == -1 or "ACTIVITY_CENTER_BG" not in body[img_start:pt]:
        print("WARNING: center modal background open not found - room restructure NOT done")
        return 1
    new_open = "<View style={{ flex: 1, backgroundColor: '#000000' }}>\n          <View style={{ padding: 20, paddingTop: 60, paddingBottom: 12 }}>"
    body = body[:img_start] + new_open + body[open_end + 3:]
    print("ACTIVITY_CENTER_POOL_V2_ROOM_OPEN_OK")
    landed.append("room-open")

    # 6e. After the "Inside now" occupants IIFE: Veno hint + arrange message,
    #     close the header View, then the horizontal ScrollView scene.
    inside_idx = body.find("Inside now:")
    ii = body.find("{(() => {", inside_idx) if inside_idx != -1 else -1
    iife_end = _iife_end(body, ii) if ii != -1 else -1
    if ii == -1 or iife_end == -1:
        print("WARNING: Inside now occupants block not found - room scene NOT inserted")
        return 1
    scene = SCENE_BLOCK.replace("__POOL_ART_REQUIRE__", art)
    body = body[:iife_end] + scene + body[iife_end:]
    print("ACTIVITY_CENTER_POOL_V2_SCENE_OK")
    landed.append("scene")

    # 6f. The old overlay close + ImageBackground close become the root close.
    ib = body.find("</ImageBackground>")
    vc = body.rfind("</View>", 0, ib) if ib != -1 else -1
    if ib == -1 or vc == -1:
        print("WARNING: center modal background close not found - room restructure NOT done")
        return 1
    body = body[:vc] + "</View>" + body[ib + len("</ImageBackground>"):]
    print("ACTIVITY_CENTER_POOL_V2_ROOM_CLOSE_OK")
    landed.append("room-close")

    # 6g. LEAVE + onRequestClose save first (closeActiveCenter), so a drag
    #     is persisted when Veno leaves the center.
    if "onRequestClose={closeActiveCenter}" in body:
        print("ACTIVITY_CENTER_POOL_V2_CLOSE_ALREADY_APPLIED")
        landed.append("close")
    elif body.count("onRequestClose={() => setActiveCenter(null)}") == 1:
        body = body.replace("onRequestClose={() => setActiveCenter(null)}", "onRequestClose={closeActiveCenter}", 1)
        print("ACTIVITY_CENTER_POOL_V2_CLOSE_OK")
        landed.append("close")
    else:
        print("WARNING: modal onRequestClose matched %dx - close-save NOT wired" % body.count("onRequestClose={() => setActiveCenter(null)}"))
        warnings.append("close")
    if "onPress={closeActiveCenter}" in body:
        print("ACTIVITY_CENTER_POOL_V2_LEAVE_ALREADY_APPLIED")
        landed.append("leave")
    elif body.count("onPress={() => setActiveCenter(null)}") == 1:
        body = body.replace("onPress={() => setActiveCenter(null)}", "onPress={closeActiveCenter}", 1)
        print("ACTIVITY_CENTER_POOL_V2_LEAVE_OK")
        landed.append("leave")
    else:
        print("WARNING: LEAVE onPress matched %dx - close-save NOT wired" % body.count("onPress={() => setActiveCenter(null)}"))
        warnings.append("leave")

    src = src[:s0] + body + src[s1:]
    changed = True

    # ---- Piece 7: hideManage on PoolTableMenuModal (v1's piece; check only). ----
    mspan = None
    start = src.find("const PoolTableMenuModal = ({")
    pos = start
    while start != -1:
        end = src.find("\n};\n", pos)
        if end == -1:
            break
        cand = src[start:end + 4]
        if "PLAY VS COMPUTER" in cand and "CANCEL" in cand:
            mspan = cand
            break
        pos = end + 4
    if mspan is None:
        print("WARNING: PoolTableMenuModal component not found - MOVE/SELL visibility on the center path unverified (menu still opens; onMove/onSell close it)")
        warnings.append("hidemanage")
    elif "hideManage" in mspan:
        print("ACTIVITY_CENTER_POOL_V2_HIDEMANAGE_OK")
        landed.append("hidemanage")
    else:
        print("WARNING: hideManage missing on PoolTableMenuModal - MOVE/SELL stay visible but inert on the center path")
        warnings.append("hidemanage")

    if _balance(src) != orig:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    if not landed:
        print("ACTIVITY_CENTER_POOL_V2_PARTIAL: nothing landed")
        return 1
    if not changed and not achanged:
        print("ACTIVITY_CENTER_POOL_V2_ALREADY_APPLIED")
        return 0
    if achanged:
        API.write_text(asrc)
    if changed:
        IDX.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_POOL_V2_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
