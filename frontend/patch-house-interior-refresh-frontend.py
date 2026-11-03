#!/usr/bin/env python3
"""Street Legends frontend: house interior refreshes on leave + re-enter.

USER REQUIREMENT (2026-11-03): "It should refresh when I leave and
enter the house. I shouldn't have to refresh the app."

PROVEN BUG (live server check 2026-11-03 13:00 EST): the server house
was CORRECT (mansion, poker sold, radio bought) but re-entering the
house in the app showed the OLD list (radio gone, poker back).

ROOT CAUSE (from patch-houses-map.py, which quotes live index.tsx):
the house popup ENTER HOUSE button does
    onPress={() => setInteriorHouse(selectedMarker.data)}
i.e. it copies the MAP's cached nearby-house object into the interior.
That cached object is never refreshed after interior buy/sell taps, so
re-entering restores stale items. LEAVE already clears interiorHouse
(LEAVE HOUSE button + modal onRequestClose both setInteriorHouse(null)),
so the fix is the ENTER side: open instantly on the cached object, then
replace it with FRESH server data (GET /houses/player/{playerId}, the
source of truth) as soon as it arrives. Fetch failure keeps the cached
object (never worse than today).

RADIO SAFETY: the radio patch (frontend/patch-house-radio-frontend.py)
stops audio via a useEffect on interiorHouse becoming falsy + a
RadioStopOnUnmount render before the LEAVE HOUSE button. This patch
never touches radio code: the enter handler only ever sets
interiorHouse truthy -> truthy (no falsy transition, so the radio
effect cannot fire on enter), and the leave section only ADDS a null
clear if one is missing (it is already present per the quoted code, so
it normally changes nothing there). Either patch run order works.

Run from /app: python3 frontend/patch-house-interior-refresh-frontend.py
Frontend only, Expo Go reload, no backend, no Deploy.
Idempotent (scoped): if // HOUSE_INTERIOR_REFRESH is already present,
the enter change is skipped; leave checks never duplicate a clear.
Any missed anchor prints a WARNING naming it and the patch continues;
the marker is always the last line (except file-not-found, ERROR + exit 1).
A missed ENTER refetch with a working LEAVE clear is partial progress
(re-enter shows loading/empty, not stale) — report it, do not re-run blind.
"""
import re
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
MARKER = "HOUSE_INTERIOR_REFRESH_FRONTEND_OK"
REFRESH_MARKER = "// HOUSE_INTERIOR_REFRESH"


def _indent_of(line):
    m = re.match(r"[ \t]*", line)
    return m.group(0) if m else ""


def _enter_block(indent, fetch_expr):
    """Multi-line async onPress replacing the cached-only enter line."""
    lines = [
        indent + "onPress={async () => {",
        indent + "  " + REFRESH_MARKER
        + ": open instantly on the cached marker, then replace with fresh server data",
        indent + "  setInteriorHouse(selectedMarker.data);",
        indent + "  if (!playerId) return;",
        indent + "  try {",
        indent + "    const fresh: any = await " + fetch_expr + ";",
        indent + "    const house = fresh?.house ?? fresh?.data?.house ?? fresh?.data ?? fresh;",
        indent + "    if (house && house.id) {",
        indent + "      setInteriorHouse(house);",
        indent + "      try { setSelectedMarker((prev: any) => (prev ? { ...prev, data: house } : prev)); } catch (_) {}",
        indent + "    }",
        indent + "  } catch (_) {}",
        indent + "}}",
    ]
    return "\n".join(lines)


def _ensure_getplayerhouse_import(lines, src):
    """Return (new_src, ok, note). Only called when getPlayerHouse is not
    already referenced; adds it to an existing services/api import."""
    text = src
    # Single-line import: ... } from '../../services/api' (or "../..")
    for idx, ln in enumerate(lines):
        if "services/api" in ln and "import" in ln and "{" in ln and "}" in ln:
            if "getPlayerHouse" in ln:
                return text, True, "SKIP: getPlayerHouse import already present"
            new_ln = ln.replace("}", ", getPlayerHouse }", 1)
            if new_ln != ln:
                lines[idx] = new_ln
                return "\n".join(lines), True, "OK: getPlayerHouse added to services/api import"
    # Multiline import: closing brace line before the from clause.
    for idx, ln in enumerate(lines):
        if re.match(r"\s*}\s*from\s*['\"].*services/api['\"]", ln):
            block = "\n".join(lines[max(0, idx - 15):idx + 1])
            if "import" in block and "getPlayerHouse" not in block:
                lines[idx] = ln.replace("}", ", getPlayerHouse }", 1)
                return "\n".join(lines), True, "OK: getPlayerHouse added to multiline services/api import"
    return text, False, ""


def main():
    try:
        src = INDEX.read_text(encoding="utf-8")
    except FileNotFoundError:
        print("HOUSE_INTERIOR_REFRESH_ERROR: index.tsx not found (run from /app)")
        return 1
    orig = src
    lines = src.split("\n")

    # ---- 1. ENTER: refetch fresh house on ENTER HOUSE ----
    if REFRESH_MARKER in src:
        print("SKIP: interior refresh enter block already present")
    else:
        # Anchor: the line that copies the cached marker into the interior.
        cand = [i for i, ln in enumerate(lines) if "setInteriorHouse(selectedMarker.data)" in ln]
        enter_idx = None
        if len(cand) == 1:
            enter_idx = cand[0]
        elif len(cand) > 1:
            print("WARNING: ENTER anchor matched %d lines (expected 1) - enter refetch SKIPPED" % len(cand))
        else:
            # Fallback: ENTER HOUSE text, look above it for the cached enter.
            text_idx = [i for i, ln in enumerate(lines) if "ENTER HOUSE" in ln]
            for ti in text_idx:
                for j in range(ti - 1, max(-1, ti - 13), -1):
                    if "setInteriorHouse(selectedMarker" in lines[j]:
                        enter_idx = j
                        break
                if enter_idx is not None:
                    break
            if enter_idx is None:
                print("WARNING: ENTER HOUSE anchor not found - enter refetch SKIPPED")
        if enter_idx is not None:
            # Decide the fetch expression from what live index.tsx already has.
            fetch_expr = None
            if "getPlayerHouse" in src:
                fetch_expr = "getPlayerHouse(playerId)"
                print("OK: using existing getPlayerHouse in index.tsx")
            else:
                new_src, ok, note = _ensure_getplayerhouse_import(lines, src)
                if ok:
                    src = new_src
                    lines = src.split("\n")
                    # Anchor line numbers may shift by 0 (same-line edit) — recompute.
                    cand = [i for i, ln in enumerate(lines) if "setInteriorHouse(selectedMarker.data)" in ln]
                    enter_idx = cand[0] if len(cand) == 1 else enter_idx
                    fetch_expr = "getPlayerHouse(playerId)"
                    print(note)
                elif "api.get(" in src or "import api " in src or "import api," in src:
                    fetch_expr = "api.get(`/houses/player/${playerId}`)"
                    print("OK: using existing api client for GET /houses/player/{playerId}")
                else:
                    print("WARNING: neither getPlayerHouse nor an api client found in index.tsx - enter refetch SKIPPED")
            if fetch_expr is not None:
                indent = _indent_of(lines[enter_idx])
                lines[enter_idx] = _enter_block(indent, fetch_expr)
                src = "\n".join(lines)
                print("OK: ENTER HOUSE now refetches fresh house from server")

    # ---- 2. LEAVE: ensure the LEAVE HOUSE button clears interiorHouse ----
    # (Quoted live code already does onPress={() => setInteriorHouse(null)};
    # this section is check-only when that clear is present, never duplicates.)
    lines = src.split("\n")
    leave_text = [i for i, ln in enumerate(lines) if "LEAVE HOUSE" in ln and "<Text" in ln]
    if not leave_text:
        # Fall back: any line mentioning LEAVE HOUSE that is not a comment.
        leave_text = [i for i, ln in enumerate(lines)
                      if "LEAVE HOUSE" in ln and not ln.strip().startswith("//")
                      and not ln.strip().startswith("*")]
    if not leave_text:
        print("WARNING: LEAVE HOUSE button anchor not found - leave clear unverified (onRequestClose may still clear)")
    else:
        ti = leave_text[0]
        onpress_idx = None
        for j in range(ti - 1, max(-1, ti - 9), -1):
            if "onPress" in lines[j]:
                onpress_idx = j
                break
        if onpress_idx is None:
            print("WARNING: LEAVE HOUSE button onPress not found above LEAVE HOUSE text - leave clear unverified")
        elif "setInteriorHouse(null)" in lines[onpress_idx]:
            print("SKIP: LEAVE HOUSE button already clears interiorHouse")
        elif re.match(r"\s*onPress=\{\(\) => \{[^}]*\}\}", lines[onpress_idx]):
            lines[onpress_idx] = lines[onpress_idx].replace(
                "onPress={() => {", "onPress={() => { setInteriorHouse(null); ", 1)
            src = "\n".join(lines)
            print("OK: LEAVE HOUSE button now clears interiorHouse")
        else:
            print("WARNING: LEAVE HOUSE button onPress form not safely injectable - leave clear unverified")

    # ---- 3. onRequestClose: report / ensure the same clear ----
    lines = src.split("\n")
    req = [i for i, ln in enumerate(lines) if "onRequestClose" in ln]
    if not req:
        print("WARNING: interior modal onRequestClose not found - back-button close unverified")
    elif any("setInteriorHouse(null)" in lines[i] for i in req):
        print("SKIP: interior modal onRequestClose already clears interiorHouse")
    else:
        done = False
        for i in req:
            if re.match(r"\s*onRequestClose=\{\(\) => [^}]*\}", lines[i]):
                lines[i] = re.sub(r"onRequestClose=\{\(\) => [^}]*\}",
                                  "onRequestClose={() => setInteriorHouse(null)}", lines[i], count=1)
                src = "\n".join(lines)
                print("OK: interior modal onRequestClose now clears interiorHouse")
                done = True
                break
        if not done:
            print("WARNING: interior modal onRequestClose form not safely injectable - back-button close unverified")

    if src != orig:
        INDEX.write_text(src, encoding="utf-8")
        print("OK: index.tsx updated")
    else:
        print("SKIP: index.tsx unchanged (no sections applied)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
