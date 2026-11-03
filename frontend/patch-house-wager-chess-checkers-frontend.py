#!/usr/bin/env python3
"""Street Legends frontend: PvP cash wager UI for Chess & Checkers (SECOND patch).

Runs AFTER the base Chess & Checkers frontend patch. Edits frontend/app/(tabs)/index.tsx:
  - PvP lobby: host wager-amount input + PROPOSE, guest AGREE / DECLINE,
    wager status display, insufficient-cash warning (from the backend detail),
    winner cash result display. Both players must agree; no wager moves without it.
  - PvP game modal: on mount with an agreed wager, calls wager/start (cash is
    deducted from both players then; a failed start leaves the match unwagered).
  - Game end: calls wager/settle. Chess settles on the page finished state (checkmate winner color mapped to host/guest; stalemate or insufficient material settles as a draw); the game poll also settles if it sees a finished room with a held wager.
  - Leaving a PLAYING room with a held wager is paid on the server side by the
    backend leave handler (remaining player wins the pot); the frontend leave
    paths are unchanged.
IN-GAME Street Legends cash only. NOT real money, NOT play chips.
Emoji are literal characters, never Unicode escapes. Every "already present"
check is scoped to the component being wired. If any section prints WARNING,
send the full output before re-running: that section did not land even if the
OK marker prints.

Run from repo root: python3 frontend/patch-house-wager-chess-checkers.py
Idempotent: re-running prints ALREADY_APPLIED and changes nothing.
Frontend only: reload Expo Go to check.
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
MARKER = "// WAGER_CHESS_CHECKERS_FRONTEND_V1"
LOBBY = "ChessCheckersPvpModal"
GAME = "ChessCheckersPvpGameModal"
MSG = "chess-checkers"
EVENT = "chess-checkers-room"


def comp_pos(src, comp):
    return src.find("const " + comp + " = ")


def line_end(src, pos):
    e = src.find("\n", pos)
    return len(src) if e == -1 else e + 1


def insert_after_comp_line(src, comp, needle, text):
    c = comp_pos(src, comp)
    if c == -1:
        return src, False
    n = src.find(needle, c)
    if n == -1:
        return src, False
    at = line_end(src, n)
    return src[:at] + text + "\n" + src[at:], True


def insert_before_comp_line(src, comp, needle, text):
    c = comp_pos(src, comp)
    if c == -1:
        return src, False
    n = src.find(needle, c)
    if n == -1:
        return src, False
    ls = src.rfind("\n", 0, n) + 1
    return src[:ls] + text + "\n" + src[ls:], True


def main():
    warnings = []
    if not INDEX.exists():
        print("CHESS_CHECKERS_WAGER_ERROR: index.tsx not found. Run from repo root.")
        return 1
    src = INDEX.read_text()
    if MARKER in src:
        print("CHESS_CHECKERS_WAGER_ALREADY_APPLIED")
        return 0
    lobby_state = """  const [wagerAmount, setWagerAmount] = useState('');
  const [wagerInfo, setWagerInfo] = useState('');
  const wagerPost = async (action: string, body: any) => {
    if (!room?.code) return null;
    try {
      const res = await fetch(CC_API_BASE + '/api/chess_checkers/rooms/rooms/' + room.code + '/wager/' + action, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { setWagerInfo(data?.detail || 'Wager request failed.'); return null; }
      setRoom(data); return data;
    } catch (e) { setWagerInfo('Wager rooms are not live yet - the backend still needs a Deploy.'); return null; }
  };
  const proposeWager = async () => {
    const amount = parseInt(wagerAmount, 10);
    if (!amount || amount <= 0) { setWagerInfo('Enter a cash amount above 0.'); return; }
    setWagerInfo('');
    const data = await wagerPost('propose', { player_id: playerId, amount: amount });
    if (data) setWagerInfo('Wager proposed: $' + amount + '. Waiting for your friend to agree.');
  };
  const agreeWager = async () => {
    setWagerInfo('');
    const data = await wagerPost('agree', { player_id: playerId });
    if (data) setWagerInfo('Wager agreed: $' + data.wager_amount + '. Cash is taken when the game starts.');
  };
  const declineWager = async () => {
    setWagerInfo('');
    await wagerPost('decline', { player_id: playerId });
  };"""
    lobby_panel = """            {room && room.status !== 'finished' ? (
              <View style={{ backgroundColor: '#1a1a1a', borderRadius: 8, padding: 10, marginBottom: 12 }}>
                <Text style={{ color: '#ffffff', fontWeight: '800', marginBottom: 6 }}>💰 CASH WAGER - Street Legends cash, not real money</Text>
                {room.wager_status === 'held' ? (
                  <Text style={{ color: '#f39c12', fontSize: 13 }}>Wager held: ${room.wager_amount} each. Winner takes ${room.wager_amount * 2}.</Text>
                ) : room.wager_status === 'agreed' ? (
                  <Text style={{ color: '#f39c12', fontSize: 13 }}>Wager agreed: ${room.wager_amount}. Cash is taken from both players when the game starts.</Text>
                ) : room.wager_status === 'proposed' ? (
                  playerId === room.host_id ? (
                    <Text style={{ color: '#cccccc', fontSize: 13 }}>Wager proposed: ${room.wager_amount}. Waiting for {foeName} to agree or decline.</Text>
                  ) : (
                    <View>
                      <Text style={{ color: '#ffffff', fontSize: 13, marginBottom: 6 }}>{foeName} proposes a ${room.wager_amount} cash wager. Make sure you have at least that much cash before agreeing.</Text>
                      <View style={{ flexDirection: 'row', gap: 8 }}>
                        <TouchableOpacity onPress={agreeWager} style={{ flex: 1, backgroundColor: '#2e7d32', paddingVertical: 10, borderRadius: 8 }}>
                          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>AGREE</Text>
                        </TouchableOpacity>
                        <TouchableOpacity onPress={declineWager} style={{ flex: 1, backgroundColor: '#666666', paddingVertical: 10, borderRadius: 8 }}>
                          <Text style={{ color: '#ffffff', fontWeight: '800', textAlign: 'center' }}>DECLINE</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  )
                ) : room.wager_status === 'paid' ? (
                  <Text style={{ color: '#2e7d32', fontSize: 13, fontWeight: '800' }}>{room.wager_winner_id === playerId ? ('You won the wager: $' + (room.wager_amount * 2) + ' cash!') : (foeName + ' won the wager.')}</Text>
                ) : room.wager_status === 'refunded' ? (
                  <Text style={{ color: '#cccccc', fontSize: 13 }}>Wager refunded - the game was a draw.</Text>
                ) : playerId === room.host_id ? (
                  <View>
                    <Text style={{ color: '#cccccc', fontSize: 12, marginBottom: 6 }}>Propose a cash wager. Both players must agree, and both need at least this much cash.</Text>
                    <View style={{ flexDirection: 'row', gap: 8 }}>
                      <TextInput value={wagerAmount} onChangeText={setWagerAmount} keyboardType="number-pad" placeholder="Cash amount" placeholderTextColor="#888888" style={{ flex: 1, backgroundColor: '#222222', color: '#ffffff', padding: 10, borderRadius: 8 }} />
                      <TouchableOpacity onPress={proposeWager} style={{ backgroundColor: '#2e7d32', paddingVertical: 10, paddingHorizontal: 16, borderRadius: 8 }}>
                        <Text style={{ color: '#ffffff', fontWeight: '800' }}>PROPOSE</Text>
                      </TouchableOpacity>
                    </View>
                  </View>
                ) : (
                  <Text style={{ color: '#cccccc', fontSize: 13 }}>No wager yet - the host can propose one.</Text>
                )}
                {wagerInfo ? (<Text style={{ color: '#f39c12', fontSize: 12, marginTop: 6 }}>{wagerInfo}</Text>) : null}
              </View>
            ) : null}
"""
    start_effect = """  useEffect(() => {
    if (!visible || !code || room?.wager_status !== 'agreed') return;
    const startWager = async () => {
      try {
        const res = await fetch(CC_API_BASE + '/api/chess_checkers/rooms/rooms/' + code + '/wager/start', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: me }) });
        if (!res.ok) { const d = await res.json().catch(() => ({})); if (d?.detail) setPvpError(d.detail); }
      } catch (e) {}
    };
    startWager();
  }, [visible, code]);"""
    settle_fn = """  const settleWagerChess = async (winnerColor: string | null) => {
    if (settleDoneRef.current) return;
    settleDoneRef.current = true;
    const hostColor = game === 'checkers' ? 'r' : 'w';
    const winId = !winnerColor ? '' : (winnerColor === hostColor ? hostId : guestId);
    try { await fetch(CC_API_BASE + '/api/chess_checkers/rooms/rooms/' + code + '/wager/settle', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ player_id: me, outcome: winId ? 'win' : 'draw', winner_id: winId }) }); } catch (e) {}
  };"""
    state_settle = """          if (msg.state.status === 'finished') { settleWagerChess(msg.state.winner || null); }"""
    poll_settle = """            if (data.wager_status === 'held' && data.status === 'finished' && data.state) { settleWagerChess(data.state.winner || null); }"""
    # 1. lobby state + wager API functions (after the lobby busy line)
    src, ok = insert_after_comp_line(src, LOBBY, "const [busy, setBusy] = useState(false);", lobby_state)
    print("OK: lobby wager state + API functions added" if ok else "WARNING: lobby wager state NOT added (busy line anchor not found in " + LOBBY + ")")
    if not ok:
        warnings.append("lobby-state")
    # 2. lobby wager panel (before the PLAY button block)
    src, ok = insert_before_comp_line(src, LOBBY, "{canPlay ? (", lobby_panel)
    print("OK: lobby wager panel added" if ok else "WARNING: lobby wager panel NOT added (PLAY block anchor not found in " + LOBBY + ")")
    if not ok:
        warnings.append("lobby-panel")
    # 3. game modal settle guard ref (after lastRoomRef)
    src, ok = insert_after_comp_line(src, GAME, "const lastRoomRef = useRef<string>('');", "  const settleDoneRef = useRef(false);")
    print("OK: game settle guard ref added" if ok else "WARNING: game settle guard ref NOT added (lastRoomRef anchor not found in " + GAME + ")")
    if not ok:
        warnings.append("settle-ref")
    # 4. game modal settle function (before handlePvpMessage)
    src, ok = insert_before_comp_line(src, GAME, "const handlePvpMessage = async (event: any) => {", settle_fn)
    print("OK: game settle function added" if ok else "WARNING: game settle function NOT added (handlePvpMessage anchor not found in " + GAME + ")")
    if not ok:
        warnings.append("settle-fn")
    # 5. game modal wager start effect (after the poll effect close)
    src, ok = insert_after_comp_line(src, GAME, "}, [visible, code]);", start_effect)
    print("OK: game wager start effect added" if ok else "WARNING: game wager start effect NOT added (poll effect anchor not found in " + GAME + ")")
    if not ok:
        warnings.append("start-effect")
    # 6. game modal state-branch settle (after the state post data line)
    c = comp_pos(src, GAME)
    ok = False
    if c != -1:
        st = src.find("if (msg?.type === '" + MSG + "-state' && msg.state) {", c)
        if st != -1:
            dl = src.find("if (data) lastRoomRef.current = JSON.stringify(data);", st)
            if dl != -1:
                at = line_end(src, dl)
                src = src[:at] + state_settle + "\n" + src[at:]
                ok = True
    print("OK: game state-branch settle added" if ok else "WARNING: game state-branch settle NOT added (state post anchor not found in " + GAME + ")")
    if not ok:
        warnings.append("state-settle")
    # 7. game modal poll settle (after the room inject line)
    src, ok = insert_after_comp_line(src, GAME, 'dispatchEvent(new CustomEvent("' + EVENT + '"', poll_settle)
    print("OK: game poll settle added" if ok else "WARNING: game poll settle NOT added (room inject anchor not found in " + GAME + ")")
    if not ok:
        warnings.append("poll-settle")
    # marker (before the lobby component) so re-runs skip cleanly
    c = comp_pos(src, LOBBY)
    if c != -1:
        src = src[:c] + MARKER + "\n" + src[c:]
    INDEX.write_text(src)
    for w in warnings:
        print("WARNING: section skipped: " + w)
    print("WAGER_CHESS_CHECKERS_FRONTEND_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
