#!/usr/bin/env python3
"""Park football: add a Football row under Basketball in the park interior.

Probe-confirmed live 2026-11-07 (diag-park-football.py, VERDICT (a)):
index.tsx is 6301 lines, BasketballHtml.ts exists, all 12 basketball
markers OK (BasketballGameModal, PARK_BASKETBALL_INTERIOR, basketballOpen,
parkSceneH, PLAYABLE ACTIVITIES, Basketball TAP TO PLAY row, PoolWebView,
BASKETBALL_HTML import, park modal comment, MapScreen anchor, parkFriendIds).
The Basketball row opens with onPress={() => setBasketballOpen(true)} and
closes with </TouchableOpacity> just before the "More activities coming soon"
row; LEAVE + the modal onRequestClose both run
() => { setBasketballOpen(false); setActivePark(null); }.

This patch (frontend only, Expo Go) makes targeted insertions into that
live structure -- it does NOT replace the park modal:
  1. import FOOTBALL_HTML from '../../components/FootballHtml'
  2. FootballGameModal component (before MapScreen anchor; reuses the
     PoolWebView lazy require the basketball port added)
  3. footballOpen state (after the basketballOpen state line)
  4. Football row under the Basketball row (anchor: setBasketballOpen(true)
     -> first </TouchableOpacity> after it)
  5. LEAVE + modal onRequestClose also close footballOpen
  6. FootballGameModal render next to the BasketballGameModal render
Run from /app, AFTER patch-park-football-html.py (warns if FootballHtml.ts
is missing). Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
TS = Path('frontend/components/FootballHtml.ts')
MARKER = 'PARK_FOOTBALL_INTERIOR'
MAP_ANCHOR = 'export default function MapScreen() {'
IMPORT_LINE = "import { FOOTBALL_HTML } from '../../components/FootballHtml';"
BBALL_STATE = '  const [basketballOpen, setBasketballOpen] = useState(false);'
BBALL_ROW_PRESS = 'onPress={() => setBasketballOpen(true)}'
BBALL_RENDER = '{basketballOpen ? (<BasketballGameModal visible={basketballOpen} onClose={() => setBasketballOpen(false)} />) : null}'
CLOSE_ALL_OLD = '() => { setBasketballOpen(false); setActivePark(null); }'
CLOSE_ALL_NEW = '() => { setBasketballOpen(false); setFootballOpen(false); setActivePark(null); }'


def _delta(s):
    return (s.count('{'), s.count('}'), s.count('('), s.count(')'),
            s.count('['), s.count(']'))


def _imbalances_ok(before, after):
    b, a = _delta(before), _delta(after)
    return ((a[0] - a[1]) == (b[0] - b[1]) and (a[2] - a[3]) == (b[2] - b[3])
            and (a[4] - a[5]) == (b[4] - b[5]))


def import_after_last(src, line):
    lines = src.split('\n')
    last = -1
    for i, ln in enumerate(lines):
        if ln.startswith('import '):
            last = i
    if last == -1:
        return src, False
    lines.insert(last + 1, line)
    return '\n'.join(lines), True


GAME_MODAL = '''const FootballGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
          <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>FOOTBALL - YOU vs CPU</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {PoolWebView ? (
          <PoolWebView
            source={{ html: FOOTBALL_HTML }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
            mediaPlaybackRequiresUserAction={false}
            originWhitelist={['*']}
            style={{ flex: 1 }}
            onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}
          />
        ) : (
          <Text style={{ color: '#ffffff', textAlign: 'center', marginTop: 40 }}>Football needs WebView, which is not available in this build.</Text>
        )}
      </View>
    </Modal>
  );
};

'''

FOOTBALL_ROW = '''            {/* PARK_FOOTBALL_INTERIOR */}
            <TouchableOpacity
              onPress={() => setFootballOpen(true)}
              style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#f5c518', borderRadius: 12, padding: 14, marginBottom: 10 }}
            >
              <Text style={{ fontSize: 30 }}>🏈</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>Football</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>7 on 7 • Madden style • First to 10 TDs</Text>
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>TAP TO PLAY</Text>
            </TouchableOpacity>'''

FOOTBALL_RENDER = "          {footballOpen ? (<FootballGameModal visible={footballOpen} onClose={() => setFootballOpen(false)} />) : null}"


def insert_football_row(src):
    """Insert the Football row right after the Basketball row closes.

    Anchor: the Basketball row's onPress (unique) -> the first
    </TouchableOpacity> after it closes that row. Returns (src, err).
    """
    lines = src.split('\n')
    press = [i for i, ln in enumerate(lines) if BBALL_ROW_PRESS in ln]
    if len(press) != 1:
        return src, 'basketball row onPress anchor count=%d (want 1)' % len(press)
    closes = [i for i in range(press[0], len(lines)) if '</TouchableOpacity>' in lines[i]]
    if not closes:
        return src, 'basketball row closing </TouchableOpacity> not found'
    c = closes[0]
    new_lines = lines[:c + 1] + FOOTBALL_ROW.split('\n') + lines[c + 1:]
    return '\n'.join(new_lines), None


def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - park football row NOT added')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    if ('FootballGameModal' in src and MARKER in src
            and 'footballOpen' in src):
        print('PARK_FOOTBALL_INTERIOR_ALREADY_APPLIED')
        return 0
    # Preconditions (probe-confirmed live 2026-11-07; print only).
    if 'BasketballGameModal' not in src:
        print('WARNING: BasketballGameModal not found - the basketball interior may not be live')
    if 'PARK_BASKETBALL_INTERIOR' not in src:
        print('WARNING: PARK_BASKETBALL_INTERIOR marker not found - check the basketball port ran')
    if BBALL_ROW_PRESS not in src:
        print('WARNING: basketball row onPress anchor not found')
    if 'PoolWebView' not in src:
        print('WARNING: PoolWebView not found in index.tsx')
    if not TS.exists():
        print('WARNING: frontend/components/FootballHtml.ts missing - run patch-park-football-html.py FIRST, then re-run this patch')
    # 1. import FOOTBALL_HTML
    import_ok = False
    if 'FootballHtml' in src:
        print('SKIP: FOOTBALL_HTML already imported')
        import_ok = True
    else:
        src, ok = import_after_last(src, IMPORT_LINE)
        import_ok = ok
        print('OK: FOOTBALL_HTML imported' if ok else 'WARNING: could not add FOOTBALL_HTML import')
    # 2. FootballGameModal component
    comp_ok = False
    if 'const FootballGameModal' in src:
        print('SKIP: FootballGameModal already present')
        comp_ok = True
    elif MAP_ANCHOR in src:
        src = src.replace(MAP_ANCHOR, GAME_MODAL + MAP_ANCHOR, 1)
        comp_ok = True
        print('OK: FootballGameModal component added')
    else:
        print('WARNING: MapScreen anchor not found, FootballGameModal not added')
    # 3. footballOpen state (right after the basketballOpen state line)
    state_ok = False
    if 'footballOpen' in src:
        print('SKIP: footballOpen state already present')
        state_ok = True
    elif src.count(BBALL_STATE) == 1:
        src = src.replace(BBALL_STATE,
                          BBALL_STATE + '\n  const [footballOpen, setFootballOpen] = useState(false);', 1)
        state_ok = True
        print('OK: footballOpen state added')
    else:
        print('WARNING: basketballOpen state line count=%d (want 1) - footballOpen state not added'
              % src.count(BBALL_STATE))
    # 4. Football row under Basketball
    row_ok = False
    if MARKER in src:
        print('SKIP: Football row already present')
        row_ok = True
    else:
        src, err = insert_football_row(src)
        row_ok = err is None
        print('OK: Football row added under Basketball'
              if err is None else 'WARNING: ' + err)
    # 5. LEAVE + modal onRequestClose also close footballOpen
    close_ok = False
    n_old = src.count(CLOSE_ALL_OLD)
    if CLOSE_ALL_NEW in src:
        print('SKIP: LEAVE + onRequestClose already close footballOpen')
        close_ok = True
    elif n_old >= 1:
        src = src.replace(CLOSE_ALL_OLD, CLOSE_ALL_NEW)
        close_ok = True
        print('OK: LEAVE + onRequestClose now close footballOpen (%d place(s))' % n_old)
    else:
        print('WARNING: park close-all anchor not found (count=%d)' % n_old)
    # 6. FootballGameModal render next to the BasketballGameModal render
    render_ok = False
    if 'FootballGameModal visible=' in src:
        print('SKIP: FootballGameModal render already present')
        render_ok = True
    elif src.count(BBALL_RENDER) == 1:
        src = src.replace(BBALL_RENDER, BBALL_RENDER + '\n' + FOOTBALL_RENDER, 1)
        render_ok = True
        print('OK: FootballGameModal render added')
    else:
        print('WARNING: basketball render anchor count=%d (want 1)' % src.count(BBALL_RENDER))
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    if import_ok and comp_ok and state_ok and row_ok and close_ok and render_ok:
        print('PARK_FOOTBALL_INTERIOR_OK')
        return 0
    print('PARK_FOOTBALL_INTERIOR_PARTIAL import=%s comp=%s state=%s row=%s close=%s render=%s'
          % (import_ok, comp_ok, state_ok, row_ok, close_ok, render_ok))
    return 1


if __name__ == '__main__':
    main()
