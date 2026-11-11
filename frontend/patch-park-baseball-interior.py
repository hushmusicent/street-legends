#!/usr/bin/env python3
"""Park baseball: add a Baseball row to the park interior in
frontend/app/(tabs)/index.tsx. Same pattern as the football port:
  1. import BASEBALL_HTML from '../../components/BaseballHtml'
  2. BaseballGameModal component (before MapScreen anchor; reuses the
     PoolWebView lazy require the basketball port added)
  3. baseballOpen state (after the basketballOpen state line)
  4. Baseball row under Football if it is live, else under Basketball
     (anchor: that row's onPress -> first </TouchableOpacity> after it)
  5. LEAVE + modal onRequestClose also close baseballOpen (handles both
     the football-live close-all and the basketball-only close-all)
  6. BaseballGameModal render next to the Football render if live, else
     next to the Basketball render
The park interior is shared by EVERY park, so this one patch puts
Baseball in all the parks. Run from /app, AFTER
patch-park-baseball-html.py. Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
TS = Path('frontend/components/BaseballHtml.ts')
MARKER = 'PARK_BASEBALL_INTERIOR'
MAP_ANCHOR = 'export default function MapScreen() {'
IMPORT_LINE = "import { BASEBALL_HTML } from '../../components/BaseballHtml';"
BBALL_STATE = '  const [basketballOpen, setBasketballOpen] = useState(false);'
BBALL_ROW_PRESS = 'onPress={() => setBasketballOpen(true)}'
FBALL_ROW_PRESS = 'onPress={() => setFootballOpen(true)}'
BBALL_RENDER = '{basketballOpen ? (<BasketballGameModal visible={basketballOpen} onClose={() => setBasketballOpen(false)} />) : null}'
FBALL_RENDER = '{footballOpen ? (<FootballGameModal visible={footballOpen} onClose={() => setFootballOpen(false)} />) : null}'
# the close-all line: football-live form first, basketball-only form second
CLOSE_FBALL_OLD = '() => { setBasketballOpen(false); setFootballOpen(false); setActivePark(null); }'
CLOSE_FBALL_NEW = '() => { setBasketballOpen(false); setFootballOpen(false); setBaseballOpen(false); setActivePark(null); }'
CLOSE_BBALL_OLD = '() => { setBasketballOpen(false); setActivePark(null); }'
CLOSE_BBALL_NEW = '() => { setBasketballOpen(false); setBaseballOpen(false); setActivePark(null); }'


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
    """Insert the Baseball row right after the row whose onPress matches.
    Returns (src, err)."""
    lines = src.split('\n')
    press = [i for i, ln in enumerate(lines) if press_anchor in ln]
    if len(press) != 1:
        return src, '%s row onPress anchor count=%d (want 1)' % (label, len(press))
    closes = [i for i in range(press[0], len(lines)) if '</TouchableOpacity>' in lines[i]]
    if not closes:
        return src, '%s row closing </TouchableOpacity> not found' % label
    c = closes[0]
    new_lines = lines[:c + 1] + BASEBALL_ROW.split('\n') + lines[c + 1:]
    return '\n'.join(new_lines), None



GAME_MODAL = '''const BaseballGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
          <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>BASEBALL - YOU vs CPU</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {PoolWebView ? (
          <PoolWebView
            source={{ html: BASEBALL_HTML }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
            mediaPlaybackRequiresUserAction={false}
            originWhitelist={['*']}
            style={{ flex: 1 }}
            onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}
          />
        ) : (
          <Text style={{ color: '#ffffff', textAlign: 'center', marginTop: 40 }}>Baseball needs WebView, which is not available in this build.</Text>
        )}
      </View>
    </Modal>
  );
};

'''

BASEBALL_ROW = '''            {/* PARK_BASEBALL_INTERIOR */}
            <TouchableOpacity
              onPress={() => setBaseballOpen(true)}
              style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#f5c518', borderRadius: 12, padding: 14, marginBottom: 10 }}
            >
              <Text style={{ fontSize: 30 }}>⚾</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>Baseball</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>Backyard '97 • 6 innings • You vs CPU</Text>
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>TAP TO PLAY</Text>
            </TouchableOpacity>'''

BASEBALL_RENDER = '          {baseballOpen ? (<BaseballGameModal visible={baseballOpen} onClose={() => setBaseballOpen(false)} />) : null}'
def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - park baseball row NOT added')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    if ('BaseballGameModal' in src and MARKER in src
            and 'baseballOpen' in src):
        print('PARK_BASEBALL_INTERIOR_ALREADY_APPLIED')
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
        print('WARNING: frontend/components/BaseballHtml.ts missing - run patch-park-baseball-html.py FIRST, then re-run this patch')
    # 1. import BASEBALL_HTML
    import_ok = False
    if 'BaseballHtml' in src:
        print('SKIP: BASEBALL_HTML already imported')
        import_ok = True
    else:
        src, ok = import_after_last(src, IMPORT_LINE)
        import_ok = ok
        print('OK: BASEBALL_HTML imported' if ok else 'WARNING: could not add BASEBALL_HTML import')
    # 2. BaseballGameModal component
    comp_ok = False
    if 'const BaseballGameModal' in src:
        print('SKIP: BaseballGameModal already present')
        comp_ok = True
    elif MAP_ANCHOR in src:
        src = src.replace(MAP_ANCHOR, GAME_MODAL + MAP_ANCHOR, 1)
        comp_ok = True
        print('OK: BaseballGameModal component added')
    else:
        print('WARNING: MapScreen anchor not found, BaseballGameModal not added')
    # 3. baseballOpen state (right after the basketballOpen state line)
    state_ok = False
    if 'baseballOpen' in src:
        print('SKIP: baseballOpen state already present')
        state_ok = True
    elif src.count(BBALL_STATE) == 1:
        src = src.replace(BBALL_STATE,
                          BBALL_STATE + '\n  const [baseballOpen, setBaseballOpen] = useState(false);', 1)
        state_ok = True
        print('OK: baseballOpen state added')
    else:
        print('WARNING: basketballOpen state line count=%d (want 1) - baseballOpen state not added'
              % src.count(BBALL_STATE))
    # 4. Baseball row: under Football if it is live, else under Basketball
    row_ok = False
    if MARKER in src:
        print('SKIP: Baseball row already present')
        row_ok = True
    elif FBALL_ROW_PRESS in src:
        src, err = insert_row_after(src, FBALL_ROW_PRESS, 'football')
        row_ok = err is None
        print('OK: Baseball row added under Football'
              if err is None else 'WARNING: ' + err)
    else:
        src, err = insert_row_after(src, BBALL_ROW_PRESS, 'basketball')
        row_ok = err is None
        print('OK: Baseball row added under Basketball (no Football row live)'
              if err is None else 'WARNING: ' + err)
    # 5. LEAVE + modal onRequestClose also close baseballOpen
    close_ok = False
    if CLOSE_FBALL_NEW in src or CLOSE_BBALL_NEW in src:
        print('SKIP: LEAVE + onRequestClose already close baseballOpen')
        close_ok = True
    elif src.count(CLOSE_FBALL_OLD) >= 1:
        n = src.count(CLOSE_FBALL_OLD)
        src = src.replace(CLOSE_FBALL_OLD, CLOSE_FBALL_NEW)
        close_ok = True
        print('OK: LEAVE + onRequestClose now close baseballOpen (football-live form, %d place(s))' % n)
    elif src.count(CLOSE_BBALL_OLD) >= 1:
        n = src.count(CLOSE_BBALL_OLD)
        src = src.replace(CLOSE_BBALL_OLD, CLOSE_BBALL_NEW)
        close_ok = True
        print('OK: LEAVE + onRequestClose now close baseballOpen (basketball-only form, %d place(s))' % n)
    else:
        print('WARNING: park close-all anchor not found')
    # 6. BaseballGameModal render next to the Football render if live, else
    #    next to the Basketball render
    render_ok = False
    if 'BaseballGameModal visible=' in src:
        print('SKIP: BaseballGameModal render already present')
        render_ok = True
    elif src.count(FBALL_RENDER) == 1:
        src = src.replace(FBALL_RENDER, FBALL_RENDER + '\n' + BASEBALL_RENDER, 1)
        render_ok = True
        print('OK: BaseballGameModal render added after Football')
    elif src.count(BBALL_RENDER) == 1:
        src = src.replace(BBALL_RENDER, BBALL_RENDER + '\n' + BASEBALL_RENDER, 1)
        render_ok = True
        print('OK: BaseballGameModal render added after Basketball')
    else:
        print('WARNING: game-modal render anchor not found (football=%d basketball=%d)'
              % (src.count(FBALL_RENDER), src.count(BBALL_RENDER)))
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    if import_ok and comp_ok and state_ok and row_ok and close_ok and render_ok:
        print('PARK_BASEBALL_INTERIOR_OK')
        return 0
    print('PARK_BASEBALL_INTERIOR_PARTIAL import=%s comp=%s state=%s row=%s close=%s render=%s'
          % (import_ok, comp_ok, state_ok, row_ok, close_ok, render_ok))
    return 1


if __name__ == '__main__':
    main()
