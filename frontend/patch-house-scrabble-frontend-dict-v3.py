#!/usr/bin/env python3
"""Scrabble official dictionary v3 (NWL2023).

Replaces the game's word list with the OFFICIAL North American Scrabble
list (NASPA Word List 2023, NWL2023, ~196,601 words) in both game files:
  frontend/components/ScrabbleHtml.ts     (PvC - YOU vs CPU)
  frontend/components/ScrabblePvpHtml.ts  (PvP)

WHY: the old list (359,800 words, a general wordlist) contains words that
are NOT legal in official Scrabble, so the game let them through:
  LIQ - an abbreviation for liquid/liquor, illegal in official play
  EQ  - not a legal 2-letter word (only QI is valid with Q)
Both the player and the CPU validate against the same DICT, so swapping
the list fixes both sides at once. The CPU only plays words from DICT.

HOW: downloads NWL2023.txt (public mirror, scrabblewords repo), takes the
headword (first token) of each line, uppercases, joins with spaces, and
swaps it into the existing game files. It does NOT rewrite the game HTML,
so any later fixes (rejoin, wager, etc.) in the live files are preserved.
Handles both live states:
  - placeholder  __SCRABBLE_DICT__  still in the file, or
  - an old word blob already injected  var DICT = new Set("...".split(" "))
The list is fetched at patch time, NOT committed to the repo (NWL2023 is
a NASPA publication; the game fetches it like any app ships a word list).

Checks (aborts without changing anything if any fails):
  - download succeeds, 190,000-200,000 headwords (expect 196,601)
  - first word AA, BANANA / QI / POEM present
  - LIQ and EQ ABSENT (the reported illegal words)
After writing, re-reads each file and re-checks the injected DICT.

Run from /app (repo root):
  cd /app && curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/patch-house-scrabble-frontend-dict-v3.py?v=1" -o frontend/patch-house-scrabble-frontend-dict-v3.py && python3 frontend/patch-house-scrabble-frontend-dict-v3.py
Expect: SCRABBLE_DICT_V3_OK words=196601
Then reload Expo Go (full close + reopen) and play Scrabble: LIQ and EQ
must now be rejected with "Not a word: LIQ" / "Not a word: EQ", and the
CPU can no longer play them either.
"""
import sys
import urllib.request
from pathlib import Path

NWL_URL = "https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/North-American/NWL2023.txt"
DOM_TS = Path("frontend/components/ScrabbleHtml.ts")
DOM_PVP_TS = Path("frontend/components/ScrabblePvpHtml.ts")
ANCHOR = 'var DICT = new Set("'
END_MARKER = '".split(" ")'

# Words that MUST be in the official list (all valid on his board)
MUST_HAVE = ["AA", "BANANA", "QI", "POEM", "PLOW", "OI", "ENEMY", "EX", "ER", "HITS", "BIT"]
# Words that MUST NOT be in the official list (the reported illegal plays)
MUST_NOT_HAVE = ["LIQ", "EQ"]


def fail(msg):
    print("SCRABBLE_DICT_V3_ERROR: " + msg + " Nothing changed.")
    return False


def fetch_official():
    """Download NWL2023 and return the space-separated official headwords."""
    try:
        req = urllib.request.Request(NWL_URL, headers={"User-Agent": "street-legends-patch"})
        with urllib.request.urlopen(req, timeout=180) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return fail("could not download NWL2023 from " + NWL_URL + " (" + str(e) + ")")
    words = []
    seen = set()
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        head = line.split(None, 1)[0].upper()
        if head.isalpha() and head not in seen:
            seen.add(head)
            words.append(head)
    if not (190000 <= len(words) <= 200000):
        return fail("NWL2023 word count looks wrong (words=%d, expected ~196601)" % len(words))
    if not words or words[0] != "AA":
        return fail("NWL2023 first word is not AA (got %r)" % (words[0] if words else None))
    wset = set(words)
    for w in MUST_HAVE:
        if w not in wset:
            return fail("official list is missing a valid word: " + w)
    for w in MUST_NOT_HAVE:
        if w in wset:
            return fail("official list still contains illegal word: " + w)
    print("OK: NWL2023 downloaded (%d official words; LIQ/EQ absent, QI/POEM/BANANA present)" % len(words))
    return " ".join(words)


def extract_dict_blob(src):
    """Return the word blob inside var DICT = new Set("...".split(" ")), or None."""
    i = src.find(ANCHOR)
    if i < 0:
        return None
    start = i + len(ANCHOR)
    j = src.find(END_MARKER, start)
    if j < 0:
        return None
    return src[start:j]


def swap_dict(path, new_dict):
    if not path.exists():
        print("SKIP: %s not found (game file missing, nothing changed there)" % path)
        return False
    src = path.read_text()
    if "__SCRABBLE_DICT__" in src:
        src2 = src.replace("__SCRABBLE_DICT__", new_dict)
        mode = "placeholder"
    else:
        blob = extract_dict_blob(src)
        if blob is None:
            print("ERROR: %s: DICT anchor not found (no placeholder, no var DICT line). Nothing changed." % path)
            return False
        i = src.find(ANCHOR) + len(ANCHOR)
        j = src.find(END_MARKER, i)
        src2 = src[:i] + new_dict + src[j:]
        mode = "blob(%d words)" % len(blob.split(" "))
    path.write_text(src2)
    # verify what actually landed in the file
    check = extract_dict_blob(path.read_text())
    if check is None:
        print("ERROR: %s: could not re-read DICT after write." % path)
        return False
    cw = set(check.split(" "))
    bad = [w for w in MUST_NOT_HAVE if w in cw]
    missing = [w for w in MUST_HAVE if w not in cw]
    if bad or missing or len(cw) < 190000:
        print("ERROR: %s: verification failed (illegal still in=%s, valid missing=%s, words=%d)" % (path, bad, missing, len(cw)))
        return False
    print("OK: %s DICT swapped (%s -> %d official words; LIQ/EQ gone, QI in)" % (path.name, mode, len(cw)))
    return True


def main():
    new_dict = fetch_official()
    if new_dict is False:
        return
    ok1 = swap_dict(DOM_TS, new_dict)
    ok2 = swap_dict(DOM_PVP_TS, new_dict)
    if ok1 and ok2:
        print("SCRABBLE_DICT_V3_OK words=%d" % len(new_dict.split(" ")))
    elif ok1 or ok2:
        print("SCRABBLE_DICT_V3_PARTIAL: one game file updated, the other was not. See lines above.")
    else:
        print("SCRABBLE_DICT_V3_ERROR: neither game file was updated. Nothing changed.")


if __name__ == "__main__":
    main()
