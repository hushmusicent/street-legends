#!/usr/bin/env python3
"""Street Legends frontend: pool room REJOIN button.

When the room screen opens with no room selected, it asks the backend
for this player's live room (waiting or playing). If one exists, a
REJOIN ROOM <code> button appears above CREATE ROOM: tapping it restores
the room, and if the game is already playing it opens the game, which
resumes from the server's saved state (balls, groups, turn). This covers
a player booted out by an app close, crash, or network drop — no leave
call is made then, so the room is still live. Frontend / Expo Go only."""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "// POOL_REJOIN_FRONTEND"

def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))

def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - nothing changed")
        return 1
    src = IDX.read_text(errors="ignore")
    if MARKER in src:
        print("POOL_REJOIN_FRONTEND_ALREADY_APPLIED")
        return 0
    orig = delta(src)
    busy = "const [busy, setBusy] = useState(false);"
    if busy not in src:
        print("WARNING: room-modal busy anchor not matched - rejoin NOT added")
        return 1
    state_block = (
        "\n  " + MARKER + ": offer the player's live room back after a boot-out.\n"
        "  const [activeRoom, setActiveRoom] = useState<any | null>(null);\n"
        "  useEffect(() => {\n"
        "    if (!visible || room) return;\n"
        "    let cancelled = false;\n"
        "    (async () => {\n"
        "      try {\n"
        "        const res = await fetch(API_BASE + '/api/pool/rooms/active/' + playerId);\n"
        "        if (!cancelled && res.ok) { const d = await res.json(); setActiveRoom(d); }\n"
        "        else if (!cancelled) { setActiveRoom(null); }\n"
        "      } catch (e) { if (!cancelled) setActiveRoom(null); }\n"
        "    })();\n"
        "    return () => { cancelled = true; };\n"
        "  }, [visible, room?.code]);"
    )
    src = src.replace(busy, busy + state_block, 1)
    # Button: insert before the CREATE ROOM button's TouchableOpacity.
    ci = src.find("onPress={createRoom}")
    if ci == -1:
        print("WARNING: CREATE ROOM button not found - button NOT added")
        return 1
    t_start = src.rfind("<TouchableOpacity", 0, ci)
    if t_start == -1:
        print("WARNING: CREATE ROOM button start not found - button NOT added")
        return 1
    line_start = src.rfind("\n", 0, t_start) + 1
    btn = (
        "            {activeRoom ? (\n"
        "              <TouchableOpacity onPress={() => { setRoom(activeRoom); if (activeRoom.status === 'playing') { onPlay(); } }} style={{ backgroundColor: '#f39c12', paddingVertical: 12, borderRadius: 8, marginBottom: 12 }}>\n"
        "                <Text style={{ color: '#111111', fontWeight: '800', textAlign: 'center' }}>REJOIN ROOM {activeRoom.code}</Text>\n"
        "              </TouchableOpacity>\n"
        "            ) : null}\n"
    )
    src = src[:line_start] + btn + src[line_start:]
    if delta(src) != orig:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    IDX.write_text(src)
    print("POOL_REJOIN_FRONTEND_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
