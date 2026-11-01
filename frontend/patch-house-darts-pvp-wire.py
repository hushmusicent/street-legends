"""Street Legends frontend: wire the DARTBOARD menu's PLAYER VS PLAYER button
to the game invite room (scoped fix, not a re-run of the full PvP patch).

Run from repo root: python3 frontend/patch-house-darts-pvp-wire.py
Idempotent - safe to re-run.

ROOT CAUSE (found from the user's diagnostic screenshot 2026-10-31): the
earlier darts-pvp and darts-pvp-fix patches both skipped the menu wiring
with a GLOBAL check ("onPlayPvp={() =>" anywhere in the file). That check
is true because the POOL menu already has an onPlayPvp prop - so the
patches concluded the dartboard menu was wired when it never was. The
button therefore fell back to closing the menu ("takes me back").

This patch checks ONLY the DartboardMenuModal render line itself. For
every line that renders DartboardMenuModal and lacks onPlayPvp, it inserts
 onPlayPvp={() => { setDartMenuOpen(false); setDartPvpOpen(true); }}
before onSell (or before />). It never touches the pool menu, the
components, the state, or the modals - those are already in place.
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
PROP = " onPlayPvp={() => { setDartMenuOpen(false); setDartPvpOpen(true); }}"


def main():
    if not INDEX.exists():
        print("ERROR: %s not found. Run from repo root." % INDEX)
        sys.exit(1)
    lines = INDEX.read_text().split("\n")
    wired = 0
    skipped = 0
    for i, ln in enumerate(lines):
        if "DartboardMenuModal visible" not in ln:
            continue
        if "onPlayPvp=" in ln:
            print("SKIP: dartboard menu render line %d already wired" % (i + 1))
            skipped += 1
            continue
        if " onSell=" in ln:
            lines[i] = ln.replace(" onSell=", PROP + " onSell=", 1)
        elif " />" in ln:
            lines[i] = ln.replace(" />", PROP + " />", 1)
        else:
            print("WARNING: dartboard menu render line %d has no onSell or /> anchor" % (i + 1))
            continue
        print("OK: dartboard menu render line %d wired to the invite room" % (i + 1))
        wired += 1
    if wired == 0 and skipped == 0:
        print("WARNING: no DartboardMenuModal render line found")
    else:
        INDEX.write_text("\n".join(lines))
    if wired > 0 or skipped > 0:
        print("HOUSE_DART_PVP_WIRE_OK")


if __name__ == "__main__":
    main()
