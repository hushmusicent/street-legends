#!/usr/bin/env python3
"""Park basketball: rework the park interior in frontend/app/(tabs)/index.tsx.

Top to bottom (activity-center hall pattern): fixed header (park name +
Inside now + cash) -> horizontal ScrollView scene (PARK_BG, swipe left/right,
onLayout-measured) -> PLAYABLE ACTIVITIES (Basketball first, only playable
entry; "More activities coming soon" placeholder) -> LEAVE fixed at bottom.
Tapping Basketball opens BasketballGameModal (BASKETBALL_HTML WebView, PvC).
Presence lifecycle + ENTER -> setActivePark flow are NOT touched.
Run from /app, AFTER patch-park-basketball-html.py. Idempotent.
"""
from pathlib import Path

IDX = Path('frontend/app/(tabs)/index.tsx')
TS = Path('frontend/components/BasketballHtml.ts')
MARKER = 'PARK_BASKETBALL_INTERIOR'
MAP_ANCHOR = 'export default function MapScreen() {'
IMPORT_LINE = "import { BASKETBALL_HTML } from '../../components/BasketballHtml';"
WEBVIEW_BLOCK = """let PoolWebView: any = null;
try { PoolWebView = require('react-native-webview').default; } catch (e) { PoolWebView = null; }

"""

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


def replace_park_modal(src):
    lines = src.split('\n')
    starts = [i for i, ln in enumerate(lines) if '{/* PARK interior' in ln]
    if len(starts) != 1:
        return src, 'PARK interior comment anchor count=%d (want 1)' % len(starts)
    s = starts[0]
    opens = [i for i in range(s, min(len(lines), s + 5))
             if '<Modal visible={!!activePark}' in lines[i]]
    if len(opens) != 1:
        return src, 'park Modal open anchor not found just after the comment'
    closes = [i for i in range(opens[0], len(lines)) if '</Modal>' in lines[i]]
    if not closes:
        return src, 'park Modal close </Modal> not found'
    e = closes[0]
    block = '\n'.join(lines[s:e + 1])
    for needle in ('PARK_BG', 'Inside now:', 'setActivePark(null)'):
        if needle not in block:
            return src, 'park modal block missing %r - refusing to replace' % needle
    new_lines = lines[:s] + NEW_MODAL.split('\n') + lines[e + 1:]
    return '\n'.join(new_lines), None


def insert_state(src):
    anchor = '  const [parkFriendIds, setParkFriendIds] = useState<string[]>([]);'
    if src.count(anchor) == 1:
        return src.replace(anchor, anchor + '\n' + STATE_BLOCK, 1), None
    for ln in src.split('\n'):
        if 'parkFriendIds' in ln and 'useState' in ln:
            return src.replace(ln, ln + '\n' + STATE_BLOCK, 1), None
    marker = '  // PARK: presence lifecycle'
    if marker in src:
        return src.replace(marker, STATE_BLOCK + '\n' + marker, 1), None
    return src, 'no park state anchor found'



GAME_MODAL = '''const BasketballGameModal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#111111' }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', padding: 12 }}>
          <Text style={{ color: '#ffffff', fontWeight: '800', fontSize: 16 }}>BASKETBALL - YOU vs CPU</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        {PoolWebView ? (
          <PoolWebView
            source={{ html: BASKETBALL_HTML }}
            javaScriptEnabled={true}
            domStorageEnabled={true}
            allowsInlineMediaPlayback={true}
            mediaPlaybackRequiresUserAction={false}
            originWhitelist={['*']}
            style={{ flex: 1 }}
            onMessage={(event: any) => { if (event?.nativeEvent?.data === 'close') onClose(); }}
          />
        ) : (
          <Text style={{ color: '#ffffff', textAlign: 'center', marginTop: 40 }}>Basketball needs WebView, which is not available in this build.</Text>
        )}
      </View>
    </Modal>
  );
};

'''

STATE_BLOCK = '''  const [basketballOpen, setBasketballOpen] = useState(false);
  // PARK BASKETBALL: scrollable park scene (same pattern as the activity-center hall).
  const [parkSceneH, setParkSceneH] = useState(400);
  const parkSceneHRef = useRef(400);
  const parkSceneWRef = useRef(600);
  const parkSceneW = parkSceneH * 1.5;'''

NEW_MODAL = '''      {/* PARK interior - basketball + activities (PARK_BASKETBALL_INTERIOR). */}
      <Modal visible={!!activePark} animationType="slide" onRequestClose={() => { setBasketballOpen(false); setActivePark(null); }}>
        <View style={{ flex: 1, backgroundColor: '#0d1f12' }}>
          <View style={{ padding: 20, paddingTop: 60 }}>
            <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#fff' }}>{activePark?.name || 'Park'}</Text>
            <Text style={{ fontSize: 14, color: '#e0e0e0', marginTop: 4 }}>Park</Text>
            <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#fff', marginTop: 16 }}>Your cash: ${(player?.cash || 0).toLocaleString()}</Text>
            <Text style={{ fontSize: 18, fontWeight: 'bold', color: '#fff', marginTop: 24, marginBottom: 8 }}>Inside now:</Text>
            {(() => {
              const friendIds = parkFriendIds || [];
              const shown = (parkOccupants || []).filter((o: any) => o.player_id === playerId || friendIds.indexOf(o.player_id) !== -1);
              const me = shown.filter((o: any) => o.player_id === playerId);
              const friends = shown.filter((o: any) => o.player_id !== playerId);
              const ordered = me.concat(friends);
              if (ordered.length === 0) return (<Text style={{ fontSize: 16, color: '#fff' }}>{(player as any)?.name || 'You'}</Text>);
              return ordered.map((o: any) => (
                <Text key={o.player_id} style={{ fontSize: 16, color: '#fff', marginBottom: 6 }}>
                  {o.player_id === playerId ? '★ ' : ''}{o.player_name || o.name}
                </Text>
              ));
            })()}
            <Text style={{ fontSize: 13, color: '#a7f3c9', marginTop: 10 }}>Swipe the picture left and right to look around the park.</Text>
          </View>
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            style={{ flex: 1 }}
            onLayout={(e: any) => { const h = e?.nativeEvent?.layout?.height || 0; if (h > 0 && h !== parkSceneHRef.current) { parkSceneHRef.current = h; parkSceneWRef.current = h * 1.5; setParkSceneH(h); } }}
          >
            <View style={{ width: parkSceneW, height: parkSceneH }}>
              <Image source={{ uri: PARK_BG }} style={{ width: parkSceneW, height: parkSceneH }} resizeMode="cover" />
            </View>
          </ScrollView>
          <View style={{ padding: 12, paddingBottom: 4 }}>
            <Text style={{ fontSize: 17, fontWeight: 'bold', color: '#f5c518', letterSpacing: 1, marginBottom: 8 }}>PLAYABLE ACTIVITIES</Text>
            <TouchableOpacity
              onPress={() => setBasketballOpen(true)}
              style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#f5c518', borderRadius: 12, padding: 14, marginBottom: 10 }}
            >
              <Text style={{ fontSize: 30 }}>🏀</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>Basketball</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>2 on 2 • Arcade jam style • First to 21</Text>
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>TAP TO PLAY</Text>
            </TouchableOpacity>
            <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#2d7a44', borderRadius: 12, padding: 14, opacity: 0.55 }}>
              <Text style={{ fontSize: 30 }}>🌳</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>More activities coming soon</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>New games will show up here</Text>
              </View>
              <Text style={{ backgroundColor: '#555', color: '#ddd', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>SOON</Text>
            </View>
          </View>
          <TouchableOpacity
            style={{ margin: 16, marginTop: 8, backgroundColor: '#E91E63', padding: 14, borderRadius: 10, alignItems: 'center' }}
            onPress={() => { setBasketballOpen(false); setActivePark(null); }}
          >
            <Text style={{ color: '#fff', fontWeight: 'bold', fontSize: 16 }}>LEAVE</Text>
          </TouchableOpacity>
          {basketballOpen ? (<BasketballGameModal visible={basketballOpen} onClose={() => setBasketballOpen(false)} />) : null}
        </View>
      </Modal>'''
def main():
    if not IDX.exists():
        print('WARNING: index.tsx not found - park basketball interior NOT added')
        return 1
    src = IDX.read_text(encoding='utf-8', errors='ignore')
    before = src
    if ('BasketballGameModal' in src and MARKER in src
            and 'basketballOpen' in src):
        print('PARK_BASKETBALL_INTERIOR_ALREADY_APPLIED')
        return 0
    # Preconditions (probe-confirmed live 2026-11-07; print only).
    if '<Image source={{ uri: ACTIVITY_CENTER_BG }}' not in src:
        print('WARNING: center-hall Image usage not found - check Image is imported')
    if 'ScrollView' not in src:
        print('WARNING: ScrollView not found in index.tsx')
    if 'useRef' not in src:
        print('WARNING: useRef not found in index.tsx (park scene state needs it)')
    if 'PARK_BG' not in src:
        print('WARNING: PARK_BG not found in index.tsx')
    if not TS.exists():
        print('WARNING: frontend/components/BasketballHtml.ts missing - run patch-park-basketball-html.py FIRST, then re-run this patch')
    # 1. import BASKETBALL_HTML
    import_ok = False
    if 'BasketballHtml' in src:
        print('SKIP: BASKETBALL_HTML already imported')
        import_ok = True
    else:
        src, ok = import_after_last(src, IMPORT_LINE)
        import_ok = ok
        print('OK: BASKETBALL_HTML imported' if ok else 'WARNING: could not add BASKETBALL_HTML import')
    # 2. BasketballGameModal component (+ PoolWebView lazy require if absent)
    comp_ok = False
    if 'const BasketballGameModal' in src:
        print('SKIP: BasketballGameModal already present')
        comp_ok = True
    elif MAP_ANCHOR in src:
        block = GAME_MODAL
        if 'let PoolWebView' not in src:
            block = WEBVIEW_BLOCK + block
            print('OK: PoolWebView lazy require added')
        src = src.replace(MAP_ANCHOR, block + MAP_ANCHOR, 1)
        comp_ok = True
        print('OK: BasketballGameModal component added')
    else:
        print('WARNING: MapScreen anchor not found, BasketballGameModal not added')
    # 3. state (basketballOpen + park scene measurements)
    state_ok = False
    if 'basketballOpen' in src and 'parkSceneH' in src:
        print('SKIP: basketball + park scene state already present')
        state_ok = True
    else:
        src, err = insert_state(src)
        state_ok = err is None
        print('OK: basketball + park scene state added' if err is None else 'WARNING: ' + err)
    # 4. park interior rework
    modal_ok = False
    if MARKER in src:
        print('SKIP: park interior already reworked')
        modal_ok = True
    else:
        src, err = replace_park_modal(src)
        modal_ok = err is None
        print('OK: park interior reworked (header + scroll scene + activities + LEAVE)'
              if err is None else 'WARNING: ' + err)
    IDX.write_text(src, encoding='utf-8')
    if not _imbalances_ok(before, src):
        print('WARNING: bracket imbalance changed - inspect the diff before Deploy')
    if import_ok and comp_ok and state_ok and modal_ok:
        print('PARK_BASKETBALL_INTERIOR_OK')
        return 0
    print('PARK_BASKETBALL_INTERIOR_PARTIAL import=%s comp=%s state=%s modal=%s'
          % (import_ok, comp_ok, state_ok, modal_ok))
    return 1


if __name__ == '__main__':
    main()
