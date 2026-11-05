"""Street Legends backend: parallelize the four OSM nearby-handler loops.
Run from repo root: python3 backend/patch-osm-parallel.py
Idempotent - safe to re-run.

WHY (probe result 2026-11-05, OSM_LOOPS_DIAG_OK): the OSM_FAST patch
landed its mirrors + 8s/cell timeouts, but its parallel-loop replacement
missed on all four endpoints. Its loop regex required `__DB__` in the
loop body -- but live server.py uses `db.` (the `__DB__` placeholder only
exists in the patch-template files). Worse, the live loop is NOT a bare
fetch loop: each pass interleaves a cache read, the awaited fetch,
per-item DB upserts, and a cache stamp. A gather replacement cannot just
swap the await.

MECHANISM (two-phase split, per handler -- the loop body is reused
verbatim, only restructured):
  - PHASE 1: the existing loop, unchanged, except the awaited fetch is
    replaced by collecting the stale cell into `_osm_stale`. The cache
    read + freshness check + `if fresh: continue` run exactly as before.
  - GATHER: `_osm_gather_cells(_osm_stale, <fetch_fn>)` (OSM_FAST shared
    helper: parallel under a 10s total budget; a cell that times out or
    errors yields None). If the helper is absent, this patch adds it.
  - PHASE 2: a second loop over `zip(_osm_stale, _osm_results)` that runs
    the EXISTING write block verbatim (the `if <var> is None: continue`,
    per-item upserts, cache stamp) with each cell's already-fetched
    results. Sequential DB writes are fast local Mongo ops -- fine.
  - Fresh cells are skipped in phase 1 exactly as before (no fetch, no
    writes). A failed cell (None) is skipped in phase 2 and NOT stamped,
    so it retries next call -- same as now. The final find query, dedupe,
    response shape, and return statements are untouched.

WORST CASE per endpoint: ~10s total budget (was 4 cells x 8s = 32s
sequential after OSM_FAST, 120s before it). The frontend's 5s per-call
timeout still bounds the client side.

TOUCHES NOTHING ELSE: the OSM queries, fetch functions, mirrors/timeouts,
cache collections, no-fallback rule, presence/buy/sell endpoints, robbery
code, and all frontend files are untouched.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

ENDPOINTS = [
    {
        "name": "activity-centers",
        "fetch_fn": "_activity_center_fetch_cell",
        "cells_fn": "_activity_center_cells",
        "handler_fn": "nearby_activity_centers",
    },
    {
        "name": "pharmacies",
        "fetch_fn": "_pharmacy_fetch_cell",
        "cells_fn": "_pharmacy_cells",
        "handler_fn": "nearby_pharmacies",
    },
    {
        "name": "parks",
        "fetch_fn": "_park_fetch_cell",
        "cells_fn": "_park_cells",
        "handler_fn": "nearby_parks",
    },
    {
        "name": "billboards",
        "fetch_fn": "_billboard_fetch_cell",
        "cells_fn": "_billboard_cells",
        "handler_fn": "nearby_billboards",
    },
]

_GATHER_HELPER = '''
# OSM_PARALLEL: parallel cell-fetch helper (added only if OSM_FAST's
# shared block is absent). Fetches cells concurrently under a 10s total
# budget; a cell that times out or errors yields None (not cached,
# retries next call); cached rows are still served by the caller.
OSM_TOTAL_BUDGET = 10.0   # seconds for all cells of one nearby call


async def _osm_gather_cells(cells, fetch_fn):
    """Fetch Overpass cells in parallel under a total budget.
    Returns a list aligned with `cells`; a cell that times out or
    errors yields None (its cached rows are still served below)."""
    import asyncio
    if not cells:
        return []
    try:
        results = await asyncio.wait_for(
            asyncio.gather(
                *[fetch_fn(ck, cs, cw, cn, ce) for ck, cs, cw, cn, ce in cells],
                return_exceptions=True,
            ),
            timeout=OSM_TOTAL_BUDGET,
        )
    except asyncio.TimeoutError:
        logging.warning("OSM total budget %.1fs exceeded for %d cells",
                        OSM_TOTAL_BUDGET, len(cells))
        return [None] * len(cells)
    return [r if not isinstance(r, BaseException) else None for r in results]

'''

# Loop header: `for cell_key, cs, cw, cn, ce in <cells_fn>(<args>):`
# Args are captured and reused verbatim (drift-tolerant); the cells fn
# must end with `_cells`.
_HDR_RE = re.compile(
    r"^([ ]*)for cell_key, cs, cw, cn, ce in (\w+)\(([^)]*)\)\s*:\s*$"
)
# Fetch call: `<var> = await <fetch_fn>(<args>)`
# The fetch fn must end with `_fetch_cell`; args must mention cell_key.
_FETCH_RE = re.compile(
    r"^([ ]*)(\w+) = await (\w+)\(([^)]*)\)\s*$"
)
# Next top-level def/class/decorator (end of a handler function span).
_NEXT_TOP_RE = re.compile(r"^(?:async def |def |class |@)", re.MULTILINE)


def _handler_span(src, handler_fn):
    """(start, end) char offsets of a handler function, or None."""
    m = re.search(r"^async def " + re.escape(handler_fn) + r"\(", src, re.MULTILINE)
    if not m:
        return None
    start = m.start()
    m2 = _NEXT_TOP_RE.search(src, m.end())
    end = m2.start() if m2 else len(src)
    return (start, end)


def _indent_of(line):
    return len(line) - len(line.lstrip(" "))


def _split_loop(span_text, ep):
    """Find the cell loop inside one handler span and split its body.

    Returns (hdr_line_idx, body_start_idx, body_end_idx, fetch_idx,
    header_indent, body_indent, cells_fn, fetch_fn, result_var) or
    (None, <reason>) when the loop cannot be recognized."""
    lines = span_text.splitlines(keepends=True)
    hdr_idx = None
    cells_fn = None
    for i, line in enumerate(lines):
        m = _HDR_RE.match(line.rstrip("\n"))
        if m and m.group(2).endswith("_cells"):
            hdr_idx = i
            cells_fn = m.group(2)
            break
    if hdr_idx is None:
        return None, (
            f"cell loop header not found - parallel loop NOT added "
            f"(looked for 'for cell_key, cs, cw, cn, ce in "
            f"{ep['cells_fn']}(min_lat, min_lng, max_lat, max_lng):')"
        )
    header_indent = _indent_of(lines[hdr_idx])
    # Loop body: lines after the header, indented deeper than the header
    # (blank lines ride along); ends at the first non-blank line at or
    # above the header's indent.
    body_start = hdr_idx + 1
    body_end = body_start
    while body_end < len(lines):
        line = lines[body_end]
        if line.strip() == "":
            body_end += 1
            continue
        if _indent_of(line) <= header_indent:
            break
        body_end += 1
    # Trim trailing blank lines from the body.
    while body_end > body_start and lines[body_end - 1].strip() == "":
        body_end -= 1
    if body_end <= body_start:
        return None, (
            "cell loop body is empty - parallel loop NOT added "
            f"(loop header found in {ep['handler_fn']}, no body lines)"
        )
    # Fetch call inside the body.
    fetch_idx = None
    fetch_fn = None
    result_var = None
    for j in range(body_start, body_end):
        m = _FETCH_RE.match(lines[j].rstrip("\n"))
        if m and m.group(3).endswith("_fetch_cell") and "cell_key" in m.group(4):
            fetch_idx = j
            result_var = m.group(2)
            fetch_fn = m.group(3)
            break
    if fetch_idx is None:
        return None, (
            "fetch call anchor not found - parallel loop NOT added "
            f"(looked for '{ep['fetch_fn']}(cell_key, cs, cw, cn, ce)' "
            f"inside {ep['handler_fn']})"
        )
    body_indent = _indent_of(lines[fetch_idx])
    preamble = "".join(lines[body_start:fetch_idx])
    write_block = "".join(lines[fetch_idx + 1:body_end])
    if "fresh" not in preamble or "find_one" not in preamble:
        return None, (
            "loop shape not recognized - parallel loop NOT added "
            f"(freshness check / cache read missing before the fetch call "
            f"in {ep['handler_fn']})"
        )
    if "update_one" not in write_block:
        return None, (
            "loop shape not recognized - parallel loop NOT added "
            f"(upsert / cache stamp missing after the fetch call "
            f"in {ep['handler_fn']})"
        )
    return (
        (hdr_idx, body_start, body_end, fetch_idx,
         header_indent, body_indent, cells_fn, fetch_fn, result_var),
        None,
    )


def _restructure(span_text, ep):
    """Rewrite one handler span's cell loop into two phases.

    Returns (new_span_text, status) where status is 'ok',
    'already', or ('warn', reason)."""
    if "_osm_gather_cells" in span_text:
        return span_text, "already"
    split, reason = _split_loop(span_text, ep)
    if split is None:
        return span_text, ("warn", reason)
    (hdr_idx, body_start, body_end, fetch_idx,
     header_indent, body_indent, cells_fn, fetch_fn, result_var) = split
    lines = span_text.splitlines(keepends=True)
    header_line = lines[hdr_idx]
    preamble = lines[body_start:fetch_idx]
    write_block = lines[fetch_idx + 1:body_end]
    hi = " " * header_indent
    bi = " " * body_indent
    new_lines = []
    new_lines.append(hi + "_osm_stale = []\n")
    new_lines.append(header_line)
    new_lines.extend(preamble)
    new_lines.append(bi + "_osm_stale.append((cell_key, cs, cw, cn, ce))\n")
    new_lines.append(
        hi + "# OSM_PARALLEL: fetch stale cells in PARALLEL under the "
        "shared 10s\n"
    )
    new_lines.append(
        hi + "# budget (was sequential await-in-loop: 4 cells x 8s = "
        "32s worst case).\n"
    )
    new_lines.append(
        hi + f"_osm_results = await _osm_gather_cells(_osm_stale, {fetch_fn})\n"
    )
    new_lines.append(
        hi + f"for (cell_key, cs, cw, cn, ce), {result_var} in "
        f"zip(_osm_stale, _osm_results):\n"
    )
    new_lines.extend(write_block)
    new_span = (
        "".join(lines[:hdr_idx]) + "".join(new_lines) + "".join(lines[body_end:])
    )
    return new_span, "ok"


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    changed = []
    warnings = []

    # --- Gather helper: use OSM_FAST's if present, else add it -----------
    if "async def _osm_gather_cells" in src:
        print("ALREADY_APPLIED: gather helper (_osm_gather_cells)")
        helper_ok = True
    else:
        # Anchor the helper before the first nearby handler we can find.
        anchor = None
        for ep in ENDPOINTS:
            m = re.search(
                r"^async def " + re.escape(ep["handler_fn"]) + r"\(",
                src, re.MULTILINE,
            )
            if m:
                anchor = m.start()
                break
        if anchor is None:
            print("WARNING: gather helper missing and could not be added - "
                  "no nearby handler found to anchor it (looked for "
                  "'async def nearby_<name>')")
            warnings.append("helper-anchor")
            helper_ok = False
        else:
            src = src[:anchor] + _GATHER_HELPER.lstrip("\n") + src[anchor:]
            changed.append("gather helper")
            print("OK: gather helper added (_osm_gather_cells, 10s budget)")
            helper_ok = True

    # --- Per endpoint: split the cell loop into two phases ---------------
    for ep in ENDPOINTS:
        name = ep["name"]
        if not helper_ok:
            print(f"SKIPPED: {name} (gather helper missing)")
            continue
        span = _handler_span(src, ep["handler_fn"])
        if span is None:
            print(f"WARNING: {name} handler not found - parallel loop NOT added "
                  f"(looked for 'async def {ep['handler_fn']}')")
            warnings.append(f"{name}-handler")
            continue
        start, end = span
        new_span, status = _restructure(src[start:end], ep)
        if status == "already":
            print(f"ALREADY_APPLIED: {name} parallel loop")
        elif isinstance(status, tuple) and status[0] == "warn":
            print(f"WARNING: {name} {status[1]}")
            warnings.append(f"{name}-loop")
        else:
            src = src[:start] + new_span + src[end:]
            changed.append(f"{name} loop")
            print(f"OK: {name} loop parallelized (gather, 10s total budget)")

    if changed:
        SERVER.write_text(src)
        import py_compile
        py_compile.compile(str(SERVER), doraise=True)
        print("Python syntax OK.")
    else:
        print("No changes (already applied or anchors missing).")
    if warnings:
        print("OSM_PARALLEL_PARTIAL: " + ", ".join(changed) +
              ("" if changed else "nothing changed") +
              " (warnings: " + ", ".join(warnings) + ")")
    else:
        print("OSM_PARALLEL_OK")


if __name__ == "__main__":
    main()
