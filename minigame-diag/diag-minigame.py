#!/usr/bin/env python3
"""Street Legends READ-ONLY diagnostic: mini-game shootout bug.

User report: playing the shootout game on the other phone, the money and
rep won did NOT reach the actual total, and it had NO cooldown. The user
asked to check mini-games in BOTH entry points: map games and settings /
options-panel (practice / standalone) games.

WHAT THIS SCRIPT DOES (read-only):
  Prints, with file paths + line numbers + short quoted snippets, whatever
  it finds in the CURRENT /app tree (the live tree may differ from any
  local snapshot, so every section is anchor-tolerant: a missing file or
  anchor prints WARNING and the script keeps going):
    (0) Which candidate paths actually exist vs are missing.
    (1) SHOOTOUT ENDPOINTS: every shootout start/complete endpoint, plus
        the same list for castle, car-chase, runaway, package-grab.
    (2) GLOBAL COOLDOWN: for shootout specifically, is
        minigame_global_cooldown_until CHECKED on start (map + standalone)
        and SET on completion (map + standalone)? Plus the cooldowns
        reporting endpoint and per-marker cooldown fields.
    (3) CASH AWARD: in each shootout completion handler, is there a cash
        award, what amount/formula, and is it inside any condition that
        could skip it?
    (4) REP AWARD: does ANY shootout completion handler award rep /
        reputation? If none, it says so explicitly.
    (5) FRONTEND MAP FLOW: the shootout screen/flow launched from a map
        marker — which start/complete endpoints it calls, what it does
        with the response.
    (6) FRONTEND SETTINGS/PRACTICE FLOW: the shootout screen/flow launched
        from settings/options/practice (standalone) — which endpoints it
        calls, and how it differs from the map flow.
    (7) TOTAL REFRESH: after a mini-game win, does the frontend refetch
        the player (cash/rep) from the server, or only update local state
        / show locally-computed rewards?
    (8) DUPLICATES: are there two divergent shootout implementations
        (an old screen still calling a pre-fix endpoint, a screen that
        never calls complete, a local-only path)?

WHAT IT NEVER DOES:
  It only reads files. It never creates, modifies, or deletes any file,
  never calls any API, never runs any patch. It never stops early: every
  missing section prints WARNING and the script continues to the end
  marker.

RUN FROM /app (the script reads relative to the current working directory,
so the current directory must be /app when you run it):
    python3 diag-minigame.py
  An optional first argument overrides the root (used only by sim-tests):
    python3 diag-minigame.py /path/to/mock/app

LAST LINE IS ALWAYS: MINIGAME_DIAG_OK
"""

import re
import sys
from pathlib import Path

MARKER = "MINIGAME_DIAG_OK"

SKIP_DIRS = {".metro-cache", "node_modules", "__pycache__", ".git", "dist", "build", ".expo"}
SOURCE_SUFFIXES = {".ts", ".tsx", ".js", ".jsx"}

CANDIDATES = [
    "frontend/app/(tabs)/index.tsx",
    "frontend/app/(tabs)/shop.tsx",
    "frontend/app/(tabs)/settings.tsx",
    "frontend/app/shootout-simulator.tsx",
    "frontend/components/OptionsModal.tsx",
    "frontend/components/GameMap.tsx",
    "frontend/services/api.ts",
    "frontend/hooks/useMapQueries.ts",
    "backend/server.py",
]

# Game keywords: (label, route substrings, start-func substrings, complete-func substrings)
GAMES = [
    ("shootout", ["shootout"], ["shootout"], ["shootout"]),
    ("castle", ["castle"], ["castle"], ["castle"]),
    ("car-chase", ["car-chase", "carchase", "car_chase"], ["car_chase", "carchase"], ["car_chase", "carchase"]),
    ("runaway", ["runaway"], ["runaway"], ["runaway"]),
    ("package-grab", ["package-grab", "packagegrab", "package_grab"], ["package_grab", "packagegrab"], ["package_grab", "packagegrab"]),
]


def read_lines(path):
    """Read a file as lines. Returns None if the file cannot be read."""
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except (OSError, UnicodeError):
        return None
    return text.split("\n")


def print_block(title, path, lines, start_idx, end_idx):
    """Print a numbered code block (1-based line numbers)."""
    print("--- %s: %s lines %d-%d ---" % (title, path, start_idx + 1, end_idx))
    for i in range(start_idx, end_idx):
        print("%s:%d: %s" % (path, i + 1, lines[i]))


def show_matches(title, path, lines, pattern, context=0, max_hits=40):
    """Print every line matching pattern (regex, case-insensitive) with numbers."""
    rx = re.compile(pattern, re.IGNORECASE)
    hits = [i for i, ln in enumerate(lines) if rx.search(ln)]
    print("--- %s: %s (%d hits) ---" % (title, path, len(hits)))
    if not hits:
        print("WARNING: no matches for %s in %s" % (pattern, path))
        return hits
    for i in hits[:max_hits]:
        lo = max(0, i - context)
        hi = min(len(lines), i + context + 1)
        for j in range(lo, hi):
            mark = ">>>" if j == i else "   "
            print("%s %s:%d: %s" % (mark, path, j + 1, lines[j]))
    if len(hits) > max_hits:
        print("... (%d more hits omitted)" % (len(hits) - max_hits))
    return hits


def py_functions(lines):
    """Split Python lines into (def_name, start_idx, end_idx) for async defs."""
    starts = []
    for i, ln in enumerate(lines):
        m = re.match(r"async def (\w+)\(", ln)
        if m:
            starts.append((m.group(1), i))
            continue
        m2 = re.match(r"def (\w+)\(", ln)
        if m2:
            starts.append((m2.group(1), i))
    funcs = []
    for k, (name, s) in enumerate(starts):
        e = starts[k + 1][1] if k + 1 < len(starts) else len(lines)
        funcs.append((name, s, e))
    return funcs


def func_of_line(funcs, idx):
    """Name of the function containing line index idx, or None."""
    for name, s, e in funcs:
        if s <= idx < e:
            return name
    return None


def route_table(lines, path):
    """All @api_router route decorators with the following def name."""
    out = []
    for i, ln in enumerate(lines):
        m = re.search(r"@api_router\.(get|post|put|delete)\(\"([^\"]+)\"", ln)
        if m:
            defname = None
            for j in range(i + 1, min(len(lines), i + 6)):
                dm = re.match(r"async def (\w+)\(", lines[j])
                if dm:
                    defname = dm.group(1)
                    break
            out.append((m.group(1), m.group(2), defname, i))
    return out


def indent_of(line):
    return len(line) - len(line.lstrip())


def enclosing_if(lines, body_start, body_end, target_idx, cond_pat):
    """If target line sits inside an if-block matching cond_pat, return that
    if line (number + text); else None. Indent-based, approximate."""
    for i in range(body_start, target_idx):
        ln = lines[i]
        if re.search(cond_pat, ln):
            ind = indent_of(ln)
            # target must be more indented and no dedent-to-<=ind line between
            blocked = False
            for j in range(i + 1, target_idx):
                lj = lines[j]
                if lj.strip() and indent_of(lj) <= ind and not lj.strip().startswith((")", "]", "}")):
                    blocked = True
                    break
            if not blocked:
                return (i + 1, ln.strip())
    return None


def main():
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    print("MINIGAME DIAG: root = %s (read-only, no files modified)" % root)

    files = {}
    print("=== SECTION 0: candidate paths (existence only) ===")
    for cand in CANDIDATES:
        p = root / cand
        if p.is_file():
            lines = read_lines(p)
            files[cand] = lines
            print("EXISTS: %s (%d lines)" % (cand, len(lines) if lines else 0))
        else:
            files[cand] = None
            print("WARNING: candidate file not found: %s" % cand)

    server = files.get("backend/server.py")
    server_path = "backend/server.py"

    # ---------------- SECTION 1: endpoints ----------------
    print("=== SECTION 1: SHOOTOUT ENDPOINTS (plus comparison games) ===")
    if server is None:
        print("WARNING: backend/server.py missing — cannot list endpoints")
        routes = []
        funcs = []
    else:
        routes = route_table(server, server_path)
        funcs = py_functions(server)
        for label, route_keys, _, _ in GAMES:
            print("--- routes for %s ---" % label)
            found = False
            for method, route, defname, i in routes:
                if any(k in route for k in route_keys):
                    print("%s:%d: @api_router.%s(\"%s\") -> %s" % (server_path, i + 1, method, route, defname))
                    found = True
            if not found:
                print("WARNING: no routes found for %s" % label)
        print("--- shootout defs ---")
        for name, s, e in funcs:
            if "shootout" in name:
                print("%s:%d: async def %s (lines %d-%d)" % (server_path, s + 1, name, s + 1, e))

    # ---------------- SECTION 2: global cooldown ----------------
    print("=== SECTION 2: GLOBAL COOLDOWN ===")
    if server is None:
        print("WARNING: backend/server.py missing — cannot check global cooldown")
    else:
        show_matches("global-cooldown helper/constant", server_path, server,
                     r"MINIGAME_GLOBAL_COOLDOWN_SECONDS|_check_minigame_global_cooldown|_minigame_global_cooldown_until", max_hits=60)
        print("--- global CHECK calls attributed to enclosing function ---")
        for i, ln in enumerate(server):
            if "_check_minigame_global_cooldown(player)" in ln:
                print("%s:%d: in %s: %s" % (server_path, i + 1, func_of_line(funcs, i), ln.strip()))
        print("--- global SET writes attributed to enclosing function ---")
        for i, ln in enumerate(server):
            if "minigame_global_cooldown_until" in ln and "_check_minigame_global_cooldown" not in ln and "MINIGAME_GLOBAL_COOLDOWN_SECONDS" not in ln:
                print("%s:%d: in %s: %s" % (server_path, i + 1, func_of_line(funcs, i), ln.strip()))
        print("--- cooldowns reporting endpoint ---")
        show_matches("cooldowns endpoint + global key", server_path, server,
                     r"/minigames/cooldowns|get_minigame_cooldowns|cooldowns\[\"global\"\]", max_hits=20)
        print("--- per-marker cooldown fields ---")
        show_matches("per-marker cooldown fields", server_path, server,
                     r"shootout_cooldowns|castle_cooldowns|carchase_cooldowns|runaway_cooldowns|packagegrab_cooldowns", max_hits=40)
        print("--- per-game global check/set summary ---")
        for label, _, start_keys, complete_keys in GAMES:
            for kind, keys in (("start", start_keys), ("complete", complete_keys)):
                for name, s, e in funcs:
                    if any(k in name for k in keys) and kind in name or (any(k in name for k in keys) and ("start" in name if kind == "start" else "complete" in name)):
                        body = server[s:e]
                        has_check = any("_check_minigame_global_cooldown(player)" in ln for ln in body)
                        has_set = any("minigame_global_cooldown_until" in ln and "_check_minigame_global_cooldown" not in ln for ln in body)
                        print("%s %s: %s check=%s set=%s" % (label, kind, name, has_check, has_set))

    # ---------------- SECTION 3: cash award ----------------
    print("=== SECTION 3: CASH AWARD (shootout completions) ===")
    if server is None:
        print("WARNING: backend/server.py missing — cannot check cash awards")
    else:
        for name, s, e in funcs:
            if "shootout" in name and "complete" in name:
                print("--- complete function: %s (lines %d-%d) ---" % (name, s + 1, e))
                for i in range(s, e):
                    ln = server[i]
                    if re.search(r"cash|rewards?|hits", ln, re.IGNORECASE):
                        cond = enclosing_if(server, s, e, i, r"if\s+(not\s+)?standalone")
                        print("%s:%d: %s%s" % (server_path, i + 1, ln.strip(),
                              ("   [inside: %s]" % cond[1]) if cond else ""))
                print("--- $inc / update_one lines in %s ---" % name)
                for i in range(s, e):
                    if "$inc" in server[i] or "update_one" in server[i]:
                        print("%s:%d: %s" % (server_path, i + 1, server[i].strip()))
                print("--- hits==0 / no-hits branch in %s ---" % name)
                for i in range(s, e):
                    if re.search(r"if hits|hits\s*==\s*0|hits\s*>\s*0|else:", server[i]):
                        print("%s:%d: %s" % (server_path, i + 1, server[i].strip()))

    # ---------------- SECTION 4: rep award ----------------
    print("=== SECTION 4: REP AWARD (shootout completions) ===")
    if server is None:
        print("WARNING: backend/server.py missing — cannot check rep awards")
    else:
        rep_found = False
        for name, s, e in funcs:
            if "shootout" in name and "complete" in name:
                for i in range(s, e):
                    if re.search(r"reputation|rep_reward|\b rep\b|\"rep\"|'rep'", server[i]):
                        print("%s:%d: in %s: %s" % (server_path, i + 1, name, server[i].strip()))
                        rep_found = True
        if not rep_found:
            print("REP AWARD: NONE — no reputation/rep line found in any shootout complete function")
        print("--- rep lines anywhere in shootout-related defs (start + complete) ---")
        for name, s, e in funcs:
            if "shootout" in name:
                for i in range(s, e):
                    if re.search(r"reputation|rep_reward", server[i]):
                        print("%s:%d: in %s: %s" % (server_path, i + 1, name, server[i].strip()))

    # ---------------- FRONTEND helpers ----------------
    def show_frontend(title, cand, pattern, context=1, max_hits=40):
        lines = files.get(cand)
        if lines is None:
            print("WARNING: %s missing — cannot check %s" % (cand, title))
            return []
        return show_matches(title, cand, lines, pattern, context=context, max_hits=max_hits)

    # ---------------- SECTION 5: map flow ----------------
    print("=== SECTION 5: FRONTEND MAP FLOW (shootout from a map marker) ===")
    show_frontend("map shootout start handler", "frontend/app/(tabs)/index.tsx",
                  r"handleStartShootout|startShootout|selectedShootout", context=2, max_hits=40)
    show_frontend("map shootout navigation params", "frontend/app/(tabs)/index.tsx",
                  r"shootout-simulator|shootoutId|shootoutName", context=2, max_hits=30)
    show_frontend("shootout screen map-start branch", "frontend/app/shootout-simulator.tsx",
                  r"apiStartShootout|startShootout|isStandalone|setGameId", context=1, max_hits=50)
    show_frontend("shootout screen complete call", "frontend/app/shootout-simulator.tsx",
                  r"apiCompleteShootout|completeShootout", context=3, max_hits=30)

    # ---------------- SECTION 6: settings/practice flow ----------------
    print("=== SECTION 6: FRONTEND SETTINGS/PRACTICE FLOW (standalone) ===")
    show_frontend("options modal shootout navigation", "frontend/components/OptionsModal.tsx",
                  r"shootout|Shootout|standalone", context=1, max_hits=50)
    show_frontend("shootout screen standalone branch", "frontend/app/shootout-simulator.tsx",
                  r"standalone/start|Standalone mode|continuing without backend|gameId.*standalone|'standalone'", context=2, max_hits=40)
    show_frontend("api.ts shootout helpers", "frontend/services/api.ts",
                  r"hootout", context=1, max_hits=30)
    show_frontend("settings.tsx shootout references (if a settings screen exists)", "frontend/app/(tabs)/settings.tsx",
                  r"shootout|Shootout", context=1, max_hits=20)

    # ---------------- SECTION 7: total refresh ----------------
    print("=== SECTION 7: TOTAL REFRESH (after a shootout win) ===")
    show_frontend("post-complete player refresh in shootout screen", "frontend/app/shootout-simulator.tsx",
                  r"getPlayer|setPlayer|invalidateMapQueries|loadPlayerData|refreshPlayer|setCash|setRewards|calculateRewards", context=2, max_hits=60)
    show_frontend("complete-failure / local-only fallback in shootout screen", "frontend/app/shootout-simulator.tsx",
                  r"Rewards may not have saved|Failed to complete|Still show local|local rewards", context=1, max_hits=20)

    # ---------------- SECTION 8: duplicates ----------------
    print("=== SECTION 8: DUPLICATES (every shootout screen/component) ===")
    shootout_files = []
    for base in ("frontend/app", "frontend/components", "frontend/services", "frontend/hooks", "frontend/stores"):
        d = root / base
        if not d.is_dir():
            continue
        for p in sorted(d.rglob("*")):
            if not p.is_file():
                continue
            if any(skip in p.parts for skip in SKIP_DIRS):
                continue
            if p.suffix not in SOURCE_SUFFIXES:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if re.search(r"shootout", text, re.IGNORECASE):
                rel = str(p.relative_to(root))
                kinds = []
                if re.search(r"export default function .*Shootout|ShootoutSimulatorScreen|function Shootout", text):
                    kinds.append("screen/component definition")
                if "shootout-simulator" in text:
                    kinds.append("navigates to shootout-simulator")
                if re.search(r"startShootout|completeShootout|shootouts/", text):
                    kinds.append("calls shootout API")
                if "standalone" in text.lower() and "shootout" in text.lower():
                    kinds.append("mentions standalone + shootout")
                shootout_files.append(rel)
                print("%s: %s" % (rel, ", ".join(kinds) if kinds else "mentions shootout"))
                for i, ln in enumerate(text.split("\n")):
                    if re.search(r"setGameId\('standalone'\)|gameId.*=.*'standalone'|game_id.*standalone", ln):
                        print("   %s:%d: LOCAL-ONLY MARKER: %s" % (rel, i + 1, ln.strip()))
    if not shootout_files:
        print("WARNING: no frontend file mentions shootout at all")

    # ---------------- VERDICTS ----------------
    print("=== VERDICTS (from sections above only) ===")
    if server is None:
        print("VERDICT Q1 ENDPOINTS: UNKNOWN — backend/server.py missing")
        print("VERDICT Q2 GLOBAL COOLDOWN: UNKNOWN — backend/server.py missing")
        print("VERDICT Q3 CASH: UNKNOWN — backend/server.py missing")
        print("VERDICT Q4 REP: UNKNOWN — backend/server.py missing")
    else:
        shoot_routes = [(m, r, d) for (m, r, d, i) in routes if "shootout" in r]
        print("VERDICT Q1 ENDPOINTS: shootout routes found: %s" % (
            ", ".join("%s %s -> %s" % (m, r, d) for m, r, d in shoot_routes) if shoot_routes else "NONE"))
        print("VERDICT Q1 COMPARISON: castle/car-chase/runaway/package-grab routes are listed in Section 1; compare start+complete coverage per game there.")
        has_helper = any("MINIGAME_GLOBAL_COOLDOWN_SECONDS" in ln for ln in server)
        print("VERDICT Q2 GLOBAL COOLDOWN: helper present=%s; per-function check/set is in the Section 2 summary — a shootout start or complete function WITHOUT check=True / set=True is the cooldown gap for that entry point." % has_helper)
        print("VERDICT Q2 REPORTING: GET /minigames/cooldowns global key + per-marker shootout_cooldowns lines are in Section 2; if the frontend never reads the global key, the map UI will not show a global lock even when the server enforces one.")
        print("VERDICT Q3 CASH: see Section 3 — a cash $inc inside an 'if not standalone' block, or a complete call that never runs (gameId null / 404 / skipped), means winnings never reach the total. A hits==0 return carries no rewards by design.")
        print("VERDICT Q4 REP: see Section 4 — if it says NONE, missing rep is a missing award; if a reputation $inc exists in complete_shootout, missing rep points to complete-not-called, a wrong player account, or a stale UI, not to a missing award.")
    print("VERDICT Q5 MAP FLOW: see Section 5 — note whether the map handler passes a gameId to the screen or the screen starts its own session, and which complete endpoint the screen calls.")
    print("VERDICT Q6 SETTINGS FLOW: see Section 6 — note whether the standalone branch creates a real backend session or continues locally (gameId null means complete is skipped, so no cash, no rep, no cooldown).")
    print("VERDICT Q7 TOTAL REFRESH: see Section 7 — getPlayer + setPlayer after complete means the total refreshes from the server; local-only rewards display with a failed/skipped complete means the win screen can show money the total never received.")
    print("VERDICT Q8 DUPLICATES: see Section 8 — any second shootout screen file, or a LOCAL-ONLY MARKER line, is a divergent implementation to reconcile before fixing.")
    print("STILL NEEDED FROM THE USER (the script cannot see these): map vs settings entry for the reported shootout play; account/name on the other phone (winnings land on THAT account's total); win-screen $/rep amounts shown; whether the total was rechecked after a reload; other-phone build (Expo Go vs installed).")
    print(MARKER)


if __name__ == "__main__":
    main()
