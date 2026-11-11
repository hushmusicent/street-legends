"""Street Legends frontend: send the phone's LIVE GPS with eat / nightclub
visits, and make position-update failures visible.

Run from repo root: python3 frontend/patch-restaurant-fresh-gps-frontend.py
Idempotent - safe to re-run.

WHY (diag result 2026-11-05, RESTAURANT_DISTANCE_DIAG_OK verdict=(a)):
  The server's eat check measures the 100m distance from the STORED player
  position, which was frozen 17 hours old -- a Marco's Pizza right by the
  player measured as 7478m away. The backend half of this fix (backend/
  patch-restaurant-fresh-gps.py) lets the server measure from a LIVE
  position sent with the request. This patch sends it:
  - api.ts eatAtRestaurant / visitNightclub take an optional live position
    and append ?latitude=&longitude= when given; without it the server
    falls back to the stored position (old behavior).
  - The EAT HERE / nightclub popup handlers pass the live location the
    map itself uses (the currentPosition state, fed by watchPositionAsync
    every second) -- no extra GPS read, no handler-shape change. If that
    state cannot be found, the patch falls back to a fresh
    Location.getCurrentPositionAsync() read inside the (async) handler.
  - Position updates: api.ts updatePlayerPosition now retries ONCE on
    failure and console.warns with the HTTP status (a failing PUT used to
    vanish silently while the server kept a stale position for hours).
    useMapQueries.ts's silent .catch(() => {}) now warns too. The 5s
    server-update throttle is UNCHANGED, and the index.tsx call sites are
    verified to pass the fresh fix (position / newPos from
    getCurrentPositionAsync / watchPositionAsync), not a stale state value.

TOUCHES NOTHING ELSE: no map, marker, popup, threshold, or other feature
changes. The 100m threshold lives on the server and is unchanged.
"""
import re
import sys
from pathlib import Path

MARKER = "RESTAURANT_FRESH_GPS_FRONTEND"
API = Path("frontend/services/api.ts")
UMQ = Path("frontend/hooks/useMapQueries.ts")
INDEX_CANDIDATES = [
    Path("frontend/app/(tabs)/index.tsx"),  # live layout (per diag)
    Path("frontend/app/index.tsx"),         # older layout fallback
]

# ---------------------------------------------------------------- api.ts

_OLD_UPDATE = """export const updatePlayerPosition = async (playerId: string, position: Position): Promise<void> => {
  await api.put(`/players/${playerId}/position`, position);
};"""

_NEW_UPDATE = """export const updatePlayerPosition = async (playerId: string, position: Position): Promise<void> => {
  // RESTAURANT_FRESH_GPS_FRONTEND: a failing position PUT used to vanish
  // silently (.catch(() => {}) at the call sites) while the server kept a
  // stale position for hours. Retry once, and WARN with the HTTP status so
  // a broken update is visible instead of invisible.
  try {
    await api.put(`/players/${playerId}/position`, position);
  } catch (e: any) {
    console.warn('[POSITION] update failed, retrying once', e?.response?.status ?? e?.message);
    try {
      await api.put(`/players/${playerId}/position`, position);
    } catch (e2: any) {
      console.warn('[POSITION] update failed after retry', e2?.response?.status ?? e2?.message);
      throw e2;
    }
  }
};"""

_OLD_EAT = """export const eatAtRestaurant = async (restaurantId: string, playerId: string) => {
  const response = await api.post(`/restaurants/${restaurantId}/eat?player_id=${playerId}`);
  return response.data;
};"""

_NEW_EAT = """export const eatAtRestaurant = async (restaurantId: string, playerId: string, position?: { latitude: number; longitude: number }) => {
  // RESTAURANT_FRESH_GPS_FRONTEND: send the phone's LIVE GPS so the
  // server's 100m check measures from where the player actually is, not
  // the stored position (17h stale: "7478m away"). No position = old
  // behavior (server falls back to the stored position).
  const gps = position ? `&latitude=${position.latitude}&longitude=${position.longitude}` : '';
  const response = await api.post(`/restaurants/${restaurantId}/eat?player_id=${playerId}${gps}`);
  return response.data;
};"""

_OLD_VISIT = """export const visitNightclub = async (nightclubId: string, playerId: string) => {
  const response = await api.post(`/nightclubs/${nightclubId}/visit?player_id=${playerId}`);
  return response.data;
};"""

_NEW_VISIT = """export const visitNightclub = async (nightclubId: string, playerId: string, position?: { latitude: number; longitude: number }) => {
  // RESTAURANT_FRESH_GPS_FRONTEND: same live-GPS fix as eatAtRestaurant.
  const gps = position ? `&latitude=${position.latitude}&longitude=${position.longitude}` : '';
  const response = await api.post(`/nightclubs/${nightclubId}/visit?player_id=${playerId}${gps}`);
  return response.data;
};"""


def _replace_or_warn(src, old, new, done_fragment, label, warnings):
    """Replace `old` with `new` in the accumulated src; warn (change
    nothing) if the anchor is missing. `done_fragment` is a string only
    the NEW text contains (proves this piece already landed)."""
    if done_fragment in src:
        print(f"ALREADY_APPLIED: {label}")
        return src, False
    if old in src:
        return src.replace(old, new, 1), True
    print(f"WARNING: {label} anchor not found - NOT changed (looked for "
          f"'{old.splitlines()[0][:80]}')")
    warnings.append(label)
    return src, False


def _patch_api():
    """api.ts: retrying updatePlayerPosition + live-GPS eat/visit."""
    if not API.exists():
        print(f"WARNING: {API} not found - api.ts NOT changed")
        return ["api-missing"]
    src = API.read_text()
    warnings = []
    changed = []

    if MARKER in src:
        print("ALREADY_APPLIED: api.ts (marker present)")
        return warnings

    src, ok = _replace_or_warn(src, _OLD_UPDATE, _NEW_UPDATE,
                               "retrying once",
                               "api updatePlayerPosition retry", warnings)
    if ok:
        changed.append("updatePlayerPosition retry")
        print("OK: api.ts updatePlayerPosition retries once + warns "
              "with status on failure")
    src, ok = _replace_or_warn(src, _OLD_EAT, _NEW_EAT,
                               "eat?player_id=${playerId}${gps}",
                               "api eatAtRestaurant live GPS", warnings)
    if ok:
        changed.append("eatAtRestaurant live GPS")
        print("OK: api.ts eatAtRestaurant sends live GPS "
              "(?latitude=&longitude=) when given")
    src, ok = _replace_or_warn(src, _OLD_VISIT, _NEW_VISIT,
                               "visit?player_id=${playerId}${gps}",
                               "api visitNightclub live GPS", warnings)
    if ok:
        changed.append("visitNightclub live GPS")
        print("OK: api.ts visitNightclub sends live GPS "
              "(?latitude=&longitude=) when given")

    if changed:
        API.write_text(src)
    return warnings


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


def _patch_popup_call(text, fn_name, state_name, label, warnings):
    """Pass the live GPS to one popup call:
    `await <fn>(selectedMarker.data.id, playerId)` ->
    `await <fn>(selectedMarker.data.id, playerId, <gps>)`.

    <gps> is the live-location state when found, else a fresh
    Location.getCurrentPositionAsync() read inserted before the call.
    Returns (new_text, status)."""
    call_re = re.compile(
        r"await " + re.escape(fn_name) +
        r"\(selectedMarker\.data\.id,\s*playerId\)")
    m = call_re.search(text)
    if not m:
        if re.search(re.escape(fn_name) +
                     r"\(selectedMarker\.data\.id,\s*playerId,\s*[^)]+\)",
                     text):
            return text, "already"
        return text, ("warn", f"{label} call not found - live GPS NOT "
                              f"passed (looked for 'await {fn_name}("
                              f"selectedMarker.data.id, playerId)')")
    line_start = text.rfind("\n", 0, m.start()) + 1
    indent = text[line_start:m.start()]
    indent = indent[:len(indent) - len(indent.lstrip(" "))]
    if state_name:
        gps = f"{state_name} ?? undefined"
        new_call = (f"await {fn_name}(selectedMarker.data.id, playerId, "
                    f"{gps})")
        return text[:m.start()] + new_call + text[m.end():], "ok-state"
    # Fallback: fresh fix read inside the (async) handler.
    if "Location.getCurrentPositionAsync" not in text:
        return text, ("warn", f"{label}: no live-location state and "
                              f"Location.getCurrentPositionAsync not in "
                              f"file - live GPS NOT passed")
    var = "_eatGps" if fn_name == "eatAtRestaurant" else "_visitGps"
    fetch = (
        f"{indent}// {MARKER}: fresh GPS fix at tap time, so the server's\n"
        f"{indent}// 100m check measures from where the player actually is.\n"
        f"{indent}let {var}: {{ latitude: number; longitude: number }} "
        f"| undefined;\n"
        f"{indent}try {{\n"
        f"{indent}  const _fix = await "
        f"Location.getCurrentPositionAsync({{}});\n"
        f"{indent}  {var} = {{ latitude: _fix.coords.latitude, "
        f"longitude: _fix.coords.longitude }};\n"
        f"{indent}}} catch {{ {var} = undefined; }}\n"
    )
    new_call = (f"await {fn_name}(selectedMarker.data.id, playerId, {var})")
    return (text[:line_start] + fetch + text[line_start:m.start()] +
            new_call + text[m.end():]), "ok-fetch"


def _verify_position_call_sites(text):
    """Check every updatePlayerPosition(playerId, X) call site passes the
    fresh fix. Returns a list of status strings (no edits)."""
    out = []
    for m in re.finditer(
            r"updatePlayerPosition\(playerId,\s*(\w+)\)", text):
        arg = m.group(1)
        line_no = text[:m.start()].count("\n") + 1
        window = text[max(0, m.start() - 4000):m.start()]
        if arg == "defaultPos":
            out.append(("ok", f"index.tsx line {line_no}: "
                             f"updatePlayerPosition(playerId, defaultPos) -- "
                             f"permission-denied fallback, by design"))
        elif arg in ("position", "newPos") and (
                "getCurrentPositionAsync" in window or
                "watchPositionAsync" in window):
            out.append(("ok", f"index.tsx line {line_no}: "
                             f"updatePlayerPosition(playerId, {arg}) -- "
                             f"fresh fix from getCurrentPositionAsync / "
                             f"watchPositionAsync in the same function"))
        else:
            out.append(("warn", f"index.tsx line {line_no}: "
                                f"updatePlayerPosition(playerId, {arg}) -- "
                                f"could not verify it is the fresh GPS fix "
                                f"(no getCurrentPositionAsync / "
                                f"watchPositionAsync in the enclosing "
                                f"function); left unchanged"))
    return out


def _patch_index():
    """index.tsx: EAT HERE + nightclub pass live GPS; verify position
    call sites."""
    path = None
    for cand in INDEX_CANDIDATES:
        if cand.exists():
            path = cand
            break
    if path is None:
        print(f"WARNING: index.tsx not found at "
              f"{' or '.join(str(c) for c in INDEX_CANDIDATES)} - "
              f"popup handlers NOT changed")
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
              "fresh getCurrentPositionAsync() read in the handlers")
        warnings.append("index-state")

    for fn_name, label in (("eatAtRestaurant", "EAT HERE"),
                           ("visitNightclub", "nightclub visit")):
        text, status = _patch_popup_call(text, fn_name, state, label,
                                         warnings)
        if status == "already":
            print(f"ALREADY_APPLIED: {label} passes live GPS")
        elif isinstance(status, tuple):
            print(f"WARNING: {status[1]}")
            warnings.append(label)
        elif status == "ok-state":
            changed.append(label)
            print(f"OK: {label} passes live GPS (state '{state}')")
        else:
            changed.append(label)
            print(f"OK: {label} passes live GPS (fresh fix read at tap)")

    for kind, msg in _verify_position_call_sites(text):
        if kind == "ok":
            print(f"OK: {msg}")
        else:
            print(f"WARNING: {msg}")
            warnings.append("index-call-site")

    if changed:
        path.write_text(text)
    return warnings


# --------------------------------------------------------- useMapQueries

def _patch_umq():
    """useMapQueries.ts: silent .catch(() => {}) on the position update
    now warns (the retry itself lives in api.ts)."""
    if not UMQ.exists():
        print(f"WARNING: {UMQ} not found - useMapQueries NOT changed")
        return ["umq-missing"]
    text = UMQ.read_text()
    if MARKER in text:
        print("ALREADY_APPLIED: useMapQueries position-update warn")
        return []
    old = ("updatePlayerPosition(playerId, { latitude, longitude })"
           ".catch(() => {});")
    new = ("updatePlayerPosition(playerId, { latitude, longitude })"
           ".catch((e) => console.warn('[POSITION] update failed after "
           "retry', (e as any)?.response?.status ?? (e as any)?.message)); "
           f"// {MARKER}")
    if old in text:
        UMQ.write_text(text.replace(old, new, 1))
        print("OK: useMapQueries position update now warns on failure "
              "(was silently swallowed)")
        return []
    if "updatePlayerPosition(playerId, { latitude, longitude })" in text:
        print("WARNING: useMapQueries position-update catch shape not "
              "recognized - NOT changed (looked for "
              "'.catch(() => {})' on the updatePlayerPosition call)")
        return ["umq-catch"]
    print("WARNING: useMapQueries does not call updatePlayerPosition - "
          "NOT changed")
    return ["umq-call"]


def main():
    warnings = []
    warnings += _patch_api()
    warnings += _patch_index()
    warnings += _patch_umq()
    if warnings:
        print("RESTAURANT_FRESH_GPS_FRONTEND_PARTIAL: (warnings: " +
              ", ".join(warnings) + ")")
    else:
        print("RESTAURANT_FRESH_GPS_FRONTEND_OK")


if __name__ == "__main__":
    main()
