"""Street Legends frontend: fix house item buy + show player cash.
Run from repo root: python3 frontend/patch-house-buy-fix.py
Idempotent - safe to re-run.

BUGS (from user screenshot 2026-10-29):
1. Tapping BUY on the pool table pops "Property 'addHouseItem'
   doesn't exist". Cause: index.tsx imports addHouseItem, but the
   api.ts step that defines it never stuck (its sellHouse anchor
   didn't match Emergent's api.ts), so the call fails before any
   network request — nothing was bought or placed.
   FIX: append any missing item api functions (add/remove/move)
   directly to the end of services/api.ts — no anchor to miss.
2. The interior shows no cash balance, so the player can't tell if
   they can afford an item.
   FIX: show the player's cash (gold, with icon) under the house
   name in the interior header. It updates live after a buy/remove
   because the toggle handler already writes the new cash to the
   player store.
3. The old bottom-left house name label is still showing (duplicate
   of the header name).
   FIX: remove it if present.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this. Also make sure
the backend items v2 patch is Deployed, or BUY will fail at the
server after this fix.
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
API = Path("frontend/services/api.ts")

ADD_FN = """
export const addHouseItem = async (houseId: string, playerId: string, itemId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/add`, { player_id: playerId, item_id: itemId });
  return response.data;
};"""

REMOVE_FN = """
export const removeHouseItem = async (houseId: string, playerId: string, itemId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/remove`, { player_id: playerId, item_id: itemId });
  return response.data;
};"""

MOVE_FN = """
export const moveHouseItem = async (houseId: string, playerId: string, itemId: string, x: number, y: number): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/move`, { player_id: playerId, item_id: itemId, x, y });
  return response.data;
};"""

HEADER_OLD = """            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>{interiorHouse?.name || ''}</Text>
              <Text style={{ color: '#f39c12', fontWeight: '700', fontSize: 12 }}>{(interiorHouse?.items?.length || 0)}/{interiorHouse?.item_limit || 6} items</Text>
            </View>"""
HEADER_NEW = """            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
              <Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>{interiorHouse?.name || ''}</Text>
              <Text style={{ color: '#f39c12', fontWeight: '700', fontSize: 12 }}>{(interiorHouse?.items?.length || 0)}/{interiorHouse?.item_limit || 6} items</Text>
            </View>
            <Text style={{ color: '#f39c12', fontWeight: '800', fontSize: 14, marginBottom: 8 }}>💰 ${(player?.cash || 0).toLocaleString()}</Text>"""

NAME_LABEL_OLD = """          <View style={{ position: 'absolute', bottom: 32, left: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 12, paddingVertical: 8, paddingHorizontal: 14 }}>
            <Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>{interiorHouse?.name || ''}</Text>
          </View>
"""


def main():
    # 1. api.ts: append any missing item functions (anchor-free).
    if not API.exists():
        print(f"ERROR: {API} not found. Run from repo root.")
        sys.exit(1)
    api = API.read_text()
    missing = []
    if "export const addHouseItem" not in api:
        missing.append(("addHouseItem", ADD_FN))
    if "export const removeHouseItem" not in api:
        missing.append(("removeHouseItem", REMOVE_FN))
    if "export const moveHouseItem" not in api:
        missing.append(("moveHouseItem", MOVE_FN))
    if not missing:
        print("SKIP: all item api functions already present")
    else:
        if not api.endswith("\n"):
            api += "\n"
        for name, fn in missing:
            api += fn + "\n"
            print(f"OK: {name} appended to api.ts")
        API.write_text(api)

    # 2 + 3. index.tsx: cash display + remove leftover name label.
    if not INDEX.exists():
        print(f"ERROR: {INDEX} not found. Run from repo root.")
        sys.exit(1)
    src = INDEX.read_text()
    if HEADER_NEW in src:
        print("SKIP: cash display already present")
    elif src.count(HEADER_OLD) == 1:
        src = src.replace(HEADER_OLD, HEADER_NEW, 1)
        print("OK: player cash added to interior header")
    else:
        print(f"WARNING: header anchor matched {src.count(HEADER_OLD)}x")
    if NAME_LABEL_OLD in src:
        src = src.replace(NAME_LABEL_OLD, "", 1)
        print("OK: leftover bottom-left name label removed")
    elif "bottom: 32, left: 16" not in src:
        print("SKIP: bottom-left name label already gone")
    else:
        print("WARNING: name label found but did not match exactly")
    INDEX.write_text(src)
    print("HOUSE_BUY_FIX_OK")


if __name__ == "__main__":
    main()
