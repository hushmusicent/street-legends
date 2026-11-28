"""Street Legends frontend: rewarded ad - delayed preload + load timeout.

Problem: the lazy tap-to-load rewarded ad never loads. The button spins
forever: neither LOADED nor ERROR fires after load() is called. The test
rewarded ID is confirmed correct in /app, and the banner works, so the SDK
is fine -- the rewarded load itself hangs.

Fix: preload the rewarded ad 2 seconds after the Shop mounts (delayed so it
does not collide with the Shop's initial render, which is what crashed the
Shop before), and add a 15-second load timeout so the button never spins
forever. On timeout or error the button resets and can be tapped to retry.

Run from /app: python3 frontend/patch-admob-rewarded-timeout.py
Marker: ADMOB_REWARDED_TIMEOUT_OK
"""

import io
import sys

PATH = "frontend/components/AdMobAds.tsx"
MARKER = "ADMOB_REWARDED_TIMEOUT_OK"

NEW_FN = '''export function RewardedAdButton({ playerId }: { playerId: string | null }) {
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const rewardedRef = useRef<any>(null);
  const grantedRef = useRef(false);
  const timeoutRef = useRef<any>(null);

  const clearLoadTimeout = () => {
    if (timeoutRef.current) { clearTimeout(timeoutRef.current); timeoutRef.current = null; }
  };

  const startLoadTimeout = () => {
    clearLoadTimeout();
    timeoutRef.current = setTimeout(() => {
      // Ad never loaded: stop spinning so the player can retry.
      setLoaded(false);
      setBusy(false);
      Alert.alert('Ad Not Available', 'The ad did not load. Check your connection and try again.');
    }, 15000);
  };

  // Create + load the rewarded ad. Delayed preload (2s after the Shop
  // mounts) so it does not collide with the Shop's initial render.
  const setupRewarded = () => {
    if (!ADS_READY || !playerId) return;
    if (rewardedRef.current) return;
    try {
      const rewarded = RewardedAd.createForAdRequest(REWARDED_UNIT_ID);
      rewardedRef.current = rewarded;
      const unsubs = [
        rewarded.addAdEventListener(AdEventType.LOADED, () => {
          clearLoadTimeout();
          setLoaded(true);
          setBusy(false);
        }),
        rewarded.addAdEventListener(AdEventType.ERROR, () => {
          clearLoadTimeout();
          setLoaded(false);
          setBusy(false);
        }),
        rewarded.addAdEventListener(AdEventType.CLOSED, () => {
          clearLoadTimeout();
          setLoaded(false);
          setBusy(false);
          grantedRef.current = false;
          rewardedRef.current = null;
          // Preload the next one so the button is ready again.
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
    } catch (_) {
      setBusy(false);
    }
  };

  // Delayed preload after the Shop mounts.
  useEffect(() => {
    if (!ADS_READY || !playerId) return;
    const t = setTimeout(() => { try { setupRewarded(); } catch (_) {} }, 2000);
    return () => {
      clearTimeout(t);
      clearLoadTimeout();
      const unsubs = (rewardedRef as any)._unsubs;
      if (unsubs) unsubs.forEach((u: any) => { try { u(); } catch (_) {} });
    };
  }, [playerId]);

  if (!ADS_READY || !playerId) return null;

  const onPress = () => {
    if (busy) return;
    if (loaded && rewardedRef.current) {
      setBusy(true);
      grantedRef.current = false;
      try {
        rewardedRef.current.show();
      } catch (e) {
        setBusy(false);
        Alert.alert('Ad Not Ready', 'The ad is still loading. Try again in a moment.');
      }
      return;
    }
    // Not loaded yet: (re)create + load now, with a timeout.
    setBusy(true);
    rewardedRef.current = null;
    setupRewarded();
    startLoadTimeout();
  };

  return (
    <TouchableOpacity style={[styles.rewardBtn, busy && styles.rewardBtnDisabled]} onPress={onPress} disabled={busy}>
      {busy ? (
        <ActivityIndicator color="#0a0a0a" />
      ) : (
        <Text style={styles.rewardBtnText}>
          {loaded ? 'Watch ad - earn $1,000' : 'Watch ad - earn $1,000'}
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
        print("ADMOB_REWARDED_TIMEOUT_FAIL")
        return 1

    if "startLoadTimeout" in src and "Delayed preload after the Shop mounts" in src:
        print("SKIP: rewarded timeout/preload already in place")
        print(MARKER)
        return 0

    start_marker = "export function RewardedAdButton({ playerId }: { playerId: string | null }) {"
    start = src.find(start_marker)
    if start < 0:
        print("FAIL: RewardedAdButton function start not found")
        print("ADMOB_REWARDED_TIMEOUT_FAIL")
        return 1

    end_marker = "\n}\n\nconst styles"
    end = src.find(end_marker, start)
    if end < 0:
        print("FAIL: RewardedAdButton function end not found")
        print("ADMOB_REWARDED_TIMEOUT_FAIL")
        return 1
    end += 2

    new_src = src[:start] + NEW_FN + src[end:]
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("OK: RewardedAdButton replaced with delayed-preload + 15s timeout version")
    print(MARKER)
    return 0

if __name__ == "__main__":
    sys.exit(main())
