#!/usr/bin/env python3
"""Street Legends frontend: upgrade the Expo project from SDK 57 to SDK 58.

Why: the installed Expo Go app is now SDK 58, and Expo Go refuses to open
a project on a different SDK. This is the official Expo upgrade path:
  npx expo install expo@^58.0.0 --fix
  npx expo-doctor@latest
The first command bumps expo to 58 and aligns every other expo package
(and react / react-native) with SDK 58. The second checks for common
project problems. Most apps upgrade without code changes; if this app
uses a removed API (InteractionManager, Modal `animated` prop) or custom
router state, it will show up when the app reloads and gets fixed then.

Run from repo root: python3 frontend/patch-sdk58-upgrade.py
Idempotent: re-running after a successful upgrade prints SKIP, it does
not reinstall. A backup of package.json is saved first, so the upgrade
can be undone (see the revert command printed at the end).
FRONTEND ONLY - after this prints SDK58_UPGRADE_OK, reload Expo Go.
If Expo Go still says SDK 57, restart the dev server in Emergent first.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

FRONTEND = Path("frontend")
PKG = FRONTEND / "package.json"
BAK = FRONTEND / "package.json.sdk57.bak"


def expo_version():
    try:
        data = json.loads(PKG.read_text())
        return data.get("dependencies", {}).get("expo", "")
    except Exception:
        return ""


def run(cmd, timeout):
    print("RUN: " + " ".join(cmd) + "  (this can take a few minutes, don't close the terminal)")
    try:
        r = subprocess.run(cmd, cwd=str(FRONTEND), capture_output=True, text=True, timeout=timeout)
        out = (r.stdout or "") + (r.stderr or "")
        tail = "\n".join(out.strip().split("\n")[-30:])
        print(tail)
        return r.returncode
    except FileNotFoundError as e:
        print("ERROR: command not found: %s" % e)
        return 127
    except subprocess.TimeoutExpired:
        print("ERROR: command timed out after %ss" % timeout)
        return 124


def main():
    if not PKG.exists():
        print("SDK58_ERROR: frontend/package.json not found (run from /app)")
        return 1
    cur = expo_version()
    print("Current expo version: %s" % (cur or "(unknown)"))
    if cur.startswith("58") or cur.startswith("~58") or cur.startswith("^58"):
        print("SKIP: expo is already SDK 58 (%s)" % cur)
        print("SDK58_UPGRADE_OK")
        return 0
    if not BAK.exists():
        shutil.copy2(PKG, BAK)
        print("OK: backup saved to frontend/package.json.sdk57.bak")
    else:
        print("SKIP: backup already exists (frontend/package.json.sdk57.bak)")
    for lock in ("yarn.lock", "package-lock.json"):
        src = FRONTEND / lock
        dst = FRONTEND / (lock + ".sdk57.bak")
        if src.exists() and not dst.exists():
            shutil.copy2(src, dst)
            print("OK: backup saved to frontend/%s.sdk57.bak" % lock)
    rc = run(["npx", "expo", "install", "expo@^58.0.0", "--fix"], timeout=900)
    if rc != 0:
        print("WARNING: expo install exited with code %s (continuing to the doctor check)" % rc)
    rc2 = run(["npx", "expo-doctor@latest"], timeout=300)
    if rc2 != 0:
        print("WARNING: expo-doctor exited with code %s (read its output above)" % rc2)
    new = expo_version()
    print("Expo version after upgrade: %s" % (new or "(unknown)"))
    print("REVERT (only if you need to undo the upgrade): cp frontend/package.json.sdk57.bak frontend/package.json")
    if new.startswith("58") or new.startswith("~58") or new.startswith("^58"):
        print("SDK58_UPGRADE_OK (reload Expo Go; if it still says SDK 57, restart the dev server first)")
        return 0
    print("SDK58_UPGRADE_FAIL: expo is still %s, not 58. Read the install output above." % (new or "(unknown)"))
    return 1


if __name__ == "__main__":
    sys.exit(main())
