#!/usr/bin/env python3
"""Directly add the AdMob APPLICATION_ID meta-data to the committed AndroidManifest.

Why direct: the config plugins (react-native-google-mobile-ads library plugin +
custom withAdMobAppId.js) never applied the tag -- the committed manifest at
commit 75d3124c contains ZERO APPLICATION_ID entries, so the Emergent build is
evidently using this committed android/ directory as-is (or prebuild is not
applying plugins). This patch edits the manifest file itself, bypassing
config plugins entirely.

Idempotent: SKIP if an APPLICATION_ID meta-data is already present (any value).
WARNING + SKIP if the file or the anchor is not found exactly once -- never
forces the edit. Validates the result as well-formed XML before writing.

Run from /app:
  python3 frontend/patch-admob-manifest-direct.py
"""
import sys
import xml.etree.ElementTree as ET

MANIFEST = "frontend/android/app/src/main/AndroidManifest.xml"
APP_ID = "ca-app-pub-1342550857186673~4649429004"
ADMOB_META = (
    '    <meta-data android:name="com.google.android.gms.ads.APPLICATION_ID" '
    'android:value="%s"/>' % APP_ID
)
# Anchor A (preferred): last expo.modules.updates meta-data line. Insert the
# AdMob tag right after it, keeping all meta-data together at the top of
# <application>. This line is stable and unique in the committed manifest.
ANCHOR_LAST_EXPO_META = (
    '    <meta-data android:name="expo.modules.updates.EXPO_UPDATES_LAUNCH_WAIT_MS" '
    'android:value="0"/>'
)
# Anchor B (fallback): the <application ...> opening line, matched by its
# unique android:name. Insert right after that line.
ANCHOR_APP_NAME = 'android:name=".MainApplication"'
ALREADY_PRESENT = 'android:name="com.google.android.gms.ads.APPLICATION_ID"'
MARKER = "ADMOB_MANIFEST_DIRECT_OK"


def main():
    try:
        with open(MANIFEST, "r", encoding="utf-8") as f:
            text = f.read()
    except FileNotFoundError:
        print("WARNING: manifest not found at %s -- skipping (file may not exist in this copy)" % MANIFEST)
        print(MARKER)
        return 0
    except OSError as e:
        print("WARNING: could not read %s (%s) -- skipping" % (MANIFEST, e))
        print(MARKER)
        return 0

    if ALREADY_PRESENT in text:
        print("SKIP: APPLICATION_ID meta-data already present in %s -- nothing to add" % MANIFEST)
        print(MARKER)
        return 0

    new_text = None
    anchor_used = None

    # Anchor A: insert right after the last expo.modules.updates meta-data line.
    if text.count(ANCHOR_LAST_EXPO_META) == 1:
        new_text = text.replace(
            ANCHOR_LAST_EXPO_META,
            ANCHOR_LAST_EXPO_META + "\n" + ADMOB_META,
            1,
        )
        anchor_used = "last expo.modules.updates meta-data line"
    else:
        if text.count(ANCHOR_LAST_EXPO_META) == 0:
            print("WARNING: anchor A not found (last expo meta-data line missing) -- trying fallback anchor")
        else:
            print("WARNING: anchor A found %d times (expected exactly 1) -- trying fallback anchor"
                  % text.count(ANCHOR_LAST_EXPO_META))

        # Anchor B: insert right after the <application ...> opening line.
        app_lines = [ln for ln in text.split("\n")
                     if "<application" in ln and ANCHOR_APP_NAME in ln]
        if len(app_lines) == 1:
            app_line = app_lines[0]
            new_text = text.replace(app_line, app_line + "\n" + ADMOB_META, 1)
            anchor_used = "<application> opening line"
        else:
            print("WARNING: <application> opening line found %d times (expected exactly 1) -- skipping, no change made"
                  % len(app_lines))
            print(MARKER)
            return 0

    # Validate the result is still well-formed XML before writing anything.
    try:
        ET.fromstring(new_text)
    except ET.ParseError as e:
        print("WARNING: edited manifest is not well-formed XML (%s) -- skipping, no change made" % e)
        print(MARKER)
        return 0

    if new_text.count(ALREADY_PRESENT) != 1:
        print("WARNING: after edit the tag appears %d times (expected exactly 1) -- skipping, no change made"
              % new_text.count(ALREADY_PRESENT))
        print(MARKER)
        return 0

    with open(MANIFEST, "w", encoding="utf-8") as f:
        f.write(new_text)

    print("OK: added AdMob APPLICATION_ID meta-data to %s (inserted after %s)" % (MANIFEST, anchor_used))
    print("OK: App ID is %s" % APP_ID)
    print("NOTE: AdMob can now start without the 'Missing application ID' crash. "
          "The new AAB must be versionCode 168 or higher before upload -- Play has 166 live "
          "and the re-add build that crashed was 167.")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
