"""Street Legends frontend: move house to inventory + place it again.
Run from repo root: python3 frontend/patch-house-move-frontend.py
Idempotent - safe to re-run.

FEATURE (user 2026-10-29):
- House popup gains MOVE TO INVENTORY next to Hide / Sell.
- Moved house leaves the map and sits in the player's inventory.
- Shop House tab shows an INVENTORY section; PLACE HERE drops the
  house at the player's current position (keeps tier + items).

CHANGES:
- services/api.ts: moveHouseToInventory / getInventoryHouses /
  placeHouse, appended anchor-free (same lesson as the buy fix).
- app/(tabs)/index.tsx: import + MOVE button in the house popup.
- app/(tabs)/shop.tsx: inventory state + load + PLACE handler +
  INVENTORY section above the buy cards.
  GUARD: if the shop api-import anchor misses, the shop UI changes
  are SKIPPED (so the build never breaks on an undefined import).

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this. Pair with the
backend patch-house-move.py + Deploy.
"""
import re
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
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

INDEX_IMPORT_OLD = "  sendFriendRequest,\n"
INDEX_IMPORT_NEW = "  sendFriendRequest,\n  moveHouseToInventory,\n"

HIDE_BTN_CLOSE = """                    <Text style={styles.actionButtonText}>{houseHidden ? 'UNHIDE ME' : 'HIDE ME FROM MAP'}</Text>
                  </TouchableOpacity>"""
MOVE_BTN = HIDE_BTN_CLOSE + """
                  <TouchableOpacity
                    style={[styles.actionButton, { backgroundColor: '#f39c12' }]}
                    onPress={() => {
                      Alert.alert('Move House?', `${selectedMarker.data.name} will go into your inventory. You can place it again anytime from the Shop House tab.`, [
                        { text: 'Keep It Here', style: 'cancel' },
                        { text: 'Move', onPress: async () => {
                          if (!playerId) return;
                          try {
                            await moveHouseToInventory(selectedMarker.data.id, playerId);
                            showGameToast({ type: 'success', title: 'House Moved', message: 'Your house is in your inventory. Place it again from the Shop House tab.', duration: 3000 });
                            setSelectedMarker(null);
                            refetchEntities();
                            refetchPlayer();
                          } catch (err: any) {
                            showGameToast({ type: 'warning', title: 'Error', message: err?.response?.data?.detail || 'Could not move house', duration: 3000 });
                          }
                        } },
                      ]);
                    }}
                  >
                    <Text style={styles.actionButtonText}>MOVE TO INVENTORY</Text>
                  </TouchableOpacity>"""

SHOP_IMPORT_OLD = "buyHouse, getPlayerHouse } from '../../services/api';"
SHOP_IMPORT_NEW = "buyHouse, getPlayerHouse, getInventoryHouses, placeHouse } from '../../services/api';"

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


def main():
    # 1. api.ts: append anchor-free.
    if not API.exists():
        print(f"ERROR: {API} not found. Run from repo root.")
        sys.exit(1)
    api = API.read_text()
    if "export const moveHouseToInventory" in api and "export const placeHouse" in api:
        print("SKIP: move/place api functions already present")
    else:
        if not api.endswith("\n"):
            api += "\n"
        api += API_FUNCS + "\n"
        API.write_text(api)
        print("OK: move/place api functions appended")

    # 2. index.tsx: import + MOVE button.
    if not INDEX.exists():
        print(f"ERROR: {INDEX} not found. Run from repo root.")
        sys.exit(1)
    src = INDEX.read_text()
    if "moveHouseToInventory," in src:
        print("SKIP: moveHouseToInventory already imported")
    elif src.count(INDEX_IMPORT_OLD) == 1:
        src = src.replace(INDEX_IMPORT_OLD, INDEX_IMPORT_NEW, 1)
        print("OK: moveHouseToInventory imported")
    else:
        print(f"WARNING: index import anchor matched {src.count(INDEX_IMPORT_OLD)}x")
    if "MOVE TO INVENTORY" in src:
        print("SKIP: MOVE button already present")
    elif src.count(HIDE_BTN_CLOSE) == 1:
        src = src.replace(HIDE_BTN_CLOSE, MOVE_BTN, 1)
        print("OK: MOVE TO INVENTORY button added to house popup")
    else:
        # Fallback: same hide-button close, any indentation.
        m = re.search(r"(<Text style=\{styles\.actionButtonText\}>\{houseHidden \? 'UNHIDE ME' : 'HIDE ME FROM MAP'\}</Text>\s*\n\s*</TouchableOpacity>)", src)
        if m:
            src = src[:m.end()] + "\n" + MOVE_BTN[len(HIDE_BTN_CLOSE):] + src[m.end():]
            print("OK: MOVE TO INVENTORY button added (fallback anchor)")
        else:
            print("WARNING: hide button not found")
    INDEX.write_text(src)

    # 3. shop.tsx: guarded — skip UI if the import anchor misses.
    if not SHOP.exists():
        print(f"ERROR: {SHOP} not found. Run from repo root.")
        sys.exit(1)
    shop = SHOP.read_text()
    if "getInventoryHouses" in shop and "handlePlaceHouse" in shop:
        print("SKIP: shop inventory section already present")
    else:
        if shop.count(SHOP_IMPORT_OLD) != 1:
            print(f"WARNING: shop import anchor matched {shop.count(SHOP_IMPORT_OLD)}x — shop UI SKIPPED to keep the build safe")
        else:
            shop = shop.replace(SHOP_IMPORT_OLD, SHOP_IMPORT_NEW, 1)
            print("OK: shop api imports added")
            if shop.count(SHOP_STATE_OLD) == 1:
                shop = shop.replace(SHOP_STATE_OLD, SHOP_STATE_NEW, 1)
                print("OK: inventory + placing state added")
            else:
                print(f"WARNING: shop state anchor matched {shop.count(SHOP_STATE_OLD)}x")
            if shop.count(SHOP_LOAD_OLD) == 1:
                shop = shop.replace(SHOP_LOAD_OLD, SHOP_LOAD_NEW, 1)
                print("OK: inventory loaded with shop")
            else:
                print(f"WARNING: shop load anchor matched {shop.count(SHOP_LOAD_OLD)}x")
            if BUY_HANDLER_ANCHOR in shop and "handlePlaceHouse" not in shop:
                shop = shop.replace(BUY_HANDLER_ANCHOR, PLACE_HANDLER + BUY_HANDLER_ANCHOR, 1)
                print("OK: handlePlaceHouse added")
            if shop.count(HOUSES_MAP_ANCHOR) == 1:
                shop = shop.replace(HOUSES_MAP_ANCHOR, INVENTORY_SECTION + HOUSES_MAP_ANCHOR, 1)
                print("OK: INVENTORY section added to House tab")
            else:
                print(f"WARNING: HOUSES.map anchor matched {shop.count(HOUSES_MAP_ANCHOR)}x")
            SHOP.write_text(shop)
    print("HOUSE_MOVE_FRONTEND_OK")


if __name__ == "__main__":
    main()
