#!/usr/bin/env python3
"""Park scroll panel: wrap the PLAYABLE ACTIVITIES game rows in a vertical
ScrollView so the list scrolls when there are more games than fit on
screen (six games now: Basketball, Football, Baseball, Soccer, Tennis,
1-on-1 '21).

  1. Insert <ScrollView style={{ maxHeight: 320 }} ...> right after the
     PLAYABLE ACTIVITIES header line.
  2. Insert </ScrollView> right after the LAST live game row's closing
     </TouchableOpacity> (priority: 1-on-1, else Tennis, else Soccer,
     else Baseball, else Football, else Basketball).
The header stays fixed on top and the "More activities coming soon"
card stays below the panel. The panel scrolls vertically; nested
scrolling is enabled in case the park modal itself scrolls. Run from
/app, AFTER the game-row patches (it wraps whatever rows are live).
Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
MARKER = 'PARK_SCROLL_PANEL'
HEADER = 'PLAYABLE ACTIVITIES</Text>'
# game rows, most recently added first (the last live one is the panel bottom)
ROW_PRESS = [
    ('one-on-one', 'onPress={() => setOneOnOneOpen(true)}'),
    ('tennis', 'onPress={() => setTennisOpen(true)}'),
    ('soccer', 'onPress={() => setSoccerOpen(true)}'),
    ('baseball', 'onPress={() => setBaseballOpen(true)}'),
    ('football', 'onPress={() => setFootballOpen(true)}'),
    ('basketball', 'onPress={() => setBasketballOpen(true)}'),
]
SCROLL_OPEN = ('            {/* PARK_SCROLL_PANEL */}\n'
               '            <ScrollView style={{ maxHeight: 320 }} showsVerticalScrollIndicator={true} nestedScrollEnabled={true}>')


def _delta(s):
    return (s.count('{'), s.count('}'), s.count('('), s.count(')'),
            s.count('['), s.count(']'))


def _imbalances_ok(before, after):
    b, a = _delta(before), _delta(after)
    return ((a[0] - a[1]) == (b[0] - b[1]) and (a[2] - a[3]) == (b[2] - b[3])
            and (a[4] - a[5]) == (b[4] - b[5]))


def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - scroll panel NOT added')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    if MARKER in src and 'maxHeight: 320' in src:
        print('PARK_SCROLL_PANEL_ALREADY_APPLIED')
        return 0
    if 'ScrollView' not in src:
        print('WARNING: ScrollView not found in index.tsx - check the import')
    # 1. ScrollView open right after the PLAYABLE ACTIVITIES header.
    open_ok = False
    if 'maxHeight: 320' in src:
        print('SKIP: scroll panel open already present')
        open_ok = True
    else:
        lines = src.split('\n')
        hdr = [i for i, ln in enumerate(lines) if HEADER in ln]
        if len(hdr) != 1:
            print('WARNING: PLAYABLE ACTIVITIES header count=%d (want 1) - panel open not added' % len(hdr))
        else:
            lines[hdr[0] + 1:hdr[0] + 1] = SCROLL_OPEN.split('\n')
            src = '\n'.join(lines)
            open_ok = True
            print('OK: scroll panel opens under PLAYABLE ACTIVITIES')
    # 2. ScrollView close right after the LAST live game row.
    close_ok = False
    if src.count('</ScrollView>') >= 2 and MARKER in src:
        # a close was already added by a previous run (open step skipped)
        print('SKIP: scroll panel close already present')
        close_ok = True
    else:
        lines = src.split('\n')
        done = False
        for label, press in ROW_PRESS:
            press_idx = [i for i, ln in enumerate(lines) if press in ln]
            if len(press_idx) != 1:
                continue
            closes = [i for i in range(press_idx[0], len(lines))
                      if '</TouchableOpacity>' in lines[i]]
            if not closes:
                print('WARNING: %s row closing </TouchableOpacity> not found' % label)
                break
            c = closes[0]
            lines[c + 1:c + 1] = ['            </ScrollView>']
            src = '\n'.join(lines)
            close_ok = True
            done = True
            print('OK: scroll panel closes after the %s row' % label)
            break
        if not done and not close_ok:
            print('WARNING: no live game-row anchor found - panel close not added')
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    if open_ok and close_ok:
        print('PARK_SCROLL_PANEL_OK')
        return 0
    print('PARK_SCROLL_PANEL_PARTIAL open=%s close=%s' % (open_ok, close_ok))
    return 1


if __name__ == '__main__':
    main()
