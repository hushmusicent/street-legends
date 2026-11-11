#!/usr/bin/env python3
"""Street Legends frontend: Stash Box dropdown follow-up #2 — Expo Go.

The first follow-up (frontend/patch-stash-box-dropdown-frontend.py)
landed its TOGGLE intercept (STASH_BOX_DROPDOWN_TOGGLE_OK, run
2026-11-06 01:45 EST) but its row-state and row-label anchors matched
0x live — the exact-string anchors did not survive the live file's
whitespace (the live .map line may carry a type annotation like
`(item: any) => {`, and the label ternary may be tightly spaced).
This v2 uses LOOSE, whitespace-tolerant anchors and never reuses the
exact-string anchors that just missed.

Ground truth is the probe (minigame-diag/diag-stash-dropdown.py,
STASH_DROPDOWN_DIAG_OK verdict=(b), run 2026-11-06 01:39 EST), but the
probe screenshots are low-resolution, so exact spacing/punctuation
is treated as UNCERTAIN:

  - Rows render from `(HOUSE_ITEMS[houseItemCategory] || []).map(`
    (probe line 4697) with the placed line at 4698. The identical
    placed line also exists at 2884 inside handleHouseItemToggle —
    NEVER touch 2884 (the 5-line window after the .map line is what
    protects it).
  - The row computes invCount at 4699; onPress calls
    handleHouseItemToggle at 4703.
  - The label line (4710) is a nested ternary containing `✓ PLACED`
    and `INVENTORY[` and `TAP TO PLACE`. Its exact else-branch is
    UNCERTAIN — two readings: (a) plain `'TAP TO PLACE'`, (b)
    `(item.price ? 'BUY $' + item.price.toLocaleString() :
    'TAP TO PLACE')`. This patch DETECTS which else-branch the live
    line has (regex for `item.price ? 'BUY`) and keeps it; it also
    detects a possible `(invCount > 1 ? 's' : '')` plural fragment
    and keeps that too. Other items' displayed text is unchanged
    in every variant.

Exactly two changes, nothing else. Does NOT touch the toggle
intercept (already live — if it is absent that is a WARNING only,
never re-added here), the 2884 line, the modal, the stash state,
character.tsx, the backend, or any other row. Emoji are literal
characters, never unicode escapes.

Run from /app: python3 frontend/patch-stash-box-dropdown-frontend-v2.py
Idempotent: rerun prints ALREADY_APPLIED per piece, file unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"

MARKER = "STASH_BOX_DROPDOWN_V2_OK"

PLACED_NEW = ("const placed = item.id === 'stash-box' "
              "? !!(stashBox && stashBox.owned) "
              ": (interiorHouse?.items || []).some("
              "(it: any) => it.item_id === item.id);")
INTERCEPT = "if (item?.id === 'stash-box') { handleStashBoxToggle(); return; }"
LABEL_STASH = ("item.id === 'stash-box' ? (placed ? "
               "'✓ OWNED — TAP TO OPEN' : 'BUY $5,000')")

# Loose, whitespace-tolerant anchors (no exact-string matching).
MAP_CAT_RE = re.compile(r"HOUSE_ITEMS\s*\[\s*houseItemCategory\s*\]")
MAP_CALL_RE = re.compile(r"\.map\s*\(")
PLACED_RE = re.compile(
    r"const\s+placed\s*=\s*\(interiorHouse\?\.items\s*\|\|\s*\[\]\)\.some\(")
PLACED_ITEM_RE = re.compile(r"item_id\s*===\s*item\.id")
LABEL_OPEN_RE = re.compile(r"\{\s*placed\s*\?")
PRICE_ELSE_RE = re.compile(r"item\.price\s*\?\s*'BUY")
PLURAL_RE = re.compile(r"invCount\s*>\s*1\s*\?\s*'s'")


def delta(s):
    """Balance deltas only (raw counts grow with every insert)."""
    return (s.count("{") - s.count("}"),
            s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def is_map_line(line):
    return bool(MAP_CAT_RE.search(line) and MAP_CALL_RE.search(line))


def label_new(has_price, has_plural):
    if has_plural:
        inv = "'INVENTORY[' + invCount + (invCount > 1 ? 's' : '') + ']'"
    else:
        inv = "'INVENTORY[' + invCount + ']'"
    if has_price:
        els = "(item.price ? 'BUY $' + item.price.toLocaleString() : 'TAP TO PLACE')"
    else:
        els = "'TAP TO PLACE'"
    return ("{item.id === 'stash-box' ? (placed ? '✓ OWNED — TAP TO OPEN' "
            ": 'BUY $5,000') : (placed ? '✓ PLACED' : invCount > 0 ? "
            + inv + " : " + els + ")}")


def main():
    warned = []
    landed = []
    if not INDEX.exists():
        print("WARNING: frontend/app/(tabs)/index.tsx not found - Stash Box dropdown NOT wired")
        print("STASH_BOX_DROPDOWN_V2_PARTIAL: (warnings: index-missing)")
        return
    src = INDEX.read_text(errors="ignore")
    orig = src
    d0 = delta(src)

    if "id: 'stash-box'" not in src:
        print("WARNING: stash-box utilities entry not found - dropdown row NOT wired")
        print("STASH_BOX_DROPDOWN_V2_PARTIAL: (warnings: stash-entry-missing)")
        return

    lines = src.split("\n")

    # Locate the dropdown .map line (loose: HOUSE_ITEMS[houseItemCategory]
    # + .map( on the same line, any spacing / any item param).
    map_candidates = [i for i, l in enumerate(lines) if is_map_line(l)]
    map_idx = None
    if len(map_candidates) == 1:
        map_idx = map_candidates[0]
    elif len(map_candidates) > 1:
        # Prefer the one whose 5-line window holds exactly one placed
        # candidate (the dropdown row); the others are not the row.
        good = []
        for i in map_candidates:
            cands = [j for j in range(i + 1, min(i + 6, len(lines)))
                     if PLACED_RE.search(lines[j])
                     and PLACED_ITEM_RE.search(lines[j])]
            if len(cands) == 1:
                good.append(i)
        if len(good) == 1:
            map_idx = good[0]

    # 1. Row state: the placed line within 5 lines after the .map line.
    if PLACED_NEW in src:
        print("STASH_BOX_DROPDOWN_V2_ROW_PLACED_ALREADY_APPLIED")
    elif map_idx is None:
        print(f"WARNING: dropdown .map line matched {len(map_candidates)}x "
              "- stash-box row state NOT wired (expected exactly 1 "
              "HOUSE_ITEMS[houseItemCategory] .map line)")
        warned.append("row-placed")
    else:
        cands = [j for j in range(map_idx + 1, min(map_idx + 6, len(lines)))
                 if PLACED_RE.search(lines[j])
                 and PLACED_ITEM_RE.search(lines[j])]
        if len(cands) == 1:
            j = cands[0]
            indent = lines[j][:len(lines[j]) - len(lines[j].lstrip())]
            lines[j] = indent + PLACED_NEW
            print("STASH_BOX_DROPDOWN_V2_ROW_PLACED_OK")
            landed.append("row-placed")
        else:
            print(f"WARNING: dropdown row placed anchor matched {len(cands)}x "
                  "in the 5 lines after the .map line - stash-box row state "
                  "NOT wired (expected exactly 1; the 2884 line inside "
                  "handleHouseItemToggle is untouched)")
            warned.append("row-placed")

    # 2. Row label: the line with BOTH '✓ PLACED' and 'INVENTORY[' within
    #    25 lines after the .map line. Replace the ternary span from the
    #    first '{placed ?' to '</Text>' (exclusive), keeping whatever
    #    else-branch / plural fragment the live line has.
    if LABEL_STASH in src:
        print("STASH_BOX_DROPDOWN_V2_ROW_LABEL_ALREADY_APPLIED")
    elif map_idx is None:
        print("WARNING: dropdown .map line not found - stash-box row label "
              "NOT wired")
        warned.append("row-label")
    else:
        cands = [j for j in range(map_idx + 1, min(map_idx + 26, len(lines)))
                 if "✓ PLACED" in lines[j] and "INVENTORY[" in lines[j]]
        if len(cands) != 1:
            print(f"WARNING: dropdown label anchor matched {len(cands)}x in "
                  "the 25 lines after the .map line - stash-box row label "
                  "NOT wired (expected exactly 1 line with both "
                  "'✓ PLACED' and 'INVENTORY[')")
            warned.append("row-label")
        else:
            j = cands[0]
            line = lines[j]
            om = LABEL_OPEN_RE.search(line)
            ci = line.find("</Text>", om.end()) if om else -1
            if om is None or ci == -1:
                print("WARNING: label expression open/close not found on "
                      "the label line - stash-box row label NOT wired")
                warned.append("row-label")
            else:
                new_expr = label_new(
                    bool(PRICE_ELSE_RE.search(line)),
                    bool(PLURAL_RE.search(line)))
                lines[j] = line[:om.start()] + new_expr + line[ci:]
                print("STASH_BOX_DROPDOWN_V2_ROW_LABEL_OK")
                landed.append("row-label")

    # Toggle intercept: already live since v1 — presence check ONLY.
    # Never re-add it here.
    if INTERCEPT in src:
        print("STASH_BOX_DROPDOWN_V2_TOGGLE_ALREADY_APPLIED")
    else:
        print("WARNING: stash-box toggle intercept NOT present - NOT "
              "re-added by this patch (the v1 follow-up owns the "
              "intercept); tapping the row would still go generic add")
        warned.append("toggle")

    src = "\n".join(lines)
    if delta(src) != d0:
        print("WARNING: balance changed - index.tsx NOT written")
        warned.append("balance")
    elif src != orig:
        INDEX.write_text(src)
    if warned:
        print("STASH_BOX_DROPDOWN_V2_PARTIAL: " + ",".join(landed)
              + " (warnings: " + ",".join(warned) + ")")
    else:
        print(MARKER)


if __name__ == "__main__":
    main()
