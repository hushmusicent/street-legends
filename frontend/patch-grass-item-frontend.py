#!/usr/bin/env python3
"""Street Legends frontend: Grass item screen (frontend / Expo Go).

The item screen is the GENERIC inventory list (ItemsTab in character.tsx
rendering inventory-details entries), so Grass appears through the
inventory data — no hardcoded item row is added to the list itself.
What this patch does add, scoped to rows whose item.id is 'grass':
  - the oz count next to the name ("Grass x3 oz"),
  - a USE button (+50% max health, 60 seconds) and a SELL 1 OZ ($100)
    button, replacing the generic EQUIP/SELL/REPAIR row for Grass rows
    only (the generic Sell pays value//2 and pops a whole entry, and
    Equip makes no sense for a consumable, so neither may run for Grass).
  - parent handlers (handleUseGrass / handleSellGrass) following the
    existing handleSellItem pattern (call api, reload all data, alert
    the result). Sell asks nothing extra: no quantity prompt and no
    confirmation dialog — one tap sells exactly 1 oz for $100.
Art: no local asset work is needed. Item rows already render
item.icon_url as an Image (with an Ionicon fallback on error), and the
backend wires Grass's icon_url to the repo-root grass-item.png raw URL.
That file must be pushed to the repo root or the row falls back to the
leaf icon while the item still functions.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
API = ROOT / "frontend/services/api.ts"
CHAR = ROOT / "frontend/app/(tabs)/character.tsx"

API_FUNCS = '''
export const useGrassItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/grass/use`);
  return response.data;
};

export const sellGrassItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/grass/sell?qty=${qty}`);
  return response.data;
};
'''

HANDLERS = '''
  // GRASS_ITEM_FRONTEND_HANDLERS: use/sell Grass, mirroring handleSellItem.
  const handleUseGrass = async () => {
    if (!playerId) return;
    try {
      const result = await useGrassItem(playerId);
      await loadAllData();
      Alert.alert('Grass used!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to use Grass');
    }
  };

  const handleSellGrass = async () => {
    if (!playerId) return;
    try {
      const result = await sellGrassItem(playerId, 1);
      await loadAllData();
      Alert.alert('Sold!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to sell Grass');
    }
  };
'''

GRASS_ROW = '''{item.id === 'grass' ? (
            <View style={styles.itemActions}>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.equipActionBtn]}
                onPress={() => onUseGrass()}
              >
                <Ionicons name="leaf" size={14} color="#4caf50" />
                <Text style={[styles.itemActionText, { color: '#4caf50' }]}>USE (+50% HP 60s)</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.sellActionBtn]}
                onPress={() => onSellGrass()}
              >
                <Ionicons name="cash" size={14} color="#f39c12" />
                <Text style={[styles.itemActionText, { color: '#f39c12' }]}>SELL 1 OZ ($100)</Text>
              </TouchableOpacity>
            </View>
          ) : ('''


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def main():
    landed = []

    # --- api.ts ---
    if not API.exists():
        print("WARNING: services/api.ts not found - Grass api functions NOT added")
    else:
        asrc = API.read_text(errors="ignore")
        if "useGrassItem" in asrc and "sellGrassItem" in asrc:
            print("GRASS_ITEM_FRONTEND_API_ALREADY_APPLIED"); landed.append("api")
        else:
            anchor = ("export const sellItem = async (playerId: string, itemId: string) => {\n"
                      "  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);\n"
                      "  return response.data;\n"
                      "};")
            if anchor in asrc:
                asrc = asrc.replace(anchor, anchor + API_FUNCS, 1)
                API.write_text(asrc)
                print("GRASS_ITEM_FRONTEND_API_OK"); landed.append("api")
            else:
                print("WARNING: sellItem anchor not found in api.ts - Grass api functions NOT added")

    # --- character.tsx ---
    if not CHAR.exists():
        print("WARNING: character.tsx not found - item screen NOT changed")
        print("GRASS_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    src = CHAR.read_text(errors="ignore")
    char_orig = src
    orig = delta(src)

    # Imports.
    if "useGrassItem" in src and "sellGrassItem" in src:
        print("GRASS_ITEM_FRONTEND_IMPORTS_ALREADY_APPLIED"); landed.append("imports")
    elif "  sellItem,\n" in src:
        src = src.replace("  sellItem,\n", "  sellItem,\n  useGrassItem,\n  sellGrassItem,\n", 1)
        print("GRASS_ITEM_FRONTEND_IMPORTS_OK"); landed.append("imports")
    else:
        print("WARNING: api import anchor not found - Grass imports NOT added")

    # Parent handlers.
    if "handleUseGrass" in src and "handleSellGrass" in src:
        print("GRASS_ITEM_FRONTEND_HANDLERS_ALREADY_APPLIED"); landed.append("handlers")
    elif "  const handleRepairItem = async" in src:
        src = src.replace("  const handleRepairItem = async", HANDLERS.strip() + "\n\n  const handleRepairItem = async", 1)
        print("GRASS_ITEM_FRONTEND_HANDLERS_OK"); landed.append("handlers")
    else:
        print("WARNING: handleRepairItem anchor not found - Grass handlers NOT added")

    # ItemsTab props (type + destructure). The type line is ItemsTab-specific
    # (EquipmentTab's onRepair takes a slot argument, so it does not match).
    if "onUseGrass" in src and "onSellGrass" in src and "GRASS_ITEM_FRONTEND_PROPS" in src:
        print("GRASS_ITEM_FRONTEND_PROPS_ALREADY_APPLIED"); landed.append("props")
    else:
        tline = "  onRepair: (item: EquipmentItem) => void;"
        if tline in src:
            ti = src.find(tline)
            di = src.rfind("  onRepair,\n", 0, ti)
            if di != -1 and ti - di < 2000:
                src = src[:di] + "  onRepair,\n  onUseGrass,\n  onSellGrass,\n" + src[di + len("  onRepair,\n"):]
                ti = src.find(tline)
                src = src[:ti + len(tline)] + "\n  onUseGrass: () => void;\n  onSellGrass: () => void;\n  // GRASS_ITEM_FRONTEND_PROPS" + src[ti + len(tline):]
                print("GRASS_ITEM_FRONTEND_PROPS_OK"); landed.append("props")
            else:
                print("WARNING: ItemsTab destructure anchor not found - Grass props NOT added")
        else:
            print("WARNING: ItemsTab props type anchor not found - Grass props NOT added")

    # Parent render passes the handlers (unique: EquipmentTab uses handleRepairEquippedItem).
    if "onUseGrass={handleUseGrass}" in src:
        print("GRASS_ITEM_FRONTEND_RENDER_ALREADY_APPLIED"); landed.append("render")
    else:
        ri = src.find("onRepair={handleRepairItem}")
        if ri == -1:
            print("WARNING: ItemsTab render anchor not found - Grass handlers NOT wired to the item screen")
        else:
            line_start = src.rfind("\n", 0, ri) + 1
            line_end = src.find("\n", ri)
            indent = src[line_start:ri]
            if indent.strip() != "":
                print("WARNING: ItemsTab render line has unexpected content - Grass handlers NOT wired")
            else:
                src = (src[:line_end + 1] + indent + "onUseGrass={handleUseGrass}\n"
                       + indent + "onSellGrass={handleSellGrass}\n" + src[line_end + 1:])
                print("GRASS_ITEM_FRONTEND_RENDER_OK"); landed.append("render")

    # Oz count next to the name (exactly one occurrence expected).
    if "oz' : ''" in src:
        print("GRASS_ITEM_FRONTEND_QTY_ALREADY_APPLIED"); landed.append("qty")
    else:
        old_name = "{item.name} {item.is_broken && '(BROKEN)'}"
        if src.count(old_name) == 1:
            src = src.replace(old_name,
                              "{item.name}{(item as any).qty ? ' x' + (item as any).qty + ' oz' : ''} {item.is_broken && '(BROKEN)'}", 1)
            print("GRASS_ITEM_FRONTEND_QTY_OK"); landed.append("qty")
        else:
            print("WARNING: item name anchor found %d times (expected 1) - oz count NOT added" % src.count(old_name))

    # Grass action row replacing the generic row for grass rows only.
    if "GRASS_ITEM_FRONTEND_ROW" in src:
        print("GRASS_ITEM_FRONTEND_ROW_ALREADY_APPLIED"); landed.append("row")
    else:
        inv_at = src.find("INVENTORY (")
        row_at = src.find("<View style={styles.itemActions}>", inv_at) if inv_at != -1 else -1
        if row_at == -1:
            print("WARNING: item action row anchor not found - Grass USE/SELL buttons NOT added (generic row would still show for Grass)")
        else:
            line_start = src.rfind("\n", 0, row_at) + 1
            close_at = src.find("</View>", row_at)
            if close_at == -1:
                print("WARNING: item action row end not found - Grass USE/SELL buttons NOT added")
            else:
                end = close_at + len("</View>")
                src = (src[:line_start] + GRASS_ROW + "\n" + src[line_start:end] + "\n            )}\n"
                       + src[end:])
                # Marker for idempotency (inside a comment so JSX stays valid).
                src = src.replace(GRASS_ROW, "{/* GRASS_ITEM_FRONTEND_ROW */}\n" + GRASS_ROW, 1)
                print("GRASS_ITEM_FRONTEND_ROW_OK"); landed.append("row")

    if delta(src) != orig:
        print("WARNING: balance changed - character.tsx NOT written")
        return 1
    if src == char_orig:
        if "GRASS_ITEM_FRONTEND_ROW" in src and "useGrassItem" in src and "handleUseGrass" in src:
            print("GRASS_ITEM_FRONTEND_ALREADY_APPLIED")
        else:
            print("GRASS_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    CHAR.write_text(src)
    if len(landed) == 7:
        print("GRASS_ITEM_FRONTEND_OK")
    else:
        print("GRASS_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
    return 0

if __name__ == "__main__":
    sys.exit(main())
