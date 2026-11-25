#!/usr/bin/env python3
"""AdMob R8 keep-rules fix v2 (frontend) — EXPANSION, R8 stays ON.

Why: the v1 keep-rules patch (7 rules, commit 3f924fa4) was applied and
confirmed in app.json / package.json, expo-build-properties ~58.0.12 was
installed, and build 174+ was installed — the app STILL flash-closes on
launch. Second Google research found R8 is still the cause, but the 7
rules missed more classes R8 strips, and the rules may not even have
reached the binary (expo-build-properties only writes
android/app/proguard-rules.pro during prebuild; a stale android/ folder
or EAS cache can silently ship old rules). These 8 extra rules cover
the classes the first 7 missed. R8 is NOT disabled by this patch.

Changes (structural JSON edit, idempotent — no string anchors,
because the GitHub copy of app.json does not reflect the live /app
state):
  frontend/app.json — append 8 keep rules to the existing
  expo-build-properties entry's android.extraProguardRules list
  (SKIP any rule already present verbatim; leave the existing 7
  rules, and enableMinifyInReleaseBuilds, exactly as they are).

Does NOT create the expo-build-properties entry if it is missing
(v1 already added it — if it is gone, that is reported, not silently
recreated). Does NOT touch package.json, the react-native-google-mobile-
ads plugin entry, AdMobAds.tsx, AndroidManifest.xml, the backend, or
any other file.

After running this patch:
  1. Publish -> Android build -> download the AAB
  2. Upload the AAB to Play Internal testing (next AAB must be
     versionCode 175+; 174+ is the latest installed build that still
     crashes)
  3. Install from the test link and open the app
"""

import json
import os
import sys

# The 8 new rules, in this order. The last one is a single multi-line
# string (one list entry with embedded newlines), as ProGuard expects
# a keepclassmembers block.
NEW_RULES = [
    "-keep class com.google.android.ump.** { *; }",
    "-keep class com.google.android.gms.internal.** { *; }",
    "-keep class com.google.android.play.core.hsdp.** { *; }",
    "-keep class androidx.startup.** { *; }",
    "-keep class * implements androidx.startup.Initializer { *; }",
    "-keep class expo.modules.notifications.** { *; }",
    "-keep class expo.modules.ExpoModulesPackageList { *; }",
    """-keepclassmembers class * implements java.io.Serializable {
  static final long serialVersionUID;
  private static final java.io.ObjectStreamField[] serialPersistentFields;
  private void writeObject(java.io.ObjectOutputStream);
  private void readObject(java.io.ObjectInputStream);
  java.lang.Object writeReplace();
  java.lang.Object readResolve();
}""",
]

APP_JSON = "frontend/app.json"


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
    if not isinstance(plugins, list):
        print("WARNING: %s has no expo.plugins array, skipping app.json section" % APP_JSON)
        return "failed"
    for entry in plugins:
        if plugin_name(entry) != "expo-build-properties":
            continue
        if not isinstance(entry, list):
            # Bare string entry: no android config to append rules to.
            # v1 already added the full entry; if it is gone/malformed,
            # report it instead of silently recreating it.
            print("WARNING: expo-build-properties entry in app.json is a bare string with no android config, skipping (v1 patch already added the full entry)")
            return "failed"
        cfg = entry[1] if len(entry) > 1 and isinstance(entry[1], dict) else None
        if cfg is None:
            print("WARNING: expo-build-properties entry in app.json has no config object, skipping (v1 patch already added the full entry)")
            return "failed"
        android = cfg.get("android")
        if not isinstance(android, dict):
            print("WARNING: expo-build-properties entry in app.json has no android config, skipping (v1 patch already added the full entry)")
            return "failed"
        rules = android.get("extraProguardRules")
        if not isinstance(rules, list):
            print("WARNING: expo-build-properties entry in app.json has no extraProguardRules list, skipping (v1 patch already added the full entry)")
            return "failed"
        missing = [r for r in NEW_RULES if r not in rules]
        if not missing:
            print("OK: app.json already has all 8 extra keep rules (SKIP)")
            return "already"
        for r in missing:
            rules.append(r)
        dump_json(APP_JSON, data, raw)
        print("OK: app.json expo-build-properties entry updated with %d new keep rule(s) (total %d rules)" % (len(missing), len(rules)))
        return "changed"
    print("WARNING: no expo-build-properties entry found in app.json, skipping (v1 patch already added it — if it is gone, something is wrong, not recreating it here)")
    return "failed"


def main():
    print("AdMob R8 keep-rules fix v2 (expansion)")
    print("R8 stays ON. These 8 extra rules cover the classes R8 strips")
    print("that the first 7 missed: public UMP consent, the rest of the")
    print("internal Google classes, AndroidX Startup, the Play hsdp shim,")
    print("and the notifications module.")
    result = patch_app_json()
    print("")
    print("NEXT STEPS:")
    print("  1. Publish -> Android build -> download the AAB")
    print("  2. Upload the AAB to Play Internal testing")
    print("     (next AAB must be versionCode 175+; 174+ is the latest")
    print("      installed build that still crashes)")
    print("  3. Install from the test link and open the app")
    print("WARNING: if the app still flash-closes after this build, the")
    print("rules may not have reached the binary because of a stale")
    print("prebuild / EAS cache — the next step is a clean prebuild before")
    print("building, and then the actual crash log, not more config")
    print("guesses.")
    if result == "failed":
        print("ADMOB_R8_KEEP_RULES_V2_FAIL: app.json section failed, see WARNINGs above")
        return 1
    print("ADMOB_R8_KEEP_RULES_V2_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
