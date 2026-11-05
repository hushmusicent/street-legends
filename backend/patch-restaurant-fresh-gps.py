"""Street Legends backend: restaurant/nightclub distance uses the phone's LIVE GPS.

Run from repo root: python3 backend/patch-restaurant-fresh-gps.py
Idempotent - safe to re-run.

WHY (diag result 2026-11-05, RESTAURANT_DISTANCE_DIAG_OK verdict=(a)):
  The eat check reads the STORED player position (player.get("position")),
  NOT live phone GPS. The stored position was frozen 17 hours old
  (lat 41.6368324, lng -83.4785757, last_active 2026-11-05T06:31:04Z) while
  the phone moved all over Toledo, so a Marco's Pizza right by the player
  measured as 7478m away ("Not Hungry Yet"). The distance formula is
  CORRECT (haversine, radians, R=6371000) and the restaurant data is
  CORRECT (no lat/lng swap, marker id == eat lookup key) -- only the
  position source is stale. The nightclub visit endpoint has the same
  100m check against the same stored position (same bug).

FIX (three pieces):
  1. eat_at_restaurant + visit_nightclub: accept the caller's LIVE
     position as optional query params (?latitude=&longitude=). When
     supplied and in range, the in-memory player dict's position is
     overridden for THIS request only, so the existing 100m check (which
     reads player.get("position")) measures from the live fix. When not
     supplied, behavior is unchanged (stored position). Cooldown, heal
     math (25% max HP / 25% max Energy), and response shapes are untouched.
     The stored position is NOT overwritten by this override.
  2. update_player_position: stop 404ing on modified_count == 0 when the
     player EXISTS (the find_one above already proves it). An unchanged
     position is a successful no-op, not "Player not found" -- a stationary
     player was getting an error on EVERY update. Only a genuinely missing
     player 404s (the find_one guard; added if the live shape lacks it).
     Vehicle-travel remainder math and the durability hook are untouched.
  3. update_player_position, vehicle remainder variable names: the diag
     screenshots suggest the remainder variable may be assigned under one
     name and used under another (vehicle_travel_remainder_km vs
     _vehicle_remainder_km). A mismatch would NameError -> 500 on EVERY
     position update, which alone would freeze the stored position. This
     patch CHECKS the names on the live file: if they mismatch, the uses
     are renamed to the assigned name; if they match, nothing changes.
     (The name pair could not be verified from the diag screenshots --
     this piece resolves it against the live file.)

TOUCHES NOTHING ELSE: no cooldown/heal math, no spawn code, no other
endpoint, no frontend file. The 100m threshold is unchanged.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "RESTAURANT_FRESH_GPS"

# Next top-level block (end of a function span).
_NEXT_TOP_RE = re.compile(r"^(?:@api_router\.|async def |def |class |# =+)",
                          re.MULTILINE)


def _fn_span(src, fn_name):
    """(start, end) char offsets of a top-level async def, or None."""
    m = re.search(r"^async def " + re.escape(fn_name) + r"\(", src,
                  re.MULTILINE)
    if not m:
        return None
    start = m.start()
    m2 = _NEXT_TOP_RE.search(src, m.end())
    end = m2.start() if m2 else len(src)
    return (start, end)


def _blank_strings(text):
    """Blank out single/double-quoted string literals (same length)."""
    def _sub(m):
        return " " * len(m.group(0))
    return re.sub(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\'', _sub, text)


def _add_live_gps(src, fn_name):
    """Add optional ?latitude=&longitude= params + in-memory position
    override to one endpoint (eat or nightclub).

    Returns (new_src, status) where status is 'ok', 'already', or
    ('warn', reason)."""
    span = _fn_span(src, fn_name)
    if span is None:
        return src, ("warn", f"{fn_name} not found - live GPS NOT added "
                             f"(looked for 'async def {fn_name}(')")
    start, end = span
    text = src[start:end]
    def_line = text.splitlines()[0] if text.splitlines() else ""
    sig_done = "latitude" in def_line and "longitude" in def_line
    override_done = ('player["position"] = {"latitude": latitude, '
                     '"longitude": longitude}') in text
    if sig_done and override_done:
        return src, "already"

    # --- signature: add the two optional query params -------------------
    if not sig_done:
        sig = re.search(
            r"^(async def " + re.escape(fn_name) + r"\()\s*"
            r"restaurant_id:\s*str,\s*player_id:\s*str\s*(\))\s*:",
            text, re.MULTILINE)
        night_sig = re.search(
            r"^(async def " + re.escape(fn_name) + r"\()\s*"
            r"nightclub_id:\s*str,\s*player_id:\s*str\s*(\))\s*:",
            text, re.MULTILINE)
        m = sig or night_sig
        if not m:
            return src, ("warn", f"{fn_name} signature not recognized - "
                                 f"live GPS NOT added (looked for "
                                 f"'async def {fn_name}(<id>: str, "
                                 f"player_id: str):')")
        text = (text[:m.start()] + m.group(1) +
                ("restaurant_id: str, player_id: str"
                 if sig else "nightclub_id: str, player_id: str") +
                ", latitude: float = None, longitude: float = None" +
                m.group(2) + ":" + text[m.end():])

    # --- override: right after the player find_one / 404 guard ---------
    if override_done:
        return src[:start] + text + src[end:], "ok"
    lookup = re.search(
        r"^([ ]*)player = await db\.players\.find_one\(\{\"id\": player_id\}\)\n"
        r"[ ]*if not player:\n"
        r"[ ]*raise HTTPException\(status_code=404, detail=\"[^\"]*\"\)\n",
        text, re.MULTILINE)
    if lookup is None:
        return src, ("warn", f"{fn_name} player lookup block not found - "
                             f"live GPS NOT added (looked for "
                             f"'player = await db.players.find_one('"
                             f'{{"id": player_id}})'' + 404 guard)')
    indent = lookup.group(1)
    override = (
        f"\n{indent}# {MARKER}: prefer the phone's LIVE GPS (sent by the app\n"
        f"{indent}# as ?latitude=&longitude=) for the 100m check below. The\n"
        f"{indent}# stored position can be hours stale (the \"7478m away\"\n"
        f"{indent}# bug: stored pos was 17h old). This only overrides the\n"
        f"{indent}# in-memory player dict for THIS request; the stored\n"
        f"{indent}# position is NOT overwritten here.\n"
        f"{indent}if (latitude is not None and longitude is not None\n"
        f"{indent}        and -90 <= latitude <= 90\n"
        f"{indent}        and -180 <= longitude <= 180):\n"
        f"{indent}    player[\"position\"] = {{\"latitude\": latitude, "
        f"\"longitude\": longitude}}\n"
    )
    text = text[:lookup.end()] + override + text[lookup.end():]
    return src[:start] + text + src[end:], "ok"


def _fix_update_position(src):
    """Fix update_player_position: (a) no 404 on unchanged position,
    (b) vehicle remainder variable-name consistency.

    Returns (new_src, [status, ...]) with one status per sub-piece."""
    span = _fn_span(src, "update_player_position")
    if span is None:
        return src, [("warn", "update_player_position not found - position "
                              "update NOT fixed (looked for "
                              "'async def update_player_position(')")]
    start, end = span
    text = src[start:end]
    statuses = []

    # --- (b) remainder variable-name consistency ------------------------
    # Assigned name: `<name> = float(player.get("vehicle_travel_remainder_km"...`
    assign = re.search(
        r"^([ ]*)(\w+)\s*=\s*float\(player\.get\(\"vehicle_travel_remainder_km\"",
        text, re.MULTILINE)
    if assign is None:
        if "remainder" not in text and "vehicle" not in text:
            # No vehicle-travel math in this shape at all (snapshot) --
            # nothing to check, not a failure.
            print("SKIP: update_player_position has no vehicle remainder "
                  "math - variable-name check not applicable")
        else:
            statuses.append(("warn", "update_player_position: remainder "
                                     "variable assignment not found - "
                                     "variable-name check skipped (looked "
                                     "for '= float(player.get("
                                     "\"vehicle_travel_remainder_km\"')"))
    else:
        assigned = assign.group(2)
        blanked = _blank_strings(text)
        bare = set(re.findall(
            r"(?<![\w.])(_?vehicle\w*remainder\w*|vehicle_travel_remainder_km)"
            r"(?![\w])", blanked))
        bare.discard(assigned)
        if bare:
            # Rename every mismatched bare use to the assigned name,
            # leaving string literals untouched.
            for bad in sorted(bare):
                pat = re.compile(
                    r'("(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\')|\b' +
                    re.escape(bad) + r'\b')

                def _fix(m, _bad=bad, _good=assigned):
                    return m.group(1) if m.group(1) is not None else _good

                text = pat.sub(_fix, text)
            statuses.append(("ok", f"update_player_position: remainder "
                                   f"variable mismatch fixed -- uses of "
                                   f"{sorted(bare)} renamed to the assigned "
                                   f"name '{assigned}' (a mismatch here "
                                   f"NameErrors -> 500 on EVERY position "
                                   f"update)"))
        else:
            statuses.append(("already", "update_player_position: remainder "
                                        "variable names consistent "
                                        f"('{assigned}')"))

    # --- (a) modified_count == 0 must not 404 for an existing player ----
    mod = re.search(
        r"^([ ]*)if result\.modified_count == 0:\n"
        r"[ ]*raise HTTPException\(status_code=404, "
        r"detail=\"Player not found\"\)\n",
        text, re.MULTILINE)
    if mod is None:
        if MARKER in text and "successful no-op" in text:
            statuses.append(("already", "update_player_position: "
                                        "modified_count 404 already removed"))
        else:
            statuses.append(("warn", "update_player_position: modified_count "
                                     "404 block not found - 404 quirk NOT "
                                     "fixed (looked for 'if "
                                     "result.modified_count == 0: raise "
                                     "HTTPException(status_code=404, "
                                     "detail=\"Player not found\")')"))
        return src[:start] + text + src[end:], statuses
    has_guard = 'db.players.find_one({"id": player_id})' in text
    if not has_guard:
        # Snapshot shape: no find_one guard. Add one before the
        # update_one so a genuinely missing player still 404s.
        upd = re.search(
            r"^([ ]*)result = await db\.players\.update_one\(",
            text, re.MULTILINE)
        if upd is None:
            statuses.append(("warn", "update_player_position: no find_one "
                                     "guard and update_one call not found - "
                                     "404 quirk NOT fixed (removing the "
                                     "raise without a guard would let a "
                                     "missing player return success)"))
            return src[:start] + text + src[end:], statuses
        ind = upd.group(1)
        guard = (
            f"{ind}# {MARKER}: existence guard (the old code 404d\n"
            f"{ind}# on modified_count == 0, which also fires when\n"
            f"{ind}# the position is unchanged).\n"
            f"{ind}_upd_player = await db.players.find_one("
            f"{{\"id\": player_id}})\n"
            f"{ind}if not _upd_player:\n"
            f"{ind}    raise HTTPException(status_code=404, "
            f"detail=\"Player not found\")\n"
        )
        text = text[:upd.start()] + guard + text[upd.start():]
        # Re-find the modified_count block after the insertion.
        mod = re.search(
            r"^([ ]*)if result\.modified_count == 0:\n"
            r"[ ]*raise HTTPException\(status_code=404, "
            r"detail=\"Player not found\"\)\n",
            text, re.MULTILINE)
        statuses.append(("ok", "update_player_position: existence "
                               "guard added (find_one before "
                               "update_one)"))
    ind = mod.group(1)
    replacement = (
        f"{ind}# {MARKER}: modified_count == 0 also fires when the\n"
        f"{ind}# position is UNCHANGED (a stationary player). The player\n"
        f"{ind}# EXISTS (find_one above), so this is a successful no-op,\n"
        f"{ind}# not \"Player not found\".\n"
    )
    text = text[:mod.start()] + replacement + text[mod.end():]
    statuses.append(("ok", "update_player_position: modified_count 404 "
                           "removed (unchanged position is now a 200, "
                           "missing player still 404s on find_one)"))

    return src[:start] + text + src[end:], statuses


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    changed = []
    warnings = []

    for fn_name in ("eat_at_restaurant", "visit_nightclub"):
        src, status = _add_live_gps(src, fn_name)
        if status == "already":
            print(f"ALREADY_APPLIED: {fn_name} live GPS")
        elif isinstance(status, tuple) and status[0] == "warn":
            print(f"WARNING: {status[1]}")
            warnings.append(f"{fn_name}-gps")
        else:
            changed.append(f"{fn_name} live GPS")
            print(f"OK: {fn_name} accepts live GPS (?latitude=&longitude=) "
                  f"for the 100m check, falls back to stored position")

    src, statuses = _fix_update_position(src)
    for status in statuses:
        if status[0] == "already":
            print(f"ALREADY_APPLIED: {status[1]}")
        elif status[0] == "warn":
            print(f"WARNING: {status[1]}")
            warnings.append("update-position")
        else:
            changed.append(status[1][:60])
            print(f"OK: {status[1]}")

    if changed:
        SERVER.write_text(src)
        import py_compile
        py_compile.compile(str(SERVER), doraise=True)
        print("Python syntax OK.")
    else:
        print("No changes (already applied or anchors missing).")
    if warnings:
        print("RESTAURANT_FRESH_GPS_PARTIAL: " + ", ".join(changed) +
              ("" if changed else "nothing changed") +
              " (warnings: " + ", ".join(warnings) + ")")
    else:
        print("RESTAURANT_FRESH_GPS_OK")


if __name__ == "__main__":
    main()
