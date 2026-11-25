#!/usr/bin/env python3
"""Revert the direct AdMob APPLICATION_ID manifest edit and the custom
withAdMobAppId.js plugin, leaving the react-native-google-mobile-ads library
config plugin as the SINGLE source of the APPLICATION_ID meta-data tag.

Why: the EAS build (1afd6071-e496-4b6e-b0e8-90e2f4f9aede) runs prebuild, so
the library config plugin ALSO adds the APPLICATION_ID tag. The direct edit
(frontend/patch-admob-manifest-direct.py, commit e13c98b7) put a second
identical tag in the committed AndroidManifest.xml (line 32), and the
manifest merger refused to build:
  "Manifest merger failed : Attribute
   meta-data#com.google.android.gms.ads.APPLICATION_ID@value
   value=(ca-app-pub-1342550857186673~4649429004) from
   AndroidManifest.xml:32:73-127"
Removing the direct tag (and the custom plugin that duplicates the library
plugin) leaves exactly one source of the tag.

Sections:
  1. AndroidManifest.xml — remove the one APPLICATION_ID meta-data line
     the direct patch added (right after the expo.modules.updates
     meta-data lines). SKIP if absent; WARNING + SKIP if the tag appears
     more than once or is not the expected line (never delete blindly).
  2. app.json — remove the "./plugins/withAdMobAppId.js" entry from
     plugins. The library plugin (with androidAppId) stays. SKIP if
     absent; WARNING + SKIP if present in an unexpected form.
  3. Delete frontend/plugins/withAdMobAppId.js (dead code once
     unregistered). SKIP if already absent.
  4. (No-op) package.json, AdMobAds.tsx (Google test IDs stay), and the
     backend are untouched.

Idempotent: re-running prints SKIP for every section + the marker.
Run from /app: python3 frontend/patch-admob-manifest-revert.py
"""

import json
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path

MANIFEST = Path("frontend/android/app/src/main/AndroidManifest.xml")
APP_JSON = Path("frontend/app.json")
PLUGIN_FILE = Path("frontend/plugins/withAdMobAppId.js")
APP_ID = "ca-app-pub-1342550857186673~4649429004"
CUSTOM_PLUGIN = "./plugins/withAdMobAppId.js"
TAG_MARKER = 'android:name="com.google.android.gms.ads.APPLICATION_ID"'
# Exact line the direct patch wrote (4-space indent, single line).
TAG_LINE = (
    '    <meta-data android:name="com.google.android.gms.ads.APPLICATION_ID" '
    'android:value="%s"/>' % APP_ID
)


def section_manifest(path):
    """Remove the direct-edit APPLICATION_ID meta-data line."""
    if not path.exists():
        print("WARNING: %s not found in /app — manifest tag NOT removed" % path)
        return
    text = path.read_text()
    count = text.count(TAG_MARKER)
    if count == 0:
        print("SKIP: no APPLICATION_ID meta-data in %s — nothing to remove" % path)
        return
    if count > 1:
        print(
            "WARNING: %d APPLICATION_ID meta-data entries in %s — NOT deleting "
            "blindly; remove the duplicate by hand and re-run" % (count, path)
        )
        return
    # Exactly one. Require it to be the direct-patch line on its own line.
    lines = text.split("\n")
    idx = None
    for i, line in enumerate(lines):
        if TAG_MARKER in line:
            idx = i
            break
    if idx is None:
        print("WARNING: marker counted but no line contains it — nothing removed")
        return
    if lines[idx] != TAG_LINE:
        print(
            "WARNING: APPLICATION_ID line is not the expected direct-patch line "
            "— NOT removing. Actual line: %r" % lines[idx]
        )
        return
    del lines[idx]
    edited = "\n".join(lines)
    # Validate well-formed XML before writing.
    try:
        ET.fromstring(edited)
    except ET.ParseError as e:
        print(
            "WARNING: manifest would not parse as XML after removal (%s) — skipped"
            % e
        )
        return
    if TAG_MARKER in edited:
        print("WARNING: APPLICATION_ID still present after removal — skipped")
        return
    path.write_text(edited)
    print(
        "OK: removed AdMob APPLICATION_ID meta-data line from %s (was line %d)"
        % (path, idx + 1)
    )


def section_appjson(path):
    """Remove the custom plugin entry from app.json plugins."""
    if not path.exists():
        print("WARNING: %s not found in /app — custom plugin entry NOT removed" % path)
        return
    text = path.read_text()
    n = text.count(CUSTOM_PLUGIN)
    if n == 0:
        print(
            "SKIP: custom plugin %s not in %s — nothing to remove"
            % (CUSTOM_PLUGIN, path)
        )
        return
    if n > 1:
        print(
            "WARNING: custom plugin %s appears %d times in %s — NOT removing; "
            "clean up by hand and re-run" % (CUSTOM_PLUGIN, n, path)
        )
        return
    edited = None
    form = None
    # Form A: custom entry is the last plugins entry (the form the re-add
    # patch writes when the library block is last). Remove the comma after
    # the previous entry plus the custom-entry line.
    form_a_old = ',\n      "%s"\n    ],' % CUSTOM_PLUGIN
    if text.count(form_a_old) == 1:
        edited = text.replace(form_a_old, "\n    ],", 1)
        form = "last entry"
    else:
        # Form B: custom entry is mid-list (trailing comma).
        form_b_old = '      "%s",\n' % CUSTOM_PLUGIN
        if text.count(form_b_old) == 1:
            edited = text.replace(form_b_old, "", 1)
            form = "mid-list"
        else:
            # Form C: whitespace-tolerant last-entry removal.
            m = re.search(
                r",[ \t]*\n[ \t]*\""
                + re.escape(CUSTOM_PLUGIN)
                + r'"[ \t]*\n([ \t]*\],)',
                text,
            )
            if m:
                edited = text[: m.start()] + "\n" + m.group(1) + text[m.end() :]
                form = "last entry (whitespace-tolerant)"
            else:
                # Form D: whitespace-tolerant mid-list removal.
                m = re.search(
                    r"[ \t]*\""
                    + re.escape(CUSTOM_PLUGIN)
                    + r'"[ \t]*,[ \t]*\n',
                    text,
                )
                if m:
                    edited = text[: m.start()] + text[m.end() :]
                    form = "mid-list (whitespace-tolerant)"
    if edited is None:
        print(
            "WARNING: custom plugin entry present in %s but in an unexpected "
            "form — NOT removing; edit by hand" % path
        )
        return
    try:
        json.loads(edited)
    except json.JSONDecodeError as e:
        print("WARNING: app.json edit would break JSON (%s) — skipped" % e)
        return
    # Guard: the library plugin must survive the edit.
    if "react-native-google-mobile-ads" not in edited or "androidAppId" not in edited:
        print("WARNING: library plugin missing after edit — skipped")
        return
    if CUSTOM_PLUGIN in edited:
        print("WARNING: custom plugin still present after edit — skipped")
        return
    path.write_text(edited)
    print(
        "OK: removed custom plugin %s from %s plugins (%s form); "
        "library plugin kept" % (CUSTOM_PLUGIN, path, form)
    )


def section_delete_plugin(path):
    """Delete the custom plugin file (dead code once unregistered)."""
    if not path.exists():
        print("SKIP: %s already absent — nothing to delete" % path)
        return
    try:
        os.remove(path)
    except OSError as e:
        print("WARNING: could not delete %s (%s)" % (path, e))
        return
    print("OK: deleted %s" % path)


def main():
    section_manifest(MANIFEST)
    section_appjson(APP_JSON)
    section_delete_plugin(PLUGIN_FILE)
    print(
        "NOTE: the react-native-google-mobile-ads library plugin "
        "(androidAppId %s) is now the SINGLE source of the APPLICATION_ID "
        "tag. The next successful AAB must be 170+ (Play has 166 live; the "
        "failed builds produced no AAB) — Emergent auto-bumps, but verify "
        "before upload." % APP_ID
    )
    print("ADMOB_MANIFEST_REVERT_OK")


if __name__ == "__main__":
    main()
