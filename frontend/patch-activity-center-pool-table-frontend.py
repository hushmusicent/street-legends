#!/usr/bin/env python3
"""Street Legends frontend: pool table in EVERY activity center interior.

User request (2026-11-06 05:49 EST): "Now add the pool table to all the
activity center no item menu just place it there with the same play menu."

What this does (frontend only — no backend change needed):
  * Every activity center interior shares ONE modal, so one fixture there
    covers every center: a tappable pool table card below the "Inside now"
    list, above LEAVE. It is a fixed fixture — NOT in any shop/item
    catalog, NOT buyable, NOT placeable, NOT in HOUSE_ITEMS or the house
    dropdown. No item menu of any kind.
  * Tapping it opens the SAME PoolTableMenuModal the house pool table
    opens (same component, same render): PLAY VS COMPUTER and
    PLAYER VS PLAYER (when the house menu has it), which open the same
    PoolGameModal (PvC) and PoolPvpModal room screen (PvP create/join,
    REJOIN, wager UI untouched inside the room screen). No menu copy.
  * The house menu also has MOVE and SELL ($25,000 back) — those are
    house-item actions for an OWNED table. In a center they would be
    wrong (SELL calls removeHouseItem on the player's OWN house table),
    so on the center path only they are hidden behind a new optional
    `hideManage` prop on PoolTableMenuModal (default false — the house
    render is byte-unchanged). The subtitle becomes "Play a game."
    If the hideManage edit cannot land, the center render still opens
    the menu with inert onMove/onSell (just close it) so nothing can
    ever be moved or sold from a center.
  * Ownership gate: the house table can only be tapped when it is
    placed in the player's own house (the tap handler only fires for
    an owned item). The center card calls setPoolMenuCenterOpen(true)
    directly with NO ownership check — the center table is placed by
    the center, not owned. The house tap handler is never touched.
  * Backend: NONE. Pool room create takes only {player_id, player_name}
    and join takes {code, player_id, player_name}; neither checks house
    ownership of a pool table (verified in backend/patch-pool-rooms.py).
    PvC needs no backend at all.

Run from /app: python3 frontend/patch-activity-center-pool-table-frontend.py
Idempotent: per-piece presence checks; a full re-run prints
ACTIVITY_CENTER_POOL_TABLE_ALREADY_APPLIED. Frontend / Expo Go only.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "ACTIVITY_CENTER_POOL_TABLE_OK"
TAG = "// ACTIVITY_CENTER_POOL_TABLE"
POOL_IMG_REQUIRE = "require('../../assets/houses/items/pool-table.jpg')"

POOL_MENU_STATE = "  const [poolMenuOpen, setPoolMenuOpen] = useState(false);"
CENTER_STATE = "  // ACTIVITY_CENTER_POOL_TABLE: center pool table opens the same play menu (no ownership).\n  const [poolMenuCenterOpen, setPoolMenuCenterOpen] = useState(false);"

MODAL_ANCHOR = "{/* ACTIVITY_CENTER interior — no menu, just who is inside. */}"
LEAVE_PRESS = "onPress={() => setActiveCenter(null)}"


def _balance(s):
    # Net balance: open minus close. Inserting balanced JSX keeps this
    # at (0, 0, 0); a broken insertion changes it.
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def _component_span(src):
    """Return (start, end) of the PoolTableMenuModal component, or None."""
    start = src.find("const PoolTableMenuModal = ({")
    if start == -1:
        return None
    pos = start
    while True:
        end = src.find("\n};\n", pos)
        if end == -1:
            return None
        span = src[start:end + 4]
        if "PLAY VS COMPUTER" in span and "CANCEL" in span:
            return (start, end + 4)
        pos = end + 4


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - center pool table NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    orig = _balance(src)
    landed = []
    warnings = []
    changed = False

    # ---- Preconditions: the house pool menu must exist to reuse. ----
    if POOL_MENU_STATE not in src:
        print("WARNING: poolMenuOpen state not found - center pool table NOT added (house pool menu missing)")
        return 1
    if "PoolTableMenuModal visible={poolMenuOpen}" not in src:
        print("WARNING: house pool menu render not found - center pool table NOT added (house pool menu missing)")
        return 1
    if "const [poolGameOpen, setPoolGameOpen]" not in src:
        print("WARNING: poolGameOpen state not found - center pool table NOT added (PvC game missing)")
        return 1
    if "PoolGameModal visible={poolGameOpen}" not in src:
        print("WARNING: pool PvC game modal render not found - center pool table NOT added (PvC game missing)")
        return 1

    # ---- Piece 1: hideManage on PoolTableMenuModal (all-or-nothing). ----
    hide_ok = False
    span = _component_span(src)
    if span is None:
        print("WARNING: PoolTableMenuModal component not found - MOVE/SELL stay visible but inert on the center path")
        warnings.append("component")
    else:
        s0, s1 = span
        body = src[s0:s1]
        new_body = body
        edits = []

        m = re.search(r"const PoolTableMenuModal = \(\{\s*([^}]*?)\s*\}:", new_body)
        if not m or "hideManage" in m.group(1):
            edits.append(("destructure", False))
        else:
            props = m.group(1).rstrip()
            new_body = new_body[:m.start(1)] + props + ", hideManage" + new_body[m.end(1):]
            edits.append(("destructure", True))

        old_type = "onSell: () => void })"
        if new_body.count(old_type) == 1:
            new_body = new_body.replace(old_type, "onSell: () => void; hideManage?: boolean })", 1)
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
            "          <TouchableOpacity onPress={onMove} style={{ backgroundColor: '#444444', paddingVertical: 12, borderRadius: 8, marginBottom: 4 }}>\n"
            "            <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>MOVE</Text>\n"
            "          </TouchableOpacity>"
        )
        move_new = (
            "          {!hideManage && (\n"
            "          <TouchableOpacity onPress={onMove} style={{ backgroundColor: '#444444', paddingVertical: 12, borderRadius: 8, marginBottom: 4 }}>\n"
            "            <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>MOVE</Text>\n"
            "          </TouchableOpacity>\n"
            "          )}"
        )
        if new_body.count(move_old) == 1:
            new_body = new_body.replace(move_old, move_new, 1)
            edits.append(("move", True))
        else:
            edits.append(("move", False))

        hint_old = "          <Text style={{ color: '#999999', fontSize: 11, textAlign: 'center', marginBottom: 12 }}>Move: close this menu, then drag the table.</Text>"
        hint_new = (
            "          {!hideManage && (\n"
            "          <Text style={{ color: '#999999', fontSize: 11, textAlign: 'center', marginBottom: 12 }}>Move: close this menu, then drag the table.</Text>\n"
            "          )}"
        )
        if new_body.count(hint_old) == 1:
            new_body = new_body.replace(hint_old, hint_new, 1)
            edits.append(("hint", True))
        else:
            edits.append(("hint", False))

        sell_old = (
            "          <TouchableOpacity onPress={onSell} style={{ backgroundColor: '#b7950b', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "            <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>SELL ($25,000 back)</Text>\n"
            "          </TouchableOpacity>"
        )
        sell_new = (
            "          {!hideManage && (\n"
            "          <TouchableOpacity onPress={onSell} style={{ backgroundColor: '#b7950b', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n"
            "            <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>SELL ($25,000 back)</Text>\n"
            "          </TouchableOpacity>\n"
            "          )}"
        )
        if new_body.count(sell_old) == 1:
            new_body = new_body.replace(sell_old, sell_new, 1)
            edits.append(("sell", True))
        else:
            edits.append(("sell", False))

        failed = [name for name, ok in edits if not ok]
        if "hideManage" in body:
            print("ACTIVITY_CENTER_POOL_TABLE_HIDEMANAGE_ALREADY_APPLIED")
            hide_ok = True
            landed.append("hidemanage")
        elif not failed:
            src = src[:s0] + new_body + src[s1:]
            changed = True
            print("ACTIVITY_CENTER_POOL_TABLE_HIDEMANAGE_OK")
            hide_ok = True
            landed.append("hidemanage")
        else:
            print("WARNING: PoolTableMenuModal hideManage edit failed (%s) - MOVE/SELL stay visible but inert on the center path" % ",".join(failed))
            warnings.append("hidemanage")

    # ---- Piece 2: center menu open state. ----
    if "const [poolMenuCenterOpen, setPoolMenuCenterOpen]" in src:
        print("ACTIVITY_CENTER_POOL_TABLE_STATE_ALREADY_APPLIED")
        landed.append("state")
    elif src.count(POOL_MENU_STATE) == 1:
        src = src.replace(POOL_MENU_STATE, POOL_MENU_STATE + "\n" + CENTER_STATE, 1)
        changed = True
        print("ACTIVITY_CENTER_POOL_TABLE_STATE_OK")
        landed.append("state")
    else:
        print("WARNING: poolMenuOpen state matched %dx - center menu state NOT added" % src.count(POOL_MENU_STATE))
        warnings.append("state")

    # ---- Piece 3: center render of the SAME PoolTableMenuModal. ----
    has_pvp_button = False
    span2 = _component_span(src)
    if span2 is not None:
        has_pvp_button = "onPlayPvp" in src[span2[0]:span2[1]]
    has_pvp_state = "const [poolPvpOpen, setPoolPvpOpen]" in src
    has_pvp_modal = "PoolPvpModal visible={poolPvpOpen}" in src
    pvp_ok = has_pvp_button and has_pvp_state and has_pvp_modal
    if not pvp_ok:
        print("NOTE: PvP room screen not fully wired in this build (button=%s state=%s modal=%s) - center menu matches the house menu without the PvP button" % (has_pvp_button, has_pvp_state, has_pvp_modal))

    if "PoolTableMenuModal visible={poolMenuCenterOpen}" in src:
        print("ACTIVITY_CENTER_POOL_TABLE_RENDER_ALREADY_APPLIED")
        landed.append("render")
    else:
        menu_lines = src.split("\n")
        house_idx = None
        for i, ln in enumerate(menu_lines):
            if "PoolTableMenuModal visible={poolMenuOpen}" in ln:
                house_idx = i
                break
        close_idx = None
        if house_idx is not None:
            for j in range(house_idx, min(len(menu_lines), house_idx + 6)):
                if menu_lines[j].strip() == ") : null}":
                    close_idx = j
                    break
        if house_idx is None or close_idx is None:
            print("WARNING: house pool menu render close not found - center menu render NOT added")
            warnings.append("render")
        else:
            pvp_prop = " onPlayPvp={() => { setPoolMenuCenterOpen(false); setPoolPvpOpen(true); }}" if pvp_ok else ""
            hide_prop = " hideManage" if hide_ok else ""
            render_block = (
                "      {poolMenuCenterOpen ? (\n"
                "        <PoolTableMenuModal visible={poolMenuCenterOpen} onClose={() => setPoolMenuCenterOpen(false)}"
                " onPlayPvc={() => { setPoolMenuCenterOpen(false); setPoolGameOpen(true); }}" + pvp_prop +
                " onMove={() => setPoolMenuCenterOpen(false)} onSell={() => setPoolMenuCenterOpen(false)}" + hide_prop + " />\n"
                "      ) : null}"
            )
            menu_lines = menu_lines[:close_idx + 1] + [render_block] + menu_lines[close_idx + 1:]
            src = "\n".join(menu_lines)
            changed = True
            print("ACTIVITY_CENTER_POOL_TABLE_RENDER_OK")
            landed.append("render")

    # ---- Piece 4: pool table fixture card in the center interior modal. ----
    if "setPoolMenuCenterOpen(true)" in src:
        print("ACTIVITY_CENTER_POOL_TABLE_CARD_ALREADY_APPLIED")
        landed.append("card")
    elif MODAL_ANCHOR not in src:
        print("WARNING: activity center interior modal not found - pool table card NOT added")
        warnings.append("card")
    elif src.count(LEAVE_PRESS) != 1:
        print("WARNING: center LEAVE button matched %dx - pool table card NOT added" % src.count(LEAVE_PRESS))
        warnings.append("card")
    else:
        if POOL_IMG_REQUIRE in src:
            art = "              <Image source={require('../../assets/houses/items/pool-table.jpg')} style={{ width: 200, height: 100, borderRadius: 8 }} resizeMode=\"cover\" />\n"
        else:
            art = "              <Text style={{ fontSize: 44 }}>🎱</Text>\n"
        card = (
            "            <TouchableOpacity\n"
            "              style={{ marginTop: 20, backgroundColor: '#1b5e20', borderRadius: 12, padding: 12, alignItems: 'center', borderWidth: 2, borderColor: '#8d5a2b' }}\n"
            "              onPress={() => setPoolMenuCenterOpen(true)}\n"
            "            >\n"
            + art +
            "              <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16, marginTop: 8 }}>🎱 POOL TABLE — TAP TO PLAY</Text>\n"
            "            </TouchableOpacity>\n"
        )
        press_idx = src.find(LEAVE_PRESS)
        t_start = src.rfind("<TouchableOpacity", 0, press_idx)
        line_start = src.rfind("\n", 0, t_start) + 1
        src = src[:line_start] + card + src[line_start:]
        changed = True
        print("ACTIVITY_CENTER_POOL_TABLE_CARD_OK")
        landed.append("card")

    if _balance(src) != orig:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    if not landed:
        print("ACTIVITY_CENTER_POOL_TABLE_PARTIAL: nothing landed")
        return 1
    if not changed:
        print("ACTIVITY_CENTER_POOL_TABLE_ALREADY_APPLIED")
        return 0
    IDX.write_text(src)
    if warnings:
        print("ACTIVITY_CENTER_POOL_TABLE_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
