"""Street Legends frontend: keep the shop filter menu visible on long lists.
Run from repo root: python3 frontend/patch-shop-sticky-filters.py
Idempotent - safe to re-run.

BUG: the items ScrollView has no bounded height (no flex:1), so when
the shop list is long the list frame grows past the screen and the
filter tab menu (All / HP / EN / Combo / Stims) gets pushed out of
view / covered — the user loses the menu exactly when they need it
most. The inactive tab labels (#666 on near-black) also read as blank.

FIX (both shop screens, whichever is present):
1. Give the items ScrollView flex:1 so it scrolls INTERNALLY inside the
   space below the filter bar — the bar can never be pushed away.
2. Give the filter bar an opaque background so list content can never
   show through it.
3. Brighten inactive tab labels/icons (#666 -> #999) so tabs never look
   blank/hidden.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

CANDIDATES = [
    Path("frontend/app/(tabs)/shop.tsx"),
    Path("frontend/app/shop.tsx"),
]

# (old, new, description) — applied only when old is found exactly once
# or more; skipped (not an error) when absent.
REPLACEMENTS = [
    (
        "      <ScrollView\n        contentContainerStyle={styles.scrollContent}",
        "      <ScrollView\n        style={styles.itemsScroll}\n        contentContainerStyle={styles.scrollContent}",
        "items list gets flex:1 (scrolls inside remaining space)",
    ),
    (
        "  scrollContent: { padding: 12, paddingBottom: 40 },",
        "  scrollContent: { padding: 12, paddingBottom: 40 },\n  itemsScroll: { flex: 1 },",
        "itemsScroll style added",
    ),
    (
        "filterScroll: { maxHeight: 46, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },",
        "filterScroll: { maxHeight: 46, borderBottomWidth: 1, borderBottomColor: '#1a1a1a', backgroundColor: '#0a0a0a' },",
        "filter bar gets opaque background",
    ),
    (
        "  filterBar: {\n    flexDirection: 'row',\n    paddingHorizontal: 12,\n    paddingVertical: 8,\n    gap: 6,\n    borderBottomWidth: 1,\n    borderBottomColor: '#1a1a1a',",
        "  filterBar: {\n    flexDirection: 'row',\n    paddingHorizontal: 12,\n    paddingVertical: 8,\n    gap: 6,\n    borderBottomWidth: 1,\n    borderBottomColor: '#1a1a1a',\n    backgroundColor: '#0a0a0a',",
        "filter bar (black market) gets opaque background",
    ),
    (
        "filterLabel: { color: '#666', fontSize: 11, fontWeight: '600' },",
        "filterLabel: { color: '#999', fontSize: 11, fontWeight: '600' },",
        "inactive tab labels brightened",
    ),
    (
        "filter === f.key ? '#f39c12' : '#666'",
        "filter === f.key ? '#f39c12' : '#999'",
        "inactive tab icons brightened",
    ),
]


def main():
    patched_any = False
    for path in CANDIDATES:
        if not path.exists():
            print(f"SKIP: {path} not found")
            continue
        src = path.read_text()
        changed = False
        for old, new, desc in REPLACEMENTS:
            n = src.count(old)
            if n > 0 and new not in src:
                src = src.replace(old, new)
                print(f"OK ({path}): {desc} ({n}x)")
                changed = True
            elif new in src:
                pass  # already applied
            else:
                print(f"SKIP ({path}): anchor not found — {desc}")
        if changed:
            path.write_text(src)
            patched_any = True
    if not patched_any:
        print("NOTE: nothing changed — patch may already be applied.")
    print("SHOP_FILTERS_OK")


if __name__ == "__main__":
    main()
