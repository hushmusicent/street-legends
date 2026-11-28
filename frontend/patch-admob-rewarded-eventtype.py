"""Street Legends frontend: rewarded ad - use RewardedAdEventType.LOADED.

ROOT CAUSE FOUND (from the on-phone error popup): the rewarded ad never
loaded because `RewardedAd.addAdEventListener` rejects `AdEventType.LOADED`
and throws: "use RewardedAdEventType.LOADED instead of AdEventType.LOADED".
That throw is what crashed the Shop on mount (original code), made the
lazy tap do nothing, and made the timeout version silently reset. The
banner works because it never calls addAdEventListener.

Fix: in the RewardedAdButton, listen for LOADED with
`RewardedAdEventType.LOADED` instead of `AdEventType.LOADED`. ERROR and
CLOSED stay on AdEventType (RewardedAdEventType has no ERROR/CLOSED).

Run from /app: python3 frontend/patch-admob-rewarded-eventtype.py
Marker: ADMOB_REWARDED_EVENTTYPE_OK
"""

import io
import sys

PATH = "frontend/components/AdMobAds.tsx"
MARKER = "ADMOB_REWARDED_EVENTTYPE_OK"

OLD = "rewarded.addAdEventListener(AdEventType.LOADED"
NEW = "rewarded.addAdEventListener(RewardedAdEventType.LOADED"

def main():
    try:
        with io.open(PATH, encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print("FAIL: %s not found" % PATH)
        print("ADMOB_REWARDED_EVENTTYPE_FAIL")
        return 1

    if NEW in src and OLD not in src:
        print("SKIP: RewardedAdEventType.LOADED already in use")
        print(MARKER)
        return 0

    if OLD not in src:
        print("FAIL: expected rewarded LOADED listener not found")
        print("ADMOB_REWARDED_EVENTTYPE_FAIL")
        return 1

    count = src.count(OLD)
    new_src = src.replace(OLD, NEW)
    with io.open(PATH, "w", encoding="utf-8") as f:
        f.write(new_src)
    print("OK: replaced %d rewarded LOADED listener(s) with RewardedAdEventType.LOADED" % count)
    print(MARKER)
    return 0

if __name__ == "__main__":
    sys.exit(main())
