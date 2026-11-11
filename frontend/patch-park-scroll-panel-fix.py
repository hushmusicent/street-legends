#!/usr/bin/env python3
"""Repair the park scroll panel: add the missing </ScrollView> close.

The first version of patch-park-scroll-panel.py had a bad skip check:
it skipped inserting the close whenever the file already contained two
or more '</ScrollView>' lines (the basketball patch's horizontal
park-scene ScrollView plus others in this 6000-line file) -- so it
printed PARK_SCROLL_PANEL_OK while leaving the panel's <ScrollView>
unclosed, and the build failed with "Expected corresponding JSX
closing tag for <ScrollView>".

This repair finds the panel's open (maxHeight: 320), finds the LAST
live game row (1-on-1, else Tennis, else Soccer, else Baseball, else
Football, else Basketball), and inserts the missing </ScrollView>
right after that row's closing </TouchableOpacity>. If the close is
already there it does nothing. Run from /app. Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
ROW_PRESS = [
    ('one-on-one', 'onPress={() => setOneOnOneOpen(true)}'),
    ('tennis', 'onPress={() => setTennisOpen(true)}'),
    ('soccer', 'onPress={() => setSoccerOpen(true)}'),
    ('baseball', 'onPress={() => setBaseballOpen(true)}'),
    ('football', 'onPress={() => setFootballOpen(true)}'),
    ('basketball', 'onPress={() => setBasketballOpen(true)}'),
]


def _delta(s):
    return (s.count('{'), s.count('}'), s.count('('), s.count(')'),
            s.count('['), s.count(']'))


def _imbalances_ok(before, after):
    b, a = _delta(before), _delta(after)
    return ((a[0] - a[1]) == (b[0] - b[1]) and (a[2] - a[3]) == (b[2] - b[3])
            and (a[4] - a[5]) == (b[4] - b[5]))


def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - scroll panel fix NOT applied')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    lines = src.split('\n')
    # 1. the panel's open must be there (otherwise the panel never ran)
    opens = [i for i, ln in enumerate(lines) if 'maxHeight: 320' in ln]
    if len(opens) != 1:
        print('WARNING: scroll panel open (maxHeight: 320) count=%d (want 1) - run patch-park-scroll-panel.py first, then re-run this fix' % len(opens))
        return 1
    open_idx = opens[0]
    # 2. find the LAST live game row and its closing </TouchableOpacity>
    target = None
    for label, press in ROW_PRESS:
        press_idx = [i for i, ln in enumerate(lines) if press in ln]
        if len(press_idx) != 1:
            continue
        closes = [i for i in range(press_idx[0], len(lines))
                  if '</TouchableOpacity>' in lines[i]]
        if not closes:
            print('WARNING: %s row closing </TouchableOpacity> not found' % label)
            return 1
        target = (label, closes[0])
        break
    if target is None:
        print('WARNING: no live game-row anchor found - panel close not added')
        return 1
    label, c = target
    # 3. is the close already there, right after that row?
    if c + 1 < len(lines) and lines[c + 1].strip() == '</ScrollView>':
        print('PARK_SCROLL_PANEL_FIX_ALREADY_CLOSED (close already after the %s row)' % label)
        return 0
    # 4. insert the missing close
    lines[c + 1:c + 1] = ['            </ScrollView>']
    src = '\n'.join(lines)
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    print('OK: scroll panel now closes after the %s row' % label)
    print('PARK_SCROLL_PANEL_FIX_OK')
    return 0


if __name__ == '__main__':
    main()
