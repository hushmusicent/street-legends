#!/usr/bin/env python3
"""Street Legends frontend: Rock Candy item screen (frontend / Expo Go).

Mirrors the Pills frontend patch. The item screen is the GENERIC
inventory list (ItemsTab in character.tsx rendering inventory-details
entries), so Rock Candy appears through the inventory data - no
hardcoded item row is added to the list itself. What this patch does
add, scoped to rows whose item.id is 'rock_candy':
  - the oz count next to the name ("Rock Candy x3 oz"; shared with the
    Grass/Pills patch's qty part - if either already added it, this
    prints ALREADY_APPLIED for that part),
  - a USE button (+50% attack, 60 seconds) and a SELL 1 OZ ($300)
    button, replacing the generic EQUIP/SELL/REPAIR row for Rock Candy
    rows only (the generic Sell pays value//2 and pops a whole entry,
    and Equip makes no sense for a consumable, so neither may run for
    Rock Candy).
  - parent handlers (handleUseRockCandy / handleSellRockCandy)
    following the existing handleSellItem pattern (call api, reload
    all data, alert the result). Sell asks nothing extra: no quantity
    prompt and no confirmation dialog - one tap sells exactly 1 oz
    for $300.
Art: no local asset work is needed. Item rows already render
item.icon_url as an Image (with an Ionicon fallback on error), and the
backend wires Rock Candy's icon_url to an embedded data URI of the
uploaded crystal-bag image (no GitHub-hosted file needed).

Row-nesting note: if the Grass and/or Pills patches already wrapped
the generic row in {item.id === ... ? ... : (...)} ternaries, the
generic row now sits inside those ternaries' else branches, where a
braced {rock_candy ? ...} wrapper would be a JS block, not an
expression. This patch reuses the Pills detection (preceding text ends
with ") : (") and wraps bracelessly in that case; otherwise it wraps
with braces as a normal JSX child.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
API = ROOT / "frontend/services/api.ts"
CHAR = ROOT / "frontend/app/(tabs)/character.tsx"

API_FUNCS = '''
export const useRockCandyItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/rock-candy/use`);
  return response.data;
};

export const sellRockCandyItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/rock-candy/sell?qty=${qty}`);
  return response.data;
};
'''

HANDLERS = '''
  // ROCK_CANDY_ITEM_FRONTEND_HANDLERS: use/sell Rock Candy, mirroring handleSellItem.
  const handleUseRockCandy = async () => {
    if (!playerId) return;
    try {
      const result = await useRockCandyItem(playerId);
      await loadAllData();
      Alert.alert('Rock Candy used!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to use Rock Candy');
    }
  };

  const handleSellRockCandy = async () => {
    if (!playerId) return;
    try {
      const result = await sellRockCandyItem(playerId, 1);
      await loadAllData();
      Alert.alert('Sold!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to sell Rock Candy');
    }
  };
'''

RC_BUTTONS = '''<View style={styles.itemActions}>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.equipActionBtn]}
                onPress={() => onUseRockCandy()}
              >
                <Ionicons name="diamond" size={14} color="#ce93d8" />
                <Text style={[styles.itemActionText, { color: '#ce93d8' }]}>USE (+50% ATTACK 60s)</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.sellActionBtn]}
                onPress={() => onSellRockCandy()}
              >
                <Ionicons name="cash" size={14} color="#f39c12" />
                <Text style={[styles.itemActionText, { color: '#f39c12' }]}>SELL 1 OZ ($300)</Text>
              </TouchableOpacity>
            </View>'''


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def main():
    landed = []

    # --- api.ts ---
    if not API.exists():
        print("WARNING: services/api.ts not found - Rock Candy api functions NOT added")
    else:
        asrc = API.read_text(errors="ignore")
        if "useRockCandyItem" in asrc and "sellRockCandyItem" in asrc:
            print("ROCK_CANDY_ITEM_FRONTEND_API_ALREADY_APPLIED"); landed.append("api")
        else:
            anchor = ("export const sellItem = async (playerId: string, itemId: string) => {\n"
                      "  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);\n"
                      "  return response.data;\n"
                      "};")
            if anchor in asrc:
                asrc = asrc.replace(anchor, anchor + API_FUNCS, 1)
                API.write_text(asrc)
                print("ROCK_CANDY_ITEM_FRONTEND_API_OK"); landed.append("api")
            else:
                print("WARNING: sellItem anchor not found in api.ts - Rock Candy api functions NOT added")

    # --- character.tsx ---
    if not CHAR.exists():
        print("WARNING: character.tsx not found - item screen NOT changed")
        print("ROCK_CANDY_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    src = CHAR.read_text(errors="ignore")
    char_orig = src
    orig = delta(src)

    # Imports.
    if "useRockCandyItem" in src and "sellRockCandyItem" in src:
        print("ROCK_CANDY_ITEM_FRONTEND_IMPORTS_ALREADY_APPLIED"); landed.append("imports")
    elif "  sellItem,\n" in src:
        src = src.replace("  sellItem,\n", "  sellItem,\n  useRockCandyItem,\n  sellRockCandyItem,\n", 1)
        print("ROCK_CANDY_ITEM_FRONTEND_IMPORTS_OK"); landed.append("imports")
    else:
        print("WARNING: api import anchor not found - Rock Candy imports NOT added")

    # Parent handlers.
    if "handleUseRockCandy" in src and "handleSellRockCandy" in src:
        print("ROCK_CANDY_ITEM_FRONTEND_HANDLERS_ALREADY_APPLIED"); landed.append("handlers")
    elif "  const handleRepairItem = async" in src:
        src = src.replace("  const handleRepairItem = async", HANDLERS.strip() + "\n\n  const handleRepairItem = async", 1)
        print("ROCK_CANDY_ITEM_FRONTEND_HANDLERS_OK"); landed.append("handlers")
    else:
        print("WARNING: handleRepairItem anchor not found - Rock Candy handlers NOT added")

    # ItemsTab props (type + destructure). The type line is ItemsTab-specific.
    if "onUseRockCandy" in src and "onSellRockCandy" in src:
        print("ROCK_CANDY_ITEM_FRONTEND_PROPS_ALREADY_APPLIED"); landed.append("props")
    else:
        tline = "  onRepair: (item: EquipmentItem) => void;"
        if tline in src:
            ti = src.find(tline)
            di = src.rfind("  onRepair,\n", 0, ti)
            # Window is 8000, not the 2000 the Grass/Pills patches use:
            # each prior patch's handler block lands between the
            # destructure and the type line and grows the gap.
            if di != -1 and ti - di < 8000:
                src = src[:di] + "  onRepair,\n  onUseRockCandy,\n  onSellRockCandy,\n" + src[di + len("  onRepair,\n"):]
                ti = src.find(tline)
                src = src[:ti + len(tline)] + "\n  onUseRockCandy: () => void;\n  onSellRockCandy: () => void;\n  // ROCK_CANDY_ITEM_FRONTEND_PROPS" + src[ti + len(tline):]
                print("ROCK_CANDY_ITEM_FRONTEND_PROPS_OK"); landed.append("props")
            else:
                print("WARNING: ItemsTab destructure anchor not found - Rock Candy props NOT added")
        else:
            print("WARNING: ItemsTab props type anchor not found - Rock Candy props NOT added")

    # Parent render passes the handlers.
    if "onUseRockCandy={handleUseRockCandy}" in src:
        print("ROCK_CANDY_ITEM_FRONTEND_RENDER_ALREADY_APPLIED"); landed.append("render")
    else:
        ri = src.find("onRepair={handleRepairItem}")
        if ri == -1:
            print("WARNING: ItemsTab render anchor not found - Rock Candy handlers NOT wired to the item screen")
        else:
            line_start = src.rfind("\n", 0, ri) + 1
            line_end = src.find("\n", ri)
            indent = src[line_start:ri]
            if indent.strip() != "":
                print("WARNING: ItemsTab render line has unexpected content - Rock Candy handlers NOT wired")
            else:
                src = (src[:line_end + 1] + indent + "onUseRockCandy={handleUseRockCandy}\n"
                       + indent + "onSellRockCandy={handleSellRockCandy}\n" + src[line_end + 1:])
                print("ROCK_CANDY_ITEM_FRONTEND_RENDER_OK"); landed.append("render")

    # Oz count next to the name (shared with Grass/Pills; exactly one occurrence expected).
    if "oz' : ''" in src:
        print("ROCK_CANDY_ITEM_FRONTEND_QTY_ALREADY_APPLIED"); landed.append("qty")
    else:
        old_name = "{item.name} {item.is_broken && '(BROKEN)'}"
        if src.count(old_name) == 1:
            src = src.replace(old_name,
                              "{item.name}{(item as any).qty ? ' x' + (item as any).qty + ' oz' : ''} {item.is_broken && '(BROKEN)'}", 1)
            print("ROCK_CANDY_ITEM_FRONTEND_QTY_OK"); landed.append("qty")
        else:
            print("WARNING: item name anchor found %d times (expected 1) - oz count NOT added" % src.count(old_name))

    # Rock Candy action row replacing the generic row for rock_candy rows only.
    if "item.id === 'rock_candy'" in src or "ROCK_CANDY_ITEM_FRONTEND_ROW" in src:
        print("ROCK_CANDY_ITEM_FRONTEND_ROW_ALREADY_APPLIED"); landed.append("row")
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
            print("WARNING: item action row anchor not found - Rock Candy USE/SELL buttons NOT added (generic row would still show for Rock Candy)")
        else:
            line_start = src.rfind("\n", 0, row_at) + 1
            close_at = src.find("</View>", row_at)
            if close_at == -1:
                print("WARNING: item action row end not found - Rock Candy USE/SELL buttons NOT added")
            else:
                end = close_at + len("</View>")
                nested = src[:line_start].rstrip().endswith(") : (")
                if nested:
                    # Inside an existing ternary's else branch: braceless wrap.
                    wrap = ("/* ROCK_CANDY_ITEM_FRONTEND_ROW */ item.id === 'rock_candy' ? (\n"
                            + RC_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n          )")
                else:
                    wrap = ("{/* ROCK_CANDY_ITEM_FRONTEND_ROW */}\n{item.id === 'rock_candy' ? (\n"
                            + RC_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n            )}")
                src = src[:line_start] + wrap + src[end:]
                print("ROCK_CANDY_ITEM_FRONTEND_ROW_OK"); landed.append("row")

    if delta(src) != orig:
        print("WARNING: balance changed - character.tsx NOT written")
        return 1
    if src == char_orig:
        if "item.id === 'rock_candy'" in src and "useRockCandyItem" in src and "handleUseRockCandy" in src:
            print("ROCK_CANDY_ITEM_FRONTEND_ALREADY_APPLIED")
        else:
            print("ROCK_CANDY_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    CHAR.write_text(src)
    if len(landed) == 7:
        print("ROCK_CANDY_ITEM_FRONTEND_OK")
    else:
        print("ROCK_CANDY_ITEM_FRONTEND_PARTIAL: " + ",".join(landed))
    return 0

if __name__ == "__main__":
    sys.exit(main())
