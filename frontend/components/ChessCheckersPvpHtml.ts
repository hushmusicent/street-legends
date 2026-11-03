export const CHESS_CHECKERS_PVP_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chess &amp; Checkers - Player vs Player</title>
<style>
body{background:radial-gradient(ellipse at center,#262626 0%,#111 55%,#000 100%);color:#fff;font-family:Arial,Helvetica,sans-serif;text-align:center;margin:0;padding:12px}
h1{margin:8px 0 4px;font-size:28px;letter-spacing:1px}
.sub{color:#ccc;font-size:14px;margin-bottom:14px}
.card{background:#1c1c1c;border:1px solid #333;border-radius:12px;padding:14px;max-width:520px;margin:0 auto 12px;text-align:left}
.card h3{margin:6px 0 8px;font-size:15px;color:#ffd54f}
.row{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:6px}
.btn{background:#2e7d32;color:#fff;border:none;border-radius:8px;padding:11px 16px;font-weight:800;cursor:pointer;font-size:15px}
.btn.blue{background:#1e88e5}.btn.grey{background:#666}.btn.red{background:#b71c1c}
.btn.sel{outline:3px solid #ffd54f;outline-offset:1px}
.btn:disabled{opacity:.45}
.lvlgrid{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}
.lvlgrid .btn{padding:10px 0;font-size:15px}
#levelName{color:#ffd54f;font-weight:800;margin-top:6px}
#levelLegend{color:#aaa;font-size:12px;margin-top:4px}
#game{display:none;max-width:520px;margin:0 auto}
#turnText{font-weight:800;font-size:18px;margin:8px 0 2px}
#statusText{color:#ffd54f;font-weight:800;min-height:22px;margin-bottom:8px}
.board{display:grid;grid-template-columns:repeat(8,1fr);width:min(92vw,480px);aspect-ratio:1;margin:0 auto;border:8px solid #4a2c12;border-radius:8px;overflow:hidden;box-shadow:0 14px 34px rgba(0,0,0,.85),0 4px 10px rgba(0,0,0,.6),inset 0 2px 0 rgba(255,255,255,.18),inset 0 -2px 0 rgba(0,0,0,.5)}
.sq{aspect-ratio:1;display:flex;align-items:center;justify-content:center;position:relative;cursor:pointer;user-select:none}
.sq.light{background:linear-gradient(145deg,#F5D7A8 0%,#E8C89A 45%,#D9B57F 100%);box-shadow:inset 0 1px 0 rgba(255,255,255,.65),inset 0 -1px 0 rgba(0,0,0,.18)}.sq.dark{background:linear-gradient(145deg,#A06A35 0%,#8B5A2B 45%,#6E451F 100%);box-shadow:inset 0 1px 0 rgba(255,255,255,.2),inset 0 -1px 0 rgba(0,0,0,.4)}
.sq.sel{box-shadow:inset 0 0 0 4px #FFD54F,inset 0 1px 0 rgba(255,255,255,.5),inset 0 0 18px rgba(255,213,79,.55)}
.sq .pc{font-size:clamp(28px,8vw,44px);line-height:1}
.sq .wp{color:#fff;text-shadow:0 3px 3px rgba(0,0,0,.65),0 1px 0 rgba(0,0,0,.8),-1px -1px 0 #000,1px -1px 0 #000,-1px 1px 0 #000,1px 1px 0 #000}
.sq .bp{color:#111;text-shadow:0 3px 3px rgba(0,0,0,.7),0 1px 0 rgba(0,0,0,.9),0 0 2px rgba(255,255,255,.35)}
.sq.dot::after{content:"";width:26%;height:26%;background:radial-gradient(circle at 35% 30%,rgba(255,255,255,.4),rgba(0,0,0,.38) 60%);border-radius:50%;position:absolute;box-shadow:0 2px 4px rgba(0,0,0,.5)}
.sq.cap{box-shadow:inset 0 0 0 4px #e53935,inset 0 1px 0 rgba(255,255,255,.25),inset 0 0 16px rgba(229,57,53,.55)}
.disc{width:76%;height:76%;border-radius:50%;display:flex;align-items:center;justify-content:center;font-weight:900;font-size:clamp(16px,4.5vw,22px)}
.disc.red{background:radial-gradient(circle at 32% 28%,#FF6B5E 0%,#E53935 35%,#D32F2F 60%,#8E0000 100%);border:2px solid #7f0000;color:#fff;box-shadow:0 4px 6px rgba(0,0,0,.6),inset 0 2px 3px rgba(255,255,255,.45),inset 0 -3px 5px rgba(0,0,0,.45)}
.disc.black{background:radial-gradient(circle at 32% 28%,#5A5A5A 0%,#333 35%,#212121 60%,#000 100%);border:2px solid #000;color:#fff;box-shadow:0 4px 6px rgba(0,0,0,.6),inset 0 2px 3px rgba(255,255,255,.25),inset 0 -3px 5px rgba(0,0,0,.6)}
.disc.king{border:3px solid #FFD700;box-shadow:0 4px 6px rgba(0,0,0,.6),inset 0 2px 3px rgba(255,255,255,.4),inset 0 -3px 5px rgba(0,0,0,.45),0 0 12px rgba(255,215,0,.6);text-shadow:0 1px 2px rgba(0,0,0,.7)}
.controls{display:flex;flex-wrap:wrap;gap:8px;justify-content:center;margin-top:12px}
#promoOverlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.82);align-items:center;justify-content:center;z-index:50}
#promoBox{background:#222;border:2px solid #ffd54f;border-radius:12px;padding:18px;text-align:center}
#promoBox .pbtn{font-size:44px;background:#333;color:#fff;border:2px solid #555;border-radius:10px;padding:10px 14px;margin:6px;cursor:pointer}
#promoBox .pbtn:hover{border-color:#ffd54f}
.note{color:#aaa;font-size:12px;margin-top:10px}
</style>
</head>
<body>
<div id="game" style="display:block;max-width:520px;margin:0 auto">
<h1 id="gameTitle">Chess &amp; Checkers</h1>
<div id="turnText">Waiting for opponent</div>
<div id="statusText"></div>
<div class="board" id="board"></div>
<div class="controls">
<button class="btn red" id="btnLeave">LEAVE ROOM</button>
<button class="btn grey" id="btnClose">CLOSE</button>
</div>
<div class="note" id="gameNote"></div>
<div style="max-width:520px;margin:12px auto 0;text-align:left">
<div style="color:#fff;font-weight:800;margin-bottom:6px">CHAT</div>
<div id="chatLog" style="background:#1a1a1a;border-radius:8px;padding:10px;margin-bottom:10px;height:140px;overflow-y:auto"></div>
<div style="display:flex;gap:8px">
<input id="chatInput" type="text" placeholder="Say something..." style="flex:1;background:#222;color:#fff;padding:10px;border-radius:8px;border:none">
<button class="btn blue" id="btnChat">SEND</button>
</div>
</div>
</div>
<div id="promoOverlay"><div id="promoBox">
<div style="font-weight:800;margin-bottom:10px">Choose promotion piece</div>
<div id="promoBtns"></div>
</div></div>
<script>

"use strict";
/* ============ CHESS ============ */
var CHESS_VAL = {p:100, n:320, b:330, r:500, q:900, k:0};
var PST_P = [0,0,0,0,0,0,0,0,50,50,50,50,50,50,50,50,10,10,20,30,30,20,10,10,5,5,10,25,25,10,5,5,0,0,0,20,20,0,0,0,5,-5,-10,0,0,-10,-5,5,5,10,10,-20,-20,10,10,5,0,0,0,0,0,0,0,0];
var PST_N = [-50,-40,-30,-30,-30,-30,-40,-50,-40,-20,0,0,0,0,-20,-40,-30,0,10,15,15,10,0,-30,-30,5,15,20,20,15,5,-30,-30,0,15,20,20,15,0,-30,-30,5,10,15,15,10,5,-30,-40,-20,0,5,5,0,-20,-40,-50,-40,-30,-30,-30,-30,-40,-50];
var PST_B = [-20,-10,-10,-10,-10,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,10,10,5,0,-10,-10,5,5,10,10,5,5,-10,-10,0,10,10,10,10,0,-10,-10,10,10,10,10,10,10,-10,-10,5,0,0,0,0,5,-10,-20,-10,-10,-10,-10,-10,-10,-20];
var PST_R = [0,0,0,0,0,0,0,0,5,10,10,10,10,10,10,5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,-5,0,0,0,0,0,0,-5,0,0,0,5,5,0,0,0];
var PST_Q = [-20,-10,-10,-5,-5,-10,-10,-20,-10,0,0,0,0,0,0,-10,-10,0,5,5,5,5,0,-10,-5,0,5,5,5,5,0,-5,0,0,5,5,5,5,0,-5,-10,5,5,5,5,5,0,-10,-10,0,5,0,0,0,0,-10,-20,-10,-10,-5,-5,-10,-10,-20];
var PST_K = [-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-30,-40,-40,-50,-50,-40,-40,-30,-20,-30,-30,-40,-40,-30,-30,-20,-10,-20,-20,-20,-20,-20,-20,-10,20,20,0,0,0,0,20,20,20,30,10,0,0,10,30,20];
var PST = {p:PST_P, n:PST_N, b:PST_B, r:PST_R, q:PST_Q, k:PST_K};
function chessInitial(){
  var b = [];
  for (var r = 0; r < 8; r++){ var row = []; for (var c = 0; c < 8; c++) row.push(null); b.push(row); }
  var back = ["r","n","b","q","k","b","n","r"];
  for (var c = 0; c < 8; c++){ b[0][c] = {t:back[c], c:"b"}; b[1][c] = {t:"p", c:"b"}; b[6][c] = {t:"p", c:"w"}; b[7][c] = {t:back[c], c:"w"}; }
  return {board:b, turn:"w", castling:{wK:true, wQ:true, bK:true, bQ:true}, ep:null};
}
function chessCopy(s){
  var b = s.board.map(function(row){ return row.map(function(p){ return p ? {t:p.t, c:p.c} : null; }); });
  return {board:b, turn:s.turn, castling:{wK:s.castling.wK, wQ:s.castling.wQ, bK:s.castling.bK, bQ:s.castling.bQ}, ep: s.ep ? [s.ep[0], s.ep[1]] : null};
}
function chessKingPos(board, color){
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){ var p = board[r][c]; if (p && p.t === "k" && p.c === color) return [r, c]; }
  return null;
}
function chessAttacked(board, r, c, by){
  var i, j, p;
  // pawns: white pawns attack from one row below (r+1), black from one row above (r-1)
  var pr = (by === "w") ? r + 1 : r - 1;
  var dirs = [[pr, c - 1], [pr, c + 1]];
  for (i = 0; i < 2; i++){ var rr = dirs[i][0], cc = dirs[i][1]; if (rr >= 0 && rr < 8 && cc >= 0 && cc < 8){ p = board[rr][cc]; if (p && p.c === by && p.t === "p") return true; } }
  var kn = [[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]];
  for (i = 0; i < 8; i++){ var nr = r + kn[i][0], nc = c + kn[i][1]; if (nr >= 0 && nr < 8 && nc >= 0 && nc < 8){ p = board[nr][nc]; if (p && p.c === by && p.t === "n") return true; } }
  for (i = -1; i <= 1; i++) for (j = -1; j <= 1; j++){
    if (i === 0 && j === 0) continue;
    var kr = r + i, kc = c + j;
    if (kr >= 0 && kr < 8 && kc >= 0 && kc < 8){ p = board[kr][kc]; if (p && p.c === by && p.t === "k") return true; }
  }
  var orth = [[-1,0],[1,0],[0,-1],[0,1]];
  var diag = [[-1,-1],[-1,1],[1,-1],[1,1]];
  for (i = 0; i < 4; i++){
    var dr = orth[i][0], dc = orth[i][1], rr2 = r + dr, cc2 = c + dc;
    while (rr2 >= 0 && rr2 < 8 && cc2 >= 0 && cc2 < 8){
      p = board[rr2][cc2];
      if (p){ if (p.c === by && (p.t === "r" || p.t === "q")) return true; break; }
      rr2 += dr; cc2 += dc;
    }
  }
  for (i = 0; i < 4; i++){
    var dr2 = diag[i][0], dc2 = diag[i][1], rr3 = r + dr2, cc3 = c + dc2;
    while (rr3 >= 0 && rr3 < 8 && cc3 >= 0 && cc3 < 8){
      p = board[rr3][cc3];
      if (p){ if (p.c === by && (p.t === "b" || p.t === "q")) return true; break; }
      rr3 += dr2; cc3 += dc2;
    }
  }
  return false;
}
function chessInCheck(s, color){
  var kp = chessKingPos(s.board, color);
  if (!kp) return false;
  return chessAttacked(s.board, kp[0], kp[1], color === "w" ? "b" : "w");
}
function chessPseudo(s){
  var moves = [], board = s.board, turn = s.turn;
  var opp = turn === "w" ? "b" : "w";
  function push(fr, fc, tr, tc, extra){
    if (tr < 0 || tr > 7 || tc < 0 || tc > 7) return;
    var tgt = board[tr][tc];
    if (tgt && tgt.c === turn) return;
    var m = {fr:fr, fc:fc, tr:tr, tc:tc, piece:board[fr][fc].t, captured: tgt ? tgt.t : null, promotion:null, ep:false, castle:null};
    if (extra) for (var k in extra) m[k] = extra[k];
    moves.push(m);
  }
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){
    var p = board[r][c];
    if (!p || p.c !== turn) continue;
    if (p.t === "p"){
      var dir = turn === "w" ? -1 : 1;
      var startRow = turn === "w" ? 6 : 1;
      var lastRow = turn === "w" ? 0 : 7;
      var one = r + dir;
      if (one >= 0 && one < 8 && !board[one][c]){
        if (one === lastRow){ ["q","r","b","n"].forEach(function(pr){ push(r, c, one, c, {promotion:pr}); }); }
        else {
          push(r, c, one, c);
          var two = r + 2 * dir;
          if (r === startRow && !board[two][c]) push(r, c, two, c, {double:true});
        }
      }
      var caps = [[dir, -1], [dir, 1]];
      for (var ci = 0; ci < 2; ci++){
        var tr = r + caps[ci][0], tc = c + caps[ci][1];
        if (tr < 0 || tr > 7 || tc < 0 || tc > 7) continue;
        var tgt2 = board[tr][tc];
        if (tgt2 && tgt2.c === opp){
          if (tr === lastRow){ ["q","r","b","n"].forEach(function(pr){ push(r, c, tr, tc, {promotion:pr}); }); }
          else push(r, c, tr, tc);
        } else if (!tgt2 && s.ep && s.ep[0] === tr && s.ep[1] === tc){
          push(r, c, tr, tc, {ep:true, captured:"p"});
        }
      }
    } else if (p.t === "n" || p.t === "k"){
      var offs = p.t === "n" ? [[-2,-1],[-2,1],[-1,-2],[-1,2],[1,-2],[1,2],[2,-1],[2,1]] : [[-1,-1],[-1,0],[-1,1],[0,-1],[0,1],[1,-1],[1,0],[1,1]];
      for (var oi = 0; oi < offs.length; oi++) push(r, c, r + offs[oi][0], c + offs[oi][1]);
      if (p.t === "k"){
        var cr = turn === "w" ? 7 : 0;
        var rightsK = turn === "w" ? s.castling.wK : s.castling.bK;
        var rightsQ = turn === "w" ? s.castling.wQ : s.castling.bQ;
        if (r === cr && c === 4 && !chessInCheck(s, turn)){
          if (rightsK && !board[cr][5] && !board[cr][6] && board[cr][7] && board[cr][7].t === "r" && board[cr][7].c === turn
              && !chessAttacked(board, cr, 5, opp) && !chessAttacked(board, cr, 6, opp))
            moves.push({fr:r, fc:c, tr:cr, tc:6, piece:"k", captured:null, promotion:null, ep:false, castle:"K"});
          if (rightsQ && !board[cr][1] && !board[cr][2] && !board[cr][3] && board[cr][0] && board[cr][0].t === "r" && board[cr][0].c === turn
              && !chessAttacked(board, cr, 3, opp) && !chessAttacked(board, cr, 2, opp))
            moves.push({fr:r, fc:c, tr:cr, tc:2, piece:"k", captured:null, promotion:null, ep:false, castle:"Q"});
        }
      }
    } else {
      var dirs2 = [];
      if (p.t === "b" || p.t === "q") dirs2 = dirs2.concat([[-1,-1],[-1,1],[1,-1],[1,1]]);
      if (p.t === "r" || p.t === "q") dirs2 = dirs2.concat([[-1,0],[1,0],[0,-1],[0,1]]);
      for (var di = 0; di < dirs2.length; di++){
        var rr = r + dirs2[di][0], cc = c + dirs2[di][1];
        while (rr >= 0 && rr < 8 && cc >= 0 && cc < 8){
          var tp = board[rr][cc];
          if (!tp) push(r, c, rr, cc);
          else { if (tp.c === opp) push(r, c, rr, cc); break; }
          rr += dirs2[di][0]; cc += dirs2[di][1];
        }
      }
    }
  }
  return moves;
}
function chessApply(s, m){
  var ns = chessCopy(s);
  var b = ns.board;
  var pc = b[m.fr][m.fc];
  if (m.ep) b[m.fr][m.tc] = null;
  b[m.fr][m.fc] = null;
  b[m.tr][m.tc] = {t: m.promotion || pc.t, c: pc.c};
  if (m.castle){
    var cr = pc.c === "w" ? 7 : 0;
    if (m.castle === "K"){ b[cr][5] = b[cr][7]; b[cr][7] = null; }
    else { b[cr][3] = b[cr][0]; b[cr][0] = null; }
  }
  // castling rights
  if (pc.t === "k"){ if (pc.c === "w"){ ns.castling.wK = false; ns.castling.wQ = false; } else { ns.castling.bK = false; ns.castling.bQ = false; } }
  if (pc.t === "r"){
    if (pc.c === "w" && m.fr === 7 && m.fc === 0) ns.castling.wQ = false;
    if (pc.c === "w" && m.fr === 7 && m.fc === 7) ns.castling.wK = false;
    if (pc.c === "b" && m.fr === 0 && m.fc === 0) ns.castling.bQ = false;
    if (pc.c === "b" && m.fr === 0 && m.fc === 7) ns.castling.bK = false;
  }
  if (m.captured === "r"){
    if (m.tr === 7 && m.tc === 0) ns.castling.wQ = false;
    if (m.tr === 7 && m.tc === 7) ns.castling.wK = false;
    if (m.tr === 0 && m.tc === 0) ns.castling.bQ = false;
    if (m.tr === 0 && m.tc === 7) ns.castling.bK = false;
  }
  if (m.double) ns.ep = [(m.fr + m.tr) / 2, m.fc]; else ns.ep = null;
  ns.turn = s.turn === "w" ? "b" : "w";
  return ns;
}
function chessLegal(s){
  var pseudo = chessPseudo(s);
  var out = [];
  for (var i = 0; i < pseudo.length; i++){
    var ns = chessApply(s, pseudo[i]);
    if (!chessInCheck(ns, s.turn)) out.push(pseudo[i]);
  }
  return out;
}
function chessInsufficient(board){
  var others = [];
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){ var p = board[r][c]; if (p && p.t !== "k") others.push(p); }
  if (others.length === 0) return true;
  if (others.length === 1 && (others[0].t === "b" || others[0].t === "n")) return true;
  return false;
}
function chessStatus(s){
  var legal = chessLegal(s);
  var chk = chessInCheck(s, s.turn);
  if (legal.length === 0){
    if (chk) return {over:true, winner: s.turn === "w" ? "b" : "w", kind:"checkmate"};
    return {over:true, winner:null, kind:"stalemate"};
  }
  if (chessInsufficient(s.board)) return {over:true, winner:null, kind:"insufficient"};
  if (chk) return {over:false, winner:null, kind:"check"};
  return {over:false, winner:null, kind:"ok"};
}
function chessEval(s){
  var sc = 0;
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){
    var p = s.board[r][c];
    if (!p) continue;
    var idx = r * 8 + c;
    var pst = PST[p.t][p.c === "w" ? idx : (7 - r) * 8 + c];
    var v = CHESS_VAL[p.t] + pst;
    sc += (p.c === "w" ? v : -v);
  }
  return sc;
}
function chessSearch(s, depth, alpha, beta, ply){
  var st = chessStatus(s);
  if (st.over){
    if (st.kind === "checkmate") return (s.turn === "w" ? -100000 : 100000) + (s.turn === "w" ? ply : -ply);
    return 0;
  }
  if (depth === 0) return chessEval(s);
  var moves = chessLegal(s);
  // captures-first ordering
  moves.sort(function(a, b){
    var va = a.captured ? CHESS_VAL[a.captured] : 0, vb = b.captured ? CHESS_VAL[b.captured] : 0;
    return vb - va;
  });
  if (s.turn === "w"){
    var best = -Infinity;
    for (var i = 0; i < moves.length; i++){
      var sc = chessSearch(chessApply(s, moves[i]), depth - 1, alpha, beta, ply + 1);
      if (sc > best) best = sc;
      if (best > alpha) alpha = best;
      if (beta <= alpha) break;
    }
    return best;
  } else {
    var best2 = Infinity;
    for (var j = 0; j < moves.length; j++){
      var sc2 = chessSearch(chessApply(s, moves[j]), depth - 1, alpha, beta, ply + 1);
      if (sc2 < best2) best2 = sc2;
      if (best2 < beta) beta = best2;
      if (beta <= alpha) break;
    }
    return best2;
  }
}
function chessDepthFor(level){
  if (level <= 3) return 1;
  if (level <= 6) return 2;
  return 3;
}
function chessCpuMove(s, level){
  var legal = chessLegal(s);
  if (!legal.length) return null;
  if (legal.length === 1) return legal[0];
  // high randomness at low levels: sometimes pick at random
  var randP = (10 - level) * 0.05;
  if (Math.random() < randP) return legal[Math.floor(Math.random() * legal.length)];
  var depth = chessDepthFor(level);
  var noiseScale = (10 - level) * 10;
  var scored = [];
  for (var i = 0; i < legal.length; i++){
    var ns = chessApply(s, legal[i]);
    var sc = chessSearch(ns, depth - 1, -Infinity, Infinity, 1);
    var noise = noiseScale ? (Math.random() * 2 - 1) * noiseScale : 0;
    scored.push({m:legal[i], sc: sc + noise});
  }
  scored.sort(function(a, b){ return s.turn === "w" ? b.sc - a.sc : a.sc - b.sc; });
  return scored[0].m;
}
var Chess = {
  initial: chessInitial, copy: chessCopy, legal: chessLegal, apply: chessApply,
  status: chessStatus, inCheck: chessInCheck, eval: chessEval, cpu: chessCpuMove,
  glyph: {w:{k:"\u2654", q:"\u2655", r:"\u2656", b:"\u2657", n:"\u2658", p:"\u2659"}, b:{k:"\u265A", q:"\u265B", r:"\u265C", b:"\u265D", n:"\u265E", p:"\u265F"}}
};
/* ============ CHECKERS ============ */
function checkersInitial(){
  var b = [];
  for (var r = 0; r < 8; r++){ var row = []; for (var c = 0; c < 8; c++) row.push(null); b.push(row); }
  for (var rr = 0; rr < 8; rr++) for (var cc = 0; cc < 8; cc++){
    if ((rr + cc) % 2 !== 1) continue;
    if (rr <= 2) b[rr][cc] = {c:"b", k:false};
    if (rr >= 5) b[rr][cc] = {c:"r", k:false};
  }
  return {board:b, turn:"r"};
}
function checkersCopy(s){
  var b = s.board.map(function(row){ return row.map(function(p){ return p ? {c:p.c, k:p.k} : null; }); });
  return {board:b, turn:s.turn};
}
function checkersDirs(piece, color){
  if (piece.k) return [[-1,-1],[-1,1],[1,-1],[1,1]];
  if (color === "r") return [[-1,-1],[-1,1]];
  return [[1,-1],[1,1]];
}
function checkersJumpSeqs(board, r, c, piece, color){
  var results = [];
  var dirs = checkersDirs(piece, color);
  for (var d = 0; d < dirs.length; d++){
    var dr = dirs[d][0], dc = dirs[d][1];
    var mr = r + dr, mc = c + dc, lr = r + 2 * dr, lc = c + 2 * dc;
    if (mr < 0 || mr > 7 || mc < 0 || mc > 7 || lr < 0 || lr > 7 || lc < 0 || lc > 7) continue;
    var mid = board[mr][mc];
    if (!mid || mid.c === color) continue;
    if (board[lr][lc]) continue;
    var promotes = !piece.k && ((color === "r" && lr === 0) || (color === "b" && lr === 7));
    var step = {to:[lr, lc], cap:[mr, mc]};
    if (promotes){
      results.push({steps:[step], caps:[[mr, mc]], end:[lr, lc], promotes:true});
    } else {
      var nb = board.map(function(row){ return row.slice(); });
      nb[mr][mc] = null; nb[r][c] = null; nb[lr][lc] = piece;
      var cont = checkersJumpSeqs(nb, lr, lc, piece, color);
      if (cont.length){
        for (var i = 0; i < cont.length; i++){
          results.push({steps:[step].concat(cont[i].steps), caps:[[mr, mc]].concat(cont[i].caps), end:cont[i].end, promotes:cont[i].promotes});
        }
      } else {
        results.push({steps:[step], caps:[[mr, mc]], end:[lr, lc], promotes:false});
      }
    }
  }
  return results;
}
function checkersLegal(s){
  var jumps = [];
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){
    var p = s.board[r][c];
    if (!p || p.c !== s.turn) continue;
    var seqs = checkersJumpSeqs(s.board, r, c, p, s.turn);
    for (var i = 0; i < seqs.length; i++) jumps.push({fr:r, fc:c, tr:seqs[i].end[0], tc:seqs[i].end[1], steps:seqs[i].steps, caps:seqs[i].caps, promotes:seqs[i].promotes, jump:true});
  }
  if (jumps.length) return jumps;
  var moves = [];
  for (var r2 = 0; r2 < 8; r2++) for (var c2 = 0; c2 < 8; c2++){
    var p2 = s.board[r2][c2];
    if (!p2 || p2.c !== s.turn) continue;
    var dirs = checkersDirs(p2, s.turn);
    for (var d = 0; d < dirs.length; d++){
      var nr = r2 + dirs[d][0], nc = c2 + dirs[d][1];
      if (nr < 0 || nr > 7 || nc < 0 || nc > 7) continue;
      if (s.board[nr][nc]) continue;
      var prom = !p2.k && ((s.turn === "r" && nr === 0) || (s.turn === "b" && nr === 7));
      moves.push({fr:r2, fc:c2, tr:nr, tc:nc, steps:[], caps:[], promotes:prom, jump:false});
    }
  }
  return moves;
}
function checkersApply(s, m){
  var ns = checkersCopy(s);
  var pc = ns.board[m.fr][m.fc];
  ns.board[m.fr][m.fc] = null;
  for (var i = 0; i < m.caps.length; i++) ns.board[m.caps[i][0]][m.caps[i][1]] = null;
  ns.board[m.tr][m.tc] = {c:pc.c, k: pc.k || m.promotes};
  ns.turn = s.turn === "r" ? "b" : "r";
  return ns;
}
function checkersCount(board, color){
  var n = 0;
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){ var p = board[r][c]; if (p && p.c === color) n++; }
  return n;
}
function checkersStatus(s){
  // called for player to move: if they have no pieces or no moves, previous player won
  if (checkersCount(s.board, s.turn) === 0) return {over:true, winner: s.turn === "r" ? "b" : "r"};
  if (checkersLegal(s).length === 0) return {over:true, winner: s.turn === "r" ? "b" : "r"};
  return {over:false, winner:null};
}
function checkersEval(s){
  var sc = 0;
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){
    var p = s.board[r][c];
    if (!p) continue;
    var v = p.k ? 175 : 100;
    if (!p.k) v += (p.c === "r" ? (7 - r) : r) * 4;
    sc += (p.c === "r" ? v : -v);
  }
  return sc;
}
function checkersSearch(s, depth, alpha, beta){
  var st = checkersStatus(s);
  if (st.over){
    if (st.winner === "r") return 100000;
    if (st.winner === "b") return -100000;
    return 0;
  }
  if (depth === 0) return checkersEval(s);
  var moves = checkersLegal(s);
  moves.sort(function(a, b){ return b.caps.length - a.caps.length; });
  if (s.turn === "r"){
    var best = -Infinity;
    for (var i = 0; i < moves.length; i++){
      var sc = checkersSearch(checkersApply(s, moves[i]), depth - 1, alpha, beta);
      if (sc > best) best = sc;
      if (best > alpha) alpha = best;
      if (beta <= alpha) break;
    }
    return best;
  } else {
    var best2 = Infinity;
    for (var j = 0; j < moves.length; j++){
      var sc2 = checkersSearch(checkersApply(s, moves[j]), depth - 1, alpha, beta);
      if (sc2 < best2) best2 = sc2;
      if (best2 < beta) beta = best2;
      if (beta <= alpha) break;
    }
    return best2;
  }
}
function checkersDepthFor(level){ return 1 + Math.floor((level - 1) * 5 / 9); }
function checkersCpuMove(s, level){
  var legal = checkersLegal(s);
  if (!legal.length) return null;
  if (legal.length === 1) return legal[0];
  var randP = (10 - level) * 0.05;
  if (Math.random() < randP) return legal[Math.floor(Math.random() * legal.length)];
  var depth = checkersDepthFor(level);
  var noiseScale = (10 - level) * 10;
  var scored = [];
  for (var i = 0; i < legal.length; i++){
    var sc = checkersSearch(checkersApply(s, legal[i]), depth - 1, -Infinity, Infinity);
    var noise = noiseScale ? (Math.random() * 2 - 1) * noiseScale : 0;
    scored.push({m:legal[i], sc: sc + noise});
  }
  scored.sort(function(a, b){ return s.turn === "r" ? b.sc - a.sc : a.sc - b.sc; });
  return scored[0].m;
}
var Checkers = {
  initial: checkersInitial, copy: checkersCopy, legal: checkersLegal, apply: checkersApply,
  status: checkersStatus, count: checkersCount, eval: checkersEval, cpu: checkersCpuMove
};
if (typeof globalThis !== "undefined"){ globalThis.ChessGame = Chess; globalThis.CheckersGame = Checkers; globalThis.chessCpuMoveFn = chessCpuMove; globalThis.checkersCpuMoveFn = checkersCpuMove; }
function renderBoard(){
  var boardEl = document.getElementById("board");
  boardEl.innerHTML = "";
  var s = curState();
  var destMap = {};
  selMoves.forEach(function(m){ var key = m.tr + "," + m.tc; if (!destMap[key]) destMap[key] = m; });
  for (var r = 0; r < 8; r++) for (var c = 0; c < 8; c++){
    var sq = document.createElement("div");
    sq.className = "sq " + (((r + c) % 2 === 0) ? "light" : "dark");
    sq.dataset.r = r; sq.dataset.c = c;
    if (sel && sel[0] === r && sel[1] === c) sq.classList.add("sel");
    var key2 = r + "," + c;
    if (destMap[key2]){
      sq.classList.add("dot");
      var dm = destMap[key2];
      var isCap = false;
      if (curGame === "chess"){ if (dm.captured || dm.ep) isCap = true; }
      else { if (dm.caps && dm.caps.length) isCap = true; }
      if (isCap) sq.classList.add("cap");
    }
    var p = s.board[r][c];
    if (p){
      if (curGame === "chess"){
        var sp = document.createElement("span");
        sp.className = "pc " + (p.c === "w" ? "wp" : "bp");
        sp.textContent = Chess.glyph[p.c][p.t];
        sq.appendChild(sp);
      } else {
        var disc = document.createElement("div");
        disc.className = "disc " + (p.c === "r" ? "red" : "black") + (p.k ? " king" : "");
        disc.textContent = p.k ? "K" : "";
        sq.appendChild(disc);
      }
    }
    boardEl.appendChild(sq);
  }
}
function showPromo(moves, color){
  var ov = document.getElementById("promoOverlay");
  var box = document.getElementById("promoBtns");
  box.innerHTML = "";
  var opts = [["q","Q"],["r","R"],["b","B"],["n","N"]];
  opts.forEach(function(o){
    var b = document.createElement("button");
    b.className = "pbtn";
    b.textContent = Chess.glyph[color === "w" ? "w" : "b"][o[0]] + " " + o[1];
    b.onclick = function(){
      var chosen = null;
      for (var i = 0; i < moves.length; i++) if (moves[i].promotion === o[0]) chosen = moves[i];
      ov.style.display = "none";
      pendingPromo = null;
      if (chosen) applyHuman(chosen);
    };
    box.appendChild(b);
  });
  ov.style.display = "flex";
}

var PVP = (typeof window !== "undefined" && window.CHESS_CHECKERS_PVP) ? window.CHESS_CHECKERS_PVP : {};
var curGame = PVP.game || "chess";
var myColor = PVP.myColor || (curGame === "chess" ? "w" : "r");
var foeName = PVP.foeName || "Friend";
var chessState = Chess.initial();
var checkersState = Checkers.initial();
var sel = null, selMoves = [], pendingPromo = null, gameOver = false;
var roomStatus = "waiting", roomWinner = null, lastRoomJson = "";
function curState(){ return curGame === "chess" ? chessState : checkersState; }
function curLegal(){ return curGame === "chess" ? Chess.legal(chessState) : Checkers.legal(checkersState); }
function colorName(c){ if (curGame === "chess") return c === "w" ? "White" : "Black"; return c === "r" ? "Red" : "Black"; }
function updateTurn(){
  var tt = document.getElementById("turnText");
  var st = document.getElementById("statusText");
  if (gameOver){ tt.textContent = "Game over"; return; }
  if (roomStatus === "waiting"){ tt.textContent = "Waiting for your friend to join..."; return; }
  var s = curState();
  if (s.turn === myColor) tt.textContent = "Your turn (" + colorName(myColor) + ")";
  else tt.textContent = "Waiting for " + foeName + " (" + colorName(s.turn) + ")";
  if (curGame === "chess") st.textContent = Chess.inCheck(s, s.turn) ? "Check!" : "";
  else st.textContent = "";
}
function stateObj(){
  var s = curState();
  if (curGame === "chess") return {game:"chess", board:s.board, turn:s.turn, castling:s.castling, ep:s.ep, status:roomStatus, winner:roomWinner};
  return {game:"checkers", board:s.board, turn:s.turn, status:roomStatus, winner:roomWinner};
}
function postToNative(obj){
  try { if (window.ReactNativeWebView) window.ReactNativeWebView.postMessage(typeof obj === "string" ? obj : JSON.stringify(obj)); } catch (e) {}
}
function postState(){ postToNative({type:"chess-checkers-state", state: stateObj()}); }
function showPvPResult(msg){
  document.getElementById("statusText").textContent = msg;
  document.getElementById("turnText").textContent = "Game over";
}
function applyHuman(m){
  if (curGame === "chess") chessState = Chess.apply(chessState, m);
  else checkersState = Checkers.apply(checkersState, m);
  afterMovePvP();
}
function afterMovePvP(){
  sel = null; selMoves = [];
  var s = curState();
  if (curGame === "chess"){
    var st = Chess.status(s);
    if (st.over){
      gameOver = true; roomStatus = "finished";
      if (st.kind === "checkmate"){ roomWinner = st.winner; showPvPResult("Checkmate! " + colorName(st.winner) + " wins!"); }
      else if (st.kind === "stalemate"){ roomWinner = null; showPvPResult("Draw - stalemate"); }
      else { roomWinner = null; showPvPResult("Draw - insufficient material"); }
      renderBoard(); postState(); return;
    }
  } else {
    var st2 = Checkers.status(s);
    if (st2.over){
      gameOver = true; roomStatus = "finished"; roomWinner = st2.winner;
      showPvPResult(colorName(st2.winner) + " wins!");
      renderBoard(); postState(); return;
    }
  }
  renderBoard(); updateTurn(); postState();
}
function onSquarePvP(r, c){
  if (gameOver || pendingPromo) return;
  if (roomStatus !== "playing") return;
  var s = curState();
  if (s.turn !== myColor) return;
  if (sel){
    var cands = selMoves.filter(function(m){ return m.tr === r && m.tc === c; });
    if (cands.length){
      if (curGame === "chess" && cands[0].promotion){
        pendingPromo = {moves:cands, color:s.turn};
        showPromo(cands, s.turn);
        return;
      }
      applyHuman(cands[0]);
      return;
    }
  }
  var p = s.board[r][c];
  if (p && p.c === s.turn){
    sel = [r, c];
    selMoves = curLegal().filter(function(m){ return m.fr === r && m.fc === c; });
  } else { sel = null; selMoves = []; }
  renderBoard();
}
function renderChat(chat){
  var log = document.getElementById("chatLog"); if (!log) return;
  log.innerHTML = "";
  chat.forEach(function(m){
    var d = document.createElement("div");
    d.style.cssText = "color:" + (m.sender_id === (PVP.me || "") ? "#f39c12" : "#ffffff") + ";font-size:13px;margin-bottom:4px";
    d.textContent = (m.sender_id === (PVP.me || "") ? "YOU" : (m.sender_name || "Friend")) + ": " + m.text;
    log.appendChild(d);
  });
  log.scrollTop = log.scrollHeight;
}
window.addEventListener("chess-checkers-room", function(e){
  var room = e.detail; if (!room) return;
  var js = JSON.stringify(room);
  if (js === lastRoomJson) return;
  lastRoomJson = js;
  if (room.state && room.state.game === curGame){
    var st = room.state;
    if (curGame === "chess") chessState = {board: st.board, turn: st.turn, castling: st.castling || {wK:false, wQ:false, bK:false, bQ:false}, ep: st.ep || null};
    else checkersState = {board: st.board, turn: st.turn};
    sel = null; selMoves = [];
    if (st.status === "finished"){
      gameOver = true; roomStatus = "finished"; roomWinner = st.winner || null;
      var msg = roomWinner ? colorName(roomWinner) + " wins!" : "Draw";
      if (curGame === "chess" && roomWinner) msg = "Checkmate! " + msg;
      showPvPResult(msg); renderBoard(); renderChat(room.chat || []); return;
    }
    roomStatus = room.status || "playing";
    gameOver = false;
    renderBoard(); updateTurn();
  } else {
    roomStatus = room.status || roomStatus;
    updateTurn();
  }
  renderChat(room.chat || []);
});
document.getElementById("board").addEventListener("click", function(e){
  var sq = e.target.closest ? e.target.closest(".sq") : null;
  if (!sq) return;
  onSquarePvP(parseInt(sq.dataset.r, 10), parseInt(sq.dataset.c, 10));
});
document.getElementById("btnLeave").onclick = function(){ postToNative({type:"chess-checkers-leave"}); };
document.getElementById("btnClose").onclick = function(){ postToNative("close"); };
document.getElementById("btnChat").onclick = function(){
  var inp = document.getElementById("chatInput"); if (!inp) return;
  var text = inp.value.trim(); if (!text) return;
  inp.value = "";
  postToNative({type:"chess-checkers-chat", text:text});
};
document.getElementById("chatInput").addEventListener("keydown", function(e){ if (e.key === "Enter") document.getElementById("btnChat").click(); });
document.getElementById("gameTitle").textContent = curGame === "chess" ? "Chess" : "Checkers";
document.getElementById("gameNote").textContent = "You play " + colorName(myColor) + ". " + ((myColor === "w" || myColor === "r") ? "You move first." : "Your opponent moves first.");
renderBoard(); updateTurn();

</script>
</body>
</html>
`;
