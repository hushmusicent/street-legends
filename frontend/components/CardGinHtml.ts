export const CARD_GIN_HTML = `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body { margin: 0; background: radial-gradient(ellipse at 50% 0%, #3a2410 0%, #1a1208 45%, #0d0d0d 100%); color: #ffffff; font-family: sans-serif; }
#wrap { max-width: 460px; margin: 0 auto; padding: 10px; text-align: center; box-sizing: border-box; }
h1 { font-size: 22px; margin: 6px 0 2px; color: #f5c542; text-shadow: 0 2px 4px rgba(0,0,0,0.8), 0 0 18px rgba(245,197,66,0.35); }
.sub { color: #dddddd; font-size: 12px; margin-bottom: 10px; text-shadow: 0 1px 2px rgba(0,0,0,0.8); }
button { background: linear-gradient(180deg, #5a5a5a, #3a3a3a); color: #ffffff; font-weight: 800; border: 0; border-radius: 8px; padding: 12px 14px; font-size: 13px; margin: 4px; box-shadow: 0 4px 8px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.25); }
button:active { transform: translateY(2px); box-shadow: 0 1px 3px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.2); }
button.big { display: block; width: 100%; padding: 16px; font-size: 16px; }
button.green { background: linear-gradient(180deg, #43a047, #1b5e20); }
button.blue { background: linear-gradient(180deg, #42a5f5, #1565c0); }
button.gold { background: linear-gradient(180deg, #f9d54d, #b7950b); color: #222222; }
button.red { background: linear-gradient(180deg, #ef5350, #b71c1c); }
button:disabled { opacity: 0.4; }
#msg { color: #cccccc; font-size: 13px; min-height: 18px; margin: 8px 0; }
#spScore, #ginScore { font-weight: 800; font-size: 15px; margin-bottom: 6px; background: linear-gradient(180deg, rgba(0,0,0,0.55), rgba(0,0,0,0.35)); border-radius: 8px; padding: 6px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.6), 0 1px 0 rgba(255,255,255,0.08); }
.table { background: linear-gradient(145deg, #b07a3e, #8a5a2b 40%, #6b4423); border-radius: 16px; padding: 12px; margin: 8px 0; box-shadow: 0 14px 28px rgba(0,0,0,0.65), 0 4px 8px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.35), inset 0 -2px 4px rgba(0,0,0,0.4); }
.felt { background: radial-gradient(ellipse at center, #2e7d32 0%, #1e5c2e 55%, #123d1e 100%); border-radius: 10px; padding: 10px; box-shadow: inset 0 4px 14px rgba(0,0,0,0.65), inset 0 -1px 0 rgba(255,255,255,0.08); }
.trick { display: flex; gap: 8px; justify-content: center; min-height: 74px; }
.slot { width: 56px; }
.slot .who { font-size: 10px; color: #dddddd; text-shadow: 0 1px 2px rgba(0,0,0,0.9); }
.card { position: relative; display: inline-block; background: linear-gradient(145deg, #ffffff 0%, #f2f2f2 60%, #d9d9d9 100%); color: #111111; border-radius: 6px; width: 48px; height: 66px; padding: 0; font-weight: 800; font-size: 16px; box-sizing: border-box; overflow: hidden; border-bottom: 2px solid #bdbdbd; box-shadow: 0 5px 10px rgba(0,0,0,0.55), inset 0 1px 0 #ffffff, inset 0 0 0 1px rgba(0,0,0,0.10); }
.card.red { background: linear-gradient(145deg, #ffffff 0%, #f2f2f2 60%, #d9d9d9 100%); color: #c62828; }
.card.small { width: 40px; height: 56px; font-size: 14px; }
.card .corner { position: absolute; font-size: 9px; line-height: 1.0; z-index: 2; text-shadow: 0 0 2px #ffffff, 0 0 3px #ffffff; }
.card .corner.tl { top: 1px; left: 2px; text-align: center; }
.card .corner.br { bottom: 1px; right: 2px; text-align: center; transform: rotate(180deg); }
.card .pips { position: absolute; inset: 0; }
.card .pip { position: absolute; font-size: 14px; line-height: 1; transform: translate(-50%, -50%); }
.card .pip.flip { transform: translate(-50%, -50%) rotate(180deg); }
.card .pip.tl { left: 34%; top: 20%; }
.card .pip.tr { right: 34%; top: 20%; left: auto; transform: translate(50%, -50%); }
.card .pip.ml { left: 34%; top: 50%; }
.card .pip.mr { right: 34%; top: 50%; left: auto; transform: translate(50%, -50%); }
.card .pip.bl { left: 34%; top: 80%; }
.card .pip.br { right: 34%; top: 80%; left: auto; }
.card .pip.tc { left: 50%; top: 20%; }
.card .pip.bc { left: 50%; top: 80%; }
.card .pip.c { left: 50%; top: 50%; }
.card .pip.ct { left: 50%; top: 34%; }
.card .pip.cb { left: 50%; top: 66%; }
.card .pip.mlt { left: 34%; top: 34%; }
.card .pip.mrt { right: 34%; top: 34%; left: auto; transform: translate(50%, -50%); }
.card .pip.mlb { left: 34%; top: 66%; }
.card .pip.mrb { right: 34%; top: 66%; left: auto; }
.card .pip.tr.flip, .card .pip.mr.flip, .card .pip.mrt.flip, .card .pip.br.flip, .card .pip.mrb.flip { transform: translate(50%, -50%) rotate(180deg); }
.card .ace { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); font-size: 30px; }
.card .face { position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%); text-align: center; }
.card .face .fl { display: block; font-family: Georgia, serif; font-size: 24px; }
.card .face .fsuit { display: block; font-size: 16px; }
.card.small .corner { font-size: 7px; }
.card.small .pip { font-size: 11px; }
.card.small .ace { font-size: 24px; }
.card.small .face .fl { font-size: 18px; }
.card.small .face .fsuit { font-size: 12px; }
.pilebtn { background: transparent; border: 0; padding: 0; margin: 4px auto; display: block; box-shadow: none; }
.pilebtn:active { transform: none; box-shadow: none; }
.pilebtn:disabled { opacity: 1; }
.card.back { background: repeating-linear-gradient(45deg, rgba(255,255,255,0.15) 0 6px, transparent 6px 12px), linear-gradient(145deg, #42a5f5, #1565c0); color: #ffffff; font-size: 20px; line-height: 56px; }
.hand { display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; margin-top: 8px; }
.hand button.card { padding: 0; margin: 0; width: 52px; height: 72px; }
.hand button.card:disabled { opacity: 1; }
.card:disabled { opacity: 1; }
.hand .card .pip { font-size: 14px; }
.hand .card .corner { font-size: 10px; }
.hand .card .ace { font-size: 34px; }
.hand .card .face .fl { font-size: 28px; }
.hand .card .face .fsuit { font-size: 18px; }
.piles { display: flex; gap: 16px; justify-content: center; margin: 8px 0; }
.pile { font-size: 11px; color: #dddddd; text-shadow: 0 1px 2px rgba(0,0,0,0.9); }
.pile button { display: block; margin: 4px auto; }
#log { color: #999999; font-size: 12px; min-height: 16px; margin-top: 8px; }
.bidrow { display: flex; flex-wrap: wrap; gap: 5px; justify-content: center; }
.bidrow button { padding: 10px 12px; }
.hubcards { position: relative; height: 84px; margin: 6px auto; width: 130px; }
.hubcards .card { position: absolute; top: 0; box-shadow: 0 8px 16px rgba(0,0,0,0.6); }
.hubcards .card:first-child { left: 8px; transform: rotate(-12deg); }
.hubcards .card:last-child { right: 8px; transform: rotate(12deg); }

/* APP FULL-SCREEN SCALE v2 (app WebView only, not the chat widget): TALLER
   not longer - device-width viewport (no scale-down), the table stretches
   down to fill the screen height, hand wraps to rows at true card size. */
html, body { height: 100%; }
#wrap { max-width: none; min-height: 100vh; display: flex; flex-direction: column; padding: 16px; }
h1 { font-size: 28px; }
.table { padding: 18px; margin: 14px 0; flex: 1; display: flex; flex-direction: column; }
.felt { padding: 18px; min-height: 340px; flex: 1; display: flex; flex-direction: column; justify-content: center; }
.hand button.card { width: 68px; height: 94px; }
.hand .card .pip { font-size: 18px; }
.hand .card .corner { font-size: 12px; }
.hand .card .ace { font-size: 44px; }
.hand .card .face .fl { font-size: 36px; }
.hand .card .face .fsuit { font-size: 22px; }
.card.small { width: 50px; height: 68px; }
.card.small .pip { font-size: 13px; }
.card.small .corner { font-size: 8px; }
.card.small .ace { font-size: 26px; }
button { padding: 14px 18px; font-size: 15px; }
</style>
</head>
<body>
<div id="wrap">
<div id="ginView" >
<h1>CARD TABLE - GIN RUMMY</h1>
<div id="ginScore"></div>
<div class="table">
<div class="felt">
<div class="piles">
<div class="pile">STOCK (<span id="ginStockN"></span>)<button class="card back" id="ginStockBtn">🂠</button></div>
<div class="pile">DISCARD<button class="pilebtn" id="ginDiscBtn"></button></div>
</div>
<div id="ginMsg" style="color:#dddddd;font-size:13px;min-height:18px;text-shadow:0 1px 2px rgba(0,0,0,0.9);"></div>
<div id="ginMelds" class="sub"></div>
</div>
</div>
<div class="hand" id="ginHand"></div>
<div style="margin-top:10px;">
<button id="ginKnock" class="gold" disabled>KNOCK</button>
<button id="ginGinBtn" class="green" disabled>GIN</button>
<button id="ginSort">SORT</button>
<button id="ginNext"  class="green">NEXT HAND</button>
<button id="leaveBtn" class="red">LEAVE TABLE</button>
</div>
<div id="ginLog"></div>
</div>

<div id="leaveConfirm" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:50;text-align:center;">
<div style="background:linear-gradient(180deg,#2a2a2a,#1a1a1a);border:2px solid #f5c542;border-radius:12px;padding:18px;max-width:300px;margin:30% auto 0;box-shadow:0 10px 24px rgba(0,0,0,0.7);">
<div id="leaveMsg" style="font-weight:800;font-size:15px;margin-bottom:12px;"></div>
<button class="red" id="leaveYes">LEAVE</button>
<button class="green" id="leaveNo">STAY</button>
</div>
</div>
</div>
<script>
(function () {
var SUITS = ['♠', '♥', '♦', '♣'];
var RLAB = { 11: 'J', 12: 'Q', 13: 'K', 14: 'A' };
function rlab(r) { return RLAB[r] || String(r); }
function cname(c) { return rlab(c.r) + SUITS[c.s]; }
function cval(c) { return c.r >= 11 ? 10 : c.r; }
function newDeck() {
  var d = [];
  for (var s = 0; s < 4; s++) for (var r = 2; r <= 14; r++) d.push({ r: r, s: s });
  for (var i = d.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)); var t = d[i]; d[i] = d[j]; d[j] = t; }
  return d;
}
function sortCards(a) { return a.slice().sort(function (x, y) { return x.s - y.s || x.r - y.r; }); }
var PIPMAP = {
  2: ['tc', 'bc'],
  3: ['tc', 'c', 'bc'],
  4: ['tl', 'tr', 'bl', 'br'],
  5: ['tl', 'tr', 'c', 'bl', 'br'],
  6: ['tl', 'tr', 'ml', 'mr', 'bl', 'br'],
  7: ['tl', 'tr', 'ml', 'mr', 'ct', 'bl', 'br'],
  8: ['tl', 'tr', 'ml', 'mr', 'ct', 'cb', 'bl', 'br'],
  9: ['tl', 'tr', 'mlt', 'mrt', 'c', 'mlb', 'mrb', 'bl', 'br'],
  10: ['tl', 'tr', 'mlt', 'mrt', 'ct', 'cb', 'mlb', 'mrb', 'bl', 'br']
};
var PIPFLIP = { bl: 1, br: 1, bc: 1, cb: 1, mlb: 1, mrb: 1 };
function cardEl(c, cls) {
  var b = document.createElement('button');
  b.className = 'card ' + (cls || '') + ((c.s === 1 || c.s === 2) ? ' red' : '');
  var tl = document.createElement('span');
  tl.className = 'corner tl';
  tl.innerHTML = rlab(c.r) + '<br>' + SUITS[c.s];
  var br = document.createElement('span');
  br.className = 'corner br';
  br.innerHTML = rlab(c.r) + '<br>' + SUITS[c.s];
  var center = document.createElement('span');
  center.className = 'pips';
  if (c.r === 14) {
    center.innerHTML = '<span class="ace">' + SUITS[c.s] + '</span>';
  } else if (c.r >= 11) {
    center.innerHTML = '<span class="face"><span class="fl">' + RLAB[c.r] + '</span><span class="fsuit">' + SUITS[c.s] + '</span></span>';
  } else {
    center.innerHTML = PIPMAP[c.r].map(function (pos) {
      return '<span class="pip ' + pos + (PIPFLIP[pos] ? ' flip' : '') + '">' + SUITS[c.s] + '</span>';
    }).join('');
  }
  b.appendChild(tl);
  b.appendChild(center);
  b.appendChild(br);
  return b;
}
function sleep(ms) { return new Promise(function (res) { setTimeout(res, ms); }); }
var pendingLeave = null;
function askLeave(msg, fn) {
  pendingLeave = fn;
  document.getElementById('leaveMsg').textContent = msg;
  document.getElementById('leaveConfirm').style.display = 'block';
}
document.getElementById('leaveYes').addEventListener('click', function () {
  document.getElementById('leaveConfirm').style.display = 'none';
  var fn = pendingLeave;
  pendingLeave = null;
  if (fn) fn();
});
document.getElementById('leaveNo').addEventListener('click', function () {
  pendingLeave = null;
  document.getElementById('leaveConfirm').style.display = 'none';
});
/* ================= GIN RUMMY ================= */
var G = null;
function ginNewGame() {
  document.querySelectorAll('.newgame').forEach(function (el) { el.remove(); });
  G = { us: 0, them: 0, hand: 1, first: 0 };
  ginNewHand();
}
function findMelds(cards) {
  var melds = [];
  var byRank = {}, bySuit = {};
  cards.forEach(function (c, i) {
    (byRank[c.r] = byRank[c.r] || []).push(i);
    (bySuit[c.s] = bySuit[c.s] || []).push(i);
  });
  Object.keys(byRank).forEach(function (r) {
    var idx = byRank[r];
    if (idx.length >= 3) {
      melds.push(idx.slice(0, 3));
      if (idx.length === 4) melds.push(idx.slice(0, 4));
    }
  });
  Object.keys(bySuit).forEach(function (s) {
    var idx = bySuit[s].slice().sort(function (a, b) { return cards[a].r - cards[b].r; });
    for (var a = 0; a < idx.length; a++) {
      var run = [idx[a]];
      for (var b = a + 1; b < idx.length; b++) {
        if (cards[idx[b]].r === cards[run[run.length - 1]].r + 1) run.push(idx[b]);
        else break;
      }
      if (run.length >= 3) {
        for (var len = 3; len <= run.length; len++) melds.push(run.slice(0, len));
      }
    }
  });
  return melds;
}
function bestDeadwood(cards) {
  var melds = findMelds(cards);
  var best = { dead: cards.reduce(function (s, c) { return s + cval(c); }, 0), used: [] };
  function rec(remaining, used, dead) {
    if (dead < best.dead) best = { dead: dead, used: used.slice() };
    if (dead === 0) return;
    var m = findMelds(remaining);
    for (var i = 0; i < m.length; i++) {
      var mi = m[i];
      var take = mi.map(function (ix) { return remaining[ix]; });
      var rest = remaining.filter(function (c, ix) { return mi.indexOf(ix) === -1; });
      var d = take.reduce(function (s, c) { return s + cval(c); }, 0);
      rec(rest, used.concat([take]), dead - d);
    }
  }
  rec(cards, [], best.dead);
  return best;
}
function ginNewHand() {
  var d = newDeck();
  G.you = sortCards(d.slice(0, 10));
  G.cpu = d.slice(10, 20);
  G.stock = d.slice(21);
  G.discard = [d[20]];
  G.phase = G.first === 0 ? 'draw' : 'cpu';
  G.msg = G.first === 0 ? 'Your turn. Draw from the stock or the discard pile.' : 'CPU is playing...';
  G.over = false;
  document.getElementById('ginNext').style.display = 'none';
  ginRender();
  if (G.phase === 'cpu') setTimeout(ginCpuTurn, 800);
}
function ginDeadwoodAfterDiscard(hand) {
  var best = { dead: 99, card: null, melds: [] };
  hand.forEach(function (c) {
    var rest = hand.filter(function (x) { return x !== c; });
    var b = bestDeadwood(rest);
    if (b.dead < best.dead) best = { dead: b.dead, card: c, melds: b.used };
  });
  return best;
}
function ginRender() {
  if (!G) return;
  document.getElementById('ginScore').innerHTML = 'YOU: ' + G.us + ' &nbsp;|&nbsp; CPU: ' + G.them + ' &nbsp;|&nbsp; First to 100';
  document.getElementById('ginStockN').textContent = G.stock.length;
  var db = document.getElementById('ginDiscBtn');
  var top = G.discard[G.discard.length - 1];
  db.innerHTML = '';
  var ce = cardEl(top, '');
  db.appendChild(ce);
  document.getElementById('ginMsg').textContent = G.msg;
  var bd = bestDeadwood(G.you);
  document.getElementById('ginMelds').textContent = 'Your deadwood: ' + bd.dead + (bd.used.length ? ' | Melds: ' + bd.used.map(function (m) { return m.map(cname).join('-'); }).join('  ') : ' | No melds yet');
  var handEl = document.getElementById('ginHand');
  handEl.innerHTML = '';
  G.you.forEach(function (c) {
    var b = cardEl(c, '');
    if (G.phase === 'discard' || G.phase === 'knock') {
      b.addEventListener('click', function () { ginDiscard(c); });
    } else {
      b.disabled = true;
    }
    handEl.appendChild(b);
  });
  document.getElementById('ginStockBtn').disabled = !(G.phase === 'draw');
  db.disabled = !(G.phase === 'draw');
  var after = ginDeadwoodAfterDiscard(G.you);
  document.getElementById('ginKnock').disabled = !(G.phase === 'discard' && after.dead <= 10);
  document.getElementById('ginGinBtn').disabled = !(G.phase === 'discard' && after.dead === 0);
}
document.getElementById('ginStockBtn').addEventListener('click', function () {
  if (G.phase !== 'draw') return;
  G.you.push(G.stock.pop());
  G.you = sortCards(G.you);
  G.phase = 'discard';
  G.msg = 'You drew from the stock. Discard a card, or knock / gin if you can.';
  ginRender();
});
document.getElementById('ginDiscBtn').addEventListener('click', function () {
  if (G.phase !== 'draw') return;
  G.you.push(G.discard.pop());
  G.you = sortCards(G.you);
  G.phase = 'discard';
  G.msg = 'You drew from the discard pile. Discard a card, or knock / gin if you can.';
  ginRender();
});
function ginDiscard(c) {
  if (G.phase !== 'discard') return;
  G.you = G.you.filter(function (x) { return x !== c; });
  G.discard.push(c);
  G.phase = 'cpu';
  G.msg = 'CPU is playing...';
  ginRender();
  setTimeout(ginCpuTurn, 800);
}
document.getElementById('ginKnock').addEventListener('click', function () { ginEndHand(false); });
document.getElementById('ginGinBtn').addEventListener('click', function () { ginEndHand(true); });
document.getElementById('ginSort').addEventListener('click', function () { G.you = sortCards(G.you); ginRender(); });
document.getElementById('ginNext').addEventListener('click', function () {
  G.hand++;
  G.first = 1 - G.first;
  ginNewHand();
});
function ginCpuTurn() {
  if (!G || G.over) return;
  var tookDisc = false;
  var top = G.discard[G.discard.length - 1];
  var withDisc = G.cpu.concat([top]);
  if (bestDeadwood(withDisc).dead < bestDeadwood(G.cpu).dead) {
    G.cpu.push(G.discard.pop());
    tookDisc = true;
  } else {
    if (G.stock.length === 0) { G.stock = G.discard.slice(0, -1); G.discard = [G.discard[G.discard.length - 1]]; }
    G.cpu.push(G.stock.pop());
  }
  var after = ginDeadwoodAfterDiscard(G.cpu);
  if (after.dead <= 10) {
    G.msg = 'CPU knocks' + (after.dead === 0 ? ' with Gin!' : '!') + (tookDisc ? ' (drew from discard)' : ' (drew from stock)');
    ginRender();
    setTimeout(function () { ginEndHandCpu(after); }, 900);
    return;
  }
  G.cpu = G.cpu.filter(function (x) { return x !== after.card; });
  G.discard.push(after.card);
  G.phase = 'draw';
  G.msg = 'CPU drew ' + (tookDisc ? 'from the discard pile' : 'from the stock') + ' and discarded ' + cname(after.card) + '. Your turn - draw.';
  ginRender();
}
function ginLayoffs(knockerMelds, oppHand) {
  var remaining = [];
  var oppCards = oppHand.slice();
  oppCards.forEach(function (c) {
    var placed = false;
    for (var mi = 0; mi < knockerMelds.length && !placed; mi++) {
      var m = knockerMelds[mi];
      if (m.length && m[0].r === c.r) { m.push(c); placed = true; }
      else if (m.length && m[0].s === c.s) {
        var ranks = m.map(function (x) { return x.r; });
        if (ranks.indexOf(c.r - 1) !== -1 || ranks.indexOf(c.r + 1) !== -1) {
          var min = Math.min.apply(null, ranks), max = Math.max.apply(null, ranks);
          if (c.r === min - 1 || c.r === max + 1) { m.push(c); placed = true; }
        }
      }
    }
    if (!placed) remaining.push(c);
  });
  return remaining.reduce(function (s, c) { return s + cval(c); }, 0);
}
function ginEndHand(isGin) {
  var after = ginDeadwoodAfterDiscard(G.you);
  G.you = G.you.filter(function (x) { return x !== after.card; });
  G.discard.push(after.card);
  var myMelds = after.melds;
  var myDead = after.dead;
  var cpuDead = ginLayoffs(myMelds.map(function (m) { return m.slice(); }), G.cpu);
  var pts = 0, txt = '';
  if (isGin || myDead === 0) {
    pts = cpuDead + 25;
    G.us += pts;
    txt = 'GIN! You score ' + cpuDead + ' + 25 bonus = ' + pts + '.';
  } else if (myDead < cpuDead) {
    pts = cpuDead - myDead;
    G.us += pts;
    txt = 'You knock and win ' + pts + ' (CPU deadwood ' + cpuDead + ' - yours ' + myDead + ').';
  } else {
    pts = (myDead - cpuDead) + 10;
    G.them += pts;
    txt = 'Undercut! CPU wins ' + pts + ' (your deadwood ' + myDead + ' - CPU ' + cpuDead + ' + 10).';
  }
  G.over = true;
  G.msg = txt;
  document.getElementById('ginLog').textContent = txt;
  ginFinish();
}
function ginEndHandCpu(after) {
  G.cpu = G.cpu.filter(function (x) { return x !== after.card; });
  G.discard.push(after.card);
  var cpuMelds = after.melds;
  var cpuDead = after.dead;
  var myDead = ginLayoffs(cpuMelds.map(function (m) { return m.slice(); }), G.you);
  var pts = 0, txt = '';
  if (cpuDead === 0) {
    pts = myDead + 25;
    G.them += pts;
    txt = 'CPU gins! CPU scores ' + myDead + ' + 25 = ' + pts + '.';
  } else if (cpuDead < myDead) {
    pts = myDead - cpuDead;
    G.them += pts;
    txt = 'CPU knocks and wins ' + pts + ' (your deadwood ' + myDead + ' - CPU ' + cpuDead + ').';
  } else {
    pts = (cpuDead - myDead) + 10;
    G.us += pts;
    txt = 'Undercut! You win ' + pts + ' (CPU deadwood ' + cpuDead + ' - yours ' + myDead + ' + 10).';
  }
  G.over = true;
  G.msg = txt;
  document.getElementById('ginLog').textContent = txt;
  ginFinish();
}
function ginFinish() {
  ginRender();
  document.getElementById('ginKnock').disabled = true;
  document.getElementById('ginGinBtn').disabled = true;
  document.getElementById('ginStockBtn').disabled = true;
  document.getElementById('ginDiscBtn').disabled = true;
  if (G.us >= 100 || G.them >= 100) {
    G.msg = (G.us > G.them ? 'YOU WIN THE GAME!' : 'CPU WINS THE GAME.') + ' Final: You ' + G.us + ' - CPU ' + G.them + '.';
    var again = document.createElement('button');
    again.className = 'green newgame'; again.textContent = 'NEW GAME';
    again.addEventListener('click', function () { ginNewGame(); });
    document.getElementById('ginView').appendChild(again);
  } else {
    document.getElementById('ginNext').style.display = 'inline-block';
  }
  ginRender();
}

document.getElementById('leaveBtn').addEventListener('click', function () {
  var over = (typeof SP !== 'undefined' && SP) ? SP.over : (typeof G !== 'undefined' && G) ? G.over : true;
  if (!over) askLeave('Leave this game? Your progress will be lost.', function () {
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
  });
  else if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
});

ginNewGame();
})();
</script>
</body>
</html>
`;
