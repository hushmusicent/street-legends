#!/usr/bin/env python3
"""House marker batch fix (frontend).

The house marker never renders because houses are never fetched: the
entity batch in useMapQueries.ts has no getNearbyHouses call (diag
2026-11-05 23:44 EST, HOUSE_MARKER_DIAG_OK verdict=(a)) and no
separate houses fetch exists in index.tsx. Everything downstream IS
wired: MapEntitiesData declares houses, index.tsx derives nearbyHouses,
mapMarkers has a houses entry, GameMap has a house marker branch
(createMarker `} else if (m.type === 'house')` -> 72px house emoji),
markerColors/markerIcons have a house entry, handleMarkerPress has a
'house' case. Only the fetch is missing.

This patch:
  1. Adds getNearbyHouses to the entity batch (appended LAST when absent,
     so no existing results[N] index moves) and maps its result to the
     `houses` field at the correct results[N] index. If the call is
     already present but unmapped (the state the Fiend follow-up found
     at index 15), only the mapping is added - no duplicate call.
  2. Adds 'house' to the MapMarker type union in GameMap.tsx (the
     union lists every other marker type but not 'house' - a TS-level
     gap; JS still matched the string at runtime, but it must be there
     for correctness).

Does NOT touch the marker branch, sizing (fixed 72px), z-indexes (the
player dot at 1000 paints above the house at 4.4m - cosmetic, not the
cause), the backend, or the visibility rule. Does NOT key anything on
the house doc's missing type/size/owner_id fields (the doc carries
player_id, not owner_id, and no type/size) - the marker entry is built
from the doc's id + latitude/longitude + name, which exist.

Run:  python3 frontend/patch-house-marker-batch-frontend.py
   or:  python3 frontend/patch-house-marker-batch-frontend.py /path/to/app
Idempotent: rerun prints ALREADY_APPLIED per part, files unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
QUERIES = ROOT / "frontend" / "hooks" / "useMapQueries.ts"
GAMEMAP = ROOT / "frontend" / "components" / "GameMap.tsx"

# Newest-first anchors: the import/field live next to the most recently
# added entity (billboards -> parks -> pharmacies -> fiends -> centers).
_IMPORT_ANCHORS = [
    "  getBillboardsNearby,\n",
    "  getParksNearby,\n",
    "  getPharmaciesNearby,\n",
    "  getFiendsNearby,\n",
    "  getActivityCentersNearby,\n",
    "  spawnShootouts,\n",
]
_FIELD_ANCHORS = [
    "  billboards: any[];\n",
    "  parks: any[];\n",
    "  pharmacies: any[];\n",
    "  fiends: any[];\n",
    "  activityCenters: any[];\n",
    "  shootouts: any[];\n",
]


def delta(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"),
            s.count("["), s.count("]"))


def _imbalances_ok(before, after):
    """True when no bracket pair's imbalance changed (balanced code may
    legitimately raise the counts, so exact equality is wrong)."""
    b, a = delta(before), delta(after)
    return ((a[0] - a[1]) == (b[0] - b[1]) and (a[2] - a[3]) == (b[2] - b[3])
            and (a[4] - a[5]) == (b[4] - b[5]))


def _strip_strings(text):
    """Remove single/double-quoted string contents so paren counting
    never trips over a paren inside a string literal."""
    return re.sub(r"'[^']*'|\"[^\"]*\"", "''", text)


_CALL_NAME_RE = re.compile(r"^\s*(?:withTimeout\()?([A-Za-z_$][\w$]*)\(")
_MAPPING_RE = re.compile(
    r"^([ \t]*)(\w+): results\[(\d+)\]\.status === 'fulfilled' \? "
    r"results\[\d+\]\.value : \[\],?[ \t]*$", re.M)


def _parse_batch_entries(body):
    """Split a Promise.allSettled array body into call entries.

    Paren-depth aware: a call that spans several lines counts once.
    Returns a list of {name, text, start, end} with start/end as
    character offsets within body.
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
    return entries


def _parse_mappings(src):
    """Return (mapping dict index->field, last mapping match)."""
    mapping = {}
    last = None
    for m in _MAPPING_RE.finditer(src):
        mapping[int(m.group(3))] = m.group(2)
        last = m
    return mapping, last


def _add_marker_union_house(gsrc):
    """Add 'house' to the MapMarker type union. Returns
    (new_src, status) where status is 'added', 'already', or an
    error string. Scoped to the interface MapMarker block so no
    other `type:` field is touched."""
    m = re.search(r"interface MapMarker\s*\{", gsrc)
    if not m:
        return gsrc, "interface-not-found"
    # The `type:` field is the first `type:` line after the interface
    # start; its union ends at the next semicolon.
    tm = re.search(r"\n[ \t]*type:", gsrc[m.start():])
    if not tm:
        return gsrc, "type-field-not-found"
    tstart = m.start() + tm.end()
    semi = gsrc.find(";", tstart)
    if semi == -1:
        return gsrc, "type-union-not-terminated"
    union = gsrc[tstart:semi]
    if "'house'" in union:
        return gsrc, "already"
    return gsrc[:semi] + " | 'house'" + gsrc[semi:], "added"


def main():
    landed = []
    warned = []

    # ================= Part 1: hooks/useMapQueries.ts =================
    if not QUERIES.exists():
        print("WARNING: hooks/useMapQueries.ts not found - houses entity wiring NOT added")
        warned.append("queries")
    else:
        qsrc = QUERIES.read_text(errors="ignore")
        qorig = qsrc
        # 1a. Import getNearbyHouses.
        if "getNearbyHouses" in qsrc and re.search(r"^\s*getNearbyHouses,$", qsrc, re.M):
            print("HOUSE_MARKER_BATCH_QUERIES_IMPORT_ALREADY_APPLIED")
        else:
            done = False
            for anchor in _IMPORT_ANCHORS:
                if anchor in qsrc:
                    qsrc = qsrc.replace(anchor, anchor + "  getNearbyHouses,\n", 1)
                    print("HOUSE_MARKER_BATCH_QUERIES_IMPORT_OK")
                    done = True
                    break
            if not done:
                print("WARNING: api import anchor not found in useMapQueries.ts - getNearbyHouses import NOT added")
                warned.append("queries-import")
        # 1b. MapEntitiesData houses field.
        if re.search(r"^\s*houses: any\[\];", qsrc, re.M):
            print("HOUSE_MARKER_BATCH_QUERIES_FIELD_ALREADY_APPLIED")
        else:
            done = False
            for anchor in _FIELD_ANCHORS:
                if anchor in qsrc:
                    qsrc = qsrc.replace(anchor, anchor + "  houses: any[];\n", 1)
                    print("HOUSE_MARKER_BATCH_QUERIES_FIELD_OK")
                    done = True
                    break
            if not done:
                print("WARNING: MapEntitiesData anchor not found - houses field NOT added")
                warned.append("queries-field")
        # 1c. Batch discovery + call / mapping.
        m = re.search(r"Promise\.allSettled\(\[", qsrc)
        if not m:
            print("WARNING: Promise.allSettled anchor not found - houses call NOT added")
            warned.append("queries-batch")
        else:
            start = m.end()
            close = re.search(r"\n[ \t]*\]\);", qsrc[start:])
            if not close:
                print("WARNING: Promise.allSettled close anchor not found - houses call NOT added")
                warned.append("queries-batch")
            else:
                body = qsrc[start:start + close.start()]
                entries = _parse_batch_entries(body)
                mapping, last_map = _parse_mappings(qsrc)
                names = [e["name"] for e in entries]
                unmapped = [(i, entries[i]["name"])
                            for i in range(len(entries)) if i not in mapping]
                print(f"HOUSE_MARKER_BATCH_DISCOVERY: calls={len(entries)} "
                      f"mappings={len(mapping)} "
                      f"unmapped={unmapped}")
                print(f"HOUSE_MARKER_BATCH_CALLS: {', '.join(names)}")
                call_idx = next((i for i, e in enumerate(entries)
                                 if e["name"] == "getNearbyHouses"), None)
                has_mapping = "houses" in mapping.values()
                if call_idx is not None and has_mapping:
                    print("HOUSE_MARKER_BATCH_QUERIES_CALL_ALREADY_APPLIED")
                elif call_idx is not None and not has_mapping:
                    # Call present, mapping missing: add only the mapping
                    # at the call's own index.
                    if last_map is None:
                        print("WARNING: return mapping anchor not found - houses return NOT added")
                        warned.append("queries-return")
                    else:
                        mind = last_map.group(1)
                        ins2 = last_map.end()
                        qsrc = (qsrc[:ins2] + f"\n{mind}houses: results[{call_idx}].status === 'fulfilled' "
                                f"? results[{call_idx}].value : []," + qsrc[ins2:])
                        print(f"HOUSE_MARKER_BATCH_QUERIES_CALL_OK (houses mapping added at results[{call_idx}]; call was already present)")
                elif call_idx is None and has_mapping:
                    print("WARNING: houses return mapping exists but the call is missing - inconsistent state, NOT changed (hand-fix needed)")
                    warned.append("queries-inconsistent")
                else:
                    if last_map is None:
                        print("WARNING: return mapping anchor not found - houses call NOT added")
                        warned.append("queries-return")
                    else:
                        n = len(entries)
                        last_text = entries[-1]["text"] if entries else ""
                        lm = re.match(r"^([ \t]*)", last_text)
                        indent = lm.group(1) if lm and lm.group(1) else "        "
                        if "const withTimeout" in qsrc:
                            call_text = ("withTimeout(getNearbyHouses(latitude, longitude, 2000, playerId)),")
                        else:
                            call_text = "getNearbyHouses(latitude, longitude, 2000, playerId),"
                        ins_pos = start + close.start()
                        qsrc = qsrc[:ins_pos] + "\n" + indent + call_text + qsrc[ins_pos:]
                        # Re-find the last mapping (positions shifted by the insert).
                        _, last_map2 = _parse_mappings(qsrc)
                        mind = last_map2.group(1)
                        ins2 = last_map2.end()
                        qsrc = (qsrc[:ins2] + f"\n{mind}houses: results[{n}].status === 'fulfilled' "
                                f"? results[{n}].value : []," + qsrc[ins2:])
                        print(f"HOUSE_MARKER_BATCH_QUERIES_CALL_OK (houses at results[{n}]; "
                              f"unmapped call was {unmapped if unmapped else 'none'})")
        if not _imbalances_ok(qorig, qsrc):
            print("WARNING: unbalanced brackets - useMapQueries.ts NOT written")
            qsrc = qorig
            warned.append("queries-balance")
        if qsrc != qorig:
            QUERIES.write_text(qsrc)
            landed.append("queries")

    # ================= Part 2: GameMap MapMarker type union =================
    if not GAMEMAP.exists():
        print("WARNING: components/GameMap.tsx not found - 'house' type union NOT added")
        warned.append("gamemap")
    else:
        gsrc = GAMEMAP.read_text(errors="ignore")
        gorig = gsrc
        gsrc, status = _add_marker_union_house(gsrc)
        if status == "added":
            print("HOUSE_MARKER_BATCH_GAMEMAP_UNION_OK")
        elif status == "already":
            print("HOUSE_MARKER_BATCH_GAMEMAP_UNION_ALREADY_APPLIED")
        else:
            print(f"WARNING: MapMarker type union {status} - 'house' NOT added")
            warned.append("gamemap-union")
        if not _imbalances_ok(gorig, gsrc):
            print("WARNING: unbalanced brackets - GameMap.tsx NOT written")
            gsrc = gorig
            warned.append("gamemap-balance")
        if gsrc != gorig:
            GAMEMAP.write_text(gsrc)
            landed.append("gamemap")

    if warned:
        print("HOUSE_MARKER_BATCH_PARTIAL: " + ",".join(landed) +
              " (warnings: " + ",".join(warned) + ")")
    else:
        print("HOUSE_MARKER_BATCH_OK")


if __name__ == "__main__":
    main()
