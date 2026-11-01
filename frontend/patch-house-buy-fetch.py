"""Street Legends frontend: house items via fetch, no api import at all.
Run from repo root: python3 frontend/patch-house-buy-fetch.py
Idempotent - safe to re-run.

WHY (user 2026-10-30, new error after the direct patch):
"undefined is not a function" on BUY. The direct patch made the
screen call api.post, but services/api.ts evidently does NOT export
its axios client as the default — so `api` is not a callable client
and api.post doesn't exist. (Named functions like buyHouse work
fine from that file; only the default import is broken/missing.)
So this patch drops the api import for house items entirely and
uses fetch() straight to the live backend URL. No import, no
client object, nothing to be undefined.

CHANGES (app/(tabs)/index.tsx only):
- postItem() becomes a fetch POST to
  https://gta-quest-map.emergent.host/api/houses/{id}/items/{action}
  with player_id + item_id. It checks r.ok and throws the server's
  detail message (e.g. "Not enough cash"), so a failed buy still
  shows the real reason instead of silently looking placed.
- The drag-release save becomes a fetch POST to items/move with
  player_id + item_id + x + y, with the same ok check.
- The default `api` import added by the direct patch is reverted
  to a plain named import, but ONLY if no api.post use remains
  after the two replacements (so nothing is left referencing it).

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this. The backend
endpoints are already live (verified 2026-10-29).
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")

POSTITEM_OLD = "    const postItem = async (action: string) => (await api.post(`/houses/${interiorHouse.id}/items/${action}`, { player_id: playerId, item_id: item.id })).data;"
POSTITEM_NEW = """    const postItem = async (action: string) => {
      const r = await fetch(`https://gta-quest-map.emergent.host/api/houses/${interiorHouse.id}/items/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ player_id: playerId, item_id: item.id }),
      });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data?.detail || 'Request failed');
      return data;
    };"""

DRAG_OLD = "api.post(`/houses/${house.id}/items/move`, { player_id: playerId, item_id: itemId, x: fx, y: fy }).then((r: any) => r.data)"
DRAG_NEW = "fetch(`https://gta-quest-map.emergent.host/api/houses/${house.id}/items/move`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId, item_id: itemId, x: fx, y: fy }) }).then((r: any) => { if (!r.ok) throw new Error('move failed'); return r.json(); })"


def main():
    if not INDEX.exists():
        print(f"ERROR: {INDEX} not found. Run from repo root.")
        sys.exit(1)
    src = INDEX.read_text()

    if POSTITEM_NEW in src:
        print("SKIP: postItem already uses fetch")
    elif src.count(POSTITEM_OLD) == 1:
        src = src.replace(POSTITEM_OLD, POSTITEM_NEW, 1)
        print("OK: postItem now uses fetch")
    else:
        print(f"WARNING: postItem anchor matched {src.count(POSTITEM_OLD)}x")

    if DRAG_NEW in src:
        print("SKIP: drag save already uses fetch")
    elif src.count(DRAG_OLD) == 1:
        src = src.replace(DRAG_OLD, DRAG_NEW, 1)
        print("OK: drag save now uses fetch")
    else:
        print(f"WARNING: drag anchor matched {src.count(DRAG_OLD)}x")

    # Revert the default api import only if nothing uses api.post now.
    if "api.post" not in src:
        if src.count("import api, {") == 1:
            src = src.replace("import api, {", "import {", 1)
            print("OK: default api import reverted (nothing uses it now)")
        else:
            print("SKIP: default api import not found or ambiguous, left as-is")
    else:
        print("WARNING: api.post still present - default import kept")

    INDEX.write_text(src)
    print("HOUSE_BUY_FETCH_OK")


if __name__ == "__main__":
    main()
