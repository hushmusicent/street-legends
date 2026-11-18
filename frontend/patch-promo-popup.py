#!/usr/bin/env python3
"""Swipeable promo popup at game start, over the map (frontend).

What it adds:
  - frontend/components/PromoPopup.tsx (downloaded from GitHub):
    a Modal with a horizontal paging ScrollView, 2 pages.
    Page 1: promo-mk.jpg (Recovery Ward) - Health MK + Energy MK, $1 EACH.
    Page 2: promo-bundles.jpg (Bonus art) - the 4 Bonus Bundles + prices.
    X button (top right) closes it. Dots + "Swipe for more" hint.
    Shows once per app launch (visible state resets on restart).
  - frontend/assets/promo-mk.jpg + promo-bundles.jpg: decoded from the
    .b64.txt files on GitHub (push tool cannot carry binary files).
  - frontend/app/(tabs)/index.tsx: imports PromoPopup and renders
    <PromoPopup /> at the top of the map container.

Run from /app: python3 frontend/patch-promo-popup.py
Idempotent: a full re-run prints PROMO_POPUP_ALREADY_APPLIED.
"""
import base64
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
COMP = Path("frontend/components/PromoPopup.tsx")
INDEX = Path("frontend/app/(tabs)/index.tsx")
MARKER = "PROMO_POPUP_OK"

IMAGES = [
    ("frontend/assets/promo-mk.jpg.b64.txt", Path("frontend/assets/promo-mk.jpg")),
    ("frontend/assets/promo-bundles.jpg.b64.txt", Path("frontend/assets/promo-bundles.jpg")),
]


def fetch(url, dest_desc):
    r = subprocess.run(
        ["curl", "-sL", url], capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0 or not r.stdout.strip():
        print(f"ERROR: failed to download {dest_desc} from {url}")
        sys.exit(1)
    return r.stdout


def main():
    if COMP.exists() and "PROMO_POPUP_V6" in COMP.read_text() and INDEX.exists():
        src = INDEX.read_text()
        if "PromoPopup" in src and "<PromoPopup />" in src:
            print("PROMO_POPUP_ALREADY_APPLIED")
            return

    # 1. Component (download from GitHub).
    comp_text = fetch(f"{RAW}/frontend/components/PromoPopup.tsx?v=6", "PromoPopup.tsx")
    if "PROMO_POPUP_V6" not in comp_text or "promo-mk.jpg" not in comp_text:
        print("ERROR: downloaded PromoPopup.tsx looks wrong (stale V5 or empty)")
        sys.exit(1)
    COMP.parent.mkdir(parents=True, exist_ok=True)
    COMP.write_text(comp_text)
    print("OK: PromoPopup.tsx")

    # 2. Images (download b64, decode to jpg).
    for b64_path, jpg_path in IMAGES:
        b64_text = fetch(f"{RAW}/{b64_path}?v=5", b64_path)
        try:
            data = base64.b64decode(b64_text.strip())
        except Exception as e:
            print(f"ERROR: bad base64 for {b64_path}: {e}")
            sys.exit(1)
        if not data.startswith(b"\xff\xd8\xff"):
            print(f"ERROR: decoded {b64_path} is not a JPEG (stale download?)")
            sys.exit(1)
        jpg_path.parent.mkdir(parents=True, exist_ok=True)
        jpg_path.write_bytes(data)
        print(f"OK: {jpg_path} ({len(data)} bytes)")

    # 3. index.tsx: import + render.
    if not INDEX.exists():
        print("ERROR: frontend/app/(tabs)/index.tsx not found (run from /app)")
        sys.exit(1)
    src = INDEX.read_text()
    if "PROMO_POPUP_V6" in COMP.read_text() and "PromoPopup" in src and "<PromoPopup />" in src:
        # Component was just replaced with V6 above and index was already
        # wired by the V5 run, so this run DID change the popup: report OK,
        # not ALREADY_APPLIED (that line is only for a true no-op re-run).
        print(MARKER)
        return
    imp_old = "import { GameMap } from '../../components/GameMap';"
    imp_new = imp_old + "\nimport PromoPopup from '../../components/PromoPopup';"
    if imp_old not in src:
        print("ERROR: GameMap import anchor not found in index.tsx (file changed unexpectedly)")
        sys.exit(1)
    src = src.replace(imp_old, imp_new, 1)
    print("OK: import")
    render_old = "    <View style={styles.container}>\n      {currentPosition && ("
    render_new = "    <View style={styles.container}>\n      <PromoPopup />\n      {currentPosition && ("
    if render_old not in src:
        print("ERROR: map container anchor not found in index.tsx (file changed unexpectedly)")
        sys.exit(1)
    src = src.replace(render_old, render_new, 1)
    print("OK: render")
    INDEX.write_text(src)
    cur = INDEX.read_text()
    if "PromoPopup" not in cur or "<PromoPopup />" not in cur:
        print("ERROR: promo popup patch did not land in index.tsx")
        sys.exit(1)
    print(MARKER)


if __name__ == "__main__":
    main()
