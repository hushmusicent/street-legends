#!/usr/bin/env python3
"""Street Legends blank-map diag (READ-ONLY).

Symptom: the game loads (player card, cash, footer coords, tab bar all
render) but the map area is completely blank white - no tiles, no
markers, no Leaflet zoom buttons. The native overlays (center button,
info bar) DO render, location resolved to live GPS, entities loaded.

The map is Leaflet inside a react-native-webview. Its inline <script>
lives inside a TSX template literal, so NO check so far has ever parsed
it: eslint checks TSX syntax, not JS inside template literals, and the
in-patch lint could not even run (no eslint config in the project). A
syntax error in that inline script kills the whole script - L.map never
runs, no tiles, no zoom controls - while the native overlays render
fine. That is exactly this symptom.

This script extracts the inline <script> block(s) from the LIVE
frontend/components/GameMap.tsx, substitutes the TSX ${...}
placeholders with dummy values, and syntax-checks the resulting JS
with node --check (compile only, nothing executes). It writes nothing.
Run: python3 minigame-diag/diag-map-blank.py [/app]
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
MARKER = "MAP_BLANK_DIAG_OK"

GAMEMAP = ROOT / "frontend/components/GameMap.tsx"
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"

failed = []  # names of failed checks, for the verdict


def check(name, ok, note=""):
    print("  %-38s %s%s" % (name, "FOUND" if ok else "MISSING",
                            (" (" + note + ")") if note else ""))
    if not ok:
        failed.append(name)
    return ok


def fsize(p):
    try:
        st = p.stat()
        import datetime
        return "%d bytes %s" % (st.st_size,
                                datetime.datetime.fromtimestamp(
                                    st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
    except OSError:
        return "NOT FOUND"


def balance_scan(code):
    """Fallback when node is absent: bracket/backtick balance with the
    first imbalance line. Heuristic only - never claims a pass is proof."""
    stack = []  # (char, line)
    pairs = {")": "(", "}": "{", "]": "["}
    in_str = None  # ', ", or ` currently open (single-line tracking)
    esc = False
    for ln, line in enumerate(code.split("\n"), 1):
        i = 0
        while i < len(line):
            ch = line[i]
            if esc:
                esc = False
                i += 1
                continue
            if ch == "\\":
                esc = True
                i += 1
                continue
            if in_str:
                if ch == in_str:
                    in_str = None
                i += 1
                continue
            if ch in ("'", '"', "`"):
                in_str = ch
            elif ch in "({[":
                stack.append((ch, ln))
            elif ch in ")}]":
                if not stack or stack[-1][0] != pairs[ch]:
                    return (False, ln, "unmatched %r (stack top %s)" %
                            (ch, stack[-1] if stack else "empty"))
                stack.pop()
            i += 1
        # a string left open across lines is normal for ` template literals
        # only; single/double quotes spanning lines is an error in JS
        if in_str in ("'", '"'):
            return (False, ln, "unterminated %s string" % in_str)
        if in_str == "`":
            pass  # template literal continues; keep tracking below
    if stack:
        return (False, stack[-1][1],
                "unclosed %r opened here" % stack[-1][0])
    if in_str == "`":
        return (False, len(code.split("\n")), "unterminated template literal")
    return (True, None, "balanced")


def main():
    print("=== files (size + mtime) ===")
    print("  frontend/components/GameMap.tsx  %s" % fsize(GAMEMAP))
    print("  frontend/app/(tabs)/index.tsx    %s" % fsize(INDEX))
    print()

    if not GAMEMAP.exists():
        print("ERROR: GameMap.tsx not found - cannot check the map")
        print("=== verdict ===")
        print("%s missing=1" % MARKER)
        print("FAILED CHECKS:")
        print("  - gamemap-file-missing")
        return 0

    gsrc = GAMEMAP.read_text(errors="ignore")
    isrc = INDEX.read_text(errors="ignore") if INDEX.exists() else ""

    print("=== inline <script> extraction ===")
    # Find all <script> tags; keep only ones with inline content
    # (the Leaflet CDN tag has src= and empty content - skip it).
    blocks = []
    for m in re.finditer(r"<script(?:\s[^>]*)?>(.*?)</script>", gsrc, re.S):
        body = m.group(1)
        if body.strip():
            # line number of the opening <script> in the TSX file
            open_line = gsrc[:m.start()].count("\n") + 1
            blocks.append((open_line, body))
    if not blocks:
        print("  script-block  MISSING - no inline <script>...</script> found")
        failed.append("script-block")
    else:
        for i, (ln, body) in enumerate(blocks):
            print("  script-block #%d  FOUND (%d lines, <script> at GameMap.tsx:%d)"
                  % (i, body.count("\n") + 1, ln))
    print()

    print("=== script syntax check (node --check, compile only) ===")
    syntax_ok = None
    syntax_err = ""
    syntax_line = None  # line inside the script block
    syntax_file_line = None  # line in GameMap.tsx
    if blocks:
        open_line, raw = blocks[0]
        code = raw
        # Drop the single newline right after <script> so node line
        # numbers map exactly: code line N == GameMap.tsx line
        # (open_line + N).
        if code.startswith("\n"):
            code = code[1:]
        # Substitute the TSX ${...} placeholders with dummy values so
        # node sees plain JS. These are the only three in the script.
        code = code.replace("${initialLat}", "41.62462")
        code = code.replace("${initialLng}", "-83.61658")
        code = code.replace("${enemyImagesJSON}", "{}")
        leftovers = sorted(set(re.findall(r"\$\{[^}]+\}", code)))
        if leftovers:
            print("  NOTE: unknown placeholders left, replaced with 0: %s"
                  % ", ".join(leftovers))
            code = re.sub(r"\$\{[^}]+\}", "0", code)
        node = None
        for cand in ("node", "/usr/bin/node", "/usr/local/bin/node"):
            try:
                r = subprocess.run([cand, "--version"],
                                   capture_output=True, text=True, timeout=10)
                if r.returncode == 0:
                    node = cand
                    break
            except OSError:
                continue
        if node:
            print("  node: %s" % node)
            tmp = None
            try:
                fd, tmp = tempfile.mkstemp(suffix=".js", prefix="mapblank-")
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    f.write(code)
                r = subprocess.run([node, "--check", tmp],
                                   capture_output=True, text=True, timeout=30)
                err = (r.stderr or r.stdout or "").strip()
                if r.returncode == 0:
                    syntax_ok = True
                    print("  script-syntax  PASS (node --check clean)")
                else:
                    syntax_ok = False
                    failed.append("script-syntax")
                    # node prints: /tmp/x.js:<line>\n <source>\n ^\n\nSyntaxError: ...
                    mline = re.search(r":(\d+)\s*$", err.split("\n")[0]) \
                        if err else None
                    mmsg = re.search(r"SyntaxError:.*", err)
                    syntax_err = mmsg.group(0) if mmsg else err.split("\n")[0]
                    if mline:
                        syntax_line = int(mline.group(1))
                        # script body starts the line after <script>
                        syntax_file_line = open_line + syntax_line
                    print("  script-syntax  FAIL")
                    print("    node error: %s" % syntax_err)
                    if syntax_line:
                        print("    script line: %d (GameMap.tsx line ~%d)"
                              % (syntax_line, syntax_file_line))
                        srclines = code.split("\n")
                        if 1 <= syntax_line <= len(srclines):
                            print("    source: %s"
                                  % srclines[syntax_line - 1].strip()[:200])
            finally:
                if tmp:
                    try:
                        os.unlink(tmp)
                    except OSError:
                        pass
        else:
            print("  node: NOT FOUND on this machine - falling back to "
                  "bracket/backtick balance scan (heuristic only)")
            ok, ln, msg = balance_scan(code)
            syntax_ok = ok
            if ok:
                print("  script-balance  PASS (heuristic - not a real parse)")
            else:
                failed.append("script-syntax")
                syntax_line = ln
                syntax_file_line = open_line + ln if ln else None
                syntax_err = msg
                print("  script-balance  FAIL at script line %s: %s"
                      % (ln, msg))
    print()

    print("=== CDN / tile URLs in the template ===")
    check("leaflet-css-unpkg",
          "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" in gsrc)
    check("leaflet-js-unpkg",
          "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js" in gsrc)
    check("osm-tile-url",
          "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" in gsrc)
    check("L.map-call", "L.map('map'" in gsrc)
    check("L.tileLayer-call", "L.tileLayer(" in gsrc)
    print()

    print("=== WebView props (native side) ===")
    check("webview-javaScriptEnabled", "javaScriptEnabled" in gsrc)
    check("webview-originWhitelist", "originWhitelist" in gsrc)
    check("webview-source-html", "source={{ html: mapHTML }}" in gsrc
          or "source={{html: mapHTML}}" in gsrc
          or "source={{ html" in gsrc)
    check("webview-startInLoadingState", "startInLoadingState" in gsrc)
    check("webview-renderLoading", "renderLoading" in gsrc)
    check("webview-onError", "onError" in gsrc)
    check("map-container-flex", "flex: 1" in gsrc)
    check("generateBaseMapHTML", "generateBaseMapHTML" in gsrc)
    print()

    print("=== activityCenter marker code (v2 patch + repair) ===")
    check("marker-branch-activityCenter",
          "m.type === 'activityCenter'" in gsrc)
    check("marker-color-activityCenter",
          "activityCenter: '#7b1fa2'" in gsrc)
    check("marker-icon-activityCenter",
          "activityCenter: '🎮'" in gsrc)
    check("isLocationMarker-activityCenter",
          "m.type === 'activityCenter'" in gsrc
          and "isLocationMarker" in gsrc)
    # Known corruption signature: the white-screen repair patch used a
    # [^}]* regex on markerIcons, which stops at the } inside the FIRST
    # \u{...} escape ('\\u{1F480}'), inserting the activityCenter entry
    # INSIDE the monster string literal and breaking the whole script.
    # Correct text is: monster: '\\u{1F480}', activityCenter: '🎮'
    # Corrupt text is:  monster: '\\u{1F480, activityCenter: '🎮'}'
    corrupt = bool(re.search(
        r"u\{1F480,\s*activityCenter", gsrc))
    correct = bool(re.search(
        r"u\{1F480\}',\s*activityCenter", gsrc))
    if corrupt:
        print("  markerIcons-corruption  FOUND - activityCenter entry "
              "sits INSIDE the monster '\\u{1F480}' string (repair-patch "
              "[^}]* regex trap)")
        failed.append("markerIcons-corruption")
    elif correct:
        print("  markerIcons-corruption  ABSENT (entry placed correctly "
              "after the monster entry)")
    else:
        print("  markerIcons-corruption  UNKNOWN - neither the corrupt "
              "nor the correct placement pattern found")
    # Same trap class, other direction: any \\u{...} escape makes a
    # [^}]* object regex unsafe; flag it as a standing hazard.
    print("  note: markerIcons contains \\u{...} escapes: %s"
          % ("yes - [^}]* regexes on this object are unsafe"
             if re.search(r"\\u\{[0-9A-Fa-f]+\}", gsrc) else "no"))
    print()

    print("=== index.tsx GameMap usage ===")
    if isrc:
        m = re.search(r"<GameMap([\s\S]*?)/>", isrc)
        if m:
            usage = m.group(1)
            print("  gamemap-usage  FOUND")
            for prop in ("center=", "markers=", "heading=",
                         "playerAvatar=", "territories=",
                         "onMarkerPress=", "onTerritoryPress="):
                print("    %-18s %s" % (prop,
                      "present" if prop in usage else "absent"))
        else:
            print("  gamemap-usage  MISSING - no <GameMap ... /> in index.tsx")
            failed.append("gamemap-usage")
    else:
        print("  index.tsx  NOT FOUND - usage not checked")
    print()

    print("=== verdict ===")
    print("%s missing=%d" % (MARKER, len(failed)))
    if failed:
        print("FAILED CHECKS:")
        for f in failed:
            print("  - " + f)
    if syntax_ok is False:
        print("LIKELY CAUSE: SCRIPT_SYNTAX_FAIL - the inline <script> in "
              "GameMap.tsx does not parse%s%s. Leaflet never initializes, "
              "so no tiles, no markers, no zoom buttons - blank white map "
              "while the native overlays render fine. Fix the script; the "
              "CDN and tiles are not the problem."
              % (" (script line %d, GameMap.tsx ~%d)"
                 % (syntax_line, syntax_file_line) if syntax_line else "",
                 (": " + syntax_err) if syntax_err else ""))
        if "markerIcons-corruption" in failed:
            print("  The break is the markerIcons line: the repair patch's "
                  "[^}]* regex stopped at the } inside '\\u{1F480}' and "
                  "inserted the activityCenter entry inside the monster "
                  "string. Move the entry after the closing quote of the "
                  "monster entry (or rebuild the markerIcons object).")
    elif "script-block" in failed:
        print("LIKELY CAUSE: SCRIPT_MISSING - no inline script found; the "
              "WebView has nothing to run.")
    elif any(f.startswith("leaflet-") or f == "osm-tile-url"
             for f in failed):
        print("LIKELY CAUSE: URLS_MISSING - a Leaflet/tile URL is absent "
              "from the template; check the template, then CDN reachability "
              "from the phone.")
    elif any(f.startswith("webview-") for f in failed):
        print("LIKELY CAUSE: WEBVIEW_PROPS_MISSING - a WebView prop is "
              "absent; the HTML may never load or JS may be off.")
    elif failed:
        print("LIKELY CAUSE: OTHER_CHECKS_FAILED (%s) - script parses, so "
              "if the map is still blank on device, check CDN/tile "
              "reachability from the phone (open "
              "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js in the phone "
              "browser) or a WebView load error."
              % ", ".join(failed))
    else:
        print("LIKELY CAUSE: SCRIPT_OK - the inline script parses and all "
              "URLs/props are present. If the map is still blank on device, "
              "the fault is at runtime on the phone, not in the file: check "
              "CDN/tile reachability from the phone (open "
              "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js in the phone "
              "browser - it should show JS, not an error page), or a "
              "WebView load failure. Zoom buttons visible = Leaflet "
              "initialized; 'Loading map...' stuck = WebView load hanging.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
