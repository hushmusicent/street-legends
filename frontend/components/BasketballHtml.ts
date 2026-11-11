// PARK_BASKETBALL_HTML
export const BASKETBALL_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Park Basketball</title>
<style>

  * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html, body { height:100%; background:#0d1f12; color:#fff; font-family:Arial, Helvetica, sans-serif; overflow:hidden; touch-action:none; }
  #app { height:100%; display:flex; flex-direction:column; }
/* ============ GAME VIEW ============ */
  #gameView { position:fixed; inset:0; background:#000; display:none; flex-direction:column; z-index:10; }
  #gameView.open { display:flex; }
  #gameStage { position:relative; flex:1; display:flex; flex-direction:column; overflow:hidden; background:#111; }
  #canvasWrap { position:relative; flex:1; background:#0a2a12; overflow:hidden; }
  #gameCanvas { position:absolute; }
  #scorebug { position:absolute; top:52px; left:50%; transform:translateX(-50%); display:flex; gap:10px; align-items:center; background:rgba(0,0,0,.75); border:2px solid #f5c518; border-radius:10px; padding:6px 14px; font-weight:bold; z-index:5; white-space:nowrap; }
  #scorebug .team { font-size:18px; }
  #scorebug .team.home { color:#ff5a5a; }
  #scorebug .team.away { color:#5aa9ff; }
  #scorebug .clock { font-size:20px; color:#f5c518; }
  #scorebug .fire { color:#ff7a00; font-size:15px; }
  #backBtn { position:absolute; top:8px; left:8px; z-index:6; background:rgba(0,0,0,.7); color:#fff; border:2px solid #888; border-radius:8px; padding:8px 12px; font-size:14px; font-weight:bold; }
  #turboMeter { position:absolute; top:98px; left:50%; transform:translateX(-50%); width:150px; height:8px; background:rgba(255,255,255,.25); border-radius:4px; overflow:hidden; z-index:5; }
  #turboFill { height:100%; width:100%; background:#f5c518; }
  #callout { position:absolute; top:32%; left:0; right:0; text-align:center; font-size:56px; font-weight:900; font-style:italic; color:#f5c518; text-shadow:3px 3px 0 #000, -2px -2px 0 #c00; z-index:7; pointer-events:none; opacity:0; letter-spacing:1px; }
  #callout.pop { animation:pop 1s ease-out forwards; }
  @keyframes pop { 0%{opacity:0; transform:scale(.5);} 15%{opacity:1; transform:scale(1.15);} 30%{transform:scale(1);} 80%{opacity:1;} 100%{opacity:0; transform:scale(1);} }
  #subCallout { position:absolute; top:44%; left:0; right:0; text-align:center; font-size:22px; font-weight:bold; color:#fff; text-shadow:2px 2px 0 #000; z-index:7; pointer-events:none; opacity:0; }
  #subCallout.pop { animation:pop 1.2s ease-out forwards; }

  /* Joystick bottom-left, buttons bottom-right — lifted clear of the Android
     nav bar (48px) with room to spare; env() adds the safe-area inset where
     the browser reports one, the 56px fallback clears it either way. */
  #controls { position:relative; flex:none; height:232px; height:calc(232px + env(safe-area-inset-bottom, 0px)); background:rgba(0,0,0,.9); border-top:2px solid #333; }
  #stick { position:absolute; left:14px; bottom:56px; bottom:calc(56px + env(safe-area-inset-bottom, 0px)); width:160px; height:160px; border-radius:50%; background:rgba(255,255,255,.10); border:3px solid rgba(255,255,255,.45); touch-action:none; user-select:none; }
  #stickKnob { position:absolute; left:50%; top:50%; width:64px; height:64px; border-radius:50%; background:rgba(245,197,24,.9); border:3px solid #fff; transform:translate(-50%,-50%); box-shadow:0 2px 8px rgba(0,0,0,.5); pointer-events:none; }
  #buttons { position:absolute; right:14px; bottom:56px; bottom:calc(56px + env(safe-area-inset-bottom, 0px)); width:210px; height:150px; pointer-events:none; }
  .gbtn { position:absolute; width:76px; height:76px; border-radius:50%; border:3px solid rgba(255,255,255,.7); color:#fff; font-weight:900; font-size:15px; letter-spacing:.5px; pointer-events:auto; touch-action:none; user-select:none; text-shadow:1px 1px 0 #000; }
  .gbtn.on { filter:brightness(1.4); transform:scale(.93); }
  #btnShoot { right:118px; bottom:0; background:#c81e1e; }
  #btnPass { right:10px; bottom:74px; background:#1d6fd1; }
  #btnTurbo { right:42px; bottom:0; background:#f59e0b; color:#000; text-shadow:none; }
  #btnShoot.def { background:#7c3aed; }
  #btnPass.def { background:#059669; }

  /* Start / end overlays */
  .overlay { position:absolute; inset:0; background:rgba(0,0,0,.82); z-index:20; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:14px; text-align:center; padding:20px; }
  .overlay h2 { font-size:34px; font-style:italic; color:#f5c518; text-shadow:2px 2px 0 #c00; }
  .overlay .vs { font-size:22px; font-weight:bold; }
  .overlay .vs .h { color:#ff5a5a; } .overlay .vs .a { color:#5aa9ff; }
  .overlay p { color:#ccc; font-size:14px; line-height:1.5; max-width:340px; }
  .bigbtn { background:#f5c518; color:#000; border:none; border-radius:12px; padding:16px 34px; font-size:20px; font-weight:900; letter-spacing:1px; }
  .bigbtn:active { transform:scale(.96); }
  .ghostbtn { background:transparent; color:#fff; border:2px solid #888; border-radius:10px; padding:12px 22px; font-size:16px; font-weight:bold; }
  .diff-wrap { width:100%; max-width:420px; }
  .diff-label { font-size:13px; letter-spacing:2px; color:#f5c518; font-weight:bold; margin-bottom:6px; }
  .diff-btns { display:flex; gap:6px; }
  .diffbtn { flex:1; background:#1f2937; color:#fff; border:2px solid #555; border-radius:10px; padding:10px 2px; font-size:13px; font-weight:900; line-height:1.3; }
  .diffbtn.sel { background:#f5c518; color:#000; border-color:#f5c518; }
  .diff-desc { font-size:12px; color:#ccc; margin-top:6px; min-height:15px; }
  #diffChip { position:absolute; top:10px; left:126px; z-index:5; background:rgba(0,0,0,.75); border:2px solid #f5c518; border-radius:8px; padding:4px 10px; font-size:12px; font-weight:bold; color:#f5c518; }
  .overlay { overflow-y:auto; }
  #finalScore { font-size:44px; font-weight:900; }
  #finalScore .h { color:#ff5a5a; } #finalScore .a { color:#5aa9ff; }
  .hidden { display:none !important; }
</style>
</head>
<body>
<div id="gameView" class="open">
    <div id="gameStage">
      <div id="canvasWrap">
      <canvas id="gameCanvas" width="900" height="600"></canvas>
      <div id="scorebug">
        <span class="team home">HOME <span id="scoreHome">0</span></span>
        <span class="clock">FIRST TO 21</span>
        <span class="clock" id="gameClock">0:00</span>
        <span class="team away"><span id="scoreAway">0</span> AWAY</span>
        <span class="fire hidden" id="fireTag">&#128293; ON FIRE</span>
      </div>
      <button id="backBtn">&#8592; PARK</button>
      <div id="diffChip">PRO</div>
      <div id="turboMeter"><div id="turboFill"></div></div>
      <div id="callout"></div>
      <div id="subCallout"></div>
      </div>

      <div id="controls">
        <div id="stick"><div id="stickKnob"></div></div>
        <div id="buttons">
          <button class="gbtn" id="btnShoot">SHOOT</button>
          <button class="gbtn" id="btnPass">PASS</button>
          <button class="gbtn" id="btnTurbo">TURBO</button>
        </div>
      </div>

      <div class="overlay" id="startOverlay">
        <h2>PARK JAM</h2>
        <div class="vs"><span class="h">HOME</span> &nbsp;VS&nbsp; <span class="a">AWAY</span></div>
        <p>2 on 2 &bull; First to 21 by 1 &bull; Inside = 1, beyond the arc = 2<br>
        Joystick to move &bull; SHOOT to shoot (dunk up close)<br>
        TURBO + SHOOT = big dunk &bull; 3 straight baskets = ON FIRE &bull; No fouls</p>
        <div class="diff-wrap">
          <div class="diff-label">COMPUTER DIFFICULTY</div>
          <div class="diff-btns">
            <button class="diffbtn" id="diffBtn1">1<br>ROOKIE</button>
            <button class="diffbtn" id="diffBtn2">2<br>AMATEUR</button>
            <button class="diffbtn sel" id="diffBtn3">3<br>PRO</button>
            <button class="diffbtn" id="diffBtn4">4<br>ALL-STAR</button>
            <button class="diffbtn" id="diffBtn5">5<br>LEGEND</button>
          </div>
          <div class="diff-desc" id="diffDesc">Even game — the computer plays straight up.</div>
        </div>
        <button class="bigbtn" id="startBtn">TIP OFF</button>
        <button class="bigbtn" id="pvpBtn" style="margin-top:10px;background:#6a1b9a;color:#fff;border:3px solid #fff;border-radius:14px;padding:12px 26px;font-size:18px;font-weight:800;cursor:pointer">PLAYER VS PLAYER</button>
        <div id="pvpPanel" class="hidden" style="margin-top:10px;display:flex;flex-direction:column;align-items:center;gap:8px">
          <div style="font-size:14px;color:#ffd54f" id="pvpStatus">Play a real person — one phone creates a room, the other joins with the code.</div>
          <div style="display:flex;gap:8px">
            <button id="pvpCreateBtn" style="background:#2e7d32;color:#fff;border:2px solid #fff;border-radius:10px;padding:8px 14px;font-weight:800;cursor:pointer">CREATE ROOM</button>
            <input id="pvpCodeInput" placeholder="CODE" maxlength="4" inputmode="numeric" style="width:90px;text-align:center;font-size:18px;padding:8px;border-radius:8px;border:2px solid #f5c518;background:#111;color:#fff" />
            <button id="pvpJoinBtn" style="background:#1565c0;color:#fff;border:2px solid #fff;border-radius:10px;padding:8px 14px;font-weight:800;cursor:pointer">JOIN</button>
          </div>
          <div style="font-size:13px;color:#ccc" id="pvpRoomLbl"></div>
        </div>
        <button class="ghostbtn" id="startBackBtn">Back to park</button>
      </div>

      <div class="overlay hidden" id="endOverlay">
        <h2 id="finalTitle">HOME WINS!</h2>
        <div id="finalScore"><span class="h">0</span> &ndash; <span class="a">0</span></div>
        <p id="finalNote"></p>
        <button class="bigbtn" id="rematchBtn">REMATCH</button>
        <button class="ghostbtn" id="endBackBtn">Back to park</button>
      </div>
    </div>
  </div>
<script>

(function(){
'use strict';
const $ = id => document.getElementById(id);
const clamp=(v,a,b)=>v<a?a:v>b?b:v;
const lerp=(a,b,t)=>a+(b-a)*t;
const smoothstep=(a,b,t)=>{const u=clamp((t-a)/(b-a),0,1);return u*u*(3-2*u);};
const d2=(ax,az,bx,bz)=>{const dx=ax-bx,dz=az-bz;return Math.sqrt(dx*dx+dz*dz);};
const fmtT=s=>{s=Math.floor(s);return Math.floor(s/60)+':'+String(s%60).padStart(2,'0');};

/* ---------- tiny sounds (optional, guarded) ---------- */
let AC=null;
function beep(f,d,type){try{AC=AC||new (window.AudioContext||window.webkitAudioContext)();const o=AC.createOscillator(),g=AC.createGain();o.type=type||'square';o.frequency.value=f;g.gain.setValueAtTime(0.07,AC.currentTime);g.gain.exponentialRampToValueAtTime(0.001,AC.currentTime+d);o.connect(g);g.connect(AC.destination);o.start();o.stop(AC.currentTime+d);}catch(e){}}
function swish(){beep(880,0.12,'sine');setTimeout(()=>beep(1320,0.1,'sine'),60);}
function whistle(){beep(2200,0.15,'square');setTimeout(()=>beep(2200,0.25,'square'),200);}

/* ================= GAME — Genesis side view, park background ================= */
const cv=$('gameCanvas'), ctx=cv.getContext('2d');
const W=900, H=600;
const CX0=-120, CX1=120, CZ0=0, CZ1=46;
const HOOP={0:{x:112,z:23},1:{x:-112,z:23}}; // team 0 (HOME) attacks right, team 1 (AWAY) attacks left
const THREE=38, DUNK_D=18, TURBO_DUNK_D=32, TARGET=21; // DUNK_D = foul-line distance (hoop ±112, foul line ±94): SHOOT at the foul line or closer dunks
const KEY_LEN=18, KEY_HALF=8, FT_R=8, RA_R=6; // key: foul line 18 from the hoop, 16 wide; FT circle radius 8; restricted-area arc radius 6
const ARC_A=Math.asin(23/THREE); // 3pt arc clipped where it meets the sidelines (z 0 and 46, 23 from the arc centre)
const GREEN_LOW=0.70, GREEN_HIGH=0.88, METER_FILL_TIME=0.85; // shot meter: perfect zone + seconds to fill
// Close-up camera: zoomed in like real NBA Jam — only part of the court is on
// screen at once and the camera pans left/right to follow the ball.
const ZOOM=1.6, CAM_MAX=70;
// Computer difficulty (1-5). Only the COMPUTER team (AWAY, team 1) scales —
// the user's AI teammate stays at fixed Pro-ish level. shot = shot-accuracy
// multiplier, speed = movement-speed multiplier, react = seconds a CPU
// defender waits before chasing a new ball-handler, stealRate/stealP = steal
// attempt rate + success chance, block = block-chance multiplier.
const DIFFS=[
 {name:'ROOKIE',  shot:0.55, speed:0.72, react:1.0,  stealRate:0.4, stealP:0.12, block:0.4, desc:'Easy — the computer misses open shots and reacts slowly.'},
 {name:'AMATEUR', shot:0.75, speed:0.86, react:0.7,  stealRate:0.7, stealP:0.18, block:0.7, desc:'A fair challenge — the computer makes mistakes.'},
 {name:'PRO',     shot:1.0,  speed:1.0,  react:0.45, stealRate:1.0, stealP:0.25, block:1.0, desc:'Even game — the computer plays straight up.'},
 {name:'ALL-STAR',shot:1.2,  speed:1.1,  react:0.3,  stealRate:1.4, stealP:0.35, block:1.3, desc:'Hard — the computer hits open shots and hunts steals.'},
 {name:'LEGEND',  shot:1.4,  speed:1.2,  react:0.15, stealRate:1.8, stealP:0.45, block:1.6, desc:'Brutal — the computer barely misses and reacts instantly.'}
];
let diffSel=3; // start-screen selection; default Pro
function cpuDiff(){ return DIFFS[G.difficulty-1]; }

// Dunk styles — five distinct slams. Picked per dunk: random for a plain
// dunk, flashier ones (360 + tomahawk) favored on turbo dunks, and ON FIRE
// dunks are always flashy.
const DUNK_STYLES=[
 {id:'onehand', name:'ONE-HAND SLAM'},
 {id:'twohand', name:'TWO-HAND POWER'},
 {id:'reverse', name:'REVERSE SLAM'},
 {id:'spin360', name:'360 SPIN'},
 {id:'tomahawk', name:'TOMAHAWK'}
];
function pickDunkStyle(me,turbo,d){
  const flashy=[3,4]; // 360 SPIN + TOMAHAWK
  if(me.onFire) return flashy[Math.floor(Math.random()*flashy.length)];
  // a long dunk (foul line or further out, incl. turbo dunks) favors the
  // flashy styles — the classic free-throw-line dunk reads dramatic
  if((turbo||(d!==undefined&&d>=16))&&Math.random()<0.6) return flashy[Math.floor(Math.random()*flashy.length)];
  return Math.floor(Math.random()*DUNK_STYLES.length);
}

// 360 spin: spins like a top — fast and accelerating, one full turn done
// by the halfway point of the flight (t=0.5), body centered on its spin
// axis. The ball's circle and the body's rotation share this angle so
// they stay together. (The old linear turn took the whole flight and
// read like turning a knob.)
function spinAngle(t){ return Math.pow(Math.min(1,t/0.5),1.3)*Math.PI*2; }

const G={
  mode:'park', score:[0,0], elapsed:0, players:[], ball:null,
  possession:0, user:0, camX:0, shake:0, pause:0, afterPause:false, nextPoss:0,
  fire:null, turbo:100, turboHeld:false, dir:{x:0,z:0}, defT:0,
  difficulty:3, bhSince:0, _lastHolder:null, _prevBX:0,
  ts:1, slowT:0, slowFactor:0.33, netSnap:0, trail:[], // wind-trail samples, recorded during dunk flights only
  myTeam:0, // PvC: you are always HOME (team 0). PvP: 0 if host, 1 if guest.
  pvp:null, // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT}
  lastHolder:null, // the holder we last posted (so we only post changes)
};

/* ---------- PvP (park games) ---------- */
// Same room system as the other park games (backend: /api/park_pvp/rooms/*).
// Basketball is 2v2 and real-time, so the sync is event-based: the human's
// shots (with the make pre-computed and posted), passes, steals, and
// blocks are posted as they happen, and the opponent applies the same
// call, so the ball and the score match on both phones. The AI runs the
// other players locally on both sides (they may drift slightly -- the
// ball and the score are the authority, resynced via the room state).
// Each human controls a player on their own team; their position is
// posted ~4x a second and interpolated on the other side. Identity comes
// from the app as window.PARK_PVP_PLAYER = {id, name}.
var PVP_API='https://gta-quest-map.emergent.host/api/park_pvp/rooms';
var PVP_POLL_MS=250;
function pvpPlayer(){
  try {
    var p=window.PARK_PVP_PLAYER||null;
    if(p&&p.id) return {id:String(p.id),name:String(p.name||'Player')};
  } catch(e){ /* no injected identity */ }
  return {id:'local-player',name:'YOU'};
}
function pvpPost(path,body){
  try {
    return fetch(PVP_API+path,{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify(body||{})
    }).then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});
  } catch(e){ return Promise.resolve(null); }
}
function pvpGet(code){
  try {
    return fetch(PVP_API+'/'+encodeURIComponent(code))
      .then(function(r){return r.ok?r.json():null;}).catch(function(){return null;});
  } catch(e){ return Promise.resolve(null); }
}
function pvpIsOn(){ return !!(G.pvp&&G.pvp.code); }
function pvpMe(){ return G.players[G.user]; }
function pvpOppCtrl(){
  // The opponent's controlled player (the one the other human drives).
  // It is the opponent-team player nearest the ball on their side.
  var b=G.ball; if(!b) return null;
  var best=null,bestD=Infinity;
  G.players.forEach(function(p){
    if(p.team!==G.myTeam){
      var d=d2(p.x,p.z,b.x,b.z);
      if(d<bestD){bestD=d;best=p;}
    }
  });
  return best;
}
function pvpPostState(patch){
  // Post the shared state to the room. The patch carries the new event
  // (shot / pass / steal / block). The full score, possession, holder,
  // and my controlled player's position ride along so the other phone
  // resyncs and sees where I am.
  if(!pvpIsOn()) return Promise.resolve(null);
  G.pvp.seq+=1;
  var me=pvpMe();
  var h=holder();
  var st={
    seq:G.pvp.seq,
    score:G.score.slice(), possession:G.possession,
    holder:h?{team:h.team,num:h.num}:null,
    me:me?{team:me.team,num:me.num,x:me.x,z:me.z}:null,
    ev:null
  };
  if(patch&&patch.ev) st.ev=patch.ev;
  var who=pvpPlayer();
  return pvpPost('/'+G.pvp.code+'/state',{player_id:who.id,state:st});
}
function pvpStartPoll(){
  if(!G.pvp) return;
  if(G.pvp.pollTimer) clearInterval(G.pvp.pollTimer);
  G.pvp.pollTimer=setInterval(pvpPollOnce,PVP_POLL_MS);
}
function pvpStopPoll(){
  if(G.pvp&&G.pvp.pollTimer){ clearInterval(G.pvp.pollTimer); G.pvp.pollTimer=null; }
}
function pvpPollOnce(){
  if(!pvpIsOn()) return;
  var code=G.pvp.code;
  pvpGet(code).then(function(room){
    if(!room) return;
    if(room.status==='finished'){
      pvpStopPoll();
      G.mode='over';
      var won=room.winner&&room.winner===pvpPlayer().id;
      callout(won?'YOU WIN!':'YOU LOSE','The other player left the game.');
      return;
    }
    // Opponent joined — the game starts on its own now (like the house
    // games: the game starts when the second player enters the code).
    // Host: start when a guest_id is present (guest_id is always set on
    // join; guest_name alone is not a reliable trigger).
    if(G.pvp.role==='host'&&room.guest_id&&G.mode!=='play'){
      G.pvp.oppName=room.guest_name||'Opponent';
      var lbl=document.getElementById('pvpRoomLbl');
      if(lbl) lbl.textContent='CODE: '+code+' — vs '+G.pvp.oppName;
      var st2=document.getElementById('pvpStatus');
      if(st2) st2.textContent='They joined! Starting the game...';
      startGame();
    }
    // Guest: start as soon as the room is playing. Do NOT wait for the
    // host's first state post — if that post is missed or late, the
    // guest would sit on "WAITING FOR HOST" forever. The host's state
    // still resyncs positions/score when it arrives.
    if(G.pvp.role==='guest'&&room.status==='playing'&&G.mode!=='play'){
      var st3=document.getElementById('pvpStatus');
      if(st3) st3.textContent='Host joined! Starting the game...';
      startGame();
    }
    var st=room.state||null;
    if(st&&typeof st.seq==='number'&&st.seq>G.pvp.lastSeenSeq){
      G.pvp.lastSeenSeq=st.seq;
      pvpApplyState(st);
    }
  });
}
function pvpApplyState(st){
  if(!st) return;
  // If I haven't started yet (fresh join, or rejoin after getting
  // booted out), start the game first, then resync everything from
  // the room state. A rejoining host does NOT post a fresh initial
  // state (that would reset the room).
  var fresh=pvpIsOn()&&G.mode!=='play';
  if(fresh){
    if(G.pvp.role==='host') G.pvp.syncStart=true;
    startGame();
    if(G.pvp) G.pvp.syncStart=false;
  }
  if(Array.isArray(st.score)) G.score=st.score.slice();
  if(typeof st.possession==='number') G.possession=st.possession;
  updateScore();
  if(fresh) return; // skip events on the first state I apply
  // The opponent's controlled player: glide toward their posted spot.
  if(st.me&&typeof st.me.x==='number'&&typeof st.me.z==='number'){
    var op=null;
    G.players.forEach(function(p){ if(p.team===st.me.team&&p.num===st.me.num) op=p; });
    if(op){ op.tx=st.me.x; op.tz=st.me.z; }
  }
  // The holder: trust the room (the ball is the authority).
  if(st.holder&&typeof st.holder.team==='number'){
    var h=null;
    G.players.forEach(function(p){ if(p.team===st.holder.team&&p.num===st.holder.num) h=p; });
    if(h&&holder()!==h){
      var old=holder(); if(old) old.hasBall=false;
      h.hasBall=true; G.ball={state:'held',x:h.x,z:h.z,h:0}; G.possession=h.team;
      updateUserControl();
    }
  }
  if(st.ev) pvpReceiveEv(st.ev);
}
function pvpReceiveEv(ev){
  // Apply one event posted by the opponent. Only events from the OTHER
  // team are applied (my own events are already applied locally).
  if(!ev||typeof ev.team!=='number'||ev.team===G.myTeam) return;
  var p=null;
  G.players.forEach(function(q){ if(q.team===ev.team&&q.num===ev.num) p=q; });
  if(!p) return;
  if(ev.k==='shot'){
    // They shot: same type, points, meter, dunk style, blocked flag, and
    // make -- so their ball flies the same way and scores (or misses)
    // the same way on both phones.
    startShot(p,ev.type,ev.pts,ev.meter,ev.dunkStyle,ev.blocked,ev.make);
  } else if(ev.k==='pass'){
    // They passed to their teammate.
    var mate=null;
    G.players.forEach(function(q){ if(q.team===ev.team&&q.num===ev.mate) mate=q; });
    if(mate) doPassBallTo(p,mate);
  } else if(ev.k==='steal'){
    // They stole the ball from my holder.
    var bh=holder();
    if(bh&&bh.team!==p.team){
      bh.hasBall=false; bh.streak=0;
      p.hasBall=true; G.possession=p.team;
      G.players.forEach(function(q){q.streak=0;});
      callout('STEAL!','');
      updateUserControl();
    }
  } else if(ev.k==='block'){
    // They jumped to block: same jump, arms high.
    if(p.cool<=0){ p.jv=300; p.jz=0.1; p.lastJump=G.elapsed; p.cool=0.5; p.pose='block'; p.poseT=0; }
  }
}
const dirs={up:false,down:false,left:false,right:false};
const stick={x:0,y:0}; // virtual joystick vector, -1..1 per axis

function proj(x,z){
  const sx=W/2+(x-G.camX)*5.0*ZOOM;
  const sy=345+z*3.3*ZOOM;
  const s=(0.85+0.30*(z/CZ1))*ZOOM;
  return {x:sx,y:sy,s:s};
}
function rimScreen(hoop){
  const p=proj(hoop.x,hoop.z);
  const dir=hoop.x>0?-1:1;
  return {x:p.x+dir*26,y:270};
}
function holder(){return G.players.find(function(p){return p.hasBall;})||null;}
function targetHoop(team){return HOOP[team];}
function nearestDef(p){
  let best=999;
  G.players.forEach(function(q){if(q.team!==p.team){const d=d2(p.x,p.z,q.x,q.z);if(d<best)best=d;}});
  return best;
}

function mkPlayer(team,num,x,z){
  return {team:team,num:num,x:x,z:z,jz:0,jv:0,hasBall:false,streak:0,onFire:false,stumble:0,cool:0,lastJump:-9,shootCd:0,
    pose:'idle',poseT:0,step:0,drib:0,face:1,px:x,pz:z,moving:false,charge:null,dunkStyle:null};
}
function resetPositions(possTeam){
  const attHoop=HOOP[possTeam];
  const P=G.players;
  P.forEach(function(p){p.hasBall=false;});
  const off=P.filter(function(p){return p.team===possTeam;});
  const def=P.filter(function(p){return p.team!==possTeam;});
  off[0].x=0; off[0].z=23; off[0].hasBall=true; off[0].jz=0; off[0].jv=0; off[0].stumble=0; off[0].shootCd=0.9;
  off[1].x=attHoop.x*0.45; off[1].z=34; off[1].hasBall=false; off[1].jz=0; off[1].jv=0;
  def[0].x=attHoop.x*0.75; def[0].z=18; def[0].jz=0; def[0].jv=0;
  def[1].x=attHoop.x*0.55; def[1].z=32; def[1].jz=0; def[1].jv=0;
  P.forEach(function(p){p.cool=0;p.stumble=0;p.pose='idle';p.poseT=0;p.charge=null;});
  G.ball={state:'held',x:0,z:23,h:0};
  G.possession=possTeam;
  G.camX=0; G._prevBX=0;
  updateUserControl();
}
function newGame(){
  G.score=[0,0]; G.elapsed=0; G.fire=null; G.turbo=100; G.pause=0; G.afterPause=false; G.shake=0;
  G.slowT=0; G.ts=1; // slow-mo off at tip-off
  G.bhSince=0; G._lastHolder=null;
  G.players=[mkPlayer(0,1,-20,23),mkPlayer(0,2,-40,30),mkPlayer(1,1,20,23),mkPlayer(1,2,40,16)];
  resetPositions(0);
  updateScore();
}
function updateScore(){
  $('scoreHome').textContent=G.score[0];
  $('scoreAway').textContent=G.score[1];
  const ft=$('fireTag');
  if(G.fire){ ft.classList.remove('hidden'); ft.style.color=G.fire.team===0?'#ff5a5a':'#5aa9ff'; }
  else ft.classList.add('hidden');
}
function callout(main,sub){
  const c=$('callout'), s=$('subCallout');
  c.textContent=main; c.classList.remove('pop'); void c.offsetWidth; c.classList.add('pop');
  if(sub){ s.textContent=sub; s.classList.remove('pop'); void s.offsetWidth; s.classList.add('pop'); }
  else s.classList.remove('pop');
}
function updateLabels(){
  const me=G.players[G.user];
  const off=me&&me.team===G.possession;
  const bs=$('btnShoot'), bp=$('btnPass');
  if(off){ bs.textContent='SHOOT'; bp.textContent='PASS'; bs.classList.remove('def'); bp.classList.remove('def'); }
  else { bs.textContent='BLOCK'; bp.textContent='STEAL'; bs.classList.add('def'); bp.classList.add('def'); }
}
function updateUserControl(){
  const bh=holder();
  if(bh&&bh!==G._lastHolder){ G._lastHolder=bh; G.bhSince=G.elapsed; }
  if(bh&&bh.team===G.myTeam){ G.user=G.players.indexOf(bh); }
  else {
    // defense (or loose ball): user = nearest player from YOUR team to the ball.
    // In PvC your team is HOME (0); in PvP the guest controls AWAY (1).
    const b=G.ball; let best=0,bd=1e9;
    G.players.forEach(function(p,i){ if(p.team===G.myTeam){ const d=d2(p.x,p.z,b.x,b.z); if(d<bd){bd=d;best=i;} } });
    G.user=best;
  }
  updateLabels();
}

/* ---------- actions ---------- */
function shootPress(){
  if(G.mode!=='play'||G.pause>0) return;
  const me=G.players[G.user];
  if(!me) return;
  if(me.team!==G.possession){ doBlock(me); return; } // defense: BLOCK fires at once
  if(!me.hasBall) return;
  const hoop=targetHoop(me.team);
  const d=d2(me.x,me.z,hoop.x,hoop.z);
  if(d<=DUNK_D){ startShot(me,'dunk',1); return; } // dunks fire at once, no meter — at or inside the foul line
  if(G.turboHeld&&d<TURBO_DUNK_D){ startShot(me,'turboDunk',1); return; }
  // jump shot: hold SHOOT to charge the meter, release to shoot
  me.charge=0; me.pose='aim'; me.poseT=0;
}
function shootRelease(){
  const me=G.players[G.user];
  if(!me||me.charge===null||me.charge===undefined) return;
  const fill=me.charge; me.charge=null;
  if(G.mode!=='play'||G.pause>0) return;
  if(!me.hasBall) return;
  const hoop=targetHoop(me.team);
  const d=d2(me.x,me.z,hoop.x,hoop.z);
  startShot(me,'shot',d>=THREE?2:1,fill);
}
function doShoot(){ shootPress(); }
function doPass(){
  if(G.mode!=='play'||G.pause>0) return;
  const me=G.players[G.user];
  if(!me) return;
  if(me.team===G.possession&&me.hasBall) doPassBall(me);
  else if(me.team!==G.possession) doSteal(me);
}
function doPassBall(me){
  const mate=G.players.find(function(p){return p.team===me.team&&p!==me;});
  if(!mate) return;
  doPassBallTo(me,mate);
  // PvP: I passed — tell the other phone who caught it, so their ball
  // flies to the same teammate.
  if(pvpIsOn()&&me.team===G.myTeam&&G.players[G.user]===me){
    pvpPostState({ev:{k:'pass',team:me.team,num:me.num,mate:mate.num}});
  }
}
function doPassBallTo(me,mate){
  me.hasBall=false;
  me.pose='pass'; me.poseT=0;
  const from=proj(me.x,me.z);
  G.ball={state:'pass',t:0,dur:0.22,fx:from.x,fy:from.y-30,tx:0,ty:0,rx:mate.x,rz:mate.z,receiver:mate,lastTouch:me.team,x:me.x,z:me.z,h:20};
}
function doSteal(me){
  if(me.cool>0) return;
  me.cool=0.9;
  const bh=holder();
  if(!bh) return;
  if(d2(me.x,me.z,bh.x,bh.z)<17){
    if(Math.random()<0.32){
      bh.hasBall=false; bh.streak=0;
      me.hasBall=true; G.possession=me.team;
      G.players.forEach(function(q){q.streak=0;});
      callout('STEAL!','');
      updateUserControl();
      // PvP: I stole it — tell the other phone the ball is mine now.
      if(pvpIsOn()&&me.team===G.myTeam&&G.players[G.user]===me){
        pvpPostState({ev:{k:'steal',team:me.team,num:me.num}});
      }
    } else {
      me.stumble=0.45;
    }
  }
}
function doBlock(me){
  if(me.cool>0) return;
  me.jv=300; me.jz=0.1; me.lastJump=G.elapsed; me.cool=0.5;
  me.pose='block'; me.poseT=0;
  // PvP: I jumped to block — tell the other phone so they see me rise.
  if(pvpIsOn()&&me.team===G.myTeam&&G.players[G.user]===me){
    pvpPostState({ev:{k:'block',team:me.team,num:me.num}});
  }
}
function startShot(me,type,pts,meter,dunkStyle,blocked,make){
  const hoop=targetHoop(me.team);
  G.trail=[]; // wind trails are dunk-only — a new shot starts with a clean slate
  // block check at release: defender close + jumping (or just jumped)
  // CPU defenders block better on higher difficulties; the user's own
  // teammate blocks at a fixed rate.
  let blockP=0;
  G.players.forEach(function(p){
    if(p.team!==me.team&&d2(p.x,p.z,me.x,me.z)<15){
      const mult=(p.team===1)?cpuDiff().block:1;
      blockP+=mult*((p.jz>4||(G.elapsed-p.lastJump)<0.35)?0.30:0.12);
    }
  });
  // AI defenders react to the shot
  G.players.forEach(function(p){
    if(p.team!==me.team&&d2(p.x,p.z,me.x,me.z)<16&&Math.random()<0.3*((p.team===1)?cpuDiff().block:1)){ p.jv=300; p.jz=0.1; p.lastJump=G.elapsed; }
  });
  // PvP: when the shot comes from the other phone, the blocked flag and
  // the make arrive with it -- use them, do not re-roll. When the shot
  // is mine, roll the block here and pre-compute the make so both phones
  // agree on the outcome (resolveShot uses the posted make).
  var isRemote=(blocked!==undefined&&blocked!==null)||(make!==undefined&&make!==null);
  var blockedShot;
  var shotMake;
  if(isRemote){
    blockedShot=!!blocked;
    shotMake=(make===undefined||make===null)?null:!!make;
  } else {
    blockedShot=Math.random()<Math.min(blockP,0.55);
    shotMake=null; // computed in resolveShot (PvC) or posted (PvP, below)
    if(pvpIsOn()&&me.team===G.myTeam&&G.players[G.user]===me){
      // Pre-compute the make now (same logic as resolveShot) so the
      // other phone scores (or misses) the same way.
      shotMake=computeMake(me,type,pts,meter);
    }
  }
  me.hasBall=false; me.jv=260; me.jz=0.1; me.shootCd=0.6;
  me.pose=(type==='shot')?'shoot':'dunk'; me.poseT=0;
  if(type==='dunk'||type==='turboDunk') me.dunkStyle=(dunkStyle!==undefined&&dunkStyle!==null)?dunkStyle:pickDunkStyle(me,type==='turboDunk',d2(me.x,me.z,hoop.x,hoop.z));
  const rim=rimScreen(hoop);
  const from=proj(me.x,me.z);
  // a blocked shot gets swatted down near the shooter — it never reaches the rim
  const tx=blockedShot?from.x+(hoop.x>me.x?-1:1)*24:rim.x;
  const ty=blockedShot?from.y+70:rim.y;
  G.ball={state:'shot',type:type,pts:pts,shooter:me,hoop:hoop,t:0,dur:blockedShot?0.28:(type==='shot'?0.55:0.42),
    fx:from.x,fy:from.y-46,tx:tx,ty:ty,blocked:blockedShot,lastTouch:me.team,
    meter:(meter===undefined||meter===null)?null:meter,
    perfect:(meter!==null&&meter!==undefined&&meter>=GREEN_LOW&&meter<=GREEN_HIGH),
    dunkStyle:(type==='dunk'||type==='turboDunk')?me.dunkStyle:undefined,
    make:shotMake,
    x:me.x,z:me.z,h:0,sx:from.x,sy:from.y-46};
  // PvP: I shot — tell the other phone the type, points, meter, dunk
  // style, blocked flag, and make, so their ball flies the same way.
  if(pvpIsOn()&&me.team===G.myTeam&&G.players[G.user]===me&&!isRemote){
    pvpPostState({ev:{k:'shot',team:me.team,num:me.num,type:type,pts:pts,meter:(meter===undefined||meter===null)?null:meter,dunkStyle:(type==='dunk'||type==='turboDunk')?me.dunkStyle:null,blocked:blockedShot,make:shotMake}});
  }
  // slow motion for the dunk: everything drops to ~1/3 speed for the flight
  // plus a short beat after the slam, then eases back to full speed.
  // Flashy dunks (360 SPIN / TOMAHAWK) go a touch deeper. Blocked dunks
  // never slam, so they stay at normal speed.
  if((type==='dunk'||type==='turboDunk')&&!blockedShot){
    const flashy=(me.dunkStyle===3||me.dunkStyle===4);
    G.slowFactor=flashy?0.28:0.33;
    G.slowT=G.ball.dur/G.slowFactor+0.25;
  }
}
// The make chance for a shot, extracted from resolveShot so the shooter
// can pre-compute it in PvP (both phones must agree). Returns true/false.
function computeMake(shooter,type,pts,meter){
  if(shooter.onFire||(G.fire&&G.fire.team===shooter.team)) return true;
  if(meter!==null&&meter!==undefined&&meter>=GREEN_LOW&&meter<=GREEN_HIGH) return true;
  const nd=nearestDef(shooter);
  let pr=type==='shot'?(pts===2?0.36:0.55):0.95;
  if(nd>22) pr+=0.12; if(nd<10) pr-=0.10;
  if(shooter.team===1) pr*=cpuDiff().shot;
  if(meter!==null&&meter!==undefined){
    let q;
    if(meter<GREEN_LOW) q=0.15+0.85*(meter/GREEN_LOW);
    else if(meter<=GREEN_HIGH) q=1;
    else q=Math.max(0,1-(meter-GREEN_HIGH)/(1-GREEN_HIGH));
    pr*=(0.2+0.8*q);
  }
  return Math.random()<clamp(pr,0.05,0.98);
}
function scoreBall(p,pts,type,perfect){
  G.score[p.team]+=pts;
  p.streak++;
  G.players.forEach(function(q){if(q!==p)q.streak=0;});
  const isDunk=(type==='dunk'||type==='turboDunk');
  const dunkName=isDunk?DUNK_STYLES[(p.dunkStyle!==undefined&&p.dunkStyle!==null)?p.dunkStyle:1].name:null;
  if(p.streak>=3&&G.fire!==p){ G.fire=p; p.onFire=true; callout('ON FIRE!',dunkName?dunkName+'!':''); swish(); }
  else if(perfect){ callout('GREEN!','+'+pts); swish(); }
  else if(isDunk){ G.shake=0.35; callout(dunkName+'!','+'+pts); swish(); }
  else if(pts===2){ callout('FROM DOWNTOWN!','+2'); swish(); }
  else { callout('SWISH!','+'+pts); swish(); }
  G.players.forEach(function(q){if(q.team!==p.team){q.onFire=false;q.streak=0;}});
  if(G.fire&&G.fire.team!==p.team) G.fire=null;
  updateScore();
  if(G.score[p.team]>=TARGET&&G.score[p.team]>G.score[1-p.team]){ endGame(p.team); return; }
  G.pause=1.1; G.afterPause=true; G.nextPoss=1-p.team;
}
function resolveShot(b){
  if(b.blocked){
    G.ball={state:'loose',x:b.shooter.x,z:b.shooter.z,h:30,hv:120,lastTouch:b.shooter.team};
    callout('BLOCKED!','');
    return;
  }
  let make=false;
  if(b.shooter.onFire||(G.fire&&G.fire.team===b.shooter.team)) make=true;
  else if(b.perfect) make=true;
  else if(b.make!==undefined&&b.make!==null){
    // PvP: the shooter pre-computed the make and posted it -- use it,
    // do not re-roll, so both phones agree.
    make=!!b.make;
  }
  else {
    const nd=nearestDef(b.shooter);
    let pr=b.type==='shot'?(b.pts===2?0.36:0.55):0.95;
    if(nd>22) pr+=0.12; if(nd<10) pr-=0.10;
    // computer difficulty: the CPU team (AWAY) shoots better on higher
    // levels; the user's shots and the teammate's shots are untouched
    if(b.shooter.team===1) pr*=cpuDiff().shot;
    if(b.meter!==null&&b.meter!==undefined){
      // shot-meter timing: green = full chance, below green = worse the further
      // from green, overfill past green = worse the further past it
      let q;
      if(b.meter<GREEN_LOW) q=0.15+0.85*(b.meter/GREEN_LOW);
      else if(b.meter<=GREEN_HIGH) q=1;
      else q=Math.max(0,1-(b.meter-GREEN_HIGH)/(1-GREEN_HIGH));
      pr*=(0.2+0.8*q);
    }
    make=Math.random()<clamp(pr,0.05,0.98);
  }
  if(make){
    if(b.type!=='shot'){
      // dunk: the ball starts at rim height, over the rim centre, and drops
      // straight down through the net — it never teleports into the net
      const rimWX=b.hoop.x+(b.hoop.x>0?-3.25:3.25); // rim centre in world x
      const rimH=proj(b.hoop.x,b.hoop.z).y-rimScreen(b.hoop).y; // floor-to-rim height in px
      G.ball={state:'loose',x:rimWX,z:b.hoop.z,h:rimH,hv:-60,lastTouch:b.shooter.team};
      G.netSnap=1; // the net snaps as the ball goes through
    }
    scoreBall(b.shooter,b.pts,b.type,b.perfect);
  }
  else {
    b.shooter.streak=0; // a miss breaks the shooter's streak — 3 in a row must be consecutive
    const hoop=b.hoop;
    G.ball={state:'loose',x:clamp(hoop.x+(Math.random()*36-18),-118,118),z:clamp(hoop.z+(Math.random()*16-8),2,44),h:26,hv:150,lastTouch:b.shooter.team};
    callout('OFF THE RIM!','');
  }
}
function outOfBounds(team){
  callout('OUT OF BOUNDS','');
  G.pause=0.9; G.afterPause=true; G.nextPoss=team;
}
function endGame(team){
  G.mode='over';
  whistle();
  $('finalTitle').textContent=team===0?'HOME WINS!':'AWAY WINS!';
  $('finalScore').innerHTML='<span class="h">'+G.score[0]+'</span> &ndash; <span class="a">'+G.score[1]+'</span>';
  $('finalNote').textContent='First to '+TARGET+' by 1. Difficulty: '+cpuDiff().name+' (level '+G.difficulty+' of 5). '+(team===0?'Home takes it at the park.':'Away takes it at the park.');
  $('endOverlay').classList.remove('hidden');
}

/* ---------- input ---------- */
function bindHold(el,down,up){
  const on=function(e){e.preventDefault();down();el.classList.add('on');};
  const off=function(e){e.preventDefault();up();el.classList.remove('on');};
  el.addEventListener('pointerdown',on);
  el.addEventListener('pointerup',off);
  el.addEventListener('pointerleave',off);
  el.addEventListener('pointercancel',off);
  el.addEventListener('contextmenu',function(e){e.preventDefault();});
}
/* ---------- virtual joystick (bottom-left) ---------- */
const STICK_R=48; // max knob travel in px (160px base, 64px knob)
const stickEl=$('stick'), stickKnob=$('stickKnob');
let stickPid=null;
function stickSet(dx,dy){
  let m=Math.hypot(dx,dy);
  if(m>1){ dx/=m; dy/=m; m=1; }
  if(m<0.12){ dx=0; dy=0; } // dead zone — no drift from a light touch
  stick.x=dx; stick.y=dy;
  stickKnob.style.transform='translate(calc(-50% + '+(dx*STICK_R).toFixed(1)+'px), calc(-50% + '+(dy*STICK_R).toFixed(1)+'px))';
}
function stickFromEvent(e){
  const r=stickEl.getBoundingClientRect();
  const cx=r.left+r.width/2, cy=r.top+r.height/2;
  stickSet((e.clientX-cx)/STICK_R,(e.clientY-cy)/STICK_R);
}
function stickEnd(e){
  if(stickPid===null||e.pointerId===stickPid){ stickPid=null; stickSet(0,0); }
}
stickEl.addEventListener('pointerdown',function(e){ e.preventDefault(); stickPid=e.pointerId; try{ stickEl.setPointerCapture(e.pointerId); }catch(err){} stickFromEvent(e); });
stickEl.addEventListener('pointermove',function(e){ if(e.pointerId===stickPid) stickFromEvent(e); });
stickEl.addEventListener('pointerup',stickEnd);
stickEl.addEventListener('pointercancel',stickEnd);
stickEl.addEventListener('contextmenu',function(e){e.preventDefault();});
function setStick(x,y){ stickSet(x||0,y||0); } // drive helper (also used by tests)
bindHold($('btnTurbo'),function(){G.turboHeld=true;},function(){G.turboHeld=false;});
$('btnShoot').addEventListener('pointerdown',function(e){e.preventDefault();shootPress();});
['pointerup','pointerleave','pointercancel'].forEach(function(ev){ $('btnShoot').addEventListener(ev,function(e){e.preventDefault();shootRelease();}); });
$('btnPass').addEventListener('pointerdown',function(e){e.preventDefault();doPass();});
window.addEventListener('keydown',function(e){
  if(!$('gameView').classList.contains('open')) return;
  const k=e.key.toLowerCase();
  if(k==='arrowup'||k==='w') dirs.up=true;
  if(k==='arrowdown') dirs.down=true;
  if(k==='arrowleft'||k==='a') dirs.left=true;
  if(k==='arrowright'||k==='d') dirs.right=true;
  if(k==='s'||k===' ') { if(!e.repeat) shootPress(); }
  if(k==='p'&&!e.repeat) doPass();
  if(k==='shift') G.turboHeld=true;
  if(['arrowup','arrowdown','arrowleft','arrowright',' '].indexOf(k)>=0) e.preventDefault();
});
window.addEventListener('keyup',function(e){
  const k=e.key.toLowerCase();
  if(k==='arrowup'||k==='w') dirs.up=false;
  if(k==='arrowdown') dirs.down=false;
  if(k==='arrowleft'||k==='a') dirs.left=false;
  if(k==='arrowright'||k==='d') dirs.right=false;
  if(k==='s'||k===' ') shootRelease();
  if(k==='shift') G.turboHeld=false;
});
function selectDiff(lvl){
  diffSel=lvl;
  for(let i=1;i<=5;i++){
    const b=$('diffBtn'+i);
    if(!b) continue;
    if(i===lvl) b.classList.add('sel'); else b.classList.remove('sel');
  }
  $('diffDesc').textContent=DIFFS[lvl-1].desc;
}
for(let i=1;i<=5;i++){
  (function(lvl){
    const b=$('diffBtn'+lvl);
    if(b) b.addEventListener('click',function(){ selectDiff(lvl); });
  })(i);
}
$('startBtn').addEventListener('click',startGame);
$('rematchBtn').addEventListener('click',startGame);
$('startBackBtn').addEventListener('click',closeGame);
$('endBackBtn').addEventListener('click',closeGame);
$('backBtn').addEventListener('click',closeGame);
/* ---------- PvP room (create / join) ---------- */
function pvpSetStatus(t){ var el=document.getElementById('pvpStatus'); if(el) el.textContent=t; }
function pvpSetRoomLbl(t){ var el=document.getElementById('pvpRoomLbl'); if(el) el.textContent=t; }
$('pvpBtn').addEventListener('click',function(){
  document.getElementById('pvpPanel').classList.toggle('hidden');
});
$('pvpCreateBtn').addEventListener('click',function(){
  var who=pvpPlayer();
  pvpSetStatus('Creating room...');
  pvpPost('/create',{player_id:who.id,player_name:who.name,game:'basketball'}).then(function(room){
    if(!room||!room.code){ pvpSetStatus('Could not create a room — check your connection and try again.'); return; }
    G.myTeam=0; // host is HOME (red)
    G.pvp={code:room.code,role:'host',oppName:'',seq:0,lastSeenSeq:0,pollTimer:null,posT:0};
    pvpSetStatus('Room created! Give this code to the other player:');
    pvpSetRoomLbl('CODE: '+room.code+' — waiting for them to join...');
    pvpStartPoll();
  });
});
// JOIN fires on pointerdown (before the phone keyboard closes and the
// layout shifts, which made the 'click' miss the button), plus click and
// Enter as fallbacks. pvpJoining stops a double join from one tap.
var pvpJoining=false;
function pvpDoJoin(e){
  if(e&&e.type==='pointerdown') e.preventDefault();
  if(pvpJoining) return;
  var input=document.getElementById('pvpCodeInput');
  var code=(input.value||'').replace(/[^0-9]/g,'');
  if(input.blur) input.blur();
  if(!/^[0-9]{4}$/.test(code)){ pvpSetStatus('Enter the 4-digit code from the other phone.'); return; }
  var who=pvpPlayer();
  pvpJoining=true;
  pvpSetStatus('Joining room '+code+'...');
  pvpPost('/join',{code:code,player_id:who.id,player_name:who.name}).then(function(room){
    pvpJoining=false;
    if(!room||!room.code){ pvpSetStatus('Could not join room '+code+' — check the code (the host cannot join their own room).'); return; }
    G.myTeam=1; // guest is AWAY (blue)
    G.pvp={code:room.code,role:'guest',oppName:room.host_name||'Opponent',seq:0,lastSeenSeq:0,pollTimer:null,posT:0};
    pvpSetStatus('Joined! You are AWAY (blue).');
    pvpSetRoomLbl('CODE: '+room.code+' — vs '+G.pvp.oppName);
    pvpStartPoll();
    pvpPollOnce();
  });
}
$('pvpJoinBtn').addEventListener('pointerdown',pvpDoJoin);
$('pvpJoinBtn').addEventListener('click',pvpDoJoin);
$('pvpCodeInput').addEventListener('keydown',function(e){ if(e.key==='Enter') pvpDoJoin(e); });
window.addEventListener('resize',fitCanvas);

function fitCanvas(){
  const w=$('canvasWrap'); if(!w) return;
  const r=w.getBoundingClientRect();
  const scale=Math.min(r.width/W,r.height/H);
  cv.style.width=(W*scale)+'px'; cv.style.height=(H*scale)+'px';
  cv.style.left=((r.width-W*scale)/2)+'px'; cv.style.top=((r.height-H*scale)/2)+'px';
}
function openGame(){
  $('gameView').classList.add('open');
  $('endOverlay').classList.add('hidden');
  $('startOverlay').classList.remove('hidden');
  G.mode='start';
  newGame();
  fitCanvas();
}
function startGame(){
  $('startOverlay').classList.add('hidden');
  $('endOverlay').classList.add('hidden');
  G.difficulty=diffSel;
  $('diffChip').textContent=cpuDiff().name;
  newGame();
  G.mode='play';
  callout('TIP OFF!','');
  fitCanvas();
  if(pvpIsOn()&&G.pvp.role==='host'&&!G.pvp.syncStart){
    // Post the initial state so the guest's game starts too.
    // (A rejoining host does NOT post -- the room already has the game.)
    pvpPostState(null);
  }
}
function closeGame(){
  if(window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
}

/* ---------- AI + update ---------- */
function moveToward(p,tx,tz,sp,dt){
  const dx=tx-p.x,dz=tz-p.z,dd=Math.hypot(dx,dz);
  if(dd<2) return;
  p.x=clamp(p.x+dx/dd*sp*dt,CX0-4,CX1+4);
  p.z=clamp(p.z+dz/dd*sp*dt,CZ0-4,CZ1+4);
}
function updateAI(dt){
  const bh=holder();
  const D=cpuDiff();
  // PvP: the opponent's controlled player is a real person -- the AI
  // must not drive them. (In PvC this is null and nothing changes.)
  var oppCtrl=pvpIsOn()?pvpOppCtrl():null;
  G.players.forEach(function(p,i){
    if(i===G.user) return;
    if(oppCtrl&&p===oppCtrl) return;
    if(p.stumble>0){ p.stumble-=dt; return; }
    if(p.cool>0) p.cool-=dt;
    if(p.shootCd>0) p.shootCd-=dt;
    let tx=null,tz=null,sp=55,reacting=false;
    if(G.ball&&G.ball.state==='loose'){ tx=G.ball.x; tz=G.ball.z; sp=62; }
    else if(p.team===G.possession){
      if(p.hasBall){
        const hoop=targetHoop(p.team);
        const d=d2(p.x,p.z,hoop.x,hoop.z);
        if(d<=DUNK_D){ startShot(p,'dunk',1); return; }
        const nd=nearestDef(p);
        if(d<42&&p.shootCd<=0&&(nd>20||d<26)){ startShot(p,'shot',d>=THREE?2:1); return; }
        tx=hoop.x; tz=hoop.z; sp=58;
      } else {
        const hoop=targetHoop(p.team);
        tx=hoop.x*0.55; tz=34+Math.sin(G.elapsed*0.7+p.num*2)*4;
      }
    } else if(bh){
      // CPU defenders are slow to react to a new ball-handler on low
      // difficulties — they stand still for a beat instead of chasing
      reacting=(p.team===1&&G.elapsed-(G.bhSince||0)<D.react);
      const defs=G.players.filter(function(q){return q.team===p.team;});
      let nearest=defs[0],bd=1e9;
      defs.forEach(function(q){const d=d2(q.x,q.z,bh.x,bh.z);if(d<bd){bd=d;nearest=q;}});
      if(p===nearest){
        const hoop=targetHoop(bh.team);
        const dx=bh.x-hoop.x,dz=bh.z-hoop.z,dd=Math.hypot(dx,dz);
        // guard on the midcourt side of the ball-handler; when the handler
        // is right at the rim, guarding "between holder and hoop" would put
        // the defender on top of the holder and shove him out of bounds
        if(dd<8){ tx=bh.x+(hoop.x>0?-13:13); tz=bh.z; }
        else { tx=bh.x+dx/dd*13; tz=bh.z+dz/dd*13; }
        // AI steal attempt when close to the ball-handler (CPU steals more
        // often and more successfully on higher difficulties)
        if(bd<14&&p.cool<=0&&Math.random()<dt*0.6*(p.team===1?D.stealRate:1)){
          p.cool=1.1;
          if(Math.random()<(p.team===1?D.stealP:0.25)){
            bh.hasBall=false; bh.streak=0;
            p.hasBall=true; G.possession=p.team;
            G.players.forEach(function(q){q.streak=0;});
            callout('STEAL!','');
            updateUserControl();
          }
        }
      } else {
        const mate=G.players.find(function(q){return q.team===bh.team&&q!==bh;});
        const hoop=targetHoop(bh.team);
        const dx=mate.x-hoop.x,dz=mate.z-hoop.z,dd=Math.max(1,Math.hypot(dx,dz));
        tx=mate.x+dx/dd*10; tz=mate.z+dz/dd*10;
      }
    }
    // CPU team moves faster on higher difficulties; the user's AI teammate
    // stays at fixed speed. A reacting CPU defender stands still.
    if(tx!==null&&!reacting) moveToward(p,tx,tz,sp*(p.team===1?D.speed:1),dt);
  });
}
  /* ---------- animation state (poses, dribble, run cycle, meter) ---------- */
  function updateAnim(dt){
    G.players.forEach(function(p){
      const prevPose=p.pose;
      // velocity from last frame
      const vx=(p.x-p.px)/Math.max(dt,0.001), vz=(p.z-p.pz)/Math.max(dt,0.001);
      const spd=Math.hypot(vx,vz);
      p.moving=spd>8;
      if(p.moving){ p.step+=spd*dt*0.055; if(Math.abs(vx)>4) p.face=vx>0?1:-1; }
      if(p.hasBall){ p.drib=(p.drib+dt/0.55)%1; p.face=(targetHoop(p.team).x>p.x)?1:-1; }
      // shot meter charge (jump shots only)
      if(p.charge!==null&&p.charge!==undefined){
        if(!p.hasBall) p.charge=null;
        else p.charge=Math.min(1,p.charge+dt/METER_FILL_TIME);
      }
      // locked poses clear on landing / timeout
      if(p.pose==='pass'){ if(p.poseT>0.3) p.pose=null; }
      else if(p.pose==='shoot'||p.pose==='dunk'||p.pose==='block'){
        if(p.jz===0&&p.jv===0&&p.poseT>0.12) p.pose=null;
      }
      // continuous poses are recomputed every frame
      if(!p.pose||p.pose==='idle'||p.pose==='run'||p.pose==='dribble'||p.pose==='stumble'||p.pose==='aim'||p.pose==='jump'){
        let np;
        if(p.charge!==null&&p.charge!==undefined) np='aim';
        else if(p.stumble>0) np='stumble';
        else if(p.hasBall) np='dribble';
        else if(p.jz>4) np='jump';
        else if(p.moving) np='run';
        else np='idle';
        p.pose=np;
      }
      p.poseT=(p.pose===prevPose)?p.poseT+dt:0;
      p.px=p.x; p.pz=p.z;
    });
  }
function updateBall(dt){
  const b=G.ball; if(!b) return;
  if(b.state==='pass'){
    b.t+=dt/b.dur;
    const t=Math.min(1,b.t);
    b.sx=lerp(b.fx,b.receiver?proj(b.receiver.x,b.receiver.z).x:b.tx,t);
    b.sy=lerp(b.fy,proj(b.receiver.x,b.receiver.z).y-30,t)-40*Math.sin(Math.PI*t);
    if(b.t>=1){
      const r=b.receiver;
      if(r&&d2(r.x,r.z,b.rx,b.rz)<34){
        r.hasBall=true; r.shootCd=0.5; G.ball={state:'held',x:r.x,z:r.z,h:0}; G.possession=r.team;
        updateUserControl();
      } else {
        G.ball={state:'loose',x:b.rx,z:b.rz,h:10,hv:60,lastTouch:b.lastTouch};
      }
    }
  } else if(b.state==='shot'){
    b.t+=dt/b.dur;
    const t=Math.min(1,b.t);
    if(b.type==='shot'&&!b.blocked){
      // jump shot: recompute the screen path from world coords every frame
      // so the ball tracks the rim while the close-up camera pans.
      // Fly to the RIM CENTRE, not the pole: the rim sticks 26 screen px
      // toward midcourt from the pole (3.25 world units), so aiming at
      // the pole left the ball 26px short of the rim — the same shortfall
      // the dunk fix already corrected.
      const rimWX=b.hoop.x+(b.hoop.x>0?-3.25:3.25);
      const wx=lerp(b.shooter.x,rimWX,t), wz=lerp(b.shooter.z,b.hoop.z,t);
      const pr=proj(wx,wz);
      const pr0=proj(b.shooter.x,b.shooter.z);
      b.sx=pr.x;
      b.sy=lerp(pr0.y-46*pr0.s,270,t)-4*150*t*(1-t);
    } else {
      b.sx=lerp(b.fx,b.tx,t);
      b.sy=lerp(b.fy,b.ty,t)-4*150*t*(1-t);
    }
    // dunk: shooter flies to the RIM — the rim sticks 26 screen px toward
    // midcourt from the pole, which is 3.25 world units (26 / 5.0 / ZOOM).
    // Flying to the pole minus 6 used to leave the ball a hand's width short
    // of the rim, so the slam never connected.
    if(b.type!=='shot'){
      const sh=b.shooter;
      const rimWX=b.hoop.x+(b.hoop.x>0?-3.25:3.25); // rim centre in world x
      sh.x=lerp(sh.x,rimWX,t*0.9);
      sh.z=lerp(sh.z,b.hoop.z,t*0.9);
      sh.jz=Math.sin(Math.PI*t)*80;
      const spr=proj(sh.x,sh.z);
      const style=(b.dunkStyle!==undefined&&DUNK_STYLES[b.dunkStyle])?DUNK_STYLES[b.dunkStyle]:DUNK_STYLES[1];
      const sTop=spr.y-67*spr.s-(sh.jz||0);
      if(style.id==='spin360'){
        // the ball rides in the hands while the body spins like a top — it
        // circles the body center on the same fast spin angle and comes
        // back to the top at the rim
        const cx=spr.x, cy=spr.y-33.5*spr.s-(sh.jz||0);
        const ang=spinAngle(t);
        b.sx=cx+43*spr.s*Math.sin(ang);
        b.sy=cy-43*spr.s*Math.cos(ang);
      } else if(style.id==='tomahawk'){
        // windmill: the dunk arm cranks a FULL circle around the shoulder
        // (like turning a knob all the way around) — the ball swings down
        // behind the head, around below, up in front and over the top,
        // then comes down through the rim
        const cx=spr.x, cy=spr.y-40*spr.s-(sh.jz||0), R=34*spr.s;
        if(t<0.75){
          const ang=-2.6-Math.PI*2*Math.min(1,t/0.75); // one full turn, ending cocked behind the head
          b.sx=cx+Math.cos(ang)*R;
          b.sy=cy+Math.sin(ang)*R;
        } else {
          const tt=(t-0.75)/0.25;
          b.sx=lerp(cx+Math.cos(-2.6)*R,spr.x,tt); // cos/sin of (-2.6-2π) == cos/sin of -2.6
          b.sy=lerp(cy+Math.sin(-2.6)*R,sTop-10*spr.s,tt);
        }
      } else if(style.id==='reverse'){
        // the player turns mid-air: the ball travels from in front of the
        // head to behind it and slams down backwards
        const dir=(b.hoop.x>sh.x)?1:-1;
        b.sx=spr.x+lerp(dir*6*spr.s,-dir*16*spr.s,Math.min(1,t/0.6));
        b.sy=sTop-10*spr.s;
      } else if(style.id==='onehand'){
        // one arm up with the ball, cocked to the hoop side
        const dir=(b.hoop.x>sh.x)?1:-1;
        b.sx=spr.x+dir*10*spr.s;
        b.sy=sTop-8*spr.s;
      } else { // twohand: the ball rides in both raised hands to the rim
        b.sx=spr.x; b.sy=sTop-10*spr.s;
      }
      // every style ends at the rim: blend the ball onto the rim centre as
      // the dunk peaks, so the slam connects instead of floating beside the
      // hoop. By t=0.9 the ball is exactly on the rim; it stays there for
      // the stuff until the shot resolves.
      const rim=rimScreen(b.hoop);
      const rb=smoothstep(0.6,0.9,t);
      b.sx=lerp(b.sx,rim.x,rb);
      b.sy=lerp(b.sy,rim.y,rb);
      // wind trails: record the dunker's screen pos + ball pos every time
      // he has moved a few px, so the trail stretches out behind him as
      // he soars (dunks only — jump shots never record). Capped so the
      // trail stays a short streak, not a full flight path.
      const tpy=spr.y-33*spr.s-(sh.jz||0);
      const lastTr=G.trail[G.trail.length-1];
      if(!lastTr||Math.hypot(spr.x-lastTr.px,tpy-lastTr.py)>=4){
        G.trail.push({px:spr.x,py:tpy,ps:spr.s,bx:b.sx,by:b.sy,bs:spr.s,team:sh.team,wx:sh.x});
        if(G.trail.length>16) G.trail.shift();
      }
    }
    // a defender jumping near the hoop while a jump shot comes down just
    // swats it — the ball is knocked down, no basket counts.
    // (Fire shots can't be swatted — the ball is unstoppable.)
    // Blocked shots are swatted at the shooter and never reach the rim.
    if(b.type==='shot'&&t>0.45&&!b.blocked&&!b.shooter.onFire&&!(G.fire&&G.fire.team===b.shooter.team)){
      let swatted=false;
      G.players.forEach(function(p){
        if(p.team!==b.shooter.team&&p.jz>8&&d2(p.x,p.z,b.hoop.x,b.hoop.z)<17) swatted=true;
      });
      if(swatted){
        G.ball={state:'loose',x:b.hoop.x,z:b.hoop.z,h:30,hv:-80,lastTouch:b.shooter.team};
        callout('BLOCKED!','');
        return;
      }
    }
    if(b.t>=1){ if(b.type!=='shot'){ b.shooter.jz=0; b.shooter.jv=0; } resolveShot(b); }
  } else if(b.state==='loose'){
    b.hv-=1400*dt; b.h+=b.hv*dt;
    if(b.h<=0){ b.h=0; b.hv=-b.hv*0.42; if(Math.abs(b.hv)<90) b.hv=0; }
    if(b.x<CX0||b.x>CX1||b.z<CZ0||b.z>CZ1){ outOfBounds(1-b.lastTouch); G.ball={state:'held',x:0,z:23,h:0}; return; }
    if(b.h===0){
      let got=null;
      G.players.forEach(function(p){ if(!got&&d2(p.x,p.z,b.x,b.z)<12) got=p; });
      if(got){
        got.hasBall=true; got.shootCd=0.8; G.ball={state:'held',x:got.x,z:got.z,h:0};
        G.possession=got.team; updateUserControl();
      }
    }
  } else if(b.state==='held'){
    const h=holder();
    if(h){ b.x=h.x; b.z=h.z; }
  }
}
function update(dt){
  // slow motion (dunks): bookkeeping runs on real time and the time scale
  // eases in and out, so the dunk feels dramatic rather than sluggish
  if(G.slowT>0) G.slowT-=dt;
  const slowTarget=G.slowT>0?G.slowFactor:1;
  G.ts+=(slowTarget-G.ts)*Math.min(1,dt*10);
  G.elapsed+=dt*G.ts;
  if(G.shake>0) G.shake=Math.max(0,G.shake-dt*G.ts);
  if(G.netSnap>0) G.netSnap=Math.max(0,G.netSnap-dt*2.2); // the net relaxes after the snap
  if(G.pause>0){
    G.pause-=dt; // pause runs on real time — the post-score beat is not stretched
    if(G.ball&&G.ball.state==='loose') updateBall(dt); // the dunked ball keeps falling through the net during the beat
    if(G.pause<=0&&G.afterPause){
      G.afterPause=false;
      resetPositions(G.nextPoss);
      callout(G.nextPoss===0?'HOME BALL':'AWAY BALL','');
    }
    return;
  }
  dt=dt*G.ts; // everything below (movement, AI, anim, ball, camera) runs at the eased time scale
  // user movement
  const me=G.players[G.user];
  if(me){
    if(me.charge!==null&&me.charge!==undefined){ /* planted while charging the shot meter */ }
    else if(me.stumble>0) me.stumble-=dt;
    else {
      let sp=62;
      const turboOn=G.turboHeld&&G.turbo>1;
      if(turboOn){ sp*=1.55; G.turbo=Math.max(0,G.turbo-45*dt); }
      else G.turbo=Math.min(100,G.turbo+18*dt);
      const dx=(dirs.right?1:0)-(dirs.left?1:0)+stick.x;
      const dz=(dirs.down?1:0)-(dirs.up?1:0)+stick.y;
      const len=Math.hypot(dx,dz)||1;
      const stickMag=Math.min(1,Math.hypot(stick.x,stick.y));
      const speedScale=(stick.x||stick.y)?stickMag:1; // slight tilt = slow walk, full tilt = full run
      if(dx||dz){
        me.x=clamp(me.x+dx/len*sp*speedScale*dt,CX0-4,CX1+4);
        me.z=clamp(me.z+dz/len*sp*speedScale*dt,CZ0-4,CZ1+4);
      }
    }
    if(me.cool>0) me.cool-=dt;
    if(me.shootCd>0) me.shootCd-=dt;
  }
  // jump physics
  G.players.forEach(function(p){
    if(p.jz>0||p.jv>0){ p.jv-=1400*dt; p.jz+=p.jv*dt; if(p.jz<=0){p.jz=0;p.jv=0;} }
  });
  updateAI(dt);
  // soft separation
  for(let i=0;i<G.players.length;i++) for(let j=i+1;j<G.players.length;j++){
    const a=G.players[i],b=G.players[j];
    const dx=b.x-a.x,dz=b.z-a.z,dd=Math.hypot(dx,dz);
    if(dd>0.01&&dd<6){ const push=(6-dd)/2,ux=dx/dd,uz=dz/dd; a.x-=ux*push; a.z-=uz*push; b.x+=ux*push; b.z+=uz*push; }
  }
  updateAnim(dt);
  updateBall(dt);
  // out of bounds with the ball
  const bh=holder();
  if(bh&&(bh.x<CX0||bh.x>CX1||bh.z<CZ0||bh.z>CZ1)){
    bh.hasBall=false;
    outOfBounds(1-bh.team);
    G.ball={state:'held',x:0,z:23,h:0};
  }
  // close-up camera follows the ball, with a little lookahead in the
  // direction the ball is travelling so the play stays readable
  const bx=G.ball?G.ball.x:0;
  const bvx=(bx-G._prevBX)/Math.max(dt,0.001);
  G._prevBX=bx;
  const look=clamp(bvx*0.22,-18,18);
  G.camX=lerp(G.camX,clamp(bx+look,-CAM_MAX,CAM_MAX),1-Math.exp(-5*dt));
  // defense user control refresh
  G.defT-=dt;
  if(G.defT<=0){ G.defT=0.6; if(G.possession!==G.myTeam) updateUserControl(); }
  // PvP: the opponent's controlled player glides toward their posted
  // spot (no teleporting), and my position is posted ~4x a second.
  // The holder is posted when it changes (the ball is the authority).
  if(pvpIsOn()){
    var op=pvpOppCtrl();
    if(op&&typeof op.tx==='number'&&typeof op.tz==='number'){
      var odx=op.tx-op.x,odz=op.tz-op.z;
      var od=Math.hypot(odx,odz);
      if(od>2){
        var os=Math.min(od,400*dt);
        op.x+=(odx/od)*os; op.z+=(odz/od)*os;
        op.moving=true; op.step+=os*0.055;
        op.face=(odx>=0)?1:-1;
        op.x=clamp(op.x,CX0-4,CX1+4); op.z=clamp(op.z,CZ0-4,CZ1+4);
      } else {
        op.moving=false;
      }
    }
    var h=holder();
    if(h!==G.lastHolder){
      G.lastHolder=h;
      pvpPostState(null);
    } else {
      G.pvp.posT=(G.pvp.posT||0)+dt;
      if(G.pvp.posT>=0.25){
        G.pvp.posT=0;
        pvpPostState(null);
      }
    }
  }
  // HUD
  $('gameClock').textContent=fmtT(G.elapsed);
  $('turboFill').style.width=G.turbo+'%';
}

/* ---------- drawing ---------- */
function roundRect(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y); ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r); ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }
function drawBackground(){
  // sky (gradient is uniform, so it needs no panning)
  const sky=ctx.createLinearGradient(0,0,0,300);
  sky.addColorStop(0,'#6fb7f0'); sky.addColorStop(1,'#cfeefb');
  ctx.fillStyle=sky; ctx.fillRect(0,0,W,300);
  // sun + clouds drift slowly with the camera (far parallax)
  ctx.fillStyle='#fff3a0'; ctx.beginPath(); ctx.arc(780-G.camX*1.2,60,28,0,7); ctx.fill();
  ctx.fillStyle='rgba(255,255,255,.9)';
  [[150,60],[420,90],[640,50]].forEach(function(pt){const cx=pt[0]-G.camX*1.2;ctx.beginPath();ctx.ellipse(cx,pt[1],60,15,0,0,7);ctx.ellipse(cx+36,pt[1]+5,42,11,0,0,7);ctx.fill();});
  // trees (parallax with camera, zoomed to match the close-up)
  for(let tx=-200;tx<=200;tx+=26){
    const sx=W/2+(tx-G.camX*0.35)*5.0*ZOOM;
    const r=(26+((tx*13)%18))*ZOOM;
    ctx.fillStyle='#6b4a2b'; ctx.fillRect(sx-4*ZOOM,236,8*ZOOM,26*ZOOM);
    ctx.fillStyle='#2f7d33'; ctx.beginPath(); ctx.arc(sx,224,r,0,7); ctx.fill();
    ctx.fillStyle='#3c9a40'; ctx.beginPath(); ctx.arc(sx-r*0.4,212,r*0.7,0,7); ctx.fill();
  }
  // grass
  ctx.fillStyle='#4e9b47'; ctx.fillRect(0,258,W,90);
  ctx.fillStyle='#67b35e'; ctx.fillRect(0,258,W,10);
  ctx.fillStyle='rgba(0,0,0,.08)';
  for(let i=0;i<120;i++){ const sx=(((i*73-G.camX*8)%1000)+1000)%1000-50; ctx.fillRect(sx,262+((i*31)%80),3,3); }
  // path
  ctx.fillStyle='#d9c49a'; ctx.fillRect(0,318,W,16);
  // fence (horizontal rails are uniform; the posts pan with the camera)
  ctx.strokeStyle='rgba(200,200,200,.8)'; ctx.lineWidth=2;
  for(let y=306;y<=330;y+=8){ ctx.beginPath(); ctx.moveTo(0,y); ctx.lineTo(W,y); ctx.stroke(); }
  ctx.strokeStyle='#666';
  for(let wx=-170;wx<=170;wx+=12){ const sx=W/2+(wx-G.camX)*5.0*ZOOM; ctx.beginPath(); ctx.moveTo(sx,300); ctx.lineTo(sx,336); ctx.stroke(); }
  // benches (world-anchored, pan at full camera speed)
  [-95,-20,55,115].forEach(function(wx){
    const sx=W/2+(wx-G.camX)*5.0*ZOOM;
    ctx.fillStyle='#7a4a21'; ctx.fillRect(sx,318,64*ZOOM,7*ZOOM); ctx.fillRect(sx,318-14*ZOOM,64*ZOOM,7*ZOOM);
    ctx.fillStyle='#5b3a18'; ctx.fillRect(sx+5*ZOOM,318+7*ZOOM,5*ZOOM,12*ZOOM); ctx.fillRect(sx+54*ZOOM,318+7*ZOOM,5*ZOOM,12*ZOOM);
  });
  // playground slide (far left end of the park, pans with the camera)
  const slx=W/2+(-108-G.camX)*5.0*ZOOM;
  ctx.fillStyle='#c0392b'; ctx.beginPath(); ctx.moveTo(slx,258); ctx.lineTo(slx+34*ZOOM,258); ctx.lineTo(slx+22*ZOOM,320); ctx.lineTo(slx+10*ZOOM,320); ctx.closePath(); ctx.fill();
  ctx.fillStyle='#8e44ad'; ctx.fillRect(slx-8*ZOOM,238,46*ZOOM,22);
  // foreground grass strip (below the court's far edge, now deeper with zoom)
  ctx.fillStyle='#3c7a35'; ctx.fillRect(0,588,W,H-588);
}
function drawCourt(){
  const c1=proj(CX0,CZ0),c2=proj(CX1,CZ0),c3=proj(CX1,CZ1),c4=proj(CX0,CZ1);
  ctx.fillStyle='#6e7f8c';
  ctx.beginPath(); ctx.moveTo(c1.x,c1.y); ctx.lineTo(c2.x,c2.y); ctx.lineTo(c3.x,c3.y); ctx.lineTo(c4.x,c4.y); ctx.closePath(); ctx.fill();
  // test instrumentation (harmless in play): world coords of every marking, so the
  // smoke suite can prove the lines sit where the rules say they do
  G._courtMarks={foulLines:[],ftCircles:[],arcs:[],keys:[],
    centerLine:{x:0,z0:CZ0,z1:CZ1},centerCircle:{cx:0,cz:23,r:12}};
  // polyline through projected world points, stroked as one path
  function arcPts(cx,cz,r,a0,a1,step){
    const pts=[];
    for(let a=a0;a<=a1+0.001;a+=step){ pts.push(proj(cx+r*Math.cos(a),cz+r*Math.sin(a))); }
    return pts;
  }
  function strokePts(pts){
    ctx.beginPath();
    pts.forEach(function(p,i){ if(i===0)ctx.moveTo(p.x,p.y); else ctx.lineTo(p.x,p.y); });
    ctx.stroke();
  }
  ctx.strokeStyle='#fff'; ctx.lineWidth=3;
  // ---- keys: blue paint, white outline, foul line, FT circle, restricted arc ----
  [[112,1],[-112,-1]].forEach(function(hp){
    const hx=hp[0], dir=hp[1]; // dir +1: right hoop, key extends toward -x; -1: left hoop
    const fx=hx-KEY_LEN*dir; // foul line x (18 from the hoop)
    const z0=23-KEY_HALF, z1=23+KEY_HALF;
    // painted key, shaped as a proper lane (longer than wide)
    const k1=proj(fx,z0),k2=proj(hx,z0),k3=proj(hx,z1),k4=proj(fx,z1);
    ctx.fillStyle='#3b82f6';
    ctx.beginPath(); ctx.moveTo(k1.x,k1.y); ctx.lineTo(k2.x,k2.y); ctx.lineTo(k3.x,k3.y); ctx.lineTo(k4.x,k4.y); ctx.closePath(); ctx.fill();
    ctx.beginPath(); ctx.moveTo(k1.x,k1.y); ctx.lineTo(k2.x,k2.y); ctx.lineTo(k3.x,k3.y); ctx.lineTo(k4.x,k4.y); ctx.closePath(); ctx.stroke();
    // foul line: bold white line closing the key
    const f1=proj(fx,z0),f2=proj(fx,z1);
    ctx.lineWidth=5;
    ctx.beginPath(); ctx.moveTo(f1.x,f1.y); ctx.lineTo(f2.x,f2.y); ctx.stroke();
    ctx.lineWidth=3;
    // lane hash marks along both sides of the key
    [6,10,14].forEach(function(d){
      const mx=hx-d*dir;
      [z0,z1].forEach(function(zz){
        const p1=proj(mx,zz), p2=proj(mx,zz+(zz===z0?-3:3));
        ctx.beginPath(); ctx.moveTo(p1.x,p1.y); ctx.lineTo(p2.x,p2.y); ctx.stroke();
      });
    });
    // free-throw circle: solid half toward the hoop, dashed half away from it
    const s0=dir>0?-Math.PI/2:Math.PI/2, s1=dir>0?Math.PI/2:Math.PI*3/2;
    strokePts(arcPts(fx,23,FT_R,s0,s1,0.2));
    if(ctx.setLineDash) ctx.setLineDash([6,6]);
    const d0=dir>0?Math.PI/2:-Math.PI/2, d1=dir>0?Math.PI*3/2:Math.PI/2;
    strokePts(arcPts(fx,23,FT_R,d0,d1,0.2));
    if(ctx.setLineDash) ctx.setLineDash([]);
    // restricted-area arc around the rim, opening toward midcourt
    const r0=dir>0?Math.PI/2:-Math.PI/2, r1=dir>0?Math.PI*3/2:Math.PI/2;
    strokePts(arcPts(hx,23,RA_R,r0,r1,0.2));
    G._courtMarks.foulLines.push({x:fx,z0:z0,z1:z1,hoop:hx});
    G._courtMarks.ftCircles.push({cx:fx,cz:23,r:FT_R});
    G._courtMarks.keys.push({x0:Math.min(fx,hx),x1:Math.max(fx,hx),z0:z0,z1:z1});
  });
  // baselines + sidelines
  ctx.beginPath(); ctx.moveTo(c1.x,c1.y); ctx.lineTo(c2.x,c2.y); ctx.lineTo(c3.x,c3.y); ctx.lineTo(c4.x,c4.y); ctx.closePath(); ctx.stroke();
  // half-court line
  const h1=proj(0,CZ0),h2=proj(0,CZ1);
  ctx.beginPath(); ctx.moveTo(h1.x,h1.y); ctx.lineTo(h2.x,h2.y); ctx.stroke();
  // center circle
  strokePts(arcPts(0,23,12,0,Math.PI*2,0.2));
  // 3pt arcs, clipped where they meet the sidelines
  [[112,-1],[-112,1]].forEach(function(hp){
    const hx=hp[0],sgn=hp[1];
    ctx.beginPath();
    for(let a=-ARC_A;a<=ARC_A;a+=0.12){
      const p=proj(hx+THREE*Math.cos(Math.PI+sgn*a),23+THREE*Math.sin(Math.PI+sgn*a));
      if(a===-ARC_A) ctx.moveTo(p.x,p.y); else ctx.lineTo(p.x,p.y);
    }
    ctx.stroke();
    G._courtMarks.arcs.push({hx:hx,r:THREE,aMax:ARC_A});
  });
}
function drawHoop(hoop){
  const p=proj(hoop.x,hoop.z);
  const dir=hoop.x>0?-1:1;
  ctx.strokeStyle='#333'; ctx.lineWidth=5;
  ctx.beginPath(); ctx.moveTo(p.x,p.y); ctx.lineTo(p.x,252); ctx.stroke();
  ctx.fillStyle='#fff'; ctx.fillRect(p.x-26*ZOOM,232,52*ZOOM,36*ZOOM);
  ctx.strokeStyle='#e2571e'; ctx.lineWidth=3; ctx.strokeRect(p.x-26*ZOOM,232,52*ZOOM,36*ZOOM);
  ctx.fillStyle='#e2571e'; ctx.fillRect(p.x-10*ZOOM,246,20*ZOOM,12*ZOOM);
  ctx.beginPath(); ctx.ellipse(p.x+dir*26,270,15*ZOOM,5*ZOOM,0,0,7); ctx.strokeStyle='#e2571e'; ctx.lineWidth=4; ctx.stroke();
  // net under the rim — it snaps (stretches down) when a dunk goes through
  const snap=G.netSnap||0;
  const nx=p.x+dir*26, ny=270;
  ctx.strokeStyle='rgba(255,255,255,.85)'; ctx.lineWidth=1.5;
  ctx.beginPath();
  for(let i=-1;i<=1;i++){
    ctx.moveTo(nx+i*11*ZOOM,ny+2);
    ctx.lineTo(nx+i*5*ZOOM,ny+17+snap*9);
  }
  ctx.moveTo(nx-11*ZOOM,ny+2); ctx.lineTo(nx+11*ZOOM,ny+2);
  ctx.moveTo(nx-5*ZOOM,ny+17+snap*9); ctx.lineTo(nx+5*ZOOM,ny+17+snap*9);
  ctx.stroke();
}
function heldBallPos(h){
  // where the ball sits while held: bouncing on the dribble, at the chest while aiming
  const pr=proj(h.x,h.z);
  const dir=(targetHoop(h.team).x>h.x)?1:-1;
  if(h.pose==='aim') return {x:pr.x+dir*8*pr.s, y:pr.y-34*pr.s, pr:pr, bounce:0};
  const bounce=Math.sin(Math.PI*(h.drib||0)); // 0 = in the hand, 1 = on the floor
  const ballH=(8+(1-bounce)*22)*pr.s; // height above the floor
  return {x:pr.x+dir*12*pr.s+bounce*3*pr.s, y:pr.y-ballH, pr:pr, bounce:bounce};
}
/* Two-segment limb: hip/shoulder -> joint (knee/elbow) -> foot/hand.
   The joint is the midpoint plus an explicit offset so knees bend forward
   and elbows bend out — a real leg and arm, not a stick. */
function limbJoint(x1,y1,x2,y2,ox,oy){
  return {x:(x1+x2)/2+ox, y:(y1+y2)/2+oy};
}
function limb2(x1,y1,x2,y2,jx,jy,w,col){
  G._limbCalls=(G._limbCalls||0)+1; // test instrumentation: count two-segment limbs drawn
  ctx.strokeStyle=col; ctx.lineWidth=w; ctx.lineCap='round'; ctx.lineJoin='round';
  ctx.beginPath(); ctx.moveTo(x1,y1); ctx.lineTo(jx,jy); ctx.lineTo(x2,y2); ctx.stroke();
}
function drawPlayer(p){
  const pr=proj(p.x,p.z);
  const s=pr.s;
  const pose=p.pose||'idle';
  const face=p.face||1;
  const jersey=p.team===0?'#d8232a':'#1d6fd1';
  const jerseyDark=p.team===0?'#8f161b':'#134a8f';
  const skin='#e8b98a';
  let h=62*s;
  if(pose==='dunk') h=67*s; // stretched up for the slam
  const gy=pr.y;
  let bob=0;
  if(pose==='idle') bob=Math.sin(G.elapsed*2.2+p.num*1.7)*1.5*s;
  const yTop=gy-h-(p.jz||0)+bob;
  const lean=(pose==='run'||pose==='dribble')?face*2*s:0;
  // hips sit at the bottom of the torso — one connected figure, no gap
  const hipY=yTop+40*s;
  // shadow on the floor (shrinks as the player jumps)
  const shScale=clamp(1-(p.jz||0)/120,0.55,1);
  ctx.fillStyle='rgba(0,0,0,.35)';
  ctx.beginPath(); ctx.ellipse(pr.x,gy+4,26*s*shScale,7*s*shScale,0,0,7); ctx.fill();

  // ---- dunk style drives the arm/leg pose (and the 360 spin) ----
  const dStyle=(pose==='dunk'&&p.dunkStyle!==undefined&&p.dunkStyle!==null&&DUNK_STYLES[p.dunkStyle])?DUNK_STYLES[p.dunkStyle]:null;
  const isSpin=dStyle&&dStyle.id==='spin360';
  let rotA=0;
  if(isSpin){
    // spin like a top: same fast accelerating angle as the ball's circle,
    // so body and ball whip around together and finish the turn early
    const db=(G.ball&&G.ball.state==='shot'&&G.ball.type!=='shot'&&G.ball.shooter===p)?G.ball:null;
    rotA=db?spinAngle(db.t):Math.min(1,p.poseT/0.42)*Math.PI*2;
  }
  ctx.save();
  if(isSpin){ const cxp=pr.x, cyp=yTop+h*0.5; ctx.translate(cxp,cyp); ctx.rotate(rotA); ctx.translate(-cxp,-cyp); }

  // ---- legs: thigh + shin with a knee, plus shoes ----
  const step=p.step||0;
  const sw=Math.sin(step*Math.PI*2);
  let legLen=22*s, fA={dx:0,dy:0}, fB={dx:0,dy:0}; // standing: feet on the ground
  if(pose==='run'||pose==='dribble'){
    fA={dx:sw*5*s,dy:-Math.abs(sw)*6*s};
    fB={dx:-sw*5*s,dy:-Math.abs(Math.cos(step*Math.PI*2))*6*s};
  } else if(pose==='shoot'||pose==='jump'){
    legLen=16*s; fA={dx:-4*s,dy:-2*s}; fB={dx:4*s,dy:-2*s}; // tucked in the air
  } else if(pose==='dunk'){
    if(dStyle&&dStyle.id==='onehand'){ legLen=16*s; fA={dx:face*8*s,dy:-3*s}; fB={dx:-face*3*s,dy:-6*s}; } // one leg drives forward
    else if(dStyle&&dStyle.id==='tomahawk'){ legLen=18*s; fA={dx:face*10*s,dy:-2*s}; fB={dx:-face*9*s,dy:-2*s}; } // wide split, dramatic
    else if(dStyle&&dStyle.id==='reverse'){ legLen=15*s; fA={dx:-face*6*s,dy:-2*s}; fB={dx:face*6*s,dy:-2*s}; } // tucked split, back to the rim
    else { legLen=14*s; fA={dx:-4*s,dy:-2*s}; fB={dx:4*s,dy:-2*s}; } // twohand + spin360: tucked together
  } else if(pose==='aim'){
    legLen=18*s; fA={dx:-6*s,dy:0}; fB={dx:6*s,dy:0}; // crouch, wide stance
  } else if(pose==='pass'){
    fA={dx:face*7*s,dy:0}; fB={dx:-face*7*s,dy:0}; // lunge
  } else if(pose==='stumble'){
    legLen=20*s; fA={dx:-9*s,dy:0}; fB={dx:9*s,dy:0}; // splayed
  } else if(pose==='block'){
    fA={dx:-2*s,dy:0}; fB={dx:2*s,dy:0}; // together
  }
  const hipL={x:pr.x-6*s+lean,y:hipY}, hipR={x:pr.x+6*s+lean,y:hipY};
  const footL={x:hipL.x+fA.dx,y:hipY+legLen+fA.dy}, footR={x:hipR.x+fB.dx,y:hipY+legLen+fB.dy};
  const kneeL=limbJoint(hipL.x,hipL.y,footL.x,footL.y,face*4*s,-3*s);
  const kneeR=limbJoint(hipR.x,hipR.y,footR.x,footR.y,face*4*s,-3*s);
  limb2(hipL.x,hipL.y,footL.x,footL.y,kneeL.x,kneeL.y,7*s,'#1f2937');
  limb2(hipR.x,hipR.y,footR.x,footR.y,kneeR.x,kneeR.y,7*s,'#1f2937');
  // shoes
  ctx.fillStyle='#111';
  ctx.beginPath(); ctx.ellipse(footL.x+face*3*s,footL.y+1*s,7*s,3.5*s,0,0,7); ctx.fill();
  ctx.beginPath(); ctx.ellipse(footR.x+face*3*s,footR.y+1*s,7*s,3.5*s,0,0,7); ctx.fill();
  G._shoes=(G._shoes||0)+2; // test instrumentation
  // shorts band at the hips
  ctx.fillStyle=jerseyDark;
  roundRect(pr.x-14*s+lean,hipY-6*s,28*s,10*s,4*s); ctx.fill();

  // ---- torso ----
  ctx.fillStyle=jersey;
  roundRect(pr.x-13*s+lean,yTop+14*s,26*s,26*s,6*s); ctx.fill();
  ctx.fillStyle='#fff'; ctx.font='bold '+Math.round(13*s)+'px Arial'; ctx.textAlign='center';
  ctx.fillText(p.num,pr.x+lean,yTop+33*s);

  // ---- arms: upper arm + forearm with an elbow, plus hands ----
  const shL={x:pr.x-11*s+lean,y:yTop+20*s}, shR={x:pr.x+11*s+lean,y:yTop+20*s};
  let handL, handR;
  if(pose==='dribble'){
    const bp=heldBallPos(p);
    const dArm=(face>0)?shR:shL, oArm=(face>0)?shL:shR;
    if(face>0){ handR={x:bp.x,y:bp.y}; handL={x:oArm.x-face*4*s,y:oArm.y+14*s}; } // dribbling arm pumps with the ball
    else { handL={x:bp.x,y:bp.y}; handR={x:oArm.x-face*4*s,y:oArm.y+14*s}; }
  } else if(pose==='aim'){
    const bp=heldBallPos(p);
    handR={x:bp.x,y:bp.y}; handL={x:bp.x-4*s,y:bp.y+2*s}; // both hands on the ball at the chest
  } else if(pose==='dunk'){
    // the dunking hand(s) ride the ball — at the peak they arrive at the rim
    // with it, so the hands and the ball connect to the rim together.
    // (360 spin excluded: the body rotates, so its hands stay up and the
    // ball circles back to the top on its own.)
    const db=(G.ball&&G.ball.state==='shot'&&G.ball.type!=='shot'&&G.ball.shooter===p)?G.ball:null;
    if(dStyle&&dStyle.id==='onehand'){
      // one arm up with the ball, other arm down at the side
      if(db){ if(face>0){ handR={x:db.sx,y:db.sy}; handL={x:pr.x-face*12*s,y:yTop+34*s}; } else { handL={x:db.sx,y:db.sy}; handR={x:pr.x-face*12*s,y:yTop+34*s}; } }
      else if(face>0){ handR={x:pr.x+face*10*s,y:yTop-10*s}; handL={x:pr.x-face*12*s,y:yTop+34*s}; }
      else { handL={x:pr.x+face*10*s,y:yTop-10*s}; handR={x:pr.x-face*12*s,y:yTop+34*s}; }
    } else if(dStyle&&dStyle.id==='reverse'){
      // both arms up and back, behind the head — hands on the ball
      if(db){ handL={x:db.sx-4*s,y:db.sy}; handR={x:db.sx+4*s,y:db.sy}; }
      else { handL={x:pr.x-face*10*s,y:yTop-10*s}; handR={x:pr.x-face*2*s,y:yTop-12*s}; }
    } else if(dStyle&&dStyle.id==='tomahawk'){
      // dunk arm swings with the ball; other arm out for balance
      const b=G.ball;
      if(b&&b.state==='shot'&&b.type!=='shot'&&b.dunkStyle!==undefined&&DUNK_STYLES[b.dunkStyle]&&DUNK_STYLES[b.dunkStyle].id==='tomahawk'){
        if(face>0){ handR={x:b.sx,y:b.sy}; handL={x:pr.x-face*14*s,y:yTop+20*s}; }
        else { handL={x:b.sx,y:b.sy}; handR={x:pr.x-face*14*s,y:yTop+20*s}; }
      } else { handL={x:shL.x-4*s,y:yTop-8*s}; handR={x:shR.x+4*s,y:yTop-8*s}; }
    } else { // twohand + spin360: both arms straight up, on the ball
      if(db&&!(dStyle&&dStyle.id==='spin360')){ handL={x:db.sx-4*s,y:db.sy}; handR={x:db.sx+4*s,y:db.sy}; }
      else { handL={x:shL.x-4*s,y:yTop-8*s}; handR={x:shR.x+4*s,y:yTop-8*s}; }
    }
  } else if(pose==='jump'){
    handL={x:shL.x-3*s,y:yTop+2*s}; handR={x:shR.x+3*s,y:yTop+2*s}; // both arms up
  } else if(pose==='shoot'){
    handR={x:shR.x+3*s,y:yTop-6*s}; // follow-through arm up
    handL={x:shL.x-2*s,y:yTop+30*s}; // guide arm across the chest
  } else if(pose==='block'){
    handR={x:shR.x+2*s,y:yTop-12*s}; // one arm straight up
    handL={x:shL.x-4*s,y:yTop+32*s};
  } else if(pose==='pass'){
    handL={x:pr.x+face*20*s,y:yTop+30*s}; handR={x:pr.x+face*20*s,y:yTop+30*s}; // both arms push forward
  } else if(pose==='run'){
    handL={x:shL.x-sw*5*s,y:yTop+32*s}; handR={x:shR.x+sw*5*s,y:yTop+32*s}; // arms swing opposite the legs
  } else if(pose==='stumble'){
    handL={x:shL.x-10*s,y:yTop+20*s}; handR={x:shR.x+10*s,y:yTop+20*s}; // arms flailing out
  } else { // idle
    handL={x:shL.x-4*s,y:yTop+36*s}; handR={x:shR.x+4*s,y:yTop+36*s};
  }
  const elbL=limbJoint(shL.x,shL.y,handL.x,handL.y,-4*s,2*s);
  const elbR=limbJoint(shR.x,shR.y,handR.x,handR.y,4*s,2*s);
  limb2(shL.x,shL.y,handL.x,handL.y,elbL.x,elbL.y,6*s,jersey);
  limb2(shR.x,shR.y,handR.x,handR.y,elbR.x,elbR.y,6*s,jersey);
  // hands
  ctx.fillStyle=skin;
  ctx.beginPath(); ctx.arc(handL.x,handL.y,3.5*s,0,7); ctx.fill();
  ctx.beginPath(); ctx.arc(handR.x,handR.y,3.5*s,0,7); ctx.fill();
  G._hands=(G._hands||0)+2; // test instrumentation

  // head + headband
  ctx.fillStyle=skin; ctx.beginPath(); ctx.arc(pr.x+lean,yTop+8*s,9*s,0,7); ctx.fill();
  ctx.fillStyle=jersey; ctx.fillRect(pr.x-9*s+lean,yTop+1*s,18*s,4*s);
  ctx.restore();

  // pose signature (test instrumentation): limbs + style + spin angle
  p._poseSig=pose+'|'+(dStyle?dStyle.id:'-')+'|hL'+Math.round(handL.x-pr.x)+'|hR'+Math.round(handR.x-pr.x)+'|rot'+Math.round(rotA*100)+'|fA'+Math.round(fA.dx)+'|fB'+Math.round(fB.dx);
  p._limbs={legs:2,arms:2,shoes:2,hands:2};
  // YOU marker
  if(G.players[G.user]===p){
    ctx.fillStyle='#f5c518';
    ctx.beginPath(); ctx.moveTo(pr.x,yTop-22*s); ctx.lineTo(pr.x-8*s,yTop-32*s); ctx.lineTo(pr.x+8*s,yTop-32*s); ctx.closePath(); ctx.fill();
    ctx.fillStyle='#000'; ctx.font='bold 10px Arial'; ctx.fillText('YOU',pr.x,yTop-36*s);
  }
  // on fire flame
  if(p.onFire){
    ctx.fillStyle='#ff7a00';
    ctx.beginPath(); ctx.moveTo(pr.x-8*s,yTop-6*s); ctx.quadraticCurveTo(pr.x-14*s,yTop-24*s,pr.x,yTop-30*s); ctx.quadraticCurveTo(pr.x+14*s,yTop-24*s,pr.x+8*s,yTop-6*s); ctx.closePath(); ctx.fill();
    ctx.fillStyle='#ffd23e';
    ctx.beginPath(); ctx.moveTo(pr.x-4*s,yTop-8*s); ctx.quadraticCurveTo(pr.x-7*s,yTop-18*s,pr.x,yTop-22*s); ctx.quadraticCurveTo(pr.x+7*s,yTop-18*s,pr.x+4*s,yTop-8*s); ctx.closePath(); ctx.fill();
  }
  // test instrumentation (harmless in play): last drawn top of this player
  p._drawTop=yTop; p._drawX=pr.x;
}
function drawBall(){
  const b=G.ball; if(!b) return;
  let gx,gy,by;
  if(b.state==='held'){
    const h=holder(); if(!h) return;
    const bp=heldBallPos(h);
    // bounce shadow stays on the floor under the ball
    ctx.fillStyle='rgba(0,0,0,.3)';
    ctx.beginPath(); ctx.ellipse(bp.x,bp.pr.y+4,10*bp.pr.s,3*bp.pr.s,0,0,7); ctx.fill();
    drawBallAt(bp.x,bp.y,11*bp.pr.s,h.onFire||(G.fire&&G.fire.team===h.team));
  } else if(b.state==='pass'||b.state==='shot'){
    const gp=proj(b.x,b.z);
    ctx.fillStyle='rgba(0,0,0,.3)';
    ctx.beginPath(); ctx.ellipse(gp.x,gp.y+4,10*gp.s,3*gp.s,0,0,7); ctx.fill();
    const sh=b.shooter;
    drawBallAt(b.sx,b.sy,11*gp.s,sh&&(sh.onFire||(G.fire&&G.fire.team===sh.team)));
  } else if(b.state==='loose'){
    const pr=proj(b.x,b.z);
    ctx.fillStyle='rgba(0,0,0,.3)';
    ctx.beginPath(); ctx.ellipse(pr.x,pr.y+4,10*pr.s,3*pr.s,0,0,7); ctx.fill();
    drawBallAt(pr.x,pr.y-b.h,11*pr.s,false);
  }
}
function drawBallAt(x,y,r,onFire){
  G._ballDraw={x:x,y:y,r:r};
  if(onFire){
    ctx.fillStyle='#ff7a00';
    ctx.beginPath(); ctx.arc(x,y,r+5,0,7); ctx.fill();
    ctx.fillStyle='#ffd23e';
    ctx.beginPath(); ctx.arc(x,y,r+2,0,7); ctx.fill();
  }
  ctx.fillStyle='#e2571e';
  ctx.beginPath(); ctx.arc(x,y,r,0,7); ctx.fill();
  ctx.strokeStyle='#7a2d08'; ctx.lineWidth=1.5;
  ctx.beginPath(); ctx.arc(x,y,r,0,7); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x-r,y); ctx.lineTo(x+r,y); ctx.stroke();
  ctx.beginPath(); ctx.moveTo(x,y-r); ctx.lineTo(x,y+r); ctx.stroke();
}
/* ---------- shot meter (jump shots only; dunks never show it) ---------- */
function drawMeter(){
  if(G.mode!=='play') return;
  let ch=null;
  G.players.forEach(function(p){ if(p.charge!==null&&p.charge!==undefined) ch=p; });
  if(!ch) return;
  const pr=proj(ch.x,ch.z);
  const s=pr.s;
  const w=110*s, h=15*s, x=pr.x-w/2, y=pr.y-62*s-(ch.jz||0)-56*s;
  ctx.fillStyle='rgba(0,0,0,.75)'; roundRect(x-4,y-4,w+8,h+8,6*s); ctx.fill();
  // green perfect zone (filled, then outlined so it stays visible as the fill passes it)
  ctx.fillStyle='#22c55e'; ctx.fillRect(x+GREEN_LOW*w,y,(GREEN_HIGH-GREEN_LOW)*w,h);
  ctx.fillStyle=ch.charge>GREEN_HIGH?'#f97316':'#f5c518';
  ctx.fillRect(x,y,Math.min(1,ch.charge)*w,h);
  ctx.strokeStyle='#22c55e'; ctx.lineWidth=3;
  ctx.strokeRect(x+GREEN_LOW*w,y,(GREEN_HIGH-GREEN_LOW)*w,h);
  ctx.strokeStyle='#fff'; ctx.lineWidth=2; ctx.strokeRect(x,y,w,h);
  ctx.fillStyle='#fff'; ctx.font='bold '+Math.round(11*s)+'px Arial'; ctx.textAlign='center';
  ctx.fillText('PERFECT',x+(GREEN_LOW+GREEN_HIGH)/2*w,y-6);
}
function drawTrails(){
  // wind trails on dunks: fading ghost silhouettes of the dunking player
  // and the ball, trailing behind the flight, plus speed lines. Dunks only.
  const b=G.ball;
  if(!b||b.state!=='shot'||b.type==='shot'||!G.trail||G.trail.length<2){ G._trailN=0; return; }
  G._trailN=G.trail.length;
  const n=G.trail.length;
  const dir=(b.hoop.x>G.trail[n-1].px)?1:-1; // flight direction (toward the hoop)
  for(let i=0;i<n;i++){
    const s=G.trail[i];
    const a=(i+1)/n*0.30; // oldest faintest, newest strongest
    const jersey=s.team===0?'#d8232a':'#1d6fd1';
    ctx.globalAlpha=a;
    // player ghost: head + torso silhouette
    ctx.fillStyle=jersey;
    ctx.beginPath(); ctx.arc(s.px,s.py-22*s.ps,9*s.ps,0,7); ctx.fill();
    roundRect(s.px-13*s.ps,s.py-14*s.ps,26*s.ps,30*s.ps,6*s.ps); ctx.fill();
    // ball ghost
    ctx.fillStyle='#e2571e';
    ctx.beginPath(); ctx.arc(s.bx,s.by,9*s.bs,0,7); ctx.fill();
    // speed lines streaking behind the player, away from the hoop
    ctx.strokeStyle='rgba(255,255,255,'+a+')'; ctx.lineWidth=2*s.ps;
    ctx.beginPath(); ctx.moveTo(s.px-dir*18*s.ps,s.py-20*s.ps); ctx.lineTo(s.px-dir*42*s.ps,s.py-20*s.ps); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(s.px-dir*14*s.ps,s.py+6*s.ps); ctx.lineTo(s.px-dir*36*s.ps,s.py+6*s.ps); ctx.stroke();
  }
  ctx.globalAlpha=1;
}
function draw(){
  G._limbCalls=0; G._shoes=0; G._hands=0; // test instrumentation: reset per frame
  ctx.save();
  if(G.shake>0) ctx.translate((Math.random()-0.5)*G.shake*30,(Math.random()-0.5)*G.shake*30);
  drawBackground();
  drawCourt();
  drawHoop(HOOP[0]); drawHoop(HOOP[1]);
  drawTrails();
  const sorted=G.players.slice().sort(function(a,b){return a.z-b.z;});
  sorted.forEach(drawPlayer);
  drawBall();
  drawMeter();
  ctx.restore();
}

/* ---------- main loop ---------- */
let last=0;
function loop(t){
  requestAnimationFrame(loop);
  const dt=Math.min(0.05,(t-last)/1000||0.016); last=t;
  if(G.mode==='play') update(dt);
  if($('gameView').classList.contains('open')) draw();
}
newGame();
requestAnimationFrame(loop);
openGame(); // port: the app opens the game straight at difficulty + TIP OFF

/* test hook (for verification only) */
window.__game={G:G,stick:stick,setStick:setStick,startGame:startGame,openGame:openGame,doShoot:shootPress,shootPress:shootPress,shootRelease:shootRelease,doPass:doPass,update:update,draw:draw,drawCourt:drawCourt,proj:proj,rimScreen:rimScreen,startShot:startShot,updateLabels:updateLabels,resetPositions:resetPositions,scoreBall:scoreBall,DIFFS:DIFFS,DUNK_STYLES:DUNK_STYLES,ZOOM:ZOOM,selectDiff:selectDiff,pvpPlayer:pvpPlayer,pvpIsOn:pvpIsOn,pvpMe:pvpMe,pvpOppCtrl:pvpOppCtrl,pvpReceiveEv:pvpReceiveEv,pvpApplyState:pvpApplyState,pvpPostState:pvpPostState,pvpStartPoll:pvpStartPoll,pvpStopPoll:pvpStopPoll,pvpPollOnce:pvpPollOnce,computeMake:computeMake,doPassBall:doPassBall,doSteal:doSteal,doBlock:doBlock,holder:holder,updateUserControl:updateUserControl};
})();
</script>
</body>
</html>
`;
