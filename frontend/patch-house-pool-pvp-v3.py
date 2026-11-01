"""Street Legends frontend: pool PvP - tap menu gains PLAYER VS PLAYER, rooms + chat + PvP game.
Run from repo root: python3 frontend/patch-house-pool-pvp-v3.py
Idempotent - safe to re-run.
V3 fixes two v2 misses found in the user's terminal output: (1) the import helper now handles
multi-line imports, double quotes, default+named imports, and split imports, so the PvP
components are no longer skipped; (2) the menu guard now checks the menu COMPONENT itself
for the button (v2 skipped the whole menu fix because the RENDER mentions onPlayPvp, even
though the component never got the button).
FRONTEND ONLY - needs a rebuild + new AAB. Rooms work once the backend pool-rooms
endpoints are live; if the backend is not live yet, the rooms screen says so instead of crashing.
"""
import re

INDEX = "frontend/app/(tabs)/index.tsx"
PVP_TS = "frontend/components/PoolGamePvpHtml.ts"
API_BASE = "https://gta-quest-map.emergent.host"
PVP_TS_CONTENT = """export const POOL_PVP_HTML = `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<style>
body { margin: 0; background: #111111; color: #ffffff; font-family: sans-serif; }
#wrap { max-width: 430px; margin: 0 auto; padding: 10px; text-align: center; }
#header { display: flex; justify-content: space-between; font-weight: 800; font-size: 15px; margin-bottom: 6px; }
#header .turn { color: #f39c12; outline: 2px solid #f39c12; border-radius: 6px; padding: 2px 6px; }
#msg { color: #cccccc; font-size: 12px; min-height: 16px; margin-bottom: 8px; }
#cv { width: 100%; max-width: 400px; height: auto; display: block; margin: 0 auto; touch-action: none; border-radius: 10px; }
#tray { margin-top: 10px; text-align: left; }
#tray .row { display: flex; align-items: center; gap: 4px; margin-bottom: 4px; min-height: 22px; flex-wrap: wrap; }
#tray .lbl { font-weight: 800; font-size: 12px; min-width: 44px; }
.mini { width: 20px; height: 20px; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; font-size: 9px; font-weight: 800; color: #111111; border: 1px solid #555555; }
.mini.latest { outline: 2px solid #f39c12; }
.mini.stripe { background: #ffffff; }
#btns { display: flex; gap: 8px; justify-content: center; margin-top: 12px; flex-wrap: wrap; }
#btns button { background: #444444; color: #ffffff; font-weight: 800; border: 0; border-radius: 8px; padding: 10px 14px; font-size: 12px; }
#btns button.leave { background: #e74c3c; }
#hint { color: #999999; font-size: 11px; margin-top: 8px; }
</style>
</head>
<body>
<div id="wrap">
<div id="header"><span id="youLbl">YOU</span><span id="foeLbl">FRIEND</span></div>
<div id="msg">Waiting...</div>
<canvas id="cv" width="800" height="520"></canvas>
<div id="tray">
<div class="row"><span class="lbl" id="trayYouLbl">YOU</span><span id="trayYou"></span></div>
<div class="row"><span class="lbl" id="trayFoeLbl">FRIEND</span><span id="trayFoe"></span></div>
</div>
<div id="btns">
<button id="btnRestart">RESTART</button>
<button id="btnSound">SOUND ON</button>
<button id="btnLeave" class="leave">LEAVE TABLE</button>
</div>
<div id="hint">Play against your friend. Pocket your group, then the 8, to win. Chat lives on the room screen.</div>
</div>
<script>
(function () {
var CFG = window.POOL_PVP || { me: 'you', foe: 'friend', foeName: 'FRIEND', hostId: 'you' };
var ME = CFG.me, FOE = CFG.foe, FOENAME = CFG.foeName, HOST = CFG.hostId;
var cv = document.getElementById('cv');
var ctx = cv.getContext('2d');
ctx.scale(2, 2);
var W = 340, H = 200, OX = 30, OY = 30, BALL_R = 9, POCKET_R = 15;
var POCKETS = [{ x: 6, y: 6 }, { x: 170, y: 2 }, { x: 334, y: 6 }, { x: 6, y: 194 }, { x: 170, y: 198 }, { x: 334, y: 194 }];
var RACK_ORDER = [1, 9, 2, 10, 8, 3, 11, 4, 14, 5, 6, 12, 7, 13, 15];
var COLORS = { 1: '#f9c80e', 2: '#1e88e5', 3: '#e53935', 4: '#7b1fa2', 5: '#f57c00', 6: '#2e7d32', 7: '#6d1f1f', 8: '#111111' };
var balls = [], turn = HOST, groupsMap = {}, trayMe = [], trayFoe = [];
var moving = false, striking = false, aim = null, dragStart = null;
var gameOver = false, winner = null, soundOn = true, breakShot = true;
var shotPocketed = [], shotScratch = false;
var audioCtx = null, lastCushion = 0;
var msgEl = document.getElementById('msg'), youLbl = document.getElementById('youLbl'), foeLbl = document.getElementById('foeLbl');
var trayYou = document.getElementById('trayYou'), trayFoe = document.getElementById('trayFoe');
document.getElementById('trayFoeLbl').textContent = FOENAME;
foeLbl.textContent = FOENAME;

function setMsg(t) { msgEl.textContent = t; }
function groupOf(num) { if (num === 8) return 'eight'; if (num >= 1 && num <= 7) return 'solid'; return 'stripe'; }
function groupName(g) { if (g === 'solid') return 'Solids'; if (g === 'stripe') return 'Stripes'; return ''; }
function myGroup() { return groupsMap[ME] || null; }
function foeGroup() { return groupsMap[FOE] || null; }

function makeBalls() {
  var list = [{ id: 'cue', num: 0, x: 85, y: 100, vx: 0, vy: 0, pocketed: false }];
  var ax = 231.2, ay = 100, gap = 20, idx = 0;
  var rows = [1, 2, 3, 4, 5];
  for (var r = 0; r < rows.length; r++) {
    for (var i = 0; i < rows[r]; i++) {
      var num = RACK_ORDER[idx++];
      list.push({ id: 'b' + num, num: num, x: ax + r * gap * 0.866, y: ay + (i - (rows[r] - 1) / 2) * gap, vx: 0, vy: 0, pocketed: false });
    }
  }
  return list;
}

function resetLocal(firstMsg, postIt) {
  balls = makeBalls();
  turn = HOST; groupsMap = {}; trayMe = []; trayFoe = [];
  moving = false; striking = false; aim = null; dragStart = null;
  gameOver = false; winner = null; breakShot = true;
  shotPocketed = []; shotScratch = false;
  trayYou.innerHTML = ''; trayFoe.innerHTML = '';
  setMsg(firstMsg);
  updateHeader();
  if (postIt) postPvpState();
}

function updateHeader() {
  youLbl.textContent = 'YOU' + (myGroup() ? ' (' + groupName(myGroup()) + ')' : '');
  foeLbl.textContent = FOENAME + (foeGroup() ? ' (' + groupName(foeGroup()) + ')' : '');
  youLbl.className = turn === ME && !gameOver ? 'turn' : '';
  foeLbl.className = turn === FOE && !gameOver ? 'turn' : '';
}

function ensureAudio() {
  if (!audioCtx) { try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { audioCtx = null; } }
  if (audioCtx && audioCtx.state === 'suspended') { audioCtx.resume(); }
}

function playClick(intensity) {
  if (!soundOn || !audioCtx) return;
  var t = audioCtx.currentTime;
  var dur = 0.012;
  var buf = audioCtx.createBuffer(1, audioCtx.sampleRate * dur, audioCtx.sampleRate);
  var d = buf.getChannelData(0);
  for (var i = 0; i < d.length; i++) { d[i] = (Math.random() * 2 - 1) * (1 - i / d.length); }
  var src = audioCtx.createBufferSource(); src.buffer = buf;
  var bp = audioCtx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 2000; bp.Q.value = 0.7;
  var g = audioCtx.createGain(); g.gain.setValueAtTime(Math.min(0.7, 0.2 + intensity * 0.5), t);
  src.connect(bp); bp.connect(g); g.connect(audioCtx.destination); src.start(t);
  var osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 650;
  var og = audioCtx.createGain(); og.gain.setValueAtTime(Math.min(0.5, 0.15 + intensity * 0.35), t);
  og.gain.exponentialRampToValueAtTime(0.001, t + 0.08);
  osc.connect(og); og.connect(audioCtx.destination); osc.start(t); osc.stop(t + 0.09);
}

function playCueHit() {
  if (!soundOn || !audioCtx) return;
  var t = audioCtx.currentTime;
  var dur = 0.01;
  var buf = audioCtx.createBuffer(1, audioCtx.sampleRate * dur, audioCtx.sampleRate);
  var d = buf.getChannelData(0);
  for (var i = 0; i < d.length; i++) { d[i] = (Math.random() * 2 - 1) * (1 - i / d.length); }
  var src = audioCtx.createBufferSource(); src.buffer = buf;
  var bp = audioCtx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 1800; bp.Q.value = 0.8;
  var g = audioCtx.createGain(); g.gain.setValueAtTime(0.5, t);
  src.connect(bp); bp.connect(g); g.connect(audioCtx.destination); src.start(t);
  var osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 800;
  var og = audioCtx.createGain(); og.gain.setValueAtTime(0.3, t);
  og.gain.exponentialRampToValueAtTime(0.001, t + 0.06);
  osc.connect(og); og.connect(audioCtx.destination); osc.start(t); osc.stop(t + 0.07);
}

function playCushion(speed) {
  if (!soundOn || !audioCtx) return;
  if (speed < 1.2) return;
  var now = Date.now();
  if (now - lastCushion < 60) return;
  lastCushion = now;
  var t = audioCtx.currentTime;
  var osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 130;
  var g = audioCtx.createGain(); g.gain.setValueAtTime(Math.min(0.4, speed * 0.05), t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.12);
  osc.connect(g); g.connect(audioCtx.destination); osc.start(t); osc.stop(t + 0.13);
}

function playPocket() {
  if (!soundOn || !audioCtx) return;
  var t = audioCtx.currentTime;
  var osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 95;
  var g = audioCtx.createGain(); g.gain.setValueAtTime(0.5, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.15);
  osc.connect(g); g.connect(audioCtx.destination); osc.start(t); osc.stop(t + 0.16);
  var dur = 0.08;
  var buf = audioCtx.createBuffer(1, audioCtx.sampleRate * dur, audioCtx.sampleRate);
  var d = buf.getChannelData(0);
  for (var i = 0; i < d.length; i++) { d[i] = (Math.random() * 2 - 1) * (1 - i / d.length) * 0.3; }
  var src = audioCtx.createBufferSource(); src.buffer = buf;
  var bp = audioCtx.createBiquadFilter(); bp.type = 'bandpass'; bp.frequency.value = 900; bp.Q.value = 1;
  var g2 = audioCtx.createGain(); g2.gain.setValueAtTime(0.3, t + 0.05);
  src.connect(bp); bp.connect(g2); g2.connect(audioCtx.destination); src.start(t + 0.05);
}

function makeMini(num, latest) {
  var span = document.createElement('span');
  span.className = 'mini' + (num >= 9 && num <= 15 ? ' stripe' : '') + (latest ? ' latest' : '');
  if (num >= 1 && num <= 7) span.style.background = COLORS[num];
  if (num >= 9 && num <= 15) span.style.background = '#ffffff';
  if (num === 8) span.style.background = '#111111';
  if (num >= 9 && num <= 15) {
    span.style.borderTop = '4px solid ' + COLORS[num - 8];
    span.style.borderBottom = '4px solid ' + COLORS[num - 8];
  }
  if (num === 8) span.style.color = '#ffffff';
  span.textContent = String(num);
  return span;
}

function addToTray(shooterId, num) {
  var row = shooterId === ME ? trayYou : trayFoe;
  var prev = row.querySelector('.latest');
  if (prev) prev.classList.remove('latest');
  row.appendChild(makeMini(num, true));
}

function rebuildTray() {
  trayYou.innerHTML = ''; trayFoe.innerHTML = '';
  for (var i = 0; i < trayMe.length; i++) trayYou.appendChild(makeMini(trayMe[i], i === trayMe.length - 1));
  for (var j = 0; j < trayFoe.length; j++) trayFoe.appendChild(makeMini(trayFoe[j], j === trayFoe.length - 1));
}

function buildState() {
  var bs = [];
  for (var i = 0; i < balls.length; i++) bs.push({ num: balls[i].num, x: balls[i].x, y: balls[i].y, pocketed: balls[i].pocketed });
  var gm = {};
  if (groupsMap[ME]) gm[ME] = groupsMap[ME];
  if (groupsMap[FOE]) gm[FOE] = groupsMap[FOE];
  var tr = {};
  tr[ME] = trayMe.slice(); tr[FOE] = trayFoe.slice();
  return { balls: bs, groups: gm, turn: turn, trays: tr, gameOver: gameOver, winner: winner, breakShot: breakShot };
}

function postPvpState() {
  if (window.ReactNativeWebView) {
    window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'pool-shot', state: buildState() }));
  }
}

function applyPvpState(s) {
  if (!s) return;
  var nb = [];
  for (var i = 0; i < s.balls.length; i++) {
    var b = s.balls[i];
    nb.push({ id: b.num === 0 ? 'cue' : 'b' + b.num, num: b.num, x: b.x, y: b.y, vx: 0, vy: 0, pocketed: b.pocketed });
  }
  balls = nb;
  groupsMap = s.groups || {};
  turn = s.turn;
  trayMe = (s.trays && s.trays[ME]) || [];
  trayFoe = (s.trays && s.trays[FOE]) || [];
  gameOver = !!s.gameOver;
  winner = s.winner || null;
  breakShot = !!s.breakShot;
  moving = false; striking = false; aim = null; dragStart = null;
  shotPocketed = []; shotScratch = false;
  rebuildTray();
  updateHeader();
  if (gameOver) {
    setMsg(winner === ME ? 'YOU WIN! Table cleared!' : FOENAME + ' WINS!');
  } else if (turn === ME) {
    setMsg('Your turn.');
  } else {
    setMsg('Waiting for ' + FOENAME + '...');
  }
}

window.addEventListener('pool-state', function (e) { applyPvpState(e.detail); });

function inGap(b, nx, ny) {
  for (var i = 0; i < POCKETS.length; i++) {
    var p = POCKETS[i];
    if (ny === -1 && p.y < 20 && Math.abs(b.x - p.x) < POCKET_R + 2 && b.y < 30) return true;
    if (ny === 1 && p.y > 180 && Math.abs(b.x - p.x) < POCKET_R + 2 && b.y > 170) return true;
    if (nx === -1 && p.x < 20 && Math.abs(b.y - p.y) < POCKET_R + 2 && b.x < 30) return true;
    if (nx === 1 && p.x > 320 && Math.abs(b.y - p.y) < POCKET_R + 2 && b.x > 310) return true;
  }
  return false;
}

function distSeg(px, py, x1, y1, x2, y2) {
  var dx = x2 - x1, dy = y2 - y1;
  var len2 = dx * dx + dy * dy;
  var t = 0;
  if (len2 > 0) { t = ((px - x1) * dx + (py - y1) * dy) / len2; if (t < 0) t = 0; if (t > 1) t = 1; }
  var cx = x1 + t * dx, cy = y1 + t * dy;
  return Math.hypot(px - cx, py - cy);
}

function step() {
  var anyMoving = false;
  for (var i = 0; i < balls.length; i++) {
    var b = balls[i];
    if (b.pocketed) continue;
    var ox = b.x, oy = b.y;
    b.x += b.vx; b.y += b.vy;
    b.vx *= 0.985; b.vy *= 0.985;
    if (Math.hypot(b.vx, b.vy) < 0.05) { b.vx = 0; b.vy = 0; } else anyMoving = true;
    var dropped = false;
    for (var p = 0; p < POCKETS.length; p++) {
      if (distSeg(POCKETS[p].x, POCKETS[p].y, ox, oy, b.x, b.y) < POCKET_R) { dropped = true; break; }
    }
    if (dropped) {
      b.pocketed = true; b.vx = 0; b.vy = 0;
      playPocket();
      if (b.num === 0) { shotScratch = true; } else { shotPocketed.push(b.num); addToTray(ME, b.num); }
      continue;
    }
    if (b.x < 10 + BALL_R) {
      if (!inGap(b, -1, 0)) { b.x = 10 + BALL_R; if (b.vx < 0) { playCushion(Math.abs(b.vx)); b.vx = Math.abs(b.vx); } }
      else if (b.x < BALL_R) { b.x = BALL_R; b.vx = Math.abs(b.vx); }
    }
    if (b.x > W - 10 - BALL_R) {
      if (!inGap(b, 1, 0)) { b.x = W - 10 - BALL_R; if (b.vx > 0) { playCushion(Math.abs(b.vx)); b.vx = -Math.abs(b.vx); } }
      else if (b.x > W - BALL_R) { b.x = W - BALL_R; b.vx = -Math.abs(b.vx); }
    }
    if (b.y < 10 + BALL_R) {
      if (!inGap(b, 0, -1)) { b.y = 10 + BALL_R; if (b.vy < 0) { playCushion(Math.abs(b.vy)); b.vy = Math.abs(b.vy); } }
      else if (b.y < BALL_R) { b.y = BALL_R; b.vy = Math.abs(b.vy); }
    }
    if (b.y > H - 10 - BALL_R) {
      if (!inGap(b, 0, 1)) { b.y = H - 10 - BALL_R; if (b.vy > 0) { playCushion(Math.abs(b.vy)); b.vy = -Math.abs(b.vy); } }
      else if (b.y > H - BALL_R) { b.y = H - BALL_R; b.vy = -Math.abs(b.vy); }
    }
  }
  for (var a = 0; a < balls.length; a++) {
    for (var c = a + 1; c < balls.length; c++) {
      var A = balls[a], C = balls[c];
      if (A.pocketed || C.pocketed) continue;
      var dx = C.x - A.x, dy = C.y - A.y;
      var dist = Math.hypot(dx, dy);
      if (dist > 0 && dist < BALL_R * 2) {
        var nx = dx / dist, ny = dy / dist;
        var overlap = BALL_R * 2 - dist;
        A.x -= nx * overlap / 2; A.y -= ny * overlap / 2;
        C.x += nx * overlap / 2; C.y += ny * overlap / 2;
        var imp = (A.vx - C.vx) * nx + (A.vy - C.vy) * ny;
        if (imp > 0) {
          playClick(Math.min(1, imp / 10));
          A.vx -= imp * nx; A.vy -= imp * ny;
          C.vx += imp * nx; C.vy += imp * ny;
        }
      }
    }
  }
  if (!anyMoving && moving) {
    moving = false;
    evaluateShotPvp();
  }
}

function remainingOf(pid) {
  var g = groupsMap[pid];
  if (!g) return 99;
  var n = 0;
  for (var i = 0; i < balls.length; i++) {
    var b = balls[i];
    if (!b.pocketed && b.num !== 0 && groupOf(b.num) === g) n++;
  }
  return n;
}

function endGamePvp(w) {
  gameOver = true;
  winner = w;
  updateHeader();
  setMsg(w === ME ? 'YOU WIN! Table cleared!' : FOENAME + ' WINS!');
  postPvpState();
}

function evaluateShotPvp() {
  var pocketed = shotPocketed.slice();
  shotPocketed = [];
  var scratch = shotScratch; shotScratch = false;
  var eightPocketed = pocketed.indexOf(8) >= 0;
  var wasBreak = breakShot; breakShot = false;

  if (scratch) {
    var cue = null;
    for (var i = 0; i < balls.length; i++) { if (balls[i].num === 0) cue = balls[i]; }
    if (cue) { cue.pocketed = false; cue.x = 85; cue.y = 100; cue.vx = 0; cue.vy = 0; }
    setMsg('Foul! Cue ball pocketed. It is back on the table.');
    turn = FOE;
    updateHeader();
    postPvpState();
    return;
  }

  if (eightPocketed) {
    if (wasBreak) {
      resetLocal('8 on the break! Re-rack. ' + (HOST === ME ? 'You break again.' : FOENAME + ' breaks again.'), true);
      return;
    }
    if (myGroup() && remainingOf(ME) === 0) {
      endGamePvp(ME);
    } else {
      endGamePvp(FOE);
    }
    return;
  }

  if (!myGroup()) {
    var first = null;
    for (var j = 0; j < pocketed.length; j++) { if (pocketed[j] !== 8) { first = pocketed[j]; break; } }
    if (first !== null) {
      var g = groupOf(first);
      groupsMap[ME] = g;
      groupsMap[FOE] = g === 'solid' ? 'stripe' : 'solid';
      updateHeader();
      setMsg('You are ' + groupName(g) + '. Your turn again.');
      postPvpState();
      return;
    }
    turn = FOE;
    updateHeader();
    setMsg('Waiting for ' + FOENAME + '...');
    postPvpState();
    return;
  }

  var ownPocketed = 0;
  for (var k = 0; k < pocketed.length; k++) { if (groupOf(pocketed[k]) === myGroup()) ownPocketed++; }
  if (ownPocketed > 0) {
    setMsg('Your turn again.');
    updateHeader();
    postPvpState();
    return;
  }
  turn = FOE;
  updateHeader();
  setMsg('Waiting for ' + FOENAME + '...');
  postPvpState();
}

function drawBall(b) {
  var x = OX + b.x, y = OY + b.y;
  ctx.beginPath();
  ctx.ellipse(x + 1.5, y + 2, BALL_R, BALL_R * 0.9, 0, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.fill();
  if (b.num === 0) {
    ctx.beginPath(); ctx.arc(x, y, BALL_R, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff'; ctx.fill();
  } else if (b.num >= 9 && b.num <= 15) {
    ctx.beginPath(); ctx.arc(x, y, BALL_R, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff'; ctx.fill();
    ctx.save();
    ctx.beginPath(); ctx.arc(x, y, BALL_R, 0, Math.PI * 2); ctx.clip();
    ctx.fillStyle = COLORS[b.num - 8];
    ctx.fillRect(x - BALL_R, y - 4, BALL_R * 2, 8);
    ctx.restore();
  } else {
    ctx.beginPath(); ctx.arc(x, y, BALL_R, 0, Math.PI * 2);
    ctx.fillStyle = COLORS[b.num]; ctx.fill();
  }
  var g = ctx.createRadialGradient(x - 3, y - 3, 1, x, y, BALL_R);
  g.addColorStop(0, 'rgba(255,255,255,0.85)');
  g.addColorStop(0.25, 'rgba(255,255,255,0.15)');
  g.addColorStop(1, 'rgba(0,0,0,0.25)');
  ctx.beginPath(); ctx.arc(x, y, BALL_R, 0, Math.PI * 2);
  ctx.fillStyle = g; ctx.fill();
  if (b.num !== 0) {
    ctx.beginPath(); ctx.arc(x, y, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff'; ctx.fill();
    ctx.fillStyle = '#111111';
    ctx.font = 'bold 7px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.fillText(String(b.num), x, y);
  }
}

function defaultAim() {
  var cue = null;
  for (var i = 0; i < balls.length; i++) { if (balls[i].num === 0) cue = balls[i]; }
  if (!cue || cue.pocketed) return null;
  var best = null, bestD = 1e9;
  for (var i = 0; i < balls.length; i++) {
    var b = balls[i];
    if (b.pocketed || b.num === 0) continue;
    var d = Math.hypot(b.x - cue.x, b.y - cue.y);
    if (d < bestD) { bestD = d; best = b; }
  }
  if (!best) return null;
  return Math.atan2(best.y - cue.y, best.x - cue.x);
}

function drawGuide() {
  var cue = null;
  for (var i = 0; i < balls.length; i++) { if (balls[i].num === 0) cue = balls[i]; }
  if (!cue || cue.pocketed) return;
  var angle = aim ? aim.angle : defaultAim();
  if (angle === null) return;
  var ux = Math.cos(angle), uy = Math.sin(angle);
  var hit = null, hitDist = 1e9;
  for (var i = 0; i < balls.length; i++) {
    var b = balls[i];
    if (b.pocketed || b.num === 0) continue;
    var dx = b.x - cue.x, dy = b.y - cue.y;
    var along = dx * ux + dy * uy;
    if (along <= 0) continue;
    var perp = Math.abs(dx * uy - dy * ux);
    if (perp < BALL_R * 2 && along < hitDist) { hitDist = along; hit = b; }
  }
  var endX, endY;
  if (hit) {
    var contact = hitDist - BALL_R * 2;
    if (contact < BALL_R + 2) contact = BALL_R + 2;
    endX = cue.x + ux * contact; endY = cue.y + uy * contact;
  } else {
    var t = 1e9;
    if (ux > 0.001) t = Math.min(t, (W - 10 - BALL_R - cue.x) / ux);
    if (ux < -0.001) t = Math.min(t, (10 + BALL_R - cue.x) / ux);
    if (uy > 0.001) t = Math.min(t, (H - 10 - BALL_R - cue.y) / uy);
    if (uy < -0.001) t = Math.min(t, (10 + BALL_R - cue.y) / uy);
    if (t === 1e9 || t < 0) t = 60;
    endX = cue.x + ux * t; endY = cue.y + uy * t;
  }
  ctx.strokeStyle = 'rgba(255,255,255,0.9)';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(OX + cue.x + ux * (BALL_R + 2), OY + cue.y + uy * (BALL_R + 2));
  ctx.lineTo(OX + endX, OY + endY);
  ctx.stroke();
  if (hit) {
    var ox = hit.x - endX, oy = hit.y - endY;
    var od = Math.hypot(ox, oy);
    if (od > 0) {
      ctx.strokeStyle = 'rgba(255,255,255,0.6)';
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(OX + hit.x, OY + hit.y);
      ctx.lineTo(OX + hit.x + ox / od * 45, OY + hit.y + oy / od * 45);
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }
}

function drawStick() {
  if (turn !== ME || moving || striking || gameOver) return;
  var cue = null;
  for (var i = 0; i < balls.length; i++) { if (balls[i].num === 0) cue = balls[i]; }
  if (!cue || cue.pocketed) return;
  var angle = aim ? aim.angle : defaultAim();
  if (angle === null) return;
  var back = aim ? aim.stickBack : 0;
  var ux = Math.cos(angle), uy = Math.sin(angle);
  ux = -ux; uy = -uy;
  var sx = OX + cue.x + ux * (BALL_R + 4 + back);
  var sy = OY + cue.y + uy * (BALL_R + 4 + back);
  var len = 150;
  var px = -uy, py = ux;
  function seg(d0, d1, w0, w1, color) {
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(sx + ux * d0 + px * w0, sy + uy * d0 + py * w0);
    ctx.lineTo(sx + ux * d1 + px * w1, sy + uy * d1 + py * w1);
    ctx.lineTo(sx + ux * d1 - px * w1, sy + uy * d1 - py * w1);
    ctx.lineTo(sx + ux * d0 - px * w0, sy + uy * d0 - py * w0);
    ctx.closePath();
    ctx.fill();
  }
  ctx.fillStyle = 'rgba(0,0,0,0.3)';
  ctx.beginPath();
  ctx.ellipse(sx + ux * len / 2 + 2, sy + uy * len / 2 + 3, len / 2, 3, angle, 0, Math.PI * 2);
  ctx.fill();
  seg(0, 4, 2.0, 2.1, '#3b82c4');
  seg(4, 11, 2.1, 2.3, '#f5ead2');
  var shaftGrad = ctx.createLinearGradient(sx, sy, sx + ux * 105, sy + uy * 105);
  shaftGrad.addColorStop(0, '#eed9a8');
  shaftGrad.addColorStop(1, '#c9a05e');
  seg(11, 105, 2.3, 3.2, shaftGrad);
  seg(105, 140, 3.2, 3.6, '#2e1f14');
  seg(140, 144, 3.6, 3.7, '#5a4028');
  seg(144, 150, 3.7, 3.8, '#1a120c');
}

function draw() {
  ctx.clearRect(0, 0, 400, 260);
  var floor = ctx.createLinearGradient(0, 0, 0, 260);
  floor.addColorStop(0, '#1c1c1c');
  floor.addColorStop(1, '#0a0a0a');
  ctx.fillStyle = floor;
  ctx.fillRect(0, 0, 400, 260);
  var wood = ctx.createLinearGradient(OX, OY, OX, OY + H);
  wood.addColorStop(0, '#8d5a2b');
  wood.addColorStop(1, '#6d4420');
  ctx.fillStyle = wood;
  roundRect(OX, OY, W, H, 14);
  ctx.fill();
  ctx.strokeStyle = '#d4af37';
  ctx.lineWidth = 2;
  roundRect(OX + 4, OY + 4, W - 8, H - 8, 10);
  ctx.stroke();
  var felt = ctx.createRadialGradient(OX + W / 2, OY + H / 2, 20, OX + W / 2, OY + H / 2, W / 2);
  felt.addColorStop(0, '#2e7d32');
  felt.addColorStop(1, '#1b5e20');
  ctx.fillStyle = felt;
  roundRect(OX + 10, OY + 10, W - 20, H - 20, 8);
  ctx.fill();
  for (var p = 0; p < POCKETS.length; p++) {
    var px = OX + POCKETS[p].x, py = OY + POCKETS[p].y;
    var pg = ctx.createRadialGradient(px, py, 2, px, py, POCKET_R);
    pg.addColorStop(0, '#000000');
    pg.addColorStop(1, '#222222');
    ctx.beginPath(); ctx.arc(px, py, POCKET_R, 0, Math.PI * 2);
    ctx.fillStyle = pg; ctx.fill();
  }
  for (var i = 0; i < balls.length; i++) {
    if (!balls[i].pocketed) drawBall(balls[i]);
  }
  if (!moving && !gameOver && turn === ME) drawGuide();
  drawStick();
}

function roundRect(x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

function toTable(e) {
  var rect = cv.getBoundingClientRect();
  var lx = (e.clientX - rect.left) * 400 / rect.width;
  var ly = (e.clientY - rect.top) * 260 / rect.height;
  return { x: lx - OX, y: ly - OY };
}

cv.addEventListener('pointerdown', function (e) {
  ensureAudio();
  if (moving || striking || gameOver || turn !== ME) return;
  var cue = null;
  for (var i = 0; i < balls.length; i++) { if (balls[i].num === 0) cue = balls[i]; }
  if (!cue || cue.pocketed) return;
  dragStart = toTable(e);
  aim = { angle: defaultAim() || 0, power: 0, stickBack: 0 };
});
cv.addEventListener('pointermove', function (e) {
  if (!dragStart || moving || striking || gameOver || turn !== ME) return;
  var p = toTable(e);
  var dx = p.x - dragStart.x, dy = p.y - dragStart.y;
  var dist = Math.hypot(dx, dy);
  if (dist < 5) { aim = null; return; }
  var angle = Math.atan2(-dy, -dx);
  var power = Math.min(dist, 120) / 120;
  aim = { angle: angle, power: power, stickBack: Math.min(dist * 0.6, 60) };
});
cv.addEventListener('pointerup', function (e) {
  if (!dragStart) return;
  var start = dragStart; dragStart = null;
  if (moving || striking || gameOver || turn !== ME) { aim = null; return; }
  var p = toTable(e);
  var dx = p.x - start.x, dy = p.y - start.y;
  var dist = Math.hypot(dx, dy);
  if (dist < 10 || !aim) { aim = null; return; }
  var angle = aim.angle, power = aim.power;
  striking = true;
  var t0 = null;
  function strikeStep(ts) {
    if (!t0) t0 = ts;
    var k = (ts - t0) / 110;
    if (k >= 1) {
      striking = false;
      aim = null;
      shotPocketed = []; shotScratch = false;
      var cue = null;
      for (var i = 0; i < balls.length; i++) { if (balls[i].num === 0) cue = balls[i]; }
      if (!cue) return;
      var speed = 2 + power * 11;
      cue.vx = Math.cos(angle) * speed;
      cue.vy = Math.sin(angle) * speed;
      playCueHit();
      moving = true;
      return;
    }
    if (aim) aim.stickBack = aim.stickBack * (1 - k);
    requestAnimationFrame(strikeStep);
  }
  requestAnimationFrame(strikeStep);
});

document.getElementById('btnRestart').addEventListener('click', function () {
  resetLocal('Game restarted. ' + (HOST === ME ? 'You break.' : FOENAME + ' breaks.'), true);
});
document.getElementById('btnSound').addEventListener('click', function (e) {
  soundOn = !soundOn;
  e.target.textContent = soundOn ? 'SOUND ON' : 'SOUND OFF';
  if (soundOn) ensureAudio();
});
document.getElementById('btnLeave').addEventListener('click', function () {
  if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
});

var last = 0, acc = 0;
function frame(ts) {
  requestAnimationFrame(frame);
  if (!last) last = ts;
  var dt = ts - last; last = ts;
  if (dt > 100) dt = 100;
  acc += dt;
  while (acc >= 16.667) { if (moving) step(); acc -= 16.667; }
  draw();
}
resetLocal(HOST === ME ? 'You break! Pull back and release to shoot.' : 'Waiting for ' + FOENAME + ' to break...', false);
requestAnimationFrame(frame);
})();
</script>
</body>
</html>
`;
"""

STATE_OLD = " const [interiorHouse, setInteriorHouse] = useState<any | null>(null);"
STATE_PVP = STATE_OLD + "\n  const [poolPvpOpen, setPoolPvpOpen] = useState(false);\n  const [poolPvpGameOpen, setPoolPvpGameOpen] = useState(false);\n  const [poolPvpRoom, setPoolPvpRoom] = useState<any | null>(null);"
HANDLERS_PVP = """  const handlePvpLeave = async () => {
    if (poolPvpRoom?.code) {
      try { await fetch(API_BASE + '/api/pool/rooms/' + poolPvpRoom.code + '/leave', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId }) }); } catch (e) {}
    }
    setPoolPvpRoom(null);
    setPoolPvpOpen(false);
    setPoolPvpGameOpen(false);
  };
"""
MAP_ANCHOR = "export default function MapScreen() {"
MODAL_ANCHOR = "      {/* House Interior Modal */}"
WEBVIEW_BLOCK = """let PoolWebView: any = null;
try { PoolWebView = require('react-native-webview').default; } catch (e) { PoolWebView = null; }

"""
PVP_COMPONENTS = """const PoolPvpGameModal = ({ visible, onClose, room, playerId }: { visible: boolean; onClose: () => void; room: any; playerId: string }) => {
  const webRef = useRef<any>(null);
  const lastStateRef = useRef<string>('');
  const [pvpError, setPvpError] = useState('');
  const me = playerId;
  const hostId = room?.host_id;
  const guestId = room?.guest_id;
  const foeId = me === hostId ? (guestId || '') : (hostId || '');
  const foeName = me === hostId ? (room?.guest_name || 'Player') : (room?.host_name || 'Player');
  const code = room?.code;
  useEffect(() => {
    if (!visible || !code) return;
    const poll = async () => {
      try {
        const res = await fetch(API_BASE + '/api/pool/rooms/' + code);
        if (!res.ok) return;
        const data = await res.json();
        const st = data?.state;
        if (st) {
          const js = JSON.stringify(st);
          if (js !== lastStateRef.current) {
            lastStateRef.current = js;
            if (webRef.current) {
              webRef.current.injectJavaScript('window.dispatchEvent(new CustomEvent("pool-state", {detail: ' + js + '})); true;');
            }
          }
        }
      } catch (e) {}
    };
    poll();
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [visible, code]);
  const handlePvpMessage = async (event: any) => {
    const raw = event?.nativeEvent?.data;
    if (raw === 'close') { onClose(); return; }
    try {
      const msg = JSON.parse(raw);
      if (msg?.type === 'pool-shot' && msg.state) {
        lastStateRef.current = JSON.stringify(msg.state);
        const res = await fetch(API_BASE + '/api/pool/rooms/' + code + '/shot', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ player_id: me, state: msg.state }),
        });
        if (!res.ok) {
          const d = await res.json().catch(() => ({}));
          setPvpError(d?.detail || 'Could not send your shot.');
        } else {
          setPvpError('');
        }
      }
    } catch (e) {}
  };
  const pvpConfig = 'window.POOL_PVP = ' + JSON.stringify({ me: me, foe: foeId, foeName: foeName, hostId: hostId }) + '; true;';
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
          <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>POOL - YOU vs {foeName}</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {pvpError ? (<Text style={{ color: '#ff6666', textAlign: 'center', fontSize: 12, marginBottom: 6 }}>{pvpError}</Text>) : null}
        {PoolWebView ? (
          <PoolWebView
            source={{ html: POOL_PVP_HTML }}
            injectedJavaScriptBeforeContentLoaded={pvpConfig}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
            mediaPlaybackRequiresUserAction={false}
            originWhitelist={['*']}
            style={{ flex: 1 }}
            ref={webRef}
            onMessage={handlePvpMessage}
          />
        ) : (
          <Text style={{ color: '#ffffff', textAlign: 'center', marginTop: 40 }}>Pool game needs WebView, which is not available in this build.</Text>
        )}
      </View>
    </Modal>
  );
};

const PoolPvpModal = ({ visible, onClose, playerId, playerName, room, setRoom, onPlay, onLeave }: { visible: boolean; onClose: () => void; playerId: string; playerName: string; room: any; setRoom: (r: any) => void; onPlay: () => void; onLeave: () => void }) => {
  const [codeInput, setCodeInput] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);
  const showNotLive = () => setInfo('Pool rooms are not live yet - the backend still needs a Deploy that picks up the rooms code.');
  const createRoom = async () => {
    setBusy(true); setInfo('');
    try {
      const res = await fetch(API_BASE + '/api/pool/rooms/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId, player_name: playerName }) });
      if (res.status === 404) { showNotLive(); return; }
      if (!res.ok) { const d = await res.json().catch(() => ({})); setInfo(d?.detail || 'Could not create a room.'); return; }
      const data = await res.json();
      setRoom(data);
      setInfo('Room ' + data.code + ' created. Share the code with your friend.');
    } catch (e) { showNotLive(); } finally { setBusy(false); }
  };
  const joinRoom = async () => {
    const code = codeInput.trim();
    if (code.length !== 4) { setInfo('Enter the 4-digit room code.'); return; }
    setBusy(true); setInfo('');
    try {
      const res = await fetch(API_BASE + '/api/pool/rooms/join', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code, player_id: playerId, player_name: playerName }) });
      if (res.status === 404) { showNotLive(); return; }
      if (!res.ok) { const d = await res.json().catch(() => ({})); setInfo(d?.detail || 'Could not join the room.'); return; }
      const data = await res.json();
      setRoom(data);
    } catch (e) { showNotLive(); } finally { setBusy(false); }
  };
  const sendChat = async () => {
    if (!room?.code || !chatInput.trim()) return;
    const text = chatInput.trim();
    setChatInput('');
    try {
      const res = await fetch(API_BASE + '/api/pool/rooms/' + room.code + '/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId, player_name: playerName, text: text }) });
      if (res.ok) { const data = await res.json(); setRoom(data); }
    } catch (e) {}
  };
  useEffect(() => {
    if (!visible || !room?.code) return;
    const poll = async () => {
      try {
        const res = await fetch(API_BASE + '/api/pool/rooms/' + room.code);
        if (res.ok) { const data = await res.json(); setRoom(data); }
      } catch (e) {}
    };
    const t = setInterval(poll, 2000);
    return () => clearInterval(t);
  }, [visible, room?.code]);
  const foeName = room ? (playerId === room.host_id ? (room.guest_name || 'Friend') : (room.host_name || 'Friend')) : '';
  const canPlay = room && room.status === 'playing';
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111', padding: 16 }}>
        <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 18, textAlign: 'center', marginBottom: 4 }}>POOL - PLAYER VS PLAYER</Text>
        {info ? (<Text style={{ color: '#f39c12', fontSize: 12, textAlign: 'center', marginBottom: 12 }}>{info}</Text>) : null}
        {!room ? (
          <View>
            <TouchableOpacity onPress={createRoom} disabled={busy} style={{ backgroundColor: '#2e7d32', paddingVertical: 12, borderRadius: 8, marginBottom: 12 }}>
              <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>CREATE ROOM</Text>
            </TouchableOpacity>
            <Text style={{ color: '#cccccc', fontSize: 12, textAlign: 'center', marginBottom: 6 }}>Or join a friend's room:</Text>
            <TextInput value={codeInput} onChangeText={setCodeInput} keyboardType="number-pad" maxLength={4} placeholder="4-digit code" placeholderTextColor="#888888" style={{ backgroundColor: '#222222', color: '#ffffff', padding: 12, borderRadius: 8, marginBottom: 10, textAlign: 'center', fontSize: 18, fontWeight: '800' }} />
            <TouchableOpacity onPress={joinRoom} disabled={busy} style={{ backgroundColor: '#1e88e5', paddingVertical: 12, borderRadius: 8, marginBottom: 12 }}>
              <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>JOIN ROOM</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#666666', paddingVertical: 12, borderRadius: 8, marginTop: 12 }}>
              <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>CANCEL</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <View style={{ flex: 1 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 28, textAlign: 'center' }}>Room {room.code}</Text>
            <Text style={{ color: '#cccccc', fontSize: 12, textAlign: 'center', marginBottom: 12 }}>
              {room.status === 'waiting' ? 'Waiting for your friend to join...' : room.status === 'playing' ? (foeName + ' joined!') : 'Game over.'}
            </Text>
            {canPlay ? (
              <TouchableOpacity onPress={onPlay} style={{ backgroundColor: '#2e7d32', paddingVertical: 12, borderRadius: 8, marginBottom: 12 }}>
                <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>PLAY</Text>
              </TouchableOpacity>
            ) : null}
            <Text style={{ color: '#ffffff', fontWeight: '800', marginBottom: 6 }}>CHAT</Text>
            <ScrollView style={{ flex: 1, backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, marginBottom: 10 }}>
              {(room.chat || []).map((m: any, i: number) => (
                <Text key={i} style={{ color: m.sender_id === playerId ? '#f39c12' : '#ffffff', fontSize: 13, marginBottom: 4 }}>
                  {m.sender_id === playerId ? 'YOU' : (m.sender_name || 'Friend')}: {m.text}
                </Text>
              ))}
            </ScrollView>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              <TextInput value={chatInput} onChangeText={setChatInput} placeholder="Say something..." placeholderTextColor="#888888" style={{ flex: 1, backgroundColor: '#222222', color: '#ffffff', padding: 10, borderRadius: 8 }} />
              <TouchableOpacity onPress={sendChat} style={{ backgroundColor: '#1e88e5', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8 }}>
                <Text style={{ color: '#ffffff', fontWeight: '800' }}>SEND</Text>
              </TouchableOpacity>
            </View>
            <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#666666', paddingVertical: 12, borderRadius: 8, marginTop: 12 }}>
              <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>BACK</Text>
            </TouchableOpacity>
            <TouchableOpacity onPress={onLeave} style={{ backgroundColor: '#e74c3c', paddingVertical: 12, borderRadius: 8, marginTop: 12 }}>
              <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>LEAVE ROOM</Text>
            </TouchableOpacity>
          </View>
        )}
      </View>
    </Modal>
  );
};

"""

def add_to_import(src, module, names):
    """Add names to an existing import from '<module>'. Handles single/multi-line imports,
    single/double quotes, default+named imports, and split imports. Returns (src, ok)."""
    pat = re.compile(r"import\s+((?:(?!import)[^;])*?)\s+from\s+['\"]" + re.escape(module) + r"['\"]")
    for m in pat.finditer(src):
        clause = m.group(1)
        bm = re.search(r"\{([\s\S]*?)\}", clause)
        if not bm:
            continue
        have = [x.strip() for x in bm.group(1).split(",") if x.strip()]
        added = False
        for n in names:
            if n not in have:
                have.append(n)
                added = True
        if not added:
            return src, True
        before = clause[:bm.start()].strip()
        if before:
            new_clause = before + " { " + ", ".join(have) + " }"
        else:
            new_clause = "{ " + ", ".join(have) + " }"
        return src[:m.start(1)] + new_clause + src[m.end(1):], True
    return src, False

def import_after_last(src, line):
    """Insert an import line after the last existing import. Returns (src, ok)."""
    lines = src.split("\n")
    last = -1
    for i, ln in enumerate(lines):
        if ln.startswith("import "):
            last = i
    if last == -1:
        return src, False
    lines.insert(last + 1, line)
    return "\n".join(lines), True

def main():
    src = open(INDEX).read()
    with open(PVP_TS, "w") as f:
        f.write(PVP_TS_CONTENT)
    print("OK: PoolGamePvpHtml.ts written")
    import_ok = False
    if "PoolGamePvpHtml" in src:
        print("SKIP: PoolGamePvpHtml already imported")
        import_ok = True
    else:
        src, ok = import_after_last(src, "import { POOL_PVP_HTML } from '../../components/PoolGamePvpHtml';")
        if ok and "POOL_PVP_HTML" in src:
            print("OK: PoolGamePvpHtml imported")
            import_ok = True
        else:
            print("WARNING: could not add PoolGamePvpHtml import")
    need_ok = True
    for module, names in (("react", ["useEffect"]), ("react-native", ["TextInput", "ScrollView"])):
        src, ok = add_to_import(src, module, names)
        if ok:
            print("OK: import " + module + " has " + ", ".join(names))
        else:
            print("WARNING: could not add to import from '" + module + "'")
            idx = src.find(module)
            if idx != -1:
                print("  IMPORT CTX: " + src[max(0, idx - 200):idx + 120].replace("\n", " | ")[:320])
            need_ok = False
    components_ok = False
    if "const PoolPvpModal" in src and "const PoolPvpGameModal" in src:
        print("SKIP: PvP components already present")
        components_ok = True
    elif import_ok and need_ok:
        block = PVP_COMPONENTS
        if "let PoolWebView" not in src:
            block = WEBVIEW_BLOCK + block
        if MAP_ANCHOR in src:
            src = src.replace(MAP_ANCHOR, block + MAP_ANCHOR, 1)
            print("OK: PvP components added")
            components_ok = True
        else:
            print("WARNING: MapScreen anchor not found, components not added")
    else:
        print("WARNING: components skipped (import_ok=%s need_ok=%s)" % (import_ok, need_ok))
    menu_ok = False
    if "PLAY VS FRIEND" in src:
        src = src.replace("PLAY VS FRIEND", "PLAYER VS PLAYER")
        print("OK: menu button renamed to PLAYER VS PLAYER")
    mpos = src.find("PoolTableMenuModal")
    mend = src.find("export default function MapScreen()", mpos) if mpos != -1 else -1
    comp_end = -1
    if mpos != -1:
        def_line_end = src.find("\n", mpos)
        if def_line_end != -1:
            for pat in ("\n};", "\n}"):
                e = src.find(pat, def_line_end)
                if e != -1:
                    comp_end = e + len(pat)
                    break
    win_span_end = comp_end if comp_end != -1 else mend
    if mpos != -1 and comp_end != -1 and "PLAYER VS PLAYER" in src[mpos:comp_end]:
        print("SKIP: menu already has PLAYER VS PLAYER button")
        menu_ok = True
    elif mpos == -1 or mend == -1:
        print("WARNING: PoolTableMenuModal component not found, button not added")
    else:
        win = src[mpos:win_span_end]
        if "onPlayPvp" in win:
            d_ok = True
            t_ok = True
        else:
            d_ok = False
            if "onPlayPvc, onMove" in win:
                win = win.replace("onPlayPvc, onMove", "onPlayPvc, onPlayPvp, onMove", 1)
                d_ok = True
            elif "onPlayPvc," in win:
                win = win.replace("onPlayPvc,", "onPlayPvc, onPlayPvp,", 1)
                d_ok = True
            t_ok = False
            if "onPlayPvc: () => void;" in win:
                win = win.replace("onPlayPvc: () => void;", "onPlayPvc: () => void; onPlayPvp?: () => void;", 1)
                t_ok = True
        b_ok = False
        pvc_pos = win.find("PLAY VS COMPUTER")
        if pvc_pos != -1:
            open_pos = win.rfind("<TouchableOpacity", 0, pvc_pos)
            close_pos = win.find("</TouchableOpacity>", pvc_pos)
            if open_pos != -1 and close_pos != -1:
                close_end = close_pos + len("</TouchableOpacity>")
                line_start = win.rfind("\n", 0, open_pos) + 1
                indent = win[line_start:open_pos]
                if indent.strip() != "":
                    indent = "      "
                btn = "\n" + indent + "<TouchableOpacity onPress={() => { if (onPlayPvp) { onPlayPvp(); } else { onClose(); } }} style={{ backgroundColor: '#1e88e5', paddingVertical: 12, borderRadius: 8, marginBottom: 10 }}>\n" + indent + "  <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>PLAYER VS PLAYER</Text>\n" + indent + "</TouchableOpacity>"
                win = win[:close_end] + btn + win[close_end:]
                b_ok = True
        if d_ok and t_ok and b_ok:
            src = src[:mpos] + win + src[win_span_end:]
            print("OK: menu gained PLAYER VS PLAYER button")
            menu_ok = True
        else:
            print("WARNING: menu wiring incomplete (d=%s t=%s btn=%s), button NOT added" % (d_ok, t_ok, b_ok))
    state_ok = False
    if "poolPvpOpen" in src:
        print("SKIP: PvP state already present")
        state_ok = True
    else:
        pool_menu_line = None
        for ln in src.split("\n"):
            if "poolMenuOpen" in ln and "useState" in ln:
                pool_menu_line = ln
                break
        if pool_menu_line:
            src = src.replace(pool_menu_line, pool_menu_line + "\n  const [poolPvpOpen, setPoolPvpOpen] = useState(false);\n  const [poolPvpGameOpen, setPoolPvpGameOpen] = useState(false);\n  const [poolPvpRoom, setPoolPvpRoom] = useState<any | null>(null);\n" + HANDLERS_PVP.rstrip("\n"), 1)
            print("OK: PvP state + leave handler added")
            state_ok = True
        elif STATE_OLD in src:
            src = src.replace(STATE_OLD, STATE_PVP + "\n" + HANDLERS_PVP.rstrip("\n"), 1)
            print("OK: PvP state + leave handler added (fallback anchor)")
            state_ok = True
        else:
            print("WARNING: no state anchor found, PvP state not added")
    if state_ok and components_ok:
        render_block = """{poolPvpOpen ? (<PoolPvpModal visible={poolPvpOpen} onClose={() => setPoolPvpOpen(false)} playerId={playerId} playerName={'Player'} room={poolPvpRoom} setRoom={setPoolPvpRoom} onPlay={() => { setPoolPvpOpen(false); setPoolPvpGameOpen(true); }} onLeave={handlePvpLeave} />) : null}
      {poolPvpGameOpen && poolPvpRoom ? (<PoolPvpGameModal visible={poolPvpGameOpen} onClose={() => { setPoolPvpGameOpen(false); setPoolPvpOpen(true); }} room={poolPvpRoom} playerId={playerId} />) : null}
      """
        if "PoolPvpModal visible" in src:
            print("SKIP: PvP modals already rendered")
        elif MODAL_ANCHOR in src:
            src = src.replace(MODAL_ANCHOR, render_block + MODAL_ANCHOR, 1)
            print("OK: PvP modals rendered")
        else:
            print("WARNING: modal anchor not found, PvP modals not rendered")
    else:
        print("WARNING: PvP modals not rendered (state_ok=%s components_ok=%s)" % (state_ok, components_ok))
    if state_ok:
        menu_render_old = "onPlayPvc={() => { setPoolMenuOpen(false); setPoolGameOpen(true); }}"
        if "onPlayPvp={() =>" in src:
            print("SKIP: menu already wired to PvP")
        elif menu_render_old in src:
            src = src.replace(menu_render_old, menu_render_old + " onPlayPvp={() => { setPoolMenuOpen(false); setPoolPvpOpen(true); }}", 1)
            print("OK: menu wired to PvP screen")
        else:
            print("WARNING: menu render line not found, PvP button not wired")
    open(INDEX, "w").write(src)
    print("HOUSE_POOL_PVP_V3_OK")

if __name__ == "__main__":
    main()
