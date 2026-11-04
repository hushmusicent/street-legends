#!/usr/bin/env python3
"""Street Legends frontend: house PLACE uses fresh GPS at tap, not cached position.

BUG (user 2026-11-03): "It needs to land where ever im at when I place it."
Live shop.tsx handlePlaceHouse sent player.position (cached/saved position)
at tap time, so a house could land at the old saved spot instead of where
the player is standing when PLACE is tapped. Backend place endpoint already
uses the client-sent latitude/longitude exactly, so no backend change is
needed: this is a frontend-only fix (Expo Go reload, no Deploy).

FIX (scoped to shop.tsx handlePlaceHouse ONLY — the BUY handler is out of
scope and is never touched):
- Import expo-location in shop.tsx if not already imported (expo-location
  is already installed: index.tsx and fitness.tsx import it).
- Import updatePlayerPosition from services/api if not already imported
  (best-effort saved-position sync only; if that import anchor is missing,
  the fresh-GPS place still lands and sync is omitted, with a WARNING).
- Guard: `if (!playerId || !player?.position)` becomes `if (!playerId)`,
  so a missing saved position no longer blocks place when fresh GPS works.
  The following Alert + return lines are untouched.
- Fresh-GPS block (marked // PLACE_FRESH_GPS) replacing the single
  placeHouse call line: start from cached player.position if present,
  try Location.requestForegroundPermissionsAsync + getCurrentPositionAsync
  (Accuracy.High) to overwrite with fresh coords, fall back to cached
  coords on any GPS/permission failure, best-effort sync the resolved
  coords via updatePlayerPosition inside its own try/catch (never blocks
  place), Alert + return if coords are still null, otherwise place with
  the fresh coords. The setMyHouse / inventory-filter / placed-alert
  lines after the call are untouched, and the finally block still resets
  placingHouse (a return inside try still runs finally).

IDEMPOTENT (scoped): if // PLACE_FRESH_GPS is already present, nothing
is changed (SKIP). Imports are likewise skipped if already present.
Re-running never duplicates imports or blocks.

WARNINGS, not crashes: any missed anchor prints a WARNING naming it and
the patch continues with the other sections. End marker is always the
last line (except file-not-found, which prints an ERROR and exits 1).
Any WARNING means: send the full output before re-running.

Run from /app: python3 frontend/patch-house-place-fresh-gps-frontend.py
"""
import re
import sys
from pathlib import Path

SHOP = Path("frontend/app/(tabs)/shop.tsx")
MARKER = "HOUSE_PLACE_FRESH_GPS_FRONTEND_OK"
FRESH_MARKER = "// PLACE_FRESH_GPS"
LOCATION_IMPORT = "import * as Location from 'expo-location';"


def main():
    try:
        src = SHOP.read_text(encoding="utf-8")
    except FileNotFoundError:
        print("PLACE_FRESH_GPS_ERROR: shop.tsx not found (run from /app)")
        return 1
    orig = src

    # Idempotency: fresh block already present -> change nothing.
    if FRESH_MARKER in src:
        print("SKIP: fresh GPS place block already present")
        print(MARKER)
        return 0

    # 1. expo-location import (single-line import form; any existing
    #    expo-location import means Location is already bound, so skip
    #    to avoid a duplicate-identifier break).
    location_ok = False
    lines_all = src.split("\n")
    if any(ln.strip().startswith("import") and "expo-location" in ln for ln in lines_all):
        print("SKIP: expo-location import already present")
        location_ok = True
    else:
        last_import = -1
        for i, ln in enumerate(lines_all[:80]):
            if ln.strip().startswith("import "):
                last_import = i
        if last_import >= 0:
            lines_all.insert(last_import + 1, LOCATION_IMPORT)
            src = "\n".join(lines_all)
            print("OK: expo-location import added")
            location_ok = True
        else:
            print("WARNING: no import lines found in first 80 lines of shop.tsx - handler change SKIPPED (Location would be undefined)")

    # Without the Location import, never reference Location: skip the
    # handler change (and the sync import, which the block would need).
    sync_ok = False
    if location_ok:
        # 2. updatePlayerPosition import (best-effort sync only).
        api_import_re = re.compile(
            r"import\s*\{[^}]*updatePlayerPosition[^}]*\}\s*from\s*['\"]\.\./\.\./services/api['\"]",
            re.DOTALL,
        )
        if api_import_re.search(src):
            print("SKIP: updatePlayerPosition import already present")
            sync_ok = True
        else:
            added = False
            lines = src.split("\n")
            for idx, ln in enumerate(lines):
                if "placeHouse" in ln and "services/api" in ln:
                    new_ln = ln.replace("placeHouse", "placeHouse, updatePlayerPosition", 1)
                    if new_ln != ln:
                        lines[idx] = new_ln
                        src = "\n".join(lines)
                        added = True
                    break
            if not added:
                m = re.search(
                    r"(placeHouse)(\s*\}\s*from\s*['\"]\.\./\.\./services/api['\"])",
                    src,
                )
                if m:
                    src = src[:m.start()] + m.group(1) + ", updatePlayerPosition" + m.group(2) + src[m.end():]
                    added = True
            if added:
                print("OK: updatePlayerPosition import added")
                sync_ok = True
            else:
                print("WARNING: services/api import anchor with placeHouse not found - place will still land with fresh GPS, saved-position sync omitted")
                sync_ok = False

        # 3 + 4. Handler changes, scoped to handlePlaceHouse.
        h_start = src.find("const handlePlaceHouse")
        if h_start < 0:
            print("WARNING: handlePlaceHouse definition not found in shop.tsx - handler change SKIPPED")
        else:
            guard_pat = re.compile(r"if\s*\(\s*!playerId\s*\|\|\s*!player\?\.position\s*\)\s*\{")
            gm = guard_pat.search(src, h_start)
            if gm:
                src = src[:gm.start()] + "if (!playerId) {" + src[gm.end():]
                print("OK: place guard changed to playerId-only")
            else:
                print("WARNING: place guard anchor not found after handlePlaceHouse - guard unchanged")

            block_pat = re.compile(
                r"(?m)^([ \t]*)const\s+res\s*=\s*await\s+placeHouse\(h\.id,\s*playerId,\s*player\.position\.latitude,\s*player\.position\.longitude\);"
            )
            bm = block_pat.search(src, h_start)
            if bm:
                indent = bm.group(1)
                block_lines = []
                block_lines.append(indent + "// PLACE_FRESH_GPS")
                block_lines.append(indent + "let lat = player?.position?.latitude;")
                block_lines.append(indent + "let lng = player?.position?.longitude;")
                block_lines.append(indent + "try {")
                block_lines.append(indent + "  const { status } = await Location.requestForegroundPermissionsAsync();")
                block_lines.append(indent + "  if (status === 'granted') {")
                block_lines.append(indent + "    const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.High });")
                block_lines.append(indent + "    lat = loc.coords.latitude;")
                block_lines.append(indent + "    lng = loc.coords.longitude;")
                block_lines.append(indent + "  }")
                block_lines.append(indent + "} catch (_) {}")
                if sync_ok:
                    block_lines.append(indent + "try {")
                    block_lines.append(indent + "  if (lat != null && lng != null) {")
                    block_lines.append(indent + "    await updatePlayerPosition(playerId, { latitude: lat, longitude: lng });")
                    block_lines.append(indent + "  }")
                    block_lines.append(indent + "} catch (_) {}")
                block_lines.append(indent + "if (lat == null || lng == null) {")
                block_lines.append(indent + "  Alert.alert('Place House', 'Your location is not available yet.');")
                block_lines.append(indent + "  return;")
                block_lines.append(indent + "}")
                block_lines.append(indent + "const res = await placeHouse(h.id, playerId, lat, lng);")
                block_text = "\n".join(block_lines)
                src = src[:bm.start()] + block_text + src[bm.end():]
                print("OK: fresh-GPS place block inserted")
            else:
                print("WARNING: placeHouse call anchor not found after handlePlaceHouse - fresh block NOT inserted")

    if src != orig:
        SHOP.write_text(src, encoding="utf-8")
        print("OK: shop.tsx updated")
    else:
        print("SKIP: shop.tsx unchanged (no sections applied)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
