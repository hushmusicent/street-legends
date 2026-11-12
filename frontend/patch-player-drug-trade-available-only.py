#!/usr/bin/env python3
"""Drug trade: only what players actually hold can be sold or bought.

User correction (2026-11-12): "players can only sell and buy what players
have available, not just any drugs."

The v1 trade modal listed ALL 5 drugs on both sides (including 0 oz) and
let the qty picker run up to 10 even when the seller only held 2 oz
(the confirm button just disabled with an error). This fix:

  1. Each side's list shows ONLY drugs with qty > 0. A drug nobody holds
     never appears as a row you can tap.
  2. The qty +/- picker caps at min(10, oz actually held), so you cannot
     even select more than is available.
  3. If a side holds nothing at all, a "no drugs" line shows instead of
     an empty list.

Backend already enforces availability (400 when the seller lacks the oz),
so this is a FRONTEND-ONLY change. Requires the v1 trade frontend patch
(patch-player-drug-trade-frontend.py) to have been run first — it fails
clearly if the trade modal is not present.

FRONTEND — Expo Go first. Marker: TRADE_AVAILABLE_ONLY_OK
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")

# (old, new) replacements, applied in order. Each must match exactly once.
REPLACEMENTS = [
    # 1. YOUR DRUGS list: only show drugs you actually hold.
    (
        "{tradeMyDrugs.map((d: any) => (",
        "{tradeMyDrugs.filter((d: any) => d.qty > 0).map((d: any) => (",
    ),
    # 2. Empty state for YOUR side, right after your list, before the sell box.
    (
        """                    ))}
                    {tradeSellItem && (""",
        """                    ))}
                    {tradeMyDrugs.filter((d: any) => d.qty > 0).length === 0 && (
                      <Text style={styles.tradeError}>You have no drugs to sell.</Text>
                    )}
                    {tradeSellItem && (""",
    ),
    # 3. Sell qty + caps at min(10, oz you hold) — cannot pick more than held.
    (
        "onPress={() => setTradeSellQty((q: number) => Math.min(10, q + 1))}",
        "onPress={() => setTradeSellQty((q: number) => Math.min(10, (tradeMyDrugs.find((x: any) => x.item_id === tradeSellItem)?.qty || 1), q + 1))}",
    ),
    # 4. THEIR DRUGS list: only show drugs they actually hold.
    (
        "{tradeTheirDrugs.map((d: any) => (",
        "{tradeTheirDrugs.filter((d: any) => d.qty > 0).map((d: any) => (",
    ),
    # 5. Empty state for THEIR side, right after their list, before the buy box.
    (
        """                    ))}
                    {tradeBuyItem && (""",
        """                    ))}
                    {tradeTheirDrugs.filter((d: any) => d.qty > 0).length === 0 && (
                      <Text style={styles.tradeError}>{tradeTarget.name} has no drugs to sell.</Text>
                    )}
                    {tradeBuyItem && (""",
    ),
    # 6. Buy qty + caps at min(10, oz they hold) — cannot pick more than held.
    (
        "onPress={() => setTradeBuyQty((q: number) => Math.min(10, q + 1))}",
        "onPress={() => setTradeBuyQty((q: number) => Math.min(10, (tradeTheirDrugs.find((x: any) => x.item_id === tradeBuyItem)?.qty || 1), q + 1))}",
    ),
    # 7. Subtitle says the rule plainly.
    (
        "with {tradeTarget.name} • Regular price • 1-10 oz per trade",
        "with {tradeTarget.name} • Regular price • Only what each player holds • 1-10 oz per trade",
    ),
]


def main():
    if not INDEX.exists():
        print("TRADE_AVAILABLE_ONLY_FAIL frontend/app/(tabs)/index.tsx not found")
        return 1
    src = INDEX.read_text(encoding="utf-8")
    if "TRADE DRUGS" not in src or "tradeMyDrugs" not in src:
        print("TRADE_AVAILABLE_ONLY_FAIL trade modal not found — run patch-player-drug-trade-frontend.py first")
        return 1
    if "tradeMyDrugs.filter((d: any) => d.qty > 0)" in src:
        print("TRADE_AVAILABLE_ONLY_ALREADY_APPLIED")
        return 0
    for old, _new in REPLACEMENTS:
        count = src.count(old)
        if count != 1:
            print("TRADE_AVAILABLE_ONLY_FAIL anchor not found exactly once (%d): %s" % (count, old[:70]))
            return 1
    for old, new in REPLACEMENTS:
        src = src.replace(old, new, 1)
    for needle in (
        "tradeMyDrugs.filter((d: any) => d.qty > 0)",
        "tradeTheirDrugs.filter((d: any) => d.qty > 0)",
        "You have no drugs to sell.",
        "has no drugs to sell.",
        "Only what each player holds",
    ):
        if needle not in src:
            print("TRADE_AVAILABLE_ONLY_FAIL missing after edit: %s" % needle)
            return 1
    if src.count("{") != src.count("}"):
        print("TRADE_AVAILABLE_ONLY_FAIL unbalanced braces after edit")
        return 1
    INDEX.write_text(src, encoding="utf-8")
    print("TRADE_AVAILABLE_ONLY_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
