export const DOMINO_PVP_HTML = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { margin: 0; background: radial-gradient(ellipse at 50% 0%, #3a2410 0%, #1a1208 45%, #0d0d0d 100%); color: #ffffff; font-family: sans-serif; }
#wrap { max-width: 460px; margin: 0 auto; padding: 10px; text-align: center; box-sizing: border-box; }
h1 { font-size: 22px; margin: 6px 0 2px; color: #f5c542; text-shadow: 0 2px 4px rgba(0,0,0,0.9), 0 0 24px rgba(245,197,66,0.55); }
.deco { display: flex; justify-content: center; pointer-events: none; margin: 2px 0 4px; }
.deco .dom { width: 24px; height: 44px; box-shadow: 0 6px 12px rgba(0,0,0,0.7), inset 0 1px 0 #ffffff; }
.deco .dom .pip i { width: 3px; height: 3px; }
.deco .d1 { transform: rotate(-12deg); }
.deco .d2 { transform: rotate(10deg); margin-left: -8px; margin-top: 4px; }
.scorebar { background: rgba(0,0,0,0.55); border-radius: 8px; padding: 7px; font-size: 13px; font-weight: 800; margin: 6px 0; box-shadow: inset 0 2px 6px rgba(0,0,0,0.6); }
.table { background: linear-gradient(160deg, #c08a4a, #8a5a2b 45%, #5e3a1a); border-radius: 16px; padding: 20px; margin: 12px 0; box-shadow: 0 18px 32px rgba(0,0,0,0.7), 0 4px 8px rgba(0,0,0,0.5), inset 0 2px 0 rgba(255,255,255,0.3), inset 0 -2px 0 rgba(0,0,0,0.4); }
.ends { font-size: 13px; font-weight: 800; color: #ffe9a8; margin-bottom: 6px; text-shadow: 0 1px 2px rgba(0,0,0,0.8); }
.chain { display: flex; flex-wrap: wrap; gap: 4px; justify-content: center; min-height: 110px; align-items: center; background: radial-gradient(ellipse at center, rgba(0,0,0,0.35), rgba(0,0,0,0.55)); border-radius: 10px; padding: 14px; box-shadow: inset 0 4px 12px rgba(0,0,0,0.65), inset 0 -1px 0 rgba(255,255,255,0.08); }
.msg { font-size: 13px; font-weight: 800; margin: 8px 0 4px; min-height: 18px; color: #ffe9a8; }
.cpurow { display: flex; gap: 3px; justify-content: center; margin: 6px 0; flex-wrap: wrap; }
.cpulabel { font-size: 12px; font-weight: 800; color: #cccccc; margin-bottom: 2px; }
.dom { background: linear-gradient(180deg, #fffef8, #f3ecd8 60%, #e8dfc4); border: 1px solid #2a2a2a; border-radius: 5px; box-shadow: 0 4px 8px rgba(0,0,0,0.55), inset 0 1px 0 #ffffff, inset 0 -1px 0 rgba(0,0,0,0.15); display: inline-flex; }
.dom.v { flex-direction: column; width: 32px; height: 60px; }
.dom.h { flex-direction: row; width: 60px; height: 32px; }
.dom .half { flex: 1; display: grid; grid-template-columns: repeat(3, 1fr); grid-template-rows: repeat(3, 1fr); padding: 2px; }
.dom.v .half:first-child { border-bottom: 2px solid #333; }
.dom.h .half:first-child { border-right: 2px solid #333; }
.pip { display: flex; align-items: center; justify-content: center; }
.pip i { width: 5px; height: 5px; border-radius: 50%; background: #222; display: block; }
.pip.blank i { background: transparent; }
.dom.back { background: linear-gradient(180deg, #a06a35, #6b4423); border-color: #5a3a1a; box-shadow: 0 3px 6px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.25); }
.dom.endmark { outline: 3px solid #f5c542; outline-offset: 1px; }
button.dom { cursor: pointer; padding: 0; }
button.dom.playable { outline: 3px solid #f5c542; outline-offset: 1px; }
button.dom:disabled { cursor: default; opacity: 1; }
.hand { display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; margin-top: 8px; }
button { background: linear-gradient(180deg, #6a6a6a, #3a3a3a); color: #ffffff; font-weight: 800; border: 0; border-radius: 8px; padding: 12px 14px; font-size: 13px; margin: 4px; box-shadow: 0 5px 10px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.25); cursor: pointer; }
button:active { transform: translateY(2px); box-shadow: 0 2px 4px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.2); }
button.green { background: linear-gradient(180deg, #2e7d32, #1e5c2e); }
button.blue { background: linear-gradient(180deg, #1565c0, #0d47a1); }
button.red { background: linear-gradient(180deg, #c62828, #8e0000); }
button:disabled { opacity: 0.5; cursor: default; }
.overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.75); display: none; align-items: center; justify-content: center; z-index: 50; }
.overlay .box { background: #222; border: 2px solid #f5c542; border-radius: 12px; padding: 20px; max-width: 320px; text-align: center; }
.overlay .box p { font-size: 15px; font-weight: 800; margin: 0 0 12px; }

.spinnerbox { display: flex; flex-direction: column; align-items: center; margin-bottom: 8px; }
.spinnerlabel { font-size: 11px; font-weight: 800; color: #f5c542; letter-spacing: 2px; margin-top: 4px; }
.dom.spinner { outline: 3px solid #f5c542; outline-offset: 2px; width: 40px; height: 76px; }
.dom.spinner .pip i { width: 6px; height: 6px; }
.arms { display: flex; flex-direction: column; gap: 6px; }
.armrow { background: rgba(0,0,0,0.25); border-radius: 8px; padding: 6px; }
.armlabel { font-size: 12px; font-weight: 800; color: #ffe9a8; text-align: left; margin-bottom: 4px; }
.armtiles { display: flex; flex-wrap: wrap; gap: 4px; min-height: 34px; align-items: center; }
.dom.double-mark { outline: 2px solid #f5c542; outline-offset: 1px; }
button.dom.dim { opacity: 0.6; }

.table { background: linear-gradient(180deg, #2b438f, #1a2a5e); box-shadow: inset 0 2px 14px rgba(0,0,0,0.55), 0 2px 8px rgba(0,0,0,0.4); }
.cross { display: grid; grid-template-columns: auto auto auto; grid-template-rows: auto auto auto; gap: 4px; align-items: center; justify-items: center; width: max-content; margin: 6px auto; }
.cross-up { grid-column: 2; grid-row: 1; display: flex; flex-direction: column; gap: 4px; align-items: center; }
.cross-left { grid-column: 1; grid-row: 2; display: flex; gap: 4px; justify-self: end; justify-content: flex-end; }
.cross-spinner { grid-column: 2; grid-row: 2; }
.cross-right { grid-column: 3; grid-row: 2; display: flex; gap: 4px; justify-self: start; }
.cross-down { grid-column: 2; grid-row: 3; display: flex; flex-direction: column; gap: 4px; align-items: center; }
.endsline { font-size: 12px; font-weight: 700; color: #ffe9a8; letter-spacing: 1px; margin: 6px 0 10px; }
.dom.endglow { outline: 2px solid #facc15; outline-offset: 1px; box-shadow: 0 0 12px 2px rgba(250, 204, 21, 0.8); }
.pip.n1 i { background: #ef4444; }
.pip.n2 i { background: #14b8a6; }
.pip.n3 i { background: #22c55e; }
.pip.n4 i { background: #84cc16; }
.pip.n5 i { background: #c026d3; }
.pip.n6 i { background: #9333ea; }

.spot { display: inline-flex; align-items: center; justify-content: center; width: 32px; height: 32px; border: 2px dashed #facc15; border-radius: 8px; color: #facc15; font-size: 22px; font-weight: 900; line-height: 1; box-shadow: 0 0 12px 2px rgba(250, 204, 21, 0.8); background: rgba(250, 204, 21, 0.12); cursor: pointer; }
.dom.picked { outline: 3px solid #facc15; outline-offset: 2px; box-shadow: 0 0 14px 3px rgba(250, 204, 21, 0.9); transform: translateY(-4px); }

.board-scroll { overflow-x: auto; margin: 6px 0; }
.cross-left .dom, .cross-right .dom, .cross-up .dom, .cross-down .dom { flex-shrink: 0; }

/* APP TALL SCALE (app WebView only): device-height layout, the table
   stretches down to fill the screen (taller, not longer). */
html, body { height: 100%; }
#wrap { max-width: none; min-height: 100vh; display: flex; flex-direction: column; padding: 16px; }
.table { flex: 1; display: flex; flex-direction: column; }
.board-scroll { flex: 1; }
</style>
</head>
<body>
<div id="wrap">
<h1>DOMINOES</h1>
<div class="deco"><span class="dom v d1"><span class="half"><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span></span><span class="half"><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span></span></span><span class="dom v d2"><span class="half"><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span></span><span class="half"><span class="pip"><i></i></span><span class="pip blank"><i></i></span><span class="pip blank"><i></i></span><span class="pip blank"><i></i></span><span class="pip blank"><i></i></span><span class="pip blank"><i></i></span><span class="pip blank"><i></i></span><span class="pip blank"><i></i></span><span class="pip"><i></i></span></span></span></div>
<div class="scorebar" id="scorebar"></div>
<div class="cpulabel" id="foelabel"></div>
<div class="cpurow" id="foerow"></div>
<div class="table">
<div class="board-scroll">
<div class="cross">
<div class="cross-up" id="armUp"></div>
<div class="cross-left" id="armLeft"></div>
<div class="cross-spinner"><div id="spinner"></div></div>
<div class="cross-right" id="armRight"></div>
<div class="cross-down" id="armDown"></div>
</div>
</div>
<div class="endsline" id="endsline"></div>
<div class="msg" id="msg"></div>
<div id="actions"></div>
</div>
<div class="hand" id="hand"></div>
<div>
<button class="red" id="btnLeave">LEAVE TABLE</button>
</div>
</div>
<div class="overlay" id="leaveOverlay"><div class="box">
<p>Leave the dominoes table? Your progress will be lost.</p>
<button class="red" id="btnLeaveYes">LEAVE</button>
<button id="btnLeaveNo">STAY</button>
</div></div>
<div class="overlay" id="overOverlay"><div class="box">
<p id="overText"></p>
<button class="green" id="btnAgain">PLAY AGAIN</button>
<button class="red" id="btnOverLeave">LEAVE TABLE</button>
</div></div>
<script>

var CFG = window.DOMINO_PVP || {me: 'host', foe: 'guest', foeName: 'FRIEND', hostId: 'host', seed: 12345};
var MY = (CFG.me === CFG.hostId) ? 'host' : 'guest';
var FOE = (MY === 'host') ? 'guest' : 'host';
var FOE_NAME = CFG.foeName || 'FRIEND';
var PIPS = { 0: [], 1: [4], 2: [0, 8], 3: [0, 4, 8], 4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8] };
var ARMS = ["left", "right", "up", "down"];
function mulberry32(a) { return function () { a |= 0; a = a + 0x6D2B79F5 | 0; var t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
function buildSet() { var s = []; for (var a = 0; a <= 6; a++) for (var b = a; b <= 6; b++) s.push([a, b]); return s; }
function seededShuffle(arr, rnd) { for (var i = arr.length - 1; i > 0; i--) { var j = Math.floor(rnd() * (i + 1)); var t = arr[i]; arr[i] = arr[j]; arr[j] = t; } return arr; }
function handPips(hand) { var s = 0; for (var i = 0; i < hand.length; i++) s += hand[i][0] + hand[i][1]; return s; }
function highestDouble(hand) { var best = -1; for (var i = 0; i < hand.length; i++) if (hand[i][0] === hand[i][1] && hand[i][0] > best) best = hand[i][0]; return best; }
function bestTile(hand) { var m = null, s = -1; for (var i = 0; i < hand.length; i++) { var p = hand[i][0] + hand[i][1]; if (p > s) { s = p; m = hand[i]; } } return m; }
function el(id) { return document.getElementById(id); }
function postClose() { try { if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage("close"); } catch (e) {} }
function postState() { try { if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'domino-shot', state: { seed: CFG.seed, actions: LOG } })); } catch (e) {} }
function newHandState(matchNo, handNo) {
  var seed = CFG.seed + matchNo * 1000003 + handNo * 7919;
  var rnd = mulberry32(seed);
  var host, guest, bone, hd, gd, tries = 0;
  do {
    var set = seededShuffle(buildSet(), rnd);
    host = set.slice(0, 7); guest = set.slice(7, 14); bone = set.slice(14);
    hd = highestDouble(host); gd = highestDouble(guest); tries++;
  } while (hd < 0 && gd < 0 && tries < 200);
  var hands = { host: host, guest: guest };
  var spinner, spinnerDouble = true, starter;
  if (hd >= 0 && hd >= gd) { starter = 'host'; spinner = [hd, hd]; hands.host.splice(hands.host.findIndex(function (t) { return t[0] === hd && t[1] === hd; }), 1); }
  else if (gd >= 0) { starter = 'guest'; spinner = [gd, gd]; hands.guest.splice(hands.guest.findIndex(function (t) { return t[0] === gd && t[1] === gd; }), 1); }
  else {
    var ht = bestTile(hands.host), gt = bestTile(hands.guest);
    if (ht[0] + ht[1] >= gt[0] + gt[1]) { starter = 'host'; spinner = ht; hands.host.splice(hands.host.indexOf(ht), 1); }
    else { starter = 'guest'; spinner = gt; hands.guest.splice(hands.guest.indexOf(gt), 1); }
    spinnerDouble = false;
  }
  return { hands: hands, bone: bone, spinner: spinner, spinnerDouble: spinnerDouble, arms: { left: [], right: [], up: [], down: [] }, turn: starter === 'host' ? 'guest' : 'host', passes: 0, mustPlay: -1, over: false, matchOver: false, msg: (starter === MY ? 'You' : FOE_NAME) + ' started with the spinner ' + spinner[0] + '-' + spinner[1] + '.' };
}
function armEnd(st, arm) {
  if (!st.spinnerDouble && (arm === "up" || arm === "down")) return null;
  var list = st.arms[arm];
  if (list.length) return list[list.length - 1][1];
  if (!st.spinner) return null;
  if (!st.spinnerDouble && arm === "right") return st.spinner[1];
  return st.spinner[0];
}
function canPlayOnArm(st, tile, arm) { var e = armEnd(st, arm); return e !== null && (tile[0] === e || tile[1] === e); }
function matchingArms(st, tile) { var out = []; for (var i = 0; i < ARMS.length; i++) if (canPlayOnArm(st, tile, ARMS[i])) out.push(ARMS[i]); return out; }
function playableTiles(st, seat) { var out = []; var hand = st.hands[seat]; for (var i = 0; i < hand.length; i++) if (matchingArms(st, hand[i]).length) out.push(i); return out; }
function placeOnArm(st, tile, arm) {
  var e = armEnd(st, arm);
  var placed = (tile[0] === e) ? [tile[0], tile[1]] : [tile[1], tile[0]];
  st.arms[arm].push(placed);
  st.passes = 0;
}
var LOG = [];
var S = null;
var PENDING = -1;
var PENDING_ARMS = [];
function replay() {
  var scores = { host: 0, guest: 0 };
  var matchNo = 0, handNo = 1;
  var st = newHandState(matchNo, handNo);
  for (var a = 0; a < LOG.length; a++) {
    var act = LOG[a];
    if (act.t === 'play') {
      var hand = st.hands[act.p];
      var idx = -1;
      for (var i = 0; i < hand.length; i++) if (hand[i][0] === act.tile[0] && hand[i][1] === act.tile[1]) { idx = i; break; }
      if (idx < 0) continue;
      hand.splice(idx, 1);
      placeOnArm(st, act.tile, act.side);
      st.mustPlay = -1;
      st.msg = (act.p === MY ? 'You' : FOE_NAME) + ' played ' + act.tile[0] + '-' + act.tile[1] + ' on ' + act.side + '.';
      if (hand.length === 0) {
        var pts = handPips(st.hands[act.p === 'host' ? 'guest' : 'host']);
        scores[act.p] += pts;
        st.over = true;
        st.msg = (act.p === MY ? 'You win the hand' : FOE_NAME + ' wins the hand') + ', +' + pts + ' points.';
        if (scores[act.p] >= 100) st.matchOver = true;
      } else {
        st.turn = (act.p === 'host') ? 'guest' : 'host';
      }
    } else if (act.t === 'draw') {
      if (st.bone.length) {
        var t = st.bone.pop();
        st.hands[act.p].push(t);
        st.mustPlay = matchingArms(st, t).length ? st.hands[act.p].length - 1 : -1;
      }
    } else if (act.t === 'pass') {
      st.passes++;
      st.msg = (act.p === MY ? 'You pass.' : FOE_NAME + ' passes.');
      if (st.bone.length === 0 && st.passes >= 2) {
        var hp = handPips(st.hands.host), gp = handPips(st.hands.guest);
        st.over = true;
        if (hp === gp) { st.msg = 'Blocked! Equal pips, no points.'; }
        else if (hp < gp) { scores.host += (gp - hp); st.msg = 'Blocked! Host had fewer pips, +' + (gp - hp) + ' points.'; if (scores.host >= 100) st.matchOver = true; }
        else { scores.guest += (hp - gp); st.msg = 'Blocked! Guest had fewer pips, +' + (hp - gp) + ' points.'; if (scores.guest >= 100) st.matchOver = true; }
      } else {
        st.turn = (act.p === 'host') ? 'guest' : 'host';
      }
    } else if (act.t === 'nexthand') {
      if (st.over && !st.matchOver) {
        handNo++;
        st = newHandState(matchNo, handNo);
        st.msg = 'Next hand.';
      }
    } else if (act.t === 'rematch') {
      if (st.matchOver) {
        matchNo++; scores = { host: 0, guest: 0 }; handNo = 1;
        st = newHandState(matchNo, handNo);
        st.msg = 'New match.';
      }
    }
  }
  S = st; S.scores = scores; S.matchNo = matchNo; S.handNo = handNo;
  PENDING = -1; PENDING_ARMS = [];
  render();
}
function doAction(act) { LOG.push(act); postState(); replay(); }
function pipGrid(n) {
  var cells = PIPS[n], out = "";
  for (var i = 0; i < 9; i++) out += cells.indexOf(i) >= 0 ? '<span class="pip n' + n + '"><i></i></span>' : '<span class="pip blank"><i></i></span>';
  return out;
}
function domHtml(tile, orient, extra, playable, dim) {
  var cls = "dom " + orient + (extra ? " " + extra : "") + (dim ? " dim" : "");
  if (orient === "v") return '<button class="' + cls + (playable ? " playable" : "") + '"><span class="half">' + pipGrid(tile[0]) + '</span><span class="half">' + pipGrid(tile[1]) + '</span></button>';
  return '<span class="' + cls + '"><span class="half">' + pipGrid(tile[0]) + '</span><span class="half">' + pipGrid(tile[1]) + '</span></span>';
}
function armTileHtml(tile, orient, extra) {
  var cls = "dom " + orient + (extra ? " " + extra : "");
  return '<span class="' + cls + '"><span class="half">' + pipGrid(tile[0]) + '</span><span class="half">' + pipGrid(tile[1]) + '</span></span>';
}
function wireSpots(elId, arm) {
  var list = document.getElementById(elId).querySelectorAll(".spot");
  for (var s = 0; s < list.length; s++) (function (spot) { spot.onclick = function () { placePending(arm); }; })(list[s]);
}
function tapTile(i) {
  if (!S || S.turn !== MY || S.over || S.matchOver) return;
  if (S.mustPlay >= 0 && i !== S.mustPlay) return;
  if (PENDING >= 0 && i === PENDING) { PENDING = -1; PENDING_ARMS = []; render(); return; }
  var tile = S.hands[MY][i];
  var arms = matchingArms(S, tile);
  if (!arms.length) return;
  if (arms.length === 1) {
    doAction({ t: 'play', p: MY, tile: tile, side: arms[0] });
    return;
  }
  PENDING = i; PENDING_ARMS = arms;
  render();
}
function placePending(arm) {
  if (PENDING < 0 || PENDING >= S.hands[MY].length) return;
  var tile = S.hands[MY][PENDING];
  doAction({ t: 'play', p: MY, tile: tile, side: arm });
}
function tapDraw() {
  if (!S || S.turn !== MY || S.over || S.matchOver || S.bone.length === 0) return;
  doAction({ t: 'draw', p: MY });
}
function tapPass() {
  if (!S || S.turn !== MY || S.over || S.matchOver) return;
  doAction({ t: 'pass', p: MY });
}
function tapNext() {
  if (!S || !S.over || S.matchOver) return;
  doAction({ t: 'nexthand' });
}
function render() {
  if (!S) return;
  el("scorebar").textContent = "YOU " + S.scores[MY] + "  |  " + FOE_NAME + " " + S.scores[FOE] + "  |  First to 100  |  Hand " + S.handNo;
  el("foelabel").textContent = FOE_NAME + ": " + S.hands[FOE].length + " tiles";
  var backs = "";
  for (var i = 0; i < S.hands[FOE].length; i++) backs += '<span class="dom h back" style="width:28px;height:16px;"></span>';
  el("foerow").innerHTML = backs;
  if (S.spinner) {
    if (S.spinnerDouble) el("spinner").innerHTML = '<span class="dom v spinner"><span class="half">' + pipGrid(S.spinner[0]) + '</span><span class="half">' + pipGrid(S.spinner[1]) + '</span></span>';
    else el("spinner").innerHTML = domHtml(S.spinner, "h", "");
  }
  var placing = PENDING >= 0 && PENDING < S.hands[MY].length;
  if (placing && (!PENDING_ARMS || !PENDING_ARMS.length)) PENDING_ARMS = matchingArms(S, S.hands[MY][PENDING]);
  function armTilesHtml(arm, reverse) {
    var list = S.arms[arm];
    var order = reverse ? list.slice().reverse() : list;
    var out = "";
    for (var j = 0; j < order.length; j++) {
      var t = order[j];
      var isDouble = t[0] === t[1];
      var orient = (arm === "left" || arm === "right") ? (isDouble ? "v" : "h") : (isDouble ? "h" : "v");
      var isEnd = reverse ? (j === 0) : (j === order.length - 1);
      var extra = (isDouble ? "double-mark " : "") + (isEnd ? "endglow" : "");
      var shown = reverse ? [t[1], t[0]] : t;
      out += armTileHtml(shown, orient, extra.trim());
    }
    if (placing && PENDING_ARMS.indexOf(arm) >= 0) { var spot = '<span class="spot" data-arm="' + arm + '">+</span>'; out = reverse ? (spot + out) : (out + spot); }
    return out;
  }
  el("armUp").innerHTML = armTilesHtml("up", true);
  el("armLeft").innerHTML = armTilesHtml("left", true);
  el("armRight").innerHTML = armTilesHtml("right", false);
  el("armDown").innerHTML = armTilesHtml("down", false);
  wireSpots("armUp", "up"); wireSpots("armLeft", "left"); wireSpots("armRight", "right"); wireSpots("armDown", "down");
  var ends = [];
  for (var a = 0; a < ARMS.length; a++) { var e = armEnd(S, ARMS[a]); if (e !== null) ends.push(ARMS[a].toUpperCase() + " " + e); }
  el("endsline").textContent = "SPINNER " + S.spinner[0] + "-" + S.spinner[1] + "  ·  " + ends.join("  ·  ");
  var msg = S.msg;
  if (S.turn !== MY && !S.over && !S.matchOver) msg = "Waiting for " + FOE_NAME + "...";
  if (S.mustPlay >= 0 && S.turn === MY && !S.over && !S.matchOver) msg = "You drew a playable tile - play it.";
  if (placing && S.turn === MY && !S.over && !S.matchOver) msg = "Tap a glowing + spot to place the " + S.hands[MY][PENDING][0] + "-" + S.hands[MY][PENDING][1] + ". Tap the tile again to cancel.";
  el("msg").textContent = msg;
  var acts = "";
  if (!S.over && !S.matchOver && S.turn === MY) {
    var play = playableTiles(S, MY);
    if (S.mustPlay < 0 && play.length === 0 && S.bone.length > 0) acts += '<button class="blue" id="btnDraw">DRAW (' + S.bone.length + ' left)</button>';
    if (S.mustPlay < 0 && play.length === 0 && S.bone.length === 0) acts += '<button class="blue" id="btnPass">PASS</button>';
  }
  if (S.over && !S.matchOver) acts += '<button class="green" id="btnNext">NEXT HAND</button>';
  el("actions").innerHTML = acts;
  var bd = el("btnDraw"); if (bd) bd.onclick = tapDraw;
  var bp = el("btnPass"); if (bp) bp.onclick = tapPass;
  var bn = el("btnNext"); if (bn) bn.onclick = tapNext;
  var playIdx = (S.turn === MY && !S.over && !S.matchOver) ? playableTiles(S, MY) : [];
  var hh = "";
  for (var k = 0; k < S.hands[MY].length; k++) {
    var ok = playIdx.indexOf(k) >= 0;
    var dim = (S.mustPlay >= 0 && k !== S.mustPlay);
    hh += domHtml(S.hands[MY][k], "v", (k === PENDING) ? "picked" : "", ok && (S.mustPlay < 0 || k === S.mustPlay), dim);
  }
  el("hand").innerHTML = hh;
  var btns = el("hand").querySelectorAll("button.dom");
  for (var q = 0; q < btns.length; q++) (function (idx) { btns[q].onclick = function () { tapTile(idx); }; })(q);
  if (S.matchOver) {
    el("overText").textContent = (S.scores[MY] >= 100 ? "YOU WIN THE MATCH!" : FOE_NAME + " WINS THE MATCH.") + " Final: You " + S.scores[MY] + " - " + FOE_NAME + " " + S.scores[FOE] + ".";
    el("overOverlay").style.display = "flex";
  } else {
    el("overOverlay").style.display = "none";
  }
}
el("btnLeave").onclick = function () {
  if (S.over || S.matchOver || (S.spinner === null && S.hands[MY].length === 0)) { postClose(); }
  else el("leaveOverlay").style.display = "flex";
};
el("btnLeaveYes").onclick = function () { el("leaveOverlay").style.display = "none"; postClose(); };
el("btnLeaveNo").onclick = function () { el("leaveOverlay").style.display = "none"; };
el("btnAgain").onclick = function () { el("overOverlay").style.display = "none"; doAction({ t: 'rematch' }); };
el("btnOverLeave").onclick = function () { el("overOverlay").style.display = "none"; postClose(); };
window.addEventListener('domino-state', function (ev) {
  if (ev && ev.detail && ev.detail.actions && ev.detail.actions.length > LOG.length) {
    LOG = ev.detail.actions.slice();
    replay();
  }
});
replay();

</script>
</body>
</html>
`;
