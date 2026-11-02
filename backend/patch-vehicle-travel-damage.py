#!/usr/bin/env python3
"""Street Legends backend: vehicle takes durability damage as the
player travels (confirmed spec 2026-11-01/02).

  - 1 durability per km traveled (fractional km carried over, so
    0.6 km + 0.6 km = 1 loss, not 0).
  - At 0 durability the vehicle needs repairs (existing repair
    endpoint POST /players/{player_id}/inventory/repair already
    handles this; no new repair system).
  - At 0 durability, enemies attack 2x: the combat code already has
    speed_adv["enemy_double"] when player speed is 1, which its own
    comment calls "(broken vehicle)". Once travel can actually break
    the vehicle, that rule fires. This patch does NOT touch combat
    (a guessed combat edit could break fights); it prints the
    enemy_double assignment lines it finds so the wiring can be
    confirmed from the patch output.

What this patch changes in backend/server.py (every step guarded;
a missed anchor SKIPs that step with a WARNING instead of breaking
the build):
  1. DURABILITY_LOSS["vehicle"]: add "per_km": 1 (rate documentation).
  2. apply_vehicle_durability_loss: add an optional distance_km
     parameter (existing callers unaffected).
  3. The per_use loss assignment becomes travel-aware: when
     action_type == "travel", loss = whole km traveled; otherwise
     exactly the old per_use value (no behavior change for use /
     territory).
  4. update_player_position: fetch the player first, compute the
     distance from the previous GPS position via calculate_distance,
     accumulate km (remainder saved on the player doc as
     vehicle_travel_remainder_km), and when a full km accumulates,
     call apply_vehicle_durability_loss(player_id, "travel",
     distance_km=whole_km). The call is wrapped so a travel-loss
     error can never break position updates (the core movement path).

Backend only (no frontend change: durability display + repair UI
already exist). Needs an Emergent Deploy to go live.

Run from repo root: python3 backend/patch-vehicle-travel-damage.py
Idempotent - safe to re-run.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

HOOK_CODE = '''    player = await db.players.find_one({"_id": player_id})
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    _vehicle_remainder_km = float(player.get("vehicle_travel_remainder_km", 0.0) or 0.0)
    _vehicle_whole_km = 0
    try:
        _prev = player.get("position") or {}
        if _prev.get("latitude") is not None and _prev.get("longitude") is not None:
            _dist_m = calculate_distance(Position(latitude=_prev["latitude"], longitude=_prev["longitude"]), position)
            _total_km = _vehicle_remainder_km + (_dist_m / 1000.0)
            _vehicle_whole_km = int(_total_km)
            _vehicle_remainder_km = _total_km - _vehicle_whole_km
    except Exception:
        pass
'''

CALL_CODE = '''    if _vehicle_whole_km >= 1:
        try:
            await apply_vehicle_durability_loss(player_id, "travel", distance_km=_vehicle_whole_km)
        except Exception:
            pass
'''


def main():
    if not SERVER.exists():
        print("ERROR: backend/server.py not found. Run from repo root.")
        return 1
    src = SERVER.read_text()
    ok_travel = False

    # 1. DURABILITY_LOSS["vehicle"] per_km.
    m = re.search(r'"vehicle":\s*\{[^}]*"per_use"[^}]*"per_territory"[^}]*\}', src)
    if not m:
        print("WARNING: DURABILITY_LOSS vehicle dict not found")
    elif '"per_km"' in m.group(0):
        print("SKIP: DURABILITY_LOSS vehicle per_km already present")
    else:
        seg = m.group(0)
        seg2 = seg[:-1].rstrip() + ', "per_km": 1}'
        src = src[:m.start()] + seg2 + src[m.end():]
        print("OK: DURABILITY_LOSS vehicle per_km = 1 added")

    # 2. apply_vehicle_durability_loss signature: add distance_km param.
    # Match the def up to its closing paren (so the already-extended
    # form is recognized on re-run), then insert before that paren.
    sig_ok = False
    m = re.search(r"async def apply_vehicle_durability_loss\([^)]*\)", src)
    if not m:
        print("WARNING: apply_vehicle_durability_loss def line not found")
    elif "distance_km" in m.group(0):
        print("SKIP: apply_vehicle_durability_loss already takes distance_km")
        sig_ok = True
    else:
        old = m.group(0)  # ends with ")"
        new = old[:-1] + ', distance_km: float = 0)'
        src = src[:m.start()] + new + src[m.end():]
        print("OK: apply_vehicle_durability_loss takes distance_km")
        sig_ok = True

    # 3. per_use assignment becomes travel-aware (single-line ternary).
    # Recognize the already-converted ternary line on re-run (it no
    # longer contains the exact old assignment text).
    old_loss = 'loss = DURABILITY_LOSS["vehicle"]["per_use"]'
    ternary_lines = [ln for ln in src.split("\n")
                     if 'action_type == "travel"' in ln and 'DURABILITY_LOSS["vehicle"]["per_use"]' in ln]
    loss_lines = [ln for ln in src.split("\n") if old_loss in ln]
    if ternary_lines:
        print("SKIP: per_use loss already travel-aware")
        ok_travel = True
    elif not loss_lines:
        print("WARNING: per_use loss assignment not found")
    else:
        indent = loss_lines[0][:len(loss_lines[0]) - len(loss_lines[0].lstrip())]
        new_line = indent + 'loss = int(distance_km) if action_type == "travel" else DURABILITY_LOSS["vehicle"]["per_use"]'
        src = src.replace(loss_lines[0], new_line, 1)
        print("OK: per_use loss is now travel-aware (travel = whole km)")
        ok_travel = True
    ok_travel = ok_travel and sig_ok

    # 4. update_player_position hook (only if the travel branch is wired).
    if not ok_travel:
        print("WARNING: travel branch not wired; position hook skipped")
    else:
        lines = src.split("\n")
        # Find the update_player_position def.
        didx = None
        for i, ln in enumerate(lines):
            if "def update_player_position" in ln:
                didx = i
                break
        if didx is None:
            print("WARNING: update_player_position def not found")
        elif "vehicle_travel_remainder_km" in src:
            print("SKIP: update_player_position travel hook already present")
        else:
            # (a) Insert player fetch + distance + remainder right after
            # the docstring (the line after the def line, if it is a
            # docstring; otherwise right after the def line).
            ins = didx + 1
            if ins < len(lines) and lines[ins].strip().startswith('"""'):
                ins += 1
            hook_lines = HOOK_CODE.rstrip("\n").split("\n")
            lines[ins:ins] = hook_lines
            src = "\n".join(lines)
            print("OK: update_player_position fetches player + computes travel km")
            # (b) Add remainder to the $set (position save).
            lines = src.split("\n")
            set_idx = None
            for i in range(didx, min(len(lines), didx + 40)):
                if '"position": position.dict()' in lines[i] and '"last_active"' in lines[i]:
                    set_idx = i
                    break
            if set_idx is None:
                print("WARNING: position $set line not found; remainder not saved")
            else:
                ln = lines[set_idx]
                # Insert the remainder field before the closing "}}" of $set.
                ln2 = ln.replace('"last_active": datetime.utcnow()',
                                 '"last_active": datetime.utcnow(), "vehicle_travel_remainder_km": _vehicle_remainder_km', 1)
                if ln2 != ln:
                    lines[set_idx] = ln2
                    src = "\n".join(lines)
                    print("OK: position save stores vehicle_travel_remainder_km")
                else:
                    print("WARNING: position $set edit did not apply")
            # (c) Call travel loss after the update_one, before the
            # modified_count check (so it runs even when the position
            # save itself reports no change).
            lines = src.split("\n")
            call_idx = None
            for i in range(didx, min(len(lines), didx + 60)):
                if "if result.modified_count" in lines[i]:
                    call_idx = i
                    break
            if call_idx is None:
                print("WARNING: modified_count check not found; travel-loss call skipped")
            else:
                call_lines = CALL_CODE.rstrip("\n").split("\n")
                lines[call_idx:call_idx] = call_lines
                src = "\n".join(lines)
                print("OK: update_player_position calls travel durability loss")

    # Diagnostic: print the enemy_double assignment lines (no change).
    # An assignment is enemy_double"] followed by a single "=" (not
    # "=="); reads and comparisons are skipped.
    print("--- enemy_double assignments (for wiring confirmation) ---")
    shown = 0
    for i, ln in enumerate(src.split("\n")):
        if re.search(r"""["']enemy_double["']\s*\]\s*=(?!=)""", ln):
            print("server.py:%d: %s" % (i + 1, ln.strip()[:140]))
            shown += 1
            if shown >= 3:
                break
    if shown == 0:
        print("(no enemy_double assignment found)")

    SERVER.write_text(src)
    if ok_travel:
        print("VEHICLE_TRAVEL_DAMAGE_OK")
    else:
        print("VEHICLE_TRAVEL_DAMAGE_WARNING: travel branch not fully wired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
