#!/usr/bin/env python3
"""Street Legends frontend: pool PvP spec for the six non-pool house
games (darts, cards, dominoes, chess_checkers, texas_holdem, scrabble)
in ONE patch. Frontend / Expo Go only. NEVER touches the pool modals.

Per game, scoped to that game's own modal component range (from its
`const <Name> = (` line to the next top-level `const ` line):
 1. BAKED IDENTITIES (game modal): a baked HTML variable right after
    the modal's pvpConfig line, replacing the page's fallback literal
    with the real config JSON, and the WebView source prop switched to
    the baked variable. Texas is the exception: no baked replace (its
    page-config line could not be established) — it gets
    injectedJavaScript={pvpConfig} after its before-content-loaded line
    as a best-effort re-apply, and Texas identities still need a device
    test.
 2. AUTO-START (room modal): joinRoom calls onPlay() after a successful
    join (guest's game opens on join); a prev-status effect calls
    onPlay() only on a waiting->playing transition (host's game opens
    when the friend joins; closing the game back to the room screen
    does not re-trigger). PLAY stays as fallback.
 3. CHAT REMOVAL (room modal): the CHAT block (header, list, input,
    SEND row) is deleted and replaced by a PVP_ALL_NOCHAT marker
    comment. Backend chat endpoints are left alone (unused).
 4. REJOIN BUTTONS (room modal): an activeRoom state + effect that
    fetches <BASE>/api/<base>/rooms/active/<playerId> when the modal is
    visible with no room selected, and a REJOIN ROOM {code} button
    before CREATE ROOM that restores the room and opens the game when
    status is 'playing'. The base identifier is read off that modal's
    own create-fetch call, never assumed.

Idempotent: every part carries a per-game marker comment; a second run
prints ALREADY_APPLIED per part and changes nothing. If brace/paren
open-minus-close deltas change, NOTHING is written. If one game's
anchors miss, a WARNING is printed for that game and the others still
apply. Run from /app (or pass the root)."""
import re, sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"

# key, room modal, game modal, fetch base path, html const, baked var,
# config keys (in pvpConfig JSON order), fallback literal (None = special)
GAMES = [
    ("DARTS", "DartPvpModal", "DartPvpGameModal", "darts", "DART_PVP_HTML",
     "dartsBakedHtml", ["me", "foe", "foeName", "hostId"],
     "{ me: 'you', foe: 'friend', foeName: 'FRIEND', hostId: 'you' }"),
    ("CARDS", "CardPvpModal", "CardPvpGameModal", "cards", "CARD_PVP_HTML",
     "cardsBakedHtml", ["me", "foe", "foeName", "hostId", "game", "seed"],
     "{ me: 'you', foe: 'friend', foeName: 'FRIEND', hostId: 'you', game: 'gin', seed: 12345 }"),
    ("DOMINOES", "DominoPvpModal", "DominoPvpGameModal", "dominoes", "DOMINO_PVP_HTML",
     "dominoesBakedHtml", ["me", "foe", "foeName", "hostId", "seed"],
     "{me: 'host', foe: 'guest', foeName: 'FRIEND', hostId: 'host', seed: 12345}"),
    ("CHESS", "ChessCheckersPvpModal", "ChessCheckersPvpGameModal", "chess_checkers",
     "CHESS_CHECKERS_PVP_HTML", "chessBakedHtml",
     ["me", "foe", "foeName", "hostId", "game", "myColor"], "CHESS_SPECIAL"),
    ("TEXAS", "TexasHoldemPvpModal", "TexasHoldemPvpGameModal", "texas_holdem",
     "TEXAS_HOLDEM_PVP_HTML", None, None, "TEXAS_SPECIAL"),
    ("SCRABBLE", "ScrabblePvpModal", "ScrabblePvpGameModal", "scrabble", "SCRABBLE_PVP_HTML",
     "scrabbleBakedHtml", ["me", "foe", "foeName", "hostId", "seed"],
     '{ me: "host", foe: "guest", foeName: "FRIEND", hostId: "host", seed: 12345 }'),
]

CHESS_TARGET = 'var PVP = (typeof window !== "undefined" && window.CHESS_CHECKERS_PVP) ? window.CHESS_CHECKERS_PVP : {};'


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def modal_range(src, name):
    m = re.search(r"^const " + re.escape(name) + r" = \(", src, re.M)
    if not m:
        return None
    start = m.start()
    nxt = re.search(r"^const ", src[m.end():], re.M)
    end = m.end() + nxt.start() if nxt else len(src)
    return (start, end)


def cfg_json(keys):
    # Config variables in the game modals are named me/foeId/foeName/
    # hostId/game/seed/myColor; the JSON keys are me/foe/foeName/...
    var = {"me": "me", "foe": "foeId", "foeName": "foeName",
           "hostId": "hostId", "game": "game", "seed": "seed",
           "myColor": "myColor"}
    return "{" + ", ".join("%s: %s" % (k, var[k]) for k in keys) + "}"


def part_baked(src, g):
    key, _rm, gm, _bp, html, baked, keys, fb = g
    # Texas has no baked marker: its idempotency marker is the re-apply tag.
    marker = "PVP_ALL_TEXAS_REAPPLY" if key == "TEXAS" else "PVP_ALL_BAKED_" + key
    rng = modal_range(src, gm)
    if not rng:
        print("WARNING: %s game modal not found - baked identities SKIPPED" % key)
        return src, False
    s, e = rng
    seg = src[s:e]
    if marker in seg:
        print("%s_ALREADY_APPLIED" % marker)
        return src, True
    if key == "TEXAS":
        m = re.search(r"injectedJavaScriptBeforeContentLoaded=\{pvpConfig\}", seg)
        if not m:
            print("WARNING: TEXAS injection anchor not found - re-apply SKIPPED")
            return src, False
        ins = "\n            injectedJavaScript={pvpConfig + '/* PVP_ALL_TEXAS_REAPPLY */'}"
        seg = seg[:m.end()] + ins + seg[m.end():]
        print("PVP_ALL_TEXAS_REAPPLY_OK (baked replace skipped: page-config line not established; device test still needed)")
        return src[:s] + seg + src[e:], True
    m = re.search(r"const pvpConfig = [^\n]*;\n", seg)
    if not m:
        print("WARNING: %s pvpConfig not found - baked identities SKIPPED" % key)
        return src, False
    if key == "CHESS":
        repl = ("const %s = %s.replace('%s', 'var PVP = ' + JSON.stringify(%s) + ';');"
                % (baked, html, CHESS_TARGET, cfg_json(keys)))
    else:
        repl = ("const %s = %s.replace(%s, JSON.stringify(%s));"
                % (baked, html, repr(fb), cfg_json(keys)))
    block = "\n  // %s: real ids baked into the page source.\n  %s\n" % (marker, repl)
    seg2 = seg[:m.end()] + block + seg[m.end():]
    sm = re.search(r"source=\{\{\s*html:\s*" + re.escape(html) + r"\s*\}\}", seg2)
    if not sm:
        print("WARNING: %s source prop not found - baked identities SKIPPED" % key)
        return src, False
    seg2 = seg2[:sm.start()] + "source={{ html: %s }}" % baked + seg2[sm.end():]
    print("PVP_ALL_BAKED_%s_OK" % key)
    return src[:s] + seg2 + src[e:], True


def part_autostart(src, g):
    key, rm, _gm, _bp, _html, _b, _k, _fb = g
    rng = modal_range(src, rm)
    if not rng:
        print("WARNING: %s room modal not found - auto-start SKIPPED" % key)
        return src, False
    s, e = rng
    seg = src[s:e]
    ok = True
    jmark = "PVP_ALL_AUTOPLAY_JOIN_" + key
    if jmark in seg:
        print("PVP_ALL_AUTOPLAY_JOIN_%s_ALREADY_APPLIED" % key)
    else:
        jm = re.search(r"const joinRoom = async \(\) => \{", seg)
        if not jm:
            print("WARNING: %s joinRoom not found - guest auto-start SKIPPED" % key)
            ok = False
        else:
            sm = re.search(r"\n([ \t]*)setRoom\(data\);\n", seg[jm.end():])
            if not sm:
                print("WARNING: %s joinRoom setRoom not found - guest auto-start SKIPPED" % key)
                ok = False
            else:
                pos = jm.end() + sm.end() - 1
                ind = sm.group(1)
                seg = (seg[:pos] + "\n" + ind + "// " + jmark +
                       ": game opens on successful join.\n" + ind + "onPlay();" + seg[pos:])
                print("PVP_ALL_AUTOPLAY_JOIN_%s_OK" % key)
    hmark = "PVP_ALL_AUTOPLAY_HOST_" + key
    if hmark in seg:
        print("PVP_ALL_AUTOPLAY_HOST_%s_ALREADY_APPLIED" % key)
    else:
        ref = "prevStatusRef" + key.title().replace("_", "")
        cm = re.search(r"const canPlay = room && room\.status === 'playing';", seg)
        if cm:
            anchor_end, note = cm.end(), ""
        else:
            ret = seg.find("return (")
            body = seg[:ret] if ret != -1 else seg
            fm = re.search(r"[^\n]*room\.status[^\n]*\n", body)
            if not fm:
                print("WARNING: %s status anchor not found - host auto-start SKIPPED" % key)
                return src[:s] + seg + src[e:], ok
            anchor_end, note = fm.end(), " (fallback room-status anchor)"
        block = (
            "\n  // %s: host's game opens on waiting->playing flip.\n"
            "  const %s = useRef<string>(room?.status || '');\n"
            "  useEffect(() => {\n"
            "    const prev = %s.current;\n"
            "    %s.current = room?.status || '';\n"
            "    if (room?.status === 'playing' && prev === 'waiting') { onPlay(); }\n"
            "  }, [room?.status]);"
            % (hmark, ref, ref, ref))
        seg = seg[:anchor_end] + block + seg[anchor_end:]
        print("PVP_ALL_AUTOPLAY_HOST_%s_OK%s" % (key, note))
    return src[:s] + seg + src[e:], ok


def part_chat(src, g):
    key, rm, _gm, _bp, _html, _b, _k, _fb = g
    marker = "PVP_ALL_NOCHAT"
    rng = modal_range(src, rm)
    if not rng:
        print("WARNING: %s room modal not found - chat removal SKIPPED" % key)
        return src, False
    s, e = rng
    seg = src[s:e]
    if marker in seg:
        print("PVP_ALL_NOCHAT_%s_ALREADY_APPLIED" % key)
        return src, True
    chat_at = seg.find("}}>CHAT</Text>")
    if chat_at == -1:
        print("WARNING: %s CHAT header not found - chat removal SKIPPED" % key)
        return src, False
    line_start = seg.rfind("\n", 0, chat_at) + 1
    indent = re.match(r"[ \t]*", seg[line_start:]).group(0)
    send_at = seg.find(">SEND</Text>", chat_at)
    if send_at == -1:
        print("WARNING: %s SEND button not found - chat removal SKIPPED" % key)
        return src, False
    touch_end = seg.find("</TouchableOpacity>", send_at)
    view_end = seg.find("</View>", touch_end) if touch_end != -1 else -1
    if touch_end == -1 or view_end == -1:
        print("WARNING: %s chat block end not found - chat removal SKIPPED" % key)
        return src, False
    end = view_end + len("</View>")
    seg = seg[:line_start] + indent + "{/* PVP_ALL_NOCHAT: chat removed */}\n" + seg[end:]
    print("PVP_ALL_NOCHAT_%s_OK" % key)
    return src[:s] + seg + src[e:], True


def part_rejoin(src, g):
    key, rm, _gm, bp, _html, _b, _k, _fb = g
    marker = "PVP_ALL_REJOIN_" + key
    rng = modal_range(src, rm)
    if not rng:
        print("WARNING: %s room modal not found - rejoin SKIPPED" % key)
        return src, False
    s, e = rng
    seg = src[s:e]
    if marker in seg:
        print("PVP_ALL_REJOIN_%s_ALREADY_APPLIED" % key)
        return src, True
    base_m = re.search(r"(\w+) \+ '/api/" + re.escape(bp) + r"/rooms/create'", seg)
    if not base_m:
        print("WARNING: %s create-fetch base not found - rejoin SKIPPED" % key)
        return src, False
    base = base_m.group(1)
    busy = "const [busy, setBusy] = useState(false);"
    if busy not in seg:
        print("WARNING: %s busy anchor not found - rejoin SKIPPED" % key)
        return src, False
    st = "activeRoom" + key.title().replace("_", "")
    setst = "setActiveRoom" + key.title().replace("_", "")
    state_block = (
        "\n  // %s: offer the player's live room back after a boot-out.\n"
        "  const [%s, %s] = useState<any | null>(null);\n"
        "  useEffect(() => {\n"
        "    if (!visible || room) return;\n"
        "    let cancelled = false;\n"
        "    (async () => {\n"
        "      try {\n"
        "        const res = await fetch(%s + '/api/%s/rooms/active/' + playerId);\n"
        "        if (!cancelled && res.ok) { const d = await res.json(); %s(d); }\n"
        "        else if (!cancelled) { %s(null); }\n"
        "      } catch (e) { if (!cancelled) %s(null); }\n"
        "    })();\n"
        "    return () => { cancelled = true; };\n"
        "  }, [visible, room?.code]);"
        % (marker, st, setst, base, bp, setst, setst, setst))
    seg = seg.replace(busy, busy + state_block, 1)
    ci = seg.find("onPress={createRoom}")
    if ci == -1:
        print("WARNING: %s CREATE ROOM button not found - rejoin button SKIPPED" % key)
        return src[:s] + seg + src[e:], False
    t_start = seg.rfind("<TouchableOpacity", 0, ci)
    if t_start == -1:
        print("WARNING: %s CREATE button start not found - rejoin button SKIPPED" % key)
        return src[:s] + seg + src[e:], False
    line_start = seg.rfind("\n", 0, t_start) + 1
    btn = (
        "            {%s ? (\n"
        "              <TouchableOpacity onPress={() => { setRoom(%s); if (%s.status === 'playing') { onPlay(); } }} style={{ backgroundColor: '#f39c12', paddingVertical: 12, borderRadius: 8, marginBottom: 12 }}>\n"
        "                <Text style={{ color: '#111111', fontWeight: '800', textAlign: 'center' }}>REJOIN ROOM {%s.code}</Text>\n"
        "              </TouchableOpacity>\n"
        "            ) : null}\n" % (st, st, st, st))
    seg = seg[:line_start] + btn + seg[line_start:]
    print("PVP_ALL_REJOIN_%s_OK (base %s)" % (key, base))
    return src[:s] + seg + src[e:], True


def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - nothing changed")
        return 1
    src = IDX.read_text(errors="ignore")
    orig = delta(src)
    all_ok = True
    for g in GAMES:
        src, ok1 = part_baked(src, g)
        src, ok2 = part_autostart(src, g)
        src, ok3 = part_chat(src, g)
        src, ok4 = part_rejoin(src, g)
        if not (ok1 and ok2 and ok3 and ok4):
            all_ok = False
    # Pool must be untouched: pool modals carry no PVP_ALL markers.
    for pool_name in ("PoolPvpModal", "PoolPvpGameModal"):
        rng = modal_range(src, pool_name)
        if rng and "PVP_ALL_" in src[rng[0]:rng[1]]:
            print("WARNING: pool modal %s touched - NOT WRITING" % pool_name)
            return 1
    if delta(src) != orig:
        print("WARNING: brace/paren balance changed - index.tsx NOT written")
        return 1
    if src.count("PVP_ALL_NOCHAT") < 6:
        print("NOTE: NOCHAT markers in file: %d (expected 6 for the six games; pool's chat was already removed separately)"
              % src.count("PVP_ALL_NOCHAT"))
    IDX.write_text(src)
    print("PVP_ALL_OK" if all_ok else "PVP_ALL_PARTIAL")
    return 0


if __name__ == "__main__":
    sys.exit(main())
