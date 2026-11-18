#!/usr/bin/env python3
"""Street Legends frontend: Billboard album rotation.

Adds the user's Calvin Thomas King album promo as a second billboard
ad, shown RANDOMLY alongside the existing Hush Music Ent. logo art.
Each billboard deterministically picks one of the two images from its
own id (hash), so the mix looks random across the map but a given
billboard stays put across reloads and the map marker and the popup
always agree. Tapping an album billboard links to the Ditto album
page; tapping a logo billboard still links to hushmusicent.com.

What it changes:
  1. app/(tabs)/index.tsx:
     - const ALBUM_AD (album art data URI, downloaded from GitHub)
       + billboardAdIsAlbum(id) helper, inserted after BILLBOARD_AD.
     - Billboard popup becomes an IIFE that picks the ad, title, link
       and button from the billboard id: album -> ALBUM_AD, square
       aspect (keeps the QR code whole), title 'King Veno - The
       Calvin Thomas King Album', button LISTEN NOW ->
       https://ditto.fm/the-calvin-thomas-king-album ; logo ->
       BILLBOARD_AD, 3/2 aspect, 'Hush Music Ent.', VISIT SITE ->
       https://www.hushmusicent.com.
  2. components/GameMap.tsx:
     - var ALBUM_THUMB (240px album thumb data URI) + the same
       billboardAdIsAlbum helper, inserted after BILLBOARD_THUMB.
     - Billboard marker branch picks ALBUM_THUMB or BILLBOARD_THUMB
       from m.id, so the map marker matches the popup.

Does NOT touch the billboard backend, placement, or any other marker.
Frontend / Expo Go only. Idempotent.
"""
import sys
import urllib.request
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
INDEX = ROOT / "frontend" / "app" / "(tabs)" / "index.tsx"
GAMEMAP = ROOT / "frontend" / "components" / "GameMap.tsx"
MARKER = "BILLBOARD_ALBUM_OK"
BASE = "https://raw.githubusercontent.com/hushmusicent/street-legends/main/frontend/assets"
ALBUM_URL = BASE + "/billboard-album.jpg.b64.txt?v=1"
THUMB_URL = BASE + "/billboard-album-thumb.jpg.b64.txt?v=1"
DITTO_URL = "https://ditto.fm/the-calvin-thomas-king-album"

HELPER_TS = """
// BILLBOARD_AD_PICK: which ad a billboard shows, deterministic per
// billboard id (hash) so the mix looks random but a billboard stays
// put across reloads and the marker and popup always agree.
const billboardAdIsAlbum = (id: string) => {
  let h = 0;
  const s = String(id || '');
  for (let i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) >>> 0; }
  return (h % 2) === 1;
};
"""

HELPER_JS = """
    // BILLBOARD_AD_PICK: same hash as index.tsx — deterministic per
    // billboard id so the marker matches the popup.
    var billboardAdIsAlbum = function (id) {
      var s = String(id || '');
      var h = 0;
      for (var i = 0; i < s.length; i++) { h = (h * 31 + s.charCodeAt(i)) >>> 0; }
      return (h % 2) === 1;
    };
"""

POPUP_OLD = """          {selectedMarker.type === 'billboard' && (
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

POPUP_NEW = """          {selectedMarker.type === 'billboard' && (() => {
            const isAlbum = billboardAdIsAlbum(selectedMarker.data.id);
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

# GameMap marker branch: only the img src line changes (pick the thumb).
GAMEMAP_OLD_IMG = """    '<img src="' + BILLBOARD_THUMB + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +"""
GAMEMAP_NEW_IMG = """    '<img src="' + bbThumb + '" style="width:100%;height:100%;object-fit:cover;" /></div>' +"""
GAMEMAP_BRANCH_ANCHOR = """} else if (m.type === 'billboard') {
  var bbName = m.name || 'Highway';"""
GAMEMAP_BRANCH_NEW = """} else if (m.type === 'billboard') {
  var bbName = m.name || 'Highway';
  var bbThumb = billboardAdIsAlbum(m.id) ? ALBUM_THUMB : BILLBOARD_THUMB;"""


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
    """Insert insert_text right after the first line starting with
    startswith. Returns (new_lines, found)."""
    for i, line in enumerate(lines):
        if line.startswith(startswith):
            lines.insert(i + 1, insert_text)
            return lines, True
    print("ERROR: %s anchor not found (%s). File has drifted; stopping." % (label, startswith[:60]))
    return lines, False


def main():
    album_b64 = fetch_b64(ALBUM_URL, "billboard-album.jpg.b64.txt")
    thumb_b64 = fetch_b64(THUMB_URL, "billboard-album-thumb.jpg.b64.txt")

    # ---- index.tsx ----
    if not INDEX.exists():
        print("ERROR: %s not found. Run from /app." % INDEX)
        sys.exit(1)
    src = INDEX.read_text(encoding="utf-8", errors="ignore")
    if "billboardAdIsAlbum" in src and "ALBUM_AD" in src:
        print("BILLBOARD_ALBUM_INDEX_ALREADY_APPLIED")
    else:
        if 'const BILLBOARD_AD = "data:image/jpeg;base64,' not in src:
            print("ERROR: BILLBOARD_AD anchor not found in index.tsx. Stopping without writing.")
            sys.exit(1)
        if POPUP_OLD not in src:
            print("ERROR: billboard popup anchor not found in index.tsx. Stopping without writing.")
            sys.exit(1)
        lines = src.split("\n")
        album_def = 'const ALBUM_AD = "data:image/jpeg;base64,' + album_b64 + '";'
        lines, ok = insert_after_line(
            lines, 'const BILLBOARD_AD = "data:image/jpeg;base64,', album_def + HELPER_TS.rstrip("\n"), "index.tsx BILLBOARD_AD")
        if not ok:
            sys.exit(1)
        src = "\n".join(lines)
        src = src.replace(POPUP_OLD, POPUP_NEW, 1)
        INDEX.write_text(src, encoding="utf-8")
        print("BILLBOARD_ALBUM_INDEX_OK")

    # ---- GameMap.tsx ----
    if not GAMEMAP.exists():
        print("ERROR: %s not found. Run from /app." % GAMEMAP)
        sys.exit(1)
    gsrc = GAMEMAP.read_text(encoding="utf-8", errors="ignore")
    if "billboardAdIsAlbum" in gsrc and "ALBUM_THUMB" in gsrc:
        print("BILLBOARD_ALBUM_GAMEMAP_ALREADY_APPLIED")
    else:
        if 'var BILLBOARD_THUMB = "data:image/jpeg;base64,' not in gsrc:
            print("ERROR: BILLBOARD_THUMB anchor not found in GameMap.tsx. Stopping without writing.")
            sys.exit(1)
        if GAMEMAP_OLD_IMG not in gsrc:
            print("ERROR: billboard marker img anchor not found in GameMap.tsx. Stopping without writing.")
            sys.exit(1)
        if GAMEMAP_BRANCH_ANCHOR not in gsrc:
            print("ERROR: billboard marker branch anchor not found in GameMap.tsx. Stopping without writing.")
            sys.exit(1)
        glines = gsrc.split("\n")
        thumb_def = '    var ALBUM_THUMB = "data:image/jpeg;base64,' + thumb_b64 + '";'
        glines, ok = insert_after_line(
            glines, '    var BILLBOARD_THUMB = "data:image/jpeg;base64,', thumb_def + HELPER_JS.rstrip("\n"), "GameMap.tsx BILLBOARD_THUMB")
        if not ok:
            sys.exit(1)
        gsrc = "\n".join(glines)
        gsrc = gsrc.replace(GAMEMAP_BRANCH_ANCHOR, GAMEMAP_BRANCH_NEW, 1)
        gsrc = gsrc.replace(GAMEMAP_OLD_IMG, GAMEMAP_NEW_IMG, 1)
        GAMEMAP.write_text(gsrc, encoding="utf-8")
        print("BILLBOARD_ALBUM_GAMEMAP_OK")

    print(MARKER)


if __name__ == "__main__":
    main()
