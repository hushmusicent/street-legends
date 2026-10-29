"""Street Legends frontend: show house item limits on the shop cards.
Run from repo root: python3 frontend/patch-house-item-limits-frontend.py
Idempotent - safe to re-run.

CHANGES (supply shop House tab):
1. HOUSES const gains items per tier: apartment 2, cabin 3, mansion 6.
2. Each house card shows "Holds N items" under its blurb, so the tier
   difference is visible before buying.

FRONTEND change: needs a rebuild + new AAB upload to Play internal
testing. A backend Deploy alone does NOT ship this.
"""
import sys
from pathlib import Path

PATH = Path("frontend/app/(tabs)/shop.tsx")

REPLACEMENTS = [
    (
        "  { tier: 'apartment', name: 'Street Apartment', price: 100000, image: require('../../assets/houses/house-apartment.jpg'), blurb: 'A rough city pad. Four walls, a barred window, and a door that locks.' },",
        "  { tier: 'apartment', name: 'Street Apartment', price: 100000, image: require('../../assets/houses/house-apartment.jpg'), blurb: 'A rough city pad. Four walls, a barred window, and a door that locks.', items: 2 },",
        "apartment holds 2 items",
    ),
    (
        "  { tier: 'cabin', name: 'Country Cabin', price: 500000, image: require('../../assets/houses/house-cabin.jpg'), blurb: 'Wood walls, open fields, and quiet. Room to breathe.' },",
        "  { tier: 'cabin', name: 'Country Cabin', price: 500000, image: require('../../assets/houses/house-cabin.jpg'), blurb: 'Wood walls, open fields, and quiet. Room to breathe.', items: 3 },",
        "cabin holds 3 items",
    ),
    (
        "  { tier: 'mansion', name: 'Luxury Mansion', price: 1000000, image: require('../../assets/houses/house-mansion.jpg'), blurb: 'Marble floors, a chandelier, and gardens. You made it.' },",
        "  { tier: 'mansion', name: 'Luxury Mansion', price: 1000000, image: require('../../assets/houses/house-mansion.jpg'), blurb: 'Marble floors, a chandelier, and gardens. You made it.', items: 6 },",
        "mansion holds 6 items",
    ),
    (
        "                  <Text style={HOUSE_STYLES.houseBlurb}>{h.blurb}</Text>",
        "                  <Text style={HOUSE_STYLES.houseBlurb}>{h.blurb}</Text>\n                  <Text style={HOUSE_STYLES.houseCapacity}>Holds {h.items} items</Text>",
        "house card shows its item capacity",
    ),
    (
        "  houseBlurb: { color: '#999', fontSize: 13, marginTop: 4 },",
        "  houseBlurb: { color: '#999', fontSize: 13, marginTop: 4 },\n  houseCapacity: { color: '#f39c12', fontSize: 12, fontWeight: '700', marginTop: 6 },",
        "houseCapacity style added",
    ),
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
    print("HOUSE_ITEM_LIMITS_FRONTEND_OK")


if __name__ == "__main__":
    main()
