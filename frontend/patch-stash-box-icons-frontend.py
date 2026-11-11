#!/usr/bin/env python3
"""Street Legends frontend: Stash Box item icons (frontend / Expo Go).

The Stash Box modal (bought, opens fine) shows the five fiend items as
TEXT ONLY: the deposit picker rows ("Grass - $100/oz - 4 oz held") and the
filled slot tiles ("Grass / 1 oz") have no item art next to them. The user
asked: "Where is the icons at".

WHERE THE ART LIVES (diagnosed, not guessed):
- Each item's backend patch added it to ALL_ITEMS with an `icon_url` data
  URI (grass/pills/rock_candy/flake/brown_sugar). All five icon_urls are
  data URIs (80-270 KB each), so there is NO short URL to hardcode and
  re-embedding the art would bloat this patch by ~1 MB. NOT done here.
- The frontend already consumes that art in exactly one place:
  character.tsx `ItemIcon` renders `item.icon_url` as
  `<Image source={{ uri: item.icon_url, cache: 'force-cache' }} />`.
- The clean runtime source for index.tsx is the EXISTING
  `getAllItems()` in services/api.ts (GET /items -> ALL_ITEMS keyed by
  item id). It covers all five items even at 0 oz held (Rock Candy),
  unlike getPlayerInventoryDetails which only returns held items.
  No new backend endpoint, no new base64 in this patch.
- `Image` is already imported and used in index.tsx (the modal header
  renders the chest art fine on device). `STASH_ITEMS` is a local const
  with only {id, name, price} - no icon field - so the modal needs its
  own id -> icon_url map, loaded when the modal opens.

What this patch does, scoped to the Stash Box modal in index.tsx only:
  1. api import: add `getAllItems` to the services/api import block.
  2. icon state + loader, right after the STASH_ITEMS array: a
     `stashItemIcons` map (id -> icon_url) filled from getAllItems()
     whenever the modal opens. Failures are swallowed: rows/slots
     simply render without an icon, exactly as they do today.
  3. deposit picker rows: a 36x36 rounded thumbnail at the left of
     each row, before the item name. Name, $/oz and "N oz held" text
     are byte-unchanged.
  4. filled slot tiles: the same 36x36 thumbnail above the item
     name/qty text, centered. Empty and locked slots are untouched.

Guards: each piece has its own anchor; a missing anchor warns and
leaves that piece unchanged. Idempotent: rerun prints ALREADY_APPLIED.
Nothing else is touched: not the label, row-state, toggle, modal
open/close, deposit/withdraw logic, prices, or any other row.

Run from /app: python3 frontend/patch-stash-box-icons-frontend.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"

MARKER = "STASH_BOX_ICONS_OK"

# Exact STASH_ITEMS block as the stash-box frontend patch inserted it.
STASH_ITEMS_BLOCK = """  const STASH_ITEMS = [
    { id: 'grass', name: 'Grass', price: 100 },
    { id: 'pills', name: 'Pills', price: 200 },
    { id: 'rock_candy', name: 'Rock Candy', price: 300 },
    { id: 'flake', name: 'Flake', price: 400 },
    { id: 'brown_sugar', name: 'Brown Sugar', price: 500 },
  ];"""

ICON_STATE = """
  // STASH_BOX icons: art from GET /items (ALL_ITEMS icon_url) - the same
  // source the item screen renders. Covers all 5 items even at 0 oz held.
  const [stashItemIcons, setStashItemIcons] = useState<Record<string, string>>({});
  const loadStashItemIcons = async () => {
    try {
      const all: any = await getAllItems();
      const icons: Record<string, string> = {};
      for (const id of ['grass', 'pills', 'rock_candy', 'flake', 'brown_sugar']) {
        const u = all?.[id]?.icon_url;
        if (typeof u === 'string' && u) icons[id] = u;
      }
      setStashItemIcons(icons);
    } catch (_) {}
  };
  useEffect(() => { if (stashModalOpen) { loadStashItemIcons(); } }, [stashModalOpen]);"""

PICKER_NAME_OLD = "{it.name} · ${it.price}/oz"
PICKER_NAME_NEW = """<View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
  {stashItemIcons[it.id] ? (<Image source={{ uri: stashItemIcons[it.id] }} style={{ width: 36, height: 36, borderRadius: 8 }} resizeMode="cover" />) : null}
  <Text style={{ color: '#fff', fontWeight: '700' }}>{it.name} · ${it.price}/oz</Text>
</View>"""

SLOT_NAME_LINE = "{item ? item.name : entry.item}"
SLOT_ICON_LINE = "                  {item && stashItemIcons[entry.item] ? (<Image source={{ uri: stashItemIcons[entry.item] }} style={{ width: 36, height: 36, borderRadius: 8, marginBottom: 2 }} resizeMode=\"cover\" />) : null}"


def delta(s):
    """Balance deltas only (raw counts grow with every insert)."""
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"), s.count("[") - s.count("]"))


def main():
    landed = []
    warned = []

    if not INDEX.exists():
        print("WARNING: frontend/app/(tabs)/index.tsx not found - Stash Box icons NOT added")
        print("STASH_BOX_ICONS_PARTIAL: (warnings: index)")
        return
    src = INDEX.read_text(errors="ignore")
    orig = src
    i0 = delta(src)

    # 0. Already applied?
    if "stashItemIcons" in src and "stashItemIcons[it.id]" in src and "stashItemIcons[entry.item]" in src:
        print("STASH_BOX_ICONS_ALREADY_APPLIED")
        print(MARKER)
        return

    # 1. api import: getAllItems into the services/api import block.
    import_ok = False
    m = re.search(r"import\s+\{([^}]*)\}\s*from\s*['\"]\.\./\.\./services/api['\"]", src)
    if m:
        if "getAllItems" in m.group(1):
            print("STASH_BOX_ICONS_IMPORT_ALREADY_APPLIED")
            import_ok = True
        else:
            close = src.find("} from '../../services/api';", m.start())
            if close < 0:
                close = src.find('} from "../../services/api";', m.start())
            if close >= 0:
                src = src[:close] + "  getAllItems,\n" + src[close:]
                print("STASH_BOX_ICONS_IMPORT_OK")
                import_ok = True
            else:
                print("WARNING: services/api import close not found - getAllItems NOT imported")
                warned.append("index-import")
    else:
        print("WARNING: services/api import block not found in index.tsx - getAllItems NOT imported")
        warned.append("index-import")

    if not import_ok:
        # The loader references getAllItems; without the import the file
        # would not compile. Skip the dependent pieces entirely.
        print("STASH_BOX_ICONS_PARTIAL: (warnings: " + ",".join(warned) + ")")
        return

    # 2. Icon state + loader, right after the STASH_ITEMS array.
    if "stashItemIcons" in src:
        print("STASH_BOX_ICONS_STATE_ALREADY_APPLIED")
    elif src.count(STASH_ITEMS_BLOCK) == 1:
        src = src.replace(STASH_ITEMS_BLOCK, STASH_ITEMS_BLOCK + ICON_STATE, 1)
        print("STASH_BOX_ICONS_STATE_OK")
    else:
        print(f"WARNING: STASH_ITEMS block matched {src.count(STASH_ITEMS_BLOCK)}x - icon state NOT added")
        warned.append("index-icons-state")

    # 3. Deposit picker rows: thumbnail before the item name.
    if "stashItemIcons[it.id]" in src:
        print("STASH_BOX_ICONS_PICKER_ALREADY_APPLIED")
    else:
        lines = src.split("\n")
        hits = [i for i, ln in enumerate(lines) if PICKER_NAME_OLD in ln]
        if len(hits) != 1:
            print(f"WARNING: deposit picker row matched {len(hits)}x - picker icons NOT added (expected exactly 1 line with '{{it.name}} - ${{it.price}}/oz')")
            warned.append("index-picker")
        else:
            i = hits[0]
            opener = lines[i - 1] if i > 0 else ""
            if "key={it.id}" not in opener:
                print("WARNING: deposit picker row opener not found above the name line - picker icons NOT added")
                warned.append("index-picker")
            elif "justifyContent: 'space-between', " not in opener:
                print("WARNING: deposit picker row style differs from the assumed shape - picker icons NOT added")
                warned.append("index-picker")
            else:
                lines[i - 1] = opener.replace(
                    "justifyContent: 'space-between', ",
                    "justifyContent: 'space-between', alignItems: 'center', ", 1)
                indent = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
                new_block = [indent + ln for ln in PICKER_NAME_NEW.split("\n")]
                lines[i:i + 1] = new_block
                src = "\n".join(lines)
                print("STASH_BOX_ICONS_PICKER_OK")

    # 4. Filled slot tiles: thumbnail above the item name.
    if "stashItemIcons[entry.item]" in src:
        print("STASH_BOX_ICONS_SLOT_ALREADY_APPLIED")
    else:
        lines = src.split("\n")
        hits = [i for i, ln in enumerate(lines) if SLOT_NAME_LINE in ln]
        if len(hits) != 1:
            print(f"WARNING: filled slot name line matched {len(hits)}x - slot icons NOT added (expected exactly 1 line with '{{item ? item.name : entry.item}}')")
            warned.append("index-slot")
        else:
            lines.insert(hits[0], SLOT_ICON_LINE)
            src = "\n".join(lines)
            print("STASH_BOX_ICONS_SLOT_OK")

    if delta(src) != i0:
        print("WARNING: balance changed - index.tsx NOT written")
        warned.append("index-balance")
    elif src != orig:
        INDEX.write_text(src)
        landed.append("index")

    if warned:
        print("STASH_BOX_ICONS_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warned) + ")")
    else:
        print(MARKER)


if __name__ == "__main__":
    main()
