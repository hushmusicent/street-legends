#!/usr/bin/env python3
"""Street Legends frontend: MOVE button next to YOUR HOUSE in the Shop.

User 2026-11-01: in the Shop House tab, on the house they own, right
next to YOUR HOUSE, so people can move their house if they forgot
where they placed it (tapping the map marker is impossible then).

The backend for this is ALREADY LIVE (verified 2026-11-01: GET
/api/houses/inventory/<player> returns {"houses":[]}):
  POST /houses/{house_id}/move-to-inventory {player_id} -> stored=True
  GET  /houses/inventory/{player_id} -> stored houses
  POST /houses/{house_id}/place {player_id, latitude, longitude}
So this patch is FRONTEND ONLY (Expo Go reload to check, no Deploy).

What it does in shop.tsx (every step guarded, so a missed anchor
SKIPs that step instead of breaking the build):
  1. api.ts: ensure moveHouseToInventory / getInventoryHouses /
     placeHouse exist (appended anchor-free if missing).
  2. Shop imports: ensure moveHouseToInventory + getInventoryHouses +
     placeHouse are imported (exact anchor, else a loose fallback that
     inserts the names into the services/api import braces).
  3. Shop state/load/place-handler/INVENTORY section: the Oct 29 shop
     changes, so after MOVE the shop shows INVENTORY + PLACE HERE
     instead of offering BUY again (re-buying would delete the stored
     house, so the inventory section MUST exist before MOVE is safe).
  4. NEW: the YOUR HOUSE button block is wrapped in a row View with a
     MOVE button right next to it (side by side, equal width). MOVE
     asks first ("Move House? ... will go into your inventory..."),
     then calls moveHouseToInventory(myHouse.id, playerId), clears
     myHouse, and reloads the inventory so PLACE HERE appears.
     Guarded on myHouse existing in the file: if the shop has no
     myHouse state, MOVE is SKIPPED (it would reference an undefined
     variable and break the build).

Run from repo root: python3 frontend/patch-house-shop-move-button.py
Idempotent - safe to re-run.
"""
import re
import sys
from pathlib import Path

SHOP = Path("frontend/app/(tabs)/shop.tsx")
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

SHOP_IMPORT_OLD = "buyHouse, getPlayerHouse } from '../../services/api';"
SHOP_IMPORT_NEW = "buyHouse, getPlayerHouse, getInventoryHouses, placeHouse, moveHouseToInventory } from '../../services/api';"
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


def find_button_block(lines, text_idx):
    """Find the TouchableOpacity/Pressable block enclosing lines[text_idx].
    Returns (start, end, tag) line indices (end inclusive) or None."""
    for tag in ("TouchableOpacity", "Pressable"):
        start = None
        for i in range(text_idx, max(-1, text_idx - 15), -1):
            if ("<" + tag) in lines[i]:
                start = i
                break
        if start is None:
            continue
        depth = 0
        for j in range(start, len(lines)):
            depth += lines[j].count("<" + tag)
            depth -= lines[j].count("</" + tag + ">")
            if depth <= 0 and j > start:
                return (start, j, tag)
            if depth <= 0 and j == start and ("</" + tag + ">") in lines[j]:
                return (start, j, tag)
    return None


def main():
    # 1. api.ts functions (anchor-free append, like the Oct 29 patch).
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

    # 2-4. shop.tsx.
    if not SHOP.exists():
        print("ERROR: %s not found. Run from repo root." % SHOP)
        return 1
    shop = SHOP.read_text()
    # Imports (exact anchor, else loose fallback into the api import braces).
    if "moveHouseToInventory" in shop and "getInventoryHouses" in shop:
        print("SKIP: shop move/inventory api already imported")
    elif shop.count(SHOP_IMPORT_OLD) == 1:
        shop = shop.replace(SHOP_IMPORT_OLD, SHOP_IMPORT_NEW, 1)
        print("OK: shop api imports added")
    else:
        m = re.search(r"\} from '../../services/api';", shop)
        if m:
            ins = m.start()
            shop = shop[:ins] + ", getInventoryHouses, placeHouse, moveHouseToInventory " + shop[ins:]
            print("OK: shop api imports added (fallback)")
        else:
            print("WARNING: shop api import anchor not found — shop UI SKIPPED to keep the build safe")
            SHOP.write_text(shop)
            print("HOUSE_SHOP_MOVE_BUTTON_WARNING: shop import missing, MOVE not added")
            return 0
    # Alert import (MOVE uses Alert; duplicate module imports compile fine).
    if "Alert" not in shop:
        m2 = re.search(r"from 'react-native';", shop)
        if m2:
            shop = shop[:m2.end()] + "\nimport { Alert } from 'react-native';" + shop[m2.end():]
            print("OK: Alert import added")
    # State / load / place handler / inventory section (Oct 29 shop changes).
    if "getInventoryHouses" in shop and "handlePlaceHouse" in shop and "inventoryHouses" in shop:
        print("SKIP: shop inventory section already present")
    else:
        if shop.count(SHOP_STATE_OLD) == 1:
            shop = shop.replace(SHOP_STATE_OLD, SHOP_STATE_NEW, 1)
            print("OK: inventory + placing state added")
        else:
            print("WARNING: shop state anchor matched %dx" % shop.count(SHOP_STATE_OLD))
        if shop.count(SHOP_LOAD_OLD) == 1:
            shop = shop.replace(SHOP_LOAD_OLD, SHOP_LOAD_NEW, 1)
            print("OK: inventory loaded with shop")
        else:
            print("WARNING: shop load anchor matched %dx" % shop.count(SHOP_LOAD_OLD))
        if BUY_HANDLER_ANCHOR in shop and "handlePlaceHouse" not in shop:
            shop = shop.replace(BUY_HANDLER_ANCHOR, PLACE_HANDLER + BUY_HANDLER_ANCHOR, 1)
            print("OK: handlePlaceHouse added")
        if shop.count(HOUSES_MAP_ANCHOR) == 1:
            shop = shop.replace(HOUSES_MAP_ANCHOR, INVENTORY_SECTION + HOUSES_MAP_ANCHOR, 1)
            print("OK: INVENTORY section added to House tab")
        else:
            print("WARNING: HOUSES.map anchor matched %dx" % shop.count(HOUSES_MAP_ANCHOR))
    # NEW: MOVE button right next to YOUR HOUSE (row wrap, equal width).
    lines = shop.split("\n")
    move_done = False
    if "MOVE" in shop and "moveHouseToInventory(myHouse.id" in shop:
        print("SKIP: MOVE button next to YOUR HOUSE already present")
        move_done = True
    else:
        yh = [i for i, ln in enumerate(lines) if "YOUR HOUSE" in ln]
        if not yh:
            print("WARNING: YOUR HOUSE button not found in shop.tsx")
        elif "myHouse" not in shop:
            print("WARNING: myHouse state not in shop.tsx — MOVE skipped (would break the build)")
        else:
            blk = find_button_block(lines, yh[0])
            if not blk:
                print("WARNING: YOUR HOUSE button block not found (no enclosing TouchableOpacity/Pressable)")
            else:
                start, end, tag = blk
                indent = lines[start][:len(lines[start]) - len(lines[start].lstrip())]
                orig = lines[start:end + 1]
                move_btn = [
                    indent + "  <View style={{ flex: 1 }}>",
                    indent + "    <TouchableOpacity",
                    indent + "      style={{ backgroundColor: '#1e88e5', paddingVertical: 12, borderRadius: 8, alignItems: 'center' }}",
                    indent + "      onPress={() => {",
                    indent + "        if (!myHouse?.id || !playerId) { Alert.alert('Move House', 'No house to move.'); return; }",
                    indent + "        Alert.alert('Move House?', `${myHouse.name || 'Your house'} will go into your inventory. You can place it again anytime from the Shop House tab.`, [",
                    indent + "          { text: 'Keep It Here', style: 'cancel' },",
                    indent + "          { text: 'Move', onPress: async () => {",
                    indent + "            try {",
                    indent + "              await moveHouseToInventory(myHouse.id, playerId);",
                    indent + "              setMyHouse(null);",
                    indent + "              try { const inv = await getInventoryHouses(playerId); setInventoryHouses(inv || []); } catch (_) {}",
                    indent + "              Alert.alert('House Moved', 'Your house is in your inventory. Place it again from the INVENTORY section below.');",
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
                wrapped = (
                    [indent + "<View style={{ flexDirection: 'row', gap: 10 }}>",
                     indent + "  <View style={{ flex: 1 }}>"]
                    + ["  " + ln for ln in orig]
                    + [indent + "  </View>"]
                    + move_btn
                    + [indent + "</View>"]
                )
                lines[start:end + 1] = wrapped
                shop = "\n".join(lines)
                print("OK: MOVE button added right next to YOUR HOUSE")
                move_done = True
    SHOP.write_text(shop)
    if move_done:
        print("HOUSE_SHOP_MOVE_BUTTON_OK")
    else:
        print("HOUSE_SHOP_MOVE_BUTTON_WARNING: MOVE button not added (see WARNING lines above)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
