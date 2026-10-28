"""Street Legends FRONTEND: stop starting in New York City.
Run from repo root: python3 frontend/patch-no-nyc.py
Idempotent - safe to re-run.
NOTE: this is a FRONTEND change — after applying, rebuild + upload a new
AAB to Play internal testing. Backend Deploy alone does NOT ship it.

WHY the game keeps opening in NYC (Times Square, 40.7580, -73.9855):
frontend/app/(tabs)/index.tsx hardcodes NYC as the fallback in THREE
places, and GPS first fix on a cold start routinely takes >8 seconds:
1. An 8-second timer forces NYC if location init is slow.
2. Permission-denied path forces NYC AND saves NYC to the server as the
   player's position.
3. Error catch forces NYC and does NOT start live tracking, so the map
   stays stranded in NYC until the app is restarted.

FIX: all three fallbacks now use the player's last saved server position
(their real area — Toledo for this player) instead of a hardcoded demo
city, never save a fake position to the server, and always start live
tracking so the map corrects itself the moment GPS locks in. The 8s
timer becomes 20s (GPS first fix needs the room) and also uses the
last-known fallback instead of NYC.
"""
import sys
from pathlib import Path

SCREEN = Path("frontend/app/(tabs)/index.tsx")

HELPER = """  // Fallback when live GPS is unavailable: use the player's last saved
  // server position (their real area), NEVER a hardcoded demo city.
  // Then start live tracking so the map corrects itself when GPS locks in.
  const fallbackToLastKnown = async () => {
    try {
      if (playerId) {
        const p: any = await getPlayer(playerId);
        const pos = p?.position;
        if (pos?.latitude && pos?.longitude) {
          setCurrentPosition({ latitude: pos.latitude, longitude: pos.longitude });
          if (p) setPlayer(p);
        }
      }
    } catch {}
    setLoading(false);
    startLocationTracking();
  };

"""

TIMER_OLD = """    // Fallback: If loading takes too long, use default location
    const fallbackTimer = setTimeout(() => {
      if (loading) {
        console.log('[Map] Location init timeout, using default');
        const defaultPos = { latitude: 40.7580, longitude: -73.9855 };
        setCurrentPosition(defaultPos);
        setLoading(false);
      }
    }, 8000);"""
TIMER_NEW = """    // Fallback: If live GPS is slow, use the player's last known position
    // (never a hardcoded demo city) and start tracking so it corrects.
    const fallbackTimer = setTimeout(() => {
      if (loading) {
        console.log('[Map] Location init slow, using last known position');
        fallbackToLastKnown();
      }
    }, 20000);"""

PERM_OLD = """      if (status !== 'granted') {
        // Use default location (New York) for demo when permission denied
        const defaultPos = { latitude: 40.7580, longitude: -73.9855 };
        setCurrentPosition(defaultPos);
        if (playerId) {
          updatePlayerPosition(playerId, defaultPos).catch(console.error);
          getPlayer(playerId).then(setPlayer).catch(console.error);
        }
        setLoading(false);
        startLocationTracking();
        return;
      }"""
PERM_NEW = """      if (status !== 'granted') {
        // No GPS permission: use last known position, never a fake city.
        // Do NOT save a fallback to the server.
        await fallbackToLastKnown();
        return;
      }"""

CATCH_OLD = """    } catch (error: any) {
      // Fallback to default location on error
      const defaultPos = { latitude: 40.7580, longitude: -73.9855 };
      setCurrentPosition(defaultPos);
      setLoading(false);
    }"""
CATCH_NEW = """    } catch (error: any) {
      // GPS failed: fall back to last known position and start tracking so
      // the map corrects itself when GPS locks in.
      await fallbackToLastKnown();
    }"""


def main():
    if not SCREEN.exists():
        print(f"ERROR: {SCREEN} not found. Run from repo root.")
        sys.exit(1)
    src = SCREEN.read_text()
    if "40.7580" not in src and "fallbackToLastKnown" in src:
        print("SKIP: no NYC fallback left (already patched)")
        print("NO_NYC_OK")
        return
    if "40.7580" not in src:
        print("WARNING: no NYC coordinates found — file may already differ")
        print("NO_NYC_OK")
        return

    if "fallbackToLastKnown" not in src:
        anchor = "  const initializeLocation = async () => {"
        if src.count(anchor) != 1:
            print(f"ERROR: initializeLocation anchor matched {src.count(anchor)}x.")
            sys.exit(1)
        src = src.replace(anchor, HELPER + anchor, 1)
        print("OK: last-known fallback helper added")
    else:
        print("SKIP: helper already present")

    for old, new, label in [
        (TIMER_OLD, TIMER_NEW, "8s timer"),
        (PERM_OLD, PERM_NEW, "permission-denied"),
        (CATCH_OLD, CATCH_NEW, "error catch"),
    ]:
        if new in src:
            print(f"SKIP: {label} already patched")
        elif src.count(old) == 1:
            src = src.replace(old, new, 1)
            print(f"OK: {label} no longer forces NYC")
        else:
            print(f"WARNING: {label} anchor matched {src.count(old)}x — skipping")

    SCREEN.write_text(src)
    remaining = src.count("40.7580")
    print(f"NYC coordinates remaining in file: {remaining}")
    print("NO_NYC_OK")


if __name__ == "__main__":
    main()
