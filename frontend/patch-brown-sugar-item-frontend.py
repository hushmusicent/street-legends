#!/usr/bin/env python3
"""Street Legends frontend: Brown Sugar item screen (frontend / Expo Go).

Mirrors the Flake frontend patch. The item screen is the GENERIC
inventory list (ItemsTab in character.tsx rendering inventory-details
entries), so Brown Sugar appears through the inventory data - no
hardcoded item row is added to the list itself. What this patch does
add, scoped to rows whose item.id is 'brown_sugar':
  - the oz count next to the name ("Brown Sugar x3 oz"; shared with the
    Grass/Pills/Rock Candy/Flake patch's qty part - if any already added
    it, this prints ALREADY_APPLIED for that part),
  - a USE button (+50% luck, 60 seconds) and a SELL 1 OZ ($500)
    button, replacing the generic EQUIP/SELL/REPAIR row for Brown Sugar
    rows only (the generic Sell pays value//2 and pops a whole entry,
    and Equip makes no sense for a consumable, so neither may run for
    Brown Sugar).
  - parent handlers (handleUseBrownSugar / handleSellBrownSugar)
    following the existing handleSellItem pattern (call api, reload
    all data, alert the result). Sell asks nothing extra: no quantity
    prompt and no confirmation dialog - one tap sells exactly 1 oz
    for $500.
Art: no local asset work is needed. Item rows already render
item.icon_url as an Image (with an Ionicon fallback on error), and the
backend wires Brown Sugar's icon_url to an embedded data URI of the
uploaded pink-bag image (no GitHub-hosted file needed).

ONCE-ONLY RULE (user, 09:11 EST, extended 09:15 EST "For other 4
also"): the player can only use the same item once until its effect
wears off - for ALL FIVE items (Brown Sugar + Grass + Pills + Rock
Candy + Flake). This patch therefore ALSO blocks the four existing
item rows while their own buff is active:
  - the parent computes one active flag per item from
    player.active_buffs (own buff only, expiry-checked);
  - each of the five USE buttons gets disabled={...Active} and its
    label switches to "<STAT> ACTIVE" while active, so the tap never
    silently disappears;
  - the backend is still the source of truth: a stale client flag can
    still reach the endpoint, which rejects with HTTP 400 and the
    handler shows that message in an alert. No existing handler is
    rewritten - the four existing handlers already alert the backend
    error detail on failure.
  - SELL is never blocked by the rule (selling while a buff is active
    is allowed; the buff itself is untouched).

Row-nesting note: if the Grass, Pills, Rock Candy, and/or Flake
patches already wrapped the generic row in {item.id === ... ? ... : (...)}
ternaries, the generic row now sits inside those ternaries' else
branches, where a braced {brown_sugar ? ...} wrapper would be a JS
block, not an expression. This patch detects that case (preceding text
ends with ") : (") and wraps bracelessly; otherwise it wraps with braces
as a normal JSX child.

Row-FINDING note (copied from the Flake frontend patch): the generic
row is found by CONTENT, not by a ternary walk - the itemActions block
that calls a generic handler (onEquip/onSell/onRepair with item) and
none of the item-specific handlers. If exactly one such block exists,
it is wrapped.

Qty-note: the snapshot has TWO "{item.name} {item.is_broken ...}"
lines (one outside ItemsTab), so the Rock Candy exactly-1 rule would
WARNING here. This patch scopes the replacement to the occurrence
after the ItemsTab function start instead.

Api-naming note: Emergent renamed the earlier items' api functions
use* -> consume* in live services/api.ts (character.tsx still calls
the use* names, bridged by alias exports the white-screen repair
added). This patch is count-guarded and checks BOTH names: if live
api.ts already exports consumeBrownSugarItem, it is treated as the
use-function and NO duplicate is added - only the alias export
`export const useBrownSugarItem = consumeBrownSugarItem;` is appended
at the END of the file (never mid-file: the alias is evaluated at
import time, so consumeBrownSugarItem must already be defined above
it). The sell function is added only when its export count is zero.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
API = ROOT / "frontend/services/api.ts"
CHAR = ROOT / "frontend/app/(tabs)/character.tsx"

USE_FUNC = '''
export const useBrownSugarItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/brown_sugar/use`);
  return response.data;
};
'''

SELL_FUNC = '''
export const sellBrownSugarItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/brown_sugar/sell?qty=${qty}`);
  return response.data;
};
'''

API_ALIAS = '''
// BROWN_SUGAR_FRONTEND_API_ALIAS: character.tsx calls useBrownSugarItem; live api.ts exports consumeBrownSugarItem.
export const useBrownSugarItem = consumeBrownSugarItem;
'''

FLAGS = '''  // BROWN_SUGAR_FRONTEND_FLAGS: once-only rule - each item's buff is read from player.active_buffs (own buff only, expiry-checked).
  const brownSugarActive = ((player as any)?.active_buffs || []).some((b: any) => b.item_id === 'brown_sugar' && (!b.expires_at || b.expires_at >= new Date().toISOString()));
  const grassActive = ((player as any)?.active_buffs || []).some((b: any) => b.item_id === 'grass' && (!b.expires_at || b.expires_at >= new Date().toISOString()));
  const pillsActive = ((player as any)?.active_buffs || []).some((b: any) => b.item_id === 'pills' && (!b.expires_at || b.expires_at >= new Date().toISOString()));
  const rockCandyActive = ((player as any)?.active_buffs || []).some((b: any) => b.item_id === 'rock_candy' && (!b.expires_at || b.expires_at >= new Date().toISOString()));
  const flakeActive = ((player as any)?.active_buffs || []).some((b: any) => b.item_id === 'flake' && (!b.expires_at || b.expires_at >= new Date().toISOString()));'''

HANDLERS = '''  // BROWN_SUGAR_ITEM_FRONTEND_HANDLERS: use/sell Brown Sugar, mirroring handleSellItem.
  // On a blocked re-use the backend returns HTTP 400 and the alert shows its message.
  const handleUseBrownSugar = async () => {
    if (!playerId) return;
    try {
      const result = await useBrownSugarItem(playerId);
      await loadAllData();
      Alert.alert('Brown Sugar used!', result.message);
    } catch (error: any) {
      Alert.alert('Brown Sugar', error?.response?.data?.detail || 'Failed to use Brown Sugar');
    }
  };

  const handleSellBrownSugar = async () => {
    if (!playerId) return;
    try {
      const result = await sellBrownSugarItem(playerId, 1);
      await loadAllData();
      Alert.alert('Sold!', result.message);
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Failed to sell Brown Sugar');
    }
  };'''

BS_BUTTONS = '''<View style={styles.itemActions}>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.equipActionBtn]}
                onPress={() => onUseBrownSugar()}
                disabled={brownSugarActive}
              >
                <Ionicons name="clover" size={14} color="#9b59b6" />
                <Text style={[styles.itemActionText, { color: '#9b59b6' }]}>{brownSugarActive ? 'LUCK ACTIVE' : 'USE (+50% LUCK 60s)'}</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={[styles.itemActionBtn, styles.sellActionBtn]}
                onPress={() => onSellBrownSugar()}
              >
                <Ionicons name="cash" size={14} color="#f39c12" />
                <Text style={[styles.itemActionText, { color: '#f39c12' }]}>SELL 1 OZ ($500)</Text>
              </TouchableOpacity>
            </View>'''

# Existing rows: (item handler name, active flag, button label, active label).
EXISTING_ROWS = [
    ("Grass", "onUseGrass", "grassActive", "USE (+50% HP 60s)", "HP ACTIVE"),
    ("Pills", "onUsePills", "pillsActive", "USE (+50% ENERGY 60s)", "ENERGY ACTIVE"),
    ("RockCandy", "onUseRockCandy", "rockCandyActive", "USE (+50% ATTACK 60s)", "ATTACK ACTIVE"),
    ("Flake", "onUseFlake", "flakeActive", "USE (+50% ARMOR 60s)", "ARMOR ACTIVE"),
]


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def main():
    landed = []

    # --- api.ts (count-guarded; checks BOTH use* and consume* names) ---
    if not API.exists():
        print("WARNING: services/api.ts not found - Brown Sugar api functions NOT added")
    else:
        asrc = API.read_text(errors="ignore")
        use_n = asrc.count("useBrownSugarItem")
        con_n = asrc.count("consumeBrownSugarItem")
        sell_n = asrc.count("sellBrownSugarItem")
        if use_n >= 1 and sell_n >= 1:
            print("BROWN_SUGAR_FRONTEND_API_ALREADY_APPLIED"); landed.append("api")
        else:
            anchor = ("export const sellItem = async (playerId: string, itemId: string) => {\n"
                      "  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);\n"
                      "  return response.data;\n"
                      "};")
            add = ""
            if use_n == 0 and con_n == 0:
                add += USE_FUNC
            if sell_n == 0:
                add += SELL_FUNC
            changed = False
            if add:
                if anchor in asrc:
                    asrc = asrc.replace(anchor, anchor + add, 1)
                    changed = True
                    print("BROWN_SUGAR_FRONTEND_API_OK")
                else:
                    print("WARNING: sellItem anchor not found in api.ts - Brown Sugar api functions NOT added")
            if use_n == 0 and con_n >= 1:
                # Alias at END of file only: it is evaluated at import time,
                # so consumeBrownSugarItem must already be defined above it.
                asrc = asrc + API_ALIAS
                changed = True
                print("BROWN_SUGAR_FRONTEND_API_USE_ALIAS_OK")
            if changed:
                API.write_text(asrc)
                landed.append("api")

    # --- character.tsx ---
    if not CHAR.exists():
        print("WARNING: character.tsx not found - item screen NOT changed")
        print("BROWN_SUGAR_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    src = CHAR.read_text(errors="ignore")
    char_orig = src
    orig = delta(src)

    # Imports.
    if "useBrownSugarItem" in src and "sellBrownSugarItem" in src:
        print("BROWN_SUGAR_FRONTEND_IMPORTS_ALREADY_APPLIED"); landed.append("imports")
    elif "  sellItem,\n" in src:
        src = src.replace("  sellItem,\n", "  sellItem,\n  useBrownSugarItem,\n  sellBrownSugarItem,\n", 1)
        print("BROWN_SUGAR_FRONTEND_IMPORTS_OK"); landed.append("imports")
    else:
        print("WARNING: api import anchor not found - Brown Sugar imports NOT added")

    # Parent handlers + active flags (two independent inserts, same anchor).
    _h_done = _f_done = False
    if "handleUseBrownSugar" in src and "handleSellBrownSugar" in src:
        print("BROWN_SUGAR_FRONTEND_HANDLERS_ALREADY_APPLIED"); _h_done = True
    elif "  const handleRepairItem = async" in src:
        src = src.replace("  const handleRepairItem = async", HANDLERS.strip() + "\n\n  const handleRepairItem = async", 1)
        print("BROWN_SUGAR_FRONTEND_HANDLERS_OK"); _h_done = True
    else:
        print("WARNING: handleRepairItem anchor not found - Brown Sugar handlers NOT added")
    _flag_names = ("brownSugarActive", "grassActive", "pillsActive", "rockCandyActive", "flakeActive")
    if all(x in src for x in _flag_names):
        print("BROWN_SUGAR_FRONTEND_FLAGS_ALREADY_APPLIED"); _f_done = True
    elif "  const handleRepairItem = async" in src:
        src = src.replace("  const handleRepairItem = async", FLAGS.strip() + "\n\n  const handleRepairItem = async", 1)
        print("BROWN_SUGAR_FRONTEND_FLAGS_OK"); _f_done = True
    else:
        print("WARNING: handleRepairItem anchor not found - active flags NOT added")
    if _h_done and _f_done:
        landed.append("handlers")

    # ItemsTab props (type + destructure): Brown Sugar handlers + all five active flags.
    # Presence is checked on the ItemsTab TYPE lines only - the flag consts live in the
    # parent component (added by the FLAGS part above), so their names being in the file
    # does NOT mean the props were added.
    _prop_type_markers = ("onUseBrownSugar: () => void;", "brownSugarActive: boolean;")
    if all(x in src for x in _prop_type_markers):
        print("BROWN_SUGAR_FRONTEND_PROPS_ALREADY_APPLIED"); landed.append("props")
    elif any(x in src for x in _prop_type_markers):
        print("WARNING: ItemsTab props partially present - Brown Sugar props NOT added (hand-fix needed)")
    else:
        tline = "  onRepair: (item: EquipmentItem) => void;"
        if tline in src:
            ti = src.find(tline)
            di = src.rfind("  onRepair,\n", 0, ti)
            # Window is 8000, not the 2000 the Grass/Pills patches use:
            # each prior patch's handler block lands between the
            # destructure and the type line and grows the gap.
            if di != -1 and ti - di < 8000:
                src = src[:di] + "  onRepair,\n  onUseBrownSugar,\n  onSellBrownSugar,\n  brownSugarActive,\n  grassActive,\n  pillsActive,\n  rockCandyActive,\n  flakeActive,\n" + src[di + len("  onRepair,\n"):]
                ti = src.find(tline)
                src = src[:ti + len(tline)] + "\n  onUseBrownSugar: () => void;\n  onSellBrownSugar: () => void;\n  brownSugarActive: boolean;\n  grassActive: boolean;\n  pillsActive: boolean;\n  rockCandyActive: boolean;\n  flakeActive: boolean;\n  // BROWN_SUGAR_ITEM_FRONTEND_PROPS" + src[ti + len(tline):]
                print("BROWN_SUGAR_FRONTEND_PROPS_OK"); landed.append("props")
            else:
                print("WARNING: ItemsTab destructure anchor not found - Brown Sugar props NOT added")
        else:
            print("WARNING: ItemsTab props type anchor not found - Brown Sugar props NOT added")

    # Parent render passes the handlers + active flags.
    _render_lines = ("onUseBrownSugar={handleUseBrownSugar}", "onSellBrownSugar={handleSellBrownSugar}",
                     "brownSugarActive={brownSugarActive}", "grassActive={grassActive}",
                     "pillsActive={pillsActive}", "rockCandyActive={rockCandyActive}",
                     "flakeActive={flakeActive}")
    if all(x in src for x in _render_lines):
        print("BROWN_SUGAR_FRONTEND_RENDER_ALREADY_APPLIED"); landed.append("render")
    elif any(x in src for x in _render_lines):
        print("WARNING: ItemsTab render partially present - Brown Sugar render props NOT added (hand-fix needed)")
    else:
        ri = src.find("onRepair={handleRepairItem}")
        if ri == -1:
            print("WARNING: ItemsTab render anchor not found - Brown Sugar handlers NOT wired to the item screen")
        else:
            line_start = src.rfind("\n", 0, ri) + 1
            line_end = src.find("\n", ri)
            indent = src[line_start:ri]
            if indent.strip() != "":
                print("WARNING: ItemsTab render line has unexpected content - Brown Sugar handlers NOT wired")
            else:
                extra = "".join(indent + x + "\n" for x in _render_lines)
                src = src[:line_end + 1] + extra + src[line_end + 1:]
                print("BROWN_SUGAR_FRONTEND_RENDER_OK"); landed.append("render")

    # Oz count next to the name (shared with Grass/Pills/Rock Candy/Flake).
    # Scoped to ItemsTab: the snapshot has a second name line outside it.
    if "oz' : ''" in src:
        print("BROWN_SUGAR_FRONTEND_QTY_ALREADY_APPLIED"); landed.append("qty")
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
                print("BROWN_SUGAR_FRONTEND_QTY_OK"); landed.append("qty")
            else:
                print("WARNING: item name anchor found %d times inside ItemsTab (expected 1) - oz count NOT added" % after.count(old_name))

    # Brown Sugar action row replacing the generic row for brown_sugar rows only.
    # CONTENT-BASED find (see header): the generic row is the itemActions
    # block that calls a generic handler and no item-specific handler.
    if "item.id === 'brown_sugar'" in src or "BROWN_SUGAR_ITEM_FRONTEND_ROW" in src:
        print("BROWN_SUGAR_FRONTEND_ROW_ALREADY_APPLIED"); landed.append("row")
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
                    "onUseRockCandy(", "onSellRockCandy(", "onUseFlake(", "onSellFlake(",
                    "onUseBrownSugar(", "onSellBrownSugar("))
                generic_call = any(h in block for h in (
                    "onEquip(item)", "onSell(item)", "onRepair(item)"))
                if generic_call and not item_specific:
                    generic_hits.append(cand)
                pos = cand + 1
            if len(generic_hits) == 1:
                row_at = generic_hits[0]
        if row_at == -1:
            print("WARNING: generic item action row not found - Brown Sugar USE/SELL buttons NOT added (generic row would still show for Brown Sugar)")
        else:
            line_start = src.rfind("\n", 0, row_at) + 1
            close_at = src.find("</View>", row_at)
            if close_at == -1:
                print("WARNING: item action row end not found - Brown Sugar USE/SELL buttons NOT added")
            else:
                end = close_at + len("</View>")
                nested = src[:line_start].rstrip().endswith(") : (")
                if nested:
                    # Inside an existing ternary's else branch: braceless wrap.
                    wrap = ("/* BROWN_SUGAR_ITEM_FRONTEND_ROW */ item.id === 'brown_sugar' ? (\n"
                            + BS_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n          )")
                else:
                    wrap = ("{/* BROWN_SUGAR_ITEM_FRONTEND_ROW */}\n{item.id === 'brown_sugar' ? (\n"
                            + BS_BUTTONS + "\n          ) : (\n"
                            + src[line_start:end] + "\n            )}")
                src = src[:line_start] + wrap + src[end:]
                print("BROWN_SUGAR_FRONTEND_ROW_OK"); landed.append("row")

    # Blocked state on the four EXISTING rows: disable the USE button and
    # switch its label while that item's own buff is active. Each item is
    # independent; a missing row only warns for that item.
    _block_done = []
    for _rb_name, _rb_handler, _rb_flag, _rb_label, _rb_active in EXISTING_ROWS:
        _rb_press = "onPress={() => %s()}" % _rb_handler
        if ("disabled={%s}" % _rb_flag) in src:
            print("BROWN_SUGAR_FRONTEND_BLOCK_%s_ALREADY_APPLIED" % _rb_name.upper()); _block_done.append(_rb_name); continue
        if src.count(_rb_press) != 1 or src.count(">" + _rb_label + "</Text>") != 1:
            print("WARNING: %s USE button not found exactly once (press x%d, label x%d) - blocked state NOT added for %s" % (
                _rb_name, src.count(_rb_press), src.count(">" + _rb_label + "</Text>"), _rb_name))
            continue
        src = src.replace(_rb_press, _rb_press + "\n                disabled={%s}" % _rb_flag, 1)
        src = src.replace(">" + _rb_label + "</Text>",
                          ">{" + _rb_flag + " ? '" + _rb_active + "' : '" + _rb_label + "'}</Text>", 1)
        print("BROWN_SUGAR_FRONTEND_BLOCK_%s_OK" % _rb_name.upper()); _block_done.append(_rb_name)
    if len(_block_done) == 4:
        landed.append("rowsblock")
    elif _block_done:
        print("BROWN_SUGAR_FRONTEND_ROWSBLOCK_PARTIAL: " + ",".join(_block_done))

    if delta(src) != orig:
        print("WARNING: balance changed - character.tsx NOT written")
        return 1
    if src == char_orig:
        if "item.id === 'brown_sugar'" in src and "useBrownSugarItem" in src and "handleUseBrownSugar" in src:
            print("BROWN_SUGAR_FRONTEND_ALREADY_APPLIED")
        else:
            print("BROWN_SUGAR_FRONTEND_PARTIAL: " + ",".join(landed))
        return 0
    CHAR.write_text(src)
    if len(landed) == 8:
        print("BROWN_SUGAR_FRONTEND_OK")
    else:
        print("BROWN_SUGAR_FRONTEND_PARTIAL: " + ",".join(landed))
    return 0

if __name__ == "__main__":
    sys.exit(main())
