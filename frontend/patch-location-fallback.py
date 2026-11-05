#!/usr/bin/env python3
"""Street Legends: location fallback — never wait forever for GPS.

Problem: the app opens (tab bar renders) but sticks forever on
"Finding your location..." and never shows the map. The bundle loads,
so the blocker moved from code to location acquisition: the location
request never resolves and nothing ever times out. (The snapshot's
mount effect has an 8s timer, but it reads a stale mount-time `loading`
value and applies only the fixed default — it never tries last-known,
never shows a note, never offers a retry, and never starts tracking,
so a later live fix can never arrive.)

Fix (frontend/app/(tabs)/index.tsx only, Expo Go):
 A. States: locationFallbackUsed flag + loadingRef (mirrors `loading`,
    so the safety timer reads the CURRENT value, not a stale closure).
 B. applyLocationFallback helper: last known position first
    (Location.getLastKnownPositionAsync), then the fixed default
    Times Square (40.7580, -73.9855); sets the fallback flag, clears
    loading, and starts tracking so a later live fix still arrives.
 C. Mount-effect safety timer: 10s, ref-checked; if still loading,
    applies the fallback. Replaces the old 8s timer when present,
    otherwise inserts one after initializeLocation().
 D. initializeLocation: getCurrentPositionAsync is raced against a
    10s timeout (typed Promise<null>); on timeout the fallback runs.
    Permission denied goes straight to fallback + note, never spins.
    A live fix clears the fallback flag.
 E. Watch callback clears the fallback flag when a live fix arrives.
 F. On-map banner + RETRY: when the fallback is used, the map shows
    "Location unavailable — showing last known area. Tap to retry."
    with a Retry button that re-runs initializeLocation.
    The permission flow itself is untouched (no re-request loop).
Each part is guarded: a missed anchor prints a WARNING and skips only
that part. Second run prints ALREADY_APPLIED and changes nothing."""
import re
import sys
from pathlib import Path

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/app")
CHAR = ROOT / "frontend/app/(tabs)/index.tsx"
MARKER = "LOCATION_FALLBACK"

DEFAULT_POS = "{ latitude: 40.7580, longitude: -73.9855 }"


def delta(s):
    return (s.count("{") - s.count("}"), s.count("(") - s.count(")"))


def insert_after_line(src, anchor_line, new_text):
    """Insert new_text (with its own trailing newline) right after the
    first line whose stripped content equals anchor_line. Returns
    (new_src, True) or (src, False)."""
    lines = src.split("\n")
    for i, ln in enumerate(lines):
        if ln.strip() == anchor_line.strip():
            lines.insert(i + 1, new_text)
            return "\n".join(lines), True
    return src, False


def main():
    if not CHAR.exists():
        print("WARNING: index.tsx not found - nothing changed")
        return 1
    src = CHAR.read_text(errors="ignore")
    orig = delta(src)
    char_orig = src
    landed = []

    # A. States: fallback flag + loading ref (mirrors `loading`).
    if "locationFallbackUsed" in src:
        print("LOCATION_FALLBACK_STATES_ALREADY_APPLIED"); landed.append("states")
    elif "loadingRef" in src:
        print("WARNING: loadingRef already exists but locationFallbackUsed does not - states NOT added (manual check needed)")
    else:
        old = "  const [loading, setLoading] = useState(true);"
        new = ("  const [loading, setLoading] = useState(true);\n"
               "  const [locationFallbackUsed, setLocationFallbackUsed] = useState(false);\n"
               "  const loadingRef = useRef(true);\n"
               "  useEffect(() => { loadingRef.current = loading; }, [loading]);")
        if old in src:
            src = src.replace(old, new, 1)
            print("LOCATION_FALLBACK_STATES_OK"); landed.append("states")
        else:
            print("WARNING: loading state anchor not found - fallback flag NOT added")

    # Helper: last known first, then Times Square; clears loading, starts tracking.
    if "applyLocationFallback" in src:
        print("LOCATION_FALLBACK_HELPER_ALREADY_APPLIED"); landed.append("helper")
    else:
        helper = (
            "  // LOCATION_FALLBACK_HELPER: last known position first, then Times Square.\n"
            "  const applyLocationFallback = async () => {\n"
            "    let fallbackPos = " + DEFAULT_POS + ";\n"
            "    try {\n"
            "      const lastKnown = await Location.getLastKnownPositionAsync();\n"
            "      if (lastKnown) {\n"
            "        fallbackPos = { latitude: lastKnown.coords.latitude, longitude: lastKnown.coords.longitude };\n"
            "      }\n"
            "    } catch {}\n"
            "    setCurrentPosition(fallbackPos);\n"
            "    setLocationFallbackUsed(true);\n"
            "    setLoading(false);\n"
            "    startLocationTracking();\n"
            "  };\n\n")
        anchor = "  const initializeLocation = async () => {"
        if anchor in src:
            src = src.replace(anchor, helper + anchor, 1)
            print("LOCATION_FALLBACK_HELPER_OK"); landed.append("helper")
        else:
            print("WARNING: initializeLocation anchor not found - fallback helper NOT added")

    # B. Mount-effect safety timer: 10s, ref-checked.
    if "LOCATION_FALLBACK_TIMER" in src:
        print("LOCATION_FALLBACK_TIMER_ALREADY_APPLIED"); landed.append("timer")
    else:
        new_timer = (
            "    // LOCATION_FALLBACK_TIMER: if location still has not resolved after 10s,\n"
            "    // stop waiting (last known position first, then Times Square).\n"
            "    const fallbackTimer = setTimeout(() => {\n"
            "      if (loadingRef.current) {\n"
            "        console.log('[Map] Location init timeout, using fallback');\n"
            "        applyLocationFallback();\n"
            "      }\n"
            "    }, 10000);")
        old_block = (
            "    // Fallback: If loading takes too long, use default location\n"
            "    const fallbackTimer = setTimeout(() => {\n"
            "      if (loading) {\n"
            "        console.log('[Map] Location init timeout, using default');\n"
            "        const defaultPos = { latitude: 40.7580, longitude: -73.9855 };\n"
            "        setCurrentPosition(defaultPos);\n"
            "        setLoading(false);\n"
            "      }\n"
            "    }, 8000);")
        if old_block in src:
            src = src.replace(old_block, new_timer, 1)
            print("LOCATION_FALLBACK_TIMER_OK"); landed.append("timer")
        else:
            m = re.search(r"const fallbackTimer = setTimeout\(\(\) => \{.*?\}, \d+\);",
                          src, re.DOTALL)
            if m:
                src = src[:m.start()] + new_timer + src[m.end():]
                print("LOCATION_FALLBACK_TIMER_OK"); landed.append("timer")
            elif src.count("    initializeLocation();") == 1:
                src, ok = insert_after_line(
                    src, "initializeLocation();",
                    "\n" + new_timer)
                if ok:
                    print("LOCATION_FALLBACK_TIMER_OK"); landed.append("timer")
                else:
                    print("WARNING: mount-effect anchor not found - safety timer NOT added")
            else:
                print("WARNING: mount-effect anchor not found - safety timer NOT added")

    # C. Race the initial GPS fix against a 10s timeout.
    if "LOCATION_FALLBACK_RACE" in src:
        print("LOCATION_FALLBACK_RACE_ALREADY_APPLIED"); landed.append("race")
    else:
        old = (
            "      // Get initial position quickly with balanced accuracy\n"
            "      const location = await Location.getCurrentPositionAsync({\n"
            "        accuracy: Location.Accuracy.Balanced,\n"
            "      });")
        new = (
            "      // Get initial position quickly with balanced accuracy (10s cap).\n"
            "      // LOCATION_FALLBACK_RACE\n"
            "      const location = await Promise.race([\n"
            "        Location.getCurrentPositionAsync({\n"
            "          accuracy: Location.Accuracy.Balanced,\n"
            "        }),\n"
            "        new Promise<null>((resolve) => setTimeout(() => resolve(null), 10000)),\n"
            "      ]);\n"
            "      if (!location) {\n"
            "        // Timed out with no fix: last known position, then Times Square.\n"
            "        await applyLocationFallback();\n"
            "        return;\n"
            "      }")
        if old in src:
            src = src.replace(old, new, 1)
            print("LOCATION_FALLBACK_RACE_OK"); landed.append("race")
        else:
            print("WARNING: getCurrentPositionAsync anchor not found - GPS race NOT added")

    # D1. Permission denied: straight to fallback + note, never spin.
    if "LOCATION_FALLBACK_DENIED" in src:
        print("LOCATION_FALLBACK_DENIED_ALREADY_APPLIED"); landed.append("denied")
    else:
        old = (
            "        // Use default location (New York) for demo when permission denied\n"
            "        const defaultPos = { latitude: 40.7580, longitude: -73.9855 };\n"
            "        setCurrentPosition(defaultPos);")
        new = (
            "        // Use default location (New York) for demo when permission denied\n"
            "        const defaultPos = { latitude: 40.7580, longitude: -73.9855 };\n"
            "        setCurrentPosition(defaultPos);\n"
            "        setLocationFallbackUsed(true); // LOCATION_FALLBACK_DENIED")
        if old in src:
            src = src.replace(old, new, 1)
            print("LOCATION_FALLBACK_DENIED_OK"); landed.append("denied")
        else:
            print("WARNING: permission-denied anchor not found - denied path NOT flagged (default still applies, but no note)")

    # D2. Catch path: flag the fallback and start tracking so a later live fix arrives.
    if "LOCATION_FALLBACK_CATCH" in src:
        print("LOCATION_FALLBACK_CATCH_ALREADY_APPLIED"); landed.append("catch")
    else:
        old = (
            "      // Fallback to default location on error\n"
            "      const defaultPos = { latitude: 40.7580, longitude: -73.9855 };\n"
            "      setCurrentPosition(defaultPos);\n"
            "      setLoading(false);")
        new = (
            "      // Fallback to default location on error\n"
            "      const defaultPos = { latitude: 40.7580, longitude: -73.9855 };\n"
            "      setCurrentPosition(defaultPos);\n"
            "      setLocationFallbackUsed(true); // LOCATION_FALLBACK_CATCH\n"
            "      setLoading(false);\n"
            "      startLocationTracking();")
        if old in src:
            src = src.replace(old, new, 1)
            print("LOCATION_FALLBACK_CATCH_OK"); landed.append("catch")
        else:
            print("WARNING: error-fallback anchor not found - catch path NOT flagged (default still applies, but no note/tracking)")

    # D3. Live fix clears the fallback flag.
    if "LOCATION_FALLBACK_LIVE" in src:
        print("LOCATION_FALLBACK_LIVE_ALREADY_APPLIED"); landed.append("live")
    else:
        src, ok = insert_after_line(
            src, "setCurrentPosition(position);",
            "      setLocationFallbackUsed(false); // LOCATION_FALLBACK_LIVE")
        if ok:
            print("LOCATION_FALLBACK_LIVE_OK"); landed.append("live")
        else:
            print("WARNING: live-position anchor not found - fallback flag NOT cleared on live fix")

    # E. Watch callback clears the fallback flag when a live fix arrives.
    if "LOCATION_FALLBACK_WATCH" in src:
        print("LOCATION_FALLBACK_WATCH_ALREADY_APPLIED"); landed.append("watch")
    else:
        src, ok = insert_after_line(
            src, "setCurrentPosition(newPos);",
            "          setLocationFallbackUsed(false); // LOCATION_FALLBACK_WATCH")
        if ok:
            print("LOCATION_FALLBACK_WATCH_OK"); landed.append("watch")
        else:
            print("WARNING: watch-position anchor not found - fallback flag NOT cleared by live tracking")

    # F1. Retry function (re-runs the raced init; banner only shows post-fallback).
    if "retryLocation" in src:
        print("LOCATION_FALLBACK_RETRY_ALREADY_APPLIED"); landed.append("retry")
    else:
        retry = (
            "  // LOCATION_FALLBACK: manual retry from the on-map banner.\n"
            "  const retryLocation = () => {\n"
            "    setLocationFallbackUsed(false);\n"
            "    initializeLocation();\n"
            "  };\n\n")
        anchor = "  const startLocationTracking = async () => {"
        if anchor in src:
            src = src.replace(anchor, retry + anchor, 1)
            print("LOCATION_FALLBACK_RETRY_OK"); landed.append("retry")
        else:
            print("WARNING: startLocationTracking anchor not found - retry function NOT added")

    # F2. On-map banner + Retry button (renders only while the fallback is in use).
    if "locationFallbackBanner" in src:
        print("LOCATION_FALLBACK_BANNER_ALREADY_APPLIED"); landed.append("banner")
    else:
        banner = (
            "      {locationFallbackUsed && currentPosition && (\n"
            "        <View style={styles.locationFallbackBanner}>\n"
            "          <Text style={styles.locationFallbackText}>Location unavailable — showing last known area. Tap to retry.</Text>\n"
            "          <TouchableOpacity style={styles.retryButton} onPress={retryLocation}>\n"
            "            <Text style={styles.retryText}>Retry location</Text>\n"
            "          </TouchableOpacity>\n"
            "        </View>\n"
            "      )}\n")
        anchor = "      <SafeAreaView style={styles.hud}>"
        if anchor in src:
            src = src.replace(anchor, banner + anchor, 1)
            print("LOCATION_FALLBACK_BANNER_OK"); landed.append("banner")
        else:
            print("WARNING: HUD anchor not found - fallback banner NOT added")

    # F3. Banner styles.
    if "locationFallbackBanner:" in src:
        print("LOCATION_FALLBACK_STYLES_ALREADY_APPLIED"); landed.append("styles")
    else:
        old = "  loadingText: { color: '#5F6368', marginTop: 12, fontSize: 14 },"
        new = (old + "\n"
               "  locationFallbackBanner: { position: 'absolute', bottom: 84, left: 12, right: 12, backgroundColor: 'rgba(255,255,255,0.95)', borderRadius: 10, padding: 10, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', zIndex: 5 },\n"
               "  locationFallbackText: { flex: 1, color: '#5F6368', fontSize: 13, marginRight: 8 },")
        if old in src:
            src = src.replace(old, new, 1)
            print("LOCATION_FALLBACK_STYLES_OK"); landed.append("styles")
        else:
            print("WARNING: loadingText style anchor not found - banner styles NOT added (banner would render unstyled)")

    if delta(src) != orig:
        print("WARNING: balance changed - index.tsx NOT written")
        return 1
    if src == char_orig:
        if "applyLocationFallback" in src and "LOCATION_FALLBACK_TIMER" in src:
            print("LOCATION_FALLBACK_ALREADY_APPLIED")
        else:
            print("LOCATION_FALLBACK_PARTIAL: " + ",".join(landed))
        return 0
    CHAR.write_text(src)
    if len(landed) == 11:
        print("LOCATION_FALLBACK_OK")
    else:
        print("LOCATION_FALLBACK_PARTIAL: " + ",".join(landed))
    return 0

if __name__ == "__main__":
    sys.exit(main())
