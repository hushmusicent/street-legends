#!/usr/bin/env python3
"""Street Legends READ-ONLY diagnostic: friend house visiting + presence.

User request: friends should be able to enter and enjoy another friend's
house, and the house should show who currently is in it.

WHAT THIS SCRIPT DOES (read-only):
  Prints, with file paths + line numbers + short quoted snippets, whatever
  it finds in the CURRENT /app tree (the live tree may differ from any
  local snapshot, so every section is anchor-tolerant: a missing file or
  anchor prints WARNING and the script keeps going):
    (0) Which candidate paths actually exist vs are missing.
    (1) ENTER HOUSE: what the map house-popup ENTER HOUSE button does
        exactly (its onPress code) — marker object vs refetch of the
        viewer's own house — and any owner check on entering.
    (2) GUEST BUY/SELL RISK: every interior buy/sell/add/remove/
        place-from-inventory path (frontend handlers + backend endpoints)
        and whether any of them checks that the acting player owns the
        house; the house document's owner field name.
    (3) FRIENDS: how friends are stored (player doc field name and shape)
        and how houses-nearby filters by friends today.
    (4) PRESENCE: any existing enter/leave/presence/heartbeat code
        (frontend or backend). If none, it says so explicitly.
    (5) ANCHORS for a future visit patch: (a) interior-header presence
        list site, (b) guest-mode gating sites for buy/sell/move buttons,
        (c) presence enter-call site on interior open + leave-call sites
        on LEAVE HOUSE button + modal close.
    (6) MAP MARKERS: how house markers are rendered, and whether a
        friend's house marker offers the same popup/Enter as your own.

WHAT IT NEVER DOES:
  It only reads files. It never creates, modifies, or deletes any file,
  never calls any API, never runs any patch. It never stops early: every
  missing section prints WARNING and the script continues to the end
  marker.

RUN FROM /app (the script reads relative to the current working directory,
so the current directory must be /app when you run it):
    python3 diag-house-visit.py
  An optional first argument overrides the root (used only by sim-tests):
    python3 diag-house-visit.py /path/to/mock/app

LAST LINE IS ALWAYS: HOUSE_VISIT_DIAG_OK
"""

import re
import sys
from pathlib import Path

MARKER = "HOUSE_VISIT_DIAG_OK"

SKIP_DIRS = {".metro-cache", "node_modules", "__pycache__", ".git", "dist", "build", ".expo"}
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx"}

# Candidate paths, checked in section 0 (existence only, no content assumed).
CANDIDATES = [
    "frontend/app/(tabs)/index.tsx",
    "frontend/app/(tabs)/shop.tsx",
    "frontend/services/api.ts",
    "frontend/api.ts",
    "frontend/lib/api.ts",
    "frontend/hooks/useMapQueries.ts",
    "backend/server.py",
]

FINDINGS = {
    "enter_marker": False,        # ENTER onPress sets interior from marker
    "enter_refetch_own": False,   # ENTER refetches viewer's own house
    "enter_owner_check": False,   # any owner check around entering
    "backend_owner_checks": [],   # endpoint names with an owner check
    "backend_no_check": [],       # item endpoints with NO owner check seen
    "house_owner_field": None,    # e.g. player_id
    "friends_field": None,        # e.g. friends: List[str]
    "nearby_friends_filter": False,
    "presence_hits": 0,
    "header_anchor": False,
    "leave_anchor": False,
    "marker_popup": False,
}


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
    """End index (exclusive) of a TS/JS function starting at/after start_idx,
    by brace counting with basic string/comment awareness."""
    depth = 0
    started = False
    i = start_idx
    limit = min(len(lines), start_idx + max_lines)
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
    """End index (exclusive) of a Python function starting at start_idx:
    up to (not including) the next top-level def/class/decorator."""
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


def walk_frontend(root):
    """All frontend source files (skip caches/build output), sorted."""
    frontend = root / "frontend"
    files = []
    if not frontend.is_dir():
        return files
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
    return files


def section_candidates(root):
    """(0) Which candidate paths exist vs are missing."""
    print("=== SECTION 0: candidate paths (existence only) ===")
    found = {}
    for rel in CANDIDATES:
        path = root / rel
        ok = path.is_file()
        found[rel] = ok
        print("%s: %s" % ("EXISTS" if ok else "MISSING", path))
        if not ok:
            print("WARNING: candidate file not found: %s" % path)
    return found


def section_enter(root, files):
    """(1) ENTER HOUSE button: marker object vs own-house refetch, owner check."""
    print("=== SECTION 1: ENTER HOUSE button ===")
    index = root / "frontend" / "app" / "(tabs)" / "index.tsx"
    lines = read_lines(index)
    if lines is None:
        print("WARNING: map file not found: %s (cannot trace ENTER HOUSE)" % index)
        return
    print("--- lines mentioning 'ENTER HOUSE' in %s ---" % index)
    n = grep_lines(lines, index, r"ENTER HOUSE", limit=20)
    if n == 0:
        print("WARNING: no 'ENTER HOUSE' text in %s" % index)
    print("--- lines mentioning 'setInteriorHouse(selectedMarker' in %s ---" % index)
    n = grep_lines(lines, index, r"setInteriorHouse\(selectedMarker", limit=20)
    if n > 0:
        FINDINGS["enter_marker"] = True
    else:
        print("WARNING: no setInteriorHouse(selectedMarker...) line in %s" % index)
    print("--- ENTER HOUSE onPress blocks (ENTER HOUSE text + nearby onPress) ---")
    shown = 0
    for i, line in enumerate(lines):
        if "ENTER HOUSE" in line:
            # Walk backwards up to 15 lines for the enclosing onPress.
            start = max(0, i - 15)
            for j in range(i, start - 1, -1):
                if "onPress" in lines[j]:
                    end = extract_ts_function(lines, j)
                    print_block("ENTER HOUSE onPress block", index, lines, j, end)
                    shown += 1
                    break
            if shown >= 3:
                break
    if shown == 0:
        print("WARNING: no onPress block found near ENTER HOUSE text in %s" % index)
    print("--- own-house refetch near ENTER (getPlayerHouse / houses/player) ---")
    n = grep_lines(lines, index, r"getPlayerHouse|houses/player", limit=20)
    if n > 0:
        # Refetch alone does not prove ENTER refetches the viewer's own
        # house; the onPress block above is the deciding evidence.
        print("NOTE: getPlayerHouse/houses/player appears in %s (see onPress block above for whether ENTER uses it)" % index)
    print("--- owner checks near entering (player_id comparisons in %s) ---" % index)
    n = grep_lines(lines, index, r"selectedMarker.*player_id|player_id.*selectedMarker|owner", limit=20)
    if n > 0:
        FINDINGS["enter_owner_check"] = True
    else:
        print("WARNING: no owner check (player_id/owner near selectedMarker) seen in %s" % index)
    print("--- selectedMarker definition + assignment lines ---")
    n = grep_lines(lines, index, r"selectedMarker|setSelectedMarker", limit=30)
    if n == 0:
        print("WARNING: no selectedMarker mention in %s" % index)


def section_buysell(root, files):
    """(2) Interior buy/sell/add/remove/place paths + owner checks."""
    print("=== SECTION 2: GUEST BUY/SELL RISK (frontend handlers) ===")
    print("--- interior item handler lines across frontend source ---")
    handler_pats = [
        (r"addHouseItem\s*\(", "addHouseItem call"),
        (r"removeHouseItem\s*\(", "removeHouseItem call"),
        (r"placeItemFromInventory\s*\(", "placeItemFromInventory call"),
        (r"postItem\s*\(", "postItem call"),
        (r"/houses/\$\{[^}]*\}/items/", "houses items endpoint call"),
        (r"handleHouseItemToggle|handleItemToggle|toggleHouseItem", "item toggle handler"),
    ]
    for pattern, label in handler_pats:
        hits = 0
        for path in files:
            flines = read_lines(path)
            if flines is None:
                continue
            for i, line in enumerate(flines):
                if re.search(pattern, line):
                    if hits < 12:
                        print("%s:%d: [%s] %s" % (path, i + 1, label, line.strip()))
                    hits += 1
        if hits == 0:
            print("WARNING: frontend pattern not found: %s (%s)" % (label, pattern))
    print("--- frontend handler definitions (toggle/add/remove) with bodies ---")
    shown = 0
    for path in files:
        flines = read_lines(path)
        if flines is None:
            continue
        for i, line in enumerate(flines):
            if re.search(r"const\s+(handleHouseItemToggle|handleItemToggle|toggleHouseItem|postItem|handleBuyItem|handleSellItem)\b", line):
                end = extract_ts_function(flines, i)
                print_block("handler definition", path, flines, i, end)
                shown += 1
                if shown >= 4:
                    break
        if shown >= 4:
            break
    if shown == 0:
        print("WARNING: no frontend item-handler definition found in searched files")
    print("--- frontend owner checks near item handlers (player_id vs house owner) ---")
    hits = 0
    for path in files:
        flines = read_lines(path)
        if flines is None:
            continue
        for i, line in enumerate(flines):
            if re.search(r"interiorHouse\?\.player_id|interiorHouse\.player_id|house.*owner|isOwner|ownerId", line):
                if hits < 15:
                    print("%s:%d: %s" % (path, i + 1, line.strip()))
                hits += 1
    if hits == 0:
        print("WARNING: no frontend owner check (interiorHouse.player_id / isOwner) seen in searched files")
    print("=== SECTION 2b: GUEST BUY/SELL RISK (backend endpoints) ===")
    server = root / "backend" / "server.py"
    lines = read_lines(server)
    if lines is None:
        print("WARNING: backend file not found: %s (cannot trace item endpoints)" % server)
        return
    print("--- house document owner field (player_id in house creation) ---")
    n = grep_lines(lines, server, r"\"player_id\"\s*:\s*player_id|'player_id'\s*:\s*player_id", limit=10)
    if n > 0:
        FINDINGS["house_owner_field"] = "player_id"
    print("--- house item route lines in %s ---" % server)
    route_idxs = []
    for i, line in enumerate(lines):
        if re.search(r"/houses/\{house_id\}/items/", line):
            print("%s:%d: %s" % (server, i + 1, line.strip()))
            route_idxs.append(i)
    if not route_idxs:
        print("WARNING: no /houses/{house_id}/items/ route in %s" % server)
    print("--- item endpoint bodies + owner checks (403 / player_id comparison) ---")
    for ridx in route_idxs:
        # Find the def after the route decorator.
        def_idx = None
        for j in range(ridx, min(len(lines), ridx + 6)):
            if re.match(r"^(async\s+def\s|def\s)", lines[j]):
                def_idx = j
                break
        if def_idx is None:
            print("WARNING: no def found after route at %s:%d" % (server, ridx + 1))
            continue
        end = extract_py_function(lines, def_idx)
        print_block("item endpoint", server, lines, def_idx, end)
        body = "\n".join(lines[def_idx:end])
        name = lines[def_idx].strip()
        if re.search(r"player_id.{0,40}!=\s*house\.get\(\"player_id\"\)|house\.get\(\"player_id\"\).{0,40}!=\s*player_id|Only the owner|Not your house", body):
            FINDINGS["backend_owner_checks"].append(name)
            print("OWNER CHECK PRESENT in endpoint above")
        else:
            FINDINGS["backend_no_check"].append(name)
            print("WARNING: no owner check seen in endpoint above (guest could call it if frontend lets them)")
    print("--- house sell / move / hide endpoints (owner checks) ---")
    n = grep_lines(lines, server, r"/houses/\{house_id\}/(sell|move-to-inventory|place|toggle-hide)", limit=20)
    if n == 0:
        print("WARNING: no sell/move/place/toggle-hide house route in %s" % server)


def section_friends(root):
    """(3) Friends storage + houses-nearby friends filter."""
    print("=== SECTION 3: FRIENDS storage + nearby filter ===")
    server = root / "backend" / "server.py"
    lines = read_lines(server)
    if lines is None:
        print("WARNING: backend file not found: %s (cannot trace friends)" % server)
        return
    print("--- player doc friends field ---")
    n = grep_lines(lines, server, r"friends\s*:\s*List\[str\]|\"friends\"|'friends'", limit=20)
    if n > 0:
        FINDINGS["friends_field"] = "friends (list of player IDs)"
    else:
        print("WARNING: no friends field found in %s" % server)
    print("--- friend add/accept (mutual $addToSet) ---")
    n = grep_lines(lines, server, r"\$addToSet.{0,40}friends|\$pull.{0,40}friends", limit=20)
    if n == 0:
        print("WARNING: no friend add/remove ($addToSet/$pull friends) in %s" % server)
    print("--- houses-nearby function + friends filter ---")
    n = grep_lines(lines, server, r"get_nearby_houses|/houses/nearby", limit=20)
    if n == 0:
        print("WARNING: no houses-nearby function/route in %s" % server)
    for i, line in enumerate(lines):
        if "get_nearby_houses" in line and re.match(r"^(async\s+def\s|def\s)", line):
            end = extract_py_function(lines, i)
            print_block("get_nearby_houses definition", server, lines, i, end)
            body = "\n".join(lines[i:end])
            if "friends" in body and "visible_owners" in body:
                FINDINGS["nearby_friends_filter"] = True
                print("NEARBY FRIENDS FILTER PRESENT in body above (visible_owners = friends | self)")
            break
    if not FINDINGS["nearby_friends_filter"]:
        print("WARNING: nearby friends filter (friends | self) not confirmed in get_nearby_houses body")


def section_presence(root, files):
    """(4) Any existing enter/leave/presence/heartbeat code."""
    print("=== SECTION 4: PRESENCE (enter/leave/heartbeat) ===")
    server = root / "backend" / "server.py"
    slines = read_lines(server)
    pats = [
        (r"presence", "presence"),
        (r"heartbeat", "heartbeat"),
        (r"occupants?", "occupant(s)"),
        (r"visitors?", "visitor(s)"),
        (r"/houses/\{house_id\}/(enter|leave)", "house enter/leave route"),
        (r"in_house|currently_in|is_in_house", "in-house flag"),
    ]
    total = 0
    print("--- presence patterns in backend/server.py ---")
    if slines is None:
        print("WARNING: backend file not found: %s" % server)
    else:
        for pattern, label in pats:
            n = grep_lines(slines, server, pattern, limit=15)
            if n > 0:
                print("PATTERN FOUND: %s (%d hits)" % (label, n))
            total += n
    print("--- presence patterns across frontend source ---")
    for pattern, label in pats:
        hits = 0
        for path in files:
            flines = read_lines(path)
            if flines is None:
                continue
            for i, line in enumerate(flines):
                if re.search(pattern, line, re.IGNORECASE):
                    if hits < 12:
                        print("%s:%d: [%s] %s" % (path, i + 1, label, line.strip()))
                    hits += 1
        if hits > 0:
            print("PATTERN FOUND (frontend): %s (%d hits)" % (label, hits))
        total += hits
    FINDINGS["presence_hits"] = total
    if total == 0:
        print("PRESENCE CODE FOUND: none — no enter/leave/presence/heartbeat/occupant/visitor code in searched files")
    else:
        print("PRESENCE CODE FOUND: %d total hits above (review each: may be unrelated, e.g. game rooms)" % total)


def section_anchors(root, files):
    """(5) Anchors for the future visit patch."""
    print("=== SECTION 5: ANCHORS for the future visit patch ===")
    index = root / "frontend" / "app" / "(tabs)" / "index.tsx"
    lines = read_lines(index)
    if lines is None:
        print("WARNING: map file not found: %s (cannot locate interior anchors)" % index)
    else:
        print("--- (a) interior header site: house name + items-count Text ---")
        n = grep_lines(lines, index, r"interiorHouse\?\.name|item_limit|items\?\.length", limit=20)
        if n > 0:
            FINDINGS["header_anchor"] = True
        else:
            print("WARNING: interior header anchor (name / items-count Text) not found in %s" % index)
        print("--- (b) guest-gating sites: item tap / buy / sell / move / hide ---")
        for pattern, label in [
            (r"handleHouseItemToggle|handleItemToggle", "item tap toggle handler"),
            (r"removeHouseItem|addHouseItem", "buy/sell item calls in index"),
            (r"MOVE|SELL|HIDE", "MOVE/SELL/HIDE buttons in index"),
            (r"onRequestClose", "modal close (leave-call site candidate)"),
        ]:
            n = grep_lines(lines, index, pattern, limit=12)
            if n == 0:
                print("WARNING: anchor pattern not found in index: %s (%s)" % (label, pattern))
        print("--- (c) leave-call sites: LEAVE HOUSE button + modal close ---")
        n = grep_lines(lines, index, r"LEAVE HOUSE", limit=12)
        if n > 0:
            FINDINGS["leave_anchor"] = True
        else:
            print("WARNING: LEAVE HOUSE button text not found in %s" % index)
        n = grep_lines(lines, index, r"setInteriorHouse\(null\)", limit=12)
        if n == 0:
            print("WARNING: no setInteriorHouse(null) (leave/close) in %s" % index)
    shop = root / "frontend" / "app" / "(tabs)" / "shop.tsx"
    slines = read_lines(shop)
    if slines is None:
        print("WARNING: shop file not found: %s (cannot locate shop buy/move gates)" % shop)
    else:
        print("--- shop House-tab gating sites (buy / MOVE buttons) ---")
        for pattern, label in [
            (r"MOVE", "MOVE button in shop"),
            (r"handleBuyHouse|buyHouse|BUY", "house buy in shop"),
        ]:
            n = grep_lines(slines, shop, pattern, limit=12)
            if n == 0:
                print("WARNING: anchor pattern not found in shop: %s (%s)" % (label, pattern))
    print("--- (c) enter-call site: ENTER HOUSE onPress (see Section 1 block) ---")
    print("ENTER-CALL SITE = the ENTER HOUSE onPress block printed in Section 1 (presence enter call would be added there, after interior opens).")


def section_markers(root, files):
    """(6) House marker rendering + friend vs own popup."""
    print("=== SECTION 6: MAP MARKERS (friend vs own) ===")
    index = root / "frontend" / "app" / "(tabs)" / "index.tsx"
    lines = read_lines(index)
    if lines is None:
        print("WARNING: map file not found: %s (cannot trace markers)" % index)
        return
    print("--- nearby-houses fetch (getNearbyHouses / houses/nearby) ---")
    n = grep_lines(lines, index, r"getNearbyHouses|houses/nearby|nearbyHouses", limit=20)
    if n == 0:
        print("WARNING: no nearby-houses fetch in %s" % index)
    print("--- house marker rendering lines ---")
    n = grep_lines(lines, index, r"🏠|<Marker|house.*Marker|Marker.*house", limit=30)
    if n == 0:
        print("WARNING: no house marker rendering line in %s" % index)
    print("--- marker press -> selectedMarker (popup source) ---")
    n = grep_lines(lines, index, r"setSelectedMarker|onPress.*[Ss]electedMarker|selectedMarker.*=", limit=20)
    if n == 0:
        print("WARNING: no marker-press -> selectedMarker line in %s" % index)
    print("--- popup options (Enter / Sell / Hide / Move text near marker popup) ---")
    n = grep_lines(lines, index, r"ENTER HOUSE|SELL|HIDE|MOVE", limit=20)
    if n > 0:
        FINDINGS["marker_popup"] = True
    else:
        print("WARNING: no popup option text (ENTER/SELL/HIDE/MOVE) in %s" % index)
    print("--- any owner/friend distinction at marker or popup (player_id compare) ---")
    n = grep_lines(lines, index, r"selectedMarker\.data\.player_id|marker.*player_id|player_id.*marker", limit=20)
    if n == 0:
        print("WARNING: no owner/friend distinction (player_id) at marker/popup in %s — popup likely identical for own and friend houses" % index)


def verdicts():
    """One short verdict per question, from FINDINGS only."""
    print("=== VERDICTS (from sections above only) ===")
    if FINDINGS["enter_marker"]:
        print("VERDICT Q1 ENTER HOUSE: ENTER sets the interior from the tapped marker object (setInteriorHouse(selectedMarker.data)) — it does NOT refetch on ENTER by itself. Any refetch comes from a separate refresh step, if present. Owner check on ENTER: %s." % ("seen (see Section 1)" if FINDINGS["enter_owner_check"] else "NOT seen — a friend tapping a friend's marker would open that house object"))
    else:
        print("VERDICT Q1 ENTER HOUSE: UNCONFIRMED — setInteriorHouse(selectedMarker...) not found; see Section 1 WARNINGs.")
    if FINDINGS["backend_owner_checks"]:
        print("VERDICT Q2 GUEST BUY/SELL (backend): owner checks PRESENT on: %s. A guest calling a checked endpoint gets 403 even if the UI lets them tap." % "; ".join(FINDINGS["backend_owner_checks"]))
    else:
        print("VERDICT Q2 GUEST BUY/SELL (backend): NO owner check confirmed on item endpoints — see Section 2b WARNINGs.")
    if FINDINGS["backend_no_check"]:
        print("VERDICT Q2 GUEST BUY/SELL (backend risk): NO owner check seen on: %s — these MUST be guarded server-side before guest visiting ships (hiding buttons in UI alone is not enough)." % "; ".join(FINDINGS["backend_no_check"]))
    print("VERDICT Q2 house owner field: %s." % (FINDINGS["house_owner_field"] or "UNCONFIRMED — see Section 2b"))
    print("VERDICT Q3 FRIENDS: field %s; nearby friends filter %s." % (
        FINDINGS["friends_field"] or "UNCONFIRMED",
        "PRESENT (visible_owners = friends | self)" if FINDINGS["nearby_friends_filter"] else "NOT confirmed — see Section 3 WARNINGs"))
    if FINDINGS["presence_hits"] == 0:
        print("VERDICT Q4 PRESENCE: NONE — no enter/leave/presence/heartbeat/occupant/visitor code found in searched files. Presence must be built new (enter/leave/heartbeat + stale timeout).")
    else:
        print("VERDICT Q4 PRESENCE: %d hits — review Section 4; some hits may be unrelated (e.g. game rooms), so do not assume a house-presence system exists." % FINDINGS["presence_hits"])
    print("VERDICT Q5 ANCHORS: interior-header site %s; LEAVE-call site %s; full anchor lines in Section 5 (enter-call = ENTER onPress block in Section 1)." % (
        "FOUND (name / items-count Text)" if FINDINGS["header_anchor"] else "NOT found",
        "FOUND (LEAVE HOUSE text)" if FINDINGS["leave_anchor"] else "NOT found"))
    print("VERDICT Q6 MARKERS: popup options %s; owner/friend distinction at popup NOT confirmed unless Section 6 shows a player_id compare — expect the same popup for own and friend houses until a guest-mode gate is added." % (
        "FOUND (ENTER/SELL/HIDE/MOVE text)" if FINDINGS["marker_popup"] else "NOT found"))


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print("HOUSE VISIT DIAG: root = %s (read-only, no files modified)" % root)
    files = []
    try:
        section_candidates(root)
    except Exception as exc:
        print("WARNING: section 0 failed with %s (continuing)" % exc)
    try:
        files = walk_frontend(root)
        print("Frontend source files walked: %d" % len(files))
    except Exception as exc:
        print("WARNING: frontend walk failed with %s (continuing)" % exc)
    for fn in (section_enter, section_buysell, section_friends, section_presence, section_anchors, section_markers):
        try:
            if fn in (section_enter, section_buysell, section_presence, section_anchors, section_markers):
                fn(root, files)
            else:
                fn(root)
        except Exception as exc:
            print("WARNING: section %s failed with %s (continuing)" % (fn.__name__, exc))
    try:
        verdicts()
    except Exception as exc:
        print("WARNING: verdicts failed with %s (continuing)" % exc)
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
