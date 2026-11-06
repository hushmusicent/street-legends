#!/usr/bin/env python3
"""Street Legends frontend: Stash Box dropdown follow-up — Expo Go.

Wires the Utilities dropdown row for the Stash Box. The first patch
(frontend/patch-stash-box-frontend.py) landed the api, the stash-box
utilities entry, the stash state/modal and the character.tsx STORE
buttons, but its three dropdown anchors were wrong (placed matched 2x,
label matched 0x, toggle handler matched 0x — it assumed an async
handleHouseItemToggle). This follow-up builds ONLY on what the probe
(minigame-diag/diag-stash-dropdown.py, STASH_DROPDOWN_DIAG_OK
verdict=(b), run 2026-11-06 01:39 EST) actually printed:

  - Row state: the placed line matched 2x. Match #1 is line 2884
    INSIDE handleHouseItemToggle (leave it alone). Match #2 is line
    4698, the dropdown row, directly under line 4697
    `(HOUSE_ITEMS[houseItemCategory] || []).map((item) => {`.
    Disambiguate with that 2-line anchor.
  - Row label: the exact patch text matched 0x. Live line 4710 is a
    nested ternary with invCount:
    `{placed ? '✓ PLACED' : invCount > 0 ? 'INVENTORY[' + invCount
    + ']' : 'TAP TO PLACE'}` (there may be an extra
    `(invCount > 1 ? ...` fragment in the same line). Anchor on the
    unique fragment and replace through `'TAP TO PLACE'}`.
  - Toggle: handleHouseItemToggle IS the real handler, but it is SYNC
    (not async) and its first lines are the tv/radio intercepts, not
    the interiorHouse check. Live lines 2880-2883:
      const handleHouseItemToggle = (item: any) => {
        if (item?.id === 'tv' && ...) { toggleTv(); return; }
        if (item?.id === 'radio' && ...) { toggleRadio(); return; }
        if (isGuestVisit) { return; }
    The intercept goes right AFTER the radio line, WITHOUT await
    (handleStashBoxToggle is async and fire-and-forget is correct
    here, same as the sync tv/radio calls). The generic add lives in
    handleHouseItemToggleDo (postItem('add') line 2915).

Exactly three changes, nothing else. Does NOT touch the 2884 placed
line, the modal, the stash state, character.tsx, the backend, or any
other row. Emoji are literal characters, never unicode escapes.

Run from /app: python3 frontend/patch-stash-box-dropdown-frontend.py
Idempotent: rerun prints ALREADY_APPLIED per piece, file unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"

MARKER = "STASH_BOX_DROPDOWN_OK"

PLACED_OLD = ("const placed = (interiorHouse?.items || []).some("
              "(it: any) => it.item_id === item.id);")
PLACED_NEW = ("const placed = item.id === 'stash-box' "
              "? !!(stashBox && stashBox.owned) "
              ": (interiorHouse?.items || []).some("
              "(it: any) => it.item_id === item.id);")
MAP_LINE = "(HOUSE_ITEMS[houseItemCategory] || []).map((item) => {"

LABEL_ANCHOR = "{placed ? '✓ PLACED' : invCount > 0 ? 'INVENTORY['"
LABEL_NEW = ("{item.id === 'stash-box' ? (placed ? '✓ OWNED — TAP TO OPEN' "
             ": 'BUY $5,000') : (placed ? '✓ PLACED' : invCount > 0 ? "
             "'INVENTORY[' + invCount + ']' : 'TAP TO PLACE')}")
LABEL_END = "'TAP TO PLACE'}"

INTERCEPT = "if (item?.id === 'stash-box') { handleStashBoxToggle(); return; }"
RADIO_RE = re.compile(
    r"^([ \t]*)if \(item\?\.id === 'radio' && "
    r"\(interiorHouse\?\.items \|\| \[\]\)\.some\("
    r"\(it: any\) => it\.item_id === 'radio'\)\) "
    r"\{ toggleRadio\(\); return; \}$", re.M)
PLACED_RE = re.compile(
    r"^([ \t]*)const placed = \(interiorHouse\?\.items \|\| \[\]\)\.some\("
    r"\(it: any\) => it\.item_id === item\.id\);$", re.M)


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
        print("STASH_BOX_DROPDOWN_PARTIAL: (warnings: index-missing)")
        return
    src = INDEX.read_text(errors="ignore")
    orig = src
    d0 = delta(src)

    if "id: 'stash-box'" not in src:
        print("WARNING: stash-box utilities entry not found - dropdown row NOT wired")
        print("STASH_BOX_DROPDOWN_PARTIAL: (warnings: stash-entry-missing)")
        return

    # 1. Row state: the dropdown row's placed line only (2-line anchor).
    #    The 2884 line inside handleHouseItemToggle must stay identical.
    if PLACED_NEW in src:
        print("STASH_BOX_DROPDOWN_ROW_PLACED_ALREADY_APPLIED")
    else:
        row_hits = []
        for m in PLACED_RE.finditer(src):
            prev = src[:m.start()].rstrip("\n").split("\n")[-1].strip()
            # endswith, not ==: the JSX line usually opens with a '{'
            # ("{(HOUSE_ITEMS[...] || []).map((item) => {").
            if prev.endswith(MAP_LINE):
                row_hits.append(m)
        if len(row_hits) == 1:
            m = row_hits[0]
            src = (src[:m.start()] + m.group(1) + PLACED_NEW
                   + src[m.end():])
            print("STASH_BOX_DROPDOWN_ROW_PLACED_OK")
            landed.append("row-placed")
        else:
            print(f"WARNING: dropdown row placed anchor matched {len(row_hits)}x "
                  "- stash-box row state NOT wired (expected exactly 1 under the "
                  "HOUSE_ITEMS .map line; the 2884 line inside "
                  "handleHouseItemToggle is untouched)")
            warned.append("row-placed")

    # 2. Row label: fragment-anchored, replace through 'TAP TO PLACE'}.
    #    The other items keep their nested invCount ternary exactly.
    if LABEL_NEW in src:
        print("STASH_BOX_DROPDOWN_ROW_LABEL_ALREADY_APPLIED")
    elif src.count(LABEL_ANCHOR) == 1:
        ai = src.find(LABEL_ANCHOR)
        ei = src.find(LABEL_END, ai)
        if ei == -1:
            print("WARNING: label end anchor not found after the label "
                  "fragment - stash-box row label NOT wired")
            warned.append("row-label")
        else:
            end = ei + len(LABEL_END)
            src = src[:ai] + LABEL_NEW + src[end:]
            print("STASH_BOX_DROPDOWN_ROW_LABEL_OK")
            landed.append("row-label")
    else:
        print(f"WARNING: dropdown label anchor matched "
              f"{src.count(LABEL_ANCHOR)}x - stash-box row label NOT wired")
        warned.append("row-label")

    # 3. Toggle intercept: right after the radio line, no await.
    if INTERCEPT in src:
        print("STASH_BOX_DROPDOWN_TOGGLE_ALREADY_APPLIED")
    elif "handleStashBoxToggle" not in src:
        print("WARNING: handleStashBoxToggle not present - stash-box tap "
              "NOT intercepted (stash state missing)")
        warned.append("toggle")
    else:
        rm = list(RADIO_RE.finditer(src))
        ht = src.find("const handleHouseItemToggle")
        if len(rm) == 1 and 0 <= ht < rm[0].start():
            m = rm[0]
            src = (src[:m.end()] + "\n" + m.group(1) + INTERCEPT
                   + src[m.end():])
            print("STASH_BOX_DROPDOWN_TOGGLE_OK")
            landed.append("toggle")
        else:
            print(f"WARNING: radio intercept anchor matched {len(rm)}x "
                  "- stash-box tap NOT intercepted (generic add would 400 "
                  "'House is full')")
            warned.append("toggle")

    if delta(src) != d0:
        print("WARNING: balance changed - index.tsx NOT written")
        warned.append("balance")
    elif src != orig:
        INDEX.write_text(src)
    if warned:
        print("STASH_BOX_DROPDOWN_PARTIAL: " + ",".join(landed)
              + " (warnings: " + ",".join(warned) + ")")
    else:
        print(MARKER)


if __name__ == "__main__":
    main()
