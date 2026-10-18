import React, { useRef, useEffect, useCallback } from 'react';
import { View, AppState } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useRouter, usePathname } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import { logoutPlayer } from '../services/api';

const IDLE_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes

/**
 * Wraps the app and logs the player out after 30 minutes of inactivity.
 * On timeout: tells the backend to hide their character (is_logged_out=True),
 * clears the local session, and sends them to the login screen.
 * Their character disappears from other players' maps until they log back in.
 */
export default function IdleLogout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const playerId = useGameStore((s) => s.playerId);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const loggingOutRef = useRef(false);

  const doLogout = useCallback(async () => {
    if (loggingOutRef.current) return;
    const id = useGameStore.getState().playerId;
    if (!id) return;
    loggingOutRef.current = true;

    try {
      // Tell backend to hide this character from the game world
      await logoutPlayer(id);
    } catch (e) {
      console.warn('Idle logout API call failed:', e);
    }
    try {
      await AsyncStorage.removeItem('playerId');
    } catch (e) {
      console.warn('Failed to clear playerId:', e);
    }
    useGameStore.setState({ playerId: null });
    loggingOutRef.current = false;
    router.replace('/login');
  }, [router]);

  const resetTimer = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    // Don't run the timer on login/create-character screens
    const id = useGameStore.getState().playerId;
    if (!id) return;
    timerRef.current = setTimeout(doLogout, IDLE_TIMEOUT_MS);
  }, [doLogout]);

  // Reset on navigation
  useEffect(() => {
    resetTimer();
  }, [pathname, resetTimer]);

  // Reset when playerId changes (login/logout)
  useEffect(() => {
    resetTimer();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [playerId, resetTimer]);

  // When app goes to background, treat as idle start; on return, reset
  useEffect(() => {
    const sub = AppState.addEventListener('change', (state) => {
      if (state === 'active') {
        resetTimer();
      }
    });
    return () => sub.remove();
  }, [resetTimer]);

  return (
    <View
      style={{ flex: 1 }}
      // Any touch anywhere counts as activity
      onTouchStart={resetTimer}
    >
      {children}
    </View>
  );
}
