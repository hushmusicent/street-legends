#!/usr/bin/env python3
"""Re-add AdMob to Street Legends PROPERLY (v2).

Build 165 crashed on launch (splash flashes, app closes immediately)
after the AdMob native module was added; build 166 (AdMob stripped via
frontend/patch-admob-strip.py, commit a6385a70) opens fine. Google's
AdMob quick-start says a missing APPLICATION_ID <meta-data> tag in
AndroidManifest.xml crashes the app with "Missing application ID" — the
react-native-google-mobile-ads config plugin entry in app.json never
landed that tag in the Emergent build. This patch re-adds AdMob with a
belt-and-suspenders fix so the tag is guaranteed in the manifest:

  Section 1: re-add "react-native-google-mobile-ads": "17.4.0" to
    frontend/package.json dependencies.
  Section 2: re-add the react-native-google-mobile-ads config plugin
    (androidAppId ca-app-pub-1342550857186673~4649429004) to
    frontend/app.json plugins.
  Section 3: create frontend/plugins/withAdMobAppId.js — a custom Expo
    config plugin (withAndroidManifest) that ensures the <application>
    element contains exactly one
    <meta-data android:name="com.google.android.gms.ads.APPLICATION_ID"
    android:value="ca-app-pub-1342550857186673~4649429004"/> — it adds
    the tag only if not already present, so it never duplicates the
    library plugin's tag. Registered in app.json plugins AFTER the
    library plugin so it runs after it. This is the key fix for the
    "Missing application ID" crash.
  Section 4: switch frontend/components/AdMobAds.tsx to Google's TEST
    ad unit IDs (per the banner + rewarded guides): banner
    ca-app-pub-3940256099942544/9214589741, rewarded
    ca-app-pub-3940256099942544/5224354917. Live IDs during testing risk
    account suspension. Everything else in the component is untouched
    (same LARGE_ANCHORED_ADAPTIVE_BANNER size, same "Watch ad - earn
    $1,000" rewarded flow, same guarded require, same
    /ads/rewarded-grant POST on EARNED_REWARD). The LIVE IDs
    (banner .../3539848112, rewarded .../8869991021) must be swapped
    back in for the release build.

Left untouched on purpose:
  - backend POST /api/ads/rewarded-grant (unchanged).
  - expo-notifications (push) — not touched by any section.
  - app.json version / versionCode — NOT bumped here. Play has 166
    live; the new AAB must be 167+ before upload. The Emergent build
    auto-bumped 163 -> 165 last time, but verify the built AAB's
    versionCode before uploading.

Run from /app in the Emergent terminal. Idempotent: re-running prints
SKIP for every section. A section that cannot find its anchor prints
WARNING and is skipped — never forced.
"""

import json
import re
import sys
from pathlib import Path

MARKER = "ADMOB_READD_V2_OK"
ROOT = Path("frontend")
PKG_NAME = "react-native-google-mobile-ads"
APP_ID = "ca-app-pub-1342550857186673~4649429004"
CUSTOM_PLUGIN = "./plugins/withAdMobAppId.js"

LIVE_BANNER = "ca-app-pub-1342550857186673/3539848112"
LIVE_REWARDED = "ca-app-pub-1342550857186673/8869991021"
TEST_BANNER = "ca-app-pub-3940256099942544/9214589741"
TEST_REWARDED = "ca-app-pub-3940256099942544/5224354917"

# ---- Section 3: custom config plugin (written verbatim) ----
PLUGIN_JS = """const { withAndroidManifest } = require('@expo/config-plugins');

const ADMOB_APP_ID = 'ca-app-pub-1342550857186673~4649429004';
const ADMOB_APP_ID_NAME = 'com.google.android.gms.ads.APPLICATION_ID';

/**
 * Belt-and-suspenders fix for the "Missing application ID" startup crash
 * (build 165 flash-closed on launch).
 *
 * Google's AdMob quick-start says a missing APPLICATION_ID <meta-data>
 * tag in AndroidManifest.xml crashes the app with "Missing application
 * ID." The react-native-google-mobile-ads config plugin is supposed to
 * write that tag, but it never landed in the Emergent build, so this
 * plugin guarantees it. It is registered AFTER the library plugin in
 * app.json, so it runs after the library plugin and adds the tag under
 * <application> only if no meta-data with that android:name is already
 * present. It never duplicates the tag, so it is safe on every prebuild.
 */
function withAdMobAppId(config) {
  return withAndroidManifest(config, (config) => {
    const androidManifest = config.modResults;
    const manifest = androidManifest && androidManifest.manifest;
    if (!manifest || !manifest.application || !manifest.application[0]) {
      return config;
    }
    const app = manifest.application[0];
    if (!app['meta-data']) {
      app['meta-data'] = [];
    }
    const metaData = app['meta-data'];
    const exists = metaData.some(
      (m) => m.$ && m.$['android:name'] === ADMOB_APP_ID_NAME
    );
    if (!exists) {
      metaData.push({
        $: {
          'android:name': ADMOB_APP_ID_NAME,
          'android:value': ADMOB_APP_ID,
        },
      });
    }
    return config;
  });
}

module.exports = withAdMobAppId;
"""

# Exact library-plugin block as written by Section 2.
LIB_BLOCK = '''      [
        "react-native-google-mobile-ads",
        {
          "androidAppId": "ca-app-pub-1342550857186673~4649429004"
        }
      ]'''

# Regex for the library-plugin array block in any equivalent form
# (same shape the strip patch handled).
LIB_BLOCK_RE = (
    r'[ \t]*\[[ \t]*\r?\n[ \t]*"' + re.escape(PKG_NAME) + r'"[ \t]*,[ \t]*\r?\n'
    r'[ \t]*\{[ \t]*\r?\n[ \t]*"androidAppId"[ \t]*:[ \t]*"[^"]*"[ \t]*\r?\n'
    r'[ \t]*\}[ \t]*\r?\n[ \t]*\]'
)


def add_dep(path):
    """Section 1: re-add the AdMob dep to package.json."""
    if not path.exists():
        print(f"ERROR: {path} not found. Run from /app.")
        sys.exit(1)
    text = path.read_text()
    if '"' + PKG_NAME + '"' in text:
        print("SKIP: package.json dep (already present)")
        return
    anchor = '    "react-native-iap": "^17.1.0",'
    new = '    "react-native-google-mobile-ads": "17.4.0",\n    "react-native-iap": "^17.1.0",'
    if text.count(anchor) != 1:
        print(f"WARNING: package.json anchor matched {text.count(anchor)}x — dep not added")
        return
    edited = text.replace(anchor, new, 1)
    try:
        json.loads(edited)
    except json.JSONDecodeError as e:
        print(f"WARNING: package.json edit would break JSON ({e}) — not written")
        return
    path.write_text(edited)
    print("OK: package.json dep (react-native-google-mobile-ads 17.4.0)")


def add_lib_plugin(path):
    """Section 2: re-add the library config plugin to app.json."""
    if not path.exists():
        print(f"ERROR: {path} not found. Run from /app.")
        sys.exit(1)
    text = path.read_text()
    if '"' + PKG_NAME + '"' in text:
        print("SKIP: app.json library plugin (already present)")
        return
    anchor = '''      "./plugins/withRemoveMediaPermissions.js",
      "./plugins/withBuildConfig.js"'''
    new = anchor + ",\n" + LIB_BLOCK
    if text.count(anchor) != 1:
        print(f"WARNING: app.json anchor matched {text.count(anchor)}x — library plugin not added")
        return
    edited = text.replace(anchor, new, 1)
    try:
        json.loads(edited)
    except json.JSONDecodeError as e:
        print(f"WARNING: app.json edit would break JSON ({e}) — not written")
        return
    path.write_text(edited)
    print("OK: app.json library plugin (androidAppId " + APP_ID + ")")


def write_custom_plugin(path):
    """Section 3a: write the custom config plugin file (deterministic)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_text() == PLUGIN_JS:
        print("SKIP: plugins/withAdMobAppId.js (already written)")
        return
    path.write_text(PLUGIN_JS)
    print("OK: plugins/withAdMobAppId.js written")


def register_custom_plugin(path):
    """Section 3b: register the custom plugin in app.json, AFTER the
    library plugin entry."""
    if not path.exists():
        print(f"ERROR: {path} not found. Run from /app.")
        sys.exit(1)
    text = path.read_text()
    if CUSTOM_PLUGIN in text:
        print("SKIP: app.json custom plugin (already registered)")
        return
    # Form 1: library plugin block as the last plugins entry (the form
    # Section 2 writes).
    anchor_last = LIB_BLOCK + "\n    ],"
    if text.count(anchor_last) == 1:
        edited = text.replace(
            anchor_last, LIB_BLOCK + ',\n      "' + CUSTOM_PLUGIN + '"\n    ],', 1
        )
        try:
            json.loads(edited)
        except json.JSONDecodeError as e:
            print(f"WARNING: app.json custom plugin edit would break JSON ({e}) — skipped")
            return
        path.write_text(edited)
        print("OK: app.json custom plugin registered (after library plugin)")
        return
    # Form 2: library plugin block mid-list (any equivalent form).
    pat = re.compile(LIB_BLOCK_RE + r'[ \t]*,[ \t]*\r?\n')
    matches = list(pat.finditer(text))
    if len(matches) == 1:
        m = matches[0]
        edited = text[: m.end()] + '      "' + CUSTOM_PLUGIN + '",\n' + text[m.end():]
        try:
            json.loads(edited)
        except json.JSONDecodeError as e:
            print(f"WARNING: app.json custom plugin edit would break JSON ({e}) — skipped")
            return
        path.write_text(edited)
        print("OK: app.json custom plugin registered (after library plugin)")
        return
    print(
        "WARNING: app.json library plugin entry not found in a known form — "
        "custom plugin file was written but NOT registered; add "
        + CUSTOM_PLUGIN
        + " to app.json plugins right after the library plugin entry"
    )


def swap_test_ids(path):
    """Section 4: switch AdMobAds.tsx from live IDs to Google test IDs."""
    if not path.exists():
        print("WARNING: components/AdMobAds.tsx not found in /app — test IDs NOT swapped")
        return
    text = path.read_text()
    # Guard: never touch a component that imports the ads module at top
    # level (the guarded-require component is the only known-good form).
    if re.search(
        r"^\s*import\b[^\n]*['\"]" + re.escape(PKG_NAME) + r"['\"]",
        text,
        re.MULTILINE,
    ):
        print(
            "WARNING: AdMobAds.tsx uses a TOP-LEVEL import of "
            + PKG_NAME
            + " — test IDs NOT swapped"
        )
        return
    if (
        TEST_BANNER in text
        and TEST_REWARDED in text
        and LIVE_BANNER not in text
        and LIVE_REWARDED not in text
    ):
        print("SKIP: AdMobAds.tsx test IDs (already applied)")
        return
    if text.count(LIVE_BANNER) != 1 or text.count(LIVE_REWARDED) != 1:
        print(
            f"WARNING: AdMobAds.tsx live IDs found banner={text.count(LIVE_BANNER)}x "
            f"rewarded={text.count(LIVE_REWARDED)}x — expected 1x each; test IDs NOT swapped"
        )
        return
    edited = text.replace(LIVE_BANNER, TEST_BANNER).replace(LIVE_REWARDED, TEST_REWARDED)
    old_comment = "// AdMob unit IDs for Street Legends (production - never test IDs)."
    new_comment = (
        "// AdMob unit IDs for Street Legends — GOOGLE TEST IDs while testing "
        "(swap in the live IDs for the release build)."
    )
    if old_comment in edited:
        edited = edited.replace(old_comment, new_comment)
    path.write_text(edited)
    if "require('" + PKG_NAME + "')" in edited or 'require("' + PKG_NAME + '")' in edited:
        print("OK: AdMobAds.tsx test IDs (banner + rewarded, guarded require intact)")
    else:
        print("OK: AdMobAds.tsx test IDs (banner + rewarded) — NOTE: guarded require pattern not found, check the component")


def print_notes():
    """Informational notes: test IDs + versionCode. The test-ID note is
    state-aware: it only claims the test IDs are in use when they are
    actually present in AdMobAds.tsx."""
    comp_path = ROOT / "components" / "AdMobAds.tsx"
    test_ids_live = False
    if comp_path.exists():
        comp = comp_path.read_text()
        test_ids_live = TEST_BANNER in comp and TEST_REWARDED in comp
    if test_ids_live:
        print(
            "NOTE: AdMobAds.tsx now uses Google TEST ad unit IDs "
            "(banner " + TEST_BANNER + ", rewarded " + TEST_REWARDED + "). "
            "Swap the LIVE IDs back in (banner " + LIVE_BANNER + ", rewarded "
            + LIVE_REWARDED + ") for the release build."
        )
    else:
        print(
            "NOTE: AdMobAds.tsx does NOT have the Google TEST ad unit IDs "
            "in place (see the Section 4 WARNING above) — check the "
            "component before building; live IDs must still be swapped "
            "back in for the release build."
        )
    try:
        appjson = json.loads((ROOT / "app.json").read_text())
        version = appjson.get("expo", {}).get("version", "?")
        vc = appjson.get("expo", {}).get("android", {}).get("versionCode", "?")
        print(
            f"INFO: app.json version={version} versionCode={vc} — Play has 166 live; "
            "the new AAB must be 167+ before upload (Emergent auto-bumped it last "
            "time — verify the built AAB)."
        )
    except Exception:
        print(
            "INFO: could not read app.json version/versionCode — Play has 166 live; "
            "the new AAB must be 167+ before upload."
        )


def main():
    add_dep(ROOT / "package.json")
    add_lib_plugin(ROOT / "app.json")
    write_custom_plugin(ROOT / "plugins" / "withAdMobAppId.js")
    register_custom_plugin(ROOT / "app.json")
    swap_test_ids(ROOT / "components" / "AdMobAds.tsx")
    print_notes()
    print(MARKER)


if __name__ == "__main__":
    main()
