"""Street Legends frontend: rewarded ad - surface the real load error.

Problem: the rewarded ad will not load at all. The button either spins
forever or does nothing on tap, and the failure is silent -- the ERROR
event resets the button without saying why, so nobody knows whether the
ad failed to fill, the unit ID is bad, or the SDK rejected the request.

Fix: capture the error object from the ERROR event and show its message in
an Alert, so the exact failure reason is visible on the phone. Also show a
short 'Loading ad...' state on tap so a tap always gives feedback, and
reset the stale ad ref on error/timeout so a retry really creates a fresh ad.

Run from /app: python3 frontend/patch-admob-rewarded-show-error.py
Marker: ADMOB_REWARDED_SHOW_ERROR_OK
"""

import io
import sys

PATH = "frontend/components/AdMobAds.tsx"
MARKER = "ADMOB_REWARDED_SHOW_ERROR_OK"

NEW_FN = '''export function RewardedAdButton({ playerId }: { playerId: string | null }) {
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
        rewarded.addAdEventListener(AdEventType.LOADED, () => {
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
}'''

def main():
    try:
        with io.open(PATH, encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("FAIL: %s not found" % PATH)
        print("ADMOB_REWARDED_SHOW_ERROR_FAIL")
        return 1

    if "Ad failed to load: " in src and "resetAd" in src:
        print("SKIP: rewarded error display already in place")
        print(MARKER)
        return 0

    start_marker = "export function RewardedAdButton({ playerId }: { playerId: string | null }) {"
    start = src.find(start_marker)
    if start < 0:
        print("FAIL: RewardedAdButton function start not found")
        print("ADMOB_REWARDED_SHOW_ERROR_FAIL")
        return 1

    end_marker = "\n}\n\nconst styles"
    end = src.find(end_marker, start)
    if end < 0:
        print("FAIL: RewardedAdButton function end not found")
        print("ADMOB_REWARDED_SHOW_ERROR_FAIL")
        return 1
    end += 2

    new_src = src[:start] + NEW_FN + src[end:]
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("OK: RewardedAdButton replaced with error-surfacing version")
    print(MARKER)
    return 0

if __name__ == "__main__":
    sys.exit(main())
