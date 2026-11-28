"""Street Legends frontend: add AD_ID permission directly to AndroidManifest.

The app.json fix landed (ADMOB_AD_ID_PERMISSION_OK) but the build still
lacks the permission: the android/ folder in /app is stale (generated
before app.json gained the permission) and the build reuses it instead of
regenerating it. A clean prebuild would wipe the agent's buildFeatures
fix in build.gradle, so instead this patch adds the permission directly
to the existing manifest. app.json already has it too, so any future
prebuild regeneration will also include it.

Inserts `<uses-permission android:name="com.google.android.gms.permission.AD_ID" />`
just before the <application> tag in
frontend/android/app/src/main/AndroidManifest.xml. Idempotent.

After this patch: Publish + new Android build (AAB must exceed 193),
upload it, and create the Production release again. Verify with:
grep -c "AD_ID" frontend/android/app/src/main/AndroidManifest.xml
(expect 1).

Run from /app: python3 frontend/patch-admob-ad-id-manifest.py
Marker: ADMOB_AD_ID_MANIFEST_OK
"""

import io
import sys

PATH = "frontend/android/app/src/main/AndroidManifest.xml"
MARKER = "ADMOB_AD_ID_MANIFEST_OK"
PERM_LINE = '    <uses-permission android:name="com.google.android.gms.permission.AD_ID" />'
ANCHOR = "<application"

def main():
    try:
        with io.open(PATH, encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("FAIL: %s not found" % PATH)
        print("ADMOB_AD_ID_MANIFEST_FAIL")
        return 1

    if "com.google.android.gms.permission.AD_ID" in src:
        print("SKIP: AD_ID permission already in AndroidManifest.xml")
        print(MARKER)
        return 0

    if ANCHOR not in src:
        print("FAIL: <application> tag not found in manifest")
        print("ADMOB_AD_ID_MANIFEST_FAIL")
        return 1

    new_src = src.replace(ANCHOR, PERM_LINE + "\n    " + ANCHOR, 1)
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("OK: added AD_ID permission to AndroidManifest.xml")
    print(MARKER)
    return 0

if __name__ == "__main__":
    sys.exit(main())
