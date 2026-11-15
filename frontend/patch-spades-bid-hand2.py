#!/usr/bin/env python3
"""Spades bid fix: bid buttons missing on Hand 2+ (PvC).

BUG: In CARD TABLE - SPADES - YOU vs CPU, the bid buttons (NIL, 1..13)
only appear on Hand 1. On Hand 2 the message says "Hand 2. Place your
bid (0 = Nil)." but no buttons ever show, so the player cannot bid.

ROOT CAUSE: the dealer rotates, so on Hand 1 the human (seat 0) is the
first bidder (leader = (dealer+1)%4 = 0) and the buttons render at hand
start. On Hand 2 the leader is West (seat 1): spNewHand() calls
spRenderBidRow(), which returns early because SP.turn is 1, then the CPU
bids run. But spBid() NEVER advances SP.turn while bidding - it stays
at the leader. When the turn comes back to the human, spBid() calls
spRenderBidRow(), which still sees SP.turn = 1 and refuses to render,
and even a tap would be rejected by spBid()'s guard
(if (p === 0 && SP.turn !== 0) return). Hands 2, 3 and 4 all break;
only hands where the human leads work.

FIX (one line, PvC only): in spBid(), set SP.turn = next when advancing
to the next bidder, before the next===0 branch. When the turn reaches
the human, SP.turn is 0, spRenderBidRow() renders the buttons and the
tap passes the guard. When all bids are in, the existing line
SP.turn = SP.leader overwrites it for play, so play is unaffected.
PvP Spades does NOT have this bug (its log replay sets SP.turn to the
waiting seat), so CardPvpHtml.ts is left alone.

Targeted edit only - it does NOT rewrite the game HTML, so the
fill-screen layout and the last-card fix in the live file are kept.

Run from /app (repo root):
  cd /app && curl -sL "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/patch-spades-bid-hand2.py?v=1" -o frontend/patch-spades-bid-hand2.py && python3 frontend/patch-spades-bid-hand2.py
Expect: SPADES_BID_HAND2_OK
Then reload Expo Go and play Spades to Hand 2: the bid buttons must
appear when it is your turn to bid.
"""
from pathlib import Path

TS = Path("frontend/components/CardSpadesHtml.ts")

OLD = """    if (SP.turn !== 0) spCpuTurn();
    return;
  }
  if (next === 0) { SP.phase = 'bid'; spRenderBidRow(); spRender(); }"""

NEW = """    if (SP.turn !== 0) spCpuTurn();
    return;
  }
  SP.turn = next;
  if (next === 0) { SP.phase = 'bid'; spRenderBidRow(); spRender(); }"""


def main():
    if not TS.exists():
        print("SPADES_BID_HAND2_ERROR: %s not found. Run from /app (repo root). Nothing changed." % TS)
        return
    src = TS.read_text()
    if "SP.turn = next;" in src and OLD not in src:
        print("SPADES_BID_HAND2_ALREADY_APPLIED")
        return
    n = src.count(OLD)
    if n != 1:
        print("SPADES_BID_HAND2_ERROR: bid anchor found %d times (expected 1). Nothing changed." % n)
        return
    TS.write_text(src.replace(OLD, NEW, 1))
    check = TS.read_text()
    if "SP.turn = next;" in check and check.count("if (next === 0) { SP.phase = 'bid'; spRenderBidRow(); spRender(); }") == 1:
        print("SPADES_BID_HAND2_OK")
    else:
        print("SPADES_BID_HAND2_ERROR: verification failed after write.")


if __name__ == "__main__":
    main()
