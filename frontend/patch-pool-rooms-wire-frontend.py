#!/usr/bin/env python3
"""Street Legends frontend: pool PvP rooms — stop masking real errors.

The phone's pool rooms screen shows "Pool rooms are not live yet" when
a Create/Join attempt returns 404 OR when the fetch throws. Once the
backend wiring patch has wired create/join, a fetch throw is a network
problem, not a missing backend — but the old code reports it as
"not live yet", hiding the real error. This patch changes ONLY that:

  * Create/Join fetch throws now show:
    "Could not reach the server. Check your connection."
    instead of the "not live yet" text.
  * A genuine 404 still shows "not live yet" (that is the case where
    the backend patch did not wire the route).
  * Any other non-OK response still shows the server's detail message
    (that behaviour already existed and is left untouched).

URLs are NOT changed: the frontend call shape
(POST /api/pool/rooms/create {player_id, player_name} and
 POST /api/pool/rooms/join {code, player_id, player_name})
is the spec the backend patch adapts to. No layout, button, chat,
polling, or game code is touched.

Run from /app: python3 frontend/patch-pool-rooms-wire-frontend.py
Idempotent: re-running prints POOL_ROOMS_WIRE_FRONTEND_ALREADY_APPLIED.
Frontend only: reload Expo Go fresh after running.
"""
import re
import sys

PATH = "frontend/app/(tabs)/index.tsx"
MARKER_OK = "POOL_ROOMS_WIRE_FRONTEND_OK"
MARKER_ALREADY = "POOL_ROOMS_WIRE_FRONTEND_ALREADY_APPLIED"
ANCHOR_WARNING = ("WARNING: pool rooms modal anchor not matched - "
                  "frontend NOT changed")
CONN_MSG = "Could not reach the server. Check your connection."
CREATE_URL = "/api/pool/rooms/create"
JOIN_URL = "/api/pool/rooms/join"
CATCH_RE = re.compile(
    r"(catch\s*\(\s*e?\s*\)\s*\{\s*)showNotLive\(\);\s*(\})")


def _balance(text):
    return (text.count("{") - text.count("}"),
            text.count("(") - text.count(")"),
            text.count("[") - text.count("]"))


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            orig = f.read()
    except FileNotFoundError:
        print(ANCHOR_WARNING)
        return 0
    src = orig
    modal_idx = src.find("const PoolPvpModal")
    if modal_idx == -1:
        print(ANCHOR_WARNING)
        return 0
    region = src[modal_idx:]
    create_idx = region.find(CREATE_URL)
    join_idx = region.find(JOIN_URL)
    if create_idx == -1 or join_idx == -1:
        print(ANCHOR_WARNING)
        return 0

    # For each of create/join, find its fetch-throw catch within the
    # following lines and swap showNotLive() for the connection message.
    # The 404 branch ("if (res.status === 404) { showNotLive(); ... }")
    # is deliberately NOT touched: a genuine 404 on an unwired route
    # is exactly what "not live yet" means.
    lines = src.split("\n")
    # Map region offsets back to absolute line numbers.
    region_start_line = src[:modal_idx].count("\n")
    region_lines = region.split("\n")
    changed = 0
    already = 0
    for url in (CREATE_URL, JOIN_URL):
        # Absolute line of the fetch call inside the modal region.
        fetch_line = None
        for i, ln in enumerate(region_lines):
            if url in ln:
                fetch_line = region_start_line + i
                break
        if fetch_line is None:
            print(ANCHOR_WARNING)
            return 0
        found = False
        for j in range(fetch_line, min(len(lines), fetch_line + 30)):
            if CONN_MSG in lines[j]:
                # A previous run already fixed this catch site.
                already += 1
                found = True
                break
            m = CATCH_RE.search(lines[j])
            if m:
                lines[j] = CATCH_RE.sub(
                    lambda mm: mm.group(1) + "setInfo('" + CONN_MSG + "'); " + mm.group(2),
                    lines[j], count=1)
                changed += 1
                found = True
                break
        if not found:
            print(ANCHOR_WARNING)
            return 0
    if changed == 0 and already == 2:
        print(MARKER_ALREADY)
        return 0
    if changed == 0:
        print(ANCHOR_WARNING)
        return 0
    new_src = "\n".join(lines)
    # Safety: the replacement must not change brace/paren/bracket balance.
    if _balance(orig) != _balance(new_src):
        print("WARNING: brace balance changed - index.tsx NOT written")
        return 1
    # URLs must be byte-identical in count before/after.
    if (new_src.count(CREATE_URL) != orig.count(CREATE_URL) or
            new_src.count(JOIN_URL) != orig.count(JOIN_URL)):
        print("WARNING: pool room URLs changed - index.tsx NOT written")
        return 1
    with open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("POOL_ROOMS_WIRE_FRONTEND: fetch-throw message fixed in %d catch site(s)" % changed)
    print(MARKER_OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
