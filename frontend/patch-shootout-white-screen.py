#!/usr/bin/env python3
"""Fix Shootout white 'Street Legends' page after collecting the payout.

User (2026-11-11): "shoot out goes to the white page with the name after
you try to collect the payout." After finishing a shootout and tapping DONE
on the results modal, the app lands on a blank white page that just says
"Street Legends" instead of going back to the map.

Root cause: the results modal's DONE button calls handleClose(), which does
router.back(). When the shootout is opened from the settings menu, the
navigation stack does not always have a screen to go back to (the settings
modal that launched it can be dismissed first), so router.back() exits to
the app's blank root instead of the map.

Fix (frontend, shootout-simulator.tsx):
  Change handleClose() to navigate explicitly to the map tab with
  router.replace('/(tabs)') instead of router.back(). This always lands on
  the map, whether or not there is a screen behind the shootout. The X
  button in the header uses the same handleClose, so it is fixed too.

This is a FRONTEND patch: run in /app, then check in Expo Go first.
Marker: SHOOTOUT_WHITE_SCREEN_OK
"""
import sys
from pathlib import Path

FILE = Path("frontend/app/shootout-simulator.tsx")

OLD = """  // Close handler
  const handleClose = () => {
    router.back();
  };"""

NEW = """  // Close handler — navigate explicitly to the map tab. router.back()
  // can land on the blank white "Street Legends" root when the shootout
  // was opened from the settings menu and there is no screen behind it.
  const handleClose = () => {
    router.replace('/(tabs)');
  };"""


def main():
    if not FILE.exists():
        print("SHOOTOUT_WHITE_SCREEN_FAIL frontend/app/shootout-simulator.tsx not found")
        return 1
    src = FILE.read_text(encoding="utf-8")

    if "router.replace('/(tabs)')" in src:
        print("SHOOTOUT_WHITE_SCREEN_ALREADY_APPLIED")
        return 0

    if OLD not in src:
        print("SHOOTOUT_WHITE_SCREEN_FAIL handleClose block not found (file may have changed)")
        return 1

    src = src.replace(OLD, NEW, 1)

    checks = [
        "router.replace('/(tabs)')",
        "const handleClose = () => {",
        "onPress={handleClose}",
    ]
    for needle in checks:
        if needle not in src:
            print("SHOOTOUT_WHITE_SCREEN_FAIL missing after edit: %s" % needle)
            return 1

    FILE.write_text(src, encoding="utf-8")
    print("SHOOTOUT_WHITE_SCREEN_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
