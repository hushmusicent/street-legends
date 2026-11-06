#!/usr/bin/env python3
"""Street Legends backend: put the working Overpass mirror first (.fr)
and bust the stale empty cache.

Run from repo root: python3 backend/patch-osm-mirror-fr.py
Idempotent - safe to re-run.

WHY (probe results 2026-11-06):
  - VERDICT (a), OSM_ALTERNATIVES_DIAG_OK: from /app,
    https://overpass.openstreetmap.fr/api/interpreter answers 200 in
    0.9s with REAL Toledo data (2 usable centers in the UT cell:
    'Davis College', 'The University of Toledo'). Every other new
    mirror failed (atownsend/geofabrik/maprva/openplaceguide/osm.jp
    DNS/404/empty); .de still refuses; kumi still times out.
  - ROOT CAUSE of the empty map: the only reachable mirror until now
    (osm.ch) is SWISS-REGIONAL -- it returns 19 universities for
    Zurich and ZERO for Toledo. The data exists; the mirror didn't.
  - THE TRAP: the v2 handler marks a grid cell as fetched for 24h
    even when Overpass returns an EMPTY list ([] is not None, so the
    cell is stamped). Toledo cells were cached empty on 2026-11-05
    ~22:43 EST and stay "fresh" until ~22:43 EST 2026-11-06.
    Swapping the mirror alone would still serve [] until then.

MECHANISM (backend only):
  1. MIRROR: insert overpass.openstreetmap.fr FIRST in
     OSM_OVERPASS_MIRRORS (osm.ch, .de, kumi stay after it, in order).
     Order matters: a 200-with-0-elements counts as success and stops
     the fallback loop, so the working mirror must be tried first.
  2. CACHE EPOCH: a new module constant OSM_CACHE_EPOCH = 2, written
     into every OSM cache stamp and required by every OSM freshness
     check. Rows written before this epoch (no osm_epoch field) are
     treated as stale, so the very next nearby call re-fetches every
     cell with the new mirror. No real-data rows are deleted -- only
     the freshness markers are invalidated. No new endpoint, no
     admin route.
  3. EMPTY FETCHES NO LONGER STAMP: `if <var> is None:` becomes
     `if not <var>:` in each handler's write loop, so an empty 200
     behaves like a failed fetch for caching purposes (retries next
     call instead of caching the empty for 24h). The no-fallback rule
     is unchanged: the endpoint still returns cached real rows or [].
     Tradeoff: a cell that is genuinely empty re-fetches on every
     nearby call (bounded by the shared 10s total budget).

SCOPE: all four OSM nearby endpoints -- activity-centers, pharmacies,
parks, billboards. Each handler's cache logic is duplicated (there is
NO shared cache helper), so each of the four is edited in place,
scoped to its own handler function. Queries, timeouts (8s/cell, 10s
budget), the no-fallback rule, presence, and every frontend file are
untouched. The pre-existing v1 fictional-center cleanup delete_many
in the centers handler is untouched.
"""
import re
import sys
import py_compile
from pathlib import Path

SERVER = Path("backend/server.py")
FR_URL = "https://overpass.openstreetmap.fr/api/interpreter"
EPOCH = 2
MARKER_OK = "OSM_MIRROR_FR_OK"
MARKER_PARTIAL = "OSM_MIRROR_FR_PARTIAL"

ENDPOINTS = [
    {"name": "activity-centers", "handler": "nearby_activity_centers", "var": "centers"},
    {"name": "pharmacies", "handler": "nearby_pharmacies", "var": "pharmacies"},
    {"name": "parks", "handler": "nearby_parks", "var": "parks"},
    {"name": "billboards", "handler": "nearby_billboards", "var": "boards"},
]

FRESH_OLD = 'if cached and cached.get("fetched_at"):'
FRESH_NEW = 'if cached and cached.get("fetched_at") and cached.get("osm_epoch") == OSM_CACHE_EPOCH:'
STAMP_OLD = '{"$set": {"fetched_at": now.isoformat()}},'
STAMP_NEW = '{"$set": {"fetched_at": now.isoformat(), "osm_epoch": OSM_CACHE_EPOCH}},'


def _find_list_span(src):
    """Return (start, end) of the OSM_OVERPASS_MIRRORS list literal, or None.

    Finds 'OSM_OVERPASS_MIRRORS = [' then the first ']' after it. URL
    strings never contain brackets, so the first ']' closes the list.
    Handles multi-line and single-line forms, either quote style.
    """
    m = re.search(r"OSM_OVERPASS_MIRRORS\s*=\s*\[", src)
    if not m:
        return None
    close = src.find("]", m.end())
    if close == -1:
        return None
    return (m.start(), close + 1)


def _handler_span(lines, handler_fn):
    """(start, end) line indexes of a handler function, or None.

    Starts at the `async def <handler>(` line; ends at the next
    top-level line (async def / def / class / decorator at column 0).
    """
    start = None
    for i, line in enumerate(lines):
        if line.startswith("async def " + handler_fn + "("):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        line = lines[j]
        if (
            line.startswith("async def ")
            or line.startswith("def ")
            or line.startswith("class ")
            or line.startswith("@")
        ):
            end = j
            break
    return (start, end)


def _edit_line(lines, start, end, old, new):
    """Replace the one line in lines[start:end] whose stripped text == old.

    Returns 'ok' | 'already' | 'missing' | 'ambiguous'. 'already' when
    no old line remains and a line whose stripped text == new is
    present. Indentation of the original line is preserved. Mutates
    lines in place on 'ok'.
    """
    hits = [i for i in range(start, end) if lines[i].strip() == old]
    if len(hits) == 1:
        i = hits[0]
        indent = lines[i][: len(lines[i]) - len(lines[i].lstrip(" "))]
        eol = "\n" if lines[i].endswith("\n") else ""
        lines[i] = indent + new + eol
        return "ok"
    if len(hits) > 1:
        return "ambiguous"
    for i in range(start, end):
        if lines[i].strip() == new:
            return "already"
    return "missing"


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - nothing changed")
        print(MARKER_PARTIAL)
        return 0

    src = SERVER.read_text()
    orig = src
    warnings = []
    landed = []

    # --- Part 1: mirror first -------------------------------------------
    span = _find_list_span(src)
    if span is None:
        print(
            "WARNING: OSM_OVERPASS_MIRRORS definition not found - nothing "
            "changed (looked for 'OSM_OVERPASS_MIRRORS = [')"
        )
        print(MARKER_PARTIAL)
        return 0
    start, end = span
    list_text = src[start:end]
    if FR_URL in list_text:
        print("ALREADY_APPLIED: openstreetmap.fr already in OSM_OVERPASS_MIRRORS")
    else:
        body_start = list_text.index("[") + 1
        body = list_text[body_start:-1]  # between [ and ]
        if body.strip() == "":
            new_list = 'OSM_OVERPASS_MIRRORS = [\n    "%s",\n]' % FR_URL
        elif "\n" in body:
            entry_m = re.search(r"(\n[ \t]*)(['\"])", body)
            if not entry_m:
                print(
                    "WARNING: OSM_OVERPASS_MIRRORS entries not recognized - "
                    "nothing changed (looked for a quoted URL entry inside "
                    "OSM_OVERPASS_MIRRORS)"
                )
                print(MARKER_PARTIAL)
                return 0
            indent = entry_m.group(1)[1:]  # drop the leading newline
            quote = entry_m.group(2)
            insert_at = body.index(entry_m.group(0))
            new_body = (
                body[:insert_at]
                + "\n"
                + indent
                + quote
                + FR_URL
                + quote
                + ","
                + body[insert_at:]
            )
            new_list = list_text[:body_start] + new_body + "]"
        else:
            quote = '"' if '"' in body else "'"
            new_body = " " + quote + FR_URL + quote + "," + body
            new_list = list_text[:body_start] + new_body + "]"
        src = src[:start] + new_list + src[end:]
        print("OK: openstreetmap.fr added first in OSM_OVERPASS_MIRRORS")
        landed.append("mirror")

    # --- Part 2: cache epoch constant ------------------------------------
    # Anchor: immediately after the mirrors list closing bracket.
    # The per-endpoint edits reference OSM_CACHE_EPOCH, so if the
    # constant can neither be found nor added, the handler edits are
    # skipped (an undefined name at runtime would be worse than stale).
    epoch_ok = False
    if re.search(r"^OSM_CACHE_EPOCH\s*=", src, re.MULTILINE):
        print("ALREADY_APPLIED: OSM_CACHE_EPOCH already defined")
        epoch_ok = True
    else:
        span = _find_list_span(src)
        if span is None:
            print(
                "WARNING: OSM_OVERPASS_MIRRORS definition lost after mirror "
                "edit - epoch NOT added, handler cache edits skipped"
            )
            warnings.append("epoch-anchor")
        else:
            insert_at = span[1]
            epoch_block = (
                "\n# OSM_MIRROR_FR: cache epoch -- bump when the mirror set "
                "changes so\n# cells cached empty under a dead/regional "
                "mirror re-fetch once.\n# Rows written before this epoch (no "
                "osm_epoch field) are stale.\nOSM_CACHE_EPOCH = %d\n" % EPOCH
            )
            src = src[:insert_at] + epoch_block + src[insert_at:]
            print("OK: OSM_CACHE_EPOCH = %d added after OSM_OVERPASS_MIRRORS" % EPOCH)
            landed.append("epoch")
            epoch_ok = True

    # --- Parts 3-5: per-endpoint cache edits ------------------------------
    lines = src.splitlines(keepends=True)
    for ep in ENDPOINTS:
        name = ep["name"]
        if not epoch_ok:
            print(
                f"WARNING: {name} cache edits skipped - OSM_CACHE_EPOCH "
                f"is not defined"
            )
            warnings.append(f"{name}-epoch")
            continue
        span = _handler_span(lines, ep["handler"])
        if span is None:
            print(
                f"WARNING: {name} handler not found - cache NOT updated "
                f"(looked for 'async def {ep['handler']}(')"
            )
            warnings.append(f"{name}-handler")
            continue
        hstart, hend = span

        # 3. Freshness gate: require the epoch.
        st = _edit_line(lines, hstart, hend, FRESH_OLD, FRESH_NEW)
        if st == "ok":
            print(f"OK: {name} freshness check requires osm_epoch == OSM_CACHE_EPOCH")
            landed.append(f"{name}-fresh")
        elif st == "already":
            print(f"ALREADY_APPLIED: {name} freshness check")
        else:
            print(
                f"WARNING: {name} freshness gate matched {st} - cache NOT "
                f"updated for {name} (looked for "
                f"'{FRESH_OLD}' in {ep['handler']})"
            )
            warnings.append(f"{name}-fresh")

        # 4. Cache stamp: write the epoch.
        st = _edit_line(lines, hstart, hend, STAMP_OLD, STAMP_NEW)
        if st == "ok":
            print(f"OK: {name} cache stamp writes osm_epoch")
            landed.append(f"{name}-stamp")
        elif st == "already":
            print(f"ALREADY_APPLIED: {name} cache stamp")
        else:
            print(
                f"WARNING: {name} cache stamp matched {st} - cache NOT "
                f"updated for {name} (looked for "
                f"'{STAMP_OLD}' in {ep['handler']})"
            )
            warnings.append(f"{name}-stamp")

        # 5. Empty fetches no longer stamp: `if <var> is None:` -> `if not <var>:`.
        empty_old = f"if {ep['var']} is None:"
        empty_new = f"if not {ep['var']}:"
        st = _edit_line(lines, hstart, hend, empty_old, empty_new)
        if st == "ok":
            print(f"OK: {name} empty fetch no longer stamps the cache")
            landed.append(f"{name}-empty")
        elif st == "already":
            print(f"ALREADY_APPLIED: {name} empty-fetch check")
        else:
            print(
                f"WARNING: {name} empty-fetch check matched {st} - cache "
                f"NOT updated for {name} (looked for "
                f"'{empty_old}' in {ep['handler']})"
            )
            warnings.append(f"{name}-empty")

    if landed:
        src = "".join(lines)
        # Syntax check the patched file before declaring success.
        tmp = None
        try:
            import tempfile

            tmp = tempfile.NamedTemporaryFile(
                "w", suffix=".py", delete=False, encoding="utf-8"
            )
            tmp.write(src)
            tmp.close()
            py_compile.compile(tmp.name, doraise=True)
        except Exception as exc:
            print("WARNING: patched server.py failed syntax check - NOT written")
            print("  %s" % exc)
            print(MARKER_PARTIAL)
            return 0
        finally:
            if tmp is not None:
                try:
                    import os

                    os.unlink(tmp.name)
                except Exception:
                    pass
        SERVER.write_text(src)

    if src == orig and not landed:
        print("ALREADY_APPLIED: no changes needed")
    if warnings:
        print(
            MARKER_PARTIAL
            + ": "
            + ", ".join(landed if landed else ["nothing changed"])
            + " (warnings: "
            + ", ".join(warnings)
            + ")"
        )
    else:
        print(MARKER_OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
