#!/usr/bin/env python3
"""Rename 'Backyard' -> 'Park' on the park sports already in /app.

The updated HTML/interior patches (built from the renamed games) only
take effect when they RUN. If the old patches already ran, their files
are already in /app with 'Backyard' labels -- the idempotency check
makes re-running them a no-op. This patch fixes the live files in place:
  - frontend/app/(tabs)/index.tsx: the park rows ("Backyard '97" etc.)
  - frontend/components/{Baseball,Soccer,Tennis,OneOnOne}Html.ts: the
    embedded game titles ("BACKYARD BASEBALL", etc.)
Files that don't exist yet are skipped (the updated patches will create
them with 'Park' labels when they run). Run from /app. Idempotent.
"""
from pathlib import Path

RENAMES = {
    'frontend/app/(tabs)/index.tsx': [
        ("Backyard '97", "Park '97"),
        ("Backyard '98", "Park '98"),
        ("Backyard '84", "Park '84"),
        ("Backyard '21", "Park '21"),
    ],
    'frontend/components/BaseballHtml.ts': [
        ("Backyard Baseball '97", "Park Baseball '97"),
        ("BACKYARD BASEBALL", "PARK BASEBALL"),
        ("6 innings in the backyard,", "6 innings in the park,"),
    ],
    'frontend/components/SoccerHtml.ts': [
        ("Backyard Soccer '98", "Park Soccer '98"),
        ("BACKYARD SOCCER", "PARK SOCCER"),
        ("5 on 5 in the backyard,", "5 on 5 in the park,"),
    ],
    'frontend/components/TennisHtml.ts': [
        ("Backyard Tennis '84", "Park Tennis '84"),
        ("BACKYARD TENNIS", "PARK TENNIS"),
    ],
    'frontend/components/OneOnOneHtml.ts': [
        ("Backyard 1-on-1 '21", "Park 1-on-1 '21"),
        ("BACKYARD 1-ON-1 '21", "PARK 1-ON-1 '21"),
    ],
}


def main():
    changed = 0
    skipped = 0
    for rel, pairs in RENAMES.items():
        p = Path(rel)
        if not p.exists():
            print('SKIP: %s not present yet (patch not run)' % rel)
            skipped += 1
            continue
        src = p.read_text(encoding='utf-8', errors='ignore')
        n = 0
        for old, new in pairs:
            c = src.count(old)
            if c:
                src = src.replace(old, new)
                n += c
        if n:
            p.write_text(src, encoding='utf-8')
            changed += n
            print('OK: %s -- %d replacement(s)' % (rel, n))
        else:
            print('OK: %s -- already Park (nothing to rename)' % rel)
    print('PARK_RENAME_OK (changed=%d, skipped_files=%d)' % (changed, skipped))
    return 0


if __name__ == '__main__':
    main()
