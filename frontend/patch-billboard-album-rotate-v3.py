#!/usr/bin/env python3
"""Street Legends frontend v3: Billboards rotate through THREE ads.

Adds the user's 'ASIS - Real As It Gets' promo as a third billboard
ad, alongside the Hush Music Ent. logo and the Calvin Thomas King
album. Same 30-second rotation, now cycling 0 logo -> 1 King album
-> 2 ASIS (90s full cycle). Tapping a billboard still opens whatever
picture/site is showing at that moment.

What it changes (builds on v2):
  1. app/(tabs)/index.tsx:
     - const ASIS_AD (ASIS art data URI, downloaded from GitHub),
       inserted after ALBUM_AD.
     - billboardAdIsAlbumNow (mod 2) -> billboardAdNow (mod 3).
     - Popup IIFE picks from 3 ads: ASIS -> 'ASIS - Real As It
       Gets', LISTEN NOW -> https://ditto.fm/real-as-it-gets ;
       King album -> LISTEN NOW -> ditto King album link ; logo ->
       VISIT SITE -> hushmusicent.com. Album ads are square (QR
       whole), logo is 3/2.
  2. components/GameMap.tsx:
     - var ASIS_THUMB (240px ASIS thumb data URI), after ALBUM_THUMB.
     - billboardThumbNow() mod 2 -> mod 3 (same 30s bucket as the
       popup). The setInterval that swaps marker imgs is unchanged.

Requires the v2 rotation (ALBUM_AD + billboardAdIsAlbumNow) to be
present; if ALBUM_AD is missing it is downloaded and added first.
Frontend / Expo Go only. Idempotent.
"""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend" / "app" / "(tabs)" / "index.tsx"
GAMEMAP = ROOT / "frontend" / "components" / "GameMap.tsx"
MARKER = "BILLBOARD_ALBUM_ROTATE_V3_OK"
BASE = "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/assets"
ALBUM_URL = BASE + "/billboard-album.jpg.b64.txt?v=1"
ASIS_URL = BASE + "/billboard-asis.jpg.b64.txt?v=1"
THUMB_URL = BASE + "/billboard-album-thumb.jpg.b64.txt?v=1"
ASIS_THUMB_URL = BASE + "/billboard-asis-thumb.jpg.b64.txt?v=1"
DITTO_KING = "https://ditto.fm/the-calvin-thomas-king-album"
DITTO_ASIS = "https://ditto.fm/real-as-it-gets"

# v2 helper -> v3 helper (3-way).
V2_HELPER_TS = """// BILLBOARD_ROTATE: which ad is showing RIGHT NOW — wall-clock 30s
// bucket, same as the map marker, so the popup always matches the
// picture the player tapped. Flips every 30 seconds.
const billboardAdIsAlbumNow = () => (Math.floor(Date.now() / 30000) % 2) === 1;"""

V3_HELPER_TS = """// BILLBOARD_ROTATE: which ad is showing RIGHT NOW — wall-clock 30s
// bucket cycling through 3 ads, same as the map marker, so the
// popup always matches the picture the player tapped. 0 logo,
// 1 King album, 2 ASIS. Flips every 30 seconds.
const billboardAdNow = () => Math.floor(Date.now() / 30000) % 3;"""

# v2 popup picker lines -> v3 picker lines.
V2_PICKER = """            const isAlbum = billboardAdIsAlbumNow();
            const adUri = isAlbum ? ALBUM_AD : BILLBOARD_AD;
            const adTitle = isAlbum ? 'King Veno - The Calvin Thomas King Album' : 'Hush Music Ent.';
            const adLink = isAlbum ? '""" + DITTO_KING + """' : 'https://www.hushmusicent.com';
            const adButton = isAlbum ? 'LISTEN NOW' : 'VISIT SITE';
            const adAspect = isAlbum ? 1 : 3 / 2;"""

V3_PICKER = """            const adIdx = billboardAdNow();
            const adUri = adIdx === 2 ? ASIS_AD : adIdx === 1 ? ALBUM_AD : BILLBOARD_AD;
            const adTitle = adIdx === 2 ? 'ASIS - Real As It Gets' : adIdx === 1 ? 'King Veno - The Calvin Thomas King Album' : 'Hush Music Ent.';
            const adLink = adIdx === 2 ? '""" + DITTO_ASIS + """' : adIdx === 1 ? '""" + DITTO_KING + """' : 'https://www.hushmusicent.com';
            const adButton = adIdx === 0 ? 'VISIT SITE' : 'LISTEN NOW';
            const adAspect = adIdx === 0 ? 3 / 2 : 1;"""

# v0 popup (no rotation at all) -> full v3 IIFE (used when v2 never ran).
POPUP_V0 = """          {selectedMarker.type === 'billboard' && (
            <View>
              <View style={styles.popupHeader}>
                <Text style={{ fontSize: 28 }}>🛣️</Text>
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>Hush Music Ent.</Text>
                  <Text style={styles.popupSubtitle}>{selectedMarker.data.name || 'Highway'}</Text>
                </View>
              </View>
              <Image source={{ uri: BILLBOARD_AD }} style={{ width: '100%', aspectRatio: 3 / 2, borderRadius: 10, marginTop: 8 }} resizeMode="cover" />
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#FFD700', marginTop: 10 }]}
                onPress={() => { Linking.openURL('https://www.hushmusicent.com'); }}
              >
                <Text style={[styles.actionButtonText, { color: '#000' }]}>VISIT SITE</Text>
              </TouchableOpacity>
            </View>
          )}"""

POPUP_V3 = """          {selectedMarker.type === 'billboard' && (() => {
""" + V3_PICKER + """
            return (
            <View>
              <View style={styles.popupHeader}>
                <Text style={{ fontSize: 28 }}>🛣️</Text>
                <View style={styles.popupHeaderText}>
                  <Text style={styles.popupTitle}>{adTitle}</Text>
                  <Text style={styles.popupSubtitle}>{selectedMarker.data.name || 'Highway'}</Text>
                </View>
              </View>
              <Image source={{ uri: adUri }} style={{ width: '100%', aspectRatio: adAspect, borderRadius: 10, marginTop: 8 }} resizeMode="cover" />
              <TouchableOpacity
                style={[styles.actionButton, { backgroundColor: '#FFD700', marginTop: 10 }]}
                onPress={() => { Linking.openURL(adLink); }}
              >
                <Text style={[styles.actionButtonText, { color: '#000' }]}>{adButton}</Text>
              </TouchableOpacity>
            </View>
            );
          })()}"""

# GameMap: v2 thumb picker -> v3 thumb picker.
V2_THUMB_FN = """    var billboardThumbNow = function () {
      return (Math.floor(Date.now() / 30000) % 2 === 1) ? ALBUM_THUMB : BILLBOARD_THUMB;
    };"""

V3_THUMB_FN = """    var billboardThumbNow = function () {
      var idx = Math.floor(Date.now() / 30000) % 3;
      return idx === 2 ? ASIS_THUMB : idx === 1 ? ALBUM_THUMB : BILLBOARD_THUMB;
    };"""

# GameMap: full rotate block (function + interval) for the v0 case
# where v2 never ran — same as v2's block but mod 3.
V3_ROTATE_JS = """    // BILLBOARD_ROTATE: current ad by wall-clock 30s bucket (same as
    // the popup). createMarker() never rebuilds an existing marker,
    // so the interval below swaps the img in the DOM every second.
    var billboardThumbNow = function () {
      var idx = Math.floor(Date.now() / 30000) % 3;
      return idx === 2 ? ASIS_THUMB : idx === 1 ? ALBUM_THUMB : BILLBOARD_THUMB;
    };
    setInterval(function () {
      var now = billboardThumbNow();
      var imgs = document.querySelectorAll('img.billboard-ad-img');
      for (var i = 0; i < imgs.length; i++) {
        if (imgs[i].getAttribute('src') !== now) imgs[i].setAttribute('src', now);
      }
    }, 1000);"""

# GameMap marker branch img: v0 form -> v3 form.
GAMEMAP_IMG_V0 = """    '<img src="' + BILLBOARD_THUMB + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +"""
GAMEMAP_IMG_V3 = """    '<img class="billboard-ad-img" src="' + billboardThumbNow() + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +"""


def fetch_b64(url, label):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read().decode("utf-8").strip()
    except Exception as e:
        print("ERROR: could not download %s (%s): %s" % (label, url, e))
        sys.exit(1)
    if len(data) < 1000 or "data:image" in data or "<" in data[:50]:
        print("ERROR: %s download looks wrong (len %d). Aborting." % (label, len(data)))
        sys.exit(1)
    return data


def insert_after_line(lines, startswith, insert_text, label):
    for i, line in enumerate(lines):
        if line.startswith(startswith):
            lines.insert(i + 1, insert_text)
            return lines, True
    print("ERROR: %s anchor not found (%s). File has drifted; stopping." % (label, startswith[:60]))
    return lines, False


def main():
    # ---- index.tsx ----
    if not INDEX.exists():
        print("ERROR: %s not found. Run from /app." % INDEX)
        sys.exit(1)
    src = INDEX.read_text(encoding="utf-8", errors="ignore")
    if "billboardAdNow" in src and "ASIS_AD" in src and V3_PICKER in src:
        print("BILLBOARD_ALBUM_ROTATE_V3_INDEX_ALREADY_APPLIED")
    else:
        # ALBUM_AD first (v2 asset) if v2 never ran.
        if "ALBUM_AD" not in src:
            album_b64 = fetch_b64(ALBUM_URL, "billboard-album.jpg.b64.txt")
            if 'const BILLBOARD_AD = "data:image/jpeg;base64,' not in src:
                print("ERROR: BILLBOARD_AD anchor not found in index.tsx. Stopping without writing.")
                sys.exit(1)
            lines = src.split("\n")
            album_def = 'const ALBUM_AD = "data:image/jpeg;base64,' + album_b64 + '";'
            lines, ok = insert_after_line(
                lines, 'const BILLBOARD_AD = "data:image/jpeg;base64,', album_def, "index.tsx BILLBOARD_AD")
            if not ok:
                sys.exit(1)
            src = "\n".join(lines)
        # ASIS_AD after ALBUM_AD.
        if "ASIS_AD" not in src:
            asis_b64 = fetch_b64(ASIS_URL, "billboard-asis.jpg.b64.txt")
            lines = src.split("\n")
            asis_def = 'const ASIS_AD = "data:image/jpeg;base64,' + asis_b64 + '";'
            lines, ok = insert_after_line(
                lines, 'const ALBUM_AD = "data:image/jpeg;base64,', asis_def, "index.tsx ALBUM_AD")
            if not ok:
                sys.exit(1)
            src = "\n".join(lines)
        # Helper: v2 -> v3. If no helper at all (v0, v2 never ran),
        # add the v3 helper after ASIS_AD.
        if V2_HELPER_TS in src:
            src = src.replace(V2_HELPER_TS, V3_HELPER_TS, 1)
        elif "billboardAdNow" not in src:
            lines = src.split("\n")
            lines, ok = insert_after_line(
                lines, 'const ASIS_AD = "data:image/jpeg;base64,', V3_HELPER_TS, "index.tsx ASIS_AD")
            if not ok:
                sys.exit(1)
            src = "\n".join(lines)
        # Popup picker: v2 -> v3, or v0 -> full v3 IIFE.
        if V3_PICKER in src:
            pass
        elif V2_PICKER in src:
            src = src.replace(V2_PICKER, V3_PICKER, 1)
        elif POPUP_V0 in src:
            src = src.replace(POPUP_V0, POPUP_V3, 1)
        else:
            print("ERROR: billboard popup anchor not found in index.tsx. Stopping without writing.")
            sys.exit(1)
        INDEX.write_text(src, encoding="utf-8")
        print("BILLBOARD_ALBUM_ROTATE_V3_INDEX_OK")

    # ---- GameMap.tsx ----
    if not GAMEMAP.exists():
        print("ERROR: %s not found. Run from /app." % GAMEMAP)
        sys.exit(1)
    gsrc = GAMEMAP.read_text(encoding="utf-8", errors="ignore")
    if "ASIS_THUMB" in gsrc and V3_THUMB_FN in gsrc:
        print("BILLBOARD_ALBUM_ROTATE_V3_GAMEMAP_ALREADY_APPLIED")
    else:
        # ALBUM_THUMB first (v2 asset) if v2 never ran.
        if "ALBUM_THUMB" not in gsrc:
            thumb_b64 = fetch_b64(THUMB_URL, "billboard-album-thumb.jpg.b64.txt")
            if 'var BILLBOARD_THUMB = "data:image/jpeg;base64,' not in gsrc:
                print("ERROR: BILLBOARD_THUMB anchor not found in GameMap.tsx. Stopping without writing.")
                sys.exit(1)
            glines = gsrc.split("\n")
            thumb_def = '    var ALBUM_THUMB = "data:image/jpeg;base64,' + thumb_b64 + '";'
            glines, ok = insert_after_line(
                glines, '    var BILLBOARD_THUMB = "data:image/jpeg;base64,', thumb_def, "GameMap.tsx BILLBOARD_THUMB")
            if not ok:
                sys.exit(1)
            gsrc = "\n".join(glines)
        # ASIS_THUMB after ALBUM_THUMB.
        if "ASIS_THUMB" not in gsrc:
            asis_thumb_b64 = fetch_b64(ASIS_THUMB_URL, "billboard-asis-thumb.jpg.b64.txt")
            glines = gsrc.split("\n")
            asis_thumb_def = '    var ASIS_THUMB = "data:image/jpeg;base64,' + asis_thumb_b64 + '";'
            glines, ok = insert_after_line(
                glines, '    var ALBUM_THUMB = "data:image/jpeg;base64,', asis_thumb_def, "GameMap.tsx ALBUM_THUMB")
            if not ok:
                sys.exit(1)
            gsrc = "\n".join(glines)
        # Thumb picker: v2 -> v3. If no rotate block at all (v0, v2
        # never ran), add the full v3 rotate block after ASIS_THUMB
        # and swap the marker img to the v3 form.
        if V3_THUMB_FN in gsrc:
            pass
        elif V2_THUMB_FN in gsrc:
            gsrc = gsrc.replace(V2_THUMB_FN, V3_THUMB_FN, 1)
        elif "billboardThumbNow" not in gsrc:
            glines = gsrc.split("\n")
            glines, ok = insert_after_line(
                glines, '    var ASIS_THUMB = "data:image/jpeg;base64,', V3_ROTATE_JS.rstrip("\n"), "GameMap.tsx ASIS_THUMB")
            if not ok:
                sys.exit(1)
            gsrc = "\n".join(glines)
            if GAMEMAP_IMG_V0 in gsrc:
                gsrc = gsrc.replace(GAMEMAP_IMG_V0, GAMEMAP_IMG_V3, 1)
            else:
                print("ERROR: billboard marker img anchor not found in GameMap.tsx. Stopping without writing.")
                sys.exit(1)
        GAMEMAP.write_text(gsrc, encoding="utf-8")
        print("BILLBOARD_ALBUM_ROTATE_V3_GAMEMAP_OK")

    print(MARKER)


if __name__ == "__main__":
    main()
