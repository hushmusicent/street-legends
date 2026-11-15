#!/usr/bin/env python3
"""Dominoes All Fives scoring: score now keeps moving during a hand.

BUG: In DOMINOES - YOU vs CPU the score stays 0-0 for a whole hand.
The game only scores at the END of a hand (going out = opponent's
remaining pips, blocked = pip difference). It has NO in-play scoring,
so a "First to 100" match barely moves. The same gap is in PvP.

FIX: official Spinner / All Fives (Muggins) in-play scoring. After
every tile is placed, add up the pips on all open ends (the far end of
each arm - left, right, up, down; the spinner's own value on any arm
that has no tiles yet). If the total is a multiple of 5, the player
who just played scores that many points. The message says so
("Ends total 15 - +15 points!") and the scorebar updates at once.
Hand-end scoring is untouched and adds on top; reaching 100
mid-hand ends the match, same as at hand end.

PvC (DominoHtml.ts): new endsTotal() + scoreEnds(player), called
after placeOnArm in youPlay (single-arm pick), placePending and
cpuTurn. PvP (DominoPvpHtml.ts): new endsTotalPvp(st), called in
replay() after each 'play' action, so both phones compute the same
scores from the same log. The opening spinner is NOT scored (kept
identical in PvC and PvP).

Targeted edits only - they do NOT rewrite the game HTML, so the
spinner/boneyard rules and the center-prize code in the live files
are kept.

Run from /app (repo root):
  cd /app && curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/patch-dominoes-allfives.py?v=1" -o frontend/patch-dominoes-allfives.py && python3 frontend/patch-dominoes-allfives.py
Expect: DOMINOES_ALLFIVES_OK
Then reload Expo Go and play Dominoes: the score must go up during
the hand whenever the open ends total 5, 10, 15, 20, 25 or 30.
"""
from pathlib import Path

DOM_TS = Path("frontend/components/DominoHtml.ts")
DOM_PVP_TS = Path("frontend/components/DominoPvpHtml.ts")

# ---- PvC: helper functions (inserted after placeOnArm) ----
PVC_PLACE_ANCHOR = """function placeOnArm(tile, arm) {
  var e = armEnd(arm);
  var placed = (tile[0] === e) ? [tile[0], tile[1]] : [tile[1], tile[0]];
  S.arms[arm].push(placed);
  S.passes = 0;
}"""

PVC_HELPERS = PVC_PLACE_ANCHOR + """
function endsTotal() {
  var t = 0;
  for (var a = 0; a < ARMS.length; a++) { var e = armEnd(ARMS[a]); if (e !== null) t += e; }
  return t;
}
function scoreEnds(player) {
  var t = endsTotal();
  if (t > 0 && t % 5 === 0) {
    if (player === "you") S.youScore += t; else S.cpuScore += t;
    if (S.youScore >= 100 || S.cpuScore >= 100) {
      S.matchOver = true;
      el("overText").textContent = (S.youScore >= 100 ? "YOU WIN THE MATCH!" : "CPU WINS THE MATCH.") + " Final: You " + S.youScore + " - CPU " + S.cpuScore + ".";
      el("overOverlay").style.display = "flex";
    }
    return t;
  }
  return 0;
}"""

PVC_YOUPLAY_OLD = """    S.you.splice(i, 1);
    placeOnArm(tile, arms[0]);
    S.mustPlay = -1; S.pending = -1; S.pendingArms = [];
    S.msg = "You played " + tile[0] + "-" + tile[1] + " on " + arms[0] + ".";"""
PVC_YOUPLAY_NEW = """    S.you.splice(i, 1);
    placeOnArm(tile, arms[0]);
    var pts = scoreEnds("you");
    S.mustPlay = -1; S.pending = -1; S.pendingArms = [];
    S.msg = "You played " + tile[0] + "-" + tile[1] + " on " + arms[0] + "." + (pts ? " Ends total " + pts + " - +" + pts + " points!" : "");"""

PVC_PENDING_OLD = """  var tile = S.you[i]; S.you.splice(i, 1);
  placeOnArm(tile, arm);
  S.mustPlay = -1; S.pending = -1; S.pendingArms = [];
  S.msg = "You played " + tile[0] + "-" + tile[1] + " on " + arm + ".";"""
PVC_PENDING_NEW = """  var tile = S.you[i]; S.you.splice(i, 1);
  placeOnArm(tile, arm);
  var pts = scoreEnds("you");
  S.mustPlay = -1; S.pending = -1; S.pendingArms = [];
  S.msg = "You played " + tile[0] + "-" + tile[1] + " on " + arm + "." + (pts ? " Ends total " + pts + " - +" + pts + " points!" : "");"""

PVC_CPU_OLD = """  var tile = S.cpu[best]; S.cpu.splice(best, 1);
  var arms = matchingArms(tile);
  var arm = arms[0];
  placeOnArm(tile, arm);
  S.msg = "CPU played " + tile[0] + "-" + tile[1] + " on " + arm + ".";"""
PVC_CPU_NEW = """  var tile = S.cpu[best]; S.cpu.splice(best, 1);
  var arms = matchingArms(tile);
  var arm = arms[0];
  placeOnArm(tile, arm);
  var pts = scoreEnds("cpu");
  S.msg = "CPU played " + tile[0] + "-" + tile[1] + " on " + arm + "." + (pts ? " Ends total " + pts + " - +" + pts + " points!" : "");"""

# ---- PvP: helper + replay hook ----
PVP_PLACE_ANCHOR = """function placeOnArm(st, tile, arm) {
  var e = armEnd(st, arm);
  var placed = (tile[0] === e) ? [tile[0], tile[1]] : [tile[1], tile[0]];
  st.arms[arm].push(placed);
  st.passes = 0;
}"""

PVP_HELPERS = PVP_PLACE_ANCHOR + """
function endsTotalPvp(st) {
  var t = 0;
  for (var a = 0; a < ARMS.length; a++) { var e = armEnd(st, ARMS[a]); if (e !== null) t += e; }
  return t;
}"""

PVP_REPLAY_OLD = """      st.msg = (act.p === MY ? 'You' : FOE_NAME) + ' played ' + act.tile[0] + '-' + act.tile[1] + ' on ' + act.side + '.';
      if (hand.length === 0) {"""
PVP_REPLAY_NEW = """      st.msg = (act.p === MY ? 'You' : FOE_NAME) + ' played ' + act.tile[0] + '-' + act.tile[1] + ' on ' + act.side + '.';
      var endsPts = endsTotalPvp(st);
      if (endsPts > 0 && endsPts % 5 === 0) { scores[act.p] += endsPts; st.msg += ' Ends total ' + endsPts + ' - +' + endsPts + ' points!'; if (scores[act.p] >= 100) st.matchOver = true; }
      if (hand.length === 0) {"""


def replace_once(path, old, new, label):
    src = path.read_text()
    n = src.count(old)
    if n == 0:
        print("WARNING: %s: anchor not found for %s - skipped" % (path.name, label))
        return False
    if n != 1:
        print("ERROR: %s: anchor for %s found %d times (expected 1) - skipped" % (path.name, label, n))
        return False
    path.write_text(src.replace(old, new, 1))
    print("OK: %s %s" % (path.name, label))
    return True


def main():
    done = []
    if not DOM_TS.exists():
        print("DOMINOES_ALLFIVES_ERROR: %s not found. Run from /app (repo root). Nothing changed." % DOM_TS)
        return
    if not DOM_PVP_TS.exists():
        print("DOMINOES_ALLFIVES_ERROR: %s not found. Run from /app (repo root). Nothing changed." % DOM_PVP_TS)
        return
    # PvC
    src = DOM_TS.read_text()
    if "function scoreEnds(player)" in src:
        print("SKIP: DominoHtml.ts All Fives already applied")
        done.append("pvc")
    else:
        if replace_once(DOM_TS, PVC_PLACE_ANCHOR, PVC_HELPERS, "PvC helpers"):
            done.append("pvc-helpers")
        if replace_once(DOM_TS, PVC_YOUPLAY_OLD, PVC_YOUPLAY_NEW, "PvC youPlay"):
            done.append("pvc-youplay")
        if replace_once(DOM_TS, PVC_PENDING_OLD, PVC_PENDING_NEW, "PvC placePending"):
            done.append("pvc-pending")
        if replace_once(DOM_TS, PVC_CPU_OLD, PVC_CPU_NEW, "PvC cpuTurn"):
            done.append("pvc-cpu")
    # PvP
    src = DOM_PVP_TS.read_text()
    if "function endsTotalPvp(st)" in src:
        print("SKIP: DominoPvpHtml.ts All Fives already applied")
        done.append("pvp")
    else:
        if replace_once(DOM_PVP_TS, PVP_PLACE_ANCHOR, PVP_HELPERS, "PvP helper"):
            done.append("pvp-helper")
        if replace_once(DOM_PVP_TS, PVP_REPLAY_OLD, PVP_REPLAY_NEW, "PvP replay"):
            done.append("pvp-replay")
    # verify
    ok_pvc = "function scoreEnds(player)" in DOM_TS.read_text() and DOM_TS.read_text().count('scoreEnds("you")') == 2 and DOM_TS.read_text().count('scoreEnds("cpu")') == 1
    ok_pvp = "function endsTotalPvp(st)" in DOM_PVP_TS.read_text() and "endsTotalPvp(st)" in DOM_PVP_TS.read_text()
    if ok_pvc and ok_pvp:
        print("DOMINOES_ALLFIVES_OK")
    else:
        print("DOMINOES_ALLFIVES_PARTIAL: pvc=%s pvp=%s (see lines above)" % (ok_pvc, ok_pvp))


if __name__ == "__main__":
    main()
