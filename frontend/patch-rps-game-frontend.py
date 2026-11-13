#!/usr/bin/env python3
"""Rock Paper Scissors PvP frontend — RPS button in the player popup,
waiting view, challenge prompt, pick popup, result on both screens.

User (2026-11-12): "Put it to the game." (Approved the simple design:
no start menu, single round. A taps RPS on B's player menu -> A waits
for B to respond -> B says YES -> a small popup opens on BOTH phones to
pick Rock/Paper/Scissors -> result shows on BOTH screens.)

Adds (frontend/app/(tabs)/index.tsx + frontend/services/api.ts):
  api.ts: challengeRps / getPendingRps / respondRps / throwRps /
    getRpsGame / cancelRps.
  Player popup: gold ROCK PAPER SCISSORS button after CHALLENGE TO
    BATTLE. Tapping it challenges the player, closes the popup, and
    opens the game modal on "Waiting for {name} to respond…" + CANCEL.
  Map poll: extends the existing 15s trade-offer poll (checkOffers) to
    also check incoming RPS challenges; a NEW incoming challenge opens
    the challenge prompt modal ("{name} challenged you to Rock Paper
    Scissors" with YES / NO). If the trade poll is not present, a
    standalone 15s poll is added instead — never a per-second poll.
  Game poll: while a game is pending/accepted, poll getRpsGame every 3s
    so the challenger sees the accept and both sides see the result.
  Pick popup: inside the game modal when status is "accepted" and you
    have not thrown yet — three big buttons ROCK / PAPER / SCISSORS.
    After you throw it shows "You threw X. Waiting for {name}…".
  Result: when status is "finished" the modal shows both throws side by
    side, YOU WIN! / YOU LOSE / DRAW, a "Rock beats Scissors." line, and
    a DONE button that closes back to the map. No betting, no rematch,
    no score.

Does NOT touch Follow / Add Friend / CHALLENGE TO BATTLE / TRADE DRUGS,
the trade modal, or any other feature.

FRONTEND — Expo Go first. Marker: RPS_GAME_FRONTEND_OK
"""
import re
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
API = Path("frontend/services/api.ts")

# ---------------------------------------------------------------- api.ts
API_BLOCK = """
// RPS_GAME: Rock Paper Scissors PvP (single round, no betting).
export const challengeRps = async (challengerId: string, opponentId: string): Promise<any> => {
  const response = await api.post('/rps/challenge', { challenger_id: challengerId, opponent_id: opponentId });
  return response.data;
};
export const getPendingRps = async (playerId: string): Promise<any> => {
  const response = await api.get(`/rps/pending/${playerId}`);
  return response.data;
};
export const respondRps = async (gameId: string, playerId: string, accept: boolean): Promise<any> => {
  const response = await api.post('/rps/respond', { game_id: gameId, player_id: playerId, accept });
  return response.data;
};
export const throwRps = async (gameId: string, playerId: string, throwVal: string): Promise<any> => {
  const response = await api.post('/rps/throw', { game_id: gameId, player_id: playerId, throw: throwVal });
  return response.data;
};
export const getRpsGame = async (gameId: string, playerId: string): Promise<any> => {
  const response = await api.get(`/rps/game/${gameId}?player_id=${playerId}`);
  return response.data;
};
export const cancelRps = async (gameId: string, playerId: string): Promise<any> => {
  const response = await api.post('/rps/cancel', { game_id: gameId, player_id: playerId });
  return response.data;
};
"""

# ---------------------------------------------------------------- index.tsx
IMPORT_ANCHOR = "  sellToFiend,\n"
IMPORT_BLOCK = """  sellToFiend,
  challengeRps,
  getPendingRps,
  respondRps,
  throwRps,
  getRpsGame,
  cancelRps,
"""

STATE_ANCHOR = "  const [playerRelationship, setPlayerRelationship] = useState<RelationshipStatus | null>(null);"

STATE_BLOCK = STATE_ANCHOR + """
  // RPS_GAME: rock paper scissors PvP state.
  const [rpsGame, setRpsGame] = useState<any | null>(null);
  const [rpsIncoming, setRpsIncoming] = useState<any | null>(null);
  const [rpsBusy, setRpsBusy] = useState(false);
  const rpsSeenIdsRef = useRef<Set<string>>(new Set());"""

HANDLERS_ANCHOR = """  const handlePvPChallenge = useCallback(async (targetPlayer: NearbyPlayer) => {
    if (!playerId) return;
    try {
      const battle = await startBattle(playerId, 'player', targetPlayer.id);
      setCurrentBattle(battle);
      setSelectedMarker(null);
      router.push(`/battle/${battle.id}`);
    } catch (error: any) {
      Alert.alert('Error', error.response?.data?.detail || 'Failed to start PvP');
    }
  }, [playerId]);"""

HANDLERS_BLOCK = HANDLERS_ANCHOR + """

  // RPS_GAME: throw emoji + the "Rock beats Scissors." result line.
  const rpsEmoji = (t: string | null) => t === 'rock' ? '🪨' : t === 'paper' ? '📄' : t === 'scissors' ? '✂️' : '?';
  const rpsResultLine = (g: any) => {
    if (!g || g.status !== 'finished') return '';
    const a = g.your_throw, b = g.opponent_throw;
    if (!a || !b) return '';
    const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);
    if (a === b) return 'Both threw ' + cap(a) + '.';
    const beats: Record<string, string> = { rock: 'scissors', paper: 'rock', scissors: 'paper' };
    const winThrow = beats[a] === b ? a : b;
    const loseThrow = winThrow === a ? b : a;
    return cap(winThrow) + ' beats ' + cap(loseThrow) + '.';
  };

  // RPS_GAME: challenge the tapped player, close the popup, open the
  // waiting view. No start menu — the challenge IS the start.
  const handleRpsChallenge = useCallback(async (targetPlayer: NearbyPlayer) => {
    if (!playerId || rpsBusy) return;
    setRpsBusy(true);
    try {
      const game: any = await challengeRps(playerId, targetPlayer.id);
      setSelectedMarker(null);
      setRpsGame(game);
      showGameToast({ type: 'success', title: 'Challenge sent', message: 'Waiting for ' + targetPlayer.name + ' to respond', duration: 3000 });
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Challenge failed', message: e?.response?.data?.detail || 'Could not challenge ' + targetPlayer.name, duration: 3000 });
    } finally {
      setRpsBusy(false);
    }
  }, [playerId, rpsBusy]);

  // RPS_GAME: answer an incoming challenge. YES opens the pick popup.
  const handleRpsRespond = useCallback(async (game: any, accept: boolean) => {
    if (!playerId || !game || rpsBusy) return;
    setRpsBusy(true);
    try {
      const res: any = await respondRps(game.game_id, playerId, accept);
      setRpsIncoming(null);
      if (accept) {
        setRpsGame(res);
      } else {
        showGameToast({ type: 'info', title: 'Challenge declined', message: 'You declined the Rock Paper Scissors challenge', duration: 3000 });
      }
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Could not answer', message: e?.response?.data?.detail || 'Challenge is no longer there', duration: 3000 });
      setRpsIncoming(null);
    } finally {
      setRpsBusy(false);
    }
  }, [playerId, rpsBusy]);

  // RPS_GAME: throw. The result appears when both have thrown.
  const handleRpsThrow = useCallback(async (throwVal: string) => {
    if (!playerId || !rpsGame || rpsBusy) return;
    setRpsBusy(true);
    try {
      const res: any = await throwRps(rpsGame.game_id, playerId, throwVal);
      setRpsGame(res);
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Throw failed', message: e?.response?.data?.detail || 'Could not throw', duration: 3000 });
    } finally {
      setRpsBusy(false);
    }
  }, [playerId, rpsGame, rpsBusy]);

  // RPS_GAME: cancel my own pending challenge.
  const handleRpsCancel = useCallback(async () => {
    if (!playerId || !rpsGame || rpsBusy) return;
    setRpsBusy(true);
    try {
      await cancelRps(rpsGame.game_id, playerId);
      setRpsGame(null);
      showGameToast({ type: 'info', title: 'Challenge cancelled', message: 'You cancelled the challenge', duration: 3000 });
    } catch (e: any) {
      showGameToast({ type: 'warning', title: 'Cancel failed', message: e?.response?.data?.detail || 'Could not cancel', duration: 3000 });
    } finally {
      setRpsBusy(false);
    }
  }, [playerId, rpsGame, rpsBusy]);

  // RPS_GAME: close the game modal back to the map.
  const handleRpsDone = useCallback(() => {
    setRpsGame(null);
  }, []);

  // RPS_GAME: while a game is pending/accepted, poll its state every 3s
  // so the challenger sees the accept and both sides see the result.
  useEffect(() => {
    if (!rpsGame || !playerId) return;
    if (rpsGame.status !== 'pending' && rpsGame.status !== 'accepted') return;
    const t = setInterval(async () => {
      try {
        const g: any = await getRpsGame(rpsGame.game_id, playerId);
        setRpsGame(g);
      } catch (_) {}
    }, 3000);
    return () => clearInterval(t);
  }, [rpsGame?.game_id, rpsGame?.status, playerId]);"""

# Standalone 15s poll — only used when the trade checkOffers poll is absent.
STANDALONE_POLL_ANCHOR = "  }, [rpsGame?.game_id, rpsGame?.status, playerId]);"

STANDALONE_POLL_BLOCK = """  }, [rpsGame?.game_id, rpsGame?.status, playerId]);

  // RPS_GAME: while the map is open, poll for incoming RPS challenges
  // every 15s and pop the challenge prompt once per new challenge.
  useEffect(() => {
    if (!playerId) return;
    let stopped = false;
    const checkRps = async () => {
      try {
        const pending: any = await getPendingRps(playerId);
        if (stopped) return;
        for (const g of (pending?.incoming || [])) {
          const id = g.game_id;
          if (id && !rpsSeenIdsRef.current.has(id)) {
            rpsSeenIdsRef.current.add(id);
            setRpsIncoming(g);
          }
        }
      } catch (_) {}
    };
    checkRps();
    const t = setInterval(checkRps, 15000);
    return () => { stopped = true; clearInterval(t); };
  }, [playerId]);"""

# Extend the existing trade-offer poll (checkOffers) with the RPS check.
POLL_EXTEND_ANCHOR = """    checkOffers();
    const t = setInterval(checkOffers, 15000);"""

POLL_EXTEND_BLOCK = """    const checkRps = async () => {
      try {
        const pending: any = await getPendingRps(playerId);
        if (stopped) return;
        for (const g of (pending?.incoming || [])) {
          const id = g.game_id;
          if (id && !rpsSeenIdsRef.current.has(id)) {
            rpsSeenIdsRef.current.add(id);
            setRpsIncoming(g);
          }
        }
      } catch (_) {}
    };
    checkOffers();
    checkRps();
    const t = setInterval(() => { checkOffers(); checkRps(); }, 15000);"""

BUTTON_ANCHOR = """              <TouchableOpacity style={[styles.actionButton, {backgroundColor: '#e74c3c'}]} onPress={() => handlePvPChallenge(selectedMarker.data)}>
                <Text style={styles.actionButtonText}>CHALLENGE TO BATTLE</Text>
              </TouchableOpacity>"""

BUTTON_BLOCK = BUTTON_ANCHOR + """
              <TouchableOpacity style={[styles.actionButton, { backgroundColor: '#f5c518', marginTop: 8 }]} onPress={() => handleRpsChallenge(selectedMarker.data)}>
                <Text style={[styles.actionButtonText, { color: '#111' }]}>🪨📄✂️ ROCK PAPER SCISSORS</Text>
              </TouchableOpacity>"""

MODAL_ANCHOR = """      </Modal>

      {/* Castle Cannon / Car Chase / Runaway / Package Grab / Shootout Mini-game Modal */}"""

MODAL_BLOCK = """      </Modal>

      {/* RPS_GAME: incoming challenge prompt */}
      <Modal
        visible={!!rpsIncoming}
        transparent
        animationType="fade"
        onRequestClose={() => {}}
      >
        <Pressable style={styles.modalOverlay} onPress={() => {}}>
          <Pressable style={styles.terrModal} onPress={(e) => e.stopPropagation()}>
            <View style={styles.terrHeader}>
              <Text style={styles.bankIcon}>🪨📄✂️</Text>
              <View style={styles.terrHeaderText}>
                <Text style={styles.terrName}>ROCK PAPER SCISSORS</Text>
                <Text style={styles.terrSubtitle}>{rpsIncoming?.challenger_name || 'A player'} challenged you!</Text>
              </View>
            </View>
            <View style={styles.terrActions}>
              <TouchableOpacity style={[styles.terrBtn, { backgroundColor: '#27ae60' }]} disabled={rpsBusy} onPress={() => handleRpsRespond(rpsIncoming, true)}>
                <Text style={styles.terrBtnText}>YES — LET'S PLAY</Text>
              </TouchableOpacity>
              <TouchableOpacity style={[styles.terrBtn, { backgroundColor: '#e74c3c', marginTop: 10 }]} disabled={rpsBusy} onPress={() => handleRpsRespond(rpsIncoming, false)}>
                <Text style={styles.terrBtnText}>NO</Text>
              </TouchableOpacity>
            </View>
          </Pressable>
        </Pressable>
      </Modal>

      {/* RPS_GAME: waiting / pick / result */}
      <Modal
        visible={!!rpsGame}
        transparent
        animationType="fade"
        onRequestClose={() => {}}
      >
        <Pressable style={styles.modalOverlay} onPress={() => {}}>
          <Pressable style={styles.terrModal} onPress={(e) => e.stopPropagation()}>
            {rpsGame && (
              <>
                <View style={styles.terrHeader}>
                  <Text style={styles.bankIcon}>🪨📄✂️</Text>
                  <View style={styles.terrHeaderText}>
                    <Text style={styles.terrName}>ROCK PAPER SCISSORS</Text>
                    <Text style={styles.terrSubtitle}>
                      {rpsGame.status === 'pending' ? 'Waiting for ' + rpsGame.other_name + ' to respond…'
                        : rpsGame.status === 'declined' ? rpsGame.other_name + ' said no.'
                        : 'vs ' + rpsGame.other_name}
                    </Text>
                  </View>
                </View>

                {rpsGame.status === 'pending' && (
                  <View style={styles.terrActions}>
                    <Text style={[styles.rpsNote, { textAlign: 'center', marginBottom: 12 }]}>Waiting for {rpsGame.other_name} to respond…</Text>
                    <TouchableOpacity style={[styles.terrBtn, { backgroundColor: '#e74c3c' }]} disabled={rpsBusy} onPress={handleRpsCancel}>
                      <Text style={styles.terrBtnText}>CANCEL</Text>
                    </TouchableOpacity>
                  </View>
                )}

                {rpsGame.status === 'declined' && (
                  <View style={styles.terrActions}>
                    <Text style={[styles.rpsNote, { textAlign: 'center', marginBottom: 12 }]}>{rpsGame.other_name} said no.</Text>
                    <TouchableOpacity style={[styles.terrBtn, { backgroundColor: '#555' }]} onPress={handleRpsDone}>
                      <Text style={styles.terrBtnText}>BACK</Text>
                    </TouchableOpacity>
                  </View>
                )}

                {rpsGame.status === 'accepted' && !rpsGame.your_throw && (
                  <View>
                    <Text style={[styles.rpsNote, { textAlign: 'center' }]}>CHOOSE YOUR THROW</Text>
                    <View style={styles.rpsThrows}>
                      <TouchableOpacity style={styles.rpsThrowBtn} disabled={rpsBusy} onPress={() => handleRpsThrow('rock')}>
                        <Text style={styles.rpsThrowEmoji}>🪨</Text>
                        <Text style={styles.rpsThrowText}>ROCK</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.rpsThrowBtn} disabled={rpsBusy} onPress={() => handleRpsThrow('paper')}>
                        <Text style={styles.rpsThrowEmoji}>📄</Text>
                        <Text style={styles.rpsThrowText}>PAPER</Text>
                      </TouchableOpacity>
                      <TouchableOpacity style={styles.rpsThrowBtn} disabled={rpsBusy} onPress={() => handleRpsThrow('scissors')}>
                        <Text style={styles.rpsThrowEmoji}>✂️</Text>
                        <Text style={styles.rpsThrowText}>SCISSORS</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}

                {rpsGame.status === 'accepted' && rpsGame.your_throw && (
                  <View style={styles.terrActions}>
                    <Text style={[styles.rpsNote, { textAlign: 'center', marginBottom: 12 }]}>You threw {rpsGame.your_throw}. Waiting for {rpsGame.other_name}…</Text>
                  </View>
                )}

                {rpsGame.status === 'finished' && (
                  <View>
                    <View style={styles.rpsArena}>
                      <View style={styles.rpsSide}>
                        <Text style={styles.rpsSideLabel}>YOU</Text>
                        <Text style={styles.rpsBigEmoji}>{rpsEmoji(rpsGame.your_throw)}</Text>
                      </View>
                      <Text style={styles.rpsVs}>VS</Text>
                      <View style={styles.rpsSide}>
                        <Text style={styles.rpsSideLabel}>{(rpsGame.other_name || 'OPPONENT').toUpperCase()}</Text>
                        <Text style={styles.rpsBigEmoji}>{rpsEmoji(rpsGame.opponent_throw)}</Text>
                      </View>
                    </View>
                    <Text style={[styles.rpsResult, rpsGame.result === 'win' ? styles.rpsWin : rpsGame.result === 'lose' ? styles.rpsLose : styles.rpsDraw]}>
                      {rpsGame.result === 'win' ? 'YOU WIN!' : rpsGame.result === 'lose' ? 'YOU LOSE' : 'DRAW'}
                    </Text>
                    <Text style={styles.rpsResultLine}>{rpsResultLine(rpsGame)}</Text>
                    <View style={styles.terrActions}>
                      <TouchableOpacity style={[styles.terrBtn, { backgroundColor: '#f5c518' }]} onPress={handleRpsDone}>
                        <Text style={[styles.terrBtnText, { color: '#111' }]}>DONE</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                )}
              </>
            )}
          </Pressable>
        </Pressable>
      </Modal>

      {/* Castle Cannon / Car Chase / Runaway / Package Grab / Shootout Mini-game Modal */}"""

STYLE_ANCHOR = """  socialButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
  },"""

STYLE_BLOCK = STYLE_ANCHOR + """

  // RPS_GAME styles
  rpsNote: { color: '#fff', fontSize: 14, fontWeight: '700' },
  rpsThrows: { flexDirection: 'row', gap: 10, marginTop: 14 },
  rpsThrowBtn: { flex: 1, backgroundColor: '#2a2a2a', borderWidth: 2, borderColor: '#444', borderRadius: 14, paddingVertical: 16, alignItems: 'center' },
  rpsThrowEmoji: { fontSize: 42 },
  rpsThrowText: { color: '#fff', fontSize: 13, fontWeight: '800', letterSpacing: 1, marginTop: 6 },
  rpsArena: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginVertical: 10 },
  rpsSide: { flex: 1, alignItems: 'center' },
  rpsSideLabel: { color: '#aaa', fontSize: 12, letterSpacing: 1, marginBottom: 6 },
  rpsBigEmoji: { fontSize: 76 },
  rpsVs: { color: '#f5c518', fontSize: 22, fontWeight: '900' },
  rpsResult: { textAlign: 'center', fontSize: 30, fontWeight: '900', letterSpacing: 1, marginTop: 8 },
  rpsWin: { color: '#2ecc71' },
  rpsLose: { color: '#e74c3c' },
  rpsDraw: { color: '#f5c518' },
  rpsResultLine: { textAlign: 'center', color: '#bbb', fontSize: 15, marginTop: 4, marginBottom: 12 },"""


def _replace_once(src, anchor, block, name, failures):
    if src.count(anchor) != 1:
        failures.append("%s: anchor count %d (want 1)" % (name, src.count(anchor)))
        return src
    return src.replace(anchor, block, 1)


def main():
    failures = []
    if not INDEX.exists() or not API.exists():
        print("RPS_GAME_FRONTEND_FAIL index.tsx or api.ts not found")
        return 1

    api_src = API.read_text(encoding="utf-8")
    if ("export const challengeRps" in api_src and "export const getPendingRps" in api_src
            and "export const respondRps" in api_src and "export const throwRps" in api_src
            and "export const getRpsGame" in api_src and "export const cancelRps" in api_src):
        print("RPS_GAME_FRONTEND_API_ALREADY_APPLIED")
    else:
        api_src = api_src.rstrip() + "\n" + API_BLOCK
        API.write_text(api_src, encoding="utf-8")

    src = INDEX.read_text(encoding="utf-8")
    if ("handleRpsChallenge" in src and "handleRpsRespond" in src and "handleRpsThrow" in src
            and "ROCK PAPER SCISSORS" in src and "rpsGame" in src and "rpsIncoming" in src):
        print("RPS_GAME_FRONTEND_INDEX_ALREADY_APPLIED")
    else:
        src = _replace_once(src, IMPORT_ANCHOR, IMPORT_BLOCK, "index.tsx import", failures)
        src = _replace_once(src, STATE_ANCHOR, STATE_BLOCK, "index.tsx rps state", failures)
        src = _replace_once(src, HANDLERS_ANCHOR, HANDLERS_BLOCK, "index.tsx rps handlers", failures)
        src = _replace_once(src, BUTTON_ANCHOR, BUTTON_BLOCK, "index.tsx rps button", failures)
        src = _replace_once(src, MODAL_ANCHOR, MODAL_BLOCK, "index.tsx rps modals", failures)
        src = _replace_once(src, STYLE_ANCHOR, STYLE_BLOCK, "index.tsx rps styles", failures)
        # Poll: extend the existing trade checkOffers poll when it is there;
        # otherwise add a standalone 15s poll (never per-second).
        if "const checkOffers = async () => {" in src:
            src = _replace_once(src, POLL_EXTEND_ANCHOR, POLL_EXTEND_BLOCK, "index.tsx rps poll extend", failures)
        elif "const checkRps = async () => {" not in src:
            src = _replace_once(src, STANDALONE_POLL_ANCHOR, STANDALONE_POLL_BLOCK, "index.tsx rps standalone poll", failures)
        INDEX.write_text(src, encoding="utf-8")

    # Verify the landed behaviours, not just the marker.
    api_src = API.read_text(encoding="utf-8")
    src = INDEX.read_text(encoding="utf-8")
    for needle in (
        "export const challengeRps",
        "export const getPendingRps",
        "export const respondRps",
        "export const throwRps",
        "export const getRpsGame",
        "export const cancelRps",
        "/rps/challenge",
        "/rps/pending/${playerId}",
        "/rps/respond",
        "/rps/throw",
        "/rps/game/${gameId}?player_id=${playerId}",
        "/rps/cancel",
    ):
        if needle not in api_src:
            failures.append("api.ts missing: %s" % needle)
    for needle in (
        "challengeRps,",
        "getPendingRps,",
        "respondRps,",
        "throwRps,",
        "getRpsGame,",
        "cancelRps,",
        "handleRpsChallenge",
        "handleRpsRespond",
        "handleRpsThrow",
        "handleRpsCancel",
        "handleRpsDone",
        "rpsGame",
        "rpsIncoming",
        "rpsSeenIdsRef",
        "ROCK PAPER SCISSORS",
        "Waiting for {rpsGame.other_name} to respond",
        "challenged you!",
        "YES — LET'S PLAY",
        "CHOOSE YOUR THROW",
        "YOU WIN!",
        "YOU LOSE",
        "checkRps",
        "setInterval(async () => {",
        "rpsThrows",
        "rpsResultLine",
    ):
        if needle not in src:
            failures.append("index.tsx missing: %s" % needle)
    # The poll must be a 15s one (extended trade poll or standalone) — never 1s.
    if ("setInterval(checkRps, 15000)" not in src
            and "setInterval(() => { checkOffers(); checkRps(); }, 15000)" not in src):
        failures.append("index.tsx missing the 15s RPS poll (extended or standalone)")
    if "setInterval(checkRps, 1000)" in src or "setInterval(checkOffers, 1000)" in src:
        failures.append("index.tsx has a 1s poll — must be 15s")
    if "getPendingRps(playerId)" not in src:
        failures.append("index.tsx missing getPendingRps call")
    if failures:
        for f in failures:
            print("RPS_GAME_FRONTEND_FAIL " + f)
        return 1
    if src.count("{") != src.count("}"):
        print("RPS_GAME_FRONTEND_FAIL unbalanced braces in index.tsx")
        return 1
    if src.count("(") != src.count(")"):
        print("RPS_GAME_FRONTEND_FAIL unbalanced parens in index.tsx")
        return 1
    print("RPS_GAME_FRONTEND_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
