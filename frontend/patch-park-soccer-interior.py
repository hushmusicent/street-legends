#!/usr/bin/env python3
"""Park soccer: add a Soccer row to the park interior in
frontend/app/(tabs)/index.tsx. Same pattern as the baseball port:
  1. import SOCCER_HTML from '../../components/SoccerHtml'
  2. SoccerGameModal component (before MapScreen anchor; reuses the
     PoolWebView lazy require the basketball port added)
  3. soccerOpen state (after the baseballOpen state line if live,
     else after the basketballOpen state line)
  4. Soccer row under Baseball if it is live, else under Football,
     else under Basketball
     (anchor: that row's onPress -> first </TouchableOpacity> after it)
  5. LEAVE + modal onRequestClose also close soccerOpen (handles all
     four close-all forms: football+baseball, baseball-only,
     football-only, basketball-only)
  6. SoccerGameModal render next to the Baseball render if live, else
     next to the Football render, else next to the Basketball render
The park interior is shared by EVERY park, so this one patch puts
Soccer in all the parks. Run from /app, AFTER
patch-park-soccer-html.py. Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
TS = Path('frontend/components/SoccerHtml.ts')
MARKER = 'PARK_SOCCER_INTERIOR'
MAP_ANCHOR = 'export default function MapScreen() {'
IMPORT_LINE = "import { SOCCER_HTML } from '../../components/SoccerHtml';"
BBALL_STATE = '  const [basketballOpen, setBasketballOpen] = useState(false);'
BASEBALL_STATE = '  const [baseballOpen, setBaseballOpen] = useState(false);'
BBALL_ROW_PRESS = 'onPress={() => setBasketballOpen(true)}'
FBALL_ROW_PRESS = 'onPress={() => setFootballOpen(true)}'
BASEBALL_ROW_PRESS = 'onPress={() => setBaseballOpen(true)}'
BBALL_RENDER = '{basketballOpen ? (<BasketballGameModal visible={basketballOpen} onClose={() => setBasketballOpen(false)} />) : null}'
FBALL_RENDER = '{footballOpen ? (<FootballGameModal visible={footballOpen} onClose={() => setFootballOpen(false)} />) : null}'
BASEBALL_RENDER = '{baseballOpen ? (<BaseballGameModal visible={baseballOpen} onClose={() => setBaseballOpen(false)} />) : null}'
# the close-all line: most complete form first, basketball-only last
CLOSE_FORMS = [
    ('() => { setBasketballOpen(false); setFootballOpen(false); setBaseballOpen(false); setActivePark(null); }',
     '() => { setBasketballOpen(false); setFootballOpen(false); setBaseballOpen(false); setSoccerOpen(false); setActivePark(null); }'),
    ('() => { setBasketballOpen(false); setBaseballOpen(false); setActivePark(null); }',
     '() => { setBasketballOpen(false); setBaseballOpen(false); setSoccerOpen(false); setActivePark(null); }'),
    ('() => { setBasketballOpen(false); setFootballOpen(false); setActivePark(null); }',
     '() => { setBasketballOpen(false); setFootballOpen(false); setSoccerOpen(false); setActivePark(null); }'),
    ('() => { setBasketballOpen(false); setActivePark(null); }',
     '() => { setBasketballOpen(false); setSoccerOpen(false); setActivePark(null); }'),
]


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
    """Insert the Soccer row right after the row whose onPress matches.
    Returns (src, err)."""
    lines = src.split('\n')
    press = [i for i, ln in enumerate(lines) if press_anchor in ln]
    if len(press) != 1:
        return src, '%s row onPress anchor count=%d (want 1)' % (label, len(press))
    closes = [i for i in range(press[0], len(lines)) if '</TouchableOpacity>' in lines[i]]
    if not closes:
        return src, '%s row closing </TouchableOpacity> not found' % label
    c = closes[0]
    new_lines = lines[:c + 1] + SOCCER_ROW.split('\n') + lines[c + 1:]
    return '\n'.join(new_lines), None



GAME_MODAL = '''const SoccerGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
          <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>SOCCER - YOU vs CPU</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {PoolWebView ? (
          <PoolWebView
            source={{ html: SOCCER_HTML }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
            mediaPlaybackRequiresUserAction={false}
            originWhitelist={['*']}
            style={{ flex: 1 }}
            onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}
          />
        ) : (
          <Text style={{ color: '#ffffff', textAlign: 'center', marginTop: 40 }}>Soccer needs WebView, which is not available in this build.</Text>
        )}
      </View>
    </Modal>
  );
};

'''

SOCCER_ROW = '''            {/* PARK_SOCCER_INTERIOR */}
            <TouchableOpacity
              onPress={() => setSoccerOpen(true)}
              style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#f5c518', borderRadius: 12, padding: 14, marginBottom: 10 }}
            >
              <Text style={{ fontSize: 30 }}>⚽</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>Soccer</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>Backyard '98 • 5v5 • 2 halves • You vs CPU</Text>
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>TAP TO PLAY</Text>
            </TouchableOpacity>'''

SOCCER_RENDER = '          {soccerOpen ? (<SoccerGameModal visible={soccerOpen} onClose={() => setSoccerOpen(false)} />) : null}'
def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - park soccer row NOT added')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    if ('SoccerGameModal' in src and MARKER in src
            and 'soccerOpen' in src):
        print('PARK_SOCCER_INTERIOR_ALREADY_APPLIED')
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
        print('WARNING: frontend/components/SoccerHtml.ts missing - run patch-park-soccer-html.py FIRST, then re-run this patch')
    # 1. import SOCCER_HTML
    import_ok = False
    if 'SoccerHtml' in src:
        print('SKIP: SOCCER_HTML already imported')
        import_ok = True
    else:
        src, ok = import_after_last(src, IMPORT_LINE)
        import_ok = ok
        print('OK: SOCCER_HTML imported' if ok else 'WARNING: could not add SOCCER_HTML import')
    # 2. SoccerGameModal component
    comp_ok = False
    if 'const SoccerGameModal' in src:
        print('SKIP: SoccerGameModal already present')
        comp_ok = True
    elif MAP_ANCHOR in src:
        src = src.replace(MAP_ANCHOR, GAME_MODAL + MAP_ANCHOR, 1)
        comp_ok = True
        print('OK: SoccerGameModal component added')
    else:
        print('WARNING: MapScreen anchor not found, SoccerGameModal not added')
    # 3. soccerOpen state (after baseballOpen if live, else basketballOpen)
    state_ok = False
    if 'soccerOpen' in src:
        print('SKIP: soccerOpen state already present')
        state_ok = True
    elif src.count(BASEBALL_STATE) == 1:
        src = src.replace(BASEBALL_STATE,
                          BASEBALL_STATE + '\n  const [soccerOpen, setSoccerOpen] = useState(false);', 1)
        state_ok = True
        print('OK: soccerOpen state added after baseballOpen')
    elif src.count(BBALL_STATE) == 1:
        src = src.replace(BBALL_STATE,
                          BBALL_STATE + '\n  const [soccerOpen, setSoccerOpen] = useState(false);', 1)
        state_ok = True
        print('OK: soccerOpen state added after basketballOpen')
    else:
        print('WARNING: state anchor not found (baseball=%d basketball=%d) - soccerOpen state not added'
              % (src.count(BASEBALL_STATE), src.count(BBALL_STATE)))
    # 4. Soccer row: under Baseball if live, else Football, else Basketball
    row_ok = False
    if MARKER in src:
        print('SKIP: Soccer row already present')
        row_ok = True
    elif BASEBALL_ROW_PRESS in src:
        src, err = insert_row_after(src, BASEBALL_ROW_PRESS, 'baseball')
        row_ok = err is None
        print('OK: Soccer row added under Baseball'
              if err is None else 'WARNING: ' + err)
    elif FBALL_ROW_PRESS in src:
        src, err = insert_row_after(src, FBALL_ROW_PRESS, 'football')
        row_ok = err is None
        print('OK: Soccer row added under Football (no Baseball row live)'
              if err is None else 'WARNING: ' + err)
    else:
        src, err = insert_row_after(src, BBALL_ROW_PRESS, 'basketball')
        row_ok = err is None
        print('OK: Soccer row added under Basketball (no Baseball/Football row live)'
              if err is None else 'WARNING: ' + err)
    # 5. LEAVE + modal onRequestClose also close soccerOpen
    close_ok = False
    if 'setSoccerOpen(false); setActivePark(null)' in src:
        print('SKIP: LEAVE + onRequestClose already close soccerOpen')
        close_ok = True
    else:
        for old, new in CLOSE_FORMS:
            if src.count(old) >= 1:
                n = src.count(old)
                src = src.replace(old, new)
                close_ok = True
                print('OK: LEAVE + onRequestClose now close soccerOpen (%d place(s))' % n)
                break
        if not close_ok:
            print('WARNING: park close-all anchor not found')
    # 6. SoccerGameModal render next to the Baseball render if live, else
    #    Football, else Basketball
    render_ok = False
    if 'SoccerGameModal visible=' in src:
        print('SKIP: SoccerGameModal render already present')
        render_ok = True
    elif src.count(BASEBALL_RENDER) == 1:
        src = src.replace(BASEBALL_RENDER, BASEBALL_RENDER + '\n' + SOCCER_RENDER, 1)
        render_ok = True
        print('OK: SoccerGameModal render added after Baseball')
    elif src.count(FBALL_RENDER) == 1:
        src = src.replace(FBALL_RENDER, FBALL_RENDER + '\n' + SOCCER_RENDER, 1)
        render_ok = True
        print('OK: SoccerGameModal render added after Football')
    elif src.count(BBALL_RENDER) == 1:
        src = src.replace(BBALL_RENDER, BBALL_RENDER + '\n' + SOCCER_RENDER, 1)
        render_ok = True
        print('OK: SoccerGameModal render added after Basketball')
    else:
        print('WARNING: game-modal render anchor not found (baseball=%d football=%d basketball=%d)'
              % (src.count(BASEBALL_RENDER), src.count(FBALL_RENDER), src.count(BBALL_RENDER)))
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    if import_ok and comp_ok and state_ok and row_ok and close_ok and render_ok:
        print('PARK_SOCCER_INTERIOR_OK')
        return 0
    print('PARK_SOCCER_INTERIOR_PARTIAL import=%s comp=%s state=%s row=%s close=%s render=%s'
          % (import_ok, comp_ok, state_ok, row_ok, close_ok, render_ok))
    return 1


if __name__ == '__main__':
    main()
