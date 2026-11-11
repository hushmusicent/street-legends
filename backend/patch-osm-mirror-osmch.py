"""Street Legends backend: add the reachable Overpass mirror (osm.ch) first.

Run from repo root: python3 backend/patch-osm-mirror-osmch.py
Idempotent - safe to re-run.

WHY (probe result 2026-11-05, OSM_MIRRORS_DIAG_OK verdict=(a)):
  - From /app, only ONE of six Overpass mirrors answers:
    https://overpass.osm.ch/api/interpreter. overpass-api.de refuses
    instantly (Errno 111), kumi times out, private.coffee / nchc /
    openstreetmap.ru did not answer either.
  - The four OSM fetch functions (_activity_center_fetch_cell,
    _pharmacy_fetch_cell, _park_fetch_cell, _billboard_fetch_cell)
    all loop over OSM_OVERPASS_MIRRORS in order, so the fix is to put
    the working mirror FIRST in that list. The centers endpoint
    returns 0 at UT because every fetch fails on both dead mirrors
    and the cache is empty; with osm.ch first, the first try succeeds.

MECHANISM: insert "https://overpass.osm.ch/api/interpreter" as the
first entry of the live OSM_OVERPASS_MIRRORS definition, keeping
overpass-api.de and overpass.kumi.systems after it as fallbacks.
Nothing else changes: no query changes, no timeout changes (8s/cell,
10s total budget stay), no cache changes, no response-shape changes,
no frontend changes, no position-pipeline changes. The old
per-endpoint *_OVERPASS_URL consts (all still overpass-api.de) are
NOT used by the fetch functions (URL literals NONE), so they are
left alone.

TOUCHES NOTHING ELSE: only the OSM_OVERPASS_MIRRORS list.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OSMCH_URL = "https://overpass.osm.ch/api/interpreter"
MARKER_OK = "OSM_MIRROR_OSMCH_OK"
MARKER_PARTIAL = "OSM_MIRROR_OSMCH_PARTIAL"

# Exact anchors the WARNINGs name (probe-verified live shape).
LIST_ANCHOR = "OSM_OVERPASS_MIRRORS = ["


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


def main():
    if not SERVER.exists():
        print("WARNING: backend/server.py not found - mirror NOT added")
        print(MARKER_PARTIAL)
        return 0

    src = SERVER.read_text()
    span = _find_list_span(src)
    if span is None:
        print(
            "WARNING: OSM_OVERPASS_MIRRORS definition not found - mirror "
            "NOT added (looked for 'OSM_OVERPASS_MIRRORS = [')"
        )
        print(MARKER_PARTIAL)
        return 0

    start, end = span
    list_text = src[start:end]

    if OSMCH_URL in list_text:
        print("ALREADY_APPLIED: osm.ch already in OSM_OVERPASS_MIRRORS")
        print(MARKER_OK)
        return 0

    body_start = list_text.index("[") + 1
    body = list_text[body_start:-1]  # between [ and ]

    if body.strip() == "":
        # Empty list: single entry, multi-line style.
        new_list = 'OSM_OVERPASS_MIRRORS = [\n    "%s",\n]' % OSMCH_URL
    elif "\n" in body:
        # Multi-line list: insert before the first entry, matching its
        # indentation and quote style.
        entry_m = re.search(r"(\n[ \t]*)(['\"])", body)
        if not entry_m:
            print(
                "WARNING: OSM_OVERPASS_MIRRORS entries not recognized - "
                "mirror NOT added (looked for a quoted URL entry inside "
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
            + OSMCH_URL
            + quote
            + ","
            + body[insert_at:]
        )
        new_list = list_text[:body_start] + new_body + "]"
    else:
        # Single-line list: insert right after '['.
        quote = '"' if '"' in body else "'"
        new_body = " " + quote + OSMCH_URL + quote + "," + body
        new_list = list_text[:body_start] + new_body + "]"

    new_src = src[:start] + new_list + src[end:]
    SERVER.write_text(new_src)

    # Syntax check the patched file before declaring success.
    import py_compile

    try:
        py_compile.compile(str(SERVER), doraise=True)
    except py_compile.PyCompileError as exc:
        # Roll back: a broken server.py is worse than no patch.
        SERVER.write_text(src)
        print("WARNING: patched server.py failed syntax check - rolled back")
        print("  %s" % exc)
        print(MARKER_PARTIAL)
        return 0

    print("OK: osm.ch added first in OSM_OVERPASS_MIRRORS")
    print("OK: new list order:")
    for line in new_list.splitlines():
        print("    " + line)
    print(MARKER_OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
