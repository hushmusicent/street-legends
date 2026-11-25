#!/usr/bin/env python3
"""AdMob R8 keep-rules fix (frontend) — durable fix, R8 stays ON.

Why: Expo SDK 58 turns R8 on by default in release builds
(android.enableMinifyInReleaseBuilds=true). R8 strips the AdMob
startup provider classes (MobileAdsInitProvider, WorkManager / Room)
before any JS runs, so the app flash-closes on launch whenever
react-native-google-mobile-ads is present, and works when it is
removed. These ProGuard keep rules tell R8 to leave those classes
alone. R8 is NOT disabled by this patch.

Changes (structural JSON edits, idempotent — no string anchors,
because the GitHub copy of app.json / package.json does not reflect
the live /app state):
  1. frontend/app.json — append ["expo-build-properties", {"android":
     {"enableMinifyInReleaseBuilds": true, "extraProguardRules": [...]}}]
     to expo.plugins (SKIP if already present with all rules; merge any
     missing rules if the entry exists without them).
  2. frontend/package.json — add "expo-build-properties": "~58.0.12"
     to dependencies, in alphabetical position (SKIP if already present).

Does NOT touch the react-native-google-mobile-ads plugin entry,
AdMobAds.tsx, AndroidManifest.xml, the backend, or any other file.

After running this patch:
  1. Run:  cd /app/frontend && npx expo install expo-build-properties
  2. Publish -> Android build -> download the AAB
  3. Upload the AAB to Play Internal testing (next AAB must be
     versionCode 174+; Play has 166 live, 173 is the latest installed
     build that still crashes)
  4. Install from the test link and open the app
"""

import json
import os
import sys

KEEP_RULES = [
    "-keep class com.google.android.gms.internal.consent_sdk.** { *; }",
    "-keep class com.google.android.gms.ads.** { *; }",
    "-keep class com.google.android.gms.common.** { *; }",
    "-keep class * extends androidx.room.RoomDatabase { <init>(); }",
    "-keep class * extends androidx.work.InputMerger { <init>(); }",
    "-keep class io.invertase.googlemobileads.** { *; }",
    "-keepattributes *Annotation*",
]

APP_JSON = "frontend/app.json"
PKG_JSON = "frontend/package.json"
BUILD_PROPS_VERSION = "~58.0.12"


def detect_indent(raw):
    """Dominant indent of the raw file (first indented non-empty line)."""
    for line in raw.splitlines()[1:]:
        stripped = line.lstrip(" ")
        if stripped and line != stripped:
            return len(line) - len(stripped)
    return 2


def load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return json.loads(raw), raw


def dump_json(path, data, raw):
    # expo-build-properties (SDK 58) needs extraProguardRules as ONE string.
    for _pl in data.get("expo", {}).get("plugins", []):
        if isinstance(_pl, list) and _pl and _pl[0] == "expo-build-properties" and len(_pl) > 1:
            _a = (_pl[1] or {}).get("android") or {}
            if isinstance(_a.get("extraProguardRules"), list):
                _a["extraProguardRules"] = "\n".join(_a["extraProguardRules"])
    text = json.dumps(data, indent=detect_indent(raw), ensure_ascii=False)
    if raw.endswith("\n"):
        text += "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def plugin_name(entry):
    if isinstance(entry, str):
        return entry
    if isinstance(entry, list) and entry and isinstance(entry[0], str):
        return entry[0]
    return None


def build_props_entry():
    return ["expo-build-properties", {
        "android": {
            "enableMinifyInReleaseBuilds": True,
            "extraProguardRules": list(KEEP_RULES),
        }
    }]


def patch_app_json():
    """Return 'changed', 'already', or 'failed'."""
    if not os.path.exists(APP_JSON):
        print("WARNING: %s not found, skipping app.json section" % APP_JSON)
        return "failed"
    try:
        data, raw = load_json(APP_JSON)
    except Exception as e:
        print("WARNING: %s is not parseable JSON (%s), skipping app.json section" % (APP_JSON, e))
        return "failed"
    expo = data.get("expo")
    if not isinstance(expo, dict):
        print("WARNING: %s has no 'expo' object, skipping app.json section" % APP_JSON)
        return "failed"
    plugins = expo.get("plugins")
    if plugins is None:
        plugins = []
        expo["plugins"] = plugins
    if not isinstance(plugins, list):
        print("WARNING: %s expo.plugins is not an array, skipping app.json section" % APP_JSON)
        return "failed"
    for i, entry in enumerate(plugins):
        if plugin_name(entry) != "expo-build-properties":
            continue
        if isinstance(entry, str):
            # Bare entry with no config: upgrade it in place to the full entry.
            plugins[i] = build_props_entry()
            dump_json(APP_JSON, data, raw)
            print("OK: app.json expo-build-properties entry upgraded with keep rules")
            return "changed"
        if isinstance(entry, list):
            cfg = entry[1] if len(entry) > 1 and isinstance(entry[1], dict) else None
            if cfg is None:
                entry.append(build_props_entry()[1])
                dump_json(APP_JSON, data, raw)
                print("OK: app.json expo-build-properties entry given android keep-rule config")
                return "changed"
            android = cfg.get("android")
            if not isinstance(android, dict):
                cfg["android"] = build_props_entry()[1]["android"]
                dump_json(APP_JSON, data, raw)
                print("OK: app.json expo-build-properties entry given android keep-rule config")
                return "changed"
            rules = android.get("extraProguardRules")
            if not isinstance(rules, list):
                android["extraProguardRules"] = list(KEEP_RULES)
                android["enableMinifyInReleaseBuilds"] = True
                dump_json(APP_JSON, data, raw)
                print("OK: app.json expo-build-properties entry given keep rules")
                return "changed"
            missing = [r for r in KEEP_RULES if r not in rules]
            if not missing and android.get("enableMinifyInReleaseBuilds") is True:
                print("OK: app.json already has expo-build-properties with all keep rules (SKIP)")
                return "already"
            for r in missing:
                rules.append(r)
            android["enableMinifyInReleaseBuilds"] = True
            dump_json(APP_JSON, data, raw)
            print("OK: app.json expo-build-properties entry updated with %d missing keep rule(s)" % len(missing))
            return "changed"
    plugins.append(build_props_entry())
    dump_json(APP_JSON, data, raw)
    print("OK: app.json expo-build-properties plugin added with 7 keep rules")
    return "changed"


def patch_package_json():
    """Return 'changed', 'already', or 'failed'."""
    if not os.path.exists(PKG_JSON):
        print("WARNING: %s not found, skipping package.json section" % PKG_JSON)
        return "failed"
    try:
        data, raw = load_json(PKG_JSON)
    except Exception as e:
        print("WARNING: %s is not parseable JSON (%s), skipping package.json section" % (PKG_JSON, e))
        return "failed"
    deps = data.get("dependencies")
    if not isinstance(deps, dict):
        print("WARNING: %s has no 'dependencies' object, skipping package.json section" % PKG_JSON)
        return "failed"
    if "expo-build-properties" in deps:
        print("OK: package.json already has expo-build-properties (SKIP)")
        return "already"
    new_deps = {}
    inserted = False
    for key, value in deps.items():
        if not inserted and key > "expo-build-properties":
            new_deps["expo-build-properties"] = BUILD_PROPS_VERSION
            inserted = True
        new_deps[key] = value
    if not inserted:
        new_deps["expo-build-properties"] = BUILD_PROPS_VERSION
    data["dependencies"] = new_deps
    dump_json(PKG_JSON, data, raw)
    print("OK: package.json expo-build-properties %s added to dependencies" % BUILD_PROPS_VERSION)
    return "changed"


def main():
    print("AdMob R8 keep-rules fix")
    print("R8 stays ON. These rules tell it to keep the AdMob startup classes")
    print("(MobileAdsInitProvider, WorkManager / Room, consent SDK) it was")
    print("stripping, which is what flash-closed the app on launch.")
    r1 = patch_app_json()
    r2 = patch_package_json()
    print("")
    print("NEXT STEPS:")
    print("  1. Run: cd /app/frontend && npx expo install expo-build-properties")
    print("  2. Publish -> Android build -> download the AAB")
    print("  3. Upload the AAB to Play Internal testing")
    print("     (next AAB must be versionCode 174+; Play has 166 live,")
    print("      173 is the latest installed build that still crashes)")
    print("  4. Install from the test link and open the app")
    print("NOTE: this is the research-backed durable fix, but it is NOT yet")
    print("proven on the device (no crash log). If the app still flash-closes")
    print("after this build, the next step is the actual crash log, not more")
    print("config guesses.")
    if r1 == "failed" and r2 == "failed":
        print("ADMOB_R8_KEEP_RULES_FAIL: both sections failed, see WARNINGs above")
        return 1
    print("ADMOB_R8_KEEP_RULES_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
