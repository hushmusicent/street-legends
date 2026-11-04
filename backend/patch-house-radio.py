#!/usr/bin/env python3
"""Street Legends backend: Radio house item (Appliances tab).

PRICE = 5000 (buy), SELL = PRICE // 2 (2500 back, via the generic
half-refund remove endpoint). Price confirmed by the user ("add a radio
for 5k to the house appliances tab").

Catalog only: adds "radio" {"name": "Radio", "category": "appliances",
"price": PRICE} to HOUSE_ITEM_CATALOG. The generic items/add | remove |
move endpoints already handle any catalog item (same pattern as the
Texas Hold'em / Chess & Checkers ports), so no rooms, no PvP, no
wagering, no new routes are needed for this item. The audio behavior
(play/stop toggle, house-level ownership, LEAVE HOUSE stop) is entirely
frontend; the backend only needs to know the item exists at $5,000.

No new routes are defined, so the /api-prefix lesson cannot bite here;
no Motor DB calls are added, so no await issue; no datetime use, so no
timezone import issue. The new source is still syntax-checked with
py_compile before writing (same guard as the room patches).

Run from /app: python3 backend/patch-house-radio.py
Idempotent: re-running prints SKIP and changes nothing.
Backend only: Deploy (Publish) after running so the catalog is live.
Frontend patch comes separately (Expo Go reload, no build).
"""
import re
import sys
import py_compile
import tempfile
import os

PATH = "backend/server.py"
MARKER = "RADIO_BACKEND_OK"
PRICE = 5000
ENTRY = '"radio": {"name": "Radio", "category": "appliances", "price": %d},' % PRICE


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("RADIO_BACKEND_ERROR: backend/server.py not found (run from /app)")
        return 1
    m = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{([\s\S]*?)\n\}", src)
    if m and '"radio"' in m.group(1):
        print("SKIP: Radio already in HOUSE_ITEM_CATALOG")
    else:
        m2 = re.search(r"HOUSE_ITEM_CATALOG\s*=\s*\{", src)
        if not m2:
            print("RADIO_BACKEND_ERROR: HOUSE_ITEM_CATALOG not found")
            return 1
        anchor = None
        for key in ("texas_holdem", "chess_checkers", "scrabble", "dominoes", "cardtable", "dartboard", "pool-table"):
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
        print("OK: Radio added to HOUSE_ITEM_CATALOG (price %d, appliances)" % PRICE)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8")
    try:
        tmp.write(src)
        tmp.close()
        py_compile.compile(tmp.name, doraise=True)
    except Exception as e:
        print("RADIO_BACKEND_ERROR: syntax check failed: %s" % e)
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
