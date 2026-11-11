#!/usr/bin/env python3
"""Street Legends FRONTEND-ONLY map-icons fix (Expo Go).

Root cause (found by simulation on the snapshot tree, to be confirmed
live by minigame-diag/diag-map-blank.py): the white-screen repair patch
(frontend/patch-white-screen-repair.py) broke the map's inline script.
Its GameMap edit used a [^}]* regex on the markerIcons object, which
stopped at the first } character - inside the first unicode escape,
monster: '\\u{1F480}' (the file stores these escapes double-backslashed,
so the } is a literal file character). It inserted
, activityCenter: '🎮' INSIDE the monster string literal, producing:

  var markerIcons = { monster: '\\u{1F480, activityCenter: '🎮'}', mission: ...

a JS SyntaxError ("Invalid or unexpected token") at the markerIcons
line. The inline <script> in the WebView never parses, so L.map never
runs: blank white map, no tiles, no zoom buttons, native overlays fine.
Re-running the repair will NOT fix this - its ALREADY_APPLIED check
sees activityCenter present and skips. This patch restores that one
line only.

This patch touches frontend/components/GameMap.tsx only. It NEVER
uses a [^}]* regex on the markerIcons object: the corruption is
matched on its exact text, and the result is verified by extracting
the inline <script> block and running node --check on it (compile
only, nothing executes). If the script does NOT parse after the fix,
nothing is written. Idempotent: a second run prints ALREADY_APPLIED
and leaves the file byte-identical.
Run: cd /app && python3 frontend/patch-map-icons-fix.py
"""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
GAMEMAP = ROOT / "frontend/components/GameMap.tsx"
MARKER = "MAP_ICONS_FIX_OK"

# Corruption signature (raw file text; the file stores the escape
# double-backslashed, so match 1-3 backslashes and preserve the run):
#   monster: '\\u{1F480, activityCenter: '🎮'}'
# Correct form:
#   monster: '\\u{1F480}', activityCenter: '🎮'
# NOTE: no [^}]* regex is USED on this object anywhere in this file -
# the \\u{...} escapes make that pattern unsafe here. ([^}]* is only
# mentioned in the prose above, never in a pattern.)
CORRUPT_RE = re.compile(
    r"monster:\s*(['\"])(\\{1,3})u\{1F480,\s*activityCenter:\s*['\"]🎮['\"]\}(\1)")
# A properly closed monster entry, whatever follows it.
CORRECT_MONSTER_RE = re.compile(
    r"monster:\s*(['\"])(\\{1,3})u\{1F480\}\1")
# The icon entry as its own object entry.
ICON_ENTRY_RE = re.compile(r"activityCenter:\s*['\"]🎮['\"]")
COLOR_ENTRY = "activityCenter: '#7b1fa2'"
BRANCH_ANCHOR = "m.type === 'activityCenter'"

SCRIPT_RE = re.compile(r"<script(?:\s[^>]*)?>(.*?)</script>", re.S)
PLACEHOLDER_RE = re.compile(r"\$\{[A-Za-z0-9_]+\}")


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"),
            s.count("[") - s.count("]"), s.count("`") % 2)


def find_node():
    for cand in ("node", "/usr/bin/node", "/usr/local/bin/node"):
        try:
            r = subprocess.run([cand, "--version"],
                               capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                return cand
        except OSError:
            continue
    return None


def extract_script(src):
    """First non-empty inline <script> block, same as diag-map-blank.py."""
    for m in SCRIPT_RE.finditer(src):
        body = m.group(1)
        if body.strip():
            open_line = src[:m.start()].count("\n") + 1
            return open_line, body
    return None, None


def substitute_placeholders(code):
    code = code.replace("${initialLat}", "41.62462")
    code = code.replace("${initialLng}", "-83.61658")
    code = code.replace("${enemyImagesJSON}", "{}")
    leftovers = sorted(set(PLACEHOLDER_RE.findall(code)))
    if leftovers:
        print("  NOTE: unknown placeholders left, replaced with 0: %s"
              % ", ".join(leftovers))
        code = PLACEHOLDER_RE.sub("0", code)
    return code


def node_check(code):
    """Returns (ok, error_text). Compile only, nothing executes."""
    node = find_node()
    if not node:
        return None, "node not available"
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(suffix=".js", prefix="mapicons-")
        with open(fd, "w", encoding="utf-8") as f:
            f.write(code)
        r = subprocess.run([node, "--check", tmp],
                           capture_output=True, text=True, timeout=30)
        err = (r.stderr or r.stdout or "").strip()
        if r.returncode == 0:
            return True, ""
        mmsg = re.search(r"SyntaxError:.*", err)
        return False, (mmsg.group(0) if mmsg else err.split("\n")[0])
    except OSError as e:
        return None, "node --check could not run: %s" % e
    finally:
        if tmp:
            try:
                Path(tmp).unlink()
            except OSError:
                pass


def balance_scan(code):
    """Fallback when node is absent: bracket/backtick balance only."""
    d = delta(code)
    return d == (0, 0, 0, 0), "delta=%s" % (d,)


def main():
    if not GAMEMAP.exists():
        print("WARNING: components/GameMap.tsx not found - "
              "markerIcons line NOT fixed (searched for frontend/components/GameMap.tsx)")
        return 1

    src = GAMEMAP.read_text(errors="ignore")
    orig = src
    odelta = delta(src)

    # --- Locate the markerIcons statement (single line in this file) ---
    lines = src.split("\n")
    stmt_idx = None
    for i, line in enumerate(lines):
        if "markerIcons" in line and "=" in line and "{" in line:
            stmt_idx = i
            break
    if stmt_idx is None:
        print("WARNING: markerIcons object not found in GameMap.tsx - "
              "markerIcons line NOT fixed (searched for a line containing "
              "'markerIcons', '=' and '{')")
        return 1

    stmt = lines[stmt_idx]
    new_stmt = None
    mode = None

    m = CORRUPT_RE.search(stmt)
    if m:
        # Restore: close the monster string, then the icon as its own entry.
        q = m.group(1)
        bs = m.group(2)
        fixed = ("monster: " + q + bs + "u{1F480}" + q
                 + ", activityCenter: '🎮'")
        new_stmt = stmt[:m.start()] + fixed + stmt[m.end():]
        mode = "corrupt"
        print("BEFORE: %s" % stmt.strip())
        print("AFTER:  %s" % new_stmt.strip())
    elif CORRECT_MONSTER_RE.search(stmt) and ICON_ENTRY_RE.search(stmt):
        print("MAP_ICONS_FIX_ALREADY_APPLIED "
              "(markerIcons line already correct - monster closed, "
              "activityCenter is its own entry)")
        return 0
    elif CORRECT_MONSTER_RE.search(stmt):
        # Monster is fine but the icon entry is missing entirely:
        # add it in the correct place (right after the monster entry).
        cm = CORRECT_MONSTER_RE.search(stmt)
        new_stmt = (stmt[:cm.end()] + ", activityCenter: '🎮'"
                    + stmt[cm.end():])
        mode = "icon-missing"
        print("BEFORE: %s" % stmt.strip())
        print("AFTER:  %s" % new_stmt.strip())
    else:
        print("WARNING: markerIcons monster entry not found in expected "
              "form in GameMap.tsx - markerIcons line NOT fixed (searched "
              "for monster: '<backslash>u{1F480}' with a closing quote, "
              "corrupt or correct)")
        return 1

    # --- Dedupe: if the icon entry now appears more than once in this
    # statement (e.g. a correct v2 end-entry plus the restored one),
    # keep the first and drop the rest. ---
    icon_count = len(ICON_ENTRY_RE.findall(new_stmt))
    if icon_count > 1:
        seen = [False]
        def _drop(match):
            if not seen[0]:
                seen[0] = True
                return match.group(0)
            return ""
        new_stmt = re.sub(r",\s*activityCenter:\s*['\"]🎮['\"]",
                          _drop, new_stmt)
        removed = icon_count - len(ICON_ENTRY_RE.findall(new_stmt))
        print("MAP_ICONS_FIX_DEDUPED (removed %d extra activityCenter "
              "icon entries from the markerIcons line)" % removed)

    lines[stmt_idx] = new_stmt
    new_src = "\n".join(lines)

    # --- In-patch verification (before writing anything) ---
    if delta(new_src) != odelta:
        print("WARNING: balance changed - GameMap.tsx NOT written")
        return 1

    color_count = new_src.count(COLOR_ENTRY)
    icon_count = len(ICON_ENTRY_RE.findall(
        new_src.split("\n")[stmt_idx]))
    branch_present = BRANCH_ANCHOR in new_src
    print("MAP_ICONS_FIX_COUNTS: markerColors activityCenter=%d "
          "(expect 1), markerIcons activityCenter=%d (expect 1), "
          "marker branch present=%s"
          % (color_count, icon_count, branch_present))
    if color_count != 1:
        print("WARNING: markerColors activityCenter entry count is %d, "
              "not 1 - GameMap.tsx NOT written" % color_count)
        return 1
    if icon_count != 1:
        print("WARNING: markerIcons activityCenter entry count is %d, "
              "not 1 - GameMap.tsx NOT written" % icon_count)
        return 1
    if not branch_present:
        print("WARNING: activityCenter marker branch missing from "
              "GameMap.tsx - GameMap.tsx NOT written")
        return 1

    open_line, raw = extract_script(new_src)
    if raw is None:
        print("WARNING: no inline <script> block found in GameMap.tsx - "
              "GameMap.tsx NOT written")
        return 1
    code = raw
    if code.startswith("\n"):
        code = code[1:]
    code = substitute_placeholders(code)
    ok, err = node_check(code)
    if ok is True:
        print("MAP_ICONS_FIX_NODE_CHECK_PASS "
              "(inline script parses clean, <script> at GameMap.tsx:%d)"
              % open_line)
    elif ok is False:
        print("WARNING: inline script still does NOT parse after the fix "
              "- GameMap.tsx NOT written (node error: %s)" % err)
        return 1
    else:
        # node unavailable: balance-scan fallback only.
        balanced, info = balance_scan(code)
        print("WARNING: %s - script check fell back to a "
              "bracket/backtick balance scan only" % err)
        if not balanced:
            print("WARNING: balance scan failed (%s) - "
                  "GameMap.tsx NOT written" % info)
            return 1
        print("MAP_ICONS_FIX_BALANCE_SCAN_PASS (%s)" % info)

    if new_src == orig:
        print("MAP_ICONS_FIX_ALREADY_APPLIED (no change needed)")
        return 0
    GAMEMAP.write_text(new_src)
    if mode == "corrupt":
        print("MAP_ICONS_FIX_OK (corrupted markerIcons line restored)")
    else:
        print("MAP_ICONS_FIX_OK (activityCenter icon entry added)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
