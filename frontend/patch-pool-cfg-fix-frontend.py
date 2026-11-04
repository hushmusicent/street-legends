#!/usr/bin/env python3
"""Street Legends frontend: pool PvP game must use the real player ids.

Symptom (both phones, same screenshot): YOU (Stripes), FRIEND (Solids),
'Your turn.' on BOTH phones at once. That is only possible if both games
think they are the same player — the HTML game's fallback config
(me='you', foe='friend', hostId='you') — i.e. window.POOL_PVP never
reached the page (injectedJavaScriptBeforeContentLoaded does not reliably
fire for inline HTML in this WebView build), so both games run as 'you',
both think it is their turn, and the first pocketed group (Stripes) shows
on both. The room/turn sync itself is fine; the identities are not.

Fix: add an injectedJavaScript (runs after load, reliably) to
PoolPvpGameModal that re-applies the real config into the game's
ME/FOE/FOENAME/HOST variables, repairs a placeholder turn ('you'/'friend')
to the real host id, and refreshes the header/message. If the
before-content-loaded injection already worked, this is a no-op (turn is
already a real player id, not a placeholder). Frontend / Expo Go only."""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "POOL_CFG_REINIT"
ANCHOR = "injectedJavaScriptBeforeContentLoaded={pvpConfig}"
REINIT = (
    'injectedJavaScript={pvpConfig + \'/* POOL_CFG_REINIT */ try { '
    'ME = window.POOL_PVP.me; FOE = window.POOL_PVP.foe; '
    'FOENAME = window.POOL_PVP.foeName; HOST = window.POOL_PVP.hostId; '
    'if (turn === "you" || turn === "friend") { turn = HOST; } '
    'updateHeader(); '
    'if (turn === ME) { setMsg("Your turn."); } '
    'else { setMsg("Waiting for " + FOENAME + "..."); } '
    '} catch (e) {} true;\'}'
)

def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - nothing changed")
        return 1
    src = IDX.read_text(errors="ignore")
    if MARKER in src:
        print("POOL_CFG_FIX_ALREADY_APPLIED")
        return 0
    if ANCHOR not in src:
        print("WARNING: game WebView anchor not matched - index.tsx NOT changed")
        return 1
    new_src = src.replace(ANCHOR, ANCHOR + "\n            " + REINIT, 1)
    if (new_src.count("{") - new_src.count("}")) != (src.count("{") - src.count("}")):
        print("WARNING: brace balance changed - index.tsx NOT written")
        return 1
    if (new_src.count("(") - new_src.count(")")) != (src.count("(") - src.count(")")):
        print("WARNING: paren balance changed - index.tsx NOT written")
        return 1
    IDX.write_text(new_src)
    print("POOL_CFG_FIX_OK")
    return 0

if __name__ == "__main__":
    sys.exit(main())
