"""Street Legends frontend: shop filter menu visible on EVERY tab.
Run from repo root: python3 frontend/patch-shop-filters-v2.py
Idempotent - safe to re-run.

BUG: on the House tab the filter pills (All / House / ...) are cut off
to a sliver and unusable. Cause: the House tab's ScrollView never got
the flex:1 fix from patch-shop-sticky-filters.py (that patch only
touched the items list), so the House list grows unbounded and swallows
the filter bar. This patch also re-applies every v1 fix in case v1 was
never run in Emergent.

FIX (supply shop + black market, whichever is present):
1. House ScrollView gets style={styles.itemsScroll} (flex:1) so it
   scrolls INSIDE the space below the filter bar.
2. Items ScrollView gets the same if v1 never applied.
3. itemsScroll style added if missing.
4. Filter bar gets an opaque background + minHeight so it can never
   collapse to a sliver or show list content through it.
5. Inactive tab labels brightened (#666 -> #999) if v1 never applied.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

CANDIDATES = [
    Path("frontend/app/(tabs)/shop.tsx"),
    Path("frontend/app/shop.tsx"),
]

# (old, new, description)
REPLACEMENTS = [
    (
        "      {filter === 'house' ? (\n        <ScrollView contentContainerStyle={styles.scrollContent}>",
        "      {filter === 'house' ? (\n        <ScrollView style={styles.itemsScroll} contentContainerStyle={styles.scrollContent}>",
        "House list gets flex:1 (scrolls inside remaining space)",
    ),
    (
        "      <ScrollView\n        contentContainerStyle={styles.scrollContent}",
        "      <ScrollView\n        style={styles.itemsScroll}\n        contentContainerStyle={styles.scrollContent}",
        "items list gets flex:1 (if v1 never applied)",
    ),
    (
        "  scrollContent: { padding: 12, paddingBottom: 40 },",
        "  scrollContent: { padding: 12, paddingBottom: 40 },\n  itemsScroll: { flex: 1 },",
        "itemsScroll style added (if missing)",
    ),
    (
        "filterScroll: { maxHeight: 46, borderBottomWidth: 1, borderBottomColor: '#1a1a1a' },",
        "filterScroll: { maxHeight: 46, minHeight: 46, borderBottomWidth: 1, borderBottomColor: '#1a1a1a', backgroundColor: '#0a0a0a' },",
        "filter bar gets opaque background + minHeight (can't collapse)",
    ),
    (
        "filterScroll: { maxHeight: 46, borderBottomWidth: 1, borderBottomColor: '#1a1a1a', backgroundColor: '#0a0a0a' },",
        "filterScroll: { maxHeight: 46, minHeight: 46, borderBottomWidth: 1, borderBottomColor: '#1a1a1a', backgroundColor: '#0a0a0a' },",
        "filter bar gets minHeight (v1 already gave it a background)",
    ),
    (
        "  filterBar: {\n    flexDirection: 'row',\n    paddingHorizontal: 12,\n    paddingVertical: 8,\n    gap: 6,\n    borderBottomWidth: 1,\n    borderBottomColor: '#1a1a1a',",
        "  filterBar: {\n    flexDirection: 'row',\n    paddingHorizontal: 12,\n    paddingVertical: 8,\n    gap: 6,\n    borderBottomWidth: 1,\n    borderBottomColor: '#1a1a1a',\n    backgroundColor: '#0a0a0a',",
        "filter bar (black market) gets opaque background",
    ),
    (
        "filterLabel: { color: '#666', fontSize: 11, fontWeight: '600' },",
        "filterLabel: { color: '#999', fontSize: 11, fontWeight: '600' },",
        "inactive tab labels brightened (if v1 never applied)",
    ),
    (
        "filter === f.key ? '#f39c12' : '#666'",
        "filter === f.key ? '#f39c12' : '#999'",
        "inactive tab icon color brightened (if v1 never applied)",
    ),
]


def main():
    for path in CANDIDATES:
        if not path.exists():
            continue
        src = path.read_text()
        changed = False
        for old, new, desc in REPLACEMENTS:
            if new in src:
                continue
            if src.count(old) >= 1:
                src = src.replace(old, new)
                print(f"OK ({path.name}): {desc}")
                changed = True
        if changed:
            path.write_text(src)
    print("SHOP_FILTERS_V2_OK")


if __name__ == "__main__":
    main()
