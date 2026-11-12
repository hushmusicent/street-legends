#!/usr/bin/env python3
"""Show other players' profile pictures on the map marker AND in the player popup.

Root cause (verified live): the backend DOES return profile_pic for nearby
players, but the app never used it — the player marker object only passed
id/coordinate/type/level/name, GameMap drew every 'player' marker as a
generic blue circle with the bust emoji, and the player popup header used a
generic Ionicons person icon. This patch is FRONTEND-ONLY (no backend change).

Changes:
  1. index.tsx — mapMarkers useMemo: pass profile_pic: p.profile_pic on the
     'player' marker object.
  2. index.tsx — player popup header: render the player's picture (36px
     circle) when selectedMarker.data.profile_pic is set, else the generic
     Ionicons person icon. The popup data is the full nearby player object,
     so profile_pic is available.
  3. GameMap.tsx — MapMarker interface gains profile_pic?: string | null.
  4. GameMap.tsx — new m.type === 'player' branch before the final generic
     else in the marker-HTML chain: with a pic, a 42x58 wrapper with a 38px
     circular photo (3px solid #4285F4 border, URL quote-escaped like the
     territory owner-pic marker) + level badge; without a pic, the generic
     blue circle with the bust emoji (reuses the `icon` variable).
  5. GameMap.tsx — isPlayerMarker added to the sizing chains so a player
     marker gets width 42, height 58, anchorY 29; no other marker type changes.

Fallback: a player with no profile_pic set (e.g. AppSolutGroup right now)
still shows the generic blue circle / generic person icon until they upload
a picture on their phone.

FRONTEND — Expo Go first. Marker: PLAYER_PROFILE_PIC_OK
"""
import sys
from pathlib import Path

INDEX = Path("frontend/app/(tabs)/index.tsx")
GAMEMAP = Path("frontend/components/GameMap.tsx")

# (label, file_key, old, new, new_probe) — new_probe is a distinctive string
# that is present once the replacement has landed; a step is skipped when
# its new_probe is already present (idempotent + survives partial runs).
STEPS = [
    (
        "index-marker-profile-pic",
        "index",
        """      type: 'player' as const,
      level: p.level,
      name: p.name,""",
        """      type: 'player' as const,
      level: p.level,
      name: p.name,
      profile_pic: p.profile_pic,""",
        "profile_pic: p.profile_pic",
    ),
    (
        "index-popup-header-pic",
        "index",
        """                <Ionicons name="person" size={28} color="#4285F4" />""",
        """                {selectedMarker.data.profile_pic ? (<Image source={{ uri: selectedMarker.data.profile_pic }} style={{ width: 36, height: 36, borderRadius: 18 }} />) : (<Ionicons name="person" size={28} color="#4285F4" />)}""",
        "selectedMarker.data.profile_pic",
    ),
    (
        "gamemap-interface-profile-pic",
        "gamemap",
        """  cooldownSeconds?: number;""",
        """  cooldownSeconds?: number;
  profile_pic?: string | null;""",
        "profile_pic?: string | null;",
    ),
    (
        "gamemap-player-marker-branch",
        "gamemap",
        """            } else {
              markerHTML = '<div style="background:' + color + ';width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:14px;position:relative;">' + icon + levelHTML + '</div>';""",
        """            } else if (m.type === 'player') {
              if (m.profile_pic) {
                var picUrl = m.profile_pic.replace(/"/g, '&quot;');
                markerHTML = '<div style="width:42px;height:58px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                  '<div style="width:38px;height:38px;border-radius:50%;border:3px solid #4285F4;box-shadow:0 2px 8px rgba(0,0,0,0.5);overflow:hidden;background:#222;">' +
                  '<img src="' + picUrl + '" style="width:100%;height:100%;object-fit:cover;display:block;" /></div>' + levelHTML + '</div>';
              } else {
                markerHTML = '<div style="width:42px;height:58px;position:relative;display:flex;flex-direction:column;align-items:center;">' +
                  '<div style="background:#4285F4;width:38px;height:38px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:3px solid white;box-shadow:0 2px 8px rgba(0,0,0,0.5);font-size:18px;position:relative;">' + icon + levelHTML + '</div></div>';
              }
            } else {
              markerHTML = '<div style="background:' + color + ';width:32px;height:32px;border-radius:50%;display:flex;align-items:center;justify-content:center;border:2px solid white;box-shadow:0 2px 6px rgba(0,0,0,0.3);font-size:14px;position:relative;">' + icon + levelHTML + '</div>';""",
        "var picUrl = m.profile_pic.replace",
    ),
    (
        "gamemap-is-player-marker-var",
        "gamemap",
        """            var isShootoutMarker = (m.type === 'shootout');""",
        """            var isShootoutMarker = (m.type === 'shootout');
            var isPlayerMarker = (m.type === 'player');""",
        "var isPlayerMarker = (m.type === 'player');",
    ),
    (
        "gamemap-marker-width-player",
        "gamemap",
        "(enemyImg ? 42 : 32)",
        "((enemyImg || isPlayerMarker) ? 42 : 32)",
        "((enemyImg || isPlayerMarker) ? 42 : 32)",
    ),
    (
        "gamemap-marker-height-player",
        "gamemap",
        "(enemyImg ? 58 : 32)",
        "((enemyImg || isPlayerMarker) ? 58 : 32)",
        "((enemyImg || isPlayerMarker) ? 58 : 32)",
    ),
    (
        "gamemap-marker-anchor-player",
        "gamemap",
        "(enemyImg ? 29 : 16)",
        "((enemyImg || isPlayerMarker) ? 29 : 16)",
        "((enemyImg || isPlayerMarker) ? 29 : 16)",
    ),
]


def main():
    if not INDEX.exists():
        print("PLAYER_PROFILE_PIC_FAIL frontend/app/(tabs)/index.tsx not found")
        return 1
    if not GAMEMAP.exists():
        print("PLAYER_PROFILE_PIC_FAIL frontend/components/GameMap.tsx not found")
        return 1
    index_src = INDEX.read_text(encoding="utf-8")
    gamemap_src = GAMEMAP.read_text(encoding="utf-8")
    sources = {"index": index_src, "gamemap": gamemap_src}
    failed = []
    applied = 0
    skipped = 0
    for label, file_key, old, new, probe in STEPS:
        src = sources[file_key]
        if probe in src:
            skipped += 1
            continue
        count = src.count(old)
        if count != 1:
            failed.append("%s (anchor found %d times)" % (label, count))
            continue
        sources[file_key] = src.replace(old, new, 1)
        applied += 1
    # Always write back whatever landed, even on failure (skill rule).
    INDEX.write_text(sources["index"], encoding="utf-8")
    GAMEMAP.write_text(sources["gamemap"], encoding="utf-8")
    if failed:
        print("PLAYER_PROFILE_PIC_FAIL missed: %s" % "; ".join(failed))
        return 1
    if applied == 0 and skipped == len(STEPS):
        print("PLAYER_PROFILE_PIC_ALREADY_APPLIED")
        return 0
    # Sanity: braces/parens must stay balanced in both files.
    for name, src in sources.items():
        if src.count("{") != src.count("}"):
            print("PLAYER_PROFILE_PIC_FAIL unbalanced braces in %s" % name)
            return 1
        if src.count("(") != src.count(")"):
            print("PLAYER_PROFILE_PIC_FAIL unbalanced parens in %s" % name)
            return 1
    print("PLAYER_PROFILE_PIC_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
