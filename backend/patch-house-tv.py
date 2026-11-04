#!/usr/bin/env python3
"""Street Legends backend: TV house item (Appliances tab).

PRICE = 5000 (buy), SELL = PRICE // 2 (2500 back, via the generic
half-refund remove endpoint). Price confirmed by the user ("For $5k").

Catalog only: adds "tv" {"name": "TV", "category": "appliances",
"price": PRICE} to HOUSE_ITEM_CATALOG. The generic items/add | remove |
move endpoints already handle any catalog item (same pattern as the
Radio port), so no rooms, no PvP, no wagering, no new routes are needed
for this item. The schedule-player behavior (live schedule fetch,
random fallback, LEAVE HOUSE stop) is entirely frontend; the backend
only needs to know the item exists at $5,000.

No new routes are defined, so the /api-prefix lesson cannot bite here;
no Motor DB calls are added, so no await issue; no datetime use, so no
timezone import issue. The new source is still syntax-checked with
py_compile before writing (same guard as the Radio port).

Run from /app: python3 backend/patch-house-tv.py
Idempotent: re-running prints TV_BACKEND_ALREADY_APPLIED and changes nothing.
Backend only: Deploy (Publish) after running so the catalog is live.
Frontend patch comes separately (Expo Go reload, no build).
"""
import re
import sys
import py_compile
import tempfile
import os

PATH = "backend/server.py"
MARKER = "TV_BACKEND_OK"
PRICE = 5000
ENTRY = '"tv": {"name": "TV", "category": "appliances", "price": %d},' % PRICE


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("TV_BACKEND_ERROR: backend/server.py not found (run from /app)")
        return 1
    m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{([\s\S]*?)\n\}", src)
    if m and '"tv"' in m.group(1):
        print("TV_BACKEND_ALREADY_APPLIED")
        print(MARKER)
        return 0
    m2 = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
    if not m2:
        print("TV_BACKEND_ERROR: HOUSE_ITEM_CATALOG not found")
        return 1
    anchor = None
    for key in ("radio", "texas_holdem", "chess_checkers", "scrabble", "dominoes", "cardtable", "dartboard", "pool-table"):
        anchor = re.search(r'\n(\s*)"' + key + r'":\s*\{[^}]*\},', src[m2.end():])
        if anchor:
            break
    if anchor:
        indent = anchor.group(1)
        ins_at = m2.end() + anchor.end()
        src = src[:ins_at] + "\n" + indent + ENTRY + src[ins_at:]
    else:
        ins_at = m2.end()
        src = src[:ins_at] + "\n    " + ENTRY + src[ins_at:]
    print("OK: TV added to HOUSE_ITEM_CATALOG (price %d, appliances)" % PRICE)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("TV_BACKEND_ERROR: syntax check failed: %s" % e)
        return 1
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
