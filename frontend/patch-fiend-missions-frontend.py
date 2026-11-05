#!/usr/bin/env python3
"""Fiend missions for Street Legends (frontend).

Pairs with backend/patch-fiend-missions.py (run that first, then Publish,
then this patch). Fiends buy the five enemy-drop items at +25% over
regular price: Grass $125, Pills $250, Rock Candy $375, Flake $500,
Brown Sugar $625 per oz. Each Fiend mission asks for a bundle (1-3 item
types, 1-5 oz each) from a deterministic 1,000-variant catalog; payout =
sum(qty x fiend price). At completion there is a flat 10% chance the
Each Fiend has one of 1000 distinct real first names (500 male / 500
female, deterministic per variant id); the popup title, map label and
result alerts show the name.
Fiend is an undercover cop: the requested items are confiscated AND the
player is fined $1,000 (capped at current cash), no payout, mission
consumed either way. Cop status is hidden until the attempt.

What this patch does:
  1. services/api.ts: getFiendsNearby + sellToFiend (count-guarded).
  2. hooks/useMapQueries.ts: getFiendsNearby appended LAST in the entity
     batch (index counted at patch time, so the existing results indices
     never move), fiends field on MapEntitiesData.
  3. app/(tabs)/index.tsx: 'fiend' marker type (literal zombie icon),
     nearbyFiends memo, mapMarkers spread + deps, handleMarkerPress
     branch + deps, handleSellToFiend (sale vs cop messages), Fiend
     popup (requested items + payout + SELL TO FIEND, disabled with
     NOT ENOUGH ITEMS when the player lacks any requested quantity).
  4. components/GameMap.tsx: 'fiend' in the marker type union,
     markerColors fiend '#8BC34A', markerIcons fiend '🧟' (literal
     character, NEVER a unicode escape), a Fiend marker branch mirroring
     the nightclub branch, fiend included in the 48x62 location sizing.
     NEVER uses a [^}]* regex on markerIcons (that broke the map once:
     the \\u{...} escapes contain a } that ends the match early).
  5. app/(tabs)/character.tsx: REMOVE the SELL button from all five
     item rows (Grass/Pills/Rock Candy/Flake/Brown Sugar). USE buttons
     and the once-only ACTIVE states stay untouched. Selling is Fiend-only
     after this (no player-to-player trading exists in the game).

Run:  python3 frontend/patch-fiend-missions-frontend.py
   or:  python3 frontend/patch-fiend-missions-frontend.py /path/to/app
Idempotent: rerun prints ALREADY_APPLIED per part, files unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
API = ROOT / "frontend" / "services" / "api.ts"
QUERIES = ROOT / "frontend" / "hooks" / "useMapQueries.ts"
INDEX = ROOT / "frontend" / "app" / "(tabs)" / "index.tsx"
GAMEMAP = ROOT / "frontend" / "components" / "GameMap.tsx"
CHARACTER = ROOT / "frontend" / "app" / "(tabs)" / "character.tsx"

FIEND_API = '''
export const getFiendsNearby = async (latitude: number, longitude: number, playerId?: string): Promise<any[]> => {
  let url = `/fiends/nearby?latitude=${latitude}&longitude=${longitude}`;
  if (playerId) url += `&player_id=${playerId}`;
  const response = await api.get(url);
  return response.data;
};

export const sellToFiend = async (fiendId: string, playerId: string): Promise<any> => {
  const response = await api.post(`/fiends/${fiendId}/complete?player_id=${playerId}`);
  return response.data;
};
'''

FIEND_SPREAD = """    ...nearbyFiends.map((f: any) => ({
      id: f.id,
      coordinate: f.position,
      type: 'fiend' as const,
      name: f.name || 'Fiend',
      icon: '🧟',
    })),
"""

FIEND_BRANCH = """    } else if (m.type === 'fiend') {
              var fiendName = m.name || 'Fiend';
              markerHTML = '<div style="width:48px;height:62px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                '<div style="width:42px;height:42px;border-radius:10px;background:linear-gradient(135deg,#8BC34A,#558B2F);display:flex;align-items:center;justify-content:center;border:3px solid #fff;box-shadow:0 3px 10px rgba(139,195,74,0.6);font-size:22px;cursor:pointer;">🧟</div>' +
                '<div style="position:absolute;bottom:0;left:50%;transform:translateX(-50%);background:rgba(85,139,47,0.9);color:#fff;padding:1px 6px;border-radius:4px;font-size:7px;font-weight:bold;white-space:nowrap;z-index:10;border:1px solid #fff;">' + fiendName + '</div>' +
                '</div>';
"""

FIEND_POPUP = """          {selectedMarker.type === 'fiend' && (
            <View>
              <View style={styles.popupHeader}>
                <Text style={{ fontSize: 28 }}>🧟</Text>
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{selectedMarker.data.name || 'Fiend'}</Text>
                  <Text style={styles.popupSubtitle}>Pays 25% over regular price</Text>
                </View>
              </View>
              {(selectedMarker.data.items || []).map((it: any) => (
                <View key={it.item_id} style={styles.rewardItem}>
                  <Text style={styles.rewardText}>{it.qty} oz {it.name} — ${it.line_total}</Text>
                </View>
              ))}
              <View style={styles.rewardsRow}>
                <View style={styles.rewardItem}>
                  <Ionicons name="cash" size={14} color="#34A853" />
                  <Text style={styles.rewardText}>Payout ${selectedMarker.data.payout}</Text>
                </View>
              </View>
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: fiendCanSell ? '#4caf50' : '#555', opacity: fiendCanSell ? 1 : 0.6 }]}
                disabled={!fiendCanSell}
                onPress={() => handleSellToFiend(selectedMarker.data)}
              >
                <Text style={styles.actionButtonText}>{fiendCanSell ? 'SELL TO FIEND' : 'NOT ENOUGH ITEMS'}</Text>
              </TouchableOpacity>
            </View>
          )}

"""

FIEND_HELPER = """  // FIEND_MISSIONS: does the player hold every item a Fiend asks for?
  const fiendHasItems = (fiend: any) => {
    const inv: any[] = (player as any)?.inventory || [];
    return (fiend?.items || []).every((req: any) => {
      let have = 0;
      for (const it of inv) {
        if (typeof it === 'string') { if (it === req.item_id) have += 1; }
        else if (it && it.item_id === req.item_id) { have += (it.qty || 1); }
      }
      return have >= req.qty;
    });
  };
  const fiendCanSell = selectedMarker?.type === 'fiend' ? fiendHasItems(selectedMarker.data) : false;
"""

FIEND_HANDLER = """  // FIEND_MISSIONS: sell the requested bundle to a Fiend (or get caught by a cop).
  const handleSellToFiend = async (fiend: any) => {
    if (!playerId) return;
    try {
      const result: any = await sellToFiend(fiend.id, playerId);
      const who = (result && result.fiend_name) || fiend.name || 'Fiend';
      if (result && result.outcome === 'cop') {
        Alert.alert('Undercover cop!', who + ' was an undercover cop! Your goods were confiscated and you were fined $' + (result.fined ?? 0) + '.');
      } else {
        Alert.alert('Sold!', 'Sold to ' + who + ' for $' + (result.payout ?? 0) + '!');
      }
      setSelectedMarker(null);
      try { refetchEntities(); } catch (_) {}
      try { refetchPlayer(); } catch (_) {}
    } catch (error: any) {
      Alert.alert('Error', error?.response?.data?.detail || 'Sale failed');
    }
  };

"""

# (item id, SELL label, sell handler) for the five item rows.
SELL_ROWS = [
    ("grass", "SELL 1 OZ ($100)", "onSellGrass"),
    ("pills", "SELL 1 OZ ($200)", "onSellPills"),
    ("rock_candy", "SELL 1 OZ ($300)", "onSellRockCandy"),
    ("flake", "SELL 1 OZ ($400)", "onSellFlake"),
    ("brown_sugar", "SELL 1 OZ ($500)", "onSellBrownSugar"),
]


def delta(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"), s.count("["), s.count("]"))


def _remove_sell_button(src, label, handler):
    """Delete the SELL TouchableOpacity block for one item row.

    Finds the unique label line, walks up to the enclosing
    <TouchableOpacity and down to its </TouchableOpacity>, verifies the
    span calls the item's sell handler, and deletes the span.
    Returns (new_src, status) where status is 'removed', 'absent', or an
    error string.
    """
    lines = src.split("\n")
    hits = [i for i, ln in enumerate(lines) if label in ln]
    if len(hits) == 0:
        return src, "absent"
    if len(hits) > 1:
        return src, f"found {len(hits)} times"
    li = hits[0]
    start = None
    for j in range(li, max(-1, li - 12), -1):
        if "<TouchableOpacity" in lines[j]:
            start = j
            break
    if start is None:
        return src, "no TouchableOpacity above label"
    end = None
    for j in range(li, min(len(lines), li + 8)):
        if "</TouchableOpacity>" in lines[j]:
            end = j
            break
    if end is None:
        return src, "no closing TouchableOpacity below label"
    span = "\n".join(lines[start:end + 1])
    if handler not in span:
        return src, "span does not call " + handler
    del lines[start:end + 1]
    return "\n".join(lines), "removed"


def main():
    landed = []
    warned = []

    # ================= Part 1: services/api.ts =================
    if not API.exists():
        print("WARNING: services/api.ts not found - Fiend api functions NOT added")
        warned.append("api")
    else:
        asrc = API.read_text(errors="ignore")
        aorig = asrc
        if "getFiendsNearby" in asrc and "sellToFiend" in asrc:
            print("FIEND_FRONTEND_API_ALREADY_APPLIED")
            landed.append("api")
        else:
            asrc = asrc.rstrip("\n") + "\n" + FIEND_API
            print("FIEND_FRONTEND_API_OK")
            landed.append("api")
        if asrc != aorig:
            API.write_text(asrc)

    # ================= Part 2: hooks/useMapQueries.ts =================
    if not QUERIES.exists():
        print("WARNING: hooks/useMapQueries.ts not found - Fiend entity wiring NOT added")
        warned.append("queries")
    else:
        qsrc = QUERIES.read_text(errors="ignore")
        qorig = qsrc
        qd0 = delta(qsrc)
        if "getFiendsNearby" in qsrc and "fiends: any[];" in qsrc and "fiends: results[" in qsrc:
            print("FIEND_FRONTEND_QUERIES_ALREADY_APPLIED")
            landed.append("queries")
        else:
            # 2a. Import.
            if "getFiendsNearby" in qsrc:
                print("FIEND_FRONTEND_QUERIES_IMPORT_ALREADY_APPLIED")
            elif "  getActivityCentersNearby,\n" in qsrc:
                qsrc = qsrc.replace("  getActivityCentersNearby,\n", "  getActivityCentersNearby,\n  getFiendsNearby,\n", 1)
                print("FIEND_FRONTEND_QUERIES_IMPORT_OK")
            elif "  spawnShootouts,\n" in qsrc:
                qsrc = qsrc.replace("  spawnShootouts,\n", "  spawnShootouts,\n  getFiendsNearby,\n", 1)
                print("FIEND_FRONTEND_QUERIES_IMPORT_OK")
            else:
                print("WARNING: api import anchor not found in useMapQueries.ts - getFiendsNearby import NOT added")
                warned.append("queries-import")
            # 2b. MapEntitiesData field.
            if "fiends: any[];" in qsrc:
                print("FIEND_FRONTEND_QUERIES_FIELD_ALREADY_APPLIED")
            elif "  activityCenters: any[];\n" in qsrc:
                qsrc = qsrc.replace("  activityCenters: any[];\n", "  activityCenters: any[];\n  fiends: any[];\n", 1)
                print("FIEND_FRONTEND_QUERIES_FIELD_OK")
            elif "  shootouts: any[];\n" in qsrc:
                qsrc = qsrc.replace("  shootouts: any[];\n", "  shootouts: any[];\n  fiends: any[];\n", 1)
                print("FIEND_FRONTEND_QUERIES_FIELD_OK")
            else:
                print("WARNING: MapEntitiesData anchor not found - fiends field NOT added")
                warned.append("queries-field")
            # 2c. Append the call LAST in Promise.allSettled + the return mapping.
            # Count existing calls and return mappings so no index moves.
            m = re.search(r"Promise\.allSettled\(\[\n(.*?)\n      \]\);", qsrc, re.S)
            if not m:
                print("WARNING: Promise.allSettled anchor not found - Fiend call NOT added")
                warned.append("queries-call")
            else:
                block = m.group(1)
                call_lines = [ln for ln in block.split("\n") if re.match(r"^\s{8}[A-Za-z_][\w]*\(", ln)]
                ret_lines = re.findall(r"results\[\d+\]", qsrc)
                n_calls = len(call_lines)
                n_rets = len(set(ret_lines))
                if "getFiendsNearby(latitude" in qsrc:
                    print("FIEND_FRONTEND_QUERIES_CALL_ALREADY_APPLIED")
                elif n_calls == 0 or n_calls != n_rets:
                    print(f"WARNING: entity call count ({n_calls}) != return mapping count ({n_rets}) - Fiend call NOT added")
                    warned.append("queries-call")
                else:
                    n = n_calls  # new call takes the next index; nothing moves
                    last_call = call_lines[-1]
                    idx = qsrc.find(last_call)
                    ins = idx + len(last_call)
                    qsrc = qsrc[:ins] + "\n        getFiendsNearby(latitude, longitude, playerId)," + qsrc[ins:]
                    # Return mapping: after the LAST results[N] line.
                    ret_matches = list(re.finditer(r"^(\s+)\w+: results\[\d+\]\.status === 'fulfilled' \? results\[\d+\]\.value : \[\],$", qsrc, re.M))
                    if not ret_matches:
                        print("WARNING: return mapping anchor not found - fiends return NOT added")
                        warned.append("queries-return")
                    else:
                        last_ret = ret_matches[-1]
                        ins2 = last_ret.end()
                        qsrc = qsrc[:ins2] + f"\n        fiends: results[{n}].status === 'fulfilled' ? results[{n}].value : []," + qsrc[ins2:]
                        print(f"FIEND_FRONTEND_QUERIES_CALL_OK (fiends at results[{n}])")
            # The edit must not change any bracket pair's imbalance.
            d = delta(qsrc)
            if (d[0] - d[1]) != (qd0[0] - qd0[1]) or (d[2] - d[3]) != (qd0[2] - qd0[3]) or (d[4] - d[5]) != (qd0[4] - qd0[5]):
                print("WARNING: unbalanced brackets - useMapQueries.ts NOT written")
                qsrc = qorig
                warned.append("queries-balance")
            if qsrc != qorig:
                QUERIES.write_text(qsrc)
                landed.append("queries")

    # ================= Part 3: app/(tabs)/index.tsx =================
    if not INDEX.exists():
        print("WARNING: app/(tabs)/index.tsx not found - Fiend map wiring NOT added")
        warned.append("index")
    else:
        src = INDEX.read_text(errors="ignore")
        iorig = src
        id0 = delta(src)
        # 3a. Api imports (regex over the services/api import, like the repair).
        if "getFiendsNearby" in src and "sellToFiend" in src:
            print("FIEND_FRONTEND_INDEX_IMPORT_ALREADY_APPLIED")
        else:
            m = re.search(r"\} from '\.\./\.\./services/api';", src)
            if not m:
                print("WARNING: services/api import not found in index.tsx - Fiend imports NOT added")
                warned.append("index-import")
            else:
                block = src[:m.start()]
                add = ""
                if "getFiendsNearby" not in block:
                    add += "  getFiendsNearby,\n"
                if "sellToFiend" not in block:
                    add += "  sellToFiend,\n"
                src = src[:m.start()] + add + src[m.start():]
                print("FIEND_FRONTEND_INDEX_IMPORT_OK")
        # 3b. selectedMarker union + fiendHasItems helper + fiendCanSell.
        if "'fiend'" in src and "fiendHasItems" in src:
            print("FIEND_FRONTEND_INDEX_HELPER_ALREADY_APPLIED")
        else:
            sm = re.search(r"const \[selectedMarker, setSelectedMarker\] = useState<\{.*?\} \| null>\(null\);", src, re.S)
            if not sm:
                print("WARNING: selectedMarker state not found - 'fiend' type / helper NOT added")
                warned.append("index-helper")
            else:
                block = sm.group(0)
                new_block = block
                if "'fiend'" not in block:
                    new_block = re.sub(r"(type: 'monster'[^;]*);", r"\1 | 'fiend';", new_block, count=1)
                    print("FIEND_FRONTEND_INDEX_UNION_OK")
                else:
                    print("FIEND_FRONTEND_INDEX_UNION_ALREADY_APPLIED")
                src = src[:sm.start()] + new_block + src[sm.end():]
                if "fiendHasItems" not in src:
                    sm2 = re.search(r"const \[selectedMarker, setSelectedMarker\] = useState<\{.*?\} \| null>\(null\);", src, re.S)
                    src = src[:sm2.end()] + "\n" + FIEND_HELPER.rstrip("\n") + src[sm2.end():]
                    print("FIEND_FRONTEND_INDEX_HELPER_OK")
        # 3c. nearbyFiends memo.
        if "nearbyFiends" in src:
            print("FIEND_FRONTEND_INDEX_MEMO_ALREADY_APPLIED")
        elif "  const nearbyShootouts = useMemo(() => entitiesData?.shootouts || [], [entitiesData?.shootouts]);" in src:
            src = src.replace(
                "  const nearbyShootouts = useMemo(() => entitiesData?.shootouts || [], [entitiesData?.shootouts]);",
                "  const nearbyShootouts = useMemo(() => entitiesData?.shootouts || [], [entitiesData?.shootouts]);\n  const nearbyFiends = useMemo(() => entitiesData?.fiends || [], [entitiesData?.fiends]);",
                1)
            print("FIEND_FRONTEND_INDEX_MEMO_OK")
        elif "  const nearbyActivityCenters = useMemo(() => entitiesData?.activityCenters || [], [entitiesData?.activityCenters]);" in src:
            src = src.replace(
                "  const nearbyActivityCenters = useMemo(() => entitiesData?.activityCenters || [], [entitiesData?.activityCenters]);",
                "  const nearbyActivityCenters = useMemo(() => entitiesData?.activityCenters || [], [entitiesData?.activityCenters]);\n  const nearbyFiends = useMemo(() => entitiesData?.fiends || [], [entitiesData?.fiends]);",
                1)
            print("FIEND_FRONTEND_INDEX_MEMO_OK")
        else:
            print("WARNING: nearby memo anchor not found - nearbyFiends NOT added")
            warned.append("index-memo")
        # 3d. mapMarkers spread + deps.
        if "type: 'fiend' as const," in src:
            print("FIEND_FRONTEND_INDEX_MARKERS_ALREADY_APPLIED")
        else:
            sm = re.search(r"      type: 'shootout' as const,\n", src)
            if not sm:
                print("WARNING: shootout marker spread not found - Fiend markers NOT added")
                warned.append("index-markers")
            else:
                end = src.find("\n    }),", sm.end())
                if end == -1:
                    print("WARNING: shootout marker spread end not found - Fiend markers NOT added")
                    warned.append("index-markers")
                else:
                    ins = end + len("\n    }),")
                    src = src[:ins] + "\n" + FIEND_SPREAD.rstrip("\n") + src[ins:]
                    print("FIEND_FRONTEND_INDEX_MARKERS_OK")
            dm = re.search(r"\], \[nearbyMonsters[^\]]*nearbyShootouts, (?:nearbyActivityCenters, )?localCooldowns\]\);", src)
            if dm:
                src = src[:dm.start()] + dm.group(0).replace("nearbyShootouts,", "nearbyShootouts, nearbyFiends,", 1) + src[dm.end():]
                print("FIEND_FRONTEND_INDEX_MARKERS_DEPS_OK")
            else:
                print("WARNING: mapMarkers deps anchor not found - Fiend markers may go stale")
                warned.append("index-markers-deps")
        # 3e. handleMarkerPress branch + deps.
        if "marker.type === 'fiend'" in src:
            print("FIEND_FRONTEND_INDEX_PRESS_ALREADY_APPLIED")
        else:
            anchor = "      if (shootout) setSelectedShootout(shootout);\n    }"
            if anchor in src:
                # Turn the shootout branch's closing } into "} else if (fiend)".
                src = src.replace(anchor, "      if (shootout) setSelectedShootout(shootout);\n    } else if (marker.type === 'fiend') {\n      const fiend = nearbyFiends.find((f: any) => f.id === marker.id);\n      if (fiend) setSelectedMarker({ type: 'fiend', data: fiend });\n    }", 1)
                print("FIEND_FRONTEND_INDEX_PRESS_OK")
            else:
                print("WARNING: shootout press branch not found - Fiend taps NOT wired")
                warned.append("index-press")
            dm = re.search(r"nearbyShootouts(?:, nearbyActivityCenters)?\]\);", src)
            if dm:
                src = src[:dm.start()] + dm.group(0).replace("nearbyShootouts", "nearbyShootouts, nearbyFiends", 1) + src[dm.end():]
                print("FIEND_FRONTEND_INDEX_PRESS_DEPS_OK")
            else:
                print("WARNING: handleMarkerPress deps anchor not found - Fiend taps may use a stale list")
                warned.append("index-press-deps")
        # 3f. handleSellToFiend handler (before handleStartMission).
        if "handleSellToFiend" in src:
            print("FIEND_FRONTEND_INDEX_HANDLER_ALREADY_APPLIED")
        elif "  const handleStartMission = useCallback((mission: Mission) => {" in src:
            src = src.replace("  const handleStartMission = useCallback((mission: Mission) => {",
                              FIEND_HANDLER.rstrip("\n") + "\n  const handleStartMission = useCallback((mission: Mission) => {", 1)
            print("FIEND_FRONTEND_INDEX_HANDLER_OK")
        else:
            print("WARNING: handleStartMission anchor not found - SELL TO FIEND handler NOT added")
            warned.append("index-handler")
        # 3g. Fiend popup (before the mission popup).
        if "selectedMarker.type === 'fiend'" in src:
            print("FIEND_FRONTEND_INDEX_POPUP_ALREADY_APPLIED")
        elif "          {selectedMarker.type === 'mission' && (" in src:
            src = src.replace("          {selectedMarker.type === 'mission' && (",
                              FIEND_POPUP.rstrip("\n") + "\n          {selectedMarker.type === 'mission' && (", 1)
            print("FIEND_FRONTEND_INDEX_POPUP_OK")
        else:
            print("WARNING: mission popup anchor not found - Fiend popup NOT added")
            warned.append("index-popup")
        d = delta(src)
        if (d[0] - d[1]) != (id0[0] - id0[1]) or (d[2] - d[3]) != (id0[2] - id0[3]) or (d[4] - d[5]) != (id0[4] - id0[5]):
            print("WARNING: unbalanced brackets - index.tsx NOT written")
            src = iorig
            warned.append("index-balance")
        if src != iorig:
            INDEX.write_text(src)
            landed.append("index")

    # ================= Part 4: components/GameMap.tsx =================
    if not GAMEMAP.exists():
        print("WARNING: components/GameMap.tsx not found - Fiend marker NOT added")
        warned.append("gamemap")
    else:
        gsrc = GAMEMAP.read_text(errors="ignore")
        gorig = gsrc
        gd0 = delta(gsrc)
        # 4a. Marker type union.
        uline = [ln for ln in gsrc.split("\n") if "type: 'monster'" in ln]
        if uline and "'fiend'" in uline[0]:
            print("FIEND_FRONTEND_GAMEMAP_UNION_ALREADY_APPLIED")
        else:
            m = re.search(r"(  type: 'monster'[^;]*);", gsrc)
            if m:
                gsrc = gsrc[:m.end() - 1] + " | 'fiend'" + gsrc[m.end() - 1:]
                print("FIEND_FRONTEND_GAMEMAP_UNION_OK")
            else:
                print("WARNING: MapMarker union not found - 'fiend' type NOT added")
                warned.append("gamemap-union")
        # 4b. markerColors: insert before the final ' };' of the markerColors line.
        if "fiend: '#8BC34A'" in gsrc:
            print("FIEND_FRONTEND_GAMEMAP_COLOR_ALREADY_APPLIED")
        else:
            done = False
            for ln in gsrc.split("\n"):
                if "var markerColors = {" in ln:
                    idx = ln.rfind(" };")
                    if idx != -1:
                        gsrc = gsrc.replace(ln, ln[:idx] + ", fiend: '#8BC34A'" + ln[idx:], 1)
                        print("FIEND_FRONTEND_GAMEMAP_COLOR_OK")
                        done = True
                    break
            if not done:
                print("WARNING: markerColors line not found - Fiend color NOT added")
                warned.append("gamemap-color")
        # 4c. markerIcons: insert before the final ' };' of the markerIcons
        # line. NEVER a [^}]* regex here (the \\u{...} escapes break it).
        if "fiend: '🧟'" in gsrc:
            print("FIEND_FRONTEND_GAMEMAP_ICON_ALREADY_APPLIED")
        else:
            done = False
            for ln in gsrc.split("\n"):
                if "var markerIcons = {" in ln:
                    idx = ln.rfind(" };")
                    if idx != -1:
                        gsrc = gsrc.replace(ln, ln[:idx] + ", fiend: '🧟'" + ln[idx:], 1)
                        print("FIEND_FRONTEND_GAMEMAP_ICON_OK")
                        done = True
                    break
            if not done:
                print("WARNING: markerIcons line not found - Fiend icon NOT added")
                warned.append("gamemap-icon")
        # 4d. Fiend marker branch (before the bank branch).
        if "m.type === 'fiend'" in gsrc:
            print("FIEND_FRONTEND_GAMEMAP_BRANCH_ALREADY_APPLIED")
        elif "            } else if (m.type === 'bank') {" in gsrc:
            gsrc = gsrc.replace("            } else if (m.type === 'bank') {",
                                FIEND_BRANCH.rstrip("\n") + "\n            } else if (m.type === 'bank') {", 1)
            print("FIEND_FRONTEND_GAMEMAP_BRANCH_OK")
        else:
            print("WARNING: bank marker branch not found - Fiend marker branch NOT added")
            warned.append("gamemap-branch")
        # 4e. 48x62 location sizing.
        if "m.type === 'fiend'" in gsrc and "isLocationMarker" in gsrc:
            lm = re.search(r"var isLocationMarker = \(([^;]*)\);", gsrc)
            if lm and "'fiend'" in lm.group(1):
                print("FIEND_FRONTEND_GAMEMAP_SIZING_ALREADY_APPLIED")
            elif lm:
                gsrc = gsrc[:lm.end() - 2] + " || m.type === 'fiend'" + gsrc[lm.end() - 2:]
                print("FIEND_FRONTEND_GAMEMAP_SIZING_OK")
            else:
                print("WARNING: isLocationMarker line not found - Fiend sizing NOT added")
                warned.append("gamemap-sizing")
        d = delta(gsrc)
        if (d[0] - d[1]) != (gd0[0] - gd0[1]) or (d[2] - d[3]) != (gd0[2] - gd0[3]) or (d[4] - d[5]) != (gd0[4] - gd0[5]):
            print("WARNING: unbalanced brackets - GameMap.tsx NOT written")
            gsrc = gorig
            warned.append("gamemap-balance")
        if gsrc != gorig:
            GAMEMAP.write_text(gsrc)
            landed.append("gamemap")

    # ================= Part 5: character.tsx (remove SELL buttons) =================
    if not CHARACTER.exists():
        print("WARNING: app/(tabs)/character.tsx not found - SELL buttons NOT removed")
        warned.append("character")
    else:
        csrc = CHARACTER.read_text(errors="ignore")
        corig = csrc
        cd0 = delta(csrc)
        for item_id, label, handler in SELL_ROWS:
            new_src, status = _remove_sell_button(csrc, label, handler)
            if status == "removed":
                csrc = new_src
                print(f"FIEND_FRONTEND_SELL_{item_id.upper()}_REMOVED_OK")
                landed.append(f"sell-{item_id}")
            elif status == "absent":
                # SELL button already gone (or row never landed): verify the
                # USE button is still there so we know the row itself exists.
                use_labels = {"grass": "USE (+50% HP 60s)", "pills": "USE (+50% ENERGY 60s)",
                              "rock_candy": "USE (+50% ATTACK 60s)", "flake": "USE (+50% ARMOR 60s)",
                              "brown_sugar": "USE (+50% LUCK 60s)"}
                if use_labels[item_id] in csrc or f"onUse{item_id.replace('_', ' ').title().replace(' ', '')}" in csrc:
                    print(f"FIEND_FRONTEND_SELL_{item_id.upper()}_ALREADY_REMOVED")
                    landed.append(f"sell-{item_id}")
                else:
                    print(f"WARNING: {item_id} row not found - SELL button state unknown")
                    warned.append(f"sell-{item_id}")
            else:
                print(f"WARNING: {item_id} SELL button NOT removed ({status})")
                warned.append(f"sell-{item_id}")
        d = delta(csrc)
        if (d[0] - d[1]) != (cd0[0] - cd0[1]) or (d[2] - d[3]) != (cd0[2] - cd0[3]) or (d[4] - d[5]) != (cd0[4] - cd0[5]):
            print("WARNING: unbalanced brackets - character.tsx NOT written")
            csrc = corig
            warned.append("character-balance")
        if csrc != corig:
            CHARACTER.write_text(csrc)

    if warned:
        print("FIEND_FRONTEND_PARTIAL: " + ",".join(landed) + " (warnings: " + ",".join(warned) + ")")
    else:
        print("FIEND_FRONTEND_OK")


if __name__ == "__main__":
    main()
