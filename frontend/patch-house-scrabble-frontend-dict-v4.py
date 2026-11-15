#!/usr/bin/env python3
"""Street Legends frontend: Scrabble official dictionary v4 (lowercase fix).

v3 injected the official NWL2023 list but UPPERCASED it, while the game
validates with DICT.has(word.toLowerCase()) — a lowercase lookup against
an uppercase Set never matches, so EVERY word was rejected ("Not a word:
FEUD" — FEUD is in NWL2023). v4 rebuilds the same official list in
LOWERCASE, which is what the game (and the old v2 list) used.

Downloads NWL2023 at run time, takes the headword (first token) of each
line, lowercases, joins with spaces, and swaps ONLY the DICT blob in
ScrabbleHtml.ts (PvC) + ScrabblePvpHtml.ts (PvP). Validates the count
(190,000-200,000), first word "aa", and that feud/qi/poem/banana are IN
and liq/eq are OUT (all lowercase); aborts changing nothing on failure.
Does NOT commit the word list. Does NOT rewrite the game HTML.

Run from /app: python3 frontend/patch-house-scrabble-frontend-dict-v4.py
Frontend only: reload Expo Go after running, then play FEUD — it must
be accepted, and LIQ must still be rejected.
"""
import sys
import urllib.request
from pathlib import Path

URL = "https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/North-American/NWL2023.txt"
TARGETS = [
    Path("frontend/components/ScrabbleHtml.ts"),
    Path("frontend/components/ScrabblePvpHtml.ts"),
]
MARKER = "SCRABBLE_DICT_V4_OK"

START = 'var DICT = new Set("'
END_MARKER = '".split(" ")'


def extract_blob(src):
    i = src.find(START)
    if i == -1:
        return None, None
    j = src.find(END_MARKER, i + len(START))
    if j == -1:
        return None, None
    return src[i + len(START):j], (i, j + len(END_MARKER))


def main():
    print("Downloading NWL2023 ...")
    try:
        with urllib.request.urlopen(URL, timeout=60) as r:
            raw = r.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print("SCRABBLE_DICT_V4_DOWNLOAD_FAIL: %s (nothing changed)" % e)
        return 1
    words = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        head = line.split(None, 1)[0].lower()
        if head.isalpha():
            words.append(head)
    # De-duplicate, keep order.
    seen = set()
    uniq = []
    for w in words:
        if w not in seen:
            seen.add(w)
            uniq.append(w)
    n = len(uniq)
    print("NWL2023 downloaded (%d official words, lowercase)" % n)
    if not (190000 <= n <= 200000):
        print("SCRABBLE_DICT_V4_COUNT_FAIL: words=%d (expected 190000-200000, nothing changed)" % n)
        return 1
    if uniq[0] != "aa":
        print("SCRABBLE_DICT_V4_FIRST_FAIL: first=%r (expected 'aa', nothing changed)" % uniq[0])
        return 1
    s = set(uniq)
    for w in ("feud", "qi", "poem", "banana", "plow"):
        if w not in s:
            print("SCRABBLE_DICT_V4_MISSING: %r not in list (nothing changed)" % w)
            return 1
    for w in ("liq", "eq"):
        if w in s:
            print("SCRABBLE_DICT_V4_ILLEGAL_PRESENT: %r in list (nothing changed)" % w)
            return 1
    print("OK: NWL2023 downloaded (%d official words; LIQ/EQ absent, FEUD/QI/POEM/BANANA present, lowercase)" % n)
    new_dict = " ".join(uniq)
    changed = 0
    for path in TARGETS:
        if not path.exists():
            print("WARNING: %s not found - skipped" % path)
            continue
        src = path.read_text(errors="ignore")
        blob, span = extract_blob(src)
        if blob is None:
            print("WARNING: DICT blob not found in %s - skipped" % path)
            continue
        old_count = len(blob.split(" ")) if blob else 0
        if blob == new_dict:
            print("OK: %s DICT already lowercase official (%d words)" % (path.name, n))
            continue
        src2 = src[:span[0]] + START + new_dict + END_MARKER + src[span[1]:]
        # Re-verify after swap.
        blob2, _ = extract_blob(src2)
        if blob2 != new_dict:
            print("SCRABBLE_DICT_V4_SWAP_FAIL: %s (nothing written)" % path.name)
            return 1
        path.write_text(src2)
        print("OK: %s DICT swapped (old %d words -> %d words, lowercase)" % (path.name, old_count, n))
        changed += 1
    if changed == 0:
        print("SCRABBLE_DICT_V4_ALREADY_APPLIED")
    print("%s words=%d" % (MARKER, n))
    return 0


if __name__ == "__main__":
    sys.exit(main())
