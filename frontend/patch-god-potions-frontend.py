"""Street Legends frontend: God Potions $1 IAP shop section + BILLING permission.
Run from repo root: python3 frontend/patch-god-potions-frontend.py
Idempotent - safe to re-run. Aborts on anchor mismatch.

Does:
1. frontend/app/(tabs)/shop.tsx
   - imports GodPotions component
   - renders <GodPotions playerId={playerId} /> above the filter tabs
2. frontend/app.json
   - adds "react-native-iap" to expo.plugins (its config plugin merges the
     com.android.vending.BILLING permission into AndroidManifest)

Prereqs (run first in the Emergent terminal):
    cd frontend && npx expo install react-native-iap

After this patch: rebuild the app (new native build), upload the new AAB to
Play Console, THEN create the one-time products god_potion_health_1h and
god_potion_energy_1h ($1.00 each) - the products page unlocks once Play sees
an APK/AAB with the BILLING permission.
"""
import json
import sys
from pathlib import Path

SHOP = Path("frontend/app/(tabs)/shop.tsx")
APPJSON = Path("frontend/app.json")
COMPONENT = Path("frontend/components/GodPotions.tsx")
MARKER = "GodPotions"


def patch_shop(src: str) -> tuple[str, int]:
    changed = 0

    imp_old = "import api from '../../services/api';"
    imp_new = "import api from '../../services/api';\nimport { GodPotions } from '../../components/GodPotions';"
    if imp_new in src:
        print("SKIP: GodPotions import already present")
    else:
        if src.count(imp_old) != 1:
            print(f"ERROR: shop import anchor matched {src.count(imp_old)}x. Aborting.")
            sys.exit(1)
        src = src.replace(imp_old, imp_new, 1)
        changed += 1
        print("OK: GodPotions import added")

    render_old = "      {/* Filter Tabs */}"
    render_new = "      <GodPotions playerId={playerId} />\n\n      {/* Filter Tabs */}"
    if render_new in src:
        print("SKIP: GodPotions section already rendered")
    else:
        if src.count(render_old) != 1:
            print(f"ERROR: shop render anchor matched {src.count(render_old)}x. Aborting.")
            sys.exit(1)
        src = src.replace(render_old, render_new, 1)
        changed += 1
        print("OK: GodPotions section inserted in shop")

    return src, changed


def patch_appjson() -> int:
    try:
        data = json.loads(APPJSON.read_text())
    except FileNotFoundError:
        print(f"ERROR: {APPJSON} not found. Run from repo root.")
        sys.exit(1)
    plugins = data.get("expo", {}).get("plugins")
    if plugins is None:
        print("ERROR: expo.plugins not found in app.json. Aborting.")
        sys.exit(1)
    names = [p if isinstance(p, str) else p[0] for p in plugins]
    if "react-native-iap" in names:
        print("SKIP: react-native-iap plugin already in app.json")
        return 0
    plugins.append("react-native-iap")
    APPJSON.write_text(json.dumps(data, indent=2) + "\n")
    print("OK: react-native-iap plugin added to app.json (adds BILLING permission)")
    return 1


def main():
    if not SHOP.exists():
        print(f"ERROR: {SHOP} not found. Run from repo root.")
        sys.exit(1)
    if not COMPONENT.exists():
        print(f"ERROR: {COMPONENT} not found.")
        print("Download it first:")
        print('curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/components/GodPotions.tsx" -o frontend/components/GodPotions.tsx')
        sys.exit(1)

    changed = 0
    src = SHOP.read_text()
    src, c = patch_shop(src)
    changed += c
    if c:
        SHOP.write_text(src)

    changed += patch_appjson()

    if changed:
        print(f"\nDone. {changed} patch(es) applied.")
    else:
        print("\nNothing to do - all patches already applied.")
    print("GOD_POTIONS_FRONTEND_OK")


if __name__ == "__main__":
    main()
