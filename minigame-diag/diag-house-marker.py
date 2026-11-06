#!/usr/bin/env python3
"""Street Legends live probe: why the player's house marker does not render
on the map.

Run from repo root (/app):  python3 minigame-diag/diag-house-marker.py
Optional args: --root PATH --host URL --player-id ID --lat F --lng F
--house-id ID.

READ-ONLY: reads frontend/backend files and does two read-only GETs
(/api/houses/nearby, /api/houses/<id>) on the public host. Never edits
anything, never restarts anything, never calls a state-changing endpoint.
Always finishes with a summary line (HOUSE_MARKER_DIAG_OK or
HOUSE_MARKER_DIAG_PARTIAL). Short timeouts on every network call; never
hangs.

WHY: the backend HAS the house and returns it -- GET
/api/houses/nearby for his spot returns count 1, his Luxury Mansion
(88dddba5-52f8-4b8d-926a-7e83aef5dbdf) at 41.6821908,-83.493423, 4.4m
from his phone -- but no marker shows on the map, and he says "We made
the house bigger", so a size/type field may matter. Two live facts make
this worth checking piece by piece:
  * the returned house doc's `type` field is None and `owner_id` reads
    empty -- the frontend may key the marker on a field that is missing;
  * the Fiend follow-up (2026-11-05) found the batch's 16th call was
    getNearbyHouses at index 15 WITH NO return mapping -- fetched but
    possibly never rendered.

Checks, in order:
  1. The entity batch + return mapping (useMapQueries.ts): the
     getNearbyHouses call, its index and args (live GPS or stored
     position?), and whether results[N] is mapped to a field.
  2. index.tsx: the nearbyHouses derivation, the mapMarkers useMemo
     (is there a houses entry? what `type` string? any filter?), and
     the handleMarkerPress 'house' case.
  3. GameMap.tsx: the house marker branch (markerColors / markerIcons
     house entries, the createMarker else-if chain, marker sizing, and
     whether sizing depends on a house size/type field), plus the
     player marker's zIndexOffset (1000 in the snapshot -- a house 4.4m
     away sits under the player dot).
  4. The live house doc (GET /api/houses/nearby + /api/houses/<id>),
     printed verbatim, compared field by field against what the marker
     path needs (type None / owner empty / size missing / hidden).
  5. The render path trace (batch -> mapped field -> nearbyHouses ->
     mapMarkers -> GameMap prop -> createMarker) and the backend
     visibility rule (owner + friends only) as it exists live.
  6. Verdict: (a) houses call unmapped / never turned into a marker,
     (b) a filter/branch skips his house (condition + failing value),
     (c) marker created but invisible/covered (zero size from a missing
     size field, generic '?' fallback, under the player dot),
     (d) houses come from a separate path that is broken,
     (e) healthy -- the marker should render (on-device stale build).
"""
import argparse
import json
import math
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

PLAYER_ID_DEFAULT = "3872dca3-bf7d-4807-8fc5-47c22ba67620"
HOUSE_ID_DEFAULT = "88dddba5-52f8-4b8d-926a-7e83aef5dbdf"
LAT_DEFAULT = 41.68221
LNG_DEFAULT = -83.49347
HOST_DEFAULT = "https://gta-quest-map.emergent.host"


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def print_block(title, lines, start, end):
    """Print lines[start:end] (0-based, end exclusive) with 1-based nos."""
    print(f"===== {title} (lines {start + 1}-{end}) =====")
    for idx in range(start, end):
        print(f"{idx + 1:>6}: {lines[idx]}")
    print(f"===== END {title} =====")


def show_context(lines, idx, before=2, after=2, label=None):
    if label:
        print(f"--- {label} (line {idx + 1}) ---")
    lo = max(0, idx - before)
    hi = min(len(lines), idx + after + 1)
    for i in range(lo, hi):
        mark = ">>>" if i == idx else "   "
        print(f"{mark} {i + 1:>6}: {lines[i]}")


def find_lines(lines, pattern, flags=0):
    return [(i, lines[i]) for i, l in enumerate(lines)
            if re.search(pattern, l, flags)]


def read_file(path):
    try:
        return Path(path).read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return None


def http_get_json(url, timeout=10):
    """Read-only GET returning (status, parsed_json_or_None, raw_or_error)."""
    req = urllib.request.Request(url, headers={"User-Agent": "StreetLegends-diag/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw), raw
            except json.JSONDecodeError:
                return resp.status, None, raw
    except urllib.error.HTTPError as e:
        try:
            return e.code, None, e.read().decode("utf-8", "replace")
        except Exception:
            return e.code, None, ""
    except Exception as e:  # timeout, DNS, refused, ...
        return None, None, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- batch
def parse_batch_calls(lines, start_idx):
    """Enumerate the Promise.allSettled([ ... ]) calls starting at the
    line containing 'Promise.allSettled'. Returns (calls, end_idx) where
    calls is a list of (index, start_line_0based, call_text). Lines are
    joined by paren balance so wrapped calls still count as one call.
    """
    # Find the opening '[' on/after start_idx (usually same line).
    depth = 0
    open_idx = None
    for i in range(start_idx, min(start_idx + 3, len(lines))):
        if "[" in lines[i]:
            open_idx = i
            depth = lines[i].count("[") - lines[i].count("]")
            break
    if open_idx is None:
        return [], start_idx
    calls = []
    i = open_idx + 1
    buf = None
    buf_start = None
    paren = 0
    while i < len(lines) and i < open_idx + 120:
        line = lines[i]
        depth += line.count("[") - line.count("]")
        if depth <= 0:
            break
        stripped = line.strip()
        if buf is None:
            m = re.match(r"([A-Za-z_][\w.]*)\s*\(", stripped)
            if m:
                buf = stripped
                buf_start = i
                paren = stripped.count("(") - stripped.count(")")
                if paren <= 0:
                    calls.append((len(calls), buf_start, buf))
                    buf = None
        else:
            buf += " " + stripped
            paren += stripped.count("(") - stripped.count(")")
            if paren <= 0:
                calls.append((len(calls), buf_start, buf))
                buf = None
        i += 1
    return calls, i


def parse_return_mapping(lines, after_idx):
    """Find `return {` after after_idx and map results[N] -> field name.
    Returns (mapping, block_start, block_end) or ({}, None, None).
    """
    for i in range(after_idx, min(after_idx + 40, len(lines))):
        if re.search(r"^\s*return\s*\{", lines[i]):
            start = i
            depth = 0
            end = None
            for j in range(start, min(start + 80, len(lines))):
                depth += lines[j].count("{") - lines[j].count("}")
                if depth <= 0:
                    end = j + 1
                    break
            if end is None:
                end = min(start + 80, len(lines))
            mapping = {}
            for k in range(start, end):
                for m in re.finditer(r"results\[(\d+)\]", lines[k]):
                    key_m = re.match(r"\s*([\w$]+)\s*:", lines[k])
                    key = key_m.group(1) if key_m else f"(line {k + 1})"
                    mapping[int(m.group(1))] = key
            return mapping, start, end
    return {}, None, None


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

    print("=== house-marker diag ===")
    print(f"player: {args.player_id}  house: {args.house_id}")
    print(f"phone GPS: lat={args.lat} lng={args.lng}  host: {args.host}")

    missing = []
    f = {}  # findings

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

    # ------------------------------------------------ check 1: the batch
    print()
    print("=== 1. entity batch + return mapping (useMapQueries.ts) ===")
    batch_file = None
    batch_lines = None
    for cand_path, cand_lines in [(hooks_path, hooks_lines)] + [
        (p, read_file(p)) for p in index_paths
    ]:
        if cand_lines and any("Promise.allSettled" in l for l in cand_lines):
            batch_file = cand_path
            batch_lines = cand_lines
            break
    calls = []
    mapping = {}
    houses_call = None
    if batch_file is None:
        print("BATCH NOT FOUND: no Promise.allSettled block in useMapQueries.ts "
              "or index.tsx -- the entity batch may live elsewhere")
        missing.append("batch")
    else:
        print(f"batch lives in: {batch_file}")
        bidx = next(i for i, l in enumerate(batch_lines)
                    if "Promise.allSettled" in l)
        calls, batch_end = parse_batch_calls(batch_lines, bidx)
        print(f"batch calls: {len(calls)}")
        for idx, line_no, text in calls:
            print(f"  [{idx}] line {line_no + 1}: {text}")
        for idx, line_no, text in calls:
            name = text.split("(")[0].strip()
            if "house" in name.lower():
                houses_call = (idx, line_no, text)
                break
        if houses_call:
            idx, line_no, text = houses_call
            print(f"HOUSES CALL: index {idx}, line {line_no + 1}: {text}")
            call_args = text[text.find("(") + 1: text.rfind(")")]
            print(f"  call args: {call_args}")
            if "player.position" in call_args or "player?.position" in call_args:
                print("  args source: STORED player position (player.position)")
                f["houses_args_source"] = "stored"
            elif "latitude" in call_args and "longitude" in call_args:
                print("  args source: LIVE GPS (latitude/longitude query params)")
                f["houses_args_source"] = "live-gps"
            else:
                print("  args source: UNKNOWN (neither live GPS params nor "
                      "player.position -- see args above)")
                f["houses_args_source"] = "unknown"
        else:
            print("HOUSES CALL: NONE -- no call with 'house' in its name "
                  "in the batch")
        mapping, rstart, rend = parse_return_mapping(batch_lines, batch_end)
        if rstart is not None:
            print_block("return mapping", batch_lines, rstart, rend)
            print(f"mapped results indices: {sorted(mapping)} -> "
                  f"{[mapping[i] for i in sorted(mapping)]}")
        else:
            print("RETURN MAPPING NOT FOUND after the batch")
        unmapped = [i for i in range(len(calls)) if i not in mapping]
        print(f"UNMAPPED call indices (fetched, never turned into a field): "
              f"{unmapped}")
        f["calls"] = calls
        f["mapping"] = mapping
        f["unmapped"] = unmapped
        f["houses_call"] = houses_call
        # MapEntitiesData interface
        iface = find_lines(batch_lines, r"interface\s+MapEntitiesData")
        if iface:
            istart = iface[0][0]
            iend = min(istart + 40, len(batch_lines))
            for j in range(istart, iend):
                if j > istart and batch_lines[j].strip() == "}":
                    iend = j + 1
                    break
            print_block("MapEntitiesData interface", batch_lines, istart, iend)
            print("interface declares a houses field: "
                  + ("YES" if any("houses" in batch_lines[j]
                                   for j in range(istart, iend)) else "NO"))
            f["iface_has_houses"] = any("houses" in batch_lines[j]
                                        for j in range(istart, iend))
        else:
            print("MapEntitiesData interface: NOT FOUND in this file")
            f["iface_has_houses"] = None
        imp = find_lines(batch_lines, r"house", re.IGNORECASE)
        imp = [x for x in imp if "import" in x[1]]
        print("import lines mentioning house: "
              + (str([l.strip() for _, l in imp]) if imp else "NONE"))

    # ------------------------------------------------ check 2: index.tsx
    print()
    print("=== 2. index.tsx: nearbyHouses derivation + mapMarkers ===")
    f["mapmarkers_has_houses"] = None
    f["houses_marker_type"] = None
    f["houses_filter"] = None
    f["separate_houses_fetch"] = None
    if index_lines:
        print(f"index file: {index_path}")
        deriv = find_lines(index_lines, r"nearbyHouses")
        if deriv:
            print("nearbyHouses occurrences:")
            for i, l in deriv:
                show_context(index_lines, i, before=1, after=1)
        else:
            print("nearbyHouses: NO occurrences in index.tsx -- nothing "
                  "derives a houses list from the entities data")
        mm = find_lines(index_lines, r"mapMarkers\s*=\s*useMemo")
        if mm:
            mstart = mm[0][0]
            mend = None
            for j in range(mstart, min(mstart + 250, len(index_lines))):
                if re.match(r"\s*\],\s*\[", index_lines[j]):
                    for k in range(j, min(j + 4, len(index_lines))):
                        if ");" in index_lines[k]:
                            mend = k + 1
                            break
                    break
            if mend is None:
                mend = min(mstart + 250, len(index_lines))
            print_block("mapMarkers useMemo", index_lines, mstart, mend)
            block = "".join(index_lines[mstart:mend])
            spreads = re.findall(r"\.\.\.nearby(\w+)", block)
            print(f"mapMarkers spreads (nearby* lists turned into markers): "
                  f"{spreads}")
            types = re.findall(r"type:\s*'([^']+)'", block)
            print(f"mapMarkers marker type strings: {sorted(set(types))}")
            has_houses = "nearbyHouses" in block
            print(f"mapMarkers has a houses entry: {'YES' if has_houses else 'NO'}")
            f["mapmarkers_has_houses"] = has_houses
            if has_houses:
                hlines = [i for i in range(mstart, mend)
                          if "nearbyHouses" in index_lines[i]]
                for i in hlines:
                    show_context(index_lines, i, before=1, after=3)
                # the type string on/near the houses spread (a .filter()
                # may sit between the spread and .map, so allow anything
                # in between -- do NOT anchor on `.map(` directly)
                seg = "\n".join(index_lines[mstart:mend])
                hm = re.search(
                    r"nearbyHouses[\s\S]{0,800}?type:\s*'([^']+)'",
                    seg)
                if hm:
                    print(f"houses marker type string: '{hm.group(1)}'")
                    f["houses_marker_type"] = hm.group(1)
                else:
                    hm2 = re.search(
                        r"nearbyHouses[\s\S]{0,800}?type:\s*([^\n,]+)",
                        seg)
                    print("houses marker type string: "
                          + (hm2.group(1).strip() if hm2
                             else "NOT FOUND near the houses spread"))
                    f["houses_marker_type"] = (
                        hm2.group(1).strip() if hm2 else None)
                filt = [i for i in range(mstart, mend)
                        if "nearbyHouses" in index_lines[i]
                        and ".filter(" in index_lines[i]]
                if filt:
                    print("FILTER on the houses spread:")
                    for i in filt:
                        show_context(index_lines, i, before=0, after=0)
                    f["houses_filter"] = index_lines[filt[0]].strip()
                else:
                    print("FILTER on the houses spread: NONE in mapMarkers")
            # any .filter( on a houses line anywhere in the file
            hf = find_lines(index_lines, r"nearbyHouses.*\.filter\(|\.filter\([^)]*house", re.IGNORECASE)
            if hf and not f["houses_filter"]:
                print("FILTER on a houses list elsewhere in index.tsx:")
                for i, l in hf:
                    show_context(index_lines, i, before=0, after=0)
                f["houses_filter"] = hf[0][1].strip()
        else:
            print("mapMarkers useMemo: NOT FOUND in index.tsx")
        press = find_lines(index_lines, r"marker\.type\s*===?\s*'house'")
        press += find_lines(index_lines, r'marker\.type\s*===?\s*"house"')
        if press:
            print("handleMarkerPress 'house' case:")
            for i, l in press:
                show_context(index_lines, i, before=1, after=3)
            f["press_has_house"] = True
        else:
            print("handleMarkerPress 'house' case: ABSENT (tapping a house "
                  "marker would do nothing even if it rendered)")
            f["press_has_house"] = False
        # separate houses fetch outside the batch?
        sep = find_lines(index_lines, r"useQuery\(\s*\[.house", re.IGNORECASE)
        sep += find_lines(index_lines, r"getNearbyHouses\s*\(")
        sep = [x for x in sep if "Promise.allSettled" not in x[1]]
        if sep:
            print("SEPARATE houses fetch in index.tsx (outside the batch):")
            for i, l in sep:
                show_context(index_lines, i, before=1, after=1)
            f["separate_houses_fetch"] = True
        else:
            print("separate houses fetch in index.tsx: NONE")
            f["separate_houses_fetch"] = False
    else:
        print("index.tsx not readable -- check 2 skipped")

    # ------------------------------------------------ check 3: GameMap
    print()
    print("=== 3. GameMap.tsx: house marker branch ===")
    f["gamemap_house_branch"] = None
    f["gamemap_house_icon"] = None
    f["gamemap_house_color"] = None
    f["gamemap_size_refs_house"] = False
    if gamemap_lines:
        colors = find_lines(gamemap_lines, r"markerColors\s*=")
        icons = find_lines(gamemap_lines, r"markerIcons\s*=")
        for label, found in [("markerColors", colors), ("markerIcons", icons)]:
            if found:
                i, l = found[0]
                # Whole-line print only -- NEVER a [^}]* regex here: the
                # line contains \u{...} escapes whose inner } would end
                # such a match early (that broke the map once before).
                print(f"{label} line {i + 1}: {l.strip()}")
                has_house = ("'house'" in l or '"house"' in l
                             or "house:" in l)
                print(f"  has a house entry: {'YES' if has_house else 'NO'}")
                if label == "markerIcons":
                    f["gamemap_house_icon"] = has_house
                else:
                    f["gamemap_house_color"] = has_house
            else:
                print(f"{label}: NOT FOUND in GameMap.tsx")
        house_lines = find_lines(gamemap_lines, r"house", re.IGNORECASE)
        if house_lines:
            print(f"'house' mentions in GameMap.tsx: {len(house_lines)}")
            for i, l in house_lines:
                show_context(gamemap_lines, i, before=1, after=1)
        else:
            print("'house' mentions in GameMap.tsx: NONE -- no house "
                  "marker branch, no house icon/color entry")
        # A real else-if branch only -- NOT a sizing ternary like
        # (m.type === 'house') ? 56 : 32, which mentions the type
        # without being a marker branch.
        branch = find_lines(gamemap_lines,
                            r"\}\s*else if\s*\(\s*m\.type\s*===?\s*'house'\s*\)")
        branch += find_lines(gamemap_lines,
                             r'\}\s*else if\s*\(\s*m\.type\s*===?\s*"house"\s*\)')
        if branch:
            bi = branch[0][0]
            print(f"house branch in createMarker: line {bi + 1}")
            bend = min(bi + 40, len(gamemap_lines))
            for j in range(bi + 1, bend):
                if re.match(r"\s*\}\s*else if", gamemap_lines[j]):
                    bend = j
                    break
            print_block("house branch (createMarker)", gamemap_lines, bi, bend)
            f["gamemap_house_branch"] = True
            body = "\n".join(gamemap_lines[bi:bend])
            print("branch reads a .size field (m.size / h.size): "
                  + ("YES" if re.search(r"\.\s*size\b", body) else "NO"))
            print("branch returns/skips early (return/continue before "
                  "marker creation): "
                  + ("YES -- see lines above" if re.search(
                      r"\breturn\b|\bcontinue\b", body) else "NO"))
        else:
            print("house branch in createMarker: NONE -- a marker with "
                  "type 'house' falls through to the generic fallback "
                  "(markerColors[type] || '#999', markerIcons[type] || '?', "
                  "32px circle)")
            f["gamemap_house_branch"] = False
        # marker sizing lines
        for pat, label in [(r"var markerWidth\s*=", "markerWidth"),
                           (r"var markerHeight\s*=", "markerHeight"),
                           (r"var iconAnchorY\s*=", "iconAnchorY")]:
            hits = find_lines(gamemap_lines, pat)
            if hits:
                i, l = hits[0]
                print(f"{label} line {i + 1}: {l.strip()}")
                # Only a real .size FIELD access counts (a house-specific
                # constant width, e.g. (m.type === 'house') ? 56 : 32,
                # is fine). The substring "size" alone would also match
                # every font-size: style in the branch HTML.
                if re.search(r"\.\s*size\b", l):
                    print("  -> sizing reads a .size field: YES")
                    f["gamemap_size_refs_house"] = True
        # entity marker creation + z-index
        mk = find_lines(gamemap_lines, r"L\.marker\(\[m\.lat,\s*m\.lng\]")
        if mk:
            i, l = mk[0]
            print(f"entity marker creation line {i + 1}: {l.strip()}")
            print("  zIndexOffset on entity markers: "
                  + ("YES -- see line above" if "zIndexOffset" in l
                     else "NO (default 0 -- later markers paint above)"))
            f["entity_zindex"] = ("zIndexOffset" in l)
        pm = find_lines(gamemap_lines, r"zIndexOffset:\s*1000")
        if pm:
            print(f"player marker zIndexOffset 1000: line {pm[0][0] + 1} "
                  f"(player dot paints above ALL entity markers)")
        # MapMarker type union
        mm = find_lines(gamemap_lines, r"interface\s+MapMarker")
        if mm:
            istart = mm[0][0]
            iend = min(istart + 20, len(gamemap_lines))
            for j in range(istart, iend):
                if j > istart and gamemap_lines[j].strip() == "}":
                    iend = j + 1
                    break
            print_block("MapMarker interface", gamemap_lines, istart, iend)
            print("type union includes 'house': "
                  + ("YES" if any("'house'" in gamemap_lines[j]
                                   or '"house"' in gamemap_lines[j]
                                   for j in range(istart, iend))
                     else "NO"))
    else:
        print("GameMap.tsx not readable -- check 3 skipped")

    # ------------------------------------------------ check 4: live doc
    print()
    print("=== 4. live house doc (read-only GETs) ===")
    live_doc = None
    live_status = None
    url = (f"{args.host}/api/houses/nearby?latitude={args.lat}"
           f"&longitude={args.lng}&player_id={args.player_id}")
    status, data, raw = http_get_json(url, timeout=10)
    live_status = status
    print(f"GET {url}")
    print(f"  status: {status}")
    if data is not None:
        print("  response JSON:")
        print(json.dumps(data, indent=2)[:4000])
        docs = data if isinstance(data, list) else data.get("houses") or data.get("items") or []
        print(f"  houses returned: {len(docs)}")
        for d in docs:
            if isinstance(d, dict) and d.get("id") == args.house_id:
                live_doc = d
                break
        if live_doc is None and docs:
            live_doc = docs[0] if isinstance(docs[0], dict) else None
            print("  (house id not in response -- showing first doc)")
    else:
        print(f"  GET failed / not JSON: {str(raw)[:300]}")
    url2 = f"{args.host}/api/houses/{args.house_id}"
    status2, data2, raw2 = http_get_json(url2, timeout=10)
    print(f"GET {url2} -> status: {status2}")
    if status2 == 200 and isinstance(data2, dict):
        print("  house-by-id doc:")
        print(json.dumps(data2, indent=2)[:2000])
        if live_doc is None:
            live_doc = data2
    elif status2 == 404:
        print("  (no /api/houses/<id> route -- 404; nearby is the only read path)")
    elif status2 is not None:
        print(f"  body: {str(raw2)[:300]}")
    else:
        print(f"  GET failed: {str(raw2)[:200]}")

    dist_m = None
    if live_doc is not None:
        print()
        print("--- live doc vs what the marker path needs ---")
        print(json.dumps(live_doc, indent=2))
        for field in ["id", "type", "size", "owner_id", "hidden",
                      "latitude", "longitude", "name"]:
            print(f"  doc.{field} = {live_doc.get(field)!r}")
        try:
            dist_m = haversine_m(args.lat, args.lng,
                                 float(live_doc["latitude"]),
                                 float(live_doc["longitude"]))
            print(f"  phone -> house distance: {dist_m:.1f} m")
        except (KeyError, TypeError, ValueError):
            print("  phone -> house distance: CANNOT COMPUTE (lat/lng "
                  "missing from doc)")
        if live_doc.get("type") is None:
            print("  FLAG: doc.type is None -- any branch/filter keyed on "
                  "a type string (apartment/cabin/mansion/house) fails")
        if not live_doc.get("owner_id"):
            print("  FLAG: doc.owner_id is empty -- any owner check "
                  "(owner_id == playerId) fails")
        if live_doc.get("size") is None:
            print("  FLAG: doc has NO size field -- any marker sizing "
                  "that reads a size field resolves to 0/NaN")
        if live_doc.get("hidden"):
            print("  FLAG: doc.hidden is truthy -- hidden houses are "
                  "skipped by visibility/marker code")
    else:
        print("LIVE DOC: none -- the nearby GET returned no house doc to "
              "compare against")

    # ------------------------------------------------ check 5: path + api
    print()
    print("=== 5. render path trace + api + backend visibility ===")
    print("--- api.ts getNearbyHouses ---")
    if api_lines:
        ah = find_lines(api_lines, r"getNearbyHouses")
        if ah:
            for i, l in ah[:3]:
                show_context(api_lines, i, before=0, after=5)
        else:
            print("getNearbyHouses: NOT FOUND in frontend/services/api.ts")
    # backend visibility
    print("--- backend houses endpoint (server.py) ---")
    if server_lines:
        hroute = find_lines(server_lines, r"houses/nearby")
        if hroute:
            for i, l in hroute:
                show_context(server_lines, i, before=2, after=2)
            # print the enclosing endpoint function: the def sits BELOW
            # its @api_router.get decorator (scan down, not up)
            defi = None
            for j in range(hroute[0][0], min(hroute[0][0] + 6, len(server_lines))):
                if re.match(r"^(async\s+def|def)\s+", server_lines[j]):
                    defi = j
                    break
            if defi is not None:
                end = len(server_lines)
                for j in range(defi + 1, len(server_lines)):
                    if re.match(r"^(async\s+def|def|@|class)\s", server_lines[j]) \
                            or re.match(r"^[A-Za-z_][\w]*\s*=", server_lines[j]):
                        end = j
                        break
                print_block("houses nearby endpoint", server_lines, defi, end)
                body = "\n".join(server_lines[defi:end])
                for kw in ["owner", "friend", "hidden"]:
                    if kw in body.lower():
                        print(f"  endpoint mentions '{kw}' -- see body above")
        else:
            print("houses/nearby route: NOT FOUND in backend/server.py "
                  "(snapshot may predate the house feature; the live GET "
                  "above is the evidence that the endpoint exists)")
    print("--- trace: batch -> map -> marker ---")
    trace = []
    trace.append(("batch has a houses call",
                  "YES" if houses_call else "NO"))
    if houses_call:
        mapped = houses_call[0] in mapping
        trace.append((f"results[{houses_call[0]}] mapped to a field",
                      f"YES -> {mapping[houses_call[0]]}" if mapped
                      else "NO -- fetched, never turned into a field"))
    trace.append(("MapEntitiesData declares houses",
                  "YES" if f.get("iface_has_houses") else
                  ("NO" if f.get("iface_has_houses") is False else "UNKNOWN")))
    trace.append(("index.tsx derives nearbyHouses",
                  "YES" if index_lines and any("nearbyHouses" in l
                                                for l in index_lines)
                  else "NO"))
    trace.append(("mapMarkers has a houses entry",
                  "YES" if f.get("mapmarkers_has_houses") else
                  ("NO" if f.get("mapmarkers_has_houses") is False
                   else "UNKNOWN")))
    trace.append(("GameMap has a house marker branch",
                  "YES" if f.get("gamemap_house_branch") else
                  ("NO" if f.get("gamemap_house_branch") is False
                   else "UNKNOWN")))
    trace.append(("markerColors/markerIcons have a house entry",
                  f"colors={f.get('gamemap_house_color')} "
                  f"icons={f.get('gamemap_house_icon')}"))
    trace.append(("handleMarkerPress has a 'house' case",
                  "YES" if f.get("press_has_house") else "NO"))
    for label, val in trace:
        print(f"  {label}: {val}")
    f["trace"] = trace

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
    else:
        # (a) batch never delivers houses to the render pipeline
        if houses_call and houses_call[0] not in mapping:
            verdict = "a"
            reason = (f"getNearbyHouses is call [{houses_call[0]}] in the "
                      f"batch but results[{houses_call[0]}] has NO return "
                      f"mapping -- the house is fetched and thrown away "
                      f"(unmapped indices: {f['unmapped']})")
        elif not houses_call and not f.get("separate_houses_fetch"):
            verdict = "a"
            reason = ("no houses call in the entity batch and no separate "
                      "houses fetch in index.tsx -- houses are never "
                      "fetched at all")
        elif (houses_call and houses_call[0] in mapping
                and f.get("mapmarkers_has_houses") is False):
            verdict = "a"
            reason = (f"results[{houses_call[0]}] IS mapped to "
                      f"'{mapping[houses_call[0]]}' but mapMarkers has NO "
                      f"houses entry -- the data arrives and is never "
                      f"turned into a marker")
        # (d) separate path, broken
        elif (not houses_call and f.get("separate_houses_fetch")
                and (live_status in (None, 404) or live_doc is None)):
            verdict = "d"
            reason = ("houses come from a separate fetch (not the batch) "
                      f"and the live houses GET failed (status "
                      f"{live_status}) -- that path is broken")
        # (b) a filter/branch skips his house
        elif f.get("houses_filter"):
            verdict, reason = eval_filter(f["houses_filter"], live_doc,
                                          args.player_id)
            if verdict is None:
                verdict = "b"
                reason = ("a filter sits on the houses path and could not "
                          "be evaluated automatically -- the filter line "
                          "is printed in check 2; read it against the "
                          "live doc above")
        # (c) created but invisible / covered
        elif f.get("gamemap_size_refs_house") and live_doc is not None \
                and live_doc.get("size") is None:
            verdict = "c"
            reason = ("marker sizing references a house size field but the "
                      "live doc has NO size -- width/height resolve to "
                      "0/NaN, so the marker is created with no size and "
                      "is invisible")
        elif f.get("gamemap_house_branch") is False:
            if live_doc is not None and dist_m is not None and dist_m <= 60:
                verdict = "c"
                reason = (f"no house branch in GameMap -- a house marker "
                          f"falls through to the generic 32px '?' fallback, "
                          f"and the house is {dist_m:.1f}m from the phone "
                          f"while the player dot (zIndexOffset 1000, 36px "
                          f"+ pulse) paints above all entity markers "
                          f"(default z-index) -- the '?' sits under your "
                          f"avatar")
            else:
                verdict = "c"
                reason = ("no house branch in GameMap -- a house marker "
                          "falls through to the generic 32px '?' fallback "
                          "(markerColors[type] || '#999', markerIcons[type] "
                          "|| '?'); there is no house icon, so the marker "
                          "does not look like a house")
        elif f.get("gamemap_house_icon") is False:
            verdict = "c"
            reason = ("the house branch exists but markerIcons has no "
                      "house entry -- the marker renders with a '?' icon")
        # (e) healthy
        else:
            verdict = "e"
            reason = ("batch maps houses, mapMarkers includes them, "
                      "GameMap has a house branch, and the live doc "
                      "passes every check -- the marker should render. "
                      "Cause is on-device: stale Expo Go build/cache. "
                      "Force a fresh reload (shake -> Reload, or clear "
                      "the Expo Go cache and reopen), then move ~50m "
                      "away from the house and look back -- if it "
                      "appears, the build was stale.")
    print(f"VERDICT: ({verdict}) {reason}")
    print()
    if missing:
        print("HOUSE_MARKER_DIAG_PARTIAL missing=" + ",".join(missing)
              + f" verdict={verdict}")
    else:
        print(f"HOUSE_MARKER_DIAG_OK verdict={verdict}")


def eval_filter(filter_text, live_doc, player_id):
    """Evaluate the common houses-filter shapes against the live doc.
    Returns (verdict, reason) or (None, '') if it passes / not evaluable.
    """
    if live_doc is None:
        return None, ""
    t = filter_text
    # includes-list on type: ['apartment','cabin','mansion'].includes(h.type)
    m = re.search(r"\[([^\]]+)\]\.includes\(\s*\w+\.type\s*\)", t)
    if m:
        allowed = re.findall(r"'([^']+)'|\"([^\"]+)\"", m.group(1))
        allowed = [a or b for a, b in allowed]
        if live_doc.get("type") not in allowed:
            return ("b", f"mapMarkers filter requires type in {allowed} "
                         f"but the live doc has type={live_doc.get('type')!r} "
                         f"-- the house is filtered out before GameMap")
        return None, ""
    # owner check: h.owner_id === playerId
    if re.search(r"\w+\.owner_id\s*===?\s*playerId", t):
        if live_doc.get("owner_id") != player_id:
            return ("b", "mapMarkers filter requires owner_id == playerId "
                         f"but the live doc has owner_id="
                         f"{live_doc.get('owner_id')!r} -- the house is "
                         f"filtered out before GameMap")
        return None, ""
    # truthy type: .filter(h => h.type) / h.type &&
    if re.search(r"=>\s*\w+\.type\b", t) or re.search(r"\w+\.type\s*&&", t):
        if not live_doc.get("type"):
            return ("b", "mapMarkers filter requires a truthy type but the "
                         f"live doc has type={live_doc.get('type')!r} -- "
                         f"the house is filtered out before GameMap")
        return None, ""
    # hidden check: !h.hidden
    if re.search(r"!\s*\w+\.hidden", t):
        if live_doc.get("hidden"):
            return ("b", "mapMarkers filter requires !hidden but the live "
                         f"doc has hidden={live_doc.get('hidden')!r}")
        return None, ""
    return None, ""


if __name__ == "__main__":
    main()
