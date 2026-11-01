#!/usr/bin/env python3
"""Street Legends frontend v2: MOVE button next to YOUR HOUSE, wherever
that button actually lives.

Why v2: v1 only looked in frontend/app/(tabs)/shop.tsx and required a
myHouse state, so its MOVE step never landed in the shop Expo Go
serves (the button evidently lives in a different file or under a
different state name). v2 finds the button instead of assuming it.

What v2 does (every step guarded; a missed anchor SKIPs that step
instead of breaking the build):
  1. Search frontend/app/**/*.tsx + frontend/components/*.tsx for
     "YOUR HOUSE". The first file with a match is the button file.
  2. Find the button block enclosing that line: scan back (up to 25
     lines) for the nearest JSX tag with an onPress prop (any
     component, not just TouchableOpacity/Pressable), then find its
     matching close tag by name + nesting count (or a self-closing
     "/>" on the same tag). If none is found, WARNING + stop.
  3. House id in scope: if the button sits inside a .map((h) =>
     (or house/item) use that variable's .id; else myHouse.id,
     ownedHouse.id, or playerHouse.id if one exists in the file.
     If none is found, WARNING + stop (guessing would break it).
     playerId must also appear in the file, else WARNING + stop.
  4. Wrap the button block in a row View (flexDirection row, gap 10)
     with the original button in a flex:1 View and a MOVE button in
     another flex:1 View, right next to it, equal width. If the
     YOUR HOUSE text sits in a ternary (shared BUY/YOUR HOUSE
     button), MOVE renders only under the same owned condition when
     that condition can be read off the ternary; otherwise MOVE
     renders always but its handler guards on the owned house
     existing (so tapping it on a BUY card just says no house).
  5. Ensure moveHouseToInventory is imported in the button file
     (dedupe: only names missing from that import line are added,
     so the v1 duplicate-import Deploy failure cannot recur).
     Ensure Alert is imported there too.
  6. Ensure the INVENTORY section + PLACE HERE exist in the shop tab
     file (the file with HOUSES.map; usually the same file as the
     button, otherwise the tab screen itself), so after MOVE there
     is always a PLACE HERE path and never a re-BUY trap. Uses the
     Oct 29 shop anchors, guarded.

The backend for MOVE is already live (move-to-inventory / inventory /
place), so this is FRONTEND ONLY (Expo Go reload to check).

Run from repo root: python3 frontend/patch-house-shop-move-button-v2.py
Idempotent - safe to re-run.
"""
import glob
import re
import sys
from pathlib import Path

API = Path("frontend/services/api.ts")

API_FUNCS = """
export const moveHouseToInventory = async (houseId: string, playerId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/move-to-inventory`, { player_id: playerId });
  return response.data;
};

export const getInventoryHouses = async (playerId: string): Promise<any> => {
  const response = await api.get(`/houses/inventory/${playerId}`);
  return response.data.houses || [];
};

export const placeHouse = async (houseId: string, playerId: string, latitude: number, longitude: number): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/place`, { player_id: playerId, latitude, longitude });
  return response.data;
};
"""

SHOP_STATE_OLD = "  const [myHouse, setMyHouse] = useState<any | null>(null);"
SHOP_STATE_NEW = "  const [myHouse, setMyHouse] = useState<any | null>(null);\n  const [inventoryHouses, setInventoryHouses] = useState<any[]>([]);\n  const [placingHouse, setPlacingHouse] = useState<string | null>(null);"
SHOP_LOAD_OLD = "        try { const h = await getPlayerHouse(playerId); setMyHouse(h); } catch (_) {}"
SHOP_LOAD_NEW = "        try { const h = await getPlayerHouse(playerId); setMyHouse(h); } catch (_) {}\n        try { const inv = await getInventoryHouses(playerId); setInventoryHouses(inv || []); } catch (_) {}"
PLACE_HANDLER = """  const handlePlaceHouse = (h: any) => {
    if (!playerId || !player?.position) {
      Alert.alert('Place House', 'Your location is not available yet.');
      return;
    }
    Alert.alert('Place House?', `Drop ${h.name} right where you are standing?`, [
      { text: 'Not Yet', style: 'cancel' },
      { text: 'Place It', onPress: async () => {
        setPlacingHouse(h.id);
        try {
          const res = await placeHouse(h.id, playerId, player.position.latitude, player.position.longitude);
          setMyHouse(res.house);
          setInventoryHouses((prev) => prev.filter((x) => x.id !== h.id));
          Alert.alert('House Placed', `${h.name} is now on the map where you stand.`);
        } catch (e: any) {
          Alert.alert('Place Failed', e?.response?.data?.detail || e?.message || 'Could not place house.');
        } finally {
          setPlacingHouse(null);
        }
      } },
    ]);
  };

"""
BUY_HANDLER_ANCHOR = "  const handleBuyHouse = (h: typeof HOUSES[0]) => {"
INVENTORY_SECTION = """          {inventoryHouses.length > 0 && (
            <View style={{ marginBottom: 16 }}>
              <Text style={{ color: '#f39c12', fontWeight: '800', fontSize: 14, marginBottom: 8 }}>YOUR INVENTORY — PLACE IT WHERE YOU STAND</Text>
              {inventoryHouses.map((h: any) => {
                const img = HOUSES.find((x) => x.tier === h.tier)?.image;
                return (
                  <View key={h.id} style={HOUSE_STYLES.houseCard}>
                    {img ? (<Image source={img} style={HOUSE_STYLES.houseImage} />) : null}
                    <View style={HOUSE_STYLES.houseInfo}>
                      <Text style={HOUSE_STYLES.houseName}>{h.name}</Text>
                      <Text style={HOUSE_STYLES.houseBlurb}>In your inventory — {h.items?.length || 0}/{h.item_limit || 6} items inside.</Text>
                      <TouchableOpacity
                        style={[HOUSE_STYLES.houseBuyBtn, placingHouse === h.id && HOUSE_STYLES.houseBuyBtnDisabled]}
                        disabled={placingHouse === h.id}
                        onPress={() => handlePlaceHouse(h)}
                      >
                        {placingHouse === h.id ? (
                          <ActivityIndicator size="small" color="#fff" />
                        ) : (
                          <Text style={HOUSE_STYLES.houseBuyText}>PLACE HERE</Text>
                        )}
                      </TouchableOpacity>
                    </View>
                  </View>
                );
              })}
            </View>
          )}
"""
HOUSES_MAP_ANCHOR = "          {HOUSES.map((h) => {"


def find_files_with(text):
    out = []
    for path in sorted(glob.glob("frontend/app/**/*.tsx", recursive=True) +
                       glob.glob("frontend/components/*.tsx")):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                if text in f.read():
                    out.append(path)
        except FileNotFoundError:
            pass
    return out


def find_button_block(lines, text_idx):
    """Find the JSX element with onPress enclosing lines[text_idx].
    Returns (start, end, tag) or None. Handles self-closing tags."""
    for i in range(text_idx, max(-1, text_idx - 25), -1):
        m = re.search(r"<([A-Za-z][A-Za-z0-9.]*)[^>]*\bonPress\b", lines[i])
        if not m:
            continue
        tag = m.group(1)
        # Self-closing on the same line (or within the tag if it spans lines).
        chunk = "\n".join(lines[i:text_idx + 1])
        if re.search(r"<" + re.escape(tag) + r"[^>]*\/>", chunk):
            return (i, i, tag)
        depth = 0
        for j in range(i, len(lines)):
            depth += len(re.findall(r"<" + re.escape(tag) + r"(?=[\s>])", lines[j]))
            depth -= len(re.findall(r"</" + re.escape(tag) + r">", lines[j]))
            if depth <= 0 and j > i:
                return (i, j, tag)
    return None


def house_id_expr(lines, text_idx, src):
    """House id expression in scope at the YOUR HOUSE button."""
    window = "\n".join(lines[max(0, text_idx - 60):text_idx + 1])
    m = re.search(r"\.map\(\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*=>", window)
    if m:
        return m.group(1) + ".id"
    for name in ("myHouse", "ownedHouse", "playerHouse"):
        if name in src:
            return name + ".id"
    # A card component that receives the house as a prop, possibly aliased
    # (e.g. const h = house, or destructured { house }).
    m2 = re.search(r"const\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*house\b", src)
    if m2:
        return m2.group(1) + ".id"
    if re.search(r"\bhouse\b", src):
        return "house.id"
    return None


def ternary_condition(line):
    """Owned condition if YOUR HOUSE sits in a ternary on this line."""
    m = re.search(r"\b([A-Za-z_][A-Za-z0-9_.]*)\s*\?\s*['\"]YOUR HOUSE['\"]", line)
    if m:
        return m.group(1)
    return None


def ensure_api_imports(src, path):
    """Add missing move/inventory/place names to the services/api import (dedupe)."""
    if "moveHouseToInventory" in src and "getInventoryHouses" in src and "placeHouse" in src:
        print("SKIP: api imports already complete in %s" % path)
        return src, True
    m = re.search(r"\} from '../../services/api';", src)
    if not m:
        # Try a looser services/api import (different relative depth).
        m = re.search(r"\} from '[^']*services/api';", src)
    if not m:
        print("WARNING: no services/api import found in %s" % path)
        return src, False
    ins = m.start()
    already = src[:ins]
    missing = [n for n in ("moveHouseToInventory", "getInventoryHouses", "placeHouse") if n not in already]
    if missing:
        src = src[:ins] + ", " + ", ".join(missing) + " " + src[ins:]
        print("OK: api imports added to %s (missing only: %s)" % (path, ", ".join(missing)))
    else:
        print("SKIP: api imports already complete in %s" % path)
    return src, True


def main():
    # 0. api.ts functions (anchor-free append).
    if not API.exists():
        print("ERROR: %s not found. Run from repo root." % API)
        return 1
    api = API.read_text()
    if "export const moveHouseToInventory" in api and "export const placeHouse" in api:
        print("SKIP: move/place api functions already present")
    else:
        if not api.endswith("\n"):
            api += "\n"
        api += API_FUNCS + "\n"
        API.write_text(api)
        print("OK: move/place api functions appended")

    # 1. Find the YOUR HOUSE button file.
    btn_files = find_files_with("YOUR HOUSE")
    if not btn_files:
        print("WARNING: no file containing YOUR HOUSE found under frontend/app or frontend/components")
        print("HOUSE_SHOP_MOVE_BUTTON_V2_WARNING: YOUR HOUSE not found anywhere")
        return 0
    btn_path = btn_files[0]
    print("OK: YOUR HOUSE found in %s" % btn_path)
    src = Path(btn_path).read_text()
    lines = src.split("\n")
    yh = [i for i, ln in enumerate(lines) if "YOUR HOUSE" in ln]
    text_idx = yh[0]
    print("OK: YOUR HOUSE at %s line %d" % (btn_path, text_idx + 1))

    # 2. Button block.
    blk = find_button_block(lines, text_idx)
    if not blk:
        print("WARNING: no onPress button block enclosing YOUR HOUSE (checked 25 lines above)")
        print("HOUSE_SHOP_MOVE_BUTTON_V2_WARNING: button block not found in %s" % btn_path)
        return 0
    start, end, tag = blk
    print("OK: button block %s lines %d-%d" % (tag, start + 1, end + 1))

    # 3. House id + playerId in scope.
    hid = house_id_expr(lines, text_idx, src)
    if not hid:
        print("WARNING: no house id in scope (no .map variable, myHouse, ownedHouse, or playerHouse)")
        print("HOUSE_SHOP_MOVE_BUTTON_V2_WARNING: house id not found in %s" % btn_path)
        return 0
    if "playerId" not in src:
        print("WARNING: playerId not in %s" % btn_path)
        print("HOUSE_SHOP_MOVE_BUTTON_V2_WARNING: playerId not found in %s" % btn_path)
        return 0
    print("OK: house id expression %s" % hid)

    # 4. Imports in the button file (dedupe) + Alert.
    src, ok = ensure_api_imports(src, btn_path)
    if not ok:
        print("HOUSE_SHOP_MOVE_BUTTON_V2_WARNING: api import missing in %s" % btn_path)
        return 0
    if "Alert" not in src:
        m2 = re.search(r"from 'react-native';", src)
        if m2:
            src = src[:m2.end()] + "\nimport { Alert } from 'react-native';" + src[m2.end():]
            print("OK: Alert import added to %s" % btn_path)
    lines = src.split("\n")
    # Re-locate after the import edits (line numbers may have shifted).
    yh = [i for i, ln in enumerate(lines) if "YOUR HOUSE" in ln]
    text_idx = yh[0]
    blk = find_button_block(lines, text_idx)
    if not blk:
        print("WARNING: button block lost after import edits (should not happen)")
        print("HOUSE_SHOP_MOVE_BUTTON_V2_WARNING: button block lost")
        return 0
    start, end, tag = blk
    cond = ternary_condition(lines[text_idx])
    if cond:
        print("OK: YOUR HOUSE is conditional on %s; MOVE renders under the same condition" % cond)

    # 5. Row wrap + MOVE next to the button (skip if already present).
    if "moveHouseToInventory(" in src and ">MOVE<" in src:
        print("SKIP: MOVE button already present in %s" % btn_path)
        Path(btn_path).write_text(src)
        print("HOUSE_SHOP_MOVE_BUTTON_V2_OK")
        return 0
    indent = lines[start][:len(lines[start]) - len(lines[start].lstrip())]
    orig = lines[start:end + 1]
    move_lines = [
        indent + "  <View style={{ flex: 1 }}>",
        indent + "    <TouchableOpacity",
        indent + "      style={{ backgroundColor: '#1e88e5', paddingVertical: 12, borderRadius: 8, alignItems: 'center' }}",
        indent + "      onPress={() => {",
        indent + "        if (!(%s) || !playerId) { Alert.alert('Move House', 'No house to move.'); return; }" % hid,
        indent + "        Alert.alert('Move House?', `Your house will go into your inventory. You can place it again anytime from the Shop House tab.`, [",
        indent + "          { text: 'Keep It Here', style: 'cancel' },",
        indent + "          { text: 'Move', onPress: async () => {",
        indent + "            try {",
        indent + "              await moveHouseToInventory(%s, playerId);" % hid,
        indent + "              Alert.alert('House Moved', 'Your house is in your inventory. Place it again from the INVENTORY section in the Shop House tab.');",
        indent + "            } catch (err: any) {",
        indent + "              Alert.alert('Move Failed', err?.response?.data?.detail || err?.message || 'Could not move house.');",
        indent + "            }",
        indent + "          } },",
        indent + "        ]);",
        indent + "      }}",
        indent + "    >",
        indent + "      <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>MOVE</Text>",
        indent + "    </TouchableOpacity>",
        indent + "  </View>",
    ]
    if cond:
        # MOVE only renders when owned; when it is null, the original
        # button's flex:1 View takes the full row width (no BUY
        # regression), and when owned both flex:1 share it evenly.
        move_lines = (
            [indent + "  {%s ? (" % cond]
            + move_lines
            + [indent + "  ) : null}"]
        )
    wrapped = (
        [indent + "<View style={{ flexDirection: 'row', gap: 10 }}>",
         indent + "  <View style={{ flex: 1 }}>"]
        + ["  " + ln for ln in orig]
        + [indent + "  </View>"]
        + move_lines
        + [indent + "</View>"]
    )
    lines[start:end + 1] = wrapped
    src = "\n".join(lines)
    Path(btn_path).write_text(src)
    print("OK: MOVE button added right next to YOUR HOUSE in %s" % btn_path)

    # 6. INVENTORY section + PLACE in the shop tab file (HOUSES.map).
    tab_files = find_files_with("HOUSES.map")
    tab_path = tab_files[0] if tab_files else btn_path
    tab_src = Path(tab_path).read_text()
    if "handlePlaceHouse" in tab_src and "YOUR INVENTORY" in tab_src:
        print("SKIP: INVENTORY section already present in %s" % tab_path)
    else:
        changed = False
        if tab_src.count(SHOP_STATE_OLD) == 1:
            tab_src = tab_src.replace(SHOP_STATE_OLD, SHOP_STATE_NEW, 1)
            print("OK: inventory + placing state added to %s" % tab_path)
            changed = True
        if tab_src.count(SHOP_LOAD_OLD) == 1:
            tab_src = tab_src.replace(SHOP_LOAD_OLD, SHOP_LOAD_NEW, 1)
            print("OK: inventory loaded with %s" % tab_path)
            changed = True
        if BUY_HANDLER_ANCHOR in tab_src and "handlePlaceHouse" not in tab_src:
            tab_src = tab_src.replace(BUY_HANDLER_ANCHOR, PLACE_HANDLER + BUY_HANDLER_ANCHOR, 1)
            print("OK: handlePlaceHouse added to %s" % tab_path)
            changed = True
        if tab_src.count(HOUSES_MAP_ANCHOR) == 1:
            tab_src = tab_src.replace(HOUSES_MAP_ANCHOR, INVENTORY_SECTION + HOUSES_MAP_ANCHOR, 1)
            print("OK: INVENTORY section added to %s" % tab_path)
            changed = True
        else:
            print("WARNING: HOUSES.map anchor matched %dx in %s" % (tab_src.count(HOUSES_MAP_ANCHOR), tab_path))
        if changed:
            Path(tab_path).write_text(tab_src)
    print("HOUSE_SHOP_MOVE_BUTTON_V2_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
