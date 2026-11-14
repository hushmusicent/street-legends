#!/usr/bin/env python3
"""Refresh the IAP components in /app (fixes the stuck God Potion spinner).

Root cause found in the code: GodPotions and BonusBundles share one Play
Billing connection, and BOTH registered a purchase listener. A Bonus buy
would fire GodPotions' listener (spurious 'Activation Failed'), and a God
Potion buy would fire BonusBundles' listener (spurious 'Grant Failed').
Worse, GodPotions called endConnection() when the Shop closed, which could
kill billing mid-purchase, and neither buy() had a timeout -- so if Play
Billing never answered, the BUY button spun forever.

Fix (both files):
- Each listener ignores purchases for the OTHER component's products.
- Neither component calls endConnection() on unmount.
- buy() has a 30s safety timeout that unsticks the button.

This patch re-downloads both fixed components from GitHub.
Run from /app: python3 frontend/patch-iap-refresh.py
Idempotent: a full re-run prints IAP_REFRESH_ALREADY_APPLIED.
"""
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
FILES = [
    ("frontend/components/GodPotions.tsx", "Do NOT call endConnection() here: the Bonus tab shares this"),
    ("frontend/components/BonusBundles.tsx", "Do NOT call endConnection() here: GodPotions is also mounted in"),
]
MARKER = "IAP_REFRESH_OK"

def main():
    need = []
    for rel, sig in FILES:
        p = Path(rel)
        if not p.exists():
            print(f"ERROR: {rel} not found (run from /app)")
            sys.exit(1)
        if sig not in p.read_text():
            need.append((rel, sig))
    if not need:
        print("IAP_REFRESH_ALREADY_APPLIED")
        return
    for rel, sig in need:
        r = subprocess.run(
            ["curl", "-sL", f"{RAW}/{rel}?v=4", "-o", rel],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            print(f"ERROR: download failed for {rel}")
            sys.exit(1)
        if sig not in Path(rel).read_text():
            print(f"ERROR: refreshed {rel} is not the fixed version")
            sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
