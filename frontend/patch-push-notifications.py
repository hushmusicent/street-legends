"""Street Legends frontend: push notifications (Expo).
Run from /app: python3 frontend/patch-push-notifications.py
Idempotent - safe to re-run.

What it adds:
- New file frontend/components/PushNotifications.tsx: requests notification
  permission, gets the Expo push token, POSTs it to the backend, and
  handles notification taps (opens the map tab). Renders nothing.
  Every step is guarded: if expo-notifications is missing or permission
  is denied, the component silently does nothing - it can NOT white-screen
  the app (same guarded-require pattern as GodPotions.tsx).
- Mounts <PushNotifications /> in frontend/app/_layout.tsx (root layout,
  so it runs on every screen).
- Adds "expo-notifications": "~58.0.9" to frontend/package.json (the
  version bundled with Expo SDK 58, which is what the live repo uses).
  The handoff curl also runs `npx expo install expo-notifications` so
  the native module is actually installed before the user reloads Expo Go.

NOTE: push works in Expo Go once installed. For the Play Store build,
FCM credentials must be configured in EAS (google-services.json) or
pushes will not arrive on the store build - that is a separate step.
"""
import sys
from pathlib import Path

COMPONENT_PATH = Path("frontend/components/PushNotifications.tsx")
LAYOUT_PATH = Path("frontend/app/_layout.tsx")
PACKAGE_PATH = Path("frontend/package.json")

COMPONENT = """import React, { useEffect, useRef } from 'react';
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
"""

# ---- Section 2: _layout.tsx import ----
LAYOUT_IMPORT_ANCHOR = """import IdleLogout from '../components/IdleLogout';"""

LAYOUT_IMPORT_NEW = """import IdleLogout from '../components/IdleLogout';
import PushNotifications from '../components/PushNotifications';"""

# ---- Section 3: _layout.tsx mount (inside IdleLogout, next to GameToastProvider) ----
LAYOUT_MOUNT_ANCHOR = """        <GameToastProvider />"""

LAYOUT_MOUNT_NEW = """        <PushNotifications />
        <GameToastProvider />"""

# ---- Section 4: package.json dep (live text: SDK 58) ----
PACKAGE_ANCHOR = '''    "expo-navigation-bar": "~58.0.4",'''

PACKAGE_NEW = '''    "expo-navigation-bar": "~58.0.4",
    "expo-notifications": "~58.0.9",'''


def main():
    # Section 1: write the component file (deterministic content, safe to re-run).
    COMPONENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPONENT_PATH.write_text(COMPONENT)
    print("OK: push component")

    if not LAYOUT_PATH.exists():
        print(f"ERROR: {LAYOUT_PATH} not found. Run from /app.")
        sys.exit(1)
    layout = LAYOUT_PATH.read_text()
    if LAYOUT_IMPORT_NEW in layout:
        print("SKIP: layout import (already applied)")
    elif layout.count(LAYOUT_IMPORT_ANCHOR) == 1:
        layout = layout.replace(LAYOUT_IMPORT_ANCHOR, LAYOUT_IMPORT_NEW, 1)
        print("OK: layout import")
    else:
        print(f"WARNING: anchor matched {layout.count(LAYOUT_IMPORT_ANCHOR)}x — layout import")
    if LAYOUT_MOUNT_NEW in layout:
        print("SKIP: layout mount (already applied)")
    elif layout.count(LAYOUT_MOUNT_ANCHOR) == 1:
        layout = layout.replace(LAYOUT_MOUNT_ANCHOR, LAYOUT_MOUNT_NEW, 1)
        print("OK: layout mount")
    else:
        print(f"WARNING: anchor matched {layout.count(LAYOUT_MOUNT_ANCHOR)}x — layout mount")
    LAYOUT_PATH.write_text(layout)

    if not PACKAGE_PATH.exists():
        print(f"ERROR: {PACKAGE_PATH} not found. Run from /app.")
        sys.exit(1)
    pkg = PACKAGE_PATH.read_text()
    if PACKAGE_NEW in pkg:
        print("SKIP: package.json dep (already applied)")
    elif pkg.count(PACKAGE_ANCHOR) == 1:
        pkg = pkg.replace(PACKAGE_ANCHOR, PACKAGE_NEW, 1)
        print("OK: package.json dep")
    else:
        print(f"WARNING: anchor matched {pkg.count(PACKAGE_ANCHOR)}x — package.json dep")
    PACKAGE_PATH.write_text(pkg)
    print("PUSH_NOTIFICATIONS_FRONTEND_OK")


if __name__ == "__main__":
    main()
