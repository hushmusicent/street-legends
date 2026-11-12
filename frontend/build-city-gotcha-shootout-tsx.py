#!/usr/bin/env python3
"""Build the new shootout-simulator.tsx that hosts City Gotcha in a WebView.

The City Gotcha game (city-gotcha-shootout.html) is embedded as a template
literal and loaded in a react-native-webview WebView. The app:
  - starts a backend shootout session on mount (map: routeGameId or
    apiStartShootout; settings: standalone endpoint),
  - injects window.SHOOTOUT_CONFIG = { level } before the game loads,
  - listens for the game's gameOver postMessage, then calls
    apiCompleteShootout(gameId, hits, isStandalone) and shows the results
    modal with the backend cash / XP / rep (50% in settings, full on map),
  - DONE goes straight to the map tab (router.replace), never a white screen.

Run from ~/workspace/street-legends. Writes frontend/app/shootout-simulator.tsx.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML_PATH = ROOT / "city-gotcha-shootout.html"
OUT_PATH = ROOT / "frontend" / "app" / "shootout-simulator.tsx"

TSX_TEMPLATE = '''import React, { useCallback, useEffect, useRef, useState } from 'react';
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
const GAME_HTML = `__GAME_HTML__`;

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
'''


def main():
    if not HTML_PATH.exists():
        print("CITY_GOTCHA_TSX_FAIL city-gotcha-shootout.html not found")
        return 1
    html = HTML_PATH.read_text(encoding="utf-8")
    # The HTML must be safe inside a JS template literal: no backticks, no ${.
    if "`" in html:
        print("CITY_GOTCHA_TSX_FAIL game HTML contains backticks; cannot embed safely")
        return 1
    if "${" in html:
        print("CITY_GOTCHA_TSX_FAIL game HTML contains ${; cannot embed safely")
        return 1
    # The game must report to the app.
    if "ReactNativeWebView.postMessage" not in html or "SHOOTOUT_CONFIG" not in html:
        print("CITY_GOTCHA_TSX_FAIL game HTML lacks app-mode bridge (postMessage / SHOOTOUT_CONFIG)")
        return 1
    tsx = TSX_TEMPLATE.replace("__GAME_HTML__", html)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(tsx, encoding="utf-8")
    print("CITY_GOTCHA_TSX_OK %d bytes" % len(tsx))
    return 0


if __name__ == "__main__":
    sys.exit(main())
