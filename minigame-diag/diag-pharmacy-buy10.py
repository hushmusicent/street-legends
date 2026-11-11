#!/usr/bin/env python3
"""Pharmacy buy-10 + descriptions probe: print the LIVE pharmacy code on /app
so the patch can be built against what is actually there.

CONTEXT (parent, 2026-11-07): the user is IN the pharmacy right now
(screenshot: Rite Aid, cash $1,827,304, Grass 3 oz, Pills 2 oz, Rock Candy
0 oz, Flake 2 oz, Brown Sugar 0 oz, BUY 1 OZ / SELL 1 OZ buttons). He said:
"the pharmacy needs description on items and allow to buy 1 or 10 items
at a time". The pharmacy was built 2026-11-05 (backend/patch-pharmacy.py
PHARMACY_BACKEND_OK + frontend/patch-pharmacy-frontend.py
PHARMACY_FRONTEND_OK, commit 5e5d15ec, sync 83). The patch files ALREADY
carry a qty parameter on buy/sell (backend + api.ts + handler all take
qty, default 1) -- but the frontend hardcodes 1 and shows no descriptions.
This probe confirms whether the LIVE code has that qty support (frontend-only
patch) or the backend never got it (backend patch needed too).

This probe is READ-ONLY: it never edits a file, never restarts anything,
and makes no network calls -- it only reads the code under <root>. It prints:
  0. which files exist (server.py / index.tsx / api.ts) + line counts
  1. BACKEND buy endpoint: route, qty parameter, price math (qty x unit
     price?), inventory add, cash check, validation
  2. FRONTEND api.ts pharmacyBuy/pharmacySell: qty parameter + payload
  3. FRONTEND index.tsx pharmacy items array (id/name/buy/sell/desc?),
     handlePharmacyTrade (qty?), and the item-row JSX VERBATIM
     (name / Held / BUY / SELL buttons)
  4. VERDICT: (a) backend supports qty -> frontend-only patch,
     (b) backend lacks qty -> backend patch needed too,
     (c) pharmacy not live at all

Run:  python3 minigame-diag/diag-pharmacy-buy10.py [--root /app]
"""
import argparse
import sys
from pathlib import Path

MARKER = "PHARMACY_BUY10_DIAG_OK"

SERVER_PATH = "backend/server.py"
INDEX_CANDIDATES = [
    "frontend/app/(tabs)/index.tsx",
    "frontend/app/index.tsx",
]
API_PATH = "frontend/services/api.ts"


def read_file(path):
    try:
        return Path(path).read_text(errors="ignore").splitlines()
    except OSError:
        return None


def count(lines, needle):
    return sum(1 for ln in lines if needle in ln) if lines else 0


def show_block(lines, start, end, label):
    print("  --- %s (lines %d-%d) ---" % (label, start + 1, end + 1))
    for i in range(start, min(end + 1, len(lines))):
        print("  %d: %r" % (i + 1, lines[i][:300]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    print("=== 0. files ===")
    srv = read_file(root / SERVER_PATH)
    print("server.py: %s" % ("EXISTS (%d lines)" % len(srv) if srv else "MISSING"))
    idx_lines = None
    for cand in INDEX_CANDIDATES:
        p = root / cand
        if p.exists():
            idx_lines = read_file(p)
            print("index.tsx: %s (%d lines)" % (p, len(idx_lines)))
            break
    if idx_lines is None:
        print("index.tsx: NOT FOUND under %s" % root)
    api = read_file(root / API_PATH)
    print("api.ts: %s" % ("EXISTS (%d lines)" % len(api) if api else "MISSING"))
    src_idx = "\n".join(idx_lines) if idx_lines else ""
    src_srv = "\n".join(srv) if srv else ""
    src_api = "\n".join(api) if api else ""

    print("=== 1. BACKEND buy endpoint ===")
    if srv:
        buy_at = [i for i, ln in enumerate(srv) if "/pharmacies/buy" in ln]
        print("  '/pharmacies/buy' occurrences: %d" % len(buy_at))
        for i in buy_at[:3]:
            show_block(srv, max(0, i - 2), min(len(srv) - 1, i + 30), "buy endpoint around line %d" % (i + 1))
        # qty handling signals (plain substring counts, no regex on live code)
        for needle in ("qty", "quantity", "price_paid", "unit_price", "qty *", "qty*"):
            print("  count %r in server.py: %d" % (needle, count(srv, needle)))
    else:
        print("  server.py missing - cannot check backend")

    print("=== 2. FRONTEND api.ts pharmacyBuy/pharmacySell ===")
    if api:
        for fn in ("pharmacyBuy", "pharmacySell"):
            hits = [i for i, ln in enumerate(api) if fn in ln]
            print("  %s occurrences: %d" % (fn, len(hits)))
            for i in hits[:2]:
                show_block(api, i, min(len(api) - 1, i + 2), fn)
    else:
        print("  api.ts missing - cannot check api functions")

    print("=== 3. FRONTEND index.tsx pharmacy items + trade + row ===")
    if idx_lines:
        # items array
        arr = [i for i, ln in enumerate(idx_lines) if "id: 'grass'" in ln or 'id: "grass"' in ln]
        print("  grass item line count: %d" % len(arr))
        for i in arr[:1]:
            show_block(idx_lines, i, min(len(idx_lines) - 1, i + 5), "pharmacyItems array")
        # description field?
        print("  'desc' in index.tsx: %s (count %d)" % (("desc" in src_idx), count(idx_lines, "desc")))
        # trade handler
        th = [i for i, ln in enumerate(idx_lines) if "handlePharmacyTrade" in ln and "const " in ln]
        print("  handlePharmacyTrade definition count: %d" % len(th))
        for i in th[:1]:
            show_block(idx_lines, i, min(len(idx_lines) - 1, i + 14), "handlePharmacyTrade")
        # buy call qty
        print("  'pharmacyBuy(playerId, item.id, 1)' count: %d" % count(idx_lines, "pharmacyBuy(playerId, item.id, 1)"))
        print("  'pharmacyBuy(playerId, item.id,' count: %d" % count(idx_lines, "pharmacyBuy(playerId, item.id,"))
        # item row JSX (name + Held + buttons)
        held = [i for i, ln in enumerate(idx_lines) if "Held: {held} oz" in ln]
        print("  'Held: {held} oz' count: %d" % len(held))
        for i in held[:1]:
            show_block(idx_lines, i - 2, min(len(idx_lines) - 1, i + 22), "item row JSX")
    else:
        print("  index.tsx missing - cannot check frontend")

    print("=== 4. VERDICT ===")
    backend_qty = bool(srv) and ("/pharmacies/buy" in src_srv) and ("qty" in src_srv)
    frontend_live = bool(idx_lines) and ("Held: {held} oz" in src_idx) and ("BUY 1 OZ" in src_idx)
    if not frontend_live:
        print("VERDICT: (c) pharmacy not live in index.tsx")
    elif backend_qty:
        print("VERDICT: (a) backend supports qty -> FRONTEND-ONLY patch")
        print("  (add desc per item + BUY 10 button calling handlePharmacyTrade(item,'buy',10))")
    else:
        print("VERDICT: (b) backend lacks qty -> BACKEND patch needed too")
        print("  (buy endpoint must take qty, charge qty x unit price, add qty oz)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
