"""Street Legends frontend: make the rewarded ad lazy-load (tap-to-load).

Problem: opening the Shop closes the game. The Shop mounts
<RewardedAdButton>, whose useEffect immediately creates a rewarded ad and
calls load() at mount. That mount-time rewarded-ad load crashes the app
(the banner works fine, so the SDK itself is OK -- it is the rewarded-ad
create/load at Shop mount that kills it).

Fix: do NOT create or load the rewarded ad on mount. Create + load it only
when the player taps the button, then auto-show it once LOADED fires. The
Shop opens cleanly; the ad only touches the native SDK after a tap.

Run from /app: python3 frontend/patch-admob-rewarded-lazy.py
Marker: ADMOB_REWARDED_LAZY_OK
"""

import io
import sys

PATH = "frontend/components/AdMobAds.tsx"
MARKER = "ADMOB_REWARDED_LAZY_OK"

NEW_FN = '''export function RewardedAdButton({ playerId }: { playerId: string | null }) {
  const [loaded, setLoaded] = useState(false);
  const [busy, setBusy] = useState(false);
  const rewardedRef = useRef<any>(null);
  const grantedRef = useRef(false);
  const autoShowRef = useRef(false);

  // Lazy load: do NOT create/load the rewarded ad on mount. Creating it at
  // Shop mount crashed the app. We create + load only when tapped.
  const ensureRewarded = () => {
    if (rewardedRef.current) return rewardedRef.current;
    if (!ADS_READY || !playerId) return null;
    try {
      const rewarded = RewardedAd.createForAdRequest(REWARDED_UNIT_ID);
      rewardedRef.current = rewarded;
      const unsubs = [
        rewarded.addAdEventListener(AdEventType.LOADED, () => {
          setLoaded(true);
          if (autoShowRef.current) {
            autoShowRef.current = false;
            grantedRef.current = false;
            try { rewarded.show(); } catch (_) { setBusy(false); }
          }
        }),
        rewarded.addAdEventListener(AdEventType.ERROR, () => {
          setLoaded(false);
          setBusy(false);
          autoShowRef.current = false;
        }),
        rewarded.addAdEventListener(AdEventType.CLOSED, () => {
          setLoaded(false);
          setBusy(false);
          grantedRef.current = false;
          autoShowRef.current = false;
          rewardedRef.current = null;
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
      return rewarded;
    } catch (_) {
      return null;
    }
  };

  useEffect(() => {
    return () => {
      const unsubs = (rewardedRef as any)._unsubs;
      if (unsubs) unsubs.forEach((u: any) => { try { u(); } catch (_) {} });
    };
  }, []);

  if (!ADS_READY || !playerId) return null;

  const onPress = () => {
    if (busy) return;
    setBusy(true);
    const rewarded = ensureRewarded();
    if (!rewarded) { setBusy(false); return; }
    if (loaded) {
      grantedRef.current = false;
      try { rewarded.show(); } catch (_) { setBusy(false); }
      return;
    }
    // Load now; the LOADED handler auto-shows.
    autoShowRef.current = true;
    try { rewarded.load(); } catch (_) { setBusy(false); autoShowRef.current = false; }
  };

  return (
    <TouchableOpacity style={[styles.rewardBtn, busy && styles.rewardBtnDisabled]} onPress={onPress} disabled={busy}>
      {busy ? (
        <ActivityIndicator color="#0a0a0a" />
      ) : (
        <Text style={styles.rewardBtnText}>Watch ad - earn $1,000</Text>
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
        print("ADMOB_REWARDED_LAZY_FAIL")
        return 1

    if "autoShowRef" in src and "Lazy load: do NOT create/load the rewarded ad on mount" in src:
        print("SKIP: lazy rewarded ad already in place")
        print(MARKER)
        return 0

    start_marker = "export function RewardedAdButton({ playerId }: { playerId: string | null }) {"
    start = src.find(start_marker)
    if start < 0:
        print("FAIL: RewardedAdButton function start not found")
        print("ADMOB_REWARDED_LAZY_FAIL")
        return 1

    # The function ends at the closing brace right before "\n\nconst styles".
    end_marker = "\n}\n\nconst styles"
    end = src.find(end_marker, start)
    if end < 0:
        print("FAIL: RewardedAdButton function end not found")
        print("ADMOB_REWARDED_LAZY_FAIL")
        return 1
    end += 2  # include the closing "}\n" (end points at "\n}", so +2 covers "}\n")

    new_src = src[:start] + NEW_FN + src[end:]
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("OK: RewardedAdButton replaced with lazy tap-to-load version")
    print(MARKER)
    return 0

if __name__ == "__main__":
    sys.exit(main())
