#!/usr/bin/env python3
"""House marker mapping fix (frontend).

One-line fix for the missing house marker (diag 2, 2026-11-06 00:23 EST,
HOUSE_MARKER_2_DIAG_OK verdict=(b)):
  The entity batch fetches houses at call [15] (getNearbyHouses), but the
  return mapping assigns the `houses` field from results[14] -- the
  activity-centers result. So the `houses` field holds the centers
  data (empty while Overpass is down) and the real houses result at
  results[15] is fetched and thrown away. No house marker is ever
  built, even though the batch, the nearbyHouses derivation, the
  mapMarkers houses entry (type 'house' as const, no filter), the
  GameMap branch (72px house), and the tap handler are all correct.

This patch changes exactly one line in
frontend/hooks/useMapQueries.ts: the `houses` return-mapping line
reads results[15] instead of results[14]. activityCenters stays on
results[14]; fiends stays on results[16]; every other mapping line
is byte-identical.

Safety: the patch first re-discovers the batch order live (paren-depth
entry parsing, so a multi-line call counts once) and only applies the
fix when getNearbyHouses really is call [15]. If the batch order differs,
or the houses line does not read results[14], it changes nothing and
prints a WARNING. Does NOT touch the batch calls, imports, mapMarkers,
GameMap, or the backend. Does NOT re-map the duplicated getNearbyPlayers
at index 3 (out of scope).

Run:  python3 frontend/patch-house-marker-mapping-frontend.py
   or:  python3 frontend/patch-house-marker-mapping-frontend.py /path/to/app
Idempotent: rerun prints ALREADY_APPLIED, file unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
QUERIES = ROOT / "frontend" / "hooks" / "useMapQueries.ts"

MARKER_OK = "HOUSE_MARKER_MAPPING_OK"
MARKER_PARTIAL = "HOUSE_MARKER_MAPPING_PARTIAL"

_CALL_NAME_RE = re.compile(r"^\s*(?:withTimeout\()?([A-Za-z_$][\w$]*)\(")
_MAPPING_RE = re.compile(
    r"^([ \t]*)(\w+): results\[(\d+)\]\.status === 'fulfilled' \? "
    r"results\[\d+\]\.value : \[\],?[ \t]*$", re.M)


def delta(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"),
            s.count("["), s.count("]"))


def _imbalances_ok(before, after):
    """True when no bracket pair's imbalance changed."""
    b, a = delta(before), delta(after)
    return ((a[0] - a[1]) == (b[0] - b[1]) and (a[2] - a[3]) == (b[2] - b[3])
            and (a[4] - a[5]) == (b[4] - b[5]))


def _strip_strings(text):
    """Remove single/double-quoted string contents so paren counting
    never trips over a paren inside a string literal."""
    return re.sub(r"'[^']*'|\"[^\"]*\"", "''", text)


def _parse_batch_entries(body):
    """Split a Promise.allSettled array body into call entries.

    Paren-depth aware: a call that spans several lines counts once.
    Returns a list of {name, text} in call order.
    """
    lines = body.split("\n")
    entries = []
    depth = 0
    cur_lines = None
    for ln in lines:
        stripped = ln.strip()
        if cur_lines is None:
            if not stripped or "(" not in _strip_strings(ln):
                continue
            cur_lines = []
        cur_lines.append(ln)
        code = _strip_strings(ln)
        depth += code.count("(") - code.count(")")
        if depth <= 0 and stripped.endswith(","):
            text = "\n".join(cur_lines)
            m = _CALL_NAME_RE.match(text)
            entries.append({"name": m.group(1) if m else "?", "text": text})
            cur_lines = None
            depth = 0
    return entries


def _parse_mappings(src):
    """Return {field: (index, match)} for every return-mapping line."""
    mapping = {}
    for m in _MAPPING_RE.finditer(src):
        mapping[m.group(2)] = (int(m.group(3)), m)
    return mapping


def main():
    warned = []

    if not QUERIES.exists():
        print("WARNING: hooks/useMapQueries.ts not found - houses mapping NOT changed "
              "(looked for 'frontend/hooks/useMapQueries.ts')")
        print(MARKER_PARTIAL)
        return

    qsrc = QUERIES.read_text(errors="ignore")
    qorig = qsrc

    # ---- Step 1: discover the live batch order and confirm houses is [15].
    houses_idx = None
    m = re.search(r"Promise\.allSettled\(\[", qsrc)
    if not m:
        print("WARNING: Promise.allSettled anchor not found - houses mapping NOT changed "
              "(looked for 'Promise.allSettled([' in useMapQueries.ts)")
        warned.append("batch-anchor")
    else:
        start = m.end()
        close = re.search(r"\n[ \t]*\]\);", qsrc[start:])
        if not close:
            print("WARNING: Promise.allSettled close anchor not found - houses mapping NOT changed "
                  "(looked for the closing ']);' of the batch array)")
            warned.append("batch-close")
        else:
            body = qsrc[start:start + close.start()]
            entries = _parse_batch_entries(body)
            names = [e["name"] for e in entries]
            print(f"HOUSE_MARKER_MAPPING_BATCH_DISCOVERY: calls={len(entries)} "
                  f"calls={names}")
            houses_idx = next((i for i, e in enumerate(entries)
                               if e["name"] == "getNearbyHouses"), None)
            if houses_idx is None:
                print("WARNING: getNearbyHouses call not found in the entity batch - houses mapping "
                      "NOT changed (looked for 'getNearbyHouses(' in the Promise.allSettled call list)")
                warned.append("batch-call")
            elif houses_idx != 15:
                print(f"WARNING: getNearbyHouses is call [{houses_idx}], not [15] - houses mapping "
                      "NOT changed (batch order differs from diag 2; hand-check needed)")
                warned.append("batch-order")
            else:
                print("HOUSE_MARKER_MAPPING_BATCH_OK (getNearbyHouses is call [15])")

    if warned:
        print(f"{MARKER_PARTIAL} (warnings: {','.join(warned)})")
        return

    # ---- Step 2: find the houses return-mapping line.
    mapping = _parse_mappings(qsrc)
    if "houses" not in mapping:
        print("WARNING: houses return-mapping line not found - houses mapping NOT changed "
              "(looked for \"houses: results[N].status === 'fulfilled' ? results[N].value : [],\" "
              "in the return block)")
        print(f"{MARKER_PARTIAL} (warnings: mapping-line)")
        return

    cur_idx, match = mapping["houses"]
    line = match.group(0)
    if cur_idx == 15:
        print("HOUSE_MARKER_MAPPING_ALREADY_APPLIED "
              "(houses already reads results[15])")
        print(MARKER_OK)
        return
    if cur_idx != 14:
        print(f"WARNING: houses return-mapping line reads results[{cur_idx}], not results[14] - "
              "houses mapping NOT changed (looked for 'houses: results[14].status === "
              "'fulfilled' ? results[14].value : [],')")
        print(f"{MARKER_PARTIAL} (warnings: mapping-shape)")
        return

    # Sanity: activityCenters must still be the results[14] owner.
    ac_idx = mapping.get("activityCenters", (None, None))[0]
    if ac_idx != 14:
        print(f"WARNING: activityCenters return-mapping line reads results[{ac_idx}], not "
              "results[14] - houses mapping NOT changed (return block shape differs from diag 2)")
        print(f"{MARKER_PARTIAL} (warnings: mapping-shape)")
        return

    # ---- Step 3: change ONLY the houses line, results[14] -> results[15].
    indent = match.group(1)
    new_line = (f"{indent}houses: results[15].status === 'fulfilled' "
                f"? results[15].value : [],")
    # Preserve the line's trailing comma state exactly.
    if line.rstrip().endswith(","):
        pass  # new_line already ends with a comma
    else:
        new_line = new_line.rstrip(",")
    qsrc = qsrc[:match.start()] + new_line + qsrc[match.end():]

    # ---- Step 4: verify nothing else moved, then write.
    after = _parse_mappings(qsrc)
    changed = {f: (mapping[f][0], after[f][0])
               for f in mapping if f in after and mapping[f][0] != after[f][0]}
    if changed != {"houses": (14, 15)} or after.get("activityCenters", (None,))[0] != 14:
        print(f"WARNING: unexpected mapping drift after edit ({changed}) - file NOT written")
        print(f"{MARKER_PARTIAL} (warnings: drift)")
        return
    if not _imbalances_ok(qorig, qsrc):
        print("WARNING: unbalanced brackets - useMapQueries.ts NOT written")
        print(f"{MARKER_PARTIAL} (warnings: balance)")
        return

    QUERIES.write_text(qsrc)
    print("HOUSE_MARKER_MAPPING_OK")
    print("  before: houses: results[14].status === 'fulfilled' ? results[14].value : [],")
    print("  after:  houses: results[15].status === 'fulfilled' ? results[15].value : [],")
    print("  (activityCenters still results[14]; fiends still results[16]; all other lines unchanged)")


if __name__ == "__main__":
    main()
