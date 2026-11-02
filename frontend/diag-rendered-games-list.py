#!/usr/bin/env python3
"""Street Legends diagnostic (READ-ONLY, no writes): which array does
the Games tab actually render, and is Scrabble in THAT array?

Why: the backend is live (rooms return "Room not found") and the
frontend file contains a Scrabble entry after Dominoes (v2 SKIP),
yet the Games list still shows only Pool/Dartboard/Card/Dominoes.
v2 only checked that Scrabble appears NEAR Dominoes, not that it is
in the array the Games tab maps over. A Scrabble entry in a different
array/modal (nearby but not rendered) would fool that check.

What this prints:
  1. The file containing Pool/Dartboard/Card/Dominoes Table.
  2. Every `.map(` array variable in that file (the rendered lists).
  3. For each mapped variable: whether it is a literal array in the
     file (const/let <var> = [...]) or dynamic (state/props/fetch —
     i.e. NOT a literal, so the list is not frontend-literal-driven).
  4. For each literal mapped array: which of Pool/Dartboard/Card/
     Dominoes/Scrabble are in it (by id or name), with line numbers.
  5. Where Scrabble appears in the file if it is NOT in any mapped
     literal array (so we know which non-rendered block holds it).

Run from /app: python3 frontend/diag-rendered-games-list.py
Read-only. Prints DIAG_RENDERED_GAMES_LIST_OK at the end.
"""
import glob
import re
import sys


GAMES = [
    ("pool", "Pool Table"),
    ("dartboard", "Dartboard"),
    ("cardtable", "Card Table"),
    ("dominoes", "Dominoes Table"),
    ("scrabble", "Scrabble Table"),
]


def find_file():
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


def bracket_block(lines, start):
    """Array literal starting at lines[start] (which contains '[').
    Returns (end_line_inclusive) via bracket depth, or None."""
    depth = 0
    for j in range(start, len(lines)):
        depth += lines[j].count("[")
        depth -= lines[j].count("]")
        if depth <= 0 and j > start:
            return j
    return None


def main():
    path, src = find_file()
    if not path:
        print("WARNING: no file containing all four of Pool/Dartboard/Card/Dominoes Table")
        return 0
    print("FILE: %s" % path)
    lines = src.split("\n")
    # All .map( variables.
    mapped = []
    for i, ln in enumerate(lines):
        for m in re.finditer(r"(\w+)\.map\s*\(", ln):
            var = m.group(1)
            if var not in mapped:
                mapped.append(var)
    print("MAPPED VARIABLES (arrays the file renders via .map): %s" % (", ".join(mapped) if mapped else "(none found)"))
    found_rendered_scrabble = False
    for var in mapped:
        # Find literal definition: const/let/var <var> = [
        def_idx = None
        for i, ln in enumerate(lines):
            if re.search(r"\b(const|let|var)\s+%s\s*=\s*\[" % re.escape(var), ln):
                def_idx = i
                break
        if def_idx is None:
            print("  %s: DYNAMIC (not a literal array in this file — state/props/fetch; list is not frontend-literal-driven)" % var)
            continue
        end = bracket_block(lines, def_idx)
        if end is None:
            print("  %s: literal at line %d but bracket match failed" % (var, def_idx + 1))
            continue
        block = "\n".join(lines[def_idx:end + 1])
        present = []
        for gid, gname in GAMES:
            if re.search(r"id\s*:\s*['\"]%s['\"]" % gid, block) or gname in block:
                present.append(gname)
        print("  %s: literal lines %d-%d, contains: %s" % (var, def_idx + 1, end + 1, ", ".join(present) if present else "(none of the five)"))
        if "Scrabble Table" in block or re.search(r"id\s*:\s*['\"]scrabble['\"]", block):
            found_rendered_scrabble = True
            # Scrabble entry line(s) in this array.
            for k in range(def_idx, end + 1):
                if "Scrabble Table" in lines[k] or re.search(r"id\s*:\s*['\"]scrabble['\"]", lines[k]):
                    print("    Scrabble entry line: %d: %s" % (k + 1, lines[k].strip()[:120]))
    # Where does Scrabble appear in the file at all?
    scrabble_lines = [i + 1 for i, ln in enumerate(lines)
                      if "Scrabble Table" in ln or re.search(r"id\s*:\s*['\"]scrabble['\"]", ln)]
    print("SCRABBLE LINES IN FILE: %s" % (", ".join(map(str, scrabble_lines)) if scrabble_lines else "(none)"))
    if scrabble_lines and not found_rendered_scrabble:
        print("CONCLUSION: Scrabble IS in the file but NOT in any mapped literal array — it is in a non-rendered block (different array/modal). The Games tab does not render it.")
    elif found_rendered_scrabble:
        print("CONCLUSION: Scrabble IS in a mapped literal array — the frontend list should render it (if the bundle is current; otherwise the bundle is stale).")
    else:
        print("CONCLUSION: Scrabble is NOT in the file at all in a mapped array or elsewhere as an entry.")
    print("DIAG_RENDERED_GAMES_LIST_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
