export const DOMINO_HTML = `<!DOCTYPE html>
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
<div class="cpulabel" id="cpulabel"></div>
<div class="cpurow" id="cpurow"></div>
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
<button class="green" id="btnNew">NEW GAME</button>
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

var HW = (typeof window !== "undefined") ? window.hatchWidget : null;
var PIPS = { 0: [], 1: [4], 2: [0, 8], 3: [0, 4, 8], 4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8] };
var ARMS = ["left", "right", "up", "down"];
function buildSet() { var s = []; for (var a = 0; a <= 6; a++) for (var b = a; b <= 6; b++) s.push([a, b]); return s; }
function shuffle(arr) { for (var i = arr.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = arr[i]; arr[i] = arr[j]; arr[j] = t; } return arr; }
function handPips(hand) { var s = 0; for (var i = 0; i < hand.length; i++) s += hand[i][0] + hand[i][1]; return s; }
function highestDouble(hand) { var best = -1; for (var i = 0; i < hand.length; i++) if (hand[i][0] === hand[i][1] && hand[i][0] > best) best = hand[i][0]; return best; }
function bestTile(hand) { var m = null, s = -1; for (var i = 0; i < hand.length; i++) { var p = hand[i][0] + hand[i][1]; if (p > s) { s = p; m = hand[i]; } } return m; }
function defaultState() {
  return { you: [], cpu: [], bone: [], spinner: null, spinnerDouble: true, arms: { left: [], right: [], up: [], down: [] }, turn: "you", youScore: 0, cpuScore: 0, handNo: 1, msg: "", over: false, matchOver: false, passes: 0, mustPlay: -1, pending: -1, pendingArms: [] };
}
var S = defaultState();
if (HW && HW.getState) { try { var raw = HW.getState(S); if (raw && Object.keys(raw).length) S = raw; } catch (e) {} }
function save() { if (HW && HW.setState) { try { HW.setState(S); } catch (e) {} } }
if (HW && HW.addEventListener) { HW.addEventListener("hatch-widget-state", function (ev) { if (ev && ev.detail && ev.detail.state && Object.keys(ev.detail.state).length) { S = ev.detail.state; render(); } }); }
function el(id) { return document.getElementById(id); }
function postClose() { try { if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage("close"); } catch (e) {} }
function armEnd(arm) {
  if (!S.spinnerDouble && (arm === "up" || arm === "down")) return null;
  var list = S.arms[arm];
  if (list.length) return list[list.length - 1][1];
  if (!S.spinner) return null;
  if (!S.spinnerDouble && arm === "right") return S.spinner[1];
  return S.spinner[0];
}
function canPlayOnArm(tile, arm) { var e = armEnd(arm); return e !== null && (tile[0] === e || tile[1] === e); }
function matchingArms(tile) { var out = []; for (var i = 0; i < ARMS.length; i++) if (canPlayOnArm(tile, ARMS[i])) out.push(ARMS[i]); return out; }
function playableTiles(hand) { var out = []; for (var i = 0; i < hand.length; i++) if (matchingArms(hand[i]).length) out.push(i); return out; }
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
function deal() {
  var set, you, cpu, bone, yd, cd, tries = 0;
  do {
    set = shuffle(buildSet());
    you = set.slice(0, 7); cpu = set.slice(7, 14); bone = set.slice(14);
    yd = highestDouble(you); cd = highestDouble(cpu); tries++;
  } while (yd < 0 && cd < 0 && tries < 200);
  S.you = you; S.cpu = cpu; S.bone = bone;
  S.arms = { left: [], right: [], up: [], down: [] };
  S.passes = 0; S.mustPlay = -1; S.pending = -1; S.pendingArms = []; S.over = false;
  var starter, tile;
  if (yd >= 0 && yd >= cd) { starter = "you"; tile = [yd, yd]; S.you.splice(S.you.findIndex(function (t) { return t[0] === yd && t[1] === yd; }), 1); S.spinnerDouble = true; }
  else if (cd >= 0) { starter = "cpu"; tile = [cd, cd]; S.cpu.splice(S.cpu.findIndex(function (t) { return t[0] === cd && t[1] === cd; }), 1); S.spinnerDouble = true; }
  else {
    var yt = bestTile(S.you), ct = bestTile(S.cpu);
    if (yt[0] + yt[1] >= ct[0] + ct[1]) { starter = "you"; tile = yt; S.you.splice(S.you.indexOf(yt), 1); }
    else { starter = "cpu"; tile = ct; S.cpu.splice(S.cpu.indexOf(ct), 1); }
    S.spinnerDouble = false;
  }
  S.spinner = tile;
  S.turn = starter === "you" ? "cpu" : "you";
  S.msg = (starter === "you" ? "You" : "CPU") + " started with the spinner " + tile[0] + "-" + tile[1] + ". " + (S.turn === "you" ? "Your turn." : "CPU to play.");
  save(); render();
  if (S.turn === "cpu") setTimeout(cpuTurn, 900);
}
function newGame() { S = defaultState(); save(); deal(); }
function endHand(winner, points, note) {
  if (winner === "you") S.youScore += points; else S.cpuScore += points;
  S.over = true;
  S.msg = note + " You " + S.youScore + " - CPU " + S.cpuScore + ".";
  if (S.youScore >= 100 || S.cpuScore >= 100) {
    S.matchOver = true;
    el("overText").textContent = (S.youScore >= 100 ? "YOU WIN THE MATCH!" : "CPU WINS THE MATCH.") + " Final: You " + S.youScore + " - CPU " + S.cpuScore + ".";
    if (S.youScore >= 100) if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'center_prize_win', game: 'dominoes', level: 1 }));
    el("overOverlay").style.display = "flex";
  }
  save(); render();
}
function placeOnArm(tile, arm) {
  var e = armEnd(arm);
  var placed = (tile[0] === e) ? [tile[0], tile[1]] : [tile[1], tile[0]];
  S.arms[arm].push(placed);
  S.passes = 0;
}
function afterPlay(player) {
  if (player === "you" && S.you.length === 0) { endHand("you", handPips(S.cpu), "You played your last tile! You win the hand, +" + handPips(S.cpu) + " points."); return true; }
  if (player === "cpu" && S.cpu.length === 0) { endHand("cpu", handPips(S.you), "CPU played its last tile. CPU wins the hand, +" + handPips(S.you) + " points."); return true; }
  return false;
}
function checkBlocked() {
  if (S.bone.length > 0 || S.passes < 2) return false;
  var yp = handPips(S.you), cp = handPips(S.cpu);
  if (yp === cp) { S.over = true; S.msg = "Blocked! Equal pips, no points. You " + S.youScore + " - CPU " + S.cpuScore + "."; save(); render(); return true; }
  if (yp < cp) endHand("you", cp - yp, "Blocked! You had fewer pips (" + yp + " vs " + cp + "), +" + (cp - yp) + " points.");
  else endHand("cpu", yp - cp, "Blocked! CPU had fewer pips (" + cp + " vs " + yp + "), +" + (yp - cp) + " points.");
  return true;
}
function youPlay(i) {
  if (S.turn !== "you" || S.over || S.matchOver) return;
  if (S.mustPlay >= 0 && i !== S.mustPlay) return;
  if (S.pending >= 0 && i === S.pending) { S.pending = -1; S.pendingArms = []; save(); render(); return; }
  var tile = S.you[i];
  var arms = matchingArms(tile);
  if (!arms.length) return;
  if (arms.length === 1) {
    S.you.splice(i, 1);
    placeOnArm(tile, arms[0]);
    S.mustPlay = -1; S.pending = -1; S.pendingArms = [];
    S.msg = "You played " + tile[0] + "-" + tile[1] + " on " + arms[0] + ".";
    if (afterPlay("you")) return;
    S.turn = "cpu"; save(); render();
    setTimeout(cpuTurn, 900);
    return;
  }
  S.pending = i; S.pendingArms = arms;
  S.msg = "Tap a glowing + spot to place the " + tile[0] + "-" + tile[1] + ". Tap the tile again to cancel.";
  save(); render();
}
function placePending(arm) {
  var i = S.pending;
  if (i < 0 || i >= S.you.length) return;
  var tile = S.you[i]; S.you.splice(i, 1);
  placeOnArm(tile, arm);
  S.mustPlay = -1; S.pending = -1; S.pendingArms = [];
  S.msg = "You played " + tile[0] + "-" + tile[1] + " on " + arm + ".";
  if (afterPlay("you")) return;
  S.turn = "cpu"; save(); render();
  setTimeout(cpuTurn, 900);
}
function youDraw() {
  if (S.turn !== "you" || S.over || S.matchOver || S.bone.length === 0) return;
  var t = S.bone.pop();
  S.you.push(t);
  if (matchingArms(t).length) {
    S.mustPlay = S.you.length - 1;
    S.msg = "You drew " + t[0] + "-" + t[1] + " - play it.";
  } else {
    S.mustPlay = -1;
    S.msg = "You drew a tile. Boneyard: " + S.bone.length + ".";
  }
  save(); render();
}
function youPass() {
  if (S.turn !== "you" || S.over || S.matchOver) return;
  S.passes++;
  S.msg = "You pass. Boneyard is empty.";
  S.turn = "cpu"; save(); render();
  setTimeout(cpuTurn, 900);
}
function cpuTurn() {
  if (S.turn !== "cpu" || S.over || S.matchOver) return;
  var play = playableTiles(S.cpu);
  while (play.length === 0 && S.bone.length > 0) {
    var t = S.bone.pop();
    S.cpu.push(t);
    if (matchingArms(t).length) play = [S.cpu.length - 1];
    else play = [];
  }
  if (play.length === 0) {
    S.passes++;
    S.msg = "CPU passes. Boneyard is empty.";
    if (checkBlocked()) return;
    S.turn = "you"; save(); render(); return;
  }
  var best = play[0], bestSum = -1;
  for (var i = 0; i < play.length; i++) { var t2 = S.cpu[play[i]], s = t2[0] + t2[1]; if (s > bestSum) { bestSum = s; best = play[i]; } }
  var tile = S.cpu[best]; S.cpu.splice(best, 1);
  var arms = matchingArms(tile);
  var arm = arms[0];
  placeOnArm(tile, arm);
  S.msg = "CPU played " + tile[0] + "-" + tile[1] + " on " + arm + ".";
  if (afterPlay("cpu")) return;
  S.turn = "you"; save(); render();
}

function armTileHtml(tile, orient, extra) {
  var cls = "dom " + orient + (extra ? " " + extra : "");
  return '<span class="' + cls + '"><span class="half">' + pipGrid(tile[0]) + '</span><span class="half">' + pipGrid(tile[1]) + '</span></span>';
}


function wireSpots(elId, arm) {
  var list = document.getElementById(elId).querySelectorAll(".spot");
  for (var s = 0; s < list.length; s++) (function (spot) { spot.onclick = function () { placePending(arm); }; })(list[s]);
}

function render() {
  el("scorebar").textContent = "YOU " + S.youScore + "  |  CPU " + S.cpuScore + "  |  First to 100  |  Hand " + S.handNo;
  el("cpulabel").textContent = "CPU: " + S.cpu.length + " tiles";
  var backs = "";
  for (var i = 0; i < S.cpu.length; i++) backs += '<span class="dom h back" style="width:28px;height:16px;"></span>';
  el("cpurow").innerHTML = backs;
  if (S.spinner) {
    if (S.spinnerDouble) el("spinner").innerHTML = '<span class="dom v spinner"><span class="half">' + pipGrid(S.spinner[0]) + '</span><span class="half">' + pipGrid(S.spinner[1]) + '</span></span>';
    else el("spinner").innerHTML = domHtml(S.spinner, "h", "");
  }
  var placing = S.pending >= 0 && S.pending < S.you.length;
  if (placing && (!S.pendingArms || !S.pendingArms.length)) S.pendingArms = matchingArms(S.you[S.pending]);
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
    if (placing && S.pendingArms.indexOf(arm) >= 0) { var spot = '<span class="spot" data-arm="' + arm + '">+</span>'; out = reverse ? (spot + out) : (out + spot); }
    return out;
  }
  el("armUp").innerHTML = armTilesHtml("up", true);
  el("armLeft").innerHTML = armTilesHtml("left", true);
  el("armRight").innerHTML = armTilesHtml("right", false);
  el("armDown").innerHTML = armTilesHtml("down", false);
  wireSpots("armUp", "up"); wireSpots("armLeft", "left"); wireSpots("armRight", "right"); wireSpots("armDown", "down");
  var ends = [];
  for (var a = 0; a < ARMS.length; a++) { var e = armEnd(ARMS[a]); if (e !== null) ends.push(ARMS[a].toUpperCase() + " " + e); }
  el("endsline").textContent = "SPINNER " + S.spinner[0] + "-" + S.spinner[1] + "  ·  " + ends.join("  ·  ");
  var msg = S.msg;
  if (S.mustPlay >= 0 && S.turn === "you" && !S.over && !S.matchOver) msg = "You drew a playable tile - play it.";
  if (placing && S.turn === "you" && !S.over && !S.matchOver) msg = "Tap a glowing + spot to place the " + S.you[S.pending][0] + "-" + S.you[S.pending][1] + ". Tap the tile again to cancel.";
  el("msg").textContent = msg;
  var acts = "";
  if (!S.over && !S.matchOver && S.turn === "you") {
    var play = playableTiles(S.you);
    if (S.mustPlay < 0 && play.length === 0 && S.bone.length > 0) acts += '<button class="blue" id="btnDraw">DRAW (' + S.bone.length + ' left)</button>';
    if (S.mustPlay < 0 && play.length === 0 && S.bone.length === 0) acts += '<button class="blue" id="btnPass">PASS</button>';
  }
  if (S.over && !S.matchOver) acts += '<button class="green" id="btnNext">NEXT HAND</button>';
  el("actions").innerHTML = acts;
  var bd = el("btnDraw"); if (bd) bd.onclick = youDraw;
  var bp = el("btnPass"); if (bp) bp.onclick = youPass;
  var bn = el("btnNext"); if (bn) bn.onclick = function () { S.handNo++; save(); deal(); };
  var playIdx = (S.turn === "you" && !S.over && !S.matchOver) ? playableTiles(S.you) : [];
  var hh = "";
  for (var k = 0; k < S.you.length; k++) {
    var ok = playIdx.indexOf(k) >= 0;
    var dim = (S.mustPlay >= 0 && k !== S.mustPlay);
    hh += domHtml(S.you[k], "v", (k === S.pending) ? "picked" : "", ok && (S.mustPlay < 0 || k === S.mustPlay), dim);
  }
  el("hand").innerHTML = hh;
  var btns = el("hand").querySelectorAll("button.dom");
  for (var q = 0; q < btns.length; q++) (function (idx) { btns[q].onclick = function () { youPlay(idx); }; })(q);
}
el("btnNew").onclick = newGame;
el("btnLeave").onclick = function () {
  if (S.over || S.matchOver || (S.spinner === null && S.you.length === 0)) { postClose(); }
  else el("leaveOverlay").style.display = "flex";
};
el("btnLeaveYes").onclick = function () { el("leaveOverlay").style.display = "none"; postClose(); };
el("btnLeaveNo").onclick = function () { el("leaveOverlay").style.display = "none"; };
el("btnAgain").onclick = function () { el("overOverlay").style.display = "none"; newGame(); };
el("btnOverLeave").onclick = function () { el("overOverlay").style.display = "none"; postClose(); };
if (S.spinner === null && S.you.length === 0 && !S.matchOver) deal();
else render();

</script>
</body>
</html>
`;
