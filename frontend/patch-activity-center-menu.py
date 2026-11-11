#!/usr/bin/env python3
"""Street Legends frontend: Activity Center menu redesign (park-style).

User (2026-11-10 23:30 EST): "Better yet change the activity centers.
take away the items and make a menu like the park and use the items as
the icons."

What this does (frontend only, Expo Go first):
  * Removes the hall scene: the horizontal ScrollView with the hall
    picture and the 7 draggable fixture Views (pool, dartboard, card
    table, dominoes, Scrabble, chess & checkers, Pop Shot cabinet) is
    replaced by a vertical menu ScrollView, mirroring the park's
    PLAYABLE ACTIVITIES section exactly (dark-green rows, gold border,
    gold TAP TO PLAY pill, "More activities coming soon" card).
  * Each menu row uses the item's own picture as its icon (the same
    house-item picture the hall used, resolved from HOUSE_ITEMS the
    same way the fixture patches resolved it) — 56x56, contain.
  * Tapping a row opens the SAME play menu the fixture tap opened
    (setPoolMenuCenterOpen / setDartMenuCenterOpen /
    setCardMenuCenterOpen / setDominoMenuCenterOpen /
    setScrabbleMenuCenterOpen / setChessMenuCenterOpen /
    setPopShotCenterOpen). The game modals themselves are untouched.
  * The hold-to-arrange hint and the arrange message go away (no more
    dragging). The drag responders / position state stay in the file
    as dead code (harmless, untouched) — only the hall render is
    removed. The backend layout endpoint and saved layouts are
    untouched (they simply stop being rendered).
  * Matches the park chrome: root background #000000 -> #0d1f12
    (park dark green), adds "Your cash" under the subtitle (park has
    it), LEAVE purple #7b1fa2 -> pink #E91E63 (park LEAVE).

Run from /app: python3 frontend/patch-activity-center-menu.py
Frontend only: reload Expo Go to check; Deploy after.
Idempotent: a full re-run prints ACTIVITY_CENTER_MENU_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
from pathlib import Path

IDX = Path("frontend/app/(tabs)/index.tsx")
if not IDX.exists():
    IDX = Path("frontend/app/index.tsx")
MARKER = "ACTIVITY_CENTER_MENU_OK"

HINT_7 = "Hold the pool table, dartboard, card table, dominoes table, Scrabble table, chess and checkers table, or Pop Shot cabinet to move it \u2014 swipe the room to look around."

# Canonical asset requires (resolved from HOUSE_ITEMS first, same as the
# fixture patches; the Pop Shot cabinet is a fixed .png).
POOL_PNG = "require('../../assets/houses/items/pool-table.png')"
POOL_JPG = "require('../../assets/houses/items/pool-table.jpg')"
DART_PNG = "require('../../assets/houses/items/dartboard.png')"
DART_JPG = "require('../../assets/houses/items/dartboard.jpg')"
CARD_PNG = "require('../../assets/houses/items/cardtable.png')"
CARD_JPG = "require('../../assets/houses/items/cardtable.jpg')"
DOM_PNG = "require('../../assets/houses/items/dominoes.png')"
DOM_JPG = "require('../../assets/houses/items/dominoes.jpg')"
SCR_PNG = "require('../../assets/houses/items/scrabble.png')"
SCR_JPG = "require('../../assets/houses/items/scrabble.jpg')"
CC_PNG = "require('../../assets/houses/items/chess-checkers.png')"
CC_JPG = "require('../../assets/houses/items/chess-checkers.jpg')"
PS_CABINET = "require('../../assets/activity-center/pop-shot-cabinet.png')"


def _resolve_art(src, root, item_id, stem, png_req, jpg_req):
    """Item picture require, in fallback order (same as fixture patches)."""
    m = re.search(r"id:\s*'" + re.escape(item_id) + r"'[^}]*?image:\s*(require\([^)]+\))", src)
    if m:
        return m.group(1), "house-items-entry"
    m = re.search(r"require\(['\"][^'\"]*" + re.escape(stem) + r"\.png['\"]\)", src)
    if m:
        return m.group(0), "png-require-in-index"
    m = re.search(r"require\(['\"][^'\"]*" + re.escape(stem) + r"\.jpg['\"]\)", src)
    if m:
        return m.group(0), "jpg-require-in-index"
    if (root / ("frontend/assets/houses/items/" + stem + ".png")).exists():
        return png_req, "asset-file-png"
    if (root / ("frontend/assets/houses/items/" + stem + ".jpg")).exists():
        return jpg_req, "asset-file-jpg"
    return png_req, "canonical-path"


def _row(req, name, desc, opener):
    return """            <TouchableOpacity
              onPress={() => %s(true)}
              style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#f5c518', borderRadius: 12, padding: 14, marginBottom: 10 }}
            >
              <Image source={%s} style={{ width: 56, height: 56, borderRadius: 8 }} resizeMode="contain" />
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>%s</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>%s</Text>
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>TAP TO PLAY</Text>
            </TouchableOpacity>""" % (opener, req, name, desc)


def _menu_scroll(rows):
    soon = """            <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#2d7a44', borderRadius: 12, padding: 14, opacity: 0.55 }}>
              <Text style={{ fontSize: 30 }}>🌳</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>More activities coming soon</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>New games will show up here</Text>
              </View>
              <Text style={{ backgroundColor: '#555', color: '#ddd', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>SOON</Text>
            </View>"""
    body = "\n".join(rows) + "\n" + soon
    return """          {/* ACTIVITY_CENTER_MENU: park-style menu — the items are the icons. */}
          <ScrollView
            style={{ flex: 1 }}
            showsVerticalScrollIndicator={false}
          >
            <View style={{ padding: 12, paddingBottom: 4 }}>
              <Text style={{ fontSize: 17, fontWeight: 'bold', color: '#f5c518', letterSpacing: 1, marginBottom: 8 }}>PLAYABLE ACTIVITIES</Text>
%s
            </View>
          </ScrollView>""" % body


def _balance(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def main():
    root = Path(".")
    if not IDX.exists():
        print("WARNING: index.tsx not found - center menu NOT added")
        return 1
    src = IDX.read_text(encoding="utf-8", errors="ignore")
    orig = src
    landed = []
    warnings = []

    # ---- Idempotency: the menu already replaced the hall. ----
    if MARKER in src:
        print("ACTIVITY_CENTER_MENU_ALREADY_APPLIED")
        return 0
    if "ACTIVITY_CENTER_MENU: park-style menu" in src:
        print("ACTIVITY_CENTER_MENU_ALREADY_APPLIED")
        return 0

    # ---- Locate the center modal span. ----
    m0 = src.find("<Modal visible={!!activeCenter}")
    if m0 == -1:
        print("WARNING: center modal not found - menu NOT added")
        return 1
    # The modal's close is the first </Modal> after the open.
    m1 = src.find("</Modal>", m0)
    if m1 == -1:
        print("WARNING: center modal close not found - menu NOT added")
        return 1
    modal = src[m0:m1]

    # ---- Preconditions (probe, print only). ----
    for setter in ("setPoolMenuCenterOpen", "setDartMenuCenterOpen",
                   "setCardMenuCenterOpen", "setDominoMenuCenterOpen",
                   "setScrabbleMenuCenterOpen", "setChessMenuCenterOpen",
                   "setPopShotCenterOpen"):
        if setter not in src:
            print("WARNING: %s not found - its menu row will not open" % setter)
            warnings.append(setter)
    if "scrollEnabled={centerSceneScrollEnabled}" not in modal:
        print("WARNING: hall ScrollView anchor not found in center modal - menu NOT added")
        return 1

    # ---- Resolve the 7 item pictures (same as the fixture patches). ----
    art = {}
    art["pool"], s1 = _resolve_art(src, root, "pool-table", "pool-table", POOL_PNG, POOL_JPG)
    art["dart"], s2 = _resolve_art(src, root, "dartboard", "dartboard", DART_PNG, DART_JPG)
    art["card"], s3 = _resolve_art(src, root, "cardtable", "cardtable", CARD_PNG, CARD_JPG)
    art["dom"], s4 = _resolve_art(src, root, "dominoes", "dominoes", DOM_PNG, DOM_JPG)
    art["scr"], s5 = _resolve_art(src, root, "scrabble", "scrabble", SCR_PNG, SCR_JPG)
    art["chess"], s6 = _resolve_art(src, root, "chess_checkers", "chess-checkers", CC_PNG, CC_JPG)
    art["pop"] = PS_CABINET
    print("OK: art resolved pool=%s dart=%s card=%s dom=%s scr=%s chess=%s pop=cabinet-png"
          % (s1, s2, s3, s4, s5, s6))

    rows = [
        _row(art["pool"], "Pool", "8-ball \u2022 You vs CPU or a friend", "setPoolMenuCenterOpen"),
        _row(art["dart"], "Dartboard", "Darts \u2022 You vs CPU or a friend", "setDartMenuCenterOpen"),
        _row(art["card"], "Card Table", "Spades & Gin Rummy \u2022 You vs CPU or a friend", "setCardMenuCenterOpen"),
        _row(art["dom"], "Dominoes", "Dominoes \u2022 You vs CPU or a friend", "setDominoMenuCenterOpen"),
        _row(art["scr"], "Scrabble", "Scrabble \u2022 You vs CPU or a friend", "setScrabbleMenuCenterOpen"),
        _row(art["chess"], "Chess & Checkers", "Chess & Checkers \u2022 You vs CPU or a friend", "setChessMenuCenterOpen"),
        _row(art["pop"], "Pop Shot", "Arcade basketball \u2022 60 seconds \u2022 Solo", "setPopShotCenterOpen"),
    ]
    menu = _menu_scroll(rows)

    # ---- 1. Replace the hall ScrollView with the menu ScrollView. ----
    anchor = modal.find("scrollEnabled={centerSceneScrollEnabled}")
    sv_start = modal.rfind("<ScrollView", 0, anchor)
    sv_end = modal.find("</ScrollView>", anchor)
    if sv_start == -1 or sv_end == -1:
        print("WARNING: hall ScrollView span not found - menu NOT added")
        return 1
    sv_end += len("</ScrollView>")
    modal = modal[:sv_start] + menu + modal[sv_end:]
    print("OK: hall scene replaced by park-style menu")
    landed.append("menu")

    # ---- 2. Remove the hold-to-arrange hint (dragging is gone). ----
    if HINT_7 in modal:
        # The hint sits inside a Veno-only conditional block; remove the
        # whole block (from the "{playerId === CENTER_ARRANGE_OWNER_ID"
        # line through its closing ")}").
        h = modal.find(HINT_7)
        b_start = modal.rfind("{playerId === CENTER_ARRANGE_OWNER_ID", 0, h)
        b_end = modal.find(")}", h)
        if b_start != -1 and b_end != -1:
            modal = modal[:b_start] + modal[b_end + 2:]
            print("OK: hold-to-arrange hint removed")
            landed.append("hint")
        else:
            print("WARNING: hint block boundaries not found - hint NOT removed")
            warnings.append("hint")
    else:
        print("NOTE: hold hint already absent")

    # ---- 3. Remove the arrange-message display line. ----
    am = modal.find("{centerArrangeMsg ?")
    if am != -1:
        am_end = modal.find(") : null}", am)
        if am_end != -1:
            modal = modal[:am] + modal[am_end + len(") : null}"):]
            print("OK: arrange message line removed")
            landed.append("arrangemsg")
        else:
            print("WARNING: arrange message line end not found")
            warnings.append("arrangemsg")
    else:
        print("NOTE: arrange message line already absent")

    # ---- 4. Root background black -> park dark green. ----
    if "backgroundColor: '#000000'" in modal:
        modal = modal.replace("backgroundColor: '#000000'", "backgroundColor: '#0d1f12'", 1)
        print("OK: root background -> park dark green")
        landed.append("bg")
    else:
        print("NOTE: root background already not black")

    # ---- 5. Add "Your cash" under the subtitle (park has it). ----
    sub = "<Text style={{ fontSize: 14, color: '#e0e0e0', marginTop: 4 }}>Activity Center</Text>"
    if "Your cash:" not in modal and sub in modal:
        cash = sub + "\n            <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#fff', marginTop: 16 }}>Your cash: ${(player?.cash || 0).toLocaleString()}</Text>"
        modal = modal.replace(sub, cash, 1)
        print("OK: Your cash line added")
        landed.append("cash")
    else:
        print("NOTE: Your cash already present or subtitle anchor missing")

    # ---- 6. LEAVE purple -> park pink. ----
    leave_old = "style={{ marginTop: 32, backgroundColor: '#7b1fa2', padding: 14, borderRadius: 10, alignItems: 'center' }}"
    leave_new = "style={{ margin: 16, marginTop: 8, backgroundColor: '#E91E63', padding: 14, borderRadius: 10, alignItems: 'center' }}"
    if leave_old in modal:
        modal = modal.replace(leave_old, leave_new, 1)
        print("OK: LEAVE -> park pink")
        landed.append("leave")
    else:
        print("NOTE: LEAVE style already changed or anchor missing")

    # ---- Write back + marker. ----
    src = src[:m0] + modal + src[m1:]
    # Marker comment, placed right before the menu ScrollView.
    src = src.replace("          {/* ACTIVITY_CENTER_MENU: park-style menu",
                      "          {/* " + MARKER + " — ACTIVITY_CENTER_MENU: park-style menu", 1)

    # ---- Safety checks. ----
    if _balance(orig) != _balance(src):
        print("WARNING: bracket balance changed - inspect before Deploy")
        warnings.append("balance")
    for setter in ("setPoolMenuCenterOpen", "setDartMenuCenterOpen",
                   "setCardMenuCenterOpen", "setDominoMenuCenterOpen",
                   "setScrabbleMenuCenterOpen", "setChessMenuCenterOpen",
                   "setPopShotCenterOpen"):
        if (setter + "(true)") not in src:
            print("WARNING: menu row for %s missing" % setter)
            warnings.append(setter)
    if "centerSceneScrollEnabled" in src and "scrollEnabled={centerSceneScrollEnabled}" in src:
        print("WARNING: hall ScrollView still present - menu did not replace it")
        return 1
    if HINT_7 in src:
        print("WARNING: hold hint still present")
        warnings.append("hint-left")

    tmp = tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        # TSX is not Python: validate by bracket balance only (the
        # _balance check above) plus the targeted presence checks.
    except Exception as e:
        print("WRITE_FAIL: %s (index.tsx NOT written)" % e)
        return 1
    IDX.write_text(src, encoding="utf-8")
    if warnings:
        print("ACTIVITY_CENTER_MENU_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warnings) + ")")
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
