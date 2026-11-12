#!/usr/bin/env python3
"""Map markers payload: actually send profile_pic to the map WebView.

User (2026-11-12): "Still blue" / "in the other phone also."
The popup shows the real picture, but the map marker stays blue on
BOTH phones.

Root cause (frontend/components/GameMap.tsx, the markers useEffect):
the payload sent into the WebView via window.updateMarkers() only
includes id, lat, lng, type, level, name, cooldownSeconds — it DROPS
profile_pic. So inside the WebView, m.profile_pic is always undefined
and the player branch can never render the photo; it always falls back
to the generic blue circle. The popup works because it reads the pic
straight from React state, not from this payload.

Fix: add `profile_pic: (m as any).profile_pic || null` to the markers
payload. The WebView's createMarker player branch (from the profile-pic
patch) and the marker-pic-refresh patch then receive the picture and
render/rebuild the icon.

IMPORTANT — the map HTML is generated ONCE (useMemo with empty deps,
"never regenerate") and the WebView keeps running it. A fast refresh
does NOT pick up GameMap JS changes. After running this patch the user
must FULLY close the app and reopen it in Expo Go (kill it from the
recent-apps list, then open it again) — that remounts GameMap, the HTML
regenerates with the new JS, and the marker rebuilds with the picture.

FRONTEND-only, idempotent. Marker: MARKER_PAYLOAD_PIC_OK
"""
import sys
from pathlib import Path

GAMEMAP = Path("frontend/components/GameMap.tsx")

OLD = """        type: m.type,
        level: m.level || 0,
        name: m.name || '',
        cooldownSeconds: (m as any).cooldownSeconds || 0,"""

NEW = """        type: m.type,
        level: m.level || 0,
        name: m.name || '',
        profile_pic: (m as any).profile_pic || null,
        cooldownSeconds: (m as any).cooldownSeconds || 0,"""


def main():
    if not GAMEMAP.exists():
        print("MARKER_PAYLOAD_PIC_FAIL frontend/components/GameMap.tsx not found")
        return 1
    src = GAMEMAP.read_text(encoding="utf-8")
    if "profile_pic: (m as any).profile_pic || null" in src:
        print("MARKER_PAYLOAD_PIC_ALREADY_APPLIED")
        return 0
    if src.count(OLD) != 1:
        print("MARKER_PAYLOAD_PIC_FAIL markers payload block not found exactly once (%d)" % src.count(OLD))
        return 1
    src = src.replace(OLD, NEW, 1)
    if "profile_pic: (m as any).profile_pic || null" not in src:
        print("MARKER_PAYLOAD_PIC_FAIL missing after edit")
        return 1
    if src.count("{") != src.count("}"):
        print("MARKER_PAYLOAD_PIC_FAIL unbalanced braces after edit")
        return 1
    if src.count("(") != src.count(")"):
        print("MARKER_PAYLOAD_PIC_FAIL unbalanced parens after edit")
        return 1
    GAMEMAP.write_text(src, encoding="utf-8")
    print("MARKER_PAYLOAD_PIC_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
