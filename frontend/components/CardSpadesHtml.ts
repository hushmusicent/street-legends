export const CARD_SPADES_HTML = `<!DOCTYPE html>
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
<div id="spadesView" >
<h1>CARD TABLE - SPADES</h1>
<div id="spScore"></div>
<div id="spBids" class="sub"></div>
<div class="table">
<div class="felt">
<div class="trick" id="spTrick"></div>
<div id="spMsg" style="color:#dddddd;font-size:13px;min-height:18px;text-shadow:0 1px 2px rgba(0,0,0,0.9);"></div>
</div>
</div>
<div id="spBidRow" class="bidrow"></div>
<div class="hand" id="spHand"></div>
<div id="spBtns" style="margin-top:10px;">
<button id="spNext"  class="green">NEXT HAND</button>
<button id="leaveBtn" class="red">LEAVE TABLE</button>
</div>
<div id="spLog"></div>
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
/* ================= SPADES ================= */
var SP = null;
function spNewGame() {
  document.querySelectorAll('.newgame').forEach(function (el) { el.remove(); });
  SP = { us: 0, them: 0, usBags: 0, themBags: 0, hand: 1, dealer: 3, over: false };
  spNewHand();
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
function spCpuBid(hand) {
  var sp = 0, hi = 0;
  hand.forEach(function (c) { if (c.s === 0) sp++; if (c.r === 14) hi += 1; else if (c.r === 13) hi += 0.75; else if (c.r === 12) hi += 0.5; });
  var est = sp + hi;
  if (est < 1 && sp === 0) return 0;
  return Math.max(1, Math.min(13, Math.round(est)));
}
function spNewHand() {
  var d = newDeck();
  var hands = [[], [], [], []];
  for (var i = 0; i < 52; i++) hands[i % 4].push(d[i]);
  hands = hands.map(sortCards);
  SP.hands = hands;
  SP.bids = [null, null, null, null];
  SP.tricks = [0, 0];
  SP.took = [0, 0, 0, 0];
  SP.trick = [];
  SP.ledSuit = null;
  SP.broken = false;
  SP.leader = (SP.dealer + 1) % 4;
  SP.turn = SP.leader;
  SP.phase = 'bid';
  SP.msg = 'Hand ' + SP.hand + '. Place your bid (0 = Nil).';
  document.getElementById('spNext').style.display = 'none';
  spRenderBidRow();
  spRender();
  if (SP.turn !== 0) spCpuTurn();
}
function spRenderBidRow() {
  var row = document.getElementById('spBidRow');
  row.innerHTML = '';
  if (SP.phase !== 'bid' || SP.turn !== 0) return;
  for (var b = 0; b <= 13; b++) {
    (function (bid) {
      var btn = document.createElement('button');
      btn.textContent = bid === 0 ? 'NIL' : bid;
      btn.addEventListener('click', function () { spBid(0, bid); });
      row.appendChild(btn);
    })(b);
  }
}
function spBid(p, bid) {
  if (p === 0 && SP.turn !== 0) return;
  SP.bids[p] = bid;
  if (p === 0) { document.getElementById('spBidRow').innerHTML = ''; }
  spRender();
  var next = (p + 1) % 4;
  if (SP.bids.every(function (x) { return x !== null; })) {
    SP.phase = 'play';
    SP.turn = SP.leader;
    SP.msg = 'Play a card. Spades are trump.';
    spRender();
    if (SP.turn !== 0) spCpuTurn();
    return;
  }
  if (next === 0) { SP.phase = 'bid'; spRenderBidRow(); spRender(); }
  else { setTimeout(function () { spBid(next, spCpuBid(SP.hands[next])); }, 500); }
}
function spCanPlay(c) {
  if (SP.phase !== 'play' || SP.turn !== 0) return false;
  if (SP.trick.length === 0) {
    if (c.s === 0 && !SP.broken) {
      var onlySpades = SP.hands[0].every(function (x) { return x.s === 0; });
      return onlySpades;
    }
    return true;
  }
  var hasSuit = SP.hands[0].some(function (x) { return x.s === SP.ledSuit; });
  if (hasSuit) return c.s === SP.ledSuit;
  return true;
}
function spPlay(p, c) {
  var hand = SP.hands[p];
  var idx = hand.indexOf(c);
  hand.splice(idx, 1);
  if (SP.trick.length === 0) SP.ledSuit = c.s;
  if (c.s === 0 && SP.ledSuit !== 0) SP.broken = true;
  SP.trick.push({ p: p, c: c });
  spRender();
  if (SP.trick.length === 4) {
    setTimeout(spEndTrick, 700);
  } else {
    SP.turn = (p + 1) % 4;
    spRender();
    if (SP.turn !== 0) spCpuTurn();
  }
}
function spEndTrick() {
  var w = spCurrentWinner().p;
  SP.took[w]++;
  SP.tricks[w % 2 === 0 ? 0 : 1]++;
  SP.msg = ['You', 'West', 'Partner', 'East'][w] + ' takes the trick.';
  SP.trick = [];
  SP.ledSuit = null;
  if (SP.hands[0].length === 0) { spScoreHand(); return; }
  SP.turn = w;
  SP.leader = w;
  spRender();
  if (SP.turn !== 0) spCpuTurn();
}
function spScoreHand() {
  var usBid = SP.bids[0] + SP.bids[2], themBid = SP.bids[1] + SP.bids[3];
  var usT = SP.tricks[0], themT = SP.tricks[1];
  var usPts = 0, themPts = 0, log = [];
  if (usT >= usBid) { usPts += usBid * 10 + (usT - usBid); SP.usBags += (usT - usBid); }
  else usPts -= usBid * 10;
  if (themT >= themBid) { themPts += themBid * 10 + (themT - themBid); SP.themBags += (themT - themBid); }
  else themPts -= themBid * 10;
  [0, 2].forEach(function (p) {
    if (SP.bids[p] === 0) {
      if (SP.took[p] === 0) { usPts += 100; log.push((p === 0 ? 'Your' : 'Partner') + ' Nil made: +100.'); }
      else { usPts -= 100; log.push((p === 0 ? 'Your' : 'Partner') + ' Nil broken: -100.'); }
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
  SP.msg = 'Hand over. You bid ' + usBid + ' took ' + usT + ' (' + (usPts >= 0 ? '+' : '') + usPts + '). Opponents bid ' + themBid + ' took ' + themT + ' (' + (themPts >= 0 ? '+' : '') + themPts + ').';
  document.getElementById('spLog').textContent = log.join(' ');
  spRender();
  if (SP.us >= 500 || SP.them >= 500) {
    SP.over = true;
    SP.msg = (SP.us > SP.them ? 'YOU WIN THE GAME!' : SP.them > SP.us ? 'OPPONENTS WIN THE GAME.' : 'TIE GAME!') + ' Final: You ' + SP.us + ' - Opponents ' + SP.them + '.';
    if (SP.us > SP.them) if (window.ReactNativeWebView && window.ReactNativeWebView.postMessage) window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'center_prize_win', game: 'card_table', level: 1 }));
    document.getElementById('spNext').style.display = 'none';
    var again = document.createElement('button');
    again.className = 'green newgame'; again.textContent = 'NEW GAME';
    again.addEventListener('click', function () { spNewGame(); });
    document.getElementById('spBtns').appendChild(again);
  } else {
    document.getElementById('spNext').style.display = 'inline-block';
  }
  spRender();
}
document.getElementById('spNext').addEventListener('click', function () {
  SP.hand++;
  SP.dealer = (SP.dealer + 1) % 4;
  spNewHand();
});
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
function spCpuTurn() {
  if (!SP || SP.phase === 'bid') {
    var p = SP.turn;
    setTimeout(function () { if (SP && SP.turn === p) spBid(p, spCpuBid(SP.hands[p])); }, 600);
    return;
  }
  if (SP.phase !== 'play' || SP.trick.length === 4) return;
  var p = SP.turn;
  setTimeout(function () {
    if (!SP || SP.phase !== 'play' || SP.turn !== p) return;
    spPlay(p, spCpuChoose(p));
  }, 700);
}
function spRender() {
  if (!SP) return;
  var names = ['You', 'West', 'Partner', 'East'];
  document.getElementById('spScore').innerHTML = 'YOU + PARTNER: ' + SP.us + ' (bags ' + SP.usBags + ') &nbsp;|&nbsp; OPPONENTS: ' + SP.them + ' (bags ' + SP.themBags + ') &nbsp;|&nbsp; First to 500';
  document.getElementById('spBids').textContent = SP.bids.every(function (x) { return x !== null; })
    ? 'Bids - You ' + SP.bids[0] + ', West ' + SP.bids[1] + ', Partner ' + SP.bids[2] + ', East ' + SP.bids[3] + ' | Tricks - You ' + SP.tricks[0] + ', Opp ' + SP.tricks[1]
    : 'Bids - You ' + (SP.bids[0] === null ? '?' : SP.bids[0]) + ', West ' + (SP.bids[1] === null ? '?' : SP.bids[1]) + ', Partner ' + (SP.bids[2] === null ? '?' : SP.bids[2]) + ', East ' + (SP.bids[3] === null ? '?' : SP.bids[3]);
  var tr = document.getElementById('spTrick');
  tr.innerHTML = '';
  for (var i = 0; i < 4; i++) {
    var slot = document.createElement('div');
    slot.className = 'slot';
    var played = SP.trick.find(function (t) { return t.p === i; });
    slot.innerHTML = '<div class="who">' + names[i] + (SP.turn === i && SP.phase === 'play' ? ' ●' : '') + '</div>';
    if (played) slot.appendChild(cardEl(played.c, 'small'));
    tr.appendChild(slot);
  }
  document.getElementById('spMsg').textContent = SP.msg;
  var handEl = document.getElementById('spHand');
  handEl.innerHTML = '';
  SP.hands[0].forEach(function (c) {
    var b = cardEl(c, '');
    var yourPlayTurn = (SP.phase === 'play' && SP.turn === 0);
    b.disabled = !(yourPlayTurn && spCanPlay(c));
    b.style.opacity = (yourPlayTurn && !spCanPlay(c)) ? '0.6' : '1';
    b.addEventListener('click', function () { if (spCanPlay(c)) spPlay(0, c); });
    handEl.appendChild(b);
  });
}


document.getElementById('leaveBtn').addEventListener('click', function () {
  var over = (typeof SP !== 'undefined' && SP) ? SP.over : (typeof G !== 'undefined' && G) ? G.over : true;
  if (!over) askLeave('Leave this game? Your progress will be lost.', function () {
    if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
  });
  else if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage('close');
});

spNewGame();
})();
</script>
</body>
</html>
`;
