#!/usr/bin/env python3
"""Fix the EAS build failure: enable BuildConfig for all Android modules.

The build fails in RUN_GRADLEW with:
  "defaultConfig contains custom BuildConfig fields, but the feature
   is disabled" (project ':expo-log-box').
AGP 9.x disables BuildConfig generation by default, but expo-log-box
defines custom BuildConfig fields. This patch:
  1. Downloads frontend/plugins/withBuildConfig.js from GitHub.
  2. Registers it in frontend/app.json's plugins array.
The plugin sets `android.defaults.buildfeatures.buildconfig=true` in
android/gradle.properties during prebuild, turning BuildConfig back on
for every module.

Run from /app: python3 frontend/patch-buildconfig.py
Then retry "Generate new build" in the Android Builds page.
Idempotent: a full re-run prints BUILDCONFIG_ALREADY_APPLIED.
"""
import json
import subprocess
import sys
from pathlib import Path

RAW = "https://raw.githubusercontent.com/hushmusicent/street-legends/main"
PLUGIN = Path("frontend/plugins/withBuildConfig.js")
APP_JSON = Path("frontend/app.json")
PLUGIN_REF = "./plugins/withBuildConfig.js"
MARKER = "BUILDCONFIG_OK"

def main():
    if not APP_JSON.exists():
        print("ERROR: frontend/app.json not found (run from /app)")
        sys.exit(1)
    # 1. Download the plugin.
    r = subprocess.run(
        ["curl", "-sL", f"{RAW}/frontend/plugins/withBuildConfig.js?v=1", "-o", str(PLUGIN)],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode != 0 or not PLUGIN.exists() or PLUGIN.stat().st_size == 0:
        print("ERROR: plugin download failed")
        sys.exit(1)
    if "android.defaults.buildfeatures.buildconfig" not in PLUGIN.read_text():
        print("ERROR: downloaded plugin is not the BuildConfig fix")
        sys.exit(1)
    # 2. Register it in app.json (idempotent).
    data = json.loads(APP_JSON.read_text())
    plugins = data.get("expo", {}).get("plugins", [])
    if PLUGIN_REF in plugins:
        print("BUILDCONFIG_ALREADY_APPLIED")
        return
    plugins.append(PLUGIN_REF)
    data["expo"]["plugins"] = plugins
    APP_JSON.write_text(json.dumps(data, indent=2) + "\n")
    print(MARKER)

if __name__ == "__main__":
    main()
