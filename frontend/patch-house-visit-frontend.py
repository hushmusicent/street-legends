#!/usr/bin/env python3
"""Street Legends frontend: friend house visiting + presence (inside only).

APPROVED SPEC (user-confirmed 2026-11-03, do not expand):
- Friend taps a friend's house marker -> ENTER -> that friend's
  interior, in guest mode.
- Guest CAN: play house games, turn on the radio, watch the TV
  (device-local playback only).
- Guest CANNOT: buy/sell/add/remove/place items, sell the house,
  move it to inventory, or hide it.
- Presence list shows INSIDE the house only (never on the map
  marker): interior header shows "In this house now:" with live
  occupant names. Leaving removes you; a closed app drops off
  after the backend 180s stale timeout.

LIVE DIAGNOSTIC FACTS (diag-house-visit.py on /app):
- ENTER loads the tapped marker object:
  onPress={() => setInteriorHouse(selectedMarker.data)}.
  A separate refresh step refetches the VIEWER's own house
  (getPlayerHouse(playerId)) — for guests that refetch MUST be
  skipped, or a guest's interior gets overwritten with the
  visitor's own house. This patch guards it with a marker-based
  guest check (state is stale inside onPress, so the marker data
  itself is the source of truth).
- Backend items endpoints are already owner-checked (403), so the
  frontend gates below are UI enforcement; the backend patch adds
  presence endpoints + house-action guards as the real safety net.
- No presence code existed. The TV toggle (tvOn) and radio toggle
  must keep working for guests: the interior guest gate is placed
  AFTER the TV/radio toggle guards, never before them.

SECTIONS (each scoped; a missed anchor prints WARNING and the patch
continues; re-running prints HOUSE_VISIT_FRONTEND_ALREADY_APPLIED
and changes nothing):
- services/api.ts: presence client functions (appended at end).
- index.tsx: services/api import extension, guest/presence state,
  presence lifecycle effect (enter once on open, heartbeat 30s,
  poll presence 15s, leave via cleanup on close/unmount — which
  covers the LEAVE HOUSE button, modal close, and unmount),
  presence row in the interior header, house-popup guest gate
  (guests see ONLY ENTER), interior toggle guest gate,
  guest refetch skip on ENTER.

Run from /app: python3 frontend/patch-house-visit-frontend.py
Frontend only: reload Expo Go after running, no build, no Deploy
for this patch itself (the backend presence patch needs Publish
separately).
"""
import re
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
API = Path("frontend/services/api.ts")
MARKER = "HOUSE_VISIT_FRONTEND_OK"
CODE_MARKER = "// HOUSE_VISIT"
API_MARKER = "// HOUSE_VISIT_PRESENCE_API"
PRESENCE_FNS = [
    "houseEnterPresence",
    "houseLeavePresence",
    "houseHeartbeatPresence",
    "getHousePresence",
]

API_FNS_TEXT = """
// HOUSE_VISIT_PRESENCE_API: friend house presence client.
export const houseEnterPresence = async (houseId: string, playerId: string, playerName: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/enter`, { player_id: playerId, player_name: playerName });
  return response.data;
};
export const houseLeavePresence = async (houseId: string, playerId: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/leave`, { player_id: playerId });
  return response.data;
};
export const houseHeartbeatPresence = async (houseId: string, playerId: string, playerName: string): Promise<any> => {
  const response = await api.post(`/houses/${houseId}/heartbeat`, { player_id: playerId, player_name: playerName });
  return response.data;
};
export const getHousePresence = async (houseId: string): Promise<any> => {
  const response = await api.get(`/houses/${houseId}/presence`);
  return response.data;
};
"""


def _indent_of(line):
    m = re.match(r"[ \t]*", line)
    return m.group(0) if m else ""


def _brace_delta(text):
    return text.count("{") - text.count("}")


def _extend_api_import(lines, src):
    """Add presence fn names to the services/api import. Returns (src, ok)."""
    for idx, ln in enumerate(lines):
        if "services/api" in ln and "import" in ln and "{" in ln and "}" in ln:
            missing = [n for n in PRESENCE_FNS if n not in ln]
            if not missing:
                return src, True
            new_ln = ln.replace("}", ", " + ", ".join(missing) + " }", 1)
            lines[idx] = new_ln
            return "\n".join(lines), True
    for idx, ln in enumerate(lines):
        if re.match(r"\s*}\s*from\s*['\"].*services/api['\"]", ln):
            block = "\n".join(lines[max(0, idx - 15):idx + 1])
            if "import" in block:
                missing = [n for n in PRESENCE_FNS if n not in block]
                if not missing:
                    return src, True
                lines[idx] = ln.replace("}", ", " + ", ".join(missing) + " }", 1)
                return "\n".join(lines), True
    return src, False


def _wrap_button(lines, text_idx, label):
    """Wrap one TouchableOpacity button (containing text_idx) in a guest
    conditional so guests never see it. Returns (lines, ok, note)."""
    open_idx = None
    for j in range(text_idx, max(-1, text_idx - 11), -1):
        if "<TouchableOpacity" in lines[j]:
            open_idx = j
            break
    if open_idx is None:
        return lines, False, "WARNING: popup %s button anchor not matched - button stays visible; backend 403 still blocks guests" % label
    close_idx = None
    for j in range(text_idx, min(len(lines), text_idx + 11)):
        if "</TouchableOpacity>" in lines[j]:
            close_idx = j
            break
    if close_idx is None or close_idx < open_idx:
        return lines, False, "WARNING: popup %s button close anchor not matched - button stays visible; backend 403 still blocks guests" % label
    span = "\n".join(lines[open_idx:close_idx + 1])
    if "<TouchableOpacity" in span[span.find("<TouchableOpacity") + 1:] and span.count("<TouchableOpacity") > 1:
        return lines, False, "WARNING: popup %s button has nested pressables - gate SKIPPED; backend 403 still blocks guests" % label
    if "HOUSE_VISIT popup guest gate" in span:
        return lines, True, "SKIP: popup %s already guest-gated" % label
    indent = _indent_of(lines[open_idx])
    opener = indent + "{selectedMarker?.data?.player_id === playerId ? ( // HOUSE_VISIT popup guest gate"
    closer = indent + ") : null}"
    lines = lines[:open_idx] + [opener] + lines[open_idx:close_idx + 1] + [closer] + lines[close_idx + 1:]
    return lines, True, "OK: popup %s hidden for guests (ENTER stays)" % label


def main():
    if not INDEX.exists():
        print("HOUSE_VISIT_FRONTEND_ERROR: frontend/app/(tabs)/index.tsx not found (run from /app)")
        return 1
    src = INDEX.read_text(encoding="utf-8")
    orig = src
    if CODE_MARKER in src:
        print("HOUSE_VISIT_FRONTEND_ALREADY_APPLIED")
        return 0
    lines = src.split("\n")

    # ---- 0. services/api.ts: presence client functions ----
    api_ok = False
    if API.exists():
        api_src = API.read_text(encoding="utf-8")
        if all(n in api_src for n in PRESENCE_FNS):
            print("SKIP: presence client functions already in services/api.ts")
            api_ok = True
        elif "const api =" not in api_src:
            print("WARNING: api client anchor not found in services/api.ts - presence client functions SKIPPED")
        else:
            API.write_text(api_src.rstrip("\n") + "\n" + API_FNS_TEXT, encoding="utf-8")
            print("OK: presence client functions added to services/api.ts")
            api_ok = True
    else:
        print("WARNING: services/api.ts not found - presence client functions SKIPPED")

    # ---- 1. services/api import extension ----
    import_ok = False
    if api_ok:
        lines = src.split("\n")
        new_src, import_ok = _extend_api_import(lines, src)
        if import_ok:
            src = new_src
            lines = src.split("\n")
            print("OK: presence functions added to services/api import")
        else:
            print("WARNING: services/api import not found in index.tsx - presence import SKIPPED")
    else:
        print("WARNING: presence import skipped (client functions unavailable)")

    presence_wiring = api_ok and import_ok

    # ---- 2. Guest/presence state ----
    state_ok = False
    state_idx = None
    for i, ln in enumerate(lines):
        if "const [tvOn, setTvOn] = useState(false);" in ln:
            state_idx = i
            break
    if state_idx is None:
        for i, ln in enumerate(lines):
            if "const [interiorHouse, setInteriorHouse] = useState<any | null>(null);" in ln:
                state_idx = i
                break
    if state_idx is None:
        print("WARNING: interior state anchor not found - guest/presence state SKIPPED")
    else:
        indent = _indent_of(lines[state_idx])
        state_block = [
            indent + CODE_MARKER + ": guest mode + presence (inside the house only).",
            indent + "const [houseOccupants, setHouseOccupants] = useState<any[]>([]);",
            indent + "const isGuestVisit = !!(interiorHouse && (interiorHouse as any).player_id && (interiorHouse as any).player_id !== playerId);",
        ]
        lines = lines[:state_idx + 1] + state_block + lines[state_idx + 1:]
        src = "\n".join(lines)
        state_ok = True
        print("OK: guest/presence state added")

    # ---- 3. Presence lifecycle effect (only if wiring + state landed) ----
    if presence_wiring and state_ok:
        nm = re.search(r"const\s*\[\s*(player\w*)\s*,\s*setPlayer", src)
        if nm:
            name_expr = "(%s as any)?.name || 'Player'" % nm.group(1)
        else:
            name_expr = "'Player'"
            print("WARNING: player name variable not found - presence names fall back to 'Player'")
        # Insert effect right after the state block (after isGuestVisit line).
        eff_idx = None
        for i, ln in enumerate(lines):
            if "const isGuestVisit =" in ln:
                eff_idx = i
                break
        if eff_idx is None:
            print("WARNING: guest state line not found - presence effect SKIPPED")
        else:
            indent = _indent_of(lines[eff_idx])
            effect = [
                indent + CODE_MARKER + ": presence lifecycle - enter on open, heartbeat 30s, poll 15s,",
                indent + "  leave via cleanup on close/unmount (covers LEAVE HOUSE button, modal close, unmount).",
                indent + "useEffect(() => {",
                indent + "  if (!interiorHouse || !playerId) return;",
                indent + "  let stopped = false;",
                indent + "  const visitName = " + name_expr + ";",
                indent + "  const loadOccupants = async () => {",
                indent + "    try {",
                indent + "      const res: any = await getHousePresence(interiorHouse.id);",
                indent + "      if (!stopped && res?.occupants) setHouseOccupants(res.occupants);",
                indent + "    } catch (_) {}",
                indent + "  };",
                indent + "  (async () => {",
                indent + "    try {",
                indent + "      const res: any = await houseEnterPresence(interiorHouse.id, playerId, visitName);",
                indent + "      if (!stopped && res?.occupants) setHouseOccupants(res.occupants);",
                indent + "    } catch (_) {}",
                indent + "  })();",
                indent + "  const hb = setInterval(async () => {",
                indent + "    try { await houseHeartbeatPresence(interiorHouse.id, playerId, visitName); } catch (_) {}",
                indent + "  }, 30000);",
                indent + "  const poll = setInterval(loadOccupants, 15000);",
                indent + "  return () => {",
                indent + "    stopped = true;",
                indent + "    clearInterval(hb);",
                indent + "    clearInterval(poll);",
                indent + "    houseLeavePresence(interiorHouse.id, playerId).catch(() => {});",
                indent + "  };",
                indent + "}, [interiorHouse?.id, playerId]);",
            ]
            lines = lines[:eff_idx + 1] + effect + lines[eff_idx + 1:]
            src = "\n".join(lines)
            print("OK: presence lifecycle effect added (enter/heartbeat/poll/leave)")
    else:
        if not presence_wiring:
            print("WARNING: presence effect SKIPPED (import/client unavailable)")
        if not state_ok:
            print("WARNING: presence effect SKIPPED (state unavailable)")

    # ---- 4. Presence row in the interior header (scoped from LEAVE HOUSE) ----
    if presence_wiring and state_ok:
        lines = src.split("\n")
        # LEAVE HOUSE text line: prefer a real <Text> element, so this
        # patch's own comments (which mention LEAVE HOUSE) never match.
        leave_idx = None
        for i, ln in enumerate(lines):
            if "LEAVE HOUSE" in ln and "<Text" in ln:
                leave_idx = i
                break
        if leave_idx is None:
            for i, ln in enumerate(lines):
                if ("LEAVE HOUSE" in ln and not ln.strip().startswith("//")
                        and not ln.strip().startswith("*")
                        and "HOUSE_VISIT" not in ln):
                    leave_idx = i
                    break
        hdr_idx = None
        if leave_idx is not None:
            for j in range(leave_idx, max(-1, leave_idx - 500), -1):
                if "item_limit" in lines[j] and "items" in lines[j]:
                    hdr_idx = j
                    break
        if hdr_idx is None:
            print("WARNING: interior header anchor not found - presence list NOT rendered (enter/heartbeat/poll still run)")
        else:
            indent = _indent_of(lines[hdr_idx])
            row = [
                indent + "{houseOccupants.length > 0 ? (",
                indent + "  <Text style={{ color: '#fff', fontSize: 12 }}>In this house now: {houseOccupants.map((o: any) => (o.player_id === playerId ? ((o.player_name || 'Player') + ' (you)') : (o.player_name || 'Player'))).join(', ')}</Text>",
                indent + ") : null}",
            ]
            lines = lines[:hdr_idx + 1] + row + lines[hdr_idx + 1:]
            src = "\n".join(lines)
            print("OK: presence row added to interior header")
    else:
        print("WARNING: presence row SKIPPED (wiring/state unavailable)")

    # ---- 5. House-popup guest gate (guests see ONLY ENTER) ----
    lines = src.split("\n")
    region_start = None
    for i, ln in enumerate(lines):
        if "selectedMarker.type === 'house'" in ln or "selectedMarker?.type === 'house'" in ln:
            region_start = i
            break
    if region_start is None:
        print("WARNING: house popup region not found - popup guest gate SKIPPED; backend 403 still blocks guests")
    else:
        region_end = len(lines)
        for i in range(region_start + 1, min(len(lines), region_start + 600)):
            if "selectedMarker.type ===" in lines[i] and "house" not in lines[i]:
                region_end = i
                break
        # Collect button text lines inside the region, bottom-up (stable indices).
        targets = []
        for label, patterns in [
            ("MOVE", ["MOVE TO INVENTORY"]),
            ("HIDE", ["HIDE ME FROM MAP", "HIDE"]),
            ("SELL", ["SELL FOR", "SELL"]),
        ]:
            found = None
            for i in range(region_start, region_end):
                for pat in patterns:
                    if pat in lines[i]:
                        found = i
                        break
                if found is not None:
                    break
            if found is not None:
                targets.append((found, label))
        targets.sort(reverse=True)
        for text_idx, label in targets:
            lines, ok, note = _wrap_button(lines, text_idx, label)
            print(note)
        src = "\n".join(lines)

    # ---- 6. Interior toggle guest gate (AFTER TV/radio guards) ----
    lines = src.split("\n")
    if "if (isGuestVisit) { return; }" in src:
        print("SKIP: interior guest gate already present")
    else:
        dm = re.search(r"handleHouseItemToggle\s*=\s*(?:async\s*)?\(\s*(\w+)", src)
        if not dm:
            print("WARNING: handleHouseItemToggle anchor not matched - interior guest gate SKIPPED (backend 403 still blocks guests)")
        else:
            start = dm.start()
            window = src[start:start + 6000]
            wlines = window.split("\n")
            guard_idx = None
            for i, ln in enumerate(wlines):
                if ("toggleTv" in ln or "toggleRadio" in ln) and "return" in ln:
                    guard_idx = i
            if guard_idx is not None:
                indent = _indent_of(wlines[guard_idx])
                wlines = wlines[:guard_idx + 1] + [indent + "if (isGuestVisit) { return; }"] + wlines[guard_idx + 1:]
                src = src[:start] + "\n".join(wlines) + src[start + 6000:]
                print("OK: interior guest gate added after TV/radio guards")
            else:
                call_idx = None
                for i, ln in enumerate(wlines):
                    if "addHouseItem(" in ln or "removeHouseItem(" in ln:
                        call_idx = i
                        break
                if call_idx is None:
                    print("WARNING: handleHouseItemToggle body anchor not matched - interior guest gate SKIPPED (backend 403 still blocks guests)")
                else:
                    indent = _indent_of(wlines[call_idx])
                    wlines = wlines[:call_idx] + [indent + "if (isGuestVisit) { return; }"] + wlines[call_idx:]
                    src = src[:start] + "\n".join(wlines) + src[start + 6000:]
                    print("OK: interior guest gate added before item add/remove")

    # ---- 7. Guest refetch skip on ENTER ----
    lines = src.split("\n")
    if "_visitIsGuest" in src:
        print("SKIP: guest refetch guard already present")
    elif "// HOUSE_INTERIOR_REFRESH" not in src:
        print("SKIP: no ENTER refetch present - guest interior already safe (marker object only)")
    else:
        set_idx = None
        for i, ln in enumerate(lines):
            if "setInteriorHouse(selectedMarker.data);" in ln:
                set_idx = i
                break
        if set_idx is None:
            print("WARNING: ENTER refresh anchor not matched - guest refetch skip SKIPPED (guest interior may be overwritten on ENTER; do not ship guest mode until fixed)")
        else:
            indent = _indent_of(lines[set_idx])
            lines.insert(set_idx + 1, indent + "const _visitIsGuest = !!((selectedMarker as any)?.data?.player_id && (selectedMarker as any).data.player_id !== playerId); // HOUSE_VISIT guest refetch guard")
            src = "\n".join(lines)
            lines = src.split("\n")
            cond_idx = None
            for i in range(set_idx, min(len(lines), set_idx + 40)):
                if "if (house && house.id) {" in lines[i]:
                    cond_idx = i
                    break
            if cond_idx is None:
                print("WARNING: ENTER refresh house condition not matched - guest refetch skip PARTIAL (flag defined but refetch not gated; do not ship guest mode until fixed)")
            else:
                lines[cond_idx] = lines[cond_idx].replace(
                    "if (house && house.id) {", "if (!_visitIsGuest && house && house.id) {", 1)
                src = "\n".join(lines)
                print("OK: guest ENTER refetch skipped (marker house kept for guests)")

    # ---- Balance guard + write ----
    if _brace_delta(src) != _brace_delta(orig):
        print("WARNING: brace balance changed - index.tsx NOT written (review before running)")
        return 1
    if src != orig:
        INDEX.write_text(src, encoding="utf-8")
        print("OK: index.tsx updated")
    else:
        print("SKIP: index.tsx unchanged (no sections applied)")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
