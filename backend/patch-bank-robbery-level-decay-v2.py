"""Street Legends backend: bank robbery chance loses 2% of itself per level-up.
Run from repo root: python3 backend/patch-bank-robbery-level-decay-v2.py
Idempotent - safe to re-run.

USER DECISION (2026-11-05): first 10% per level-up, then changed to 2%.
Robbery chance loses 2% OF THE CHANCE with every level up (multiplicative
x0.98 per level-up). His current chance is UNCHANGED by this patch: 66% at
Lv.14, Luck 8, full HP. After one level-up it becomes ~64.7%, after two
~63.4%, and so on toward the 20% floor (reached around Lv.73).

MECHANISM (stored per-player multiplier, NOT a 0.98^(level-1) formula --
that formula would crush every existing player on day one):
  - New player field "robbery_mult", default 1.0 (read with .get default,
    so existing players and fresh players are undecayed until they level up).
  - rob_bank applies it AFTER the luck/health computation and cap:
        success_chance = max(0.20, min(0.70, success_chance * robbery_mult))
    so the 20% floor and 70% cap still hold, and Luck <= 0 stays at 20%.
  - Every level-up multiplies the stored value by 0.98. There is NO central
    XP helper in this codebase -- the only two places a level increments are
    battle_action (monster victory) and complete_mission. Both are hooked.
    (Guild raids $inc XP with no level check -- a pre-existing gap: raid XP
    alone never levels a player up, so the decay fires when the level
    actually increments at the next battle/mission level-up.)

UPGRADE PATH: if the v1 patch (x0.9) already ran, this patch replaces its
0.9 decay lines with 0.98 and fixes its comments -- it does NOT add a
second multiplier. If v1 never ran, this patch installs the whole thing
with 0.98. Either way the end state is identical.

TOUCHES NOTHING ELSE: fine ($450-$1000 flat), 100m rule, cooldown,
health falloff, and battle luck (miss/crit/loot) are all untouched.
"""
import re
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

# ---- Part A: apply the multiplier in rob_bank ---------------------------
ROB_ANCHOR = "    success = random.random() < success_chance"
ROB_INSERT = """    # Level-decay: robbery chance loses 2% of itself per level-up.
    # Per-player multiplier (1.0 = undecayed; x0.98 at each level-up).
    # Applied AFTER the luck/health computation and cap; floored at 20%.
    success_chance = max(0.20, min(0.70, success_chance * player.get("robbery_mult", 1.0)))
"""
# v1's Part A comment (same operative line, old 10% wording).
ROB_V1_MARKER = "# Level-decay: robbery chance loses 10% of itself per level-up."

# ---- Part B: decay the stored multiplier at every level-up --------------
# Both level-up sites share this line (indentation differs: 16 spaces in
# battle_action, 8 in complete_mission), so match it with its indent.
LVL_RE = re.compile(
    r'^([ ]*)update_data\["xp_to_next"\] = calculate_xp_to_level\(new_level\)$',
    re.MULTILINE,
)
# v1 decay lines (0.9) and v2 decay lines (0.98).
LVL_V1_COMMENT = "# Robbery level-decay: x0.9 per level-up"
LVL_V2_COMMENT = "# Robbery level-decay: x0.98 per level-up"
LVL_V1_LINE = 'round(player.get("robbery_mult", 1.0) * 0.9, 6)'
LVL_V2_LINE = 'round(player.get("robbery_mult", 1.0) * 0.98, 6)'


def main():
    if not SERVER.exists():
        print(f"ERROR: {SERVER} not found. Run from repo root.")
        sys.exit(1)
    src = SERVER.read_text()
    changed = []

    # --- Part A ---
    if ROB_INSERT.strip().splitlines()[0] in src:
        print("ALREADY_APPLIED: rob_bank multiplier (v2)")
    elif ROB_V1_MARKER in src:
        # v1's Part A is in place; only its wording is stale. Fix comments.
        src = src.replace(
            "# Level-decay: robbery chance loses 10% of itself per level-up.",
            "# Level-decay: robbery chance loses 2% of itself per level-up.",
        ).replace(
            "# Per-player multiplier (1.0 = undecayed; x0.9 at each level-up).",
            "# Per-player multiplier (1.0 = undecayed; x0.98 at each level-up).",
        )
        changed.append("rob_bank comment 10% -> 2%")
        print("OK: rob_bank multiplier wording updated to 2% (v1 -> v2)")
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
    if LVL_V2_LINE in src:
        print("ALREADY_APPLIED: level-up decay x0.98")
    elif LVL_V1_LINE in src:
        # v1 decay already hooked at both sites; swap 0.9 -> 0.98 in place.
        n_lines = src.count(LVL_V1_LINE)
        src = src.replace(LVL_V1_LINE, LVL_V2_LINE)
        src = src.replace(LVL_V1_COMMENT, LVL_V2_COMMENT)
        changed.append(f"level-up decay 0.9 -> 0.98 x{n_lines} site(s)")
        print(f"OK: level-up decay updated 0.9 -> 0.98 at {n_lines} site(s)")
    else:
        hits = LVL_RE.findall(src)

        def _decay(m):
            ind = m.group(1)
            return (
                m.group(0)
                + "\n" + ind + LVL_V2_COMMENT
                + "\n" + ind + 'update_data["robbery_mult"] = ' + LVL_V2_LINE
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
    print("BANK_ROBBERY_LEVEL_DECAY_V2_OK")


if __name__ == "__main__":
    main()
