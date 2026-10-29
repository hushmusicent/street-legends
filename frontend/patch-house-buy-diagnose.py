"""Street Legends frontend: diagnose + repair missing house api functions.
Run from repo root: python3 frontend/patch-house-buy-diagnose.py
Idempotent - safe to re-run.

WHY THIS EXISTS (user screenshot 2026-10-29):
The interior shows the buy-fix cash display (so that patch's
index.tsx change IS in the installed build), yet tapping BUY still
pops "Property 'addHouseItem' doesn't exist". Same patch, one half
live and one half not — so api.ts itself is in an unknown state:
either the function was never appended, or an earlier copy is
commented out / broken and blocked the append.

WHAT IT DOES:
- For each house api function, prints whether a REAL (not commented
  out) `export const <name>` exists in services/api.ts, with its
  line number and the line's text. A commented-out copy does NOT
  count as real.
- Appends a clean definition for every function that has no real
  copy (appending is safe when the only copies are comments, since
  comments declare nothing and can't collide).
- Reports whether index.tsx mentions each function (import check).
- Prints HOUSE_BUY_DIAGNOSE_OK at the end.

After running: REBUILD + install the new AAB. The phone app only
changes with a new build — running the patch alone does not update
the installed app. If the error still appears after a rebuild, send
a screenshot of this patch's output: it shows exactly what api.ts
contains, which is what is needed to fix the remaining case.
"""
import sys
from pathlib import Path

API = Path("frontend/services/api.ts")
INDEX = Path("frontend/app/(tabs)/index.tsx")

FUNCS = {
    "addHouseItem": """
export const addHouseItem = async (houseId: string, playerId: string, itemId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/add`, { player_id: playerId, item_id: itemId });
  return response.data;
};""",
    "removeHouseItem": """
export const removeHouseItem = async (houseId: string, playerId: string, itemId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/remove`, { player_id: playerId, item_id: itemId });
  return response.data;
};""",
    "moveHouseItem": """
export const moveHouseItem = async (houseId: string, playerId: string, itemId: string, x: number, y: number): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/move`, { player_id: playerId, item_id: itemId, x, y });
  return response.data;
};""",
    "moveHouseToInventory": """
export const moveHouseToInventory = async (houseId: string, playerId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/move-to-inventory`, { player_id: playerId });
  return response.data;
};""",
    "getInventoryHouses": """
export const getInventoryHouses = async (playerId: string): Promise<any> => {
  const response = await api.get(`/houses/inventory/${playerId}`);
  return response.data.houses || [];
};""",
    "placeHouse": """
export const placeHouse = async (houseId: string, playerId: string, latitude: number, longitude: number): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/place`, { player_id: playerId, latitude, longitude });
  return response.data;
};""",
    "placeItemFromInventory": """
export const placeItemFromInventory = async (houseId: string, playerId: string, itemId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/items/place-from-inventory`, { player_id: playerId, item_id: itemId });
  return response.data;
};""",
}


def real_lines(lines, name):
    """Line numbers (1-based) where `export const <name>` appears as
    real code, not inside a comment."""
    found = []
    needle = f"export const {name}"
    for i, line in enumerate(lines, 1):
        if needle in line:
            stripped = line.strip()
            if stripped.startswith("//") or stripped.startswith("/*") or stripped.startswith("*"):
                continue
            found.append((i, line.rstrip()[:80]))
    return found


def main():
    if not API.exists():
        print(f"ERROR: {API} not found. Run from repo root.")
        sys.exit(1)
    lines = API.read_text().splitlines()
    src = API.read_text()
    appended = []
    for name, fn in FUNCS.items():
        found = real_lines(lines, name)
        if found:
            for ln, text in found:
                print(f"{name}: FOUND line {ln}: {text}")
        else:
            commented = [i + 1 for i, l in enumerate(lines) if f"export const {name}" in l]
            if commented:
                print(f"{name}: only commented-out copies at lines {commented} -> appending a real one")
            else:
                print(f"{name}: MISSING -> appending")
            appended.append(fn)
    if appended:
        if not src.endswith("\n"):
            src += "\n"
        for fn in appended:
            src += fn + "\n"
        API.write_text(src)
        print(f"OK: appended {len(appended)} function(s) to api.ts")
    else:
        print("OK: all house api functions already present as real code")

    # Functions the map screen itself uses (shop-only ones excluded:
    # getInventoryHouses / placeHouse live in shop.tsx, not here).
    INDEX_FUNCS = ["addHouseItem", "removeHouseItem", "moveHouseItem",
                   "moveHouseToInventory", "placeItemFromInventory"]
    if INDEX.exists():
        index_src = INDEX.read_text()
        for name in FUNCS:
            n = index_src.count(name)
            print(f"index.tsx mentions {name}: {n}x")
        missing_imports = [nm for nm in INDEX_FUNCS if index_src.count(nm) == 0]
        if missing_imports:
            anchor = "} from '../../services/api';"
            if index_src.count(anchor) == 1:
                insert = "".join(f"  {nm},\n" for nm in missing_imports)
                index_src = index_src.replace(anchor, insert + anchor, 1)
                INDEX.write_text(index_src)
                print(f"OK: added missing imports to index.tsx: {', '.join(missing_imports)}")
            else:
                print(f"WARNING: index api import block matched {index_src.count(anchor)}x - imports not added")
        else:
            print("OK: all map-screen imports present")
    else:
        print(f"WARNING: {INDEX} not found")
    print("HOUSE_BUY_DIAGNOSE_OK")


if __name__ == "__main__":
    main()
