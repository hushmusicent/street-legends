#!/usr/bin/env python3
"""Street Legends diagnostic: Pool game white screen (house + center).

The pool game shows a white screen after PLAY VS COMPUTER in BOTH the
house and the activity center, so the break is in the shared PoolGameModal
/ PoolGameHtml.ts, not in either menu. This prints the live state of the
two files in /app so the cause can be pinned down (no changes made).

Run from /app: python3 frontend/patch-pool-diagnostic.py
"""
import sys
from pathlib import Path

POOL_TS = Path("frontend/components/PoolGameHtml.ts")
IDX = Path("frontend/app/(tabs)/index.tsx")
if not IDX.exists():
    IDX = Path("frontend/app/index.tsx")


def main():
    print("=== POOL DIAGNOSTIC ===")
    # 1. PoolGameHtml.ts
    if POOL_TS.exists():
        src = POOL_TS.read_text(errors="ignore")
        print("PoolGameHtml.ts bytes: %d" % len(src))
        print("  has POOL_GAME_HTML export: %s" % ("POOL_GAME_HTML" in src))
        print("  has <canvas: %s" % ("<canvas" in src))
        print("  has endGame: %s" % ("function endGame" in src))
        print("  has center_prize_win: %s" % ("center_prize_win" in src))
        print("  has YOU WIN Table cleared: %s" % ("YOU WIN! Table cleared!" in src))
        print("  has <script>: %s" % ("<script>" in src))
        print("  has </script>: %s" % ("</script>" in src))
        # rough JS balance inside the script tag
        import re
        m = re.search(r"<script>([\s\S]*?)</script>", src)
        if m:
            js = m.group(1)
            print("  script bytes: %d  braces {%d/%d} parens (%d/%d)" % (
                len(js), js.count("{"), js.count("}"), js.count("("), js.count(")")))
        else:
            print("  script tag NOT FOUND")
    else:
        print("PoolGameHtml.ts MISSING")
    # 2. index.tsx PoolGameModal
    if IDX.exists():
        src = IDX.read_text(errors="ignore")
        print("index.tsx bytes: %d" % len(src))
        print("  has PoolGameModal: %s" % ("const PoolGameModal" in src))
        print("  has PoolWebView require: %s" % ("require('react-native-webview')" in src))
        print("  has POOL_GAME_HTML import: %s" % ("POOL_GAME_HTML" in src))
        print("  has poolGameOpen state: %s" % ("const [poolGameOpen" in src))
        print("  has PoolGameModal render: %s" % ("<PoolGameModal visible={poolGameOpen}" in src))
        print("  PoolGameModal has playerId prop: %s" % ("PoolGameModal = ({ visible, onClose, playerId }" in src))
        print("  PoolGameModal has handlePrizeMsg: %s" % ("handlePrizeMsg" in src))
        print("  awardCenterPrize imported: %s" % ("awardCenterPrize" in src))
        # the WebView source line for pool
        i = src.find("source={{ html: POOL_GAME_HTML }}")
        print("  pool WebView source line: %s" % (i != -1))
        if i != -1:
            seg = src[i:i+500]
            print("  pool onMessage is handlePrizeMsg: %s" % ("onMessage={handlePrizeMsg}" in seg))
            print("  pool onMessage is close-only: %s" % ("onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}" in seg))
    else:
        print("index.tsx MISSING")
    print("POOL_DIAGNOSTIC_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
