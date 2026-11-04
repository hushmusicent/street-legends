export const CARD_PVP_HTML = `<!DOCTYPE html>
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
<div id="ginPvpView" style="display:none;">
<h1 id="ginPvpTitle">CARD TABLE - GIN RUMMY</h1>
<div id="ginPvpScore"></div>
<div class="table">
<div class="felt">
<div class="piles">
<div class="pile">STOCK (<span id="ginPvpStockN"></span>)<button class="card back" id="ginPvpStockBtn">🂠</button></div>
<div class="pile">DISCARD<button class="pilebtn" id="ginPvpDiscBtn"></button></div>
</div>
<div id="ginPvpMsg" style="color:#dddddd;font-size:13px;min-height:18px;text-shadow:0 1px 2px rgba(0,0,0,0.9);"></div>
<div id="ginPvpMelds" class="sub"></div>
<div id="ginPvpFoe" style="margin-top:8px;"></div>
</div>
</div>
<div class="hand" id="ginPvpHand"></div>
<div style="margin-top:10px;">
<button id="ginPvpKnock" class="gold" disabled>KNOCK</button>
<button id="ginPvpGinBtn" class="green" disabled>GIN</button>
<button id="ginPvpSort">SORT</button>
<button id="ginPvpNext" style="display:none;" class="green">NEXT HAND</button>
<button id="ginPvpAgain" style="display:none;" class="green">NEW GAME</button>
<button id="ginLeaveBtn" class="red">LEAVE TABLE</button>
</div>
<div id="ginPvpLog"></div>
</div>
<div id="spPvpView" style="display:none;">
<h1 id="spPvpTitle">CARD TABLE - SPADES</h1>
<div id="spPvpScore"></div>
<div id="spPvpBids" class="sub"></div>
<div id="spPvpCounts" class="sub"></div>
<div class="table">
<div class="felt">
<div class="trick" id="spPvpTrick"></div>
<div id="spPvpMsg" style="color:#dddddd;font-size:13px;min-height:18px;text-shadow:0 1px 2px rgba(0,0,0,0.9);"></div>
</div>
</div>
<div id="spPvpBidRow" class="bidrow"></div>
<div class="hand" id="spPvpHand"></div>
<div style="margin-top:10px;">
<button id="spPvpNext" style="display:none;" class="green">NEXT HAND</button>
<button id="spPvpAgain" style="display:none;" class="green">NEW GAME</button>
<button id="spLeaveBtn" class="red">LEAVE TABLE</button>
</div>
<div id="spPvpLog"></div>
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
var SUITS = ['♠', '♥', '♦', '♣'];
var RLAB = { 11: 'J', 12: 'Q', 13: 'K', 14: 'A' };
function rlab(r) { return RLAB[r] || String(r); }
function cname(c) { return rlab(c.r) + SUITS[c.s]; }
function cval(c) { return c.r >= 11 ? 10 : c.r; }
function sortCards(a) { return a.slice().sort(function (x, y) { return x.s - y.s || x.r - y.r; }); }
function mulberry32(a) {
  return function () {
    a |= 0; a = a + 0x6D2B79F5 | 0;
    var t = Math.imul(a ^ a >>> 15, 1 | a);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296;
  };
}
function seededDeck(seed) {
  var d = [];
  for (var s = 0; s < 4; s++) for (var r = 2; r <= 14; r++) d.push({ r: r, s: s });
  var rnd = mulberry32(seed);
  for (var i = d.length - 1; i > 0; i--) {
    var j = Math.floor(rnd() * (i + 1));
    var t = d[i]; d[i] = d[j]; d[j] = t;
  }
  return d;
}
var PIPMAP = {
  2: ['tc', 'bc'], 3: ['tc', 'c', 'bc'], 4: ['tl', 'tr', 'bl', 'br'],
  5: ['tl', 'tr', 'c', 'bl', 'br'], 6: ['tl', 'tr', 'ml', 'mr', 'bl', 'br'],
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
function cardBackEl(cls) {
  var b = document.createElement('button');
  b.className = 'card back ' + (cls || '');
  b.innerHTML = '🂠';
  return b;
}
/* Shared PvP sync: the room state is PUBLIC ONLY (no hands). Both devices
   shuffle the same seeded deck, so each device knows the full deal but only
   shows its own hand. Human actions travel in the log; CPU moves (Spades)
   are deterministic, so both devices compute them identically. */
var CFG = window.CARD_PVP || { me: 'you', foe: 'friend', foeName: 'FRIEND', hostId: 'you', game: 'gin', seed: 12345 };
var AMHOST = (CFG.me === CFG.hostId);
var MESEAT = AMHOST ? 'host' : 'guest';
var FOESEAT = AMHOST ? 'guest' : 'host';
var LOG = [];
function postState() {
  if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'card-shot', state: { game: CFG.game, seed: CFG.seed, actions: LOG } }));
}
function postAction(a) {
  LOG.push(a);
  postState();
  if (CFG.game === 'gin') ginReplay();
  else spReplay();
}
window.addEventListener('card-state', function (e) {
  var st = e.detail;
  if (st && st.actions && st.actions.length > LOG.length) {
    LOG = st.actions.slice();
    if (CFG.game === 'gin') ginReplay();
    else spReplay();
  }
});
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
function leaveTable() {
  var over = true;
  if (CFG.game === 'gin' && G) over = G.over;
  if (CFG.game === 'spades' && SP) over = SP.over;
  if (!over) askLeave('Leave this game? Your progress will be lost.', function () {
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
  });
  else if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
}
document.getElementById('ginLeaveBtn').addEventListener('click', leaveTable);
document.getElementById('spLeaveBtn').addEventListener('click', leaveTable);
/* ================= GIN RUMMY PvP ================= */
var G = null;
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
function ginLayoffs(knockerMelds, oppHand) {
  var remaining = [];
  oppHand.slice().forEach(function (c) {
    var placed = false;
    for (var mi = 0; mi < knockerMelds.length && !placed; mi++) {
      var m = knockerMelds[mi];
      if (m.length && m[0].r === c.r) { m.push(c); placed = true; }
      else if (m.length && m[0].s === c.s) {
        var ranks = m.map(function (x) { return x.r; });
        var min = Math.min.apply(null, ranks), max = Math.max.apply(null, ranks);
        if (c.r === min - 1 || c.r === max + 1) { m.push(c); placed = true; }
      }
    }
    if (!placed) remaining.push(c);
  });
  return remaining.reduce(function (s, c) { return s + cval(c); }, 0);
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
function ginDeal(handNum) {
  var d = seededDeck(CFG.seed * 1000003 + handNum * 7919);
  return { host: sortCards(d.slice(0, 10)), guest: sortCards(d.slice(10, 20)), stock: d.slice(21), discard: [d[20]] };
}
function ginReplay() {
  var hand = 1, scores = { host: 0, guest: 0 };
  var D = ginDeal(hand);
  var hands = { host: D.host.slice(), guest: D.guest.slice() };
  var stock = D.stock.slice(), discard = D.discard.slice();
  var turn = 'host', phase = 'draw', over = false, endText = '', lastMsg = '';
  var prevNext = false, prevNew = false;
  LOG.forEach(function (a) {
    if (a.t === 'nexthand') {
      if (prevNext) return;
      prevNext = true; prevNew = false;
      hand++;
      D = ginDeal(hand);
      hands = { host: D.host.slice(), guest: D.guest.slice() };
      stock = D.stock.slice(); discard = D.discard.slice();
      turn = (hand % 2 === 1) ? 'host' : 'guest';
      phase = 'draw'; over = false; endText = '';
      lastMsg = 'Hand ' + hand + ' dealt. ' + (turn === MESEAT ? 'Your turn - draw.' : CFG.foeName + ' draws first.');
      return;
    }
    if (a.t === 'newgame') {
      if (prevNew) return;
      prevNew = true; prevNext = false;
      hand = 1; scores = { host: 0, guest: 0 };
      D = ginDeal(1);
      hands = { host: D.host.slice(), guest: D.guest.slice() };
      stock = D.stock.slice(); discard = D.discard.slice();
      turn = 'host'; phase = 'draw'; over = false; endText = '';
      lastMsg = 'New game. Host draws first.';
      return;
    }
    prevNext = false; prevNew = false;
    if (over) return;
    if (a.t === 'draw') {
      if (turn !== a.p || phase !== 'draw') return;
      if (a.from === 'stock') { if (stock.length) hands[a.p].push(stock.pop()); }
      else if (discard.length) hands[a.p].push(discard.pop());
      hands[a.p] = sortCards(hands[a.p]);
      phase = 'discard';
      lastMsg = (a.p === MESEAT ? 'You drew from the ' : CFG.foeName + ' drew from the ') + a.from + ' pile.';
    } else if (a.t === 'discard') {
      if (turn !== a.p || phase !== 'discard') return;
      var idx = hands[a.p].findIndex(function (c) { return c.r === a.card.r && c.s === a.card.s; });
      if (idx >= 0) hands[a.p].splice(idx, 1);
      discard.push(a.card);
      turn = (a.p === 'host') ? 'guest' : 'host';
      phase = 'draw';
      lastMsg = (a.p === MESEAT ? 'You discarded ' : CFG.foeName + ' discarded ') + cname(a.card) + '.';
    } else if (a.t === 'knock' || a.t === 'gin') {
      if (turn !== a.p || phase !== 'discard') return;
      var ki = hands[a.p].findIndex(function (c) { return c.r === a.card.r && c.s === a.card.s; });
      if (ki >= 0) hands[a.p].splice(ki, 1);
      discard.push(a.card);
      var other = (a.p === 'host') ? 'guest' : 'host';
      var melds = a.melds.map(function (m) { return m.map(function (o) { return { r: o.r, s: o.s }; }); });
      var oppDead;
      if (a.t === 'gin') {
        oppDead = hands[other].reduce(function (s, c) { return s + cval(c); }, 0);
      } else {
        oppDead = ginLayoffs(melds, hands[other]);
      }
      var pts = 0, txt = '';
      if (a.t === 'gin') {
        pts = oppDead + 25;
        scores[a.p] += pts;
        txt = (a.p === MESEAT ? 'YOU GIN!' : CFG.foeName + ' GINS!') + ' ' + pts + ' points (' + oppDead + ' + 25).';
      } else if (a.dead < oppDead) {
        pts = oppDead - a.dead;
        scores[a.p] += pts;
        txt = (a.p === MESEAT ? 'You knock and win ' : CFG.foeName + ' knocks and wins ') + pts + '.';
      } else {
        pts = (a.dead - oppDead) + 10;
        scores[other] += pts;
        txt = 'Undercut! ' + (a.p === MESEAT ? CFG.foeName + ' wins ' : 'You win ') + pts + '.';
      }
      over = true; endText = txt;
      lastMsg = txt;
    }
  });
  var matchOver = (scores.host >= 100 || scores.guest >= 100) && over;
  G = { hand: hand, scores: scores, hands: hands, stock: stock, discard: discard, turn: turn, phase: phase, over: over, endText: endText, lastMsg: lastMsg, matchOver: matchOver };
  ginRenderPvp();
}
function ginRenderPvp() {
  if (!G) return;
  var myScore = AMHOST ? G.scores.host : G.scores.guest;
  var foeScore = AMHOST ? G.scores.guest : G.scores.host;
  document.getElementById('ginPvpScore').innerHTML = 'YOU: ' + myScore + ' &nbsp;|&nbsp; ' + CFG.foeName + ': ' + foeScore + ' &nbsp;|&nbsp; First to 100';
  document.getElementById('ginPvpStockN').textContent = G.stock.length;
  var db = document.getElementById('ginPvpDiscBtn');
  var top = G.discard[G.discard.length - 1];
  db.innerHTML = '';
  db.appendChild(cardEl(top, ''));
  document.getElementById('ginPvpMsg').textContent = G.over ? G.endText : (G.turn === MESEAT ? (G.phase === 'draw' ? 'Your turn. Draw from the stock or the discard pile.' : 'Your turn. Discard a card, or knock / gin if you can.') : CFG.foeName + ' is playing...');
  var myHand = G.hands[MESEAT];
  var bd = bestDeadwood(myHand);
  document.getElementById('ginPvpMelds').textContent = 'Your deadwood: ' + bd.dead + (bd.used.length ? ' | Melds: ' + bd.used.map(function (m) { return m.map(cname).join('-'); }).join('  ') : ' | No melds yet');
  var foeRow = document.getElementById('ginPvpFoe');
  foeRow.innerHTML = '';
  var foeCount = G.hands[FOESEAT].length;
  var flabel = document.createElement('div');
  flabel.className = 'sub';
  flabel.textContent = CFG.foeName + ': ' + foeCount + ' cards';
  foeRow.appendChild(flabel);
  for (var i = 0; i < Math.min(foeCount, 11); i++) foeRow.appendChild(cardBackEl('small'));
  var handEl = document.getElementById('ginPvpHand');
  handEl.innerHTML = '';
  var myTurn = (G.turn === MESEAT);
  myHand.forEach(function (c) {
    var b = cardEl(c, '');
    if (myTurn && G.phase === 'discard' && !G.over) {
      b.addEventListener('click', function () {
        postAction({ t: 'discard', p: MESEAT, card: { r: c.r, s: c.s } });
      });
    } else {
      b.disabled = true;
    }
    handEl.appendChild(b);
  });
  document.getElementById('ginPvpStockBtn').disabled = !(myTurn && G.phase === 'draw' && !G.over);
  db.disabled = !(myTurn && G.phase === 'draw' && !G.over);
  var after = (myTurn && G.phase === 'discard') ? ginDeadwoodAfterDiscard(myHand) : { dead: 99 };
  document.getElementById('ginPvpKnock').disabled = !(myTurn && G.phase === 'discard' && !G.over && after.dead <= 10);
  document.getElementById('ginPvpGinBtn').disabled = !(myTurn && G.phase === 'discard' && !G.over && after.dead === 0);
  document.getElementById('ginPvpLog').textContent = G.lastMsg;
  var nextBtn = document.getElementById('ginPvpNext');
  nextBtn.style.display = (G.over && !G.matchOver) ? 'inline-block' : 'none';
  var againBtn = document.getElementById('ginPvpAgain');
  againBtn.style.display = G.matchOver ? 'inline-block' : 'none';
  if (G.matchOver) {
    document.getElementById('ginPvpMsg').textContent = (myScore > foeScore ? 'YOU WIN THE GAME!' : CFG.foeName + ' WINS THE GAME.') + ' Final: You ' + myScore + ' - ' + CFG.foeName + ' ' + foeScore + '.';
  }
}
document.getElementById('ginPvpStockBtn').addEventListener('click', function () {
  if (!G || G.turn !== MESEAT || G.phase !== 'draw' || G.over) return;
  postAction({ t: 'draw', p: MESEAT, from: 'stock' });
});
document.getElementById('ginPvpDiscBtn').addEventListener('click', function () {
  if (!G || G.turn !== MESEAT || G.phase !== 'draw' || G.over) return;
  postAction({ t: 'draw', p: MESEAT, from: 'discard' });
});
document.getElementById('ginPvpKnock').addEventListener('click', function () {
  if (!G || G.turn !== MESEAT || G.phase !== 'discard' || G.over) return;
  var after = ginDeadwoodAfterDiscard(G.hands[MESEAT]);
  if (after.dead > 10) return;
  postAction({ t: 'knock', p: MESEAT, card: { r: after.card.r, s: after.card.s }, dead: after.dead, melds: after.melds });
});
document.getElementById('ginPvpGinBtn').addEventListener('click', function () {
  if (!G || G.turn !== MESEAT || G.phase !== 'discard' || G.over) return;
  var after = ginDeadwoodAfterDiscard(G.hands[MESEAT]);
  if (after.dead !== 0) return;
  postAction({ t: 'gin', p: MESEAT, card: { r: after.card.r, s: after.card.s }, dead: 0, melds: after.melds });
});
document.getElementById('ginPvpSort').addEventListener('click', function () {
  if (!G) return;
  G.hands[MESEAT] = sortCards(G.hands[MESEAT]);
  ginRenderPvp();
});
document.getElementById('ginPvpNext').addEventListener('click', function () {
  if (!G || !G.over || G.matchOver) return;
  postAction({ t: 'nexthand' });
});
document.getElementById('ginPvpAgain').addEventListener('click', function () {
  if (!G || !G.matchOver) return;
  postAction({ t: 'newgame' });
});

/* ================= SPADES PvP ================= */
/* Seats: 0 = South (host), 1 = West (CPU), 2 = North (guest), 3 = East (CPU).
   Host + guest are partners vs the two CPUs. Both devices run the same
   deterministic engine from the seeded deal; human bids/plays travel in
   the log, CPU bids/plays are computed identically on both devices. */
var SP = null;
function spCpuBid(hand) {
  var sp = 0, hi = 0;
  hand.forEach(function (c) { if (c.s === 0) sp++; if (c.r === 14) hi += 1; else if (c.r === 13) hi += 0.75; else if (c.r === 12) hi += 0.5; });
  var est = sp + hi;
  if (est < 1 && sp === 0) return 0;
  return Math.max(1, Math.min(13, Math.round(est)));
}
function spCurrentWinner() {
  var best = SP.trick[0];
  SP.trick.forEach(function (t) {
    if (t.c.s === 0 && best.c.s !== 0) best = t;
    else if (t.c.s === best.c.s && t.c.s === SP.ledSuit && t.c.r > best.c.r) best = t;
    else if (t.c.s === 0 && best.c.s === 0 && t.c.r > best.c.r) best = t;
  });
  return best;
}
function spCpuChoose(p) {
  var hand = SP.hands[p];
  if (SP.trick.length === 0) {
    var nonSp = hand.filter(function (c) { return c.s !== 0; });
    var pool = nonSp.length && !SP.broken ? nonSp : hand;
    pool = pool.slice().sort(function (a, b) { return a.r - b.r; });
    return pool[0];
  }
  var led = SP.ledSuit;
  var suit = hand.filter(function (c) { return c.s === led; });
  if (suit.length) {
    var cur = spCurrentWinner();
    var win = suit.filter(function (c) { return cur.c.s !== 0 ? false : (c.s === led && c.r > cur.c.r); });
    win = win.sort(function (a, b) { return a.r - b.r; });
    if (win.length) return win[0];
    return suit.slice().sort(function (a, b) { return a.r - b.r; })[0];
  }
  var sp = hand.filter(function (c) { return c.s === 0; });
  var hasSpade = SP.trick.some(function (t) { return t.c.s === 0; });
  if (sp.length && !hasSpade) {
    var low = sp.slice().sort(function (a, b) { return a.r - b.r; });
    return low[0];
  }
  var non = hand.filter(function (c) { return c.s !== 0; });
  var pool2 = non.length ? non : hand;
  return pool2.slice().sort(function (a, b) { return b.r - a.r; })[0];
}
function spDeal(handNum) {
  var d = seededDeck(CFG.seed * 1000003 + handNum * 7919);
  var hands = [[], [], [], []];
  for (var i = 0; i < 52; i++) hands[i % 4].push(d[i]);
  return hands.map(sortCards);
}
function spSeatName(seat) {
  if (seat === 0) return AMHOST ? 'You' : CFG.foeName;
  if (seat === 2) return AMHOST ? CFG.foeName : 'You';
  if (seat === 1) return 'West (CPU)';
  return 'East (CPU)';
}
function spApplyPlay(seat, card) {
  var hand = SP.hands[seat];
  var idx = hand.findIndex(function (c) { return c.r === card.r && c.s === card.s; });
  if (idx < 0) return false;
  hand.splice(idx, 1);
  if (SP.trick.length === 0) SP.ledSuit = card.s;
  if (card.s === 0 && SP.ledSuit !== 0) SP.broken = true;
  SP.trick.push({ p: seat, c: card });
  return true;
}
function spEndTrickPvp() {
  var w = spCurrentWinner().p;
  SP.took[w]++;
  SP.tricks[w % 2 === 0 ? 0 : 1]++;
  SP.msg = spSeatName(w) + ' takes the trick.';
  SP.lastTrick = SP.trick.slice();
  SP.trick = [];
  SP.ledSuit = null;
  SP.turn = w;
}
function spScoreHandPvp() {
  var usBid = SP.bids[0] + SP.bids[2], themBid = SP.bids[1] + SP.bids[3];
  var usT = SP.tricks[0], themT = SP.tricks[1];
  var usPts = 0, themPts = 0, log = [];
  if (usT >= usBid) { usPts += usBid * 10 + (usT - usBid); SP.usBags += (usT - usBid); }
  else usPts -= usBid * 10;
  if (themT >= themBid) { themPts += themBid * 10 + (themT - themBid); SP.themBags += (themT - themBid); }
  else themPts -= themBid * 10;
  [0, 2].forEach(function (p) {
    if (SP.bids[p] === 0) {
      if (SP.took[p] === 0) { usPts += 100; log.push(spSeatName(p) + ' Nil made: +100.'); }
      else { usPts -= 100; log.push(spSeatName(p) + ' Nil broken: -100.'); }
    }
  });
  [1, 3].forEach(function (p) {
    if (SP.bids[p] === 0) {
      if (SP.took[p] === 0) { themPts += 100; log.push('Opponent Nil made: +100.'); }
      else { themPts -= 100; log.push('Opponent Nil broken: -100.'); }
    }
  });
  if (SP.usBags >= 10) { usPts -= 100; SP.usBags -= 10; log.push('You hit 10 bags: -100.'); }
  if (SP.themBags >= 10) { themPts -= 100; SP.themBags -= 10; log.push('Opponents hit 10 bags: -100.'); }
  SP.us += usPts; SP.them += themPts;
  SP.endText = 'Hand over. You bid ' + usBid + ' took ' + usT + ' (' + (usPts >= 0 ? '+' : '') + usPts + '). Opponents bid ' + themBid + ' took ' + themT + ' (' + (themPts >= 0 ? '+' : '') + themPts + '). ' + log.join(' ');
  // SPADES_LAST_CARD_PVP_TEXT
  if (SP.lastTrick && SP.lastTrick.length) { var lp = SP.lastTrick[SP.lastTrick.length - 1]; SP.endText += ' Last card played: ' + rlab(lp.c.r) + SUITS[lp.c.s] + ' by ' + spSeatName(lp.p) + '.'; }
}
function spReplay() {
  var meSeat = AMHOST ? 0 : 2;
  var us = 0, them = 0, usBags = 0, themBags = 0;
  var hand = 1, idx = 0, done = false;
  var SPc = null;
  for (var iter = 0; iter < 60 && !done; iter++) {
    var hands = spDeal(hand);
    var dealer = (3 + (hand - 1)) % 4;
    var leader = (dealer + 1) % 4;
    SPc = {
      hand: hand, us: us, them: them, usBags: usBags, themBags: themBags,
      hands: hands, bids: [null, null, null, null], tricks: [0, 0], took: [0, 0, 0, 0],
      trick: [], ledSuit: null, broken: false, turn: leader, phase: 'bid',
      over: false, matchOver: false, msg: '', endText: ''
    };
    SP = SPc;
    var order = [leader, (leader + 1) % 4, (leader + 2) % 4, (leader + 3) % 4];
    var bidStop = false;
    for (var bi = 0; bi < 4; bi++) {
      var seat = order[bi];
      if (seat === 0 || seat === 2) {
        var ba = LOG[idx];
        if (ba && ba.t === 'bid' && ba.seat === seat) {
          SP.bids[seat] = ba.bid;
          idx++;
        } else {
          SP.turn = seat; SP.phase = 'bid'; SP.msg = 'Waiting for ' + spSeatName(seat) + ' to bid.';
          bidStop = true;
          break;
        }
      } else {
        SP.bids[seat] = spCpuBid(SP.hands[seat]);
      }
    }
    if (bidStop) { done = true; break; }
    SP.phase = 'play'; SP.turn = leader;
    SP.msg = 'Play a card. Spades are trump.';
    var playStop = false;
    var tricksDone = 0;
    while (tricksDone < 13) {
      var t = SP.turn;
      if (t === 1 || t === 3) {
        var cc = spCpuChoose(t);
        spApplyPlay(t, cc);
      } else {
        var pa = LOG[idx];
        if (pa && pa.t === 'play' && pa.seat === t) {
          if (!spApplyPlay(t, pa.card)) { playStop = true; break; }
          idx++;
        } else {
          SP.msg = 'Waiting for ' + spSeatName(t) + ' to play.';
          playStop = true;
          break;
        }
      }
      if (SP.trick.length === 4) {
        spEndTrickPvp();
        tricksDone++;
      } else {
        SP.turn = (t + 1) % 4;
      }
    }
    if (playStop) { done = true; break; }
    spScoreHandPvp();
    us = SP.us; them = SP.them; usBags = SP.usBags; themBags = SP.themBags;
    SP.phase = 'over'; SP.over = true;
    SP.msg = SP.endText;
    if (us >= 500 || them >= 500) {
      SP.matchOver = true;
      SP.msg = (us > them ? 'YOU WIN THE GAME!' : them > us ? 'CPU OPPONENTS WIN THE GAME.' : 'TIE GAME!') + ' Final: You ' + us + ' - Opponents ' + them + '.';
      var na = LOG[idx];
      if (na && na.t === 'newgame') {
        idx++;
        us = 0; them = 0; usBags = 0; themBags = 0; hand = 1;
        continue;
      }
      done = true;
      break;
    }
    var nh = LOG[idx];
    if (nh && nh.t === 'nexthand') {
      idx++;
      hand++;
      continue;
    }
    done = true;
  }
  SP = SPc;
  SP.us = us; SP.them = them; SP.usBags = usBags; SP.themBags = themBags;
  spRenderPvp();
}
function spCanPlayPvp(c) {
  var meSeat = AMHOST ? 0 : 2;
  if (!SP || SP.phase !== 'play' || SP.turn !== meSeat) return false;
  var myHand = SP.hands[meSeat];
  if (SP.trick.length === 0) {
    if (c.s === 0 && !SP.broken) return myHand.every(function (x) { return x.s === 0; });
    return true;
  }
  var hasSuit = myHand.some(function (x) { return x.s === SP.ledSuit; });
  if (hasSuit) return c.s === SP.ledSuit;
  return true;
}
function spRenderPvp() {
  if (!SP) return;
  var meSeat = AMHOST ? 0 : 2;
  document.getElementById('spPvpScore').innerHTML = 'YOU + ' + CFG.foeName + ': ' + SP.us + ' (bags ' + SP.usBags + ') &nbsp;|&nbsp; CPU OPPONENTS: ' + SP.them + ' (bags ' + SP.themBags + ') &nbsp;|&nbsp; First to 500';
  document.getElementById('spPvpBids').textContent = SP.bids.every(function (x) { return x !== null; })
    ? 'Bids - ' + spSeatName(0) + ' ' + SP.bids[0] + ', ' + spSeatName(1) + ' ' + SP.bids[1] + ', ' + spSeatName(2) + ' ' + SP.bids[2] + ', ' + spSeatName(3) + ' ' + SP.bids[3] + ' | Tricks - You ' + SP.tricks[0] + ', Opp ' + SP.tricks[1]
    : 'Bids - ' + spSeatName(0) + ' ' + (SP.bids[0] === null ? '?' : SP.bids[0]) + ', ' + spSeatName(1) + ' ' + (SP.bids[1] === null ? '?' : SP.bids[1]) + ', ' + spSeatName(2) + ' ' + (SP.bids[2] === null ? '?' : SP.bids[2]) + ', ' + spSeatName(3) + ' ' + (SP.bids[3] === null ? '?' : SP.bids[3]);
  document.getElementById('spPvpCounts').textContent = spSeatName(0) + ': ' + SP.hands[0].length + ' cards | ' + spSeatName(1) + ': ' + SP.hands[1].length + ' | ' + spSeatName(2) + ': ' + SP.hands[2].length + ' | ' + spSeatName(3) + ': ' + SP.hands[3].length;
  var tr = document.getElementById('spPvpTrick');
  tr.innerHTML = '';
  for (var i = 0; i < 4; i++) {
    var slot = document.createElement('div');
    slot.className = 'slot';
    var shownTrick = (SP.phase === 'over' && SP.lastTrick) ? SP.lastTrick : SP.trick;
    var played = shownTrick.find(function (t) { return t.p === i; });
    slot.innerHTML = '<div class="who">' + spSeatName(i) + (SP.turn === i && SP.phase === 'play' ? ' ●' : '') + '</div>';
    if (played) slot.appendChild(cardEl(played.c, 'small'));
    tr.appendChild(slot);
  }
  document.getElementById('spPvpMsg').textContent = SP.msg;
  var row = document.getElementById('spPvpBidRow');
  row.innerHTML = '';
  if (SP.phase === 'bid' && SP.turn === meSeat) {
    for (var b = 0; b <= 13; b++) {
      (function (bid) {
        var btn = document.createElement('button');
        btn.textContent = bid === 0 ? 'NIL' : bid;
        btn.addEventListener('click', function () { postAction({ t: 'bid', seat: meSeat, bid: bid }); });
        row.appendChild(btn);
      })(b);
    }
  }
  var handEl = document.getElementById('spPvpHand');
  handEl.innerHTML = '';
  SP.hands[meSeat].forEach(function (c) {
    var b = cardEl(c, '');
    var yourPlayTurn = (SP.phase === 'play' && SP.turn === meSeat);
    b.disabled = !(yourPlayTurn && spCanPlayPvp(c));
    b.style.opacity = (yourPlayTurn && !spCanPlayPvp(c)) ? '0.6' : '1';
    b.addEventListener('click', function () {
      if (spCanPlayPvp(c)) postAction({ t: 'play', seat: meSeat, card: { r: c.r, s: c.s } });
    });
    handEl.appendChild(b);
  });
  document.getElementById('spPvpLog').textContent = SP.endText || '';
  document.getElementById('spPvpNext').style.display = (SP.phase === 'over' && !SP.matchOver) ? 'inline-block' : 'none';
  document.getElementById('spPvpAgain').style.display = SP.matchOver ? 'inline-block' : 'none';
}
document.getElementById('spPvpNext').addEventListener('click', function () {
  if (!SP || SP.phase !== 'over' || SP.matchOver) return;
  postAction({ t: 'nexthand' });
});
document.getElementById('spPvpAgain').addEventListener('click', function () {
  if (!SP || !SP.matchOver) return;
  postAction({ t: 'newgame' });
});
/* ================= INIT ================= */
if (CFG.game === 'spades') {
  document.getElementById('spPvpView').style.display = 'block';
  document.getElementById('ginPvpView').style.display = 'none';
  document.getElementById('spPvpTitle').textContent = 'CARD TABLE - SPADES - YOU vs ' + CFG.foeName;
  spReplay();
} else {
  document.getElementById('ginPvpView').style.display = 'block';
  document.getElementById('spPvpView').style.display = 'none';
  document.getElementById('ginPvpTitle').textContent = 'CARD TABLE - GIN RUMMY - YOU vs ' + CFG.foeName;
  ginReplay();
}

</script>
</body>
</html>
`;
