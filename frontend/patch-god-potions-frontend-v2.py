"""Street Legends frontend v2: fix BILLING permission + react-native-iap v17 API.
Run from repo root: python3 frontend/patch-god-potions-frontend-v2.py
Idempotent - safe to re-run. Upgrades a v1 install or installs fresh.

What went wrong in v1:
1. react-native-iap v17 ships NO Expo config plugin, so the "react-native-iap"
   entry in app.json did nothing - the BILLING permission never reached the
   manifest and Play still blocks product creation. v2 writes the permission
   directly: "com.android.vending.BILLING" in expo.android.permissions.
2. v17 renamed getProducts -> fetchProducts, and products now expose
   id/displayPrice (not productId/localizedPrice). v2 updates GodPotions.tsx.

After this patch: rebuild the app (new native build), upload the new AAB to
Play Console, THEN create the one-time products god_potion_health_1h and
god_potion_energy_1h ($1.00 each).
"""
import json
import sys
from pathlib import Path

SHOP = Path("frontend/app/(tabs)/shop.tsx")
APPJSON = Path("frontend/app.json")
COMPONENT = Path("frontend/components/GodPotions.tsx")

BILLING_PERMISSION = "com.android.vending.BILLING"

# GodPotions.tsx v1 -> v2 API fixes (react-native-iap v17)
COMPONENT_FIXES = [
    (
        "v17 fetchProducts import",
        "  getProducts,\n",
        "  fetchProducts,\n",
    ),
    (
        "v17 fetchProducts call",
        "await getProducts({ skus: SKUS })",
        "await fetchProducts({ skus: SKUS })",
    ),
    (
        "v17 product id field",
        "(x: any) => x.productId === sku",
        "(x: any) => (x.id ?? x.productId) === sku",
    ),
    (
        "v17 displayPrice field",
        "p?.localizedPrice || '$1.00'",
        "p?.displayPrice || p?.localizedPrice || '$1.00'",
    ),
]


def patch_appjson() -> int:
    try:
        data = json.loads(APPJSON.read_text())
    except FileNotFoundError:
        print(f"ERROR: {APPJSON} not found. Run from repo root.")
        sys.exit(1)
    changed = 0
    expo = data.get("expo", {})

    # 1. Remove the bogus react-native-iap plugin entry (v17 has no Expo plugin)
    plugins = expo.get("plugins", [])
    new_plugins = [p for p in plugins if not (p == "react-native-iap" or (isinstance(p, list) and p and p[0] == "react-native-iap"))]
    if len(new_plugins) != len(plugins):
        expo["plugins"] = new_plugins
        changed += 1
        print("OK: removed no-op react-native-iap plugin entry from app.json")

    # 2. Add the BILLING permission directly (guaranteed manifest merge)
    android = expo.setdefault("android", {})
    perms = android.setdefault("permissions", [])
    if BILLING_PERMISSION not in perms:
        perms.append(BILLING_PERMISSION)
        changed += 1
        print("OK: com.android.vending.BILLING added to android.permissions")
    else:
        print("SKIP: BILLING permission already in app.json")

    if changed:
        APPJSON.write_text(json.dumps(data, indent=2) + "\n")
    return changed


def patch_component() -> int:
    if not COMPONENT.exists():
        print(f"ERROR: {COMPONENT} not found.")
        print('Download it first:')
        print('curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/components/GodPotions.tsx" -o frontend/components/GodPotions.tsx')
        sys.exit(1)
    src = COMPONENT.read_text()
    changed = 0
    for name, old, new in COMPONENT_FIXES:
        if new in src:
            print(f"SKIP (already applied): {name}")
            continue
        if src.count(old) != 1:
            print(f"ERROR: anchor for '{name}' matched {src.count(old)}x. Aborting.")
            sys.exit(1)
        src = src.replace(old, new, 1)
        changed += 1
        print(f"OK: {name}")
    if changed:
        COMPONENT.write_text(src)
    return changed


def patch_shop() -> int:
    if not SHOP.exists():
        print(f"ERROR: {SHOP} not found. Run from repo root.")
        sys.exit(1)
    src = SHOP.read_text()
    changed = 0

    imp_old = "import api from '../../services/api';"
    imp_new = "import api from '../../services/api';\nimport { GodPotions } from '../../components/GodPotions';"
    if imp_new not in src:
        if src.count(imp_old) != 1:
            print(f"ERROR: shop import anchor matched {src.count(imp_old)}x. Aborting.")
            sys.exit(1)
        src = src.replace(imp_old, imp_new, 1)
        changed += 1
        print("OK: GodPotions import added")
    else:
        print("SKIP: GodPotions import already present")

    render_old = "      {/* Filter Tabs */}"
    render_new = "      <GodPotions playerId={playerId} />\n\n      {/* Filter Tabs */}"
    if render_new not in src:
        if src.count(render_old) != 1:
            print(f"ERROR: shop render anchor matched {src.count(render_old)}x. Aborting.")
            sys.exit(1)
        src = src.replace(render_old, render_new, 1)
        changed += 1
        print("OK: GodPotions section inserted in shop")
    else:
        print("SKIP: GodPotions section already rendered")

    if changed:
        SHOP.write_text(src)
    return changed


def main():
    changed = 0
    changed += patch_appjson()
    changed += patch_component()
    changed += patch_shop()

    if changed:
        print(f"\nDone. {changed} patch(es) applied.")
        print("NEXT: rebuild the app (new native build) and upload the new AAB to Play Console.")
    else:
        print("\nNothing to do - all patches already applied.")
    print("GOD_POTIONS_FRONTEND_V2_OK")


if __name__ == "__main__":
    main()
