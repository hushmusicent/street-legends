#!/usr/bin/env python3
"""Street Legends diagnostic (READ-ONLY, no writes): how does the
house interior Games list actually render?

Why: the backend is live and the file has a Scrabble entry, but the
Games list still shows only Pool/Dartboard/Card/Dominoes. The previous
diagnostic proved the Games list is NOT a .map over a literal array
in index.tsx (its .map lists are all map-screen lists: territories,
nearbyShops, etc.). So the Games list must render another way:
hardcoded JSX cards, a FlatList, a different file/component, or a
dynamic list from state/backend. Guessing again would miss like v1/v2.

What this prints (no writes):
  1. Every frontend file containing BOTH "PLACED" and "Pool Table"
     (the house Games list render, not the map screen).
  2. For the first such file: the 70-line window around the first
     "Pool Table" + "PLACED" occurrence, with line numbers, so the
     render mechanism is visible directly: hardcoded JSX cards vs
     .map vs FlatList data vs dynamic state/backend.
  3. Whether "Scrabble Table" appears in that window (i.e. whether
     the rendered list itself has a Scrabble card/row).

Run from /app: python3 frontend/diag-house-games-render.py
Read-only. Prints DIAG_HOUSE_GAMES_RENDER_OK at the end.
"""
import glob
import sys


def main():
    hits = []
    for path in sorted(glob.glob("frontend/**/*.tsx", recursive=True) +
                       glob.glob("frontend/**/*.ts", recursive=True)):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                src = f.read()
        except FileNotFoundError:
            continue
        if "PLACED" in src and "Pool Table" in src:
            hits.append((path, src))
    if not hits:
        print("WARNING: no frontend file contains both PLACED and Pool Table")
        print("DIAG_HOUSE_GAMES_RENDER_OK")
        return 0
    print("FILES WITH PLACED + Pool Table:")
    for path, _ in hits:
        print("  %s" % path)
    path, src = hits[0]
    lines = src.split("\n")
    # First line containing Pool Table that is near a PLACED line
    # (within 30 lines) — the Games list render.
    anchor = None
    for i, ln in enumerate(lines):
        if "Pool Table" in ln:
            window = "\n".join(lines[max(0, i - 5):min(len(lines), i + 30)])
            if "PLACED" in window:
                anchor = i
                break
    if anchor is None:
        # Fall back to the first Pool Table line.
        for i, ln in enumerate(lines):
            if "Pool Table" in ln:
                anchor = i
                break
    if anchor is None:
        print("WARNING: Pool Table line not found in %s" % path)
        print("DIAG_HOUSE_GAMES_RENDER_OK")
        return 0
    start = max(0, anchor - 10)
    end = min(len(lines), anchor + 60)
    print("RENDER WINDOW in %s (lines %d-%d, anchor Pool Table at line %d):" % (path, start + 1, end, anchor + 1))
    for k in range(start, end):
        print("%d: %s" % (k + 1, lines[k]))
    window_text = "\n".join(lines[start:end])
    print("SCRABBLE IN THIS RENDER WINDOW: %s" % ("YES" if "Scrabble Table" in window_text or "scrabble" in window_text.lower() else "NO"))
    print("DIAG_HOUSE_GAMES_RENDER_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
