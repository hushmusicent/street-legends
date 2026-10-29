"""Street Legends frontend: house visibility + item inventory rows.
Run from repo root: python3 frontend/patch-house-visibility-items-frontend.py
Idempotent - safe to re-run.

USER RULES (2026-10-29):
1. Houses visible to owner + friends only: the map query now passes
   the player's id, so the backend filters strangers out.
2. Items that went back into inventory when a house was replaced now
   show in the interior dropdown as IN INVENTORY — TAP TO PLACE
   (blue, free) instead of BUY. Tapping places one copy into the
   house; the count drops. ✓ PLACED and BUY rows are unchanged.

CHANGES:
- services/api.ts: getNearbyHouses takes an optional playerId;
  placeItemFromInventory appended anchor-free.
- hooks/useMapQueries.ts: map fetch passes playerId to
  getNearbyHouses (playerId is already a param of useMapEntities).
- app/(tabs)/index.tsx: import + three-state dropdown row + toggle
  handler that places from inventory when the item is banked.
  GUARD: if the import anchor misses, the row/handler changes are
  SKIPPED so the build never breaks on an undefined import.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this. Pair with the
backend patch-house-visibility-items.py + Deploy.
"""
import sys
from pathlib import Path

API = Path("frontend/services/api.ts")
QUERIES = Path("frontend/hooks/useMapQueries.ts")
INDEX = Path("frontend/app/(tabs)/index.tsx")

NEARBY_OLD = """export const getNearbyHouses = async (latitude: number, longitude: number, radius: number = 2000): Promise<any[]> => {
  const response = await api.get(`/houses/nearby?latitude=${latitude}&longitude=${longitude}&radius=${radius}`);
  return response.data;
};"""
NEARBY_NEW = """export const getNearbyHouses = async (latitude: number, longitude: number, radius: number = 2000, playerId?: string): Promise<any[]> => {
  const query = `/houses/nearby?latitude=${latitude}&longitude=${longitude}&radius=${radius}` + (playerId ? `&player_id=${playerId}` : '');
  const response = await api.get(query);
  return response.data;
};"""

PLACE_FN = """
export const placeItemFromInventory = async (houseId: string, playerId: string, itemId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/place-from-inventory`, { player_id: playerId, item_id: itemId });
  return response.data;
};"""

QUERY_CALL_OLD = "        getNearbyHouses(latitude, longitude, 2000),"
QUERY_CALL_NEW = "        getNearbyHouses(latitude, longitude, 2000, playerId),"

ROW_PLACED_OLD = "                      const placed = (interiorHouse?.items || []).some((it: any) => it.item_id === item.id);"
ROW_PLACED_NEW = "                      const placed = (interiorHouse?.items || []).some((it: any) => it.item_id === item.id);\n                      const invCount = (player?.inventory_items || []).filter((id: string) => id === item.id).length;"

ROW_LABEL_OLD = """                          <Text style={{ color: placed ? '#4caf50' : '#f39c12', fontWeight: '800', fontSize: 12 }}>{placed ? '✓ PLACED' : (item.price ? `BUY $${item.price.toLocaleString()}` : 'TAP TO PLACE')}</Text>"""
ROW_LABEL_NEW = """                          <Text style={{ color: placed ? '#4caf50' : invCount > 0 ? '#5dade2' : '#f39c12', fontWeight: '800', fontSize: 12 }}>{placed ? '✓ PLACED' : invCount > 0 ? `IN INVENTORY${invCount > 1 ? ` (${invCount})` : ''} — TAP TO PLACE` : (item.price ? `BUY $${item.price.toLocaleString()}` : 'TAP TO PLACE')}</Text>"""

HANDLER_OLD = """  const handleHouseItemToggle = async (item: any) => {
    if (!interiorHouse || !playerId) return;
    const placed = (interiorHouse.items || []).some((it: any) => it.item_id === item.id);
    try {
      const res = placed
        ? await removeHouseItem(interiorHouse.id, playerId, item.id)
        : await addHouseItem(interiorHouse.id, playerId, item.id);
      if (res?.house) {
        setInteriorHouse(res.house);
        if (typeof res.cash === 'number' && player) setPlayer({ ...player, cash: res.cash });
      } else {
        const next = (interiorHouse.items || []).filter((it: any) => it.item_id !== item.id);
        if (!placed) next.push({ item_id: item.id, name: item.name, x: 0.5, y: 0.5 });
        setInteriorHouse({ ...interiorHouse, items: next });
      }
    } catch (e: any) {
      Alert.alert('Item', e?.response?.data?.detail || e?.message || 'Could not update item.');
    }
  };"""

HANDLER_NEW = """  const handleHouseItemToggle = async (item: any) => {
    if (!interiorHouse || !playerId) return;
    const placed = (interiorHouse.items || []).some((it: any) => it.item_id === item.id);
    const invCount = (player?.inventory_items || []).filter((id: string) => id === item.id).length;
    try {
      const res = placed
        ? await removeHouseItem(interiorHouse.id, playerId, item.id)
        : invCount > 0
          ? await placeItemFromInventory(interiorHouse.id, playerId, item.id)
          : await addHouseItem(interiorHouse.id, playerId, item.id);
      if (res?.house) {
        setInteriorHouse(res.house);
        if (player) {
          const next: any = { ...player };
          if (typeof res.cash === 'number') next.cash = res.cash;
          if (Array.isArray(res.inventory_items)) next.inventory_items = res.inventory_items;
          setPlayer(next);
        }
      } else {
        const next = (interiorHouse.items || []).filter((it: any) => it.item_id !== item.id);
        if (!placed) next.push({ item_id: item.id, name: item.name, x: 0.5, y: 0.5 });
        setInteriorHouse({ ...interiorHouse, items: next });
        if (!placed && invCount > 0 && player) {
          const inv = [...(player.inventory_items || [])];
          const idx = inv.indexOf(item.id);
          if (idx >= 0) inv.splice(idx, 1);
          setPlayer({ ...player, inventory_items: inv });
        }
      }
    } catch (e: any) {
      Alert.alert('Item', e?.response?.data?.detail || e?.message || 'Could not update item.');
    }
  };"""


def main():
    # 1. api.ts: nearby playerId + place-from-inventory fn.
    if not API.exists():
        print(f"ERROR: {API} not found. Run from repo root.")
        sys.exit(1)
    api = API.read_text()
    if NEARBY_NEW in api:
        print("SKIP: getNearbyHouses already takes playerId")
    elif api.count(NEARBY_OLD) == 1:
        api = api.replace(NEARBY_OLD, NEARBY_NEW, 1)
        print("OK: getNearbyHouses takes playerId")
    else:
        print(f"WARNING: getNearbyHouses anchor matched {api.count(NEARBY_OLD)}x")
    if "export const placeItemFromInventory" in api:
        print("SKIP: placeItemFromInventory already present")
    else:
        if not api.endswith("\n"):
            api += "\n"
        api += PLACE_FN + "\n"
        print("OK: placeItemFromInventory appended")
    API.write_text(api)

    # 2. useMapQueries.ts: pass playerId.
    if not QUERIES.exists():
        print(f"ERROR: {QUERIES} not found. Run from repo root.")
        sys.exit(1)
    q = QUERIES.read_text()
    if QUERY_CALL_NEW in q:
        print("SKIP: map query already passes playerId")
    elif q.count(QUERY_CALL_OLD) == 1:
        q = q.replace(QUERY_CALL_OLD, QUERY_CALL_NEW, 1)
        print("OK: map query passes playerId")
    else:
        print(f"WARNING: map query anchor matched {q.count(QUERY_CALL_OLD)}x")
    QUERIES.write_text(q)

    # 3. index.tsx: import (guarded) + row + handler.
    if not INDEX.exists():
        print(f"ERROR: {INDEX} not found. Run from repo root.")
        sys.exit(1)
    src = INDEX.read_text()
    import_ok = "placeItemFromInventory," in src
    if import_ok:
        print("SKIP: placeItemFromInventory already imported")
    elif src.count("  moveHouseToInventory,\n") == 1:
        src = src.replace("  moveHouseToInventory,\n", "  moveHouseToInventory,\n  placeItemFromInventory,\n", 1)
        import_ok = True
        print("OK: placeItemFromInventory imported")
    elif src.count("  sendFriendRequest,\n") == 1:
        src = src.replace("  sendFriendRequest,\n", "  sendFriendRequest,\n  placeItemFromInventory,\n", 1)
        import_ok = True
        print("OK: placeItemFromInventory imported (fallback anchor)")
    else:
        print("WARNING: index import anchor not found - row/handler SKIPPED to keep the build safe")
    if import_ok:
        if ROW_PLACED_NEW in src:
            print("SKIP: inventory count already in row")
        elif src.count(ROW_PLACED_OLD) == 1:
            src = src.replace(ROW_PLACED_OLD, ROW_PLACED_NEW, 1)
            print("OK: inventory count added to row")
        else:
            print(f"WARNING: row anchor matched {src.count(ROW_PLACED_OLD)}x")
        if ROW_LABEL_NEW in src:
            print("SKIP: inventory label already present")
        elif src.count(ROW_LABEL_OLD) == 1:
            src = src.replace(ROW_LABEL_OLD, ROW_LABEL_NEW, 1)
            print("OK: inventory label added to row")
        else:
            print(f"WARNING: row label anchor matched {src.count(ROW_LABEL_OLD)}x")
        if HANDLER_NEW in src:
            print("SKIP: inventory toggle handler already present")
        elif src.count(HANDLER_OLD) == 1:
            src = src.replace(HANDLER_OLD, HANDLER_NEW, 1)
            print("OK: toggle handler places from inventory")
        else:
            print(f"WARNING: handler anchor matched {src.count(HANDLER_OLD)}x")
    INDEX.write_text(src)
    print("HOUSE_VISIBILITY_ITEMS_FRONTEND_OK")


if __name__ == "__main__":
    main()
