// PARK_SOCCER_HTML
export const SOCCER_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<title>Park Soccer '98</title>
<style>
  html,body{margin:0;padding:0;height:100%;background:#0a1f0a;overflow:hidden;font-family:Arial,Helvetica,sans-serif;-webkit-user-select:none;user-select:none;-webkit-tap-highlight-color:transparent}
  #wrap{position:fixed;inset:0}
  canvas{display:block;width:100%;height:100%;touch-action:none}
  #scorebar{position:absolute;left:0;right:0;bottom:0;height:64px;background:linear-gradient(#5b2a86,#3a1a5e);border-top:3px solid #f5c518;color:#fff;z-index:6;display:flex;align-items:center;gap:10px;padding:0 10px;font-weight:bold}
  #scorebar .sc{font-size:26px;white-space:nowrap}
  #scorebar .sc b{color:#f5c518}
  #scorebar .mid{flex:1;text-align:center;font-size:13px;line-height:1.3}
  #scorebar .mid .pw{color:#ffd54f}
  #scorebar .half{font-size:13px;white-space:nowrap;background:#fff;color:#3a1a5e;border-radius:12px;padding:4px 10px}
  #stick{position:absolute;left:18px;bottom:84px;width:120px;height:120px;border-radius:50%;background:rgba(255,255,255,.14);border:2px solid rgba(255,255,255,.5);z-index:7;touch-action:none}
  #stickKnob{position:absolute;left:35px;top:35px;width:50px;height:50px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#ffe082,#f5c518 60%,#c49000);box-shadow:0 4px 8px rgba(0,0,0,.5)}
  .abtn{position:absolute;z-index:7;border:3px solid #fff;border-radius:50%;font-weight:bold;color:#fff;touch-action:none;box-shadow:0 4px 8px rgba(0,0,0,.5)}
  #btnShoot{right:18px;bottom:88px;width:84px;height:84px;background:radial-gradient(circle at 35% 30%,#ef5350,#c62828 65%);font-size:15px}
  #btnSwitch{right:112px;bottom:158px;width:66px;height:66px;background:radial-gradient(circle at 35% 30%,#66bb6a,#2e7d32 65%);font-size:12px}
  #btnTurbo{right:18px;bottom:182px;width:66px;height:66px;background:radial-gradient(circle at 35% 30%,#ffb74d,#e65100 65%);font-size:12px}
  #stamBar{position:absolute;right:18px;bottom:256px;width:66px;height:9px;background:rgba(0,0,0,.55);border:2px solid #fff;border-radius:5px;z-index:7;overflow:hidden}
  #stamFill{height:100%;width:100%;background:linear-gradient(90deg,#ffea00,#ff9800)}
  #btnPass{right:112px;bottom:76px;width:66px;height:66px;background:radial-gradient(circle at 35% 30%,#42a5f5,#1565c0 65%);font-size:14px}
  #msg{position:absolute;left:50%;top:16%;transform:translateX(-50%);z-index:8;text-align:center;pointer-events:none}
  #msg .t{font-size:40px;font-weight:bold;color:#f5c518;text-shadow:3px 3px 0 #000}
  #msg .s{font-size:16px;font-weight:bold;color:#fff;text-shadow:2px 2px 0 #000;margin-top:4px}
  #menuBtn{position:absolute;left:50%;transform:translateX(-50%);top:8px;z-index:8;pointer-events:auto;background:rgba(0,0,0,.6);color:#fff;border:2px solid #fff;border-radius:10px;padding:8px 14px;font-weight:bold}
  #overlay{position:absolute;inset:0;background:rgba(0,0,0,.55);display:flex;flex-direction:column;align-items:center;justify-content:center;z-index:10;color:#fff;text-align:center;padding:16px}
  #overlay h1{margin:0 0 4px;font-size:34px;letter-spacing:2px;color:#f5c518;text-shadow:2px 2px 0 #000}
  #overlay p{margin:4px 0 12px;font-size:15px;max-width:440px;line-height:1.45}
  .diff{display:flex;gap:8px;flex-wrap:wrap;justify-content:center;margin-bottom:14px}
  .diff button{pointer-events:auto;background:#222;color:#fff;border:2px solid #888;border-radius:10px;padding:10px 12px;font-weight:bold;font-size:14px}
  .diff button.sel{background:#f5c518;color:#111;border-color:#fff}
  #startBtn{pointer-events:auto;background:#2e7d32;color:#fff;border:3px solid #fff;border-radius:14px;padding:14px 34px;font-size:20px;font-weight:bold;letter-spacing:1px}
  #leaveBtn{pointer-events:auto;background:#c62828;color:#fff;border:3px solid #fff;border-radius:14px;padding:14px 34px;font-size:20px;font-weight:bold;letter-spacing:1px;margin-top:10px}
  .hidden{display:none !important}
</style>
</head>
<body>
<div id="wrap">
  <canvas id="cv"></canvas>
  <button id="menuBtn">MENU</button>
  <div id="msg" class="hidden"><div class="t"></div><div class="s"></div></div>
  <div id="scorebar">
    <div class="sc"><b>BOM</b> <span id="scH">0</span> - <span id="scA">0</span> <b>MEL</b></div>
    <div class="mid"><div id="sbCard">KICK OFF</div><div class="pw" id="sbPow"></div></div>
    <div class="half" id="sbHalf">1ST HALF</div>
    <div class="sc" id="sbClock">1:00</div>
  </div>
  <div id="stick"><div id="stickKnob"></div></div>
  <div id="stamBar"><div id="stamFill"></div></div>
  <button class="abtn" id="btnTurbo">TURBO</button>
  <button class="abtn" id="btnSwitch">SWITCH</button>
  <button class="abtn" id="btnShoot">SHOOT</button>
  <button class="abtn" id="btnPass">PASS</button>
  <div id="overlay">
    <h1>PARK SOCCER</h1>
    <p>5 on 5 in the park, just like the 1998 classic. Move with the stick, SHOOT at the goal, PASS to a teammate. Grab the star for a POWER SHOT. Most goals wins.</p>
    <div class="diff" id="diffRow"></div>
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
    <p style="font-size:13px;color:#ccc">You are the Bombers (yellow). The P1 ring is the kid you control — it switches to the Bomber nearest the ball. Your goalie stays home. First to the final whistle wins.</p>
  </div>
</div>
<script>
"use strict";
/* ================= BACKYARD SOCCER '98 (built fresh from the screenshots) =================
   A brand-new game, built from the 1998 screenshots -- a small backyard field,
   cartoon kids, goals at each end, a purple score bar with the score, the
   player card, the power-up and the half. The kids are drawn with 3D hues
   and shadows: shaded-sphere heads, gradient jerseys, drop shadows, a shaded
   ball. 5 on 5 (4 field + 1 goalie each side), you vs the CPU.
   Views: one top-down field view (like the screenshots). */

/* ---------- the field ---------- */
const FW = 1500, FH = 540;         // the backyard field -- LONG, the camera scrolls it
const GOAL_Y0 = 200, GOAL_Y1 = 340; // the goal mouth (140 tall, centred)
const GOAL_DEPTH = 26;             // how deep the goal is
const WALL = 14;                   // the fence thickness
const HALF_LEN = 60;               // seconds per half
const HOME = 0, AWAY = 1;
const TEAM_NAME = ['Bombers', 'Melonheads'];
const TEAM_SHORT = ['BOM', 'MEL'];
const TEAM_COLOR = ['#ffeb3b', '#222222'];   // yellow vs black kits
const TEAM_TRIM = ['#c49000', '#ffffff'];
const TEAM_SKIN = ['#f1c27d', '#8d5524'];

/* ---------- the rosters (names + traits from the '98 screenshots) ---------- */
const ROSTER = [
  [ // Bombers (HOME, yellow) -- you
    { n: 'REESE', r: 'GK', t: 'HAS ALLERGIES' },
    { n: 'BIG AL', r: 'DF', t: 'BIG BOOTER' },
    { n: 'KIMMY', r: 'LIKES NOUGAT', t: 'LIKES NOUGAT' },
    { n: 'LIL RON', r: 'MF', t: 'HAS ALLERGIES' },
    { n: 'DANTE', r: 'FW', t: 'BIG BOOTER' },
  ],
  [ // Melonheads (AWAY, black) -- CPU
    { n: 'SALLY', r: 'GK', t: 'I GOAL TODAY' },
    { n: 'RONNY', r: 'DF', t: 'HAS SCORED 6 GOALS TODAY' },
    { n: 'WORTHINGTON', r: 'MF', t: 'HAS ALLERGIES' },
    { n: 'DEL VECCHIO', r: 'MF', t: 'BIG BOOTER' },
    { n: 'CODY JONES', r: 'FW', t: 'I GOAL TODAY' },
  ],
];
const DIFFS = [
  { n: 'ROOKIE', cpu: 0.70, gk: 0.75 },
  { n: 'AMATEUR', cpu: 0.85, gk: 0.90 },
  { n: 'PRO', cpu: 1.00, gk: 1.00 },
  { n: 'ALL-STAR', cpu: 1.15, gk: 1.10 },
  { n: 'LEGEND', cpu: 1.30, gk: 1.20 },
];
let diffIdx = 2;

/* ---------- state ---------- */
const G = {
  started: false, over: false, half: 1, clock: HALF_LEN,
  score: [0, 0], players: [], ball: null, carrier: null,
  ctrl: null,           // the player you control (P1)
  attackDir: [1, -1],   // HOME attacks right (+1), AWAY attacks left (-1)
  power: null,          // the star on the field {x,y,t}
  powerT: 18,           // seconds until the next star spawns
  powered: null,        // the player holding a power-up
  manualT: 0,          // seconds left that a manual SWITCH pick sticks
  stam: 100,           // turbo stamina 0-100 (drains while you sprint, refills when you don't)
  turbo: false,        // the TURBO button is held right now
  stealCd: 0,          // seconds until STEAL can be pressed again
  msgT: 0, kickoffT: 0, stealT: 0,
  myTeam: HOME, // PvC: you are always HOME (Bombers). PvP: HOME if host, AWAY if guest.
  pvp: null,    // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT}
  lastCarrier: null, // the carrier we last posted (so we only post changes)
};

/* ---------- PvP (park games) ---------- */
// Same room system as Baseball/Tennis/1-on-1 PvP (backend: /api/park_pvp/rooms/*).
// Soccer is 5v5 and real-time, so the sync is event-based: the human's
// kicks (shoot/pass), steals, and carrier changes are posted as they
// happen, and the opponent applies the same call, so the ball and the
// score match on both phones. The AI runs the other 8 players locally
// on both sides (they may drift slightly -- the ball is the authority).
// Each human controls their own active player; their position is posted
// ~4x a second and interpolated on the other side. Identity comes from
// the app as window.PARK_PVP_PLAYER = {id, name}.
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
function pvpMe(){ return G.ctrl; }
function pvpOppCtrl(){
  // The opponent's active player (the one the other human controls).
  // It is the opponent-team player nearest the ball on their side.
  var best = null, bestD = Infinity;
  teamPlayers(1 - G.myTeam).forEach(function(p){
    var d = Math.hypot(p.x - G.ball.x, p.y - G.ball.y);
    if (d < bestD){ bestD = d; best = p; }
  });
  return best;
}
function pvpPostState(patch){
  // Post the shared state to the room. The patch carries the new event
  // (kick / steal / carrier / goal / kickoff). The full score, carrier,
  // and my controlled player's position ride along so the other phone
  // resyncs and sees where I am.
  if (!pvpIsOn()) return Promise.resolve(null);
  if (!patch && G.pvp.posting) return Promise.resolve(null);
  G.pvp.seq += 1;
  var me = G.ctrl;
  var st = {
    seq: G.pvp.seq,
    score: G.score.slice(), half: G.half, clock: G.clock,
    carrier: G.carrier ? { team: G.carrier.team, idx: G.carrier.idx } : null,
    me: me ? { team: me.team, idx: me.idx, x: me.x, y: me.y } : null,
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
  if (typeof st.half === 'number') G.half = st.half;
  if (typeof st.clock === 'number') G.clock = st.clock;
  updateSB();
  if (fresh) return; // skip events on the first state I apply
  // The opponent's controlled player: glide toward their posted spot.
  if (st.me && typeof st.me.x === 'number' && typeof st.me.y === 'number'){
    var op = null;
    teamPlayers(1 - G.myTeam).forEach(function(p){
      if (p.idx === st.me.idx) op = p;
    });
    if (op){ op.tx = st.me.x; op.ty = st.me.y; }
  }
  // The carrier: trust the room (the ball is the authority).
  if (st.carrier && typeof st.carrier.team === 'number'){
    var c = null;
    teamPlayers(st.carrier.team).forEach(function(p){
      if (p.idx === st.carrier.idx) c = p;
    });
    if (c && G.carrier !== c){
      if (G.carrier) G.carrier.hasBall = false;
      c.hasBall = true; G.carrier = c;
      G.ball.x = c.x; G.ball.y = c.y;
      setControl();
    }
  } else if (st.carrier === null && G.carrier){
    G.carrier.hasBall = false; G.carrier = null;
  }
  if (st.ev) pvpReceiveEv(st.ev);
}
function pvpReceiveEv(ev){
  // Apply one event posted by the opponent. Only events from the OTHER
  // team are applied (my own events are already applied locally).
  if (!ev || typeof ev.team !== 'number' || ev.team === G.myTeam) return;
  var p = null;
  teamPlayers(ev.team).forEach(function(q){ if (q.idx === ev.idx) p = q; });
  if (!p) return;
  if (ev.k === 'kick'){
    // They kicked the ball: same target, same power, same speed, so the
    // ball flies the same way on both phones.
    kickBall(p, ev.tx, ev.ty, !!ev.power, ev.speed || 0, ev.kickT);
    p.kickT = 0.35;
  } else if (ev.k === 'steal'){
    // They took the ball from my carrier.
    var c = G.carrier;
    if (c && c.team !== p.team){
      c.hasBall = false;
      p.hasBall = true; G.carrier = p;
      G.ball.x = p.x; G.ball.y = p.y; G.ball.vx = 0; G.ball.vy = 0;
      setControl();
      showMsg('STEAL!', p.name + ' takes it!');
    }
  } else if (ev.k === 'goal'){
    // They scored. The score is already resynced from the state above,
    // so do NOT score again here -- just run the kickoff for the
    // conceding team (same 1600ms beat as a local goal).
    G.ball.live = false;
    setTimeout(function(){
      if (G.over) return;
      kickoff(1 - ev.team);
      showMsg('KICK OFF', TEAM_NAME[1 - ev.team] + ' to restart');
    }, 1600);
  } else if (ev.k === 'kickoff'){
    kickoff(ev.team);
  }
}
const cv = document.getElementById('cv');
const ctx = cv.getContext('2d');
let W = 0, H = 0;
function fitCanvas(){
  const r = cv.parentElement.getBoundingClientRect();
  W = r.width; H = r.height;
  cv.width = Math.round(W * (window.devicePixelRatio || 1));
  cv.height = Math.round(H * (window.devicePixelRatio || 1));
  ctx.setTransform(cv.width / W, 0, 0, cv.height / H, 0, 0);
}
window.addEventListener('resize', fitCanvas); fitCanvas();

/* ---------- the camera (scrolls goal to goal, following the ball) ---------- */
const SB_H = 64; // the score bar height
let camX = 0;    // the field x at the left edge of the screen
function fieldScale(){ return (H - 46 - SB_H - 10) / FH; }
function viewW(){ return (W - 20) / fieldScale(); } // how much field fits on screen
function fieldSX(x){ return 10 + (x - camX) * fieldScale(); }
function fieldSY(y){ return 46 + y * fieldScale(); }
function updateCamera(dt){
  // centre the view on the ball, clamped so you never see past either goal
  const vw = viewW();
  const target = Math.max(0, Math.min(FW - vw, G.ball.x - vw / 2));
  camX += (target - camX) * Math.min(1, dt * 4); // smooth pan, no jerking
  if (Math.abs(target - camX) < 0.5) camX = target;
}

/* ---------- players ---------- */
function homePos(i, dir){
  // formation spots (x from your own goal outward), flipped by attack dir
  const spots = [
    { x: 52, y: 270 },            // GK (stays home by his goal)
    { x: Math.round(FW * 0.28), y: 150 },  // DF
    { x: Math.round(FW * 0.42), y: 380 },  // MF
    { x: Math.round(FW * 0.48), y: 160 },  // MF
    { x: Math.round(FW * 0.68), y: 270 },  // FW
  ];
  const s = spots[i];
  const x = dir > 0 ? s.x : FW - s.x;
  return { x: x, y: s.y };
}
function makePlayers(){
  G.players = [];
  for (let t = 0; t < 2; t++){
    const dir = G.attackDir[t];
    for (let i = 0; i < 5; i++){
      const p = homePos(i, dir);
      G.players.push({
        team: t, idx: i, role: ROSTER[t][i].r, name: ROSTER[t][i].n, trait: ROSTER[t][i].t,
        x: p.x, y: p.y, vx: 0, vy: 0, hx: p.x, hy: p.y,
        speed: (ROSTER[t][i].r === 'GK' ? 150 : 165) * (t === AWAY ? DIFFS[diffIdx].cpu : 1),
        face: dir, runT: 0, moving: false, hasBall: false,
      });
    }
  }
}
function teamPlayers(t){ return G.players.filter(function(p){ return p.team === t; }); }
function goalie(t){ return G.players.find(function(p){ return p.team === t && p.role === 'GK'; }); }
function goalX(t){
  // the x of the goal a team DEFENDS (their own goal line)
  return G.attackDir[t] > 0 ? 0 : FW;
}
function attackGoalX(t){
  // the x of the goal a team ATTACKS
  return G.attackDir[t] > 0 ? FW : 0;
}

/* ---------- kickoff ---------- */
function kickoff(kickTeam){
  makePlayers();
  G.ball = { x: FW / 2, y: FH / 2, vx: 0, vy: 0, r: 11, live: true };
  G.carrier = null; G.powered = null; G.power = null; G.powerT = 18; G.stealT = 0;
  // the kicking team puts a forward on the ball
  const fw = teamPlayers(kickTeam).find(function(p){ return p.role === 'FW'; });
  fw.x = FW / 2 - (kickTeam === HOME ? 24 : -24); fw.y = FH / 2;
  G.carrier = fw; fw.hasBall = true;
  G.ball.x = fw.x; G.ball.y = fw.y;
  setControl();
  camX = Math.max(0, Math.min(FW - viewW(), G.ball.x - viewW() / 2));
  G.kickoffT = 0.8;
}
function setControl(){
  // you control the player from YOUR team nearest the ball (P1) --
  // goalie included now. In PvC your team is HOME (Bombers); in PvP
  // the guest controls the Melonheads (AWAY).
  let best = null, bestD = Infinity;
  teamPlayers(G.myTeam).forEach(function(p){
    const d = Math.hypot(p.x - G.ball.x, p.y - G.ball.y);
    if (d < bestD){ bestD = d; best = p; }
  });
  G.ctrl = best;
}
function switchPlayer(){
  // cycle through YOUR team's players nearest the ball (goalie included) --
  // each tap of SWITCH moves the P1 ring to the next one
  const near = teamPlayers(G.myTeam).slice().sort(function(a, b){
    return Math.hypot(a.x - G.ball.x, a.y - G.ball.y) - Math.hypot(b.x - G.ball.x, b.y - G.ball.y);
  });
  if (!near.length) return;
  let i = near.indexOf(G.ctrl);
  i = (i + 1) % near.length;
  G.ctrl = near[i];
  G.manualT = 3; // your pick sticks for 3 seconds before auto-switch resumes
}

/* ---------- messages + scoreboard ---------- */
function showMsg(t, s){
  const m = document.getElementById('msg');
  m.querySelector('.t').textContent = t;
  m.querySelector('.s').textContent = s || '';
  m.classList.remove('hidden');
  G.msgT = 0;
}
function clearMsg(){ document.getElementById('msg').classList.add('hidden'); }
function updateSB(){
  document.getElementById('scH').textContent = G.score[HOME];
  document.getElementById('scA').textContent = G.score[AWAY];
  document.getElementById('sbHalf').textContent = G.half === 1 ? '1ST HALF' : (G.over ? 'FULL TIME' : '2ND HALF');
  const c = Math.max(0, Math.ceil(G.clock));
  document.getElementById('sbClock').textContent = Math.floor(c / 60) + ':' + String(c % 60).padStart(2, '0');
  const cpl = G.carrier;
  document.getElementById('sbCard').textContent = cpl
    ? (cpl.name + ' - ' + cpl.role + '  •  ' + cpl.trait)
    : 'LOOSE BALL';
  document.getElementById('stamFill').style.width = Math.round(G.stam) + '%';
  // the PASS button turns into STEAL when the opponent has the ball
  document.getElementById('btnPass').textContent = (G.carrier && G.carrier.team === AWAY) ? 'STEAL' : 'PASS';
  document.getElementById('sbPow').textContent = G.powered
    ? ('POWER-UP ON THE BALL: ' + G.powered.name + ' HAS A POWER SHOT!')
    : (G.power ? 'POWER-UP ON THE FIELD — GRAB THE STAR!' : '');
}

/* ---------- start / half / full time ---------- */
function startGame(){
  G.started = true; G.over = false; G.half = 1; G.clock = HALF_LEN;
  G.score = [0, 0]; G.attackDir = [1, -1];
  document.getElementById('overlay').classList.add('hidden');
  kickoff(HOME);
  showMsg('KICK OFF!', 'Bombers to start — good luck!');
  updateSB();
  if (pvpIsOn() && G.pvp.role === 'host' && !G.pvp.syncStart){
    // Post the initial state so the guest's game starts too.
    // (A rejoining host does NOT post -- the room already has the game.)
    pvpPostState(null);
  }
}
function endHalf(){
  if (G.half === 1){
    G.half = 2; G.clock = HALF_LEN;
    G.attackDir = [-1, 1]; // swap ends, like real soccer
    showMsg('HALF TIME', 'Bombers ' + G.score[HOME] + ' - ' + G.score[AWAY] + ' Melonheads — ends swapped!');
    kickoff(AWAY);
  } else {
    G.over = true;
    const w = G.score[HOME] > G.score[AWAY] ? 'YOU WIN!' : (G.score[HOME] < G.score[AWAY] ? 'MELONHEADS WIN' : 'DRAW!');
    const s = 'Bombers ' + G.score[HOME] + ' - ' + G.score[AWAY] + ' Melonheads';
    showMsg(w, s + ' — tap MENU for a rematch');
    document.getElementById('startBtn').textContent = 'REMATCH';
    document.getElementById('overlay').classList.remove('hidden');
  }
  updateSB();
}

/* ---------- the ball ---------- */
function kickBall(from, tx, ty, power, speed, kickT){
  const dx = tx - from.x, dy = ty - from.y;
  const d = Math.hypot(dx, dy) || 1;
  const sp = speed || (power ? 640 : 470);
  G.ball.vx = (dx / d) * sp; G.ball.vy = (dy / d) * sp;
  if (from.hasBall){ from.hasBall = false; G.carrier = null; }
  G.ball.live = true;
  G.ball.kickT = (kickT !== undefined) ? kickT : 0.35; // nobody can pick it up until it has travelled clear
}
function shoot(p){
  p.kickT = 0.35; // the kicking leg swings out
  const gx = attackGoalX(p.team);
  // aim at the far corner of the goal, with a little spread
  const gy = FH / 2 + (Math.random() < 0.5 ? -1 : 1) * (GOAL_Y1 - GOAL_Y0) * 0.28;
  const pow = G.powered === p;
  kickBall(p, gx, gy, pow);
  if (pow){ G.powered = null; showMsg('POWER SHOT!', p.name + ' unleashes it!'); }
  // PvP: I shot — tell the other phone the exact target and power, so
  // their ball flies the same way.
  if (pvpIsOn() && p.team === G.myTeam && p === G.ctrl){
    pvpPostState({ ev: { k: 'kick', team: p.team, idx: p.idx, tx: gx, ty: gy, power: pow, speed: 0, kickT: 0.35 } });
  }
}
function steal(p){
  // the STEAL tackle: when the opponent has the ball, take it if you are
  // close enough -- otherwise lunge at them to close the distance.
  const c = G.carrier;
  if (!c || c.team === p.team) return;
  const d = Math.hypot(c.x - p.x, c.y - p.y);
  if (d < 70){
    c.hasBall = false;
    p.hasBall = true; G.carrier = p;
    G.ball.x = p.x; G.ball.y = p.y; G.ball.vx = 0; G.ball.vy = 0;
    G.stealT = 0;
    p.kickT = 0.35; // the tackling leg swings out
    setControl();
    showMsg('STEAL!', p.name + ' takes it!');
    // PvP: I stole it — tell the other phone the ball is mine now.
    if (pvpIsOn() && p.team === G.myTeam && p === G.ctrl){
      pvpPostState({ ev: { k: 'steal', team: p.team, idx: p.idx } });
    }
  } else {
    const dx = c.x - p.x, dy = c.y - p.y;
    const dd = Math.hypot(dx, dy) || 1;
    p.x += (dx / dd) * 26; p.y += (dy / dd) * 26; // lunge at them
    clampField(p);
  }
  G.stealCd = 0.8; // you cannot spam it
}
function pass(p){
  p.kickT = 0.35; // the kicking leg swings out
  // pass to the teammate most in the direction you are facing (or nearest)
  const mates = teamPlayers(p.team).filter(function(m){ return m !== p && m.role !== 'GK'; });
  if (!mates.length) return;
  let best = null, bestS = -Infinity;
  mates.forEach(function(m){
    const dx = m.x - p.x, dy = m.y - p.y;
    const d = Math.hypot(dx, dy) || 1;
    const align = (dx * p.face + dy * 0) / d; // facing is mostly horizontal
    const s = align * 2 - d / 400;
    if (s > bestS){ bestS = s; best = m; }
  });
  if (best){
    kickBall(p, best.x, best.y, false);
    // PvP: I passed — tell the other phone the exact target, so their
    // ball flies the same way.
    if (pvpIsOn() && p.team === G.myTeam && p === G.ctrl){
      pvpPostState({ ev: { k: 'kick', team: p.team, idx: p.idx, tx: best.x, ty: best.y, power: false, speed: 0, kickT: 0.35 } });
    }
  }
}
function nearestOpp(p){
  let best = null, bestD = Infinity;
  teamPlayers(1 - p.team).forEach(function(o){
    const d = Math.hypot(o.x - p.x, o.y - p.y);
    if (d < bestD){ bestD = d; best = o; }
  });
  return { p: best, d: bestD };
}

/* ---------- movement ---------- */
function moveToward(p, tx, ty, dt, sp){
  const dx = tx - p.x, dy = ty - p.y;
  const d = Math.hypot(dx, dy);
  if (d < 4){ p.vx = 0; p.vy = 0; p.moving = false; return; }
  const s = Math.min(sp, d / Math.max(dt, 0.001) * 0.9);
  p.vx = (dx / d) * s; p.vy = (dy / d) * s;
  p.x += p.vx * dt; p.y += p.vy * dt;
  p.face = p.vx >= 0 ? 1 : -1;
  p.moving = true; p.runT += dt * 10;
}
function clampField(p){
  p.x = Math.max(WALL + 14, Math.min(FW - WALL - 14, p.x));
  p.y = Math.max(WALL + 14, Math.min(FH - WALL - 14, p.y));
}

/* ---------- the AI ---------- */
function aiPlayer(p, dt){
  const ball = G.ball;
  const myGoal = goalX(p.team), atkGoal = attackGoalX(p.team);
  const diff = DIFFS[diffIdx];
  if (p.role === 'GK'){
    // the goalie with the ball distributes it: hold a beat, then pass out
    if (G.carrier === p){
      p.holdT = (p.holdT || 0) + dt;
      if (p.holdT > 1.0){
        p.holdT = 0;
        // SAFE distribution: a short soft pass to the NEAREST outfield teammate
        // (never a long bomb upfield -- that sails past everyone and into a goal)
        const mates = teamPlayers(p.team).filter(function(m){ return m.role !== 'GK'; });
        let best = mates[0], bestD = Infinity;
        mates.forEach(function(m){
          const d = Math.hypot(m.x - p.x, m.y - p.y);
          if (d < bestD){ bestD = d; best = m; }
        });
        if (best) kickBall(p, best.x, best.y, false, 300, 0.35);
      }
      return;
    }
    p.holdT = 0;
    // the goalie stays on his line and shuffles with the ball
    const gx = myGoal === 0 ? 34 : FW - 34;
    const ty = Math.max(GOAL_Y0 + 20, Math.min(GOAL_Y1 - 20, ball.y * 0.3 + FH / 2 * 0.7));
    const bd = Math.hypot(ball.x - p.x, ball.y - p.y);
    if (G.carrier && G.carrier.team !== p.team && bd < 90){
      moveToward(p, ball.x, ball.y, dt, p.speed * 1.05); // rush the shooter
    } else {
      moveToward(p, gx, ty, dt, p.speed * 0.5);
    }
    return;
  }
  if (G.carrier === p){
    // CPU with the ball: dribble at the goal, shoot when close
    const gd = Math.hypot(atkGoal - p.x, FH / 2 - p.y);
    if (gd < 330){ shoot(p); return; }
    moveToward(p, atkGoal, FH / 2 + (p.y - FH / 2) * 0.4, dt, p.speed);
    return;
  }
  if (G.carrier && G.carrier.team === p.team){
    // teammate has it: spread out upfield (or come short for a pass)
    const up = p.hx + (atkGoal - FW / 2) * 0.45;
    moveToward(p, up, p.hy, dt, p.speed * 0.7);
    return;
  }
  if (!G.carrier){
    // loose ball: nearest chases it
    const mates = teamPlayers(p.team).filter(function(m){ return m.role !== 'GK'; });
    let nearest = mates[0], nd = Infinity;
    mates.forEach(function(m){ const d = Math.hypot(m.x - ball.x, m.y - ball.y); if (d < nd){ nd = d; nearest = m; } });
    if (nearest === p){ moveToward(p, ball.x, ball.y, dt, p.speed); return; }
    moveToward(p, p.hx, p.hy, dt, p.speed * 0.6);
    return;
  }
  // the other team has it: nearest presses, the rest hold their shape
  const mates = teamPlayers(p.team).filter(function(m){ return m.role !== 'GK'; });
  let nearest = mates[0], nd = Infinity;
  mates.forEach(function(m){ const d = Math.hypot(m.x - ball.x, m.y - ball.y); if (d < nd){ nd = d; nearest = m; } });
  if (nearest === p){ moveToward(p, ball.x, ball.y, dt, p.speed * 0.94); return; }
  const gx = (p.hx + ball.x) / 2;
  moveToward(p, gx, p.hy, dt, p.speed * 0.6);
}

/* ---------- possession + stealing ---------- */
function updatePossession(dt){
  const ball = G.ball;
  if (!ball.live) return;
  if (ball.kickT > 0){ ball.kickT -= dt; return; }
  if (G.carrier){
    const c = G.carrier;
    ball.x = c.x + c.face * 16; ball.y = c.y + 12;
    // never let a carried ball sit past the goal line (a goalie facing his
    // own line would own-goal the instant he releases it)
    ball.x = Math.max(WALL + ball.r, Math.min(FW - WALL - ball.r, ball.x));
    ball.y = Math.max(WALL + ball.r, Math.min(FH - WALL - ball.r, ball.y));
    ball.vx = 0; ball.vy = 0;
    // an opponent close on the carrier can steal it (a short contest)
    const o = nearestOpp(c);
    if (o.p && o.d < 30){
      G.stealT += dt;
      if (G.stealT > 0.9){
        c.hasBall = false; G.carrier = null; G.stealT = 0;
        o.p.hasBall = true; G.carrier = o.p;
        ball.x = o.p.x; ball.y = o.p.y;
        setControl();
      }
    } else G.stealT = 0;
    // the power-up star: the carrier grabs it by running over it
    if (G.power && Math.hypot(c.x - G.power.x, c.y - G.power.y) < 34){
      G.powered = c; G.power = null;
      showMsg('POWER-UP!', c.name + ' has a POWER SHOT — shoot it!');
    }
    return;
  }
  // loose ball: first player to reach it takes it
  let best = null, bestD = 30;
  G.players.forEach(function(p){
    const d = Math.hypot(p.x - ball.x, p.y - ball.y);
    if (d < bestD){ bestD = d; best = p; }
  });
  if (best){
    best.hasBall = true; G.carrier = best;
    ball.x = best.x; ball.y = best.y; ball.vx = 0; ball.vy = 0;
    setControl();
  }
}

/* ---------- the frame update ---------- */
function update(dt){
  if (!G.started || G.over) return;
  updateCamera(dt);
  if (G.msgT !== undefined) G.msgT += dt;
  if (G.msgT > 2.6) clearMsg();
  if (G.kickoffT > 0){ G.kickoffT -= dt; updateCamera(dt); return; }
  G.clock -= dt;
  if (G.clock <= 0){ endHalf(); return; }
  // power-up star spawner
  if (!G.power && !G.powered){
    G.powerT -= dt;
    if (G.powerT <= 0){
      G.power = { x: 150 + Math.random() * (FW - 300), y: 90 + Math.random() * (FH - 180), t: 0 };
      G.powerT = 20;
    }
  }
  if (G.power) G.power.t += dt;
  // your player (the stick drives him; he dribbles if he has the ball)
  const me = G.ctrl;
  if (me){
    const jx = joy.x, jy = joy.y;
    if (Math.hypot(jx, jy) > 0.15){
      const mag = Math.hypot(jx, jy);
      const nx = jx / Math.max(1, mag), ny = jy / Math.max(1, mag);
      let sp = me.speed * (G.carrier === me ? 0.92 : 1);
      // TURBO: hold it to sprint (1.5x) -- it drains stamina, so use it in bursts
      if (G.turbo && G.stam > 0){ sp *= 1.5; G.stam = Math.max(0, G.stam - 32 * dt); }
      me.x += nx * sp * dt; me.y += ny * sp * dt;
      me.face = nx >= 0 ? 1 : -1;
      me.moving = true; me.runT += dt * 10;
    } else {
      me.moving = false;
      // your teammates + the CPU run themselves; you hold still off the ball
      if (G.carrier !== me && !(G.carrier && G.carrier.team === G.myTeam)){
        // you are the nearest player on your team: drift toward the ball slowly
        const d = Math.hypot(G.ball.x - me.x, G.ball.y - me.y);
        if (d > 60) moveToward(me, G.ball.x, G.ball.y, dt, me.speed * 0.55);
      }
    }
    clampField(me);
  }
  // everyone else runs their AI -- except the opponent's controlled
  // player in PvP (a real person drives them; their position syncs in)
  var oppCtrl = pvpIsOn() ? pvpOppCtrl() : null;
  G.players.forEach(function(p){
    if (p === me) return;
    if (pvpIsOn() && p === oppCtrl) return;
    aiPlayer(p, dt);
    clampField(p);
  });
  // the kicking legs settle back down
  G.players.forEach(function(p){ if (p.kickT > 0) p.kickT -= dt; });
  // stamina refills when you are not holding TURBO
  if (!G.turbo && G.stam < 100) G.stam = Math.min(100, G.stam + 18 * dt);
  // the STEAL cooldown counts down
  if (G.stealCd > 0) G.stealCd -= dt;
  // the ball rolls (when loose)
  const ball = G.ball;
  if (!G.carrier && ball.live){
    ball.x += ball.vx * dt; ball.y += ball.vy * dt;
    ball.vx *= Math.pow(0.55, dt); ball.vy *= Math.pow(0.55, dt);
    if (Math.hypot(ball.vx, ball.vy) < 8){ ball.vx = 0; ball.vy = 0; }
    // the goalie saves: a ball flying at his goal that he can reach, he catches
    for (let t = 0; t < 2; t++){
      const gk = goalie(t);
      const gx = goalX(t);
      const towardGoal = (gx === 0 && ball.vx < 0) || (gx === FW && ball.vx > 0);
      if (towardGoal && Math.hypot(gk.x - ball.x, gk.y - ball.y) < 22){
        ball.vx = 0; ball.vy = 0; ball.kickT = 0;
        gk.hasBall = true; G.carrier = gk;
        ball.x = gk.x; ball.y = gk.y;
        showMsg('SAVE!', gk.name + ' keeps it out!');
        setControl();
        break;
      }
    }
    // the fence bounces it back -- except through the goal mouths
    if (ball.y < WALL + ball.r){ ball.y = WALL + ball.r; ball.vy = Math.abs(ball.vy) * 0.7; }
    if (ball.y > FH - WALL - ball.r){ ball.y = FH - WALL - ball.r; ball.vy = -Math.abs(ball.vy) * 0.7; }
    if (ball.x < WALL + ball.r){
      if (ball.y > GOAL_Y0 && ball.y < GOAL_Y1){ goalScored(AWAY); return; }
      ball.x = WALL + ball.r; ball.vx = Math.abs(ball.vx) * 0.7;
    }
    if (ball.x > FW - WALL - ball.r){
      if (ball.y > GOAL_Y0 && ball.y < GOAL_Y1){ goalScored(HOME); return; }
      ball.x = FW - WALL - ball.r; ball.vx = -Math.abs(ball.vx) * 0.7;
    }
  }
  updatePossession(dt);
  // PvP: the opponent's controlled player glides toward their posted
  // spot (no teleporting), and my position is posted ~4x a second.
  // The carrier is posted when it changes (the ball is the authority).
  if (pvpIsOn()){
    var op2 = pvpOppCtrl();
    if (op2 && typeof op2.tx === 'number' && typeof op2.ty === 'number'){
      var odx = op2.tx - op2.x, ody = op2.ty - op2.y;
      var od = Math.hypot(odx, ody);
      if (od > 2){
        var os = Math.min(od, 400 * dt);
        op2.x += (odx / od) * os; op2.y += (ody / od) * os;
        op2.moving = true; op2.runT += dt * 10;
        op2.face = (odx >= 0) ? 1 : -1;
        clampField(op2);
      } else {
        op2.moving = false;
      }
    }
    if (G.carrier !== G.lastCarrier){
      G.lastCarrier = G.carrier;
      pvpPostState(null);
    } else {
      G.pvp.posT = (G.pvp.posT || 0) + dt;
      if (G.pvp.posT >= 0.1){
        G.pvp.posT = 0;
        pvpPostState(null);
      }
    }
  }
  // keep the P1 on the player from your team nearest the ball -- unless you just switched
  if (G.manualT > 0){ G.manualT -= dt; }
  else if (!G.carrier || G.carrier.team !== G.myTeam) setControl();
  updateSB();
}
function goalScored(team, remote){
  G.score[team] += 1;
  const scorer = G.carrier;
  showMsg('GOAL!', TEAM_NAME[team] + ' score' + (scorer ? ' — ' + scorer.name + ' buries it!' : '!') +
    '  ' + TEAM_NAME[HOME] + ' ' + G.score[HOME] + ' - ' + G.score[AWAY] + ' ' + TEAM_NAME[AWAY]);
  G.ball.live = false;
  updateSB();
  // PvP: a goal was scored — tell the other phone, so both sides agree
  // on the score and the kickoff. (Remote goals are not re-posted.)
  if (pvpIsOn() && !remote){
    pvpPostState({ ev: { k: 'goal', team: team, idx: scorer ? scorer.idx : 0 } });
  }
  setTimeout(function(){
    if (G.over) return;
    kickoff(1 - team); // the team that conceded kicks off
    showMsg('KICK OFF', TEAM_NAME[1 - team] + ' to restart');
  }, 1600);
}

/* ---------- rendering: 3D hues and shadows ---------- */
function shade(ctx2, x, y, r, c1, c2){
  const g = ctx2.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.1, x, y, r);
  g.addColorStop(0, c1); g.addColorStop(1, c2);
  ctx2.fillStyle = g;
}
function drawField(){
  // the backyard around the field: sky, house, fence, trees, pool
  const sky = ctx.createLinearGradient(0, 0, 0, 46);
  sky.addColorStop(0, '#7ec8f7'); sky.addColorStop(1, '#bfe6fb');
  ctx.fillStyle = sky; ctx.fillRect(0, 0, W, 46);
  ctx.fillStyle = '#8d6e63'; ctx.fillRect(0, 0, W, 10); // the house wall
  ctx.fillStyle = '#6d4c41'; ctx.fillRect(0, 10, W, 4);
  // the grass (mowed stripes + a soft vignette for depth)
  const fx0 = fieldSX(0), fy0 = fieldSY(0), fx1 = fieldSX(FW), fy1 = fieldSY(FH);
  for (let i = 0; i < 9; i++){
    ctx.fillStyle = i % 2 ? '#4caf50' : '#43a047';
    ctx.fillRect(fx0 + (fx1 - fx0) * i / 9, fy0, (fx1 - fx0) / 9 + 1, fy1 - fy0);
  }
  const vg = ctx.createRadialGradient(W / 2, (fy0 + fy1) / 2, Math.min(W, H) * 0.35, W / 2, (fy0 + fy1) / 2, Math.max(W, H) * 0.75);
  vg.addColorStop(0, 'rgba(0,0,0,0)'); vg.addColorStop(1, 'rgba(0,0,0,0.22)');
  ctx.fillStyle = vg; ctx.fillRect(fx0, fy0, fx1 - fx0, fy1 - fy0);
  // the pool (top-left, like the screenshots)
  ctx.fillStyle = '#29b6f6'; ctx.fillRect(fieldSX(18), fieldSY(6), fieldSX(120) - fieldSX(18), 16);
  ctx.fillStyle = '#0277bd'; ctx.fillRect(fieldSX(18), fieldSY(6), fieldSX(120) - fieldSX(18), 4);
  // the trees (top-right)
  for (let i = 0; i < 4; i++){
    const tx = fieldSX(700 + i * 52), ty = 30;
    shade(ctx, tx, ty, 20, '#81c784', '#2e7d32');
    ctx.beginPath(); ctx.arc(tx, ty, 20, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#5d4037'; ctx.fillRect(tx - 3, ty + 12, 6, 12);
  }
  // the fence (brown boards around the field, with a gap at each goal)
  ctx.fillStyle = '#8d6e63';
  ctx.fillRect(fx0 - WALL, fy0 - WALL, fx1 - fx0 + WALL * 2, WALL); // top
  ctx.fillRect(fx0 - WALL, fy1, fx1 - fx0 + WALL * 2, WALL);       // bottom
  ctx.fillRect(fx0 - WALL, fy0, WALL, fy1 - fy0);                    // left (goal gap drawn over)
  ctx.fillRect(fx1, fy0, WALL, fy1 - fy0);                           // right
  ctx.fillStyle = '#6d4c41';
  for (let x = fx0; x < fx1; x += 26){
    ctx.fillRect(x, fy0 - WALL, 3, WALL); ctx.fillRect(x, fy1, 3, WALL);
  }
  for (let y = fy0; y < fy1; y += 26){
    ctx.fillRect(fx0 - WALL, y, WALL, 3); ctx.fillRect(fx1, y, WALL, 3);
  }
  // the field lines (white, like the screenshots)
  ctx.strokeStyle = 'rgba(255,255,255,0.9)'; ctx.lineWidth = 3;
  ctx.strokeRect(fx0, fy0, fx1 - fx0, fy1 - fy0);
  ctx.beginPath(); ctx.moveTo((fx0 + fx1) / 2, fy0); ctx.lineTo((fx0 + fx1) / 2, fy1); ctx.stroke();
  ctx.beginPath(); ctx.arc((fx0 + fx1) / 2, (fy0 + fy1) / 2, 52, 0, Math.PI * 2); ctx.stroke();
  // ---- the OFFICIAL markings (both ends) ----
  // penalty box: 180 deep, 320 wide, centred on the goal
  // six-yard box: 90 deep, 180 wide -- penalty spot 130 out -- arc r=90
  const PB_D = 180, PB_W = 320, GB_D = 90, GB_W = 180, PS_D = 130, ARC_R = 90;
  const ARC_A = Math.asin(Math.sqrt(ARC_R * ARC_R - (PB_D - PS_D) * (PB_D - PS_D)) / ARC_R);
  [0, 1].forEach(function(side){
    const dir = side === 0 ? 1 : -1; // 0 = left goal, 1 = right goal
    const gx = side === 0 ? 0 : FW;
    const bx = side === 0 ? fieldSX(0) : fieldSX(FW);
    const px = side === 0 ? fieldSX(PB_D) : fieldSX(FW - PB_D);
    const gx2 = side === 0 ? fieldSX(GB_D) : fieldSX(FW - GB_D);
    const cy = fieldSY(FH / 2);
    const yTop = fieldSY(FH / 2 - PB_W / 2), yBot = fieldSY(FH / 2 + PB_W / 2);
    const gyTop = fieldSY(FH / 2 - GB_W / 2), gyBot = fieldSY(FH / 2 + GB_W / 2);
    // the penalty box (three sides -- the goal line closes it)
    ctx.beginPath();
    ctx.moveTo(bx, yTop); ctx.lineTo(px, yTop); ctx.lineTo(px, yBot); ctx.lineTo(bx, yBot);
    ctx.stroke();
    // the six-yard box
    ctx.beginPath();
    ctx.moveTo(bx, gyTop); ctx.lineTo(gx2, gyTop); ctx.lineTo(gx2, gyBot); ctx.lineTo(bx, gyBot);
    ctx.stroke();
    // the penalty spot
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.arc(fieldSX(gx + dir * PS_D), cy, 4, 0, Math.PI * 2); ctx.fill();
    // the penalty arc (only the part outside the box)
    ctx.beginPath();
    const sc = fieldScale();
    if (side === 0) ctx.arc(fieldSX(PS_D), cy, ARC_R * sc, -ARC_A, ARC_A);
    else ctx.arc(fieldSX(FW - PS_D), cy, ARC_R * sc, Math.PI - ARC_A, Math.PI + ARC_A);
    ctx.stroke();
  });
  // the corner arcs (quarter-circles, r=30, at all four corners)
  const CR = 30 * fieldScale();
  ctx.beginPath(); ctx.arc(fx0, fy0, CR, 0, Math.PI / 2); ctx.stroke();
  ctx.beginPath(); ctx.arc(fx1, fy0, CR, Math.PI / 2, Math.PI); ctx.stroke();
  ctx.beginPath(); ctx.arc(fx0, fy1, CR, -Math.PI / 2, 0); ctx.stroke();
  ctx.beginPath(); ctx.arc(fx1, fy1, CR, Math.PI, Math.PI * 1.5); ctx.stroke();
  // the goals (orange posts + net, at each end)
  drawGoal(0); drawGoal(1);
  // the centre spot
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.arc((fx0 + fx1) / 2, (fy0 + fy1) / 2, 4, 0, Math.PI * 2); ctx.fill();
}
function drawGoal(side){
  // side 0 = left goal, 1 = right goal -- a 3D box you can see
  const gy0 = fieldSY(GOAL_Y0), gy1 = fieldSY(GOAL_Y1);
  const gx = side === 0 ? fieldSX(0) : fieldSX(FW);
  const depth = side === 0 ? -GOAL_DEPTH : GOAL_DEPTH;
  const x0 = Math.min(gx, gx + depth), x1 = Math.max(gx, gx + depth);
  // the net (a white-shaded box behind the line, with a grid)
  ctx.fillStyle = 'rgba(255,255,255,0.35)';
  ctx.fillRect(x0, gy0, x1 - x0, gy1 - gy0);
  ctx.strokeStyle = 'rgba(255,255,255,0.8)'; ctx.lineWidth = 1;
  for (let i = 1; i < 5; i++){
    const y = gy0 + (gy1 - gy0) * i / 5;
    ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
  }
  for (let i = 1; i < 3; i++){
    const x = x0 + (x1 - x0) * i / 3;
    ctx.beginPath(); ctx.moveTo(x, gy0); ctx.lineTo(x, gy1); ctx.stroke();
  }
  // the frame: two tall orange posts + a crossbar, with a light edge for 3D
  ctx.fillStyle = '#ff7043';
  ctx.fillRect(gx - 5, gy0 - 8, 10, gy1 - gy0 + 16); // the mouth bar (both posts joined)
  ctx.fillStyle = '#ffccbc';
  ctx.fillRect(gx - 5, gy0 - 8, 4, gy1 - gy0 + 16);
  ctx.fillStyle = '#fff';
  ctx.fillRect(gx - 2, gy0 - 8, 4, 8); ctx.fillRect(gx - 2, gy1, 4, 8);
}
function drawKid(p){
  const sx = fieldSX(p.x), sy = fieldSY(p.y);
  // a SIDE-VIEW running figure: he faces the way he moves (left or right),
  // leans into the run, one leg strides forward and one back, arms pump
  // opposite the legs. When he is still, he stands upright facing that way.
  const fx = p.face; // +1 right, -1 left
  const run = p.moving ? Math.sin(p.runT) : 0;   // -1..1, the run cycle
  const kick = (p.kickT > 0) ? Math.sin((0.35 - p.kickT) / 0.35 * Math.PI) : 0; // 0..1..0, the kick swing
  const lean = p.moving ? 6 * fx : 0; // he leans into the run
  ctx.lineCap = 'round';
  // the drop shadow (a narrow ellipse under the kid)
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.beginPath(); ctx.ellipse(sx, sy + 28, 16, 6, 0, 0, Math.PI * 2); ctx.fill();
  // ---- the legs: a real running stride, forward and back in the facing direction ----
  // front leg: reaches WELL forward when running, or kicks out hard when he shoots
  const fwd = run * 19 + kick * 24 * fx;
  const fwdLift = p.moving ? Math.max(0, -Math.cos(p.runT)) * 8 : 0; // the foot lifts clear off the ground mid-stride
  // back leg: trails WELL behind, pushing off
  const back = -run * 19;
  const backLift = p.moving ? Math.max(0, Math.cos(p.runT)) * 8 : 0;
  ctx.strokeStyle = '#222'; ctx.lineWidth = 6;
  ctx.beginPath(); ctx.moveTo(sx, sy + 12);
  ctx.lineTo(sx + fwd, sy + 28 - fwdLift); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(sx, sy + 12);
  ctx.lineTo(sx + back, sy + 28 - backLift); ctx.stroke();
  // the feet (white boots, clearly apart mid-stride)
  ctx.fillStyle = '#fff';
  ctx.beginPath(); ctx.ellipse(sx + fwd, sy + 28 - fwdLift, 6, 4, 0, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.ellipse(sx + back, sy + 28 - backLift, 6, 4, 0, 0, Math.PI * 2); ctx.fill();
  // ---- the arms: pumping forward and back, opposite the legs ----
  const col = TEAM_COLOR[p.team];
  const armSwing = -run * 13;
  ctx.strokeStyle = col; ctx.lineWidth = 5;
  // front arm: swings forward with the back leg
  ctx.beginPath(); ctx.moveTo(sx + lean, sy - 4);
  ctx.lineTo(sx + lean + fx * 8 + armSwing, sy + 8); ctx.stroke();
  // back arm: swings back with the front leg
  ctx.beginPath(); ctx.moveTo(sx + lean, sy - 4);
  ctx.lineTo(sx + lean - fx * 8 - armSwing, sy + 8); ctx.stroke();
  // the hands (skin)
  ctx.fillStyle = TEAM_SKIN[p.team];
  ctx.beginPath(); ctx.arc(sx + lean + fx * 8 + armSwing, sy + 8, 3, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(sx + lean - fx * 8 - armSwing, sy + 8, 3, 0, Math.PI * 2); ctx.fill();
  // the body: a TALL NARROW torso, leaning into the run
  const trim = TEAM_TRIM[p.team];
  shade(ctx, sx + lean, sy, 18, lighten(col), darken(col));
  ctx.beginPath(); ctx.ellipse(sx + lean, sy, 13, 18, 0, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = trim; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.ellipse(sx + lean, sy, 13, 18, 0, 0, Math.PI * 2); ctx.stroke();
  // the jersey number (his index + 1)
  ctx.fillStyle = p.team === HOME ? '#111' : '#fff';
  ctx.font = 'bold 12px Arial'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(String(p.idx + 1), sx + lean, sy + 1);
  // the head (a smaller shaded sphere, leaning forward, cap brim pointing the way he runs)
  shade(ctx, sx + lean * 1.5, sy - 26, 11, lighten(TEAM_SKIN[p.team]), darken(TEAM_SKIN[p.team]));
  ctx.beginPath(); ctx.arc(sx + lean * 1.5, sy - 26, 11, 0, Math.PI * 2); ctx.fill();
  // the cap (team colour, with a brim pointing the way he runs)
  ctx.fillStyle = col;
  ctx.beginPath(); ctx.arc(sx + lean * 1.5, sy - 28, 11, Math.PI, 0); ctx.fill();
  ctx.fillRect(sx + lean * 1.5 - 11, sy - 29, 22, 4);
  if (fx < 0){ ctx.fillRect(sx + lean * 1.5 - 17, sy - 28, 6, 3); }
  else { ctx.fillRect(sx + lean * 1.5 + 11, sy - 28, 6, 3); }
  // the P1 ring (the kid you control)
  if (G.ctrl === p){
    ctx.strokeStyle = '#f5c518'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.ellipse(sx, sy + 6, 22, 13, 0, 0, Math.PI * 2); ctx.stroke();
    ctx.fillStyle = '#f5c518'; ctx.font = 'bold 12px Arial';
    ctx.fillText('P1', sx, sy - 46);
  }
  // the power-up glow (a gold ring when he holds a power shot)
  if (G.powered === p){
    ctx.strokeStyle = 'rgba(255,213,79,0.9)'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.arc(sx, sy - 4, 24, 0, Math.PI * 2); ctx.stroke();
  }
}
function lighten(hex){
  const n = parseInt(hex.slice(1), 16);
  const r = Math.min(255, ((n >> 16) & 255) + 70), g = Math.min(255, ((n >> 8) & 255) + 70), b = Math.min(255, (n & 255) + 70);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}
function darken(hex){
  const n = parseInt(hex.slice(1), 16);
  const r = Math.max(0, ((n >> 16) & 255) - 60), g = Math.max(0, ((n >> 8) & 255) - 60), b = Math.max(0, (n & 255) - 60);
  return 'rgb(' + r + ',' + g + ',' + b + ')';
}
function drawBall(){
  const b = G.ball;
  if (!b || !b.live) return;
  const sx = fieldSX(b.x), sy = fieldSY(b.y);
  ctx.fillStyle = 'rgba(0,0,0,0.35)';
  ctx.beginPath(); ctx.ellipse(sx + 3, sy + 10, 9, 4, 0, 0, Math.PI * 2); ctx.fill();
  shade(ctx, sx, sy, b.r, '#ffffff', '#9e9e9e');
  ctx.beginPath(); ctx.arc(sx, sy, b.r, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = '#555'; ctx.lineWidth = 1.5;
  ctx.beginPath(); ctx.arc(sx, sy, b.r, 0, Math.PI * 2); ctx.stroke();
  ctx.fillStyle = '#222';
  ctx.beginPath(); ctx.arc(sx - 3, sy - 2, 3, 0, Math.PI * 2); ctx.fill();
  ctx.beginPath(); ctx.arc(sx + 4, sy + 3, 2.5, 0, Math.PI * 2); ctx.fill();
  if (G.powered){
    ctx.strokeStyle = 'rgba(255,213,79,0.95)'; ctx.lineWidth = 2.5;
    ctx.beginPath(); ctx.arc(sx, sy, b.r + 4, 0, Math.PI * 2); ctx.stroke();
  }
}
function drawPower(){
  if (!G.power) return;
  const sx = fieldSX(G.power.x), sy = fieldSY(G.power.y);
  const pulse = 1 + Math.sin(G.power.t * 5) * 0.15;
  ctx.save();
  ctx.translate(sx, sy); ctx.scale(pulse, pulse);
  ctx.fillStyle = '#ffd54f';
  ctx.strokeStyle = '#ff8f00'; ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < 5; i++){
    const a = -Math.PI / 2 + i * (Math.PI * 2 / 5);
    const a2 = a + Math.PI / 5;
    ctx.lineTo(Math.cos(a) * 16, Math.sin(a) * 16);
    ctx.lineTo(Math.cos(a2) * 7, Math.sin(a2) * 7);
  }
  ctx.closePath(); ctx.fill(); ctx.stroke();
  ctx.restore();
}
function render(){
  ctx.clearRect(0, 0, W, H);
  ctx.fillStyle = '#0a1f0a'; ctx.fillRect(0, 0, W, H);
  if (!G.started){ drawField(); return; }
  drawField();
  drawPower();
  // the kids (sorted so the lower ones draw on top, like depth)
  const sorted = G.players.slice().sort(function(a, b){ return a.y - b.y; });
  sorted.forEach(drawKid);
  drawBall();
}

/* ---------- controls ---------- */
const joy = { x: 0, y: 0 };
(function(){
  const stick = document.getElementById('stick');
  const knob = document.getElementById('stickKnob');
  let sid = null, cx = 0, cy = 0;
  function setKnob(dx, dy){
    knob.style.left = (35 + dx) + 'px';
    knob.style.top = (35 + dy) + 'px';
  }
  stick.addEventListener('pointerdown', function(e){
    sid = e.pointerId; stick.setPointerCapture(sid);
    const r = stick.getBoundingClientRect();
    cx = r.left + r.width / 2; cy = r.top + r.height / 2;
    move(e);
  });
  function move(e){
    if (e.pointerId !== sid) return;
    let dx = (e.clientX - cx) / 42, dy = (e.clientY - cy) / 42;
    const m = Math.hypot(dx, dy);
    if (m > 1){ dx /= m; dy /= m; }
    joy.x = dx; joy.y = dy;
    setKnob(dx * 32, dy * 32);
  }
  stick.addEventListener('pointermove', move);
  function end(e){
    if (e.pointerId !== sid) return;
    sid = null; joy.x = 0; joy.y = 0; setKnob(0, 0);
  }
  stick.addEventListener('pointerup', end);
  stick.addEventListener('pointercancel', end);
  const tb = document.getElementById('btnTurbo');
  tb.addEventListener('pointerdown', function(){ G.turbo = true; });
  tb.addEventListener('pointerup', function(){ G.turbo = false; });
  tb.addEventListener('pointercancel', function(){ G.turbo = false; });
  tb.addEventListener('pointerleave', function(){ G.turbo = false; });
  document.getElementById('btnSwitch').addEventListener('pointerdown', function(){
    if (G.started && !G.over) switchPlayer();
  });
  document.getElementById('btnShoot').addEventListener('pointerdown', function(){
    if (G.started && !G.over && G.carrier && G.carrier.team === HOME && G.carrier === G.ctrl) shoot(G.ctrl);
  });
  document.getElementById('btnPass').addEventListener('pointerdown', function(){
    if (!G.started || G.over) return;
    if (G.carrier && G.carrier.team === HOME && G.carrier === G.ctrl) pass(G.ctrl);
    else if (G.carrier && G.carrier.team === AWAY && G.stealCd <= 0) steal(G.ctrl);
  });
  document.getElementById('menuBtn').addEventListener('pointerdown', function(){
    document.getElementById('overlay').classList.remove('hidden');
    document.getElementById('startBtn').textContent = 'RESUME';
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
    pvpPost('/create', { player_id: who.id, player_name: who.name, game: 'soccer' }).then(function(room){
      if (!room || !room.code){ pvpSetStatus('Could not create a room — check your connection and try again.'); return; }
      G.myTeam = HOME; // host is the Bombers (yellow)
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
      G.myTeam = AWAY; // guest is the Melonheads (black)
      G.pvp = { code: room.code, role: 'guest', oppName: room.host_name || 'Opponent', seq: 0, oppSeq: -1, pollTimer: null, posT: 0 };
      pvpSetStatus('Joined! You are the Melonheads (black).');
      pvpSetRoomLbl('CODE: ' + room.code + ' — vs ' + G.pvp.oppName);
      pvpStartPoll();
      showMsg('WAITING FOR HOST', 'The host starts the game.');
    });
  });
  const diffRow = document.getElementById('diffRow');
  DIFFS.forEach(function(d, i){
    const b = document.createElement('button');
    b.textContent = d.n;
    if (i === diffIdx) b.classList.add('sel');
    b.addEventListener('pointerdown', function(){
      diffIdx = i;
      diffRow.querySelectorAll('button').forEach(function(x){ x.classList.remove('sel'); });
      b.classList.add('sel');
    });
    diffRow.appendChild(b);
  });
  document.getElementById('startBtn').addEventListener('pointerdown', function(){
    const ov = document.getElementById('overlay');
    if (G.started && !G.over){
      ov.classList.add('hidden');
      return;
    }
    startGame();
  });
})();

/* ---------- the frame loop ---------- */
let lastT = 0;
function frame(ts){
  requestAnimationFrame(frame);
  const dt = Math.min(0.05, (ts - lastT) / 1000 || 0.016);
  lastT = ts;
  update(dt);
  render();
}
requestAnimationFrame(frame);

/* ---------- smoke hooks ---------- */
window.__PS = {
  G: G, FW: FW, FH: FH, GOAL_Y0: GOAL_Y0, GOAL_Y1: GOAL_Y1, HALF_LEN: HALF_LEN,
  HOME: HOME, AWAY: AWAY, ROSTER: ROSTER, DIFFS: DIFFS,
  startGame: startGame, kickoff: kickoff, update: update, goalScored: goalScored,
  shoot: shoot, pass: pass, aiPlayer: aiPlayer, setControl: setControl,
  makePlayers: makePlayers, teamPlayers: teamPlayers, goalie: goalie,
  endHalf: endHalf, updatePossession: updatePossession,
  updateCamera: updateCamera, getCamX: function(){ return camX; }, viewW: viewW,
  switchPlayer: switchPlayer,
  setTurbo: function(v){ G.turbo = v; },
  steal: steal,
  joy: joy,
  pvpPlayer: pvpPlayer, pvpIsOn: pvpIsOn, pvpMe: pvpMe, pvpOppCtrl: pvpOppCtrl,
  pvpReceiveEv: pvpReceiveEv, pvpApplyState: pvpApplyState, pvpPostState: pvpPostState,
  pvpStartPoll: pvpStartPoll, pvpStopPoll: pvpStopPoll, pvpPollOnce: pvpPollOnce,
  kickBall: kickBall,
};

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
  if (room.status !== 'finished' && G.pvp.rmReq === r + 1 && G.pvp.oppRm === r + 1){
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
  var waiting = on && G.pvp.role === 'host' && pvpNotStarted();
  var over = on && pvpIsOver();
  pvpBar.style.display = (waiting || over) ? 'flex' : 'none';
  if (!(waiting || over)) return;
  var r = G.pvp.round || 0;
  var mine = G.pvp.rmReq === r + 1, theirs = G.pvp.oppRm === r + 1;
  document.getElementById('pvpExShare').style.display = waiting ? 'block' : 'none';
  var rb = document.getElementById('pvpExRematch');
  rb.style.display = over ? 'block' : 'none';
  rb.disabled = mine; rb.style.opacity = mine ? '0.6' : '1';
  var msg = 'Room ' + G.pvp.code + ' - send the code to your friend';
  if (over) msg = mine ? 'Rematch asked - waiting for the other player...' : (theirs ? 'The other player wants a REMATCH!' : 'Game over - play again?');
  document.getElementById('pvpExMsg').textContent = msg;
}
setInterval(pvpExtrasRefresh, 300);
</script>
</body>
</html>
`;
