#!/usr/bin/env python3
"""Street Legends frontend: Activity Center cash prizes — render sites v4.

The v3 patch wired the six table-game modals (signature + handlePrizeMsg
+ onMessage + banner) but the payout still does not land. The remaining
break is the RENDER call sites: the modals are rendered WITHOUT
playerId, so inside each modal playerId is undefined and handlePrizeMsg
silently skips the award (its `&& playerId` check fails). No error, no
banner, no payout — exactly the reported symptom.

This patch adds playerId={playerId} to the six render call sites.
It does NOT touch the modal signatures, handlers, onMessage or banners
(those are already applied — v3 reports ALREADY_APPLIED). Idempotent:
a render site already passing playerId is skipped.

Run from /app: python3 frontend/patch-center-prize-render-v4.py
Frontend only: reload Expo Go after running, then win a center game.
"""
import sys
from pathlib import Path

IDX = Path("frontend/app/(tabs)/index.tsx")
if not IDX.exists():
    IDX = Path("frontend/app/index.tsx")
MARKER = "CENTER_PRIZE_RENDER_V4_OK"

# (modal name, render old, render new)
RENDERS = [
    (
        "PoolGameModal",
        "<PoolGameModal visible={poolGameOpen} onClose={() => setPoolGameOpen(false)} />",
        "<PoolGameModal visible={poolGameOpen} onClose={() => setPoolGameOpen(false)} playerId={playerId} />",
    ),
    (
        "DartGameModal",
        "<DartGameModal visible={dartGameOpen} onClose={() => setDartGameOpen(false)} />",
        "<DartGameModal visible={dartGameOpen} onClose={() => setDartGameOpen(false)} playerId={playerId} />",
    ),
    (
        "CardGameModal",
        "<CardGameModal visible={cardGameOpen} onClose={() => setCardGameOpen(false)} game={cardGame} />",
        "<CardGameModal visible={cardGameOpen} onClose={() => setCardGameOpen(false)} game={cardGame} playerId={playerId} />",
    ),
    (
        "DominoGameModal",
        "<DominoGameModal visible={dominoGameOpen} onClose={() => setDominoGameOpen(false)} />",
        "<DominoGameModal visible={dominoGameOpen} onClose={() => setDominoGameOpen(false)} playerId={playerId} />",
    ),
    (
        "ScrabbleGameModal",
        "<ScrabbleGameModal visible={scrabbleGameOpen} onClose={() => setScrabbleGameOpen(false)} />",
        "<ScrabbleGameModal visible={scrabbleGameOpen} onClose={() => setScrabbleGameOpen(false)} playerId={playerId} />",
    ),
    (
        "ChessCheckersGameModal",
        "<ChessCheckersGameModal visible={chessCheckersGameOpen} onClose={() => setChessCheckersGameOpen(false)} />",
        "<ChessCheckersGameModal visible={chessCheckersGameOpen} onClose={() => setChessCheckersGameOpen(false)} playerId={playerId} />",
    ),
]


def _balance(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"), s.count("["), s.count("]"))


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - render playerId NOT added")
        return 1
    src = IDX.read_text(errors="ignore")
    orig = src
    landed = []
    warnings = []
    for name, old, new in RENDERS:
        if new in src:
            print("%s_RENDER_ALREADY_APPLIED" % name.upper())
            landed.append(name)
            continue
        if old in src:
            src = src.replace(old, new, 1)
            print("OK: %s render now passes playerId" % name)
            landed.append(name)
        else:
            warnings.append("%s render call not found - playerId NOT passed" % name)
    if not landed:
        print("CENTER_PRIZE_RENDER_V4_PARTIAL: nothing landed")
        return 1
    after = _balance(src)
    if after[0] != after[1] or after[2] != after[3] or after[4] != after[5]:
        print("CENTER_PRIZE_RENDER_V4_BALANCE_FAIL: brackets unbalanced %s (index.tsx NOT written)" % (after,))
        return 1
    if src != orig:
        IDX.write_text(src)
    for w in warnings:
        print("WARNING: " + w)
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
