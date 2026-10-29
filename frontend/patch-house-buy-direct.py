"""Street Legends frontend: buy/remove/drag items WITHOUT api.ts exports.
Run from repo root: python3 frontend/patch-house-buy-direct.py
Idempotent - safe to re-run.

WHY (user 2026-10-29, still failing after the diagnose patch):
Tapping BUY still pops "Property 'addHouseItem' doesn't exist".
Patching api.ts has not gotten through, for reasons not visible from
the outside. So this patch stops depending on api.ts for house
items entirely: the map screen calls the server directly through
the api client it already imports, at the same three endpoints
(items/add, items/remove, items/move, plus items/place-from-
inventory). Whatever is wrong with the named exports in api.ts can
no longer block buying, removing, or dragging an item.

CHANGES (app/(tabs)/index.tsx only):
- The services/api import gains the default `api` client
  (import api, { ... }) if it doesn't already have it.
- handleHouseItemToggle gains a local postItem() helper and its
  three calls (remove / place-from-inventory / add) become
  postItem('remove' | 'place-from-inventory' | 'add').
- The drag-release save (moveHouseItem) becomes a direct api.post
  to items/move with the same x/y.
- GUARD: if the api import can't be found/added, nothing else
  changes, so the build is never left referencing an undefined
  `api`.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this. The backend
endpoints are already live (verified 2026-10-29).
"""
import re
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")

HANDLER_ANCHOR = """  const handleHouseItemToggle = async (item: any) => {
    if (!interiorHouse || !playerId) return;"""
POSTITEM_DEF = HANDLER_ANCHOR + """
    const postItem = async (action: string) => (await api.post(`/houses/${interiorHouse.id}/items/${action}`, { player_id: playerId, item_id: item.id })).data;"""

CALLS = [
    ("await removeHouseItem(interiorHouse.id, playerId, item.id)", "await postItem('remove')"),
    ("await placeItemFromInventory(interiorHouse.id, playerId, item.id)", "await postItem('place-from-inventory')"),
    ("await addHouseItem(interiorHouse.id, playerId, item.id)", "await postItem('add')"),
]

DRAG_OLD = "moveHouseItem(house.id, playerId, itemId, fx, fy)"
DRAG_NEW = "api.post(`/houses/${house.id}/items/move`, { player_id: playerId, item_id: itemId, x: fx, y: fy }).then((r: any) => r.data)"

API_PATH = "'../../services/api'"


def main():
    if not INDEX.exists():
        print(f"ERROR: {INDEX} not found. Run from repo root.")
        sys.exit(1)
    src = INDEX.read_text()

    # 1. Default api import (skip if already present).
    has_default = re.search(r"import\s+api\s*(,|from)\s*" + API_PATH, src) is not None
    if has_default:
        print("SKIP: default api import already present")
    else:
        pat = re.compile(r"import\s*\{([\s\S]*?)\}\s*from\s*" + API_PATH)
        m = pat.search(src)
        if not m:
            print("WARNING: services/api import block not found - no changes made, build left as-is")
            print("HOUSE_BUY_DIRECT_OK")
            return
        src = src[:m.start()] + "import api, {" + m.group(1) + "} from '../../services/api'" + src[m.end():]
        print("OK: default api import added")

    # 2. postItem helper in the toggle handler.
    if "const postItem = async (action: string)" in src:
        print("SKIP: postItem helper already present")
    elif src.count(HANDLER_ANCHOR) == 1:
        src = src.replace(HANDLER_ANCHOR, POSTITEM_DEF, 1)
        print("OK: postItem helper added to toggle handler")
    else:
        print(f"WARNING: handler anchor matched {src.count(HANDLER_ANCHOR)}x - call replacements still attempted")

    # 3. The three toggle calls.
    for old, new in CALLS:
        n = src.count(old)
        if n == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {old.split('(')[0]} -> direct call")
        elif n == 0:
            print(f"SKIP: {old.split('(')[0]} not found (already direct or absent)")
        else:
            print(f"WARNING: {old.split('(')[0]} matched {n}x - skipped")

    # 4. Drag-release save.
    n = src.count(DRAG_OLD)
    if n == 1:
        src = src.replace(DRAG_OLD, DRAG_NEW, 1)
        print("OK: drag save -> direct call")
    elif n == 0:
        print("SKIP: drag move call not found (already direct or absent)")
    else:
        print(f"WARNING: drag move call matched {n}x - skipped")

    INDEX.write_text(src)
    print("HOUSE_BUY_DIRECT_OK")


if __name__ == "__main__":
    main()
