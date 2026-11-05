#!/usr/bin/env python3
"""Street Legends live probe: print the EXACT text of the four OSM nearby
handlers and their per-cell fetch functions from live backend/server.py.

Run from repo root (/app):  python3 minigame-diag/diag-osm-loops.py
Optional arg: path to server.py (default: backend/server.py).

READ-ONLY: reads server.py and prints. Never edits it, never restarts
anything, never calls any endpoint or the network. Always finishes with
a summary line (OSM_LOOPS_DIAG_OK or OSM_LOOPS_DIAG_PARTIAL).

WHY: the OSM_FAST patch (backend/patch-osm-fast.py) ran PARTIAL on /app
(2026-11-05): the shared block + fetch mirrors (8s/cell, kumi fallback)
landed on all four endpoints, but the parallel-gather loop replacement
missed on EVERY endpoint -- "sequential loop anchor not found". The live
loop code differs from the patch templates. A follow-up patch needs the
REAL live loop text, and this probe prints it verbatim with line numbers.

For each endpoint (activity-centers, pharmacies, parks, billboards):
  1. The nearby handler's complete body, verbatim, with line numbers
     (from its route decorator / def line to the next top-level def).
  2. The per-cell fetch function's complete body, verbatim, with line
     numbers. Found by name first; if renamed, found by searching for
     the function whose body posts to that endpoint's *_OVERPASS_URL.
  3. A structural summary: how the handler invokes the fetch (exact
     call lines, whether the await sits inside a for loop, whether
     asyncio.gather / _osm_gather_cells is used, the loop header line,
     the cell variable / cells-function names). If the handler never
     calls its fetch function, that is stated explicitly and the lines
     that DO fetch are printed instead.
  4. Whether the OSM_FAST shared block is present, and whether the
     fetch already contains the kumi mirror + 8s timeout.
"""
import re
import sys
from pathlib import Path

SERVER = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("backend/server.py")

ENDPOINTS = [
    {
        "name": "activity-centers",
        "fetch_fn": "_activity_center_fetch_cell",
        "cells_fn": "_activity_center_cells",
        "handler_fn": "nearby_activity_centers",
        "url_const": "ACTIVITY_CENTER_OVERPASS_URL",
        "stem": "activity_center",
    },
    {
        "name": "pharmacies",
        "fetch_fn": "_pharmacy_fetch_cell",
        "cells_fn": "_pharmacy_cells",
        "handler_fn": "nearby_pharmacies",
        "url_const": "PHARMACY_OVERPASS_URL",
        "stem": "pharmacy",
    },
    {
        "name": "parks",
        "fetch_fn": "_park_fetch_cell",
        "cells_fn": "_park_cells",
        "handler_fn": "nearby_parks",
        "url_const": "PARK_OVERPASS_URL",
        "stem": "park",
    },
    {
        "name": "billboards",
        "fetch_fn": "_billboard_fetch_cell",
        "cells_fn": "_billboard_cells",
        "handler_fn": "nearby_billboards",
        "url_const": "BILLBOARD_OVERPASS_URL",
        "stem": "billboard",
    },
]

# A top-level def/class/decorator, or any other column-0 statement, ends
# the previous function's body (function bodies are always indented,
# except for a decorator block that belongs to the NEXT function).
TOP_LEVEL_RE = re.compile(r"^(async\s+def\s|def\s|class\s|@|[A-Za-z_][A-Za-z0-9_]*\s*=)")
DEF_LINE_RE = re.compile(r"^(async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(")


def index_functions(lines):
    """Map function name -> (start_line_idx, end_line_idx_exclusive).

    start_line_idx is the first decorator line above the def (if any),
    else the def line itself. end is the line just past the body:
    the next top-level def/class/decorator/statement, or EOF.
    Line indices are 0-based; printed line numbers are 1-based.
    """
    funcs = {}
    i = 0
    n = len(lines)
    while i < n:
        m = DEF_LINE_RE.match(lines[i])
        if not m:
            i += 1
            continue
        name = m.group(2)
        # Walk back over contiguous decorator lines at column 0.
        start = i
        j = i - 1
        while j >= 0 and lines[j].startswith("@"):
            start = j
            j -= 1
        # Body ends at the next top-level statement after the def line.
        k = i + 1
        while k < n:
            if TOP_LEVEL_RE.match(lines[k]):
                break
            k += 1
        # Strip trailing blank lines from the body.
        end = k
        while end > start and not lines[end - 1].strip():
            end -= 1
        # First definition wins; a duplicate name is noted by the caller.
        if name not in funcs:
            funcs[name] = (start, end)
        i = k if k > i else i + 1
    return funcs


def print_block(title, lines, start, end):
    print(f"===== {title} (lines {start + 1}-{end}) =====")
    for idx in range(start, end):
        print(f"{idx + 1:>6}: {lines[idx]}")
    print(f"===== END {title} =====")


def indent_of(line):
    return len(line) - len(line.lstrip(" "))


def enclosing_for(lines, call_idx, body_start):
    """If lines[call_idx] sits inside a for loop, return the loop header
    line (text, 1-based line no). Else None. Scans upward for the nearest
    `for ...:` line with a smaller indent, requiring every line between
    it and the call to be more indented than the loop header (or blank).
    """
    call_indent = indent_of(lines[call_idx])
    j = call_idx - 1
    while j >= body_start:
        line = lines[j]
        if line.strip():
            ind = indent_of(line)
            if ind < call_indent and re.match(r"\s*for\s+.+:\s*$", line):
                return line.strip(), j + 1
            if ind < call_indent and re.match(
                r"\s*(def\s|async\s+def\s|return\s|if\s|elif\s|else\s*:|while\s|try\s*:|except|finally\s*:|with\s)",
                line,
            ):
                # Crossed a block boundary that is not a for loop.
                return None
        j -= 1
    return None


def find_fetch_by_url(lines, funcs, url_const, stem):
    """Find the function whose body posts to url_const (renamed-fetch
    fallback). Returns (name, (start, end)) or (None, None).

    The OSM_FAST mirror loop posts to a loop variable over
    OSM_OVERPASS_MIRRORS, so the *_OVERPASS_URL const may no longer
    appear in the fetch body at all -- match on the post + overpass
    markers too, not on the const alone. Several functions post to
    Overpass (one per endpoint), so candidates are ranked: the one
    whose name contains this endpoint's stem (e.g. "activity_center")
    wins over a merely fetch-shaped one.
    """
    def candidates(pred):
        scored = []
        for name, (start, end) in funcs.items():
            body = "".join(lines[start:end])
            if not pred(body):
                continue
            score = 0
            if stem in name:
                score += 2
            if "fetch" in name:
                score += 1
            scored.append((score, start, name, (start, end)))
        if not scored:
            return None, None
        scored.sort(key=lambda t: (-t[0], t[1]))
        # A candidate only counts if its name carries this endpoint's
        # stem -- otherwise it is some OTHER endpoint's fetch function,
        # and claiming it would be a false positive. No stem match means
        # this endpoint's fetch is genuinely not found (or renamed
        # beyond recognition); the caller reports NOT FOUND.
        if scored[0][0] < 2:
            return None, None
        return scored[0][2], scored[0][3]

    name, span = candidates(
        lambda b: url_const in b and ("client.post" in b or "httpx" in b)
    )
    if name is not None:
        return name, span
    name, span = candidates(
        lambda b: "client.post" in b
        and ("overpass" in b.lower() or "OSM_OVERPASS_MIRRORS" in b or "_osm_url" in b)
    )
    if name is not None:
        return name, span
    name, span = candidates(lambda b: url_const in b)
    if name is not None:
        return name, span
    return None, None


def summarize_handler(lines, start, end, ep, fetch_name):
    """Structural summary of how the handler invokes its fetch function."""
    body = lines[start:end]
    fetch_lines = []  # (1-based line no, text) mentioning the fetch fn
    for off, line in enumerate(body):
        if fetch_name in line:
            fetch_lines.append((start + off + 1, line.rstrip("\n")))
    gather_lines = [
        (start + off + 1, line.rstrip("\n"))
        for off, line in enumerate(body)
        if "asyncio.gather" in line or "_osm_gather_cells" in line
    ]
    loop_headers = [
        (start + off + 1, line.strip())
        for off, line in enumerate(body)
        if re.match(r"\s*for\s+.+\s+in\s+.+:\s*$", line)
    ]
    cells_calls = [
        (start + off + 1, line.strip())
        for off, line in enumerate(body)
        if ep["cells_fn"] in line
    ]

    print(f"--- {ep['name']} handler structure ---")
    print(f"handler: {ep['handler_fn']}  fetch fn searched: {fetch_name}")
    if loop_headers:
        for ln, text in loop_headers:
            print(f"  loop header line {ln}: {text}")
    else:
        print("  loop header: NONE (no `for ... in ...:` in handler)")
    if cells_calls:
        for ln, text in cells_calls:
            print(f"  cells() call line {ln}: {text}")
    else:
        print(f"  cells() call: NONE (no `{ep['cells_fn']}(` in handler)")
    if gather_lines:
        for ln, text in gather_lines:
            print(f"  gather line {ln}: {text.strip()}")
    else:
        print("  gather: NONE (no asyncio.gather / _osm_gather_cells)")

    if not fetch_lines:
        print(f"  FETCH NOT CALLED: `{fetch_name}` never appears in handler")
        other = [
            (start + off + 1, line.rstrip("\n"))
            for off, line in enumerate(body)
            if ("await" in line and ("fetch" in line.lower() or "gather" in line.lower()))
            or "fetch_cell" in line
            or "_osm_" in line
        ]
        if other:
            print("  fetch-related lines that DO exist in handler:")
            for ln, text in other:
                print(f"    line {ln}: {text.strip()}")
        else:
            print("  no fetch-related call lines in handler at all")
        return "NOT_CALLED"

    pattern = "OTHER"
    for ln, text in fetch_lines:
        idx = ln - 1
        loop = enclosing_for(lines, idx, start)
        is_await = "await" in text
        is_arg = re.search(r"\(\s*[^)]*" + re.escape(fetch_name) + r"\b", text) and "await" not in text
        print(f"  fetch mention line {ln}: {text.strip()}")
        if loop:
            print(f"    -> inside for loop (header line {loop[1]}): {loop[0]}")
            if is_await:
                pattern = "AWAIT_IN_FOR_LOOP"
        if "asyncio.gather" in text or "_osm_gather_cells" in text:
            if "for " in text and " in " in text:
                pattern = "GATHER_LISTCOMP"
            else:
                pattern = "GATHER_HELPER"
        if is_arg and pattern == "OTHER":
            m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)\s*\(", text)
            pattern = f"PASSED_AS_ARG to {m.group(1)}" if m else "PASSED_AS_ARG"
    print(f"  invocation pattern: {pattern}")
    return pattern


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root (/app).")
        print("OSM_LOOPS_DIAG_PARTIAL missing=server.py")
        sys.exit(1)
    lines = SERVER.read_text().splitlines()
    print(f"server.py: {len(lines)} lines")
    funcs = index_functions(lines)
    print(f"top-level functions indexed: {len(funcs)}")

    shared = "OSM_OVERPASS_MIRRORS = [" in "".join(lines)
    print(f"OSM_FAST shared block (OSM_OVERPASS_MIRRORS): {'PRESENT' if shared else 'ABSENT'}")

    missing = []
    for ep in ENDPOINTS:
        name = ep["name"]
        print()
        print(f"########## {name} ##########")

        # --- handler ---
        h = funcs.get(ep["handler_fn"])
        if h is None:
            print(f"HANDLER NOT FOUND: looked for 'async def {ep['handler_fn']}(' "
                  f"at column 0 (and anywhere in file)")
            missing.append(f"{name}-handler")
            h_start = h_end = None
        else:
            h_start, h_end = h
            print_block(
                f"{name} HANDLER {ep['handler_fn']}", lines, h_start, h_end
            )

        # --- fetch function: by name, else by Overpass-URL search ---
        f = funcs.get(ep["fetch_fn"])
        found_via = "name"
        if f is None:
            fname, f = find_fetch_by_url(lines, funcs, ep["url_const"], ep["stem"])
            if f is not None:
                found_via = f"Overpass-URL search (renamed: actual name {fname})"
                ep_fetch = fname
            else:
                print(f"FETCH NOT FOUND: looked for 'async def {ep['fetch_fn']}(' "
                      f"and for any function posting to {ep['url_const']}")
                missing.append(f"{name}-fetch")
                f_start = f_end = None
                ep_fetch = ep["fetch_fn"]
        else:
            ep_fetch = ep["fetch_fn"]
        if f is not None:
            f_start, f_end = f
            if found_via != "name":
                print(f"FETCH FOUND VIA {found_via}")
            print_block(
                f"{name} FETCH {ep_fetch}", lines, f_start, f_end
            )
            fbody = "".join(lines[f_start:f_end])
            has_mirror = "OSM_OVERPASS_MIRRORS" in fbody
            has_timeout = "OSM_CELL_TIMEOUT" in fbody
            print(f"fetch mirror (OSM_OVERPASS_MIRRORS in fetch): "
                  f"{'YES' if has_mirror else 'NO'}")
            print(f"fetch 8s timeout (OSM_CELL_TIMEOUT in fetch): "
                  f"{'YES' if has_timeout else 'NO'}")
            if "kumi" in fbody:
                print("fetch kumi mirror string: YES")
            else:
                print("fetch kumi mirror string: NO")
            # Raw timeout values still present in the fetch, for reference.
            for m in re.finditer(r"timeout\s*=\s*([0-9.]+)", fbody):
                print(f"fetch timeout literal: {m.group(1)}s")

        # --- structural summary (handler only; needs the handler) ---
        if h is not None:
            summarize_handler(lines, h_start, h_end, ep, ep_fetch)
        else:
            print(f"structure summary skipped ({name} handler not found)")

    print()
    if missing:
        print("OSM_LOOPS_DIAG_PARTIAL missing=" + ",".join(missing))
    else:
        print("OSM_LOOPS_DIAG_OK")


if __name__ == "__main__":
    main()
