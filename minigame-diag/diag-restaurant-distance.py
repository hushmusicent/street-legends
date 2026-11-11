"""Street Legends live diagnostic: restaurant "Not Hungry Yet" distance is wrong.

Run from repo root (/app):  python3 minigame-diag/diag-restaurant-distance.py
READ-ONLY. Never edits any file, never restarts anything, never calls any
endpoint that moves cash/inventory, eats, or changes state. The only network
call is a GET of the player doc (and, if pymongo + MONGO_URL are available,
a read-only find for the Marco's Pizza docs). Set REST_DIAG_ROOT to point
it at a different repo root (used by the mock harness).

CASE (user screenshot 2026-11-05 17:31 EST):
  He tapped a Marco's Pizza marker and got:
    "Not Hungry Yet - You're 7478m away - get within 100m of Marco's Pizza
     to eat there!"
  But the marker sits right by him on the map. His phone GPS at the time:
  41.62708, -83.57260. The popup shows Marco's Pizza, Heals 25% HP,
  HP 298/306, +77 HP, EAT HERE button. Same screenshot: 0 enemies, 0 missions.

LIVE EVIDENCE (parent, just before this diag was written):
  GET /api/players/<his id> returns position {latitude: 41.6368324,
  longitude: -83.4785757} and last_active 2026-11-05T06:31:04Z -- the SAME
  position as at 15:17 EST today, last_active frozen at 01:31 EST, while
  his phone GPS moved all over Toledo since (41.6246 -> 41.64552 ->
  41.65431 -> 41.66297 -> 41.62708). The server's stored position has NOT
  moved all day. Distance from that frozen server position to his phone-now
  position is ~7889m; the toast said 7478m -- consistent with the distance
  being computed from the FROZEN SERVER position to a Marco's near his phone.

VERDICTS:
  (a) eat check uses the stale stored server position + position updates
      are not landing (the broken link is named: a1 update endpoint,
      a2 frontend update call, a3 code links look right -- runtime failure,
      errors are swallowed so a failing PUT is invisible)
  (b) check uses live GPS but the restaurant coordinates are wrong
      (lat/lng swapped in spawn, eat, or marker rendering)
  (c) the distance formula itself is wrong (worked example printed)
  (d) the check measures to the wrong restaurant (marker id != lookup key)
  (e) something else / could not determine
  healthy: no bug found in these links -- the 7478m is consistent with the
      stored position, so re-check which Marco's was tapped
"""
import json
import math
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("REST_DIAG_ROOT", "."))
BACKEND_URL = os.environ.get(
    "REST_DIAG_BACKEND_URL", "https://gta-quest-map.emergent.host"
)
PLAYER_ID = "3872dca3-bf7d-4807-8fc5-47c22ba67620"
FROZEN_POS = (41.6368324, -83.4785757)  # server-stored position, 2026-11-05
FROZEN_LAST_ACTIVE = "2026-11-05T06:31:04Z"
PHONE_GPS = (41.62708, -83.57260)  # phone GPS at screenshot time
TOAST_M = 7478
PLAYER_NAME = "Mayor Veno"

MISSING = []


def haversine_m(lat1, lon1, lat2, lon2):
    """Same formula as the server's calculate_distance (radians, R=6371000)."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = p2 - p1
    dlon = math.radians(lon2) - math.radians(lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def haversine_degrees_bug(lat1, lon1, lat2, lon2):
    """What the formula returns if math.radians is forgotten (verdict c demo)."""
    r = 6371000.0
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r * 2 * math.asin(math.sqrt(a))


def read(path):
    p = ROOT / path
    if not p.exists():
        MISSING.append(path)
        return None
    return p.read_text(errors="replace")


def numbered(text, start=1):
    out = []
    for i, line in enumerate(text.splitlines(), start):
        out.append(f"{i:>6}: {line}")
    return "\n".join(out)


def find_fn_block(src, start_re, stop_res):
    """Return (start_line_0based, end_line_0based, text) for a top-level block.

    start_re matches the def/decorator line. The block ends at the next line
    matching any of stop_res at column 0, or EOF.
    """
    lines = src.splitlines()
    start = None
    for i, line in enumerate(lines):
        if re.search(start_re, line):
            start = i
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j] and not lines[j][0].isspace():
            if any(re.match(p, lines[j]) for p in stop_res):
                end = j
                break
    return (start, end, "\n".join(lines[start:end]))


TOP_STOP = [r"@api_router\.", r"^(async )?def ", r"^class ", r"^# =+"]


def main():
    findings = []
    print("=== 0. case numbers ===")
    frozen_to_phone = haversine_m(
        FROZEN_POS[0], FROZEN_POS[1], PHONE_GPS[0], PHONE_GPS[1]
    )
    print(f"player: {PLAYER_NAME} id={PLAYER_ID}")
    print(f"server-stored position (frozen): {FROZEN_POS} "
          f"last_active={FROZEN_LAST_ACTIVE}")
    print(f"phone GPS at screenshot: {PHONE_GPS}")
    print(f"toast distance: {TOAST_M}m (threshold 100m)")
    print(f"haversine frozen-server-pos -> phone GPS: {frozen_to_phone:.0f}m")
    print(f"  toast vs frozen->phone: {TOAST_M:.0f}m vs {frozen_to_phone:.0f}m "
          f"(diff {abs(frozen_to_phone - TOAST_M):.0f}m -- the toast is "
          f"consistent with measuring FROM the frozen server position to a "
          f"Marco's near the phone)")
    print(f"  if the check used live phone GPS and the marker is really by "
          f"him, the distance should be < 100m, not {TOAST_M}m")
    findings.append(
        f"[0] frozen server pos -> phone GPS = {frozen_to_phone:.0f}m; "
        f"toast said {TOAST_M}m"
    )
    # staleness fallback: the frozen case numbers, used if the live GET fails
    try:
        _la = datetime.fromisoformat(
            FROZEN_LAST_ACTIVE.replace("Z", "+00:00"))
        if _la.tzinfo is None:  # server stores naive UTC datetimes
            _la = _la.replace(tzinfo=timezone.utc)
        _case_age_h = (datetime.now(timezone.utc) - _la).total_seconds() / 3600
    except Exception:  # noqa: BLE001
        _case_age_h = 999.0
    case_stale = _case_age_h > 1.0 or frozen_to_phone > 1000

    # ---- 1. the eat-distance check (server-side) + the formula ----
    print("\n=== 1. the eat-distance check ===")
    server = read("backend/server.py")
    eat_block = None
    lookup_key = None  # the find_one filter inside the eat endpoint
    eat_src = None  # 'stored' | 'live-gps' | 'none' | 'missing'
    threshold = None
    if server is None:
        print("backend/server.py NOT FOUND -- cannot check the eat endpoint")
    else:
        eat_block = find_fn_block(
            server, r"async def eat_at_restaurant\(", TOP_STOP
        )
        if eat_block is None:
            print("eat_at_restaurant NOT FOUND in backend/server.py")
            eat_src = "missing"
        else:
            s, e, text = eat_block
            print(f"--- eat_at_restaurant (lines {s + 1}-{e}) ---")
            print(numbered(text, s + 1))
            if "get within 100m" in text or "within 100m" in text:
                m = re.search(r"(\d+)\s*m away", text)
                threshold = 100
                print("--> proximity check PRESENT in the eat endpoint")
            else:
                print("--> NO proximity check in the eat endpoint "
                      "(no 'within 100m' text) -- the 7478m toast cannot "
                      "come from this code as printed")
            if 'player.get("position")' in text or "player['position']" in text \
                    or 'player.get("position"' in text:
                eat_src = "stored"
                print("--> distance source: STORED player position "
                      "(player.get(\"position\")) -- NOT live phone GPS")
            elif "currentPosition" in text or "live" in text.lower():
                eat_src = "live-gps"
                print("--> distance source: looks like LIVE GPS")
            else:
                eat_src = "none" if threshold is None else "stored?"
                print(f"--> distance source: could not classify "
                      f"(eat_src={eat_src})")
            if "calculate_distance" in text:
                print("--> uses calculate_distance()")
            # restaurant lookup key (verdict d)
            m = re.search(
                r"db\.restaurants\.find_one\(\{([^}]*)\}\)", text
            )
            if m:
                print(f"--> restaurant lookup: find_one({{{m.group(1)}}})")
                lookup_key = m.group(1)
            else:
                lookup_key = None
                print("--> restaurant lookup line not found in eat block")
        # calculate_distance, verbatim
        cd = find_fn_block(server, r"def calculate_distance\(", TOP_STOP)
        if cd is None:
            print("calculate_distance NOT FOUND in backend/server.py")
            formula_ok = False
            formula_note = "calculate_distance missing"
        else:
            s, e, text = cd
            print(f"\n--- calculate_distance (lines {s + 1}-{e}) ---")
            print(numbered(text, s + 1))
            uses_radians = "math.radians" in text
            r_match = re.search(r"R\s*=\s*([\d.]+)", text)
            r_val = float(r_match.group(1)) if r_match else None
            formula_ok = bool(uses_radians and r_val in (6371000, 6371000.0))
            formula_note = (
                f"radians={uses_radians}, R={r_val} "
                f"(6371000 = metres, correct)"
            )
            print(f"--> formula check: {formula_note} "
                  f"-> {'OK' if formula_ok else 'WRONG'}")
            if not formula_ok:
                # worked example: a true 300m hop, both ways
                a, b = (41.62708, -83.57260), (41.62978, -83.57260)  # ~300m N
                true_m = haversine_m(a[0], a[1], b[0], b[1])
                buggy_m = haversine_degrees_bug(a[0], a[1], b[0], b[1])
                print(f"--> worked example: two points {true_m:.0f}m apart "
                      f"-> correct formula {true_m:.0f}m, "
                      f"degrees-without-radians formula {buggy_m:.0f}m")
                findings.append(
                    f"[1] calculate_distance WRONG ({formula_note}); "
                    f"300m hop computes as {buggy_m:.0f}m"
                )
        # nightclub visit: same proximity pattern?
        nc = find_fn_block(server, r"async def visit_nightclub\(", TOP_STOP)
        if nc is not None and "within 100m" in nc[2]:
            print("--> nightclub visit ALSO has a 100m proximity check")
        elif nc is not None:
            print("--> nightclub visit has NO proximity check (restaurants only)")

    # ---- 2. the position pipeline ----
    print("\n=== 2. the position pipeline (how the stored position is fed) ===")
    upd_endpoint_ok = None
    upd_quirk = False
    if server is not None:
        upd = find_fn_block(
            server, r"async def update_player_position\(", TOP_STOP
        )
        if upd is None:
            print("update_player_position endpoint NOT FOUND in "
                  "backend/server.py (no PUT /players/{id}/position)")
            upd_endpoint_ok = False
        else:
            s, e, text = upd
            print(f"--- update_player_position (lines {s + 1}-{e}) ---")
            print(numbered(text, s + 1))
            sets_pos = '"position"' in text or "'position'" in text
            sets_active = "last_active" in text
            upd_quirk = "modified_count == 0" in text
            upd_endpoint_ok = bool(sets_pos and sets_active)
            print(f"--> $sets position={sets_pos}, "
                  f"last_active={sets_active} -> "
                  f"{'OK' if upd_endpoint_ok else 'BROKEN'}")
            if upd_quirk:
                print("--> QUIRK: raises 404 when modified_count == 0 -- "
                      "that also fires when the position is UNCHANGED, so "
                      "a stationary player gets 'Player not found' on "
                      "every update (the update is still a no-op then, "
                      "but the frontend sees an error)")
                findings.append("[2] update endpoint 404s on unchanged "
                                "position (modified_count == 0 quirk)")
        # every other writer of player position / last_active
        print("\n--- other writers of position / last_active in server.py ---")
        writers = []
        for i, line in enumerate(server.splitlines(), 1):
            if ("$set" in line and ("position" in line or "last_active" in line)) \
                    or ("position" in line and "update_one" in line):
                writers.append((i, line.strip()))
        if writers:
            for i, line in writers[:12]:
                print(f"  {i:>6}: {line[:150]}")
        else:
            print("  (none found besides the update endpoint)")
    else:
        print("backend/server.py NOT FOUND -- cannot check the update endpoint")

    # frontend: api.ts + call sites
    api = read("frontend/services/api.ts")
    fe_put_ok = None
    if api is None:
        print("\nfrontend/services/api.ts NOT FOUND")
    else:
        m = re.search(
            r"export const updatePlayerPosition[\s\S]{0,300}?api\.(put|post|patch)\(",
            api,
        )
        mm = re.search(
            r"updatePlayerPosition[\s\S]{0,200}?`/players/\$\{playerId\}/position`",
            api,
        )
        print("\n--- frontend api.ts updatePlayerPosition ---")
        for i, line in enumerate(api.splitlines(), 1):
            if "updatePlayerPosition" in line:
                print(f"  {i:>6}: {line.strip()}")
                if i + 1 <= len(api.splitlines()):
                    print(f"  {i + 1:>6}: {api.splitlines()[i].strip()}")
        fe_put_ok = bool(m and m.group(1) == "put" and mm)
        print(f"--> frontend update call: "
              f"{'PUT /players/{{id}}/position OK' if fe_put_ok else 'MISSING OR NOT A PUT -- check the lines above'}")

    idx = read("frontend/app/(tabs)/index.tsx")
    if idx is None:
        print("\nfrontend/app/(tabs)/index.tsx NOT FOUND")
    else:
        print("\n--- frontend index.tsx position call sites ---")
        for pat in ("initializeLocation", "watchPositionAsync",
                    "updatePlayerPosition(playerId"):
            for i, line in enumerate(idx.splitlines(), 1):
                if pat in line:
                    print(f"  {i:>6}: {line.strip()[:160]}")
        # throttle + error swallowing
        if "lastServerUpdateTime" in idx:
            m = re.search(r"lastServerUpdateTime\.current\s*>\s*(\d+)", idx)
            print(f"--> watch throttle: server update at most every "
                  f"{m.group(1) if m else '?'}ms")
        swallowed = idx.count(".catch(console.error)") + idx.count(".catch(() => {})")
        print(f"--> swallowed-error call sites in index.tsx: {swallowed} "
              f"(.catch(console.error) / .catch(() => {{}}) -- a failing "
              f"PUT is invisible to the player)")
    umq = read("frontend/hooks/useMapQueries.ts")
    if umq is None:
        print("\nfrontend/hooks/useMapQueries.ts NOT FOUND")
    else:
        print("\n--- frontend useMapQueries.ts position call ---")
        for i, line in enumerate(umq.splitlines(), 1):
            if "updatePlayerPosition" in line:
                print(f"  {i:>6}: {line.strip()[:180]}")
        if "await updatePlayerPosition" in umq:
            print("--> queryFn AWAITS the position update before fetching "
                  "entities (snapshot shape)")
        elif "updatePlayerPosition" in umq:
            print("--> queryFn calls updatePlayerPosition fire-and-forget "
                  "(entities-fast shape: errors swallowed, update may race)")
        else:
            print("--> useMapQueries does NOT call updatePlayerPosition")

    # ---- 3. restaurant data + id flow + marker rendering ----
    print("\n=== 3. restaurant data, id flow, marker rendering ===")
    spawn_ok = None
    if server is not None:
        sp = find_fn_block(server, r"async def spawn_restaurants\(", TOP_STOP)
        if sp is None:
            print("spawn_restaurants NOT FOUND in backend/server.py")
        else:
            s, e, text = sp
            swapped = bool(re.search(
                r'"latitude":\s*rlng|"latitude":\s*lng|"longitude":\s*rlat',
                text))
            print(f"--- spawn_restaurants (lines {s + 1}-{e}, "
                  f"{e - s} lines) ---")
            for i, line in enumerate(text.splitlines(), s + 1):
                if any(k in line for k in ("rlat", "rlng", '"latitude"',
                                           '"longitude"', "center.get",
                                           "el.get(\"lat\")", "out center")):
                    print(f"  {i:>6}: {line.strip()[:150]}")
            print(f"--> spawn lat/lng swapped: {swapped}")
            spawn_ok = not swapped
    if api is not None:
        m = re.search(r"export const eatAtRestaurant[\s\S]{0,200}", api)
        print("\n--- frontend eat call ---")
        print(" ", (m.group(0).replace(chr(10), " ") if m else "NOT FOUND"))
        m2 = re.search(r"export const spawnRestaurants[\s\S]{0,200}", api)
        print("--- frontend spawn call ---")
        print(" ", (m2.group(0).replace(chr(10), " ") if m2 else "NOT FOUND"))
    id_flow_ok = None
    if idx is not None:
        # marker coordinate + what the EAT HERE button sends
        m = re.search(
            r"eatAtRestaurant\(selectedMarker\.data\.id,\s*playerId\)", idx
        )
        print(f"\n--> EAT HERE sends selectedMarker.data.id: "
              f"{'YES' if m else 'NO -- check the button code'}")
        rm = re.search(
            r"nearbyRestaurants\.map\(\(r\) => \(\{\s*\n?\s*id:\s*r\.id,"
            r"\s*\n?\s*coordinate:\s*\{\s*latitude:\s*r\.latitude,\s*"
            r"longitude:\s*r\.longitude", idx)
        print(f"--> marker coordinate built from the SAME doc fields "
              f"(r.latitude/r.longitude): {'YES' if rm else 'NOT CONFIRMED -- check marker code'}")
        # (d): the eat endpoint must look the restaurant up by the SAME id
        # the marker carries (the spawn doc's uuid "id"). If it looks it up
        # by name / osm_id / anything else, the check measures to a
        # different restaurant than the one tapped.
        lookup_by_id = bool(lookup_key and '"id"' in lookup_key)
        print(f"--> eat lookup key: {lookup_key!r} "
              f"-> looks up by doc id: {lookup_by_id}")
        id_flow_ok = bool(m and rm and lookup_by_id)
    gm = read("frontend/components/GameMap.tsx")
    if gm is not None:
        mm = re.search(
            r"L\.marker\(\[t\.location\.latitude,\s*t\.location\.longitude\]",
            gm)
        print(f"--> GameMap renders markers as [latitude, longitude]: "
              f"{'YES' if mm else 'NOT CONFIRMED'}")

    # ---- 4. live read-only probe ----
    print("\n=== 4. live probe (read-only GETs) ===")
    live_pos = None
    live_active = None
    live_stale = None
    mock_player = os.environ.get("REST_DIAG_MOCK_PLAYER")
    if mock_player:
        try:
            doc = json.loads(Path(mock_player).read_text())
            print(f"(mock player doc from {mock_player})")
        except Exception as exc:  # noqa: BLE001
            print(f"mock player doc unreadable: {exc}")
            doc = None
    else:
        doc = None
        url = f"{BACKEND_URL}/api/players/{PLAYER_ID}"
        req = urllib.request.Request(
            url, headers={"User-Agent": "StreetLegends-diag/1.0"})
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                doc = json.loads(resp.read().decode())
            print(f"GET {url} -> 200")
        except urllib.error.HTTPError as exc:
            print(f"GET {url} -> HTTP {exc.code} (player doc unreadable)")
        except Exception as exc:  # noqa: BLE001
            print(f"GET {url} -> FAILED: {exc}")
    if doc:
        live_pos = doc.get("position") or {}
        live_active = doc.get("last_active")
        print(f"live stored position: lat={live_pos.get('latitude')}, "
              f"lng={live_pos.get('longitude')}")
        print(f"live last_active: {live_active}")
        try:
            la = datetime.fromisoformat(
                str(live_active).replace("Z", "+00:00"))
            if la.tzinfo is None:  # server stores naive UTC datetimes
                la = la.replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - la).total_seconds() / 3600
            print(f"last_active age: {age_h:.1f} hours")
            live_stale = age_h > 1.0
        except Exception:  # noqa: BLE001
            age_h = None
            live_stale = None
            print("last_active age: could not parse")
        if live_pos.get("latitude") is not None:
            d = haversine_m(live_pos["latitude"], live_pos["longitude"],
                            PHONE_GPS[0], PHONE_GPS[1])
            print(f"live stored position -> phone GPS: {d:.0f}m "
                  f"(toast said {TOAST_M}m; frozen->phone was "
                  f"{frozen_to_phone:.0f}m)")
            if live_stale is None:
                live_stale = d > 1000
            findings.append(f"[4] live stored pos -> phone GPS = {d:.0f}m, "
                            f"last_active age = "
                            f"{age_h:.1f}h" if age_h is not None else
                            "[4] live stored pos fetched, age unparseable")
    else:
        print("live player doc unavailable -- falling back to the frozen "
              "case numbers (see [0])")
        live_stale = case_stale
        findings.append(f"[4] live GET failed; case staleness used: "
                        f"frozen last_active age={_case_age_h:.1f}h, "
                        f"frozen->phone={frozen_to_phone:.0f}m -> "
                        f"stale={case_stale}")

    # optional read-only Mongo lookup for the Marco's docs
    marcos = None
    mongo_url = os.environ.get("MONGO_URL") or os.environ.get("DB_URL")
    if mongo_url:
        try:
            import pymongo  # noqa: PLC0415
            cli = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            db = cli.get_database(os.environ.get("DB_NAME", "street_legends"))
            marcos = list(db.restaurants.find(
                {"name": "Marco's Pizza"},
                {"_id": 0, "id": 1, "name": 1, "latitude": 1, "longitude": 1,
                 "osm_id": 1}).limit(10))
            print(f"\nMarco's Pizza docs in DB: {len(marcos)}")
            for r in marcos:
                d_stored = haversine_m(
                    FROZEN_POS[0], FROZEN_POS[1], r["latitude"], r["longitude"])
                d_phone = haversine_m(
                    PHONE_GPS[0], PHONE_GPS[1], r["latitude"], r["longitude"])
                print(f"  id={r.get('id')} osm={r.get('osm_id')} "
                      f"lat={r['latitude']:.5f} lng={r['longitude']:.5f} "
                      f"dist_from_frozen={d_stored:.0f}m "
                      f"dist_from_phone={d_phone:.0f}m")
                if abs(d_stored - TOAST_M) < 300:
                    print(f"  ^^ this one matches the toast ({TOAST_M}m from "
                          f"the frozen position) -- it is the Marco's the "
                          f"check measured to")
        except ImportError:
            print("\nMarco's lookup SKIPPED: pymongo not installed")
        except Exception as exc:  # noqa: BLE001
            print(f"\nMarco's lookup FAILED: {exc}")
    else:
        print("\nMarco's lookup SKIPPED: no MONGO_URL/DB_URL in this terminal "
              "(read-only DB check needs the app env)")

    # backend logs, if any are reachable from this terminal
    print("\n--- backend logs ---")
    log_hit = False
    for cand in (ROOT / "backend" / "server.log", ROOT / "server.log",
                 ROOT / "backend.log", Path("/var/log/supervisor")):
        if cand.exists():
            print(f"  found: {cand}")
            log_hit = True
    if not log_hit:
        print("  no backend log file accessible from this terminal "
              "(position-update failures, if any, are not visible here)")

    # ---- 5. verdict ----
    print("\n=== verdict ===")
    verdict = None
    why = []
    if server is None or eat_block is None:
        verdict, why = "e", ["eat endpoint or server.py not found"]
    elif formula_ok is False:
        verdict = "c"
        why.append("calculate_distance is wrong (see worked example in [1])")
    elif spawn_ok is False:
        verdict = "b"
        why.append("spawn_restaurants stores lat/lng swapped")
    elif eat_src == "stored" and id_flow_ok is False:
        verdict = "d"
        why.append("marker id / eat lookup key mismatch (see [3])")
    elif eat_src == "stored" and live_stale:
        verdict = "a"
        why.append("eat check reads the STORED player position, and the "
                   "stored position is stale (see [4])")
        if upd_endpoint_ok is False:
            verdict = "a"
            why.append("BROKEN LINK a1: update_player_position endpoint "
                       "missing or does not $set position+last_active")
        elif fe_put_ok is False:
            why.append("BROKEN LINK a2: frontend updatePlayerPosition is "
                       "missing or is not a PUT to /players/{id}/position")
        else:
            why.append("BROKEN LINK a3: every code link looks correct, so "
                       "the failure is at RUNTIME -- the PUT's errors are "
                       "swallowed (.catch), so a failing PUT is invisible, "
                       "or the location watcher never fires. Next step: "
                       "surface the PUT response / log failures, and/or "
                       "make the eat check use fresh GPS.")
    elif eat_src == "stored" and live_stale is False:
        verdict = "healthy"
        why.append("stored position is fresh and the check math is right -- "
                   "the 7478m is consistent with the stored position, so "
                   "re-check which Marco's was tapped (there may be more "
                   "than one)")
    elif eat_src == "live-gps":
        verdict = "b"
        why.append("eat check claims live GPS but the toast is still wrong "
                   "-- restaurant coordinates or marker rendering suspect "
                   "(see [3])")
    else:
        verdict = "e"
        why.append("could not classify from the printed code")
    for w in why:
        print(f"  - {w}")
    print(f"VERDICT: ({verdict})")
    for f in findings:
        print(f"  {f}")
    if MISSING:
        print(f"missing files: {', '.join(sorted(set(MISSING)))}")
        print(f"RESTAURANT_DISTANCE_DIAG_PARTIAL verdict={verdict}")
    else:
        print(f"RESTAURANT_DISTANCE_DIAG_OK verdict={verdict}")


if __name__ == "__main__":
    main()
