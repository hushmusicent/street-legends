#!/usr/bin/env python3
"""Street Legends frontend: Flake item screen (frontend / Expo Go).

Mirrors the Rock Candy frontend patch. The item screen is the GENERIC
inventory list (ItemsTab in character.tsx rendering inventory-details
entries), so Flake appears through the inventory data - no
hardcoded item row is added to the list itself. What this patch does
add, scoped to rows whose item.id is 'flake':
  - the oz count next to the name ("Flake x3 oz"; shared with the
    Grass/Pills/Rock Candy patch's qty part - if any already added it,
    this prints ALREADY_APPLIED for that part),
  - a USE button (+50% armor, 60 seconds) and a SELL 1 OZ ($400)
    button, replacing the generic EQUIP/SELL/REPAIR row for Flake
    rows only (the generic Sell pays value//2 and pops a whole entry,
    and Equip makes no sense for a consumable, so neither may run for
    Flake).
  - parent handlers (handleUseFlake / handleSellFlake)
    following the existing handleSellItem pattern (call api, reload
    all data, alert the result). Sell asks nothing extra: no quantity
    prompt and no confirmation dialog - one tap sells exactly 1 oz
    for $400.
Art: no local asset work is needed. Item rows already render
item.icon_url as an Image (with an Ionicon fallback on error), and the
backend wires Flake's icon_url to an embedded data URI of the
uploaded pink-bag image (no GitHub-hosted file needed).

Row-nesting note: if the Grass, Pills, and/or Rock Candy patches
already wrapped the generic row in {item.id === ... ? ... : (...)}
ternaries, the generic row now sits inside those ternaries' else
branches, where a braced {flake ? ...} wrapper would be a JS block,
not an expression. This patch detects that case (preceding text ends
with ") : (") and wraps bracelessly; otherwise it wraps with braces
as a normal JSX child.

Row-FINDING note (differs from the Pills/Rock Candy patches on
purpose): their ternary-walk loop misfires once braceless prior rows
exist — it lands on the pills row, where a flake branch could never
render (an item cannot be both 'pills' and 'flake'). This patch finds
the generic row by CONTENT instead: the itemActions block that calls
a generic handler (onEquip/onSell/onRepair with item) and none of the
item-specific handlers. If exactly one such block exists, it is wrapped.

Qty-note: the snapshot has TWO "{item.name} {item.is_broken ...}"
lines (one outside ItemsTab), so the Rock Candy exactly-1 rule would
WARNING here. This patch scopes the replacement to the occurrence
after the ItemsTab function start instead.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
API = ROOT / "frontend/services/api.ts"
CHAR = ROOT / "frontend/app/(tabs)/character.tsx"

API_FUNCS = '''
export const useFlakeItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/flake/use`);
  return response.data;
};

export const sellFlakeItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/flake/sell?qty=${qty}`);
  return response.data;
};
'''

HANDLERS = '''
  // FLAKE_ITEM_FRONTEND_HANDLERS: use/sell Flake, mirroring handleSellItem.
  const handleUseFlake = async () => {
    if (!playerId) return;
    try {
      const result = await useFlakeItem(playerId);
      await loadAllData();
      Alert.alert('Flake used!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to use Flake');
    }
  };

  const handleSellFlake = async () => {
    if (!playerId) return;
    try {
      const result = await sellFlakeItem(playerId, 1);
      await loadAllData();
      Alert.alert('Sold!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to sell Flake');
    }
  };
'''

FL_BUTTONS = '''<View style={styles.itemActions}>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.equipActionBtn]}
                onPress={() => onUseFlake()}
              >
                <Ionicons name="shield" size={14} color="#f48fb1" />
                <Text style={[styles.itemActionText, { color: '#f48fb1' }]}>USE (+50% ARMOR 60s)</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.sellActionBtn]}
                onPress={() => onSellFlake()}
              >
                <Ionicons name="cash" size={14} color="#f39c12" />
                <Text style={[styles.itemActionText, { color: '#f39c12' }]}>SELL 1 OZ ($400)</Text>
              </TouchableOpacity>
            </View>'''


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def main():
    landed = []

    # --- api.ts ---
    if not API.exists():
        print("WARNING: services/api.ts not found - Flake api functions NOT added")
    else:
        asrc = API.read_text(errors="ignore")
        if "useFlakeItem" in asrc and "sellFlakeItem" in asrc:
            print("FLAKE_ITEM_FRONTEND_API_ALREADY_APPLIED"); landed.append("api")
        else:
            anchor = ("export const sellItem = async (playerId: string, itemId: string) => {\n"
                      "  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);\n"
                      "  return response.data;\n"
                      "};")
            if anchor in asrc:
                asrc = asrc.replace(anchor, anchor + API_FUNCS, 1)
                API.write_text(asrc)
                print("FLAKE_ITEM_FRONTEND_API_OK"); landed.append("api")
            else:
                print("WARNING: sellItem anchor not found in api.ts - Flake api functions NOT added")

    # --- character.tsx ---
    if not CHAR.exists():
        print("WARNING: character.tsx not found - item screen NOT changed")
        print("FLAKE_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    src = CHAR.read_text(errors="ignore")
    char_orig = src
    orig = delta(src)

    # Imports.
    if "useFlakeItem" in src and "sellFlakeItem" in src:
        print("FLAKE_ITEM_FRONTEND_IMPORTS_ALREADY_APPLIED"); landed.append("imports")
    elif "  sellItem,\n" in src:
        src = src.replace("  sellItem,\n", "  sellItem,\n  useFlakeItem,\n  sellFlakeItem,\n", 1)
        print("FLAKE_ITEM_FRONTEND_IMPORTS_OK"); landed.append("imports")
    else:
        print("WARNING: api import anchor not found - Flake imports NOT added")

    # Parent handlers.
    if "handleUseFlake" in src and "handleSellFlake" in src:
        print("FLAKE_ITEM_FRONTEND_HANDLERS_ALREADY_APPLIED"); landed.append("handlers")
    elif "  const handleRepairItem = async" in src:
        src = src.replace("  const handleRepairItem = async", HANDLERS.strip() + "\n\n  const handleRepairItem = async", 1)
        print("FLAKE_ITEM_FRONTEND_HANDLERS_OK"); landed.append("handlers")
    else:
        print("WARNING: handleRepairItem anchor not found - Flake handlers NOT added")

    # ItemsTab props (type + destructure). The type line is ItemsTab-specific.
    if "onUseFlake" in src and "onSellFlake" in src:
        print("FLAKE_ITEM_FRONTEND_PROPS_ALREADY_APPLIED"); landed.append("props")
    else:
        tline = "  onRepair: (item: EquipmentItem) => void;"
        if tline in src:
            ti = src.find(tline)
            di = src.rfind("  onRepair,\n", 0, ti)
            # Window is 8000, not the 2000 the Grass/Pills patches use:
            # each prior patch's handler block lands between the
            # destructure and the type line and grows the gap.
            if di != -1 and ti - di < 8000:
                src = src[:di] + "  onRepair,\n  onUseFlake,\n  onSellFlake,\n" + src[di + len("  onRepair,\n"):]
                ti = src.find(tline)
                src = src[:ti + len(tline)] + "\n  onUseFlake: () => void;\n  onSellFlake: () => void;\n  // FLAKE_ITEM_FRONTEND_PROPS" + src[ti + len(tline):]
                print("FLAKE_ITEM_FRONTEND_PROPS_OK"); landed.append("props")
            else:
                print("WARNING: ItemsTab destructure anchor not found - Flake props NOT added")
        else:
            print("WARNING: ItemsTab props type anchor not found - Flake props NOT added")

    # Parent render passes the handlers.
    if "onUseFlake={handleUseFlake}" in src:
        print("FLAKE_ITEM_FRONTEND_RENDER_ALREADY_APPLIED"); landed.append("render")
    else:
        ri = src.find("onRepair={handleRepairItem}")
        if ri == -1:
            print("WARNING: ItemsTab render anchor not found - Flake handlers NOT wired to the item screen")
        else:
            line_start = src.rfind("\n", 0, ri) + 1
            line_end = src.find("\n", ri)
            indent = src[line_start:ri]
            if indent.strip() != "":
                print("WARNING: ItemsTab render line has unexpected content - Flake handlers NOT wired")
            else:
                src = (src[:line_end + 1] + indent + "onUseFlake={handleUseFlake}\n"
                       + indent + "onSellFlake={handleSellFlake}\n" + src[line_end + 1:])
                print("FLAKE_ITEM_FRONTEND_RENDER_OK"); landed.append("render")

    # Oz count next to the name (shared with Grass/Pills/Rock Candy).
    # Scoped to ItemsTab: the snapshot has a second name line outside it.
    if "oz' : ''" in src:
        print("FLAKE_ITEM_FRONTEND_QTY_ALREADY_APPLIED"); landed.append("qty")
    else:
        old_name = "{item.name} {item.is_broken && '(BROKEN)'}"
        tab_start = src.find("function ItemsTab({")
        if tab_start == -1:
            print("WARNING: ItemsTab function not found - oz count NOT added")
        else:
            after = src[tab_start:]
            if after.count(old_name) == 1:
                pos = tab_start + after.find(old_name)
                src = src[:pos] + "{item.name}{(item as any).qty ? ' x' + (item as any).qty + ' oz' : ''} {item.is_broken && '(BROKEN)'}" + src[pos + len(old_name):]
                print("FLAKE_ITEM_FRONTEND_QTY_OK"); landed.append("qty")
            else:
                print("WARNING: item name anchor found %d times inside ItemsTab (expected 1) - oz count NOT added" % after.count(old_name))

    # Flake action row replacing the generic row for flake rows only.
    # CONTENT-BASED find (see header): the generic row is the itemActions
    # block that calls a generic handler and no item-specific handler.
    if "item.id === 'flake'" in src or "FLAKE_ITEM_FRONTEND_ROW" in src:
        print("FLAKE_ITEM_FRONTEND_ROW_ALREADY_APPLIED"); landed.append("row")
    else:
        inv_at = src.find("INVENTORY (")
        row_at = -1
        if inv_at != -1:
            pos = inv_at
            generic_hits = []
            while True:
                cand = src.find("<View style={styles.itemActions}>", pos)
                if cand == -1:
                    break
                close_at = src.find("</View>", cand)
                if close_at == -1:
                    break
                block = src[cand:close_at]
                item_specific = any(h in block for h in (
                    "onUseGrass(", "onSellGrass(", "onUsePills(", "onSellPills(",
                    "onUseRockCandy(", "onSellRockCandy(", "onUseFlake(", "onSellFlake("))
                generic_call = any(h in block for h in (
                    "onEquip(item)", "onSell(item)", "onRepair(item)"))
                if generic_call and not item_specific:
                    generic_hits.append(cand)
                pos = cand + 1
            if len(generic_hits) == 1:
                row_at = generic_hits[0]
        if row_at == -1:
            print("WARNING: generic item action row not found - Flake USE/SELL buttons NOT added (generic row would still show for Flake)")
        else:
            line_start = src.rfind("\n", 0, row_at) + 1
            close_at = src.find("</View>", row_at)
            if close_at == -1:
                print("WARNING: item action row end not found - Flake USE/SELL buttons NOT added")
            else:
                end = close_at + len("</View>")
                nested = src[:line_start].rstrip().endswith(") : (")
                if nested:
                    # Inside an existing ternary's else branch: braceless wrap.
                    wrap = ("/* FLAKE_ITEM_FRONTEND_ROW */ item.id === 'flake' ? (\n"
                            + FL_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n          )")
                else:
                    wrap = ("{/* FLAKE_ITEM_FRONTEND_ROW */}\n{item.id === 'flake' ? (\n"
                            + FL_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n            )}")
                src = src[:line_start] + wrap + src[end:]
                print("FLAKE_ITEM_FRONTEND_ROW_OK"); landed.append("row")

    if delta(src) != orig:
        print("WARNING: balance changed - character.tsx NOT written")
        return 1
    if src == char_orig:
        if "item.id === 'flake'" in src and "useFlakeItem" in src and "handleUseFlake" in src:
            print("FLAKE_ITEM_FRONTEND_ALREADY_APPLIED")
        else:
            print("FLAKE_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    CHAR.write_text(src)
    if len(landed) == 7:
        print("FLAKE_ITEM_FRONTEND_OK")
    else:
        print("FLAKE_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
    return 0

if __name__ == "__main__":
    sys.exit(main())
