#!/usr/bin/env python3
"""Street Legends EAS build config: version 1.0.20 + android versionCode 163
+ eas.json production profile (Android app-bundle).

Run from /app:
  cd /app && curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/patch-eas-build-version-163.py" -o frontend/patch-eas-build-version-163.py && python3 frontend/patch-eas-build-version-163.py

Why: Play already has versionCode 162 in Production. A new AAB must be
higher than 162 or Play rejects it. app.json has version "1.0.0" and NO
android.versionCode, so an EAS build from it would default to versionCode 1.
This sets version 1.0.20 and versionCode 163 explicitly, and creates
frontend/eas.json (production profile, Android app-bundle) only if it is
missing. It does NOT touch any AdMob code.

Idempotent. One echo marker: EAS_BUILD_VERSION_163_OK.
"""
import json
import re
import sys
from pathlib import Path

APPJSON_PATH = Path("frontend/app.json")
PACKAGE_PATH = Path("frontend/package.json")
EASJSON_PATH = Path("frontend/eas.json")

TARGET_VERSION = "1.0.20"
TARGET_VERSION_CODE = 163

EASJSON_CONTENT = """{
  "build": {
    "production": {
      "android": {
        "buildType": "app-bundle"
      }
    }
  }
}
"""


def replace_once(text, anchor, new, label):
    """Replace anchor exactly once. Returns (new_text, status)."""
    count = text.count(anchor)
    if count == 0:
        print(f"WARNING: {label}: anchor not found, skipping")
        return text, "skip"
    if count > 1:
        print(f"WARNING: {label}: anchor found {count} times, skipping (will not guess)")
        return text, "skip"
    return text.replace(anchor, new, 1), "ok"


def main():
    if not APPJSON_PATH.exists():
        print("ERROR: frontend/app.json not found. Run from /app.")
        sys.exit(1)

    text = APPJSON_PATH.read_text()
    original = text

    # ---- Section 1: app.json version 1.0.0 -> 1.0.20 ----
    if '"version": "1.0.20"' in text:
        print("SKIP: app.json version already 1.0.20")
    else:
        text, status = replace_once(
            text,
            '    "version": "1.0.0",',
            '    "version": "1.0.20",',
            "app.json version",
        )
        if status == "ok":
            print("OK: app.json version -> 1.0.20")

    # ---- Section 2: android.versionCode -> 163 ----
    m = re.search(r'"versionCode"\s*:\s*(\d+)', text)
    if m:
        current = int(m.group(1))
        if current >= TARGET_VERSION_CODE:
            print(f"SKIP: android.versionCode already {current} (>= 163), leaving it")
        else:
            text = re.sub(
                r'("versionCode"\s*:\s*)\d+',
                r'\g<1>163',
                text,
                count=1,
            )
            print(f"OK: android.versionCode {current} -> 163")
    else:
        # No versionCode yet: insert after the android package line.
        # Handles the package line with or without a trailing comma.
        pattern = r'("package":\s*"com\.emergent\.streetempiretest\.xfvyzd")(,?)(\n)'
        new_text, n = re.subn(
            pattern,
            r'\1,\n      "versionCode": 163\3',
            text,
            count=1,
        )
        if n == 0:
            print("WARNING: android package line not found, versionCode not added")
        else:
            text = new_text
            print("OK: android.versionCode 163 added")

    # ---- Section 3: validate app.json still parses, then write it ----
    try:
        json.loads(text)
    except json.JSONDecodeError as e:
        print(f"WARNING: app.json edit would break JSON ({e}); keeping original file")
        text = original
    if text != original:
        APPJSON_PATH.write_text(text)
        print("OK: app.json written")
    else:
        print("SKIP: app.json unchanged")

    # ---- Section 4: eas.json (create only if missing) ----
    if EASJSON_PATH.exists():
        print("SKIP: frontend/eas.json already exists, leaving it")
    else:
        try:
            json.loads(EASJSON_CONTENT)
        except json.JSONDecodeError as e:
            print(f"WARNING: eas.json template invalid ({e}); not writing it")
        else:
            EASJSON_PATH.write_text(EASJSON_CONTENT)
            print("OK: frontend/eas.json created (production profile, Android app-bundle)")

    # ---- Section 5: read-only check that the AdMob entries are in /app ----
    # The AdMob code lives ONLY in /app (not on GitHub). If /app was reset,
    # the build would ship without ads. Warn loudly; do not fail the patch.
    pkg_ok = False
    if PACKAGE_PATH.exists():
        pkg_ok = "react-native-google-mobile-ads" in PACKAGE_PATH.read_text()
    app_text = APPJSON_PATH.read_text()
    plugin_ok = "react-native-google-mobile-ads" in app_text
    if pkg_ok and plugin_ok:
        print("OK: AdMob entries present in /app (package.json dep + app.json plugin)")
    else:
        if not pkg_ok:
            print("WARNING: react-native-google-mobile-ads NOT in frontend/package.json in /app - build would ship WITHOUT ads")
        if not plugin_ok:
            print("WARNING: react-native-google-mobile-ads plugin NOT in frontend/app.json in /app - build would ship WITHOUT ads")

    print("EAS_BUILD_VERSION_163_OK")


if __name__ == "__main__":
    main()
