#!/usr/bin/env python3
"""Street Legends frontend: Stash Box dropdown follow-up #3 — Expo Go.

v1 landed the TOGGLE intercept. v2 landed the ROW-STATE line but its
label anchor matched 0x: it required ONE line to contain both
'✓ PLACED' and 'INVENTORY['. The label expression is split across
2+ physical lines in the live file (and/or the checkmark is stored as
an escape). This v3 joins the 40 lines after the dropdown .map line
and searches the joined window, so a split label is found; it also
falls back to the '\\u2713' / '\\u{2713}' escape forms for the
checkmark and writes the replacement using whichever form the live
line uses. The em-dash in 'OWNED — TAP TO OPEN' stays a literal
character, as in v2.

Exactly ONE change (the row label). Does NOT touch row-state (v2
owns it), the toggle intercept (v1 owns it), the 2884 placed line,
the modal, the stash state, character.tsx, the backend, or any other
row.

Run from /app: python3 frontend/patch-stash-box-dropdown-frontend-v3.py
Idempotent: rerun prints ALREADY_APPLIED, file unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"

MARKER = "STASH_BOX_DROPDOWN_V3_OK"

PLACED_NEW = ("const placed = item.id === 'stash-box' "
              "? !!(stashBox && stashBox.owned) "
              ": (interiorHouse?.items || []).some("
              "(it: any) => it.item_id === item.id);")
INTERCEPT = "if (item?.id === 'stash-box') { handleStashBoxToggle(); return; }"

MAP_CAT_RE = re.compile(r"HOUSE_ITEMS\s*\[\s*houseItemCategory\s*\]")
MAP_CALL_RE = re.compile(r"\.map\s*\(")
PLACED_RE = re.compile(
    r"const\s+placed\s*=\s*\(interiorHouse\?\.items\s*\|\|\s*\[\]\)\.some\(")
ROW_PLACED_RE = re.compile(r"const\s+placed\s*=\s*item\.id\s*===\s*'stash-box'")
LABEL_OPEN_RE = re.compile(r"\{\s*placed\s*\?")
PRICE_ELSE_RE = re.compile(r"item\.price\s*\?\s*'BUY")
PLURAL_RE = re.compile(r"invCount\s*>\s*1\s*\?\s*'s'")
ESCAPED_CHECK_RE = re.compile(r"\\u2713|\\u\{2713\}")
STASH_LABEL_RE = re.compile(
    r"item\.id === 'stash-box' \? \(placed \? '(?:✓|\\u2713|\\u\{2713\}) OWNED")


def delta(s):
    """Balance deltas only (raw counts grow with every insert)."""
    return (s.count("{") - s.count("}"),
            s.count("(") - s.count(")"),
            s.count("[") - s.count("]"))


def is_map_line(line):
    return bool(MAP_CAT_RE.search(line) and MAP_CALL_RE.search(line))


def expr_end(s, start):
    """Index just past the matching '}' for the '{' at start, or -1.

    String-aware: braces inside '...' / "..." literals do not count.
    The label ternary contains no nested object literals, so a plain
    brace scan with quote tracking is exact here.
    """
    depth = 0
    quote = None
    i = start
    while i < len(s):
        c = s[i]
        if quote is not None:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        else:
            if c in ("'", '"'):
                quote = c
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return i + 1
        i += 1
    return -1


def label_new(chk, has_price, has_plural):
    if has_plural:
        inv = "'INVENTORY[' + invCount + (invCount > 1 ? 's' : '') + ']'"
    else:
        inv = "'INVENTORY[' + invCount + ']'"
    if has_price:
        els = "(item.price ? 'BUY $' + item.price.toLocaleString() : 'TAP TO PLACE')"
    else:
        els = "'TAP TO PLACE'"
    return ("{item.id === 'stash-box' ? (placed ? '" + chk + " OWNED — TAP TO OPEN' "
            ": 'BUY $5,000') : (placed ? '" + chk + " PLACED' : invCount > 0 ? "
            + inv + " : " + els + ")}")


def main():
    warned = []
    landed = []
    if not INDEX.exists():
        print("WARNING: frontend/app/(tabs)/index.tsx not found - Stash Box dropdown NOT wired")
        print("STASH_BOX_DROPDOWN_V3_PARTIAL: (warnings: index-missing)")
        return
    src = INDEX.read_text(errors="ignore")
    orig = src
    d0 = delta(src)

    if "id: 'stash-box'" not in src:
        print("WARNING: stash-box utilities entry not found - dropdown row NOT wired")
        print("STASH_BOX_DROPDOWN_V3_PARTIAL: (warnings: stash-entry-missing)")
        return

    lines = src.split("\n")

    # Locate the dropdown .map line (loose, as in v2). Disambiguation
    # accepts either placed form in the 5-line window, because v2's
    # row-state edit already replaced the row's placed line.
    map_candidates = [i for i, l in enumerate(lines) if is_map_line(l)]
    map_idx = None
    if len(map_candidates) == 1:
        map_idx = map_candidates[0]
    elif len(map_candidates) > 1:
        good = []
        for i in map_candidates:
            cands = [j for j in range(i + 1, min(i + 6, len(lines)))
                     if (PLACED_RE.search(lines[j])
                         or ROW_PLACED_RE.search(lines[j]))]
            if len(cands) == 1:
                good.append(i)
        if len(good) == 1:
            map_idx = good[0]

    # Row state: v2 owns it — status check ONLY, never re-added here.
    if PLACED_NEW in src:
        print("STASH_BOX_DROPDOWN_V3_ROW_PLACED_ALREADY_APPLIED")
    else:
        print("WARNING: stash-box row state (v2) NOT present - NOT "
              "re-added by this patch (the v2 follow-up owns the row state)")
        warned.append("row-state")

    # Row label: multi-line tolerant. Join the 40 lines after the .map
    # line and search the joined window for the label expression: it
    # starts at '{placed ?' and its span (to the matching '}') must
    # contain PLACED, INVENTORY[ and TAP TO PLACE.
    if STASH_LABEL_RE.search(src):
        print("STASH_BOX_DROPDOWN_V3_ROW_LABEL_ALREADY_APPLIED")
    elif map_idx is None:
        print(f"WARNING: dropdown .map line matched {len(map_candidates)}x "
              "- stash-box row label NOT wired (expected exactly 1 "
              "HOUSE_ITEMS[houseItemCategory] .map line)")
        warned.append("row-label")
    else:
        win_lines = lines[map_idx + 1:map_idx + 41]
        win_text = "\n".join(win_lines)
        base = sum(len(l) + 1 for l in lines[:map_idx + 1])
        valid = []
        for m in LABEL_OPEN_RE.finditer(win_text):
            end = expr_end(win_text, m.start())
            if end == -1:
                continue
            close_tag = win_text.find("</Text>", end)
            if close_tag == -1:
                continue
            # Only whitespace may sit between the expression's closing
            # brace and its </Text>.
            if win_text[end:close_tag].strip() != "":
                continue
            span = win_text[m.start():end]
            if ("PLACED" in span and "INVENTORY[" in span
                    and "TAP TO PLACE" in span):
                valid.append((m.start(), end, span))
        if len(valid) != 1:
            print(f"WARNING: dropdown label expression matched {len(valid)}x "
                  "in the 40 lines after the .map line - stash-box row "
                  "label NOT wired (expected exactly 1 '{placed ?' "
                  "expression containing PLACED, INVENTORY[ and TAP TO PLACE)")
            warned.append("row-label")
        else:
            start, end, span = valid[0]
            # Checkmark form: literal first, else whichever escape the
            # live span actually uses; the replacement keeps that form.
            if "✓" in span:
                chk = "✓"
            else:
                esc = ESCAPED_CHECK_RE.search(span)
                if esc is None:
                    print("WARNING: label expression has no checkmark form "
                          "found - stash-box row label NOT wired")
                    warned.append("row-label")
                    chk = None
                else:
                    chk = esc.group(0)
            if chk is not None:
                new_expr = label_new(
                    chk,
                    bool(PRICE_ELSE_RE.search(span)),
                    bool(PLURAL_RE.search(span)))
                src = src[:base + start] + new_expr + src[base + end:]
                print("STASH_BOX_DROPDOWN_V3_ROW_LABEL_OK")
                landed.append("row-label")

    # Toggle intercept: v1 owns it — presence check ONLY.
    if INTERCEPT in src:
        print("STASH_BOX_DROPDOWN_V3_TOGGLE_ALREADY_APPLIED")
    else:
        print("WARNING: stash-box toggle intercept NOT present - NOT "
              "re-added by this patch (the v1 follow-up owns the "
              "intercept); tapping the row would still go generic add")
        warned.append("toggle")

    if delta(src) != d0:
        print("WARNING: balance changed - index.tsx NOT written")
        warned.append("balance")
    elif src != orig:
        INDEX.write_text(src)
    if warned:
        print("STASH_BOX_DROPDOWN_V3_PARTIAL: " + ",".join(landed)
              + " (warnings: " + ",".join(warned) + ")")
    else:
        print(MARKER)


if __name__ == "__main__":
    main()
