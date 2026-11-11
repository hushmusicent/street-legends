// PARK_ONE_ON_ONE_HTML
export const ONE_ON_ONE_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Park 1-on-1 '21</title>
<style>
  html,body{margin:0;padding:0;background:#111;height:100%;overflow:hidden;
    font-family:Arial,Helvetica,sans-serif;-webkit-user-select:none;user-select:none;
    -webkit-tap-highlight-color:transparent;touch-action:none}
  #wrap{position:relative;width:100vw;height:100vh;max-width:100vw;max-height:100vh;overflow:hidden}
  #cv{position:absolute;inset:0;width:100%;height:100%;display:block}
  /* the scoreboard */
  #sb{position:absolute;top:0;left:0;right:0;z-index:5;display:flex;justify-content:space-between;
    align-items:center;background:linear-gradient(#3b1d5e,#241040);color:#fff;padding:6px 10px;
    font-size:15px;font-weight:bold}
  #sb .you{color:#ffe14d}
  #sb .card{text-align:center;line-height:1.15}
  #sb .card b{font-size:14px}
  #sb .card span{font-size:11px;color:#cdb2ea}
  #sb .pill{background:#fff;color:#3b1d5e;border-radius:20px;padding:4px 12px;font-size:13px}
  #msg{position:absolute;top:52px;left:50%;transform:translateX(-50%);z-index:6;color:#fff;
    background:rgba(0,0,0,0.6);padding:6px 14px;border-radius:10px;font-weight:bold;font-size:15px;
    pointer-events:none;opacity:0;transition:opacity .2s;text-align:center;max-width:92vw}
  #dunkBanner{position:absolute;top:34%;left:50%;transform:translate(-50%,-50%) scale(0.6);z-index:7;
    color:#ffe14d;font-size:34px;font-weight:900;letter-spacing:2px;text-align:center;
    text-shadow:3px 3px 0 #000, -2px -2px 0 #000, 2px -2px 0 #000, -2px 2px 0 #000;
    opacity:0;transition:opacity .15s, transform .15s;pointer-events:none;white-space:nowrap}
  #dunkBanner.show{opacity:1;transform:translate(-50%,-50%) scale(1)}
  /* the difficulty / menu overlay */
  #overlay{position:absolute;inset:0;background:rgba(0,0,0,0.78);z-index:20;
    display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center}
  #overlay.hidden{display:none}
  #overlay h1{margin:0 0 4px;font-size:30px;letter-spacing:2px;color:#ffe14d}
  #overlay p{margin:0 0 16px;color:#cdb2ea;font-size:14px}
  #diffRow{display:flex;gap:6px;margin-bottom:18px;flex-wrap:wrap;justify-content:center}
  #diffRow button{pointer-events:auto;background:#444;color:#fff;border:2px solid #888;
    border-radius:10px;padding:8px 10px;font-weight:bold;font-size:13px}
  #diffRow button.sel{background:#2e7d32;border-color:#fff}
  #startBtn{pointer-events:auto;background:#2e7d32;color:#fff;border:3px solid #fff;border-radius:14px;
    padding:12px 34px;font-size:20px;font-weight:bold;letter-spacing:1px}
  #leaveBtn{pointer-events:auto;background:#c62828;color:#fff;border:2px solid #fff;border-radius:10px;
    padding:8px 18px;font-size:14px;font-weight:bold;margin-top:10px}
  /* the joystick */
  #joy{position:absolute;left:18px;bottom:18px;width:110px;height:110px;border-radius:50%;
    background:rgba(255,255,255,0.12);border:2px solid rgba(255,255,255,0.4);z-index:10}
  #stick{position:absolute;left:33px;top:33px;width:44px;height:44px;border-radius:50%;
    background:rgba(255,255,255,0.75)}
  /* the action buttons */
  .abtn{position:absolute;z-index:10;width:88px;height:88px;border-radius:50%;border:3px solid #fff;
    color:#fff;font-weight:900;font-size:17px}
  #btnA{right:20px;bottom:20px;background:#c62828}
  #btnB{right:118px;bottom:114px;width:70px;height:70px;background:#1565c0;font-size:15px}
  #btnC{right:118px;bottom:20px;width:70px;height:70px;background:#ef6c00;font-size:15px}
  #btnD{right:20px;bottom:118px;width:70px;height:70px;background:#7b1fa2;font-size:15px}
  /* the turbo stamina bar (right above the TURBO button) */
  #stamBar{position:absolute;right:118px;bottom:96px;width:70px;height:10px;
    background:rgba(0,0,0,0.6);border:1px solid #fff;border-radius:5px;z-index:10}
  #stamFill{height:100%;width:100%;background:#ffb300;border-radius:4px}
  #btnMenu{position:absolute;top:56px;right:10px;z-index:10;background:rgba(0,0,0,0.55);
    color:#fff;border:2px solid #fff;border-radius:8px;padding:6px 12px;font-weight:bold}
  #btnSound{position:absolute;top:56px;right:86px;z-index:10;background:rgba(0,0,0,0.55);
    color:#fff;border:2px solid #fff;border-radius:8px;padding:6px 10px;font-size:16px}
  /* the shot meter (jump shots only) */
  #meter{position:absolute;left:50%;bottom:130px;transform:translateX(-50%);width:180px;height:16px;
    background:rgba(0,0,0,0.6);border:2px solid #fff;border-radius:10px;z-index:9;display:none}
  #meterFill{height:100%;width:0%;background:#4caf50;border-radius:8px}
  #meterZone{position:absolute;top:0;bottom:0;background:rgba(255,225,77,0.55)}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="cv"></canvas>
  <div id="sb">
    <div class="sc"><span class="you">YOU</span> <span id="scYou">0</span> - <span id="scCom">0</span> COM</div>
    <div class="card"><b id="cardName">DANTE</b><br><span id="cardSub">FIRST TO 21 • 1 PT A BASKET</span></div>
    <div class="pill" id="setPill">YOU HAVE IT</div>
  </div>
  <div id="msg"></div>
  <div id="dunkBanner"></div>
  <div id="overlay">
    <h1>PARK 1-ON-1 '21</h1>
    <p>Jordan vs Bird style • First to 21, 1 point a basket • 10 signature dunks<br>
    Dribble past him, shoot the jumper, or drive in and throw it down.</p>
    <div id="diffRow"></div>
    <button id="startBtn">START GAME</button>
    <button id="pvpBtn" style="margin-top:10px;background:#6a1b9a;color:#fff;border:3px solid #fff;border-radius:14px;padding:10px 26px;font-size:17px;font-weight:800;cursor:pointer">PLAYER VS PLAYER</button>
    <div id="pvpPanel" class="hidden" style="margin-top:10px;display:flex;flex-direction:column;align-items:center;gap:8px">
      <div style="font-size:14px;color:#ffd54f" id="pvpStatus">Play a real person — one phone creates a room, the other joins with the code.</div>
      <div style="display:flex;gap:8px">
        <button id="pvpCreateBtn" style="background:#2e7d32;color:#fff;border:2px solid #fff;border-radius:10px;padding:8px 14px;font-weight:800;cursor:pointer">CREATE ROOM</button>
        <input id="pvpCodeInput" placeholder="CODE" maxlength="4" inputmode="numeric" style="width:90px;text-align:center;font-size:18px;padding:8px;border-radius:8px;border:2px solid #f5c518;background:#111;color:#fff" />
        <button id="pvpJoinBtn" style="background:#1565c0;color:#fff;border:2px solid #fff;border-radius:10px;padding:8px 14px;font-weight:800;cursor:pointer">JOIN</button>
      </div>
      <div style="font-size:13px;color:#ccc" id="pvpRoomLbl"></div>
    </div>
    <button id="leaveBtn">LEAVE GAME</button>
  </div>
  <div id="meter"><div id="meterZone"></div><div id="meterFill"></div></div>
  <div id="joy"><div id="stick"></div></div>
  <button class="abtn" id="btnA">SHOOT</button>
  <button class="abtn" id="btnB">STEAL</button>
  <button class="abtn" id="btnC">TURBO</button>
  <button class="abtn" id="btnD">DUNK</button>
  <div id="stamBar"><div id="stamFill"></div></div>
  <button id="btnMenu">MENU</button>
  <button id="btnSound" title="Sound on/off">🔊</button>
</div>
<script>
/* =================================================================
   BACKYARD 1-ON-1 '21 (Jordan vs Bird style, built fresh)
   A playground half-court: one hoop, you vs COM, first to 21 with
   1 point a basket. Dribble, shoot the jumper, steal and block on
   defense -- and drive in close to throw down one of 10 signature
   dunks. 3D hues and shadows, side-view running figures with real
   arms and legs, and dunks that look like dunks (the jump, the rise
   to the rim, the slam, the hang). No shortcuts.
   SOUND: every sound is synthesized with the Web Audio API -- no audio
   files to download, so the game stays one small file. The AudioContext
   is created on the first tap (phones block audio until a gesture), and
   every call is a no-op when there is no audio (or when muted), so the
   smoke suites run silent and never crash.
   ================================================================= */

// ---------- the sound engine (Web Audio, synthesized, no files) ----------
var SFX = (function(){
  var ctx = null, muted = false, noiseBuf = null;
  function ac(){
    if (muted) return null;
    if (typeof AudioContext === 'undefined' && typeof webkitAudioContext === 'undefined') return null;
    if (!ctx){
      try { ctx = new (AudioContext || webkitAudioContext)(); } catch (e){ return null; }
    }
    if (ctx.state === 'suspended'){ ctx.resume(); }
    return ctx;
  }
  function noise(){
    if (!noiseBuf){
      noiseBuf = ctx.createBuffer(1, ctx.sampleRate * 0.5, ctx.sampleRate);
      var d = noiseBuf.getChannelData(0);
      for (var i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    return noiseBuf;
  }
  function tone(freq, dur, type, vol, delay, slideTo){
    var c = ac(); if (!c) return;
    var t0 = c.currentTime + (delay || 0);
    var o = c.createOscillator(), g = c.createGain();
    o.type = type || 'sine';
    o.frequency.setValueAtTime(freq, t0);
    if (slideTo) o.frequency.exponentialRampToValueAtTime(slideTo, t0 + dur);
    g.gain.setValueAtTime(vol || 0.2, t0);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    o.connect(g); g.connect(c.destination);
    o.start(t0); o.stop(t0 + dur + 0.02);
  }
  function burst(dur, freq, vol, sweepTo, delay){
    var c = ac(); if (!c) return;
    var t0 = c.currentTime + (delay || 0);
    var src = c.createBufferSource(); src.buffer = noise();
    var f = c.createBiquadFilter(); f.type = 'bandpass'; f.frequency.setValueAtTime(freq, t0);
    if (sweepTo) f.frequency.exponentialRampToValueAtTime(sweepTo, t0 + dur);
    var g = c.createGain();
    g.gain.setValueAtTime(vol || 0.25, t0);
    g.gain.exponentialRampToValueAtTime(0.001, t0 + dur);
    src.connect(f); f.connect(g); g.connect(c.destination);
    src.start(t0); src.stop(t0 + dur + 0.02);
  }
  return {
    unlock: function(){ ac(); },
    toggle: function(){ muted = !muted; return muted; },
    isMuted: function(){ return muted; },
    click: function(){ tone(800, 0.05, 'sine', 0.12); },
    // the dribble: a soft low thud
    dribble: function(){ tone(120, 0.06, 'sine', 0.14, 0, 70); },
    // the ball bouncing off the ground (a loose ball / a missed shot)
    bounce: function(){ tone(100, 0.08, 'sine', 0.16, 0, 60); },
    // a jump shot leaving the hand: a soft swish
    shoot: function(){ burst(0.14, 1000, 0.1, 500); },
    // the ball rattling in (a make): a clean swish + a soft net snap
    swish: function(){ burst(0.18, 1400, 0.16, 700); tone(300, 0.08, 'sine', 0.1, 0.05, 200); },
    // the ball off the rim: a metallic clang
    rim: function(){ tone(620, 0.12, 'square', 0.08); tone(410, 0.1, 'square', 0.06, 0.03); },
    // the backboard: a dull thunk
    board: function(){ tone(95, 0.1, 'sine', 0.22, 0, 60); burst(0.05, 250, 0.12); },
    // a dunk: a deep BOOM + the crowd going up
    dunk: function(){ tone(70, 0.3, 'sine', 0.35, 0, 40); burst(0.15, 300, 0.3); burst(1.2, 1000, 0.12, 500, 0.15); },
    // a block: a sharp smack
    block: function(){ burst(0.08, 900, 0.28); tone(200, 0.08, 'sine', 0.2, 0, 100); },
    // a steal: a quick swipe + a poke
    steal: function(){ burst(0.1, 1600, 0.16, 600); },
    // a point scored: a short two-note chime
    point: function(){ tone(660, 0.12, 'sine', 0.2); tone(880, 0.18, 'sine', 0.2, 0.12); },
    // the game won: a fanfare + the crowd roaring
    win: function(){
      var notes = [523, 659, 784, 1047];
      for (var i = 0; i < notes.length; i++) tone(notes[i], 0.18, 'triangle', 0.24, i * 0.14);
      burst(1.8, 1100, 0.14, 500, 0.3);
    },
  };
})();

// ---------- the court (field units) ----------
// The court runs NORTH-SOUTH: the hoop is at the top (north), you drive
// up the court from the bottom (south). The blacktop is tall, not wide.
var CW = 400, CH = 700;              // the blacktop (smaller, tighter)
var RIM_X = 200, RIM_Y = 52;         // the rim (centre), at the top
var RIM_R = 17;                      // the rim's radius
var RIM_Z = 122;                     // the rim's height off the ground
var BOARD_Y = 40;                    // the backboard face (just north of the rim)
var KEY_X0 = 125, KEY_X1 = 275, KEY_Y0 = 0, KEY_Y1 = 200; // the painted lane
var FT_Y = 200;                      // the free-throw line
var CLEAR_Y = 320;                   // take it past here (south) after a defensive rebound
var DUNK_R = 150;                    // how close to the rim a dunk starts from
var GRAV = 2200;                     // the ball's gravity
var HOME = 0, AWAY = 1;
var TEAM_COLOR = ['#d32f2f', '#1a1a2e'];   // you: red, COM: black
var TEAM_TRIM = ['#ffe14d', '#4fc3f7'];
var TEAM_SKIN = ['#c98d5f', '#8d5a3b'];
var TEAM_NAME = ['DANTE', 'CODY'];

// the 10 signature dunks. Each has a name for the banner and a style
// that changes how the arm and the ball move through the slam.
var DUNKS = [
  { n: 'THE WINDMILL!', s: 'windmill' },
  { n: 'THE 360!', s: 'spin' },
  { n: 'THE TOMAHAWK!', s: 'tomahawk' },
  { n: 'THE REVERSE!', s: 'reverse' },
  { n: 'THE POSTER!', s: 'poster' },
  { n: 'THE ALLEY-OOP!', s: 'oop' },
  { n: 'FROM THE FREE-THROW LINE!', s: 'long' },
  { n: 'THE DOUBLE PUMP!', s: 'pump' },
  { n: 'BETWEEN THE LEGS!', s: 'legs' },
  { n: 'ROCK THE CRADLE!', s: 'cradle' },
];

// the levels: COM's feet, his hands (steal/block), and his jumper.
// The ball's speed does not change here -- the jumper's arc is the same;
// the level changes how well COM defends and shoots.
// dunk: how often COM throws it down when he is in range (vs settling
// for a jumper, which he can miss). Rookie dunks rarely; Legend almost
// always.
var DIFFS = [
  { n: 'ROOKIE', cpu: 0.5, steal: 0.03, block: 0.02, shoot: 0.28, dunk: 0.35 },
  { n: 'AMATEUR', cpu: 0.86, steal: 0.18, block: 0.16, shoot: 0.65, dunk: 0.6 },
  { n: 'PRO', cpu: 1.0, steal: 0.25, block: 0.22, shoot: 0.72, dunk: 0.8 },
  { n: 'ALL-STAR', cpu: 1.12, steal: 0.32, block: 0.3, shoot: 0.78, dunk: 0.9 },
  { n: 'LEGEND', cpu: 1.24, steal: 0.4, block: 0.38, shoot: 0.84, dunk: 0.95 },
];
var diffIdx = 2; // PRO
var WIN_SCORE = 21;

// ---------- the game state ----------
var G = {
  started: false, over: false, phase: 'menu', // 'menu' | 'play' | 'dunk' | 'over'
  score: [0, 0],
  poss: HOME,                 // who has the ball (HOME = you)
  carrier: null,              // the player holding the ball
  ball: { x: 0, y: 0, z: 30, vx: 0, vy: 0, vz: 0, live: false, r: 13 },
  players: [],
  shotT: 0,                   // the shot meter (0..1) while a jumper is up
  noCatchT: 0,                // nobody can grab the ball this long after a shot
  shotBy: null,               // who shot the jumper that is in the air
  shotMake: false,            // whether that jumper will go in
  mustClear: false,           // the new offense must take it south past CLEAR_Y
  dunkT: 0, dunkBy: null, dunk: null, dunkScored: false,
  // (slow motion: the whole dunk plays at 0.4x -- see update())
  msgT: 0,
  myTeam: HOME, // PvC: you are always HOME (DANTE). PvP: HOME if host, AWAY if guest.
  pvp: null,    // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT}
  lastOffense: HOME,
};

/* ---------- PvP (park games) ---------- */
// Same room system as Baseball/Tennis PvP (backend: /api/park_pvp/rooms/*).
// 1-on-1 is real-time, so the sync is event-based: shots, dunks, steals,
// blocks, and loose-ball grabs are posted as they happen, and the
// opponent applies the same call, so the ball and the score match on
// both phones. Player positions are posted with the state and
// interpolated on the other side. Identity comes from the app as
// window.PARK_PVP_PLAYER = {id, name}.
var PVP_API = 'https://gta-quest-map.emergent.host/api/park_pvp/rooms';
var PVP_POLL_MS = 100;
function pvpPlayer(){
  try {
    var p = window.PARK_PVP_PLAYER || null;
    if (p && p.id) return { id: String(p.id), name: String(p.name || 'Player') };
  } catch (e) { /* no injected identity */ }
  return { id: 'local-player', name: 'YOU' };
}
function pvpPost(path, body){
  try {
    return fetch(PVP_API + path, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    }).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; });
  } catch (e) { return Promise.resolve(null); }
}
function pvpGet(code){
  try {
    return fetch(PVP_API + '/' + encodeURIComponent(code))
      .then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; });
  } catch (e) { return Promise.resolve(null); }
}
function pvpIsOn(){ return !!(G.pvp && G.pvp.code); }
function pvpMe(){ return G.players[G.myTeam]; }
function pvpOpp(){ return G.players[1 - G.myTeam]; }
function pvpPostState(patch){
  // Post the shared state to the room. The patch carries the new event
  // (shot / dunk / steal / block / grab / check). The full score,
  // possession, and my position ride along so the other phone resyncs
  // and sees where I am.
  if (!pvpIsOn()) return Promise.resolve(null);
  if (!patch && G.pvp.posting) return Promise.resolve(null);
  G.pvp.seq += 1;
  var me = pvpMe();
  var st = {
    seq: G.pvp.seq,
    score: G.score.slice(), poss: G.poss, mustClear: G.mustClear,
    phase: G.phase,
    me: { x: me ? me.x : 0, y: me ? me.y : 0, z: me ? me.z : 0, hasBall: !!(me && me.hasBall) },
    ev: null
  };
  if (patch && patch.ev) st.ev = patch.ev;
  var who = pvpPlayer();
  st.round = G.pvp.round || 0; st.rm = G.pvp.rmReq || 0;
  var pvw = G.pvp; pvw.posting = true; return pvpPost('/' + G.pvp.code + '/state', { player_id: who.id, state: st }).then(function(r){ pvw.posting = false; return r; });
}
function pvpStartPoll(){
  if (!G.pvp) return;
  if (G.pvp.pollTimer) clearInterval(G.pvp.pollTimer);
  G.pvp.pollTimer = setInterval(pvpPollOnce, PVP_POLL_MS);
}
function pvpStopPoll(){
  if (G.pvp && G.pvp.pollTimer){ clearInterval(G.pvp.pollTimer); G.pvp.pollTimer = null; }
}
function pvpPollOnce(){
  if (!pvpIsOn()) return;
  var code = G.pvp.code;
  if (G.pvp.polling) return; var pvq = G.pvp; pvq.polling = true;
  pvpGet(code).then(function(room){ pvq.polling = false;
    if (!room) return;
    if (room.status === 'finished'){
      pvpStopPoll();
      G.over = true; G.phase = 'over';
      var won = room.winner && room.winner === pvpPlayer().id;
      showMsg(won ? 'YOU WIN!' : 'YOU LOSE', 'The other player left the game.');
      document.getElementById('overlay').classList.remove('hidden');
      document.getElementById('startBtn').textContent = 'START GAME';
      return;
    }
    // Opponent joined — the game starts on its own now (like the house
    // games: the game starts when the second player enters the code).
    if (pvpWagerReady(room, G.pvp.round || 0) && G.pvp.role === 'host' && room.status === 'playing' && room.guest_name && !G.started){
      G.pvp.oppName = room.guest_name;
      var lbl = document.getElementById('pvpRoomLbl');
      if (lbl) lbl.textContent = 'CODE: ' + code + ' — vs ' + G.pvp.oppName;
      var st2 = document.getElementById('pvpStatus');
      if (st2) st2.textContent = 'They joined! Starting the game...';
      startGame();
    }
    // Read ONLY the opponent's own state slot (host reads states.guest,
    // guest reads states.host) with its own seq counter, so my echoed
    // posts never block theirs.
    var oppRole = G.pvp.role === 'host' ? 'guest' : 'host';
    var st = (room.states && room.states[oppRole]) || null;
    if (st && st.me && st.me.team === G.myTeam) st = null; st = pvpRematchCheck(room, st);
    // Newer seq -> apply. Much lower seq = opponent restarted (rejoin).
    if (st && typeof st.seq === 'number' && (st.seq > G.pvp.oppSeq || st.seq < G.pvp.oppSeq - 50)){
      G.pvp.oppSeq = st.seq;
      pvpApplyState(st);
    }
  });
}
function pvpApplyState(st){
  if (!st) return;
  // If I haven't started yet (fresh join, or rejoin after getting
  // booted out), start the game first, then resync everything from
  // the room state. A rejoining host does NOT post a fresh initial
  // state (that would reset the room).
  var fresh = pvpIsOn() && !G.started;
  if (fresh){
    if (G.pvp.role === 'host') G.pvp.syncStart = true;
    startGame();
    if (G.pvp) G.pvp.syncStart = false;
  }
  // Score only goes up during a game: keep the higher value per side so
  // a late/stale post from the other phone can never reset it.
  if (Array.isArray(st.score)){ for (var si = 0; si < st.score.length; si++){ if (typeof st.score[si] === 'number' && st.score[si] > (G.score[si] || 0)) G.score[si] = st.score[si]; } }
  if (typeof st.poss === 'number') G.poss = st.poss;
  if (typeof st.mustClear === 'boolean') G.mustClear = st.mustClear;
  updateSB();
  if (fresh) return; // skip events on the first state I apply
  // Opponent position: glide toward it (no teleporting).
  if (st.me && typeof st.me.x === 'number' && typeof st.me.y === 'number'){
    var op = pvpOpp();
    if (op){ op.tx = st.me.x; op.ty = st.me.y; }
  }
  if (st.ev) pvpReceiveEv(st.ev);
}
function pvpReceiveEv(ev){
  // Apply one event posted by the opponent. Only events from the OTHER
  // team are applied (my own events are already applied locally).
  if (!ev || typeof ev.team !== 'number' || ev.team === G.myTeam) return;
  var p = G.players[ev.team];
  if (!p) return;
  if (ev.k === 'shot'){
    // They shot a jumper: same make/miss, same jump. The release happens
    // in update() at the peak, on both phones.
    G.shotMake = !!ev.make;
    G.shotBy = p;
    p.jumpT = 0.55; p.z = 0; p.vz = 0; p.released = false;
    SFX.shoot();
  } else if (ev.k === 'dunk'){
    // They dunked: same signature dunk, same slow-motion flight.
    G.dunk = DUNKS[ev.dunk] || DUNKS[0];
    G.dunkBy = p;
    G.dunkT = 0.9;
    p.dunkT = 0.9;
    p.hasBall = true;
    G.phase = 'dunk';
    showDunkBanner(G.dunk.n);
    SFX.dunk();
  } else if (ev.k === 'steal'){
    // They picked my pocket: the ball is theirs now.
    var old = G.carrier;
    if (old){ old.hasBall = false; }
    G.carrier = p; p.hasBall = true;
    G.poss = p.team;
    G.mustClear = true;
    G.ball.live = false;
    G.ball.x = p.x; G.ball.y = p.y; G.ball.z = 30;
    SFX.steal();
    showMsg((p.team === HOME ? 'YOU' : 'COM') + ' PICKED HIS POCKET!');
    updateSB();
  } else if (ev.k === 'block'){
    // They jumped to block: same jump, arms high.
    p.jumpT = 0.5; p.blockT = 0.5;
    SFX.shoot();
  } else if (ev.k === 'grab'){
    // They grabbed a loose ball: it is theirs now.
    var prev = G.carrier;
    if (prev){ prev.hasBall = false; }
    p.hasBall = true; G.carrier = p; G.poss = p.team;
    if (G.poss !== G.lastOffense) G.mustClear = true;
    G.ball.live = false; G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0;
    updateSB();
  } else if (ev.k === 'check'){
    // They scored and the other side takes it out.
    checkBall(ev.poss);
  }
}

function makePlayers(){
  G.players = [];
  G.players.push({
    team: HOME, role: 'YOU', name: 'DANTE',
    x: 400, y: 250, z: 0, vz: 0, vx: 0, vy: 0,
    speed: 265, face: 1, runT: 0, moving: false, kickT: 0,
    hasBall: false, jumpT: 0, stealCd: 0, blockT: 0, dunkT: 0,
    turbo: false, stam: 100,
  });
  G.players.push({
    team: AWAY, role: 'COM', name: 'CODY',
    x: 700, y: 250, z: 0, vz: 0, vx: 0, vy: 0,
    speed: 265 * DIFFS[diffIdx].cpu, face: -1, runT: 0, moving: false, kickT: 0,
    hasBall: false, jumpT: 0, stealCd: 0, blockT: 0, dunkT: 0,
    turbo: false, stam: 100,
  });
}
makePlayers();

function carrierPlayer(){ return G.carrier; }
function otherPlayer(p){ return G.players[1 - p.team]; }
function distToRim(p){ return Math.hypot(RIM_X - p.x, RIM_Y - p.y); }
function clampCourt(p){
  p.x = Math.max(30, Math.min(CW - 20, p.x));
  p.y = Math.max(30, Math.min(CH - 20, p.y));
}

// ---------- the canvas ----------
var cv = document.getElementById('cv');
var ctx = cv.getContext('2d');
var W = 0, H = 0, dpr = 1;
function fitCanvas(){
  var r = cv.parentElement.getBoundingClientRect();
  dpr = (typeof window !== 'undefined' && window.devicePixelRatio) || 1;
  W = Math.max(320, r.width); H = Math.max(320, r.height);
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
if (typeof window !== 'undefined' && window.addEventListener){
  window.addEventListener('resize', fitCanvas);
}
fitCanvas();

// the camera: it follows the ball and zooms in, so the players read big
// and a dunk fills the screen. The backdrop stays fixed; the court, the
// hoop, the players and the ball pan/zoom with it.
var cam = { x: 200, y: 560, zoom: 1.6 };
function baseScale(){ return Math.min((W - 30) / (CW + 90), (H - 110) / (CH + 120)); }
function effScale(){ return baseScale() * cam.zoom; }
function courtScale(){ return effScale(); }
function courtSX(x){ return W / 2 + (x - cam.x) * effScale(); }
function courtSY(y){ return (H + 56) / 2 + (y - cam.y) * effScale(); }
function updateCamera(dt){
  // Follow the action -- but when the ball is in the air (a shot) or a
  // dunk is on, point the camera AT THE RIM and snap to it fast, so the
  // player watches the ball go through instead of staring at the floor
  // while the rim sits off the top of the screen. The old camera lagged
  // the ball and the clamp stopped it 300 units south of the rim, so the
  // rim was off-screen for the first half of every shot.
  var tx = G.ball.x, ty = G.ball.y, tz = 1.6;
  var fast = false;
  if (G.phase === 'dunk' && G.dunkBy){ tx = RIM_X; ty = RIM_Y; tz = 2.2; fast = true; }
  else if (G.ball.live){ tx = RIM_X; ty = RIM_Y; fast = true; }
  else if (G.carrier){ tx = G.carrier.x; ty = G.carrier.y; }
  // the camera may centre anywhere on the court (the old clamp kept the
  // view inside the blacktop, which stopped it short of the rim)
  tx = Math.max(0, Math.min(CW, tx));
  ty = Math.max(0, Math.min(CH, ty));
  var k = Math.min(1, dt * (fast ? 12 : 4));
  cam.x += (tx - cam.x) * k;
  cam.y += (ty - cam.y) * k;
  cam.zoom += (tz - cam.zoom) * Math.min(1, dt * 3);
}

function shade(x, y, r, c1, c2){
  var g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
  g.addColorStop(0, c1); g.addColorStop(1, c2);
  ctx.fillStyle = g;
}
function lighten(hex){
  var n = parseInt(hex.slice(1), 16);
  var r = Math.min(255, ((n >> 16) & 255) + 60), g = Math.min(255, ((n >> 8) & 255) + 60), b = Math.min(255, (n & 255) + 60);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}
function darken(hex){
  var n = parseInt(hex.slice(1), 16);
  var r = Math.max(0, ((n >> 16) & 255) - 60), g = Math.max(0, ((n >> 8) & 255) - 60), b = Math.max(0, (n & 255) - 60);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}

// ---------- the playground ----------
var CROWD = [];
(function(){
  // the crowd along the fence: fixed seats, random shirts
  var shirts = ['#e53935', '#1e88e5', '#fdd835', '#43a047', '#fb8c00', '#8e24aa', '#00acc1', '#f5f5f5'];
  for (var i = 0; i < 26; i++){
    CROWD.push({ x: 40 + i * 33 + (Math.random() * 10 - 5), y: 8 + (Math.random() * 6), c: shirts[i % shirts.length], h: 26 + Math.random() * 10 });
  }
})();
function drawPlayground(){
  var sc = courtScale();
  var x0 = courtSX(0), x1 = courtSX(CW), y0 = courtSY(0), y1 = courtSY(CH);
  // the sky (fixed in screen space, down to the wall)
  var sky = ctx.createLinearGradient(0, 0, 0, 92);
  sky.addColorStop(0, '#7ec8f7'); sky.addColorStop(1, '#cfeeff');
  ctx.fillStyle = sky; ctx.fillRect(0, 0, W, 96);
  // the sun + a cloud
  shade(W - 90, 42, 26, '#fffde7', '#ffeb3b');
  ctx.beginPath(); ctx.arc(W - 90, 42, 26, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,0.9)';
  ctx.beginPath(); ctx.ellipse(120, 30, 46, 14, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(150, 36, 34, 11, 0, 0, Math.PI * 2); ctx.fill();
  // the brick wall behind the court (fixed in screen space)
  var wallY = 62;
  ctx.fillStyle = '#9c4a2f';
  ctx.fillRect(0, wallY, W, 30);
  ctx.strokeStyle = 'rgba(0,0,0,0.25)'; ctx.lineWidth = 1;
  for (var by = wallY; by < wallY + 30; by += 7){
    ctx.beginPath(); ctx.moveTo(0, by); ctx.lineTo(W, by); ctx.stroke();
  }
  for (var bx = 8; bx < W; bx += 22){
    ctx.beginPath(); ctx.moveTo(bx, wallY); ctx.lineTo(bx, wallY + 30); ctx.stroke();
  }
  // the crowd on the wall (heads + shoulders, bobbing a little)
  for (var i = 0; i < CROWD.length; i++){
    var c = CROWD[i];
    var bob = Math.sin((G.msgT + i) * 2) * 1.5;
    ctx.fillStyle = c.c;
    ctx.beginPath(); ctx.arc(c.x, wallY - 4 + bob, 7, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = darken(c.c);
    ctx.fillRect(c.x - 8, wallY + 2 + bob, 16, 8);
    ctx.fillStyle = '#c98d5f';
    ctx.beginPath(); ctx.arc(c.x, wallY - 5 + bob, 5, 0, Math.PI * 2); ctx.fill();
  }
  // the ground around the court (packed dirt)
  ctx.fillStyle = '#8d6e4a';
  ctx.fillRect(0, 92, W, H - 92);
  // the blacktop
  ctx.fillStyle = '#3a3f4a';
  ctx.fillRect(x0 - 14 * sc, y0 - 10 * sc, (x1 - x0) + 28 * sc, (y1 - y0) + 20 * sc);
  // asphalt speckle
  ctx.fillStyle = 'rgba(255,255,255,0.05)';
  for (var s = 0; s < 120; s++){
    var sx = x0 + Math.random() * (x1 - x0), sy = y0 + Math.random() * (y1 - y0);
    ctx.fillRect(sx, sy, 2, 2);
  }
  // the painted key (the lane) -- shaded blue like the screenshots.
  // It is a vertical rectangle at the top (north), under the rim.
  ctx.fillStyle = '#3d6fb4';
  ctx.fillRect(courtSX(KEY_X0), courtSY(KEY_Y0), (KEY_X1 - KEY_X0) * sc, (KEY_Y1 - KEY_Y0) * sc);
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 2;
  ctx.strokeRect(courtSX(KEY_X0), courtSY(KEY_Y0), (KEY_X1 - KEY_X0) * sc, (KEY_Y1 - KEY_Y0) * sc);
  // the free-throw line (the end of the key) + the free-throw circle
  // (a full circle centred on the line, like a real court)
  ctx.beginPath(); ctx.moveTo(courtSX(KEY_X0), courtSY(FT_Y)); ctx.lineTo(courtSX(KEY_X1), courtSY(FT_Y)); ctx.stroke();
  ctx.beginPath(); ctx.arc(courtSX(RIM_X), courtSY(FT_Y), (KEY_X1 - KEY_X0) / 2 * sc, 0, Math.PI * 2); ctx.stroke();
  // the restricted-area arc (the little semicircle under the basket)
  ctx.beginPath(); ctx.arc(courtSX(RIM_X), courtSY(RIM_Y), 34 * sc, 0, Math.PI); ctx.stroke();
  // the 3-point line, like a real court: straight from each corner, then
  // a big arc over the top, reaching the sidelines (the old arc floated
  // in the middle of the court and never touched them).
  var tp = 200; // the 3-point radius from the rim
  var cornerY = 150; // where the straight corner sections meet the arc
  var cornerDX = Math.sqrt(tp * tp - (cornerY - RIM_Y) * (cornerY - RIM_Y));
  var lx = RIM_X - cornerDX, rx3 = RIM_X + cornerDX;
  var aL = Math.atan2(cornerY - RIM_Y, lx - RIM_X);
  var aR = Math.atan2(cornerY - RIM_Y, rx3 - RIM_X);
  ctx.beginPath();
  ctx.moveTo(courtSX(lx), courtSY(0));
  ctx.lineTo(courtSX(lx), courtSY(cornerY));
  ctx.arc(courtSX(RIM_X), courtSY(RIM_Y), tp * sc, aL, aR, true);
  ctx.lineTo(courtSX(rx3), courtSY(0));
  ctx.stroke();
  // the half-court line (the far end of a half-court) + the centre
  // half-circle on it, like the middle of a full court. (The old full
  // circle in the middle of the court was not a basketball line.)
  ctx.beginPath(); ctx.moveTo(x0, courtSY(CH - 8)); ctx.lineTo(x1, courtSY(CH - 8)); ctx.stroke();
  ctx.beginPath(); ctx.arc(courtSX(RIM_X), courtSY(CH - 8), 46 * sc, Math.PI, 0); ctx.stroke();
  // the boundary
  ctx.lineWidth = 3;
  ctx.strokeRect(x0, y0, x1 - x0, y1 - y0);
  // the clear line (after a defensive rebound, take it south past here)
  if (G.mustClear){
    ctx.strokeStyle = '#ffe14d'; ctx.setLineDash([8, 6]); ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(x0, courtSY(CLEAR_Y)); ctx.lineTo(x1, courtSY(CLEAR_Y)); ctx.stroke();
    ctx.setLineDash([]);
  }
  // the chain-link fence (bottom edge)
  ctx.strokeStyle = 'rgba(200,200,200,0.5)'; ctx.lineWidth = 1;
  for (var fx = 0; fx < W; fx += 14){
    ctx.beginPath(); ctx.moveTo(fx, H - 26); ctx.lineTo(fx + 14, H - 8); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(fx + 14, H - 26); ctx.lineTo(fx, H - 8); ctx.stroke();
  }
  ctx.fillStyle = '#555';
  ctx.fillRect(0, H - 28, W, 4);
}

// ---------- the hoop ----------
function drawHoop(){
  var sc = courtScale();
  var rx = courtSX(RIM_X), ry = courtSY(RIM_Y);
  var rimY = ry - RIM_Z * sc; // the rim floats above the court (height)
  // the pole (up, north, from the backboard) + the backboard (a horizontal
  // rectangle at the top, behind the rim)
  ctx.strokeStyle = '#555'; ctx.lineWidth = Math.max(4, 7 * sc);
  ctx.beginPath(); ctx.moveTo(rx, rimY - 34 * sc); ctx.lineTo(rx, rimY - 62 * sc); ctx.stroke();
  ctx.fillStyle = '#f5f5f5';
  ctx.fillRect(rx - 26 * sc, rimY - 34 * sc, 52 * sc, 10 * sc);
  ctx.strokeStyle = '#c62828'; ctx.lineWidth = 2;
  ctx.strokeRect(rx - 26 * sc, rimY - 34 * sc, 52 * sc, 10 * sc);
  ctx.strokeRect(rx - 8 * sc, rimY - 34 * sc, 16 * sc, 10 * sc);
  // the rim (an orange ring). The net is drawn after the ball (see
  // drawNet) so a dunked or swished ball drops THROUGH it.
  ctx.strokeStyle = '#ef6c00'; ctx.lineWidth = Math.max(3, 4 * sc);
  ctx.beginPath(); ctx.ellipse(rx, rimY, RIM_R * sc, RIM_R * 0.45 * sc, 0, 0, Math.PI * 2); ctx.stroke();
}
// the net (white, hanging under the rim). Drawn AFTER the ball so the
// ball appears to drop through it, not sit on top of it.
function drawNet(){
  var sc = courtScale();
  var rx = courtSX(RIM_X), ry = courtSY(RIM_Y);
  var rimY = ry - RIM_Z * sc;
  ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 1;
  for (var n = -2; n <= 2; n++){
    ctx.beginPath(); ctx.moveTo(rx + n * 6 * sc, rimY + 2 * sc); ctx.lineTo(rx + n * 3.5 * sc, rimY + 16 * sc); ctx.stroke();
  }
  ctx.beginPath(); ctx.moveTo(rx - 12 * sc, rimY + 16 * sc); ctx.lineTo(rx + 12 * sc, rimY + 16 * sc); ctx.stroke();
}

// ---------- the players (side-view, real arms and legs) ----------
function drawPlayer(p){
  var sc = courtScale();
  var sx = courtSX(p.x), gy = courtSY(p.y);
  var s = 42 * sc + 16; // the figure's height on screen (big, so he reads)
  var fx = p.face;
  var run = p.moving ? Math.sin(p.runT) : 0;
  var lean = p.moving ? 6 * fx : 0;
  // the jump: z lifts the whole figure (the shadow stays on the ground)
  var jumpZ = p.z * sc;
  var sy = gy - jumpZ;
  // the drop shadow (shrinks and fades as he rises)
  var shScale = Math.max(0.45, 1 - p.z / 260);
  ctx.fillStyle = 'rgba(0,0,0,' + (0.35 * shScale).toFixed(2) + ')';
  ctx.beginPath(); ctx.ellipse(sx, gy + s * 0.52, s * 0.34 * shScale, s * 0.12 * shScale, 0, 0, Math.PI * 2); ctx.fill();
  ctx.lineCap = 'round';
  // the LEGS (a real running stride: one well forward, one trailing back,
  // feet lifting clear of the ground, white high-tops)
  var fwd = run * s * 0.48, back = -run * s * 0.48;
  var fLift = p.moving ? Math.max(0, -Math.cos(p.runT)) * s * 0.18 : 0;
  var bLift = p.moving ? Math.max(0, Math.cos(p.runT)) * s * 0.18 : 0;
  // when he jumps, the legs tuck (knees up)
  var tuck = (p.z > 4) ? 0.5 : 1;
  ctx.strokeStyle = '#222'; ctx.lineWidth = Math.max(3, s * 0.1);
  ctx.beginPath(); ctx.moveTo(sx, sy + s * 0.2); ctx.lineTo(sx + fwd * tuck, sy + s * 0.52 - fLift - (p.z > 4 ? s * 0.14 : 0)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(sx, sy + s * 0.2); ctx.lineTo(sx + back * tuck, sy + s * 0.52 - bLift - (p.z > 4 ? s * 0.08 : 0)); ctx.stroke();
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.ellipse(sx + fwd * tuck, sy + s * 0.52 - fLift - (p.z > 4 ? s * 0.14 : 0), s * 0.12, s * 0.08, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(sx + back * tuck, sy + s * 0.52 - bLift - (p.z > 4 ? s * 0.08 : 0), s * 0.12, s * 0.08, 0, 0, Math.PI * 2); ctx.fill();
  // the body (a tall narrow jersey, leaning into the run)
  var col = TEAM_COLOR[p.team];
  shade(sx + lean, sy, s * 0.32, lighten(col), darken(col));
  ctx.beginPath(); ctx.ellipse(sx + lean, sy, s * 0.22, s * 0.3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = TEAM_TRIM[p.team]; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.ellipse(sx + lean, sy, s * 0.22, s * 0.3, 0, 0, Math.PI * 2); ctx.stroke();
  // the head (shaded, with a headband)
  shade(sx + lean * 1.5, sy - s * 0.42, s * 0.18, lighten(TEAM_SKIN[p.team]), darken(TEAM_SKIN[p.team]));
  ctx.beginPath(); ctx.arc(sx + lean * 1.5, sy - s * 0.42, s * 0.18, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = TEAM_TRIM[p.team];
  ctx.fillRect(sx + lean * 1.5 - s * 0.18, sy - s * 0.5, s * 0.36, s * 0.07);
  // the ARMS -- one dribbles / shoots, the other pumps opposite the legs.
  // The arm positions depend on what he is doing (set by drawArms).
  drawArms(p, sx, sy, s, fx, lean, run, col);
  // the P1 ring (you)
  if (p.team === HOME){
    ctx.strokeStyle = '#ffe14d'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(sx, gy + s * 0.52, s * 0.36, s * 0.13, 0, 0, Math.PI * 2); ctx.stroke();
  }
}

// The arms. Three poses:
//  - dribble: the front arm bounces the ball at his side, the back arm pumps.
//  - shoot: both arms go up together (the shot release).
//  - dunk: one arm (or two) extends straight up with the ball, the other
//    pumps or tucks, and the style (windmill / spin / tomahawk...) bends it.
function drawArms(p, sx, sy, s, fx, lean, run, col){
  var armPump = p.moving ? -run * s * 0.3 : 0;
  var armLift = p.moving ? Math.max(0, Math.cos(p.runT)) * s * 0.12 : 0;
  ctx.strokeStyle = col; ctx.lineWidth = Math.max(3, s * 0.08);
  // the BACK arm (no ball): it pumps opposite the legs while he runs,
  // and hangs at his side when he stands.
  var ax0 = sx + lean - fx * s * 0.14, ay0 = sy - s * 0.14;
  var ax1 = sx + lean - fx * s * 0.14 + armPump, ay1 = sy + s * 0.14 - armLift;
  // during a dunk the back arm tucks (or, for a tomahawk, joins the front)
  if (p.dunkT > 0 && G.dunk && G.dunk.s === 'tomahawk'){
    ax1 = sx + lean + fx * s * 0.3; ay1 = sy - s * 0.75; // two hands on the ball
  } else if (p.z > 4){
    ax1 = sx + lean - fx * s * 0.2; ay1 = sy + s * 0.05; // tucked while airborne
  }
  ctx.beginPath(); ctx.moveTo(ax0, ay0); ctx.lineTo(ax1, ay1); ctx.stroke();
  ctx.fillStyle = TEAM_SKIN[p.team];
  ctx.beginPath(); ctx.arc(ax1, ay1, s * 0.07, 0, Math.PI * 2); ctx.fill();
  // the FRONT arm (the ball hand)
  var hx0 = sx + lean + fx * s * 0.14, hy0 = sy - s * 0.14;
  var hx1, hy1;
  if (p.dunkT > 0 && G.dunk){
    // the dunk: a REAL arm, two segments (shoulder -> elbow -> hand),
    // so the elbow bends and the arm visibly moves through the slam.
    // Each of the 10 dunks has its own hand path and elbow bend.
    var dp = 1 - p.dunkT / 0.9; // 0 -> 1 over the dunk
    var up = s * 0.85;
    var bend = 0.2; // elbow bend: 0 = straight, 1 = fully cocked
    if (G.dunk.s === 'windmill'){
      // the full circle: the arm sweeps a big loop, cocked low, extended high
      var wa = dp * Math.PI * 2;
      hx1 = sx + lean + Math.cos(wa) * s * 0.45;
      hy1 = sy - s * 0.35 - Math.abs(Math.sin(wa)) * s * 0.55;
      bend = 0.35 + 0.3 * Math.cos(wa);
    } else if (G.dunk.s === 'spin'){
      // the 360: the arm stays high and sweeps around with the spin
      hx1 = sx + lean + fx * s * 0.35 + Math.sin(dp * Math.PI * 2) * s * 0.2;
      hy1 = sy - s * 0.3 - up * Math.min(1, dp * 1.4);
      bend = 0.2;
    } else if (G.dunk.s === 'tomahawk'){
      // the tomahawk: cocked behind the head, then a hard chop down
      var th = dp < 0.4 ? dp / 0.4 : 1 - (dp - 0.4) / 0.6;
      hx1 = sx + lean - fx * s * 0.2 + fx * s * 0.55 * th;
      hy1 = sy - s * 0.3 - up * (0.3 + 0.7 * th);
      bend = 0.6 - 0.45 * th; // bent while cocked, straight at the chop
    } else if (G.dunk.s === 'reverse'){
      // the reverse: up behind the back, over the head backwards
      hx1 = sx + lean - fx * s * 0.35;
      hy1 = sy - s * 0.3 - up * Math.min(1, dp * 1.4);
      bend = 0.3;
    } else if (G.dunk.s === 'poster'){
      // the poster: straight up, stiff, right through the defender
      hx1 = sx + lean + fx * s * 0.3;
      hy1 = sy - s * 0.3 - up * Math.min(1, dp * 1.4);
      bend = 0.05;
    } else if (G.dunk.s === 'oop'){
      // the alley-oop: reach up high to catch it, then slam it down
      hx1 = sx + lean + fx * s * 0.3;
      hy1 = sy - s * 0.3 - up * (dp < 0.5 ? 0.9 : 1.0);
      bend = 0.15;
    } else if (G.dunk.s === 'long'){
      // from the free-throw line: a long glide, arm reaching forward and up
      hx1 = sx + lean + fx * s * 0.55;
      hy1 = sy - s * 0.3 - up * Math.min(1, dp * 1.2);
      bend = 0.25;
    } else if (G.dunk.s === 'pump'){
      // the double pump: down to the waist, up, down, up -- two pumps
      var pu2 = 0.5 + 0.5 * Math.sin(dp * Math.PI * 2);
      hx1 = sx + lean + fx * s * 0.3;
      hy1 = sy - s * 0.3 - up * pu2;
      bend = 0.5 - 0.3 * pu2; // bent at the bottom of each pump
    } else if (G.dunk.s === 'legs'){
      // between the legs: down low between the knees, then up high
      var lg = dp < 0.4 ? dp / 0.4 : 1;
      var lowY = sy + s * 0.2, highY = sy - s * 0.3 - up;
      hx1 = sx + lean + fx * s * 0.1;
      hy1 = lowY + (highY - lowY) * lg;
      bend = 0.6 - 0.4 * lg;
    } else if (G.dunk.s === 'cradle'){
      // rock the cradle: the ball rocks side to side, elbow bent
      hx1 = sx + lean + fx * s * 0.3 + Math.sin(dp * Math.PI * 2) * s * 0.3;
      hy1 = sy - s * 0.3 - up * (0.5 + 0.5 * Math.sin(dp * Math.PI));
      bend = 0.5;
    } else {
      hx1 = sx + lean + fx * s * 0.3;
      hy1 = sy - s * 0.3 - up * Math.min(1, dp * 1.4);
      bend = 0.2;
    }
    // the hand finishes AT the rim: blend the style's hand path to the
    // rim's screen position as the dunk closes (dp -> 1), so the ball
    // goes through the net instead of hovering south of the rim.
    var rimSX = courtSX(RIM_X), rimSY = courtSY(RIM_Y) - RIM_Z * courtScale();
    var toRim = dp * dp;
    hx1 = hx1 * (1 - toRim) + rimSX * toRim;
    hy1 = hy1 * (1 - toRim) + rimSY * toRim;
    // the elbow: bend the arm (two segments) so it reads as a real arm,
    // not a stick. The elbow pushes out from the shoulder->hand line.
    var ex = (hx0 + hx1) / 2 - fx * s * 0.22 * bend - (hy1 - hy0) * 0.12 * bend;
    var ey = (hy0 + hy1) / 2 + s * 0.18 * bend;
    ctx.beginPath(); ctx.moveTo(hx0, hy0); ctx.lineTo(ex, ey); ctx.lineTo(hx1, hy1); ctx.stroke();
    ctx.fillStyle = TEAM_SKIN[p.team];
    ctx.beginPath(); ctx.arc(hx1, hy1, s * 0.07, 0, Math.PI * 2); ctx.fill();
    // the ball rides in the dunk hand (drawn by drawBall at the hand)
    p.dunkHand = { x: hx1, y: hy1 };
  } else if (p.jumpT > 0){
    // the jump shot: both arms up, the ball released at the peak
    hx1 = sx + lean + fx * s * 0.28;
    hy1 = sy - s * 0.75;
  } else if (p.hasBall){
    // the dribble: the front arm bounces the ball at his side
    var db = Math.abs(Math.sin(G.dribbleT || 0)) * s * 0.18;
    hx1 = sx + lean + fx * s * 0.3;
    hy1 = sy + s * 0.28 - db;
  } else {
    // running / standing: the front arm pumps with the run
    hx1 = sx + lean + fx * s * 0.14 - armPump;
    hy1 = sy + s * 0.14 - armLift;
  }
  if (!(p.dunkT > 0 && G.dunk)){
    // (the dunk branch already drew its own two-segment arm above)
    ctx.beginPath(); ctx.moveTo(hx0, hy0); ctx.lineTo(hx1, hy1); ctx.stroke();
    ctx.fillStyle = TEAM_SKIN[p.team];
    ctx.beginPath(); ctx.arc(hx1, hy1, s * 0.07, 0, Math.PI * 2); ctx.fill();
  }
}

// ---------- the ball ----------
function drawBall(){
  var b = G.ball;
  var sc = courtScale();
  var bx, by;
  if (b.live === false && G.carrier){
    // carried: it rides in the ball hand (or bounces at his side)
    var cp = G.carrier;
    var csx = courtSX(cp.x), csy = courtSY(cp.y) - cp.z * sc;
    var s = 30 * sc + 14;
    if (cp.dunkT > 0 && cp.dunkHand){
      bx = cp.dunkHand.x; by = cp.dunkHand.y;
    } else {
      var db = Math.abs(Math.sin(G.dribbleT || 0));
      bx = csx + cp.face * s * 0.3;
      by = csy + s * 0.5 - db * s * 0.45;
    }
  } else {
    bx = courtSX(b.x);
    by = courtSY(b.y) - b.z * sc;
  }
  // the shadow on the ground (shrinks as the ball rises)
  var gz = (b.live === false && G.carrier) ? G.carrier.z : b.z;
  var shScale = Math.max(0.4, 1 - gz / 300);
  ctx.fillStyle = 'rgba(0,0,0,' + (0.3 * shScale).toFixed(2) + ')';
  ctx.beginPath(); ctx.ellipse(courtSX(b.x), courtSY(b.y) + 8 * sc, b.r * sc * shScale, b.r * 0.45 * sc * shScale, 0, 0, Math.PI * 2); ctx.fill();
  // the ball (shaded orange, with seams)
  shade(bx, by, b.r * sc, '#ffb74d', '#e65100');
  ctx.beginPath(); ctx.arc(bx, by, b.r * sc, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#4e342e'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.moveTo(bx - b.r * sc, by); ctx.lineTo(bx + b.r * sc, by); ctx.stroke();
  ctx.beginPath(); ctx.arc(bx, by, b.r * sc * 0.55, -0.6, 0.6); ctx.stroke();
  ctx.beginPath(); ctx.arc(bx, by, b.r * sc * 0.55, Math.PI - 0.6, Math.PI + 0.6); ctx.stroke();
}

// ---------- messages + the scoreboard ----------
var msgEl = document.getElementById('msg');
var msgTimer = null;
function showMsg(t, dur){
  msgEl.textContent = t;
  msgEl.style.opacity = '1';
  if (msgTimer) clearTimeout(msgTimer);
  msgTimer = setTimeout(function(){ msgEl.style.opacity = '0'; }, (dur || 1.6) * 1000);
}
function updateSB(){
  document.getElementById('scYou').textContent = G.score[HOME];
  document.getElementById('scCom').textContent = G.score[AWAY];
  document.getElementById('cardName').textContent = G.poss === HOME ? 'DANTE' : 'CODY';
  document.getElementById('cardSub').textContent = G.poss === HOME ? 'YOU HAVE IT' : 'COM HAS IT';
  document.getElementById('setPill').textContent = 'FIRST TO ' + WIN_SCORE + ' • ' + G.score[HOME] + '-' + G.score[AWAY];
  // the buttons flip with possession:
  // offense: SHOOT on the main button, DUNK on its own button above it
  // defense: BLOCK on the main button, STEAL on the second button,
  // and DUNK is dimmed (you cannot dunk on defense)
  var me = G.players[HOME];
  document.getElementById('btnA').textContent = (G.poss === HOME) ? 'SHOOT' : 'BLOCK';
  var bBtn = document.getElementById('btnB');
  bBtn.textContent = 'STEAL';
  bBtn.style.opacity = (G.poss === HOME) ? '0.35' : '1';
  var dBtn = document.getElementById('btnD');
  dBtn.textContent = 'DUNK';
  dBtn.style.opacity = (G.poss === HOME) ? '1' : '0.35';
}
function showDunkBanner(name){
  var b = document.getElementById('dunkBanner');
  b.textContent = name;
  b.classList.add('show');
  setTimeout(function(){ b.classList.remove('show'); }, 2500); // stays up for the whole slow dunk
}

// ---------- the check ball (start a possession) ----------
function checkBall(poss){
  G.poss = poss;
  G.noCatchT = 0; // a fresh possession: the ball is live to grab again
  G.mustClear = false;
  G.shotBy = null; G.shotT = 0; G.shotMake = false;
  G.dunkT = 0; G.dunkBy = null; G.dunk = null; G.dunkScored = false;
  var off = G.players[poss], def = G.players[1 - poss];
  off.x = 200; off.y = 560; off.z = 0; off.vz = 0; off.face = 1;
  def.x = 200; def.y = 420; def.z = 0; def.vz = 0; def.face = -1;
  G.players.forEach(function(p){ p.hasBall = false; p.jumpT = 0; p.dunkT = 0; p.stealCd = 0; p.blockT = 0; p.turbo = false; });
  off.hasBall = true; G.carrier = off;
  G.ball.live = false;
  G.ball.x = off.x; G.ball.y = off.y; G.ball.z = 30;
  G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0;
  G.phase = 'play';
  updateSB();
}

// ---------- shooting (a jumper) ----------
function shootBall(p){
  if (!G.started || G.over || G.phase !== 'play') return;
  if (G.carrier !== p) return;
  if (p.z > 0 || p.jumpT > 0 || p.dunkT > 0) return; // already in the air
  if (G.mustClear && G.poss === p.team){
    showMsg('CLEAR IT FIRST -- take it past the yellow line');
    return;
  }
  // the make chance: closer is better, a contest hurts, the level helps COM
  var d = distToRim(p);
  var def = otherPlayer(p);
  var defD = Math.hypot(def.x - p.x, def.y - p.y);
  var contested = defD < 55;
  var base = (d < 120) ? 0.82 : (d < 240) ? 0.68 : (d < 380) ? 0.52 : 0.38;
  if (contested) base -= 0.18;
  if (p.team === AWAY) base = DIFFS[diffIdx].shoot * (base / 0.68); // COM shoots at his level
  base = Math.max(0.08, Math.min(0.92, base));
  G.shotMake = Math.random() < base;
  G.shotBy = p;
  p.jumpT = 0.55; // the jump shot (0.55s: rise, release, land)
  p.z = 0; p.vz = 0;
  SFX.shoot();
  // PvP: I shot — tell the other phone whether it goes in, so their
  // ball flies the same way. The release happens at the peak, on both.
  if (pvpIsOn() && p.team === G.myTeam){
    pvpPostState({ ev: { k: 'shot', team: p.team, make: G.shotMake } });
  }
  // the ball leaves his hands at the peak of the jump (handled in update)
}
function releaseShot(p){
  // the ball is released at the top of the jump, arcing at the rim.
  // The flight time T is the time to reach the RIM (at rim height), not
  // the ground: the ball arrives at the rim's (x,y) at z=RIM_Z, then
  // drops through the net. (Aiming at the rim with a ground-time T made
  // the ball pass under the rim while at rim height, so it never scored.)
  var tx = RIM_X + (Math.random() * 10 - 5);
  var ty = RIM_Y + 6 + (Math.random() * 10 - 5);
  if (!G.shotMake){
    // a miss: off the rim (wide east/west, or long off the board to the
    // north), never a swish. Every miss target is outside the rim (r 17).
    var miss = Math.random();
    if (miss < 0.35){ tx = RIM_X - 36; ty = RIM_Y + 10 + (Math.random() * 30 - 15); }
    else if (miss < 0.7){ tx = RIM_X + 36; ty = RIM_Y + 10 + (Math.random() * 30 - 15); }
    else { tx = RIM_X + (Math.random() * 20 - 10); ty = RIM_Y - 22; }
  }
  var T = 0.7; // time to reach the rim
  var dx = tx - p.x, dy = ty - p.y;
  var hz = 70; // released from up high
  G.ball.x = p.x; G.ball.y = p.y; G.ball.z = hz;
  G.ball.vx = dx / T; G.ball.vy = dy / T;
  // arrive at rim height (RIM_Z) at time T, then drop through
  G.ball.vz = (RIM_Z - hz) / T + 0.5 * GRAV * T;
  G.ball.live = true;
  G.noCatchT = 0.4; // the shooter cannot instantly re-catch his own shot
  G.carrier = null; p.hasBall = false;
}

// ---------- dunking (one of the 10 signature dunks) ----------
function tryDunk(p){
  if (!G.started || G.over || G.phase !== 'play') return;
  if (G.carrier !== p) return;
  if (p.z > 0 || p.jumpT > 0 || p.dunkT > 0) return;
  if (G.mustClear && G.poss === p.team){
    showMsg('CLEAR IT FIRST -- take it past the yellow line');
    return;
  }
  var d = distToRim(p);
  if (d > DUNK_R){
    // too far to dunk: take the jumper instead (the button stays useful)
    shootBall(p);
    return;
  }
  // the dunk: 0.9s. The defender can block it only if he jumps at the
  // exact moment the dunker leaves the floor and is right on him.
  var dunkIdx = Math.floor(Math.random() * DUNKS.length);
  G.dunk = DUNKS[dunkIdx];
  G.dunkBy = p;
  G.dunkT = 0.9;
  p.dunkT = 0.9;
  p.hasBall = true; // he carries it up
  G.phase = 'dunk';
  // the whole dunk plays in slow motion (update() scales dt while the
  // phase is 'dunk'), so the jump, the arm, and the slam all read slow.
  showDunkBanner(G.dunk.n);
  SFX.dunk();
  // PvP: I dunked — tell the other phone which signature dunk, so their
  // dunker flies the same way.
  if (pvpIsOn() && p.team === G.myTeam){
    pvpPostState({ ev: { k: 'dunk', team: p.team, dunk: dunkIdx } });
  }
}
function finishDunk(){
  var p = G.dunkBy;
  if (!p) return;
  // the slam: the ball goes through the net, the point counts
  G.ball.x = RIM_X; G.ball.y = RIM_Y; G.ball.z = RIM_Z - 10;
  G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = -120;
  G.ball.live = true;
  G.dunkScored = true;
  // the dunker NO LONGER has the ball -- without this he is still the
  // carrier, standing at the rim in phase 'play', so COM's AI (which
  // dunks whenever it is in range and has the ball) dunked again before
  // the check ball ran. That was the double dunk, like a replay.
  p.hasBall = false; G.carrier = null;
  scorePoint(p.team);
  p.dunkT = 0;
  G.dunkT = 0;
  G.dunkBy = null; G.dunk = null; // the dunk is over -- clear the references
  G.phase = 'play';
}

// ---------- defense: steal + block ----------
function trySteal(p){
  if (!G.started || G.over || G.phase !== 'play') return;
  if (G.carrier === p) return; // you have the ball -- steal does nothing
  if (p.stealCd > 0) return;
  p.stealCd = 1.0;
  p.kickT = 0.3; // the swipe
  var ball = G.carrier;
  if (!ball) return;
  var d = Math.hypot(ball.x - p.x, ball.y - p.y);
  if (d > 55) { SFX.swish || null; return; } // swiped at air
  var chance = (p.team === AWAY) ? DIFFS[diffIdx].steal : 0.28;
  if (ball.z > 4) chance *= 0.5; // harder to steal it mid-jump
  if (Math.random() < chance){
    // the steal: the ball pops loose, the thief grabs it
    SFX.steal();
    showMsg((p.team === HOME ? 'YOU' : 'COM') + ' PICKED HIS POCKET!');
    ball.hasBall = false;
    G.carrier = p; p.hasBall = true;
    G.poss = p.team;
    G.mustClear = true; // the thief must take it past the line
    G.ball.live = false;
    G.ball.x = p.x; G.ball.y = p.y; G.ball.z = 30;
    updateSB();
    // PvP: I stole it — tell the other phone the ball is mine now.
    if (pvpIsOn() && p.team === G.myTeam){
      pvpPostState({ ev: { k: 'steal', team: p.team } });
    }
  } else {
    SFX.steal();
  }
}
function tryBlock(p){
  if (!G.started || G.over || G.phase !== 'play') return;
  if (G.carrier === p) return;
  if (p.z > 0 || p.jumpT > 0) return; // already jumping
  p.jumpT = 0.5; // the block jump (straight up, arms high)
  p.blockT = 0.5;
  SFX.shoot();
  // PvP: I jumped to block — tell the other phone so they see me rise.
  if (pvpIsOn() && p.team === G.myTeam){
    pvpPostState({ ev: { k: 'block', team: p.team } });
  }
}

// ---------- scoring ----------
function scorePoint(team){
  if (G.over) return; // no scoring after the game is over
  G.score[team]++;
  // nobody grabs the ball off the floor before the check ball runs
  // (the defender could otherwise grab a made jumper's rebound and
  // dunk it in the 900ms before checkBall, for the same double score).
  // Hold it until checkBall actually runs (it resets noCatchT to 0),
  // not just for a fixed 0.95s -- a delayed check ball would reopen it.
  G.noCatchT = 5;
  SFX.point();
  updateSB();
  if (G.score[team] >= WIN_SCORE){
    endGame(team);
    return;
  }
  // the other side takes it out (check ball at the top)
  setTimeout(function(){ if (!G.over) checkBall(1 - team); }, 900);
  // PvP: I scored — tell the other phone who takes it out next.
  if (pvpIsOn()){
    pvpPostState({ ev: { k: 'check', team: team, poss: 1 - team } });
  }
}
function endGame(winner){
  G.over = true;
  G.phase = 'over';
  SFX.win();
  showMsg(winner === HOME ? 'YOU WIN 21-' + G.score[AWAY] + '!' : 'COM WINS 21-' + G.score[HOME], 4);
  document.getElementById('startBtn').textContent = 'REMATCH';
  document.getElementById('overlay').classList.remove('hidden');
  updateSB();
}
function startGame(){
  G.score = [0, 0];
  G.over = false;
  G.started = true;
  document.getElementById('overlay').classList.add('hidden');
  checkBall(HOME); // you take it out first
  updateSB();
  if (pvpIsOn() && G.pvp.role === 'host' && !G.pvp.syncStart){
    // Post the initial state so the guest's game starts too.
    // (A rejoining host does NOT post -- the room already has the game.)
    pvpPostState(null);
  }
}

// ---------- the AI (COM) ----------
function aiPlayer(p, dt){
  var b = G.ball;
  var me = p, foe = otherPlayer(p);
  var diff = DIFFS[diffIdx];
  if (G.phase !== 'play') return;
  if (G.carrier === p){
    // COM has it: drive straight at the rim, dunk when close, shoot from
    // mid-range even when contested (the make chance already docks a
    // contested jumper, so waiting for an open look stalls the game).
    if (G.mustClear && p.y < CLEAR_Y){
      moveToward(p, RIM_X, CLEAR_Y + 60, dt, p.speed);
      return;
    }
    var d = distToRim(p);
    if (d < DUNK_R * 0.9){
      // in range to dunk: on the easy levels he often settles for a
      // jumper instead (which he can miss); on the hard levels he
      // almost always throws it down.
      if (Math.random() < diff.dunk) tryDunk(p);
      else shootBall(p);
      return;
    }
    p.turbo = (p.stam > 20); // COM turbos on the drive, like you do
    moveToward(p, RIM_X, RIM_Y + 40, dt, p.speed);
    if (d < 260 && Math.random() < dt * 0.55){
      shootBall(p);
    } else if (d < 170 && Math.random() < dt * 0.35){
      shootBall(p);
    }
  } else if (G.carrier === foe){
    // COM defends: stay between the ball and the rim, but tight on him
    // (close enough to steal -- 55% left him out of steal range)
    var gx = foe.x + (RIM_X - foe.x) * 0.3;
    var gy = foe.y + (RIM_Y - foe.y) * 0.3;
    p.turbo = (p.stam > 20 && Math.hypot(foe.x - p.x, foe.y - p.y) > 120);
    moveToward(p, gx, gy, dt, p.speed * 0.95);
    var fd = Math.hypot(foe.x - p.x, foe.y - p.y);
    // steal when right on him (sometimes)
    if (fd < 50 && Math.random() < dt * diff.steal * 1.4){
      trySteal(p);
    }
    // block when he jumps to shoot
    if (foe.jumpT > 0.25 && fd < 70 && p.jumpT <= 0 && Math.random() < diff.block){
      tryBlock(p);
    }
  } else if (b.live){
    // the ball is loose: chase it
    moveToward(p, b.x, b.y, dt, p.speed);
  }
}
function moveToward(p, tx, ty, dt, sp){
  var dx = tx - p.x, dy = ty - p.y;
  var d = Math.hypot(dx, dy);
  if (d < 2) return;
  if (p.turbo && p.stam > 0){ sp *= 1.5; p.stam = Math.max(0, p.stam - 32 * dt); }
  var s = Math.min(d, sp * dt);
  p.x += (dx / d) * s; p.y += (dy / d) * s;
  p.moving = true; p.runT += dt * 10;
  p.face = (dx >= 0) ? 1 : -1;
  clampCourt(p);
}

// ---------- the update ----------
var PS = { joy: { x: 0, y: 0 } };
G.dribbleT = 0;

function update(dt){
  if (!G.started || G.over) return;
  updateCamera(dt);
  // slow motion: the WHOLE dunk plays at 0.4x (the jump, the arm, the
  // slam), not just the first half-second. A 0.9s dunk takes ~2.25s real.
  if (G.phase === 'dunk'){ dt *= 0.4; }
  var me = pvpMe();
  var b = G.ball;
  G.dribbleT += dt * 6;
  if (G.noCatchT > 0) G.noCatchT -= dt;
  // cooldowns
  G.players.forEach(function(p){
    if (p.stealCd > 0) p.stealCd -= dt;
    if (p.blockT > 0) p.blockT -= dt;
  });
  // ---- the dunk animation ----
  if (G.phase === 'dunk' && G.dunkBy){
    var dp = G.dunkBy;
    G.dunkT -= dt; dp.dunkT = Math.max(0, G.dunkT);
    var prog = 1 - G.dunkT / 0.9; // 0 -> 1 over the dunk
    // rise to the rim (long dunks start farther and fly farther)
    var rise = Math.sin(Math.min(1, prog * 1.25) * Math.PI);
    dp.z = RIM_Z * 0.92 * rise;
    // travel to the rim (just south of it, then rise and slam)
    var tx = RIM_X, ty = RIM_Y; // directly under the rim (was 24 south of it)
    dp.x += (tx - dp.x) * Math.min(1, dt * 6);
    dp.y += (ty - dp.y) * Math.min(1, dt * 6);
    dp.face = 1;
    // the 360 spins in the air
    if (G.dunk.s === 'spin'){ dp.face = (Math.sin(prog * Math.PI * 2) >= 0) ? 1 : -1; }
    // the reverse goes up backwards (back to the basket)
    if (G.dunk.s === 'reverse'){ dp.face = -1; }
    if (G.dunkT <= 0){
      // the slam lands: the ball through the net, the point, the hang
      finishDunk();
      dp.z = RIM_Z * 0.9; // still hanging on the rim for a beat
      setTimeout(function(){ if (dp) dp.z = 0; }, 350);
    }
    // the defender can still block it if he is right there and jumps now
    var def = otherPlayer(dp);
    if (def.z > 60 && Math.hypot(def.x - dp.x, def.y - dp.y) < 60 && prog < 0.45){
      // BLOCKED at the rim: the ball pops loose
      SFX.block();
      showMsg('REJECTED! ' + (def.team === HOME ? 'YOU' : 'COM') + ' SWATTED IT!');
      b.x = RIM_X + (Math.random() * 80 - 40); b.y = RIM_Y + 40; b.z = 60;
      b.vx = (Math.random() * 200 - 100); b.vy = 220; b.vz = 260;
      b.live = true;
      G.carrier = null; dp.hasBall = false; dp.dunkT = 0;
      G.dunkT = 0; G.dunkBy = null; G.dunk = null;
      G.phase = 'play';
      dp.z = 0;
    }
    draw();
    return;
  }
  // ---- you move with the stick (TURBO held = 1.5x, drains stamina) ----
  var turboOn = me.turbo && me.stam > 0;
  if (PS.joy.x !== 0 || PS.joy.y !== 0){
    var mag = Math.hypot(PS.joy.x, PS.joy.y) || 1;
    var nx = PS.joy.x / mag, ny = PS.joy.y / mag;
    var sp = me.speed * (turboOn ? 1.5 : 1);
    me.x += nx * sp * dt; me.y += ny * sp * dt;
    me.face = nx >= 0 ? 1 : -1;
    me.moving = true; me.runT += dt * 10;
    if (turboOn) me.stam = Math.max(0, me.stam - 32 * dt);
    clampCourt(me);
  } else {
    me.moving = false;
  }
  // stamina refills when you are not turboing (both players)
  G.players.forEach(function(p){
    if (!p.turbo || p.stam <= 0) p.stam = Math.min(100, p.stam + 18 * dt);
  });
  var stamEl = document.getElementById('stamFill');
  if (stamEl) stamEl.style.width = Math.round(me.stam) + '%';
  // ---- the jumps (jump shot + block) ----
  G.players.forEach(function(p){
    if (p.jumpT > 0){
      p.jumpT -= dt;
      var jp = 1 - p.jumpT / 0.55;
      // up and down (a parabola), peak at the middle
      p.z = 62 * Math.sin(Math.min(1, jp * 1.15) * Math.PI);
      // the shot releases at the peak of the jump
      if (G.shotBy === p && p.jumpT <= 0.28 && !p.released){
        p.released = true;
        releaseShot(p);
      }
      if (p.jumpT <= 0){ p.z = 0; p.released = false; }
    }
  });
  // ---- the dribble (the ball bounces at the carrier's side) ----
  if (G.carrier){
    var cp = G.carrier;
    b.x = cp.x; b.y = cp.y; b.z = 30;
    b.live = false;
    // a dribble bounce sound every bounce (when he is moving or standing)
    if (Math.sin(G.dribbleT) > 0.96 && G.started && !G.over) SFX.dribble();
    // the clear: after a steal / defensive rebound, take it south past
    // the line (y greater than CLEAR_Y)
    if (G.mustClear && cp.y > CLEAR_Y){
      G.mustClear = false;
      showMsg('CLEARED -- go get a bucket');
    }
  }
  // ---- the ball in the air (a shot or a loose ball) ----
  if (b.live){
    b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt;
    b.vz -= GRAV * dt;
    // the backboard (a horizontal plane at the top; a shot flying north
    // into it thunks off it and comes back south)
    if (b.y < BOARD_Y + 4 && b.y > BOARD_Y - 14 && b.x > RIM_X - 40 && b.x < RIM_X + 40 && b.z > 60 && b.vy < 0){
      b.vy = Math.abs(b.vy) * 0.55;
      SFX.board();
    }
    // the rim (a shot that clips its EDGE rattles; a dead-center ball
    // drops clean through -- it must not be deflected)
    var rimD = Math.hypot(b.x - RIM_X, b.y - RIM_Y);
    if (rimD > RIM_R - 4 && rimD < RIM_R + 8 && Math.abs(b.z - RIM_Z) < 14 && b.vz < 0){
      // it rattled the rim: bounce it off sideways, it may still drop
      if (Math.random() < 0.5){ b.vx = -b.vx * 0.4; b.vy += (Math.random() * 120 - 60); }
      SFX.rim();
    }
    // through the net (a make): the ball is inside the rim, below its height
    if (rimD < RIM_R - 3 && b.z < RIM_Z && b.z > RIM_Z - 40 && b.vz < 0 && G.shotBy){
      // a made jumper (a dunk goes through finishDunk instead)
      var shooter = G.shotBy;
      G.shotBy = null;
      b.live = false;
      SFX.swish();
      scorePoint(shooter.team);
      draw();
      return;
    }
    // the bounce (the ball hits the ground)
    if (b.z <= 0){
      b.z = 0;
      b.vz = -b.vz * 0.55;
      b.vx *= 0.82; b.vy *= 0.82;
      if (Math.abs(b.vz) < 90){ b.vz = 0; }
      SFX.bounce();
      // a shot that hit the ground without going in is a miss: loose ball
      if (G.shotBy){
        G.shotBy = null;
        // it is a rebound now -- whoever grabs it gets it
      }
    }
    // out of bounds (a wild shot): the other side takes it out
    if (b.x < 10 || b.x > CW - 5 || b.y < 10 || b.y > CH - 5){
      if (G.shotBy) G.shotBy = null;
      b.live = false;
      var lastTeam = G.poss;
      showMsg('OUT OF BOUNDS');
      setTimeout(function(){ if (!G.over) checkBall(1 - lastTeam); }, 700);
      draw();
      return;
    }
    // a block: a defender who jumped and is right on the shooter swats it
    G.players.forEach(function(p){
      if (p === G.shotBy) return;
      if (p.blockT > 0.2 && p.z > 40){
        var bd = Math.hypot(p.x - b.x, p.y - b.y);
        if (bd < 55 && b.z > 60 && b.z < 130){
          SFX.block();
          showMsg('REJECTED! ' + (p.team === HOME ? 'YOU' : 'COM') + ' SWATTED IT!');
          b.vx = (Math.random() * 240 - 120); b.vy = 260; b.vz = 300;
          G.shotBy = null;
        }
      }
    });
  }
  // ---- a loose ball: whoever touches it grabs it ----
  // (not during the no-catch window right after a shot)
  if (!G.carrier && !b.live && G.phase === 'play' && G.noCatchT <= 0){
    // the ball is sitting on the ground after a miss/block: first touch takes it
    G.players.forEach(function(p){
      if (!G.carrier && Math.hypot(p.x - b.x, p.y - b.y) < 26 && p.z < 10){
        p.hasBall = true; G.carrier = p; G.poss = p.team;
        // a defensive rebound means the new offense must clear it
        if (G.poss !== G.lastOffense){
          G.mustClear = true;
        }
        b.live = false;
        updateSB();
        // PvP: I grabbed the loose ball — tell the other phone it is mine.
        if (pvpIsOn() && p.team === G.myTeam){
          pvpPostState({ ev: { k: 'grab', team: p.team } });
        }
      }
    });
  }
  if (!G.carrier && b.live && G.noCatchT <= 0){
    // a live loose ball (a rebound in the air): first touch takes it
    G.players.forEach(function(p){
      if (!G.carrier && Math.hypot(p.x - b.x, p.y - b.y) < 28 && Math.abs(p.z - b.z) < 70){
        p.hasBall = true; G.carrier = p; G.poss = p.team;
        if (G.poss !== G.lastOffense){
          G.mustClear = true;
        }
        b.live = false; b.vx = 0; b.vy = 0; b.vz = 0;
        updateSB();
        // PvP: I grabbed the loose ball in the air — tell the other phone.
        if (pvpIsOn() && p.team === G.myTeam){
          pvpPostState({ ev: { k: 'grab', team: p.team } });
        }
      }
    });
  }
  // remember who the offense was (for the clear rule)
  if (G.carrier) G.lastOffense = G.carrier.team;
  // PvP: the opponent's position glides toward the last posted spot
  // (no teleporting), and my position is posted ~4x a second.
  if (pvpIsOn()){
    var op = pvpOpp();
    if (op && typeof op.tx === 'number' && typeof op.ty === 'number'){
      var odx = op.tx - op.x, ody = op.ty - op.y;
      var od = Math.hypot(odx, ody);
      if (od > 2){
        var os = Math.min(od, 400 * dt);
        op.x += (odx / od) * os; op.y += (ody / od) * os;
        op.moving = true; op.runT += dt * 10;
        op.face = (odx >= 0) ? 1 : -1;
        clampCourt(op);
      } else {
        op.moving = false;
      }
    }
    G.pvp.posT = (G.pvp.posT || 0) + dt;
    if (G.pvp.posT >= 0.1){
      G.pvp.posT = 0;
      pvpPostState(null);
    }
  }
  // ---- the COM AI (PvC only -- in PvP the opponent is a real person) ----
  if (!pvpIsOn()) aiPlayer(G.players[AWAY], dt);
  draw();
}

// ---------- the frame ----------
function frame(){
  update(0.016);
  requestAnimationFrame(frame);
}
function draw(){
  ctx.clearRect(0, 0, W, H);
  drawPlayground();
  drawHoop();
  // the players, far (top) first so the near one overlaps
  var ps = G.players.slice().sort(function(a, b){ return a.y - b.y; });
  ps.forEach(function(p){ drawPlayer(p); });
  drawBall();
  drawNet(); // the net over the ball, so it drops through it
  // the shot meter (while a jumper is going up)
  var mEl = document.getElementById('meter');
  if (G.shotBy && G.phase === 'play'){
    mEl.style.display = 'block';
  } else {
    mEl.style.display = 'none';
  }
}

// ---------- the input ----------
var PSJ = PS.joy;
(function(){
  var joy = document.getElementById('joy'), stick = document.getElementById('stick');
  var jid = null;
  function setJoy(e){
    var r = joy.getBoundingClientRect();
    var cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    var dx = (e.clientX - cx) / (r.width / 2), dy = (e.clientY - cy) / (r.height / 2);
    var m = Math.hypot(dx, dy);
    if (m > 1){ dx /= m; dy /= m; }
    PSJ.x = dx; PSJ.y = dy;
    stick.style.left = (33 + dx * 34) + 'px';
    stick.style.top = (33 + dy * 34) + 'px';
  }
  joy.addEventListener('pointerdown', function(e){ jid = e.pointerId; joy.setPointerCapture(jid); setJoy(e); });
  joy.addEventListener('pointermove', function(e){ if (e.pointerId === jid) setJoy(e); });
  function endJoy(e){ if (e.pointerId === jid){ jid = null; PSJ.x = 0; PSJ.y = 0; stick.style.left = '33px'; stick.style.top = '33px'; } }
  joy.addEventListener('pointerup', endJoy);
  joy.addEventListener('pointercancel', endJoy);
  // Button A: SHOOT on offense (DUNK while TURBO is held), BLOCK on defense
  // Button A: SHOOT on offense (always a jumper now), BLOCK on defense.
  document.getElementById('btnA').addEventListener('pointerdown', function(){
    if (!G.started || G.over) return;
    SFX.unlock();
    if (G.poss === G.myTeam){
      shootBall(pvpMe());
    } else {
      tryBlock(pvpMe());
    }
  });
  // Button D: DUNK -- its own button, above SHOOT, offense only.
  document.getElementById('btnD').addEventListener('pointerdown', function(){
    if (!G.started || G.over) return;
    SFX.unlock();
    if (G.poss === G.myTeam) tryDunk(pvpMe());
  });
  // Button B: STEAL (defense only -- dimmed on offense)
  document.getElementById('btnB').addEventListener('pointerdown', function(){
    if (!G.started || G.over) return;
    SFX.unlock();
    if (G.poss !== G.myTeam) trySteal(pvpMe());
  });
  // Button C: TURBO (hold to sprint). Drive in with it, then hit DUNK.
  var turboBtn = document.getElementById('btnC');
  function turboOn(e){ if (!G.started || G.over) return; SFX.unlock(); pvpMe().turbo = true; updateSB(); }
  function turboOff(e){ pvpMe().turbo = false; updateSB(); }
  turboBtn.addEventListener('pointerdown', turboOn);
  turboBtn.addEventListener('pointerup', turboOff);
  turboBtn.addEventListener('pointercancel', turboOff);
  turboBtn.addEventListener('pointerleave', turboOff);
  document.getElementById('btnSound').addEventListener('pointerdown', function(){
    SFX.unlock();
    var off = SFX.toggle();
    document.getElementById('btnSound').textContent = off ? '🔇' : '🔊';
  });
  document.getElementById('btnMenu').addEventListener('pointerdown', function(){
    SFX.unlock(); SFX.click();
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('startBtn').textContent = G.started && !G.over ? 'RESUME' : 'START GAME';
  });
  var diffRow = document.getElementById('diffRow');
  DIFFS.forEach(function(d, i){
    var b = document.createElement('button');
    b.textContent = d.n;
    if (i === diffIdx) b.classList.add('sel');
    b.addEventListener('pointerdown', function(){
      SFX.unlock(); SFX.click();
      setDiff(i);
      Array.prototype.forEach.call(diffRow.children, function(c, j){ c.classList.toggle('sel', j === i); });
    });
    diffRow.appendChild(b);
  });
  document.getElementById('startBtn').addEventListener('pointerdown', function(){
    SFX.unlock(); SFX.click();
    if (G.started && !G.over){
      document.getElementById('overlay').classList.add('hidden');
      return;
    }
    if (G.over){ G.score = [0, 0]; }
    startGame();
  });
  document.getElementById('leaveBtn').addEventListener('pointerdown', function(){
    if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage){
      window.ReactNativeWebView.postMessage('close');
    }
  });
  /* ---------- PvP room (create / join) ---------- */
  function pvpSetStatus(t){ var el = document.getElementById('pvpStatus'); if (el) el.textContent = t; }
  function pvpSetRoomLbl(t){ var el = document.getElementById('pvpRoomLbl'); if (el) el.textContent = t; }
  document.getElementById('pvpBtn').addEventListener('pointerdown', function(){
    document.getElementById('pvpPanel').classList.toggle('hidden');
  });
  document.getElementById('pvpCreateBtn').addEventListener('pointerdown', function(){
    var who = pvpPlayer();
    pvpSetStatus('Creating room...');
    pvpPost('/create', { player_id: who.id, player_name: who.name, game: 'one_on_one' }).then(function(room){
      if (!room || !room.code){ pvpSetStatus('Could not create a room — check your connection and try again.'); return; }
      G.myTeam = HOME; // host is DANTE (takes it out first)
      G.pvp = { code: room.code, role: 'host', oppName: '', seq: 0, oppSeq: -1, pollTimer: null, posT: 0 };
      pvpSetStatus('Room created! Give this code to the other player:');
      pvpSetRoomLbl('CODE: ' + room.code + ' — waiting for them to join...');
      pvpStartPoll();
    });
  });
  document.getElementById('pvpJoinBtn').addEventListener('pointerdown', function(){
    var code = (document.getElementById('pvpCodeInput').value || '').trim();
    if (!/^[0-9]{4}$/.test(code)){ pvpSetStatus('Enter the 4-digit code from the other phone.'); return; }
    var who = pvpPlayer();
    pvpSetStatus('Joining room ' + code + '...');
    pvpPost('/join', { code: code, player_id: who.id, player_name: who.name }).then(function(room){
      if (!room || !room.code){ pvpSetStatus('Room not found — check the code and try again.'); return; }
      G.myTeam = AWAY; // guest is CODY
      G.pvp = { code: room.code, role: 'guest', oppName: room.host_name || 'Opponent', seq: 0, oppSeq: -1, pollTimer: null, posT: 0 };
      pvpSetStatus('Joined! You are CODY.');
      pvpSetRoomLbl('CODE: ' + room.code + ' — vs ' + G.pvp.oppName);
      pvpStartPoll();
      showMsg('WAITING FOR HOST', 'The host starts the game.');
    });
  });
})();

// change the level: COM's feet, hands, and jumper follow it
function setDiff(i){
  diffIdx = i;
  G.players.forEach(function(p){ if (p.team === AWAY) p.speed = 265 * DIFFS[diffIdx].cpu; });
}

// ---------- the test hooks ----------
window.__PB = {
  G: G, HOME: HOME, AWAY: AWAY, CW: CW, CH: CH, RIM_X: RIM_X, RIM_Y: RIM_Y,
  RIM_Z: RIM_Z, CLEAR_Y: CLEAR_Y, DUNK_R: DUNK_R, WIN_SCORE: WIN_SCORE,
  DUNKS: DUNKS, DIFFS: DIFFS,
  startGame: startGame, checkBall: checkBall, update: update,
  shootBall: shootBall, releaseShot: releaseShot, tryDunk: tryDunk, finishDunk: finishDunk,
  trySteal: trySteal, tryBlock: tryBlock, scorePoint: scorePoint,
  aiPlayer: aiPlayer, moveToward: moveToward, setDiff: setDiff,
  clampCourt: clampCourt, distToRim: distToRim, updateSB: updateSB, frame: frame,
  joy: PS.joy, draw: draw,
  pvpPlayer: pvpPlayer, pvpIsOn: pvpIsOn, pvpMe: pvpMe, pvpOpp: pvpOpp,
  pvpReceiveEv: pvpReceiveEv, pvpApplyState: pvpApplyState, pvpPostState: pvpPostState,
  pvpStartPoll: pvpStartPoll, pvpStopPoll: pvpStopPoll, pvpPollOnce: pvpPollOnce,
};

draw();
requestAnimationFrame(frame);

/* ---------- PvP extras: share room code + rematch (both players agree) ---------- */
function pvpIsOver(){ return !!(G.over || G.mode === 'over'); }
function pvpNotStarted(){ return !(G.started || G.mode === 'play' || pvpIsOver()); }
function pvpRequestRematch(){
  if (!pvpIsOn() || !pvpIsOver()) return;
  G.pvp.rmReq = (G.pvp.round || 0) + 1;
  pvpPostState({});
  pvpExtrasRefresh();
}
function pvpRematchCheck(room, st){
  // Each phone posts rm = the round it wants to play next. When both
  // phones want round+1, both restart. Posts from an older round are
  // dropped so an old score can never leak into the new game.
  var oppRole = G.pvp.role === 'host' ? 'guest' : 'host';
  var opp = (room.states && room.states[oppRole]) || null;
  var r = G.pvp.round || 0;
  G.pvp.oppRm = (opp && typeof opp.rm === 'number') ? opp.rm : 0;
  G.pvp.lastRoom = room;
  if (room.status !== 'finished' && G.pvp.rmReq === r + 1 && G.pvp.oppRm === r + 1 && pvpWagerReady(room, r + 1)){
    G.pvp.round = r + 1;
    G.pvp.oppMe = null;
    G.over = false;
    startGame();
    pvpExtrasRefresh();
  }
  if (st && (st.round || 0) < (G.pvp.round || 0)) return null;
  return st;
}
function pvpShareCode(){
  if (!pvpIsOn()) return;
  var code = String(G.pvp.code);
  if (window.ReactNativeWebView){ window.ReactNativeWebView.postMessage('share:' + code); return; }
  if (navigator.share){ navigator.share({ text: 'Join my game in Street Legends! Room code: ' + code }).catch(function(){}); return; }
  try { navigator.clipboard.writeText(code); } catch(e){}
}
var pvpBar = document.createElement('div');
pvpBar.id = 'pvpExtras';
pvpBar.style.cssText = 'position:fixed;left:50%;bottom:18px;transform:translateX(-50%);z-index:9999;display:none;flex-direction:column;align-items:center;gap:6px;background:rgba(0,0,0,.85);border:2px solid #f5c518;border-radius:12px;padding:10px 14px;font-family:Arial,Helvetica,sans-serif;max-width:92vw';
pvpBar.innerHTML = '<div id="pvpExMsg" style="color:#ffd54f;font-size:14px;font-weight:700;text-align:center"></div>'
  + '<div style="display:flex;gap:8px">'
  + '<button id="pvpExShare" style="background:#2e7d32;color:#fff;border:2px solid #fff;border-radius:10px;padding:10px 14px;font-size:15px;font-weight:800;min-height:44px">SHARE CODE</button>'
  + '<button id="pvpExRematch" style="background:#6a1b9a;color:#fff;border:2px solid #fff;border-radius:10px;padding:10px 14px;font-size:15px;font-weight:800;min-height:44px">REMATCH</button>'
  + '</div>';
document.body.appendChild(pvpBar);
/* ---------- PvP cash wager (host bets, guest accepts, winner takes both) ---------- */
function pvpWagerPost(action, body){
  return pvpPost('/' + G.pvp.code + '/wager/' + action, body).then(function(room){
    if (room && room.code){ G.pvp.lastRoom = room; G.pvp.wErr = ''; }
    else G.pvp.wErr = action === 'propose' ? 'Bet failed - you may not have that much cash.' : (action === 'agree' ? 'Could not accept - one of you is short on cash.' : 'Bet action failed - try again.');
    pvpExtrasRefresh();
    return room;
  });
}
function pvpWagerReady(room, nextRound){
  // Games (first game and rematches) wait while a bet is being decided.
  var s = (room && room.wager_status) || 'none';
  if (s === 'proposed') return false;
  if (s === 'agreed'){
    if (!G.pvp.wStarting){ G.pvp.wStarting = true; pvpWagerPost('start', { player_id: pvpPlayer().id }).then(function(){ G.pvp.wStarting = false; }); }
    return false;
  }
  if (s === 'held') return (room.wager_round || 0) === nextRound;
  return true;
}
function pvpWagerWinnerTeam(){
  // Scores are team-indexed in every park game (0 = host, 1 = guest).
  // Tennis is decided by games won in the set.
  var sc = (Array.isArray(G.games) && Array.isArray(G.pts)) ? G.games : G.score;
  if (!Array.isArray(sc) || sc[0] === sc[1]) return -1;
  return sc[0] > sc[1] ? 0 : 1;
}
function pvpWagerSettleIfOver(){
  var room = G.pvp.lastRoom, r = G.pvp.round || 0;
  if (!room || room.wager_status !== 'held' || (room.wager_round || 0) !== r) return;
  if (!pvpIsOver() || room.status === 'finished' || G.pvp.wSettled === r) return;
  G.pvp.wSettled = r;
  var t = pvpWagerWinnerTeam();
  var body = { player_id: pvpPlayer().id, outcome: t < 0 ? 'draw' : 'win', winner_id: t === 0 ? room.host_id : (t === 1 ? room.guest_id : '') };
  pvpWagerPost('settle', body);
}
var pvpWagerBox = document.createElement('div');
pvpWagerBox.style.cssText = 'display:flex;flex-direction:column;align-items:center;gap:6px';
pvpWagerBox.innerHTML = '<div id="pvpWMsg" style="color:#7CFC9A;font-size:14px;font-weight:700;text-align:center"></div>'
  + '<div id="pvpWHost" style="display:flex;gap:8px;align-items:center">'
  + '<input id="pvpWAmt" inputmode="numeric" maxlength="7" placeholder="$ BET" style="width:100px;text-align:center;font-size:16px;padding:10px;border-radius:8px;border:2px solid #f5c518;background:#111;color:#fff" />'
  + '<button id="pvpWBet" style="background:#f5c518;color:#000;border:2px solid #fff;border-radius:10px;padding:10px 14px;font-size:15px;font-weight:800;min-height:44px">BET CASH</button></div>'
  + '<div id="pvpWGuest" style="display:flex;gap:8px">'
  + '<button id="pvpWAccept" style="background:#2e7d32;color:#fff;border:2px solid #fff;border-radius:10px;padding:10px 14px;font-size:15px;font-weight:800;min-height:44px">ACCEPT BET</button>'
  + '<button id="pvpWDecline" style="background:#b71c1c;color:#fff;border:2px solid #fff;border-radius:10px;padding:10px 14px;font-size:15px;font-weight:800;min-height:44px">DECLINE</button></div>';
pvpBar.appendChild(pvpWagerBox);
document.getElementById('pvpWBet').addEventListener('click', function(){
  var amt = parseInt((document.getElementById('pvpWAmt').value || '').replace(/[^0-9]/g, ''), 10);
  if (!amt || amt <= 0){ G.pvp.wErr = 'Enter how much cash to bet.'; pvpExtrasRefresh(); return; }
  var r = G.pvp.round || 0;
  pvpWagerPost('propose', { player_id: pvpPlayer().id, amount: amt, round: pvpIsOver() ? r + 1 : r });
});
document.getElementById('pvpWAccept').addEventListener('click', function(){ pvpWagerPost('agree', { player_id: pvpPlayer().id }); });
document.getElementById('pvpWDecline').addEventListener('click', function(){ pvpWagerPost('decline', { player_id: pvpPlayer().id }); });
function pvpWagerRefresh(){
  var room = G.pvp.lastRoom || {}, s = room.wager_status || 'none', amt = room.wager_amount || 0;
  var me = pvpPlayer().id, isHost = G.pvp.role === 'host', r = G.pvp.round || 0;
  var nextRound = pvpIsOver() ? r + 1 : r;
  var betForNext = (s === 'proposed' || s === 'agreed' || s === 'held') && (room.wager_round || 0) === nextRound;
  var canPropose = isHost && room.status !== 'finished' && !betForNext && s !== 'agreed' && !(s === 'held');
  document.getElementById('pvpWHost').style.display = canPropose ? 'flex' : 'none';
  document.getElementById('pvpWGuest').style.display = (!isHost && s === 'proposed') ? 'flex' : 'none';
  var $m = '$' + Number(amt).toLocaleString();
  var msg = '';
  if (s === 'proposed') msg = isHost ? 'Waiting for them to accept your ' + $m + ' bet...' : 'Host bets ' + $m + ' - winner takes ' + '$' + Number(2 * amt).toLocaleString() + '!';
  else if (s === 'agreed') msg = 'Bet accepted! Taking ' + $m + ' from each player...';
  else if (s === 'held') msg = (room.wager_round || 0) === r && pvpIsOver() ? 'Settling the ' + $m + ' bet...' : $m + ' each is on the line!';
  else if (s === 'paid') msg = room.wager_winner_id === me ? 'You won the bet: +' + '$' + Number(2 * amt).toLocaleString() + '!' : 'You lost the ' + $m + ' bet.';
  else if (s === 'refunded') msg = 'Bet refunded to both players.';
  else if (s === 'declined') msg = isHost ? 'They declined the bet.' : 'Bet declined.';
  else if (isHost) msg = 'Optional: bet cash on this game.';
  if (G.pvp.wErr) msg = G.pvp.wErr;
  document.getElementById('pvpWMsg').textContent = msg;
}

document.getElementById('pvpExShare').addEventListener('click', pvpShareCode);
document.getElementById('pvpExRematch').addEventListener('click', pvpRequestRematch);
// In PvP the game's own REMATCH button asks the other phone instead of
// restarting only this phone.
document.addEventListener('click', function(e){
  var t = e.target;
  if (t && t.id === 'rematchBtn' && pvpIsOn()){ e.stopImmediatePropagation(); e.preventDefault(); pvpRequestRematch(); }
}, true);
function pvpExtrasRefresh(){
  var on = pvpIsOn();
  if (on) pvpWagerSettleIfOver();
  var notStarted = on && pvpNotStarted();
  var waiting = notStarted && G.pvp.role === 'host' && !(G.pvp.lastRoom && G.pvp.lastRoom.guest_id);
  var over = on && pvpIsOver();
  pvpBar.style.display = (notStarted || over) ? 'flex' : 'none';
  if (!(notStarted || over)) return;
  pvpWagerRefresh();
  var r = G.pvp.round || 0;
  var mine = G.pvp.rmReq === r + 1, theirs = G.pvp.oppRm === r + 1;
  document.getElementById('pvpExShare').style.display = waiting ? 'block' : 'none';
  var rb = document.getElementById('pvpExRematch');
  rb.style.display = over ? 'block' : 'none';
  rb.disabled = mine; rb.style.opacity = mine ? '0.6' : '1';
  var msg = waiting ? 'Room ' + G.pvp.code + ' - send the code to your friend' : 'Starting soon...';
  if (over) msg = mine ? 'Rematch asked - waiting for the other player...' : (theirs ? 'The other player wants a REMATCH!' : 'Game over - play again?');
  document.getElementById('pvpExMsg').textContent = msg;
}
setInterval(pvpExtrasRefresh, 300);
</script>
</body>
</html>
`;
