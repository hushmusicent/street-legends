#!/usr/bin/env python3
"""Street Legends frontend: fix game-modal onMessage (pool white screen + payout).

The pool diagnostic showed the PoolGameModal's WebView onMessage is
NEITHER handlePrizeMsg NOR the original close-only handler — so the
win post is never handled (no payout) and the modal's message wiring
is in an unknown state. The same break may affect the other five
table-game modals (v3's onMessage replacement did not land for them).

This patch, per modal, finds the WebView's onMessage prop inside that
modal's own body and sets it to onMessage={handlePrizeMsg}. The handler
itself (v3) is already defined in each modal; this only repairs the
prop that calls it. Idempotent: a modal already on handlePrizeMsg is
skipped. It does NOT touch signatures, banners, render sites or api.ts.

Run from /app: python3 frontend/patch-center-prize-onmessage-v5.py
Frontend only: reload Expo Go after running, then open Pool and win a
center game.
"""
import re
import sys
from pathlib import Path

IDX = Path("frontend/app/(tabs)/index.tsx")
if not IDX.exists():
    IDX = Path("frontend/app/index.tsx")
MARKER = "CENTER_PRIZE_ONMESSAGE_V5_OK"

MODALS = [
    "PoolGameModal",
    "DartGameModal",
    "CardGameModal",
    "DominoGameModal",
    "ScrabbleGameModal",
    "ChessCheckersGameModal",
]

# onMessage={...} with up to one level of nested braces (covers the
# close-only arrow function `{(event) => { if (...) ... }}`).
ONMSG_RE = re.compile(r"onMessage=\{(?:[^{}]|\{[^{}]*\})*\}")


def _balance(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"), s.count("["), s.count("]"))


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - onMessage NOT repaired")
        return 1
    src = IDX.read_text(errors="ignore")
    orig = src
    landed = []
    warnings = []
    for name in MODALS:
        sig = src.find("const %s = ({" % name)
        if sig == -1:
            warnings.append("%s not found - onMessage NOT repaired" % name)
            continue
        # Modal body ends at the next top-level modal/component definition.
        nxt = src.find("\nconst ", sig + 10)
        end = nxt if nxt != -1 else len(src)
        body = src[sig:end]
        m = ONMSG_RE.search(body)
        if not m:
            warnings.append("%s onMessage prop not found - NOT repaired" % name)
            continue
        if m.group(0) == "onMessage={handlePrizeMsg}":
            print("%s_ONMESSAGE_ALREADY_APPLIED" % name.upper())
            landed.append(name)
            continue
        # Replace just this modal's onMessage (first match in its body).
        body2, n = ONMSG_RE.subn("onMessage={handlePrizeMsg}", body, count=1)
        if n == 1:
            src = src[:sig] + body2 + src[end:]
            print("OK: %s onMessage -> handlePrizeMsg (was: %s)" % (name, m.group(0)[:90]))
            landed.append(name)
        else:
            warnings.append("%s onMessage replace failed" % name)
    if not landed:
        print("CENTER_PRIZE_ONMESSAGE_V5_PARTIAL: nothing landed")
        return 1
    after = _balance(src)
    if after[0] != after[1] or after[2] != after[3] or after[4] != after[5]:
        print("CENTER_PRIZE_ONMESSAGE_V5_BALANCE_FAIL: brackets unbalanced %s (index.tsx NOT written)" % (after,))
        return 1
    if src != orig:
        IDX.write_text(src)
    for w in warnings:
        print("WARNING: " + w)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
