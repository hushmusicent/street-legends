#!/usr/bin/env python3
"""Set app.json version to 1.0.20 and android.versionCode to 202.

Supersedes patch-eas-build-version-195.py (the project is on 201, not 194).

Backend/frontend: frontend config (affects the next EAS build).
Run from /app:
  cd /app && curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/patch-eas-build-version-202.py" -o frontend/patch-eas-build-version-202.py && python3 frontend/patch-eas-build-version-202.py

Marker: EAS_BUILD_VERSION_202_OK
Idempotent: re-running reports SKIP if already at 202.
"""
import json
import os
import sys

APP_JSON = "frontend/app.json"
MARKER = "EAS_BUILD_VERSION_202_OK"
TARGET_VERSION = "1.0.20"
TARGET_CODE = 202

def main():
    if not os.path.exists(APP_JSON):
        print(f"ERROR: {APP_JSON} not found (run from /app)")
        sys.exit(1)

    with open(APP_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    expo = data.setdefault("expo", {})
    android = expo.setdefault("android", {})

    cur_version = expo.get("version")
    cur_code = android.get("versionCode")

    if cur_version == TARGET_VERSION and cur_code == TARGET_CODE:
        print(f"SKIP: already version {TARGET_VERSION} / versionCode {TARGET_CODE}")
        print(MARKER)
        return

    expo["version"] = TARGET_VERSION
    android["versionCode"] = TARGET_CODE

    with open(APP_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    print(f"OK: version {cur_version} -> {TARGET_VERSION}")
    print(f"OK: android.versionCode {cur_code} -> {TARGET_CODE}")
    print(MARKER)

if __name__ == "__main__":
    main()
