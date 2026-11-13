#!/usr/bin/env python3
"""Map marker: rebuild a player marker's icon when their picture changes.

User (2026-11-12): "The map icon is still blue. It needs they picture."
The popup now shows the real picture, but the map marker stays the
generic blue person.

Root cause (GameMap.tsx, inside window.updateMarkers -> createMarker):
once a marker exists, createMarker ONLY moves it and returns —
  if (entityMarkers[m.id]) {
    entityMarkers[m.id].setLatLng([m.lat, m.lng]);
    return;
  }
The icon HTML (with the profile picture) is built only the FIRST time
the marker is created. So a player whose marker was created while the
picture was missing (or before the pic patches) keeps the blue icon
forever, even after the backend starts sending profile_pic and the
frontend can render it. Moving just repositions the same blue dot.

Fix (frontend/components/GameMap.tsx only):
  1. When a marker already exists AND it is a player whose profile_pic
     differs from the one the marker was built with, remove the old
     marker and fall through to create a fresh one with the new icon.
     Any other existing marker still just moves (no behavior change).
  2. Stamp the pic used onto each created marker
     (marker._profilePic) so the comparison has something to check.

This is FRONTEND-only and idempotent. The backend nearby-pic patch
and the frontend profile-pic patch must already be in for the picture
to reach the marker at all. After running, reload Expo Go so the
WebView picks up the new GameMap code; the marker rebuilds itself on
the next map update.

Marker: PLAYER_MARKER_PIC_REFRESH_OK
"""
import sys
from pathlib import Path

GAMEMAP = Path("frontend/components/GameMap.tsx")

OLD_CREATE = '''        // Helper function to create and add a marker
        function createMarker(m) {
          newIds[m.id] = true;
          if (entityMarkers[m.id]) {
            // Update existing marker position
            entityMarkers[m.id].setLatLng([m.lat, m.lng]);
            return;
          }'''

NEW_CREATE = '''        // Helper function to create and add a marker
        function createMarker(m) {
          newIds[m.id] = true;
          if (entityMarkers[m.id]) {
            // Player picture changed (or newly available)? Rebuild the
            // marker so the new icon shows. Otherwise just move it.
            var oldPic = entityMarkers[m.id]._profilePic || null;
            var newPic = m.profile_pic || null;
            if (m.type === 'player' && oldPic !== newPic) {
              map.removeLayer(entityMarkers[m.id]);
              delete entityMarkers[m.id];
            } else {
              entityMarkers[m.id].setLatLng([m.lat, m.lng]);
              return;
            }
          }'''

OLD_STAMP = '''            entityMarkers[m.id] = marker;
        }'''

NEW_STAMP = '''            marker._profilePic = m.profile_pic || null;
            entityMarkers[m.id] = marker;
        }'''


def main():
    if not GAMEMAP.exists():
        print("PLAYER_MARKER_PIC_REFRESH_FAIL frontend/components/GameMap.tsx not found")
        return 1
    src = GAMEMAP.read_text(encoding="utf-8")
    if "_profilePic" in src:
        print("PLAYER_MARKER_PIC_REFRESH_ALREADY_APPLIED")
        return 0
    if OLD_CREATE not in src:
        print("PLAYER_MARKER_PIC_REFRESH_FAIL createMarker early-return block not found (file may have changed)")
        return 1
    if src.count(OLD_STAMP) != 1:
        print("PLAYER_MARKER_PIC_REFRESH_FAIL marker store line not found exactly once (%d)" % src.count(OLD_STAMP))
        return 1
    src = src.replace(OLD_CREATE, NEW_CREATE, 1)
    src = src.replace(OLD_STAMP, NEW_STAMP, 1)
    for needle in (
        "_profilePic",
        "oldPic !== newPic",
        "map.removeLayer(entityMarkers[m.id]);",
        "marker._profilePic = m.profile_pic || null;",
    ):
        if needle not in src:
            print("PLAYER_MARKER_PIC_REFRESH_FAIL missing after edit: %s" % needle)
            return 1
    if src.count("{") != src.count("}"):
        print("PLAYER_MARKER_PIC_REFRESH_FAIL unbalanced braces after edit")
        return 1
    if src.count("(") != src.count(")"):
        print("PLAYER_MARKER_PIC_REFRESH_FAIL unbalanced parens after edit")
        return 1
    GAMEMAP.write_text(src, encoding="utf-8")
    print("PLAYER_MARKER_PIC_REFRESH_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
