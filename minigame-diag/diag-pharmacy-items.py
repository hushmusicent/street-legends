#!/usr/bin/env python3
"""Pharmacy items follow-up probe: find the REAL items array the shop row
maps over. The buy10 probe (diag-pharmacy-buy10.py) found TWO grass-item
lines in live index.tsx; the first (line 2473) uses `price` only, but the
shop row reads `item.buy` / `item.sell` -- so a second array must carry
buy/sell. This probe prints BOTH occurrences with context so the patch can
anchor on the right one. READ-ONLY. Run: python3 minigame-diag/diag-pharmacy-items.py [--root /app]
"""
import argparse
import sys
from pathlib import Path

MARKER = "PHARMACY_ITEMS_DIAG_OK"


def read_file(path):
    try:
        return Path(path).read_text(errors="ignore").splitlines()
    except OSError:
        return None


def show(lines, i, before=6, after=6, label=""):
    lo = max(0, i - before)
    hi = min(len(lines) - 1, i + after)
    print("  --- %s (line %d, ctx %d-%d) ---" % (label, i + 1, lo + 1, hi + 1))
    for j in range(lo, hi + 1):
        print("  %d: %r" % (j + 1, lines[j][:300]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    root = Path(ap.parse_args().root)
    idx = None
    for cand in ("frontend/app/(tabs)/index.tsx", "frontend/app/index.tsx"):
        p = root / cand
        if p.exists():
            idx = read_file(p)
            print("index.tsx: %s (%d lines)" % (p, len(idx)))
            break
    if idx is None:
        print("index.tsx NOT FOUND")
        print(MARKER)
        return 1
    print("=== 1. every grass item line ===")
    hits = [i for i, ln in enumerate(idx) if "id: 'grass'" in ln or 'id: "grass"' in ln]
    print("  grass item lines: %d" % len(hits))
    for i in hits:
        show(idx, i, 6, 6, "grass line")
    print("=== 2. buy/sell field counts ===")
    for needle in ("buy: 100", "sell: 50", "buy: 200", "sell: 100", "price: 100"):
        print("  %r count: %d" % (needle, sum(1 for ln in idx if needle in ln)))
    print("=== 3. pharmacyItems definition + map ===")
    defs = [i for i, ln in enumerate(idx) if "pharmacyItems" in ln and ("=" in ln or "const" in ln)]
    print("  pharmacyItems definition-ish lines: %d" % len(defs))
    for i in defs[:4]:
        show(idx, i, 1, 1, "pharmacyItems def")
    maps = [i for i, ln in enumerate(idx) if "pharmacyItems.map" in ln]
    print("  pharmacyItems.map count: %d" % len(maps))
    for i in maps[:2]:
        show(idx, i, 0, 8, "pharmacyItems.map")
    print("=== 4. canBuy/canSell in the row ===")
    for needle in ("const canBuy = cash >= item.buy", "const canSell = held >= 1"):
        hits2 = [i for i, ln in enumerate(idx) if needle in ln]
        print("  %r count: %d" % (needle, len(hits2)))
        for i in hits2[:1]:
            show(idx, i, 0, 2, "canBuy/canSell")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
