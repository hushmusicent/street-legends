#!/usr/bin/env python3
"""Street Legends frontend: Pills item screen (frontend / Expo Go).

Mirrors the Grass frontend patch. The item screen is the GENERIC
inventory list (ItemsTab in character.tsx rendering inventory-details
entries), so Pills appears through the inventory data — no hardcoded
item row is added to the list itself. What this patch does add, scoped
to rows whose item.id is 'pills':
  - the oz count next to the name ("Pills x3 oz"; shared with the Grass
    patch's qty part — if Grass already added it, this prints
    ALREADY_APPLIED for that part),
  - a USE button (+50% max energy, 60 seconds) and a SELL 1 OZ ($200)
    button, replacing the generic EQUIP/SELL/REPAIR row for Pills rows
    only (the generic Sell pays value//2 and pops a whole entry, and
    Equip makes no sense for a consumable, so neither may run for Pills).
  - parent handlers (handleUsePills / handleSellPills) following the
    existing handleSellItem pattern (call api, reload all data, alert
    the result). Sell asks nothing extra: no quantity prompt and no
    confirmation dialog — one tap sells exactly 1 oz for $200.
Art: no local asset work is needed. Item rows already render
item.icon_url as an Image (with an Ionicon fallback on error), and the
backend wires Pills's icon_url to an embedded data URI of the uploaded
pill-bottle image (no GitHub-hosted file needed).

Row-nesting note: if the Grass patch already wrapped the generic row in
a {item.id === 'grass' ? ... : (...)} ternary, the generic row now sits
inside that ternary's else branch, where a braced {pills ? ...} wrapper
would be a JS block, not an expression. This patch detects that case
(preceding text ends with ") : (") and wraps bracelessly; otherwise it
wraps with braces as a normal JSX child.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
API = ROOT / "frontend/services/api.ts"
CHAR = ROOT / "frontend/app/(tabs)/character.tsx"

API_FUNCS = '''
export const usePillsItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/pills/use`);
  return response.data;
};

export const sellPillsItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/pills/sell?qty=${qty}`);
  return response.data;
};
'''

HANDLERS = '''
  // PILLS_ITEM_FRONTEND_HANDLERS: use/sell Pills, mirroring handleSellItem.
  const handleUsePills = async () => {
    if (!playerId) return;
    try {
      const result = await usePillsItem(playerId);
      await loadAllData();
      Alert.alert('Pills used!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to use Pills');
    }
  };

  const handleSellPills = async () => {
    if (!playerId) return;
    try {
      const result = await sellPillsItem(playerId, 1);
      await loadAllData();
      Alert.alert('Sold!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to sell Pills');
    }
  };
'''

PILLS_BUTTONS = '''<View style={styles.itemActions}>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.equipActionBtn]}
                onPress={() => onUsePills()}
              >
                <Ionicons name="medkit" size={14} color="#4caf50" />
                <Text style={[styles.itemActionText, { color: '#4caf50' }]}>USE (+50% ENERGY 60s)</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.sellActionBtn]}
                onPress={() => onSellPills()}
              >
                <Ionicons name="cash" size={14} color="#f39c12" />
                <Text style={[styles.itemActionText, { color: '#f39c12' }]}>SELL 1 OZ ($200)</Text>
              </TouchableOpacity>
            </View>'''


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def main():
    landed = []

    # --- api.ts ---
    if not API.exists():
        print("WARNING: services/api.ts not found - Pills api functions NOT added")
    else:
        asrc = API.read_text(errors="ignore")
        if "usePillsItem" in asrc and "sellPillsItem" in asrc:
            print("PILLS_ITEM_FRONTEND_API_ALREADY_APPLIED"); landed.append("api")
        else:
            anchor = ("export const sellItem = async (playerId: string, itemId: string) => {\n"
                      "  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);\n"
                      "  return response.data;\n"
                      "};")
            if anchor in asrc:
                asrc = asrc.replace(anchor, anchor + API_FUNCS, 1)
                API.write_text(asrc)
                print("PILLS_ITEM_FRONTEND_API_OK"); landed.append("api")
            else:
                print("WARNING: sellItem anchor not found in api.ts - Pills api functions NOT added")

    # --- character.tsx ---
    if not CHAR.exists():
        print("WARNING: character.tsx not found - item screen NOT changed")
        print("PILLS_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    src = CHAR.read_text(errors="ignore")
    char_orig = src
    orig = delta(src)

    # Imports.
    if "usePillsItem" in src and "sellPillsItem" in src:
        print("PILLS_ITEM_FRONTEND_IMPORTS_ALREADY_APPLIED"); landed.append("imports")
    elif "  sellItem,\n" in src:
        src = src.replace("  sellItem,\n", "  sellItem,\n  usePillsItem,\n  sellPillsItem,\n", 1)
        print("PILLS_ITEM_FRONTEND_IMPORTS_OK"); landed.append("imports")
    else:
        print("WARNING: api import anchor not found - Pills imports NOT added")

    # Parent handlers.
    if "handleUsePills" in src and "handleSellPills" in src:
        print("PILLS_ITEM_FRONTEND_HANDLERS_ALREADY_APPLIED"); landed.append("handlers")
    elif "  const handleRepairItem = async" in src:
        src = src.replace("  const handleRepairItem = async", HANDLERS.strip() + "\n\n  const handleRepairItem = async", 1)
        print("PILLS_ITEM_FRONTEND_HANDLERS_OK"); landed.append("handlers")
    else:
        print("WARNING: handleRepairItem anchor not found - Pills handlers NOT added")

    # ItemsTab props (type + destructure). The type line is ItemsTab-specific.
    if "onUsePills" in src and "onSellPills" in src:
        print("PILLS_ITEM_FRONTEND_PROPS_ALREADY_APPLIED"); landed.append("props")
    else:
        tline = "  onRepair: (item: EquipmentItem) => void;"
        if tline in src:
            ti = src.find(tline)
            di = src.rfind("  onRepair,\n", 0, ti)
            if di != -1 and ti - di < 2000:
                src = src[:di] + "  onRepair,\n  onUsePills,\n  onSellPills,\n" + src[di + len("  onRepair,\n"):]
                ti = src.find(tline)
                src = src[:ti + len(tline)] + "\n  onUsePills: () => void;\n  onSellPills: () => void;\n  // PILLS_ITEM_FRONTEND_PROPS" + src[ti + len(tline):]
                print("PILLS_ITEM_FRONTEND_PROPS_OK"); landed.append("props")
            else:
                print("WARNING: ItemsTab destructure anchor not found - Pills props NOT added")
        else:
            print("WARNING: ItemsTab props type anchor not found - Pills props NOT added")

    # Parent render passes the handlers.
    if "onUsePills={handleUsePills}" in src:
        print("PILLS_ITEM_FRONTEND_RENDER_ALREADY_APPLIED"); landed.append("render")
    else:
        ri = src.find("onRepair={handleRepairItem}")
        if ri == -1:
            print("WARNING: ItemsTab render anchor not found - Pills handlers NOT wired to the item screen")
        else:
            line_start = src.rfind("\n", 0, ri) + 1
            line_end = src.find("\n", ri)
            indent = src[line_start:ri]
            if indent.strip() != "":
                print("WARNING: ItemsTab render line has unexpected content - Pills handlers NOT wired")
            else:
                src = (src[:line_end + 1] + indent + "onUsePills={handleUsePills}\n"
                       + indent + "onSellPills={handleSellPills}\n" + src[line_end + 1:])
                print("PILLS_ITEM_FRONTEND_RENDER_OK"); landed.append("render")

    # Oz count next to the name (shared with Grass; exactly one occurrence expected).
    if "oz' : ''" in src:
        print("PILLS_ITEM_FRONTEND_QTY_ALREADY_APPLIED"); landed.append("qty")
    else:
        old_name = "{item.name} {item.is_broken && '(BROKEN)'}"
        if src.count(old_name) == 1:
            src = src.replace(old_name,
                              "{item.name}{(item as any).qty ? ' x' + (item as any).qty + ' oz' : ''} {item.is_broken && '(BROKEN)'}", 1)
            print("PILLS_ITEM_FRONTEND_QTY_OK"); landed.append("qty")
        else:
            print("WARNING: item name anchor found %d times (expected 1) - oz count NOT added" % src.count(old_name))

    # Pills action row replacing the generic row for pills rows only.
    if "item.id === 'pills'" in src or "PILLS_ITEM_FRONTEND_ROW" in src:
        print("PILLS_ITEM_FRONTEND_ROW_ALREADY_APPLIED"); landed.append("row")
    else:
        inv_at = src.find("INVENTORY (")
        row_at = -1
        if inv_at != -1:
            pos = inv_at
            while True:
                cand = src.find("<View style={styles.itemActions}>", pos)
                if cand == -1:
                    break
                before = src[inv_at:cand]
                last_tern = before.rfind("{item.id ===")
                if last_tern == -1 or ") : (" in before[last_tern:]:
                    row_at = cand
                    break
                pos = cand + 1
        if row_at == -1:
            print("WARNING: item action row anchor not found - Pills USE/SELL buttons NOT added (generic row would still show for Pills)")
        else:
            line_start = src.rfind("\n", 0, row_at) + 1
            close_at = src.find("</View>", row_at)
            if close_at == -1:
                print("WARNING: item action row end not found - Pills USE/SELL buttons NOT added")
            else:
                end = close_at + len("</View>")
                nested = src[:line_start].rstrip().endswith(") : (")
                if nested:
                    # Inside an existing ternary's else branch: braceless wrap.
                    wrap = ("/* PILLS_ITEM_FRONTEND_ROW */ item.id === 'pills' ? (\n"
                            + PILLS_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n          )")
                else:
                    wrap = ("{/* PILLS_ITEM_FRONTEND_ROW */}\n{item.id === 'pills' ? (\n"
                            + PILLS_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n            )}")
                src = src[:line_start] + wrap + src[end:]
                print("PILLS_ITEM_FRONTEND_ROW_OK"); landed.append("row")

    if delta(src) != orig:
        print("WARNING: balance changed - character.tsx NOT written")
        return 1
    if src == char_orig:
        if "item.id === 'pills'" in src and "usePillsItem" in src and "handleUsePills" in src:
            print("PILLS_ITEM_FRONTEND_ALREADY_APPLIED")
        else:
            print("PILLS_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    CHAR.write_text(src)
    if len(landed) == 7:
        print("PILLS_ITEM_FRONTEND_OK")
    else:
        print("PILLS_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
    return 0

if __name__ == "__main__":
    sys.exit(main())
