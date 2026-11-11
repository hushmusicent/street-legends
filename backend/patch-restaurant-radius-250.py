#!/usr/bin/env python3
"""
Street Legends — widen the restaurant/nightclub eat-distance limit 100m -> 250m.

CONTEXT (2026-11-05, user said yes to 250m):
- The fresh-GPS fix (RESTAURANT_FRESH_GPS_OK) landed: the eat check now measures
  from the phone's live GPS. Live test 19:20 EST: the toast showed the TRUE
  distance (214m to a Burger King, was 7478m from the frozen stored position).
- But 214m is genuinely over the 100m limit, so it still refuses. 100m is too
  tight for real restaurants (marker sits on the building center; the player is
  in the lot or across the road; GPS drift). New limit: 250m.
- The position-update freeze (server spot still frozen 17h) is a SEPARATE open
  issue. This patch does NOT touch the position pipeline.

WHAT THIS PATCH DOES:
- eat_at_restaurant: `if dist_m > 100:` -> `if dist_m > 250:` and the refusal
  message `get within 100m of ... to eat there!` -> `within 250m`.
- visit_nightclub: the same, `to party there!` message.
- The threshold is a literal in both endpoints (no shared constant/helper).
  Replacements are scoped to each endpoint's function body only, so any other
  100m check (e.g. bank robbery) is NEVER touched.
- Frontend scan: the toast text is built in the backend error detail, so no
  frontend change should be needed; the patch still scans frontend source for a
  literal copy of "get within 100m" and updates it if one exists, so the number
  shown always equals the enforced limit.

Idempotent: rerun prints ALREADY_APPLIED per endpoint and leaves the file
byte-identical. Any endpoint whose anchors miss prints a WARNING and is left
unchanged (marker RESTAURANT_RADIUS_250_PARTIAL).
"""
import os
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")
FRONTEND = Path("frontend")
OLD = 100
NEW = 250

ENDPOINTS = [
    ("eat", "eat_at_restaurant", "to eat there!"),
    ("nightclub", "visit_nightclub", "to party there!"),
]


def func_span(src, fn_name):
    """Return (start, end) of the top-level function body, or None."""
    m = re.search(r"^async def %s\(.*?\):" % re.escape(fn_name), src, re.M)
    if not m:
        m = re.search(r"^def %s\(.*?\):" % re.escape(fn_name), src, re.M)
    if not m:
        return None
    start = m.start()
    # End at the next top-level decorator or def after the function starts.
    tail = re.search(r"^(?:@api_router|async def |def )", src[m.end():], re.M)
    end = m.end() + tail.start() if tail else len(src)
    return (start, end)


def patch_endpoint(src, label, fn_name, msg_tail):
    """Widen one endpoint's limit. Returns (new_src, status, notes)."""
    span = func_span(src, fn_name)
    if span is None:
        return src, "warn", "%s endpoint function not found - NOT changed (looked for 'async def %s')" % (label, fn_name)
    s, e = span
    body = src[s:e]
    notes = []

    already_limit = re.search(r"dist_m\s*>\s*250\b", body) is not None
    already_msg = ("within 250m of" in body) or ("within 250m" in body and msg_tail in body)
    if already_limit and already_msg:
        return src, "already", "%s already 250m" % label

    # 1. The comparison. Literal 100 expected; a named constant is a WARNING.
    if re.search(r"dist_m\s*>\s*100\b", body):
        body2, n = re.subn(r"dist_m\s*>\s*100\b", "dist_m > 250", body, count=1)
        if n == 1:
            body = body2
            notes.append("limit 100 -> 250")
        else:
            return src, "warn", "%s threshold anchor matched %dx - NOT changed" % (label, n)
    elif already_limit:
        notes.append("limit already 250")
    else:
        m = re.search(r"dist_m\s*>\s*([A-Za-z_][A-Za-z0-9_]*)", body)
        if m:
            return src, "warn", "%s threshold uses a named constant '%s' - NOT changed (looked for 'dist_m > 100' in %s)" % (label, m.group(1), fn_name)
        return src, "warn", "%s threshold anchor not found - NOT changed (looked for 'dist_m > 100' in %s)" % (label, fn_name)

    # 2. The refusal message, so the number shown equals the enforced limit.
    if "within 100m of" in body:
        body = body.replace("within 100m of", "within 250m of", 1)
        notes.append("message 100m -> 250m")
    elif "within 250m of" in body:
        notes.append("message already 250m")
    else:
        return src, "warn", "%s refusal message not found - limit changed but message NOT updated (looked for 'within 100m of' in %s)" % (label, fn_name)

    return src[:s] + body + src[e:], "ok", "%s: %s" % (label, "; ".join(notes))


def scan_frontend():
    """Update any literal copy of the limit text in frontend source, if present."""
    if not FRONTEND.exists():
        return "skip", "frontend/ not found - skipped (toast text lives in the backend detail)"
    hits = []
    changed = []
    for root, dirs, files in os.walk(FRONTEND):
        dirs[:] = [d for d in dirs if d not in ("node_modules", ".metro-cache", ".git")]
        for f in files:
            if not (f.endswith(".ts") or f.endswith(".tsx") or f.endswith(".js")):
                continue
            p = Path(root) / f
            try:
                text = p.read_text()
            except Exception:
                continue
            if "within 100m" in text:
                hits.append(str(p))
                new = text.replace("within 100m", "within 250m")
                p.write_text(new)
                changed.append(str(p))
    if changed:
        return "ok", "frontend copy updated in: %s" % ", ".join(changed)
    if hits:
        return "warn", "frontend copy found but not updated: %s" % ", ".join(hits)
    return "ok", "no frontend copy of 'within 100m' found (toast comes from the backend detail)"


def main():
    if not SERVER.exists():
        print("ERROR: %s not found. Run from repo root (/app)." % SERVER)
        sys.exit(1)
    src = SERVER.read_text()
    orig = src
    warnings = []
    statuses = []

    for label, fn_name, msg_tail in ENDPOINTS:
        src, status, note = patch_endpoint(src, label, fn_name, msg_tail)
        statuses.append((label, status))
        if status == "ok":
            print("OK: %s" % note)
        elif status == "already":
            print("ALREADY_APPLIED: %s" % note)
        else:
            print("WARNING: %s" % note)
            warnings.append(note)

    f_status, f_note = scan_frontend()
    if f_status == "ok":
        print("OK: %s" % f_note)
    elif f_status == "skip":
        print("SKIP: %s" % f_note)
    else:
        print("WARNING: %s" % f_note)
        warnings.append(f_note)

    if src != orig:
        SERVER.write_text(src)

    import py_compile
    py_compile.compile(str(SERVER), doraise=True)
    print("Python syntax OK.")
    if warnings:
        print("RESTAURANT_RADIUS_250_PARTIAL (warnings: %s)" % "; ".join(warnings))
    else:
        print("RESTAURANT_RADIUS_250_OK")


if __name__ == "__main__":
    main()
