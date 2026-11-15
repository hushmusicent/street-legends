#!/usr/bin/env python3
"""Revert the IAP components in /app to the versions that worked.

The IAP refresh (listener guards + buy timeout) white-screened the Shop:
pressing Shop kicked straight to the 'Street Legends' title screen, and
re-downloading + a full Expo Go restart did not fix it.

This patch puts back the exact versions from when the Shop was opening
fine (2026-11-13 20:34):
- GodPotions.tsx: original (10,063 bytes), endConnection() in cleanup.
- BonusBundles.tsx: 41d7f947 version (12,674 bytes), no endConnection()
  on unmount (the 20:07 fix), no listener guard, no buy timeout.

The stuck-spinner bug returns with these versions, but the Shop opens
again. That is the trade-off until the white screen cause is found.

Run from /app: python3 frontend/patch-iap-revert.py
Idempotent: a full re-run prints IAP_REVERT_ALREADY_APPLIED.
"""
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
# (path, size, must-contain, must-NOT-contain)
FILES = [
    ("frontend/components/GodPotions.tsx", 10063, "endConnection().catch", "SKUS.includes"),
    ("frontend/components/BonusBundles.tsx", 12674, "Do NOT call endConnection", "SKUS.includes"),
]
MARKER = "IAP_REVERT_OK"

def main():
    need = []
    for rel, size, sig, nosig in FILES:
        p = Path(rel)
        if not p.exists():
            print(f"ERROR: {rel} not found (run from /app)")
            sys.exit(1)
        cur = p.read_text()
        if not (len(cur.encode()) == size and sig in cur and nosig not in cur):
            need.append((rel, size, sig, nosig))
    if not need:
        print("IAP_REVERT_ALREADY_APPLIED")
        return
    for rel, size, sig, nosig in need:
        r = subprocess.run(
            ["curl", "-sL", f"{RAW}/{rel}?v=6", "-o", rel],
            capture_output=True, text=True, timeout=120,
        )
        if r.returncode != 0:
            print(f"ERROR: download failed for {rel}")
            sys.exit(1)
        cur = Path(rel).read_text()
        if not (len(cur.encode()) == size and sig in cur and nosig not in cur):
            print(f"ERROR: refreshed {rel} is not the reverted version")
            sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
