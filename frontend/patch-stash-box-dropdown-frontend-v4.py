#!/usr/bin/env python3
"""Street Legends frontend: Stash Box dropdown follow-up #4 — Expo Go.

v1 landed the TOGGLE intercept. v2 landed the ROW-STATE line.
v3's label search (regex + multi-line brace scan) matched 0x even
though the byte-exact probe (diag-stash-label.py) printed the label
line 4711 containing PLACED, INVENTORY[ and TAP TO PLACE on ONE line.
Prime suspect: regex — the '[' in 'INVENTORY[' breaks unescaped
regex searches, and the earlier probe prints had dropped the
`(item: any)` annotation on the .map line, so exact anchors kept
missing. This v4 uses PLAIN SUBSTRING search only (`in`, `find`) —
no `re` module is imported at all — anchored on the probe's repr dump.

Exactly ONE change (the row label). Does NOT touch row-state (v2
owns it), the toggle intercept (v1 owns it), the 2884 placed line,
the modal, the stash state, character.tsx, the backend, or any other
row.

Ground truth (repr dump, lines 4690-4720 of index.tsx, 5712 total):
- .map line 4698: `{(HOUSE_ITEMS[houseItemCategory] || []).map((item: any) => {`
- row-state line 4699 (v2, live): `const placed = item.id === 'stash-box' ? !!(stashBox && stashBox.owned) : (interiorHouse?.items || []).some((it: any) => it.item_id === item.id);`
- label line 4711 (ONE line, tight spacing):
  `<Text style={{ color: placed ? '#4caf50' : invCount > 0 ? '#5dade2' : '#f39c12', fontWeight: '800', fontSize: 12 }}>{placed ? '✓ PLACED' : invCount > 0 ? 'INVENTORY['+invCount+']' : (item.price ? 'BUY $'+item.price.toLocaleString() : 'TAP TO PLACE')}</Text>`
- Checkmark: literal '✓' U+2713, exactly 1 occurrence in the file.
  (The probe's own verdict/counts contradict its repr dump here and
  are NOT trusted; the repr is ground truth.)

Run from /app: python3 frontend/patch-stash-box-dropdown-frontend-v4.py
Idempotent: rerun prints ALREADY_APPLIED, file unchanged.
"""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"

MARKER = "STASH_BOX_DROPDOWN_V4_OK"

PLACED_NEW = ("const placed = item.id === 'stash-box' "
              "? !!(stashBox && stashBox.owned) "
              ": (interiorHouse?.items || []).some("
              "(it: any) => it.item_id === item.id);")
INTERCEPT = "if (item?.id === 'stash-box') { handleStashBoxToggle(); return; }"

# New label expression, matching the live file's tight spacing style.
# ✓ and — are literal characters, never unicode escapes.
LABEL_NEW = ("{item.id === 'stash-box' ? (placed ? '✓ OWNED — TAP TO OPEN' "
             ": 'BUY $5,000') : (placed ? '✓ PLACED' : invCount > 0 ? "
             "'INVENTORY['+invCount+']' : (item.price ? 'BUY $'+"
             "item.price.toLocaleString() : 'TAP TO PLACE'))}")


def delta(s):
    """Balance deltas only (raw counts grow with every insert)."""
    return (s.count("{") - s.count("}"),
            s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def main():
    warned = []
    landed = []
    if not INDEX.exists():
        print("WARNING: frontend/app/(tabs)/index.tsx not found - Stash Box dropdown NOT wired")
        print("STASH_BOX_DROPDOWN_V4_PARTIAL: (warnings: index-missing)")
        return
    src = INDEX.read_text(errors="ignore")
    orig = src
    d0 = delta(src)

    if "id: 'stash-box'" not in src:
        print("WARNING: stash-box utilities entry not found - dropdown row NOT wired")
        print("STASH_BOX_DROPDOWN_V4_PARTIAL: (warnings: stash-entry-missing)")
        return

    lines = src.split("\n")

    # 1. Dropdown .map line: plain substring only. Exactly one.
    map_candidates = [i for i, l in enumerate(lines)
                      if "HOUSE_ITEMS[houseItemCategory]" in l and ".map(" in l]
    map_idx = None
    if len(map_candidates) == 1:
        map_idx = map_candidates[0]
    else:
        print(f"WARNING: dropdown .map line matched {len(map_candidates)}x "
              "- stash-box row label NOT wired (expected exactly 1 "
              "HOUSE_ITEMS[houseItemCategory] .map line)")
        warned.append("row-label")

    # Row state (v2) and toggle (v1): status checks ONLY, never re-added.
    if PLACED_NEW in src:
        print("STASH_BOX_DROPDOWN_V4_ROW_PLACED_ALREADY_APPLIED")
    else:
        print("WARNING: stash-box row state (v2) NOT present - NOT "
              "re-added by this patch (the v2 follow-up owns the row state)")
        warned.append("row-state")
    if INTERCEPT in src:
        print("STASH_BOX_DROPDOWN_V4_TOGGLE_ALREADY_APPLIED")
    else:
        print("WARNING: stash-box toggle intercept NOT present - NOT "
              "re-added by this patch (the v1 follow-up owns the "
              "intercept); tapping the row would still go generic add")
        warned.append("toggle")

    # 2. Label line: the ONE line in the 40 lines after the .map line
    # containing BOTH 'PLACED' and 'TAP TO PLACE'. Plain substring
    # only. Deliberately NOT gated on 'INVENTORY[' (the byte probe's
    # own count for it contradicted its repr dump).
    if map_idx is not None:
        win = lines[map_idx + 1:map_idx + 41]
        hits = [j for j, l in enumerate(win)
                if "PLACED" in l and "TAP TO PLACE" in l]
        if len(hits) != 1:
            print(f"WARNING: dropdown label line matched {len(hits)}x in "
                  "the 40 lines after the .map line - stash-box row "
                  "label NOT wired (expected exactly 1 line with both "
                  "'PLACED' and 'TAP TO PLACE')")
            warned.append("row-label")
        else:
            li = map_idx + 1 + hits[0]
            line = lines[li]
            # 3. Already wired?
            if "OWNED" in line:
                print("STASH_BOX_DROPDOWN_V4_ROW_LABEL_ALREADY_APPLIED")
            else:
                # 4. Replace the span from '{placed ?' to '</Text>'.
                start = line.find("{placed ?")
                end = line.find("</Text>", start if start != -1 else 0)
                if start == -1 or end == -1:
                    print("WARNING: label expression open/close not found "
                          "on the label line - stash-box row label NOT wired")
                    warned.append("row-label")
                else:
                    print("LABEL BEFORE: " + repr(line))
                    lines[li] = line[:start] + LABEL_NEW + line[end:]
                    print("LABEL AFTER:  " + repr(lines[li]))
                    print("STASH_BOX_DROPDOWN_V4_ROW_LABEL_OK")
                    landed.append("row-label")
                    src = "\n".join(lines)

    if delta(src) != d0:
        print("WARNING: balance changed - index.tsx NOT written")
        warned.append("balance")
    elif src != orig:
        INDEX.write_text(src)
    if warned:
        print("STASH_BOX_DROPDOWN_V4_PARTIAL: " + ",".join(landed)
              + " (warnings: " + ",".join(warned) + ")")
    else:
        print(MARKER)


if __name__ == "__main__":
    main()
