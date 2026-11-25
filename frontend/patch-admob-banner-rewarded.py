"""Street Legends frontend: AdMob banner + rewarded ads (Expo SDK 58).
Run from /app: python3 frontend/patch-admob-banner-rewarded.py
Idempotent - safe to re-run.

What it adds:
- New file frontend/components/AdMobAds.tsx with two components:
  * AdMobBanner - a large anchored adaptive banner pinned to the bottom
    of the screen on every tab (mounted in the root layout). Hidden on
    login / create-character screens (no player yet) and on web.
  * RewardedAdButton - "Watch ad - earn $1,000" button for the Shop.
    On a completed view it POSTs /ads/rewarded-grant, then re-fetches
    the player so the cash display updates everywhere.
  Every step is guarded: if react-native-google-mobile-ads is missing
  (not installed yet) or the module fails to load, both components
  silently render nothing - they can NOT white-screen the app (same
  guarded-require pattern as GodPotions.tsx / PushNotifications.tsx).
- Adds "react-native-google-mobile-ads": "17.4.0" to
  frontend/package.json. That is the version `npx expo install
  react-native-google-mobile-ads` resolves for Expo SDK 58 (verified
  2026-11-24 against a scratch SDK 58 project). The handoff curl also
  runs `npx expo install react-native-google-mobile-ads` so the native
  module is actually installed before the user reloads Expo Go.
- Adds the AdMob config plugin to frontend/app.json with the Street
  Legends Android App ID. Only androidAppId is set: there is no iOS
  AdMob app, and the plugin only warns (never fails) when iosAppId is
  missing - verified in the plugin source. Android builds are unaffected.
- Mounts <AdMobBanner /> in frontend/app/_layout.tsx (root layout,
  inside IdleLogout, after GameToastProvider) and <RewardedAdButton />
  in frontend/app/(tabs)/shop.tsx (after GodPotions).

Production IDs (never test IDs):
- App ID: ca-app-pub-1342550857186673~4649429004
- Banner: ca-app-pub-1342550857186673/3539848112
- Rewarded: ca-app-pub-1342550857186673/8869991021

NOTE: this is a native SDK change. Expo Go shows ads once the module
is installed, but the Play Store build needs a NEW EAS build + AAB
upload before ads appear there. Also app-ads.txt verification
(hushmusicent.com/app-ads.txt) is still pending, so ad serving will
be limited until that file is in place.
"""
import json
import sys
from pathlib import Path

COMPONENT_PATH = Path("frontend/components/AdMobAds.tsx")
LAYOUT_PATH = Path("frontend/app/_layout.tsx")
SHOP_PATH = Path("frontend/app/(tabs)/shop.tsx")
PACKAGE_PATH = Path("frontend/package.json")
APPJSON_PATH = Path("frontend/app.json")

COMPONENT = """import React, { useEffect, useRef, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Platform,
} from 'react-native';
import api, { getPlayer } from '../services/api';
import { useGameStore } from '../stores/gameStore';

// AdMob unit IDs for Street Legends (production - never test IDs).
const BANNER_UNIT_ID = 'ca-app-pub-1342550857186673/3539848112';
const REWARDED_UNIT_ID = 'ca-app-pub-1342550857186673/8869991021';
const REWARD_CASH = 1000;

// Guarded load of the native ads module: on web, or when the native
// module is not installed yet, everything below silently renders
// nothing. This component must NEVER white-screen the app.
let MobileAdsFn: any = null;
let BannerAd: any = null;
let BannerAdSize: any = null;
let RewardedAd: any = null;
let AdEventType: any = null;
let RewardedAdEventType: any = null;

if (Platform.OS !== 'web') {
  try {
    const ads = require('react-native-google-mobile-ads');
    MobileAdsFn = ads.default || ads.MobileAds;
    BannerAd = ads.BannerAd;
    BannerAdSize = ads.BannerAdSize;
    RewardedAd = ads.RewardedAd;
    AdEventType = ads.AdEventType;
    RewardedAdEventType = ads.RewardedAdEventType;
    if (MobileAdsFn) {
      MobileAdsFn().initialize().catch((e: any) => console.log('AdMob init failed:', e));
    }
  } catch (e) {
    console.log('AdMob not available:', e);
  }
}

const ADS_READY = !!(BannerAd && BannerAdSize && RewardedAd);

/** Banner pinned to the bottom of the screen on every tab. Hidden on the
 *  login / create-character screens (no player yet) and on web. */
export function AdMobBanner() {
  const playerId = useGameStore((s: any) => s.playerId);
  if (!ADS_READY || !playerId) return null;
  return (
    <View style={styles.bannerWrap}>
      <BannerAd
        unitId={BANNER_UNIT_ID}
        size={BannerAdSize.LARGE_ANCHORED_ADAPTIVE_BANNER}
        onAdFailedToLoad={(error: any) => console.log('Banner ad failed to load:', error)}
      />
    </View>
  );
}

/** "Watch ad - earn $1,000" button for the Shop. On a completed view the
 *  backend grants +$1,000 cash and the player record is re-fetched so the
 *  cash display updates everywhere. */
export function RewardedAdButton({ playerId }: { playerId: string | null }) {
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const rewardedRef = useRef<any>(null);
  const grantedRef = useRef(false);

  useEffect(() => {
    if (!ADS_READY || !playerId) return;
    const rewarded = RewardedAd.createForAdRequest(REWARDED_UNIT_ID);
    rewardedRef.current = rewarded;
    const unsubs = [
      rewarded.addAdEventListener(AdEventType.LOADED, () => setLoaded(true)),
      rewarded.addAdEventListener(AdEventType.ERROR, () => {
        setLoaded(false);
        setTimeout(() => { try { rewarded.load(); } catch (_) {} }, 5000);
      }),
      rewarded.addAdEventListener(AdEventType.CLOSED, () => {
        setLoaded(false);
        setBusy(false);
        grantedRef.current = false;
        try { rewarded.load(); } catch (_) {}
      }),
      rewarded.addAdEventListener(RewardedAdEventType.EARNED_REWARD, async () => {
        if (grantedRef.current) return;
        grantedRef.current = true;
        try {
          const res = await api.post('/ads/rewarded-grant', { player_id: playerId });
          const data = res.data || {};
          const p = await getPlayer(playerId);
          useGameStore.getState().setPlayer(p);
          Alert.alert('+$1,000 Cash!', 'Ad reward claimed. Balance: $' + (data.cash ?? p?.cash ?? 0).toLocaleString());
        } catch (e: any) {
          const msg = e?.response?.data?.detail || 'Reward could not be claimed. Try again later.';
          Alert.alert('Reward Failed', String(msg));
        }
      }),
    ];
    try { rewarded.load(); } catch (_) {}
    return () => { unsubs.forEach((u) => { try { u(); } catch (_) {} }); };
  }, [playerId]);

  if (!ADS_READY || !playerId) return null;

  const onPress = () => {
    if (!loaded || busy || !rewardedRef.current) return;
    setBusy(true);
    grantedRef.current = false;
    try {
      rewardedRef.current.show();
    } catch (e) {
      setBusy(false);
      Alert.alert('Ad Not Ready', 'The ad is still loading. Try again in a moment.');
    }
  };

  return (
    <TouchableOpacity style={[styles.rewardBtn, (!loaded || busy) && styles.rewardBtnDisabled]} onPress={onPress} disabled={!loaded || busy}>
      {busy ? (
        <ActivityIndicator color="#0a0a0a" />
      ) : (
        <Text style={styles.rewardBtnText}>
          {loaded ? 'Watch ad - earn $1,000' : 'Loading ad...'}
        </Text>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  bannerWrap: {
    width: '100%',
    backgroundColor: '#0a0a0a',
    alignItems: 'center',
  },
  rewardBtn: {
    backgroundColor: '#f39c12',
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 16,
    alignItems: 'center',
    marginVertical: 8,
  },
  rewardBtnDisabled: {
    opacity: 0.6,
  },
  rewardBtnText: {
    color: '#0a0a0a',
    fontSize: 16,
    fontWeight: 'bold',
  },
});
"""

# ---- Section 2: _layout.tsx import ----
LAYOUT_IMPORT_ANCHOR = """import { GameToastProvider } from '../components/GameToast';"""

LAYOUT_IMPORT_NEW = """import { GameToastProvider } from '../components/GameToast';
import { AdMobBanner } from '../components/AdMobAds';"""

# ---- Section 3: _layout.tsx mount (inside IdleLogout, after GameToastProvider) ----
LAYOUT_MOUNT_ANCHOR = """        <GameToastProvider />"""

LAYOUT_MOUNT_NEW = """        <GameToastProvider />
        <AdMobBanner />"""

# ---- Section 4: shop.tsx import ----
SHOP_IMPORT_ANCHOR = """import { BonusBundles } from '../../components/BonusBundles';"""

SHOP_IMPORT_NEW = """import { BonusBundles } from '../../components/BonusBundles';
import { RewardedAdButton } from '../../components/AdMobAds';"""

# ---- Section 5: shop.tsx mount (after GodPotions) ----
SHOP_MOUNT_ANCHOR = """      <GodPotions playerId={playerId} />"""

SHOP_MOUNT_NEW = """      <GodPotions playerId={playerId} />

      <RewardedAdButton playerId={playerId} />"""

# ---- Section 6: package.json dep (live text: SDK 58) ----
PACKAGE_ANCHOR = '''    "react-native-iap": "^17.1.0",'''

PACKAGE_NEW = '''    "react-native-google-mobile-ads": "17.4.0",
    "react-native-iap": "^17.1.0",'''

# ---- Section 7: app.json AdMob config plugin ----
APPJSON_ANCHOR = '''      "./plugins/withRemoveMediaPermissions.js",
      "./plugins/withBuildConfig.js"'''

APPJSON_NEW = '''      "./plugins/withRemoveMediaPermissions.js",
      "./plugins/withBuildConfig.js",
      [
        "react-native-google-mobile-ads",
        {
          "androidAppId": "ca-app-pub-1342550857186673~4649429004"
        }
      ]'''


def edit_json(path, anchor, new, label):
    """String-edit a JSON file, but only write it back if it stays valid JSON."""
    if not path.exists():
        print(f"ERROR: {path} not found. Run from /app.")
        sys.exit(1)
    text = path.read_text()
    if new in text:
        print(f"SKIP: {label} (already applied)")
        return
    if text.count(anchor) != 1:
        print(f"WARNING: anchor matched {text.count(anchor)}x — {label}")
        return
    edited = text.replace(anchor, new, 1)
    try:
        json.loads(edited)
    except json.JSONDecodeError as e:
        print(f"WARNING: {label} edit would break JSON ({e}) — not written")
        return
    path.write_text(edited)
    print(f"OK: {label}")


def edit_str(text, anchor, new, label):
    """Pure string edit on already-read text. Returns (new_text, changed)."""
    if new in text:
        print(f"SKIP: {label} (already applied)")
        return text, False
    if text.count(anchor) != 1:
        print(f"WARNING: anchor matched {text.count(anchor)}x — {label}")
        return text, False
    print(f"OK: {label}")
    return text.replace(anchor, new, 1), True


def main():
    # Section 1: write the component file (deterministic content, safe to re-run).
    COMPONENT_PATH.parent.mkdir(parents=True, exist_ok=True)
    COMPONENT_PATH.write_text(COMPONENT)
    print("OK: AdMob component")

    # Sections 2-3: root layout import + banner mount.
    if not LAYOUT_PATH.exists():
        print(f"ERROR: {LAYOUT_PATH} not found. Run from /app.")
        sys.exit(1)
    layout = LAYOUT_PATH.read_text()
    layout, _ = edit_str(layout, LAYOUT_IMPORT_ANCHOR, LAYOUT_IMPORT_NEW, "layout import")
    layout, _ = edit_str(layout, LAYOUT_MOUNT_ANCHOR, LAYOUT_MOUNT_NEW, "layout mount")
    LAYOUT_PATH.write_text(layout)

    # Sections 4-5: shop import + rewarded button mount.
    if not SHOP_PATH.exists():
        print(f"ERROR: {SHOP_PATH} not found. Run from /app.")
        sys.exit(1)
    shop = SHOP_PATH.read_text()
    shop, _ = edit_str(shop, SHOP_IMPORT_ANCHOR, SHOP_IMPORT_NEW, "shop import")
    shop, _ = edit_str(shop, SHOP_MOUNT_ANCHOR, SHOP_MOUNT_NEW, "shop mount")
    SHOP_PATH.write_text(shop)

    # Section 6: package.json dep.
    edit_json(PACKAGE_PATH, PACKAGE_ANCHOR, PACKAGE_NEW, "package.json dep")

    # Section 7: app.json AdMob plugin config.
    edit_json(APPJSON_PATH, APPJSON_ANCHOR, APPJSON_NEW, "app.json AdMob plugin")

    print("ADMOB_BANNER_REWARDED_OK")


if __name__ == "__main__":
    main()
