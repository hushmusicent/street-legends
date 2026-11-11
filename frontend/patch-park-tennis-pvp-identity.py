#!/usr/bin/env python3
"""Street Legends frontend: inject the player identity into the Park
Tennis WebView so the game's PvP mode knows who is playing.

The Tennis game reads window.PARK_PVP_PLAYER = {id, name} (set before
the game loads) for its PvP room calls (create/join/state). Without it
both phones would fall back to id 'local-player' and the backend could
not tell host from guest.

Changes (idempotent, scoped to the TennisGameModal only):
  1. TennisGameModal accepts playerId + playerName props.
  2. PoolWebView gets injectedJavaScript that sets window.PARK_PVP_PLAYER
     from those props (JSON.stringify, so quotes in names are safe).
  3. The render passes playerId={playerId} playerName={'Player'}.
     (playerId is in scope in MapScreen; the name follows the house PvP
     modals, which also pass 'Player'.)

Run from /app: python3 frontend/patch-park-tennis-pvp-identity.py
Frontend only: reload Expo Go, open a park, tap Tennis, open the
PvP panel — creating a room must work (no 'local-player' fallback).
Idempotent: re-running prints PARK_TENNIS_PVP_IDENTITY_ALREADY_APPLIED.
"""
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "PARK_TENNIS_PVP_IDENTITY_OK"

# 1. Modal signature: accept playerId + playerName.
OLD_SIG = "const TennisGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {"
NEW_SIG = "const TennisGameModal = ({ visible, onClose, playerId, playerName }: { visible: boolean; onClose: () => void; playerId: string; playerName: string }) => {"

# 2. PoolWebView: add injectedJavaScript right after source={{ html: TENNIS_HTML }}.
OLD_SOURCE = "            source={{ html: TENNIS_HTML }}"
NEW_SOURCE = ("            source={{ html: TENNIS_HTML }}\n"
              "            injectedJavaScript={'window.PARK_PVP_PLAYER = {id: ' + JSON.stringify(playerId || 'local-player') + ', name: ' + JSON.stringify(playerName || 'Player') + '}; true;'}")

# 3. Render: pass the props.
OLD_RENDER = "(<TennisGameModal visible={tennisOpen} onClose={() => setTennisOpen(false)} />)"
NEW_RENDER = "(<TennisGameModal visible={tennisOpen} onClose={() => setTennisOpen(false)} playerId={playerId} playerName={'Player'} />)"


def main():
    if not INDEX.exists():
        print("WARNING: frontend/app/(tabs)/index.tsx not found - identity NOT added")
        return 1
    src = INDEX.read_text(errors="ignore")
    if "const TennisGameModal" not in src:
        print("WARNING: TennisGameModal not found - identity NOT added")
        return 1
    if "injectedJavaScript={'window.PARK_PVP_PLAYER" in src and "TENNIS_HTML" in src:
        # Already applied if the tennis modal's WebView carries the injection.
        # (Check narrowly: the injection must sit near TENNIS_HTML.)
        idx = src.find("TENNIS_HTML")
        seg = src[max(0, idx - 200): idx + 600]
        if "PARK_PVP_PLAYER" in seg:
            print("PARK_TENNIS_PVP_IDENTITY_ALREADY_APPLIED")
            return 0
    if OLD_SIG not in src:
        print("WARNING: TennisGameModal signature not found - identity NOT added")
        return 1
    if OLD_SOURCE not in src:
        print("WARNING: Tennis PoolWebView source not found - identity NOT added")
        return 1
    if OLD_RENDER not in src:
        print("WARNING: TennisGameModal render not found - identity NOT added")
        return 1
    new_src = src.replace(OLD_SIG, NEW_SIG, 1)
    new_src = new_src.replace(OLD_SOURCE, NEW_SOURCE, 1)
    new_src = new_src.replace(OLD_RENDER, NEW_RENDER, 1)
    if new_src.count("{") != new_src.count("}") or new_src.count("(") != new_src.count(")"):
        print("PARK_TENNIS_PVP_IDENTITY_BRACE_FAIL: brace/paren mismatch, index.tsx NOT written")
        return 1
    INDEX.write_text(new_src)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
