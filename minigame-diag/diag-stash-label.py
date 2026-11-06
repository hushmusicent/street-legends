#!/usr/bin/env python3
"""diag-stash-label.py -- read-only byte-exact dump of the Stash Box dropdown label.

Prints lines 4690-4720 of frontend/app/(tabs)/index.tsx with repr(), a
non-ASCII character inventory, whole-file string counts, the HOUSE_ITEMS
.map line, and a verdict. Never modifies anything. No network calls.
"""
import glob
import os

INDEX = "frontend/app/(tabs)/index.tsx"
DUMP_START = 4690
DUMP_END = 4720
CHECK = chr(0x2713)
BS = chr(92)
ESC_2713 = BS + "u2713"
ESC_BRACE = BS + "u{2713}"
NEEDLES = ["PLACED", "INVENTORY[", "TAP TO PLACE", "{placed ?", "placed ?", "BUY $"]


def find_lines(lines, needle):
    return [i + 1 for i, l in enumerate(lines) if needle in l]


def squashed(line):
    return line.replace(" ", "").replace("\t", "")


def main():
    missing = []
    print("=== stash label diag (read-only, code only) ===")
    print("root: " + os.getcwd())
    if not os.path.exists(INDEX):
        print(INDEX + ": NOT FOUND")
        print("STASH_LABEL_DIAG_PARTIAL missing=index.tsx verdict=(d)")
        return
    raw = open(INDEX, encoding="utf-8", errors="replace").read()
    lines = raw.split("\n")
    total = len(lines)
    print("index file: " + INDEX + " (" + str(total) + " lines)")

    print()
    print("=== 1. line dump (repr, lines %d-%d) ===" % (DUMP_START, DUMP_END))
    if total < DUMP_START:
        print("file has only %d lines - dump range is past end of file" % total)
        missing.append("dump-range")
    else:
        for n in range(DUMP_START, min(DUMP_END, total) + 1):
            print("%d: %s" % (n, repr(lines[n - 1])))

    print()
    print("=== 2. non-ASCII characters on dumped lines ===")
    found_nonascii = False
    for n in range(DUMP_START, min(DUMP_END, total) + 1):
        for ch in lines[n - 1]:
            if ord(ch) > 127:
                print("line %d: char %s code point U+%04X" % (n, repr(ch), ord(ch)))
                found_nonascii = True
    if not found_nonascii:
        print("no non-ASCII characters on lines %d-%d" % (DUMP_START, min(DUMP_END, total)))
    print("--- checkmark forms in the whole file ---")
    print("literal checkmark %s: %d occurrence(s)" % (repr(CHECK), raw.count(CHECK)))
    print("escape text %s: %d occurrence(s)" % (repr(ESC_2713), raw.count(ESC_2713)))
    print("escape text %s: %d occurrence(s)" % (repr(ESC_BRACE), raw.count(ESC_BRACE)))

    print()
    print("=== 3. whole-file string counts ===")
    counts = {}
    for needle in NEEDLES:
        hits = find_lines(lines, needle)
        counts[needle] = hits
        total_occ = sum(lines[i - 1].count(needle) for i in hits)
        print("%s: %d occurrence(s) on %d line(s): %s" % (repr(needle), total_occ, len(hits), hits[:10]))

    print()
    print("=== 4. HOUSE_ITEMS .map line ===")
    map_lines = find_lines(lines, "HOUSE_ITEMS[houseItemCategory]")
    if map_lines:
        for n in map_lines:
            print("line %d: %s" % (n, repr(lines[n - 1])))
    else:
        print("no line contains 'HOUSE_ITEMS[houseItemCategory]'")
        missing.append("map-line")
    print("--- first appearance of each label string after the .map line ---")
    base = map_lines[0] if map_lines else 1
    for needle in ["PLACED", "INVENTORY[", "TAP TO PLACE"]:
        after = [n for n in find_lines(lines, needle) if n >= base]
        if after:
            print("%s: first at line %d (%d line(s) after .map line %d)" % (repr(needle), after[0], after[0] - base, base))
        else:
            print("%s: NOT FOUND after .map line %d" % (repr(needle), base))

    print()
    print("=== 5. verdict ===")
    other_hits = {}
    for path in sorted(glob.glob("frontend/components/*.tsx")) + ["frontend/app/(tabs)/character.tsx"]:
        if os.path.exists(path):
            olines = open(path, encoding="utf-8", errors="replace").read().split("\n")
            hits = [i + 1 for i, l in enumerate(olines) if "PLACED" in l]
            if hits:
                other_hits[path] = hits
    if other_hits:
        for path, hits in other_hits.items():
            print("PLACED also in %s at lines %s" % (path, hits[:10]))
    else:
        print("PLACED in no other frontend file checked (components/*.tsx, character.tsx)")

    verdict = None
    detail = ""
    placed_lines = counts["PLACED"]
    if not placed_lines:
        verdict = "(d)"
        detail = "no 'PLACED' anywhere in index.tsx"
        missing.append("label-not-in-index")
    else:
        start = None
        for n in range(base, min(base + 60, total) + 1):
            if "placed?" in squashed(lines[n - 1]):
                start = n
                break
        if start is None:
            after = [n for n in placed_lines if n >= base]
            start = after[0] if after else placed_lines[0]
        span_lines = []
        joined = ""
        for n in range(start, min(start + 10, total) + 1):
            span_lines.append(n)
            joined = "\n".join(lines[m - 1] for m in span_lines)
            if "PLACED" in joined and "INVENTORY[" in joined and "TAP TO PLACE" in joined:
                break
            if "</Text>" in lines[n - 1]:
                break
        has_all = "PLACED" in joined and "INVENTORY[" in joined and "TAP TO PLACE" in joined
        if not has_all:
            verdict = "(d)"
            detail = "label span near line %d lacks one of PLACED / INVENTORY[ / TAP TO PLACE" % start
            missing.append("label-incomplete")
        else:
            has_literal = CHECK in joined
            has_escape = ESC_2713 in joined or ESC_BRACE in joined
            if has_literal and has_escape:
                form = "BOTH"
            elif has_literal:
                form = "LITERAL"
            elif has_escape:
                form = "ESCAPE"
            else:
                form = "NONE"
            print("label span: lines %d-%d" % (span_lines[0], span_lines[-1]))
            print("checkmark form in span: " + form)
            if has_escape and not has_literal:
                verdict = "(c)"
                detail = "checkmark is an escape only in the label span (lines %d-%d)" % (span_lines[0], span_lines[-1])
            elif len(span_lines) == 1:
                verdict = "(a)"
                detail = "label expression is on ONE line (%d)" % span_lines[0]
            else:
                verdict = "(b)"
                detail = "label expression is SPLIT across lines %d-%d" % (span_lines[0], span_lines[-1])
    print("VERDICT: %s %s" % (verdict, detail))
    if missing:
        print("STASH_LABEL_DIAG_PARTIAL missing=%s verdict=%s" % (",".join(missing), verdict))
    else:
        print("STASH_LABEL_DIAG_OK verdict=%s" % verdict)


if __name__ == "__main__":
    main()
