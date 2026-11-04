#!/usr/bin/env python3
"""Street Legends frontend: define API_BASE for the pool PvP modal.

Root cause (live evidence): the pool PvP modal calls fetch(API_BASE + ...)
but no const/let/var/import for API_BASE is ever inserted into
frontend/app/(tabs)/index.tsx by the pool PvP patches — the patch scripts
only define API_BASE as a *Python* constant. An undefined API_BASE throws
a ReferenceError inside the modal's try/catch on every Create/Join tap,
which the wiring patch now surfaces as 'Could not reach the server.'
Backend routes were proven FOUND, so this — not the backend — is the
remaining break. If a definition already exists, this patch changes
nothing. Frontend / Expo Go only."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "// POOL_API_BASE_DEFINED"
HOST = "https://gta-quest-map.emergent.host"

def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - nothing changed")
        return 1
    src = IDX.read_text(errors="ignore")
    if MARKER in src:
        print("POOL_API_BASE_ALREADY_APPLIED")
        return 0
    # Any existing definition (const/let/var, or an import of the name)?
    if re.search(r"(const|let|var)\s+API_BASE\s*=", src) or \
       re.search(r"import\s*\{[^}]*\bAPI_BASE\b[^}]*\}", src):
        print("POOL_API_BASE_ALREADY_APPLIED")
        return 0
    lines = src.split("\n")
    last_import = None
    for i, ln in enumerate(lines):
        if ln.strip().startswith("import ") and " from " in ln:
            last_import = i
    if last_import is None:
        print("WARNING: no import anchor found - API_BASE NOT defined")
        return 1
    insert = [MARKER, f'const API_BASE = "{HOST}";']
    lines = lines[:last_import + 1] + insert + lines[last_import + 1:]
    new_src = "\n".join(lines)
    if new_src.count("{") != src.count("{") or new_src.count("}") != src.count("}"):
        # Inserted lines contain no braces, so any change here is a bug.
        print("WARNING: brace balance changed - index.tsx NOT written")
        return 1
    IDX.write_text(new_src)
    print("POOL_API_BASE_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
