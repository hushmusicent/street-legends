#!/usr/bin/env python3
"""Street Legends Basketball PvP sync fix v4.

The file in /app keeps changing shape (agent edit present, then gone,
then a spaced variant), so exact anchors keep missing. v4 uses a LOOSE
regex: it finds the state-post return and its .then callback no matter
what spacing or body it currently has, and replaces the whole callback
with the reply-as-poll version. It also allows up to 2 polls in flight.

Fix (sync-only; does NOT touch room create/join/leave, the code format,
or the states structure):
  1. pvpPostState: use the returned room to apply the opponent's state
     immediately (reply-as-poll).
  2. pvpPollOnce: allow up to 2 polls in flight instead of skipping.

Run from /app: python3 frontend/patch-basketball-sync-v4.py
Idempotent: a full re-run prints BASKETBALL_SYNC_ALREADY_APPLIED.
"""
import re
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_SYNC_OK"

# Loose: return + .then + ANY callback body up to "return r;" + "});"
# Matches the plain version, the agent's pvpApplyFromRoom version, and
# spaced variants (pv.posting = false). Non-greedy so it stops at the
# first "return r; });".
POST_RE = re.compile(
    r"return pvpPost\('/'\+G\.pvp\.code\+'/state',\{player_id:who\.id,state:st\}\)"
    r"\.then\(function\(r\)\{.*?return r;\s*\}\);",
    re.DOTALL,
)
POST_NEW = (
    "return pvpPost('/'+G.pvp.code+'/state',{player_id:who.id,state:st}).then(function(r){\n"
    "    pv.posting=false;\n"
    "    // SYNC: the backend returns the full room. Use it right away to apply\n"
    "    // the opponent's latest state instead of waiting for the next poll.\n"
    "    try {\n"
    "      if (r && r.states) {\n"
    "        var oRole = G.pvp.role === 'host' ? 'guest' : 'host';\n"
    "        var oSt = r.states[oRole] || null;\n"
    "        if (oSt && typeof oSt.seq === 'number' && (oSt.seq > G.pvp.oppSeq || oSt.seq < G.pvp.oppSeq - 50)) {\n"
    "          G.pvp.oppSeq = oSt.seq;\n"
    "          pvpApplyState(oSt);\n"
    "        }\n"
    "        if (r.status === 'finished' && G.mode !== 'over') { pvpStopPoll(); G.mode = 'over'; }\n"
    "      }\n"
    "    } catch (e) {}\n"
    "    return r;\n"
    "  });"
)

# Poll: match the single-poll guard in any spacing variant. Accepts both
# the boolean form (pv.polling=true / pv.polling=false) and the counter
# form (polling || 0). If a counter form is already present, skip.
POLL_BOOL_RE = re.compile(
    r"if\(G\.pvp\.polling\) return;[^\n]*\n"
    r"\s*var code=G\.pvp\.code;\s*\n"
    r"\s*var pv=G\.pvp; pv\.polling\s*=\s*true;\s*\n"
    r"\s*pvpGet\(code\)\.then\(function\(room\)\{\s*\n"
    r"\s*pv\.polling\s*=\s*false;",
    re.DOTALL,
)
POLL_NEW = (
    "if((G.pvp.pollCount || 0) >= 2) return; // SYNC: allow 2 polls in flight\n"
    "  var code=G.pvp.code;\n"
    "  var pv=G.pvp; pv.pollCount=(pv.pollCount || 0)+1;\n"
    "  pvpGet(code).then(function(room){\n"
    "    pv.pollCount=Math.max(0,(pv.pollCount || 1)-1);"
)

def main():
    if not BB.exists():
        print("ERROR: BasketballHtml.ts not found (run from /app)")
        sys.exit(1)
    src = BB.read_text()
    if "pollCount" in src and "pvpApplyState(oSt)" in src:
        print("BASKETBALL_SYNC_ALREADY_APPLIED")
        return
    # --- 1. reply-as-poll (replace the whole .then callback) ---
    if "pvpApplyState(oSt)" in src:
        print("NOTE: reply-as-poll already present; keeping it")
    else:
        m = POST_RE.search(src)
        if not m:
            print("ERROR: pvpPostState return anchor not found (file changed in an unexpected way)")
            sys.exit(1)
        src = src[:m.start()] + POST_NEW + src[m.end():]
    # --- 2. parallel polls ---
    if "pollCount" in src:
        print("NOTE: parallel polls already present")
    elif "polling || 0" in src:
        # Agent's counter form already allows 2 in flight; nothing to add.
        print("NOTE: agent counter poll already allows 2 in flight")
    else:
        m2 = POLL_BOOL_RE.search(src)
        if not m2:
            print("ERROR: pvpPollOnce anchor not found (file changed in an unexpected way)")
            sys.exit(1)
        src = src[:m2.start()] + POLL_NEW + src[m2.end():]
    BB.write_text(src)
    cur = BB.read_text()
    if "pvpApplyState(oSt)" not in cur and "pvpApplyFromRoom" not in cur:
        print("ERROR: sync patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
