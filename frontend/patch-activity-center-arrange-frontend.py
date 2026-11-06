#!/usr/bin/env python3
"""Street Legends frontend: Activity Center arrange permission.

User rule (2026-11-06 05:57 EST): "And only give me permission to move
and arrange things around in the activity center."

What this does (apply AFTER frontend/patch-activity-center-pool-table-frontend.py):
  * Arrange control: an ARRANGE button in the center interior modal that
    is VISIBLE ONLY when the current player is Mayor Veno
    (player_id 3872dca3-bf7d-4807-8fc5-47c22ba67620). Anyone else never
    sees it — the table is fixed for them. The backend 403 is the real
    enforcement; this hiding is just UI.
  * Moving: NUDGE BUTTONS, not drag — picked because the interior is a
    small fixed modal column (no map surface, no ScrollView to fight):
    drag would fight the modal's own touch handling and the card's
    tap-to-play, while arrow buttons are deterministic, thumb-friendly,
    and verifiable. When Arrange is on, ◀ ▲ ▼ ▶ move the pool table
    12px per tap (clamped x -16..120, y -8..120) and RESET puts it back
    to the default spot. While arranging, tapping the card does NOT
    open the play menu (that tap is the arrange interaction's space).
  * Saving: turning Arrange off (DONE ARRANGING) or leaving the center
    saves the position via POST /activity-centers/{id}/layout. A 403
    shows "Only Mayor Veno can arrange this center." and the table
    snaps back to its stored spot. The position is stored PER CENTER
    (the center's osm id) — arranging UT never moves another center.
  * Loading: when a center opens, the table renders at its stored
    layout (activeCenter.layout.pool_table) or the default spot.
  * UNCHANGED: tap-to-play (same house pool menu, PvC + PvP) works for
    EVERYONE inside; the "Inside now" list, hall picture, LEAVE,
    enter/leave/heartbeat, the house pool table, and house move rules
    are untouched. Nothing is added to any shop/item catalog or house
    menu. The backend patch (patch-activity-center-arrange.py) must run
    first — this patch only calls the endpoint it adds.

Run from /app: python3 frontend/patch-activity-center-arrange-frontend.py
Frontend / Expo Go only. Idempotent: per-piece presence checks; a full
re-run prints ACTIVITY_CENTER_ARRANGE_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"
MARKER = "ACTIVITY_CENTER_ARRANGE_OK"
VENO_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"

MODAL_ANCHOR = "{/* ACTIVITY_CENTER interior — no menu, just who is inside. */}"
STATE_ANCHOR = "  const [centerFriendIds, setCenterFriendIds] = useState<string[]>([]);"
PRESENCE_EFFECT_CLOSE = "  }, [activeCenter?.id, playerId]);"
SUBTITLE = "<Text style={{ fontSize: 14, color: '#e0e0e0', marginTop: 4 }}>Activity Center</Text>"
CARD_STYLE_OLD = "style={{ marginTop: 20, backgroundColor: '#1b5e20', borderRadius: 12, padding: 12, alignItems: 'center', borderWidth: 2, borderColor: '#8d5a2b' }}"
CARD_TAP_OLD = "onPress={() => setPoolMenuCenterOpen(true)}"
CARD_LABEL = "🎱 POOL TABLE — TAP TO PLAY</Text>"
API_FN = """export const saveCenterLayout = async (centerId: string, playerId: string, layout: any): Promise<any> => {
  const response = await api.post(`/activity-centers/${centerId}/layout`, { player_id: playerId, layout });
  return response.data;
};"""
API_FN_ANCHOR = """export const getCenterPresence = async (centerId: string): Promise<any> => {
  const response = await api.get(`/activity-centers/${centerId}/presence`);
  return response.data;
};"""

STATE_BLOCK = """
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

LOAD_EFFECT = """
  // ACTIVITY_CENTER_ARRANGE: load this center's stored layout when it opens.
  useEffect(() => {
    const l = (activeCenter as any)?.layout?.pool_table;
    setCenterPoolPos(clampCenterPoolPos(l || { x: 0, y: 0 }));
    setCenterLayoutDirty(false);
    setCenterArrange(false);
    setCenterArrangeMsg('');
  }, [activeCenter?.id]);"""

ARRANGE_BUTTON = """            {playerId === CENTER_ARRANGE_OWNER_ID && (
              <TouchableOpacity
                style={{ marginTop: 12, backgroundColor: centerArrange ? '#b7950b' : '#333333', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8, alignSelf: 'flex-start' }}
                onPress={async () => { if (centerArrange) { await saveCenterLayoutNow(); } setCenterArrange(!centerArrange); }}
              >
                <Text style={{ color: '#ffffff', fontWeight: '800' }}>{centerArrange ? '✓ DONE ARRANGING' : 'ARRANGE'}</Text>
              </TouchableOpacity>
            )}"""

NUDGE_ROW = """            {centerArrange && playerId === CENTER_ARRANGE_OWNER_ID && (
              <View style={{ marginTop: 10, backgroundColor: 'rgba(0,0,0,0.55)', borderRadius: 10, padding: 10 }}>
                <Text style={{ color: '#ffd54f', fontWeight: '800', textAlign: 'center', marginBottom: 8 }}>MOVE THE POOL TABLE</Text>
                <View style={{ flexDirection: 'row', justifyContent: 'center', alignItems: 'center' }}>
                  <TouchableOpacity onPress={() => nudgeCenterPool(-12, 0)} style={{ backgroundColor: '#444444', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8 }}><Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 18 }}>◀</Text></TouchableOpacity>
                  <View style={{ alignItems: 'center', marginHorizontal: 10 }}>
                    <TouchableOpacity onPress={() => nudgeCenterPool(0, -12)} style={{ backgroundColor: '#444444', paddingVertical: 6, paddingHorizontal: 16, borderRadius: 8, marginBottom: 6 }}><Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 18 }}>▲</Text></TouchableOpacity>
                    <TouchableOpacity onPress={() => nudgeCenterPool(0, 12)} style={{ backgroundColor: '#444444', paddingVertical: 6, paddingHorizontal: 16, borderRadius: 8 }}><Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 18 }}>▼</Text></TouchableOpacity>
                  </View>
                  <TouchableOpacity onPress={() => nudgeCenterPool(12, 0)} style={{ backgroundColor: '#444444', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8 }}><Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 18 }}>▶</Text></TouchableOpacity>
                  <TouchableOpacity onPress={resetCenterPoolPos} style={{ backgroundColor: '#7b1fa2', paddingVertical: 10, paddingHorizontal: 12, borderRadius: 8, marginLeft: 12 }}><Text style={{ color: '#ffffff', fontWeight: '800' }}>RESET</Text></TouchableOpacity>
                </View>
                {centerArrangeMsg ? (<Text style={{ color: '#ff8a80', textAlign: 'center', marginTop: 8 }}>{centerArrangeMsg}</Text>) : null}
              </View>
            )}"""


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


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - center arrange NOT added")
        return 1
    if not API.exists():
        print("WARNING: services/api.ts not found - center arrange NOT added (layout save needs the api function)")
        return 1
    src = IDX.read_text(errors="ignore")
    asrc = API.read_text(errors="ignore")
    orig = _balance(src)
    landed = []
    warnings = []
    changed = False
    achanged = False

    # ---- Preconditions: the pool-table patch must already be applied. ----
    if "setPoolMenuCenterOpen(true)" not in src or "PoolTableMenuModal visible={poolMenuCenterOpen}" not in src:
        print("WARNING: center pool table not found - run the pool-table patch first, arrange NOT added")
        return 1
    if MODAL_ANCHOR not in src:
        print("WARNING: activity center interior modal not found - center arrange NOT added")
        return 1

    # ---- Piece 0: api.ts saveCenterLayout (precondition for the save call). ----
    if "saveCenterLayout" in asrc:
        print("ACTIVITY_CENTER_ARRANGE_API_ALREADY_APPLIED")
        landed.append("api")
    elif asrc.count(API_FN_ANCHOR) == 1:
        asrc = asrc.replace(API_FN_ANCHOR, API_FN_ANCHOR + "\n" + API_FN, 1)
        achanged = True
        print("ACTIVITY_CENTER_ARRANGE_API_OK")
        landed.append("api")
    else:
        print("WARNING: getCenterPresence anchor matched %dx in api.ts - center arrange NOT added" % asrc.count(API_FN_ANCHOR))
        return 1

    # ---- Piece 1: import saveCenterLayout in index.tsx. ----
    if "saveCenterLayout" in src:
        print("ACTIVITY_CENTER_ARRANGE_IMPORT_ALREADY_APPLIED")
        landed.append("import")
    elif src.count("  getCenterPresence,\n") == 1:
        src = src.replace("  getCenterPresence,\n", "  getCenterPresence,\n  saveCenterLayout,\n", 1)
        changed = True
        print("ACTIVITY_CENTER_ARRANGE_IMPORT_OK")
        landed.append("import")
    else:
        print("WARNING: api import block matched %dx - center arrange NOT added" % src.count("  getCenterPresence,\n"))
        return 1

    # ---- Piece 2: arrange state + helpers. ----
    if "const [centerArrange, setCenterArrange]" in src:
        print("ACTIVITY_CENTER_ARRANGE_STATE_ALREADY_APPLIED")
        landed.append("state")
    elif src.count(STATE_ANCHOR) == 1:
        src = src.replace(STATE_ANCHOR, STATE_ANCHOR + STATE_BLOCK, 1)
        changed = True
        print("ACTIVITY_CENTER_ARRANGE_STATE_OK")
        landed.append("state")
    else:
        print("WARNING: center state anchor matched %dx - center arrange NOT added" % src.count(STATE_ANCHOR))
        return 1

    # ---- Piece 3: load stored layout when a center opens. ----
    if "ACTIVITY_CENTER_ARRANGE: load this center's stored layout" in src:
        print("ACTIVITY_CENTER_ARRANGE_LOAD_ALREADY_APPLIED")
        landed.append("load")
    elif src.count(PRESENCE_EFFECT_CLOSE) == 1:
        src = src.replace(PRESENCE_EFFECT_CLOSE, PRESENCE_EFFECT_CLOSE + LOAD_EFFECT, 1)
        changed = True
        print("ACTIVITY_CENTER_ARRANGE_LOAD_OK")
        landed.append("load")
    else:
        print("WARNING: presence effect close matched %dx - layout load NOT added" % src.count(PRESENCE_EFFECT_CLOSE))
        warnings.append("load")

    # ---- Piece 4: ARRANGE button (Veno only) under the subtitle. ----
    if "DONE ARRANGING" in src:
        print("ACTIVITY_CENTER_ARRANGE_BUTTON_ALREADY_APPLIED")
        landed.append("button")
    elif src.count(SUBTITLE) == 1:
        src = src.replace(SUBTITLE, SUBTITLE + "\n" + ARRANGE_BUTTON, 1)
        changed = True
        print("ACTIVITY_CENTER_ARRANGE_BUTTON_OK")
        landed.append("button")
    else:
        print("WARNING: center subtitle matched %dx - ARRANGE button NOT added" % src.count(SUBTITLE))
        warnings.append("button")

    # ---- Piece 5: card transform (gold border + translate when arranging). ----
    card_style_new = "style={{ marginTop: 20, backgroundColor: '#1b5e20', borderRadius: 12, padding: 12, alignItems: 'center', borderWidth: 2, borderColor: centerArrange ? '#ffd54f' : '#8d5a2b', transform: [{ translateX: centerPoolPos.x }, { translateY: centerPoolPos.y }] }}"
    if "translateX: centerPoolPos.x" in src:
        print("ACTIVITY_CENTER_ARRANGE_CARDSTYLE_ALREADY_APPLIED")
        landed.append("cardstyle")
    elif src.count(CARD_STYLE_OLD) == 1:
        src = src.replace(CARD_STYLE_OLD, card_style_new, 1)
        changed = True
        print("ACTIVITY_CENTER_ARRANGE_CARDSTYLE_OK")
        landed.append("cardstyle")
    else:
        print("WARNING: pool card style matched %dx - card transform NOT added" % src.count(CARD_STYLE_OLD))
        warnings.append("cardstyle")

    # ---- Piece 6: card tap does nothing while arranging (play otherwise). ----
    card_tap_new = "onPress={() => { if (!centerArrange) setPoolMenuCenterOpen(true); }}"
    if "if (!centerArrange) setPoolMenuCenterOpen(true)" in src:
        print("ACTIVITY_CENTER_ARRANGE_CARDTAP_ALREADY_APPLIED")
        landed.append("cardtap")
    elif src.count(CARD_TAP_OLD) == 1:
        src = src.replace(CARD_TAP_OLD, card_tap_new, 1)
        changed = True
        print("ACTIVITY_CENTER_ARRANGE_CARDTAP_OK")
        landed.append("cardtap")
    else:
        print("WARNING: pool card tap matched %dx - arrange tap gate NOT added" % src.count(CARD_TAP_OLD))
        warnings.append("cardtap")

    # ---- Piece 7: nudge controls under the pool card (arrange mode only). ----
    if "MOVE THE POOL TABLE" in src:
        print("ACTIVITY_CENTER_ARRANGE_NUDGE_ALREADY_APPLIED")
        landed.append("nudge")
    elif CARD_LABEL not in src:
        print("WARNING: pool card label not found - nudge controls NOT added")
        warnings.append("nudge")
    else:
        label_idx = src.find(CARD_LABEL)
        close_idx = src.find("</TouchableOpacity>", label_idx)
        if close_idx == -1:
            print("WARNING: pool card close not found - nudge controls NOT added")
            warnings.append("nudge")
        else:
            insert_at = close_idx + len("</TouchableOpacity>")
            src = src[:insert_at] + "\n" + NUDGE_ROW + src[insert_at:]
            changed = True
            print("ACTIVITY_CENTER_ARRANGE_NUDGE_OK")
            landed.append("nudge")

    # ---- Piece 8: modal close saves first (LEAVE + onRequestClose). ----
    span = _modal_span(src)
    if span is None:
        print("WARNING: center modal span not found - close-save NOT wired")
        warnings.append("close")
    elif "onRequestClose={closeActiveCenter}" in src[span[0]:span[1]] and "onPress={closeActiveCenter}" in src[span[0]:span[1]]:
        print("ACTIVITY_CENTER_ARRANGE_CLOSE_ALREADY_APPLIED")
        landed.append("close")
    else:
        s0, s1 = span
        body = src[s0:s1]
        new_body = body
        if body.count("onRequestClose={() => setActiveCenter(null)}") == 1:
            new_body = new_body.replace("onRequestClose={() => setActiveCenter(null)}", "onRequestClose={closeActiveCenter}", 1)
        if body.count("onPress={() => setActiveCenter(null)}") == 1:
            new_body = new_body.replace("onPress={() => setActiveCenter(null)}", "onPress={closeActiveCenter}", 1)
        if new_body != body:
            src = src[:s0] + new_body + src[s1:]
            changed = True
            print("ACTIVITY_CENTER_ARRANGE_CLOSE_OK")
            landed.append("close")
        else:
            print("WARNING: modal close anchors not found - close-save NOT wired")
            warnings.append("close")

    if _balance(src) != orig:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    if not landed:
        print("ACTIVITY_CENTER_ARRANGE_PARTIAL: nothing landed")
        return 1
    if not changed and not achanged:
        print("ACTIVITY_CENTER_ARRANGE_ALREADY_APPLIED")
        return 0
    if achanged:
        API.write_text(asrc)
    if changed:
        IDX.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_ARRANGE_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
