#!/usr/bin/env python3
"""Street Legends Basketball PvP sync fix.

Problem: in a 2v2 game, the player moves on their phone but the opponent
does not move on the other phone. The backend state flow is proven live
(create/join/state/get all work), so the break is in the game. The game
posts its position every 0.1s and polls every 100ms, but the post's reply
(the full room, including the opponent's latest state) is thrown away,
so each phone only learns the opponent's position on the next poll --
a full round trip behind. On a slow connection the poll also skips while
one is in flight, so updates stack up and the opponent appears frozen.

Fix (sync-only; does NOT touch room create/join/leave, the code format,
or the states structure):
  1. In pvpPostState, use the returned room to apply the opponent's state
     immediately (reply-as-poll). Every position post now also carries
     the opponent's latest position back, halving the delay.
  2. In pvpPollOnce, allow a second poll to run while one is in flight
     (up to 2 in parallel) instead of skipping, so a slow poll cannot
     starve updates.

Run from /app: python3 frontend/patch-basketball-sync.py
Idempotent: a full re-run prints BASKETBALL_SYNC_ALREADY_APPLIED.
"""
import sys
from pathlib import Path

BB = Path("frontend/components/BasketballHtml.ts")
MARKER = "BASKETBALL_SYNC_OK"

# --- 1. reply-as-poll in pvpPostState ---
OLD_POST = """  var who=pvpPlayer();
  var pv=G.pvp; pv.posting=true;
  st.round = G.pvp.round || 0; st.rm = G.pvp.rmReq || 0;
  return pvpPost('/'+G.pvp.code+'/state',{player_id:who.id,state:st}).then(function(r){ pv.posting=false; return r; });"""

NEW_POST = """  var who=pvpPlayer();
  var pv=G.pvp; pv.posting=true;
  st.round = G.pvp.round || 0; st.rm = G.pvp.rmReq || 0;
  return pvpPost('/'+G.pvp.code+'/state',{player_id:who.id,state:st}).then(function(r){
    pv.posting=false;
    // SYNC: the backend returns the full room. Use it right away to apply
    // the opponent's latest state instead of waiting for the next poll.
    try {
      if (r && r.states) {
        var oRole = G.pvp.role === 'host' ? 'guest' : 'host';
        var oSt = r.states[oRole] || null;
        if (oSt && typeof oSt.seq === 'number' && (oSt.seq > G.pvp.oppSeq || oSt.seq < G.pvp.oppSeq - 50)) {
          G.pvp.oppSeq = oSt.seq;
          pvpApplyState(oSt);
        }
        if (r.status === 'finished' && G.mode !== 'over') { pvpStopPoll(); G.mode = 'over'; }
      }
    } catch (e) {}
    return r;
  });"""

# --- 2. allow up to 2 polls in parallel ---
OLD_POLL = """function pvpPollOnce(){
  if(!pvpIsOn()) return;
  if(G.pvp.polling) return; // previous poll still in flight
  var code=G.pvp.code;
  var pv=G.pvp; pv.polling=true;
  pvpGet(code).then(function(room){
    pv.polling=false;"""

NEW_POLL = """function pvpPollOnce(){
  if(!pvpIsOn()) return;
  // SYNC: allow up to 2 polls in flight so a slow poll cannot starve
  // updates (a single in-flight poll used to make every later poll skip).
  if((G.pvp.pollCount || 0) >= 2) return;
  var code=G.pvp.code;
  var pv=G.pvp; pv.pollCount=(pv.pollCount || 0)+1;
  pvpGet(code).then(function(room){
    pv.pollCount=Math.max(0,(pv.pollCount || 1)-1);"""

def main():
    if not BB.exists():
        print("ERROR: BasketballHtml.ts not found (run from /app)")
        sys.exit(1)
    src = BB.read_text()
    if "BASKETBALL_SYNC" in src or "reply-as-poll" in src.lower() or "pollCount" in src:
        print("BASKETBALL_SYNC_ALREADY_APPLIED")
        return
    if OLD_POST not in src:
        print("ERROR: pvpPostState anchor not found (file may already be patched or changed)")
        sys.exit(1)
    if OLD_POLL not in src:
        print("ERROR: pvpPollOnce anchor not found (file may already be patched or changed)")
        sys.exit(1)
    src = src.replace(OLD_POST, NEW_POST, 1)
    src = src.replace(OLD_POLL, NEW_POLL, 1)
    BB.write_text(src)
    cur = BB.read_text()
    if "pollCount" not in cur or "oSt.seq" not in cur:
        print("ERROR: sync patch not installed")
        sys.exit(1)
    print(MARKER)

if __name__ == "__main__":
    main()
