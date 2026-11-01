"""Street Legends frontend: darts PvP FIX - makes the PLAYER VS PLAYER button open the game invite room (tap menu gains PLAYER VS PLAYER, rooms + chat + PvP game).
Run from repo root: python3 frontend/patch-house-darts-pvp.py
Idempotent - safe to re-run.
Adapted from the pool PvP v3 patch (same proven pattern: robust imports + scoped menu guard).
FRONTEND ONLY - reload Expo Go to check. Rooms work once the backend darts-rooms
endpoints are live; if the backend is not live yet, the rooms screen says so instead of crashing.
"""
import re

INDEX = "frontend/app/(tabs)/index.tsx"
PVP_TS = "frontend/components/DartGamePvpHtml.ts"
API_BASE = "https://gta-quest-map.emergent.host"
PVP_TS_CONTENT = """export const DART_PVP_HTML = `<!DOCTYPE html>
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
"""

STATE_OLD = " const [interiorHouse, setInteriorHouse] = useState<any | null>(null);"
STATE_PVP = STATE_OLD + "\n  const [dartPvpOpen, setDartPvpOpen] = useState(false);\n  const [dartPvpGameOpen, setDartPvpGameOpen] = useState(false);\n  const [dartPvpRoom, setDartPvpRoom] = useState<any | null>(null);"
HANDLERS_PVP = """  const handleDartPvpLeave = async () => {
    if (dartPvpRoom?.code) {
      try { await fetch(API_BASE + '/api/darts/rooms/' + dartPvpRoom.code + '/leave', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId }) }); } catch (e) {}
    }
    setDartPvpRoom(null);
    setDartPvpOpen(false);
    setDartPvpGameOpen(false);
  };
"""
MAP_ANCHOR = "export default function MapScreen() {"
MODAL_ANCHOR = "      {/* House Interior Modal */}"
WEBVIEW_BLOCK = """let PoolWebView: any = null;
try { PoolWebView = require('react-native-webview').default; } catch (e) { PoolWebView = null; }

"""
PVP_COMPONENTS = """const DartPvpGameModal = ({ visible, onClose, room, playerId }: { visible: boolean; onClose: () => void; room: any; playerId: string }) => {
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
        const res = await fetch(API_BASE + '/api/darts/rooms/' + code);
        if (!res.ok) return;
        const data = await res.json();
        const st = data?.state;
        if (st) {
          const js = JSON.stringify(st);
          if (js !== lastStateRef.current) {
            lastStateRef.current = js;
            if (webRef.current) {
              webRef.current.injectJavaScript('window.dispatchEvent(new CustomEvent("dart-state", {detail: ' + js + '})); true;');
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
      if (msg?.type === 'dart-shot' && msg.state) {
        lastStateRef.current = JSON.stringify(msg.state);
        const res = await fetch(API_BASE + '/api/darts/rooms/' + code + '/shot', {
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
  const pvpConfig = 'window.DART_PVP = ' + JSON.stringify({ me: me, foe: foeId, foeName: foeName, hostId: hostId }) + '; true;';
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
          <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>DARTBOARD - YOU vs {foeName}</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {pvpError ? (<Text style={{ color: '#ff6666', textAlign: 'center', fontSize: 12, marginBottom: 6 }}>{pvpError}</Text>) : null}
        {PoolWebView ? (
          <PoolWebView
            source={{ html: DART_PVP_HTML }}
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
          <Text style={{ color: '#ffffff', textAlign: 'center', marginTop: 40 }}>Darts game needs WebView, which is not available in this build.</Text>
        )}
      </View>
    </Modal>
  );
};

const DartPvpModal = ({ visible, onClose, playerId, playerName, room, setRoom, onPlay, onLeave }: { visible: boolean; onClose: () => void; playerId: string; playerName: string; room: any; setRoom: (r: any) => void; onPlay: () => void; onLeave: () => void }) => {
  const [codeInput, setCodeInput] = useState('');
  const [chatInput, setChatInput] = useState('');
  const [info, setInfo] = useState('');
  const [busy, setBusy] = useState(false);
  const showNotLive = () => setInfo('Darts rooms are not live yet - the backend still needs a Deploy that picks up the rooms code.');
  const createRoom = async () => {
    setBusy(true); setInfo('');
    try {
      const res = await fetch(API_BASE + '/api/darts/rooms/create', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId, player_name: playerName }) });
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
      const res = await fetch(API_BASE + '/api/darts/rooms/join', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: code, player_id: playerId, player_name: playerName }) });
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
      const res = await fetch(API_BASE + '/api/darts/rooms/' + room.code + '/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: playerId, player_name: playerName, text: text }) });
      if (res.ok) { const data = await res.json(); setRoom(data); }
    } catch (e) {}
  };
  useEffect(() => {
    if (!visible || !room?.code) return;
    const poll = async () => {
      try {
        const res = await fetch(API_BASE + '/api/darts/rooms/' + room.code);
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
        <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 18, textAlign: 'center', marginBottom: 4 }}>DARTBOARD - PLAYER VS PLAYER</Text>
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
    """Insert an import line after the last existing import. Handles multi-line
    imports: the insert lands after the line holding the import's `from '...'`
    clause, not after the opening `import ` line (v3's version could split a
    multi-line import by inserting inside it). Returns (src, ok)."""
    lines = src.split("\n")
    last_end = -1
    in_import = False
    for i, ln in enumerate(lines):
        if ln.startswith("import "):
            in_import = True
        if in_import and re.search(r"from\s+['\"]", ln):
            last_end = i
            in_import = False
    if last_end == -1:
        return src, False
    lines.insert(last_end + 1, line)
    return "\n".join(lines), True

def main():
    src = open(INDEX).read()
    with open(PVP_TS, "w") as f:
        f.write(PVP_TS_CONTENT)
    print("OK: DartGamePvpHtml.ts written")
    import_ok = False
    if "DartGamePvpHtml" in src:
        print("SKIP: DartGamePvpHtml already imported")
        import_ok = True
    else:
        src, ok = import_after_last(src, "import { DART_PVP_HTML } from '../../components/DartGamePvpHtml';")
        if ok and "DART_PVP_HTML" in src:
            print("OK: DartGamePvpHtml imported")
            import_ok = True
        else:
            print("WARNING: could not add DartGamePvpHtml import")
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
    if "const DartPvpModal" in src and "const DartPvpGameModal" in src:
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
    mpos = src.find("DartboardMenuModal")
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
        print("WARNING: DartboardMenuModal component not found, button not added")
    else:
        win = src[mpos:win_span_end]
        if "onPlayPvp" in win:
            d_ok = True
            t_ok = True
        else:
            d_ok = False
            if "onPlay, onMove" in win:
                win = win.replace("onPlay, onMove", "onPlay, onPlayPvp, onMove", 1)
                d_ok = True
            elif "onPlayPvc," in win:
                win = win.replace("onPlay,", "onPlay, onPlayPvp,", 1)
                d_ok = True
            t_ok = False
            if "onPlay: () => void;" in win:
                win = win.replace("onPlay: () => void;", "onPlay: () => void; onPlayPvp?: () => void;", 1)
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
    if "dartPvpOpen" in src:
        print("SKIP: PvP state already present")
        state_ok = True
    else:
        dart_menu_line = None
        for ln in src.split("\n"):
            if "dartMenuOpen" in ln and "useState" in ln:
                dart_menu_line = ln
                break
        if dart_menu_line:
            src = src.replace(dart_menu_line, dart_menu_line + "\n  const [dartPvpOpen, setDartPvpOpen] = useState(false);\n  const [dartPvpGameOpen, setDartPvpGameOpen] = useState(false);\n  const [dartPvpRoom, setDartPvpRoom] = useState<any | null>(null);\n" + HANDLERS_PVP.rstrip("\n"), 1)
            print("OK: PvP state + leave handler added")
            state_ok = True
        elif STATE_OLD in src:
            src = src.replace(STATE_OLD, STATE_PVP + "\n" + HANDLERS_PVP.rstrip("\n"), 1)
            print("OK: PvP state + leave handler added (fallback anchor)")
            state_ok = True
        else:
            print("WARNING: no state anchor found, PvP state not added")
    if state_ok and components_ok:
        render_block = """{dartPvpOpen ? (<DartPvpModal visible={dartPvpOpen} onClose={() => setDartPvpOpen(false)} playerId={playerId} playerName={'Player'} room={dartPvpRoom} setRoom={setDartPvpRoom} onPlay={() => { setDartPvpOpen(false); setDartPvpGameOpen(true); }} onLeave={handleDartPvpLeave} />) : null}
      {dartPvpGameOpen && dartPvpRoom ? (<DartPvpGameModal visible={dartPvpGameOpen} onClose={() => { setDartPvpGameOpen(false); setDartPvpOpen(true); }} room={dartPvpRoom} playerId={playerId} />) : null}
      """
        if "DartPvpModal visible" in src:
            print("SKIP: PvP modals already rendered")
        elif MODAL_ANCHOR in src:
            src = src.replace(MODAL_ANCHOR, render_block + MODAL_ANCHOR, 1)
            print("OK: PvP modals rendered")
        else:
            dart_game_line = None
            for ln in src.split("\n"):
                if "DartGameModal visible" in ln:
                    dart_game_line = ln
                    break
            if dart_game_line:
                src = src.replace(dart_game_line, dart_game_line + "\n      " + render_block.rstrip("\n"), 1)
                print("OK: PvP modals rendered (after DartGameModal)")
            else:
                print("WARNING: modal anchor not found, PvP modals not rendered")
    else:
        print("WARNING: PvP modals not rendered (state_ok=%s components_ok=%s)" % (state_ok, components_ok))
    if state_ok:
        menu_render_old = "onPlay={() => { setDartMenuOpen(false); setDartGameOpen(true); }}"
        if "onPlayPvp={() =>" in src:
            print("SKIP: menu already wired to PvP")
        elif menu_render_old in src:
            src = src.replace(menu_render_old, menu_render_old + " onPlayPvp={() => { setDartMenuOpen(false); setDartPvpOpen(true); }}", 1)
            print("OK: menu wired to PvP screen")
        else:
            wired = False
            for ln in src.split("\n"):
                if "DartboardMenuModal visible" in ln and "onPlayPvp=" not in ln:
                    prop = " onPlayPvp={() => { setDartMenuOpen(false); setDartPvpOpen(true); }}"
                    if " onSell=" in ln:
                        src = src.replace(ln, ln.replace(" onSell=", prop + " onSell=", 1), 1)
                    elif " />" in ln:
                        src = src.replace(ln, ln.replace(" />", prop + " />", 1), 1)
                    else:
                        continue
                    print("OK: menu wired to PvP screen (render line fallback)")
                    wired = True
                    break
            if not wired:
                print("WARNING: menu render line not found, PvP button not wired")
    open(INDEX, "w").write(src)
    print("HOUSE_DART_PVP_FIX_OK")

if __name__ == "__main__":
    main()
