"""Street Legends frontend v3: fix requestPurchase for react-native-iap v17.
Run from repo root: python3 frontend/patch-god-potions-frontend-v3.py
Idempotent - safe to re-run.

v17 changed requestPurchase's shape. The old call
    requestPurchase({ sku })
throws 'Missing purchase request configuration'. v17 requires:
    requestPurchase({ request: { google: { skus: [sku] } }, type: 'in-app' })

After this patch: rebuild the app (new native build) and upload the new AAB.
"""
import sys
from pathlib import Path

COMPONENT = Path("frontend/components/GodPotions.tsx")

OLD = "await requestPurchase({ sku });"
NEW = "await requestPurchase({ request: { google: { skus: [sku] } }, type: 'in-app' });"


def main():
    if not COMPONENT.exists():
        print(f"ERROR: {COMPONENT} not found. Run from repo root.")
        sys.exit(1)
    src = COMPONENT.read_text()
    if NEW in src:
        print("SKIP: v17 requestPurchase shape already applied")
    else:
        if src.count(OLD) != 1:
            print(f"ERROR: anchor matched {src.count(OLD)}x. Aborting.")
            print("Open frontend/components/GodPotions.tsx and change the")
            print("requestPurchase({ sku }) line to:")
            print("  " + NEW)
            sys.exit(1)
        src = src.replace(OLD, NEW, 1)
        COMPONENT.write_text(src)
        print("OK: requestPurchase updated to v17 shape")
    print("GOD_POTIONS_FRONTEND_V3_OK")


if __name__ == "__main__":
    main()
