#!/usr/bin/env python3
"""Refresh BonusBundles.tsx in /app (fixes the shop freeze).

The Bonus tab and God Potions share one Play Billing connection.
BonusBundles used to call endConnection() when the Bonus tab closed,
which disconnected billing while GodPotions was still using it -- so a
God Potion purchase hung on the spinner and the shop felt frozen.

The fixed BonusBundles.tsx only removes its own listeners on unmount
and never disconnects. This patch re-downloads it from GitHub.

Run from /app: python3 frontend/patch-bonus-bundles-refresh.py
Idempotent: a full re-run prints BONUS_REFRESH_ALREADY_APPLIED.
"""
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
COMP = Path("frontend/components/BonusBundles.tsx")
MARKER = "BONUS_REFRESH_OK"

def main():
    if not COMP.exists():
        print("ERROR: BonusBundles.tsx not found (run from /app)")
        sys.exit(1)
    cur = COMP.read_text()
    if "Do NOT call endConnection() here" in cur:
        print("BONUS_REFRESH_ALREADY_APPLIED")
        return
    r = subprocess.run(
        ["curl", "-sL", f"{RAW}/frontend/components/BonusBundles.tsx?v=2", "-o", str(COMP)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0 or not COMP.exists() or COMP.stat().st_size == 0:
        print("ERROR: download failed")
        sys.exit(1)
    cur = COMP.read_text()
    if "Do NOT call endConnection() here" not in cur:
        print("ERROR: refreshed file is not the fixed version")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
