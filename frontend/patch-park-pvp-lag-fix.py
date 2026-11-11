#!/usr/bin/env python3
"""Park PvP lag fix: stop dropping position updates on a slow connection.

Root cause (measured): every request to the Emergent backend takes ~600ms
round-trip. The game posts a position every 100ms and polls every 100ms,
but BOTH skip the new update whenever one is still in flight, so on this
slow connection most updates get dropped and the opponent's position goes
~1s stale -- it freezes, then jumps. That is the lag.

Fix: remove the two "skip if in flight" guards so posts and polls fire
every 100ms regardless. Overlapping requests are safe: every state carries
a per-phone seq, the backend stores one slot per player, and the frontend
only applies a state whose seq is newer than the last one it applied from
that opponent, so a late/out-of-order response can never move the opponent
backwards. The opponent glide (400 u/s vs a 62-96 u/s player) then tracks
a target that refreshes every 100ms instead of every ~600ms.

Applies to all six park games. Baseball has no post-skip (it only posts
on events) so only its poll-skip is removed. Run from /app.
Marker: PARK_PVP_LAG_FIX_OK
"""
import re
import sys
from pathlib import Path

FILES = [
    "frontend/components/BasketballHtml.ts",
    "frontend/components/BaseballHtml.ts",
    "frontend/components/SoccerHtml.ts",
    "frontend/components/TennisHtml.ts",
    "frontend/components/OneOnOneHtml.ts",
    "frontend/components/FootballHtml.ts",
]

# Post-skip line variants (position-only posts dropped while one is in flight).
POST_SKIP_RES = [
    re.compile(r"^  if\(!patch&&G\.pvp\.posting\) return Promise\.resolve\(null\);\n", re.M),
    re.compile(r"^  if \(!patch && G\.pvp\.posting\) return Promise\.resolve\(null\);\n", re.M),
]

# Poll-skip: basketball has it on its own line; the other five share the
# line with the polling-flag assignment, so only the guard prefix is cut.
POLL_SKIP_LINE_RE = re.compile(
    r"^  if\(G\.pvp\.polling\) return; // previous poll still in flight\n", re.M
)
POLL_SKIP_PREFIX_RE = re.compile(r"if \(G\.pvp\.polling\) return; ")


def fix_one(path):
    src = Path(path).read_text(encoding="utf-8")
    orig = src
    # --- post skip: delete the whole line (both spacing variants) ---
    post_removed = 0
    for rx in POST_SKIP_RES:
        src, n = rx.subn("", src)
        post_removed += n
    # --- poll skip: delete basketball's whole line, or the guard prefix ---
    poll_removed = 0
    src, n = POLL_SKIP_LINE_RE.subn("", src)
    poll_removed += n
    src, n = POLL_SKIP_PREFIX_RE.subn("", src)
    poll_removed += n
    if src == orig:
        return "ALREADY_APPLIED"
    # Sanity: the file must still contain the PvP poll/post entry points.
    for needle in ("function pvpPostState", "function pvpPollOnce", "room.states"):
        if needle not in src:
            print(f"PARK_PVP_LAG_FIX_FAIL {path}: missing {needle} after edit")
            return "FAIL"
    Path(path).write_text(src, encoding="utf-8")
    return f"FIXED post={post_removed} poll={poll_removed}"


def main():
    results = []
    for f in FILES:
        p = Path(f)
        if not p.exists():
            print(f"PARK_PVP_LAG_FIX_FAIL {f}: file not found")
            return 1
        r = fix_one(f)
        results.append(f"{f}: {r}")
        print(f"{f}: {r}")
    if all("ALREADY_APPLIED" in r for r in results):
        print("PARK_PVP_LAG_FIX_ALREADY_APPLIED")
        return 0
    if any("FAIL" in r for r in results):
        return 1
    print("PARK_PVP_LAG_FIX_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
