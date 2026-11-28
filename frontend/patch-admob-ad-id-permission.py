"""Street Legends frontend: add AD_ID permission to app.json.

Play blocks the Production release: the declaration says the app uses the
advertising ID, but the AAB manifest lacks
`com.google.android.gms.permission.AD_ID`. Without it the advertising ID is
zeroed out and AdMob targeting/revenue breaks. The google-mobile-ads
library does NOT add this permission by itself in this setup.

Fix: add `com.google.android.gms.permission.AD_ID` to the
`android.permissions` array in frontend/app.json (Expo adds it to the
generated AndroidManifest during prebuild). Structural JSON edit (the /app
app.json differs from the GitHub copy), idempotent.

After this patch: Publish + new Android build (new AAB, versionCode must
exceed 190), upload it, and create the Production release again. The
Advertising ID error should be gone.

Run from /app: python3 frontend/patch-admob-ad-id-permission.py
Marker: ADMOB_AD_ID_PERMISSION_OK
"""

import io
import json
import sys

PATH = "frontend/app.json"
MARKER = "ADMOB_AD_ID_PERMISSION_OK"
PERM = "com.google.android.gms.permission.AD_ID"

def main():
    try:
        with io.open(PATH, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print("FAIL: %s not found" % PATH)
        print("ADMOB_AD_ID_PERMISSION_FAIL")
        return 1
    except ValueError as e:
        print("FAIL: %s is not valid JSON: %s" % (PATH, e))
        print("ADMOB_AD_ID_PERMISSION_FAIL")
        return 1

    android = data.setdefault("expo", {}).setdefault("android", {})
    perms = android.setdefault("permissions", [])
    if not isinstance(perms, list):
        print("FAIL: android.permissions is not a list")
        print("ADMOB_AD_ID_PERMISSION_FAIL")
        return 1

    if PERM in perms:
        print("SKIP: AD_ID permission already in android.permissions")
        print(MARKER)
        return 0

    perms.append(PERM)
    with io.open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    print("OK: added %s to android.permissions" % PERM)
    print(MARKER)
    return 0

if __name__ == "__main__":
    sys.exit(main())
