#!/usr/bin/env python3
"""Street Legends frontend v2: put Scrabble in the SAME rendered
Games list as Pool / Dartboard / Card / Dominoes.

Why v2: the v1 Scrabble patch printed "Scrabble Table added to
Games list" but Scrabble still does not show. Pool, Card and
Dominoes show from the frontend list with no Deploy needed, so
Scrabble's v1 entry went to a different (non-rendered) list, not
the one those are in. v2 finds the rendered list itself: the array
that contains entries for Pool + Dartboard + Card + Dominoes, and
duplicates the Dominoes entry inside THAT array, renamed to
Scrabble (same $20k price, Scrabble image). That is exactly how
the working items got in.

What v2 does (guarded; a missed anchor SKIPs with a WARNING):
  1. Search frontend/app/**/*.tsx + frontend/components/*.tsx for
     a file whose text contains Pool Table, Dartboard, Card Table
     AND Dominoes Table (the rendered list file).
  2. In that file, find the Dominoes entry block (object literal)
     by brace-matching around the dominoes anchor line.
  3. If a Scrabble entry already exists in that same array, SKIP.
  4. Find the Scrabble image variable: a line with 'scrabble' and
     ('png' or 'require' or 'import'); else, if the Dominoes entry
     image is a require path containing 'dominoes', the Scrabble
     path is that path with 'dominoes' -> 'scrabble'. If neither
     is found, WARNING + skip (no wrong-image entry).
  5. Duplicate the Dominoes entry block right after it, renamed:
     id 'dominoes' -> 'scrabble', name 'Dominoes Table' ->
     'Scrabble Table', image -> Scrabble image, all other
     'dominoes'/'Dominoes' text -> 'scrabble'/'Scrabble'.
     Price is kept (Dominoes $20k = Scrabble $20k, as set).
  6. The game HTML, modals and tap wiring from v1 are reused (they
     are already in the file); v2 only adds the missing list entry.

FRONTEND ONLY (Expo Go reload to check). The backend Deploy is a
separate step for rooms/buy; the list itself does not need it
(Pool/Card/Dominoes prove that).

Run from repo root: python3 frontend/patch-house-scrabble-list-v2.py
Idempotent - safe to re-run.
"""
import glob
import re
import sys
from pathlib import Path


def find_rendered_file():
    """File containing all four working game names."""
    want = ["Pool Table", "Dartboard", "Card Table", "Dominoes Table"]
    for path in sorted(glob.glob("frontend/app/**/*.tsx", recursive=True) +
                       glob.glob("frontend/components/*.tsx")):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except FileNotFoundError:
            continue
        if all(w in src for w in want):
            return path, src
    return None, None


def entry_block(lines, anchor):
    """Object-literal block containing lines[anchor], via brace depth.
    Returns (start, end) inclusive, or None."""
    # Scan up: depth counts '}' as +1, '{' as -1 when going up; the
    # entry start is the '{' that brings depth back to 0.
    depth = 0
    start = None
    for i in range(anchor, -1, -1):
        depth += lines[i].count("}")
        depth -= lines[i].count("{")
        if depth <= 0 and "{" in lines[i]:
            start = i
            break
    if start is None:
        return None
    # Scan down: depth counts '{' as +1, '}' as -1; end when 0.
    depth = 0
    end = None
    for j in range(start, len(lines)):
        depth += lines[j].count("{")
        depth -= lines[j].count("}")
        if depth <= 0 and j > start:
            end = j
            break
    if end is None:
        return None
    return (start, end)


def scrabble_image_var(src, block_text):
    """Scrabble image variable from an import/require line, else a
    dominoes require path rewritten to scrabble, else None.
    Handles: import scrabble_png from '...png' (ES import),
    const scrabble_png = require('...png') (assignment), and
    require('...dominoes.png') in the Dominoes block (rewritten)."""
    for ln in src.split("\n"):
        low = ln.lower()
        if "scrabble" not in low:
            continue
        # ES import: import <var> from '...png'
        m = re.search(r"^\s*import\s+([A-Za-z_][A-Za-z0-9_]*)\s+from", ln)
        if m and "png" in low:
            return m.group(1)
        # Assignment with an image: <var> = require('...png') etc.
        if "png" in low or "require" in low:
            m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", ln)
            if m:
                return m.group(1)
    # Require path in the Dominoes block, rewritten to scrabble.
    m = re.search(r"require\(['\"]([^'\"]*dominoes[^'\"]*)['\"]\)", block_text, re.I)
    if m:
        return ("__REQUIRE_PATH__", m.group(1).replace("dominoes", "scrabble").replace("Dominoes", "Scrabble"))
    return None


def main():
    path, src = find_rendered_file()
    if not path:
        print("WARNING: no file containing all four of Pool/Dartboard/Card/Dominoes Table")
        print("HOUSE_SCRABBLE_LIST_V2_WARNING: rendered list file not found")
        return 0
    print("OK: rendered list file %s" % path)
    lines = src.split("\n")
    # Dominoes anchor: prefer an id line, else the name line.
    anchor = None
    for i, ln in enumerate(lines):
        if re.search(r"id\s*:\s*['\"]dominoes['\"]", ln):
            anchor = i
            break
    if anchor is None:
        for i, ln in enumerate(lines):
            if "Dominoes Table" in ln:
                anchor = i
                break
    if anchor is None:
        print("WARNING: Dominoes entry not found in %s" % path)
        print("HOUSE_SCRABBLE_LIST_V2_WARNING: dominoes entry not found")
        return 0
    blk = entry_block(lines, anchor)
    if not blk:
        print("WARNING: could not brace-match the Dominoes entry block")
        print("HOUSE_SCRABBLE_LIST_V2_WARNING: dominoes block not matched")
        return 0
    start, end = blk
    print("OK: Dominoes entry block lines %d-%d" % (start + 1, end + 1))
    block_text = "\n".join(lines[start:end + 1])
    # Already present in this array? (scrabble id/name near the block)
    window = "\n".join(lines[max(0, start - 5):min(len(lines), end + 30)])
    if re.search(r"id\s*:\s*['\"]scrabble['\"]", window) or "Scrabble Table" in window:
        # Make sure it is in the SAME array (not just elsewhere in file).
        # If scrabble appears within 30 lines after the dominoes block,
        # treat it as already added.
        print("SKIP: Scrabble entry already present after Dominoes")
        print("HOUSE_SCRABBLE_LIST_V2_OK")
        return 0
    img = scrabble_image_var(src, block_text)
    if img is None:
        print("WARNING: no Scrabble image variable or require path found")
        print("HOUSE_SCRABBLE_LIST_V2_WARNING: scrabble image not found")
        return 0
    new_block = block_text
    # Rename id + name + all dominoes text.
    new_block = re.sub(r"(['\"])dominoes\1", r"\1scrabble\1", new_block)
    new_block = new_block.replace("Dominoes Table", "Scrabble Table")
    new_block = new_block.replace("Dominoes", "Scrabble").replace("dominoes", "scrabble")
    # Image: find the image line in the ORIGINAL block and replace
    # exactly that image (variable or require path) with Scrabble's.
    img_line = None
    for ln in block_text.split("\n"):
        if re.search(r"\bimage\s*:", ln):
            img_line = ln
            break
    if img_line is None:
        print("WARNING: no image line in Dominoes entry block")
        print("HOUSE_SCRABBLE_LIST_V2_WARNING: image line not found")
        return 0
    if isinstance(img, tuple):
        # Scrabble image is a require path. Step 4 above already
        # rewrote 'dominoes'/'Dominoes' in the block to 'scrabble'/
        # 'Scrabble', so the dominoes require path is already the
        # Scrabble path; just verify it is there.
        if not re.search(r"require\(['\"][^'\"]*scrabble[^'\"]*['\"]\)", new_block, re.I):
            print("WARNING: scrabble require path not present after rename")
            print("HOUSE_SCRABBLE_LIST_V2_WARNING: image path not found")
            return 0
    else:
        # Scrabble image is a variable.
        if "require(" in img_line:
            # Dominoes image is a require path; replace the whole
            # require(...) with the Scrabble variable.
            new_block = re.sub(r"require\(['\"][^'\"]*['\"]\)", img, new_block, count=1)
        else:
            m = re.search(r"image\s*:\s*([A-Za-z_][A-Za-z0-9_]*)", img_line)
            if not m:
                print("WARNING: dominoes image variable not identifiable in entry block")
                print("HOUSE_SCRABBLE_LIST_V2_WARNING: image variable not found")
                return 0
            new_block = new_block.replace(m.group(1), img)
    if new_block == block_text:
        print("WARNING: duplicated block is identical to Dominoes (rename failed)")
        print("HOUSE_SCRABBLE_LIST_V2_WARNING: rename failed")
        return 0
    lines[end + 1:end + 1] = new_block.split("\n")
    Path(path).write_text("\n".join(lines))
    print("OK: Scrabble entry added right after Dominoes in %s" % path)
    print("HOUSE_SCRABBLE_LIST_V2_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
