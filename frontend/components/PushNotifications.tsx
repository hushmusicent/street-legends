import React, { useEffect, useRef } from 'react';
import { Platform } from 'react-native';
import { router } from 'expo-router';
import { useGameStore } from '../stores/gameStore';
import api from '../services/api';

// Push notifications (Expo). Everything is guarded: if the native module
// is missing or permissions are denied, this component silently does
// nothing and the app keeps working.
let Notifications: any = null;
let Constants: any = null;
try {
  Notifications = require('expo-notifications');
} catch (e) {
  Notifications = null;
}
try {
  Constants = require('expo-constants').default;
} catch (e) {
  Constants = null;
}

if (Notifications) {
  try {
    Notifications.setNotificationHandler({
      handleNotification: async () => ({
        shouldShowAlert: true,
        shouldPlaySound: true,
        shouldSetBadge: false,
      }),
    });
  } catch (e) {
    // Ignore - handler already set or unavailable.
  }
}

export default function PushNotifications() {
  const playerId = useGameStore((s: any) => s.playerId);
  const registeredRef = useRef(false);
  const listenersRef = useRef(false);
  const receivedSubRef = useRef<any>(null);
  const responseSubRef = useRef<any>(null);

  useEffect(() => {
    if (Platform.OS !== 'android' || !Notifications) return;
    // Listeners once per app launch.
    if (!listenersRef.current) {
      listenersRef.current = true;
      try {
        receivedSubRef.current = Notifications.addNotificationReceivedListener(() => {});
      } catch (e) {}
      try {
        responseSubRef.current = Notifications.addNotificationResponseReceivedListener(() => {
          try {
            // Tapping any game notification opens the map (rooms + challenges live there).
            router.push('/(tabs)');
          } catch (e) {}
        });
      } catch (e) {}
    }
    // Register the push token once the player id is known (after login).
    if (!playerId || registeredRef.current) return;
    let cancelled = false;
    (async () => {
      try {
        const { status: existing } = await Notifications.getPermissionsAsync();
        let status = existing;
        if (status !== 'granted') {
          const req = await Notifications.requestPermissionsAsync();
          status = req.status;
        }
        if (status !== 'granted' || cancelled) return;
        const projectId = Constants?.expoConfig?.extra?.eas?.projectId;
        const tokenRes = projectId
          ? await Notifications.getExpoPushTokenAsync({ projectId })
          : await Notifications.getExpoPushTokenAsync();
        const token = tokenRes?.data;
        if (token && !cancelled) {
          await api.post(`/players/${playerId}/push-token`, { push_token: token, platform: 'android' });
          registeredRef.current = true;
        }
      } catch (e) {
        // Silent: no token, no notifications, game keeps working.
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerId]);

  useEffect(() => {
    return () => {
      try { receivedSubRef.current?.remove(); } catch (e) {}
      try { responseSubRef.current?.remove(); } catch (e) {}
    };
  }, []);

  return null;
}
