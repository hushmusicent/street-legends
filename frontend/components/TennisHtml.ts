// PARK_TENNIS_HTML
export const TENNIS_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Park Tennis '84</title>
<style>
  html,body{margin:0;padding:0;background:#3a2a1a;height:100%;overflow:hidden;
    font-family:Arial,Helvetica,sans-serif;-webkit-user-select:none;user-select:none;
    touch-action:none}
  #wrap{position:fixed;inset:0}
  canvas{display:block;width:100%;height:100%}
  /* the purple score bar (like the screenshots' scoreboard) */
  #sb{position:absolute;top:0;left:0;right:0;height:52px;background:linear-gradient(#5b2a86,#3d1c5c);
    color:#fff;display:flex;align-items:center;justify-content:space-between;
    padding:0 10px;box-sizing:border-box;z-index:5;border-bottom:3px solid #2a1140}
  #sb .sc{font-size:22px;font-weight:bold;letter-spacing:1px}
  #sb .sc .you{color:#ffe14d}
  #sb .card{font-size:12px;line-height:1.25;text-align:center;min-width:150px}
  #sb .card b{font-size:13px}
  #sb .pill{background:#fff;color:#5b2a86;font-weight:bold;border-radius:12px;
    padding:3px 10px;font-size:12px}
  #msg{position:absolute;top:60px;left:50%;transform:translateX(-50%);
    background:rgba(0,0,0,0.75);color:#ffe14d;font-weight:bold;font-size:18px;
    padding:8px 18px;border-radius:10px;z-index:6;pointer-events:none;
    opacity:0;transition:opacity .2s;white-space:nowrap}
  #msg small{display:block;color:#fff;font-size:12px;text-align:center}
  /* the difficulty / menu overlay */
  #overlay{position:absolute;inset:0;background:rgba(0,0,0,0.72);z-index:20;
    display:flex;flex-direction:column;align-items:center;justify-content:center;color:#fff}
  #overlay.hidden{display:none}
  #overlay h1{margin:0 0 4px;font-size:30px;letter-spacing:2px;color:#ffe14d}
  #overlay p{margin:0 0 18px;color:#cdb2ea;font-size:14px}
  #diffRow{display:flex;gap:8px;margin-bottom:18px}
  #diffRow button{background:#2a1140;color:#fff;border:2px solid #7b4bb3;border-radius:10px;
    padding:10px 14px;font-size:15px;font-weight:bold}
  #diffRow button.sel{background:#ffe14d;color:#3d1c5c;border-color:#ffe14d}
  #startBtn{pointer-events:auto;background:#2e7d32;color:#fff;border:3px solid #fff;border-radius:14px;
    padding:14px 34px;font-size:20px;font-weight:bold;letter-spacing:1px}
  #leaveBtn{pointer-events:auto;background:#c62828;color:#fff;border:3px solid #fff;border-radius:14px;
    padding:14px 34px;font-size:20px;font-weight:bold;letter-spacing:1px;margin-top:10px}
  /* the controls: joystick bottom-left, shot buttons bottom-right */
  #joy{position:absolute;left:18px;bottom:22px;width:128px;height:128px;border-radius:50%;
    background:rgba(255,255,255,0.14);border:2px solid rgba(255,255,255,0.5);z-index:10}
  #stick{position:absolute;left:44px;top:44px;width:40px;height:40px;border-radius:50%;
    background:rgba(255,255,255,0.75);border:2px solid #fff}
  .abtn{position:absolute;border-radius:50%;border:3px solid #fff;color:#fff;
    font-weight:bold;z-index:10;box-shadow:0 3px 0 rgba(0,0,0,0.4)}
  #btnHit{right:20px;bottom:26px;width:88px;height:88px;background:#c62828;font-size:19px}
  #btnLob{right:118px;bottom:96px;width:66px;height:66px;background:#1565c0;font-size:15px}
  #btnDrop{right:118px;bottom:20px;width:66px;height:66px;background:#2e7d32;font-size:15px}
  #btnMenu{position:absolute;top:60px;right:10px;z-index:10;background:rgba(0,0,0,0.55);
    color:#fff;border:2px solid #fff;border-radius:8px;padding:6px 12px;font-weight:bold}
  #btnSound{position:absolute;top:60px;right:86px;z-index:10;background:rgba(0,0,0,0.55);
    color:#fff;border:2px solid #fff;border-radius:8px;padding:6px 10px;font-size:16px}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="cv"></canvas>
  <div id="sb">
    <div class="sc"><span class="you">YOU</span> <span id="scYou">0</span> - <span id="scCom">0</span> COM</div>
    <div class="card"><b id="cardName">DANTE</b><br><span id="cardSub">YOU SERVE • DEUCE COURT</span></div>
    <div class="pill" id="setPill">SET 1 • 0-0</div>
  </div>
  <div id="msg"></div>
  <div id="overlay">
    <h1>PARK TENNIS '84</h1>
    <p>Official rules • One set, first to 6 games • Tiebreak at 6-6</p>
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
  <div id="joy"><div id="stick"></div></div>
  <button class="abtn" id="btnHit">HIT</button>
  <button class="abtn" id="btnLob">LOB</button>
  <button class="abtn" id="btnDrop">DROP</button>
  <button id="btnMenu">MENU</button>
  <button id="btnSound" title="Sound on/off">🔊</button>
</div>
<script>
/* =================================================================
   BACKYARD TENNIS '84 (built fresh from the screenshots)

   NES Tennis look: green court, brown surround, umpire chair, "NET!" /
   "DOUBLE FAULT!" -- but 3D hues and shadows like the soccer players.
   Official tennis: real scoring (15/30/40, deuce, advantage), a set to
   6 games (win by 2, tiebreak at 6-6), serves that must land in the
   diagonal service box, faults, double faults, lets on serve, and the
   ball must land in (singles lines) or the hitter loses the point.
   No shortcuts.
   SOUND: every sound is synthesized with the Web Audio API -- no audio
   files to download, so the game stays one small file. The AudioContext
   is created on the first tap (phones block audio until a gesture), and
   every call is a no-op when there is no audio (or when muted), so the
   smoke suites run silent and never crash.
   ================================================================= */
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
  // a short tone: freq (Hz), dur (s), type, volume, optional start delay
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
  // a burst of filtered noise: dur (s), filter freq, volume, optional sweep
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
    // the racket connecting with the ball: a sharp thwack + a low thump
    hit: function(){ burst(0.08, 1200, 0.3); tone(180, 0.1, 'sine', 0.25, 0, 90); },
    // the serve toss: a soft rising whoosh
    whoosh: function(){ burst(0.3, 500, 0.12, 1400); },
    // a swing that misses (a whiff): a soft swish, so the swing is heard
    swish: function(){ burst(0.15, 900, 0.1, 400); },
    // the ball bouncing: a soft low thud
    bounce: function(){ tone(140, 0.07, 'sine', 0.18, 0, 70); burst(0.04, 300, 0.08); },
    // the ball into the net: a dull thunk
    net: function(){ tone(90, 0.12, 'sine', 0.25, 0, 60); burst(0.06, 250, 0.15); },
    // a fault: a low double-buzz
    fault: function(){ tone(140, 0.16, 'sawtooth', 0.16); tone(140, 0.16, 'sawtooth', 0.16, 0.2); },
    // a point won: a bright two-note chime
    point: function(){ tone(660, 0.12, 'sine', 0.2); tone(880, 0.18, 'sine', 0.2, 0.12); },
    // a game won: three rising notes + a swell of crowd applause
    game: function(){
      tone(523, 0.14, 'triangle', 0.22); tone(659, 0.14, 'triangle', 0.22, 0.13); tone(784, 0.22, 'triangle', 0.25, 0.26);
      burst(1.1, 1000, 0.1, 600, 0.3);
    },
    // the set won: a longer fanfare + bigger applause
    set: function(){
      var notes = [523, 659, 784, 1047, 1319];
      for (var i = 0; i < notes.length; i++) tone(notes[i], 0.18, 'triangle', 0.24, i * 0.14);
      burst(1.8, 1100, 0.12, 500, 0.4);
    },
  };
})();

// ---------- the court (field units) ----------
const CW = 360, CL = 540;               // doubles width / length
const NET_Y = CL / 2;                   // 270, the net line
const SING_L = 45, SING_R = CW - 45;    // singles sidelines (27ft of 36ft)
const SERV_D = 145;                     // service line: 21ft from the net
const SERV_T = NET_Y - SERV_D;          // 125, top service line
const SERV_B = NET_Y + SERV_D;          // 415, bottom service line
const CTR_X = CW / 2;                   // 180, centre service line
const NET_H = 30;                       // the net is 30 units tall (z)
const WALL = 0;                          // the court edge is the boundary
const GRAV = 2200;                      // gravity on the ball (z units/s^2)
const HOME = 0, AWAY = 1;               // HOME = you (bottom), AWAY = COM (top)
const ROSTER = [
  [ { n: 'DANTE', r: 'YOU' } ],
  [ { n: 'CODY', r: 'COM' } ],
];
// ball: the flight-time multiplier -- Rookie balls float (1.3x the time,
// so slower), Legend balls fly (0.8x the time, so faster). The whole game
// speeds up as you climb the levels, not just COM's feet.
const DIFFS = [
  { n: 'ROOKIE', cpu: 0.72, ball: 1.3 }, { n: 'AMATEUR', cpu: 0.86, ball: 1.0 }, { n: 'PRO', cpu: 0.8, ball: 0.95 },
  { n: 'ALL-STAR', cpu: 1.12, ball: 0.85 }, { n: 'LEGEND', cpu: 1.24, ball: 0.75 },
];
let diffIdx = 1;

// ---------- the state ----------
const G = {
  started: false, over: false, half: 1,
  players: [], ball: null, carrier: null,
  // the score: points are 0..3 (0/15/30/40); games; tiebreak points
  pts: [0, 0], games: [0, 0], tbPts: [0, 0], tb: false,
  server: HOME,          // who serves this game
  pointNum: 0,           // points played in this game (serve side: even=deuce)
  tbPointNum: 0,         // points played in the tiebreak
  faults: 0,             // faults on the current serve (0 or 1)
  phase: 'serve',        // 'serve' | 'rally' | 'point' (point is over, resetting)
  pauseT: 0,             // seconds left in the between-points pause
  resume: null,          // what to run when the pause ends
  serveSide: 'deuce',    // 'deuce' | 'ad' -- which side the server serves from
  lastHitter: null,      // who hit the ball last
  bounces: 0,            // bounces since the last hit (0, 1, 2)
  serveBounced: false,   // the serve has bounced once (receiver may hit it)
  netCord: false,        // the serve clipped the net cord (a let if it lands in)
  msgT: 0,
  myTeam: HOME, // PvC: you are always HOME (DANTE, bottom). PvP: HOME if host, AWAY if guest.
  pvp: null,    // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer}
};
const PT_NAMES = ['0', '15', '30', '40'];

/* ---------- PvP (park games) ---------- */
// Same room system as Baseball PvP (backend: /api/park_pvp/rooms/*).
// Tennis is real-time, so the sync is event-based: each hit (serve or
// rally shot) is posted as it happens, and the opponent applies the same
// hitBall() call, so the ball flight matches on both phones. Player
// positions are posted with the state and interpolated on the other side.
// Identity comes from the app as window.PARK_PVP_PLAYER = {id, name}.
var PVP_API = 'https://gta-quest-map.emergent.host/api/park_pvp/rooms';
var PVP_POLL_MS = 250; // positions need a faster poll than baseball's turn-based 400ms
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
  // (hit / serve). The full score + my position ride along so the other
  // phone resyncs and sees where I am.
  if (!pvpIsOn()) return Promise.resolve(null);
  G.pvp.seq += 1;
  var me = pvpMe();
  var st = {
    seq: G.pvp.seq,
    pts: G.pts.slice(), games: G.games.slice(), tbPts: G.tbPts.slice(), tb: G.tb,
    server: G.server, phase: G.phase, pointNum: G.pointNum,
    me: { x: me ? me.x : 0, y: me ? me.y : 0 },
    hit: null, serve: null
  };
  if (patch){
    if (patch.hit) st.hit = patch.hit;
    if (patch.serve) st.serve = patch.serve;
  }
  var who = pvpPlayer();
  return pvpPost('/' + G.pvp.code + '/state', { player_id: who.id, state: st });
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
  pvpGet(code).then(function(room){
    if (!room) return;
    if (room.status === 'finished'){
      pvpStopPoll();
      G.over = true;
      var won = room.winner && room.winner === pvpPlayer().id;
      showMsg(won ? 'YOU WIN!' : 'YOU LOSE', 'The other player left the game.');
      document.getElementById('overlay').classList.remove('hidden');
      document.getElementById('startBtn').textContent = 'START GAME';
      return;
    }
    // Opponent joined — the game starts on its own now (like the house
    // games: the game starts when the second player enters the code).
    if (G.pvp.role === 'host' && room.status === 'playing' && room.guest_name && !G.started){
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
    if (st && st.me && st.me.team === G.myTeam) st = null;
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
  // Resync the score so both phones agree even if a poll was missed --
  // but never from a stale post about an earlier point.
  var staleScore = typeof st.pointNum === 'number' && typeof G.pointNum === 'number' && st.pointNum < G.pointNum;
  if (!staleScore){
  if (Array.isArray(st.pts)) G.pts = st.pts.slice();
  if (Array.isArray(st.games)) G.games = st.games.slice();
  if (Array.isArray(st.tbPts)) G.tbPts = st.tbPts.slice();
  if (typeof st.tb === 'boolean') G.tb = st.tb;
  if (typeof st.server === 'number') G.server = st.server;
  if (typeof st.pointNum === 'number') G.pointNum = st.pointNum;
  }
  updateSB();
  if (fresh) return; // skip events on the first state I apply
  // Opponent position: glide toward it (no teleporting).
  if (st.me && typeof st.me.x === 'number' && typeof st.me.y === 'number'){
    var op = pvpOpp();
    if (op){ op.tx = st.me.x; op.ty = st.me.y; }
  }
  if (st.serve) pvpReceiveServe(st.serve);
  if (st.hit) pvpReceiveHit(st.hit);
}
function pvpReceiveServe(s){
  // The opponent is serving. Run the same toss animation on their side
  // so the ball comes at me; update() launches the hit at the top.
  if (!s || typeof s.team !== 'number' || s.team === G.myTeam) return;
  if (G.phase !== 'serve') return;
  var p = G.players[s.team];
  if (!p || p.serveAnim > 0) return;
  p.serveTx = s.tx; p.serveTy = s.ty;
  p.serveAnim = 0.6;
  SFX.whoosh();
  p.hasBall = false; G.carrier = null;
  G.ball.live = false;
  G.ball.x = p.x; G.ball.y = p.y; G.ball.z = 30;
  G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0;
}
function pvpReceiveHit(h){
  // The opponent hit the ball. Launch the same ball from their racket.
  if (!h || typeof h.team !== 'number' || h.team === G.myTeam) return;
  if (G.phase !== 'rally' && G.phase !== 'serve') return;
  var p = G.players[h.team];
  if (!p) return;
  // Only apply if the ball is not already flying from a newer hit.
  hitBall(p, h.tx, h.ty, h.T);
}

function teamPlayers(t){ return G.players.filter(function(p){ return p.team === t; }); }

// ---------- the players ----------
function makePlayers(){
  G.players = [];
  // you (bottom, behind your baseline) and COM (top, behind his)
  G.players.push({
    team: HOME, idx: 0, role: 'YOU', name: 'DANTE',
    x: CTR_X, y: CL + 35, vx: 0, vy: 0, hx: CTR_X, hy: CL + 35,
    speed: 250, face: 1, runT: 0, moving: false, kickT: 0, hasBall: false,
    serveAnim: 0, serveTx: 0, serveTy: 0,
  });
  G.players.push({
    team: AWAY, idx: 0, role: 'COM', name: 'CODY',
    x: CTR_X, y: -35, vx: 0, vy: 0, hx: CTR_X, hy: -35,
    speed: 250 * DIFFS[diffIdx].cpu, face: -1, runT: 0, moving: false, kickT: 0, hasBall: false,
    serveAnim: 0, serveTx: 0, serveTy: 0,
  });
}
function serverPlayer(){ return G.players[G.server]; }
function receiverPlayer(){ return G.players[1 - G.server]; }

// the service box the serve must land in (diagonal from the server)
function serveBox(){
  // returns {x0,x1,y0,y1} of the box the serve must land in
  const s = G.server;
  const deuce = (G.serveSide === 'deuce');
  if (s === HOME){
    // you serve from the bottom; deuce = right side (x>180) -> top-left box
    return deuce
      ? { x0: SING_L, x1: CTR_X, y0: SERV_T, y1: NET_Y }
      : { x0: CTR_X, x1: SING_R, y0: SERV_T, y1: NET_Y };
  }
  // COM serves from the top; deuce = left side on screen (his right) -> bottom-right box
  return deuce
    ? { x0: CTR_X, x1: SING_R, y0: NET_Y, y1: SERV_B }
    : { x0: SING_L, x1: CTR_X, y0: NET_Y, y1: SERV_B };
}
// where the server stands (behind the baseline, on the deuce/ad side)
function serveSpot(){
  const s = G.server;
  const deuce = (G.serveSide === 'deuce');
  if (s === HOME) return { x: deuce ? 270 : 90, y: CL + 35 };
  return { x: deuce ? 90 : 270, y: -35 };
}
// where the receiver stands (behind their baseline, on the serve's side)
function receiveSpot(){
  const box = serveBox();
  const cx = (box.x0 + box.x1) / 2;
  if (G.server === HOME) return { x: cx, y: -35 };   // COM receives at the top
  return { x: cx, y: CL + 35 };                       // you receive at the bottom
}
function updateServeSide(){
  // deuce court when the points played in this game/tiebreak is even
  const n = G.tb ? G.tbPointNum : G.pointNum;
  G.serveSide = (n % 2 === 0) ? 'deuce' : 'ad';
}

// ---------- the ball ----------
// the ball flies from (x,y,z) to a target (tx,ty) in time T, landing at z=0
function hitBall(from, tx, ty, T){
  // the ball's speed follows the level: slower on Rookie, faster on Legend
  T = T * DIFFS[diffIdx].ball;
  const dx = tx - from.x, dy = ty - from.y;
  const hz = Math.max(10, from.z || 30);
  G.ball.x = from.x; G.ball.y = from.y; G.ball.z = hz;
  G.ball.vx = dx / T; G.ball.vy = dy / T;
  // z(T)=0: vz = 0.5*g*T - hz/T
  G.ball.vz = 0.5 * GRAV * T - hz / T;
  G.ball.live = true; G.ball.kickT = 0.12;
  G.lastHitter = from;
  G.bounces = 0;
  SFX.hit(); // the thwack of the racket
  from.kickT = 0.45; // the racket swings (0.45s: wind back, sweep, follow-through)
  if (from.hasBall){ from.hasBall = false; G.carrier = null; }
}
// aim a rally shot: pick a spot in the opponent's court from the joystick
function aimSpot(p, kind){
  // the opponent's court: y in [0,NET_Y) for your shots, (NET_Y,CL] for COM's
  const up = (p.team === HOME); // you hit up (toward y=0), COM hits down
  const y0 = up ? 30 : NET_Y + 30, y1 = up ? NET_Y - 30 : CL - 30;
  let tx, ty, T;
  if (kind === 'lob'){
    // deep, high arc, near the baseline
    tx = CTR_X + (Math.random() < 0.5 ? -1 : 1) * (60 + Math.random() * 60);
    ty = up ? 60 + Math.random() * 40 : CL - 60 - Math.random() * 40;
    T = 1.15;
  } else if (kind === 'drop'){
    // short, just over the net
    tx = CTR_X + (Math.random() < 0.5 ? -1 : 1) * (40 + Math.random() * 80);
    ty = up ? NET_Y - 50 - Math.random() * 30 : NET_Y + 50 + Math.random() * 30;
    T = 0.7;
  } else {
    // a normal groundstroke: aim with the stick (left/right/centre), medium
    // depth -- and sometimes go for a corner, so a stretched opponent
    // cannot always reach it. Every shot carries a small aim error (bigger
    // on a corner, tiny up the middle), so even good players sometimes
    // miss -- that is how points end, not just on winners.
    const jx = (p === G.players[HOME]) ? PS.joy.x : 0;
    const spread = 130;
    const corner = Math.random() < 0.25;
    let err;
    if (corner){
      tx = (Math.random() < 0.5) ? SING_L + 45 + Math.random() * 25 : SING_R - 45 - Math.random() * 25;
      ty = up ? 50 + Math.random() * 60 : CL - 50 - Math.random() * 60;
      err = 18;
    } else {
      tx = CTR_X + jx * spread + (Math.random() - 0.5) * 50;
      tx = Math.max(SING_L + 20, Math.min(SING_R - 20, tx));
      ty = up ? 90 + Math.random() * 120 : CL - 90 - Math.random() * 120;
      err = 8;
    }
    tx += (Math.random() - 0.5) * err * 2;
    ty += (Math.random() - 0.5) * err * 2;
    // a real miss chance: going for the corner is risky, up the middle is safe
    const missP = corner ? 0.12 : 0.03;
    if (Math.random() < missP){
      if (Math.random() < 0.7){
        // wide of the sideline
        tx = (tx < CTR_X) ? SING_L - 15 - Math.random() * 25 : SING_R + 15 + Math.random() * 25;
      } else {
        // long past the baseline
        ty = up ? -15 - Math.random() * 25 : CL + 15 + Math.random() * 25;
      }
    }
    T = 0.85; // enough time to reach it, not so much it never ends
  }
  return { tx: tx, ty: ty, T: T };
}
function hit(p, kind){
  if (!G.started || G.over || G.phase !== 'rally') return;
  if (G.carrier) return; // the ball is not in play yet
  // you can only hit it when it is close and low enough to reach
  const b = G.ball;
  if (b.kickT > 0) return;
  p.kickT = 0.45; // the racket swings on the attempt, hit or whiff
  const d = Math.hypot(b.x - p.x, b.y - p.y);
  if (d > 55 || b.z > 110){ SFX.swish(); return; }
  const s = aimSpot(p, kind);
  hitBall(p, s.tx, s.ty, s.T);
  // PvP: I hit it — tell the other phone so their ball flies the same way.
  if (pvpIsOn() && p.team === G.myTeam){
    pvpPostState({ hit: { team: p.team, tx: s.tx, ty: s.ty, T: s.T, kind: kind } });
  }
  showMsg('', '');
}
// the serve is a real serve: toss the ball up, jump, swing overhand.
// serve() only starts the 0.6s animation; the hit lands at the top of the
// jump, in update() -- so the motion reads before the ball flies.
function serve(p){
  if (!G.started || G.over || G.phase !== 'serve') return;
  if (p !== serverPlayer()) return;
  if (p.serveAnim > 0) return; // already serving
  const box = serveBox();
  let tx, ty;
  if (p.team === HOME){
    // you aim the serve with the stick (left/right inside the box)
    tx = (box.x0 + box.x1) / 2 + PS.joy.x * (box.x1 - box.x0) * 0.35;
    ty = (box.y0 + box.y1) / 2;
  } else {
    tx = (box.x0 + box.x1) / 2 + (Math.random() - 0.5) * 30;
    ty = (box.y0 + box.y1) / 2 + (Math.random() - 0.5) * 20;
  }
  p.serveTx = tx; p.serveTy = ty;
  p.serveAnim = 0.6;
  SFX.whoosh(); // the toss going up
  p.hasBall = false; G.carrier = null;
  G.ball.live = false;
  G.ball.x = p.x; G.ball.y = p.y; G.ball.z = 30;
  G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0;
  // PvP: I am serving — tell the other phone the target so they see the
  // same toss and the ball comes at them. The hit itself is launched by
  // the serve animation ending (update), on both phones.
  if (pvpIsOn() && p.team === G.myTeam){
    pvpPostState({ serve: { team: p.team, tx: tx, ty: ty } });
  }
}

// ---------- scoring ----------
function pointTo(winner){
  // winner: HOME or AWAY. Returns nothing; advances points/games/set.
  SFX.point(); // the chime when a point is won
  if (G.tb){
    G.tbPts[winner]++;
    G.tbPointNum++;
    // tiebreak serve: switch after odd point numbers (1,3,5...)
    if (G.tbPointNum % 2 === 1) G.server = 1 - G.server;
    updateServeSide();
    if (G.tbPts[winner] >= 7 && G.tbPts[winner] - G.tbPts[1 - winner] >= 2){
      G.games[winner]++; // the tiebreak counts as the 7th game
      endSet(winner);
      return;
    }
    pauseThen(startPoint, 1.8);
    return;
  }
  G.pts[winner]++;
  G.pointNum++;
  updateServeSide();
  // a game is won at 4+ points with a lead of 2
  if (G.pts[winner] >= 4 && G.pts[winner] - G.pts[1 - winner] >= 2){
    gameTo(winner);
    return;
  }
  pauseThen(startPoint, 1.8);
}
function gameTo(winner){
  SFX.game(); // the fanfare + crowd when a game is won
  G.games[winner]++;
  G.pts = [0, 0];
  G.pointNum = 0;
  G.faults = 0;
  G.server = 1 - G.server; // the serve changes hands every game
  updateServeSide();
  const g0 = G.games[0], g1 = G.games[1];
  if ((g0 >= 6 || g1 >= 6) && Math.abs(g0 - g1) >= 2){
    endSet(winner);
    return;
  }
  if (g0 === 6 && g1 === 6){
    G.tb = true; G.tbPts = [0, 0]; G.tbPointNum = 0;
    showMsg('TIEBREAK!', 'First to 7 points, win by 2');
  } else {
    showMsg('GAME!', (winner === HOME ? 'YOU' : 'COM') + ' take the game  •  ' + g0 + '-' + g1);
  }
  pauseThen(startPoint, 2.5);
}
function endSet(winner){
  SFX.set(); // the big fanfare + applause when the set is won
  G.over = true;
  const w = winner === HOME ? 'YOU WIN THE SET!' : 'COM WINS THE SET';
  showMsg(w, 'Games ' + G.games[HOME] + '-' + G.games[AWAY] + ' — tap MENU for a rematch');
  document.getElementById('startBtn').textContent = 'REMATCH';
  document.getElementById('overlay').classList.remove('hidden');
  updateSB();
}
function scoreText(){
  if (G.tb) return G.tbPts[HOME] + ' - ' + G.tbPts[AWAY];
  const a = G.pts[HOME], b = G.pts[AWAY];
  if (a >= 3 && b >= 3){
    if (a === b) return 'DEUCE';
    return (a > b ? 'AD YOU' : 'AD COM');
  }
  return PT_NAMES[a] + ' - ' + PT_NAMES[b];
}

// ---------- point flow ----------
// hold the game for 'delay' seconds (the result shows), then run 'fn'.
// during the pause the ball is dead and nobody moves.
function pauseThen(fn, delay){
  G.phase = 'point';
  G.pauseT = delay;
  G.resume = fn;
  G.ball.live = false;
  G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0;
  G.carrier = null;
  G.players.forEach(function(p){ p.hasBall = false; p.moving = false; });
  updateSB();
}
// a fault or a let re-serves from the same side without resetting the
// point (faults and pointNum stay as they are)
function setupSecondServe(){
  G.phase = 'serve';
  const sv = serverPlayer();
  G.players.forEach(function(p){ p.hasBall = false; });
  sv.hasBall = true; G.carrier = sv;
  G.ball.x = sv.x; G.ball.y = sv.y; G.ball.z = 30;
  G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0; G.ball.live = false;
  G.bounces = 0; G.netCord = false; G.serveBounced = false;
  updateSB();
}
function startPoint(){
  // put the server and receiver in place, ball on the server's racket
  G.phase = 'serve';
  G.faults = 0;
  G.bounces = 0;
  G.netCord = false;
  G.lastHitter = null;
  G.serveBounced = false;
  const sp = serveSpot(), rp = receiveSpot();
  const sv = serverPlayer(), rc = receiverPlayer();
  sv.x = sp.x; sv.y = sp.y; sv.face = (sv.team === HOME) ? 1 : -1;
  rc.x = rp.x; rc.y = rp.y; rc.face = (rc.team === HOME) ? 1 : -1;
  G.players.forEach(function(p){ p.hasBall = false; p.kickT = 0; p.serveAnim = 0; });
  sv.hasBall = true; G.carrier = sv;
  G.ball.x = sv.x; G.ball.y = sv.y; G.ball.z = 30;
  G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0; G.ball.live = false;
  updateSB();
}
function fault(){
  // a serve fault. Two in a row = double fault, lose the point.
  SFX.fault(); // the low buzzer
  G.faults++;
  if (G.faults >= 2){
    showMsg('DOUBLE FAULT!', (G.server === HOME ? 'YOU' : 'COM') + ' lose the point');
    G.faults = 0;
    pointTo(1 - G.server);
    return;
  }
  showMsg('FAULT!', 'Second serve');
  pauseThen(setupSecondServe, 1.2);
}
function letServe(){
  // the serve clipped the net but landed in: replay it, no fault counted
  showMsg('LET!', 'Serve again');
  pauseThen(setupSecondServe, 1.2);
}

// ---------- the AI (COM) ----------
function aiPlayer(p, dt){
  const b = G.ball;
  if (G.phase === 'serve'){
    if (p === serverPlayer()){
      // COM serves after a beat
      p.serveT = (p.serveT || 0) + dt;
      if (p.serveT > 0.9){ p.serveT = 0; serve(p); }
    } else {
      // the receiver shuffles into place
      const rp = receiveSpot();
      moveToward(p, rp.x, rp.y, dt, p.speed * 0.6);
    }
    return;
  }
  if (!b.live) return;
  // chase the ball: run to where it will land (first bounce point)
  const land = predictLanding();
  if (!land) return;
  // only chase it if it is coming to your side
  const mySide = (p.team === HOME) ? (land.y > NET_Y) : (land.y < NET_Y);
  if (mySide){
    moveToward(p, land.x, land.y, dt, p.speed);
    // hit it when it is close and low enough
    const d = Math.hypot(b.x - p.x, b.y - p.y);
    if (d < 55 && b.z < 110 && b.kickT <= 0){
      // the receiver cannot volley a serve: it must bounce first
      if (G.lastHitter === serverPlayer() && !G.serveBounced) return;
      const kind = (Math.random() < 0.12) ? 'lob' : ((Math.random() < 0.12) ? 'drop' : 'hit');
      const s = aimSpot(p, kind);
      hitBall(p, s.tx, s.ty, s.T);
    }
  } else {
    // drift back toward your home spot
    moveToward(p, p.hx, p.hy, dt, p.speed * 0.6);
  }
}
// where the ball will first hit the ground (solves z(t)=0)
function predictLanding(){
  const b = G.ball;
  if (!b.live) return null;
  if (b.vz <= 0 && b.z <= 0) return { x: b.x, y: b.y };
  // z(t) = z + vz*t - 0.5*g*t^2 = 0 -> t = (vz + sqrt(vz^2 + 2*g*z)) / g
  const disc = b.vz * b.vz + 2 * GRAV * b.z;
  const t = (b.vz + Math.sqrt(Math.max(0, disc))) / GRAV;
  return { x: b.x + b.vx * t, y: b.y + b.vy * t };
}
function moveToward(p, tx, ty, dt, sp){
  const dx = tx - p.x, dy = ty - p.y;
  const d = Math.hypot(dx, dy);
  if (d < 2) return;
  const s = Math.min(d, sp * dt);
  p.x += (dx / d) * s; p.y += (dy / d) * s;
  p.moving = true; p.runT += dt * 10;
  p.face = (dx >= 0) ? 1 : -1;
  clampCourt(p);
}
function clampCourt(p){
  p.x = Math.max(-30, Math.min(CW + 30, p.x));
  // Rule 1 -- nobody crosses the net, ever. You stay on your side of it
  // (below it), COM stays on his (above it). Both may stand right at it.
  // Rule 2 -- the server may not cross the baseline before serving (a foot
  // fault). While the phase is 'serve', the server stays behind his own
  // baseline; once the serve is hit the phase is 'rally' and he may move in.
  let yMin, yMax;
  if (p.team === HOME){
    yMin = NET_Y;
    yMax = CL + 40;
    if (G.phase === 'serve' && G.server === HOME) yMin = CL;
  } else {
    yMin = -40;
    yMax = NET_Y;
    if (G.phase === 'serve' && G.server === AWAY) yMax = 0;
  }
  p.y = Math.max(yMin, Math.min(yMax, p.y));
}

// ---------- the update ----------
function update(dt){
  if (!G.started || G.over) return;
  if (G.phase === 'point'){
    G.pauseT -= dt;
    if (G.pauseT <= 0){
      const fn = G.resume; G.resume = null;
      if (fn) fn();
    }
    return;
  }
  // the serve animation: toss, jump, overhand swing, then the hit
  const sv = serverPlayer();
  if (G.phase === 'serve' && sv.serveAnim > 0){
    sv.serveAnim -= dt;
    const prog = 1 - sv.serveAnim / 0.6; // 0 -> 1 over the serve
    // the ball tosses up from the server's hand and hangs high
    G.ball.x = sv.x; G.ball.y = sv.y;
    G.ball.z = 30 + 90 * Math.sin(prog * Math.PI * 0.5);
    G.ball.vx = 0; G.ball.vy = 0; G.ball.vz = 0; G.ball.live = false;
    if (sv.serveAnim <= 0){
      // at the top of the jump, swing overhand and hit it from up high
      sv.z = 120;
      hitBall(sv, sv.serveTx, sv.serveTy, 0.9);
      sv.z = 0;
      G.phase = 'rally';
      G.serveBounced = false;
      G.netCord = false;
    }
  }
  const me = pvpMe();
  const b = G.ball;
  // you move with the stick (not while you are mid-serve, jumping)
  if ((PS.joy.x !== 0 || PS.joy.y !== 0) && !(me === sv && sv.serveAnim > 0)){
    const mag = Math.hypot(PS.joy.x, PS.joy.y) || 1;
    const nx = PS.joy.x / mag, ny = PS.joy.y / mag;
    let sp = me.speed;
    me.x += nx * sp * dt; me.y += ny * sp * dt;
    me.face = nx >= 0 ? 1 : -1;
    me.moving = true; me.runT += dt * 10;
    clampCourt(me);
  } else {
    me.moving = false;
  }
  // PvP: the opponent's position glides toward the last posted spot
  // (no teleporting). In PvC the COM runs itself instead.
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
  }
  // the COM runs itself (PvC only -- in PvP the opponent is a real person)
  G.players.forEach(function(p){
    if (p.team === G.myTeam) return;
    if (pvpIsOn()) return;
    aiPlayer(p, dt);
  });
  // the racket swings settle
  G.players.forEach(function(p){ if (p.kickT > 0) p.kickT -= dt; });
  // PvP: post my position ~4x a second so the other phone sees me move.
  if (pvpIsOn() && G.pvp){
    G.pvp.posT = (G.pvp.posT || 0) + dt;
    if (G.pvp.posT >= 0.25){
      G.pvp.posT = 0;
      pvpPostState(null);
    }
  }
  // the ball
  if (G.carrier){
    const c = G.carrier;
    b.x = c.x + c.face * 14; b.y = c.y + 10;
    b.z = 30;
    b.vx = 0; b.vy = 0; b.vz = 0;
  } else if (b.live){
    if (b.kickT > 0) b.kickT -= dt;
    b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt;
    b.vz -= GRAV * dt;
    // the net: crossing y=NET_Y below the tape = into the net
    const crossed = (b.y - b.vy * dt < NET_Y && b.y >= NET_Y) || (b.y - b.vy * dt > NET_Y && b.y <= NET_Y);
    if (crossed && b.z < NET_H){
      if (G.lastHitter === serverPlayer() && !G.serveBounced){
        // a serve into the net: a clip (just under the tape) dribbles on
        // and may still land in (a let); a solid hit is a fault
        if (b.z > NET_H * 0.6){
          G.netCord = true;
          b.vy *= 0.25; b.vz = -50;
        } else {
          b.live = false;
          fault();
          return;
        }
      } else {
        b.live = false;
        SFX.net(); // the dull thunk of the net
        showMsg('NET!', (G.lastHitter.team === HOME ? 'YOU' : 'COM') + ' hit the net');
        pointTo(1 - G.lastHitter.team);
        return;
      }
    }
    // the bounce
    if (b.z <= 0){
      b.z = 0;
      b.vz = -b.vz * 0.72;
      b.vx *= 0.85; b.vy *= 0.85; // the bounce scrubs speed off the ball
      if (Math.abs(b.vz) < 60){ b.vz = 0; }
      G.bounces++;
      SFX.bounce(); // the thud of the ball on the court
      if (G.lastHitter === serverPlayer() && !G.serveBounced){
        // the serve has bounced once: check the box
        G.serveBounced = true;
        const box = serveBox();
        const inBox = (b.x >= box.x0 && b.x <= box.x1 && b.y >= box.y0 && b.y <= box.y1);
        if (G.netCord){
          G.netCord = false;
          b.live = false;
          if (inBox) letServe(); else fault();
          return;
        }
        if (!inBox){
          b.live = false;
          fault();
          return;
        }
        // good serve: the receiver may now return it
      } else if (G.bounces >= 2){
        // it bounced twice: the player who should have hit it loses
        b.live = false;
        pointTo(G.lastHitter.team);
        return;
      } else if (G.bounces === 1){
        // first bounce of a rally shot: it must land in
        const inCourt = (b.x >= SING_L && b.x <= SING_R &&
          ((G.lastHitter.team === HOME && b.y >= 0 && b.y < NET_Y) ||
           (G.lastHitter.team === AWAY && b.y > NET_Y && b.y <= CL)));
        if (!inCourt){
          b.live = false;
          showMsg('OUT!', 'It landed outside the singles court');
          pointTo(1 - G.lastHitter.team);
          return;
        }
      }
    }
    // the ball flew out past the baselines without bouncing (a wild shot).
    // after a legal first bounce the ball may fly long while live -- the
    // point ends on the second bounce, not on leaving the court in the air.
    if (G.bounces === 0 && (b.y < -40 || b.y > CL + 40 || b.x < -40 || b.x > CW + 40)){
      b.live = false;
      showMsg('OUT!', 'It flew long');
      pointTo(1 - G.lastHitter.team);
      return;
    }
  }
  // you can return it: the HIT buttons work when the ball is close
  updateSB();
}

// ---------- the serve is yours when it is your turn ----------
// (the HIT button serves when you are the server and the phase is 'serve')

// ---------- the draw ----------
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
let W = 0, H = 0;
function fitCanvas(){
  const r = cv.parentElement.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  W = r.width; H = r.height;
  cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener('resize', fitCanvas); fitCanvas();

function courtScale(){ return Math.min((H - 56) / (CL + 80), (W - 24) / (CW + 80)); }
function courtSX(x){ return W / 2 + (x - CW / 2) * courtScale(); }
function courtSY(y){ return 56 + (y + 40) * courtScale(); }

function shade(x, y, r, c1, c2){
  const g = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
  g.addColorStop(0, c1); g.addColorStop(1, c2);
  ctx.fillStyle = g;
}
function lighten(hex){
  const n = parseInt(hex.slice(1), 16);
  const r = Math.min(255, ((n >> 16) & 255) + 45), g = Math.min(255, ((n >> 8) & 255) + 45), b = Math.min(255, (n & 255) + 45);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}
function darken(hex){
  const n = parseInt(hex.slice(1), 16);
  const r = Math.max(0, ((n >> 16) & 255) - 45), g = Math.max(0, ((n >> 8) & 255) - 45), b = Math.max(0, (n & 255) - 45);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}
const TEAM_COLOR = ['#ffd21f', '#222222'];
const TEAM_TRIM = ['#b8860b', '#ffd21f'];
const TEAM_SKIN = ['#c98a5a', '#8d5a3b'];

function drawCourt(){
  const sc = courtScale();
  const x0 = courtSX(-30), x1 = courtSX(CW + 30);
  const y0 = courtSY(-40), y1 = courtSY(CL + 40);
  // the brown surround
  ctx.fillStyle = '#a0662c';
  ctx.fillRect(0, 0, W, H);
  // mowed stripes on the surround (subtle)
  ctx.fillStyle = 'rgba(0,0,0,0.08)';
  for (let i = 0; i < 6; i++){
    if (i % 2 === 0) ctx.fillRect(0, y0 + i * (y1 - y0) / 6, W, (y1 - y0) / 6);
  }
  // the green court (doubles)
  ctx.fillStyle = '#3f9e4d';
  ctx.fillRect(courtSX(0), courtSY(0), (x1 - x0) * (CW / (CW + 60)), (y1 - y0) * (CL / (CL + 80)));
  // mowed stripes on the court
  ctx.fillStyle = 'rgba(255,255,255,0.06)';
  const cw = courtSX(CW) - courtSX(0), ch = courtSY(CL) - courtSY(0);
  for (let i = 0; i < 8; i++){
    if (i % 2 === 0) ctx.fillRect(courtSX(0), courtSY(0) + i * ch / 8, cw, ch / 8);
  }
  // the white lines
  ctx.strokeStyle = '#ffffff'; ctx.lineWidth = 3;
  ctx.strokeRect(courtSX(0), courtSY(0), cw, ch);                       // doubles boundary
  ctx.strokeRect(courtSX(SING_L), courtSY(0), courtSX(SING_R) - courtSX(SING_L), ch); // singles
  ctx.beginPath(); ctx.moveTo(courtSX(0), courtSY(SERV_T)); ctx.lineTo(courtSX(CW), courtSY(SERV_T)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(courtSX(0), courtSY(SERV_B)); ctx.lineTo(courtSX(CW), courtSY(SERV_B)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(courtSX(CTR_X), courtSY(SERV_T)); ctx.lineTo(courtSX(CTR_X), courtSY(SERV_B)); ctx.stroke();
  // the centre marks on the baselines
  ctx.beginPath(); ctx.moveTo(courtSX(CTR_X), courtSY(0)); ctx.lineTo(courtSX(CTR_X), courtSY(10)); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(courtSX(CTR_X), courtSY(CL)); ctx.lineTo(courtSX(CTR_X), courtSY(CL - 10)); ctx.stroke();
  // the net (dark mesh with a white tape top, posts at the ends)
  const ny = courtSY(NET_Y);
  ctx.fillStyle = '#222';
  ctx.fillRect(courtSX(-8), ny - 14 * sc, courtSX(CW + 8) - courtSX(-8), 14 * sc);
  ctx.fillStyle = '#fff';
  ctx.fillRect(courtSX(-8), ny - 14 * sc, courtSX(CW + 8) - courtSX(-8), 3);
  ctx.fillStyle = '#444';
  ctx.fillRect(courtSX(-12), ny - 20 * sc, 5, 26 * sc);
  ctx.fillRect(courtSX(CW + 7), ny - 20 * sc, 5, 26 * sc);
  // the umpire chair (top-right, like the screenshots)
  const ux = courtSX(CW + 22), uy = courtSY(NET_Y) - 46 * sc;
  ctx.fillStyle = '#e8e8e8';
  ctx.fillRect(ux - 4, uy, 8, 46 * sc);
  ctx.fillStyle = '#c62828';
  ctx.fillRect(ux - 12, uy - 12, 24, 14);
  ctx.fillStyle = '#222';
  ctx.beginPath(); ctx.arc(ux, uy - 20, 7, 0, Math.PI * 2); ctx.fill();
}

function drawPlayer(p){
  const sc = courtScale();
  const sx = courtSX(p.x), gy = courtSY(p.y);
  const s = 30 * sc + 14; // the figure's height on screen
  // the jump: on a serve the player leaves the ground (peak mid-serve).
  // the whole figure lifts; the shadow stays on the ground at gy.
  const sProg = (p.serveAnim > 0) ? (1 - p.serveAnim / 0.6) : -1;
  const jumpZ = (sProg >= 0) ? 22 * Math.sin(sProg * Math.PI) : 0;
  const sy = gy - jumpZ;
  const fx = p.face;
  const run = p.moving ? Math.sin(p.runT) : 0;
  const lean = p.moving ? 6 * fx : 0;
  // the drop shadow (stays on the ground, even when he jumps)
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.beginPath(); ctx.ellipse(sx, gy + s * 0.52, s * 0.34, s * 0.12, 0, 0, Math.PI * 2); ctx.fill();
  ctx.lineCap = 'round';
  // the LEGS (a real running stride: one well forward, one trailing back,
  // feet lifting clear of the ground, white boots)
  const fwd = run * s * 0.48, back = -run * s * 0.48;
  const fLift = p.moving ? Math.max(0, -Math.cos(p.runT)) * s * 0.18 : 0;
  const bLift = p.moving ? Math.max(0, Math.cos(p.runT)) * s * 0.18 : 0;
  ctx.strokeStyle = '#222'; ctx.lineWidth = Math.max(3, s * 0.1);
  ctx.beginPath(); ctx.moveTo(sx, sy + s * 0.2); ctx.lineTo(sx + fwd, sy + s * 0.52 - fLift); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(sx, sy + s * 0.2); ctx.lineTo(sx + back, sy + s * 0.52 - bLift); ctx.stroke();
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.ellipse(sx + fwd, sy + s * 0.52 - fLift, s * 0.12, s * 0.08, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(sx + back, sy + s * 0.52 - bLift, s * 0.12, s * 0.08, 0, 0, Math.PI * 2); ctx.fill();
  // the body (a tall narrow jersey, leaning into the run)
  const col = TEAM_COLOR[p.team];
  shade(sx + lean, sy, s * 0.32, lighten(col), darken(col));
  ctx.beginPath(); ctx.ellipse(sx + lean, sy, s * 0.22, s * 0.3, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = TEAM_TRIM[p.team]; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.ellipse(sx + lean, sy, s * 0.22, s * 0.3, 0, 0, Math.PI * 2); ctx.stroke();
  // the head (shaded, with a cap)
  shade(sx + lean * 1.5, sy - s * 0.42, s * 0.18, lighten(TEAM_SKIN[p.team]), darken(TEAM_SKIN[p.team]));
  ctx.beginPath(); ctx.arc(sx + lean * 1.5, sy - s * 0.42, s * 0.18, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = col;
  ctx.beginPath(); ctx.arc(sx + lean * 1.5, sy - s * 0.45, s * 0.18, Math.PI, 0); ctx.fill();
  ctx.fillRect(sx + lean * 1.5 - s * 0.18, sy - s * 0.47, s * 0.36, s * 0.06);
  // the FREE ARM (the back arm, no racket): it pumps opposite the legs
  // while he runs -- forward when the back leg is forward, back when the
  // front leg is forward -- and hangs at his side when he is standing.
  const armPump = p.moving ? -run * s * 0.3 : 0;
  const armLift = p.moving ? Math.max(0, Math.cos(p.runT)) * s * 0.12 : 0;
  const ax0 = sx + lean - fx * s * 0.14, ay0 = sy - s * 0.14;
  const ax1 = sx + lean - fx * s * 0.14 + armPump, ay1 = sy + s * 0.14 - armLift;
  ctx.strokeStyle = col; ctx.lineWidth = Math.max(3, s * 0.08);
  ctx.beginPath(); ctx.moveTo(ax0, ay0); ctx.lineTo(ax1, ay1); ctx.stroke();
  ctx.fillStyle = TEAM_SKIN[p.team];
  ctx.beginPath(); ctx.arc(ax1, ay1, s * 0.07, 0, Math.PI * 2); ctx.fill();
  // the RACKET. On a serve it swings OVERHAND: up above the head, then
  // down and forward over the top. Otherwise the usual side-arm swing:
  // it winds back behind him, sweeps across in a big arc, and the head
  // rotates through it -- not a nudge.
  // swing progress 0->1 over the swing, and the racket angle with it:
  // wound back (-70deg) -> through the ball (0deg) -> follow-through (+80deg)
  const swT = (p.kickT > 0) ? (0.45 - p.kickT) / 0.45 : -1;
  const swA = (swT >= 0) ? (-70 + swT * 150) * Math.PI / 180 : null;
  const armSwing = -run * s * 0.2;
  let rx, ry, headAng;
  if (sProg >= 0){
    // overhand: the racket rises high above the head, then sweeps down
    // and forward over the top (height peaks mid-serve, forward at the end)
    const h = s * 0.6 * Math.sin(sProg * Math.PI);
    const fwd = fx * s * (0.55 * sProg - 0.2);
    rx = sx + lean + fwd;
    ry = sy - s * 0.42 - h;
    headAng = fx * (1.0 - sProg * 1.6);
  } else if (swA !== null){
    // the racket sweeps around the shoulder on an arc
    const L = s * 0.62;
    rx = sx + lean + Math.cos(swA) * fx * L;
    ry = (sy - s * 0.08) + Math.sin(swA) * L * 0.7 + armSwing * 0.3;
    headAng = fx * swA;
  } else {
    // ready: held out to the side, bobbing a little as he runs
    rx = sx + lean + fx * s * 0.3;
    ry = sy - s * 0.05 + armSwing * 0.3;
    headAng = fx * 0.5;
  }
  ctx.strokeStyle = col; ctx.lineWidth = Math.max(3, s * 0.07);
  ctx.beginPath(); ctx.moveTo(sx + lean, sy - s * 0.08); ctx.lineTo(rx, ry); ctx.stroke();
  // the racket head (an oval with strings, rotating with the swing)
  const hx = rx + fx * s * 0.14, hy = ry - s * 0.08;
  ctx.strokeStyle = '#8d6e63'; ctx.lineWidth = 3;
  ctx.beginPath(); ctx.ellipse(hx, hy, s * 0.17, s * 0.21, headAng, 0, Math.PI * 2); ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 1;
  ctx.beginPath(); ctx.ellipse(hx, hy, s * 0.12, s * 0.15, headAng, 0, Math.PI * 2); ctx.stroke();
  // the P1 ring (you)
  if (p.team === HOME){
    ctx.strokeStyle = '#ffe14d'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(sx, sy + s * 0.52, s * 0.42, s * 0.16, 0, 0, Math.PI * 2); ctx.stroke();
  }
  // the server's ball (on the racket while waiting to serve)
  if (p.hasBall){
    const bx = sx + p.face * s * 0.3, by = sy - s * 0.35;
    shade(bx, by, s * 0.11, '#e6f542', '#9dbb1a');
    ctx.beginPath(); ctx.arc(bx, by, s * 0.11, 0, Math.PI * 2); ctx.fill();
  }
}

function drawBall(){
  const b = G.ball;
  if (!b || !b.live) return;
  const sc = courtScale();
  const sx = courtSX(b.x), sy = courtSY(b.y) - b.z * sc * 0.9;
  const shScale = Math.max(0.4, 1 - b.z / 220);
  // the shadow on the ground (shrinks as the ball rises)
  ctx.fillStyle = 'rgba(0,0,0,' + (0.35 * shScale).toFixed(2) + ')';
  ctx.beginPath(); ctx.ellipse(courtSX(b.x), courtSY(b.y), 9 * sc * shScale + 4, 4 * sc * shScale + 2, 0, 0, Math.PI * 2); ctx.fill();
  // the ball (shaded yellow-green with a white seam)
  const r = 7 * sc + 4;
  shade(sx, sy, r, '#e6f542', '#8aa812');
  ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(sx, sy, r * 0.62, 0.4, 2.4); ctx.stroke();
}

function draw(){
  ctx.clearRect(0, 0, W, H);
  drawCourt();
  // the far player first (so the near one draws over)
  const sorted = G.players.slice().sort(function(a, b){ return a.y - b.y; });
  sorted.forEach(drawPlayer);
  drawBall();
}
function frame(){
  if (G.started && !G.over) update(1 / 60);
  draw();
  requestAnimationFrame(frame);
}

// ---------- the scoreboard ----------
function updateSB(){
  document.getElementById('scYou').textContent = G.games[HOME];
  document.getElementById('scCom').textContent = G.games[AWAY];
  const sv = serverPlayer();
  const side = (G.serveSide === 'deuce') ? 'DEUCE COURT' : 'AD COURT';
  document.getElementById('cardName').textContent = sv.name;
  document.getElementById('cardSub').textContent =
    (G.server === HOME ? 'YOU SERVE' : 'COM SERVES') + ' • ' + side;
  document.getElementById('setPill').textContent =
    (G.tb ? 'TIEBREAK • ' : 'SET 1 • ') + G.games[HOME] + '-' + G.games[AWAY] + '  •  ' + scoreText();
}
let msgTimer = null;
function showMsg(title, sub){
  const m = document.getElementById('msg');
  if (!title){ m.style.opacity = '0'; return; }
  m.innerHTML = title + (sub ? '<small>' + sub + '</small>' : '');
  m.style.opacity = '1';
  if (msgTimer) clearTimeout(msgTimer);
  msgTimer = setTimeout(function(){ m.style.opacity = '0'; }, 1800);
}

// ---------- the game flow ----------
function startGame(){
  G.started = true; G.over = false;
  G.pts = [0, 0]; G.games = [0, 0]; G.tbPts = [0, 0]; G.tb = false;
  G.server = HOME; G.pointNum = 0; G.tbPointNum = 0; G.faults = 0;
  G.ball = { x: CTR_X, y: CL + 35, z: 30, vx: 0, vy: 0, vz: 0, live: false, kickT: 0 };
  makePlayers();
  updateServeSide();
  startPoint();
  document.getElementById('overlay').classList.add('hidden');
  document.getElementById('startBtn').textContent = 'START GAME';
  showMsg('PARK TENNIS', 'You serve first — HIT to serve');
  if (pvpIsOn() && G.pvp.role === 'host' && !G.pvp.syncStart){
    // Post the initial state so the guest's game starts too.
    // (A rejoining host does NOT post -- the room already has the game.)
    pvpPostState(null);
  }
}

// ---------- the input ----------
const PS = {
  joy: { x: 0, y: 0 },
};
(function(){
  const joy = document.getElementById('joy');
  const stick = document.getElementById('stick');
  let jid = null;
  function setJoy(e){
    const r = joy.getBoundingClientRect();
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    let dx = (e.clientX - cx) / (r.width / 2), dy = (e.clientY - cy) / (r.height / 2);
    const m = Math.hypot(dx, dy);
    if (m > 1){ dx /= m; dy /= m; }
    PS.joy.x = dx; PS.joy.y = dy;
    stick.style.left = (44 + dx * 34) + 'px';
    stick.style.top = (44 + dy * 34) + 'px';
  }
  joy.addEventListener('pointerdown', function(e){ jid = e.pointerId; joy.setPointerCapture(jid); setJoy(e); });
  joy.addEventListener('pointermove', function(e){ if (e.pointerId === jid) setJoy(e); });
  function endJoy(e){ if (e.pointerId === jid){ jid = null; PS.joy.x = 0; PS.joy.y = 0; stick.style.left = '44px'; stick.style.top = '44px'; } }
  joy.addEventListener('pointerup', endJoy);
  joy.addEventListener('pointercancel', endJoy);
  document.getElementById('btnHit').addEventListener('pointerdown', function(){
    if (!G.started || G.over) return;
    if (G.phase === 'serve' && G.server === G.myTeam) serve(pvpMe());
    else hit(pvpMe(), 'hit');
  });
  document.getElementById('btnLob').addEventListener('pointerdown', function(){
    if (!G.started || G.over) return;
    hit(pvpMe(), 'lob');
  });
  document.getElementById('btnDrop').addEventListener('pointerdown', function(){
    if (!G.started || G.over) return;
    hit(pvpMe(), 'drop');
  });
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
  const diffRow = document.getElementById('diffRow');
  DIFFS.forEach(function(d, i){
    const b = document.createElement('button');
    b.textContent = d.n;
    if (i === diffIdx) b.classList.add('sel');
    b.addEventListener('pointerdown', function(){
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
    startGame();
  });
  document.getElementById('leaveBtn').addEventListener('pointerdown', function(){
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
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
    pvpPost('/create', { player_id: who.id, player_name: who.name, game: 'tennis' }).then(function(room){
      if (!room || !room.code){ pvpSetStatus('Could not create a room — check your connection and try again.'); return; }
      G.myTeam = HOME; // host is DANTE (bottom, serves first)
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
      G.myTeam = AWAY; // guest is CODY (top)
      G.pvp = { code: room.code, role: 'guest', oppName: room.host_name || 'Opponent', seq: 0, oppSeq: -1, pollTimer: null, posT: 0 };
      pvpSetStatus('Joined! You are CODY (top).');
      pvpSetRoomLbl('CODE: ' + room.code + ' — vs ' + G.pvp.oppName);
      pvpStartPoll();
      showMsg('WAITING FOR HOST', 'The host starts the game.');
    });
  });
})();

// ---------- the hooks (for the smoke suite) ----------
// change the level: the ball speed (via hitBall) and COM's feet follow it
function setDiff(i){
  diffIdx = i;
  G.players.forEach(function(p){ if (p.team === AWAY) p.speed = 250 * DIFFS[diffIdx].cpu; });
}
window.__PT = {
  G: G, HOME: HOME, AWAY: AWAY, CW: CW, CL: CL, NET_Y: NET_Y,
  SING_L: SING_L, SING_R: SING_R, SERV_T: SERV_T, SERV_B: SERV_B, CTR_X: CTR_X,
  startGame: startGame, startPoint: startPoint, update: update,
  serve: serve, hit: hit, hitBall: hitBall, pointTo: pointTo, gameTo: gameTo,
  setDiff: setDiff,
  pauseThen: pauseThen, setupSecondServe: setupSecondServe,
  fault: fault, letServe: letServe, serveBox: serveBox, serveSpot: serveSpot,
  predictLanding: predictLanding, aiPlayer: aiPlayer, makePlayers: makePlayers,
  scoreText: scoreText, updateSB: updateSB, frame: frame,
  joy: PS.joy, draw: draw,
  pvpPlayer: pvpPlayer, pvpIsOn: pvpIsOn, pvpMe: pvpMe, pvpOpp: pvpOpp,
  pvpReceiveHit: pvpReceiveHit, pvpReceiveServe: pvpReceiveServe,
  pvpApplyState: pvpApplyState, pvpPostState: pvpPostState,
  pvpStartPoll: pvpStartPoll, pvpStopPoll: pvpStopPoll, pvpPollOnce: pvpPollOnce,
};
G.ball = { x: CTR_X, y: CL + 35, z: 30, vx: 0, vy: 0, vz: 0, live: false, kickT: 0 };
makePlayers();
updateSB();
requestAnimationFrame(frame);
</script>
</body>
</html>
`;
