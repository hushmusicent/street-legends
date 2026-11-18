#!/usr/bin/env python3
"""Street Legends frontend: Top 50 leaderboard v3 - per-game Top 50.

v3 = everything v2 does PLUS the Top 50 lives inside each game's own
activity: every park + center game row gets its own small "🏆 TOP 50"
button that opens the leaderboard already filtered to that game.
Run v3 INSTEAD of v2 (v2 was never run in /app, so v3 is complete on
its own; if v2 was applied first, v3 upgrades its modal + render).

What this patch does (idempotent):
  F1  frontend/services/api.ts: adds getGamesTop50(game) + the
      GamesTop50Entry type, right after getLeaderboard().
  F2  frontend/app/(tabs)/index.tsx: imports getGamesTop50 from the api.
      (v2 fix kept: anchors on the import closing line, NOT on
      getAllItems being last — /app has extra api imports after it.)
  F3  Adds top50Open state next to the park modal states.
  F9  Adds top50Game state ('all' default) next to top50Open.
  F4  Adds the GAMES_TOP50_FILTERS list (All Games + 13 games) and the
      GamesTop50Modal component. F8: the modal takes a `game` prop
      (default 'all'); when it opens it defaults the filter to that
      game. Filter row still lets the user switch games inside.
      (If a v2 modal without the game prop is already present, F8
      upgrades it in place instead of inserting a second copy.)
  F5  Adds a TOP 50 button row to the activity-center menu (after the
      Pop Shot row, before "More activities coming soon") — All Games.
  F6  Adds the same TOP 50 button row to the park interior menu (after
      the 1-on-1 row, before "More activities coming soon") — All Games.
  F10 Adds a small "🏆 TOP 50" button under EACH of the 7
      activity-center game rows (Pool, Dartboard, Card Table, Dominoes,
      Scrabble, Chess & Checkers, Pop Shot). Each opens the modal
      filtered to that game.
  F11 Adds a small "🏆 TOP 50" button under EACH of the 6 park interior
      game rows (Basketball, Football, Baseball, Soccer, Tennis,
      1-on-1). Each opens the modal filtered to that game.
  F7  Renders <GamesTop50Modal> after the park interior modal, passing
      game={top50Game}.

NOTE: the park PvC win hook is NOT in this patch (same as v2).

Run from /app: python3 frontend/patch-games-top50-frontend-v3.py
Then reload Expo Go. No Deploy needed for the page itself, but the
backend patch must be Deployed first or the list comes back empty.
"""
import sys
from pathlib import Path

API = Path("frontend/services/api.ts")
INDEX = Path("frontend/app/(tabs)/index.tsx")
MARKER = "GAMES_TOP50_FRONTEND_V3_OK"

MORE_VIEW = """            <View style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#2d7a44', borderRadius: 12, padding: 14, opacity: 0.55 }}>"""

TOP50_BTN = """            <TouchableOpacity
              onPress={() => setTop50Open(true)}
              style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: '#14532d', borderWidth: 2, borderColor: '#f5c518', borderRadius: 12, padding: 14, marginBottom: 10 }}
            >
              <Text style={{ fontSize: 30 }}>🏆</Text>
              <View style={{ flex: 1, marginLeft: 12 }}>
                <Text style={{ color: '#fff', fontSize: 18, fontWeight: 'bold' }}>Top 50</Text>
                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>Most wins & best scores • Parks & centers</Text>
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>VIEW</Text>
            </TouchableOpacity>"""

# ---- F1: api.ts ----
API_ANCHOR = """export const getLeaderboard = async (limit: number = 20): Promise<LeaderboardEntry[]> => {
  const response = await api.get(`/leaderboard?limit=${limit}`);
  return response.data;
};"""
API_NEW = API_ANCHOR + """

export interface GamesTop50Entry {
  rank: number;
  id: string;
  name: string;
  level: number;
  wins: number;
  best: number;
  profile_pic: string | null;
}

export const getGamesTop50 = async (game: string = 'all'): Promise<GamesTop50Entry[]> => {
  const response = await api.get(`/games/top50?game=${encodeURIComponent(game)}`);
  return response.data;
};"""
API_SENTINEL = "export const getGamesTop50 = async"

# ---- F2: import (v2 fix) ----
# v1 anchored on "getAllItems," being the LAST import before the closing
# brace, but /app's index.tsx has MORE api imports after getAllItems
# (agent-added functions never pushed to GitHub), so that anchor never
# matched and the whole patch refused to write. v2 anchors on the
# closing line itself, which is unique in the file and does not depend
# on which entry is last.
IMPORT_ANCHOR = "} from '../../services/api';"
IMPORT_NEW = "  getGamesTop50,\n} from '../../services/api';"
IMPORT_SENTINEL = "  getGamesTop50,\n} from '../../services/api';"

# ---- F3: state ----
STATE_ANCHOR = "  const [footballOpen, setFootballOpen] = useState(false);"
STATE_NEW = STATE_ANCHOR + "\n  const [top50Open, setTop50Open] = useState(false);"
STATE_SENTINEL = "const [top50Open, setTop50Open] = useState(false);"

# ---- F9: top50Game state (which game the modal opens on) ----
GAME_STATE_ANCHOR = "  const [top50Open, setTop50Open] = useState(false);"
GAME_STATE_NEW = GAME_STATE_ANCHOR + "\n  const [top50Game, setTop50Game] = useState('all');"
GAME_STATE_SENTINEL = "const [top50Game, setTop50Game] = useState('all');"

# ---- F8: upgrade a v2 modal (no game prop) to v3 in place ----
# Only used when v2 was already applied. The v2 modal signature and its
# filter init are each unique in the file once v2 has run.
V2_MODAL_SIG = "const GamesTop50Modal = ({ visible, onClose }: { visible: boolean; onClose: () => void }) => {"
V3_MODAL_SIG = "const GamesTop50Modal = ({ visible, onClose, game = 'all' }: { visible: boolean; onClose: () => void; game?: string }) => {"
V2_FILTER_INIT = "  const [filter, setFilter] = useState('all');"
V3_FILTER_INIT = "  const [filter, setFilter] = useState(game || 'all');\n  useEffect(() => { if (visible) { setFilter(game || 'all'); } }, [visible]);"
V3_MODAL_SENTINEL = "game = 'all'"

# ---- F10/F11: small per-game TOP 50 button under each game row ----
# __GAME__ is replaced with the game key. Small right-aligned pill so it
# sits under its row without crowding the TAP TO PLAY pill.
PER_GAME_BTN_TEMPLATE = """            <TouchableOpacity
              onPress={() => { setTop50Game('__GAME__'); setTop50Open(true); }}
              style={{ alignSelf: 'flex-end', backgroundColor: '#14532d', borderWidth: 1, borderColor: '#f5c518', borderRadius: 16, paddingVertical: 5, paddingHorizontal: 12, marginBottom: 10, marginTop: -2 }}
            >
              <Text style={{ color: '#f5c518', fontWeight: 'bold', fontSize: 12 }}>🏆 TOP 50</Text>
            </TouchableOpacity>"""

# Each entry: (game key, the row's unique description line). The anchor is
# that description + the TAP TO PLAY pill + the row's closing tag, which
# is unique per game (every description occurs exactly once in index.tsx).
ROW_TAIL = """
              </View>
              <Text style={{ backgroundColor: '#f5c518', color: '#000', fontWeight: 'bold', fontSize: 12, paddingVertical: 6, paddingHorizontal: 10, borderRadius: 20 }}>TAP TO PLAY</Text>
            </TouchableOpacity>"""

CENTER_GAMES = [
    ("pool", "8-ball • You vs CPU or a friend"),
    ("dartboard", "Darts • You vs CPU or a friend"),
    ("card_table", "Spades & Gin Rummy • You vs CPU or a friend"),
    ("dominoes", "Dominoes • You vs CPU or a friend"),
    ("scrabble", "Scrabble • You vs CPU or a friend"),
    ("chess_checkers", "Chess & Checkers • You vs CPU or a friend"),
    ("pop_shot", "Arcade basketball • 60 seconds • Solo"),
]

PARK_GAMES = [
    ("basketball", "2 on 2 • Arcade jam style • First to 21"),
    ("football", "7 on 7 • Madden style • First to 10 TDs"),
    ("baseball", "Park '97 • 6 innings • You vs CPU"),
    ("soccer", "Park '98 • 5v5 • 2 halves • You vs CPU"),
    ("tennis", "Park '84 • Official rules • One set • You vs CPU"),
    ("one_on_one", "Park '21 • First to 21 • 10 signature dunks • You vs CPU"),
]

# ---- F4: filter list + modal component ----
MODAL_ANCHOR = "const BasketballGameModal = ({ visible, onClose, playerId, playerName, onCashChange }"
MODAL_CODE = """const GAMES_TOP50_FILTERS = [
  { key: 'all', label: 'All Games' },
  { key: 'baseball', label: 'Baseball' },
  { key: 'soccer', label: 'Soccer' },
  { key: 'tennis', label: 'Tennis' },
  { key: 'one_on_one', label: '1-on-1' },
  { key: 'basketball', label: 'Basketball' },
  { key: 'football', label: 'Football' },
  { key: 'pool', label: 'Pool' },
  { key: 'dartboard', label: 'Darts' },
  { key: 'card_table', label: 'Cards' },
  { key: 'dominoes', label: 'Dominoes' },
  { key: 'scrabble', label: 'Scrabble' },
  { key: 'chess_checkers', label: 'Chess' },
  { key: 'pop_shot', label: 'Pop Shot' },
];

// GAMES_TOP50_FRONTEND_V3 — Top 50 leaderboard for park + center games:
// most wins first, then best score. Gold rows for the top 3.
// `game` prop (default 'all') sets which game the list opens on — each
// game row's own TOP 50 button passes its game here.
const GamesTop50Modal = ({ visible, onClose, game = 'all' }: { visible: boolean; onClose: () => void; game?: string }) => {
  const [filter, setFilter] = useState(game || 'all');
  const [rows, setRows] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  useEffect(() => { if (visible) { setFilter(game || 'all'); } }, [visible]);
  useEffect(() => {
    if (!visible) return;
    let alive = true;
    setLoading(true);
    getGamesTop50(filter).then((data: any) => { if (alive) setRows(Array.isArray(data) ? data : []); }).catch(() => { if (alive) setRows([]); }).finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [visible, filter]);
  const curLabel = (GAMES_TOP50_FILTERS.find((f: any) => f.key === filter) || { label: 'All Games' }).label;
  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: '#0d1f12', padding: 20, paddingTop: 60 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' }}>
          <Text style={{ fontSize: 26, fontWeight: 'bold', color: '#f5c518' }}>TOP 50</Text>
          <TouchableOpacity onPress={onClose} style={{ backgroundColor: '#e74c3c', paddingVertical: 8, paddingHorizontal: 14, borderRadius: 8 }}>
            <Text style={{ color: '#ffffff', fontWeight: '800' }}>CLOSE</Text>
          </TouchableOpacity>
        </View>
        <Text style={{ fontSize: 14, color: '#e0e0e0', marginTop: 4 }}>{curLabel} • Most wins & best scores</Text>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginTop: 16, maxHeight: 44 }}>
          <View style={{ flexDirection: 'row' }}>
            {GAMES_TOP50_FILTERS.map((f: any) => (
              <TouchableOpacity key={f.key} onPress={() => setFilter(f.key)} style={{ backgroundColor: filter === f.key ? '#f5c518' : '#14532d', borderWidth: 1, borderColor: '#f5c518', borderRadius: 20, paddingVertical: 8, paddingHorizontal: 12, marginRight: 8 }}>
                <Text style={{ color: filter === f.key ? '#000' : '#fff', fontWeight: 'bold', fontSize: 13 }}>{f.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </ScrollView>
        {loading ? (
          <ActivityIndicator size="large" color="#f5c518" style={{ marginTop: 40 }} />
        ) : rows.length === 0 ? (
          <Text style={{ color: '#fff', fontSize: 16, textAlign: 'center', marginTop: 40 }}>No wins yet — be the first on the board!</Text>
        ) : (
          <ScrollView style={{ flex: 1, marginTop: 12 }} showsVerticalScrollIndicator={false}>
            {rows.map((r: any) => (
              <View key={r.id} style={{ flexDirection: 'row', alignItems: 'center', backgroundColor: r.rank <= 3 ? '#3d2f00' : '#14532d', borderWidth: r.rank <= 3 ? 2 : 1, borderColor: r.rank <= 3 ? '#f5c518' : '#2d7a44', borderRadius: 10, padding: 12, marginBottom: 8 }}>
                <Text style={{ color: '#f5c518', fontWeight: 'bold', fontSize: 18, width: 44 }}>#{r.rank}</Text>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: '#fff', fontSize: 16, fontWeight: 'bold' }}>{r.name}</Text>
                  <Text style={{ color: '#a7f3c9', fontSize: 13 }}>Level {r.level}</Text>
                </View>
                <View style={{ alignItems: 'flex-end' }}>
                  <Text style={{ color: '#fff', fontSize: 15, fontWeight: 'bold' }}>{r.wins} wins</Text>
                  <Text style={{ color: '#a7f3c9', fontSize: 13 }}>Best: {r.best}</Text>
                </View>
              </View>
            ))}
          </ScrollView>
        )}
      </View>
    </Modal>
  );
};

"""
MODAL_SENTINEL = "const GamesTop50Modal = "

# ---- F5/F6: TOP 50 buttons (center + park) ----
CENTER_ANCHOR = "            </TouchableOpacity>\n" + MORE_VIEW
CENTER_DONE = "            </TouchableOpacity>\n" + TOP50_BTN + "\n" + MORE_VIEW
PARK_ANCHOR = "            </TouchableOpacity>\n            </ScrollView>\n" + MORE_VIEW
PARK_DONE = "            </TouchableOpacity>\n            </ScrollView>\n" + TOP50_BTN + "\n" + MORE_VIEW

# ---- F7: render the modal after the park interior modal ----
RENDER_ANCHOR = """          {oneOnOneOpen ? (<OneOnOneGameModal visible={oneOnOneOpen} onClose={() => setOneOnOneOpen(false)} playerId={playerId} playerName={'Player'} onCashChange={() => { refetchPlayer(); }} />) : null}
        </View>
      </Modal>
      {/* STASH_BOX modal - 20 slots, 3 free, $5,000 per extra slot. */}"""
RENDER_NEW = """          {oneOnOneOpen ? (<OneOnOneGameModal visible={oneOnOneOpen} onClose={() => setOneOnOneOpen(false)} playerId={playerId} playerName={'Player'} onCashChange={() => { refetchPlayer(); }} />) : null}
        </View>
      </Modal>
      {top50Open ? (<GamesTop50Modal visible={top50Open} onClose={() => setTop50Open(false)} game={top50Game} />) : null}
      {/* STASH_BOX modal - 20 slots, 3 free, $5,000 per extra slot. */}"""
RENDER_SENTINEL = "{top50Open ? (<GamesTop50Modal"
RENDER_GAME_SENTINEL = "game={top50Game}"


def replace_once(src, anchor, new, section):
    """Replace anchor exactly once; return (new_src, status)."""
    n = src.count(anchor)
    if n == 0:
        print(f"GAMES_TOP50_{section}_ANCHOR_FAIL: anchor not found (nothing changed for this section)")
        return src, False
    if n > 1:
        print(f"GAMES_TOP50_{section}_ANCHOR_FAIL: anchor occurs {n} times, expected 1 (nothing changed for this section)")
        return src, False
    return src.replace(anchor, new, 1), True


def balance(text):
    return {c: text.count(c) for c in "{}()[]"}


def main():
    if not API.exists():
        print("WARNING: frontend/services/api.ts not found - NOT fixed")
        return 1
    if not INDEX.exists():
        print("WARNING: frontend/app/(tabs)/index.tsx not found - NOT fixed")
        return 1
    api = API.read_text(errors="ignore")
    idx = INDEX.read_text(errors="ignore")
    api_orig, idx_orig = api, idx
    ok = True

    # F1: api.ts getGamesTop50
    if API_SENTINEL in api:
        print("GAMES_TOP50_API_ALREADY_APPLIED")
    else:
        api, good = replace_once(api, API_ANCHOR, API_NEW, "API")
        ok = ok and good
        if good:
            print("OK: getGamesTop50() added to services/api.ts")

    # F2: import
    if IMPORT_SENTINEL in idx:
        print("GAMES_TOP50_IMPORT_ALREADY_APPLIED")
    else:
        idx, good = replace_once(idx, IMPORT_ANCHOR, IMPORT_NEW, "IMPORT")
        ok = ok and good
        if good:
            print("OK: getGamesTop50 imported in index.tsx")

    # F3: state
    if STATE_SENTINEL in idx:
        print("GAMES_TOP50_STATE_ALREADY_APPLIED")
    else:
        idx, good = replace_once(idx, STATE_ANCHOR, STATE_NEW, "STATE")
        ok = ok and good
        if good:
            print("OK: top50Open state added")

    # F9: top50Game state (must run after F3, it anchors on top50Open)
    if GAME_STATE_SENTINEL in idx:
        print("GAMES_TOP50_GAME_STATE_ALREADY_APPLIED")
    else:
        idx, good = replace_once(idx, GAME_STATE_ANCHOR, GAME_STATE_NEW, "GAME_STATE")
        ok = ok and good
        if good:
            print("OK: top50Game state added")

    # F4/F8: modal component — insert the v3 modal, or upgrade a v2 one.
    if V3_MODAL_SIG in idx:
        print("GAMES_TOP50_MODAL_ALREADY_APPLIED")
    elif V2_MODAL_SIG in idx:
        idx, good = replace_once(idx, V2_MODAL_SIG, V3_MODAL_SIG, "MODAL_SIG")
        ok = ok and good
        if good:
            print("OK: GamesTop50Modal signature upgraded to v3 (game prop)")
        idx, good2 = replace_once(idx, V2_FILTER_INIT, V3_FILTER_INIT, "MODAL_FILTER")
        ok = ok and good2
        if good2:
            print("OK: GamesTop50Modal filter now defaults to the game prop")
    else:
        idx, good = replace_once(idx, MODAL_ANCHOR, MODAL_CODE + MODAL_ANCHOR, "MODAL")
        ok = ok and good
        if good:
            print("OK: GamesTop50Modal component added (v3, game prop)")

    # F5: center menu button (scoped to the center "More activities" row)
    if CENTER_DONE in idx:
        print("GAMES_TOP50_CENTER_BTN_ALREADY_APPLIED")
    else:
        idx, good = replace_once(idx, CENTER_ANCHOR, "            </TouchableOpacity>\n" + TOP50_BTN + "\n" + MORE_VIEW, "CENTER_BTN")
        ok = ok and good
        if good:
            print("OK: TOP 50 button added to activity center menu")

    # F6: park menu button (scoped to the park "More activities" row)
    if PARK_DONE in idx:
        print("GAMES_TOP50_PARK_BTN_ALREADY_APPLIED")
    else:
        idx, good = replace_once(idx, PARK_ANCHOR, "            </TouchableOpacity>\n            </ScrollView>\n" + TOP50_BTN + "\n" + MORE_VIEW, "PARK_BTN")
        ok = ok and good
        if good:
            print("OK: TOP 50 button added to park menu")

    # F10/F11: per-game TOP 50 buttons. MUST run after F5/F6: F5/F6 anchor
    # on the row closing tag directly before "More activities", and the
    # per-game button goes right after a row's closing tag, so running
    # these first would break the F5/F6 anchors.
    for section, games in (("CENTER_GAME", CENTER_GAMES), ("PARK_GAME", PARK_GAMES)):
        for game_key, desc in games:
            btn = PER_GAME_BTN_TEMPLATE.replace("__GAME__", game_key)
            sentinel = "setTop50Game('%s')" % game_key
            if sentinel in idx:
                print("GAMES_TOP50_%s_%s_ALREADY_APPLIED" % (section, game_key.upper()))
                continue
            anchor = ("                <Text style={{ color: '#a7f3c9', fontSize: 13 }}>%s</Text>" % desc) + ROW_TAIL
            idx, good = replace_once(idx, anchor, anchor + "\n" + btn, "%s_%s" % (section, game_key.upper()))
            ok = ok and good
            if good:
                print("OK: TOP 50 button added under %s row" % game_key)

    # F7: render the modal (pass game={top50Game}). If a v2 render without
    # the game prop is already there, upgrade it in place.
    if RENDER_SENTINEL in idx and RENDER_GAME_SENTINEL in idx:
        print("GAMES_TOP50_RENDER_ALREADY_APPLIED")
    elif RENDER_SENTINEL in idx:
        old_render = "{top50Open ? (<GamesTop50Modal visible={top50Open} onClose={() => setTop50Open(false)} />) : null}"
        new_render = "{top50Open ? (<GamesTop50Modal visible={top50Open} onClose={() => setTop50Open(false)} game={top50Game} />) : null}"
        idx, good = replace_once(idx, old_render, new_render, "RENDER_GAME")
        ok = ok and good
        if good:
            print("OK: GamesTop50Modal render now passes game={top50Game}")
    else:
        idx, good = replace_once(idx, RENDER_ANCHOR, RENDER_NEW, "RENDER")
        ok = ok and good
        if good:
            print("OK: GamesTop50Modal rendered after park modal (game={top50Game})")

    if api == api_orig and idx == idx_orig:
        print("GAMES_TOP50_FRONTEND_V3_NOOP (nothing changed)")
        return 0 if ok else 1

    # Safety: inserted code must be delimiter-balanced (net delta must be 0
    # for every delimiter type) and every sentinel must be present.
    for name, before, after in (("api.ts", api_orig, api), ("index.tsx", idx_orig, idx)):
        b0, b1 = balance(before), balance(after)
        for open_c, close_c in (("{", "}"), ("(", ")"), ("[", "]")):
            d0 = b0[open_c] - b0[close_c]
            d1 = b1[open_c] - b1[close_c]
            if d0 != d1:
                print(f"GAMES_TOP50_VERIFY_FAIL: {name} delimiter balance changed for {open_c}{close_c} ({d0} -> {d1}) (nothing written)")
                return 1
    for sentinel in (API_SENTINEL, IMPORT_SENTINEL, STATE_SENTINEL, GAME_STATE_SENTINEL, MODAL_SENTINEL, V3_MODAL_SENTINEL, RENDER_SENTINEL, RENDER_GAME_SENTINEL):
        if sentinel not in idx and sentinel not in api:
            print(f"GAMES_TOP50_VERIFY_FAIL: sentinel missing after edit: {sentinel} (nothing written)")
            return 1
    if idx.count(TOP50_BTN) != 2:
        print(f"GAMES_TOP50_VERIFY_FAIL: main TOP 50 button appears {idx.count(TOP50_BTN)} times, expected 2 (nothing written)")
        return 1
    per_game = sum(1 for g, _ in CENTER_GAMES + PARK_GAMES if ("setTop50Game('%s')" % g) in idx)
    if per_game != 13:
        print(f"GAMES_TOP50_VERIFY_FAIL: per-game TOP 50 buttons present for {per_game}/13 games (nothing written)")
        return 1

    API.write_text(api)
    INDEX.write_text(idx)
    if ok:
        print(MARKER)
        return 0
    print("GAMES_TOP50_FRONTEND_V3_PARTIAL: some sections failed (see above) - applied sections were written")
    return 1


if __name__ == "__main__":
    sys.exit(main())
