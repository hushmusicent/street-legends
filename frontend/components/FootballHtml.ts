// PARK_FOOTBALL_HTML
export const FOOTBALL_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Park Football — 7 on 7 Preview (3D)</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color:transparent; }
  html, body { height:100%; background:#0d1f12; color:#fff; font-family:Arial, Helvetica, sans-serif; overflow:hidden; touch-action:none; }
  #app { height:100%; display:flex; flex-direction:column; }

  /* ============ GAME VIEW (game only — no park home page in this preview) ============ */
  #gameView { position:fixed; inset:0; background:#000; display:flex; flex-direction:column; z-index:10; }
  #gameStage { position:relative; flex:1; display:flex; flex-direction:column; overflow:hidden; background:#111; }
  #canvasWrap { position:relative; flex:1; background:#0a2a12; overflow:hidden; }
  #gameCanvas { position:absolute; }
  #scorebug { position:absolute; top:52px; left:50%; transform:translateX(-50%); display:flex; gap:10px; align-items:center; background:rgba(0,0,0,.75); border:2px solid #f5c518; border-radius:10px; padding:6px 14px; font-weight:bold; z-index:5; white-space:nowrap; }
  #scorebug .team { font-size:18px; }
  #scorebug .team.home { color:#ff5a5a; }
  #scorebug .team.away { color:#5aa9ff; }
  #scorebug .clock { font-size:20px; color:#f5c518; }
  #downLine { position:absolute; top:98px; left:50%; transform:translateX(-50%); background:rgba(0,0,0,.75); border:2px solid #f5c518; border-radius:8px; padding:4px 12px; font-size:15px; font-weight:bold; color:#fff; z-index:5; white-space:nowrap; }
  #downLine .fd { color:#f5c518; }
  #downLine .pc { color:#f5c518; }
  #backBtn { position:absolute; top:8px; left:8px; z-index:6; background:rgba(0,0,0,.7); color:#fff; border:2px solid #888; border-radius:8px; padding:8px 12px; font-size:14px; font-weight:bold; }
  #turboMeter { position:absolute; top:132px; left:50%; transform:translateX(-50%); width:150px; height:8px; background:rgba(255,255,255,.25); border-radius:4px; overflow:hidden; z-index:5; }
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
  #btnSnap { right:118px; bottom:0; background:#c81e1e; }
  #btnPass { right:10px; bottom:74px; background:#1d6fd1; }
  #btnTurbo { right:42px; bottom:0; background:#f59e0b; color:#000; text-shadow:none; }
  #btnSnap.def { background:#7c3aed; }
  #btnPass.def { background:#059669; }

  /* Start / end overlays */
  .overlay { position:absolute; inset:0; background:rgba(0,0,0,.82); z-index:20; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:14px; text-align:center; padding:20px; overflow-y:auto; }
  .overlay h2 { font-size:34px; font-style:italic; color:#f5c518; text-shadow:2px 2px 0 #c00; }
  .overlay .vs { font-size:22px; font-weight:bold; }
  .overlay .vs .h { color:#ff5a5a; } .overlay .vs .a { color:#5aa9ff; }
  .overlay p { color:#ccc; font-size:14px; line-height:1.5; max-width:360px; }
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
  #finalScore { font-size:44px; font-weight:900; }
  #finalScore .h { color:#ff5a5a; } #finalScore .a { color:#5aa9ff; }
  .hidden { display:none !important; }

  /* Play-call screen (Madden style): 3 plays with chalk route diagrams */
  #playcallOverlay { background:rgba(0,20,8,.88); }
  #playcallOverlay h2 { font-size:26px; }
  #playcallTitle { font-size:16px; font-weight:bold; color:#fff; }
  #playcallTitle .fd { color:#f5c518; }
  .play-row { display:flex; flex-wrap:wrap; gap:10px; width:100%; max-width:680px; justify-content:center; }
  .playCard { flex:1; max-width:210px; background:#0b3d1e; border:3px solid #f5c518; border-radius:12px; padding:10px 8px; cursor:pointer; }
  .playCard:active { transform:scale(.97); background:#14532d; }
  .playCard .pname { font-size:17px; font-weight:900; color:#f5c518; letter-spacing:1px; }
  .playCard .ptype { font-size:11px; font-weight:bold; color:#a7f3c9; letter-spacing:2px; margin:2px 0 6px; }
  .playCard canvas { width:100%; height:auto; background:#14532d; border-radius:8px; display:block; }
  .playCard .pdesc { font-size:11px; color:#ddd; line-height:1.35; margin-top:6px; min-height:30px; }
  .playCard .pkey { font-size:11px; color:#888; margin-top:4px; }
</style>
</head>
<body>
<div id="app">
  <!-- GAME VIEW -->
  <div id="gameView" class="open">
    <div id="gameStage">
      <div id="canvasWrap">
      <canvas id="gameCanvas" width="900" height="600"></canvas>
      <div id="scorebug">
        <span class="team home">HOME <span id="scoreHome">0</span></span>
        <span class="clock">FIRST TO 10</span>
        <span class="clock" id="gameClock">0:00</span>
        <span class="team away"><span id="scoreAway">0</span> AWAY</span>
      </div>
      <div id="downLine"><span id="downText">1ST &amp; 30 &bull; BALL ON 20</span> <span class="fd" id="fdText">&bull; 1ST DOWN AT 50</span> <span class="pc" id="playClock"></span></div>
      <button id="backBtn">MENU</button>
      <div id="diffChip">PRO</div>
      <div id="turboMeter"><div id="turboFill"></div></div>
      <div id="callout"></div>
      <div id="subCallout"></div>
      </div>

      <div id="controls">
        <div id="stick"><div id="stickKnob"></div></div>
        <div id="buttons">
          <button class="gbtn" id="btnSnap">SNAP</button>
          <button class="gbtn" id="btnPass">PASS</button>
          <button class="gbtn" id="btnTurbo">TURBO</button>
        </div>
      </div>

      <div class="overlay" id="startOverlay">
        <h2>PARK FOOTBALL</h2>
        <div class="vs"><span class="h">HOME</span> &nbsp;VS&nbsp; <span class="a">AWAY</span></div>
        <p>7 on 7 &bull; First to 10 touchdowns &bull; Touchdowns only<br>
        2 downs &bull; First down at midfield &bull; Every drive starts at the 20<br>
        Pick a play, then SNAP to hike &bull; PASS throws to the gold target<br>
        Aim with the stick to pick your receiver &bull; TURBO to sprint</p>
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
        <button class="bigbtn" id="startBtn">START GAME</button>
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
      </div>

      <div class="overlay hidden" id="playcallOverlay">
        <h2>CHOOSE YOUR PLAY</h2>
        <div id="playcallTitle">1ST &amp; 30 &bull; BALL ON 20</div>
        <div class="play-row">
          <div class="playCard" id="playCard0">
            <div class="pname">CORNERS</div>
            <div class="ptype">PASS</div>
            <canvas class="playCanvas" id="playCanvas0" width="220" height="150"></canvas>
            <div class="pdesc">Both wideouts break for the corners. Tight ends hook short.</div>
            <div class="pkey">Press 1</div>
          </div>
          <div class="playCard" id="playCard1">
            <div class="pname">CROSSINGS</div>
            <div class="ptype">PASS</div>
            <canvas class="playCanvas" id="playCanvas1" width="220" height="150"></canvas>
            <div class="pdesc">Wideouts cross the field underneath. Tight ends slant inside.</div>
            <div class="pkey">Press 2</div>
          </div>
          <div class="playCard" id="playCard2">
            <div class="pname">HB SPRINT</div>
            <div class="ptype">RUN</div>
            <canvas class="playCanvas" id="playCanvas2" width="220" height="150"></canvas>
            <div class="pdesc">Handoff up the middle — the halfback sprints for the edge.</div>
            <div class="pkey">Press 3</div>
          </div>
          <div class="playCard" id="playCard3">
            <div class="pname">GO DEEP</div>
            <div class="ptype">PASS</div>
            <canvas class="playCanvas" id="playCanvas3" width="220" height="150"></canvas>
            <div class="pdesc">Both wideouts fly deep downfield. Tight ends hook short.</div>
            <div class="pkey">Press 4</div>
          </div>
          <div class="playCard" id="playCard4">
            <div class="pname">SLANTS</div>
            <div class="ptype">PASS</div>
            <canvas class="playCanvas" id="playCanvas4" width="220" height="150"></canvas>
            <div class="pdesc">Wideouts slant inside over the middle. Tight ends leak to the flats.</div>
            <div class="pkey">Press 5</div>
          </div>
          <div class="playCard" id="playCard5">
            <div class="pname">HB SWEEP</div>
            <div class="ptype">RUN</div>
            <canvas class="playCanvas" id="playCanvas5" width="220" height="150"></canvas>
            <div class="pdesc">Handoff to the right — the halfback sweeps for the edge.</div>
            <div class="pkey">Press 6</div>
          </div>
        </div>
      </div>

      <div class="overlay hidden" id="endOverlay">
        <h2 id="finalTitle">HOME WINS!</h2>
        <div id="finalScore"><span class="h">0</span> &ndash; <span class="a">0</span></div>
        <p id="finalNote"></p>
        <button class="bigbtn" id="rematchBtn">REMATCH</button>
        <button class="ghostbtn" id="endBackBtn">MENU</button>
      </div>
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
function cheer(){beep(660,0.15,'square');setTimeout(()=>beep(880,0.2,'square'),120);setTimeout(()=>beep(990,0.25,'square'),260);}
function whistle(){beep(2200,0.15,'square');setTimeout(()=>beep(2200,0.25,'square'),200);}
function thud(){beep(140,0.12,'sine');}

/* ================= FIELD — 120 yards long, 53 wide, park setting =================
   World x is yards down the field: 0 = back of the home end zone,
   10 = home goal line, 60 = midfield, 110 = away goal line, 120 = back
   of the away end zone. Ball-on yard line = x - 10 (0..100 from the
   offense's own goal line). The offense ALWAYS attacks the FAR end
   zone (x=110) — the camera sits behind the offense and looks
   downfield, Madden style. On a turnover or a score the other team
   starts a fresh drive at its own 20, attacking the same far end zone.
   NO special teams at all — drives just start at the 20. */
const cv=$('gameCanvas'), ctx=cv.getContext('2d');
const W=900, H=600;
const FX0=0, FX1=120, GOAL0=10, GOAL1=110, MID=60, FZ0=0, FZ1=53;
const TARGET_TD=10; // first to 10 touchdowns wins
const PLAY_CLOCK=25; // seconds on the play clock; auto-snap at 0
const DIFFS=[
 {name:'ROOKIE',  speed:0.72, react:1.0,  tackle:0.4, passAcc:0.55, coverage:0.6, desc:'Easy — the computer misses throws and reacts slowly.'},
 {name:'AMATEUR', speed:0.86, react:0.7,  tackle:0.7, passAcc:0.70, coverage:0.8, desc:'A fair challenge — the computer makes mistakes.'},
 {name:'PRO',     speed:1.0,  react:0.45, tackle:1.0, passAcc:0.82, coverage:1.0, desc:'Even game — the computer plays straight up.'},
 {name:'ALL-STAR',speed:1.1,  react:0.3,  tackle:1.3, passAcc:0.90, coverage:1.2, desc:'Hard — the computer throws darts and hunts tackles.'},
 {name:'LEGEND',  speed:1.2,  react:0.15, tackle:1.6, passAcc:0.95, coverage:1.4, desc:'Brutal — the computer barely misses and reacts instantly.'}
];
let diffSel=3; // start-screen selection; default Pro
function cpuDiff(){ return DIFFS[G.difficulty-1]; }

const G={
  mode:'start', phase:'preSnap', score:[0,0], elapsed:0, players:[], ball:null,
  possession:0, user:0, qb:-1, target:null, shake:0, pause:0,
  afterPause:false, nextDrive:null, turbo:100, turboHeld:false,
  dir:{x:0,z:0}, defT:0, difficulty:3, down:1, ballOn:20, losX:30,
  lineToGain:50, crossedMid:false, playT:0, cpuThrowAt:0, cpuDropped:false,
  cpuSnapT:0, _prevBX:60, _lastCarrier:null,
  camX:8, camZ:26.5, playClock:PLAY_CLOCK, cpuPickT:0, play:null,
  runPlay:false, handoffDone:false, handoffTarget:null, handoffGrace:0,
  myTeam:0, // PvC: you are always HOME (team 0). PvP: 0 if host, 1 if guest.
  pvp:null, // null in PvC; in PvP: {code, role, oppName, seq, lastSeenSeq, pollTimer, posT, playOver}
  lastHolder:null, // the holder we last posted (so we only post changes)
};

/* ---------- PvP (park games) ---------- */
// Same room system as the other park games (backend: /api/park_pvp/rooms/*).
// Football is play-based, so the sync is per-play: the offense picks a
// play (posted), snaps (posted), and throws (posted); the play outcome
// (tackle / sack / TD / out of bounds / incomplete / interception) is
// posted by the side that detects it first, and the other side applies
// it instead of re-detecting. The AI runs the other players locally on
// both sides (they may drift slightly -- the ball and the score are the
// authority, resynced via the room state). Each human controls the ball
// carrier on offense or the nearest defender on defense; their position
// is posted ~4x a second and interpolated on the other side. Identity
// comes from the app as window.PARK_PVP_PLAYER = {id, name}.
var PVP_API='https://gta-quest-map.emergent.host/api/park_pvp/rooms';
var PVP_POLL_MS = 100;
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
  // (play / snap / pass / outcome). The full score, possession, down,
  // ball-on, holder, and my controlled player's position ride along so
  // the other phone resyncs and sees where I am.
  if(!pvpIsOn()) return Promise.resolve(null);
  if (!patch && G.pvp.posting) return Promise.resolve(null);
  G.pvp.seq+=1;
  var me=pvpMe();
  var h=holder();
  var st={
    seq:G.pvp.seq,
    score:G.score.slice(), possession:G.possession, down:G.down,
    ballOn:G.ballOn, phase:G.phase,
    holder:h?{team:h.team,num:h.num}:null,
    me:me?{team:me.team,num:me.num,x:me.x,z:me.z}:null,
    ev:null
  };
  if(patch&&patch.ev) st.ev=patch.ev;
  var who=pvpPlayer();
  st.round = G.pvp.round || 0; st.rm = G.pvp.rmReq || 0;
  var pvw = G.pvp; pvw.posting = true; return pvpPost('/'+G.pvp.code+'/state',{player_id:who.id,state:st}).then(function(r){ pvw.posting = false; return r; });
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
  if (G.pvp.polling) return; var pvq = G.pvp; pvq.polling = true;
  pvpGet(code).then(function(room){ pvq.polling = false;
    if(!room) return;
    if(room.status==='finished'){
      pvpStopPoll();
      G.mode='over'; G.phase='dead';
      var won=room.winner&&room.winner===pvpPlayer().id;
      var ft=document.getElementById('finalTitle');
      if(ft) ft.textContent=won?'YOU WIN!':'YOU LOSE';
      var eo=document.getElementById('endOverlay');
      if(eo) eo.classList.remove('hidden');
      return;
    }
    // Opponent joined — the game starts on its own now (like the house
    // games: the game starts when the second player enters the code).
    if (pvpWagerReady(room, G.pvp.round || 0) && G.pvp.role==='host'&&room.status==='playing'&&room.guest_name&&G.mode!=='play'&&G.mode!=='over'){
      G.pvp.oppName=room.guest_name;
      var lbl=document.getElementById('pvpRoomLbl');
      if(lbl) lbl.textContent='CODE: '+code+' — vs '+G.pvp.oppName;
      var st2=document.getElementById('pvpStatus');
      if(st2) st2.textContent='They joined! Starting the game...';
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
  if(!st) return;
  // If I haven't started yet (fresh join, or rejoin after getting
  // booted out), start the game first, then resync everything from
  // the room state. A rejoining host does NOT post a fresh initial
  // state (that would reset the room).
  var fresh=pvpIsOn()&&G.mode!=='play'&&G.mode!=='over';
  if(fresh){
    if(G.pvp.role==='host') G.pvp.syncStart=true;
    startGame();
    if(G.pvp) G.pvp.syncStart=false;
  }
  // Score only goes up during a game: keep the higher value per side so
  // a late/stale post from the other phone can never reset it.
  if (Array.isArray(st.score)){ for (var si = 0; si < st.score.length; si++){ if (typeof st.score[si] === 'number' && st.score[si] > (G.score[si] || 0)) G.score[si] = st.score[si]; } }
  if(typeof st.possession==='number') G.possession=st.possession;
  if(typeof st.down==='number') G.down=st.down;
  if(typeof st.ballOn==='number') G.ballOn=st.ballOn;
  updateScore();
  updateDownLine();
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
  if(ev.k==='play'){
    // They picked a play: same playbook entry, same routes.
    if(G.phase==='playcall'){ pickPlay(ev.idx, true); }
  } else if(ev.k==='snap'){
    // They snapped: the play is live on both phones now.
    if(G.phase==='preSnap'){ snap(true); }
  } else if(ev.k==='pass'){
    // They threw: same QB, same receiver, same ball flight.
    var qb=null, recv=null;
    G.players.forEach(function(p){
      if(p.team===ev.team&&p.num===ev.qb) qb=p;
      if(p.team===ev.team&&p.num===ev.recv) recv=p;
    });
    if(qb&&recv) throwPass(qb, recv, true, ev.rx, ev.rz);
  } else if(ev.k==='outcome'){
    // They detected the play ending: apply the same outcome here
    // instead of re-detecting it (positions drift slightly).
    if(G.pvp) G.pvp.playOver=true;
    finishPlay({type:ev.type, spotX:ev.spotX, spotZ:ev.spotZ}, true);
  } else if(ev.k==='tackle'){
    // They dove to tackle: same lunge, so I see them coming.
    var p=null;
    G.players.forEach(function(q){ if(q.team===ev.team&&q.num===ev.num) p=q; });
    if(p&&p.cool<=0&&p.diveT<=0){
      var bh=holder();
      if(bh){
        var dx=bh.x-p.x, dz=bh.z-p.z, dd=Math.hypot(dx,dz)||1;
        p.diveT=0.25; p.diveX=dx/dd; p.diveZ=dz/dd;
        p.cool=0.9; p.pose='dive'; p.poseT=0;
      }
    }
  }
}
const dirs={up:false,down:false,left:false,right:false};
const stick={x:0,y:0}; // virtual joystick vector, -1..1 per axis

/* ================= TRUE 3D — custom perspective projection =================
   Small projection engine on the 2D canvas: no libraries, no CDN.
   Camera sits behind the offense, elevated, looking downfield at the far
   end zone (the Madden default). World: x = yards downfield, y = height
   in yards (0 = the turf), z = yards across the field (0..53).
   Basis: fwd = normalize(look - cam), right = normalize(cross(fwd, up)),
   upv = cross(right, fwd). Screen: sx = W/2 + (cx/cz)*FOCAL,
   sy = H/2 - (cy/cz)*FOCAL, scale s = FOCAL/cz (pixels per yard).
   PS1 vertex snap: projected screen points are rounded to a 2px grid so
   the models shimmer like low-poly originals. */
const FOCAL=680; // ~66 degree horizontal field of view
const CAM_BACK=22, CAM_H=15, CAM_AHEAD=28;
const CAM={cx:0,cy:0,cz:0,fx:0,fy:0,fz:0,rx:0,ry:0,rz:0,ux:0,uy:0,uz:0};
function updateCamBasis(){
  const bx=G.ball?G.ball.x:G.losX;
  const bz=G.ball?G.ball.z:26.5;
  // smooth follow: the camera chases the ball from behind
  const k=1-Math.exp(-4*0.016);
  G.camX=lerp(G.camX,bx-CAM_BACK,0.12);
  G.camZ=lerp(G.camZ,clamp(bz,12,41),0.12);
  const cx=G.camX, cy=CAM_H, cz=G.camZ;
  const lx=bx+CAM_AHEAD, ly=0, lz=G.camZ;
  let fx=lx-cx, fy=ly-cy, fz=lz-cz;
  const fl=Math.hypot(fx,fy,fz)||1; fx/=fl; fy/=fl; fz/=fl;
  let rx=-fz, ry=0, rz=fx; // cross(fwd, up)
  const rl=Math.hypot(rx,ry,rz)||1; rx/=rl; ry/=rl; rz/=rl;
  // upv = cross(right, fwd)
  const ux=ry*fz-rz*fy, uy=rz*fx-rx*fz, uz=rx*fy-ry*fx;
  CAM.cx=cx; CAM.cy=cy; CAM.cz=cz;
  CAM.fx=fx; CAM.fy=fy; CAM.fz=fz;
  CAM.rx=rx; CAM.ry=ry; CAM.rz=rz;
  CAM.ux=ux; CAM.uy=uy; CAM.uz=uz;
}
function proj(x,z,y){
  y=y||0;
  const vx=x-CAM.cx, vy=y-CAM.cy, vz=z-CAM.cz;
  const raw=vx*CAM.fx+vy*CAM.fy+vz*CAM.fz;
  // scale depth is floored at 8 yards: a tree or player passing the
  // camera plane used to hit s=680/cz and blow up into a screen-filling
  // smear at the edges. The RAW depth is returned so snapP can still
  // cull points behind the camera (depth < 1.2).
  const cz=Math.max(raw,8);
  const cxr=vx*CAM.rx+vy*CAM.ry+vz*CAM.rz;
  const cyv=vx*CAM.ux+vy*CAM.uy+vz*CAM.uz;
  const s=FOCAL/cz;
  return {x:W/2+cxr*s, y:H/2-cyv*s, s:s, depth:raw};
}
function holder(){return G.players.find(function(p){return p.hasBall;})||null;}
function ballOnYard(x){ return clamp(Math.round(x-GOAL0),0,100); }

function mkPlayer(team,num,role,x,z){
  return {team:team,num:num,role:role,x:x,z:z,hasBall:false,cool:0,diveT:0,diveX:0,diveZ:0,
    pose:'stance',poseT:0,step:0,face:1,px:x,pz:z,vx:0,vz:0,moving:false,route:null,routeT:0,
    routePts:null,routeIdx:0,routeStop:false,
    cover:null,stumble:0,throwT:0,scrambled:false};
}

/* ---------- formations + drives ---------- */
function setupDrive(team, ballOn){
  G.possession=team;
  G.ballOn=ballOn; G.losX=GOAL0+ballOn;
  G.down=1; G.lineToGain=50; G.crossedMid=(ballOn>=50);
  if(G.crossedMid) G.lineToGain=100;
  G.playT=0; G.cpuDropped=false; G.target=null;
  G.play=null; G.runPlay=false; G.handoffDone=false; G.handoffTarget=null;
  G.handoffGrace=0;
  G.cpuPickT=0; G.cpuSnapT=0;
  setupFormation(team);
  G.ball={state:'held',x:G.players[G.qb].x,z:G.players[G.qb].z,h:0};
  G.camX=G.losX-CAM_BACK; G.camZ=26.5; G._prevBX=G.losX;
  updateCamBasis();
  updateUserControl();
  updateDownLine();
  // the play-call screen opens for every new drive IN PLAY; on the menu
  // (mode 'start') the drive is set up but the play-call stays hidden
  // until START GAME is pressed
  if(G.mode==='play'){
    G.phase='playcall';
    showPlaycall();
  } else {
    G.phase='preSnap';
  }
}
function setupFormation(offTeam){
  const los=G.losX, cz=FZ1/2;
  const P=[];
  // offense: QB + 2 WR + 2 TE + 2 OL = 7. OL just block in place.
  const off=[
    {num:12,role:'QB', x:los-4, z:cz},
    {num:81,role:'WR', x:los+2, z:8},
    {num:84,role:'WR', x:los+2, z:45},
    {num:88,role:'TE', x:los-2, z:18},
    {num:87,role:'TE', x:los-2, z:35},
    {num:64,role:'OL', x:los,   z:22},
    {num:66,role:'OL', x:los,   z:31}
  ];
  off.forEach(function(o){
    const p=mkPlayer(offTeam,o.num,o.role,o.x,o.z);
    if(o.role==='QB'){ p.hasBall=true; }
    P.push(p);
  });
  // defense: 2 DL + 2 LB + 3 DB
  const def=[
    {num:55,role:'DL', x:los+1, z:22},
    {num:56,role:'DL', x:los+1, z:31},
    {num:52,role:'LB', x:los+5, z:18},
    {num:53,role:'LB', x:los+5, z:35},
    {num:21,role:'DB', x:los+6, z:8},
    {num:24,role:'DB', x:los+6, z:cz},
    {num:27,role:'DB', x:los+6, z:45}
  ];
  def.forEach(function(o){ P.push(mkPlayer(1-offTeam,o.num,o.role,o.x,o.z)); });
  G.players=P;
  G.qb=P.findIndex(function(p){return p.team===offTeam&&p.role==='QB';});
  // man coverage: pair each backer/DB with the receiver nearest him at
  // the snap — the old index pairing crossed the DBs (the right wideout's
  // man started on the far side of the field, so the right side was wide
  // open for a free throw). Backers take their man first (they sit on the
  // tight ends), then the DBs take theirs; an extra man doubles the
  // nearest receiver instead of leaving one open.
  const defs=P.filter(function(p){return p.team!==offTeam;});
  const skills=P.filter(function(p){return p.team===offTeam&&p.role!=='QB'&&p.role!=='OL';});
  const covs=defs.filter(function(d){return d.role==='LB'||d.role==='DB';});
  covs.sort(function(a,b){ return (a.role==='DB')-(b.role==='DB'); }); // LBs first
  const taken=[];
  covs.forEach(function(d){
    let best=null,bd=1e9;
    skills.forEach(function(s){
      if(taken.indexOf(s)>=0) return;
      const dd=Math.hypot(d.x-s.x,d.z-s.z);
      if(dd<bd){bd=dd;best=s;}
    });
    if(!best){ // more coverage men than receivers: double the nearest one
      skills.forEach(function(s){ const dd=Math.hypot(d.x-s.x,d.z-s.z); if(dd<bd){bd=dd;best=s;} });
    }
    d.cover=best; if(best&&taken.indexOf(best)<0) taken.push(best);
  });
  P.forEach(function(p){ p.pose='stance'; p.poseT=0; p.cool=0; p.diveT=0; p.stumble=0; });
}

/* ---------- playbook: 3 real plays, routes as waypoints ----------
   Each route is a list of {dx, dz} offsets in yards from the receiver's
   starting spot (dx = upfield, dz = across). The diagram and the actual
   run use the SAME waypoint list, so what you see is what they run.
   WR at z=8 is the left wideout (sideline z=0 side); WR at z=45 is the
   right wideout. TE at z=18 lines up left of center, TE at z=35 right. */
const PLAYS=[
  { name:'CORNERS', type:'PASS', run:false,
    routes:{ WR8:[{dx:8,dz:0},{dx:20,dz:-12}], WR45:[{dx:8,dz:0},{dx:20,dz:12}],
             TE18:[{dx:5,dz:0,stop:true}], TE35:[{dx:5,dz:0,stop:true}] } },
  { name:'CROSSINGS', type:'PASS', run:false,
    routes:{ WR8:[{dx:5,dz:0},{dx:14,dz:18}], WR45:[{dx:5,dz:0},{dx:14,dz:-18}],
             TE18:[{dx:4,dz:6}], TE35:[{dx:4,dz:-6}] } },
  { name:'HB SPRINT', type:'RUN', run:true, handoff:'TE18',
    routes:{ WR8:[{dx:6,dz:0,stop:true}], WR45:[{dx:6,dz:0,stop:true}],
             TE18:[{dx:-2,dz:8,stop:true}], TE35:[{dx:3,dz:0,stop:true}] } },
  { name:'GO DEEP', type:'PASS', run:false,
    routes:{ WR8:[{dx:25,dz:0}], WR45:[{dx:25,dz:0}],
             TE18:[{dx:5,dz:0,stop:true}], TE35:[{dx:5,dz:0,stop:true}] } },
  { name:'SLANTS', type:'PASS', run:false,
    routes:{ WR8:[{dx:6,dz:10}], WR45:[{dx:6,dz:-10}],
             TE18:[{dx:4,dz:-8}], TE35:[{dx:4,dz:8}] } },
  { name:'HB SWEEP', type:'RUN', run:true, handoff:'TE35',
    routes:{ WR8:[{dx:6,dz:0,stop:true}], WR45:[{dx:6,dz:0,stop:true}],
             TE18:[{dx:3,dz:0,stop:true}], TE35:[{dx:-2,dz:-8,stop:true}] } }
];
function routeKey(p){ return p.role+(p.role==='WR'?(p.z<26?'8':'45'):p.role==='TE'?(p.z<26?'18':'35'):''); }
function assignRoutes(){
  const play=G.play; if(!play) return;
  G.players.forEach(function(p){
    if(p.team!==G.possession) return;
    if(p.role==='WR'||p.role==='TE'){
      const key=routeKey(p);
      const wps=play.routes[key];
      if(!wps) return;
      p.routePts=wps.map(function(w){
        return {x:p.x+w.dx, z:clamp(p.z+w.dz,2,51), stop:!!w.stop};
      });
      p.routeIdx=0; p.routeStop=false; p.routeT=0;
    }
  });
}
function showPlaycall(){
  // In PvC only the HOME offense picks (the CPU picks for AWAY). In PvP
  // the offense's human picks -- host when HOME has it, guest when AWAY
  // has it. The defense never sees the playcall overlay.
  if(G.possession===G.myTeam){
    $('playcallTitle').textContent=downName(G.down)+' & '+Math.max(1,G.lineToGain-G.ballOn)+' \u2022 BALL ON '+G.ballOn+'  \u2014  CHOOSE YOUR PLAY';
    $('playcallOverlay').classList.remove('hidden');
    for(let i=0;i<PLAYS.length;i++) drawPlayDiagram(i);
  } else {
    $('playcallOverlay').classList.add('hidden');
  }
  updatePlayClock();
}
function drawPlayDiagram(i){
  const cvEl=$('playCanvas'+i);
  if(!cvEl) return;
  const c=cvEl.getContext('2d');
  if(!c) return;
  const play=PLAYS[i];
  const Wd=220, Hd=150;
  c.fillStyle='#14532d'; c.fillRect(0,0,Wd,Hd);
  // mini field: x maps to the line of scrimmage at the left, end zone
  // at the right; z maps top to bottom (z=0 at the top)
  function mx(x){ return 30+(x-G.losX+8)*5.2; }
  function mz(z){ return 12+z*2.4; }
  c.strokeStyle='rgba(255,255,255,.35)'; c.lineWidth=1;
  for(let x=0;x<=30;x+=10){ c.beginPath(); c.moveTo(mx(G.losX+x),10); c.lineTo(mx(G.losX+x),138); c.stroke(); }
  c.strokeStyle='#f5c518'; c.lineWidth=2;
  c.beginPath(); c.moveTo(mx(G.losX),10); c.lineTo(mx(G.losX),138); c.stroke();
  // formation dots
  const los=G.losX;
  const offSpots=[{role:'QB',x:los-4,z:26.5},{role:'WR',x:los+2,z:8},{role:'WR',x:los+2,z:45},
                  {role:'TE',x:los-2,z:18},{role:'TE',x:los-2,z:35},{role:'OL',x:los,z:22},{role:'OL',x:los,z:31}];
  const defSpots=[{x:los+1,z:22},{x:los+1,z:31},{x:los+5,z:18},{x:los+5,z:35},{x:los+6,z:8},{x:los+6,z:26.5},{x:los+6,z:45}];
  defSpots.forEach(function(d){ c.fillStyle='#5aa9ff'; c.beginPath(); c.arc(mx(d.x),mz(d.z),5,0,7); c.fill(); });
  offSpots.forEach(function(o){ c.fillStyle='#ff5a5a'; c.beginPath(); c.arc(mx(o.x),mz(o.z),5,0,7); c.fill(); });
  // route arrows (yellow chalk) — the same waypoints the receivers run
  c.strokeStyle='#f5c518'; c.fillStyle='#f5c518'; c.lineWidth=2.5;
  ['WR8','WR45','TE18','TE35'].forEach(function(key){
    const wps=play.routes[key];
    if(!wps) return;
    const spot=offSpots.find(function(o){
      return (key==='WR8'&&o.role==='WR'&&o.z<26)||(key==='WR45'&&o.role==='WR'&&o.z>26)||
             (key==='TE18'&&o.role==='TE'&&o.z<26)||(key==='TE35'&&o.role==='TE'&&o.z>26);
    });
    if(!spot) return;
    let px=mx(spot.x), py=mz(spot.z);
    c.beginPath(); c.moveTo(px,py);
    wps.forEach(function(w){
      const nx=mx(spot.x+w.dx), ny=mz(spot.z+w.dz);
      c.lineTo(nx,ny); px=nx; py=ny;
    });
    c.stroke();
    // arrowhead at the end
    const last=wps[wps.length-1];
    const prev=wps.length>1?wps[wps.length-2]:{dx:0,dz:0};
    const ax=mx(spot.x+last.dx)-mx(spot.x+prev.dx), ay=mz(spot.z+last.dz)-mz(spot.z+prev.dz);
    const al=Math.hypot(ax,ay)||1, ux=ax/al, uy=ay/al;
    c.beginPath();
    c.moveTo(px,py);
    c.lineTo(px-ux*9-uy*4,py-uy*9+ux*4);
    c.lineTo(px-ux*9+uy*4,py-uy*9-ux*4);
    c.closePath(); c.fill();
  });
  // run play: draw the handoff arrow from the QB to the halfback
  // (the tight end named by the play — TE18 on the left, TE35 on the right)
  if(play.run){
    const qbSpot=offSpots[0];
    const hbSpot=offSpots.find(function(o){
      return (play.handoff==='TE18'&&o.role==='TE'&&o.z<26)||
             (play.handoff==='TE35'&&o.role==='TE'&&o.z>26);
    })||offSpots[3];
    c.strokeStyle='#fff'; c.lineWidth=2;
    c.beginPath(); c.moveTo(mx(qbSpot.x),mz(qbSpot.z)); c.lineTo(mx(hbSpot.x),mz(hbSpot.z)); c.stroke();
    c.fillStyle='#fff'; c.beginPath(); c.arc(mx(hbSpot.x),mz(hbSpot.z),3,0,7); c.fill();
  }
  G._diagramsDrawn=(G._diagramsDrawn||0)+1;
}
function pickPlay(i, remote){
  if(G.mode!=='play'||G.phase!=='playcall') return;
  if(i<0||i>=PLAYS.length) return;
  G.play=PLAYS[i];
  G.runPlay=!!PLAYS[i].run;
  $('playcallOverlay').classList.add('hidden');
  assignRoutes();
  if(G.runPlay){
    // the halfback is the tight end named by the play (TE18 or TE35)
    const hb=G.players.find(function(p){ return p.team===G.possession&&routeKey(p)===G.play.handoff; });
    G.handoffTarget=hb||null;
  }
  G.phase='preSnap';
  G.playClock=PLAY_CLOCK;
  if(G.pvp) G.pvp.playOver=false;
  updatePlayClock();
  updateLabels();
  beep(520,0.08,'square');
  // PvP: I picked the play -- tell the other phone which one, so their
  // receivers run the same routes. (Remote picks are not re-posted.)
  if(pvpIsOn()&&!remote&&G.possession===G.myTeam){
    pvpPostState({ev:{k:'play',team:G.possession,idx:i}});
  }
}
function updatePlayClock(){
  const el=$('playClock');
  if(!el) return;
  if(G.phase==='preSnap'&&G.possession===G.myTeam){
    el.textContent='\u2022 PLAY :'+Math.ceil(G.playClock);
  } else {
    el.textContent='';
  }
}
function newGame(){
  G.score=[0,0]; G.elapsed=0; G.turbo=100; G.pause=0; G.afterPause=false;
  G.shake=0; G.nextDrive=null; G._lastCarrier=null;
  setupDrive(0,20); // HOME ball first, own 20
  updateScore();
}
function updateScore(){
  $('scoreHome').textContent=G.score[0];
  $('scoreAway').textContent=G.score[1];
}
function downName(d){ return ['1ST','2ND'][clamp(d,1,2)-1]; }
function updateDownLine(){
  const toGo=Math.max(1,G.lineToGain-G.ballOn);
  $('downText').textContent=downName(G.down)+' & '+toGo+' \u2022 BALL ON '+G.ballOn;
  $('fdText').textContent=G.lineToGain===50?'\u2022 1ST DOWN AT 50':'\u2022 GOAL TO GO';
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
  const bs=$('btnSnap'), bp=$('btnPass');
  if(off){
    bs.textContent='SNAP';
    bp.textContent='PASS'; bs.classList.remove('def'); bp.classList.remove('def');
  } else {
    bs.textContent='SWITCH'; bp.textContent='TACKLE'; bs.classList.add('def'); bp.classList.add('def');
  }
}
function updateUserControl(){
  const bh=holder();
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

/* ---------- pass targeting ----------
   PASS throws to the receiver in the direction the joystick is pointing.
   Stick centered = the most open receiver (biggest gap to his nearest
   defender). The target gets a gold marker so you always know who is
   getting the ball. */
function eligibleReceivers(){
  return G.players.filter(function(p){
    return p.team===G.possession&&(p.role==='WR'||p.role==='TE');
  });
}
function computeTarget(){
  const qb=G.players[G.qb];
  if(!qb||G.phase!=='live') return null;
  const recs=eligibleReceivers();
  if(!recs.length) return null;
  const sx=stick.x, sy=stick.y;
  const aiming=Math.hypot(sx,sy)>0.3;
  let best=null, bestScore=-1e9;
  recs.forEach(function(r){
    // openness: distance to the nearest defender
    let nd=1e9;
    G.players.forEach(function(d){
      if(d.team!==r.team){ const dd=d2(d.x,d.z,r.x,r.z); if(dd<nd) nd=dd; }
    });
    let score=nd;
    if(aiming){
      // aim the stick at a receiver, camera-relative: stick up = downfield,
      // stick right = across the field (same mapping as movement)
      const wx=stick.x*CAM.rx-stick.y*CAM.fx;
      const wz=stick.x*CAM.rz-stick.y*CAM.fz;
      const dx=r.x-qb.x, dz=r.z-qb.z, dd=Math.hypot(dx,dz)||1;
      const align=(dx/dd)*wx+(dz/dd)*wz;
      score=align*40+nd*0.5;
    }
    if(score>bestScore){ bestScore=score; best=r; }
  });
  return best;
}
function snap(remote){
  if(G.mode!=='play'||G.phase!=='preSnap') return;
  G.phase='live'; G.playT=0; G.cpuDropped=false; G.handoffDone=false;
  // routes were assigned at the play call; if a test or a shortcut
  // snapped without one, fall back to the first play in the book
  if(!G.play){ G.play=PLAYS[0]; G.runPlay=false; assignRoutes(); }
  // CPU QB throws on a timer (faster on higher difficulties)
  if(G.possession===1) G.cpuThrowAt=0.9+Math.random()*0.8;
  updatePlayClock();
  updateLabels();
  beep(440,0.08,'square');
  // PvP: I snapped -- tell the other phone the play is live now.
  // (Remote snaps are not re-posted.)
  if(pvpIsOn()&&!remote&&G.possession===G.myTeam){
    pvpPostState({ev:{k:'snap',team:G.possession}});
  }
}
function throwPass(qb, recv, remote, rx, rz){
  if(!qb||!qb.hasBall||!recv) return;
  qb.hasBall=false; qb.pose='throw'; qb.poseT=0; qb.throwT=0;
  // lead the receiver: aim where he will be when the ball arrives
  const dist=d2(qb.x,qb.z,recv.x,recv.z);
  const dur=clamp(dist/55,0.3,0.7);
  const leadT=dur;
  const tx=recv.x+recv.vx*leadT, tz=recv.z+recv.vz*leadT;
  // CPU inaccuracy: a bad throw lands off target and is likely incomplete
  let lx=tx, lz=tz;
  if(qb.team===1&&Math.random()>cpuDiff().passAcc){
    lx+= (Math.random()*10-5); lz+=(Math.random()*8-4);
  }
  // PvP: a remote throw lands exactly where the thrower put it -- the
  // landing point rides with the pass event, so both phones agree.
  if(remote&&typeof rx==='number'&&typeof rz==='number'){ lx=rx; lz=rz; }
  G.ball={state:'pass',t:0,dur:dur,
    rx:clamp(lx,FX0,FX1),rz:clamp(lz,FZ0,FZ1),receiver:recv,shooter:qb,
    lastTouch:qb.team,x:qb.x,z:qb.z,h:2};
  G.target=null;
  beep(660,0.08,'sine');
  // PvP: I threw -- tell the other phone who caught it and where the
  // ball lands, so their ball flies the same way.
  // (Remote throws are not re-posted.)
  if(pvpIsOn()&&!remote&&qb.team===G.myTeam){
    pvpPostState({ev:{k:'pass',team:qb.team,qb:qb.num,recv:recv.num,rx:G.ball.rx,rz:G.ball.rz}});
  }
}
function doPass(){
  if(G.mode!=='play'||G.phase!=='live'||G.pause>0) return;
  const me=G.players[G.user];
  if(!me) return;
  if(me.team===G.possession){
    if(!me.hasBall) return;
    const tgt=computeTarget();
    if(tgt) throwPass(me,tgt);
  } else {
    doTackle(me);
  }
}
function doSwitch(){
  if(G.mode!=='play'||G.phase!=='live') return;
  const me=G.players[G.user];
  if(!me||me.team===G.possession) return;
  // SWITCH cycles to the defender from YOUR team nearest the ball (skips
  // the one you already control, so it always moves you)
  const b=G.ball;
  let best=null,bd=1e9;
  G.players.forEach(function(p,i){
    if(p.team===G.myTeam&&i!==G.user){ const d=d2(p.x,p.z,b.x,b.z); if(d<bd){bd=d;best=i;} }
  });
  if(best!==null){ G.user=best; updateLabels(); beep(520,0.06,'square'); }
}
function doTackle(me){
  // dive/lunge: a burst toward the ball carrier with a bigger tackle
  // window while lunging. Cooldown so you can't spam it.
  if(!me||me.cool>0||me.diveT>0) return;
  const bh=holder();
  if(!bh) return;
  const dx=bh.x-me.x, dz=bh.z-me.z, dd=Math.hypot(dx,dz)||1;
  me.diveT=0.25; me.diveX=dx/dd; me.diveZ=dz/dd;
  me.cool=0.9; me.pose='dive'; me.poseT=0;
  thud();
  // PvP: I dove to tackle -- tell the other phone so they see me lunge.
  if(pvpIsOn()&&me.team===G.myTeam&&G.players[G.user]===me){
    pvpPostState({ev:{k:'tackle',team:me.team,num:me.num}});
  }
}
function tryTackle(){
  const bh=holder();
  if(!bh||G.phase!=='live') return false;
  if(G.handoffGrace>0) return false; // the defense needs a beat to react to a handoff
  let tackled=false;
  G.players.forEach(function(d){
    if(d.team===bh.team) return;
    const r=d.diveT>0?2.5:1.3; // CONTACT ONLY: a defender must actually reach the carrier (arm's reach ~1.3 yds); a dive covers a little more ground
    if(d2(d.x,d.z,bh.x,bh.z)<r) tackled=true;
  });
  if(tackled){
    const spotX=bh.x, spotZ=bh.z;
    const behind=bh.x<G.losX;
    bh.hasBall=false;
    finishPlay({type:behind?'sack':'tackle', spotX:spotX, spotZ:spotZ});
    return true;
  }
  return false;
}
function scoreTD(team){
  G.score[team]++;
  updateScore();
  cheer();
  callout('TOUCHDOWN!',team===0?'HOME +1':'AWAY +1');
  G.shake=0.4;
  if(G.score[team]>=TARGET_TD){ endGame(team); return; }
  G.pause=1.6; G.afterPause=true;
  G.nextDrive={team:1-team, ballOn:20};
}
function endGame(team){
  G.mode='over'; G.phase='dead';
  whistle();
  $('finalTitle').textContent=team===0?'HOME WINS!':'AWAY WINS!';
  $('finalScore').innerHTML='<span class="h">'+G.score[0]+'</span> &ndash; <span class="a">'+G.score[1]+'</span>';
  $('finalNote').textContent='First to '+TARGET_TD+' touchdowns. Difficulty: '+cpuDiff().name+' (level '+G.difficulty+' of 5). '+(team===0?'Home takes it at the park.':'Away takes it at the park.');
  $('endOverlay').classList.remove('hidden');
}
function finishPlay(res, remote){
  // res: {type:'tackle'|'sack'|'oob'|'incomplete'|'int'|'td', spotX, spotZ}
  // PvP: the play outcome is posted by the side that detects it first.
  // Once an outcome is posted or applied, this play is over -- a second
  // local detection (positions drift slightly between phones) is ignored.
  if(pvpIsOn()){
    if(G.pvp.playOver&&!remote) return;
    if(!remote){
      G.pvp.playOver=true;
      pvpPostState({ev:{k:'outcome',team:G.possession,type:res.type,spotX:res.spotX,spotZ:res.spotZ}});
    }
  }
  G.phase='dead';
  G.target=null; // the play is over — no pass target any more
  if(res.type==='td'){ scoreTD(G.possession); return; }
  if(res.type==='int'){
    callout('INTERCEPTED!','');
    G.pause=1.4; G.afterPause=true;
    // possession was ALREADY flipped to the intercepting team by
    // updateBall — the new team takes over at its own 20
    G.nextDrive={team:G.possession, ballOn:20};
    return;
  }
  if(res.type==='incomplete'){
    callout('INCOMPLETE','');
  } else if(res.type==='sack'){
    const lost=Math.max(0,Math.round(G.losX-res.spotX));
    callout('SACKED!','-'+lost+' YDS');
  } else if(res.type==='oob'){
    callout('OUT OF BOUNDS','');
  } else {
    callout('TACKLED','');
  }
  // downs: new spot -> new ball-on; crossing the line to gain = 1st down
  const newBallOn=ballOnYard(res.spotX);
  const gained=newBallOn-G.ballOn;
  G.ballOn=newBallOn; G.losX=res.spotX;
  if(newBallOn>=G.lineToGain){
    callout('1ST DOWN!','');
    G.down=1;
    if(G.lineToGain===50){ G.lineToGain=100; G.crossedMid=true; }
  } else {
    G.down++;
  }
  updateDownLine();
  if(G.down>2){
    callout('TURNOVER ON DOWNS','');
    G.pause=1.4; G.afterPause=true;
    G.nextDrive={team:1-G.possession, ballOn:20};
    return;
  }
  G.pause=1.1; G.afterPause=true;
  G.nextDrive={team:G.possession, ballOn:G.ballOn, keepDown:true};
}
function nextSetup(){
  const nd=G.nextDrive; G.nextDrive=null;
  if(!nd) return;
  if(nd.keepDown){
    // same drive, next down: re-form at the new line of scrimmage, keep
    // the down count and the line to gain
    const keepDown=G.down, keepLine=G.lineToGain, keepMid=G.crossedMid;
    setupDrive(nd.team, nd.ballOn);
    G.down=keepDown; G.lineToGain=keepLine; G.crossedMid=keepMid;
    updateDownLine();
  } else {
    setupDrive(nd.team, nd.ballOn);
  }
  callout(nd.team===0?'HOME BALL':'AWAY BALL','');
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
$('btnSnap').addEventListener('pointerdown',function(e){
  e.preventDefault();
  if(G.mode!=='play') return;
  if(G.phase==='preSnap'){ snap(); return; }
  doSwitch(); // on defense, SNAP button = SWITCH
});
$('btnPass').addEventListener('pointerdown',function(e){e.preventDefault();doPass();});
for(let i=0;i<PLAYS.length;i++){
  (function(idx){
    const card=$('playCard'+idx);
    if(card) card.addEventListener('click',function(){ pickPlay(idx); });
  })(i);
}
window.addEventListener('keydown',function(e){
  if(!$('gameView').classList.contains('open')) return;
  const k=e.key.toLowerCase();
  if(k==='arrowup'||k==='w') dirs.up=true;
  if(k==='arrowdown') dirs.down=true;
  if(k==='arrowleft'||k==='a') dirs.left=true;
  if(k==='arrowright'||k==='d') dirs.right=true;
  if(k==='1'&&!e.repeat) pickPlay(0);
  if(k==='2'&&!e.repeat) pickPlay(1);
  if(k==='3'&&!e.repeat) pickPlay(2);
  if(k==='4'&&!e.repeat) pickPlay(3);
  if(k==='5'&&!e.repeat) pickPlay(4);
  if(k==='6'&&!e.repeat) pickPlay(5);
  if(k==='s'||k===' '){ if(!e.repeat){ if(G.phase==='preSnap') snap(); else doPass(); } }
  if(k==='x'&&!e.repeat) doSwitch();
  if(k==='c'&&!e.repeat){ const me=G.players[G.user]; if(me) doTackle(me); }
  if(k==='shift') G.turboHeld=true;
  if(['arrowup','arrowdown','arrowleft','arrowright',' '].indexOf(k)>=0) e.preventDefault();
});
window.addEventListener('keyup',function(e){
  const k=e.key.toLowerCase();
  if(k==='arrowup'||k==='w') dirs.up=false;
  if(k==='arrowdown') dirs.down=false;
  if(k==='arrowleft'||k==='a') dirs.left=false;
  if(k==='arrowright'||k==='d') dirs.right=false;
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
/* ---------- PvP room (create / join) ---------- */
function pvpSetStatus(t){ var el=document.getElementById('pvpStatus'); if(el) el.textContent=t; }
function pvpSetRoomLbl(t){ var el=document.getElementById('pvpRoomLbl'); if(el) el.textContent=t; }
$('pvpBtn').addEventListener('click',function(){
  document.getElementById('pvpPanel').classList.toggle('hidden');
});
$('pvpCreateBtn').addEventListener('click',function(){
  var who=pvpPlayer();
  pvpSetStatus('Creating room...');
  pvpPost('/create',{player_id:who.id,player_name:who.name,game:'football'}).then(function(room){
    if(!room||!room.code){ pvpSetStatus('Could not create a room — check your connection and try again.'); return; }
    G.myTeam=0; // host is HOME
    G.pvp={code:room.code,role:'host',oppName:'',seq:0,oppSeq: -1,pollTimer:null,posT:0,playOver:false};
    pvpSetStatus('Room created! Give this code to the other player:');
    pvpSetRoomLbl('CODE: '+room.code+' — waiting for them to join...');
    pvpStartPoll();
  });
});
$('pvpJoinBtn').addEventListener('click',function(){
  var code=(document.getElementById('pvpCodeInput').value||'').trim();
  if(!/^[0-9]{4}$/.test(code)){ pvpSetStatus('Enter the 4-digit code from the other phone.'); return; }
  var who=pvpPlayer();
  pvpSetStatus('Joining room '+code+'...');
  pvpPost('/join',{code:code,player_id:who.id,player_name:who.name}).then(function(room){
    if(!room||!room.code){ pvpSetStatus('Room not found — check the code and try again.'); return; }
    G.myTeam=1; // guest is AWAY
    G.pvp={code:room.code,role:'guest',oppName:room.host_name||'Opponent',seq:0,oppSeq: -1,pollTimer:null,posT:0,playOver:false};
    pvpSetStatus('Joined! You are AWAY.');
    pvpSetRoomLbl('CODE: '+room.code+' — vs '+G.pvp.oppName);
    pvpStartPoll();
    callout('WAITING FOR HOST','The host starts the game.');
  });
});
$('endBackBtn').addEventListener('click',closeGame);
$('backBtn').addEventListener('click',closeGame);
window.addEventListener('resize',fitCanvas);

function fitCanvas(){
  const w=$('canvasWrap'); if(!w) return;
  const r=w.getBoundingClientRect();
  const scale=Math.min(r.width/W,r.height/H);
  cv.style.width=(W*scale)+'px'; cv.style.height=(H*scale)+'px';
  cv.style.left=((r.width-W*scale)/2)+'px'; cv.style.top=((r.height-H*scale)/2)+'px';
}
function openGame(){
  $('endOverlay').classList.add('hidden');
  $('playcallOverlay').classList.add('hidden');
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
  G.mode='play';
  newGame();
  callout('HOME BALL','');
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
  if(dd<1.5) return;
  p.x=clamp(p.x+dx/dd*sp*dt,FX0-2,FX1+2);
  p.z=clamp(p.z+dz/dd*sp*dt,FZ0-2,FZ1+2);
}
function nearestDefTo(p){
  let best=1e9;
  G.players.forEach(function(q){ if(q.team!==p.team){ const d=d2(p.x,p.z,q.x,q.z); if(d<best) best=d; } });
  return best;
}
function updateAI(dt){
  const D=cpuDiff();
  const bh=holder();
  // PvP: the opponent's controlled player is a real person -- the AI
  // must not drive them. (In PvC this is null and nothing changes.)
  var oppCtrl=pvpIsOn()?pvpOppCtrl():null;
  G.players.forEach(function(p,i){
    if(i===G.user) return;
    if(oppCtrl&&p===oppCtrl) return;
    if(p.cool>0) p.cool-=dt;
    if(p.stumble>0){ p.stumble-=dt; return; }
    if(G.phase!=='live') return;
    // diving: ride the lunge
    if(p.diveT>0){
      p.diveT-=dt;
      p.x+=p.diveX*26*dt; p.z+=p.diveZ*26*dt;
      return;
    }
    let tx=null,tz=null,sp=11;
    if(G.ball&&G.ball.state==='pass'){
      // everyone converges on the landing point — that is how picks happen
      tx=G.ball.rx; tz=G.ball.rz; sp=12.5;
      if(p.team===1) sp*=D.speed;
      moveToward(p,tx,tz,sp,dt);
      return;
    }
    if(p.team===G.possession){
      if(p.hasBall){
        if(p.team===1){
          // CPU ball carrier: run for the end zone, wiggle to dodge.
          // The pocket QB is excluded — the dedicated CPU QB block below
          // runs him until he scrambles (then he is a runner too).
          if(p.role==='QB'&&!p.scrambled){ /* pocket QB: handled below */ }
          else {
            // CPU ball carrier: run for the end zone. Aim PAST the goal
            // line — moveToward stops 1.5 yards short of its target, so
            // aiming at the line itself left the carrier standing a yard
            // short, waiting to be tackled. No wiggle inside 10 yards:
            // the sideways dodge made him run along the line, not over it.
            const distToGoal=GOAL1-p.x;
            const wiggle=distToGoal>10?Math.sin(G.elapsed*3+p.num)*4:0;
            tx=GOAL1+10; tz=p.z+wiggle;
            sp=11*(p.role==='QB'?0.95:1);
            moveToward(p,tx,tz,sp*D.speed,dt);
          }
        }
        // HOME ball carrier is always the user — nothing to do
      } else if(p.role==='WR'||p.role==='TE'){
        // run the route waypoints, then drift upfield (or hold to block
        // when the last waypoint says stop)
        if(p.routePts&&p.routeIdx<p.routePts.length){
          const wp=p.routePts[p.routeIdx];
          moveToward(p,wp.x,wp.z,11.5,dt);
          if(d2(p.x,p.z,wp.x,wp.z)<2){
            if(wp.stop){ p.routeStop=true; p.routeIdx=p.routePts.length; }
            else p.routeIdx++;
          }
        } else if(!p.routeStop){
          moveToward(p,p.x+14,p.z,11.5,dt);
        }
      } else if(p.role==='OL'){
        // block in place: shuffle to stay between the nearest rusher and the QB
        const qb=G.players[G.qb];
        let rusher=null,rd=1e9;
        G.players.forEach(function(q){
          if(q.team!==p.team&&(q.role==='DL'||q.role==='LB')){ const d=d2(q.x,q.z,qb.x,qb.z); if(d<rd){rd=d;rusher=q;} }
        });
        if(rusher){ moveToward(p,(qb.x+rusher.x)/2,(qb.z+rusher.z)/2,7,dt); }
      }
    } else {
      // defense
      if(bh&&bh.hasBall){
        const pastLOS=bh.x>G.losX+2;
        const nearMe=d2(p.x,p.z,bh.x,bh.z)<6; // close enough to actually pressure — 12 pulled coverage men off short routes near the line
        if(p.role==='DL'||G.runPlay||pastLOS||nearMe){
          // rush / pursue: the line always rushes; on a RUN play the
          // backers come up too; on a pass play the backers and DBs hold
          // coverage unless the carrier is past the line or close by.
          // Lead the carrier only from a distance — up close the lead
          // makes the defender step PAST him, and the separation shove
          // then knocks the carrier back off the tackle spot.
          const leadD=d2(p.x,p.z,bh.x,bh.z);
          const lead=leadD<3?0:0.25;
          tx=bh.x+bh.vx*lead; tz=bh.z+bh.vz*lead;
          sp=(p.role==='DL'?10.5:11.5)*(p.team===1?D.speed:1);
          // blocked by the line: an offensive lineman within 4 yards
          // engages the rusher and HOLDS him for ~2 seconds (the pocket
          // stays up long enough to throw), then the rusher sheds the
          // block and the pocket collapses. Without the hold the rush
          // arrives in under half a second and no QB ever gets a throw off.
          let blocked=false;
          G.players.forEach(function(o){
            if(o.team===bh.team&&o.role==='OL'&&d2(p.x,p.z,o.x,o.z)<4) blocked=true;
          });
          if(blocked){
            // the timer survives brief breaks in contact (the line
            // shuffles, the rusher slips a yard) — it only drains when
            // he is genuinely free, so the shed still comes at ~2s
            p.blockT=(p.blockT||0)+dt;
            if(p.blockT<2) sp*=0.05;
          } else p.blockT=Math.max(0,(p.blockT||0)-dt*0.5);
          moveToward(p,tx,tz,sp,dt);
          // CPU dive when close enough for the dive to connect (not from 7 yards out)
          if(p.team===1&&d2(p.x,p.z,bh.x,bh.z)<3&&p.cool<=0&&Math.random()<dt*0.5*D.tackle){
            p.cool=1.2; doTackle(p);
          }
          return;
        }
        // man coverage: tight — stay on the receiver's hip (1.5 yards
        // goal-side) and lead his movement, so he doesn't get open on
        // route breaks
        if(p.cover){
          const r=p.cover;
          const cov=(p.team===1)?D.coverage:1;
          tx=r.x+1.5*cov+(r.vx||0)*0.25; tz=r.z+(r.vz||0)*0.25;
          sp=11.5*(p.team===1?D.speed:1);
          moveToward(p,tx,tz,sp,dt);
        }
      } else if(p.cover){
        // man coverage: tight — stay on the receiver's hip (1.5 yards
        // goal-side) and lead his movement, so he doesn't get open on
        // route breaks
        const r=p.cover;
        const cov=(p.team===1)?D.coverage:1;
        tx=r.x+1.5*cov+(r.vx||0)*0.25; tz=r.z+(r.vz||0)*0.25;
        sp=11.5*(p.team===1?D.speed:1);
        moveToward(p,tx,tz,sp,dt);
      }
    }
  });
  // CPU QB: drop back, then throw to the most open receiver — or scramble
  // if the rush gets home before the throw timer fires.
  // PvP: when AWAY has the ball, the guest human is the QB -- the CPU
  // timer does not throw for them.
  if(G.phase==='live'&&G.possession===1&&!(pvpIsOn()&&G.myTeam===1)){
    const qb=G.players[G.qb];
    if(qb&&qb.hasBall){
      if(!G.cpuDropped){
        // drop back a couple of steps, then plant
        if(G.playT<0.5){ qb.x-=8*dt; }
        else G.cpuDropped=true;
      } else if(G.playT>=G.cpuThrowAt){
        let best=null,bnd=-1;
        eligibleReceivers().forEach(function(r){
          const nd=nearestDefTo(r);
          if(nd>bnd){ bnd=nd; best=r; }
        });
        if(best) throwPass(qb,best);
        else { qb.scrambled=true; qb.x+=4*dt; } // no one open: tuck and run
      } else {
        // pressure check: a rusher within 3.5 yards forces a scramble
        let press=false;
        G.players.forEach(function(d){
          if(d.team===0&&d2(d.x,d.z,qb.x,qb.z)<3.5) press=true;
        });
        if(press){
          qb.scrambled=true;
          qb.x+=9*dt; qb.z+=((qb.z<26)?1:-1)*7*dt;
        }
      }
    }
  }
}
function updateAnim(dt){
  G.players.forEach(function(p){
    const prevPose=p.pose;
    const vx=(p.x-p.px)/Math.max(dt,0.001), vz=(p.z-p.pz)/Math.max(dt,0.001);
    p.vx=vx; p.vz=vz;
    const spd=Math.hypot(vx,vz);
    p.moving=spd>2;
    if(p.moving){
      p.step+=spd*dt*0.09;
      if(spd>2){ const ang=Math.atan2(vz,vx); p.faceYaw=ang; }
      if(Math.abs(vx)>2) p.face=vx>0?1:-1;
    }
    // locked poses clear on timeout
    if(p.pose==='throw'){ if(p.poseT>0.45) p.pose=null; }
    else if(p.pose==='dive'){ if(p.diveT<=0&&p.poseT>0.3) p.pose=null; }
    else if(p.pose==='catch'){ if(p.poseT>0.5) p.pose=null; }
    // continuous poses recomputed every frame
    if(!p.pose||p.pose==='idle'||p.pose==='run'||p.pose==='stance'||p.pose==='block'||p.pose==='catch'){
      let np;
      if(G.phase==='preSnap'||G.phase==='playcall') np='stance';
      else if(p.diveT>0) np='dive';
      else if(p.hasBall) np='run';
      else if(p.role==='OL'&&G.phase==='live') np='block';
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
    // world-space arc: the ball flies from the thrower's hands to the
    // landing point, peaking ~6 yards up mid-flight
    const sx0=b.shooter.x, sz0=b.shooter.z;
    b.x=lerp(sx0,b.rx,t);
    b.z=lerp(sz0,b.rz,t);
    b.h=2+6*Math.sin(Math.PI*t);
    if(b.t>=1){
      // arrival: the defender picks it off only if he beats the receiver
      // to the spot by a quarter yard — a defender who is merely a hair
      // closer than a covered receiver does not steal it. (The old rule —
      // any defender closer than the receiver, inside 5 yards — picked
      // off nearly half of all throws to a covered receiver.)
      let defBest=null,defD=1e9, recD=1e9;
      G.players.forEach(function(p){
        const d=d2(p.x,p.z,b.rx,b.rz);
        if(p.team!==b.shooter.team){ if(d<defD){defD=d;defBest=p;} }
        else if(p===b.receiver){ recD=d; }
      });
      if(defBest&&defD<5&&defD<recD-0.25){
        defBest.hasBall=true; defBest.pose='catch'; defBest.poseT=0;
        G.ball={state:'held',x:defBest.x,z:defBest.z,h:0};
        G.possession=defBest.team;
        finishPlay({type:'int', spotX:defBest.x, spotZ:defBest.z});
        return;
      }
      if(b.receiver&&recD<6){
        const r=b.receiver;
        r.hasBall=true; r.pose='catch'; r.poseT=0;
        G.ball={state:'held',x:r.x,z:r.z,h:0};
        G.possession=r.team;
        updateUserControl();
        if(r.x>=GOAL1){ finishPlay({type:'td', spotX:r.x, spotZ:r.z}); }
        return;
      }
      // nobody there: incomplete, ball dead at the spot
      G.ball={state:'dead',x:b.rx,z:b.rz,h:0};
      finishPlay({type:'incomplete', spotX:G.losX, spotZ:b.shooter.z});
    }
  } else if(b.state==='held'){
    const h=holder();
    if(h){ b.x=h.x; b.z=h.z; }
  }
}
function update(dt){
  G.elapsed+=dt;
  if(G.shake>0) G.shake=Math.max(0,G.shake-dt);
  if(G.pause>0){
    G.pause-=dt;
    if(G.pause<=0&&G.afterPause){
      G.afterPause=false;
      if(G.mode==='over') return;
      nextSetup();
    }
    return;
  }
  if(G.mode!=='play') return;
  dt=Math.min(dt,0.05);
  // play-call phase: the computer picks its own play after a beat.
  // PvP: when AWAY has the ball, the guest human picks -- the CPU
  // does not pick for them.
  if(G.phase==='playcall'){
    if(G.possession===1&&!pvpIsOn()){
      G.cpuPickT+=dt;
      if(G.cpuPickT>0.8){
        G.cpuPickT=0;
        pickPlay(Math.floor(Math.random()*PLAYS.length));
      }
    }
    updateCamBasis();
    return;
  }
  // pre-snap: the play clock counts down for the user's offense and
  // auto-snaps at 0; the computer hikes on its own after a beat.
  // PvP: when AWAY has the ball, the guest human snaps -- the CPU
  // does not snap for them.
  if(G.phase==='preSnap'){
    if(G.possession===G.myTeam){
      G.playClock-=dt;
      updatePlayClock();
      if(G.playClock<=0){ snap(); }
    } else if(!pvpIsOn()){
      G.cpuSnapT+=dt;
      if(G.cpuSnapT>1.2){ G.cpuSnapT=0; snap(); }
    }
  } else G.cpuSnapT=0;
  G.playT+=dt;
  // the gold target marker tracks the pass target while the play is live
  if(G.phase==='live'){
    const me=G.players[G.user];
    G.target=(me&&me.team===G.possession&&me.hasBall)?computeTarget():null;
  } else G.target=null;
  // run play: the halfback steps to the QB for the handoff, then takes
  // the ball (when he is close, or after 0.9s at the latest). A short
  // grace after the handoff keeps the defense from tackling him in the
  // same instant — he needs a beat to get going.
  if(G.runPlay&&G.phase==='live'&&!G.handoffDone){
    const qb=G.players[G.qb], hb=G.handoffTarget;
    if(qb&&hb&&qb.hasBall){
      const close=d2(qb.x,qb.z,hb.x,hb.z)<4;
      if(close||G.playT>0.9){
        qb.hasBall=false; hb.hasBall=true; hb.pose='run'; hb.poseT=0;
        G.ball={state:'held',x:hb.x,z:hb.z,h:0};
        G.handoffDone=true; G.handoffGrace=0.3;
        updateUserControl();
        beep(500,0.08,'square');
      }
    }
  }
  if(G.handoffGrace>0) G.handoffGrace-=dt;
  // user movement
  const me=G.players[G.user];
  if(me){
    if(me.stumble>0) me.stumble-=dt;
    else if(me.diveT>0){
      me.diveT-=dt;
      me.x+=me.diveX*26*dt; me.z+=me.diveZ*26*dt;
    } else if(!(me.role==='QB'&&G.phase!=='live')){
      // the QB is set until the snap — he cannot move before it
      let sp=11;
      const turboOn=G.turboHeld&&G.turbo>1;
      if(turboOn){ sp*=1.55; G.turbo=Math.max(0,G.turbo-45*dt); }
      else G.turbo=Math.min(100,G.turbo+18*dt);
      // CAMERA-RELATIVE controls: screen up = downfield (camera forward
      // on the ground), screen right = camera right. Pushing the stick
      // up runs you up the field; pushing it sideways moves you across it.
      const ix=(dirs.right?1:0)-(dirs.left?1:0)+stick.x;
      const iy=(dirs.down?1:0)-(dirs.up?1:0)+stick.y;
      const dx=ix*CAM.rx-iy*CAM.fx;
      const dz=ix*CAM.rz-iy*CAM.fz;
      const len=Math.hypot(dx,dz)||1;
      const stickMag=Math.min(1,Math.hypot(stick.x,stick.y));
      const speedScale=(stick.x||stick.y)?stickMag:1;
      if(dx||dz){
        // once the ball is live anyone can run anywhere on the field
        me.x=clamp(me.x+dx/len*sp*speedScale*dt,FX0-2,FX1+2);
        me.z=clamp(me.z+dz/len*sp*speedScale*dt,FZ0-2,FZ1+2);
      }
    }
    if(me.cool>0) me.cool-=dt;
  }
  updateAI(dt);
  // soft separation (capped per frame: an uncapped shove can knock the
  // ball carrier a full yard off the tackle spot or the goal line).
  // The ball carrier is EXEMPT from the shove entirely — his own line
  // was shoving him around (the QB kept getting pushed off his spot,
  // so a rusher chasing him overshot and never made the tackle).
  // Defenders reach him and tackle him; nobody shoves him.
  const _bh=holder();
  for(let i=0;i<G.players.length;i++) for(let j=i+1;j<G.players.length;j++){
    const a=G.players[i],b=G.players[j];
    if(_bh&&(a===_bh||b===_bh)) continue;
    const dx=b.x-a.x,dz=b.z-a.z,dd=Math.hypot(dx,dz);
    if(dd>0.01&&dd<2.5){ const push=Math.min((2.5-dd)/2,0.3),ux=dx/dd,uz=dz/dd; a.x-=ux*push; a.z-=uz*push; b.x+=ux*push; b.z+=uz*push; }
  }
  updateAnim(dt);
  updateBall(dt);
  updateCamBasis();
  if(G.phase!=='live') return;
  // tackle check (carrier vs every defender)
  if(tryTackle()) return;
  // touchdown: carrier crosses the goal line in bounds
  const bh=holder();
  if(bh&&bh.x>=GOAL1&&bh.z>=FZ0&&bh.z<=FZ1){
    bh.hasBall=false;
    finishPlay({type:'td', spotX:bh.x, spotZ:bh.z});
    return;
  }
  // out of bounds with the ball: play dead at the spot
  if(bh&&(bh.x<FX0||bh.x>FX1||bh.z<FZ0||bh.z>FZ1)){
    const sx=clamp(bh.x,FX0,FX1), sz=clamp(bh.z,FZ0,FZ1);
    bh.hasBall=false;
    finishPlay({type:'oob', spotX:sx, spotZ:sz});
    return;
  }
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
        op.x=clamp(op.x,FX0-2,FX1+2); op.z=clamp(op.z,FZ0-2,FZ1+2);
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
      if(G.pvp.posT >= 0.1){
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

/* Project a 3D point and snap it to the PS1 2px grid. Returns null when
   the point is too close to (or behind) the camera to draw. */
function snapP(x,y,z){
  const pr=proj(x,z,y);
  if(pr.depth<1.2) return null;
  return {x:Math.round(pr.x/2)*2, y:Math.round(pr.y/2)*2, s:pr.s, depth:pr.depth};
}
/* Fill a flat-shaded 3D polygon. pts = [[x,y,z]...] in world space.
   shade: 0 = dark, 1 = main, 2 = top — picks from the given color triple. */
function poly3(pts, cols, shade){
  const P=[];
  for(let i=0;i<pts.length;i++){
    const sp=snapP(pts[i][0],pts[i][1],pts[i][2]);
    if(!sp) return;
    P.push(sp);
  }
  ctx.fillStyle=shade===2?cols[0]:shade===0?cols[2]:cols[1];
  ctx.beginPath();
  ctx.moveTo(P[0].x,P[0].y);
  for(let i=1;i<P.length;i++) ctx.lineTo(P[i].x,P[i].y);
  ctx.closePath(); ctx.fill();
  G._polyCalls=(G._polyCalls||0)+1;
}
/* A 3D box as 6 flat-shaded faces. (cx,cy,cz) = center, w/h/d in yards,
   yaw = facing (radians, 0 = +x downfield), pitch = lean forward.
   cols = [top, main, dark]. Faces whose normal points away from the
   camera are skipped (back-face culling). */
function box3(cx,cy,cz,w,h,d,yaw,pitch,cols){
  const hw=w/2, hh=h/2, hd=d/2;
  const cp=Math.cos(-pitch), sp=Math.sin(-pitch);
  const cyaw=Math.cos(yaw), syaw=Math.sin(yaw);
  const local=[[-hw,-hh,-hd],[hw,-hh,-hd],[hw,hh,-hd],[-hw,hh,-hd],
               [-hw,-hh,hd],[hw,-hh,hd],[hw,hh,hd],[-hw,hh,hd]];
  const world=local.map(function(p){
    const x1=p[0]*cp-p[1]*sp, y1=p[0]*sp+p[1]*cp, z1=p[2];
    return [cx+x1*cyaw-z1*syaw, cy+y1, cz+x1*syaw+z1*cyaw];
  });
  const faces=[
    {c:[0,3,2,1], shade:1}, // back
    {c:[4,5,6,7], shade:1}, // front
    {c:[0,4,7,3], shade:1}, // left
    {c:[1,2,6,5], shade:1}, // right
    {c:[0,1,5,4], shade:0}, // bottom
    {c:[3,7,6,2], shade:2}  // top
  ];
  drawFaces(world,faces,cols);
}
/* A beam (box) from point A to point B, square cross-section width w.
   Used for two-segment limbs: thigh, shin, upper arm, forearm. */
function beam3(ax,ay,az,bx,by,bz,w,cols){
  const dx=bx-ax, dy=by-ay, dz=bz-az;
  const len=Math.hypot(dx,dy,dz)||0.001;
  const d=[dx/len,dy/len,dz/len];
  let u=[-d[2],0,d[0]];
  const ul=Math.hypot(u[0],u[1],u[2]);
  if(ul<0.01) u=[1,0,0]; else { u=[u[0]/ul,u[1]/ul,u[2]/ul]; }
  const v=[d[1]*u[2]-d[2]*u[1], d[2]*u[0]-d[0]*u[2], d[0]*u[1]-d[1]*u[0]];
  const hw=w/2;
  const A=[ax,ay,az], B=[bx,by,bz];
  function off(P,su,sv){
    return [P[0]+u[0]*su*hw+v[0]*sv*hw, P[1]+u[1]*su*hw+v[1]*sv*hw, P[2]+u[2]*su*hw+v[2]*sv*hw];
  }
  const world=[off(A,-1,-1),off(A,1,-1),off(A,1,1),off(A,-1,1),
               off(B,-1,-1),off(B,1,-1),off(B,1,1),off(B,-1,1)];
  // the side whose normal points most upward gets the top shade
  const faces=[
    {c:[0,3,2,1], shade:0}, // A cap
    {c:[4,5,6,7], shade:0}, // B cap
    {c:[0,1,5,4], shade:(v[1]<-0.5?2:1)}, // -v side
    {c:[2,3,7,6], shade:(v[1]>0.5?2:1)},  // +v side
    {c:[0,4,7,3], shade:(u[1]>0.5?2:1)},  // -u side
    {c:[1,2,6,5], shade:(u[1]>0.5?2:1)}   // +u side
  ];
  drawFaces(world,faces,cols);
}
function drawFaces(world,faces,cols){
  // back-face culling against the camera position, far faces first
  const vis=[];
  faces.forEach(function(f){
    const a=world[f.c[0]], b=world[f.c[1]], c2=world[f.c[2]];
    const u=[b[0]-a[0],b[1]-a[1],b[2]-a[2]], v=[c2[0]-a[0],c2[1]-a[1],c2[2]-a[2]];
    const n=[u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]];
    const fc=[(a[0]+world[f.c[2]][0])/2,(a[1]+world[f.c[2]][1])/2,(a[2]+world[f.c[2]][2])/2];
    const vd=[CAM.cx-fc[0], CAM.cy-fc[1], CAM.cz-fc[2]];
    if(n[0]*vd[0]+n[1]*vd[1]+n[2]*vd[2]>0){
      vis.push({f:f, depth:Math.hypot(vd[0],vd[1],vd[2])});
    }
  });
  vis.sort(function(a,b){return b.depth-a.depth;});
  vis.forEach(function(item){
    const pts=item.f.c.map(function(i){ return world[i]; });
    poly3(pts,cols,item.f.shade);
  });
}
/* shade a hex color by a factor (0..1 darkens, >1 lightens) */
function shadeCol(hex,f){
  const r=parseInt(hex.slice(1,3),16), g=parseInt(hex.slice(3,5),16), b=parseInt(hex.slice(5,7),16);
  const c=function(v){ return Math.max(0,Math.min(255,Math.round(v*f))); };
  return 'rgb('+c(r)+','+c(g)+','+c(b)+')';
}
function colsFor(base){ return [shadeCol(base,1.25), base, shadeCol(base,0.65)]; }

const SKINS=['#e8b98a','#c98d5f','#8d5a3b','#f0c8a0'];
const SHORTS=['#2a2a2e','#3b4a6b','#444444','#1f2937'];
const SHIRTS0=['#d8232a','#c2181e','#e53935','#b71c1c'];
const SHIRTS1=['#1d6fd1','#1565c0','#2196f3','#0d47a1'];

function drawBackground(){
  // sky
  const sky=ctx.createLinearGradient(0,0,0,300);
  sky.addColorStop(0,'#5aa9e6'); sky.addColorStop(1,'#cfeefb');
  ctx.fillStyle=sky; ctx.fillRect(0,0,W,300);
  // sun + clouds (fixed in the sky, far parallax is not needed in 3D)
  ctx.fillStyle='#fff3a0'; ctx.beginPath(); ctx.arc(760,52,24,0,7); ctx.fill();
  ctx.fillStyle='rgba(255,255,255,.9)';
  [[150,55],[420,85],[640,45]].forEach(function(pt){
    ctx.beginPath(); ctx.ellipse(pt[0],pt[1],58,14,0,0,7); ctx.ellipse(pt[0]+34,pt[1]+5,40,10,0,0,7); ctx.fill();
  });
  // treeline beyond the far end zone + along the far sideline (3D park)
  for(let tx=124;tx<=140;tx+=4){
    for(let tz=2;tz<=52;tz+=8){
      drawTree(tx+((tz*7)%3),tz);
    }
  }
  for(let tx=0;tx<=120;tx+=14){
    drawTree(tx,64);
    drawTree(tx+7,-12);
  }
  // benches + playground slide, fixed park spots outside the field
  drawBench(45,62.5);
  drawBench(78,-10.5);
  drawSlide(96,63);
}
function drawTree(x,z){
  const base=snapP(x,0,z);
  if(!base) return;
  const s=base.s;
  // trunk
  ctx.strokeStyle='#6b4a2b'; ctx.lineWidth=Math.max(2,3.2*s);
  ctx.beginPath(); ctx.moveTo(base.x,base.y); ctx.lineTo(base.x,base.y-2.2*s); ctx.stroke();
  // foliage blobs
  ctx.fillStyle='#2f7d33';
  ctx.beginPath(); ctx.arc(base.x,base.y-3.4*s,1.9*s,0,7); ctx.fill();
  ctx.fillStyle='#3c9a40';
  ctx.beginPath(); ctx.arc(base.x-0.8*s,base.y-4.2*s,1.3*s,0,7); ctx.fill();
  ctx.beginPath(); ctx.arc(base.x+0.9*s,base.y-4.0*s,1.2*s,0,7); ctx.fill();
}
function drawBench(x,z){
  const p=snapP(x,0,z);
  if(!p) return;
  const s=p.s;
  ctx.fillStyle='#7a4a21';
  ctx.fillRect(p.x-1.4*s,p.y-0.9*s,2.8*s,0.25*s);
  ctx.fillRect(p.x-1.4*s,p.y-1.5*s,2.8*s,0.25*s);
  ctx.fillStyle='#5b3a18';
  ctx.fillRect(p.x-1.2*s,p.y-0.6*s,0.2*s,0.6*s);
  ctx.fillRect(p.x+1.0*s,p.y-0.6*s,0.2*s,0.6*s);
}
function drawSlide(x,z){
  const p=snapP(x,0,z);
  if(!p) return;
  const s=p.s;
  ctx.fillStyle='#c0392b';
  ctx.beginPath(); ctx.moveTo(p.x-1.2*s,p.y); ctx.lineTo(p.x+1.2*s,p.y); ctx.lineTo(p.x+0.6*s,p.y-1.6*s); ctx.lineTo(p.x-0.6*s,p.y-1.6*s); ctx.closePath(); ctx.fill();
  ctx.fillStyle='#8e44ad'; ctx.fillRect(p.x-1.4*s,p.y-2.2*s,2.8*s,0.7*s);
}
function drawField(){
  const quads=[];
  function quad(x0,z0,x1,z1,col,depth){
    quads.push({x:depth, col:col, pts:[[x0,0,z0],[x1,0,z0],[x1,0,z1],[x0,0,z1]]});
  }
  // mow stripes: alternating light/dark green every 10 yards
  for(let x=FX0;x<FX1;x+=10){
    quad(x,FZ0,x+10,FZ1,((x/10)%2===0)?'#3f8f3a':'#4a9e45',x+5);
  }
  // end zones: HOME red (near), AWAY blue (far)
  quad(FX0,FZ0,GOAL0,FZ1,'#d8232a',5);
  quad(GOAL1,FZ0,FX1,FZ1,'#1d6fd1',115);
  // yard lines every 5 yards, goal lines + midfield wider
  for(let x=GOAL0;x<=GOAL1;x+=5){
    const w=(x===GOAL0||x===GOAL1||x===MID)?0.5:0.3;
    quad(x-w/2,FZ0,x+w/2,FZ1,'#ffffff',x);
  }
  // hash marks (two rows)
  [21,32].forEach(function(hz){
    for(let x=GOAL0;x<=GOAL1;x+=1){
      quad(x-0.15,hz-0.7,x+0.15,hz+0.7,'#ffffff',x);
    }
  });
  // first-down line: gold dashes; goal-to-go line at the goal line
  const fdx=G.lineToGain===50?MID:GOAL1;
  for(let z=FZ0;z<FZ1;z+=2){
    quad(fdx-0.15,z,fdx+0.15,Math.min(z+1.1,FZ1),G.lineToGain===50?'#f5c518':'#ffffff',fdx);
  }
  // line of scrimmage: thin blue line
  quad(G.losX-0.15,FZ0,G.losX+0.15,FZ1,'#38bdf8',G.losX);
  // sidelines + end lines (white border quads)
  quad(FX0-0.15,FZ0,FX0+0.15,FZ1,'#ffffff',FX0);
  quad(FX1-0.15,FZ0,FX1+0.15,FZ1,'#ffffff',FX1);
  quad(FX0,FZ0-0.15,FX1,FZ0+0.15,'#ffffff',60);
  quad(FX0,FZ1-0.15,FX1,FZ1+0.15,'#ffffff',60);
  // painter's order: far end zone first, near last
  quads.sort(function(a,b){return b.x-a.x;});
  quads.forEach(function(q){
    const P=[];
    let ok=true;
    q.pts.forEach(function(pt){
      const sp=snapP(pt[0],pt[1],pt[2]);
      if(!sp) ok=false; else P.push(sp);
    });
    if(!ok) return;
    ctx.fillStyle=q.col;
    ctx.beginPath(); ctx.moveTo(P[0].x,P[0].y);
    for(let i=1;i<P.length;i++) ctx.lineTo(P[i].x,P[i].y);
    ctx.closePath(); ctx.fill();
  });
  // end-zone labels + yard numbers (screen-space text at projected spots)
  ctx.fillStyle='#fff'; ctx.textAlign='center';
  [[(FX0+GOAL0)/2,'HOME'],[(GOAL1+FX1)/2,'AWAY']].forEach(function(ez){
    const p=snapP(ez[0],0,FZ1/2);
    if(!p) return;
    ctx.font='bold '+Math.max(10,Math.round(1.1*p.s))+'px Arial';
    ctx.fillText(ez[1],p.x,p.y);
  });
  for(let y=10;y<=50;y+=10){
    const n=y===50?50:(y>50?100-y:y);
    [[GOAL0+y,12],[GOAL0+y,41]].forEach(function(pt){
      const p=snapP(pt[0],0,pt[1]);
      if(!p) return;
      ctx.font='bold '+Math.max(8,Math.round(1.0*p.s))+'px Arial';
      ctx.fillText(String(n),p.x,p.y);
    });
  }
  // goal posts (yellow H) behind each end zone — decorative only,
  // this game has no special teams
  [[GOAL0-2],[GOAL1+2]].forEach(function(gp){
    const gx=gp[0];
    const base=snapP(gx,0,FZ1/2);
    if(!base) return;
    const s=base.s;
    ctx.strokeStyle='#facc15'; ctx.lineWidth=Math.max(2,0.35*s);
    const topY=base.y-4.2*s;
    ctx.beginPath(); ctx.moveTo(base.x-1.3*s,base.y); ctx.lineTo(base.x-1.3*s,topY); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(base.x+1.3*s,base.y); ctx.lineTo(base.x+1.3*s,topY); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(base.x-1.3*s,base.y-2.6*s); ctx.lineTo(base.x+1.3*s,base.y-2.6*s); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(base.x,base.y); ctx.lineTo(base.x,base.y-2.6*s); ctx.stroke();
  });
  G._fieldMarks={goalLines:[GOAL0,GOAL1],midfield:MID,firstDownLine:fdx,los:G.losX};
}

/* ==========================================================================
   drawPlayer — THE player look. Park pickup players in STREET CLOTHES:
   team-color tee/hoodie, dark shorts, sneakers, a cap. NO football
   uniform — no headgear, no pads, no numbered shirts. Team identity is
   the shirt color only (HOME red, AWAY blue). Change the look here and
   only here.
   The figure is built from real 3D boxes and beams (two-segment legs
   and arms with knee/elbow joints) in world space, projected through
   the perspective camera. ========================================================================== */
function drawPlayer(p){
  const pose=p.pose||'idle';
  const yaw=(p.faceYaw!==undefined)?p.faceYaw:(p.team===0?0:Math.PI);
  const fx=Math.cos(yaw), fz=Math.sin(yaw); // facing vector (x, z)
  const rx=-fz, rz=fx; // right vector (x, z)
  const shirt=(p.team===0?SHIRTS0:SHIRTS1)[p.num%4];
  const shorts=SHORTS[p.num%4];
  const skin=SKINS[p.num%4];
  const shirtCols=colsFor(shirt), shortsCols=colsFor(shorts), skinCols=colsFor(skin);
  const shoeCols=colsFor('#f5f5f5');
  const capCols=colsFor(p.num%2===0?shirt:'#222222');
  const step=p.step||0;
  const sw=Math.sin(step*Math.PI*2);
  const sw2=Math.sin(step*Math.PI*2+Math.PI);

  // ---- pose: hip height, lean, leg/arm targets ----
  let hipH=0.95, lean=0;
  if(pose==='run'){ hipH=0.92; lean=0.18; }
  else if(pose==='stance'||pose==='block'){ hipH=0.82; lean=0.12; }
  else if(pose==='dive'){ hipH=0.55; lean=1.05; }
  else if(pose==='throw'){ hipH=0.95; lean=0.05; }
  else if(pose==='catch'){ hipH=0.98; lean=-0.08; }
  const hipX=p.x, hipZ=p.z;

  // shadow on the turf
  const sh=snapP(p.x,0,p.z);
  if(sh){
    ctx.fillStyle='rgba(0,0,0,.35)';
    ctx.beginPath(); ctx.ellipse(sh.x,sh.y+3,1.5*sh.s,0.4*sh.s,0,0,7); ctx.fill();
  }

  // ---- legs: hip -> knee -> foot, two segments each ----
  function leg(side){ // side: -1 left, +1 right
    const hip=[hipX+rx*0.14*side, hipH, hipZ+rz*0.14*side];
    let foot, kneeF=0.12;
    if(pose==='run'){
      const s=(side<0?sw:sw2);
      const lift=Math.max(0,side<0?Math.cos(step*Math.PI*2):-Math.cos(step*Math.PI*2))*0.14;
      foot=[hip[0]+fx*s*0.35, 0.05+lift, hip[2]+fz*s*0.35];
    } else if(pose==='stance'||pose==='block'){
      foot=[hip[0]+fx*0.08+rx*0.08*side, 0.04, hip[2]+fz*0.08+rz*0.08*side];
    } else if(pose==='dive'){
      foot=[hip[0]-fx*0.55, 0.12, hip[2]-fz*0.55];
      kneeF=-0.05;
    } else if(pose==='catch'){
      foot=[hip[0]+rx*0.1*side, 0.1, hip[2]+rz*0.1*side];
    } else { // idle / throw: planted
      foot=[hip[0]+rx*0.1*side, 0.04, hip[2]+rz*0.1*side];
    }
    const knee=[(hip[0]+foot[0])/2+fx*kneeF, (hip[1]+foot[1])/2, (hip[2]+foot[2])/2+fz*kneeF];
    beam3(hip[0],hip[1],hip[2], knee[0],knee[1],knee[2], 0.2, skinCols);
    beam3(knee[0],knee[1],knee[2], foot[0],foot[1],foot[2], 0.17, skinCols);
    // sneaker at the foot
    box3(foot[0]+fx*0.08, 0.06, foot[2]+fz*0.08, 0.3, 0.12, 0.18, yaw, 0, shoeCols);
    G._limbCalls=(G._limbCalls||0)+2;
    G._shoes=(G._shoes||0)+1;
  }
  leg(-1); leg(1);
  // shorts
  box3(hipX, hipH+0.12, hipZ, 0.55, 0.34, 0.32, yaw, lean*0.5, shortsCols);

  // ---- torso: team-color tee/hoodie, leaning with the run ----
  const chestY=hipH+0.55;
  box3(hipX+fx*lean*0.3, chestY, hipZ+fz*lean*0.3, 0.56, 0.62, 0.34, yaw, lean, shirtCols);
  // hoodie pocket stripe
  const pk=snapP(hipX+fx*(lean*0.3+0.2), chestY-0.12, hipZ+fz*(lean*0.3+0.2));
  if(pk){
    ctx.fillStyle='rgba(0,0,0,.25)';
    ctx.fillRect(pk.x-0.18*pk.s, pk.y-0.06*pk.s, 0.36*pk.s, 0.12*pk.s);
  }

  // ---- arms: shoulder -> elbow -> hand, two segments each ----
  const shY=chestY+0.28;
  function arm(side){
    const sh=[hipX+rx*0.3*side+fx*lean*0.3, shY, hipZ+rz*0.3*side+fz*lean*0.3];
    let hand, elbOut=0.12;
    if(pose==='throw'){
      if(side>0){ // throwing arm: cocked up and back
        hand=[sh[0]-fx*0.3, shY+0.55, sh[2]-fz*0.3];
      } else { // other arm points at the target
        hand=[sh[0]+fx*0.55, shY+0.05, sh[2]+fz*0.55];
      }
    } else if(pose==='catch'){
      hand=[sh[0]+fx*0.2, shY+0.55, sh[2]+fz*0.2];
    } else if(pose==='dive'){
      hand=[sh[0]+fx*0.75, shY-0.15, sh[2]+fz*0.75];
    } else if(pose==='block'){
      hand=[sh[0]+fx*0.5, shY-0.05, sh[2]+fz*0.5];
    } else if(pose==='run'){
      const s=(side<0?sw2:sw); // arms pump opposite the legs
      if(p.hasBall&&side>0){ // ball carrier tucks the ball
        hand=[sh[0]+fx*0.25, shY-0.4, sh[2]+fz*0.25];
      } else {
        hand=[sh[0]+fx*s*0.35, shY-0.45, sh[2]+fz*s*0.35];
      }
    } else if(pose==='stance'){
      hand=[sh[0]+fx*0.1, shY-0.55, sh[2]+fz*0.1]; // hands near the knees
    } else { // idle
      hand=[sh[0]+rx*0.06*side, shY-0.5, sh[2]+rz*0.06*side];
    }
    const elb=[(sh[0]+hand[0])/2+rx*elbOut*side, (sh[1]+hand[1])/2, (sh[2]+hand[2])/2+rz*elbOut*side];
    beam3(sh[0],sh[1],sh[2], elb[0],elb[1],elb[2], 0.16, shirtCols);
    beam3(elb[0],elb[1],elb[2], hand[0],hand[1],hand[2], 0.14, skinCols);
    // hand
    box3(hand[0], hand[1], hand[2], 0.14, 0.14, 0.14, yaw, 0, skinCols);
    G._limbCalls=(G._limbCalls||0)+2;
    G._hands=(G._hands||0)+1;
    if(side>0){ p._handR=hand; } else { p._handL=hand; }
  }
  arm(-1); arm(1);

  // ---- head + cap ----
  const headY=chestY+0.48;
  box3(hipX+fx*lean*0.3, headY, hipZ+fz*lean*0.3, 0.27, 0.3, 0.27, yaw, lean, skinCols);
  // cap: flat crown + brim pointing where he faces
  box3(hipX+fx*lean*0.3, headY+0.17, hipZ+fz*lean*0.3, 0.31, 0.09, 0.31, yaw, lean, capCols);
  box3(hipX+fx*(lean*0.3+0.22), headY+0.13, hipZ+fz*(lean*0.3+0.22), 0.16, 0.04, 0.3, yaw, lean, capCols);

  // pose signature (test instrumentation): limbs + pose + hands
  const hr=p._handR||[0,0,0], hl=p._handL||[0,0,0];
  p._poseSig=pose+'|hL'+Math.round(hl[0]-p.x)+'|hR'+Math.round(hr[0]-p.x);
  p._limbs={legs:2,arms:2,shoes:2,hands:2};
  // YOU marker
  if(G.players[G.user]===p){
    const mp=snapP(p.x,2.55,p.z);
    if(mp){
      ctx.fillStyle='#f5c518';
      ctx.beginPath(); ctx.moveTo(mp.x,mp.y); ctx.lineTo(mp.x-0.35*mp.s,mp.y-0.5*mp.s); ctx.lineTo(mp.x+0.35*mp.s,mp.y-0.5*mp.s); ctx.closePath(); ctx.fill();
      ctx.fillStyle='#000'; ctx.font='bold 10px Arial'; ctx.textAlign='center';
      ctx.fillText('YOU',mp.x,mp.y-0.62*mp.s);
    }
  }
  const topP=snapP(p.x,2.0,p.z);
  p._drawTop=topP?topP.y:0; p._drawX=topP?topP.x:0;
}
function drawBall(){
  const b=G.ball; if(!b) return;
  if(b.state==='held'){
    const h=holder(); if(!h) return;
    const dir=(h.face||1);
    const pr=snapP(h.x+dir*0.3,1.1,h.z);
    if(!pr) return;
    drawBallAt(pr.x,pr.y,0.32*pr.s);
    G._ballDraw={x:pr.x,y:pr.y,r:0.32*pr.s};
  } else if(b.state==='pass'){
    const gp=snapP(b.x,0,b.z);
    if(gp){
      ctx.fillStyle='rgba(0,0,0,.3)';
      ctx.beginPath(); ctx.ellipse(gp.x,gp.y+3,0.5*gp.s,0.14*gp.s,0,0,7); ctx.fill();
    }
    const bp=snapP(b.x,b.h,b.z);
    if(!bp) return;
    drawBallAt(bp.x,bp.y,0.32*bp.s);
    // spin: the ball tumbles end over end on a throw
    ctx.strokeStyle='#fff'; ctx.lineWidth=1.5;
    const t=b.t||0;
    ctx.beginPath(); ctx.moveTo(bp.x-0.4*bp.s*Math.cos(t*14),bp.y-0.14*bp.s*Math.sin(t*14)); ctx.lineTo(bp.x+0.4*bp.s*Math.cos(t*14),bp.y+0.14*bp.s*Math.sin(t*14)); ctx.stroke();
    G._ballDraw={x:bp.x,y:bp.y,r:0.32*bp.s};
  } else if(b.state==='dead'){
    const pr=snapP(b.x,0.1,b.z);
    if(!pr) return;
    drawBallAt(pr.x,pr.y,0.32*pr.s);
    G._ballDraw={x:pr.x,y:pr.y,r:0.32*pr.s};
  }
}
function drawBallAt(x,y,r){
  // brown leather football with white laces, pointed ends
  ctx.fillStyle='#7a4a21';
  ctx.beginPath(); ctx.ellipse(x,y,r*1.4,r,0,0,7); ctx.fill();
  ctx.strokeStyle='#5b3a18'; ctx.lineWidth=1.5;
  ctx.beginPath(); ctx.ellipse(x,y,r*1.4,r,0,0,7); ctx.stroke();
  ctx.strokeStyle='#fff'; ctx.lineWidth=1.5;
  ctx.beginPath(); ctx.moveTo(x-r*0.7,y); ctx.lineTo(x+r*0.7,y); ctx.stroke();
  for(let i=-1;i<=1;i++){
    ctx.beginPath(); ctx.moveTo(x+i*4,y-4); ctx.lineTo(x+i*4,y+4); ctx.stroke();
  }
}
function drawTarget(){
  // gold marker over the receiver PASS is about to throw to
  const t=G.target;
  if(!t||G.phase!=='live') { G._targetDraw=null; return; }
  const pr=snapP(t.x,2.7,t.z);
  if(!pr){ G._targetDraw=null; return; }
  G._targetDraw={x:pr.x,y:pr.y};
  ctx.fillStyle='#f5c518';
  ctx.beginPath(); ctx.moveTo(pr.x,pr.y+0.4*pr.s); ctx.lineTo(pr.x-0.4*pr.s,pr.y-0.3*pr.s); ctx.lineTo(pr.x+0.4*pr.s,pr.y-0.3*pr.s); ctx.closePath(); ctx.fill();
  ctx.fillStyle='#000'; ctx.font='bold 9px Arial'; ctx.textAlign='center';
  ctx.fillText('TARGET',pr.x,pr.y-0.45*pr.s);
}
function draw(){
  G._limbCalls=0; G._shoes=0; G._hands=0; G._polyCalls=0;
  updateCamBasis();
  ctx.save();
  if(G.shake>0) ctx.translate((Math.random()-0.5)*G.shake*30,(Math.random()-0.5)*G.shake*30);
  drawBackground();
  drawField();
  // painter's order: farthest players first (downfield = far from the
  // camera behind the offense)
  const sorted=G.players.slice().sort(function(a,b){return b.x-a.x;});
  sorted.forEach(drawPlayer);
  drawBall();
  drawTarget();
  ctx.restore();
}

/* ---------- main loop ---------- */
let last=0;
function loop(t){
  requestAnimationFrame(loop);
  const dt=Math.min(0.05,(t-last)/1000||0.016); last=t;
  if(G.mode==='play') update(dt);
  draw();
}
newGame();
requestAnimationFrame(loop);

/* test hook (for verification only) */
window.__game={G:G,stick:stick,setStick:setStick,startGame:startGame,openGame:openGame,closeGame:closeGame,snap:snap,doPass:doPass,doSwitch:doSwitch,doTackle:doTackle,setupDrive:setupDrive,scoreTD:scoreTD,endGame:endGame,finishPlay:finishPlay,throwPass:throwPass,computeTarget:computeTarget,eligibleReceivers:eligibleReceivers,update:update,draw:draw,drawField:drawField,proj:proj,updateLabels:updateLabels,updateUserControl:updateUserControl,updateDownLine:updateDownLine,DIFFS:DIFFS,TARGET_TD:TARGET_TD,FIELD:{FX0:FX0,FX1:FX1,GOAL0:GOAL0,GOAL1:GOAL1,MID:MID,FZ0:FZ0,FZ1:FZ1},selectDiff:selectDiff,holder:holder,pickPlay:pickPlay,PLAYS:PLAYS,PLAY_CLOCK:PLAY_CLOCK,FOCAL:FOCAL,pvpPlayer:pvpPlayer,pvpIsOn:pvpIsOn,pvpMe:pvpMe,pvpOppCtrl:pvpOppCtrl,pvpReceiveEv:pvpReceiveEv,pvpApplyState:pvpApplyState,pvpPostState:pvpPostState,pvpStartPoll:pvpStartPoll,pvpStopPoll:pvpStopPoll,pvpPollOnce:pvpPollOnce,showPlaycall:showPlaycall};
})();

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
