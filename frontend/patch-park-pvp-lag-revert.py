#!/usr/bin/env python3
"""Revert the park PvP lag fix (patch-park-pvp-lag-fix.py).

The lag fix removed the two "skip if in flight" guards so position posts
and room polls would fire every 100ms. That changed the room flow and the
two phones no longer land in the same PvP game, so this puts the guards
back exactly as they were. The lag fix is parked until a version that
only touches sync (not room setup) is ready.

Restores, per game:
  - pvpPostState: the position-only post skip
      basketball:   if(!patch&&G.pvp.posting) return Promise.resolve(null);
      other games:  if (!patch && G.pvp.posting) return Promise.resolve(null);
  - pvpPollOnce: the poll skip
      basketball:   if(G.pvp.polling) return; // previous poll still in flight
      other games:  if (G.pvp.polling) return;  (prefix of the polling-flag line)

Baseball has no post-skip, so only its poll-skip is restored.
Run from /app. Marker: PARK_PVP_LAG_REVERT_OK
"""
import re
import sys
from pathlib import Path

FILES = [
    ("frontend/components/BasketballHtml.ts", "tight"),
    ("frontend/components/BaseballHtml.ts", "spaced"),
    ("frontend/components/SoccerHtml.ts", "spaced"),
    ("frontend/components/TennisHtml.ts", "spaced"),
    ("frontend/components/OneOnOneHtml.ts", "spaced"),
    ("frontend/components/FootballHtml.ts", "spaced"),
]

POST_SKIP = {
    "tight": "  if(!patch&&G.pvp.posting) return Promise.resolve(null);\n",
    "spaced": "  if (!patch && G.pvp.posting) return Promise.resolve(null);\n",
}
# Insert the post-skip right before the seq increment in pvpPostState.
POST_ANCHOR_RE = re.compile(r"^(  G\.pvp\.seq\s*\+=\s*1;\n)", re.M)

POLL_SKIP = {
    "tight": "  if(G.pvp.polling) return; // previous poll still in flight\n",
    "spaced": "if (G.pvp.polling) return; ",
}
# Basketball: insert the poll-skip as its own line after the pvpIsOn guard
# in pvpPollOnce. Other games: prepend the guard to the polling-flag line.
POLL_TIGHT_ANCHOR_RE = re.compile(
    r"(^function pvpPollOnce\(\)\{\n  if\(!pvpIsOn\(\)\) return;\n)", re.M
)
POLL_SPACED_FLAG_RE = re.compile(
    r"^(  var pvq = G\.pvp; pvq\.polling = true;\n)", re.M
)


def revert_one(path, style):
    src = Path(path).read_text(encoding="utf-8")
    orig = src
    # --- restore post skip (baseball never had one, so skip it) ---
    post_done = False
    if "BaseballHtml" not in path:
        # Only restore if the skip is actually missing and the anchor exists.
        if "G.pvp.posting) return" not in src:
            m = POST_ANCHOR_RE.search(src)
            if m:
                src = src[: m.start()] + POST_SKIP[style] + src[m.start():]
                post_done = True
    # --- restore poll skip ---
    poll_done = False
    if "G.pvp.polling) return" not in src:
        if style == "tight":
            m = POLL_TIGHT_ANCHOR_RE.search(src)
            if m:
                src = src[: m.end()] + POLL_SKIP["tight"] + src[m.end():]
                poll_done = True
        else:
            m = POLL_SPACED_FLAG_RE.search(src)
            if m:
                src = src[: m.start()] + "  " + POLL_SKIP["spaced"] + src[m.start() + 2:]
                poll_done = True
    if src == orig:
        return "ALREADY_APPLIED"
    for needle in ("function pvpPostState", "function pvpPollOnce", "room.states"):
        if needle not in src:
            print(f"PARK_PVP_LAG_REVERT_FAIL {path}: missing {needle} after edit")
            return "FAIL"
    Path(path).write_text(src, encoding="utf-8")
    return f"REVERTED post={post_done} poll={poll_done}"


def main():
    results = []
    for f, style in FILES:
        p = Path(f)
        if not p.exists():
            print(f"PARK_PVP_LAG_REVERT_FAIL {f}: file not found")
            return 1
        r = revert_one(f, style)
        results.append(f"{f}: {r}")
        print(f"{f}: {r}")
    if all("ALREADY_APPLIED" in r for r in results):
        print("PARK_PVP_LAG_REVERT_ALREADY_APPLIED")
        return 0
    if any("FAIL" in r for r in results):
        return 1
    print("PARK_PVP_LAG_REVERT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
