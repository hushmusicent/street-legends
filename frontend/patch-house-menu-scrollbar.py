#!/usr/bin/env python3
"""Street Legends frontend patch: visible side scrollbar on the
house interior Games/Appliances/Utilities menu, so players know
the list scrolls (Scrabble sits below Dominoes and was missed
because the menu hid its scrollbar).

What it changes (frontend / Expo Go, no backend Deploy needed):
  In frontend/app/(tabs)/index.tsx, the menu ScrollView that
  renders (HOUSE_ITEMS[houseItemCategory] || []).map(...) currently
  has showsVerticalScrollIndicator={false}, which hides the side
  scrollbar. This patch changes ONLY that ScrollView to
  showsVerticalScrollIndicator={true} and adds
  persistentScrollbar={true} (Android: scrollbar stays visible,
  not just while scrolling), so the side scroll bar is always
  there and players know to scroll.

  It does NOT touch other ScrollViews (e.g. the interior room's
  horizontal ScrollView, which uses showsHorizontalScrollIndicator).

Idempotent: re-running finds the already-true scrollbar and
changes nothing, still prints OK.

Run from /app: python3 frontend/patch-house-menu-scrollbar.py
Then reload Expo Go (fresh open) to see the side scrollbar.
Prints HOUSE_MENU_SCROLLBAR_OK at the end.
"""
import glob
import re
import sys


def main():
    path = None
    src = None
    for p in sorted(glob.glob("frontend/app/**/*.tsx", recursive=True)):
        try:
            with open(p, "r", encoding="utf-8", errors="replace") as f:
                s = f.read()
        except FileNotFoundError:
            continue
        if "HOUSE_ITEMS[houseItemCategory]" in s and "showsVerticalScrollIndicator" in s:
            path, src = p, s
            break
    if not path:
        print("WARNING: no file with HOUSE_ITEMS[houseItemCategory] + showsVerticalScrollIndicator")
        return 0
    print("FILE: %s" % path)
    lines = src.split("\n")
    # Find the HOUSE_ITEMS map line, then search backwards for the
    # menu ScrollView (showsVerticalScrollIndicator) before it.
    map_idx = None
    for i, ln in enumerate(lines):
        if "HOUSE_ITEMS[houseItemCategory]" in ln and ".map(" in ln:
            map_idx = i
            break
    if map_idx is None:
        print("WARNING: HOUSE_ITEMS[houseItemCategory] .map line not found")
        return 0
    scroll_idx = None
    for i in range(map_idx, max(-1, map_idx - 30), -1):
        if "<ScrollView" in lines[i] and "showsVerticalScrollIndicator" in lines[i]:
            scroll_idx = i
            break
        if "<ScrollView" in lines[i] and i > 0:
            # ScrollView tag may span lines; check the tag block.
            block = "\n".join(lines[max(0, i - 2):i + 3])
            if "showsVerticalScrollIndicator" in block:
                scroll_idx = i
                break
    if scroll_idx is None:
        print("WARNING: menu ScrollView with showsVerticalScrollIndicator not found before HOUSE_ITEMS map (line %d)" % (map_idx + 1))
        return 0
    print("MENU SCROLLVIEW at line %d: %s" % (scroll_idx + 1, lines[scroll_idx].strip()[:160]))
    old = lines[scroll_idx]
    new = old
    if "showsVerticalScrollIndicator={false}" in new:
        new = new.replace("showsVerticalScrollIndicator={false}", "showsVerticalScrollIndicator={true}")
        print("OK: showsVerticalScrollIndicator false -> true")
    elif "showsVerticalScrollIndicator={true}" in new:
        print("SKIP: showsVerticalScrollIndicator already true")
    else:
        # No explicit prop on this line; add it to the ScrollView tag.
        new = new.replace("<ScrollView", "<ScrollView showsVerticalScrollIndicator={true}", 1)
        print("OK: added showsVerticalScrollIndicator={true}")
    if "persistentScrollbar" not in new:
        # Insert persistentScrollbar right after the ScrollView tag name
        # (or after showsVerticalScrollIndicator) so Android keeps it visible.
        if "showsVerticalScrollIndicator={true}" in new:
            new = new.replace("showsVerticalScrollIndicator={true}", "showsVerticalScrollIndicator={true} persistentScrollbar={true}", 1)
        else:
            new = new.replace("<ScrollView", "<ScrollView persistentScrollbar={true}", 1)
        print("OK: added persistentScrollbar={true}")
    else:
        print("SKIP: persistentScrollbar already present")
    if new != old:
        lines[scroll_idx] = new
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print("OK: wrote %s (line %d updated)" % (path, scroll_idx + 1))
    else:
        print("OK: no change needed (already visible scrollbar)")
    print("HOUSE_MENU_SCROLLBAR_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
