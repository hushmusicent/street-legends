#!/usr/bin/env python3
"""Install the new City Gotcha shootout into the app (replaces shootout-simulator.tsx).

The new shootout-simulator.tsx hosts the City Gotcha game in a WebView:
  - Settings mini-games (standalone): same game, levels, 50% payout
    (backend halves cash/XP/rep for standalone).
  - Map mini-games (shootout markers): same pop-up game, full payout
    with XP + rep.
  - $10 per hit is paid by the backend (see backend patch
    patch-shootout-10-per-hit.py). The game reports HITS to the app;
    the app completes the session through apiCompleteShootout.
  - DONE goes straight to the map tab (router.replace), never a white page.

This patch downloads the generated shootout-simulator.tsx from GitHub main
and writes it over frontend/app/shootout-simulator.tsx in /app. It keeps a
backup of the old file at frontend/app/shootout-simulator.tsx.bak.

react-native-webview is already in the app's package.json (14.0.1), so no
install step is needed.

This is a FRONTEND patch: run in /app, check in Expo Go first, then Deploy.
Marker: CITY_GOTCHA_APP_OK
"""
import sys
import urllib.request
from pathlib import Path

RAW_URL = "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/app/shootout-simulator.tsx?v=1"
TARGET = Path("frontend/app/shootout-simulator.tsx")
BACKUP = Path("frontend/app/shootout-simulator.tsx.bak")


def main():
    try:
        with urllib.request.urlopen(RAW_URL, timeout=30) as resp:
            content = resp.read().decode("utf-8")
    except Exception as e:
        print("CITY_GOTCHA_APP_FAIL download failed: %s" % e)
        return 1
    # sanity: this must be the new WebView version, not the old popup one
    for needle in (
        "from 'react-native-webview'",
        "injectedJavaScriptBeforeContentLoaded",
        "SHOOTOUT_CONFIG",
        "apiCompleteShootout",
        "router.replace('/(tabs)')",
        "CITY GOTCHA",
    ):
        if needle not in content:
            print("CITY_GOTCHA_APP_FAIL downloaded file missing: %s" % needle)
            return 1
    if "const GAME_HTML" not in content:
        print("CITY_GOTCHA_APP_FAIL downloaded file has no embedded game")
        return 1
    if TARGET.exists():
        BACKUP.write_text(TARGET.read_text(encoding="utf-8"), encoding="utf-8")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(content, encoding="utf-8")
    print("CITY_GOTCHA_APP_OK %d bytes" % len(content))
    return 0


if __name__ == "__main__":
    sys.exit(main())
