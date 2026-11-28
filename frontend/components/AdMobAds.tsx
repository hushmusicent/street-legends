import React, { useEffect, useRef, useState } from 'react';
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

// AdMob unit IDs for Street Legends — GOOGLE TEST IDs while testing (swap in the live IDs for the release build).
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
  const [note, setNote] = useState('');
  const rewardedRef = useRef<any>(null);
  const grantedRef = useRef(false);
  const timeoutRef = useRef<any>(null);

  const clearLoadTimeout = () => {
    if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
  };

  const resetAd = () => {
    clearLoadTimeout();
    const unsubs = (rewardedRef as any)._unsubs;
    if (unsubs) unsubs.forEach((u: any) => { try { u(); } catch (_) {} });
    rewardedRef.current = null;
    setLoaded(false);
    setBusy(false);
  };

  const startLoadTimeout = () => {
    clearLoadTimeout();
    timeoutRef.current = setTimeout(() => {
      const err = 'Timed out after 15s - no ad response.';
      setNote(err);
      resetAd();
      Alert.alert('Ad Not Available', err);
    }, 15000);
  };

  const setupRewarded = () => {
    if (!ADS_READY || !playerId) return;
    if (rewardedRef.current) return;
    try {
      const rewarded = RewardedAd.createForAdRequest(REWARDED_UNIT_ID);
      rewardedRef.current = rewarded;
      const unsubs = [
        rewarded.addAdEventListener(RewardedAdEventType.LOADED, () => {
          clearLoadTimeout();
          setNote('');
          setLoaded(true);
          setBusy(false);
        }),
        rewarded.addAdEventListener(AdEventType.ERROR, (err: any) => {
          const msg = 'Ad failed to load: ' + (err?.message || JSON.stringify(err) || 'unknown error');
          setNote(msg);
          resetAd();
          Alert.alert('Ad Failed', msg);
        }),
        rewarded.addAdEventListener(AdEventType.CLOSED, () => {
          clearLoadTimeout();
          setLoaded(false);
          setBusy(false);
          grantedRef.current = false;
          rewardedRef.current = null;
          setTimeout(() => { try { setupRewarded(); } catch (_) {} }, 1000);
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
      (rewardedRef as any)._unsubs = unsubs;
      startLoadTimeout();
      rewarded.load();
    } catch (e: any) {
      const msg = 'Could not create ad: ' + (e?.message || String(e));
      setNote(msg);
      setBusy(false);
      Alert.alert('Ad Error', msg);
    }
  };

  // Delayed preload after the Shop mounts.
  useEffect(() => {
    if (!ADS_READY || !playerId) return;
    const t = setTimeout(() => { try { setupRewarded(); } catch (_) {} }, 2000);
    return () => {
      clearTimeout(t);
      resetAd();
    };
  }, [playerId]);

  if (!ADS_READY || !playerId) return null;

  const onPress = () => {
    if (busy) return;
    setNote('Loading ad...');
    if (loaded && rewardedRef.current) {
      setBusy(true);
      grantedRef.current = false;
      try {
        rewardedRef.current.show();
      } catch (e: any) {
        setBusy(false);
        Alert.alert('Ad Not Ready', 'The ad is still loading. Try again in a moment.');
      }
      return;
    }
    // Not loaded yet: fresh ad + load now, with a timeout.
    setBusy(true);
    resetAd();
    setupRewarded();
  };

  return (
    <TouchableOpacity style={[styles.rewardBtn, busy && styles.rewardBtnDisabled]} onPress={onPress} disabled={busy}>
      {busy ? (
        <ActivityIndicator color="#0a0a0a" />
      ) : (
        <Text style={styles.rewardBtnText}>
          {loaded ? 'Watch ad - earn $1,000' : (note ? note : 'Watch ad - earn $1,000')}
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
