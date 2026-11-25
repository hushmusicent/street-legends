#!/usr/bin/env python3
"""AdMob R8 keep-rules fix v2.1 (frontend) — REPAIR of the v2 failure, R8 stays ON.

Why v2 failed: v2 ran in the live /app terminal at 13:55 and printed
"WARNING: expo-build-properties entry in app.json has no extraProguardRules
list, skipping (v1 patch already added the full entry)" then
ADMOB_R8_KEEP_RULES_V2_FAIL. The v1 patch had run clean at 13:20 and
printed "OK: app.json expo-build-properties plugin added with 7 keep
rules", and grep confirmed the string "expo-build-properties" in
app.json — but v2 found the live entry WITHOUT its extraProguardRules
list. Either v1 stored the entry in a different structure than v2
expected, or something rewrote app.json between the two runs and
dropped the list. The live /app app.json structure was never directly
seen (GitHub is stale here), so this patch prints the exact entry it
finds and repairs EVERY plausible form, ending with all 15 rules in
place. R8 is NOT disabled by this patch.

Changes (structural JSON edit, idempotent — no string anchors):
  frontend/app.json — the expo-build-properties entry in expo.plugins
  is brought to the canonical form:
    ["expo-build-properties", {"android": {
        "enableMinifyInReleaseBuilds": true,
        "extraProguardRules": [15 rules]}}]
  Cases handled: entry absent (append it), bare string (replace in
  place), list with no config (add the config), list with config but
  no android dict (add android), android dict but no extraProguardRules
  list (add the full 15-rule list, preserving every other key),
  list present (append only the missing rules, preserving the existing
  ones and their order), dict-form or any other unexpected form
  (WARNING with repr, then replace with the canonical form).
  Duplicate expo-build-properties entries are removed so only one
  remains.

Does NOT touch package.json, the react-native-google-mobile-ads
plugin entry, AdMobAds.tsx, AndroidManifest.xml, the backend, or any
other file. R8 stays ON (enableMinifyInReleaseBuilds true).

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

# The v1 7 rules, then the v2 8 rules, in this order. The last rule is
# a single multi-line string (one list entry with embedded newlines),
# as ProGuard expects a keepclassmembers block.
RULES_V1 = [
    "-keep class com.google.android.gms.internal.consent_sdk.** { *; }",
    "-keep class com.google.android.gms.ads.** { *; }",
    "-keep class com.google.android.gms.common.** { *; }",
    "-keep class * extends androidx.room.RoomDatabase { <init>(); }",
    "-keep class * extends androidx.work.InputMerger { <init>(); }",
    "-keep class io.invertase.googlemobileads.** { *; }",
    "-keepattributes *Annotation*",
]

RULES_V2 = [
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

ALL_RULES = RULES_V1 + RULES_V2

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
    if isinstance(entry, dict) and "expo-build-properties" in entry:
        return "expo-build-properties"
    return None


def canonical_entry():
    return ["expo-build-properties", {
        "android": {
            "enableMinifyInReleaseBuilds": True,
            "extraProguardRules": list(ALL_RULES),
        }
    }]


def entry_rules(entry):
    """The extraProguardRules list of a list-form entry, or None."""
    if not isinstance(entry, list) or len(entry) < 2:
        return None
    cfg = entry[1]
    if not isinstance(cfg, dict):
        return None
    android = cfg.get("android")
    if not isinstance(android, dict):
        return None
    rules = android.get("extraProguardRules")
    return rules if isinstance(rules, list) else None


def repair_entry(entry):
    """Bring one list-form expo-build-properties entry to the canonical
    15-rule form in place. Caller handles non-list forms.
    Returns (changed_bool, note_str)."""
    if len(entry) < 2 or not isinstance(entry[1], dict):
        # List with no config object (or a non-dict config): add/replace it.
        if len(entry) < 2:
            entry.append(canonical_entry()[1])
        else:
            entry[1] = canonical_entry()[1]
        return True, "entry had no config object, added full android keep-rule config"
    cfg = entry[1]
    android = cfg.get("android")
    if not isinstance(android, dict):
        cfg["android"] = canonical_entry()[1]["android"]
        return True, "entry had no android config, added android keep-rule config"
    rules = android.get("extraProguardRules")
    if not isinstance(rules, list):
        android["extraProguardRules"] = list(ALL_RULES)
        android["enableMinifyInReleaseBuilds"] = True
        return True, "entry had no extraProguardRules list, added all 15 keep rules"
    missing = [r for r in ALL_RULES if r not in rules]
    changed = False
    if missing:
        for r in missing:
            rules.append(r)
        changed = True
    if android.get("enableMinifyInReleaseBuilds") is not True:
        android["enableMinifyInReleaseBuilds"] = True
        changed = True
    if changed:
        return True, "appended %d missing keep rule(s) (total %d rules)" % (len(missing), len(rules))
    return False, "already has all 15 keep rules"


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

    matches = [i for i, e in enumerate(plugins) if plugin_name(e) == "expo-build-properties"]
    if not matches:
        print("DIAGNOSTIC: no expo-build-properties entry found in app.json plugins")
        plugins.append(canonical_entry())
        dump_json(APP_JSON, data, raw)
        print("OK: app.json expo-build-properties plugin added with all 15 keep rules")
        return "changed"

    # Diagnostic: show exactly what the live entry looks like.
    first = plugins[matches[0]]
    print("DIAGNOSTIC: expo-build-properties entry found (type %s):" % type(first).__name__)
    print("  %r" % (first,))
    rules = entry_rules(first)
    if rules is not None:
        print("DIAGNOSTIC: extraProguardRules list exists with %d rule(s)" % len(rules))
    else:
        print("DIAGNOSTIC: extraProguardRules list is MISSING (this is why v2 failed)")

    changed, note = (True, "entry was not a list-form plugin entry, replaced with canonical form") \
        if (not isinstance(first, list) or not first or not isinstance(first[0], str)) \
        else repair_entry(first)
    if not isinstance(first, list) or not first or not isinstance(first[0], str):
        # Bare string, dict-form, or any other unexpected form: the
        # entry object itself must be swapped in the plugins list.
        plugins[matches[0]] = canonical_entry()
        print("WARNING: entry was a %s, replaced with the canonical list-form entry" % type(first).__name__)
    if changed:
        print("OK: app.json expo-build-properties entry repaired — %s" % note)
    else:
        print("OK: app.json expo-build-properties entry %s" % note)

    # Remove any duplicate entries so only one remains.
    if len(matches) > 1:
        for i in sorted(matches[1:], reverse=True):
            del plugins[i]
        changed = True
        print("OK: removed %d duplicate expo-build-properties entr(ies)" % (len(matches) - 1))

    # Verify the result before writing.
    final = plugins[matches[0]]
    final_rules = entry_rules(final)
    if final_rules is None or any(r not in final_rules for r in ALL_RULES):
        print("WARNING: repair did not leave all 15 rules in place, not writing")
        return "failed"
    if len(final_rules) != len(ALL_RULES):
        print("WARNING: entry now has %d rules, expected %d — keeping the extra ones, but this is unexpected" % (len(final_rules), len(ALL_RULES)))
    if not changed:
        return "already"
    dump_json(APP_JSON, data, raw)
    print("OK: app.json now has expo-build-properties with %d keep rules (R8 stays ON)" % len(final_rules))
    return "changed"


def main():
    print("AdMob R8 keep-rules fix v2.1 (repair of the v2 failure)")
    print("R8 stays ON. This repairs the v2 failure: the v1 entry was")
    print("present in app.json but its extraProguardRules list was")
    print("missing, so v2 had nothing to append to. This patch prints")
    print("the exact entry it finds and brings it to all 15 rules")
    print("(the v1 7 + the v2 8), whatever form it is in now.")
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
        print("ADMOB_R8_KEEP_RULES_V2_1_FAIL: app.json section failed, see WARNINGs above")
        return 1
    print("ADMOB_R8_KEEP_RULES_V2_1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
