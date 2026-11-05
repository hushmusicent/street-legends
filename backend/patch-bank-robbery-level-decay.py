"""Street Legends backend: bank robbery chance loses 10% of itself per level-up.
Run from repo root: python3 backend/patch-bank-robbery-level-decay.py
Idempotent - safe to re-run.

USER DECISION (2026-11-05): robbery chance loses 10% OF THE CHANCE with
every level up (multiplicative x0.9 per level-up). His current chance is
UNCHANGED by this patch: 66% at Lv.14, Luck 8, full HP. After one level-up
it becomes 59.4%, after two ~53.5%, and so on toward the 20% floor.

MECHANISM (stored per-player multiplier, NOT a 0.9^(level-1) formula --
that formula would crush every existing player to the floor on day one):
  - New player field "robbery_mult", default 1.0 (read with .get default,
    so existing players and fresh players are undecayed until they level up).
  - rob_bank applies it AFTER the luck/health computation and cap:
        success_chance = max(0.20, min(0.70, success_chance * robbery_mult))
    so the 20% floor and 70% cap still hold, and Luck <= 0 stays at 20%.
  - Every level-up multiplies the stored value by 0.9. There is NO central
    XP helper in this codebase -- the only two places a level increments are
    battle_action (monster victory) and complete_mission. Both are hooked.
    (Guild raids $inc XP with no level check -- a pre-existing gap: raid XP
    alone never levels a player up, so the decay fires when the level
    actually increments at the next battle/mission level-up.)

TOUCHES NOTHING ELSE: fine ($450-$1000 flat), 100m rule, cooldown,
health falloff, and battle luck (miss/crit/loot) are all untouched.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# ---- Part A: apply the multiplier in rob_bank ---------------------------
ROB_ANCHOR = "    success = random.random() < success_chance"
ROB_MARKER = "# Level-decay: robbery chance loses 10% of itself per level-up."
ROB_INSERT = """    # Level-decay: robbery chance loses 10% of itself per level-up.
    # Per-player multiplier (1.0 = undecayed; x0.9 at each level-up).
    # Applied AFTER the luck/health computation and cap; floored at 20%.
    success_chance = max(0.20, min(0.70, success_chance * player.get("robbery_mult", 1.0)))
"""

# ---- Part B: decay the stored multiplier at every level-up --------------
# Both level-up sites share this line (indentation differs: 16 spaces in
# battle_action, 8 in complete_mission), so match it with its indent.
LVL_RE = re.compile(
    r'^([ ]*)update_data\["xp_to_next"\] = calculate_xp_to_level\(new_level\)$',
    re.MULTILINE,
)
LVL_MARKER = '# Robbery level-decay: x0.9 per level-up'


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    changed = []

    # --- Part A ---
    if ROB_MARKER in src:
        print("ALREADY_APPLIED: rob_bank multiplier")
    elif ROB_ANCHOR not in src:
        print("WARNING: rob_bank anchor not found - multiplier NOT applied "
              "(looked for '    success = random.random() < success_chance')")
    elif "success_chance = " not in src:
        print("WARNING: no success_chance computation found - multiplier NOT "
              "applied (rob_bank chance lines missing)")
    else:
        src = src.replace(ROB_ANCHOR, ROB_INSERT + ROB_ANCHOR, 1)
        changed.append("rob_bank")
        print("OK: rob_bank multiplier applied")

    # --- Part B ---
    if LVL_MARKER in src:
        print("ALREADY_APPLIED: level-up decay")
    else:
        hits = LVL_RE.findall(src)

        def _decay(m):
            ind = m.group(1)
            return (
                m.group(0)
                + "\n" + ind + "# Robbery level-decay: x0.9 per level-up"
                + "\n" + ind + 'update_data["robbery_mult"] = round(player.get("robbery_mult", 1.0) * 0.9, 6)'
            )

        if not hits:
            print("WARNING: level-up anchor not found - decay NOT hooked "
                  "(looked for 'update_data[\"xp_to_next\"] = "
                  "calculate_xp_to_level(new_level)')")
        else:
            src = LVL_RE.sub(_decay, src)
            changed.append(f"level-up decay x{len(hits)} site(s)")
            print(f"OK: level-up decay hooked at {len(hits)} site(s)")

    if changed:
        SERVER.write_text(src)
        import py_compile
        py_compile.compile(str(SERVER), doraise=True)
        print("Python syntax OK.")
    else:
        print("No changes (already applied or anchors missing).")
    print("BANK_ROBBERY_LEVEL_DECAY_OK")


if __name__ == "__main__":
    main()
