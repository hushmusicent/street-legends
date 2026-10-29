"""Street Legends frontend: house map marker big and frameless.
Run from repo root: python3 frontend/patch-house-marker-big.py
Idempotent - safe to re-run.

BUG: houses fall into the generic marker branch: a small 32px orange
circle with a white border and a tiny 14px emoji. On the map it looks
like every other dot, and when you stand on your own house your player
marker covers it completely.

FIX (frontend/components/GameMap.tsx):
1. Dedicated house branch: a large frameless house emoji (64px, soft
   drop shadow for legibility, no circle, no border, no background,
   no label) — it reads as a house, not another framed dot.
2. House icon size 72x72 (bigger than any other marker) with a
   centered anchor.
3. (REMOVED per user 2026-10-29: house must NOT draw above the player
   marker — the player stays on top. No zIndex change is applied; if a
   previous run added one, this patch reverts it.)

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

PATH = Path("frontend/components/GameMap.tsx")

HOUSE_BRANCH_OLD = "            } else if (enemyImg) {"
HOUSE_BRANCH_NEW = """            } else if (m.type === 'house') {
              markerHTML = '<div style="font-size:64px;line-height:1;filter:drop-shadow(0 4px 10px rgba(0,0,0,0.6));cursor:pointer;">🏠</div>';
            } else if (enemyImg) {"""

SIZE_OLD = "            var isBossMarker = (m.type === 'monster' && m.isBoss);"
SIZE_NEW = "            var isBossMarker = (m.type === 'monster' && m.isBoss);\n            var isHouseMarker = (m.type === 'house');"

WIDTH_OLD = "            var markerWidth = (isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 56 : (isLocationMarker ? 48 : ((isBankMarker || isCasinoMarker) ? 52 : (isBossMarker ? 48 : (enemyImg ? 42 : 32))));"
WIDTH_NEW = "            var markerWidth = isHouseMarker ? 72 : ((isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 56 : (isLocationMarker ? 48 : ((isBankMarker || isCasinoMarker) ? 52 : (isBossMarker ? 48 : (enemyImg ? 42 : 32)))));"

HEIGHT_OLD = "            var markerHeight = (isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 72 : (isLocationMarker ? 62 : ((isBankMarker || isCasinoMarker) ? 68 : (isBossMarker ? 68 : (enemyImg ? 58 : 32))));"
HEIGHT_NEW = "            var markerHeight = isHouseMarker ? 72 : ((isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 72 : (isLocationMarker ? 62 : ((isBankMarker || isCasinoMarker) ? 68 : (isBossMarker ? 68 : (enemyImg ? 58 : 32)))));"

ANCHOR_OLD = "            var iconAnchorY = (isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 36 : (isLocationMarker ? 31 : ((isBankMarker || isCasinoMarker) ? 34 : (isBossMarker ? 34 : (enemyImg ? 29 : 16))));"
ANCHOR_NEW = "            var iconAnchorY = isHouseMarker ? 36 : ((isCastleMarker || isCarChaseMarker || isRunawayMarker || isPackageGrabMarker || isShootoutMarker) ? 36 : (isLocationMarker ? 31 : ((isBankMarker || isCasinoMarker) ? 34 : (isBossMarker ? 34 : (enemyImg ? 29 : 16)))));"

ZINDEX_OLD = "            var marker = L.marker([m.lat, m.lng], { icon: divIcon, zIndexOffset: isHouseMarker ? 1000 : 0 }).addTo(map);"
ZINDEX_NEW = "            var marker = L.marker([m.lat, m.lng], { icon: divIcon }).addTo(map);"

REPLACEMENTS = [
    (HOUSE_BRANCH_OLD, HOUSE_BRANCH_NEW, "house marker branch added"),
    (SIZE_OLD, SIZE_NEW, "isHouseMarker flag added"),
    (WIDTH_OLD, WIDTH_NEW, "house marker width 72"),
    (HEIGHT_OLD, HEIGHT_NEW, "house marker height 72"),
    (ANCHOR_OLD, ANCHOR_NEW, "house marker centered anchor"),
    (ZINDEX_OLD, ZINDEX_NEW, "house NOT forced above player marker (reverted if present)"),
]


def main():
    if not PATH.exists():
        print(f"ERROR: {PATH} not found. Run from repo root.")
        sys.exit(1)
    src = PATH.read_text()
    for old, new, desc in REPLACEMENTS:
        if new in src:
            print(f"SKIP: {desc} (already applied)")
        elif src.count(old) == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {desc}")
        else:
            print(f"WARNING: anchor matched {src.count(old)}x — {desc}")
    PATH.write_text(src)
    print("HOUSE_MARKER_BIG_OK")


if __name__ == "__main__":
    main()
