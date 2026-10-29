"""Street Legends frontend: item categories on the house screen.
Run from repo root: python3 frontend/patch-house-item-categories.py
Idempotent - safe to re-run.

ADDS (House Interior Modal in index.tsx):
A bottom panel with three category tabs — Games, Appliances,
Utilities. Tapping a tab selects it. NO ITEMS ARE PUT IN YET: each
category shows an empty state ("No games yet." etc.) until items are
added in a later step. The panel also shows the house name and how
many item slots are used (e.g. 0/6) from the house's item_limit.

LAYOUT: the panel overlays the bottom of the room image (absolute,
bottom 0) so the horizontal room scroll is untouched. The old
bottom-left name label is removed (the name now lives in the panel
header). LEAVE HOUSE stays pinned top-right.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

PATH = Path("frontend/app/(tabs)/index.tsx")

STATE_OLD = "  const [interiorHouse, setInteriorHouse] = useState<any | null>(null);"
STATE_NEW = """  const [interiorHouse, setInteriorHouse] = useState<any | null>(null);
  const [houseItemCategory, setHouseItemCategory] = useState('games');"""

PANEL_OLD = """          <TouchableOpacity
            style={{ position: 'absolute', top: 48, right: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 }}"""
PANEL_NEW = """          {/* House item categories — empty for now, items come later */}
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
          <TouchableOpacity
            style={{ position: 'absolute', top: 48, right: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 20, paddingVertical: 8, paddingHorizontal: 16 }}"""

NAME_LABEL_OLD = """          <View style={{ position: 'absolute', bottom: 32, left: 16, backgroundColor: 'rgba(0,0,0,0.6)', borderRadius: 12, paddingVertical: 8, paddingHorizontal: 14 }}>
            <Text style={{ color: '#fff', fontWeight: '800', fontSize: 16 }}>{interiorHouse?.name || ''}</Text>
          </View>
"""
NAME_LABEL_NEW = ""

REPLACEMENTS = [
    (STATE_OLD, STATE_NEW, "house item category state added"),
    (PANEL_OLD, PANEL_NEW, "item category panel added"),
    (NAME_LABEL_OLD, NAME_LABEL_NEW, "old name label removed (name now in panel)"),
]


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from repo root.")
        sys.exit(1)
    src = PATH.read_text()
    for old, new, desc in REPLACEMENTS:
        if new and new in src:
            print(f"SKIP: {desc} (already applied)")
        elif src.count(old) == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {desc}")
        elif src.count(old) == 0 and new == "":
            print(f"SKIP: {desc} (already removed)")
        else:
            print(f"WARNING: anchor matched {src.count(old)}x — {desc}")
    PATH.write_text(src)
    print("HOUSE_ITEM_CATEGORIES_OK")


if __name__ == "__main__":
    main()
