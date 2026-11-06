"""Street Legends frontend: send the phone's LIVE GPS with bank robberies.

Run from repo root: python3 frontend/patch-bank-robbery-fresh-gps-frontend.py
Idempotent - safe to re-run.

WHY (2026-11-05, user screenshot 19:45 EST):
  The robbery check reads the STORED player position (frozen 17h+), so
  tapping Huntington Bank right by the player said "You're 18769m away -
  get within 100m of Huntington Bank to rob it!". Restaurants + nightclub
  already got this fix (live GPS + 250m); banks were deliberately left out
  of both. The backend half of this fix (backend/
  patch-bank-robbery-fresh-gps.py) lets the server measure from a LIVE
  position sent with the request and widens the limit to 250m. This patch
  sends it:
  - api.ts robBank takes an optional live position and appends
    ?latitude=&longitude= when given; without it the server falls back to
    the stored position (old behavior).
  - handleRobBank passes the live location the map itself uses (the
    currentPosition state, fed by watchPositionAsync) -- the same source
    the EAT HERE / nightclub handlers use. The state is also added to the
    handleRobBank deps, so the callback never closes over a stale fix
    (its deps did not include the position before). If the state cannot be
    found, the patch falls back to a fresh Location.getCurrentPositionAsync()
    read inside the handler.
TOUCHES NOTHING ELSE: no popup, loot/risk/cooldown display, threshold, or
other feature changes. The 250m limit lives on the server.
"""
import re
import sys
from pathlib import Path

MARKER = "BANK_ROBBERY_FRESH_GPS_FRONTEND"
API = Path("frontend/services/api.ts")
INDEX_CANDIDATES = [
    Path("frontend/app/(tabs)/index.tsx"),  # live layout (per diag)
    Path("frontend/app/index.tsx"),         # older layout fallback
]

# ---------------------------------------------------------------- api.ts

_OLD_ROB = """export const robBank = async (bankId: string, playerId: string) => {
  const response = await api.post(`/banks/${bankId}/rob?player_id=${playerId}`);
  return response.data;
};"""

_NEW_ROB = """export const robBank = async (bankId: string, playerId: string, position?: { latitude: number; longitude: number }) => {
  // BANK_ROBBERY_FRESH_GPS_FRONTEND: send the phone's LIVE GPS so the
  // server's proximity check measures from where the player actually is,
  // not the stored position (17h stale: "18769m away"). No position = old
  // behavior (server falls back to the stored position).
  const gps = position ? `&latitude=${position.latitude}&longitude=${position.longitude}` : '';
  const response = await api.post(`/banks/${bankId}/rob?player_id=${playerId}${gps}`);
  return response.data;
};"""


def _patch_api():
    """api.ts: robBank takes an optional live position."""
    if not API.exists():
        print(f"WARNING: {API} not found - api.ts NOT changed")
        return ["api-missing"]
    src = API.read_text()
    if "rob?player_id=${playerId}${gps}" in src:
        print("ALREADY_APPLIED: api.ts robBank live GPS")
        return []
    if _OLD_ROB not in src:
        print("WARNING: api robBank live GPS anchor not found - NOT "
              "changed (looked for 'export const robBank = async "
              "(bankId: string, playerId: string) => {')")
        return ["api-rob"]
    API.write_text(src.replace(_OLD_ROB, _NEW_ROB, 1))
    print("OK: api.ts robBank sends live GPS (?latitude=&longitude=) "
          "when given")
    return []


# ------------------------------------------------------------- index.tsx

def _live_gps_state(text):
    """Name of the live-location state (the one the map uses), or None.

    Found from the setter called with the fresh fix: setCurrentPosition(
    position | newPos | defaultPos ) -> state 'currentPosition'."""
    m = re.search(r"set([A-Z]\w*)\(\s*(?:position|newPos|defaultPos)\s*\)",
                  text)
    if m:
        return m.group(1)[0].lower() + m.group(1)[1:]
    return None


def _patch_rob_call(text, state_name, warnings):
    """Pass the live GPS to the ROB THE BANK call:
    `await robBank(selectedBank.id, playerId)` ->
    `await robBank(selectedBank.id, playerId, <gps>)`.

    <gps> is the live-location state when found, else a fresh
    Location.getCurrentPositionAsync() read inserted before the call.
    Returns (new_text, status)."""
    call_re = re.compile(
        r"await robBank\(selectedBank\.id,\s*playerId\)")
    m = call_re.search(text)
    if not m:
        if re.search(r"robBank\(selectedBank\.id,\s*playerId,\s*[^)]+\)",
                     text):
            return text, "already"
        return text, ("warn", "ROB THE BANK call not found - live GPS NOT "
                              "passed (looked for 'await robBank("
                              "selectedBank.id, playerId)')")
    line_start = text.rfind("\n", 0, m.start()) + 1
    indent = text[line_start:m.start()]
    indent = indent[:len(indent) - len(indent.lstrip(" "))]
    if state_name:
        new_call = ("await robBank(selectedBank.id, playerId, "
                    f"{state_name} ?? undefined)")
        return text[:m.start()] + new_call + text[m.end():], "ok-state"
    # Fallback: fresh fix read inside the (async) handler.
    if "Location.getCurrentPositionAsync" not in text:
        return text, ("warn", "ROB THE BANK: no live-location state and "
                              "Location.getCurrentPositionAsync not in "
                              "file - live GPS NOT passed")
    var = "_robGps"
    fetch = (
        f"{indent}// {MARKER}: fresh GPS fix at tap time, so the server's\n"
        f"{indent}// proximity check measures from where the player actually is.\n"
        f"{indent}let {var}: {{ latitude: number; longitude: number }} "
        f"| undefined;\n"
        f"{indent}try {{\n"
        f"{indent}  const _fix = await "
        f"Location.getCurrentPositionAsync({{}});\n"
        f"{indent}  {var} = {{ latitude: _fix.coords.latitude, "
        f"longitude: _fix.coords.longitude }};\n"
        f"{indent}}} catch {{ {var} = undefined; }}\n"
    )
    new_call = f"await robBank(selectedBank.id, playerId, {var})"
    return (text[:line_start] + fetch + text[line_start:m.start()] +
            new_call + text[m.end():]), "ok-fetch"


def _patch_rob_deps(text, state_name):
    """Add the live-location state to handleRobBank's deps, so the
    callback never closes over a stale fix. Returns (new_text, status)."""
    if not state_name:
        return text, "skip"
    if re.search(r"\[playerId, selectedBank, robbingBank, refetchPlayer, "
                 + re.escape(state_name) + r"\]", text):
        return text, "already"
    old = "[playerId, selectedBank, robbingBank, refetchPlayer]"
    if old not in text:
        return text, ("warn", "handleRobBank deps not found - live GPS "
                              "passed but the callback may close over a "
                              "stale fix (looked for '}, [playerId, "
                              "selectedBank, robbingBank, refetchPlayer]);')")
    new = ("[playerId, selectedBank, robbingBank, refetchPlayer, "
           + state_name + "]")
    return text.replace(old, new, 1), "ok"


def _patch_index():
    """index.tsx: ROB THE BANK passes live GPS + deps include the state."""
    path = None
    for cand in INDEX_CANDIDATES:
        if cand.exists():
            path = cand
            break
    if path is None:
        print(f"WARNING: index.tsx not found at "
              f"{' or '.join(str(c) for c in INDEX_CANDIDATES)} - "
              f"ROB THE BANK handler NOT changed")
        return ["index-missing"]
    text = path.read_text()
    warnings = []
    changed = []

    state = _live_gps_state(text)
    if state:
        print(f"OK: live-location state found: '{state}' (map's own "
              f"location, fed by watchPositionAsync)")
    else:
        print("WARNING: live-location state not found - falling back to a "
              "fresh getCurrentPositionAsync() read in the handler")
        warnings.append("index-state")

    text, status = _patch_rob_call(text, state, warnings)
    if status == "already":
        print("ALREADY_APPLIED: ROB THE BANK passes live GPS")
    elif isinstance(status, tuple):
        print(f"WARNING: {status[1]}")
        warnings.append("rob-call")
    elif status == "ok-state":
        changed.append("rob-call")
        print(f"OK: ROB THE BANK passes live GPS (state '{state}')")
    else:
        changed.append("rob-call")
        print("OK: ROB THE BANK passes live GPS (fresh fix read at tap)")

    # Deps are attempted even when the call is already patched: the
    # call and the deps are separate pieces.
    text, dstatus = _patch_rob_deps(text, state)
    if dstatus == "already":
        print("ALREADY_APPLIED: handleRobBank deps include live state")
    elif dstatus == "skip":
        pass
    elif isinstance(dstatus, tuple):
        print(f"WARNING: {dstatus[1]}")
        warnings.append("rob-deps")
    else:
        changed.append("rob-deps")
        print(f"OK: handleRobBank deps now include '{state}' (no "
              f"stale closed-over fix)")

    if changed:
        path.write_text(text)
    return warnings


def main():
    warnings = []
    warnings += _patch_api()
    warnings += _patch_index()
    if warnings:
        print("BANK_ROBBERY_FRESH_GPS_FRONTEND_PARTIAL: (warnings: " +
              ", ".join(warnings) + ")")
    else:
        print("BANK_ROBBERY_FRESH_GPS_FRONTEND_OK")


if __name__ == "__main__":
    main()
