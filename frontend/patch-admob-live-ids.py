"""Street Legends frontend: swap AdMob test IDs back to LIVE IDs.

The rewarded ad flow is proven working on test IDs (banner shows, rewarded
ad plays, 'Reward granted' fires, backend grants $1,000). Time to go live.

Swaps in frontend/components/AdMobAds.tsx:
  Banner:   ca-app-pub-3940256099942544/9214589741  ->  ca-app-pub-1342550857186673/3539848112
  Rewarded: ca-app-pub-3940256099942544/5224354917  ->  ca-app-pub-1342550857186673/8869991021

After this patch: Publish + new Android build (AAB must exceed the last
versionCode), upload to Play Internal testing, install from the test link,
and confirm a live banner shows (no 'Test Ad' label) and a live rewarded
ad plays and grants $1,000.

Run from /app: python3 frontend/patch-admob-live-ids.py
Marker: ADMOB_LIVE_IDS_OK
"""

import io
import sys

PATH = "frontend/components/AdMobAds.tsx"
MARKER = "ADMOB_LIVE_IDS_OK"

TEST_BANNER = "ca-app-pub-3940256099942544/9214589741"
LIVE_BANNER = "ca-app-pub-1342550857186673/3539848112"
TEST_REWARDED = "ca-app-pub-3940256099942544/5224354917"
LIVE_REWARDED = "ca-app-pub-1342550857186673/8869991021"

def main():
    try:
        with io.open(PATH, encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("FAIL: %s not found" % PATH)
        print("ADMOB_LIVE_IDS_FAIL")
        return 1

    if LIVE_BANNER in src and LIVE_REWARDED in src and TEST_BANNER not in src and TEST_REWARDED not in src:
        print("SKIP: live IDs already in place")
        print(MARKER)
        return 0

    changed = []
    if TEST_BANNER in src:
        src = src.replace(TEST_BANNER, LIVE_BANNER)
        changed.append("banner")
    if TEST_REWARDED in src:
        src = src.replace(TEST_REWARDED, LIVE_REWARDED)
        changed.append("rewarded")

    if not changed:
        print("FAIL: neither test ID found in %s" % PATH)
        print("ADMOB_LIVE_IDS_FAIL")
        return 1

    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(src)
    print("OK: swapped test IDs to live IDs (%s)" % ", ".join(changed))
    print(MARKER)
    return 0

if __name__ == "__main__":
    sys.exit(main())
