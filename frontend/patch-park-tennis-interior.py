#!/usr/bin/env python3
"""Park tennis: add a Tennis row to the park interior in
frontend/app/(tabs)/index.tsx. Same pattern as the baseball/soccer ports:
  1. import TENNIS_HTML from '../../components/TennisHtml'
  2. TennisGameModal component (before MapScreen anchor; reuses the
     PoolWebView lazy require the basketball port added)
  3. tennisOpen state (after the last live game state: soccerOpen, else
     baseballOpen, else basketballOpen)
  4. Tennis row under the LAST live game row (Soccer, else Baseball,
     else Football, else Basketball)
     (anchor: that row's onPress -> first </TouchableOpacity> after it)
  5. LEAVE + modal onRequestClose also close tennisOpen (insert
     setTennisOpen(false) before setActivePark(null) on every line that
     already closes the basketball modal -- covers every combination
     of live games without enumerating them)
  6. TennisGameModal render after the last live game render (Soccer,
     else Baseball, else Football, else Basketball)
The park interior is shared by EVERY park, so this one patch puts
Tennis in all the parks. Run from /app, AFTER
patch-park-tennis-html.py. Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
TS = Path('frontend/components/TennisHtml.ts')
MARKER = 'PARK_TENNIS_INTERIOR'
MAP_ANCHOR = 'export default function MapScreen() {'
IMPORT_LINE = "import { TENNIS_HTML } from '../../components/TennisHtml';"
BBALL_STATE = '  const [basketballOpen, setBasketballOpen] = useState(false);'
BASEBALL_STATE = '  const [baseballOpen, setBaseballOpen] = useState(false);'
SOCCER_STATE = '  const [soccerOpen, setSoccerOpen] = useState(false);'
BBALL_ROW_PRESS = 'onPress={() => setBasketballOpen(true)}'
FBALL_ROW_PRESS = 'onPress={() => setFootballOpen(true)}'
BASEBALL_ROW_PRESS = 'onPress={() => setBaseballOpen(true)}'
SOCCER_ROW_PRESS = 'onPress={() => setSoccerOpen(true)}'
BBALL_RENDER = '{basketballOpen ? (<BasketballGameModal visible={basketballOpen} onClose={() => setBasketballOpen(false)} />) : null}'
FBALL_RENDER = '{footballOpen ? (<FootballGameModal visible={footballOpen} onClose={() => setFootballOpen(false)} />) : null}'
BASEBALL_RENDER = '{baseballOpen ? (<BaseballGameModal visible={baseballOpen} onClose={() => setBaseballOpen(false)} />) : null}'
SOCCER_RENDER = '{soccerOpen ? (<SoccerGameModal visible={soccerOpen} onClose={() => setSoccerOpen(false)} />) : null}'


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


def insert_row_after(src, press_anchor, label):
    """Insert the Tennis row right after the row whose onPress matches.
    Returns (src, err)."""
    lines = src.split('\n')
    press = [i for i, ln in enumerate(lines) if press_anchor in ln]
    if len(press) != 1:
        return src, '%s row onPress anchor count=%d (want 1)' % (label, len(press))
    closes = [i for i in range(press[0], len(lines)) if '</TouchableOpacity>' in lines[i]]
    if not closes:
        return src, '%s row closing </TouchableOpacity> not found' % label
    c = closes[0]
    new_lines = lines[:c + 1] + TENNIS_ROW.split('\n') + lines[c + 1:]
    return '\n'.join(new_lines), None



GAME_MODAL = '''const TennisGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
          <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>TENNIS - YOU vs CPU</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {PoolWebView ? (
          <PoolWebView
            source={{ html: TENNIS_HTML }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
            mediaPlaybackRequiresUserAction={false}
            originWhitelist={['*']}
            style={{ flex: 1 }}
            onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}
          />
        ) : (
          <Text style={{ color: '#ffffff', textAlign: 'center', marginTop: 40 }}>Tennis needs WebView, which is not available in this build.</Text>
        )}
      </View>
    </Modal>
  );
};

'''

TENNIS_ROW = '''            {/* PARK_TENNIS_INTERIOR */}
            <TouchableOpacity
              onPress={() => setTennisOpen(true)}
              style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#f5c518', borderRadius: 12, padding: 14, marginBottom: 10 }}
            >
              <Text style={{ fontSize: 30 }}>🎾</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>Tennis</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>Backyard '84 • Official rules • One set • You vs CPU</Text>
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>TAP TO PLAY</Text>
            </TouchableOpacity>'''

TENNIS_RENDER = '          {tennisOpen ? (<TennisGameModal visible={tennisOpen} onClose={() => setTennisOpen(false)} />) : null}'
def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - park tennis row NOT added')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    if ('TennisGameModal' in src and MARKER in src
            and 'tennisOpen' in src):
        print('PARK_TENNIS_INTERIOR_ALREADY_APPLIED')
        return 0
    # Preconditions (print only).
    if 'BasketballGameModal' not in src:
        print('WARNING: BasketballGameModal not found - the basketball interior may not be live')
    if 'PARK_BASKETBALL_INTERIOR' not in src:
        print('WARNING: PARK_BASKETBALL_INTERIOR marker not found - check the basketball port ran')
    if BBALL_ROW_PRESS not in src:
        print('WARNING: basketball row onPress anchor not found')
    if 'PoolWebView' not in src:
        print('WARNING: PoolWebView not found in index.tsx')
    if not TS.exists():
        print('WARNING: frontend/components/TennisHtml.ts missing - run patch-park-tennis-html.py FIRST, then re-run this patch')
    # 1. import TENNIS_HTML
    import_ok = False
    if 'TennisHtml' in src:
        print('SKIP: TENNIS_HTML already imported')
        import_ok = True
    else:
        src, ok = import_after_last(src, IMPORT_LINE)
        import_ok = ok
        print('OK: TENNIS_HTML imported' if ok else 'WARNING: could not add TENNIS_HTML import')
    # 2. TennisGameModal component
    comp_ok = False
    if 'const TennisGameModal' in src:
        print('SKIP: TennisGameModal already present')
        comp_ok = True
    elif MAP_ANCHOR in src:
        src = src.replace(MAP_ANCHOR, GAME_MODAL + MAP_ANCHOR, 1)
        comp_ok = True
        print('OK: TennisGameModal component added')
    else:
        print('WARNING: MapScreen anchor not found, TennisGameModal not added')
    # 3. tennisOpen state (after the last live game state)
    state_ok = False
    if 'tennisOpen' in src:
        print('SKIP: tennisOpen state already present')
        state_ok = True
    elif src.count(SOCCER_STATE) == 1:
        src = src.replace(SOCCER_STATE,
                          SOCCER_STATE + '\n  const [tennisOpen, setTennisOpen] = useState(false);', 1)
        state_ok = True
        print('OK: tennisOpen state added after soccerOpen')
    elif src.count(BASEBALL_STATE) == 1:
        src = src.replace(BASEBALL_STATE,
                          BASEBALL_STATE + '\n  const [tennisOpen, setTennisOpen] = useState(false);', 1)
        state_ok = True
        print('OK: tennisOpen state added after baseballOpen')
    elif src.count(BBALL_STATE) == 1:
        src = src.replace(BBALL_STATE,
                          BBALL_STATE + '\n  const [tennisOpen, setTennisOpen] = useState(false);', 1)
        state_ok = True
        print('OK: tennisOpen state added after basketballOpen')
    else:
        print('WARNING: state anchor not found (soccer=%d baseball=%d basketball=%d) - tennisOpen state not added'
              % (src.count(SOCCER_STATE), src.count(BASEBALL_STATE), src.count(BBALL_STATE)))
    # 4. Tennis row: under the LAST live game row
    row_ok = False
    if MARKER in src:
        print('SKIP: Tennis row already present')
        row_ok = True
    else:
        for press, label in [(SOCCER_ROW_PRESS, 'soccer'), (BASEBALL_ROW_PRESS, 'baseball'),
                             (FBALL_ROW_PRESS, 'football'), (BBALL_ROW_PRESS, 'basketball')]:
            if press in src:
                src, err = insert_row_after(src, press, label)
                row_ok = err is None
                print('OK: Tennis row added under %s' % label.capitalize()
                      if err is None else 'WARNING: ' + err)
                break
        if not row_ok:
            print('WARNING: no game-row onPress anchor found - Tennis row not added')
    # 5. LEAVE + modal onRequestClose also close tennisOpen: on every line
    #    that already closes the basketball modal, insert the tennis close
    #    before setActivePark(null). Covers every live-games combination.
    close_ok = False
    if 'setTennisOpen(false); setActivePark(null)' in src:
        print('SKIP: LEAVE + onRequestClose already close tennisOpen')
        close_ok = True
    else:
        lines = src.split('\n')
        n = 0
        for i, ln in enumerate(lines):
            if 'setBasketballOpen(false)' in ln and 'setActivePark(null)' in ln:
                lines[i] = ln.replace('setActivePark(null)', 'setTennisOpen(false); setActivePark(null)', 1)
                n += 1
        src = '\n'.join(lines)
        if n > 0:
            close_ok = True
            print('OK: LEAVE + onRequestClose now close tennisOpen (%d place(s))' % n)
        else:
            print('WARNING: park close-all anchor not found')
    # 6. TennisGameModal render after the last live game render
    render_ok = False
    if 'TennisGameModal visible=' in src:
        print('SKIP: TennisGameModal render already present')
        render_ok = True
    else:
        for render, label in [(SOCCER_RENDER, 'Soccer'), (BASEBALL_RENDER, 'Baseball'),
                              (FBALL_RENDER, 'Football'), (BBALL_RENDER, 'Basketball')]:
            if src.count(render) == 1:
                src = src.replace(render, render + '\n' + TENNIS_RENDER, 1)
                render_ok = True
                print('OK: TennisGameModal render added after %s' % label)
                break
        if not render_ok:
            print('WARNING: game-modal render anchor not found (soccer=%d baseball=%d football=%d basketball=%d)'
                  % (src.count(SOCCER_RENDER), src.count(BASEBALL_RENDER), src.count(FBALL_RENDER), src.count(BBALL_RENDER)))
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    if import_ok and comp_ok and state_ok and row_ok and close_ok and render_ok:
        print('PARK_TENNIS_INTERIOR_OK')
        return 0
    print('PARK_TENNIS_INTERIOR_PARTIAL import=%s comp=%s state=%s row=%s close=%s render=%s'
          % (import_ok, comp_ok, state_ok, row_ok, close_ok, render_ok))
    return 1


if __name__ == '__main__':
    main()
