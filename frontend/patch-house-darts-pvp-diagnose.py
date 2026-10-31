"""Street Legends frontend DIAGNOSTIC (read-only): why does the dartboard
PLAYER VS PLAYER button take the user back instead of opening the invite room?

Run from repo root: python3 frontend/patch-house-darts-pvp-diagnose.py
This patch changes NOTHING. It only prints scoped evidence from
frontend/app/(tabs)/index.tsx, because the earlier patches' global
"already present" checks can be true while the ACTIVE render is unwired
(e.g. a duplicate menu render, or the rooms modal rendered outside the
state's component). Send the printed lines (screenshot) to Muse.

Prints:
  1. How many DartboardMenuModal definitions exist.
  2. Every DartboardMenuModal render line, and whether THAT line has onPlayPvp.
  3. How many dartPvpOpen state declarations exist.
  4. How many DartPvpModal / DartPvpGameModal definitions exist.
  5. Every DartPvpModal render line.
  6. The menu button's onPress line (does it call onPlayPvp?).
  7. Whether onPlayPvp is in the menu component's props.
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")


def main():
    if not INDEX.exists():
        print("ERROR: %s not found. Run from repo root." % INDEX)
        sys.exit(1)
    src = INDEX.read_text()
    lines = src.split("\n")

    defs = [i for i, ln in enumerate(lines) if "const DartboardMenuModal" in ln]
    print("MENU_DEFS: %d" % len(defs))
    for i in defs:
        print("  def line %d: %s" % (i + 1, lines[i].strip()[:220]))

    renders = [i for i, ln in enumerate(lines) if "DartboardMenuModal visible" in ln]
    print("MENU_RENDERS: %d" % len(renders))
    for k, i in enumerate(renders):
        ln = lines[i]
        print("  RENDER[%d] line %d has_onPlayPvp=%s" % (k, i + 1, "onPlayPvp=" in ln))
        print("    %s" % ln.strip()[:300])

    states = [i for i, ln in enumerate(lines) if "const [dartPvpOpen" in ln]
    print("PVP_STATE_DECLS: %d" % len(states))
    for i in states:
        print("  state line %d: %s" % (i + 1, lines[i].strip()[:160]))

    for name in ("const DartPvpModal", "const DartPvpGameModal"):
        found = [i for i, ln in enumerate(lines) if name in ln]
        print("%s: %d" % (name, len(found)))

    pvp_renders = [i for i, ln in enumerate(lines) if "DartPvpModal visible" in ln]
    print("PVP_MODAL_RENDERS: %d" % len(pvp_renders))
    for k, i in enumerate(pvp_renders):
        print("  PVP_RENDER[%d] line %d: %s" % (k, i + 1, lines[i].strip()[:300]))

    for i, ln in enumerate(lines):
        if "PLAYER VS PLAYER" in ln:
            print("BUTTON_TEXT line %d: %s" % (i + 1, ln.strip()[:160]))
            for j in range(max(0, i - 3), i + 1):
                if "onPress" in lines[j]:
                    print("  BUTTON_ONPRESS line %d: %s" % (j + 1, lines[j].strip()[:260]))
            break

    if defs:
        print("MENU_PROPS_HAS_ONPLAYPVP: %s" % ("onPlayPvp" in lines[defs[0]]))
    print("DART_PVP_DIAGNOSE_DONE")


if __name__ == "__main__":
    main()
