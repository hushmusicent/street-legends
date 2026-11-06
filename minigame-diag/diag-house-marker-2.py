#!/usr/bin/env python3
"""House marker follow-up diag (#2): where does the marker die AFTER the batch?

Diag #1 (minigame-diag/diag-house-marker.py, 2026-11-05 23:44 EST) said
verdict=(a): "no houses call in the entity batch -- houses are never
fetched at all." That was WRONG. Its batch parser matched call lines
with `^([A-Za-z_][\\w.]*)\\s*\\(` -- a call wrapped in withTimeout(...)
starts with "withTimeout", so the getNearbyHouses call was counted under
the wrong name and never found. The batch fix patch
(frontend/patch-house-marker-batch-frontend.py) then RAN on /app
(2026-11-06 00:09 EST) and printed: calls=20, mappings=19, with
getNearbyHouses at index 15 and its mapping ALREADY there -- the patch
changed nothing, and the user still sees no house marker. The break
is DOWNSTREAM of the batch.

This diag traces the house from the batch to the screen:
  1. batch call args (live GPS or the frozen stored position?) + the
     return mapping, fully reconciled (every call index -> field, and
     which call is unmapped -- calls=20, mappings=19);
  2. the useMapEntities call site in index.tsx (what feeds its
     latitude/longitude) + where that value is set;
  3. the nearbyHouses derivation + the mapMarkers houses entry, verbatim
     (what type string does each house marker get? any filter?);
  4. live GETs (phone GPS vs the frozen stored position) + a
     marker-build SIMULATION: the entry's logic applied to the live
     house doc by hand, step by step;
  5. GameMap receipt: the markers={...} prop, the markersPayload
     transform, miniGameTypes (is 'house' in the mini-game pool?), the
     house branch;
  6. verdict.

Live facts (parent, 2026-11-05/06): the backend GET /api/houses/nearby
returns his Luxury Mansion (id 88dddba5-52f8-4b8d-926a-7e83aef5dbdf,
player_id 3872dca3-bf7d-4807-8fc5-47c22ba67620, tier 'mansion', name
'Luxury Mansion', lat 41.6821908, lng -83.493423, 6/6 items, stored
false, distance 4m from his phone). The doc has NO `type` field (None),
NO `size` field, NO `owner_id` field (it uses `player_id`). GameMap's
createMarker house branch fires on m.type === 'house' and renders the
house emoji at fixed 72px; the MapMarker type union now includes
'house'. The stored server position is frozen at 41.6368324,-83.4785757
(17h+, last_active 2026-11-05T06:31:04Z) -- ~19km from his phone, far
outside the 2000m houses radius.

Read-only: never edits a file, never restarts anything, only GETs.
Run:  python3 minigame-diag/diag-house-marker-2.py [--root /app]
"""
import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HOST_DEFAULT = "https://gta-quest-map.emergent.host"
PLAYER_ID_DEFAULT = "3872dca3-bf7d-4807-8fc5-47c22ba67620"
LAT_DEFAULT = 41.68221
LNG_DEFAULT = -83.49347
HOUSE_ID_DEFAULT = "88dddba5-52f8-4b8d-926a-7e83aef5dbdf"
FROZEN_LAT = 41.6368324
FROZEN_LNG = -83.4785757


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def print_block(title, lines, start, end):
    print(f"--- {title} (lines {start + 1}-{end}) ---")
    for i in range(start, min(end, len(lines))):
        print(f"{i + 1:>5}: {lines[i]}")


def show_context(lines, idx, before=2, after=2, label=None):
    if label:
        print(f"  [{label}] line {idx + 1}:")
    for j in range(max(0, idx - before), min(len(lines), idx + after + 1)):
        mark = ">>>" if j == idx else "   "
        print(f"  {mark} {j + 1:>5}: {lines[j]}")


def find_lines(lines, pattern, flags=0):
    rx = re.compile(pattern, flags)
    return [(i, l) for i, l in enumerate(lines) if rx.search(l)]


def read_file(path):
    try:
        return Path(path).read_text(errors="ignore").splitlines()
    except OSError:
        return None


def http_get_json(url, timeout=10):
    """(status, parsed_json_or_None, raw_text_or_error). Never raises."""
    req = urllib.request.Request(url, headers={"User-Agent": "house-marker-2-diag/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "ignore")
            try:
                return resp.status, json.loads(raw), raw
            except ValueError:
                return resp.status, None, raw
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode("utf-8", "ignore")
        except Exception:
            raw = ""
        return e.code, None, raw
    except Exception as e:  # timeout, DNS, refused, ...
        return None, None, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- batch parser
# Ported from frontend/patch-house-marker-batch-frontend.py -- the parser
# that CORRECTLY enumerates the live batch (diag #1's parser missed
# withTimeout-wrapped calls: its ^name\( match saw "withTimeout", not
# the inner function name).

def _strip_strings(text):
    return re.sub(r"'[^']*'|\"[^\"]*\"", "''", text)


_CALL_NAME_RE = re.compile(r"^\s*(?:withTimeout\()?([A-Za-z_$][\w$]*)\(")
_MAPPING_RE = re.compile(
    r"^([ \t]*)(\w+): results\[(\d+)\]\.status === 'fulfilled' \? "
    r"results\[\d+\]\.value : \[\],?[ \t]*$", re.M)


def _parse_batch_entries(body):
    """Split a Promise.allSettled array body into call entries.

    Paren-depth aware: a call that spans several lines counts once, and
    a withTimeout(...) wrapper yields the INNER function name.
    Returns a list of {name, text, start, end} (offsets within body).
    """
    lines = body.split("\n")
    entries = []
    depth = 0
    cur_lines = None
    cur_start = 0
    offset = 0
    for ln in lines:
        stripped = ln.strip()
        if cur_lines is None:
            if not stripped or "(" not in _strip_strings(ln):
                offset += len(ln) + 1
                continue
            cur_lines = []
            cur_start = offset
        cur_lines.append(ln)
        code = _strip_strings(ln)
        depth += code.count("(") - code.count(")")
        if depth <= 0 and stripped.endswith(","):
            text = "\n".join(cur_lines)
            m = _CALL_NAME_RE.match(text)
            entries.append({
                "name": m.group(1) if m else "?",
                "text": text,
                "start": cur_start,
                "end": offset + len(ln),
            })
            cur_lines = None
            depth = 0
        offset += len(ln) + 1
    # A trailing entry without a comma (last call in the array).
    if cur_lines:
        text = "\n".join(cur_lines)
        m = _CALL_NAME_RE.match(text)
        entries.append({
            "name": m.group(1) if m else "?",
            "text": text,
            "start": cur_start,
            "end": offset,
        })
    return entries


def _parse_mappings(src):
    """Return (mapping dict index->field, last mapping match)."""
    mapping = {}
    last = None
    for m in _MAPPING_RE.finditer(src):
        mapping[int(m.group(3))] = m.group(2)
        last = m
    return mapping, last


def _find_allsettled_span(lines):
    """Find the Promise.allSettled([ ... ]) span. Returns
    (body_text, body_start_line, body_end_line) or (None, None, None)."""
    for i, l in enumerate(lines):
        if "Promise.allSettled" in l:
            # Find the opening '[' on/after this line.
            open_idx = None
            depth = 0
            for j in range(i, min(i + 3, len(lines))):
                if "[" in lines[j]:
                    open_idx = j
                    depth = lines[j].count("[") - lines[j].count("]")
                    break
            if open_idx is None:
                return None, None, None
            for j in range(open_idx + 1, min(open_idx + 200, len(lines))):
                depth += lines[j].count("[") - lines[j].count("]")
                if depth <= 0:
                    return ("\n".join(lines[open_idx + 1:j]),
                            open_idx + 1, j)
            return ("\n".join(lines[open_idx + 1:]), open_idx + 1,
                    min(open_idx + 200, len(lines)))
    return None, None, None


def _balanced_segment(lines, start_idx, max_lines=80):
    """Extract the text from start_idx until brackets balance back to
    the level they had at the start (for a spread entry ending in
    `})),`). Returns (text, end_line_idx) or (None, None)."""
    depth_paren = depth_brace = depth_brack = 0
    started = False
    parts = []
    for j in range(start_idx, min(start_idx + max_lines, len(lines))):
        ln = lines[j]
        parts.append(ln)
        code = _strip_strings(ln)
        # strip // comments for counting only
        code = re.sub(r"//.*", "", code)
        depth_paren += code.count("(") - code.count(")")
        depth_brace += code.count("{") - code.count("}")
        depth_brack += code.count("[") - code.count("]")
        if not started:
            if "(" in code or "{" in code or "[" in code:
                started = True
            continue
        if depth_paren <= 0 and depth_brace <= 0 and depth_brack <= 0:
            return "\n".join(parts), j
    return None, None


def classify_position_expr(expr):
    """Classify a latitude/longitude expression: live-gps / stored /
    literal / unknown."""
    e = expr or ""
    if re.search(r"currentPosition|livePosition|gpsPosition|\blocation\b",
                 e):
        return "live-gps"
    if re.search(r"player\.position|player\?\.position|playerData|"
                 r"storedPosition|lastKnown|last_position", e):
        return "stored"
    if re.search(r"^-?\d+(\.\d+)?$", e.strip()):
        return "literal"
    if "latitude" in e and "longitude" in e:
        return "hook-params"
    return "unknown"


def eval_expr(expr, doc, var="h"):
    """Evaluate a small marker-field expression against the live doc.
    Returns (value, how) where value is the computed value (or None) and
    how describes what was evaluated. Returns (None, 'unevaluated') for
    shapes this evaluator does not cover."""
    if expr is None:
        return None, "missing expression"
    e = expr.strip().rstrip(",").strip()
    e = re.sub(r"\s+as\s+const\s*$", "", e)
    # string literal
    m = re.match(r"^'([^']*)'$", e) or re.match(r'^"([^"]*)"$', e)
    if m:
        return m.group(1), "string literal"
    # numeric literal
    if re.match(r"^-?\d+(\.\d+)?$", e):
        try:
            return float(e), "numeric literal"
        except ValueError:
            pass
    # `h.field || 'fallback'` / `h.field || fallback`
    m = re.match(rf"^{re.escape(var)}\.([\w$]+)\s*\|\|\s*(.+)$", e)
    if m:
        v, _ = eval_expr(var + "." + m.group(1), doc, var)
        if v:
            return v, f"doc field {m.group(1)} (truthy)"
        fb, _ = eval_expr(m.group(2), doc, var)
        return fb, f"fallback for missing {m.group(1)}"
    # ternary `h.field ? 'a' : 'b'`
    m = re.match(rf"^{re.escape(var)}\.([\w$]+)\s*\?\s*(.+?)\s*:\s*(.+)$", e, re.S)
    if m:
        cond = bool(doc.get(m.group(1)))
        pick = m.group(2) if cond else m.group(3)
        v, _ = eval_expr(pick, doc, var)
        return v, f"ternary on doc.{m.group(1)}={doc.get(m.group(1))!r}"
    # `h.field?.sub` / `h.field.sub`
    m = re.match(rf"^{re.escape(var)}\.([\w$]+)(?:\?\.|\.)([\w$]+)$", e)
    if m:
        parent = doc.get(m.group(1))
        if isinstance(parent, dict):
            return parent.get(m.group(2)), f"doc.{m.group(1)}.{m.group(2)}"
        return None, f"doc.{m.group(1)} is {parent!r}, has no .{m.group(2)}"
    # `h.field`
    m = re.match(rf"^{re.escape(var)}\.([\w$]+)$", e)
    if m:
        return doc.get(m.group(1)), f"doc field {m.group(1)}"
    return None, "unevaluated expression: " + e[:80]


def eval_houses_filter(filter_text, doc, player_id):
    """Evaluate a .filter() on the houses spread against the live doc.
    Returns (drops: True/False/None, reason). None = unevaluated."""
    if doc is None or not filter_text:
        return None, ""
    t = filter_text
    # includes-list on type: ['apartment','cabin','mansion'].includes(h.type)
    m = re.search(r"\[([^\]]+)\]\.includes\(\s*\w+\.type\s*\)", t)
    if m:
        allowed = [a or b for a, b in
                   re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1))]
        if doc.get("type") not in allowed:
            return True, (f"filter requires type in {allowed} but the live "
                          f"doc has type={doc.get('type')!r}")
        return False, ""
    # includes-list on tier
    m = re.search(r"\[([^\]]+)\]\.includes\(\s*\w+\.tier\s*\)", t)
    if m:
        allowed = [a or b for a, b in
                   re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1))]
        if doc.get("tier") not in allowed:
            return True, (f"filter requires tier in {allowed} but the live "
                          f"doc has tier={doc.get('tier')!r}")
        return False, ""
    # owner check: h.owner_id === playerId
    if re.search(r"\w+\.owner_id\s*===?\s*playerId", t):
        if doc.get("owner_id") != player_id:
            return True, ("filter requires owner_id == playerId but the "
                          f"live doc has owner_id={doc.get('owner_id')!r}")
        return False, ""
    # player_id check: h.player_id === playerId
    if re.search(r"\w+\.player_id\s*===?\s*playerId", t):
        if doc.get("player_id") != player_id:
            return True, ("filter requires player_id == playerId but the "
                          f"live doc has player_id={doc.get('player_id')!r}")
        return False, ""
    # truthy type: .filter(h => h.type) / h.type &&
    if re.search(r"=>\s*\w+\.type\b", t) or re.search(r"\w+\.type\s*&&", t):
        if not doc.get("type"):
            return True, ("filter requires a truthy type but the live doc "
                          f"has type={doc.get('type')!r}")
        return False, ""
    # hidden check: !h.hidden
    if re.search(r"!\s*\w+\.hidden", t):
        if doc.get("hidden"):
            return True, ("filter requires !hidden but the live doc has "
                          f"hidden={doc.get('hidden')!r}")
        return False, ""
    # stored check: !h.stored
    if re.search(r"!\s*\w+\.stored", t):
        if doc.get("stored"):
            return True, ("filter requires !stored but the live doc has "
                          f"stored={doc.get('stored')!r}")
        return False, ""
    return None, ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--host", default=HOST_DEFAULT)
    ap.add_argument("--player-id", default=PLAYER_ID_DEFAULT)
    ap.add_argument("--lat", type=float, default=LAT_DEFAULT)
    ap.add_argument("--lng", type=float, default=LNG_DEFAULT)
    ap.add_argument("--house-id", default=HOUSE_ID_DEFAULT)
    args = ap.parse_args()
    root = Path(args.root)

    print("=== house-marker diag #2 (downstream of the batch) ===")
    print(f"player: {args.player_id}  house: {args.house_id}")
    print(f"phone GPS: lat={args.lat} lng={args.lng}  host: {args.host}")
    print(f"frozen stored position: lat={FROZEN_LAT} lng={FROZEN_LNG}")

    missing = []
    f = {}

    hooks_path = root / "frontend/hooks/useMapQueries.ts"
    index_paths = [
        root / "frontend/app/(tabs)/index.tsx",
        root / "frontend/app/index.tsx",
    ]
    gamemap_path = root / "frontend/components/GameMap.tsx"
    api_path = root / "frontend/services/api.ts"
    server_path = root / "backend/server.py"

    hooks_lines = read_file(hooks_path)
    if hooks_lines is None:
        print(f"FILE MISSING: {hooks_path}")
        missing.append("useMapQueries.ts")
        hooks_lines = []
    index_lines = None
    index_path = None
    for p in index_paths:
        lines = read_file(p)
        if lines is not None:
            index_lines = lines
            index_path = p
            break
    if index_lines is None:
        print(f"FILE MISSING: {index_paths[0]} (and {index_paths[1]})")
        missing.append("index.tsx")
        index_lines = []
    gamemap_lines = read_file(gamemap_path)
    if gamemap_lines is None:
        print(f"FILE MISSING: {gamemap_path}")
        missing.append("GameMap.tsx")
        gamemap_lines = []
    api_lines = read_file(api_path)
    if api_lines is None:
        print(f"FILE MISSING (non-critical): {api_path}")
        missing.append("api.ts")
        api_lines = []
    server_lines = read_file(server_path)
    if server_lines is None:
        print(f"FILE MISSING (non-critical): {server_path}")
        missing.append("server.py")
        server_lines = []

    # ------------------------------------------------ check 1: batch + mapping
    print()
    print("=== 1. entity batch + return mapping (useMapQueries.ts) ===")
    batch_lines = None
    batch_file = None
    for cand_path, cand_lines in [(hooks_path, hooks_lines)] + [
        (p, read_file(p)) for p in index_paths
    ]:
        if cand_lines and any("Promise.allSettled" in l for l in cand_lines):
            batch_file = cand_path
            batch_lines = cand_lines
            break
    entries = []
    mapping = {}
    houses_call = None
    if batch_file is None:
        print("BATCH NOT FOUND: no Promise.allSettled block in "
              "useMapQueries.ts or index.tsx")
        missing.append("batch")
    else:
        print(f"batch lives in: {batch_file}")
        body, bstart, bend = _find_allsettled_span(batch_lines)
        if body is None:
            print("BATCH SPAN NOT FOUND: Promise.allSettled present but "
                  "its [ ... ] array could not be located")
            missing.append("batch-span")
        else:
            entries = _parse_batch_entries(body)
            print(f"batch calls: {len(entries)}")
            for idx, e in enumerate(entries):
                one = " ".join(e["text"].split())
                print(f"  [{idx}] {one[:160]}")
            for idx, e in enumerate(entries):
                if e["name"] == "getNearbyHouses":
                    houses_call = (idx, e)
                    break
            if houses_call:
                idx, e = houses_call
                one = " ".join(e["text"].split())
                print(f"HOUSES CALL: index {idx}: {one}")
                inner = e["text"]
                call_args = inner[inner.find("(") + 1: inner.rfind(")")]
                print(f"  call args: {call_args.strip()}")
                if re.search(r"player\.position|player\?\.position|"
                             r"storedPosition", call_args):
                    print("  call args source: STORED player position "
                          "(player.position / storedPosition in the call)")
                    f["houses_args_source"] = "stored"
                elif "latitude" in call_args and "longitude" in call_args:
                    print("  call args source: hook params (latitude, "
                          "longitude) -- see check 2 for what feeds them")
                    f["houses_args_source"] = "hook-params"
                else:
                    print("  call args source: UNKNOWN -- see args above")
                    f["houses_args_source"] = "unknown"
                print("  playerId passed to getNearbyHouses: "
                      + ("YES" if "playerId" in call_args else "NO"))
                f["houses_call_has_playerid"] = "playerId" in call_args
            else:
                print("HOUSES CALL: NONE in the batch")
                f["houses_args_source"] = None
            mapping, last_map = _parse_mappings("\n".join(batch_lines))
            # Print the return block verbatim.
            rstart = None
            for i, l in enumerate(batch_lines):
                if re.search(r"^\s*return\s*\{", l):
                    rstart = i
                    break
            if rstart is not None:
                depth = 0
                rend = min(rstart + 80, len(batch_lines))
                for j in range(rstart, rend):
                    depth += batch_lines[j].count("{") - batch_lines[j].count("}")
                    if depth <= 0 and j > rstart:
                        rend = j + 1
                        break
                print_block("return mapping", batch_lines, rstart, rend)
            else:
                print("RETURN MAPPING BLOCK NOT FOUND after the batch")
            print("--- reconciliation: call index -> call name -> mapped field ---")
            for idx, e in enumerate(entries):
                print(f"  [{idx}] {e['name']:<22} -> "
                      f"{mapping.get(idx, 'UNMAPPED')}")
            unmapped = [i for i in range(len(entries)) if i not in mapping]
            print(f"UNMAPPED call indices (fetched, never turned into a "
                  f"field): {unmapped}")
            dup_players = [i for i, e in enumerate(entries)
                           if e["name"] == "getNearbyPlayers"]
            if len(dup_players) > 1:
                print(f"duplicate getNearbyPlayers at indices {dup_players}: "
                      + ", ".join(
                          f"[{i}] -> {mapping.get(i, 'UNMAPPED')}"
                          for i in dup_players))
            f["entries"] = entries
            f["mapping"] = mapping
            f["unmapped"] = unmapped
            f["houses_call"] = houses_call
            iface = find_lines(batch_lines, r"interface\s+MapEntitiesData")
            if iface:
                istart = iface[0][0]
                iend = min(istart + 40, len(batch_lines))
                for j in range(istart, iend):
                    if j > istart and batch_lines[j].strip() == "}":
                        iend = j + 1
                        break
                print("interface declares a houses field: "
                      + ("YES" if any("houses" in batch_lines[j]
                                       for j in range(istart, iend))
                         else "NO"))
                f["iface_has_houses"] = any(
                    "houses" in batch_lines[j]
                    for j in range(istart, iend))
            imp = [l for l in find_lines(batch_lines, r"getNearbyHouses")
                   if "import" in l[1]]
            print("getNearbyHouses import: "
                  + (str([l.strip() for _, l in imp]) if imp else "NONE"))

    # ------------------------------------------------ check 2: call site
    print()
    print("=== 2. useMapEntities call site (index.tsx) ===")
    f["callsite_source"] = None
    if index_lines:
        print(f"index file: {index_path}")
        um = find_lines(index_lines, r"useMapEntities\s*\(\s*\{")
        if um:
            ustart = um[0][0]
            # brace-balance the object literal
            depth = 0
            uend = min(ustart + 30, len(index_lines))
            for j in range(ustart, uend):
                depth += index_lines[j].count("{") - index_lines[j].count("}")
                if depth <= 0 and j > ustart:
                    uend = j + 1
                    break
            print_block("useMapEntities call", index_lines, ustart, uend)
            block = "\n".join(index_lines[ustart:uend])
            lat_m = re.search(r"latitude\s*:\s*([^\n,]+)", block)
            lng_m = re.search(r"longitude\s*:\s*([^\n,]+)", block)
            lat_e = lat_m.group(1).strip() if lat_m else None
            lng_e = lng_m.group(1).strip() if lng_m else None
            print(f"  latitude arg: {lat_e}")
            print(f"  longitude arg: {lng_e}")
            src_lat = classify_position_expr(lat_e)
            src_lng = classify_position_expr(lng_e)
            print(f"  args source: lat={src_lat} lng={src_lng}")
            if src_lat == "stored" or src_lng == "stored":
                f["callsite_source"] = "stored"
            elif src_lat == "live-gps" or src_lng == "live-gps":
                f["callsite_source"] = "live-gps"
            elif src_lat == "hook-params" or src_lng == "hook-params":
                f["callsite_source"] = "hook-params"
            else:
                f["callsite_source"] = "unknown"
            en = re.search(r"enabled\s*:\s*([^\n,]+)", block)
            if en:
                print(f"  enabled: {en.group(1).strip()}")
            # Where does currentPosition come from?
            cp = find_lines(index_lines, r"currentPosition")
            print(f"  'currentPosition' occurrences in index.tsx: {len(cp)}")
            setters = find_lines(index_lines, r"setCurrentPosition\s*\(")
            for i, l in setters:
                show_context(index_lines, i, before=2, after=1,
                             label="setCurrentPosition")
            pp = find_lines(index_lines, r"player\?\.position|player\.position")
            if pp:
                print("  'player.position' occurrences (frozen stored "
                      "position reads):")
                for i, l in pp:
                    show_context(index_lines, i, before=1, after=1)
            else:
                print("  'player.position' occurrences: NONE")
        else:
            print("useMapEntities call: NOT FOUND in index.tsx")
            missing.append("callsite")
    else:
        print("index.tsx not readable -- check 2 skipped")

    # ------------------------------------------------ check 3: derivation + entry
    print()
    print("=== 3. nearbyHouses derivation + mapMarkers houses entry ===")
    f["mapmarkers_has_houses"] = None
    f["houses_marker_type_expr"] = None
    f["houses_filter"] = None
    f["houses_entry"] = None
    if index_lines:
        deriv = find_lines(index_lines, r"nearbyHouses")
        if deriv:
            print("nearbyHouses occurrences:")
            for i, l in deriv:
                show_context(index_lines, i, before=1, after=1)
            # the derivation line itself
            dline = next((l for _, l in deriv if "nearbyHouses =" in l or
                          "nearbyHouses=" in l), None)
            if dline:
                print(f"  derivation: {dline.strip()}")
                f["derivation"] = dline.strip()
        else:
            print("nearbyHouses: NO occurrences in index.tsx")
        mm = find_lines(index_lines, r"mapMarkers\s*=\s*useMemo")
        if mm:
            mstart = mm[0][0]
            mend = None
            for j in range(mstart, min(mstart + 400, len(index_lines))):
                if re.match(r"\s*\],\s*\[", index_lines[j]):
                    for k in range(j, min(j + 4, len(index_lines))):
                        if ");" in index_lines[k]:
                            mend = k + 1
                            break
                    break
            if mend is None:
                mend = min(mstart + 400, len(index_lines))
            block = "".join(index_lines[mstart:mend])
            spreads = re.findall(r"\.\.\.nearby(\w+)", block)
            print(f"mapMarkers spreads (nearby* lists turned into markers): "
                  f"{spreads}")
            types = re.findall(r"type:\s*'([^']+)'", block)
            print(f"mapMarkers literal marker type strings: "
                  f"{sorted(set(types))}")
            has_houses = "nearbyHouses" in block
            print(f"mapMarkers has a houses entry: "
                  f"{'YES' if has_houses else 'NO'}")
            f["mapmarkers_has_houses"] = has_houses
            if has_houses:
                hlines = [i for i in range(mstart, mend)
                          if "nearbyHouses" in index_lines[i]]
                seg, send = _balanced_segment(index_lines, hlines[0])
                if seg is None:
                    seg = "\n".join(index_lines[hlines[0]:hlines[0] + 12])
                print("--- mapMarkers houses entry (verbatim) ---")
                print(seg)
                f["houses_entry"] = seg
                # filter?
                fm = re.search(r"\.filter\s*\(", seg)
                if fm:
                    fstart = seg.find(".filter(")
                    depth = 0
                    fend = None
                    for k in range(fstart, len(seg)):
                        if seg[k] == "(":
                            depth += 1
                        elif seg[k] == ")":
                            depth -= 1
                            if depth == 0:
                                fend = k + 1
                                break
                    filt = seg[fstart:fend] if fend else seg[fstart:]
                    print(f"FILTER on the houses spread: {filt}")
                    f["houses_filter"] = filt
                else:
                    print("FILTER on the houses spread: NONE")
                # type expression
                tm = re.search(r"type:\s*([^\n,]+)", seg)
                if tm:
                    print(f"houses marker type expression: "
                          f"{tm.group(1).strip()}")
                    f["houses_marker_type_expr"] = tm.group(1).strip()
                else:
                    print("houses marker type expression: NOT FOUND in "
                          "the entry")
                # coordinate expression
                cm = re.search(r"coordinate:\s*\{", seg)
                if cm:
                    cstart = seg.find("coordinate:")
                    depth = 0
                    cend = None
                    for k in range(seg.find("{", cstart), len(seg)):
                        if seg[k] == "{":
                            depth += 1
                        elif seg[k] == "}":
                            depth -= 1
                            if depth == 0:
                                cend = k + 1
                                break
                    coord = seg[cstart:cend] if cend else seg[cstart:]
                    print(f"houses marker coordinate: {coord}")
                    f["houses_coord"] = coord
                else:
                    cm2 = re.search(r"coordinate:\s*([^\n,]+)", seg)
                    print("houses marker coordinate: "
                          + (cm2.group(1).strip() if cm2
                             else "NOT FOUND in the entry"))
                    f["houses_coord"] = (cm2.group(1).strip() if cm2
                                         else None)
                # id expression
                im = re.search(r"\bid:\s*([^\n,]+)", seg)
                if im:
                    print(f"houses marker id expression: "
                          f"{im.group(1).strip()}")
                    f["houses_id_expr"] = im.group(1).strip()
            # deps array: is nearbyHouses in it?
            deps_m = re.search(r"\],\s*\[(.*?)\]\s*\);",
                               block, re.S)
            if deps_m:
                print(f"mapMarkers deps: [{deps_m.group(1).strip()}]")
                print("  nearbyHouses in deps: "
                      + ("YES" if "nearbyHouses" in deps_m.group(1)
                         else "NO"))
                f["deps_has_houses"] = "nearbyHouses" in deps_m.group(1)
        else:
            print("mapMarkers useMemo: NOT FOUND in index.tsx")
    else:
        print("index.tsx not readable -- check 3 skipped")

    # ------------------------------------------------ check 4: live GETs + simulation
    print()
    print("=== 4. live GETs + marker-build simulation ===")
    live_doc = None
    phone_count = None
    frozen_count = None
    stored_pos = None
    # (a) what the batch SHOULD receive: phone GPS + playerId
    url_phone = (f"{args.host}/api/houses/nearby?latitude={args.lat}"
                 f"&longitude={args.lng}&player_id={args.player_id}")
    status, data, raw = http_get_json(url_phone, timeout=10)
    print(f"GET (phone GPS) {url_phone}")
    print(f"  status: {status}")
    if data is not None:
        docs = data if isinstance(data, list) else data.get("houses") or []
        phone_count = len(docs)
        print(f"  houses returned: {phone_count}")
        for d in docs:
            if isinstance(d, dict) and d.get("id") == args.house_id:
                live_doc = d
                break
        if live_doc is None and docs:
            live_doc = docs[0] if isinstance(docs[0], dict) else None
            print("  (house id not in response -- showing first doc)")
    else:
        print(f"  GET failed / not JSON: {str(raw)[:300]}")
    # (b) what the batch receives IF it passes the frozen stored position
    url_frozen = (f"{args.host}/api/houses/nearby?latitude={FROZEN_LAT}"
                  f"&longitude={FROZEN_LNG}&player_id={args.player_id}")
    status_f, data_f, raw_f = http_get_json(url_frozen, timeout=10)
    print(f"GET (frozen stored position) {url_frozen}")
    print(f"  status: {status_f}")
    if data_f is not None:
        docs_f = data_f if isinstance(data_f, list) else data_f.get("houses") or []
        frozen_count = len(docs_f)
        print(f"  houses returned: {frozen_count}")
    else:
        print(f"  GET failed / not JSON: {str(raw_f)[:300]}")
    # (c) the stored position itself, live
    url_p = f"{args.host}/api/players/{args.player_id}"
    status_p, data_p, raw_p = http_get_json(url_p, timeout=10)
    print(f"GET {url_p} -> status: {status_p}")
    if isinstance(data_p, dict):
        stored_pos = data_p.get("position") or {}
        print(f"  stored position: {stored_pos}")
        print(f"  last_active: {data_p.get('last_active')}")
        try:
            d_m = haversine_m(float(stored_pos["latitude"]),
                              float(stored_pos["longitude"]),
                              args.lat, args.lng)
            print(f"  stored position -> phone GPS: {d_m:.0f} m")
        except (KeyError, TypeError, ValueError):
            pass
    f["phone_count"] = phone_count
    f["frozen_count"] = frozen_count
    f["stored_pos"] = stored_pos

    # --- simulation: the entry's logic applied to the live doc
    print()
    print("--- simulation: houses entry logic applied to the live doc ---")
    sim = {"produced": None, "type": None, "coordinate": None, "dropped_at": None}
    if live_doc is None:
        print("SIMULATION: no live doc -- cannot simulate (the phone-GPS "
              "GET returned no house)")
        sim["dropped_at"] = "no-live-doc"
    elif not f.get("houses_entry"):
        print("SIMULATION: no houses entry in mapMarkers -- nothing to "
              "simulate (no marker is ever built)")
        sim["dropped_at"] = "no-entry"
    else:
        print("live doc fields used by the entry:")
        for field in ["id", "type", "tier", "size", "owner_id", "player_id",
                      "hidden", "stored", "latitude", "longitude", "name"]:
            print(f"  doc.{field} = {live_doc.get(field)!r}")
        try:
            dist_m = haversine_m(args.lat, args.lng,
                                 float(live_doc["latitude"]),
                                 float(live_doc["longitude"]))
            print(f"  phone -> house distance: {dist_m:.1f} m")
        except (KeyError, TypeError, ValueError):
            print("  phone -> house distance: CANNOT COMPUTE")
        # step 1: derivation -- which entities field does nearbyHouses read?
        deriv = f.get("derivation") or ""
        if "entitiesData?.houses" in deriv or "entitiesData.houses" in deriv:
            print("  step 1 derivation: nearbyHouses reads "
                  "entitiesData?.houses -- OK")
        elif deriv:
            print(f"  step 1 derivation: nearbyHouses reads something "
                  f"else: {deriv.strip()} -- CHECK whether that field is "
                  f"ever filled")
            sim["dropped_at"] = "derivation"
        # step 2: filter
        if sim["dropped_at"] is None and f.get("houses_filter"):
            drops, why = eval_houses_filter(f["houses_filter"], live_doc,
                                            args.player_id)
            print(f"  step 2 filter: {f['houses_filter']}")
            if drops:
                print(f"    -> DROPS the doc: {why}")
                sim["dropped_at"] = "filter"
            elif drops is False:
                print("    -> passes")
            else:
                print("    -> cannot evaluate automatically (see filter "
                      "text above -- read it against the doc)")
        elif sim["dropped_at"] is None:
            print("  step 2 filter: none")
        # step 3: build the marker
        if sim["dropped_at"] is None:
            entry = f["houses_entry"]
            tm = re.search(r"type:\s*([^\n,]+)", entry)
            type_val, type_how = (None, "no type expression in entry")
            if tm:
                type_val, type_how = eval_expr(tm.group(1).strip(),
                                              live_doc, "h")
            print(f"  step 3 type: expression "
                  f"'{tm.group(1).strip() if tm else '?'}' -> "
                  f"{type_val!r} ({type_how})")
            coord_val = None
            coord_how = "no coordinate expression in entry"
            cm = re.search(r"coordinate:\s*\{", entry)
            if cm:
                cstart = entry.find("coordinate:")
                depth = 0
                cend = None
                for k in range(entry.find("{", cstart), len(entry)):
                    if entry[k] == "{":
                        depth += 1
                    elif entry[k] == "}":
                        depth -= 1
                        if depth == 0:
                            cend = k + 1
                            break
                coord_txt = entry[cstart:cend] if cend else entry[cstart:]
                lat_m = re.search(r"latitude\s*:\s*([^\n,}]+)", coord_txt)
                lng_m = re.search(r"longitude\s*:\s*([^\n,}]+)", coord_txt)
                lat_v, lat_h = eval_expr(lat_m.group(1), live_doc, "h") \
                    if lat_m else (None, "no latitude in coordinate")
                lng_v, lng_h = eval_expr(lng_m.group(1), live_doc, "h") \
                    if lng_m else (None, "no longitude in coordinate")
                coord_val = (lat_v, lng_v)
                coord_how = f"lat {lat_v!r} ({lat_h}); lng {lng_v!r} ({lng_h})"
            else:
                cm2 = re.search(r"coordinate:\s*([^\n,]+)", entry)
                if cm2:
                    cv, ch = eval_expr(cm2.group(1).strip(), live_doc, "h")
                    coord_val = cv
                    coord_how = f"coordinate expression -> {cv!r} ({ch})"
            print(f"  step 3 coordinate: {coord_how}")
            id_m = re.search(r"\bid:\s*([^\n,]+)", entry)
            id_v, _ = eval_expr(id_m.group(1), live_doc, "h") \
                if id_m else (live_doc.get("id"), "doc.id fallback")
            print(f"  step 3 id: {id_v!r}")
            if coord_val is None or (isinstance(coord_val, tuple)
                                     and (coord_val[0] is None
                                          or coord_val[1] is None)):
                print("  -> DROPPED at coordinate: the marker has no "
                      "usable lat/lng, so GameMap's markersPayload "
                      "(m.coordinate.latitude) would throw -- and if it "
                      "threw, ALL markers would die, so this alone cannot "
                      "explain houses-only absence; read the coordinate "
                      "expression above")
                sim["dropped_at"] = "coordinate"
            elif type_val is None:
                print("  -> DROPPED at type: the type expression resolves "
                      "to None -- the marker is built with no usable type, "
                      "so GameMap's house branch (m.type === 'house') can "
                      "never fire")
                sim["dropped_at"] = "type-none"
            else:
                sim["produced"] = {"id": id_v, "type": type_val,
                                   "coordinate": coord_val}
                sim["type"] = type_val
                sim["coordinate"] = coord_val
                print(f"  SIMULATION: marker WOULD be produced: "
                      f"id={id_v!r} type={type_val!r} "
                      f"coordinate={coord_val!r}")
                if type_val != "house":
                    print(f"    -> but type is {type_val!r}, not 'house' "
                          f"-- GameMap's house branch will NOT fire")
    f["sim"] = sim

    # ------------------------------------------------ check 5: GameMap receipt
    print()
    print("=== 5. GameMap receipt (index.tsx -> GameMap.tsx) ===")
    f["gamemap_receives_mapmarkers"] = None
    f["house_in_minigame_types"] = None
    f["gamemap_house_branch"] = None
    if index_lines:
        gm = find_lines(index_lines, r"<GameMap")
        if gm:
            gi = gm[0][0]
            # the opening tag may span lines; print until '/>' or '>'
            gend = gi
            for j in range(gi, min(gi + 12, len(index_lines))):
                gend = j
                if "/>" in index_lines[j] or index_lines[j].strip().endswith(">"):
                    break
            print_block("GameMap usage (index.tsx)", index_lines, gi, gend + 1)
            tag = "\n".join(index_lines[gi:gend + 1])
            mm2 = re.search(r"markers\s*=\s*\{([^}]*)\}", tag)
            if mm2:
                print(f"  markers prop: markers={{{mm2.group(1).strip()}}}")
                expr = mm2.group(1).strip()
                if expr == "mapMarkers":
                    print("  GameMap receives the full mapMarkers list")
                    f["gamemap_receives_mapmarkers"] = True
                elif "mapMarkers" in expr and ".filter(" in expr:
                    print("  GameMap receives mapMarkers FILTERED -- "
                          "print the filter:")
                    print(f"    {expr}")
                    if "'house'" in expr or '"house"' in expr:
                        print("    -> the filter mentions 'house'")
                    f["gamemap_receives_mapmarkers"] = "filtered"
                elif "mapMarkers" in expr:
                    print("  GameMap receives mapMarkers, transformed: "
                          f"{expr}")
                    f["gamemap_receives_mapmarkers"] = "transformed"
                else:
                    print("  GameMap does NOT receive mapMarkers -- it "
                          f"receives: {expr}")
                    f["gamemap_receives_mapmarkers"] = False
            else:
                print("  markers prop: NOT FOUND in the GameMap tag")
                f["gamemap_receives_mapmarkers"] = False
        else:
            print("<GameMap usage: NOT FOUND in index.tsx")
    if gamemap_lines:
        mg = find_lines(gamemap_lines, r"miniGameTypes\s*=")
        if mg:
            i, l = mg[0]
            print(f"miniGameTypes line {i + 1}: {l.strip()}")
            has_house = "'house'" in l or '"house"' in l
            print(f"  'house' in miniGameTypes: {'YES' if has_house else 'NO'}")
            if has_house:
                print("  -> house markers are routed to the mini-game pool: "
                      "only ONE random mini-game marker renders at a time")
            f["house_in_minigame_types"] = has_house
        else:
            print("miniGameTypes: NOT FOUND in GameMap.tsx")
        # markersPayload transform
        mp = find_lines(gamemap_lines, r"markers\.map\s*\(\s*m\s*=>")
        if mp:
            mi = mp[0][0]
            print_block("markersPayload transform (GameMap.tsx)",
                        gamemap_lines, mi, min(mi + 12, len(gamemap_lines)))
            block = "\n".join(gamemap_lines[mi:mi + 12])
            print("  payload lat: "
                  + ("m.coordinate.latitude" if "m.coordinate.latitude" in block
                     else "SEE BLOCK ABOVE"))
            print("  payload lng: "
                  + ("m.coordinate.longitude" if "m.coordinate.longitude" in block
                     else "SEE BLOCK ABOVE"))
        else:
            print("markersPayload transform: NOT FOUND in GameMap.tsx")
        # MapMarker interface
        mm3 = find_lines(gamemap_lines, r"interface\s+MapMarker")
        if mm3:
            istart = mm3[0][0]
            iend = min(istart + 20, len(gamemap_lines))
            for j in range(istart, iend):
                if j > istart and gamemap_lines[j].strip() == "}":
                    iend = j + 1
                    break
            print("MapMarker type union includes 'house': "
                  + ("YES" if any("'house'" in gamemap_lines[j]
                                   for j in range(istart, iend)) else "NO"))
        # house branch
        branch = find_lines(gamemap_lines,
                            r"\}\s*else if\s*\(\s*m\.type\s*===?\s*'house'\s*\)")
        branch += find_lines(gamemap_lines,
                             r'\}\s*else if\s*\(\s*m\.type\s*===?\s*"house"\s*\)')
        if branch:
            bi = branch[0][0]
            print(f"house branch in createMarker: line {bi + 1}")
            print_block("house branch", gamemap_lines, bi,
                        min(bi + 4, len(gamemap_lines)))
            f["gamemap_house_branch"] = True
        else:
            print("house branch in createMarker: NONE -- a 'house' marker "
                  "falls through to the generic fallback")
            f["gamemap_house_branch"] = False
        colors = find_lines(gamemap_lines, r"markerColors\s*=")
        icons = find_lines(gamemap_lines, r"markerIcons\s*=")
        for label, found in [("markerColors", colors), ("markerIcons", icons)]:
            if found:
                i, l = found[0]
                print(f"{label} line {i + 1}: {l.strip()}")
                print(f"  has a house entry: "
                      + ("YES" if ("'house'" in l or "house:" in l) else "NO"))

    # ------------------------------------------------ check 6: verdict
    print()
    print("=== 6. VERDICT ===")
    verdict = None
    reason = ""
    critical = [m for m in missing
                if m in ("useMapQueries.ts", "index.tsx", "GameMap.tsx",
                         "batch")]
    if critical:
        verdict = "undetermined"
        reason = ("critical files missing: " + ", ".join(critical)
                  + " -- cannot tell which link is broken")
    # (a) batch calls with the wrong position
    if verdict is None and (f.get("callsite_source") == "stored"
                            or f.get("houses_args_source") == "stored"):
        if f.get("frozen_count") == 0 and f.get("phone_count"):
            verdict = "a"
            reason = ("the batch is fed the STORED/frozen position "
                      f"(see check 2) -- the houses endpoint returns "
                      f"{f['frozen_count']} houses from the frozen spot "
                      f"but {f['phone_count']} from the phone GPS, and "
                      f"the house is ~19km from the frozen spot, far "
                      f"outside the 2000m radius")
        elif f.get("frozen_count") == 0:
            verdict = "a"
            reason = ("the batch is fed the STORED/frozen position "
                      "(see check 2) and the houses endpoint returns 0 "
                      "houses from that spot -- the house is outside "
                      "the radius from there")
        else:
            verdict = "a"
            reason = ("the batch is fed the STORED/frozen position "
                      "(see check 2); the frozen-spot GET still returns "
                      "houses, so the position alone does not explain "
                      "it -- but the stored position is the wrong "
                      "source and must be fixed first")
    # (b) results[15] mapped to the wrong field or dropped
    if verdict is None and f.get("houses_call") is not None:
        idx = f["houses_call"][0]
        mapped_field = f["mapping"].get(idx)
        if mapped_field is None:
            verdict = "b"
            reason = (f"getNearbyHouses is call [{idx}] but results[{idx}] "
                      f"has NO return mapping (unmapped indices: "
                      f"{f['unmapped']}) -- the house is fetched and "
                      f"thrown away")
        elif mapped_field != "houses":
            verdict = "b"
            reason = (f"results[{idx}] is mapped to "
                      f"'{mapped_field}', not 'houses' -- the "
                      f"nearbyHouses derivation reads "
                      f"entitiesData?.houses, which stays empty")
    if verdict is None and f.get("houses_call") is None:
        verdict = "b"
        reason = ("no getNearbyHouses call in the batch at all (diag #1 "
                  "was right after all, on a different parse) -- "
                  "houses are never fetched")
    # (c) entry drops / mistypes the doc (no marker built)
    if verdict is None and sim["dropped_at"] in ("derivation", "filter",
                                                 "coordinate", "type-none"):
        verdict = "c"
        if sim["dropped_at"] == "derivation":
            reason = ("the nearbyHouses derivation does not read "
                      "entitiesData?.houses -- see the derivation line "
                      "in check 3; the mapped field is never read")
        elif sim["dropped_at"] == "filter":
            reason = ("the houses entry's filter drops the live doc -- "
                      "see the simulation in check 4")
        elif sim["dropped_at"] == "coordinate":
            reason = ("the houses entry builds a marker with no usable "
                      "lat/lng -- see the simulation in check 4")
        else:
            reason = ("the houses entry's type expression resolves to "
                      "None (doc has no type field) -- the marker is "
                      "built with no usable type, so GameMap's house "
                      "branch can never fire")
    if verdict is None and sim["dropped_at"] == "no-entry":
        verdict = "c"
        reason = ("mapMarkers has NO houses entry -- the data arrives "
                  "and is never turned into a marker")
    if verdict is None and sim["dropped_at"] == "no-live-doc":
        verdict = "c"
        reason = ("the phone-GPS houses GET returned no house doc -- "
                  "the backend has nothing to render at this spot")
    # (d) markers built but never passed to GameMap
    if verdict is None and f.get("gamemap_receives_mapmarkers") in (False, "filtered"):
        verdict = "d"
        reason = ("the houses markers are built but GameMap does not "
                  "receive them -- see the markers={...} prop in "
                  "check 5")
    # (e) markers passed but the branch doesn't fire
    if verdict is None and sim.get("produced") is not None \
            and sim.get("type") != "house":
        verdict = "e"
        reason = (f"the simulation produces a marker with type "
                  f"{sim['type']!r}, not 'house' -- it reaches GameMap "
                  f"but the house branch (m.type === 'house') never "
                  f"fires")
    if verdict is None and f.get("house_in_minigame_types"):
        verdict = "e"
        reason = ("'house' is in GameMap's miniGameTypes -- house "
                  "markers are routed to the mini-game pool, where "
                  "only ONE random mini-game marker renders at a time, "
                  "so the house is usually hidden")
    if verdict is None and f.get("gamemap_house_branch") is False:
        verdict = "e"
        reason = ("no house branch in GameMap's createMarker -- a "
                  "'house' marker falls through to the generic '?' "
                  "fallback instead of the house icon")
    # (f) healthy
    if verdict is None:
        verdict = "f"
        reason = ("batch maps houses, the entry builds a 'house' "
                  "marker with a complete coordinate, GameMap receives "
                  "it and has a house branch -- the marker should "
                  "render. Cause is on-device: stale Expo Go bundle. "
                  "Force a fresh reload (shake -> Reload, or clear "
                  "the Expo Go cache and reopen), then move ~50m away "
                  "from the house and look back -- if it appears, the "
                  "build was stale.")
    print(f"VERDICT: ({verdict}) {reason}")
    print()
    if missing:
        print("HOUSE_MARKER_2_DIAG_PARTIAL missing=" + ",".join(missing)
              + f" verdict=({verdict})")
    else:
        print(f"HOUSE_MARKER_2_DIAG_OK verdict=({verdict})")


if __name__ == "__main__":
    main()
