#!/usr/bin/env python3
"""Read-only diagnostic for the house MOVE feature (no changes made).

Prints, so the MOVE patch can be written against the real code:
  1. The Supply Shop house card: the file containing "YOUR HOUSE", plus
     60 lines around the first "YOUR HOUSE" match (the card + its button).
  2. The map house-marker options: lines containing "hide" in the map
     screen (the enter/hide/sell menu the shop text mentions).
  3. The houses backend routes: every @api_router line mentioning houses
     in backend/server.py, plus the handler line that follows it.

Run from repo root: python3 frontend/diag-house-shop.py
Prints DIAG_HOUSE_SHOP_OK at the end. Changes nothing.
"""
import glob
import re
import sys

ROOTS = ["frontend/app", "frontend/components"]


def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except FileNotFoundError:
        return None


def show_context(path, lines, idx, before, after, label):
    start = max(0, idx - before)
    end = min(len(lines), idx + after + 1)
    print("--- %s (%s lines %d-%d) ---" % (label, path, start + 1, end))
    for i in range(start, end):
        print("%d: %s" % (i + 1, lines[i]))


def main():
    # 1. Shop house card: find the file with "YOUR HOUSE".
    shop_path = None
    shop_lines = None
    for path in sorted(glob.glob("frontend/app/**/*.tsx", recursive=True) +
                       glob.glob("frontend/components/*.tsx")):
        src = read(path)
        if src and "YOUR HOUSE" in src:
            shop_path = path
            shop_lines = src.split("\n")
            break
    if shop_path:
        idx = next(i for i, ln in enumerate(shop_lines) if "YOUR HOUSE" in ln)
        show_context(shop_path, shop_lines, idx, 40, 20, "SHOP HOUSE CARD")
    else:
        print("SHOP: no file containing YOUR HOUSE found under frontend/app or frontend/components")

    # 2. Map house-marker options: lines with "hide" in the map screen.
    map_src = read("frontend/app/(tabs)/index.tsx")
    if map_src:
        map_lines = map_src.split("\n")
        hits = [i for i, ln in enumerate(map_lines) if "hide" in ln.lower()]
        print("--- MAP hide lines: %d hits ---" % len(hits))
        for idx in hits[:3]:
            show_context("frontend/app/(tabs)/index.tsx", map_lines, idx, 8, 8, "MAP hide")
    else:
        print("MAP: frontend/app/(tabs)/index.tsx not found")

    # 3. Houses backend routes.
    be = read("backend/server.py")
    if be:
        be_lines = be.split("\n")
        routes = [(i, ln.strip()) for i, ln in enumerate(be_lines)
                  if "api_router" in ln and "house" in ln.lower()]
        print("--- BACKEND houses routes: %d ---" % len(routes))
        for i, ln in routes:
            nxt = be_lines[i + 1].strip() if i + 1 < len(be_lines) else ""
            print("%d: %s | %s" % (i + 1, ln, nxt))
    else:
        print("BACKEND: backend/server.py not found")

    print("DIAG_HOUSE_SHOP_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
