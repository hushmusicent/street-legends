"""Street Legends backend: bank robbery uses the phone's LIVE GPS + 250m.

Run from repo root: python3 backend/patch-bank-robbery-fresh-gps.py
Idempotent - safe to re-run.

WHY (2026-11-05, user screenshot 19:45 EST):
  The robbery check reads the STORED player position (frozen 17h+ at
  41.6368324,-83.4785757) and the 100m limit. Tapping Huntington Bank right
  by the player said "You're 18769m away - get within 100m of Huntington
  Bank to rob it!" -- 18,769m is the frozen stored position to the bank
  near his phone. Restaurants + nightclub already got this fix (live GPS +
  250m, RESTAURANT_FRESH_GPS_OK + RESTAURANT_RADIUS_250_OK); banks were
  deliberately left out of both. This patch gives banks the same treatment.

FIX (two pieces, rob_bank only):
  1. rob_bank accepts optional ?latitude=&longitude=. When supplied and in
     range, the in-memory player dict's position is overridden for THIS
     request only, so the existing proximity check (which reads
     player.get("position")) measures from the live fix. No params = old
     behavior (stored position). The stored position is NOT overwritten.
  2. The robbery limit 100m -> 250m (comparison + refusal message),
     scoped to the rob_bank function body only. No other 100m check
     touched.
  UNTOUCHED: the luck/health chance formula (v2 squared falloff +
  robbery_mult level decay), the flat $450-$1000 fine, the 60-min
  cooldown per bank per player, the loot range, the response shape,
  the position pipeline (the stored-position freeze is a SEPARATE open
  issue), and every other endpoint.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")
MARKER = "BANK_ROBBERY_FRESH_GPS"

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


def _add_live_gps(src):
    """Add optional ?latitude=&longitude= params + in-memory position
    override to rob_bank.

    Returns (new_src, status) where status is 'ok', 'already', or
    ('warn', reason)."""
    span = _fn_span(src, "rob_bank")
    if span is None:
        return src, ("warn", "rob_bank not found - live GPS NOT added "
                             "(looked for 'async def rob_bank(')")
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
            r"^(async def rob_bank\()\s*"
            r"bank_id:\s*str,\s*player_id:\s*str\s*(\))\s*:",
            text, re.MULTILINE)
        if not sig:
            return src, ("warn", "rob_bank signature not recognized - "
                                 "live GPS NOT added (looked for "
                                 "'async def rob_bank(bank_id: str, "
                                 "player_id: str):')")
        text = (text[:sig.start()] + sig.group(1) +
                "bank_id: str, player_id: str"
                ", latitude: float = None, longitude: float = None" +
                sig.group(2) + ":" + text[sig.end():])

    # --- override: right after the player find_one / 404 guard ---------
    if override_done:
        return src[:start] + text + src[end:], "ok"
    lookup = re.search(
        r"^([ ]*)player = await db\.players\.find_one\(\{\"id\": player_id\}\)\n"
        r"[ ]*if not player:\n"
        r"[ ]*raise HTTPException\(status_code=404, detail=\"[^\"]*\"\)\n",
        text, re.MULTILINE)
    if lookup is None:
        return src, ("warn", "rob_bank player lookup block not found - "
                             "live GPS NOT added (looked for "
                             "'player = await db.players.find_one('"
                             '{"id": player_id}})'' + 404 guard)')
    indent = lookup.group(1)
    override = (
        f"\n{indent}# {MARKER}: prefer the phone's LIVE GPS (sent by the app\n"
        f"{indent}# as ?latitude=&longitude=) for the proximity check below.\n"
        f"{indent}# The stored position can be hours stale (the \"18769m\n"
        f"{indent}# away\" bug: stored pos was 17h old). This only overrides\n"
        f"{indent}# the in-memory player dict for THIS request; the stored\n"
        f"{indent}# position is NOT overwritten here.\n"
        f"{indent}if (latitude is not None and longitude is not None\n"
        f"{indent}        and -90 <= latitude <= 90\n"
        f"{indent}        and -180 <= longitude <= 180):\n"
        f"{indent}    player[\"position\"] = {{\"latitude\": latitude, "
        f"\"longitude\": longitude}}\n"
    )
    text = text[:lookup.end()] + override + text[lookup.end():]
    return src[:start] + text + src[end:], "ok"


def _widen_radius(src):
    """Widen rob_bank's limit 100m -> 250m, scoped to its body only.

    Returns (new_src, status) where status is 'ok', 'already', or
    ('warn', reason)."""
    span = _fn_span(src, "rob_bank")
    if span is None:
        return src, ("warn", "rob_bank not found - radius NOT changed "
                             "(looked for 'async def rob_bank(')")
    start, end = span
    text = src[start:end]

    already_limit = re.search(r"dist_m\s*>\s*250\b", text) is not None
    already_msg = "within 250m of" in text
    if already_limit and already_msg:
        return src, "already"

    # The proximity block must exist (live shape, added by real-banks).
    if "dist_m" not in text:
        return src, ("warn", "rob_bank proximity check not found - radius "
                             "NOT changed (looked for 'dist_m > 100' in "
                             "rob_bank; the snapshot shape has no proximity "
                             "check at all)")
    if re.search(r"dist_m\s*>\s*100\b", text):
        text = re.sub(r"dist_m\s*>\s*100\b", "dist_m > 250", text, count=1)
    elif already_limit:
        pass
    else:
        m = re.search(r"dist_m\s*>\s*([A-Za-z_][A-Za-z0-9_]*)", text)
        if m:
            return src, ("warn", "rob_bank threshold uses a named constant "
                                 f"'{m.group(1)}' - NOT changed (looked for "
                                 "'dist_m > 100' in rob_bank)")
        return src, ("warn", "rob_bank threshold anchor not found - NOT "
                             "changed (looked for 'dist_m > 100' in "
                             "rob_bank)")

    if "within 100m of" in text:
        text = text.replace("within 100m of", "within 250m of", 1)
    elif "within 250m of" in text:
        pass
    else:
        return src, ("warn", "rob_bank refusal message not found - limit "
                             "changed but message NOT updated (looked for "
                             "'within 100m of' in rob_bank)")

    return src[:start] + text + src[end:], "ok"


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    changed = []
    warnings = []

    src, status = _add_live_gps(src)
    if status == "already":
        print("ALREADY_APPLIED: rob_bank live GPS")
    elif isinstance(status, tuple) and status[0] == "warn":
        print(f"WARNING: {status[1]}")
        warnings.append("rob-gps")
    else:
        changed.append("rob_bank live GPS")
        print("OK: rob_bank accepts live GPS (?latitude=&longitude=) "
              "for the proximity check, falls back to stored position")

    src, status = _widen_radius(src)
    if status == "already":
        print("ALREADY_APPLIED: rob_bank radius 250m")
    elif isinstance(status, tuple) and status[0] == "warn":
        print(f"WARNING: {status[1]}")
        warnings.append("rob-radius")
    else:
        changed.append("rob_bank radius 250m")
        print("OK: rob_bank limit 100m -> 250m (comparison + refusal "
              "message, rob_bank body only)")

    if changed:
        SERVER.write_text(src)
        import py_compile
        py_compile.compile(str(SERVER), doraise=True)
        print("Python syntax OK.")
    else:
        print("No changes (already applied or anchors missing).")
    if warnings:
        print("BANK_ROBBERY_FRESH_GPS_PARTIAL: " + ", ".join(changed) +
              ("" if changed else "nothing changed") +
              " (warnings: " + ", ".join(warnings) + ")")
    else:
        print("BANK_ROBBERY_FRESH_GPS_OK")


if __name__ == "__main__":
    main()
