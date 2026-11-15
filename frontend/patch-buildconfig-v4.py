#!/usr/bin/env python3
"""Fix the EAS build failure, v4.

v1 set android.defaults.buildfeatures.buildconfig=true in gradle.properties,
but AGP 9 REMOVED that property — setting it is a hard error at
"Configure project :app". v2/v3 set buildConfig from the root build.gradle
inside a subprojects afterEvaluate block. The block landed in the generated
file (confirmed at line 27), but AGP 9 rejects late mutation via
afterEvaluate, so the build still died during configuration before any task
ran. v4 configures buildFeatures when each Android plugin is applied
(plugins.withId + extensions.configure), during the module's own evaluation
— before AGP finalizes the DSL. That is the mechanism AGP 9's own migration
guide prescribes.

This patch:
  1. Re-downloads frontend/plugins/withBuildConfig.js (v4) from GitHub.
  2. Makes sure it is registered in frontend/app.json's plugins array.
Run from /app: python3 frontend/patch-buildconfig-v4.py
Then retry "Generate new build" in the Android Builds page.
Idempotent: a full re-run prints BUILDCONFIG_V4_ALREADY_APPLIED.
"""
import json
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
PLUGIN = Path("frontend/plugins/withBuildConfig.js")
APP_JSON = Path("frontend/app.json")
PLUGIN_REF = "./plugins/withBuildConfig.js"
MARKER = "BUILDCONFIG_V4_OK"

def main():
    if not APP_JSON.exists():
        print("ERROR: frontend/app.json not found (run from /app)")
        sys.exit(1)
    # 1. Download the v4 plugin.
    r = subprocess.run(
        ["curl", "-sL", f"{RAW}/frontend/plugins/withBuildConfig.js?v=7", "-o", str(PLUGIN)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0 or not PLUGIN.exists() or PLUGIN.stat().st_size == 0:
        print("ERROR: plugin download failed")
        sys.exit(1)
    text = PLUGIN.read_text()
    if "BUILDCONFIG-FIX-V4" not in text or "plugins.withId" not in text:
        print("ERROR: downloaded plugin is not the v4 BuildConfig fix")
        sys.exit(1)
    if "android.defaults.buildfeatures.buildconfig" in text and "filter" not in text:
        print("ERROR: plugin still sets the removed AGP 9 property")
        sys.exit(1)
    # 2. Register it in app.json (idempotent).
    data = json.loads(APP_JSON.read_text())
    plugins = data.get("expo", {}).get("plugins", [])
    if PLUGIN_REF in plugins:
        print("BUILDCONFIG_V4_ALREADY_APPLIED")
        return
    plugins.append(PLUGIN_REF)
    data["expo"]["plugins"] = plugins
    APP_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(MARKER)

if __name__ == "__main__":
    main()
