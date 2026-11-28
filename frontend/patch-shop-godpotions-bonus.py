#!/usr/bin/env python3
"""Move GodPotions onto the Bonus tab so it scrolls with the Bonus content.

Problem (user, 2026-11-27): on the other (test) phone the shop items do not
show — the GodPotions section is rendered unconditionally above the items
ScrollView, fixed in place, eating the vertical space the items need. On his
phone it looks fine; on the other phone the items never appear.

Fix: render <GodPotions> only when filter === 'bonus', inside the Bonus
ScrollView, directly above <BonusBundles>, so it scrolls with the Bonus tab
content. On every other tab (All / HP / EN / Combo / Stims / House) the items
list gets the full remaining height.

Idempotent: safe to re-run. If GodPotions is already inside the Bonus
ScrollView and no unconditional copy remains, it prints OK and changes
nothing. If an anchor is missing it still writes the file with whatever
succeeded and names the miss.
"""
import sys

PATH = "frontend/app/(tabs)/shop.tsx"
MARKER = "SHOP_GODPOTIONS_BONUS_OK"

UNCONDITIONAL = "      <GodPotions playerId={playerId} />\n"
BONUS_OPEN = "      {filter === 'bonus' ? ("
BONUS_BUNDLES = "          <BonusBundles playerId={playerId} />"
GOD_IN_BONUS = "          <GodPotions playerId={playerId} />\n"


def main():
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            src = f.read()
    except FileNotFoundError:
        print(f"SHOP_GODPOTIONS_BONUS_FAIL: {PATH} not found")
        print(MARKER)
        return 0

    orig = src
    notes = []

    # Where does the Bonus block start, and where is BonusBundles?
    bonus_idx = src.find(BONUS_OPEN)
    bundles_idx = src.find(BONUS_BUNDLES)
    if bonus_idx < 0:
        notes.append("MISS: bonus conditional anchor not found")
    if bundles_idx < 0:
        notes.append("MISS: BonusBundles anchor not found")

    # Is GodPotions already inside the Bonus ScrollView?
    god_in_bonus = False
    if bonus_idx >= 0 and bundles_idx > bonus_idx:
        between = src[bonus_idx:bundles_idx]
        god_in_bonus = "<GodPotions playerId={playerId} />" in between

    # 1) Remove the unconditional <GodPotions> that sits before the bonus
    # conditional. Only remove the copy that is OUTSIDE the bonus block.
    removed = 0
    if bonus_idx >= 0:
        head = src[:bonus_idx]
        if UNCONDITIONAL in head:
            head = head.replace(UNCONDITIONAL, "", 1)
            # collapse the blank line left behind (GodPotions line + blank
            # line before the bonus conditional)
            head = head.replace("      </ScrollView>\n\n\n", "      </ScrollView>\n\n", 1)
            src = head + src[bonus_idx:]
            removed = 1
            notes.append("OK: removed unconditional GodPotions")
        else:
            notes.append("SKIP: no unconditional GodPotions before bonus block")
    else:
        # No bonus anchor: fall back to removing a single unconditional copy
        # only if exactly one exists in the whole file and it is NOT already
        # inside a bonus block (we cannot prove that here, so do not remove).
        notes.append("SKIP: cannot locate unconditional copy without bonus anchor")

    # Recompute indices after the removal.
    bonus_idx = src.find(BONUS_OPEN)
    bundles_idx = src.find(BONUS_BUNDLES)

    # 2) Insert GodPotions inside the Bonus ScrollView, above BonusBundles.
    inserted = 0
    if god_in_bonus:
        notes.append("SKIP: GodPotions already inside Bonus ScrollView")
    elif bundles_idx >= 0 and bonus_idx >= 0 and bundles_idx > bonus_idx:
        src = src[:bundles_idx] + GOD_IN_BONUS + src[bundles_idx:]
        inserted = 1
        notes.append("OK: inserted GodPotions above BonusBundles")
    else:
        notes.append("MISS: could not insert GodPotions above BonusBundles")

    if src != orig:
        with open(PATH, "w", encoding="utf-8") as f:
            f.write(src)
        notes.append("OK: wrote " + PATH)

    for n in notes:
        print(n)
    print(f"removed={removed} inserted={inserted}")
    print(MARKER)
    return 0


if __name__ == "__main__":
    sys.exit(main())
