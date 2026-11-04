#!/usr/bin/env python3
"""Read-only presence diagnostic v2: why the house still shows nobody
inside. Prints only, changes nothing. Run from /app (or pass the root).

The row only renders when occupants are non-empty, so 'no row' means
'enter never registered' (or the row sits outside the interior view).
This prints the exact evidence for that: what id the enter/poll calls
use, the effect's deps, the row's surrounding lines, the api.ts
presence URLs, and what object setInteriorHouse actually receives."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
API = ROOT / "frontend/services/api.ts"

def show(title, lines):
    print("=== %s ===" % title)
    for ln in lines:
        print(ln)
    if not lines:
        print("(none found)")

def main():
    print("PRESENCE_V2_OK")
    if not IDX.exists():
        print("index.tsx NOT FOUND"); return 1
    lines = IDX.read_text(errors="ignore").split("\n")
    show("1. presence call args (enter/poll/heartbeat/leave)", [
        "%d: %s" % (i + 1, ln.strip()[:170]) for i, ln in enumerate(lines)
        if re.search(r"house(Enter|Leave|Heartbeat)Presence\(|getHousePresence\(", ln)
    ])
    show("2. presence effect deps", [
        "%d: %s" % (i + 1, ln.strip()[:170]) for i, ln in enumerate(lines)
        if "interiorHouse" in ln and "}, [" in ln
    ])
    row_at = next((i for i, ln in enumerate(lines) if "In this house now" in ln), None)
    if row_at is not None:
        show("3. presence row context (5 lines around it)", [
            "%d: %s" % (i + 1, lines[i][:170]) for i in range(max(0, row_at - 5), min(len(lines), row_at + 4))
        ])
    else:
        print("=== 3. presence row context ===\n(no 'In this house now' row found)")
    show("4. setInteriorHouse calls (what house object is passed)", [
        "%d: %s" % (i + 1, ln.strip()[:170]) for i, ln in enumerate(lines)
        if "setInteriorHouse(" in ln
    ][:6])
    show("5. houseOccupants state lines", [
        "%d: %s" % (i + 1, ln.strip()[:170]) for i, ln in enumerate(lines)
        if "houseOccupants" in ln
    ][:12])
    if API.exists():
        alines = API.read_text(errors="ignore").split("\n")
        show("6. api.ts presence URLs", [
            "%d: %s" % (i + 1, ln.strip()[:170]) for i, ln in enumerate(alines)
            if "/houses/" in ln and ("enter" in ln or "leave" in ln or "heartbeat" in ln or "presence" in ln)
        ])
    else:
        print("=== 6. api.ts presence URLs ===\nservices/api.ts NOT FOUND")
    return 0

if __name__ == "__main__":
    sys.exit(main())
