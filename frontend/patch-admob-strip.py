#!/usr/bin/env python3
"""Strip react-native-google-mobile-ads (AdMob) from Street Legends frontend.

Build 165 crashes on launch (splash flashes, app closes immediately) after
the AdMob native module was added; the previous build (162) opened fine.
Same failure mode as the Board Games AdMob crash: the native ads SDK breaks
the app at startup. This patch removes the native module so the app can
open again:
  - Section 1: removes "react-native-google-mobile-ads" from
    frontend/package.json dependencies (any version string).
  - Section 2: removes the react-native-google-mobile-ads config plugin
    entry from frontend/app.json plugins.
  - Section 3 (read-only check): confirms AdMobAds.tsx loads the module
    through a guarded require() inside try/catch, so the component and its
    mounts can stay — with the package gone they render nothing.

Left in place on purpose (harmless without the package):
  - frontend/components/AdMobAds.tsx + mounts in app/_layout.tsx and
    app/(tabs)/shop.tsx (guarded require, verified in
    patch-admob-banner-rewarded.py).
  - backend POST /api/ads/rewarded-grant (untouched).
  - The AdMob App ID / ad unit IDs in AdMob (unchanged; re-adding ads
    later is just the reverse of this patch).

Run from /app in the Emergent terminal. Idempotent: re-running prints
SKIP for every section. A section that cannot find its anchor prints
WARNING and is skipped — never forced.
"""

import json
import re
import sys
from pathlib import Path

MARKER = "ADMOB_STRIP_OK"
ROOT = Path("frontend")
PKG_NAME = "react-native-google-mobile-ads"


def strip_dep(text):
    """Remove the AdMob dep line from package.json text.

    Returns (new_text, status) with status 'ok' | 'skip' | 'warn'.
    Handles any version string, with or without a trailing comma.
    """
    if PKG_NAME not in text:
        return text, "skip"
    pat = re.compile(
        r'^[ \t]*"' + re.escape(PKG_NAME) + r'"[ \t]*:[ \t]*"[^"]*"[ \t]*,?[ \t]*\r?\n',
        re.MULTILINE,
    )
    matches = list(pat.finditer(text))
    if len(matches) != 1:
        return text, "warn"
    edited = text[: matches[0].start()] + text[matches[0].end() :]
    try:
        json.loads(edited)
        return edited, "ok"
    except json.JSONDecodeError:
        pass
    # The removed line may have been the last dep: the preceding line now
    # has a dangling comma before the closing brace. Drop exactly that
    # comma (located positionally at the removal point) and retry.
    pos = matches[0].start()
    j = pos - 1
    while j >= 0 and edited[j] in " \t\r\n":
        j -= 1
    if j >= 0 and edited[j] == ",":
        k = j + 1
        while k < len(edited) and edited[k] in " \t\r\n":
            k += 1
        if k < len(edited) and edited[k] == "}":
            repaired = edited[:j] + edited[j + 1 :]
            try:
                json.loads(repaired)
                return repaired, "ok"
            except json.JSONDecodeError:
                pass
    return text, "warn"


def strip_plugin(text):
    """Remove the AdMob config plugin entry from app.json text.

    Returns (new_text, status) with status 'ok' | 'skip' | 'warn'.
    Tries, in order: array form as last entry (the form the install patch
    wrote), array form mid-list, bare-string form last, bare-string mid.
    """
    if PKG_NAME not in text:
        return text, "skip"
    array_body = (
        r'[ \t]*\[[ \t]*\r?\n[ \t]*"' + re.escape(PKG_NAME) + r'"[ \t]*,[ \t]*\r?\n'
        r'[ \t]*\{[ \t]*\r?\n[ \t]*"androidAppId"[ \t]*:[ \t]*"[^"]*"[ \t]*\r?\n'
        r'[ \t]*\}[ \t]*\r?\n[ \t]*\]'
    )
    patterns = [
        # Array form, last plugin entry (leading comma) — the installed form.
        re.compile(r',[ \t]*\r?\n' + array_body),
        # Array form, mid-list (trailing comma).
        re.compile(array_body + r'[ \t]*,[ \t]*\r?\n'),
        # Bare string form, last entry.
        re.compile(r',[ \t]*\r?\n[ \t]*"' + re.escape(PKG_NAME) + r'"[ \t]*'),
        # Bare string form, mid-list.
        re.compile(r'[ \t]*"' + re.escape(PKG_NAME) + r'"[ \t]*,[ \t]*\r?\n'),
    ]
    for pat in patterns:
        matches = list(pat.finditer(text))
        if len(matches) == 1:
            edited = text[: matches[0].start()] + text[matches[0].end() :]
            try:
                json.loads(edited)
                return edited, "ok"
            except json.JSONDecodeError:
                continue
    return text, "warn"


def check_component(path):
    """Read-only check: AdMobAds.tsx must load the module through a guarded
    require(), never a top-level import. Returns a status line to print."""
    if not path.exists():
        return "INFO: components/AdMobAds.tsx not found in /app (nothing to check)"
    text = path.read_text()
    if re.search(
        r"^\s*import\b[^\n]*['\"]" + re.escape(PKG_NAME) + r"['\"]",
        text,
        re.MULTILINE,
    ):
        return (
            "WARNING: AdMobAds.tsx uses a TOP-LEVEL import of "
            + PKG_NAME
            + " — its mounts must be stubbed/removed before building; "
            + "this patch does NOT fix that"
        )
    if "require('" + PKG_NAME + "')" in text or 'require("' + PKG_NAME + '")' in text:
        return "OK: AdMobAds.tsx uses guarded require — component/mounts left in place (render nothing)"
    return "WARNING: AdMobAds.tsx load pattern unrecognized — check mounts before building"


def edit_file(path, strip_fn, label):
    if not path.exists():
        print(f"ERROR: {path} not found. Run from /app.")
        sys.exit(1)
    text = path.read_text()
    new_text, status = strip_fn(text)
    if status == "skip":
        print(f"SKIP: {label} (already gone)")
    elif status == "warn":
        print(f"WARNING: {label} anchor not found or edit would break JSON — skipped")
    else:
        path.write_text(new_text)
        print(f"OK: {label}")


def main():
    edit_file(ROOT / "package.json", strip_dep, "package.json AdMob dep removed")
    edit_file(ROOT / "app.json", strip_plugin, "app.json AdMob plugin removed")
    print(check_component(ROOT / "components" / "AdMobAds.tsx"))
    print(MARKER)


if __name__ == "__main__":
    main()
