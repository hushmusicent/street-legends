#!/usr/bin/env python3
"""Street Legends frontend: pool PvP spec — real identities, auto-start,
no chat. (User spec 2026-11-04 01:38 EST.)

1. IDENTITIES (the 'both phones are the same player' bug, stronger fix):
   bake the real player ids into the game's own page source at render
   time (replace the fallback literal in POOL_PVP_HTML with the room's
   real me/foe/foeName/hostId), so the game can never run on the
   'you'/'friend' fallback regardless of whether any WebView injection
   fires. Creator (host) therefore breaks first; the guest's input stays
   blocked (turn !== ME, already in the game) until the turn reaches them.
2. AUTO-START: the game opens on both phones as soon as the second
   player is in — guest: joinRoom calls onPlay() right after a successful
   join; host: an effect fires when the room status flips waiting ->
   playing. PLAY stays as a fallback. Closing the game back to the room
   screen does NOT re-trigger it (no waiting->playing flip on reopen).
3. NO CHAT: the CHAT section (header, message list, input, SEND) is
   removed from the room screen, and the 'Chat lives on the room screen.'
   line is removed from the game hint. Backend chat endpoints are left
   alone (unused, harmless).
Frontend / Expo Go only."""
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
IDX = ROOT / "frontend/app/(tabs)/index.tsx"
HTML = ROOT / "frontend/components/PoolGamePvpHtml.ts"

def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))

def main():
    if not IDX.exists():
        print("WARNING: index.tsx not found - nothing changed")
        return 1
    src = IDX.read_text(errors="ignore")
    orig_delta = delta(src)
    landed = []

    # ---- Part A: bake ids into page source ----
    cfg_anchor = "const pvpConfig = 'window.POOL_PVP = ' + JSON.stringify({ me: me, foe: foeId, foeName: foeName, hostId: hostId }) + '; true;';"
    if "// POOL_PVP_SPEC_CFG" in src:
        print("POOL_PVP_SPEC_CFG_ALREADY_APPLIED")
        landed.append("cfg")
    elif cfg_anchor in src and "source={{ html: POOL_PVP_HTML }}" in src:
        cfg_block = (
            "\n  // POOL_PVP_SPEC_CFG: bake real ids into the page itself.\n"
            "  const pvpHtml = POOL_PVP_HTML.replace(\"{ me: 'you', foe: 'friend', foeName: 'FRIEND', hostId: 'you' }\", JSON.stringify({ me: me, foe: foeId, foeName: foeName, hostId: hostId }));"
        )
        src = src.replace(cfg_anchor, cfg_anchor + cfg_block, 1)
        src = src.replace("source={{ html: POOL_PVP_HTML }}", "source={{ html: pvpHtml }}", 1)
        print("POOL_PVP_SPEC_CFG_OK")
        landed.append("cfg")
    else:
        print("WARNING: cfg anchors not matched - identities NOT changed")

    # ---- Part B1: guest auto-starts on successful join ----
    if "// POOL_PVP_SPEC_AUTOPLAY_JOIN" in src:
        print("POOL_PVP_SPEC_AUTOPLAY_JOIN_ALREADY_APPLIED")
        landed.append("join")
    else:
        j = src.find("const joinRoom = async () => {")
        if j == -1:
            print("WARNING: joinRoom not found - guest auto-start NOT added")
        else:
            k = src.find("setRoom(data);", j, j + 1500)
            if k == -1:
                print("WARNING: joinRoom setRoom not found - guest auto-start NOT added")
            else:
                src = src[:k + len("setRoom(data);")] + "\n      // POOL_PVP_SPEC_AUTOPLAY_JOIN: game starts once the code is in.\n      onPlay();" + src[k + len("setRoom(data);"):]
                print("POOL_PVP_SPEC_AUTOPLAY_JOIN_OK")
                landed.append("join")

    # ---- Part B2: host auto-starts on waiting -> playing ----
    if "// POOL_PVP_SPEC_AUTOPLAY_HOST" in src:
        print("POOL_PVP_SPEC_AUTOPLAY_HOST_ALREADY_APPLIED")
        landed.append("host")
    else:
        canplay = "const canPlay = room && room.status === 'playing';"
        if canplay in src:
            host_block = (
                "\n  // POOL_PVP_SPEC_AUTOPLAY_HOST: host's game opens when the\n"
                "  // room flips waiting -> playing (not on reopen from the game).\n"
                "  const prevStatusRef = useRef<string>(room?.status || '');\n"
                "  useEffect(() => {\n"
                "    const prev = prevStatusRef.current;\n"
                "    prevStatusRef.current = room?.status || '';\n"
                "    if (room?.status === 'playing' && prev === 'waiting') { onPlay(); }\n"
                "  }, [room?.status]);"
            )
            src = src.replace(canplay, canplay + host_block, 1)
            print("POOL_PVP_SPEC_AUTOPLAY_HOST_OK")
            landed.append("host")
        else:
            print("WARNING: canPlay anchor not matched - host auto-start NOT added")

    # ---- Part C: remove chat UI from the room screen ----
    if "POOL_PVP_SPEC_NOCHAT" in src:
        print("POOL_PVP_SPEC_NOCHAT_ALREADY_APPLIED")
        landed.append("chat")
    else:
        chat_at = src.find("}}>CHAT</Text>")
        if chat_at == -1:
            print("WARNING: CHAT header not found - chat NOT removed")
        else:
            line_start = src.rfind("\n", 0, chat_at) + 1
            send_at = src.find(">SEND</Text>", chat_at)
            if send_at == -1:
                print("WARNING: SEND button not found - chat NOT removed")
            else:
                touch_end = src.find("</TouchableOpacity>", send_at)
                view_end = src.find("</View>", touch_end)
                if touch_end == -1 or view_end == -1:
                    print("WARNING: chat block end not found - chat NOT removed")
                else:
                    end = view_end + len("</View>")
                    src = src[:line_start] + "            {/* POOL_PVP_SPEC_NOCHAT: chat removed by request */}\n" + src[end:]
                    print("POOL_PVP_SPEC_NOCHAT_OK")
                    landed.append("chat")

    if delta(src) != orig_delta:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    IDX.write_text(src)

    # ---- Part C2: game hint line (separate file) ----
    if HTML.exists():
        h = HTML.read_text(errors="ignore")
        if "Chat lives on the room screen." in h:
            HTML.write_text(h.replace(" Chat lives on the room screen.", ""))
            print("POOL_PVP_SPEC_HINT_OK")
        else:
            print("POOL_PVP_SPEC_HINT_ALREADY_APPLIED")
    else:
        print("WARNING: PoolGamePvpHtml.ts not found - hint line NOT changed")

    if len(landed) == 4:
        print("POOL_PVP_SPEC_OK")
        return 0
    print("POOL_PVP_SPEC_PARTIAL: " + ",".join(landed))
    return 0

if __name__ == "__main__":
    sys.exit(main())
