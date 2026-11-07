#!/usr/bin/env python3
"""Park live probe: print the LIVE park code on /app so the basketball
port can be built against what is actually there, not what the patches
assumed.

CONTEXT (parent, 2026-11-07): the user approved the park basketball
preview (~/workspace/street-legends/park-basketball-preview.html,
72,872 bytes) and said "Wire it to the all the parks and give the
park scene a scroll left and right". The parks feature was built
2026-11-05 (backend/patch-park.py PARK_BACKEND_OK + frontend/
patch-park-frontend.py PARK_FRONTEND_OK, commit 5a85b814, sync 84)
but its RUN STATUS was never confirmed — neither patch's output was
ever sent. This diag is the probe that comes first, per his rule:
diagnose from the actual data before patching.

This probe is READ-ONLY: it never edits a file, never restarts
anything, and makes no network calls at all -- it only reads the
frontend/backend code under <root>. It prints:
  0. which files exist (index.tsx / api.ts / useMapQueries.ts /
     GameMap.tsx / server.py / package.json) + line counts
  1. BACKEND parks live? (/parks/nearby + enter/leave/heartbeat/
     presence endpoints, park_presence/parks/park_cache collections,
     Overpass URL + UA header in the park fetch)
  2. api.ts park client functions (getParksNearby + 4 presence fns)
  3. useMapQueries entity batch: calls in order + results[N]
     mappings — the batch index parks occupy live
  4. index.tsx park wiring: marker type, nearbyParks memo + spread,
     handleMarkerPress branch, popup ENTER, state vars, presence
     effect, PARK_BG (data URI or require?), the PARK interior Modal
     VERBATIM (picture / "Inside now" / LEAVE), and whether the modal
     already has a ScrollView / Basketball / activities
  5. GameMap.tsx park wiring: type union, color, icon, branch, sizing
  6. WebView/HTML game pattern live (the pattern the basketball port
     follows): PoolWebView lazy require, components/*Html.ts files
     present + imported, one exemplar game modal VERBATIM
     (WebView source/onMessage/CLOSE), one exemplar menu modal,
     react-native-webview in package.json
  7. Activity-center hall scroll pattern live (the pattern the park
     scene will copy): horizontal ScrollView + onLayout measurement +
     LEAVE placement
  8. exact unique anchors the port patch will use
  9. VERDICT: (a) parks fully live, (b) partially live (list what is
     missing), (c) parks not live at all

Run:  python3 minigame-diag/diag-park-live.py [--root /app]
"""
import argparse
import re
import sys
from pathlib import Path

MARKER = "PARK_LIVE_DIAG_V2_OK"

INDEX_CANDIDATES = [
    "frontend/app/(tabs)/index.tsx",
    "frontend/app/index.tsx",
]
API_PATH = "frontend/services/api.ts"
QUERIES_PATH = "frontend/hooks/useMapQueries.ts"
GAMEMAP_PATH = "frontend/components/GameMap.tsx"
SERVER_PATH = "backend/server.py"
PACKAGE_PATH = "frontend/package.json"

PARK_API_FNS = ["getParksNearby", "parkEnterPresence", "parkLeavePresence",
                "parkHeartbeatPresence", "getParkPresence"]

GAME_HTML_FILES = ["DartGameHtml.ts", "CardPvpHtml.ts", "PoolGameHtml.ts",
                   "DominoHtml.ts", "ScrabbleHtml.ts",
                   "ChessCheckersHtml.ts", "TexasHoldemHtml.ts",
                   "DartGamePvpHtml.ts", "PoolGamePvpHtml.ts",
                   "DominoPvpHtml.ts", "ScrabblePvpHtml.ts",
                   "ChessCheckersPvpHtml.ts", "TexasHoldemPvpHtml.ts"]


def read_file(path):
    try:
        return Path(path).read_text(errors="ignore").splitlines()
    except OSError:
        return None


def find_lines(lines, needle):
    """Plain substring search; returns [(idx, line)]. Never regexes
    over objects that may contain \\u{...} escapes."""
    return [(i, l) for i, l in enumerate(lines) if needle in l]


def find_re(lines, pattern, flags=0):
    rx = re.compile(pattern, flags)
    return [(i, l) for i, l in enumerate(lines) if rx.search(l)]


def show_context(lines, idx, before=3, after=3, label=None):
    if label:
        print(f"  [{label}] line {idx + 1}:")
    for j in range(max(0, idx - before), min(len(lines), idx + after + 1)):
        mark = ">>>" if j == idx else "   "
        print(f"  {mark} {j + 1:>5}: {lines[j][:170]}")


def print_block(title, lines, start, end):
    print(f"--- {title} (lines {start + 1}-{end}) ---")
    for i in range(start, min(end, len(lines))):
        print(f"{i + 1:>5}: {lines[i][:170]}")


def enclosing_function(lines, idx, window=200):
    pat = re.compile(
        r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\(")
    pat2 = re.compile(
        r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\(")
    for j in range(idx, max(-1, idx - window), -1):
        m = pat.match(lines[j]) or pat2.match(lines[j])
        if m:
            return m.group(1), j
    return None, None


def parse_batch_calls(text):
    """Split the Promise.all([...]) list in useMapQueries.ts by
    top-level commas (paren/bracket-depth aware, string aware).
    Returns the entry first-lines in order, or None if no batch."""
    start = text.find("Promise.all([")
    if start < 0:
        return None
    i = text.find("[", start)
    depth = 1
    instr = None
    esc = False
    entries = []
    cur = ""
    j = i + 1
    while j < len(text):
        ch = text[j]
        if instr:
            cur += ch
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == instr:
                instr = None
        else:
            if ch in ("'", '"', "`"):
                instr = ch
                cur += ch
            elif ch in "([{":
                depth += 1
                cur += ch
            elif ch in ")]}":
                depth -= 1
                if depth == 0:
                    if cur.strip():
                        entries.append(cur)
                    break
                cur += ch
            elif ch == "," and depth == 1:
                if cur.strip():
                    entries.append(cur)
                cur = ""
            else:
                cur += ch
        j += 1
    out = []
    for e in entries:
        first = e.strip().split("\n")[0].strip()
        out.append(first[:110])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    args = ap.parse_args()
    root = Path(args.root)
    missing = []

    print("=== park live diag (read-only, code only) ===")
    print(f"root: {root}")

    # ------------------------------------------------ 0. locate files
    print()
    print("=== 0. files ===")
    paths = {}
    for name, cands in [("index", INDEX_CANDIDATES),
                        ("api", [API_PATH]),
                        ("queries", [QUERIES_PATH]),
                        ("gamemap", [GAMEMAP_PATH]),
                        ("server", [SERVER_PATH]),
                        ("package", [PACKAGE_PATH])]:
        found = None
        for c in cands:
            p = root / c
            if p.is_file():
                found = p
                break
        paths[name] = found
        if found:
            n = len(read_file(found))
            print(f"{name}: {found} ({n} lines)")
        else:
            print(f"{name}: NOT FOUND (tried {cands})")
            missing.append(name + "-file")

    index_lines = read_file(paths["index"]) if paths["index"] else None
    api_lines = read_file(paths["api"]) if paths["api"] else None
    queries_lines = read_file(paths["queries"]) if paths["queries"] else None
    gamemap_lines = read_file(paths["gamemap"]) if paths["gamemap"] else None
    server_lines = read_file(paths["server"]) if paths["server"] else None

    # ------------------------------------------------ 1. backend parks
    print()
    print("=== 1. BACKEND parks live? (server.py) ===")
    if server_lines is None:
        print("server.py: NOT FOUND -- backend verdict unknown")
        missing.append("backend")
    else:
        backend = {
            "nearby route": "/parks/nearby",
            "nearby fn": "def nearby_parks",
            "enter fn": "def park_enter",
            "leave fn": "def park_leave",
            "heartbeat fn": "def park_heartbeat",
            "presence fn": "def park_presence",
            "park_presence coll": "park_presence",
            "park_cache coll": "park_cache",
            "park fetch fn": "_park_fetch_cell",
            "overpass url const": "PARK_OVERPASS_URL",
        }
        for label, needle in backend.items():
            hits = find_lines(server_lines, needle)
            print(f"  {label}: {len(hits)}x"
                  + (f" (lines {[i + 1 for i, _ in hits][:6]})"
                     if hits else " -- MISSING"))
            if not hits:
                missing.append("backend:" + label)
        # parks collection: the DB handle varies (patch detects it from
        # "<handle>.restaurants.find"), so match any "<handle>.parks.".
        pc = find_re(server_lines, r"\.\s*parks\s*\.\s*(update_one|find|find_one)")
        print(f"  parks coll (<handle>.parks.*): {len(pc)}x"
              + (f" (lines {[i + 1 for i, _ in pc][:6]})" if pc else
                 " -- MISSING"))
        if not pc:
            missing.append("backend:parks coll")
        url_hits = find_lines(server_lines, "PARK_OVERPASS_URL = ")
        if url_hits:
            print(f"  Overpass URL: {url_hits[0][1].strip()[:160]}")
        # UA header in the park fetch: look at _park_fetch_cell body.
        fetch_hits = find_lines(server_lines, "def _park_fetch_cell")
        if fetch_hits:
            i = fetch_hits[0][0]
            body = "\n".join(server_lines[i:i + 25])
            has_ua = "User-Agent" in body or "headers" in body
            ua_msg = ("YES" if has_ua else
                      "NO - fetch sends the default httpx UA "
                      "(Overpass .fr 403s generic UAs; the OSM UA fix "
                      "must cover parks too)")
            print(f"  park fetch UA header: {ua_msg}")
            if not has_ua:
                missing.append("backend:park-ua")
            for j in range(i, min(len(server_lines), i + 25)):
                if "AsyncClient" in server_lines[j]:
                    print(f"    line {j + 1}: {server_lines[j].strip()[:160]}")
        else:
            print("  park fetch fn: NOT FOUND -- cannot check UA")

    # ------------------------------------------------ 2. api.ts park fns
    print()
    print("=== 2. api.ts park client functions ===")
    if api_lines is None:
        print("api.ts: NOT FOUND -- frontend api verdict unknown")
        missing.append("api")
    else:
        for fn in PARK_API_FNS:
            hits = find_lines(api_lines, "export const " + fn)
            print(f"  {fn}: {len(hits)}x"
                  + (f" (line {hits[0][0] + 1})" if hits else " -- MISSING"))
            if not hits:
                missing.append("api:" + fn)

    # ------------------------------------------------ 3. batch index
    print()
    print("=== 3. useMapQueries entity batch: where do parks sit? ===")
    if queries_lines is None:
        print("useMapQueries.ts: NOT FOUND")
        missing.append("queries")
    else:
        text = "\n".join(queries_lines)
        calls = parse_batch_calls(text)
        if calls is None:
            print("Promise.all([ batch: NOT FOUND in useMapQueries.ts")
            missing.append("queries:batch")
        else:
            print(f"batch calls: {len(calls)}")
            for n, c in enumerate(calls):
                print(f"  [{n}] {c}")
            park_idx = [n for n, c in enumerate(calls) if "Park" in c]
            print(f"parks call index: "
                  f"{park_idx if park_idx else 'NOT IN BATCH -- MISSING'}")
            if not park_idx:
                missing.append("queries:parks-call")
        res_hits = find_re(queries_lines, r"results\[\d+\]")
        print(f"results[N] mapping references: {len(res_hits)}")
        for i, l in res_hits:
            print(f"  line {i + 1}: {l.strip()[:160]}")
        parks_map = [i for i, l in res_hits if "park" in l.lower()]
        print(f"results[N] lines mentioning park: "
              f"{[i + 1 for i in parks_map] if parks_map else 'NONE'}")
        if not parks_map:
            missing.append("queries:parks-mapping")
        field_hits = find_lines(queries_lines, "parks")
        print(f"'parks' mentions in useMapQueries.ts: {len(field_hits)}")

    # ------------------------------------------------ 4. index.tsx park wiring
    print()
    print("=== 4. index.tsx park wiring ===")
    if index_lines is None:
        print("index.tsx: NOT FOUND")
        missing.append("index")
    else:
        checks = [
            ("'park' marker type", "type: 'park'"),
            ("nearbyParks memo", "nearbyParks"),
            ("mapMarkers park spread", "nearbyParks.map"),
            ("handleMarkerPress", "handleMarkerPress"),
            ("popup park branch", "selectedMarker.type === 'park'"),
            ("ENTER -> setActivePark", "setActivePark"),
            ("state activePark", "activePark"),
            ("state parkOccupants", "parkOccupants"),
            ("state parkFriendIds", "parkFriendIds"),
            ("presence enter call", "parkEnterPresence"),
            ("presence heartbeat call", "parkHeartbeatPresence"),
            ("presence get call", "getParkPresence"),
            ("presence leave call", "parkLeavePresence"),
            ("PARK_BG const", "PARK_BG"),
            ("ScrollView import", "ScrollView"),
        ]
        for label, needle in checks:
            hits = find_lines(index_lines, needle)
            print(f"  {label}: {len(hits)}x"
                  + (f" (lines {[i + 1 for i, _ in hits][:8]})"
                     if hits else " -- MISSING"))
            if not hits and label not in ("ScrollView import",):
                missing.append("index:" + label)
        # PARK_BG: data URI or require?
        bg_hits = find_lines(index_lines, "PARK_BG = ")
        if bg_hits:
            v = bg_hits[0][1]
            kind = ("data URI (embedded, "
                    f"{len(v)} chars)" if "data:image" in v
                    else "require / other")
            print(f"  PARK_BG shape: {kind}; starts: "
                  f"{v.strip()[:90]}")
        # Popup ENTER block verbatim.
        pop = find_lines(index_lines, "selectedMarker.type === 'park'")
        if pop:
            i = pop[0][0]
            end = next((j for j in range(i, min(len(index_lines), i + 40))
                        if ")}" in index_lines[j]), i + 25)
            print_block("popup ENTER block", index_lines, i, end + 1)
        # PARK interior Modal verbatim.
        modal_start = None
        for needle in ("{/* PARK interior", "visible={!!activePark}"):
            hits = find_lines(index_lines, needle)
            if hits:
                modal_start = hits[0][0]
                break
        if modal_start is not None:
            end = next((j for j in range(modal_start, len(index_lines))
                        if "</Modal>" in index_lines[j]),
                       min(len(index_lines), modal_start + 60))
            print_block("PARK interior Modal", index_lines,
                        modal_start, end + 1)
            span = index_lines[modal_start:end + 1]
            print("  modal contents check:")
            for label, needle in [
                    ("park picture (ImageBackground)", "ImageBackground"),
                    ("park name text", "activePark?.name"),
                    ("cash text", "Your cash"),
                    ("Inside now list", "Inside now"),
                    ("LEAVE button", "LEAVE"),
                    ("ScrollView already inside modal", "ScrollView"),
                    ("Basketball already inside modal", "Basketball"),
                    ("activities list already inside modal", "Activities")]:
                n = sum(1 for l in span if needle in l)
                print(f"    {label}: {n}x")
                if needle in ("ScrollView", "Basketball", "Activities") and n:
                    missing.append("index:modal-already-has-" + needle)
        else:
            print("PARK interior Modal: NOT FOUND -- "
                  "no {/* PARK interior */} comment and no "
                  "visible={!!activePark}")
            missing.append("index:park-modal")

    # ------------------------------------------------ 5. GameMap.tsx
    print()
    print("=== 5. GameMap.tsx park wiring ===")
    if gamemap_lines is None:
        print("GameMap.tsx: NOT FOUND")
        missing.append("gamemap")
    else:
        for label, needle in [
                ("'park' in marker type union", "'park'"),
                ("markerColors park", "park:"),
                ("markerIcons park (literal player char)", "⛹️"),
                ("park marker branch", "type === 'park'"),
                ("park sizing (48x62 / isLocationMarker)", "isLocationMarker")]:
            hits = find_lines(gamemap_lines, needle)
            print(f"  {label}: {len(hits)}x"
                  + (f" (lines {[i + 1 for i, _ in hits][:6]})"
                     if hits else " -- MISSING"))
            if not hits:
                missing.append("gamemap:" + label)
        col = find_lines(gamemap_lines, "#E91E63")
        print(f"  park pink #E91E63: {len(col)}x"
              + (f" (lines {[i + 1 for i, _ in col][:4]})" if col else ""))

    # ------------------------------------------------ 6. WebView game pattern
    print()
    print("=== 6. WebView/HTML game pattern live (port follows this) ===")
    if index_lines is None:
        print("index.tsx: NOT FOUND -- cannot check WebView pattern")
    else:
        wv = find_lines(index_lines, "PoolWebView")
        print(f"  PoolWebView lazy require: {len(wv)}x"
              + (f" (lines {[i + 1 for i, _ in wv][:6]})" if wv else
                 " -- MISSING"))
        if not wv:
            missing.append("index:webview-require")
        src_html = find_lines(index_lines, "source={{ html:")
        print(f"  WebView source={{{{ html: ... }}}} usages: {len(src_html)}x"
              + (f" (lines {[i + 1 for i, _ in src_html][:10]})"
                 if src_html else ""))
        onmsg = find_lines(index_lines, "onMessage")
        print(f"  WebView onMessage handlers: {len(onmsg)}x")
        # Html.ts files present + imported.
        comp_dir = root / "frontend" / "components"
        present = []
        if comp_dir.is_dir():
            present = [p.name for p in sorted(comp_dir.glob("*Html.ts"))]
        print(f"  components/*Html.ts files present: "
              f"{present if present else 'NONE'}")
        for name in GAME_HTML_FILES:
            if name in present:
                hits = find_lines(index_lines, name.replace(".ts", ""))
                print(f"    {name}: present, imported in index.tsx "
                      f"{len(hits)}x")
        if not present:
            missing.append("components:no-html-files")
        # Exemplar game modal verbatim (darts first, else pool).
        ex = None
        for mname in ("DartGameModal", "PoolGameModal", "CardGameModal",
                      "DominoGameModal", "ScrabbleGameModal"):
            hits = find_lines(index_lines, "const " + mname)
            if hits:
                ex = (mname, hits[0][0])
                break
        if ex:
            mname, i = ex
            end = next((j for j in range(i, min(len(index_lines), i + 60))
                        if "</Modal>" in index_lines[j]),
                       min(len(index_lines), i + 40))
            print_block(f"exemplar game modal {mname}", index_lines,
                        i, end + 1)
            span = index_lines[i:end + 1]
            for label, needle in [
                    ("WebView source html var", "source={{ html:"),
                    ("javaScriptEnabled", "javaScriptEnabled"),
                    ("onMessage close", "onMessage"),
                    ("CLOSE button", "CLOSE")]:
                print(f"    {label}: "
                      f"{sum(1 for l in span if needle in l)}x")
        else:
            print("  exemplar game modal: NONE FOUND "
                  "(no DartGameModal/PoolGameModal/CardGameModal/"
                  "DominoGameModal/ScrabbleGameModal)")
            missing.append("index:game-modal-exemplar")
        # Exemplar menu modal (PvC/PvP) — just the def line + buttons.
        menu = None
        for mname in ("DartboardMenuModal", "PoolTableMenuModal",
                      "CardTableMenuModal", "DominoTableMenuModal"):
            hits = find_lines(index_lines, "const " + mname)
            if hits:
                menu = (mname, hits[0][0])
                break
        if menu:
            mname, i = menu
            print(f"  exemplar menu modal: {mname} at line {i + 1}")
            for label, needle in [("PLAY VS COMPUTER", "PLAY VS COMPUTER"),
                                  ("PLAYER VS PLAYER", "PLAYER VS PLAYER")]:
                hits = find_lines(index_lines, needle)
                print(f"    {label}: {len(hits)}x")
        else:
            print("  exemplar menu modal: NONE FOUND")
            missing.append("index:menu-modal-exemplar")
    pkg = read_file(paths["package"]) if paths["package"] else None
    if pkg is not None:
        hits = find_lines(pkg, "react-native-webview")
        print(f"  react-native-webview in package.json: {len(hits)}x"
              + (f" ({hits[0][1].strip()[:80]})" if hits else " -- MISSING"))
        if not hits:
            missing.append("package:webview")

    # ------------------------------------------------ 7. hall scroll pattern
    print()
    print("=== 7. activity-center hall scroll pattern live (park scene copies this) ===")
    if index_lines is None:
        print("index.tsx: NOT FOUND")
    else:
        hall = find_lines(index_lines, "centerSceneH")
        print(f"  centerSceneH mentions: {len(hall)}x"
              + (f" (lines {[i + 1 for i, _ in hall][:8]})" if hall else
                 " -- hall pattern NOT in index.tsx"))
        horiz = find_lines(index_lines, "horizontal")
        print(f"  'horizontal' mentions: {len(horiz)}x"
              + (f" (lines {[i + 1 for i, _ in horiz][:8]})" if horiz else ""))
        sc = find_lines(index_lines, "<ScrollView")
        print(f"  <ScrollView openings: {len(sc)}x"
              + (f" (lines {[i + 1 for i, _ in sc][:8]})" if sc else ""))
        if hall:
            i = hall[0][0]
            show_context(index_lines, i, before=2, after=6,
                         label="hall scene measurement")
        # The hall ScrollView block: first <ScrollView after a
        # centerScene mention.
        if sc and hall:
            si = next((i for i, _ in sc if i > hall[0][0]), None)
            if si is not None:
                print_block("hall ScrollView block", index_lines,
                            si, min(len(index_lines), si + 30))

    # ------------------------------------------------ 8. port anchors
    print()
    print("=== 8. exact anchors the port patch will use ===")
    if index_lines is not None:
        # (a) ENTER onPress -> setActivePark
        ent = find_lines(index_lines, "setActivePark(p)")
        if ent:
            i = ent[0][0]
            print("ENTER-OPEN anchor (unique if 1x):")
            show_context(index_lines, i, before=4, after=1)
        else:
            print("ENTER-OPEN anchor: setActivePark(p) NOT FOUND")
        # (b) PARK_BG const line
        bg = find_lines(index_lines, "const PARK_BG = ")
        if bg:
            print(f"PARK_BG anchor: line {bg[0][0] + 1} "
                  f"(first 60 chars: {bg[0][1].strip()[:60]})")
        # (c) LEAVE line inside the park modal
        lv = find_lines(index_lines, "LEAVE")
        print(f"LEAVE mentions in index.tsx: {len(lv)} "
              f"(lines {[i + 1 for i, _ in lv][:8]})")
        # (d) import block end (for the BasketballHtml import)
        imp = find_re(index_lines, r"^import .* from ")
        if imp:
            print(f"import block: {len(imp)} imports; last at line "
                  f"{imp[-1][0] + 1}: {imp[-1][1].strip()[:120]}")
        # (e) WebView lazy-require block
        wv = find_lines(index_lines, "let PoolWebView")
        if wv:
            i = wv[0][0]
            print("WEBVIEW-REQUIRE anchor:")
            show_context(index_lines, i, before=0, after=2)

    # ------------------------------------------------ 9. verdict
    print()
    print("=== 9. VERDICT ===")
    backend_missing = [m for m in missing if m.startswith("backend")]
    frontend_missing = [m for m in missing
                        if not m.startswith("backend")]
    if not missing:
        verdict = "(a)"
        print("VERDICT: (a) parks FULLY LIVE (backend + frontend) -- "
              "the port is a straight frontend rework: park interior "
              "ScrollView scene + activities list + BasketballHtml "
              "WebView component. No backend patch needed.")
    elif not backend_missing:
        verdict = "(b)"
        print("VERDICT: (b) BACKEND live, FRONTEND partially live -- "
              "missing frontend pieces:")
        for m in sorted(set(frontend_missing)):
            print(f"  - {m}")
    elif not frontend_missing:
        verdict = "(b)"
        print("VERDICT: (b) FRONTEND live, BACKEND partially live -- "
              "missing backend pieces:")
        for m in sorted(set(backend_missing)):
            print(f"  - {m}")
    else:
        verdict = "(b)"
        print("VERDICT: (b) parks PARTIALLY live -- missing pieces:")
        for m in sorted(set(missing)):
            print(f"  - {m}")
    if "index-file" in missing or "server-file" in missing:
        verdict = "(c)"
        print("VERDICT: (c) core files missing -- cannot judge; check "
              "the root path (run from /app).")
    print(f"missing count: {len(set(missing))}  verdict={verdict}")
    if missing:
        print(f"PARK_LIVE_DIAG_PARTIAL missing={','.join(sorted(set(missing)))} "
              f"verdict={verdict}")
    else:
        print(f"{MARKER} verdict={verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
