#!/usr/bin/env python3
"""Street Legends frontend: finish house presence (frontend / Expo Go only).

Live evidence (presence compact diag, 2026-11-03): houseOccupants state,
isGuestVisit flag, guest gate, and all four presence client functions in
services/api.ts already exist, and the backend presence endpoints are
deployed — but index.tsx has NO presence lifecycle effect (enter never
runs, occupants stay empty) and NO "In this house now" row (filled
occupants would never display). This patch adds exactly those two missing
pieces, plus the services/api import if it is missing.

Does NOT touch: the friend popup Enter button, the guest gate,
SELL/HIDE/MOVE, TV/radio, wagering, or any backend code.
Idempotent: second run prints HOUSE_VISIT_PRESENCE_FIX_ALREADY_APPLIED.
Each step (import, effect, row) is independent: one step's WARNING never
aborts the other steps, except a brace/paren balance change, which aborts
the whole write.

Usage: python3 frontend/patch-house-visit-presence-fix-frontend.py
       (runs against /app; pass a mock root as argv[1] for testing)
"""
import re
import sys
from pathlib import Path

MARKER = "HOUSE_VISIT_PRESENCE_FIX_OK"
ALREADY = "HOUSE_VISIT_PRESENCE_FIX_ALREADY_APPLIED"
EFFECT_MARKER = "// HOUSE_VISIT_PRESENCE_FIX: presence lifecycle"
ROW_TEXT = "In this house now"
NAMES = ["houseEnterPresence", "houseLeavePresence",
         "houseHeartbeatPresence", "getHousePresence"]


def indent_of(line):
    m = re.match(r"\s*", line)
    return m.group(0) if m else ""


def balanced(text):
    return (text.count("{") == text.count("}")
            and text.count("(") == text.count(")")
            and text.count("[") == text.count("]"))


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
    idx = root / "frontend/app/(tabs)/index.tsx"
    if not idx.exists():
        print(f"WARNING: index.tsx not found at {idx} - nothing changed")
        return 0
    src = idx.read_text(errors="ignore")
    orig = src
    lines = src.split("\n")

    # --- Already applied? (row text + effect marker + full import) ---
    import_match = re.search(
        r"import\s*\{([^}]*)\}\s*from\s*['\"][^'\"]*services/api[^'\"]*['\"]",
        src, re.DOTALL)
    imported = set()
    if import_match:
        imported = {n.strip() for n in import_match.group(1).split(",")
                    if n.strip()}
    if (EFFECT_MARKER in src and ROW_TEXT in src
            and all(n in imported for n in NAMES)):
        print(ALREADY)
        return 0

    # --- Step 1: import ---
    import_ok = False
    if import_match and all(n in imported for n in NAMES):
        print("SKIP: presence names already imported")
        import_ok = True
    elif import_match:
        missing = [n for n in NAMES if n not in imported]
        existing = import_match.group(1).strip()
        new_block = existing + (", " if existing and not existing.endswith(",")
                                else "") + ", ".join(missing)
        src = (src[:import_match.start(1)] + new_block
               + src[import_match.end(1):])
        lines = src.split("\n")
        print("OK: presence import extended with " + ", ".join(missing))
        import_ok = True
    else:
        # No named services/api import. Derive the path from another
        # services import if one is visible.
        api_path = None
        for ln in lines:
            m = re.search(r"from\s*['\"]([^'\"]*services/)[^'\"]*['\"]", ln)
            if m:
                api_path = m.group(1) + "api"
                break
        if api_path is None and "../services/api" in src:
            api_path = "../services/api"
        if api_path is None:
            print("WARNING: services/api import path not determined - "
                  "presence import SKIPPED (effect/row skipped)")
        else:
            last_import = None
            for i, ln in enumerate(lines):
                if ln.strip().startswith("import "):
                    last_import = i
            new_line = ("import { " + ", ".join(NAMES) + " } from '"
                        + api_path + "';")
            if last_import is None:
                lines = [new_line] + lines
            else:
                lines = lines[:last_import + 1] + [new_line] \
                    + lines[last_import + 1:]
            src = "\n".join(lines)
            print("OK: presence import added (" + api_path + ")")
            import_ok = True

    # --- Step 2: effect ---
    effect_done = False
    effect_present = any("houseEnterPresence(" in ln
                         and "import" not in ln.strip()[:6]
                         for ln in src.split("\n"))
    if effect_present:
        print("SKIP: presence effect already present")
        effect_done = True
    elif not import_ok:
        print("WARNING: presence effect SKIPPED (import unavailable)")
    elif "setHouseOccupants" not in src:
        print("WARNING: houseOccupants state not found - presence effect "
              "SKIPPED")
    else:
        lines = src.split("\n")
        eff_idx = None
        for i, ln in enumerate(lines):
            if "const isGuestVisit =" in ln:
                eff_idx = i
                break
        if eff_idx is None:
            print("WARNING: isGuestVisit anchor not found - presence effect "
                  "SKIPPED")
        else:
            nm = re.search(r"const\s*\[\s*(player\w*)\s*,\s*setPlayer", src)
            if nm:
                name_expr = "(%s as any)?.name || 'Player'" % nm.group(1)
            else:
                name_expr = "'Player'"
                print("NOTE: player state variable not found - presence "
                      "names fall back to 'Player'")
            ind = indent_of(lines[eff_idx])
            effect = [
                ind + EFFECT_MARKER + " - enter/poll/heartbeat/leave",
                ind + "useEffect(() => {",
                ind + "  if (!interiorHouse || !playerId) return;",
                ind + "  let stopped = false;",
                ind + "  const visitName = " + name_expr + ";",
                ind + "  const loadOccupants = async () => {",
                ind + "    try {",
                ind + "      const res: any = await getHousePresence(interiorHouse.id);",
                ind + "      if (!stopped && res?.occupants) setHouseOccupants(res.occupants);",
                ind + "    } catch (_) {}",
                ind + "  };",
                ind + "  (async () => {",
                ind + "    try {",
                ind + "      const res: any = await houseEnterPresence(interiorHouse.id, playerId, visitName);",
                ind + "      if (!stopped && res?.occupants) setHouseOccupants(res.occupants);",
                ind + "    } catch (_) {}",
                ind + "  })();",
                ind + "  const hb = setInterval(async () => {",
                ind + "    try { await houseHeartbeatPresence(interiorHouse.id, playerId, visitName); } catch (_) {}",
                ind + "  }, 30000);",
                ind + "  const poll = setInterval(loadOccupants, 15000);",
                ind + "  return () => {",
                ind + "    stopped = true;",
                ind + "    clearInterval(hb);",
                ind + "    clearInterval(poll);",
                ind + "    houseLeavePresence(interiorHouse.id, playerId).catch(() => {});",
                ind + "  };",
                ind + "}, [interiorHouse?.id, playerId]);",
            ]
            lines = lines[:eff_idx + 1] + effect + lines[eff_idx + 1:]
            src = "\n".join(lines)
            print("OK: presence lifecycle effect added after isGuestVisit")
            effect_done = True

    # --- Step 3: row ---
    row_done = False
    if ROW_TEXT in src:
        print("SKIP: presence row already present")
        row_done = True
    elif not import_ok:
        print("WARNING: presence row SKIPPED (import unavailable)")
    elif "setHouseOccupants" not in src:
        print("WARNING: presence row SKIPPED (state unavailable)")
    else:
        lines = src.split("\n")
        leave_idx = None
        for i, ln in enumerate(lines):
            if "LEAVE HOUSE" in ln and "<Text" in ln:
                leave_idx = i
                break
        if leave_idx is None:
            for i, ln in enumerate(lines):
                if ("LEAVE HOUSE" in ln
                        and not ln.strip().startswith("//")
                        and not ln.strip().startswith("*")
                        and "HOUSE_VISIT" not in ln):
                    leave_idx = i
                    break
        hdr_idx = None
        anchor_kind = None
        if leave_idx is not None:
            for j in range(leave_idx, max(-1, leave_idx - 500), -1):
                if "item_limit" in lines[j] and "items" in lines[j]:
                    hdr_idx = j
                    anchor_kind = "item_limit"
                    break
        row = [
            "{houseOccupants.length > 0 ? (",
            "  <Text style={{ color: '#fff', fontSize: 12 }}>In this house now: "
            "{houseOccupants.map((o: any) => (o.player_id === playerId "
            "? ((o.player_name || 'Player') + ' (you)') "
            ": (o.player_name || 'Player'))).join(', ')}</Text>",
            ") : null}",
        ]
        if hdr_idx is not None:
            ind = indent_of(lines[hdr_idx])
            row = [ind + r for r in row]
            lines = lines[:hdr_idx + 1] + row + lines[hdr_idx + 1:]
            src = "\n".join(lines)
            print("OK: presence row added after item_limit line (anchor: "
                  + anchor_kind + ")")
            row_done = True
        elif leave_idx is not None:
            ind = indent_of(lines[leave_idx])
            row = [ind + r for r in row]
            lines = lines[:leave_idx] + row + lines[leave_idx:]
            src = "\n".join(lines)
            print("OK: presence row added before LEAVE HOUSE line (anchor: "
                  "leave-house-fallback)")
            row_done = True
        else:
            print("WARNING: interior header anchor not found - presence row "
                  "NOT added")

    if src == orig:
        print("NOTE: no changes made (all steps skipped or already present)")
        return 0
    if not balanced(src):
        print("WARNING: brace balance changed - index.tsx NOT written")
        return 1
    idx.write_text(src)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
