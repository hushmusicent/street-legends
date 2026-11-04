#!/usr/bin/env python3
"""Street Legends READ-ONLY diagnostic: house PLACE location bug.

User report: the house does not land where the player is when PLACE is tapped.
Spec: PLACE must land wherever the player is at tap moment.

WHAT THIS SCRIPT DOES (read-only):
  Prints, with file paths + line numbers, whatever it finds in the CURRENT
  /app tree (the live tree may differ from any local snapshot, so every
  section is anchor-tolerant: a missing anchor prints WARNING and the script
  keeps going):
    (1) shop.tsx handlePlaceHouse function (full body).
    (2) Where player.position comes from: player state definition, how it is
        loaded/refreshed, position-update calls, and any GPS / Location /
        map-region usage that could supply a FRESH location at tap time.
    (3) services/api.ts placeHouse + any position-update function.
    (4) backend/server.py place endpoint body (latitude/longitude handling).

WHAT IT NEVER DOES:
  It only reads files. It never creates, modifies, or deletes any file, never
  calls any API, never runs any patch. It never stops early: every missing
  section prints WARNING and the script continues to the end marker.

RUN FROM /app (the script reads relative to the current working directory,
so the current directory must be /app when you run it):
    python3 diag-house-place.py
  An optional first argument overrides the root (used only by sim-tests):
    python3 diag-house-place.py /path/to/mock/app

LAST LINE IS ALWAYS: HOUSE_PLACE_DIAG_OK
"""

import re
import sys
from pathlib import Path

MARKER = "HOUSE_PLACE_DIAG_OK"

SKIP_DIRS = {".metro-cache", "node_modules", "__pycache__", ".git", "dist", "build", ".expo"}
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx"}

# Regexes as raw strings (patterns contain backslashes and quotes).
SHOP_HANDLER_RE = re.compile(r"handlePlaceHouse")
API_PLACE_RE = re.compile(r"export\s+const\s+placeHouse\b")
PLACE_ROUTE_RE = re.compile(r"/houses/\{house_id\}/place")
PLACE_DEF_RE = re.compile(r"^(async\s+def\s+place_house|def\s+place_house)\b")
PLAYER_PATTERNS = [
    (r"usePlayer\b", "usePlayer hook"),
    (r"PlayerContext\b", "PlayerContext"),
    (r"const\s+\[\s*player\b", "player useState"),
    (r"setPlayer\s*\(", "setPlayer call"),
    (r"refetchPlayer\b", "refetchPlayer"),
    (r"getPlayer\b", "getPlayer"),
    (r"player\?\.position\b", "player?.position use"),
    (r"player\.position\b", "player.position use"),
]
POSITION_UPDATE_PATTERNS = [
    (r"updatePlayerPosition\b", "updatePlayerPosition"),
    (r"updatePosition\b", "updatePosition"),
    (r"/players/[^\"'`]*position", "players position endpoint call"),
    (r"position['\"]\s*:\s*position", "position save"),
]
FRESH_LOCATION_PATTERNS = [
    (r"expo-location", "expo-location import"),
    (r"Location\.", "Location.* call"),
    (r"getCurrentPositionAsync\b", "getCurrentPositionAsync"),
    (r"getCurrentPosition\b", "getCurrentPosition"),
    (r"watchPositionAsync\b", "watchPositionAsync"),
    (r"watchPosition\b", "watchPosition"),
    (r"getLastKnownPositionAsync\b", "getLastKnownPositionAsync"),
    (r"MapView\b", "MapView"),
    (r"onRegionChange\b", "onRegionChange"),
    (r"showsUserLocation\b", "showsUserLocation"),
    (r"followsUserLocation\b", "followsUserLocation"),
]


def read_lines(path):
    """Read a file as lines. Returns None if the file cannot be read."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeError):
        return None
    return text.split("\n")


def print_block(title, path, lines, start_idx, end_idx):
    """Print a numbered code block (1-based line numbers)."""
    print("--- %s: %s lines %d-%d ---" % (title, path, start_idx + 1, end_idx))
    for i in range(start_idx, end_idx):
        print("%s:%d: %s" % (path, i + 1, lines[i]))


def extract_ts_function(lines, start_idx, max_lines=250):
    """Return the end index (exclusive) of a TS/JS function starting at or
    after start_idx, by brace counting with basic string/comment awareness.
    If braces never balance, returns start_idx + max_lines (capped)."""
    # Find the first opening brace at or after start_idx.
    depth = 0
    started = False
    i = start_idx
    limit = min(len(lines), start_idx + max_lines)
    # State: None, "'", '"', "`", "//", "/*".
    state = None
    while i < limit:
        line = lines[i]
        j = 0
        while j < len(line):
            ch = line[j]
            nxt = line[j + 1] if j + 1 < len(line) else ""
            if state == "//":
                break
            if state == "/*":
                if ch == "*" and nxt == "/":
                    state = None
                    j += 2
                    continue
                j += 1
                continue
            if state in ("'", '"', "`"):
                if ch == "\\":
                    j += 2
                    continue
                if ch == state:
                    state = None
                j += 1
                continue
            # Not in string/comment.
            if ch == "/" and nxt == "/":
                state = "//"
                break
            if ch == "/" and nxt == "*":
                state = "/*"
                j += 2
                continue
            if ch in ("'", '"', "`"):
                state = ch
                j += 1
                continue
            if ch == "{":
                depth += 1
                started = True
            elif ch == "}":
                depth -= 1
                if started and depth == 0:
                    return i + 1
            j += 1
        if state == "//":
            state = None
        i += 1
    return limit


def extract_py_function(lines, start_idx, max_lines=150):
    """Return the end index (exclusive) of a Python function starting at
    start_idx: up to (not including) the next top-level def/class/decorator."""
    limit = min(len(lines), start_idx + max_lines)
    i = start_idx + 1
    top_re = re.compile(r"^(@|async\s+def\s|def\s|class\s)")
    while i < limit:
        if top_re.match(lines[i]):
            return i
        i += 1
    return limit


def grep_lines(lines, path, pattern, limit=40):
    """Print up to `limit` lines matching pattern, with file:line numbers.
    Returns the number of matches found (0 if none)."""
    rx = re.compile(pattern)
    count = 0
    for i, line in enumerate(lines):
        if rx.search(line):
            if count < limit:
                print("%s:%d: %s" % (path, i + 1, line.strip()))
            count += 1
    return count


def section_shop_handler(root):
    """(1) shop.tsx handlePlaceHouse full body."""
    print("=== SECTION 1: shop.tsx handlePlaceHouse ===")
    shop = root / "frontend" / "app" / "(tabs)" / "shop.tsx"
    lines = read_lines(shop)
    if lines is None:
        print("WARNING: shop file not found: %s" % shop)
        return False
    found = False
    for i, line in enumerate(lines):
        if "handlePlaceHouse" in line and ("const handlePlaceHouse" in line or "handlePlaceHouse =" in line):
            end = extract_ts_function(lines, i)
            print_block("handlePlaceHouse definition", shop, lines, i, end)
            found = True
            break
    if not found:
        print("WARNING: handlePlaceHouse definition anchor not found in %s" % shop)
    print("--- handlePlaceHouse call sites in %s ---" % shop)
    n = grep_lines(lines, shop, r"handlePlaceHouse", limit=20)
    if n == 0:
        print("WARNING: no handlePlaceHouse mention at all in %s" % shop)
    return found


def section_player_position(root):
    """(2) Where player.position comes from + fresh-location candidates."""
    print("=== SECTION 2: player.position provenance + fresh-location sources ===")
    shop = root / "frontend" / "app" / "(tabs)" / "shop.tsx"
    lines = read_lines(shop)
    if lines is None:
        print("WARNING: shop file not found: %s (cannot trace player in shop)" % shop)
    else:
        print("--- lines mentioning 'player' in %s ---" % shop)
        n = grep_lines(lines, shop, r"player", limit=40)
        if n == 0:
            print("WARNING: no 'player' mention in %s" % shop)
        print("--- lines mentioning 'position' in %s ---" % shop)
        n = grep_lines(lines, shop, r"position", limit=40)
        if n == 0:
            print("WARNING: no 'position' mention in %s" % shop)
    # Walk frontend source files (skip caches/build output).
    files = []
    frontend = root / "frontend"
    if frontend.is_dir():
        for path in sorted(frontend.rglob("*")):
            if not path.is_file():
                continue
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            if path.suffix not in SOURCE_SUFFIXES:
                continue
            if path.stat().st_size > 1024 * 1024:
                continue
            files.append(path)
    else:
        print("WARNING: frontend directory not found: %s" % frontend)
    print("--- player-state patterns across frontend source (%d files) ---" % len(files))
    any_player = False
    for pattern, label in PLAYER_PATTERNS:
        hits = 0
        for path in files:
            flines = read_lines(path)
            if flines is None:
                continue
            for i, line in enumerate(flines):
                if re.search(pattern, line):
                    if hits < 15:
                        print("%s:%d: [%s] %s" % (path, i + 1, label, line.strip()))
                    hits += 1
        if hits == 0:
            print("WARNING: player pattern not found: %s (%s)" % (label, pattern))
        else:
            any_player = True
    print("--- position-update patterns across frontend source ---")
    any_update = False
    for pattern, label in POSITION_UPDATE_PATTERNS:
        hits = 0
        for path in files:
            flines = read_lines(path)
            if flines is None:
                continue
            for i, line in enumerate(flines):
                if re.search(pattern, line):
                    if hits < 15:
                        print("%s:%d: [%s] %s" % (path, i + 1, label, line.strip()))
                    hits += 1
        if hits == 0:
            print("WARNING: position-update pattern not found: %s (%s)" % (label, pattern))
        else:
            any_update = True
    print("--- fresh-location (GPS / map-region) patterns across frontend source ---")
    fresh = []
    for pattern, label in FRESH_LOCATION_PATTERNS:
        hits = 0
        for path in files:
            flines = read_lines(path)
            if flines is None:
                continue
            for i, line in enumerate(flines):
                if re.search(pattern, line):
                    if hits < 15:
                        print("%s:%d: [%s] %s" % (path, i + 1, label, line.strip()))
                    hits += 1
        if hits > 0:
            fresh.append(label)
        else:
            print("WARNING: fresh-location pattern not found: %s (%s)" % (label, pattern))
    if fresh:
        print("FRESH-LOCATION CANDIDATES FOUND: %s" % ", ".join(fresh))
    else:
        print("FRESH-LOCATION CANDIDATES FOUND: none in searched files (only cached player.position seen, if any)")
    return any_player, any_update, fresh


def section_api_place(root):
    """(3) services/api.ts placeHouse + position-update functions."""
    print("=== SECTION 3: services/api.ts placeHouse + position-update ===")
    api = root / "frontend" / "services" / "api.ts"
    lines = read_lines(api)
    if lines is None:
        print("WARNING: api file not found: %s" % api)
        return False
    found = False
    for i, line in enumerate(lines):
        if API_PLACE_RE.search(line):
            end = extract_ts_function(lines, i)
            print_block("placeHouse definition", api, lines, i, end)
            found = True
            break
    if not found:
        print("WARNING: placeHouse definition anchor not found in %s" % api)
    print("--- lines mentioning 'position' in %s ---" % api)
    n = grep_lines(lines, api, r"position", limit=40)
    if n == 0:
        print("WARNING: no 'position' mention in %s" % api)
    return found


def section_backend_place(root):
    """(4) backend/server.py place endpoint body (lat/lng handling)."""
    print("=== SECTION 4: backend/server.py place endpoint ===")
    server = root / "backend" / "server.py"
    lines = read_lines(server)
    if lines is None:
        print("WARNING: backend file not found: %s" % server)
        return False
    route_idx = None
    for i, line in enumerate(lines):
        if PLACE_ROUTE_RE.search(line):
            route_idx = i
            break
    def_idx = None
    for i, line in enumerate(lines):
        if PLACE_DEF_RE.match(line):
            def_idx = i
            break
    if route_idx is None and def_idx is None:
        print("WARNING: place endpoint anchor not found in %s (searched for route /houses/{house_id}/place and def place_house; route NOT guessed)" % server)
        return False
    if route_idx is not None:
        print("%s:%d: %s" % (server, route_idx + 1, lines[route_idx].strip()))
    if def_idx is not None:
        end = extract_py_function(lines, def_idx)
        print_block("place_house definition", server, lines, def_idx, end)
        print("--- latitude/longitude handling lines in place_house body ---")
        found_lat = False
        for i in range(def_idx, end):
            if "latitude" in lines[i] or "longitude" in lines[i]:
                print("%s:%d: %s" % (server, i + 1, lines[i].strip()))
                found_lat = True
        if not found_lat:
            print("WARNING: no latitude/longitude lines in place_house body in %s" % server)
    else:
        print("WARNING: place_house function definition not found in %s (route line found but def missing)" % server)
    return True


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print("HOUSE PLACE DIAG: root = %s (read-only, no files modified)" % root)
    try:
        handler_found = section_shop_handler(root)
    except Exception as exc:
        print("WARNING: section 1 failed with %s (continuing)" % exc)
        handler_found = False
    try:
        _player, _update, fresh = section_player_position(root)
    except Exception as exc:
        print("WARNING: section 2 failed with %s (continuing)" % exc)
        fresh = []
    try:
        api_found = section_api_place(root)
    except Exception as exc:
        print("WARNING: section 3 failed with %s (continuing)" % exc)
        api_found = False
    try:
        backend_found = section_backend_place(root)
    except Exception as exc:
        print("WARNING: section 4 failed with %s (continuing)" % exc)
        backend_found = False
    print("=== PLACE DATA-FLOW SUMMARY (from sections above only) ===")
    print("shop handlePlaceHouse found: %s" % handler_found)
    print("api placeHouse found: %s" % api_found)
    print("backend place endpoint found: %s" % backend_found)
    if fresh:
        print("fresh-location candidates in searched files: %s" % ", ".join(fresh))
    else:
        print("fresh-location candidates in searched files: none (if handler sends player.position, it is the cached/saved position unless a candidate above refreshes it)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        print("WARNING: diagnostic failed with %s" % exc)
        print(MARKER)
        code = 0
    sys.exit(code)
