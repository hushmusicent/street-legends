#!/usr/bin/env python3
"""Shootout pays a flat $10 per hit (City Gotcha rate).

User (2026-11-11): the new City Gotcha shootout pays $10 a hit, and it is
being ported into the app for both settings (standalone) and map games.
The old backend formula paid (5 + level*2) per hit, which does not match
the $10 the game shows.

Change (backend/server.py, complete_shootout only):
  - hit_reward is now a flat 10 per hit (was 5 + level*2).
  - xp_per_hit and rep stay as they are (map gets full XP/rep).
  - The existing 50% standalone reduction is untouched: settings games
    pay $5/hit (+ half XP/rep), map games pay the full $10/hit (+ full
    XP/rep).

This is a BACKEND patch: run in /app, then Deploy (Publish).
Marker: SHOOTOUT_10_PER_HIT_OK
"""
import sys
from pathlib import Path

SERVER = Path("backend/server.py")

OLD = """        # Rewards per hit scale with level
        hit_reward = 5 + level * 2
        xp_per_hit = 2 + level // 2"""

NEW = """        # City Gotcha rate: a flat $10 per hit (level does not change it)
        hit_reward = 10
        xp_per_hit = 2 + level // 2"""


def main():
    if not SERVER.exists():
        print("SHOOTOUT_10_PER_HIT_FAIL backend/server.py not found")
        return 1
    src = SERVER.read_text(encoding="utf-8")
    if "hit_reward = 10" in src and "hit_reward = 5 + level * 2" not in src:
        print("SHOOTOUT_10_PER_HIT_ALREADY_APPLIED")
        return 0
    if OLD not in src:
        print("SHOOTOUT_10_PER_HIT_FAIL reward block not found (file may have changed)")
        return 1
    src = src.replace(OLD, NEW, 1)
    # sanity: complete_shootout still has the standalone halving and rep
    for needle in (
        "async def complete_shootout(",
        "cash_reward = hits * hit_reward",
        "rep_reward = max(1, hits // 3 + level // 5)",
        "if standalone:",
        "cash_reward = cash_reward // 2",
    ):
        if needle not in src:
            print("SHOOTOUT_10_PER_HIT_FAIL missing after edit: %s" % needle)
            return 1
    SERVER.write_text(src, encoding="utf-8")
    print("SHOOTOUT_10_PER_HIT_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
