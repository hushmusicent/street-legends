"""Street Legends frontend: house item tabs move to the top + dropdown.
Run from repo root: python3 frontend/patch-house-item-tabs-top.py
Idempotent - safe to re-run.

CHANGE (House Interior Modal in index.tsx):
1. The bottom item panel from patch-house-item-categories.py is
   REMOVED.
2. The 3 tabs (Games / Appliances / Utilities) now sit at the TOP of
   the interior, below LEAVE HOUSE so nothing collides.
3. Tapping a tab DROPS DOWN its item list beneath the tabs. Tapping
   the same tab again closes it; tapping another tab switches lists.
4. Tapping an item in the list SELECTS it (and closes the dropdown).
   NO ITEMS ARE PUT IN YET: each list is empty and shows "No games
   yet." etc. A HOUSE_ITEMS const (empty arrays per category) is the
   fill point for a later step.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

PATH = Path("frontend/app/(tabs)/index.tsx")

STATE_CATEGORIES = "  const [houseItemCategory, setHouseItemCategory] = useState('games');"
STATE_NEW = "  const [houseItemCategory, setHouseItemCategory] = useState<string | null>(null);\n  const [selectedHouseItem, setSelectedHouseItem] = useState<any | null>(null);"
STATE_INTERIOR = "  const [interiorHouse, setInteriorHouse] = useState<any | null>(null);"

HOUSE_IMAGES_BLOCK = """const HOUSE_IMAGES: Record<string, any> = {
  apartment: require('../../assets/houses/house-apartment.jpg'),
  cabin: require('../../assets/houses/house-cabin.jpg'),
  mansion: require('../../assets/houses/house-mansion.jpg'),
};"""
HOUSE_ITEMS_CONST = """
// House shop items by category — empty for now, filled in a later step.
const HOUSE_ITEMS: Record<string, any[]> = {
  games: [],
  appliances: [],
  utilities: [],
};"""

BOTTOM_PANEL_OLD = """          {/* House item categories — empty for now, items come later */}
          <View style={{ position: 'absolute', bottom: 0, left: 0, right: 0, backgroundColor: 'rgba(0,0,0,0.88)', borderTopWidth: 1, borderTopColor: '#222', paddingHorizontal: 16, paddingTop: 12, paddingBottom: 20 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>{interiorHouse?.name || ''}</Text>
              <Text style={{ color: '#f39c12', fontWeight: '700', fontSize: 12 }}>{(interiorHouse?.items?.length || 0)}/{interiorHouse?.item_limit || 6} items</Text>
            </View>
            <View style={{ flexDirection: 'row', gap: 8, marginBottom: 10 }}>
              {([
                { key: 'games', icon: '🎮', label: 'Games' },
                { key: 'appliances', icon: '📺', label: 'Appliances' },
                { key: 'utilities', icon: '💡', label: 'Utilities' },
              ]).map((c) => (
                <TouchableOpacity
                  key={c.key}
                  onPress={() => setHouseItemCategory(c.key)}
                  style={{ flex: 1, alignItems: 'center', paddingVertical: 10, borderRadius: 10, backgroundColor: houseItemCategory === c.key ? '#f39c12' : '#1a1a1a' }}
                >
                  <Text style={{ fontSize: 22 }}>{c.icon}</Text>
                  <Text style={{ color: houseItemCategory === c.key ? '#000' : '#fff', fontWeight: '800', fontSize: 11, marginTop: 2 }}>{c.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
            <Text style={{ color: '#888', fontSize: 13, textAlign: 'center' }}>
              {houseItemCategory === 'games' ? 'No games yet.' : houseItemCategory === 'appliances' ? 'No appliances yet.' : 'No utilities yet.'}
            </Text>
          </View>
"""

TOP_TABS_OLD = """          <TouchableOpacity
            style={{ position: 'absolute', top: 48, right: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 }}"""
TOP_TABS_NEW = """          {/* House item tabs (top) + dropdown */}
          <View style={{ position: 'absolute', top: 96, left: 16, right: 16 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>{interiorHouse?.name || ''}</Text>
              <Text style={{ color: '#f39c12', fontWeight: '700', fontSize: 12 }}>{(interiorHouse?.items?.length || 0)}/{interiorHouse?.item_limit || 6} items</Text>
            </View>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              {([
                { key: 'games', icon: '🎮', label: 'Games' },
                { key: 'appliances', icon: '📺', label: 'Appliances' },
                { key: 'utilities', icon: '💡', label: 'Utilities' },
              ]).map((c) => (
                <TouchableOpacity
                  key={c.key}
                  onPress={() => setHouseItemCategory(houseItemCategory === c.key ? null : c.key)}
                  style={{ flex: 1, alignItems: 'center', paddingVertical: 10, borderRadius: 10, backgroundColor: houseItemCategory === c.key ? '#f39c12' : 'rgba(0,0,0,0.6)' }}
                >
                  <Text style={{ fontSize: 22 }}>{c.icon}</Text>
                  <Text style={{ color: houseItemCategory === c.key ? '#000' : '#fff', fontWeight: '800', fontSize: 11, marginTop: 2 }}>{c.label}</Text>
                </TouchableOpacity>
              ))}
            </View>
            {houseItemCategory && (
              <View style={{ marginTop: 8, backgroundColor: 'rgba(0,0,0,0.88)', borderRadius: 12, borderWidth: 1, borderColor: '#222', padding: 12, maxHeight: 280 }}>
                <ScrollView showsVerticalScrollIndicator={false}>
                  {(HOUSE_ITEMS[houseItemCategory] || []).length === 0 ? (
                    <Text style={{ color: '#888', fontSize: 13, textAlign: 'center' }}>
                      {houseItemCategory === 'games' ? 'No games yet.' : houseItemCategory === 'appliances' ? 'No appliances yet.' : 'No utilities yet.'}
                    </Text>
                  ) : (
                    (HOUSE_ITEMS[houseItemCategory] || []).map((item: any) => (
                      <TouchableOpacity
                        key={item.id}
                        onPress={() => { setSelectedHouseItem(item); setHouseItemCategory(null); }}
                        style={{ paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: '#222' }}
                      >
                        <Text style={{ color: '#fff', fontWeight: '700' }}>{item.name}</Text>
                      </TouchableOpacity>
                    ))
                  )}
                </ScrollView>
              </View>
            )}
          </View>
          <TouchableOpacity
            style={{ position: 'absolute', top: 48, right: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 }}"""


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from repo root.")
        sys.exit(1)
    src = PATH.read_text()

    # 1. Category state: retarget to dropdown semantics (null = closed).
    if STATE_NEW in src:
        print("SKIP: category state already dropdown-style")
    elif src.count(STATE_CATEGORIES) == 1:
        src = src.replace(STATE_CATEGORIES, STATE_NEW, 1)
        print("OK: category state now dropdown-style (null = closed)")
    elif "const [houseItemCategory" not in src and src.count(STATE_INTERIOR) == 1:
        src = src.replace(STATE_INTERIOR, STATE_INTERIOR + "\n" + STATE_NEW, 1)
        print("OK: category + selection state added (categories patch was absent)")
    else:
        print("WARNING: category state anchor not matched")

    # 2. HOUSE_ITEMS fill point (empty arrays per category).
    if "const HOUSE_ITEMS" in src:
        print("SKIP: HOUSE_ITEMS already present")
    elif src.count(HOUSE_IMAGES_BLOCK) == 1:
        src = src.replace(HOUSE_IMAGES_BLOCK, HOUSE_IMAGES_BLOCK + HOUSE_ITEMS_CONST, 1)
        print("OK: HOUSE_ITEMS const added (empty, fill point for later)")
    elif src.count(STATE_INTERIOR) == 1:
        src = src.replace(STATE_INTERIOR, STATE_INTERIOR + HOUSE_ITEMS_CONST, 1)
        print("OK: HOUSE_ITEMS const added after interior state (HOUSE_IMAGES anchor missed)")
    else:
        print("WARNING: neither HOUSE_IMAGES nor interior state matched — dropdown needs HOUSE_ITEMS")

    # 3. Remove the bottom panel (if the categories patch was applied).
    if src.count(BOTTOM_PANEL_OLD) == 1:
        src = src.replace(BOTTOM_PANEL_OLD, "", 1)
        print("OK: bottom panel removed")
    elif "{/* House item categories" not in src:
        print("SKIP: bottom panel absent (categories patch was never applied)")
    else:
        print("WARNING: bottom panel found but did not match exactly — left in place")

    # 4. Add the top tabs + dropdown before LEAVE HOUSE.
    if "House item tabs (top) + dropdown" in src:
        print("SKIP: top tabs already present")
    elif src.count(TOP_TABS_OLD) == 1:
        src = src.replace(TOP_TABS_OLD, TOP_TABS_NEW, 1)
        print("OK: top tabs + dropdown added")
    else:
        print(f"WARNING: LEAVE HOUSE anchor matched {src.count(TOP_TABS_OLD)}x")

    PATH.write_text(src)
    print("HOUSE_ITEM_TABS_TOP_OK")


if __name__ == "__main__":
    main()
