#!/usr/bin/env python3
"""Street Legends shootout global-cooldown guard (backend, Publish).

Background: v1 added minigame_global_cooldown_until (play once -> all
mini-games lock 15 min) and v2 moved its write outside the standalone
condition for all five games. Live compact output proves the check helpers
exist, but whether live complete_shootout SETS the global cooldown was not
proven (output capped). This patch guarantees the set, exactly once per
completion, for map AND standalone completions:

  - For each of the five mini-game complete functions, if its body already
    contains a minigame_global_cooldown_until write, it is left
    byte-unchanged and reported ALREADY_PRESENT (the expected live case
    when v2 already ran).
  - Otherwise the global write is inserted right after the player lookup
    block (after the player-not-found raise), which sits at function top
    level, OUTSIDE any standalone condition, and AFTER the
    already-completed check - so a re-completed game never double-writes.
  - The write uses the existing _minigame_global_cooldown_until() helper
    when it is defined in the file, else the inline
    (datetime.utcnow() + timedelta(seconds=900)).isoformat() form
    (timedelta is imported by server.py).

No /api prefix changes; the inserted update_one is awaited, like every
other Motor call in these functions. No reward formula, cooldown length,
or per-marker cooldown is changed.

Idempotent: a second run prints SHOOTOUT_GLOBAL_COOLDOWN_ALREADY_APPLIED
and changes nothing. A function whose anchor is missed is reported with a
WARNING and left unchanged; if no function can be processed, no marker is
printed and the exit code is 1.
"""
import re
import sys
from pathlib import Path

MARKER = "# SHOOTOUT_GLOBAL_COOLDOWN"
OK = "SHOOTOUT_GLOBAL_COOLDOWN_OK"
ALREADY = "SHOOTOUT_GLOBAL_COOLDOWN_ALREADY_APPLIED"

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
SERVER = ROOT / "backend" / "server.py"

COMPLETE_FNS = [
    "complete_castle_game",
    "complete_car_chase",
    "complete_runaway",
    "complete_package_grab",
    "complete_shootout",
]

# player = await db.players.find_one({"id": game["player_id"]})
# if not player:
#     raise HTTPException(status_code=404, detail="Player not found")
PLAYER_BLOCK = re.compile(
    r"player = await db\.players\.find_one\(\{\"id\": game\[\"player_id\"\]\}\)\n"
    r"(\s*)if not player:\n"
    r"\s*raise HTTPException\(status_code=404, detail=\"Player not found\"\)"
)


def function_span(src, name):
    """Return (start, end) offsets of one top-level async def body."""
    m = re.search(rf"^async def {name}\(", src, re.M)
    if not m:
        return None
    start = m.start()
    rest = src[m.end():]
    nxt = re.search(r"^(@api_router|async def |def |class )", rest, re.M)
    end = m.end() + (nxt.start() if nxt else len(rest))
    return (start, end)


def main():
    if not SERVER.exists():
        print(f"WARNING: server.py not found at {SERVER} - nothing changed")
        return 1
    src = SERVER.read_text(errors="ignore")
    if MARKER in src:
        print(ALREADY)
        return 0
    if "_minigame_global_cooldown_until()" in src and "def _minigame_global_cooldown_until" in src:
        expr = "_minigame_global_cooldown_until()"
    else:
        print("WARNING: _minigame_global_cooldown_until helper not defined in server.py - using inline 900s form")
        expr = "(datetime.utcnow() + timedelta(seconds=900)).isoformat()"
    changed = []
    already = []
    skipped = []
    for name in COMPLETE_FNS:
        span = function_span(src, name)
        if span is None:
            print(f"WARNING: {name} function anchor not found - owner guard SKIPPED")
            skipped.append(name)
            continue
        body = src[span[0]:span[1]]
        if "minigame_global_cooldown_until" in body:
            print(f"{name}: ALREADY_PRESENT (global write exists - byte-unchanged)")
            already.append(name)
            continue
        m = PLAYER_BLOCK.search(body)
        if not m:
            print(f"WARNING: {name} player lookup anchor not found - global write SKIPPED")
            skipped.append(name)
            continue
        insert_at = span[0] + m.end()
        block = (
            f"\n    {MARKER}: ANY completion (map or practice) locks all mini-games for 15 min\n"
            "    await db.players.update_one(\n"
            "        {\"id\": game[\"player_id\"]},\n"
            f"        {{\"$set\": {{\"minigame_global_cooldown_until\": {expr}}}}}\n"
            "    )"
        )
        src = src[:insert_at] + block + src[insert_at:]
        print(f"{name}: global cooldown write ADDED")
        changed.append(name)
    if not changed and not already:
        print("SHOOTOUT_GLOBAL_COOLDOWN_NOT_APPLIED: see WARNING lines above; file NOT written")
        return 1
    if changed:
        SERVER.write_text(src)
    print(f"changed={changed} already_present={already} skipped={skipped}")
    print(OK)
    return 0


if __name__ == "__main__":
    sys.exit(main())
