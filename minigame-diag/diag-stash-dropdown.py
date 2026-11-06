#!/usr/bin/env python3
"""Stash Box dropdown probe: print the LIVE Utilities dropdown code so a
follow-up patch can wire the Stash Box row correctly.

CONTEXT (parent, 2026-11-06): the Stash Box frontend patch
(frontend/patch-stash-box-frontend.py) RAN PARTIAL on /app (screenshot
01:34 EST). Backend ran clean (STASH_BOX_OK). Frontend OKs: API,
INDEX_IMPORT, INDEX_IMG, INDEX_ENTRY, INDEX_MODAL, CHAR_IMPORTS,
CHAR_HANDLERS, CHAR_PROPS, CHAR_RENDER, CHAR_STORE_* (all 5 items),
CHAR_MODAL. The 3 WARNINGS were all in the Utilities dropdown row:
  1. "dropdown placed anchor matched 2x - stash-box row state NOT wired"
     (patch expected exactly 1x of:
      const placed = (interiorHouse?.items || []).some((it: any) => it.item_id === item.id);)
  2. "dropdown label anchor matched 0x - stash-box row label NOT wired"
     (patch expected exactly 1x of: {placed ? '✓ PLACED' : 'TAP TO PLACE'})
  3. "toggle handler anchor matched 0x - stash-box tap NOT intercepted
     (generic add would 400 'House is full')"
     (patch expected exactly 1x of:
       const handleHouseItemToggle = async (item: any) => {
         if (!interiorHouse || !playerId) return;)
So the stash-box entry IS in the utilities array and the modal + the
character.tsx STORE buttons landed, but the dropdown row itself is not
wired: its owned/placed state, its label, and its tap handler. Until
fixed, tapping the Stash Box row in Utilities goes through the generic
items/add path and 400s 'House is full'.

This probe is READ-ONLY: it never edits a file, never restarts
anything, and makes no network calls at all -- it only reads the
frontend code under <root>/frontend. It prints:
  1. the dropdown row rendering (verbatim, with both "placed" matches
     told apart: which one is the dropdown row vs the other);
  2. the REAL toggle handler (the patch's handleHouseItemToggle matched
     0x, so find it via the generic postItem('add') call site);
  3. the stash-box row as it renders today;
  4. a 2-4 line unique anchor for each of the 3 missing pieces;
  5. a verdict: (a) all three anchors unique, (b) different shape than
     the patch assumed, (c) dropdown lives in another file.

Run:  python3 minigame-diag/diag-stash-dropdown.py [--root /app]
"""
import argparse
import re
import sys
from pathlib import Path

PLACED_EXACT = ("const placed = (interiorHouse?.items || []).some("
                "(it: any) => it.item_id === item.id);")
LABEL_EXACT = "{placed ? '✓ PLACED' : 'TAP TO PLACE'}"
HANDLER_EXACT = ("  const handleHouseItemToggle = async (item: any) => {\n"
                 "    if (!interiorHouse || !playerId) return;")


def _strip_strings(text):
    return re.sub(r"'[^']*'|\"[^\"]*\"|`[^`]*`", "''", text)


def print_block(title, lines, start, end):
    print(f"--- {title} (lines {start + 1}-{end}) ---")
    for i in range(start, min(end, len(lines))):
        print(f"{i + 1:>5}: {lines[i]}")


def show_context(lines, idx, before=5, after=5, label=None):
    if label:
        print(f"  [{label}] line {idx + 1}:")
    for j in range(max(0, idx - before), min(len(lines), idx + after + 1)):
        mark = ">>>" if j == idx else "   "
        print(f"  {mark} {j + 1:>5}: {lines[j]}")


def find_lines(lines, pattern, flags=0):
    rx = re.compile(pattern, flags)
    return [(i, l) for i, l in enumerate(lines) if rx.search(l)]


def read_file(path):
    try:
        return Path(path).read_text(errors="ignore").splitlines()
    except OSError:
        return None


def enclosing_function(lines, idx, window=200):
    """Name + start line of the function enclosing line idx, or (None, None)."""
    pat = re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(")
    pat2 = re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")
    pat3 = re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*=\s*useCallback")
    for j in range(idx, max(-1, idx - window), -1):
        m = pat.match(lines[j]) or pat2.match(lines[j]) or pat3.match(lines[j])
        if m:
            return m.group(1), j
    return None, None


def brace_block_end(lines, start, cap=120):
    """End line (inclusive) of the brace block opened at/after start."""
    depth = 0
    started = False
    for j in range(start, min(len(lines), start + cap)):
        code = _strip_strings(lines[j])
        depth += code.count("{") - code.count("}")
        if "{" in code:
            started = True
        if started and depth <= 0:
            return j
    return min(len(lines), start + cap) - 1


def nearest_map_line(lines, idx, window=80):
    """Nearest line at/above idx containing '.map(' (the row render loop)."""
    for j in range(idx, max(-1, idx - window), -1):
        if ".map(" in lines[j]:
            return j
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    f = {}          # findings
    missing = []

    print("=== stash dropdown diag (read-only, code only) ===")
    print(f"root: {root}")

    # ------------------------------------------------ locate the files
    index_candidates = [
        root / "frontend" / "app" / "(tabs)" / "index.tsx",
        root / "frontend" / "app" / "index.tsx",
    ]
    index_path = next((p for p in index_candidates if p.is_file()), None)
    index_lines = read_file(index_path) if index_path else None
    print(f"index.tsx: {index_path if index_path else 'NOT FOUND'}")
    if index_lines is None:
        print("STASH_DROPDOWN_DIAG_PARTIAL missing=index.tsx verdict=(b)")
        return 0

    # Where else could the dropdown live? Scan the whole frontend tree
    # for the strings only the house-shop dropdown carries.
    other_hits = []
    frontend_root = root / "frontend"
    if frontend_root.is_dir():
        for p in sorted(frontend_root.rglob("*.tsx")):
            if index_path and p.resolve() == index_path.resolve():
                continue
            try:
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            if ("HOUSE_ITEMS" in text or "TAP TO PLACE" in text
                    or "stash-box" in text):
                other_hits.append(str(p))
    print(f"other files mentioning HOUSE_ITEMS / TAP TO PLACE / stash-box: "
          f"{other_hits if other_hits else 'NONE'}")
    f["other_hits"] = other_hits

    # ------------------------------------------------ 1. dropdown row rendering
    print()
    print("=== 1. Utilities dropdown row rendering (index.tsx) ===")
    util_hits = find_lines(index_lines, r"utilities", re.IGNORECASE)
    print(f"'utilities' mentions in index.tsx: {len(util_hits)}")
    for i, l in util_hits[:12]:
        show_context(index_lines, i, before=0, after=0)
    hi = find_lines(index_lines, r"HOUSE_ITEMS\s*=")
    if hi:
        i = hi[0][0]
        print(f"HOUSE_ITEMS definition: line {i + 1}")
        show_context(index_lines, i, before=0, after=8)
        f["house_items_line"] = i + 1
    else:
        print("HOUSE_ITEMS definition: NOT FOUND in index.tsx")
        f["house_items_line"] = None

    placed_hits = [i for i, l in enumerate(index_lines)
                   if PLACED_EXACT in l]
    print(f"placed anchor (exact patch line): matched {len(placed_hits)}x")
    f["placed_count"] = len(placed_hits)
    f["placed_lines"] = [i + 1 for i in placed_hits]
    for k, i in enumerate(placed_hits):
        fn, fstart = enclosing_function(index_lines, i)
        # Is this the dropdown row? The row's label sits within ~15 lines
        # below the placed line.
        nearby = "\n".join(index_lines[i:min(len(index_lines), i + 16)])
        is_row = ("PLACED" in nearby or "TAP TO PLACE" in nearby)
        print(f"placed match #{k + 1} line {i + 1}: enclosing function "
              f"'{fn}' (line {fstart + 1 if fstart is not None else '?'}) "
              f"-- {'DROPDOWN ROW' if is_row else 'OTHER (not the row)'}")
        show_context(index_lines, i, before=5, after=5)
        if k == 0:
            f["placed_is_row"] = is_row
    if not placed_hits:
        loose = find_lines(index_lines, r"\bplaced\b.*\.some\(|\.some\([^)]*item_id")
        print(f"placed anchor: 0x exact; loose placed/.some matches: "
              f"{len(loose)}")
        for i, l in loose[:6]:
            show_context(index_lines, i, before=1, after=1)

    label_hits = [i for i, l in enumerate(index_lines) if LABEL_EXACT in l]
    print(f"label anchor (exact patch text): matched {len(label_hits)}x")
    f["label_count"] = len(label_hits)
    f["label_lines"] = [i + 1 for i in label_hits]
    for i in label_hits:
        show_context(index_lines, i, before=3, after=3)
    if not label_hits:
        loose = find_lines(index_lines, r"PLACED|TAP TO PLACE")
        print(f"label anchor: 0x exact; loose PLACED / TAP TO PLACE "
              f"matches: {len(loose)}")
        for i, l in loose[:8]:
            show_context(index_lines, i, before=1, after=1)
        f["loose_label_lines"] = [i + 1 for i, _ in loose]

    # The row-render block: the .map( loop above the first placed/label hit.
    anchor_line = None
    if placed_hits:
        anchor_line = placed_hits[0]
    elif label_hits:
        anchor_line = label_hits[0]
    elif f.get("loose_label_lines"):
        anchor_line = f["loose_label_lines"][0] - 1
    if anchor_line is not None:
        mline = nearest_map_line(index_lines, anchor_line)
        if mline is not None:
            print(f"row-render .map( loop starts: line {mline + 1}")
            print_block("dropdown row render block", index_lines,
                        mline, mline + 30)
            f["row_map_line"] = mline + 1
        else:
            print("row-render .map( loop: NOT FOUND above the row anchor")
            f["row_map_line"] = None
            print_block("row area (30 lines around first row anchor)",
                        index_lines, max(0, anchor_line - 10),
                        anchor_line + 20)
    else:
        print("row-render block: NO placed/label anchor to anchor on")
        f["row_map_line"] = None
        missing.append("row-render")

    # ------------------------------------------------ 2. toggle handler
    print()
    print("=== 2. toggle handler (what a row tap calls) ===")
    hht = find_lines(index_lines, r"handleHouseItemToggle")
    print(f"handleHouseItemToggle mentions: {len(hht)} (patch expected 1)")
    f["hht_count"] = len(hht)
    for i, l in hht[:6]:
        show_context(index_lines, i, before=1, after=1)

    add_sites = find_lines(index_lines, r"postItem\(\s*['\"]add['\"]")
    add_sites += find_lines(index_lines, r"items/add")
    # de-dupe by line
    add_sites = sorted(set(i for i, _ in add_sites))
    print(f"generic add call sites (postItem('add') / items/add): "
          f"{len(add_sites)} at lines {[i + 1 for i in add_sites]}")
    f["add_sites"] = [i + 1 for i in add_sites]
    handler_name = None
    handler_start = None
    for i in add_sites:
        fn, fstart = enclosing_function(index_lines, i)
        print(f"add call site line {i + 1}: inside function "
              f"'{fn}' (starts line {fstart + 1 if fstart is not None else '?'})")
        show_context(index_lines, i, before=2, after=2)
        if fn and handler_name is None:
            handler_name, handler_start = fn, fstart
    f["handler_name"] = handler_name
    f["handler_start"] = (handler_start + 1
                          if handler_start is not None else None)
    if handler_name and handler_start is not None:
        end = brace_block_end(index_lines, handler_start)
        print(f"--- toggle handler '{handler_name}' verbatim "
              f"(lines {handler_start + 1}-{end + 1}) ---")
        print_block(f"handler {handler_name}", index_lines,
                    handler_start, end + 1)
        calls = find_lines(index_lines,
                           r"onPress\s*=\s*\{[^}]*" + re.escape(handler_name) +
                           r"|" + re.escape(handler_name) + r"\s*\(")
        call_lines = [i + 1 for i, _ in calls
                      if i != handler_start]
        print(f"call sites invoking '{handler_name}': "
              f"{call_lines if call_lines else 'NONE FOUND'}")
        f["handler_calls"] = call_lines
    else:
        print("toggle handler: NOT FOUND via the generic add call site")
        missing.append("toggle-handler")

    # Any other handler that calls the generic add/remove for house items?
    other_add = find_lines(index_lines, r"postItem\(|items/remove")
    other_add_lines = sorted(set(i + 1 for i, _ in other_add))
    print(f"all postItem / items/remove lines in index.tsx: "
          f"{other_add_lines if other_add_lines else 'NONE'}")
    f["postitem_lines"] = other_add_lines

    # ------------------------------------------------ 3. stash-box row today
    print()
    print("=== 3. stash-box row today ===")
    sb = find_lines(index_lines, r"stash-box")
    print(f"'stash-box' mentions in index.tsx: {len(sb)}")
    for i, l in sb[:10]:
        show_context(index_lines, i, before=2, after=2)
    f["stash_box_lines"] = [i + 1 for i, _ in sb]
    entry = find_lines(index_lines,
                       r"id:\s*'stash-box'|\"stash-box\"")
    if entry:
        i = entry[0][0]
        print(f"stash-box utilities entry: line {i + 1}")
        show_context(index_lines, i, before=2, after=2)
        f["stash_entry_line"] = i + 1
    else:
        print("stash-box utilities entry: NOT FOUND in index.tsx")
        f["stash_entry_line"] = None
        missing.append("stash-entry")
    print("--- what the row renders for stash-box TODAY ---")
    if placed_hits:
        print("  state: the placed line reads interiorHouse.items -- "
              "stash-box is never in house.items (utility flag, not a "
              "counted item), so placed = false for it.")
    if label_hits or f.get("loose_label_lines"):
        lab = (label_hits or f.get("loose_label_lines", []))
        print(f"  label: the row label at line {lab[0]} applies to every "
              f"row, stash-box included (placed=false -> the "
              f"'TAP TO PLACE' side).")
    if handler_name:
        print(f"  tap: goes to '{handler_name}' (line {f['handler_start']}) "
              f"-> the generic add path -> 400 'House is full' (the "
              f"stash-box intercept was never added).")
    else:
        print("  tap: handler unknown -- could not be traced.")

    # ------------------------------------------------ 4. anchors for follow-up
    print()
    print("=== 4. exact anchors for the follow-up patch ===")
    anchors = {}
    # (a) row-state anchor
    if len(placed_hits) == 1:
        i = placed_hits[0]
        anchors["row-state"] = (f"line {i + 1}: {index_lines[i].strip()}")
        print("ROW-STATE anchor (unique, 1x):")
        print(f"  line {i + 1}: {index_lines[i]}")
    elif placed_hits:
        # Use the dropdown-row match + the line above it to disambiguate.
        row_i = None
        for i in placed_hits:
            nearby = "\n".join(index_lines[i:min(len(index_lines), i + 16)])
            if "PLACED" in nearby or "TAP TO PLACE" in nearby:
                row_i = i
                break
        if row_i is None:
            row_i = placed_hits[0]
        anchors["row-state"] = (
            f"lines {row_i}-{row_i + 1}: "
            f"{index_lines[row_i - 1].strip() if row_i > 0 else ''} | "
            f"{index_lines[row_i].strip()}")
        print("ROW-STATE anchor (placed line is NOT unique -- use the "
              "2-line anchor below, row line + line above it):")
        if row_i > 0:
            print(f"  line {row_i}: {index_lines[row_i - 1]}")
        print(f"  line {row_i + 1}: {index_lines[row_i]}")
    else:
        anchors["row-state"] = None
        print("ROW-STATE anchor: NONE -- no placed line at all; the "
              "follow-up must print the smallest surrounding block:")
        if anchor_line is not None:
            print_block("row area (no placed line)",
                        index_lines, max(0, anchor_line - 5),
                        anchor_line + 10)
        missing.append("row-state-anchor")
    # (b) row-label anchor
    if len(label_hits) == 1:
        i = label_hits[0]
        anchors["row-label"] = (f"line {i + 1}: {index_lines[i].strip()}")
        print("ROW-LABEL anchor (unique, 1x):")
        print(f"  line {i + 1}: {index_lines[i]}")
    elif f.get("loose_label_lines"):
        # Label is built differently than the patch assumed: print the
        # actual label lines as the anchor block.
        lines = f["loose_label_lines"]
        anchors["row-label"] = (
            f"lines {lines[0]}-{lines[-1]} (label built differently -- "
            f"see block)")
        print("ROW-LABEL anchor: the exact patch text is 0x -- the label "
              "is built differently. Use these actual label lines:")
        for i in lines[:6]:
            print(f"  line {i}: {index_lines[i - 1]}")
    else:
        anchors["row-label"] = None
        print("ROW-LABEL anchor: NONE -- no PLACED/TAP TO PLACE text "
              "anywhere in index.tsx.")
        missing.append("row-label-anchor")
    # (c) toggle-intercept anchor
    if handler_name and handler_start is not None:
        first = index_lines[handler_start]
        second = (index_lines[handler_start + 1]
                  if handler_start + 1 < len(index_lines) else "")
        anchors["toggle-intercept"] = (
            f"lines {handler_start + 1}-{handler_start + 2}: "
            f"{first.strip()} | {second.strip()}")
        print("TOGGLE-INTERCEPT anchor (first 2 lines of the real "
              f"handler '{handler_name}'):")
        print(f"  line {handler_start + 1}: {first}")
        print(f"  line {handler_start + 2}: {second}")
    else:
        anchors["toggle-intercept"] = None
        print("TOGGLE-INTERCEPT anchor: NONE -- no handler found.")
        missing.append("toggle-anchor")
    f["anchors"] = {k: (v is not None) for k, v in anchors.items()}

    # ------------------------------------------------ 5. verdict
    print()
    print("=== 5. VERDICT ===")
    dropdown_elsewhere = bool(other_hits) and not (
        placed_hits or label_hits or f.get("loose_label_lines"))
    if dropdown_elsewhere:
        # The index-scoped "missing" items are not missing -- they live
        # in the other file. Replace them with a single pointer.
        missing = [f"dropdown-in-{Path(other_hits[0]).name}"]
    if dropdown_elsewhere:
        verdict = "(c)"
        print("VERDICT: (c) the dropdown lives in a different file than "
              f"index.tsx: {other_hits}")
    elif (len(placed_hits) == 1 and len(label_hits) == 1
          and handler_name and f["anchors"]["toggle-intercept"]):
        verdict = "(a)"
        print("VERDICT: (a) all three anchors found and unique -- the "
              "follow-up is a straight patch.")
    else:
        verdict = "(b)"
        print("VERDICT: (b) one or more pieces have a different shape "
              "than the patch assumed:")
        if len(placed_hits) != 1:
            print(f"  - placed line matched {len(placed_hits)}x "
                  f"(lines {f['placed_lines']}), patch expected 1x")
        if len(label_hits) != 1:
            print(f"  - label text matched {len(label_hits)}x, patch "
                  f"expected 1x; loose label lines: "
                  f"{f.get('loose_label_lines')}")
        if handler_name:
            print(f"  - toggle handler is '{handler_name}' (line "
                  f"{f['handler_start']}), not 'handleHouseItemToggle'")
        else:
            print("  - no toggle handler found via the generic add site")
    print(f"anchors present: row-state={f['anchors']['row-state']} "
          f"row-label={f['anchors']['row-label']} "
          f"toggle-intercept={f['anchors']['toggle-intercept']}")
    if missing:
        print(f"STASH_DROPDOWN_DIAG_PARTIAL missing={','.join(sorted(set(missing)))} "
              f"verdict={verdict}")
    else:
        print(f"STASH_DROPDOWN_DIAG_OK verdict={verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
