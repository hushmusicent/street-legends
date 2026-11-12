import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Modal, SafeAreaView, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { WebView } from 'react-native-webview';
import { showGameToast } from '../components/GameToast';
import { useGameStore } from '../hooks/useGameStore';
import { useInvalidateMapQueries } from '../hooks/useMapQueries';
import { startShootout as apiStartShootout, completeShootout as apiCompleteShootout, getPlayer } from '../services/api';

const API_URL = process.env.EXPO_PUBLIC_BACKEND_URL || '';

// The City Gotcha game, embedded. In app mode it auto-starts at the injected
// level and posts {type:'gameOver', hits, shots, score, level} when done.
const GAME_HTML = `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>City Gotcha — Shootout</title>
<style>
  * { margin:0; padding:0; box-sizing:border-box; -webkit-tap-highlight-color: transparent; }
  html, body { width:100%; height:100%; overflow:hidden; background:#0a0a12; touch-action:none; }
  body { font-family: 'Courier New', monospace; }
  /* The wrap is sized by JS to window.innerHeight. 100vh overflows in a
     WebView (it counts the area under the status bar), which made the game
     taller than the screen and cut the player off the bottom. */
  #wrap { position:relative; width:100vw; height:100%; max-width:400px; margin:0 auto; background:#0a0a12; }
  canvas { display:block; width:100%; height:100%; touch-action:none; }
  /* Overlay screens */
  .overlay { position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(5,5,15,.82); z-index:10; text-align:center; padding:16px; }
  .hidden { display:none !important; }
  .title { color:#ffd23f; font-size:34px; font-weight:bold; letter-spacing:3px; text-shadow:0 3px 0 #b8860b, 0 6px 12px rgba(0,0,0,.7); flex-shrink:0; }
  .subtitle { color:#7fd4ff; font-size:14px; margin:8px 0 4px; letter-spacing:2px; flex-shrink:0; }
  .howto { color:#e8e8e8; font-size:13px; line-height:1.6; margin:12px 0 6px; max-width:340px; flex-shrink:1; min-height:0; overflow-y:auto; max-height:52vh; padding:10px 12px; border:1px solid rgba(255,255,255,.18); border-radius:10px; background:rgba(0,0,0,.35); -webkit-overflow-scrolling:touch; scrollbar-width:thin; }
  .howto::-webkit-scrollbar { width:6px; }
  .howto::-webkit-scrollbar-thumb { background:#555; border-radius:3px; }
  .howto b { color:#ffd23f; }
  .btn { margin-top:18px; background:#e74c3c; color:#fff; border:none; border-bottom:4px solid #922b21; border-radius:10px; font-family:inherit; font-size:22px; font-weight:bold; letter-spacing:2px; padding:14px 42px; cursor:pointer; flex-shrink:0; }
  .btn:active { transform:translateY(2px); border-bottom-width:2px; }
  .btn.green { background:#27ae60; border-bottom-color:#1e8449; }
  .big { color:#ffd23f; font-size:30px; font-weight:bold; margin:8px 0; }
  .stat { color:#fff; font-size:18px; margin:4px 0; }
  .stat span { color:#ffd23f; font-weight:bold; }
  #muteBtn { position:absolute; top:70px; right:8px; z-index:20; background:rgba(0,0,0,.55); color:#fff; border:1px solid #555; border-radius:8px; font-size:16px; padding:6px 10px; cursor:pointer; }
  #quitBtn { position:absolute; top:70px; left:8px; z-index:20; background:rgba(231,76,60,.85); color:#fff; border:1px solid #922b21; border-radius:8px; font-family:inherit; font-size:14px; font-weight:bold; letter-spacing:1px; padding:7px 12px; cursor:pointer; }
</style>
</head>
<body>
<div id="wrap">
  <canvas id="game"></canvas>
  <button id="muteBtn">🔊</button>
  <button id="quitBtn">✕ QUIT</button>

  <div id="startScreen" class="overlay">
    <div class="title">CITY GOTCHA</div>
    <div class="subtitle">GOTCHA-STYLE SHOOTOUT • CITY SCENE</div>
    <div class="howto">
      The city scrolls by. <b>Tap an enemy to shoot it.</b><br>
      Every hit pays <b>$10</b>.<br>
      🏃 Runners on the street • 🚗 Cars driving by<br>
      🪟 Popping out of windows • 🏢 Between buildings<br>
      🏙️ Up on the rooftops<br><br>
      ⚠️ <b>They shoot back!</b> Gang members fire at you —<br>
      you have <b>10 ❤️</b>. Get hit 10 times and it's over.<br>
      Shoot them first. Watch for <b>❤️ in the windows</b> —<br>
      shoot a heart to gain one back.<br>
      Don't shoot innocents! Citizens in light clothes<br>
      and hostages with their hands up cost you cash,<br>
      and hitting a vehicle costs cash too:<br>
      <b>citizen −$10 • hostage −$20 • vehicle −$15</b>.<br><br>
      Each shot costs <b>1 AMMO</b> (refills over time).<br>
      Higher level = <b>faster scroll</b> + <b>shorter timer</b>.<br>
      Clear the timer to move up a level.
    </div>
    <button class="btn" id="startBtn">START</button>
  </div>

  <div id="levelScreen" class="overlay hidden">
    <div class="big" id="levelTitle">LEVEL COMPLETE!</div>
    <div class="stat">Cash: <span id="levelScore">$0</span></div>
    <div class="stat">Hits: <span id="levelHits">0</span> • Shots: <span id="levelShots">0</span></div>
    <div class="stat">Accuracy: <span id="levelAcc">0%</span></div>
    <div class="stat" id="nextInfo"></div>
    <button class="btn green" id="nextBtn">NEXT LEVEL ▶</button>
  </div>

  <div id="overScreen" class="overlay hidden">
    <div class="big" id="overTitle">TIME UP!</div>
    <div class="stat">Final Cash: <span id="overScore">$0</span></div>
    <div class="stat">Level reached: <span id="overLevel">1</span></div>
    <button class="btn" id="againBtn">PLAY AGAIN</button>
  </div>
</div>

<script>
(() => {
'use strict';
// ---------- Canvas ----------
const canvas = document.getElementById('game');
const ctx = canvas.getContext('2d');
let W = 0, H = 0, DPR = 1;
function resize() {
  // Size the wrap to the real viewport (window.innerHeight), not 100vh —
  // in a WebView 100vh counts the area under the status bar, so the game
  // ran taller than the screen and the player was cut off the bottom.
  const wrap = document.getElementById('wrap');
  if (wrap) wrap.style.height = window.innerHeight + 'px';
  DPR = Math.min(2, window.devicePixelRatio || 1);
  W = canvas.clientWidth; H = canvas.clientHeight;
  canvas.width = Math.round(W * DPR); canvas.height = Math.round(H * DPR);
  ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
}
window.addEventListener('resize', resize);

// ---------- Audio (tiny WebAudio blips) ----------
let audioCtx = null, muted = false;
function beep(freq, dur, type, vol) {
  if (muted) return;
  try {
    if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const o = audioCtx.createOscillator(), g = audioCtx.createGain();
    o.type = type || 'square'; o.frequency.value = freq;
    g.gain.value = vol || 0.06;
    o.connect(g); g.connect(audioCtx.destination);
    o.start(); g.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + (dur || 0.08));
    o.stop(audioCtx.currentTime + (dur || 0.08));
  } catch (e) {}
}
const sfxShot = () => beep(900, 0.07, 'square', 0.08);
const sfxHit = () => { beep(300, 0.1, 'square', 0.09); setTimeout(() => beep(180, 0.12, 'square', 0.09), 60); };
const sfxMiss = () => beep(140, 0.08, 'sawtooth', 0.04);
document.getElementById('muteBtn').addEventListener('click', (e) => {
  e.stopPropagation();
  muted = !muted;
  e.target.textContent = muted ? '🔇' : '🔊';
});
// QUIT: in the app it tells the app to close the game (back to the map);
// in the browser it goes back to the start screen.
document.getElementById('quitBtn').addEventListener('click', (e) => {
  e.stopPropagation();
  if (APP_MODE) {
    appReport({ type: 'quit' });
    return;
  }
  S.mode = 'menu';
  document.getElementById('startScreen').classList.remove('hidden');
});

// ---------- App mode (embedded in the Street Legends app via WebView) ----------
// When the app hosts this game it injects window.SHOOTOUT_CONFIG = { level }
// (or passes ?level= in the URL). In app mode the game auto-starts at that
// level, skips its own start/level screens, and reports the result back to
// the app with window.ReactNativeWebView.postMessage so the app can pay out
// through the backend (50% in settings, full on the map, with XP + rep).
const APP_CONFIG = (() => {
  try {
    if (typeof window !== 'undefined' && window.SHOOTOUT_CONFIG) return window.SHOOTOUT_CONFIG;
    const q = new URLSearchParams(window.location.search);
    if (q.get('level')) return { level: parseInt(q.get('level'), 10) || 1, appMode: true };
  } catch (e) {}
  return null;
})();
const APP_MODE = !!APP_CONFIG;

function appReport(result) {
  try {
    if (typeof window !== 'undefined' && window.ReactNativeWebView && window.ReactNativeWebView.postMessage) {
      window.ReactNativeWebView.postMessage(JSON.stringify(result));
    }
  } catch (e) {}
}

// ---------- Game state ----------
const S = {
  mode: 'start', // start | playing | level | over
  level: 1,
  score: 0,
  hits: 0,
  shots: 0,
  ammo: 24,
  maxAmmo: 24,
  timeLeft: 40,
  timeTotal: 40,
  scrollX: 0,
  scrollSpeed: 1.8,
  hp: 10,
  maxHp: 10,
  invulnT: 0,
  bullets: [],
  enemies: [],
  effects: [],
  floaters: [],
  spawnT: 0,
  heartT: 4000,
  ammoT: 0,
  lastTs: 0,
  crosshair: null,
};

function levelConfig(l) {
  return {
    scrollSpeed: 1.8 + (l - 1) * 0.45,        // faster scroll, ramps up
    timeTotal: Math.max(18, 40 - (l - 1) * 3), // shorter timer
    spawnInterval: Math.max(300, 650 - (l - 1) * 90),
    enemySpeed: 1.15 + (l - 1) * 0.22,
    fireInterval: Math.max(900, 2200 - (l - 1) * 200), // how often an enemy shoots
    maxAmmo: 24,
    maxHp: 10,
  };
}

// ---------- City generation ----------
// Buildings are generated in world coordinates; the camera scrolls through them.
const buildings = []; // {x, w, h, hue, windows:[{x,y,lit}], roof:'tower'|'antenna'|null}
const BUILDING_W_MIN = 90, BUILDING_W_MAX = 150;
let worldEnd = 0;
function genCity() {
  buildings.length = 0;
  let x = -40;
  worldEnd = 0;
  while (x < 9000) {
    const w = BUILDING_W_MIN + Math.random() * (BUILDING_W_MAX - BUILDING_W_MIN);
    const h = 150 + Math.random() * 190;
    const hue = 210 + Math.random() * 40; // blue-grey city
    const windows = [];
    const cols = Math.floor(w / 26), rows = Math.floor(h / 34);
    for (let c = 0; c < cols; c++) for (let r = 0; r < rows; r++) {
      windows.push({ x: 10 + c * 26, y: 14 + r * 34, lit: Math.random() < 0.45 });
    }
    const roof = Math.random() < 0.3 ? (Math.random() < 0.5 ? 'tower' : 'antenna') : null;
    buildings.push({ x, w, h, hue, windows, roof });
    x += w + 14 + Math.random() * 26; // gap = alley
  }
  worldEnd = x;
}
genCity();

// Far skyline (parallax layer 2)
const farBuildings = [];
(function genFar() {
  let x = 0;
  while (x < 6000) {
    const w = 60 + Math.random() * 110, h = 90 + Math.random() * 170;
    farBuildings.push({ x, w, h });
    x += w + 20 + Math.random() * 40;
  }
})();

// ---------- Enemies ----------
// type: runner | car | window | alley | rooftop | citizen | hostage
// Every gang-member hit pays $10 flat. Citizens, hostages and vehicles
// COST cash when hit — don't shoot them.
const POINTS = { runner: 10, car: -15, window: 10, alley: 10, rooftop: 10, citizen: -10, hostage: -20 };
// Innocents: citizens walk the street / appear in windows and alleys;
// hostages appear in windows and on rooftops with their hands up.
// They look different from gang members on purpose — light clothes, no hat,
// hostages with raised hands. Shooting one costs points.
function spawnInnocent() {
  const cfg = levelConfig(S.level);
  const groundY = H - 92;
  const hostage = Math.random() < 0.4;
  const roll = Math.random();
  if (!hostage && roll < 0.5) {
    // citizen running across the street
    const dir = Math.random() < 0.5 ? 1 : -1;
    S.enemies.push({ type: 'citizen', x: dir === 1 ? -50 : W + 50, y: groundY - 46, w: 34, h: 46, vx: dir * (1.2 + Math.random() * 0.8) * cfg.enemySpeed, t: 0, ttl: 12000, bob: Math.random() * 6 });
  } else if (hostage && roll < 0.5) {
    // hostage in a window, hands up
    const on = buildings.filter(b => b.x - S.scrollX > -50 && b.x - S.scrollX < W + 50);
    if (!on.length) return;
    const b = on[Math.floor(Math.random() * on.length)];
    const win = b.windows[Math.floor(Math.random() * b.windows.length)];
    S.enemies.push({ type: 'hostage', x: b.x + win.x - 4, y: (H - 92) - b.h + win.y - 6, w: 26, h: 30, vx: 0, t: 0, ttl: 2000 + Math.random() * 900, pop: 0 });
  } else if (hostage) {
    // hostage on a rooftop, hands up
    const on = buildings.filter(b => b.x - S.scrollX > 0 && b.x - S.scrollX < W - 60);
    if (!on.length) return;
    const b = on[Math.floor(Math.random() * on.length)];
    S.enemies.push({ type: 'hostage', x: b.x + b.w / 2 - 15, y: (H - 92) - b.h - 44, w: 30, h: 44, vx: 0, t: 0, ttl: 2000 + Math.random() * 900, pop: 0, b });
  } else {
    // citizen between buildings
    const on = buildings.filter(b => b.x - S.scrollX > 0 && b.x - S.scrollX < W - 60);
    if (on.length < 2) return;
    const b = on[Math.floor(Math.random() * (on.length - 1))];
    const gapX = b.x + b.w + 4;
    S.enemies.push({ type: 'citizen', x: gapX, y: groundY - 44, w: 30, h: 44, vx: 0, t: 0, ttl: 2000 + Math.random() * 900, pop: 0 });
  }
}

function spawnEnemy() {
  const cfg = levelConfig(S.level);
  // ~28% of spawns are innocents — citizens or hostages. Don't shoot them.
  if (Math.random() < 0.28) { spawnInnocent(); return; }
  const roll = Math.random();
  let type;
  if (roll < 0.30) type = 'runner';
  else if (roll < 0.48) type = 'car';
  else if (roll < 0.68) type = 'window';
  else if (roll < 0.84) type = 'alley';
  else type = 'rooftop';

  const groundY = H - 92; // street level
  if (type === 'runner') {
    const dir = Math.random() < 0.5 ? 1 : -1;
    S.enemies.push({ type, x: dir === 1 ? -50 : W + 50, y: groundY - 46, w: 34, h: 46, vx: dir * (1.6 + Math.random()) * cfg.enemySpeed, t: 0, ttl: 12000, bob: Math.random() * 6, fireT: 900 + Math.random() * cfg.fireInterval });
  } else if (type === 'car') {
    const dir = Math.random() < 0.5 ? 1 : -1;
    S.enemies.push({ type, x: dir === 1 ? -110 : W + 110, y: groundY - 26, w: 96, h: 30, vx: dir * (3.2 + Math.random() * 1.4) * cfg.enemySpeed, t: 0, ttl: 9000, color: ['#e74c3c', '#f39c12', '#3498db', '#9b59b6'][Math.floor(Math.random() * 4)] });
  } else if (type === 'window') {
    // pick a building currently on screen
    const on = buildings.filter(b => b.x - S.scrollX > -50 && b.x - S.scrollX < W + 50);
    if (!on.length) return;
    const b = on[Math.floor(Math.random() * on.length)];
    const win = b.windows[Math.floor(Math.random() * b.windows.length)];
    S.enemies.push({ type, x: b.x + win.x - 4, y: (H - 92) - b.h + win.y - 6, w: 26, h: 30, vx: 0, t: 0, ttl: 1400 + Math.random() * 700, pop: 0, fireT: 700 + Math.random() * cfg.fireInterval });
  } else if (type === 'alley') {
    // between two buildings
    const on = buildings.filter(b => b.x - S.scrollX > 0 && b.x - S.scrollX < W - 60);
    if (on.length < 2) return;
    const b = on[Math.floor(Math.random() * (on.length - 1))];
    const gapX = b.x + b.w + 4;
    S.enemies.push({ type, x: gapX, y: groundY - 44, w: 30, h: 44, vx: 0, t: 0, ttl: 1800 + Math.random() * 800, pop: 0, fireT: 800 + Math.random() * cfg.fireInterval });
  } else { // rooftop
    const on = buildings.filter(b => b.x - S.scrollX > 0 && b.x - S.scrollX < W - 60);
    if (!on.length) return;
    const b = on[Math.floor(Math.random() * on.length)];
    S.enemies.push({ type, x: b.x + b.w / 2 - 15, y: (H - 92) - b.h - 44, w: 30, h: 44, vx: 0, t: 0, ttl: 1700 + Math.random() * 800, pop: 0, b, fireT: 800 + Math.random() * cfg.fireInterval });
  }
}

function startLevel(l) {
  const cfg = levelConfig(l);
  S.level = l;
  S.timeTotal = cfg.timeTotal;
  S.timeLeft = cfg.timeTotal;
  S.scrollSpeed = cfg.scrollSpeed;
  S.ammo = cfg.maxAmmo;
  S.maxAmmo = cfg.maxAmmo;
  S.hp = cfg.maxHp || 3;
  S.maxHp = cfg.maxHp || 3;
  S.invulnT = 0;
  S.bullets = [];
  S.enemies = []; S.effects = []; S.floaters = [];
  S.spawnT = 0; S.heartT = 4000; S.ammoT = 0;
  S.mode = 'playing';
  document.getElementById('startScreen').classList.add('hidden');
  document.getElementById('levelScreen').classList.add('hidden');
  document.getElementById('overScreen').classList.add('hidden');
}

function endLevel() {
  if (APP_MODE) {
    // Report to the app; it pays out via the backend and shows results.
    appReport({ type: 'gameOver', won: true, hits: S.hits, shots: S.shots, score: S.score, level: S.level });
    S.mode = 'done';
    return;
  }
  S.mode = 'level';
  const acc = S.shots ? Math.round(S.hits / S.shots * 100) : 0;
  document.getElementById('levelScore').textContent = '$' + S.score;
  document.getElementById('levelHits').textContent = S.hits;
  document.getElementById('levelShots').textContent = S.shots;
  document.getElementById('levelAcc').textContent = acc + '%';
  const next = levelConfig(S.level + 1);
  document.getElementById('levelTitle').textContent = 'LEVEL ' + S.level + ' CLEAR!';
  document.getElementById('nextInfo').textContent =
    'Next: scroll ' + next.scrollSpeed.toFixed(1) + 'x • timer ' + next.timeTotal + 's';
  document.getElementById('levelScreen').classList.remove('hidden');
}

function gameOver(reason) {
  if (APP_MODE) {
    appReport({ type: 'gameOver', won: false, hits: S.hits, shots: S.shots, score: S.score, level: S.level, reason: reason || 'time' });
    S.mode = 'done';
    return;
  }
  S.mode = 'over';
  document.getElementById('overTitle').textContent = reason === 'hp' ? 'SHOT DOWN!' : 'TIME UP!';
  document.getElementById('overScore').textContent = '$' + S.score;
  document.getElementById('overLevel').textContent = S.level;
  document.getElementById('overScreen').classList.remove('hidden');
}

// ---------- Shooting ----------
function shoot(px, py) {
  if (S.mode !== 'playing') return;
  if (S.ammo <= 0) { sfxMiss(); return; }
  S.ammo--; S.shots++;
  sfxShot();
  // muzzle flash at bottom centre (the shooter)
  S.effects.push({ kind: 'flash', x: W / 2, y: H - 30, t: 0, ttl: 90 });
  // find an enemy under the tap (topmost = last spawned)
  let hit = null;
  for (let i = S.enemies.length - 1; i >= 0; i--) {
    const e = S.enemies[i];
    // window/rooftop/alley/hostage/heart and still citizens ride the scroll; runner/car and running citizens move on their own
    const ridesScroll = e.type === 'window' || e.type === 'rooftop' || e.type === 'alley' || e.type === 'hostage' || e.type === 'heart' || (e.type === 'citizen' && !e.vx);
    const ex = ridesScroll ? e.x - S.scrollX : e.x;
    const ey = (e.type === 'rooftop' || e.type === 'hostage') && e.b ? (H - 92 - e.b.h - 44) : e.y;
    if (px >= ex - 6 && px <= ex + e.w + 6 && py >= ey - 6 && py <= ey + e.h + 6) { hit = { e, i, ex, ey }; break; }
  }
  if (hit) {
    // a heart pickup gives a heart back (no points, no shot counted as a hit)
    if (hit.e.type === 'heart') {
      S.hp = Math.min(S.maxHp, S.hp + 1);
      beep(660, 0.1, 'sine', 0.1); setTimeout(() => beep(880, 0.14, 'sine', 0.1), 90);
      S.effects.push({ kind: 'heal', x: hit.ex + hit.e.w / 2, y: hit.ey + hit.e.h / 2, t: 0, ttl: 300 });
      S.floaters.push({ x: hit.ex + hit.e.w / 2, y: hit.ey, txt: '+1 ❤️', t: 0, ttl: 900, heal: true });
      S.enemies.splice(hit.i, 1);
      return;
    }
    const pts = POINTS[hit.e.type];
    const innocent = pts < 0;
    S.score = Math.max(0, S.score + pts);
    if (!innocent) { S.hits++; sfxHit(); }
    else { sfxMiss(); beep(90, 0.25, 'sawtooth', 0.1); }
    S.effects.push({ kind: innocent ? 'bad' : 'boom', x: hit.ex + hit.e.w / 2, y: hit.ey + hit.e.h / 2, t: 0, ttl: 260 });
    S.floaters.push({ x: hit.ex + hit.e.w / 2, y: hit.ey, txt: (pts > 0 ? '+$' : '-$') + Math.abs(pts), t: 0, ttl: 900, bad: innocent });
    S.enemies.splice(hit.i, 1);
  } else {
    sfxMiss();
    S.effects.push({ kind: 'ring', x: px, y: py, t: 0, ttl: 200 });
  }
}

canvas.addEventListener('pointerdown', (e) => {
  const r = canvas.getBoundingClientRect();
  const px = e.clientX - r.left, py = e.clientY - r.top;
  S.crosshair = { x: px, y: py, t: 0 };
  shoot(px, py);
});
canvas.addEventListener('pointermove', (e) => {
  const r = canvas.getBoundingClientRect();
  S.crosshair = { x: e.clientX - r.left, y: e.clientY - r.top, t: 0 };
});

// ---------- Update ----------
function update(dt) {
  if (S.mode !== 'playing') return;
  // scroll
  S.scrollX += S.scrollSpeed * (dt / 16.7);
  if (S.scrollX > worldEnd - W - 100) { S.scrollX = 0; genCity(); } // loop the city
  // timer
  S.timeLeft -= dt / 1000;
  if (S.timeLeft <= 0) { S.timeLeft = 0; endLevel(); return; }
  // ammo refill: +1 per second
  S.ammoT += dt;
  if (S.ammoT >= 1000) { S.ammoT = 0; if (S.ammo < S.maxAmmo) S.ammo++; }
  // spawn
  const cfg = levelConfig(S.level);
  S.spawnT += dt;
  if (S.spawnT >= cfg.spawnInterval) { S.spawnT = 0; spawnEnemy(); if (Math.random() < 0.3) spawnEnemy(); }
  // hearts in windows here and there — shoot one to gain a heart back
  S.heartT += dt;
  if (S.heartT >= 8000) {
    S.heartT = 0;
    const on = buildings.filter(b => b.x - S.scrollX > -50 && b.x - S.scrollX < W + 50);
    if (on.length) {
      const b = on[Math.floor(Math.random() * on.length)];
      const win = b.windows[Math.floor(Math.random() * b.windows.length)];
      S.enemies.push({ type: 'heart', x: b.x + win.x - 4, y: (H - 92) - b.h + win.y - 6, w: 26, h: 24, vx: 0, t: 0, ttl: 3500, pop: 0 });
    }
  }
  // enemies
  for (let i = S.enemies.length - 1; i >= 0; i--) {
    const e = S.enemies[i];
    e.t += dt;
    if ((e.type === 'runner' || e.type === 'car' || (e.type === 'citizen' && e.vx))) {
      e.x += e.vx * (dt / 16.7);
      if (e.x < -140 || e.x > W + 140) { S.enemies.splice(i, 1); continue; }
    }
    if (e.type === 'window' || e.type === 'alley' || e.type === 'rooftop' || e.type === 'hostage' || e.type === 'heart' || (e.type === 'citizen' && !e.vx)) {
      e.pop = Math.min(1, e.t / 160); // pop-up animation
      if (e.t > e.ttl) { S.enemies.splice(i, 1); continue; }
    }
    if (e.t > e.ttl) S.enemies.splice(i, 1);
    // gang members shoot back at the player
    if (e.fireT !== undefined && (e.type === 'runner' || e.type === 'window' || e.type === 'alley' || e.type === 'rooftop')) {
      e.fireT -= dt;
      if (e.fireT <= 0) {
        e.fireT = levelConfig(S.level).fireInterval * (0.7 + Math.random() * 0.6);
        // enemy screen position
        const ridesScroll = e.type === 'window' || e.type === 'rooftop' || e.type === 'alley';
        const ex = ridesScroll ? e.x - S.scrollX : e.x;
        const ey = e.type === 'rooftop' && e.b ? (H - 92 - e.b.h - 44) : e.y;
        const sx = ex + e.w / 2, sy = ey + e.h / 2;
        const tx = W / 2, ty = H - 30; // the player
        const dx = tx - sx, dy = ty - sy;
        const dist = Math.max(1, Math.hypot(dx, dy));
        const speed = 5.2;
        S.bullets.push({ x: sx, y: sy, vx: dx / dist * speed, vy: dy / dist * speed, t: 0 });
        beep(500, 0.06, 'square', 0.04);
      }
    }
  }
  // enemy bullets — they fly at the player
  const px = W / 2, py = H - 30;
  for (let i = S.bullets.length - 1; i >= 0; i--) {
    const b = S.bullets[i];
    b.x += b.vx * (dt / 16.7); b.y += b.vy * (dt / 16.7); b.t += dt;
    if (b.x < -20 || b.x > W + 20 || b.y < -20 || b.y > H + 20 || b.t > 4000) { S.bullets.splice(i, 1); continue; }
    // hit the player?
    if (S.invulnT <= 0 && Math.abs(b.x - px) < 24 && Math.abs(b.y - py) < 26) {
      S.bullets.splice(i, 1);
      S.hp--;
      S.invulnT = 1100; // brief invulnerability so one burst can't delete you
      beep(120, 0.25, 'sawtooth', 0.12);
      S.effects.push({ kind: 'hurt', x: px, y: py, t: 0, ttl: 350 });
      if (S.hp <= 0) { gameOver('hp'); return; }
    }
  }
  if (S.invulnT > 0) S.invulnT -= dt;
  // effects / floaters
  for (let i = S.effects.length - 1; i >= 0; i--) { S.effects[i].t += dt; if (S.effects[i].t > S.effects[i].ttl) S.effects.splice(i, 1); }
  for (let i = S.floaters.length - 1; i >= 0; i--) { S.floaters[i].t += dt; S.floaters[i].y -= 0.5 * (dt / 16.7); if (S.floaters[i].t > S.floaters[i].ttl) S.floaters.splice(i, 1); }
}

// ---------- Draw ----------
function drawHeartPickup(x, y, w, h) {
  // red heart with a soft glow, pulsing
  const pulse = 1 + Math.sin(Date.now() / 180) * 0.12;
  const cx = x + w / 2, cy = y + h / 2, s = (w / 2) * pulse;
  ctx.fillStyle = 'rgba(231,76,60,.35)';
  ctx.beginPath(); ctx.arc(cx, cy, s + 6, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = '#e74c3c';
  ctx.beginPath();
  ctx.moveTo(cx, cy + s * 0.9);
  ctx.bezierCurveTo(cx - s * 1.3, cy, cx - s * 0.7, cy - s, cx, cy - s * 0.35);
  ctx.bezierCurveTo(cx + s * 0.7, cy - s, cx + s * 1.3, cy, cx, cy + s * 0.9);
  ctx.fill();
  ctx.fillStyle = 'rgba(255,255,255,.7)';
  ctx.beginPath(); ctx.arc(cx - s * 0.35, cy - s * 0.35, s * 0.18, 0, Math.PI * 2); ctx.fill();
}

function drawCitizen(x, y, w, h, handsUp) {
  // innocent: light clothes, NO hat — clearly not a gang member
  ctx.fillStyle = '#e8b98a';
  ctx.fillRect(x + w * 0.28, y + 9, w * 0.44, 11);          // head
  ctx.fillStyle = '#f5f5f5';
  ctx.fillRect(x + w * 0.18, y + 20, w * 0.64, 15);         // light shirt
  ctx.fillStyle = '#5d7ea6';
  ctx.fillRect(x + w * 0.24, y + 35, w * 0.2, h - 35);      // leg L
  ctx.fillRect(x + w * 0.56, y + 35, w * 0.2, h - 35);      // leg R
  if (handsUp) {
    ctx.fillStyle = '#e8b98a';
    ctx.fillRect(x + w * 0.05, y - 2, 6, 16);               // arm up L
    ctx.fillRect(x + w * 0.78, y - 2, 6, 16);               // arm up R
  }
}

function drawGang(x, y, w, h, color) {
  // simple gang member: hat, head, body, legs
  ctx.fillStyle = '#2d1a0e';
  ctx.fillRect(x + w * 0.22, y + 2, w * 0.56, 7);           // hat brim
  ctx.fillRect(x + w * 0.32, y - 5, w * 0.36, 8);           // hat top
  ctx.fillStyle = '#e8b98a';
  ctx.fillRect(x + w * 0.28, y + 9, w * 0.44, 11);          // head
  ctx.fillStyle = color || '#3a6b2f';
  ctx.fillRect(x + w * 0.18, y + 20, w * 0.64, 15);         // jacket
  ctx.fillStyle = '#222';
  ctx.fillRect(x + w * 0.24, y + 35, w * 0.2, h - 35);      // leg L
  ctx.fillRect(x + w * 0.56, y + 35, w * 0.2, h - 35);      // leg R
}

function draw() {
  const groundY = H - 92;
  // sky
  const sky = ctx.createLinearGradient(0, 0, 0, groundY);
  sky.addColorStop(0, '#1b2a52'); sky.addColorStop(0.6, '#3a6ea8'); sky.addColorStop(1, '#7fb2d9');
  ctx.fillStyle = sky; ctx.fillRect(0, 0, W, groundY);
  // sun/moon
  ctx.fillStyle = '#ffd23f';
  ctx.beginPath(); ctx.arc(W - 70, 60, 26, 0, Math.PI * 2); ctx.fill();
  // far skyline (parallax 0.3)
  ctx.fillStyle = '#2c3e63';
  const farOff = (S.scrollX * 0.3) % 6000;
  for (const b of farBuildings) {
    let bx = b.x - farOff;
    if (bx < -200) bx += 6000;
    if (bx > W + 50) continue;
    ctx.fillRect(bx, groundY - b.h, b.w, b.h);
  }
  // near buildings (parallax 1.0)
  for (const b of buildings) {
    const bx = b.x - S.scrollX;
    if (bx > W + 20 || bx + b.w < -20) continue;
    const by = groundY - b.h;
    // body
    ctx.fillStyle = 'hsl(' + b.hue + ', 28%, 26%)';
    ctx.fillRect(bx, by, b.w, b.h);
    // roof edge
    ctx.fillStyle = 'hsl(' + b.hue + ', 30%, 18%)';
    ctx.fillRect(bx - 3, by - 6, b.w + 6, 8);
    // roof props
    if (b.roof === 'tower') {
      ctx.fillStyle = '#5d4037';
      ctx.fillRect(bx + b.w / 2 - 12, by - 26, 24, 20);
      ctx.fillStyle = '#3e2723';
      ctx.beginPath(); ctx.moveTo(bx + b.w / 2 - 14, by - 26); ctx.lineTo(bx + b.w / 2, by - 36); ctx.lineTo(bx + b.w / 2 + 14, by - 26); ctx.fill();
    } else if (b.roof === 'antenna') {
      ctx.strokeStyle = '#cfd8dc'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.moveTo(bx + b.w / 2, by - 6); ctx.lineTo(bx + b.w / 2, by - 34); ctx.stroke();
      ctx.fillStyle = '#e74c3c'; ctx.beginPath(); ctx.arc(bx + b.w / 2, by - 36, 3, 0, Math.PI * 2); ctx.fill();
    }
    // windows
    for (const win of b.windows) {
      ctx.fillStyle = win.lit ? '#ffd54f' : '#16222e';
      ctx.fillRect(bx + win.x, by + win.y, 14, 18);
    }
  }
  // street
  ctx.fillStyle = '#2e3440'; ctx.fillRect(0, groundY, W, 92);
  ctx.fillStyle = '#ffd23f';
  for (let x = -((S.scrollX * 1.4) % 60); x < W; x += 60) ctx.fillRect(x, groundY + 44, 30, 5);
  ctx.fillStyle = '#1c2733'; ctx.fillRect(0, groundY, W, 6); // curb
  // sidewalk
  ctx.fillStyle = '#4a5568'; ctx.fillRect(0, groundY - 4, W, 6);

  // enemies
  for (const e of S.enemies) {
    if (e.type === 'runner') {
      const bobY = Math.sin(e.t / 90) * 3;
      drawGang(e.x, e.y + bobY, e.w, e.h, '#3a6b2f');
    } else if (e.type === 'car') {
      ctx.fillStyle = e.color;
      ctx.fillRect(e.x, e.y, e.w, e.h);
      ctx.fillStyle = '#bfe3ff';
      ctx.fillRect(e.x + 18, e.y + 4, 26, 12);
      ctx.fillRect(e.x + 56, e.y + 4, 22, 12);
      ctx.fillStyle = '#111';
      ctx.beginPath(); ctx.arc(e.x + 22, e.y + e.h, 9, 0, Math.PI * 2); ctx.fill();
      ctx.beginPath(); ctx.arc(e.x + e.w - 22, e.y + e.h, 9, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = '#ffe082';
      ctx.fillRect(e.x + (e.vx > 0 ? e.w - 4 : 0), e.y + 12, 4, 6);
    } else if (e.type === 'window') {
      const bx = e.x - S.scrollX, by = e.y;
      ctx.save();
      ctx.globalAlpha = e.pop;
      // dark window behind
      ctx.fillStyle = '#0d1520'; ctx.fillRect(bx - 2, by - 2, e.w + 4, e.h + 4);
      drawGang(bx, by, e.w, e.h, '#7b2d8b');
      ctx.restore();
    } else if (e.type === 'alley') {
      const bx = e.x - S.scrollX;
      ctx.save(); ctx.globalAlpha = e.pop;
      drawGang(bx, e.y, e.w, e.h, '#8b2d2d');
      ctx.restore();
    } else if (e.type === 'rooftop') {
      const bx = e.x - S.scrollX;
      const by = e.b ? (groundY - e.b.h - 44) : e.y;
      ctx.save(); ctx.globalAlpha = e.pop;
      drawGang(bx, by, e.w, e.h, '#2d5a8b');
      ctx.restore();
    } else if (e.type === 'citizen') {
      if (e.vx) {
        const bobY = Math.sin(e.t / 90) * 3;
        drawCitizen(e.x, e.y + bobY, e.w, e.h, false);
      } else {
        const bx = e.x - S.scrollX;
        ctx.save(); ctx.globalAlpha = e.pop;
        drawCitizen(bx, e.y, e.w, e.h, false);
        ctx.restore();
      }
    } else if (e.type === 'hostage') {
      const bx = e.x - S.scrollX;
      const by = e.b ? (groundY - e.b.h - 44) : e.y;
      ctx.save(); ctx.globalAlpha = e.pop;
      drawCitizen(bx, by, e.w, e.h, true); // hands up
      ctx.restore();
    } else if (e.type === 'heart') {
      const bx = e.x - S.scrollX;
      ctx.save(); ctx.globalAlpha = e.pop;
      drawHeartPickup(bx, e.y, e.w, e.h);
      ctx.restore();
    }
  }

  // enemy bullets
  for (const b of S.bullets) {
    ctx.fillStyle = '#ff5252';
    ctx.beginPath(); ctx.arc(b.x, b.y, 5, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = '#ffd23f';
    ctx.beginPath(); ctx.arc(b.x, b.y, 2.5, 0, Math.PI * 2); ctx.fill();
  }

  // effects
  for (const ef of S.effects) {
    const p = ef.t / ef.ttl;
    if (ef.kind === 'boom') {
      ctx.fillStyle = 'rgba(255,210,63,' + (1 - p) + ')';
      ctx.beginPath(); ctx.arc(ef.x, ef.y, 8 + p * 26, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(231,76,60,' + (1 - p) + ')';
      ctx.beginPath(); ctx.arc(ef.x, ef.y, 5 + p * 16, 0, Math.PI * 2); ctx.fill();
    } else if (ef.kind === 'heal') {
      ctx.fillStyle = 'rgba(39,174,96,' + (1 - p) + ')';
      ctx.beginPath(); ctx.arc(ef.x, ef.y, 8 + p * 24, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(255,255,255,' + (1 - p) + ')';
      ctx.font = 'bold 20px Courier New, monospace'; ctx.textAlign = 'center';
      ctx.fillText('❤️', ef.x, ef.y + 7);
    } else if (ef.kind === 'hurt') {
      ctx.fillStyle = 'rgba(231,76,60,' + (1 - p) * 0.55 + ')';
      ctx.fillRect(0, 0, W, H);
    } else if (ef.kind === 'bad') {
      ctx.fillStyle = 'rgba(231,76,60,' + (1 - p) + ')';
      ctx.beginPath(); ctx.arc(ef.x, ef.y, 8 + p * 26, 0, Math.PI * 2); ctx.fill();
      ctx.fillStyle = 'rgba(255,255,255,' + (1 - p) + ')';
      ctx.font = 'bold 22px Courier New, monospace'; ctx.textAlign = 'center';
      ctx.fillText('✕', ef.x, ef.y + 8);
    } else if (ef.kind === 'ring') {
      ctx.strokeStyle = 'rgba(255,255,255,' + (1 - p) + ')'; ctx.lineWidth = 2;
      ctx.beginPath(); ctx.arc(ef.x, ef.y, 4 + p * 18, 0, Math.PI * 2); ctx.stroke();
    } else if (ef.kind === 'flash') {
      ctx.fillStyle = 'rgba(255,240,150,' + (1 - p) + ')';
      ctx.beginPath(); ctx.arc(ef.x, ef.y, 6 + p * 20, 0, Math.PI * 2); ctx.fill();
    }
  }
  // floaters
  ctx.font = 'bold 20px Courier New, monospace';
  ctx.textAlign = 'center';
  for (const f of S.floaters) {
    ctx.fillStyle = f.heal ? 'rgba(46,204,113,' + (1 - f.t / f.ttl) + ')' : f.bad ? 'rgba(231,76,60,' + (1 - f.t / f.ttl) + ')' : 'rgba(255,210,63,' + (1 - f.t / f.ttl) + ')';
    ctx.fillText(f.txt, f.x, f.y);
  }

  // crosshair
  if (S.crosshair && S.mode === 'playing') {
    const c = S.crosshair;
    ctx.strokeStyle = 'rgba(255,255,255,.9)'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(c.x, c.y, 14, 0, Math.PI * 2); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(c.x - 20, c.y); ctx.lineTo(c.x - 8, c.y);
    ctx.moveTo(c.x + 8, c.y); ctx.lineTo(c.x + 20, c.y);
    ctx.moveTo(c.x, c.y - 20); ctx.lineTo(c.x, c.y - 8);
    ctx.moveTo(c.x, c.y + 8); ctx.lineTo(c.x, c.y + 20);
    ctx.stroke();
    ctx.fillStyle = '#e74c3c';
    ctx.beginPath(); ctx.arc(c.x, c.y, 2.5, 0, Math.PI * 2); ctx.fill();
  }

  // ---------- HUD (Gotcha style) ----------
  const hudH = 64;
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, W, hudH);
  ctx.fillStyle = '#ffd23f';
  ctx.font = 'bold 17px Courier New, monospace';
  ctx.textAlign = 'left';
  ctx.fillText('AMMO→' + S.ammo, 10, 22);
  ctx.fillText('CASH→$' + S.score, 10, 44);
  ctx.textAlign = 'right';
  ctx.fillText('R→' + String(S.level).padStart(2, '0'), W - 10, 22);
  // MAP progress bar
  const mapX = W / 2 - 70, mapY = 12, mapW = 140, mapH = 12;
  ctx.fillStyle = '#222';
  ctx.fillRect(mapX - 2, mapY - 2, mapW + 4, mapH + 4);
  ctx.fillStyle = '#27ae60';
  const prog = S.timeTotal ? 1 - S.timeLeft / S.timeTotal : 0;
  ctx.fillRect(mapX, mapY, mapW * prog, mapH);
  ctx.fillStyle = '#ffd23f'; ctx.font = 'bold 11px Courier New, monospace'; ctx.textAlign = 'center';
  ctx.fillText('MAP', W / 2, mapY + mapH + 14);
  // TIME
  ctx.fillStyle = S.timeLeft <= 10 ? '#e74c3c' : '#ffd23f';
  ctx.font = 'bold 17px Courier New, monospace'; ctx.textAlign = 'right';
  ctx.fillText('TIME ' + Math.ceil(S.timeLeft), W - 10, 44);
  // HP hearts (top centre, under the MAP bar) — 10 hearts, compact
  ctx.font = '13px Courier New, monospace'; ctx.textAlign = 'center';
  let hearts = '';
  for (let i = 0; i < S.maxHp; i++) hearts += i < S.hp ? '❤️' : '🖤';
  ctx.fillText(hearts, W / 2, 62);
  // low ammo warning
  if (S.ammo === 0 && S.mode === 'playing') {
    ctx.fillStyle = '#e74c3c'; ctx.font = 'bold 16px Courier New, monospace'; ctx.textAlign = 'center';
    ctx.fillText('RELOADING…', W / 2, hudH + 26);
  }
  // shooter at bottom centre (the player) — flashes while invulnerable
  if (S.mode === 'playing') {
    const flashing = S.invulnT > 0 && Math.floor(S.invulnT / 120) % 2 === 0;
    if (!flashing) drawGang(W / 2 - 17, H - 46, 34, 46, '#c0392b');
    ctx.fillStyle = '#111';
    ctx.fillRect(W / 2 - 30, H - 8, 60, 8);
  }
}

// ---------- Main loop ----------
function loop(ts) {
  const dt = Math.min(50, ts - (S.lastTs || ts));
  S.lastTs = ts;
  update(dt);
  draw();
  requestAnimationFrame(loop);
}

// ---------- Buttons ----------
document.getElementById('startBtn').addEventListener('click', () => {
  S.score = 0; S.hits = 0; S.shots = 0; S.scrollX = 0;
  startLevel(1);
});
document.getElementById('nextBtn').addEventListener('click', () => startLevel(S.level + 1));
document.getElementById('againBtn').addEventListener('click', () => {
  S.score = 0; S.hits = 0; S.shots = 0; S.scrollX = 0;
  startLevel(1);
});

resize();
if (APP_MODE) {
  // App mode: skip the start screen and jump straight into the level the app asked for.
  const startLevelNum = (APP_CONFIG && APP_CONFIG.level) || 1;
  S.score = 0; S.hits = 0; S.shots = 0; S.scrollX = 0;
  startLevel(startLevelNum);
}
requestAnimationFrame(loop);
})();
</script>
</body>
</html>
`;

interface GameResult {
  type: string;
  won: boolean;
  hits: number;
  shots: number;
  score: number;
  level: number;
  reason?: string;
}

export default function ShootoutSimulator() {
  const params = useLocalSearchParams();
  const shootoutId = params.shootoutId as string | undefined;
  const routeGameId = params.gameId as string | undefined;
  const level = parseInt((params.level as string) || '1', 10) || 1;
  const isStandalone = params.standalone === 'true';
  const { playerId, refreshPlayer } = useGameStore();
  const { invalidatePlayer, invalidateCooldowns } = useInvalidateMapQueries();

  const [gameId, setGameId] = useState<string | null>(routeGameId || null);
  const gameIdRef = useRef<string | null>(routeGameId || null);
  const [starting, setStarting] = useState(true);
  const [startError, setStartError] = useState<string | null>(null);
  const [showResults, setShowResults] = useState(false);
  const [rewards, setRewards] = useState<{ cash: number; xp: number; rep: number } | null>(null);
  const [resultHits, setResultHits] = useState(0);
  const [resultWon, setResultWon] = useState(false);
  const completedRef = useRef(false);

  // Start a backend session so winnings are awarded.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (routeGameId) {
        setGameId(routeGameId);
        gameIdRef.current = routeGameId;
        setStarting(false);
        return;
      }
      if (!playerId) {
        if (!cancelled) { setStartError('No player loaded. Go back and try again.'); setStarting(false); }
        return;
      }
      try {
        if (isStandalone) {
          const res = await fetch(`${API_URL}/api/shootouts/standalone/start?player_id=${playerId}&level=${level}`, { method: 'POST' });
          if (!res.ok) {
            const body = await res.json().catch(() => ({} as any));
            throw new Error(body?.detail || 'Failed to start shootout');
          }
          const data = await res.json();
          if (!cancelled) { setGameId(data.game_id); gameIdRef.current = data.game_id; setStarting(false); }
        } else if (shootoutId) {
          const result = await apiStartShootout(shootoutId, playerId);
          if (!cancelled) { setGameId(result.game_id); gameIdRef.current = result.game_id; setStarting(false); }
        } else {
          if (!cancelled) { setStartError('No shootout selected.'); setStarting(false); }
        }
      } catch (e: any) {
        const msg = e?.response?.data?.detail || e?.message || 'Failed to start shootout';
        if (!cancelled) { setStartError(msg); setStarting(false); }
      }
    })();
    return () => { cancelled = true; };
  }, [playerId, shootoutId, routeGameId, isStandalone, level]);

  const handleGameMessage = useCallback(async (event: any) => {
    if (completedRef.current) return;
    let data: GameResult;
    try {
      data = JSON.parse(event.nativeEvent.data);
    } catch {
      return;
    }
    if (data.type === 'quit') {
      router.replace('/(tabs)');
      return;
    }
    if (data.type !== 'gameOver') return;
    completedRef.current = true;
    const gid = gameIdRef.current;
    setResultHits(data.hits);
    setResultWon(data.won);
    if (gid && playerId) {
      try {
        const result = await apiCompleteShootout(gid, data.hits, isStandalone);
        if (result.rewards) {
          setRewards({
            cash: result.rewards.cash || 0,
            xp: result.rewards.xp || 0,
            rep: result.rewards.reputation || 0,
          });
        }
        if (refreshPlayer) refreshPlayer();
        if (playerId) {
          invalidatePlayer(playerId);
          if (!isStandalone) invalidateCooldowns(playerId);
        }
        if (result.message) showGameToast({ type: 'success', title: data.won ? 'SHOOTOUT COMPLETE' : 'TIME UP', message: result.message, duration: 2500 });
      } catch (e: any) {
        console.error('Failed to complete shootout:', e);
        showGameToast({ type: 'error', title: 'Rewards', message: 'Rewards may not have saved. Check your balance.', duration: 3000 });
      }
    } else {
      showGameToast({ type: 'error', title: 'Rewards', message: 'No game session — this round will not pay out.', duration: 3000 });
    }
    setShowResults(true);
  }, [playerId, isStandalone, refreshPlayer, invalidatePlayer, invalidateCooldowns]);

  const handleClose = useCallback(() => {
    router.replace('/(tabs)');
  }, []);

  const injectedConfig = `window.SHOOTOUT_CONFIG = { level: ${level}, appMode: true }; true;`;

  if (starting) {
    return (
      <SafeAreaView style={styles.center}>
        <ActivityIndicator size="large" color="#f39c12" />
        <Text style={styles.centerText}>Loading shootout…</Text>
      </SafeAreaView>
    );
  }

  if (startError) {
    return (
      <SafeAreaView style={styles.center}>
        <Text style={styles.errorTitle}>Cannot start shootout</Text>
        <Text style={styles.centerText}>{startError}</Text>
        <TouchableOpacity style={styles.doneButton} onPress={handleClose}>
          <Text style={styles.doneButtonText}>BACK TO MAP</Text>
        </TouchableOpacity>
      </SafeAreaView>
    );
  }

  // The config is injected INTO the HTML itself (right before </head>), not
  // via injectedJavaScriptBeforeContentLoaded. That prop does not reliably
  // fire for source={{html}} inline documents, so the game never saw
  // SHOOTOUT_CONFIG, never entered app mode, never hid the start screen,
  // and never reported results — so QUIT did nothing and no payout landed.
  const gameHtml = GAME_HTML.replace(
    '</head>',
    `<script>window.SHOOTOUT_CONFIG = { level: ${level}, appMode: true };</script></head>`
  );

  return (
    <SafeAreaView style={styles.container}>
      <WebView
        source={{ html: gameHtml }}
        injectedJavaScriptBeforeContentLoaded={injectedConfig}
        onMessage={handleGameMessage}
        javaScriptEnabled
        domStorageEnabled
        allowsInlineMediaPlayback
        mediaPlaybackRequiresUserAction={false}
        style={styles.webview}
      />
      <Modal visible={showResults} transparent animationType="fade">
        <View style={styles.resultsOverlay}>
          <View style={styles.resultsBox}>
            <Text style={styles.resultsTitle}>{resultWon ? '🎯 SHOOTOUT COMPLETE' : '⏱️ TIME UP'}</Text>
            <Text style={styles.resultsSubtitle}>Level {level} • {resultHits} hits • {isStandalone ? 'Practice (50% rewards)' : 'Full rewards'}</Text>
            <View style={styles.resultsStats}>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Cash Earned:</Text>
                <Text style={[styles.resultValue, styles.resultCash]}>${rewards?.cash ?? 0}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>XP Earned:</Text>
                <Text style={[styles.resultValue, styles.resultXP]}>+{rewards?.xp ?? 0}</Text>
              </View>
              <View style={styles.resultRow}>
                <Text style={styles.resultLabel}>Rep Gained:</Text>
                <Text style={[styles.resultValue, styles.resultRep]}>+{rewards?.rep ?? 0}</Text>
              </View>
            </View>
            <TouchableOpacity style={styles.doneButton} onPress={handleClose}>
              <Text style={styles.doneButtonText}>DONE</Text>
            </TouchableOpacity>
          </View>
        </View>
      </Modal>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#0a0a0a' },
  webview: { flex: 1, backgroundColor: '#0a0a0a' },
  center: { flex: 1, backgroundColor: '#0a0a0a', alignItems: 'center', justifyContent: 'center', padding: 24 },
  centerText: { color: '#ccc', fontSize: 16, marginTop: 12, textAlign: 'center' },
  errorTitle: { color: '#e74c3c', fontSize: 20, fontWeight: 'bold', marginBottom: 8, textAlign: 'center' },
  resultsOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.7)', alignItems: 'center', justifyContent: 'center', padding: 20 },
  resultsBox: { width: '100%', maxWidth: 380, backgroundColor: '#1a1a2e', borderRadius: 16, padding: 24, alignItems: 'center' },
  resultsTitle: { color: '#ffd23f', fontSize: 22, fontWeight: 'bold', textAlign: 'center' },
  resultsSubtitle: { color: '#aaa', fontSize: 13, marginTop: 6, textAlign: 'center' },
  resultsStats: { width: '100%', marginTop: 18 },
  resultRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 8, borderBottomWidth: 1, borderBottomColor: '#2c2c44' },
  resultLabel: { color: '#ccc', fontSize: 16 },
  resultValue: { color: '#fff', fontSize: 16, fontWeight: 'bold' },
  resultCash: { color: '#2ecc71' },
  resultXP: { color: '#3498db' },
  resultRep: { color: '#9b59b6' },
  doneButton: { marginTop: 20, backgroundColor: '#27ae60', borderRadius: 10, paddingVertical: 12, paddingHorizontal: 36 },
  doneButtonText: { color: '#fff', fontSize: 18, fontWeight: 'bold', letterSpacing: 1 },
});
