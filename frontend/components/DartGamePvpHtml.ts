export const DART_PVP_HTML = `<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<style>
body { margin: 0; background: #111111; color: #ffffff; font-family: sans-serif; }
#wrap { max-width: 430px; margin: 0 auto; padding: 10px; text-align: center; box-sizing: border-box; }
#header { display: flex; justify-content: space-between; font-weight: 800; font-size: 18px; margin-bottom: 4px; }
#header .turn { color: #f39c12; outline: 2px solid #f39c12; border-radius: 6px; padding: 2px 8px; }
#darts { color: #cccccc; font-size: 12px; margin-bottom: 4px; }
#msg { color: #cccccc; font-size: 13px; min-height: 18px; margin-bottom: 6px; }
#cv { width: 100%; max-width: 400px; height: auto; display: block; margin: 0 auto; touch-action: none; border-radius: 10px; }
#log { color: #999999; font-size: 12px; min-height: 16px; margin-top: 8px; }
#btns { display: flex; gap: 8px; justify-content: center; margin-top: 12px; flex-wrap: wrap; }
#btns button { background: #444444; color: #ffffff; font-weight: 800; border: 0; border-radius: 8px; padding: 10px 14px; font-size: 12px; }
#btns button.leave { background: #e74c3c; }
#hint { color: #999999; font-size: 11px; margin-top: 8px; }
</style>
</head>
<body>
<div id="wrap">
<div id="header"><span id="youLbl">YOU - 301</span><span id="cpuLbl">FRIEND - 301</span></div>
<div id="darts">Darts left: 3</div>
<div id="msg">Your turn. Tap when the target is over your number, or drag to steer it.</div>
<canvas id="cv" width="800" height="800"></canvas>
<div id="log"></div>
<div id="btns">
<button id="btnRestart">RESTART</button>
<button id="btnSound">SOUND ON</button>
<button id="btnLeave" class="leave">LEAVE TABLE</button>
</div>
<div id="hint">301 darts. First to exactly 0 wins. Go below 0 and you bust - your turn ends and your score goes back. The target roams the board and crosses the bullseye often - tap when it is over your number, or drag to steer it, then release. The shake counts, so time it. You and your friend take turns, 3 darts each, on the same moving target.</div>
</div>
<script>
(function () {
var cv = document.getElementById('cv');
var ctx = cv.getContext('2d');
ctx.scale(2, 2);
var C = 200, R_OUT = 170, R_DIN = 155, R_TOUT = 107, R_TIN = 92, R_BULL = 28, R_EYE = 12;
var NUMS = [20, 1, 18, 4, 13, 6, 10, 15, 2, 17, 3, 19, 7, 16, 8, 11, 14, 9, 12, 5];
var CFG = window.DART_PVP || { me: 'you', foe: 'friend', foeName: 'FRIEND', hostId: 'you' };
var scores = {}; scores[CFG.me] = 301; scores[CFG.foe] = 301;
var turn = CFG.hostId;
var dartsThisTurn = [], turnStartScore = 301, gameOver = false, winner = null;
var soundOn = true, audioCtx = null;
var downPos = null, dragging = false;
var baseAim = { x: C, y: C };
var wp = null, wpSinceBull = 0, wpSpeed = 300, wpRedirectAt = 0, lastT = 0;
var markers = [];
var msgEl = document.getElementById('msg'), youLbl = document.getElementById('youLbl'), cpuLbl = document.getElementById('cpuLbl');
var dartsEl = document.getElementById('darts'), logEl = document.getElementById('log');

function setMsg(t) { msgEl.textContent = t; }
function updateHeader() {
  youLbl.textContent = 'YOU - ' + scores[CFG.me];
  cpuLbl.textContent = CFG.foeName + ' - ' + scores[CFG.foe];
  youLbl.className = turn === CFG.me && !gameOver ? 'turn' : '';
  cpuLbl.className = turn === CFG.foe && !gameOver ? 'turn' : '';
  dartsEl.textContent = 'Darts left: ' + (3 - dartsThisTurn.length);
}

function ensureAudio() {
  if (!audioCtx) { try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) { audioCtx = null; } }
  if (audioCtx && audioCtx.state === 'suspended') { audioCtx.resume(); }
}

function playThunk() {
  if (!soundOn || !audioCtx) return;
  var t = audioCtx.currentTime;
  var dur = 0.05;
  var buf = audioCtx.createBuffer(1, audioCtx.sampleRate * dur, audioCtx.sampleRate);
  var d = buf.getChannelData(0);
  for (var i = 0; i < d.length; i++) { d[i] = (Math.random() * 2 - 1) * (1 - i / d.length); }
  var src = audioCtx.createBufferSource(); src.buffer = buf;
  var bp = audioCtx.createBiquadFilter(); bp.type = 'lowpass'; bp.frequency.value = 900;
  var g = audioCtx.createGain(); g.gain.setValueAtTime(0.6, t);
  g.gain.exponentialRampToValueAtTime(0.001, t + 0.08);
  src.connect(bp); bp.connect(g); g.connect(audioCtx.destination); src.start(t);
  var osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = 180;
  var og = audioCtx.createGain(); og.gain.setValueAtTime(0.4, t);
  og.gain.exponentialRampToValueAtTime(0.001, t + 0.1);
  osc.connect(og); og.connect(audioCtx.destination); osc.start(t); osc.stop(t + 0.11);
}

function playWin() {
  if (!soundOn || !audioCtx) return;
  var t = audioCtx.currentTime;
  [523, 659, 784].forEach(function (f, i) {
    var osc = audioCtx.createOscillator(); osc.type = 'sine'; osc.frequency.value = f;
    var g = audioCtx.createGain(); g.gain.setValueAtTime(0.3, t + i * 0.15);
    g.gain.exponentialRampToValueAtTime(0.001, t + i * 0.15 + 0.25);
    osc.connect(g); g.connect(audioCtx.destination); osc.start(t + i * 0.15); osc.stop(t + i * 0.15 + 0.26);
  });
}

function segAngle(idx) {
  return (idx * 18 - 90) * Math.PI / 180;
}

function scoreFor(x, y) {
  var dx = x - C, dy = y - C;
  var r = Math.hypot(dx, dy);
  if (r <= R_EYE) return { points: 50, label: 'Bullseye 50' };
  if (r <= R_BULL) return { points: 25, label: 'Bull 25' };
  if (r > R_OUT) return { points: 0, label: 'Miss' };
  var deg = Math.atan2(dy, dx) * 180 / Math.PI;
  var norm = (deg + 90 + 360 + 9) % 360;
  var idx = Math.floor(norm / 18) % 20;
  var num = NUMS[idx];
  if (r > R_DIN) return { points: num * 2, label: 'Double ' + num };
  if (r > R_TIN && r <= R_TOUT) return { points: num * 3, label: 'Triple ' + num };
  return { points: num, label: 'Single ' + num };
}

function addErr(p, err) {
  return { x: p.x + (Math.random() - 0.5) * 2 * err, y: p.y + (Math.random() - 0.5) * 2 * err };
}

function endGame(w) {
  gameOver = true;
  winner = w;
  updateHeader();
  setMsg(w === CFG.me ? 'YOU WIN! 301 cleared!' : CFG.foeName + ' WINS!');
  playWin();
}

function endTurn() {
  dartsThisTurn = [];
  markers = [];
  if (gameOver) return;
  turn = turn === CFG.me ? CFG.foe : CFG.me;
  turnStartScore = scores[turn];
  updateHeader();
  setMsg(turn === CFG.me ? 'Your turn. Tap when the target is over your number, or drag to steer it.' : CFG.foeName + ' is throwing...');
  postState();
}

function applyDart(shooter, x, y) {
  var s = scoreFor(x, y);
  markers.push({ x: x, y: y, who: shooter });
  dartsThisTurn.push(s.label + ' (' + s.points + ')');
  var cur = scores[shooter];
  var next = cur - s.points;
  var meThrow = shooter === CFG.me;
  if (next < 0) {
    scores[shooter] = turnStartScore;
    logEl.textContent = (meThrow ? 'You' : CFG.foeName) + ' threw: ' + dartsThisTurn.join(', ') + ' - BUST!';
    updateHeader();
    setMsg((meThrow ? 'BUST! ' : CFG.foeName + ' busts! ') + 'Score goes back. ' + (meThrow ? CFG.foeName + "'s" : 'Your') + ' turn.');
    postState();
    setTimeout(endTurn, 1200);
    return 'bust';
  }
  scores[shooter] = next;
  updateHeader();
  if (next === 0) {
    logEl.textContent = (meThrow ? 'You' : CFG.foeName) + ' threw: ' + dartsThisTurn.join(', ');
    endGame(shooter);
    postState();
    return 'win';
  }
  if (dartsThisTurn.length >= 3) {
    logEl.textContent = (meThrow ? 'You' : CFG.foeName) + ' threw: ' + dartsThisTurn.join(', ');
    postState();
    setTimeout(endTurn, 900);
    return 'done';
  }
  if (meThrow) setMsg('Dart ' + (dartsThisTurn.length + 1) + ' of 3. ' + s.label + '!');
  else setMsg(CFG.foeName + ' threw ' + s.label + '.');
  postState();
  return 'continue';
}

function buildState() {
  return { scores: scores, turn: turn, dartsThisTurn: dartsThisTurn, markers: markers, gameOver: gameOver, winner: winner, turnStartScore: turnStartScore };
}
function postState() {
  if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'dart-shot', state: buildState() }));
}
function applyPvpState(st) {
  if (!st) return;
  scores = st.scores || scores;
  turn = st.turn || turn;
  dartsThisTurn = st.dartsThisTurn || [];
  markers = st.markers || [];
  gameOver = !!st.gameOver;
  winner = st.winner || null;
  turnStartScore = st.turnStartScore;
  updateHeader();
  if (gameOver && winner) setMsg(winner === CFG.me ? 'YOU WIN! 301 cleared!' : CFG.foeName + ' WINS!');
  else if (turn === CFG.me) setMsg('Your turn. Tap when the target is over your number, or drag to steer it.');
  else setMsg(CFG.foeName + ' is throwing...');
}
window.addEventListener('dart-state', function (e) { applyPvpState(e.detail); });

function shakeOffset(t) {
  return {
    x: Math.sin(t * 12.0) * 3 + Math.sin(t * 22.0) * 2 + (Math.random() - 0.5) * 2,
    y: Math.cos(t * 10.0) * 3 + Math.sin(t * 18.0) * 2 + (Math.random() - 0.5) * 2
  };
}

function reticlePos(t) {
  var s = shakeOffset(t);
  return { x: baseAim.x + s.x, y: baseAim.y + s.y };
}

function pickWaypoint() {
  var toBull = false;
  if (wpSinceBull >= 2) toBull = true;
  else if (Math.random() < 0.35) toBull = true;
  if (toBull) {
    var a = Math.random() * Math.PI * 2, rr = Math.random() * 15;
    wp = { x: C + Math.cos(a) * rr, y: C + Math.sin(a) * rr };
    wpSinceBull = 0;
  } else {
    var ang = Math.random() * Math.PI * 2;
    var rad = Math.sqrt(Math.random()) * 165;
    wp = { x: C + Math.cos(ang) * rad, y: C + Math.sin(ang) * rad };
    wpSinceBull++;
  }
  wpRedirectAt = performance.now() / 1000 + 0.8 + Math.random() * 0.7;
}

function drawBoard(t) {
  var wall = ctx.createLinearGradient(0, 0, 0, 400);
  wall.addColorStop(0, '#2e2620');
  wall.addColorStop(0.5, '#1c1712');
  wall.addColorStop(1, '#100d0a');
  ctx.fillStyle = wall;
  ctx.fillRect(0, 0, 400, 400);
  var glow = ctx.createRadialGradient(C, C, 40, C, C, 210);
  glow.addColorStop(0, 'rgba(255, 200, 120, 0.14)');
  glow.addColorStop(1, 'rgba(255, 200, 120, 0)');
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, 400, 400);
  ctx.save();
  ctx.beginPath(); ctx.arc(C + 6, C + 10, 198, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
  ctx.fill();
  ctx.restore();
  var wood = ctx.createLinearGradient(C - 195, C - 195, C + 195, C + 195);
  wood.addColorStop(0, '#d9a86c');
  wood.addColorStop(0.45, '#a4713d');
  wood.addColorStop(1, '#5e3a1c');
  ctx.beginPath(); ctx.arc(C, C, 195, 0, Math.PI * 2);
  ctx.fillStyle = wood; ctx.fill();
  ctx.beginPath(); ctx.arc(C, C, 190, 0, Math.PI * 2);
  ctx.fillStyle = '#1a1a1a'; ctx.fill();
  for (var i = 0; i < 20; i++) {
    var a0 = segAngle(i) - 9 * Math.PI / 180;
    var a1 = segAngle(i) + 9 * Math.PI / 180;
    var even = i % 2 === 0;
    ctx.beginPath();
    ctx.moveTo(C + Math.cos(a0) * R_BULL, C + Math.sin(a0) * R_BULL);
    ctx.arc(C, C, R_OUT, a0, a1);
    ctx.lineTo(C + Math.cos(a1) * R_BULL, C + Math.sin(a1) * R_BULL);
    ctx.closePath();
    ctx.fillStyle = even ? '#ece0c2' : '#232323';
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(C + Math.cos(a0) * R_TIN, C + Math.sin(a0) * R_TIN);
    ctx.arc(C, C, R_TOUT, a0, a1);
    ctx.lineTo(C + Math.cos(a1) * R_TIN, C + Math.sin(a1) * R_TIN);
    ctx.closePath();
    ctx.fillStyle = even ? '#e53935' : '#2e7d32';
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(C + Math.cos(a0) * R_DIN, C + Math.sin(a0) * R_DIN);
    ctx.arc(C, C, R_OUT, a0, a1);
    ctx.lineTo(C + Math.cos(a1) * R_DIN, C + Math.sin(a1) * R_DIN);
    ctx.closePath();
    ctx.fillStyle = even ? '#e53935' : '#2e7d32';
    ctx.fill();
    ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
    ctx.font = 'bold 15px sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    var na = segAngle(i);
    ctx.fillText(String(NUMS[i]), C + Math.cos(na) * 182 + 1, C + Math.sin(na) * 182 + 1);
    ctx.fillStyle = '#ffffff';
    ctx.fillText(String(NUMS[i]), C + Math.cos(na) * 182, C + Math.sin(na) * 182);
  }
  var depth = ctx.createRadialGradient(C, C, 30, C, C, 190);
  depth.addColorStop(0, 'rgba(255, 255, 255, 0.10)');
  depth.addColorStop(0.55, 'rgba(0, 0, 0, 0)');
  depth.addColorStop(1, 'rgba(0, 0, 0, 0.38)');
  ctx.beginPath(); ctx.arc(C, C, 190, 0, Math.PI * 2);
  ctx.fillStyle = depth; ctx.fill();
  var bullG = ctx.createRadialGradient(C - 6, C - 6, 2, C, C, R_BULL);
  bullG.addColorStop(0, '#66bb6a');
  bullG.addColorStop(1, '#1b5e20');
  ctx.beginPath(); ctx.arc(C, C, R_BULL, 0, Math.PI * 2);
  ctx.fillStyle = bullG; ctx.fill();
  var eyeG = ctx.createRadialGradient(C - 3, C - 3, 1, C, C, R_EYE);
  eyeG.addColorStop(0, '#ff8a80');
  eyeG.addColorStop(1, '#b71c1c');
  ctx.beginPath(); ctx.arc(C, C, R_EYE, 0, Math.PI * 2);
  ctx.fillStyle = eyeG; ctx.fill();
  for (var j = 0; j < markers.length; j++) {
    var m = markers[j];
    var col = m.who === CFG.me ? '#1e88e5' : '#e74c3c';
    ctx.save();
    ctx.beginPath(); ctx.ellipse(m.x + 5, m.y + 7, 9, 4, 0.6, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(0, 0, 0, 0.45)';
    ctx.fill();
    ctx.restore();
    ctx.strokeStyle = '#dddddd'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(m.x, m.y); ctx.lineTo(m.x + 14, m.y - 14); ctx.stroke();
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.moveTo(m.x + 14, m.y - 14); ctx.lineTo(m.x + 24, m.y - 10); ctx.lineTo(m.x + 18, m.y - 22); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.arc(m.x, m.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#ffffff'; ctx.fill();
  }
  if (!gameOver) {
    var rp = reticlePos(t);
    ctx.save();
    ctx.shadowColor = 'rgba(243, 156, 18, 0.9)';
    ctx.shadowBlur = 12;
    ctx.strokeStyle = '#f39c12'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(rp.x, rp.y, 14, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(rp.x - 22, rp.y); ctx.lineTo(rp.x - 9, rp.y);
    ctx.moveTo(rp.x + 9, rp.y); ctx.lineTo(rp.x + 22, rp.y);
    ctx.moveTo(rp.x, rp.y - 22); ctx.lineTo(rp.x, rp.y - 9);
    ctx.moveTo(rp.x, rp.y + 9); ctx.lineTo(rp.x, rp.y + 22);
    ctx.stroke();
    ctx.restore();
    ctx.beginPath(); ctx.arc(rp.x, rp.y, 2.5, 0, Math.PI * 2);
    ctx.fillStyle = '#f39c12'; ctx.fill();
  }
}

function toBoard(e) {
  var rect = cv.getBoundingClientRect();
  var lx = (e.clientX - rect.left) * 400 / rect.width;
  var ly = (e.clientY - rect.top) * 400 / rect.height;
  return { x: lx, y: ly };
}

cv.addEventListener('pointerdown', function (e) {
  ensureAudio();
  if (gameOver || turn !== CFG.me || dartsThisTurn.length >= 3) return;
  downPos = toBoard(e);
  dragging = false;
});
cv.addEventListener('pointermove', function (e) {
  if (!downPos) return;
  var p = toBoard(e);
  if (!dragging && Math.hypot(p.x - downPos.x, p.y - downPos.y) > 10) dragging = true;
  if (dragging) baseAim = p;
});
cv.addEventListener('pointerup', function (e) {
  if (!downPos) return;
  downPos = null;
  dragging = false;
  if (gameOver || turn !== CFG.me || dartsThisTurn.length >= 3) return;
  var t = performance.now() / 1000;
  var rp = reticlePos(t);
  var hit = addErr(rp, 5);
  playThunk();
  applyDart(CFG.me, hit.x, hit.y);
  wp = null;
});

document.getElementById('btnRestart').addEventListener('click', function () {
  scores = {}; scores[CFG.me] = 301; scores[CFG.foe] = 301; turn = CFG.hostId;
  dartsThisTurn = []; turnStartScore = 301; gameOver = false; winner = null;
  markers = [];
  baseAim = { x: C, y: C };
  wp = null; wpSinceBull = 0;
  logEl.textContent = '';
  updateHeader();
  setMsg(turn === CFG.me ? 'Your turn. Tap when the target is over your number, or drag to steer it.' : CFG.foeName + ' is throwing...');
  postState();
});
document.getElementById('btnSound').addEventListener('click', function (e) {
  soundOn = !soundOn;
  e.target.textContent = soundOn ? 'SOUND ON' : 'SOUND OFF';
  if (soundOn) ensureAudio();
});
document.getElementById('btnLeave').addEventListener('click', function () {
  if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
});

function frame(now) {
  requestAnimationFrame(frame);
  var t = now / 1000;
  var dt = lastT ? Math.min(0.05, t - lastT) : 0.016;
  lastT = t;
  if (!dragging && !gameOver) {
    if (!wp) pickWaypoint();
    if (t >= wpRedirectAt) {
      wpRedirectAt = t + 0.8 + Math.random() * 0.7;
      if (Math.random() < 0.3) wp = null;
    }
    if (wp) {
      var dx = wp.x - baseAim.x, dy = wp.y - baseAim.y;
      var dist = Math.hypot(dx, dy);
      if (dist < 12) {
        wp = null;
      } else {
        var ux = dx / dist, uy = dy / dist;
        var step = wpSpeed * dt;
        baseAim.x += ux * step + (-uy) * (Math.random() - 0.5) * 6;
        baseAim.y += uy * step + (ux) * (Math.random() - 0.5) * 6;
        var br = Math.hypot(baseAim.x - C, baseAim.y - C);
        if (br > 175) { baseAim.x = C + (baseAim.x - C) * 175 / br; baseAim.y = C + (baseAim.y - C) * 175 / br; }
      }
    }
  }
  drawBoard(t);
}
updateHeader();
requestAnimationFrame(frame);
})();
</script>
</body>
</html>
`;
