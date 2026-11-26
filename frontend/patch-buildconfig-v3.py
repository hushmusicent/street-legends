#!/usr/bin/env python3
"""Fix the EAS build failure, v3.

v1 set android.defaults.buildfeatures.buildconfig=true in gradle.properties,
but AGP 9 REMOVED that property — setting it is a hard error at
"Configure project :app". v2 enabled BuildConfig from the root build.gradle
but used a direct Groovy assignment to the buildConfig property, which AGP 9
rejects (it is a read-only Property<Boolean> with no setter) — the build
died during configuration, before any task ran. v3 calls .set(true) on the
Property directly.

This patch:
  1. Re-downloads frontend/plugins/withBuildConfig.js (v3) from GitHub.
  2. Makes sure it is registered in frontend/app.json's plugins array.
Run from /app: python3 frontend/patch-buildconfig-v3.py
Then retry "Generate new build" in the Android Builds page.
Idempotent: a full re-run prints BUILDCONFIG_V3_ALREADY_APPLIED.
"""

# Guard added: BUILDCONFIG-FIX-V5 (AGP 9 safe) already in android/build.gradle -> do nothing.
from pathlib import Path as _P
for _c in (_P(__file__).resolve().parent / "android" / "build.gradle", _P("/app/frontend/android/build.gradle")):
    if _c.exists() and "BUILDCONFIG-FIX-V5" in _c.read_text():
        print("android/build.gradle already has BUILDCONFIG-FIX-V5; nothing to do.")
        raise SystemExit(0)
import json
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
PLUGIN = Path("frontend/plugins/withBuildConfig.js")
APP_JSON = Path("frontend/app.json")
PLUGIN_REF = "./plugins/withBuildConfig.js"
MARKER = "BUILDCONFIG_V3_OK"

def main():
    if not APP_JSON.exists():
        print("ERROR: frontend/app.json not found (run from /app)")
        sys.exit(1)
    # 1. Download the v3 plugin.
    r = subprocess.run(
        ["curl", "-sL", f"{RAW}/frontend/plugins/withBuildConfig.js?v=6", "-o", str(PLUGIN)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0 or not PLUGIN.exists() or PLUGIN.stat().st_size == 0:
        print("ERROR: plugin download failed")
        sys.exit(1)
    text = PLUGIN.read_text()
    if "BUILDCONFIG-FIX-V3" not in text or "buildConfig.set(true)" not in text:
        print("ERROR: downloaded plugin is not the v3 BuildConfig fix")
        sys.exit(1)
    if "buildConfig = true" in text:
        print("ERROR: plugin still uses the direct assignment (stale v2)")
        sys.exit(1)
    if "android.defaults.buildfeatures.buildconfig" in text and "filter" not in text:
        print("ERROR: plugin still sets the removed AGP 9 property")
        sys.exit(1)
    # 2. Register it in app.json (idempotent).
    data = json.loads(APP_JSON.read_text())
    plugins = data.get("expo", {}).get("plugins", [])
    if PLUGIN_REF in plugins:
        print("BUILDCONFIG_V3_ALREADY_APPLIED")
        return
    plugins.append(PLUGIN_REF)
    data["expo"]["plugins"] = plugins
    APP_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(MARKER)

if __name__ == "__main__":
    main()
