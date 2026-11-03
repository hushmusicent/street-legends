export const TEXAS_HOLDEM_PVP_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Texas Hold'em - Player vs Player</title>
<style>
body{background:radial-gradient(ellipse at center,#262626 0%,#111 55%,#000 100%);color:#fff;font-family:Arial,Helvetica,sans-serif;text-align:center;margin:0;padding:12px}
h1{margin:8px 0 4px;font-size:28px;letter-spacing:1px}
.sub{color:#ccc;font-size:14px;margin-bottom:14px}
.card{background:#1c1c1c;border:1px solid #333;border-radius:12px;padding:14px;max-width:520px;margin:0 auto 12px;text-align:left;box-shadow:0 6px 18px rgba(0,0,0,.5)}
.card h3{margin:6px 0 8px;font-size:15px;color:#ffd54f}
.row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px}
.btn{background:linear-gradient(180deg,#43A047,#2e7d32);color:#fff;border:none;border-radius:8px;padding:11px 16px;font-weight:800;cursor:pointer;font-size:15px;box-shadow:0 3px 6px rgba(0,0,0,.5),inset 0 1px 0 rgba(255,255,255,.25)}
.btn.blue{background:linear-gradient(180deg,#42A5F5,#1e88e5)}.btn.grey{background:linear-gradient(180deg,#7a7a7a,#666)}.btn.red{background:linear-gradient(180deg,#D32F2F,#b71c1c)}
.btn.sel{outline:3px solid #ffd54f;outline-offset:1px}
.btn:disabled{opacity:.45}

#game{display:none;max-width:520px;margin:0 auto}
#turnText{font-weight:800;font-size:18px;margin:8px 0 2px;text-shadow:0 2px 4px rgba(0,0,0,.8)}
#statusText{color:#ffd54f;font-weight:800;min-height:22px;margin-bottom:8px;text-shadow:0 2px 4px rgba(0,0,0,.8)}
.table{width:min(92vw,480px);margin:0 auto;box-sizing:border-box;background:repeating-linear-gradient(90deg,rgba(0,0,0,.28) 0 2px,transparent 2px 64px),linear-gradient(145deg,#8a5a2b 0%,#6b3f1d 45%,#5d3418 60%,#7a4a22 100%);border-radius:50%;box-shadow:0 20px 44px rgba(0,0,0,.9),inset 0 3px 0 rgba(255,255,255,.25),inset 0 -6px 14px rgba(0,0,0,.5);padding:16px}
.felt{position:relative;box-sizing:border-box;background:radial-gradient(ellipse at 50% 35%,#4caf50 0%,#2e7d32 55%,#1b5e20 100%);border-radius:50%;padding:26px 10px;display:flex;flex-direction:column;align-items:center;gap:10px;min-height:300px}
.felt::before{content:"";position:absolute;inset:14px;border:2px dashed rgba(255,255,255,.35);border-radius:50%;pointer-events:none}
.pname{font-weight:800;font-size:16px;text-shadow:0 2px 3px rgba(0,0,0,.7)}
.pinfo{color:#e8f5e9;font-size:13px;text-shadow:0 1px 2px rgba(0,0,0,.6)}
.dealer-chip{display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;width:28px;height:28px;border-radius:50%;background:radial-gradient(circle at 35% 30%,#ffffff,#dddddd 60%,#bbbbbb);color:#000;font-weight:900;font-size:15px;border:2px solid #111;box-shadow:0 3px 5px rgba(0,0,0,.65);vertical-align:middle}
.pot{font-weight:900;font-size:18px;color:#fff;text-shadow:0 2px 3px rgba(0,0,0,.6)}
.hole,.comm{display:flex;gap:8px;justify-content:center;align-items:center;min-height:68px}
.pcard{position:relative;width:46px;height:64px;border-radius:8px;background:linear-gradient(180deg,#ffffff,#e8e8e8);color:#111;display:flex;align-items:center;justify-content:center;font-weight:900;box-shadow:0 5px 10px rgba(0,0,0,.6);border:1px solid #999}
.pcard .s{font-size:30px;line-height:1}
.pcard .corner-tl{position:absolute;top:3px;left:4px;font-size:12px;line-height:1.1;text-align:center}
.pcard .corner-br{position:absolute;bottom:3px;right:4px;font-size:12px;line-height:1.1;text-align:center;transform:rotate(180deg)}
.pcard .cs{font-size:10px}
.pcard.red{color:#c62828}
.pcard.back{background:repeating-linear-gradient(45deg,#c62828,#c62828 6px,#7f0000 6px,#7f0000 12px);border:2px solid #fff;color:transparent}
.pcard.mini{width:24px;height:34px}
.slot{width:46px;height:64px;border:2px dashed rgba(255,255,255,.35);border-radius:6px}
.handname{color:#ffd54f;font-weight:800;font-size:14px;min-height:18px;text-shadow:0 1px 2px rgba(0,0,0,.6)}
.chipstack{display:inline-flex;align-items:center;vertical-align:middle;margin-right:4px}
.chipstack .chip{width:15px;height:15px;border-radius:50%;margin-left:-5px;border:2px dashed rgba(255,255,255,.85);box-shadow:0 2px 3px rgba(0,0,0,.6)}
.chipstack .chip:first-child{margin-left:0}
.chip.c-white{background:radial-gradient(circle at 35% 30%,#ffffff,#dddddd 60%,#bbbbbb)}
.chip.c-red{background:radial-gradient(circle at 35% 30%,#ff6b5e,#c62828 60%,#7f0000)}
.chip.c-blue{background:radial-gradient(circle at 35% 30%,#64b5f6,#1565c0 60%,#0d47a1)}
.burnpile{min-height:26px;display:flex;align-items:center;justify-content:center;gap:6px;color:#ccc;font-size:12px;font-weight:800}
#actions{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:12px;align-items:center}
#betBox{display:flex;gap:8px;align-items:center}
#betSlider{width:180px}
#betAmount{font-weight:800;min-width:52px}
#handBox{display:none;margin-top:12px}
.controls{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:12px}
#overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.88);align-items:center;justify-content:center;z-index:50}
#overlayBox{background:#222;border:2px solid #ffd54f;border-radius:12px;padding:20px;text-align:center;max-width:320px;box-shadow:0 14px 34px rgba(0,0,0,.85)}
#overlayBox p{font-size:17px;font-weight:800;margin:0 0 14px}
.note{color:#aaa;font-size:12px;margin-top:10px}
</style>
</head>
<body>
<h1>Texas Hold'em</h1>
<div class="sub">Heads-up No-Limit &middot; Player vs Player &middot; Blinds 10 / 20</div>
<div id="game">
<div id="turnText"></div>
<div id="statusText"></div>
<div class="table"><div class="felt">
<div><div class="pname"><span id="oppName"></span><span id="oppDealer"></span></div><div class="pinfo">Stack: <span id="oppStack"></span> &middot; Bet: <span id="oppBet"></span></div><div class="hole" id="oppCards"></div><div class="handname" id="oppHand"></div></div>
<div class="pot">Pot: <span id="potText"></span></div>
<div id="burnPile" class="burnpile"></div>
<div class="comm" id="commCards"></div>
<div><div class="hole" id="myCards"></div><div class="handname" id="myHand"></div><div class="pname"><span id="myName"></span><span id="myDealer"></span></div><div class="pinfo">Stack: <span id="myStack"></span> &middot; Bet: <span id="myBet"></span></div></div>
</div></div>
<div id="actions">
<button class="btn red" id="btnFold">FOLD</button>
<button class="btn grey" id="btnCheck">CHECK</button>
<button class="btn blue" id="btnCall">CALL</button>
<div id="betBox"><input type="range" id="betSlider" step="10"><span id="betAmount"></span><button class="btn" id="btnBet">BET</button></div>
<button class="btn red" id="btnAllIn">ALL-IN</button>
</div>
<div id="handBox"><div id="handResult" style="font-weight:800;margin-bottom:10px"></div><div class="controls">
<button class="btn" id="btnNextHand">NEXT HAND</button>
<button class="btn" id="btnPlayAgain" style="display:none">PLAY AGAIN</button>
<button class="btn grey" id="btnClose2">CLOSE</button>
</div></div>
<div class="controls"><button class="btn grey" id="btnLeave">LEAVE ROOM</button><button class="btn grey" id="btnClose">CLOSE</button></div>
<div class="card" style="margin-top:12px"><h3>CHAT</h3><div id="chatLog" style="max-height:140px;overflow:auto;background:#1a1a1a;border-radius:8px;padding:10px;margin-bottom:10px;text-align:left;font-size:13px"></div><div class="row"><input id="chatInput" type="text" placeholder="Say something..." style="flex:1;background:#222;color:#fff;padding:10px;border-radius:8px;border:none"><button class="btn blue" id="btnChatSend">SEND</button></div></div>
<div class="note">Heads-up No-Limit. Your hole cards are hidden from your opponent until showdown. A fold never reveals your cards.</div>
</div>

<script>

var SUITS = ['s','h','d','c'];
var SUIT_SYM = {s:'\u2660', h:'\u2665', d:'\u2666', c:'\u2663'};
function rankName(r){ return r===14?'A':r===13?'K':r===12?'Q':r===11?'J':String(r); }
function rankPlural(r){ return r===14?'Aces':r===13?'Kings':r===12?'Queens':r===11?'Jacks':rankName(r)+'s'; }
function makeDeck(){ var d=[]; for(var s=0;s<4;s++) for(var r=2;r<=14;r++) d.push({r:r,s:SUITS[s]}); return d; }
function shuffleDeck(d, rng){ rng = rng || Math.random; for(var i=d.length-1;i>0;i--){ var j=Math.floor(rng()*(i+1)); var t=d[i]; d[i]=d[j]; d[j]=t; } return d; }
function cardKey(c){ return c.r + '_' + c.s; }
function eval5(cards){
  var ranks = cards.map(function(c){ return c.r; }).sort(function(a,b){ return b-a; });
  var flush = true; for(var i=1;i<5;i++) if(cards[i].s !== cards[0].s) flush = false;
  var uniq = []; for(var k=0;k<5;k++) if(uniq.indexOf(ranks[k]) < 0) uniq.push(ranks[k]);
  var straightHigh = 0;
  if(uniq.length === 5){
    if(uniq[0] - uniq[4] === 4) straightHigh = uniq[0];
    else if(uniq[0] === 14 && uniq[1] === 5 && uniq[2] === 4 && uniq[3] === 3 && uniq[4] === 2) straightHigh = 5;
  }
  var counts = {}; for(var m=0;m<5;m++) counts[ranks[m]] = (counts[ranks[m]] || 0) + 1;
  var groups = Object.keys(counts).map(function(key){ return {r: +key, n: counts[key]}; });
  groups.sort(function(a,b){ return (b.n - a.n) || (b.r - a.r); });
  if(straightHigh && flush){
    return {cat: 8, tb: [straightHigh], name: straightHigh === 14 ? 'Royal Flush' : 'Straight Flush, ' + rankName(straightHigh) + ' high'};
  }
  if(groups[0].n === 4) return {cat: 7, tb: [groups[0].r, groups[1].r], name: 'Four of a Kind, ' + rankPlural(groups[0].r)};
  if(groups[0].n === 3 && groups[1].n === 2) return {cat: 6, tb: [groups[0].r, groups[1].r], name: 'Full House, ' + rankPlural(groups[0].r) + ' full of ' + rankPlural(groups[1].r)};
  if(flush) return {cat: 5, tb: ranks.slice(), name: 'Flush, ' + rankName(ranks[0]) + ' high'};
  if(straightHigh) return {cat: 4, tb: [straightHigh], name: 'Straight, ' + rankName(straightHigh) + ' high'};
  if(groups[0].n === 3){
    var kick = groups.slice(1).map(function(g){ return g.r; }).sort(function(a,b){ return b-a; });
    return {cat: 3, tb: [groups[0].r].concat(kick), name: 'Three of a Kind, ' + rankPlural(groups[0].r)};
  }
  if(groups[0].n === 2 && groups[1].n === 2){
    var pr = [groups[0].r, groups[1].r].sort(function(a,b){ return b-a; });
    return {cat: 2, tb: pr.concat([groups[2].r]), name: 'Two Pair, ' + rankPlural(pr[0]) + ' and ' + rankPlural(pr[1])};
  }
  if(groups[0].n === 2){
    var kick2 = groups.slice(1).map(function(g){ return g.r; }).sort(function(a,b){ return b-a; });
    return {cat: 1, tb: [groups[0].r].concat(kick2), name: 'Pair of ' + rankPlural(groups[0].r)};
  }
  return {cat: 0, tb: ranks.slice(), name: 'High Card, ' + rankName(ranks[0])};
}
function cmpEval(a, b){
  if(a.cat !== b.cat) return a.cat - b.cat;
  var n = Math.max(a.tb.length, b.tb.length);
  for(var i=0;i<n;i++){ var x = a.tb[i] || 0, y = b.tb[i] || 0; if(x !== y) return x - y; }
  return 0;
}
function evalBest(cards){
  var best = null;
  var n = cards.length;
  for(var a=0;a<n-4;a++) for(var b=a+1;b<n-3;b++) for(var c=b+1;c<n-2;c++) for(var d=c+1;d<n-1;d++) for(var e=d+1;e<n;e++){
    var five = [cards[a], cards[b], cards[c], cards[d], cards[e]];
    var ev = eval5(five);
    if(!best || cmpEval(ev, best) > 0) best = ev;
  }
  return best;
}
function eval7(cards7){
  var best = null;
  for(var a=0;a<3;a++) for(var b=a+1;b<4;b++) for(var c=b+1;c<5;c++) for(var d=c+1;d<6;d++) for(var e=d+1;e<7;e++){
    var five = [cards7[a], cards7[b], cards7[c], cards7[d], cards7[e]];
    var ev = eval5(five);
    if(!best || cmpEval(ev, best) > 0) best = ev;
  }
  return best;
}
function hasFlushDraw(hole, comm){
  var all = hole.concat(comm); var cnt = {};
  for(var i=0;i<all.length;i++) cnt[all[i].s] = (cnt[all[i].s] || 0) + 1;
  for(var s in cnt) if(cnt[s] === 4) return true;
  return false;
}
function hasStraightDraw(hole, comm){
  var ranks = []; var all = hole.concat(comm);
  for(var i=0;i<all.length;i++) if(ranks.indexOf(all[i].r) < 0) ranks.push(all[i].r);
  if(ranks.indexOf(14) >= 0) ranks.push(1);
  ranks.sort(function(a,b){ return a-b; });
  for(var lo=1; lo<=10; lo++){
    var n = 0; for(var k=0;k<5;k++) if(ranks.indexOf(lo + k) >= 0) n++;
    if(n === 4) return true;
  }
  return false;
}
function newPokerGame(){
  return {
    p: [{name: 'YOU', stack: 1000, bet: 0, hole: [], folded: false, allIn: false, acted: false},
        {name: 'CPU', stack: 1000, bet: 0, hole: [], folded: false, allIn: false, acted: false}],
    pot: 0, comm: [], deck: [], burned: [], street: 0, button: 0, currentBet: 0, toAct: 0, lastRaise: 20, reopened: true, actedRound: [false, false],
    handOver: false, handNum: 0, winner: -1, winAmount: 0, tie: false,
    handNames: [null, null], showdown: false, sessionOver: false, sessionWinner: -1
  };
}
function pgResetSession(g){
  g.p[0].stack = 1000; g.p[1].stack = 1000;
  g.handNum = 0; g.button = 0; g.sessionOver = false; g.sessionWinner = -1;
}
function pgPostBlind(g, idx, amount){
  var me = g.p[idx];
  var amt = Math.min(amount, me.stack);
  me.stack -= amt; me.bet = amt;
  if(me.stack === 0) me.allIn = true;
  return amt;
}
function pgNewHand(g){
  g.handNum++;
  if(g.handNum > 1) g.button = 1 - g.button;
  g.pot = 0; g.comm = []; g.burned = []; g.street = 0; g.currentBet = 0; g.toAct = g.button; g.lastRaise = 20; g.reopened = true; g.actedRound = [false, false];
  g.handOver = false; g.winner = -1; g.winAmount = 0; g.tie = false;
  g.handNames = [null, null]; g.showdown = false;
  for(var i=0;i<2;i++){ var pl = g.p[i]; pl.bet = 0; pl.hole = []; pl.folded = false; pl.allIn = false; pl.acted = false; }
  g.deck = shuffleDeck(makeDeck());
  g.p[0].hole = [g.deck.pop(), g.deck.pop()];
  g.p[1].hole = [g.deck.pop(), g.deck.pop()];
  var sb = g.button, bb = 1 - g.button;
  var sbAmt = pgPostBlind(g, sb, 10);
  var bbAmt = pgPostBlind(g, bb, 20);
  g.currentBet = Math.max(sbAmt, bbAmt);
  g.toAct = sb;
  if(g.p[0].allIn || g.p[1].allIn) pgDealOut(g);
}
function pgLegal(g, idx){
  var me = g.p[idx];
  var need = g.currentBet - me.bet;
  var lastRaise = (typeof g.lastRaise === 'number') ? g.lastRaise : 20;
  var minTo = (g.currentBet === 0) ? 20 : g.currentBet + lastRaise;
  var maxTo = me.bet + me.stack;
  var hasActedRound = (g.actedRound ? !!g.actedRound[idx] : !!me.acted);
  var canRaise = (g.reopened !== false) || !hasActedRound;
  return {need: need, canCheck: need === 0, canCall: need > 0, callAmount: Math.min(need, me.stack), minTo: minTo, maxTo: maxTo, canRaise: canRaise, lastRaise: lastRaise};
}
function pgCheckBust(g){
  if(g.p[0].stack === 0 && g.p[1].stack > 0){ g.sessionOver = true; g.sessionWinner = 1; }
  else if(g.p[1].stack === 0 && g.p[0].stack > 0){ g.sessionOver = true; g.sessionWinner = 0; }
}
function pgCollectAndAdvance(g){
  var m = Math.min(g.p[0].bet, g.p[1].bet);
  g.pot += 2 * m;
  g.p[0].stack += (g.p[0].bet - m);
  g.p[1].stack += (g.p[1].bet - m);
  g.p[0].bet = 0; g.p[1].bet = 0;
  g.p[0].acted = false; g.p[1].acted = false; g.actedRound = [false, false];
  g.currentBet = 0;
  if(g.street === 3){ pgShowdown(g); return; }
  if(g.p[0].allIn || g.p[1].allIn){ pgDealOut(g); return; }
  g.street++;
  g.lastRaise = 20; g.reopened = true;
  g.burned.push(g.deck.pop());
  if(g.street === 1){ g.comm.push(g.deck.pop()); g.comm.push(g.deck.pop()); g.comm.push(g.deck.pop()); }
  else { g.comm.push(g.deck.pop()); }
  g.toAct = 1 - g.button;
}
function pgDealOut(g){
  while(g.street < 3){
    g.street++;
    g.burned.push(g.deck.pop());
    if(g.street === 1){ g.comm.push(g.deck.pop()); g.comm.push(g.deck.pop()); g.comm.push(g.deck.pop()); }
    else { g.comm.push(g.deck.pop()); }
  }
  var m = Math.min(g.p[0].bet, g.p[1].bet);
  g.pot += 2 * m;
  g.p[0].stack += (g.p[0].bet - m);
  g.p[1].stack += (g.p[1].bet - m);
  g.p[0].bet = 0; g.p[1].bet = 0; g.currentBet = 0;
  pgShowdown(g);
}
function pgShowdown(g){
  g.street = 4; g.showdown = true; g.handOver = true;
  var ev0 = eval7(g.p[0].hole.concat(g.comm));
  var ev1 = eval7(g.p[1].hole.concat(g.comm));
  g.handNames = [ev0.name, ev1.name];
  var cmp = cmpEval(ev0, ev1);
  if(cmp > 0){ g.winner = 0; g.winAmount = g.pot; g.p[0].stack += g.pot; }
  else if(cmp < 0){ g.winner = 1; g.winAmount = g.pot; g.p[1].stack += g.pot; }
  else {
    g.tie = true; g.winner = -1;
    var half = Math.floor(g.pot / 2), odd = g.pot % 2;
    g.winAmount = g.pot;
    g.p[0].stack += half + ((odd === 1 && g.button === 0) ? 1 : 0);
    g.p[1].stack += half + ((odd === 1 && g.button === 1) ? 1 : 0);
  }
  g.pot = 0;
  pgCheckBust(g);
}
function pgAct(g, action, amount){
  if(g.handOver) return;
  var me = g.p[g.toAct], opp = g.p[1 - g.toAct];
  var leg = pgLegal(g, g.toAct);
  if(action === 'fold'){
    me.folded = true; if(g.actedRound) g.actedRound[g.toAct] = true; g.handOver = true; g.winner = 1 - g.toAct;
    g.winAmount = g.pot + g.p[0].bet + g.p[1].bet;
    opp.stack += g.winAmount;
    g.pot = 0; g.p[0].bet = 0; g.p[1].bet = 0;
    pgCheckBust(g);
    return;
  }
  if(action === 'check'){
    if(leg.need !== 0) return;
    me.acted = true; if(g.actedRound) g.actedRound[g.toAct] = true;
    if(opp.acted) pgCollectAndAdvance(g); else g.toAct = 1 - g.toAct;
    return;
  }
  if(action === 'call'){
    var pay = Math.min(leg.need, me.stack);
    me.bet += pay; me.stack -= pay;
    if(me.stack === 0) me.allIn = true;
    me.acted = true; if(g.actedRound) g.actedRound[g.toAct] = true;
    if(opp.acted || me.allIn) pgCollectAndAdvance(g); else g.toAct = 1 - g.toAct;
    return;
  }
  if(action === 'raise'){
    if(!leg.canRaise) return;
    var to = amount;
    if(to === undefined || to === null) to = leg.maxTo;
    if(to > leg.maxTo) to = leg.maxTo;
    var isShort = (to < leg.minTo && to === leg.maxTo);
    if(to < leg.minTo && to !== leg.maxTo) to = leg.minTo;
    if(to > leg.maxTo) to = leg.maxTo;
    var oldBet = g.currentBet;
    var add = to - me.bet;
    if(add < 0) add = 0;
    if(add > me.stack) add = me.stack;
    if(add <= 0) return;
    me.bet += add; me.stack -= add;
    if(me.stack === 0) me.allIn = true;
    g.currentBet = me.bet;
    if(isShort){ g.reopened = false; }
    else {
      g.reopened = true;
      if(oldBet === 0) g.lastRaise = to;
      else g.lastRaise = to - oldBet;
    }
    me.acted = true; opp.acted = false; if(g.actedRound) g.actedRound[g.toAct] = true;
    g.toAct = 1 - g.toAct;
    return;
  }
}
function preflopScore(hole){
  var r1 = hole[0].r, r2 = hole[1].r, hi = Math.max(r1, r2), lo = Math.min(r1, r2);
  var s = 0;
  if(r1 === r2) s = 0.5 + (r1 / 14) * 0.3;
  else s = (hi / 14) * 0.4 + (lo / 14) * 0.1;
  if(hole[0].s === hole[1].s) s += 0.08;
  if(Math.abs(r1 - r2) === 1) s += 0.05;
  else if(Math.abs(r1 - r2) === 2) s += 0.02;
  if(hi >= 11 && lo >= 11 && r1 !== r2) s += 0.08;
  if(s > 1) s = 1; if(s < 0) s = 0;
  return s;
}
function cpuDecide(g, idx, rng){
  rng = rng || Math.random;
  var me = g.p[idx];
  var leg = pgLegal(g, idx);
  var potTotal = g.pot + g.p[0].bet + g.p[1].bet;
  var strength;
  if(g.street === 0) strength = preflopScore(me.hole);
  else {
    var ev = evalBest(me.hole.concat(g.comm));
    strength = (ev.cat / 8) * 0.85;
    if(ev.cat < 5 && hasFlushDraw(me.hole, g.comm)) strength += 0.15;
    if(ev.cat < 4 && hasStraightDraw(me.hole, g.comm)) strength += 0.12;
    if(strength > 1) strength = 1;
  }
  var noise = 0.10 * (rng() * 2 - 1);
  var s = strength + noise;
  if(s > 1) s = 1; if(s < 0) s = 0;
  function clampRaise(desired){
    var to = desired;
    if(to > leg.maxTo) to = leg.maxTo;
    if(to < leg.minTo && to !== leg.maxTo) to = leg.minTo;
    if(to > leg.maxTo) to = leg.maxTo;
    return to;
  }
  if(!leg.canRaise){
    if(leg.need === 0) return {act: 'check'};
    if(s >= 0.55) return {act: 'call'};
    return {act: 'fold'};
  }
  if(leg.need === 0){
    var betThresh = 0.56;
    var bluffProb = 0.08;
    if(s >= betThresh || (g.street > 0 && rng() < bluffProb)){
      var frac = s >= 0.8 ? 0.7 : 0.45;
      var desired = me.bet + Math.max(20, Math.floor(potTotal * frac));
      return {act: 'raise', to: clampRaise(desired)};
    }
    return {act: 'check'};
  }
  var callThresh = 0.55;
  if(s >= 0.85){
    var rdes = g.currentBet + Math.max(20, Math.floor(potTotal * 0.75));
    return {act: 'raise', to: clampRaise(rdes)};
  }
  if(s >= callThresh) return {act: 'call'};
  return {act: 'fold'};
}
function el(id){ return document.getElementById(id); }
var G = null, mode = 'pvc', view = 'play', viewPlayer = 0, cpuThinking = false, statusMsg = '', curLeg = null;
function cardHTML(c, faceDown){
  if(faceDown) return '<div class="pcard back"></div>';
  var cls = (c.s === 'h' || c.s === 'd') ? 'pcard red' : 'pcard';
  var sym = SUIT_SYM[c.s], rk = rankName(c.r);
  return '<div class="' + cls + '"><span class="corner-tl">' + rk + '<br><span class="cs">' + sym + '</span></span><span class="s">' + sym + '</span><span class="corner-br">' + rk + '<br><span class="cs">' + sym + '</span></span></div>';
}
function chipHTML(amount){
  if(!amount || amount <= 0) return '';
  return '<span class="chipstack"><span class="chip c-white"></span><span class="chip c-red"></span><span class="chip c-blue"></span></span>';
}


var ROOM = (typeof window !== 'undefined' && window.TEXAS_HOLDEM_ROOM) ? window.TEXAS_HOLDEM_ROOM : null;
var myIndex = ROOM ? ROOM.myIndex : 0;
var myId = ROOM ? ROOM.me : '';
var foeName = ROOM ? (ROOM.foeName || 'Opponent') : 'Opponent';
var hostId = ROOM ? ROOM.hostId : '';
function postToNative(obj){
  try{
    if (typeof window !== 'undefined' && window.ReactNativeWebView && window.ReactNativeWebView.postMessage){
      window.ReactNativeWebView.postMessage(typeof obj === 'string' ? obj : JSON.stringify(obj));
    } else if (typeof window !== 'undefined' && window.parent && window.parent.postMessage){
      window.parent.postMessage(typeof obj === 'string' ? obj : JSON.stringify(obj), '*');
    }
  }catch(e){}
}
function escHtml(s){
  s = String(s);
  return s.split('&').join('&amp;').split('<').join('&lt;').split('>').join('&gt;');
}
function pvpActorName(idx){ return idx === myIndex ? 'You' : foeName; }
function renderChat(msgs){
  if (typeof document === 'undefined') return;
  var box = document.getElementById('chatLog');
  if (!box) return;
  var html = '';
  for (var i = 0; i < msgs.length; i++){
    var m = msgs[i];
    var who = (m.sender_id === myId) ? 'You' : (m.sender_name || foeName);
    html += '<div><b>' + escHtml(who) + ':</b> ' + escHtml(m.text || '') + '</div>';
  }
  box.innerHTML = html;
}
function updateBetButton(){
  if (!G || !curLeg) return;
  if (typeof document === 'undefined') return;
  var v = parseInt(el('betSlider').value, 10);
  el('betAmount').textContent = v;
  var label = (curLeg.need === 0 && G.currentBet === 0) ? 'BET ' : 'RAISE TO ';
  el('btnBet').textContent = label + v;
}
function renderPvp(){
  if (typeof document === 'undefined') return;
  if (!G){
    el('turnText').textContent = 'Waiting for room...';
    el('statusText').textContent = ROOM ? 'Connecting to room ' + ROOM.code + '...' : 'Open this game from the rooms lobby.';
    el('actions').style.display = 'none';
    el('handBox').style.display = 'none';
    return;
  }
  var bottom = myIndex, top = 1 - myIndex;
  var bp = G.p[bottom], tp = G.p[top];
  var potTotal = G.pot + G.p[0].bet + G.p[1].bet;
  el('potText').innerHTML = chipHTML(potTotal) + potTotal;
  el('oppName').textContent = pvpActorName(top);
  el('oppStack').textContent = tp.stack;
  el('oppBet').innerHTML = tp.bet > 0 ? chipHTML(tp.bet) + tp.bet : '0';
  el('oppDealer').innerHTML = '';
  el('myName').textContent = pvpActorName(bottom);
  el('myStack').textContent = bp.stack;
  el('myBet').innerHTML = bp.bet > 0 ? chipHTML(bp.bet) + bp.bet : '0';
  el('myDealer').innerHTML = '';
  var commHtml = '';
  for (var i = 0; i < 5; i++){ if (i < G.comm.length) commHtml += cardHTML(G.comm[i], false); else commHtml += '<div class="slot"></div>'; }
  el('commCards').innerHTML = commHtml;
  var bottomFaceDown = false;
  var topFaceDown = !G.showdown;
  el('myCards').innerHTML = bp.hole.map(function(c){ return cardHTML(c, bottomFaceDown); }).join('');
  el('oppCards').innerHTML = tp.hole.map(function(c){ return cardHTML(c, topFaceDown); }).join('');
  if (G.button === bottom) el('myCards').innerHTML += '<span class="dealer-chip">D</span>';
  else if (G.button === top) el('oppCards').innerHTML += '<span class="dealer-chip">D</span>';
  el('burnPile').innerHTML = (G.burned && G.burned.length > 0) ? '<span class="pcard back mini"></span> Burn &times;' + G.burned.length : '';
  el('myHand').textContent = G.showdown ? (G.handNames[bottom] || '') : '';
  el('oppHand').textContent = G.showdown ? (G.handNames[top] || '') : '';
  if (G.handOver){
    el('turnText').textContent = 'Hand over';
    if (G.showdownPending){
      el('statusText').textContent = 'Showdown — revealing cards...';
    } else {
      el('statusText').textContent = statusMsg;
    }
    el('actions').style.display = 'none';
    el('handBox').style.display = 'block';
    var res = '';
    if (G.showdownPending){
      res = 'Showdown — waiting for the reveal...';
    } else if (G.tie){
      res = 'Split pot! ' + G.winAmount + ' chips split.';
    } else if (G.winner >= 0){
      res = pvpActorName(G.winner) + ' wins ' + G.winAmount + (G.showdown ? ' with ' + G.handNames[G.winner] : ' (opponent folded)') + '.';
    } else {
      res = 'Hand over.';
    }
    if (G.sessionOver) res += ' ' + pvpActorName(G.sessionWinner) + ' wins the session!';
    el('handResult').textContent = res;
    el('btnNextHand').style.display = (G.sessionOver || (G.showdownPending && !G.awarded)) ? 'none' : '';
    el('btnPlayAgain').style.display = G.sessionOver ? '' : 'none';
    return;
  }
  el('handBox').style.display = 'none';
  el('turnText').textContent = pvpActorName(G.toAct) + "'s turn";
  el('statusText').textContent = statusMsg;
  if (G.toAct !== myIndex){
    el('actions').style.display = 'none';
    return;
  }
  el('actions').style.display = 'flex';
  var leg = pgLegal(G, G.toAct);
  curLeg = leg;
  el('btnCheck').style.display = leg.canCheck ? '' : 'none';
  el('btnCall').style.display = leg.canCall ? '' : 'none';
  if (leg.canCall) el('btnCall').textContent = 'CALL ' + leg.callAmount;
  el('betBox').style.display = leg.canRaise ? 'flex' : 'none';
  el('btnAllIn').style.display = leg.canRaise ? '' : 'none';
  var sl = el('betSlider');
  sl.min = Math.min(leg.minTo, leg.maxTo);
  sl.max = leg.maxTo;
  var cur = parseInt(sl.value, 10);
  if (isNaN(cur) || cur < parseInt(sl.min, 10) || cur > leg.maxTo) sl.value = leg.minTo <= leg.maxTo ? leg.minTo : leg.maxTo;
  updateBetButton();
}
function computeAward(g){
  if (g.awarded) return g.winner;
  if (!g.p || g.p.length < 2 || !g.comm || g.comm.length < 5) return -2;
  if (!g.p[0].hole || g.p[0].hole.length !== 2 || !g.p[1].hole || g.p[1].hole.length !== 2) return -2;
  if (g.p[0].hole[0].hidden || g.p[1].hole[0].hidden) return -2;
  var ev0 = eval7(g.p[0].hole.concat(g.comm));
  var ev1 = eval7(g.p[1].hole.concat(g.comm));
  g.handNames = [ev0.name, ev1.name];
  var cmp = cmpEval(ev0, ev1);
  var pot = g.pot + g.p[0].bet + g.p[1].bet;
  g.winAmount = pot;
  if (cmp > 0){ g.winner = 0; g.tie = false; g.p[0].stack += pot; }
  else if (cmp < 0){ g.winner = 1; g.tie = false; g.p[1].stack += pot; }
  else {
    g.tie = true; g.winner = -1;
    var half = Math.floor(pot / 2), odd = pot % 2;
    g.p[0].stack += half + ((odd === 1 && g.button === 0) ? 1 : 0);
    g.p[1].stack += half + ((odd === 1 && g.button === 1) ? 1 : 0);
  }
  g.p[0].bet = 0; g.p[1].bet = 0; g.pot = 0; g.currentBet = 0;
  g.awarded = true;
  if (g.p[0].stack === 0 && g.p[1].stack > 0){ g.sessionOver = true; g.sessionWinner = 1; }
  else if (g.p[1].stack === 0 && g.p[0].stack > 0){ g.sessionOver = true; g.sessionWinner = 0; }
  return g.winner;
}
function winnerPlayerId(g){
  if (!ROOM) return '';
  if (g.tie) return '';
  if (g.winner === 0) return hostId;
  if (g.winner === 1) return (ROOM.foe || '');
  return '';
}
function doPvpAction(act, amt){
  if (!G || G.handOver || G.toAct !== myIndex) return;
  var prev = G.toAct;
  var legBefore = pgLegal(G, prev);
  var opp = G.p[1 - prev];
  var me = G.p[prev];
  var completesStreet = false;
  if (act === 'check' && opp.acted) completesStreet = true;
  if (act === 'call' && (opp.acted || legBefore.callAmount >= me.stack)) completesStreet = true;
  var txt = '';
  var n = pvpActorName(prev);
  if (act === 'fold') txt = n + ' folds';
  else if (act === 'check') txt = n + ' checks';
  else if (act === 'call') txt = n + ' calls ' + legBefore.callAmount;
  else if (act === 'raise') txt = n + ((legBefore.need === 0 && G.currentBet === 0) ? ' bets ' : ' raises to ') + amt;
  if (completesStreet){
    var _sd = pgShowdown;
    pgShowdown = function(g2){ g2.street = 4; g2.showdown = true; g2.handOver = true; g2.showdownPending = true; };
    pgAct(G, act, amt);
    pgShowdown = _sd;
    if (txt) statusMsg = txt;
    if (G.showdownPending){
      postToNative({type: 'texas-holdem-state', state: G, status: 'finished'});
    } else {
      postToNative({type: 'texas-holdem-state', state: G});
    }
    renderPvp();
    return;
  }
  pgAct(G, act, amt);
  if (txt) statusMsg = txt;
  if (G.handOver){
    postToNative({type: 'texas-holdem-state', state: G, status: 'finished'});
  } else {
    postToNative({type: 'texas-holdem-state', state: G});
  }
  renderPvp();
}
function doPvpAllIn(){
  if (!G || G.handOver || G.toAct !== myIndex) return;
  var leg = pgLegal(G, G.toAct);
  if (!leg.canRaise){ if (leg.canCall) doPvpAction('call'); return; }
  if (leg.need > 0 && leg.maxTo <= G.currentBet) doPvpAction('call');
  else doPvpAction('raise', leg.maxTo);
}
function nextHandPvp(){
  if (!G || G.sessionOver) return;
  if (G.showdownPending && !G.awarded) return;
  pgNewHand(G);
  statusMsg = 'New hand. Blinds 10 / 20.';
  postToNative({type: 'texas-holdem-state', state: G, status: 'playing', new_hand: true});
  renderPvp();
}
function playAgainPvp(){
  if (!G) return;
  pgResetSession(G);
  pgNewHand(G);
  statusMsg = 'Fresh stacks of 1000. Blinds 10 / 20.';
  postToNative({type: 'texas-holdem-state', state: G, status: 'playing', new_hand: true});
  renderPvp();
}
function applyRoom(room){
  if (!room) return;
  if (room.chat) renderChat(room.chat);
  var st = room.state;
  var empty = !st || (typeof st === 'object' && Object.keys(st).length === 0);
  if (empty){
    if (myIndex === 0){
      G = newPokerGame();
      pgNewHand(G);
      statusMsg = 'You dealt the first hand. Blinds 10 / 20.';
      postToNative({type: 'texas-holdem-state', state: G, status: 'playing', new_hand: true});
      renderPvp();
    } else {
      G = null;
      if (typeof document !== 'undefined'){
        el('turnText').textContent = 'Waiting for host to deal...';
        el('statusText').textContent = 'The host opens the game to deal the first hand.';
        el('actions').style.display = 'none';
        el('handBox').style.display = 'none';
      }
    }
    return;
  }
  G = st;
  if (room.status === 'finished' && G.showdown && !G.awarded){
    var w = computeAward(G);
    if (w !== -2){
      statusMsg = 'Showdown revealed.';
      postToNative({type: 'texas-holdem-state', state: G, status: 'finished', winner: winnerPlayerId(G)});
    }
  }
  renderPvp();
}
function buildPvp(){
  if (typeof document === 'undefined') return;
  el('btnFold').onclick = function(){ doPvpAction('fold'); };
  el('btnCheck').onclick = function(){ doPvpAction('check'); };
  el('btnCall').onclick = function(){ doPvpAction('call'); };
  el('btnBet').onclick = function(){ doPvpAction('raise', parseInt(el('betSlider').value, 10)); };
  el('btnAllIn').onclick = function(){ doPvpAllIn(); };
  el('betSlider').oninput = function(){ updateBetButton(); };
  el('btnNextHand').onclick = function(){ nextHandPvp(); };
  el('btnPlayAgain').onclick = function(){ playAgainPvp(); };
  el('btnLeave').onclick = function(){ postToNative({type: 'texas-holdem-leave'}); };
  el('btnClose').onclick = function(){ postToNative('close'); };
  el('btnClose2').onclick = function(){ postToNative('close'); };
  el('btnChatSend').onclick = function(){
    var v = el('chatInput').value;
    if (!v || !v.trim()) return;
    el('chatInput').value = '';
    postToNative({type: 'texas-holdem-chat', text: v.trim()});
  };
  if (typeof window !== 'undefined' && window.addEventListener){
    window.addEventListener('texas-holdem-room', function(ev){ applyRoom(ev.detail); });
  }
  renderPvp();
}
if (typeof document !== 'undefined' && document.getElementById){ buildPvp(); }

</script>
</body>
</html>
`;
