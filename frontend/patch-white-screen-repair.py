#!/usr/bin/env python3
"""Street Legends FRONTEND-ONLY white-screen repair (Expo Go).

Evidence (live /app, 2026-11-05 diag + Emergent's own fix):
- index.tsx calls the activity-center api functions and renders
  ImageBackground, but the v2 activity patch's exact-line import anchors
  missed, so neither was imported: the map screen throws a
  ReferenceError on mount and Expo Go never leaves the splash.
- GameMap.tsx got the activityCenter marker branch but NOT the
  markerColors/markerIcons entries (its markers render '?' on grey).
- api.ts: grass/pills/rock item api functions never landed (their
  sellItem anchor missed), while flake/activity fns did.
- api.ts ALSO had a duplicate 'sellRockCandyItem' declaration (a
  parse-time error that kills the whole Metro bundle). Emergent's agent
  already removed the duplicates, keeping consumeRockCandyItem + a
  single sellRockCandyItem. This patch MUST NOT re-create it: every
  api function is added only when its export count is zero, and
  consumeRockCandyItem is treated as the rock use-function.

This patch touches index.tsx, GameMap.tsx and api.ts only. It READS
character.tsx (to align the rock handler call) but never writes it.
Each part is guarded: ALREADY_APPLIED if present, WARNING + skip only
that part if its anchor cannot be found. Imports are handled with
regex over the whole import statement (multi-line and either quote
style), never exact-line anchors. After writing, it runs the project's
own eslint (frontend/node_modules/.bin/eslint) on the five bundle
files when present and reports Parsing errors separately.
Run: cd /app && python3 frontend/patch-white-screen-repair.py
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"
CHAR = ROOT / "frontend/app/(tabs)/character.tsx"
GAMEMAP = ROOT / "frontend/components/GameMap.tsx"
API = ROOT / "frontend/services/api.ts"
MARKER = "WHITE_SCREEN_REPAIR_OK"

CENTER_IMPORTS = ["getActivityCentersNearby", "centerEnterPresence",
                  "centerLeavePresence", "centerHeartbeatPresence",
                  "getCenterPresence", "getFriendsList"]

# Verbatim api bodies from the original item frontend patches.
ITEM_API = {
    "grass": ("useGrassItem", "sellGrassItem", None, """export const useGrassItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/grass/use`);
  return response.data;
};

export const sellGrassItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/grass/sell?qty=${qty}`);
  return response.data;
};
"""),
    "pills": ("usePillsItem", "sellPillsItem", None, """export const usePillsItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/pills/use`);
  return response.data;
};

export const sellPillsItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/pills/sell?qty=${qty}`);
  return response.data;
};
"""),
    "rock": ("useRockCandyItem", "sellRockCandyItem", "consumeRockCandyItem", """export const useRockCandyItem = async (playerId: string) => {
  const response = await api.post(`/players/${playerId}/rock-candy/use`);
  return response.data;
};

export const sellRockCandyItem = async (playerId: string, qty: number = 1) => {
  const response = await api.post(`/players/${playerId}/rock-candy/sell?qty=${qty}`);
  return response.data;
};
"""),
}

CONSUME_NAMES = {"grass": "consumeGrassItem", "pills": "consumePillsItem",
                 "rock": "consumeRockCandyItem"}


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def count_export(src, name):
    return len(re.findall(r"export\s+const\s+" + re.escape(name) + r"\b", src))


def add_to_named_import(src, module_substr, names):
    """Add missing names to a named import from a module containing
    module_substr. Returns (new_src, added_list, found_bool, context)."""
    pat = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]([^'\"]*" +
                     re.escape(module_substr) + r"[^'\"]*)['\"]", re.DOTALL)
    m = pat.search(src)
    if not m:
        head = "\n".join(src.split("\n")[:15])
        return src, [], False, head
    inner = m.group(1)
    existing = set()
    for part in inner.split(","):
        part = part.strip()
        if not part:
            continue
        existing.add(part.split(" as ")[0].strip())
    missing = [n for n in names if n not in existing]
    if not missing:
        return src, [], True, ""
    insert = "".join("  %s,\n" % n for n in missing)
    # Insert just before the closing brace of the import.
    new_inner = inner.rstrip()
    if not new_inner.endswith(","):
        new_inner += ","
    new_inner += "\n" + insert
    new_src = src[:m.start(1)] + new_inner + src[m.end(1):]
    return new_src, missing, True, ""


def main():
    landed = []
    warned = []

    # ---------- Part 1: ImageBackground import (index.tsx) ----------
    # NOTE: presence must be checked INSIDE the react-native import, not
    # anywhere in the file: the interior modal USES ImageBackground, so a
    # bare "ImageBackground" in src would falsely report ALREADY_APPLIED
    # while the import is still missing (that is the live bug).
    if not INDEX.exists():
        print("WARNING: app/(tabs)/index.tsx not found - ImageBackground import NOT added")
        warned.append("rn-import")
    else:
        src = INDEX.read_text(errors="ignore")
        orig = src
        iorig = delta(src)
        new_src, added, found, ctx = add_to_named_import(src, "react-native", ["ImageBackground"])
        if found and not added:
            print("WHITE_SCREEN_REPAIR_RN_IMPORT_ALREADY_APPLIED")
            landed.append("rn-import")
        elif found and added:
            src = new_src
            print("WHITE_SCREEN_REPAIR_RN_IMPORT_OK")
            landed.append("rn-import")
        elif "react-native" in src:
            print("WARNING: react-native import exists in an unrecognized shape - ImageBackground NOT added - context:\n" + ctx)
            warned.append("rn-import")
        else:
            # No react-native import at all: insert a fresh one after the first import line.
            lines = src.split("\n")
            pos = next((i for i, ln in enumerate(lines) if ln.startswith("import ")), -1)
            if pos == -1:
                print("WARNING: no import line found in index.tsx - ImageBackground NOT added")
                warned.append("rn-import")
            else:
                lines.insert(pos + 1, "import { ImageBackground } from 'react-native';")
                src = "\n".join(lines)
                print("WHITE_SCREEN_REPAIR_RN_IMPORT_OK (fresh import line added - no react-native import existed)")
                landed.append("rn-import")
        if delta(src) != iorig:
            print("WARNING: balance changed - index.tsx NOT written (ImageBackground)")
        elif src != orig:
            INDEX.write_text(src)

    # ---------- Part 2: activity-center api imports (index.tsx) ----------
    # Same presence rule as Part 1: the state effect CALLS these names, so
    # "name in src" is true even when the import is missing. Only the
    # import statement counts.
    if not INDEX.exists():
        print("WARNING: app/(tabs)/index.tsx not found - center api imports NOT added")
        warned.append("api-import")
    else:
        src = INDEX.read_text(errors="ignore")
        orig = src
        iorig = delta(src)
        new_src, added, found, ctx = add_to_named_import(src, "services/api", CENTER_IMPORTS)
        if found and not added:
            print("WHITE_SCREEN_REPAIR_API_IMPORT_ALREADY_APPLIED")
            landed.append("api-import")
        elif found and added:
            src = new_src
            print("WHITE_SCREEN_REPAIR_API_IMPORT_OK (added: %s)" % ", ".join(added))
            landed.append("api-import")
        elif "services/api" in src:
            print("WARNING: services/api import exists in an unrecognized shape - center api imports NOT added - context:\n" + ctx)
            warned.append("api-import")
        else:
            # No services/api import at all: add a named import after the react-native import.
            m = re.search(r"import\s*\{[^}]*\}\s*from\s*['\"]react-native['\"]", src, re.DOTALL)
            if not m:
                print("WARNING: no services/api import and no react-native import anchor in index.tsx - center api imports NOT added")
                warned.append("api-import")
            else:
                line = "import { %s } from '../../services/api';" % ", ".join(CENTER_IMPORTS)
                src = src[:m.end()] + "\n" + line + src[m.end():]
                print("WHITE_SCREEN_REPAIR_API_IMPORT_OK (fresh named import line added - no services/api import existed)")
                landed.append("api-import")
        if delta(src) != iorig:
            print("WARNING: balance changed - index.tsx NOT written (api imports)")
        elif src != orig:
            INDEX.write_text(src)

    # ---------- Part 3: GameMap marker color + icon ----------
    if not GAMEMAP.exists():
        print("WARNING: components/GameMap.tsx not found - center marker color/icon NOT added")
        warned.append("gamemap")
    else:
        gsrc = GAMEMAP.read_text(errors="ignore")
        gorig = gsrc
        gdelta = delta(gsrc)
        done_color = done_icon = False
        m = re.search(r"markerColors\s*=\s*\{([^}]*)\}", gsrc)
        if m and "activityCenter" in m.group(1):
            print("WHITE_SCREEN_REPAIR_MAP_COLOR_ALREADY_APPLIED")
            done_color = True
        elif m:
            inner = m.group(1)
            add = (" activityCenter: '#7b1fa2'" if inner.rstrip().endswith(",")
                   else ", activityCenter: '#7b1fa2'")
            gsrc = gsrc[:m.start(1)] + inner + add + gsrc[m.end(1):]
            print("WHITE_SCREEN_REPAIR_MAP_COLOR_OK")
            done_color = True
        else:
            print("WARNING: markerColors object not found in GameMap.tsx - center marker color NOT added")
            warned.append("gamemap-color")
        m = re.search(r"markerIcons\s*=\s*\{([^}]*)\}", gsrc)
        if m and "activityCenter" in m.group(1):
            print("WHITE_SCREEN_REPAIR_MAP_ICON_ALREADY_APPLIED")
            done_icon = True
        elif m:
            inner = m.group(1)
            add = (" activityCenter: '🎮'" if inner.rstrip().endswith(",")
                   else ", activityCenter: '🎮'")
            gsrc = gsrc[:m.start(1)] + inner + add + gsrc[m.end(1):]
            print("WHITE_SCREEN_REPAIR_MAP_ICON_OK")
            done_icon = True
        else:
            print("WARNING: markerIcons object not found in GameMap.tsx - center marker icon NOT added")
            warned.append("gamemap-icon")
        if done_color and done_icon:
            landed.append("gamemap")
        if delta(gsrc) != gdelta:
            print("WARNING: balance changed - GameMap.tsx NOT written")
        elif gsrc != gorig:
            GAMEMAP.write_text(gsrc)

    # ---------- Part 4: markerPress + mapMarkers deps ----------
    if not INDEX.exists():
        print("WARNING: app/(tabs)/index.tsx not found - markerPress deps NOT added")
        warned.append("deps")
    else:
        src = INDEX.read_text(errors="ignore")
        orig = src
        iorig = delta(src)
        updated = 0
        already = 0
        # Collect matches first, then apply from LAST to FIRST: editing
        # src shifts later offsets, so forward iteration with stale
        # spans corrupts the file (that is what the balance guard caught).
        matches = list(re.finditer(r"\[([^\]]*nearbyRestaurants[^\]]*)\]", src))
        for m in reversed(matches):
            inner = m.group(1)
            if "nearbyActivityCenters" in inner:
                already += 1
                continue
            if "nearbyShootouts" not in inner and "localCooldowns" not in inner:
                continue
            new_inner = inner.replace("nearbyRestaurants, ",
                                      "nearbyRestaurants, nearbyActivityCenters, ", 1)
            if new_inner == inner:
                continue
            src = src[:m.start(1)] + new_inner + src[m.end(1):]
            updated += 1
        if updated:
            print("WHITE_SCREEN_REPAIR_DEPS_OK (%d deps array(s) updated)" % updated)
            landed.append("deps")
        elif already:
            print("WHITE_SCREEN_REPAIR_DEPS_ALREADY_APPLIED")
            landed.append("deps")
        else:
            print("WARNING: handleMarkerPress/mapMarkers deps anchor not found - center taps may use a stale list (not the crash)")
            warned.append("deps")
        if delta(src) != iorig:
            print("WARNING: balance changed - index.tsx NOT written (deps)")
        elif src != orig:
            INDEX.write_text(src)

    # ---------- Part 5: api.ts missing item functions (count-guarded) ----------
    char_src = CHAR.read_text(errors="ignore") if CHAR.exists() else ""
    if not API.exists():
        print("WARNING: services/api.ts not found - item api functions NOT added")
        warned.append("api")
    else:
        asrc = API.read_text(errors="ignore")
        aorig = asrc
        adelta = delta(asrc)
        # Count every declaration first: never re-add, never duplicate.
        counts = {}
        for item, (use_fn, sell_fn, _, _) in ITEM_API.items():
            counts[use_fn] = count_export(asrc, use_fn)
            counts[sell_fn] = count_export(asrc, sell_fn)
            counts[CONSUME_NAMES[item]] = count_export(asrc, CONSUME_NAMES[item])
        for name, c in sorted(counts.items()):
            if c >= 2:
                print("WARNING: %s is declared %d times in api.ts - NOT adding (duplicates must be removed by hand)" % (name, c))
                warned.append("api-dup-" + name)
        print("WHITE_SCREEN_REPAIR_API_COUNTS: " + ", ".join(
            "%s=%d" % (n, counts[n]) for n in sorted(counts)))
        missing_bodies = []
        alias_needed = []
        for item, (use_fn, sell_fn, _, body) in ITEM_API.items():
            consume_fn = CONSUME_NAMES[item]
            # Use function: add only if neither use nor consume exists.
            if counts[use_fn] == 0 and counts[consume_fn] == 0:
                missing_bodies.append((use_fn, body.split("\n\n")[0] + "\n"))
            elif counts[use_fn] == 0 and counts[consume_fn] >= 1:
                # Consume variant is the use-function (Emergent's rename).
                if re.search(r"\b" + re.escape(use_fn) + r"\b", char_src):
                    alias_needed.append((use_fn, consume_fn))
            # Sell function: add only if zero declarations.
            if counts[sell_fn] == 0:
                missing_bodies.append((sell_fn, body.split("\n\n")[1] + "\n"))
        if missing_bodies:
            insert = "\n" + "".join(b for _, b in missing_bodies)
            sell_anchor = ("export const sellItem = async (playerId: string, itemId: string) => {\n"
                           "  const response = await api.post(`/players/${playerId}/inventory/${itemId}/sell`);\n"
                           "  return response.data;\n"
                           "};")
            if sell_anchor in asrc:
                asrc = asrc.replace(sell_anchor, sell_anchor + insert, 1)
                print("WHITE_SCREEN_REPAIR_API_OK (added after sellItem: %s)" %
                      ", ".join(n for n, _ in missing_bodies))
            elif "// ============== NIGHTCLUBS ==============" in asrc:
                asrc = asrc.replace("// ============== NIGHTCLUBS ==============",
                                    insert + "\n// ============== NIGHTCLUBS ==============", 1)
                print("WHITE_SCREEN_REPAIR_API_OK (added before NIGHTCLUBS: %s)" %
                      ", ".join(n for n, _ in missing_bodies))
            else:
                asrc = asrc.rstrip() + "\n" + insert
                print("WHITE_SCREEN_REPAIR_API_OK (appended at end of file: %s)" %
                      ", ".join(n for n, _ in missing_bodies))
            landed.append("api")
        else:
            print("WHITE_SCREEN_REPAIR_API_ALREADY_APPLIED (all item functions present)")
            landed.append("api")
        # Alias: character.tsx calls use* but api only exports consume*.
        for use_fn, consume_fn in alias_needed:
            if count_export(asrc, use_fn) == 0:
                asrc = asrc.rstrip() + (
                    "\n\n// WHITE_SCREEN_REPAIR: alias - character.tsx calls %s but api exports %s.\n"
                    "export const %s = %s;\n" % (use_fn, consume_fn, use_fn, consume_fn))
                print("WHITE_SCREEN_REPAIR_API_ALIAS_OK (%s = %s)" % (use_fn, consume_fn))
                landed.append("api-alias-" + use_fn)
        if delta(asrc) != adelta:
            print("WARNING: balance changed - api.ts NOT written")
        elif asrc != aorig:
            API.write_text(asrc)

    # ---------- Part 6: in-patch lint (project's own eslint) ----------
    eslint = ROOT / "frontend/node_modules/.bin/eslint"
    if not eslint.exists():
        print("WHITE_SCREEN_REPAIR_LINT_SKIPPED: no frontend/node_modules/.bin/eslint")
    else:
        try:
            r = subprocess.run(
                [str(eslint), "frontend/app/(tabs)/index.tsx",
                 "frontend/app/(tabs)/character.tsx",
                 "frontend/components/GameMap.tsx",
                 "frontend/services/api.ts",
                 "frontend/hooks/useMapQueries.ts"],
                cwd=str(ROOT), capture_output=True, text=True, timeout=180)
            out = (r.stdout + r.stderr)[:3000]
            print("WHITE_SCREEN_REPAIR_LINT_EXIT: %s" % r.returncode)
            print("\n".join(out.split("\n")[:30]))
            if "Parsing error" in out:
                olines = out.split("\n")
                for i, ln in enumerate(olines):
                    if "Parsing error" in ln:
                        ctx = " | ".join(olines[max(0, i - 2):i + 1])
                        print("WARNING: Parsing error in bundle file - " + ctx)
        except subprocess.TimeoutExpired:
            print("WHITE_SCREEN_REPAIR_LINT_TIMEOUT: eslint did not finish in 180s")
        except Exception as e:  # noqa: BLE001 - lint is advisory only
            print("WHITE_SCREEN_REPAIR_LINT_ERROR: %s" % e)

    if warned:
        print("WHITE_SCREEN_REPAIR_PARTIAL: " + ",".join(landed))
    else:
        print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
