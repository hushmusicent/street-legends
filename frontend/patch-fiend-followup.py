#!/usr/bin/env python3
"""Fiend missions follow-up (frontend).

Fixes the four gaps the first Fiend frontend patch left on live /app
(2026-11-05 11:49 EST run, FIEND_FRONTEND_PARTIAL):
  1. The Fiend data call never joined the entity batch: live
     useMapQueries.ts has 16 Promise.allSettled calls but only 15
     return mappings, so the first patch refused to add the call and no
     Fiend data ever reaches the map. This patch discovers the mismatch
     live (paren-depth entry parsing, so a multi-line call counts once),
     prints it, and appends getFiendsNearby LAST plus its return mapping at
     the correct results index. Existing mappings never move.
  2. handleMarkerPress deps never got nearbyFiends (Fiend taps could use
     a stale list).
  3. markerColors never got fiend '#8BC34A' (the icon did land).
  4. The dedicated Fiend marker branch never landed in GameMap.tsx.
Also adds fiend to the 48x62 location sizing (isLocationMarker), which
the first patch never reached either.

Does NOT re-do anything that already landed (api functions, index
wiring, popup, icon, SELL removals) - every part checks its own
ALREADY_APPLIED state first. Does NOT touch the backend, the SELL
buttons, or the once-only logic. The markerColors/markerIcons objects
are edited with a brace-count scan, never a negated-brace-star regex
(that exact pattern broke the map once: the U+1F480 escapes contain a
closing brace that ends the match early).

Run:  python3 frontend/patch-fiend-followup.py
   or:  python3 frontend/patch-fiend-followup.py /path/to/app
Idempotent: rerun prints ALREADY_APPLIED per part, files unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
QUERIES = ROOT / "frontend" / "hooks" / "useMapQueries.ts"
INDEX = ROOT / "frontend" / "app" / "(tabs)" / "index.tsx"
GAMEMAP = ROOT / "frontend" / "components" / "GameMap.tsx"


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


def _object_span(src, decl_re):
    """Find the { ... } object declared by decl_re. Returns
    (open_brace_index, close_brace_index) or None. Brace-count scan
    that skips single-quoted string spans (hex colors and icon
    escapes can contain braces)."""
    m = re.search(decl_re, src)
    if not m:
        return None
    start = src.find("{", m.start())
    if start == -1:
        return None
    depth = 0
    i = start
    in_str = False
    esc = False
    while i < len(src):
        ch = src[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == "'":
                in_str = False
        else:
            if ch == "'":
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return (start, i)
        i += 1
    return None


def _add_dep_to_array(src, anchor_re, dep, label):
    """Add dep to the deps array that closes the hook found by
    anchor_re (a useCallback/useMemo start). Returns (new_src, status)
    where status is 'added', 'already', or an error string."""
    m = re.search(anchor_re, src)
    if not m:
        return src, "anchor-not-found"
    # The deps array is the first "[ ... ]);" after the hook start whose
    # opener is preceded by "}, " (useCallback) or "], " (useMemo).
    dm = None
    for cand in re.finditer(r"\n[ \t]*(?:\}|\]), \[([^\]]*)\]\);", src[m.start():], re.S):
        if re.fullmatch(r"[\w$, \n\t]*", cand.group(1)):
            dm = cand
            break
    if not dm:
        return src, "deps-array-not-found"
    content = dm.group(1)
    entries = [e.strip() for e in content.split(",") if e.strip()]
    if dep in entries:
        return src, "already"
    if "nearbyShootouts" in entries:
        anchor_entry = "nearbyShootouts"
    elif "nearbyActivityCenters" in entries:
        anchor_entry = "nearbyActivityCenters"
    else:
        anchor_entry = None
    if "\n" not in content:
        if anchor_entry is not None:
            idx = entries.index(anchor_entry)
            entries.insert(idx + 1, dep)
        else:
            entries.append(dep)
        new_content = ", ".join(entries)
    else:
        lines = content.split("\n")
        if anchor_entry is not None:
            li = next(i for i, ln in enumerate(lines) if anchor_entry in ln)
            indent = lines[li][: len(lines[li]) - len(lines[li].lstrip())]
            lines.insert(li + 1, indent + dep + ",")
        else:
            li = max(i for i, ln in enumerate(lines) if ln.strip())
            if not lines[li].rstrip().endswith(","):
                lines[li] = lines[li].rstrip() + ","
            indent = lines[li][: len(lines[li]) - len(lines[li].lstrip())]
            lines.insert(li + 1, indent + dep + ",")
        new_content = "\n".join(lines)
    base = m.start()
    return (src[: base + dm.start(1)] + new_content
            + src[base + dm.end(1):]), "added"


def main():
    landed = []
    warned = []

    # ================= Part 1: hooks/useMapQueries.ts =================
    if not QUERIES.exists():
        print("WARNING: hooks/useMapQueries.ts not found - Fiend entity wiring NOT added")
        warned.append("queries")
    else:
        qsrc = QUERIES.read_text(errors="ignore")
        qorig = qsrc
        qd0 = delta(qsrc)
        # 1a. Import.
        if "  getFiendsNearby,\n" in qsrc:
            print("FIEND_FOLLOWUP_QUERIES_IMPORT_ALREADY_APPLIED")
        elif "  getActivityCentersNearby,\n" in qsrc:
            qsrc = qsrc.replace("  getActivityCentersNearby,\n",
                                "  getActivityCentersNearby,\n  getFiendsNearby,\n", 1)
            print("FIEND_FOLLOWUP_QUERIES_IMPORT_OK")
        elif "  spawnShootouts,\n" in qsrc:
            qsrc = qsrc.replace("  spawnShootouts,\n",
                                "  spawnShootouts,\n  getFiendsNearby,\n", 1)
            print("FIEND_FOLLOWUP_QUERIES_IMPORT_OK")
        else:
            print("WARNING: api import anchor not found in useMapQueries.ts - getFiendsNearby import NOT added")
            warned.append("queries-import")
        # 1b. MapEntitiesData field.
        if "fiends: any[];" in qsrc:
            print("FIEND_FOLLOWUP_QUERIES_FIELD_ALREADY_APPLIED")
        elif "  activityCenters: any[];\n" in qsrc:
            qsrc = qsrc.replace("  activityCenters: any[];\n",
                                "  activityCenters: any[];\n  fiends: any[];\n", 1)
            print("FIEND_FOLLOWUP_QUERIES_FIELD_OK")
        elif "  shootouts: any[];\n" in qsrc:
            qsrc = qsrc.replace("  shootouts: any[];\n",
                                "  shootouts: any[];\n  fiends: any[];\n", 1)
            print("FIEND_FOLLOWUP_QUERIES_FIELD_OK")
        else:
            print("WARNING: MapEntitiesData anchor not found - fiends field NOT added")
            warned.append("queries-field")
        # 1c. Batch discovery + append the call LAST + its return mapping.
        m = re.search(r"Promise\.allSettled\(\[", qsrc)
        if not m:
            print("WARNING: Promise.allSettled anchor not found - Fiend call NOT added")
            warned.append("queries-batch")
        else:
            start = m.end()
            close = re.search(r"\n[ \t]*\]\);", qsrc[start:])
            if not close:
                print("WARNING: Promise.allSettled close anchor not found - Fiend call NOT added")
                warned.append("queries-batch")
            else:
                body = qsrc[start:start + close.start()]
                entries = _parse_batch_entries(body)
                mapping, last_map = _parse_mappings(qsrc)
                loose = sorted(set(int(x) for x in
                                   re.findall(r"results\[(\d+)\]", qsrc)))
                names = [e["name"] for e in entries]
                unmapped = [(i, entries[i]["name"])
                            for i in range(len(entries)) if i not in mapping]
                print(f"FIEND_FOLLOWUP_BATCH_DISCOVERY: calls={len(entries)} "
                      f"mappings={len(mapping)} loose_results_refs={loose} "
                      f"unmapped={unmapped}")
                print(f"FIEND_FOLLOWUP_BATCH_CALLS: {', '.join(names)}")
                call_idx = next((i for i, e in enumerate(entries)
                                 if e["name"] == "getFiendsNearby"), None)
                has_mapping = "fiends" in mapping.values()
                if call_idx is not None and has_mapping:
                    print("FIEND_FOLLOWUP_QUERIES_CALL_ALREADY_APPLIED")
                elif call_idx is not None and not has_mapping:
                    # Call present, mapping missing: add only the mapping
                    # at the call's own index.
                    if last_map is None:
                        print("WARNING: return mapping anchor not found - fiends return NOT added")
                        warned.append("queries-return")
                    else:
                        mind = last_map.group(1)
                        ins2 = last_map.end()
                        qsrc = (qsrc[:ins2] + f"\n{mind}fiends: results[{call_idx}].status === 'fulfilled' "
                                f"? results[{call_idx}].value : []," + qsrc[ins2:])
                        print(f"FIEND_FOLLOWUP_QUERIES_CALL_OK (fiends mapping added at results[{call_idx}]; call was already present)")
                elif call_idx is None and has_mapping:
                    print("WARNING: fiends return mapping exists but the call is missing - inconsistent state, NOT changed (hand-fix needed)")
                    warned.append("queries-inconsistent")
                else:
                    if last_map is None:
                        print("WARNING: return mapping anchor not found - Fiend call NOT added")
                        warned.append("queries-return")
                    else:
                        n = len(entries)
                        last_text = entries[-1]["text"] if entries else ""
                        lm = re.match(r"^([ \t]*)", last_text)
                        indent = lm.group(1) if lm and lm.group(1) else "        "
                        if "const withTimeout" in qsrc:
                            call_text = ("withTimeout(getFiendsNearby(latitude, longitude, playerId)),")
                        else:
                            call_text = "getFiendsNearby(latitude, longitude, playerId),"
                        ins_pos = start + close.start()
                        qsrc = qsrc[:ins_pos] + "\n" + indent + call_text + qsrc[ins_pos:]
                        # Re-find the last mapping (positions shifted by the insert).
                        _, last_map2 = _parse_mappings(qsrc)
                        mind = last_map2.group(1)
                        ins2 = last_map2.end()
                        qsrc = (qsrc[:ins2] + f"\n{mind}fiends: results[{n}].status === 'fulfilled' "
                                f"? results[{n}].value : []," + qsrc[ins2:])
                        print(f"FIEND_FOLLOWUP_QUERIES_CALL_OK (fiends at results[{n}]; "
                              f"unmapped call was {unmapped if unmapped else 'none'})")
        if not _imbalances_ok(qorig, qsrc):
            print("WARNING: unbalanced brackets - useMapQueries.ts NOT written")
            qsrc = qorig
            warned.append("queries-balance")
        if qsrc != qorig:
            QUERIES.write_text(qsrc)
            landed.append("queries")

    # ================= Part 2: GameMap markerColors =================
    if not GAMEMAP.exists():
        print("WARNING: components/GameMap.tsx not found - Fiend color/branch NOT added")
        warned.append("gamemap")
    else:
        gsrc = GAMEMAP.read_text(errors="ignore")
        gorig = gsrc
        gd0 = delta(gsrc)
        span = _object_span(gsrc, r"var markerColors\s*=\s*\{")
        if span is None:
            print("WARNING: markerColors object not found - Fiend color NOT added")
            warned.append("gamemap-color")
        else:
            open_i, close_i = span
            obj = gsrc[open_i:close_i + 1]
            if "fiend" in obj:
                print("FIEND_FOLLOWUP_GAMEMAP_COLOR_ALREADY_APPLIED")
            elif "\n" not in obj:
                gsrc = gsrc[:close_i] + ", fiend: '#8BC34A'" + gsrc[close_i:]
                print("FIEND_FOLLOWUP_GAMEMAP_COLOR_OK")
            else:
                # Multi-line object: ensure the last entry ends with a
                # comma, then add the fiend entry on its own line before
                # the closing brace.
                nl = gsrc.rfind("\n", 0, close_i)
                indent = gsrc[nl + 1:close_i]
                if indent.strip() != "":
                    gsrc = gsrc[:close_i] + ", fiend: '#8BC34A'" + gsrc[close_i:]
                    print("FIEND_FOLLOWUP_GAMEMAP_COLOR_OK")
                else:
                    k = nl - 1
                    while k >= 0 and gsrc[k] in " \t\r\n":
                        k -= 1
                    if k >= 0 and gsrc[k] != ",":
                        gsrc = gsrc[:k + 1] + "," + gsrc[k + 1:]
                        close_i += 1
                        nl = gsrc.rfind("\n", 0, close_i)
                        indent = gsrc[nl + 1:close_i]
                    gsrc = gsrc[:nl + 1] + indent + "fiend: '#8BC34A',\n" + gsrc[nl + 1:]
                    print("FIEND_FOLLOWUP_GAMEMAP_COLOR_OK")
        # ================= Part 3: Fiend marker branch + sizing =================
        if "m.type === 'fiend'" in gsrc:
            print("FIEND_FOLLOWUP_GAMEMAP_BRANCH_ALREADY_APPLIED")
        else:
            done = False
            for btype in ("bank", "nightclub", "restaurant", "casino", "castle",
                          "carChase", "runaway", "packageGrab", "shootout"):
                bm = re.search(r"^([ \t]*)\} else if \(m\.type === '" + btype + r"'\) \{$",
                               gsrc, re.M)
                if bm:
                    ind = bm.group(1)
                    branch = (
                        f"{ind}}} else if (m.type === 'fiend') {{\n"
                        f"{ind}  var fiendName = m.name || 'Fiend';\n"
                        f"{ind}  markerHTML = '<div style=\"width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;\">' +\n"
                        f"{ind}    '<div style=\"width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#8BC34A,#558B2F);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(139,195,74,0.6);font-size:22px;cursor:pointer;\">🧟</div>' +\n"
                        f"{ind}    '<div style=\"position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(85,139,47,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;\">' + fiendName + '</div>' +\n"
                        f"{ind}    '</div>';\n"
                    )
                    gsrc = gsrc[:bm.start()] + branch + gsrc[bm.start():]
                    print(f"FIEND_FOLLOWUP_GAMEMAP_BRANCH_OK (before '{btype}' branch)")
                    done = True
                    break
            if not done:
                print("WARNING: no marker branch anchor found - Fiend marker branch NOT added")
                warned.append("gamemap-branch")
        # 48x62 location sizing (isLocationMarker).
        sm = re.search(r"var isLocationMarker = \(([^;]*)\);", gsrc)
        if sm and "'fiend'" in sm.group(1):
            print("FIEND_FOLLOWUP_GAMEMAP_SIZING_ALREADY_APPLIED")
        elif sm:
            gsrc = gsrc[:sm.end() - 2] + " || m.type === 'fiend'" + gsrc[sm.end() - 2:]
            print("FIEND_FOLLOWUP_GAMEMAP_SIZING_OK")
        else:
            print("WARNING: isLocationMarker line not found - Fiend sizing NOT added")
            warned.append("gamemap-sizing")
        if not _imbalances_ok(gorig, gsrc):
            print("WARNING: unbalanced brackets - GameMap.tsx NOT written")
            gsrc = gorig
            warned.append("gamemap-balance")
        if gsrc != gorig:
            GAMEMAP.write_text(gsrc)
            landed.append("gamemap")

    # ================= Part 4: index.tsx deps =================
    if not INDEX.exists():
        print("WARNING: app/(tabs)/index.tsx not found - Fiend deps NOT added")
        warned.append("index")
    else:
        src = INDEX.read_text(errors="ignore")
        iorig = src
        id0 = delta(src)
        src, status = _add_dep_to_array(
            src, r"const handleMarkerPress = useCallback\(", "nearbyFiends", "press")
        if status == "added":
            print("FIEND_FOLLOWUP_INDEX_PRESS_DEPS_OK")
        elif status == "already":
            print("FIEND_FOLLOWUP_INDEX_PRESS_DEPS_ALREADY_APPLIED")
        else:
            print(f"WARNING: handleMarkerPress deps {status} - Fiend taps may use a stale list")
            warned.append("index-press-deps")
        src, status = _add_dep_to_array(
            src, r"const mapMarkers = useMemo\(", "nearbyFiends", "markers")
        if status == "added":
            print("FIEND_FOLLOWUP_INDEX_MARKERS_DEPS_OK")
        elif status == "already":
            print("FIEND_FOLLOWUP_INDEX_MARKERS_DEPS_ALREADY_APPLIED")
        else:
            print(f"WARNING: mapMarkers deps {status} - Fiend markers may go stale")
            warned.append("index-markers-deps")
        if not _imbalances_ok(iorig, src):
            print("WARNING: unbalanced brackets - index.tsx NOT written")
            src = iorig
            warned.append("index-balance")
        if src != iorig:
            INDEX.write_text(src)
            landed.append("index")

    if warned:
        print("FIEND_FOLLOWUP_PARTIAL: " + ",".join(landed) +
              " (warnings: " + ",".join(warned) + ")")
    else:
        print("FIEND_FOLLOWUP_OK")


if __name__ == "__main__":
    main()
