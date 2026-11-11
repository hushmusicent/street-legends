// ACTIVITY_CENTER_POP_SHOT_HTML
export const POP_SHOT_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Pop Shot - Arcade Basketball</title>
<style>
  html,body{margin:0;padding:0;height:100%;background:#14101f;overflow:hidden;
    font-family:Arial,Helvetica,sans-serif;-webkit-user-select:none;user-select:none;
    touch-action:none}
  #wrap{position:relative;width:100%;height:100%}
  #cv{position:absolute;inset:0;width:100%;height:100%;display:block}
  /* the top score bar */
  #sb{position:absolute;top:0;left:0;right:0;z-index:10;display:flex;align-items:center;
    background:linear-gradient(90deg,#4a148c,#6a1b9a);color:#fff;padding:8px 10px;gap:10px}
  #sb .sc{font-weight:900;font-size:22px;white-space:nowrap}
  #sb .sc .you{color:#ffe082}
  #sb .card{flex:1;text-align:center;line-height:1.15}
  #sb .card b{font-size:15px}
  #sb .card span{font-size:11px;color:#e1bee7}
  #sb .pill{background:#fff;color:#4a148c;font-weight:900;font-size:13px;
    padding:5px 10px;border-radius:20px;white-space:nowrap}
  #sb .pill.hot{background:#ff5722;color:#fff}
  /* message toast */
  #msg{position:absolute;top:60px;left:50%;transform:translateX(-50%);z-index:10;
    background:rgba(0,0,0,0.65);color:#fff;font-weight:900;font-size:20px;
    padding:8px 18px;border-radius:12px;display:none;pointer-events:none}
  #msg.show{display:block}
  /* the shot meter: vertical bar on the left, fills bottom to top */
  #meter{position:absolute;left:14px;top:120px;width:44px;height:280px;z-index:9;
    background:rgba(0,0,0,0.6);border:2px solid #fff;border-radius:10px;overflow:hidden}
  #meterZone{position:absolute;left:0;right:0;background:rgba(76,175,80,0.55)}
  #meterGood{display:none}
  #meterFill{position:absolute;left:0;right:0;bottom:0;height:0%;background:#e0e0e0}
  #meterLabel{position:absolute;left:14px;top:404px;width:44px;z-index:9;text-align:center;
    color:#fff;font-weight:900;font-size:11px;text-shadow:0 1px 2px #000}
  /* the action button: hold to charge the meter, release to shoot */
  .abtn{position:absolute;z-index:10;width:96px;height:96px;border-radius:50%;border:3px solid #fff;
    color:#fff;font-weight:900;font-size:19px}
  #btnShoot{right:20px;bottom:20px;background:#c62828}
  #btnShoot.held{background:#ff5722;transform:scale(0.94)}
  #btnMenu{position:absolute;top:56px;right:10px;z-index:10;background:rgba(0,0,0,0.55);
    color:#fff;border:2px solid #fff;border-radius:8px;padding:6px 12px;font-weight:bold}
  #btnSound{position:absolute;top:56px;right:86px;z-index:10;background:rgba(0,0,0,0.55);
    color:#fff;border:2px solid #fff;border-radius:8px;padding:6px 10px;font-size:16px}
  /* the menu overlay */
  #overlay{position:absolute;inset:0;z-index:20;background:rgba(10,6,24,0.88);color:#fff;
    display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:16px}
  #overlay.hidden{display:none}
  #overlay h1{margin:0 0 8px;font-size:30px;color:#ffeb3b;letter-spacing:1px}
  #overlay p{margin:0 0 14px;font-size:14px;color:#e1bee7;max-width:520px;line-height:1.45}
  #diffRow{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:16px}
  #diffRow button{background:#311b92;color:#fff;border:2px solid #7e57c2;border-radius:10px;
    padding:9px 13px;font-weight:900;font-size:14px}
  #diffRow button.sel{background:#ffeb3b;color:#311b92;border-color:#ffeb3b}
  #startBtn,#leaveBtn{display:block;width:230px;margin:6px auto;padding:13px;border:none;border-radius:12px;
    font-weight:900;font-size:17px}
  #startBtn{background:#2e7d32;color:#fff}
  #leaveBtn{background:#c62828;color:#fff}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="cv"></canvas>
  <div id="sb">
    <div class="sc"><span class="you">YOU</span> <span id="scYou">0</span> PTS</div>
    <div class="sc" id="scPrize" style="color:#ffd54f">PRIZE $0</div>
    <div class="card"><b id="cardName">POP SHOT</b><br><span id="cardSub">HOLD SHOOT • RELEASE IN THE GREEN</span></div>
    <div class="pill" id="setPill">60s</div>
  </div>
  <div id="msg"></div>
  <div id="meter"><div id="meterGood"></div><div id="meterZone"></div><div id="meterFill"></div></div>
  <div id="meterLabel">POWER</div>
  <button class="abtn" id="btnShoot">SHOOT</button>
  <button id="btnMenu">MENU</button>
  <button id="btnSound" title="Sound on/off">🔊</button>
  <div id="overlay">
    <h1>POP SHOT</h1>
    <p>Arcade basketball, one basket. Hold SHOOT to charge the meter and let go in the green to score. Only the green makes it in. 60 seconds — how many can you hit in a row?</p>
    <div id="diffRow"></div>
    <button id="startBtn">START GAME</button>
    <button id="leaveBtn">LEAVE GAME</button>
  </div>
</div>
<script>
'use strict';
// Backyard Pop Shot: single-basket arcade basketball (Pop-A-Shot style).
// Hold SHOOT to charge the meter (it sweeps up and down), release in the
// green for a swish. 60 seconds, 2 points a make, 3 a make on a hot streak.
var cv = document.getElementById('cv');
var ctx = cv.getContext('2d');
var W = 900, H = 600;
function fitCanvas(){
  var r = cv.parentElement.getBoundingClientRect();
  W = Math.max(320, r.width); H = Math.max(320, r.height);
  cv.width = W; cv.height = H;
}
if (typeof window !== 'undefined' && window.addEventListener){
  window.addEventListener('resize', fitCanvas);
}
fitCanvas();

// ---------- sound (Web Audio, no files; safe no-op without audio) ----------
var SFX = (function(){
  var ac = null, muted = false;
  function ctx_(){
    if (muted) return null;
    try {
      if (typeof AudioContext !== 'undefined'){
        if (!ac) ac = new AudioContext();
        if (ac.state === 'suspended') ac.resume();
        return ac;
      }
      return null;
    } catch (e){ return null; }
  }
  function tone(f0, f1, dur, type, vol){
    var a = ctx_(); if (!a) return;
    try {
      var o = a.createOscillator(), g = a.createGain();
      o.type = type || 'sine';
      o.frequency.setValueAtTime(f0, a.currentTime);
      o.frequency.exponentialRampToValueAtTime(Math.max(20, f1), a.currentTime + dur);
      g.gain.setValueAtTime(vol || 0.15, a.currentTime);
      g.gain.exponentialRampToValueAtTime(0.001, a.currentTime + dur);
      o.connect(g); g.connect(a.destination);
      o.start(); o.stop(a.currentTime + dur);
    } catch (e){}
  }
  function burst(freq, dur, vol){
    var a = ctx_(); if (!a) return;
    try {
      var len = Math.floor(a.sampleRate * dur);
      var buf = a.createBuffer(1, len, a.sampleRate);
      var d = buf.getChannelData(0);
      for (var i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len);
      var src = a.createBufferSource(); src.buffer = buf;
      var f = a.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = freq;
      var g = a.createGain(); g.gain.value = vol || 0.2;
      src.connect(f); f.connect(g); g.connect(a.destination);
      src.start();
    } catch (e){}
  }
  function crowd(dur){
    var a = ctx_(); if (!a) return;
    try {
      var len = Math.floor(a.sampleRate * dur);
      var buf = a.createBuffer(1, len, a.sampleRate);
      var d = buf.getChannelData(0);
      for (var i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * (1 - i / len) * 0.5;
      var src = a.createBufferSource(); src.buffer = buf;
      var f = a.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 900;
      var g = a.createGain(); g.gain.value = 0.25;
      src.connect(f); f.connect(g); g.connect(a.destination);
      src.start();
    } catch (e){}
  }
  return {
    click: function(){ tone(700, 500, 0.06, 'square', 0.08); },
    swish: function(){ burst(1800, 0.18, 0.25); tone(900, 1400, 0.12, 'sine', 0.08); },
    rim: function(){ tone(220, 140, 0.15, 'square', 0.15); burst(500, 0.1, 0.15); },
    board: function(){ tone(160, 90, 0.12, 'square', 0.18); },
    bounce: function(){ tone(140, 70, 0.1, 'sine', 0.15); },
    perfect: function(){ tone(880, 880, 0.09, 'triangle', 0.15); setTimeout(function(){ tone(1175, 1175, 0.12, 'triangle', 0.15); }, 90); },
    score: function(){ tone(660, 880, 0.12, 'triangle', 0.15); },
    buzzer: function(){ tone(220, 180, 0.6, 'sawtooth', 0.2); },
    win: function(){ tone(523, 523, 0.12, 'triangle', 0.15); setTimeout(function(){ tone(659, 659, 0.12, 'triangle', 0.15); }, 120); setTimeout(function(){ tone(784, 784, 0.2, 'triangle', 0.15); }, 240); crowd(0.9); },
    unlock: function(){ ctx_(); },
    toggle: function(){ muted = !muted; return muted; },
    isMuted: function(){ return muted; }
  };
})();

// ---------- difficulties: meter speed + green zone width ----------
var DIFFS = [
  { n: 'ROOKIE',   speed: 0.7,  green: [65, 85] },
  { n: 'AMATEUR',  speed: 0.85, green: [72, 86] },
  { n: 'PRO',      speed: 1.0,  green: [75, 85] },
  { n: 'ALL-STAR', speed: 1.15, green: [78, 84] },
  { n: 'LEGEND',   speed: 1.3,  green: [80, 84] },
];
var diffIdx = 2; // PRO
var GAME_LEN = 60; // seconds
var GRAV = 2200;

// ---------- state ----------
function rimPos(){ return { x: W / 2, y: H * 0.30 }; }
function handsPos(){ return { x: W / 2, y: H - 118 }; }
// NOTE: resetGame MUTATES this one object (never reassigns it) so that
// window.__PA.G -- captured once at load -- always sees the live state.
var G = {};
function resetGame(){
  var rp = rimPos(), hp = handsPos();
  G.started = false; G.over = false;
  G.score = 0; G.best = 0; G.streak = 0; G.bestStreak = 0; G.makes = 0; G.shots = 0;
  // CENTER_PRIZE: cash prize counts. A make is ON FIRE when it is the
  // 3rd straight make (or beyond) — G.streak >= 2 before the increment.
  G.prizeMakes = 0; G.prizeOnFire = 0; G.prizePaid = false;
  G.timeLeft = GAME_LEN;
  G.meter = 0; G.meterDir = 1; G.charging = false;
  G.ball = { x: hp.x, y: hp.y, vx: 0, vy: 0, state: 'hands', t: 0, spin: 0 };
  G.shot = null; // {quality:'perfect'|'good'|'short'|'long', outcome:'swish'|'in'|'out'|'short'|'long', T, tx, ty}
  G.handsLift = 0; G.handsT = 0;
  G.netSway = 0; G.rimShake = 0;
  G.msg = ''; G.msgT = 0;
  G.retT = 0; // ball-return timer
  updateMeterZones();
  updateSB();
}
function setDiff(i){
  diffIdx = i;
  var row = document.getElementById('diffRow');
  if (row){
    var btns = row.querySelectorAll('button');
    for (var b = 0; b < btns.length; b++) btns[b].classList.toggle('sel', b === i);
  }
  updateMeterZones();
}
function updateMeterZones(){
  var g = DIFFS[diffIdx].green;
  // only the green zone shows: release inside it to score.
  var zone = document.getElementById('meterZone');
  if (zone){
    zone.style.bottom = g[0] + '%';
    zone.style.height = (g[1] - g[0]) + '%';
  }
}
function showMsg(t, dur){
  G.msg = t; G.msgT = dur || 1.2;
  var m = document.getElementById('msg');
  if (m){ m.textContent = t; m.classList.add('show'); }
}
function hideMsg(){
  var m = document.getElementById('msg');
  if (m) m.classList.remove('show');
}
// CENTER_PRIZE: running cash total at the current level. Same formula
// as the server (round((makes*10 + onfire*15) * 1.1^level)), so the
// on-screen total always matches the payout. diffIdx is 0-based, so
// level 1 (ROOKIE) is diffIdx 0 and the multiplier is 1.1^diffIdx.
function prizeTotal(){
  return Math.round((G.prizeMakes * 10 + G.prizeOnFire * 15) * Math.pow(1.1, diffIdx));
}
function postPrize(){
  // Pay out once, at the end of the 60 seconds. Quitting early via
  // MENU forfeits the prize. Posts to the app (WebView); in a plain
  // browser there is no ReactNativeWebView and nothing happens.
  if (G.prizePaid) return;
  G.prizePaid = true;
  if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage){
    window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'pop_shot_prize', makes: G.prizeMakes, onfire: G.prizeOnFire, level: diffIdx + 1 }));
  }
}
function updateSB(){
  document.getElementById('scYou').textContent = G.score;
  var pz = document.getElementById('scPrize');
  if (pz) pz.textContent = 'PRIZE $' + prizeTotal();
  document.getElementById('cardSub').textContent =
    G.over ? ('FINAL • ' + G.makes + ' MAKES • BEST STREAK ' + G.bestStreak)
    : (G.streak >= 3 ? ('ON FIRE x' + G.streak + ' • HOLD SHOOT, RELEASE IN THE GREEN')
                     : 'HOLD SHOOT • RELEASE IN THE GREEN');
  var pill = document.getElementById('setPill');
  pill.textContent = G.over ? 'TIME!' : Math.ceil(G.timeLeft) + 's';
  pill.classList.toggle('hot', G.streak >= 3 && !G.over);
  var fill = document.getElementById('meterFill');
  if (fill){
    fill.style.height = G.meter + '%';
    // green only when the meter is inside the green zone; neutral grey
    // everywhere else (no brown, no yellow).
    fill.style.background = qualityOf(G.meter) === 'perfect' ? '#4caf50' : '#e0e0e0';
  }
}
function qualityOf(m){
  var g = DIFFS[diffIdx].green;
  if (m >= g[0] && m <= g[1]) return 'perfect';
  return 'bad';
}
function startGame(){
  resetGame();
  G.started = true; G.over = false;
  document.getElementById('overlay').classList.add('hidden');
  SFX.unlock(); SFX.click();
  showMsg('SHOOT!', 1.0);
}

// ---------- shooting ----------
function shootRelease(){
  if (!G.started || G.over) return;
  if (G.ball.state !== 'hands') return;
  var m = G.meter;
  var q = qualityOf(m);
  var rp = rimPos(), hp = handsPos();
  var T = 0.95; // flight time to the rim (high arc: up over the rim, down behind it)
  var tx, ty, outcome;
  if (q === 'perfect'){
    // inside the green: a clean swish
    tx = rp.x; ty = rp.y; outcome = 'swish';
  } else if (m < DIFFS[diffIdx].green[0]){
    // too weak: falls short of the rim
    tx = rp.x; ty = rp.y + 95; outcome = 'short';
  } else {
    // too strong: sails long off the backboard
    tx = rp.x; ty = rp.y - 55; outcome = 'long';
  }
  var b = G.ball;
  b.vx = (tx - b.x) / T;
  b.vy = (ty - b.y - 0.5 * GRAV * T * T) / T;
  b.state = 'flying'; b.t = 0;
  G.shot = { quality: q, outcome: outcome, T: T, tx: tx, ty: ty, rimHit: false, scored: false };
  G.shots++;
  G.handsT = 0.45; // the hands snap up and follow through
  G.charging = false; G.meter = 0;
  document.getElementById('btnShoot').classList.remove('held');
  SFX.unlock();
  updateSB();
}
function resolveShot(){
  var s = G.shot, b = G.ball;
  if (!s || s.scored) return;
  s.scored = true;
  if (s.outcome === 'swish' || s.outcome === 'in'){
    var pts = 1; // 1 point per made shot
    G.score += pts;
    // CENTER_PRIZE: $10 a make, $15 an ON FIRE make (3rd straight+),
    // +10% per level. Counts only — the dollars are computed by
    // prizeTotal() with the same formula the server uses, so the
    // on-screen total always matches what the backend pays.
    if (G.streak >= 2) G.prizeOnFire++;
    else G.prizeMakes++;
    G.streak++; G.makes++;
    if (G.streak > G.bestStreak) G.bestStreak = G.streak;
    if (s.outcome === 'swish'){ SFX.swish(); if (s.quality === 'perfect') SFX.perfect(); }
    else SFX.score();
    showMsg(s.outcome === 'swish' ? (s.quality === 'perfect' ? 'PERFECT! +' + pts : 'SWISH! +' + pts)
                                   : 'IN! +' + pts, 1.0);
  } else {
    G.streak = 0;
    if (s.outcome === 'out'){ SFX.rim(); showMsg('OFF THE RIM', 1.0); }
    else if (s.outcome === 'short'){ showMsg('TOO SHORT', 1.0); }
    else { SFX.board(); showMsg('TOO LONG', 1.0); }
  }
  updateSB();
}
function update(dt){
  if (!G.started || G.over) return;
  // the clock
  G.timeLeft -= dt;
  if (G.timeLeft <= 0){
    G.timeLeft = 0;
    G.over = true;
    SFX.buzzer();
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('startBtn').textContent = 'REMATCH';
    document.getElementById('cardName').textContent = 'TIME! ' + G.score + ' PTS • $' + prizeTotal() + ' PRIZE';
    showMsg('TIME! • $' + prizeTotal() + ' PRIZE', 1.5);
    postPrize();
    updateSB();
    return;
  }
  if (G.msgT > 0){ G.msgT -= dt; if (G.msgT <= 0) hideMsg(); }
  if (G.netSway > 0) G.netSway = Math.max(0, G.netSway - dt * 2.2);
  if (G.rimShake > 0) G.rimShake = Math.max(0, G.rimShake - dt * 3);
  // the meter sweeps up and down while SHOOT is held
  if (G.charging && G.ball.state === 'hands'){
    var rate = 180 * DIFFS[diffIdx].speed; // meter units per second
    G.meter += G.meterDir * rate * dt;
    if (G.meter >= 100){ G.meter = 100; G.meterDir = -1; }
    if (G.meter <= 0){ G.meter = 0; G.meterDir = 1; }
  }
  // hands follow-through after a release
  if (G.handsT > 0){
    G.handsT -= dt;
    var p = 1 - Math.max(0, G.handsT) / 0.45;
    G.handsLift = Math.sin(Math.min(1, p * 1.6) * Math.PI * 0.5);
  } else {
    G.handsLift = Math.max(0, G.handsLift - dt * 3);
  }
  var b = G.ball, rp = rimPos(), hp = handsPos();
  if (b.state === 'flying'){
    b.t += dt;
    b.vy += GRAV * dt;
    b.x += b.vx * dt;
    b.y += b.vy * dt;
    b.spin += dt * 9;
    var s = G.shot;
    if (s && b.vy > 0){
      var dx = b.x - rp.x, dy = b.y - rp.y;
      var dist = Math.sqrt(dx * dx + dy * dy);
      // reaching the rim plane: decide the outcome
      if (s.outcome === 'swish' && dist < 16){
        G.netSway = 1; resolveShot();
        b.state = 'through'; b.t = 0;
      } else if (s.outcome === 'in' && dist < 26 && !s.rimHit){
        s.rimHit = true; G.rimShake = 1; SFX.rim();
        b.vx *= -0.25; b.vy = Math.abs(b.vy) * 0.35; // rattle, then drop in
        b.x = rp.x + (b.x < rp.x ? -20 : 20);
      } else if (s.outcome === 'in' && s.rimHit && b.y > rp.y + 8){
        G.netSway = 1; resolveShot();
        b.state = 'through'; b.t = 0;
      } else if (s.outcome === 'out' && dist < 26 && !s.rimHit){
        s.rimHit = true; G.rimShake = 1; SFX.rim();
        b.vx = (b.x < rp.x ? -1 : 1) * 260; b.vy = -140; // bounce off the rim, out
        resolveShot();
      } else if (s.outcome === 'short' && b.y > rp.y + 60){
        resolveShot();
        b.state = 'returning'; b.t = 0;
      } else if (s.outcome === 'long' && b.y < rp.y - 30 && !s.rimHit){
        s.rimHit = true; SFX.board();
        b.vy = Math.abs(b.vy) * 0.4; b.vx = -b.vx * 0.3; // off the board, back out
        resolveShot();
        b.state = 'returning'; b.t = 0;
      }
    }
    // safety: a flying ball that left the scene comes back
    if (b.y > H + 60 || b.x < -80 || b.x > W + 80){ b.state = 'returning'; b.t = 0; }
  } else if (b.state === 'through'){
    // dropping through the net, then the ball rolls back to the hands
    b.t += dt;
    b.vy += GRAV * dt * 0.6;
    b.y += b.vy * dt * 0.5;
    b.x += (hp.x - b.x) * dt * 2;
    if (b.t > 0.45){ b.state = 'returning'; b.t = 0; }
  } else if (b.state === 'returning'){
    // the ball rolls back down the ramp to the hands
    b.t += dt;
    var k = Math.min(1, b.t / 0.5);
    b.x = b.x + (hp.x - b.x) * Math.min(1, dt * 6);
    b.y = b.y + (hp.y - b.y) * Math.min(1, dt * 6);
    if (k >= 1 || (Math.abs(b.x - hp.x) < 6 && Math.abs(b.y - hp.y) < 6)){
      b.x = hp.x; b.y = hp.y; b.vx = 0; b.vy = 0; b.state = 'hands';
      SFX.bounce();
    }
  } else {
    // in the hands: it rides with the hands (which lift on a shot)
    b.x = hp.x; b.y = hp.y - G.handsLift * 26;
  }
  updateSB();
}

// ---------- drawing ----------
function drawBall(x, y, r, spin){
  ctx.save();
  ctx.translate(x, y);
  ctx.rotate(spin || 0);
  var g = ctx.createRadialGradient(-r * 0.35, -r * 0.4, r * 0.15, 0, 0, r * 1.05);
  g.addColorStop(0, '#ffb74d'); g.addColorStop(0.6, '#f57c00'); g.addColorStop(1, '#bf5a00');
  ctx.fillStyle = g;
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = 'rgba(60,20,0,0.85)'; ctx.lineWidth = Math.max(1.5, r * 0.08);
  ctx.beginPath(); ctx.arc(0, 0, r, 0, Math.PI * 2); ctx.stroke();
  // specular highlight: the ball is a lit sphere, not a flat disc
  ctx.fillStyle = 'rgba(255,255,255,0.75)';
  ctx.beginPath(); ctx.ellipse(-r * 0.36, -r * 0.44, r * 0.22, r * 0.14, -0.6, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.moveTo(-r, 0); ctx.lineTo(r, 0); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(0, -r); ctx.lineTo(0, r); ctx.stroke();
  ctx.beginPath(); ctx.arc(-r * 1.35, 0, r * 0.95, -0.7, 0.7); ctx.stroke();
  ctx.beginPath(); ctx.arc(r * 1.35, 0, r * 0.95, Math.PI - 0.7, Math.PI + 0.7); ctx.stroke();
  ctx.restore();
}
function drawHands(){
  var hp = handsPos();
  var lift = G.handsLift;
  var hx = hp.x, hy = hp.y - lift * 26;
  var r = 26; // ball radius in the hands
  var s = Math.min(W, H) / 600; // scale with screen
  ctx.save();
  // ground shadow under the hands
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.beginPath(); ctx.ellipse(hx, H - 34, 70 * s + 20, 10, 0, 0, Math.PI * 2); ctx.fill();
  var skin = '#c68642', skinD = '#a5662e';
  // the wrists / forearms come up from the bottom edge
  ctx.strokeStyle = skin; ctx.lineCap = 'round';
  ctx.lineWidth = 22 * s + 6;
  ctx.beginPath(); ctx.moveTo(hx - 52 * s, H + 6); ctx.lineTo(hx - 34 * s, hy + 26 * s); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(hx + 52 * s, H + 6); ctx.lineTo(hx + 34 * s, hy + 26 * s); ctx.stroke();
  // the palms cup the ball from below
  ctx.fillStyle = skin;
  ctx.beginPath(); ctx.ellipse(hx - 30 * s, hy + 20 * s, 20 * s + 4, 15 * s + 3, -0.5, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(hx + 30 * s, hy + 20 * s, 20 * s + 4, 15 * s + 3, 0.5, 0, Math.PI * 2); ctx.fill();
  // the fingers curl up the sides of the ball
  ctx.strokeStyle = skinD; ctx.lineWidth = 7 * s + 2;
  var fl = lift > 0.4 ? 1 : 0; // on the follow-through the fingers point up
  for (var f = 0; f < 3; f++){
    var fx = -r + 4 + f * (r * 0.85);
    var fy0 = hy + 14 * s - f * 2;
    var fy1 = hy - (6 + f * 7) * s - (fl ? 14 * s : 0);
    ctx.beginPath(); ctx.moveTo(hx - 26 * s + fx * 0.4, fy0); ctx.lineTo(hx - 26 * s + fx * 0.4, fy1); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(hx + 26 * s - fx * 0.4, fy0); ctx.lineTo(hx + 26 * s - fx * 0.4, fy1); ctx.stroke();
  }
  // the thumbs brace the front of the ball
  ctx.strokeStyle = skin; ctx.lineWidth = 9 * s + 2;
  ctx.beginPath(); ctx.moveTo(hx - 34 * s, hy + 8 * s); ctx.lineTo(hx - 16 * s, hy - 2 * s); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(hx + 34 * s, hy + 8 * s); ctx.lineTo(hx + 16 * s, hy - 2 * s); ctx.stroke();
  ctx.restore();
  // the ball sits in the hands (drawn after the palms, before the fingertips)
  if (G.ball.state === 'hands'){
    drawBall(hx, hy, r, 0);
    // fingertips over the ball's edge
    ctx.save();
    ctx.strokeStyle = '#c68642'; ctx.lineCap = 'round'; ctx.lineWidth = 6 * s + 2;
    for (var f2 = 0; f2 < 3; f2++){
      var fx2 = -r + 4 + f2 * (r * 0.85);
      ctx.beginPath(); ctx.moveTo(hx - 26 * s + fx2 * 0.4, hy + 6 * s); ctx.lineTo(hx - 26 * s + fx2 * 0.4, hy - (4 + f2 * 7) * s); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(hx + 26 * s - fx2 * 0.4, hy + 6 * s); ctx.lineTo(hx + 26 * s - fx2 * 0.4, hy - (4 + f2 * 7) * s); ctx.stroke();
    }
    ctx.restore();
  }
}
function drawMachine(){
  var rp = rimPos();
  var cx = W / 2;
  // the arcade backdrop: dark gym wall with a glow behind the board
  var bg = ctx.createLinearGradient(0, 0, 0, H);
  bg.addColorStop(0, '#1b1030'); bg.addColorStop(0.55, '#241a3d'); bg.addColorStop(1, '#120d1e');
  ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
  // floor + a soft light pool in the centre (3D depth)
  ctx.fillStyle = '#2d1f3d'; ctx.fillRect(0, H - 70, W, 70);
  var pool = ctx.createRadialGradient(cx, H - 36, 10, cx, H - 36, 260);
  pool.addColorStop(0, 'rgba(255,220,120,0.14)'); pool.addColorStop(1, 'rgba(255,220,120,0)');
  ctx.fillStyle = pool; ctx.fillRect(0, H - 70, W, 70);
  ctx.fillStyle = 'rgba(255,255,255,0.06)';
  for (var fx = 0; fx < W; fx += 90) ctx.fillRect(fx, H - 70, 44, 70);
  // side netting (the Pop-A-Shot cage)
  ctx.strokeStyle = 'rgba(255,255,255,0.35)'; ctx.lineWidth = 1.5;
  var topY = 62, botY = H - 70;
  for (var i = 0; i <= 10; i++){
    var t = i / 10;
    ctx.beginPath(); ctx.moveTo(cx - 150 - t * 40, topY + t * (botY - topY) * 0.4);
    ctx.lineTo(cx - 190, topY + t * (botY - topY)); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + 150 + t * 40, topY + t * (botY - topY) * 0.4);
    ctx.lineTo(cx + 190, topY + t * (botY - topY)); ctx.stroke();
  }
  for (var j = 0; j < 7; j++){
    var y = topY + (j / 6) * (botY - topY) * 0.85;
    ctx.beginPath(); ctx.moveTo(cx - 190, y + j * 8); ctx.lineTo(cx - 150, y); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(cx + 190, y + j * 8); ctx.lineTo(cx + 150, y); ctx.stroke();
  }
  // the ramp the ball rolls back down: lit top edge, dark base (3D)
  var rampG = ctx.createLinearGradient(0, botY - 46, 0, botY);
  rampG.addColorStop(0, '#5a4480'); rampG.addColorStop(1, '#2c1f42');
  ctx.fillStyle = rampG;
  ctx.beginPath();
  ctx.moveTo(cx - 190, botY); ctx.lineTo(cx + 190, botY);
  ctx.lineTo(cx + 150, botY - 46); ctx.lineTo(cx - 150, botY - 46);
  ctx.closePath(); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.16)';
  ctx.fillRect(cx - 150, botY - 46, 300, 6);
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.fillRect(cx - 190, botY - 3, 380, 3);
  // the backboard (single basket, black with gold trim)
  var bw = 250, bh = 130, bx = cx - bw / 2, by = 58;
  var sh = ctx.createRadialGradient(cx, by + bh / 2, 20, cx, by + bh / 2, 260);
  sh.addColorStop(0, 'rgba(255,235,59,0.20)'); sh.addColorStop(1, 'rgba(255,235,59,0)');
  ctx.fillStyle = sh; ctx.fillRect(cx - 280, by - 40, 560, 260);
  ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.fillRect(bx + 5, by + 7, bw, bh); // drop shadow
  var boardG = ctx.createLinearGradient(0, by, 0, by + bh);
  boardG.addColorStop(0, '#232323'); boardG.addColorStop(0.5, '#111111'); boardG.addColorStop(1, '#050505');
  ctx.fillStyle = boardG; ctx.fillRect(bx, by, bw, bh);
  ctx.strokeStyle = '#f5c518'; ctx.lineWidth = 5; ctx.strokeRect(bx, by, bw, bh);
  ctx.strokeStyle = 'rgba(255,255,255,0.25)'; ctx.lineWidth = 1.5;
  ctx.strokeRect(bx + 3, by + 3, bw - 6, bh - 6); // inner bevel highlight
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 3;
  ctx.strokeRect(cx - 42, by + 62, 84, 56); // the shooter's square
  ctx.fillStyle = '#f5c518'; ctx.font = '900 22px Arial'; ctx.textAlign = 'center';
  ctx.fillText('POP SHOT', cx, by + 34);
  // the rim -- BACK half only (top arc). The front half is drawn in
  // drawNet(), AFTER the ball, so a made shot reads as passing THROUGH
  // the rim instead of flying over it. ry 13: a taller opening, so the
  // ball visibly fits through the ring.
  var shake = G.rimShake > 0 ? Math.sin(G.rimShake * 40) * 2 * G.rimShake : 0;
  var rimY = rp.y + shake;
  ctx.strokeStyle = '#bf360c'; ctx.lineWidth = 7;
  ctx.beginPath(); ctx.ellipse(cx, rimY, 34, 13, 0, Math.PI, Math.PI * 2); ctx.stroke();
}
// the rim's FRONT half + the net, drawn AFTER the ball so the ball reads
// as dropping THROUGH the rim and inside the net (not in front of them).
function drawNet(){
  var rp = rimPos();
  var cx = W / 2;
  var shake = G.rimShake > 0 ? Math.sin(G.rimShake * 40) * 2 * G.rimShake : 0;
  var rimY = rp.y + shake;
  // rim front half (bottom arc): bright metal, top highlight, shadow below
  ctx.strokeStyle = 'rgba(0,0,0,0.4)'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(cx, rimY + 3, 34, 13, 0, 0, Math.PI); ctx.stroke();
  ctx.strokeStyle = '#ff5722'; ctx.lineWidth = 7;
  ctx.beginPath(); ctx.ellipse(cx, rimY, 34, 13, 0, 0, Math.PI); ctx.stroke();
  ctx.strokeStyle = '#ffab91'; ctx.lineWidth = 2.5;
  ctx.beginPath(); ctx.ellipse(cx, rimY - 1, 34, 13, 0, 0.15, Math.PI - 0.15); ctx.stroke();
  // the net (sways after a make): tapered cone, strings bow out, edges dim
  var sway = G.netSway > 0 ? Math.sin(G.netSway * 18) * 6 * G.netSway : 0;
  ctx.lineWidth = 1.6;
  for (var n = -2; n <= 2; n++){
    var a = (Math.abs(n) === 0) ? 0.95 : (Math.abs(n) === 1 ? 0.8 : 0.6);
    ctx.strokeStyle = 'rgba(255,255,255,' + a.toFixed(2) + ')';
    ctx.beginPath();
    ctx.moveTo(cx + n * 13, rimY + 7);
    ctx.quadraticCurveTo(cx + n * 15 + sway * 0.5, rimY + 30, cx + n * 6 + sway, rimY + 56);
    ctx.stroke();
  }
  ctx.strokeStyle = 'rgba(255,255,255,0.55)';
  ctx.beginPath(); ctx.moveTo(cx - 27, rimY + 22); ctx.lineTo(cx + 27, rimY + 22); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(cx - 19, rimY + 40); ctx.lineTo(cx + 19, rimY + 40); ctx.stroke();
}
function draw(){
  ctx.clearRect(0, 0, W, H);
  drawMachine();
  drawHands();
  var b = G.ball;
  var rp = rimPos();
  // The ball is BEHIND the rim/net only while it is dropping INTO the
  // basket (through the rim opening). On the way UP it is IN FRONT of the
  // machine, so the rim/net draw FIRST and the ball draws OVER them --
  // it must never read as going up through the rim and net.
  var behind = (b.state === 'through') ||
               (b.state === 'flying' && b.vy > 0 && b.y > rp.y - 40 && b.y < rp.y + 30);
  if (!behind) drawNet();
  if (b.state !== 'hands'){
    // the ball's shadow on the floor while it flies: smaller + lighter
    // the higher the ball is (3D height cue)
    var gy = H - 74;
    var hF = Math.max(0, Math.min(1, (gy - b.y) / 480));
    var shR = 22 * (1 - hF * 0.45);
    var shA = Math.max(0.06, 0.35 - hF * 0.27);
    ctx.fillStyle = 'rgba(0,0,0,' + shA.toFixed(2) + ')';
    ctx.beginPath(); ctx.ellipse(b.x, gy, shR, shR * 0.32, 0, 0, Math.PI * 2); ctx.fill();
    drawBall(b.x, b.y, 24, b.spin);
  }
  // rim front + net OVER the ball only when it is dropping in behind them
  if (behind) drawNet();
  // the streak flame
  if (G.streak >= 3 && !G.over){
    ctx.fillStyle = '#ff5722'; ctx.font = '900 26px Arial'; ctx.textAlign = 'center';
    ctx.fillText('🔥 ON FIRE x' + G.streak, W / 2, 132);
  }
  if (G.over){
    ctx.fillStyle = 'rgba(0,0,0,0.45)'; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#ffeb3b'; ctx.font = '900 34px Arial'; ctx.textAlign = 'center';
    ctx.fillText('TIME!  ' + G.score + ' PTS', W / 2, H / 2 - 10);
    ctx.fillStyle = '#fff'; ctx.font = '700 19px Arial';
    ctx.fillText(G.makes + ' makes • best streak ' + G.bestStreak, W / 2, H / 2 + 24);
  }
}

// ---------- input ----------
function frame(ts){
  if (typeof requestAnimationFrame !== 'undefined'){
    requestAnimationFrame(frame);
  }
  var now = ts || 0;
  if (!frame.last) frame.last = now;
  var dt = Math.min(0.05, (now - frame.last) / 1000 || 0.016);
  frame.last = now;
  if (G.started && !G.over) update(dt);
  draw();
}
function bindUI(){
  // difficulty buttons
  var row = document.getElementById('diffRow');
  DIFFS.forEach(function(d, i){
    var b = document.createElement('button');
    b.textContent = d.n;
    if (i === diffIdx) b.classList.add('sel');
    b.addEventListener('click', function(){ setDiff(i); SFX.click(); });
    row.appendChild(b);
  });
  document.getElementById('startBtn').addEventListener('click', function(){
    startGame();
  });
  document.getElementById('leaveBtn').addEventListener('click', function(){
    if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage){
      window.ReactNativeWebView.postMessage('close');
    } else {
      document.getElementById('overlay').classList.add('hidden');
      resetGame();
    }
  });
  document.getElementById('btnMenu').addEventListener('click', function(){
    SFX.unlock(); SFX.click();
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('startBtn').textContent = G.started && !G.over ? 'RESUME' : 'START GAME';
  });
  document.getElementById('btnSound').addEventListener('click', function(){
    SFX.unlock();
    var off = SFX.toggle();
    document.getElementById('btnSound').textContent = off ? '🔇' : '🔊';
  });
  // SHOOT: hold to charge the meter, release to shoot
  var shootBtn = document.getElementById('btnShoot');
  function pressOn(e){
    if (e) e.preventDefault();
    if (!G.started || G.over) return;
    if (G.ball.state !== 'hands') return;
    SFX.unlock();
    G.charging = true;
    if (G.meterDir !== 1 && G.meter <= 0) G.meterDir = 1;
    shootBtn.classList.add('held');
  }
  function pressOff(e){
    if (e) e.preventDefault();
    if (!G.charging) return;
    shootBtn.classList.remove('held');
    shootRelease();
  }
  shootBtn.addEventListener('pointerdown', pressOn);
  shootBtn.addEventListener('pointerup', pressOff);
  shootBtn.addEventListener('pointercancel', pressOff);
  shootBtn.addEventListener('pointerleave', pressOff);
  // keyboard: hold Space to charge, release to shoot
  if (typeof window !== 'undefined' && window.addEventListener){
    window.addEventListener('keydown', function(e){
      if (e.code === 'Space' && !e.repeat) pressOn(e);
    });
    window.addEventListener('keyup', function(e){
      if (e.code === 'Space') pressOff(e);
    });
  }
}

resetGame();
bindUI();
updateMeterZones();
if (typeof requestAnimationFrame !== 'undefined'){
  requestAnimationFrame(frame);
}

// hooks for the smoke suite
window.__PA = {
  G: G, DIFFS: DIFFS, GAME_LEN: GAME_LEN, GRAV: GRAV,
  rimPos: rimPos, handsPos: handsPos,
  startGame: startGame, resetGame: resetGame, setDiff: setDiff,
  update: update, draw: draw, frame: frame,
  shootRelease: shootRelease, resolveShot: resolveShot,
  qualityOf: qualityOf, updateSB: updateSB, showMsg: showMsg,
  prizeTotal: prizeTotal, postPrize: postPrize
};
</script>
</body>
</html>
`;
