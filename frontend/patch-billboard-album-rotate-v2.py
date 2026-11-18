#!/usr/bin/env python3
"""Street Legends frontend v2: Billboards ROTATE ad + link every 30s.

Replaces the v1 fixed per-billboard pick. The user corrected it:
the billboard picture AND link must change every 30 seconds, and
tapping a billboard opens whatever picture/site is showing at that
moment.

How it works (wall-clock 30s buckets, same function both sides):
  - GameMap WebView: a setInterval swaps every billboard marker img
    to the current ad every second. This is REQUIRED because
    createMarker() returns early for existing markers (position-only
    update) — updateMarkers can never change an on-map marker's
    picture, so the flip has to happen in the WebView DOM itself.
    New markers are built with the current ad via billboardThumbNow().
  - index.tsx popup: billboardAdIsAlbumNow() (same 30s bucket) picks
    the ad, title, link and button at tap time, so the popup always
    matches the picture the player tapped. Album -> ALBUM_AD, square
    (QR whole), LISTEN NOW -> https://ditto.fm/the-calvin-thomas-king-album.
    Logo -> BILLBOARD_AD, 3/2, VISIT SITE -> https://www.hushmusicent.com.

Handles BOTH states: v1 (hash helper present) and v0 (no album art
yet — downloads ALBUM_AD/ALBUM_THUMB from GitHub first).
Frontend / Expo Go only. Idempotent.
"""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend" / "app" / "(tabs)" / "index.tsx"
GAMEMAP = ROOT / "frontend" / "components" / "GameMap.tsx"
MARKER = "BILLBOARD_ALBUM_ROTATE_V2_OK"
BASE = "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/assets"
ALBUM_URL = BASE + "/billboard-album.jpg.b64.txt?v=1"
THUMB_URL = BASE + "/billboard-album-thumb.jpg.b64.txt?v=1"
DITTO_URL = "https://ditto.fm/the-calvin-thomas-king-album"

# --- v1 hash helper (index.tsx) -> replaced by the wall-clock helper ---
V1_HELPER_TS = """// BILLBOARD_AD_PICK: which ad a billboard shows, deterministic per
// billboard id (hash) so the mix looks random but a billboard stays
// put across reloads and the marker and popup always agree.
const billboardAdIsAlbum = (id: string) => {
  let h = 0;
  const s = String(id || '');
  for (let i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) >>> 0; }
  return (h % 2) === 1;
};"""

NEW_HELPER_TS = """// BILLBOARD_ROTATE: which ad is showing RIGHT NOW — wall-clock 30s
// bucket, same as the map marker, so the popup always matches the
// picture the player tapped. Flips every 30 seconds.
const billboardAdIsAlbumNow = () => (Math.floor(Date.now() / 30000) % 2) === 1;"""

# --- v1 hash helper (GameMap.tsx) -> replaced by the rotate function ---
V1_HELPER_JS = """    // BILLBOARD_AD_PICK: same hash as index.tsx — deterministic per
    // billboard id so the marker matches the popup.
    var billboardAdIsAlbum = function (id) {
      var s = String(id || '');
      var h = 0;
      for (var i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) >>> 0; }
      return (h % 2) === 1;
    };"""

NEW_ROTATE_JS = """    // BILLBOARD_ROTATE: current ad by wall-clock 30s bucket (same as
    // the popup). createMarker() never rebuilds an existing marker,
    // so the interval below swaps the img in the DOM every second.
    var billboardThumbNow = function () {
      return (Math.floor(Date.now() / 30000) % 2 === 1) ? ALBUM_THUMB : BILLBOARD_THUMB;
    };
    setInterval(function () {
      var now = billboardThumbNow();
      var imgs = document.querySelectorAll('img.billboard-ad-img');
      for (var i = 0; i < imgs.length; i++) {
        if (imgs[i].getAttribute('src') !== now) imgs[i].setAttribute('src', now);
      }
    }, 1000);"""

# --- popup: v0 original ---
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

# --- popup: v2 (rotating) — used for both v0 and v1 states ---
POPUP_V2 = """          {selectedMarker.type === 'billboard' && (() => {
            const isAlbum = billboardAdIsAlbumNow();
            const adUri = isAlbum ? ALBUM_AD : BILLBOARD_AD;
            const adTitle = isAlbum ? 'King Veno - The Calvin Thomas King Album' : 'Hush Music Ent.';
            const adLink = isAlbum ? '""" + DITTO_URL + """' : 'https://www.hushmusicent.com';
            const adButton = isAlbum ? 'LISTEN NOW' : 'VISIT SITE';
            const adAspect = isAlbum ? 1 : 3 / 2;
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

# --- GameMap marker branch img: v0 and v1 forms -> v2 ---
GAMEMAP_IMG_V0 = """    '<img src="' + BILLBOARD_THUMB + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +"""
GAMEMAP_IMG_V1 = """    '<img src="' + bbThumb + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +"""
GAMEMAP_IMG_V2 = """    '<img class="billboard-ad-img" src="' + billboardThumbNow() + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +"""
GAMEMAP_BBTHUMB_LINE = """  var bbThumb = billboardAdIsAlbum(m.id) ? ALBUM_THUMB : BILLBOARD_THUMB;"""


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
    idx_done = False
    if "billboardAdIsAlbumNow" in src and "ALBUM_AD" in src and POPUP_V2 in src:
        print("BILLBOARD_ALBUM_ROTATE_INDEX_ALREADY_APPLIED")
        idx_done = True
    else:
        # ALBUM_AD: add it if v1 never ran.
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
        # Helper: replace v1 hash helper with the wall-clock helper,
        # or add the wall-clock helper after ALBUM_AD.
        if V1_HELPER_TS in src:
            src = src.replace(V1_HELPER_TS, NEW_HELPER_TS, 1)
        elif "billboardAdIsAlbumNow" not in src:
            lines = src.split("\n")
            lines, ok = insert_after_line(
                lines, 'const ALBUM_AD = "data:image/jpeg;base64,', NEW_HELPER_TS, "index.tsx ALBUM_AD")
            if not ok:
                sys.exit(1)
            src = "\n".join(lines)
        # Popup: replace v0 or v1 form with v2.
        if POPUP_V2 in src:
            pass
        elif POPUP_V0 in src:
            src = src.replace(POPUP_V0, POPUP_V2, 1)
        elif "billboardAdIsAlbum(selectedMarker.data.id)" in src:
            # v1 IIFE: swap just the picker line.
            src = src.replace(
                "const isAlbum = billboardAdIsAlbum(selectedMarker.data.id);",
                "const isAlbum = billboardAdIsAlbumNow();", 1)
        else:
            print("ERROR: billboard popup anchor not found in index.tsx. Stopping without writing.")
            sys.exit(1)
        INDEX.write_text(src, encoding="utf-8")
        print("BILLBOARD_ALBUM_ROTATE_INDEX_OK")

    # ---- GameMap.tsx ----
    if not GAMEMAP.exists():
        print("ERROR: %s not found. Run from /app." % GAMEMAP)
        sys.exit(1)
    gsrc = GAMEMAP.read_text(encoding="utf-8", errors="ignore")
    if "billboardThumbNow" in gsrc and "ALBUM_THUMB" in gsrc and GAMEMAP_IMG_V2 in gsrc:
        print("BILLBOARD_ALBUM_ROTATE_GAMEMAP_ALREADY_APPLIED")
    else:
        # ALBUM_THUMB: add it if v1 never ran.
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
        # Rotate function: replace v1 hash helper, or add after ALBUM_THUMB.
        if V1_HELPER_JS in gsrc:
            gsrc = gsrc.replace(V1_HELPER_JS, NEW_ROTATE_JS, 1)
        elif "billboardThumbNow" not in gsrc:
            glines = gsrc.split("\n")
            glines, ok = insert_after_line(
                glines, '    var ALBUM_THUMB = "data:image/jpeg;base64,', NEW_ROTATE_JS.rstrip("\n"), "GameMap.tsx ALBUM_THUMB")
            if not ok:
                sys.exit(1)
            gsrc = "\n".join(glines)
        # Marker branch: drop the v1 bbThumb line, swap the img to v2.
        if GAMEMAP_BBTHUMB_LINE in gsrc:
            gsrc = gsrc.replace(GAMEMAP_BBTHUMB_LINE + "\n", "", 1)
        if GAMEMAP_IMG_V2 in gsrc:
            pass
        elif GAMEMAP_IMG_V1 in gsrc:
            gsrc = gsrc.replace(GAMEMAP_IMG_V1, GAMEMAP_IMG_V2, 1)
        elif GAMEMAP_IMG_V0 in gsrc:
            gsrc = gsrc.replace(GAMEMAP_IMG_V0, GAMEMAP_IMG_V2, 1)
        else:
            print("ERROR: billboard marker img anchor not found in GameMap.tsx. Stopping without writing.")
            sys.exit(1)
        GAMEMAP.write_text(gsrc, encoding="utf-8")
        print("BILLBOARD_ALBUM_ROTATE_GAMEMAP_OK")

    print(MARKER)


if __name__ == "__main__":
    main()
