#!/usr/bin/env python3
"""Street Legends frontend patch: speed up map-entity loading at startup.

Symptom: map tiles load promptly but enemies/territories/restaurants/markers
take a long time to appear. Root causes (see useMapQueries.ts):
  (a) useMapEntities is ONE query whose queryFn awaits updatePlayerPosition
      FIRST, then Promise.allSettled over 14 (live 16) entity calls and only
      returns when ALL settle - every marker type waits on the SLOWEST call.
      The axios timeout is 30s, so one hung endpoint can hold all markers
      for up to 30s.
  (b) The activity-centers call in the same batch goes backend -> OpenStreetMap
      Overpass (external HTTP, slow on cache miss) - the most likely slowest
      call, and it gates every other type.
This patch (frontend-only, touches frontend/hooks/useMapQueries.ts only):
  1. Position update becomes fire-and-forget (never awaited before the batch).
  2. EACH entity call is raced against a 5s timeout: a hung/slow endpoint
     resolves to [] for its type instead of holding the whole batch; the slow
     type fills in on the next refetch (5-min interval / focus refetch).
     5s was chosen because a healthy entity call on this backend answers in
     well under 1s on decent connectivity and ~1-2s on 4G, so 5s gives 2-5x
     headroom over a slow-but-healthy call while cutting the 30s tail by 6x.
  3. Entities query retry 2 -> 0 (a retry would double/triple a slow first
     load; the 5-minute refetch is the retry). NOTE: as coded the queryFn
     never rejects (position update is catch-swallowed, allSettled never
     rejects), so retry is nearly inert today - this is hygiene, not the fix.
Deliberately NOT done: splitting the batch into per-type queries so fast
types render early. That would change the MapEntitiesData shape and the
index.tsx memo contract (14 derived memos + store sync + mapMarkers deps)
on a live file that has drifted far from the snapshot - regression risk.
The 5s cap bounds the worst case instead. Split-out is a follow-up option.
Does NOT change refetchInterval, staleTime, query keys, activity-centers
wiring, or any backend code. Does NOT touch GameMap.tsx or index.tsx.

Marker: MAP_ENTITIES_FAST_OK (or MAP_ENTITIES_FAST_PARTIAL if a part warns).
Idempotent: rerun prints ALREADY_APPLIED for every part, file unchanged.
"""
import re
import sys
from pathlib import Path

ROOT = Path("/app")
HOOK = ROOT / "frontend/hooks/useMapQueries.ts"

ENTITY_TIMEOUT_MS = 5000

HELPER = """
// Slowest-call cap: no single entity call may hold up the whole batch.
// A call that has not answered within ENTITY_TIMEOUT_MS resolves to [] for
// its type; the type fills in on the next refetch. The underlying request
// keeps running (no abort) and its late result is simply ignored.
const ENTITY_TIMEOUT_MS = 5000;
const withTimeout = <T,>(promise: Promise<T>): Promise<T> =>
  Promise.race([
    promise,
    new Promise<T>((resolve) => {
      setTimeout(() => resolve([] as unknown as T), ENTITY_TIMEOUT_MS);
    }),
  ]);
"""


def delta(s):
    return (s.count("{"), s.count("}"), s.count("("), s.count(")"),
            s.count("["), s.count("]"))


def main():
    landed = []
    warned = []
    if not HOOK.exists():
        print("WARNING: frontend/hooks/useMapQueries.ts not found - no speedup applied")
        print("MAP_ENTITIES_FAST_PARTIAL:")
        return 0
    src = HOOK.read_text(errors="ignore")
    orig = src
    odelta = delta(src)

    # ---------- Part 1: withTimeout helper (after roundPosition) ----------
    if "const withTimeout" in src:
        print("MAP_ENTITIES_FAST_HELPER_ALREADY_APPLIED")
        landed.append("helper")
    else:
        m = re.search(
            r"(const roundPosition = \(lat: number, lng: number\) => \(\{\n"
            r"  lat: Math\.round\(lat \* 200\) / 200, // ~500m grid\n"
            r"  lng: Math\.round\(lng \* 200\) / 200,\n"
            r"\}\);)",
            src,
        )
        if m:
            src = src[: m.end()] + "\n" + HELPER.rstrip("\n") + src[m.end():]
            print("MAP_ENTITIES_FAST_HELPER_OK")
            landed.append("helper")
        else:
            m2 = re.search(r"// Query keys factory for consistency", src)
            if m2:
                src = src[: m2.start()] + HELPER.strip("\n") + "\n\n" + src[m2.start():]
                print("MAP_ENTITIES_FAST_HELPER_OK (inserted before query-keys factory)")
                landed.append("helper")
            else:
                print("WARNING: roundPosition / query-keys anchor not found - "
                      "withTimeout helper NOT added (per-call timeouts cannot work)")
                warned.append("helper")

    # ---------- Part 2: fire-and-forget position update ----------
    if re.search(r"^[ \t]*updatePlayerPosition\(playerId, \{ latitude, longitude \}\)\.catch\(\(\) => \{\}\);",
                 src, re.M):
        print("MAP_ENTITIES_FAST_POSITION_ALREADY_APPLIED")
        landed.append("position")
    else:
        m = re.search(
            r"([ \t]*)await updatePlayerPosition\(playerId, \{ latitude, longitude \}\)\.catch\(\(\) => \{\}\);",
            src,
        )
        if m:
            src = src[: m.start()] + m.group(1) + (
                "// Update position in the background - do not block entity loading on it\n"
                + m.group(1)
                + "updatePlayerPosition(playerId, { latitude, longitude }).catch(() => {});"
            ) + src[m.end():]
            # Drop the now-stale "Update position first" comment if present above it.
            src = src.replace(
                "      // Update position first\n"
                "      // Update position in the background - do not block entity loading on it",
                "      // Update position in the background - do not block entity loading on it",
            )
            print("MAP_ENTITIES_FAST_POSITION_OK")
            landed.append("position")
        else:
            print("WARNING: awaited updatePlayerPosition anchor not found - "
                  "position update may still block the entity batch")
            warned.append("position")

    # ---------- Part 3: wrap every call in the allSettled batch ----------
    m = re.search(r"const results = await Promise\.allSettled\(\[", src)
    if not m:
        print("WARNING: Promise.allSettled anchor not found - per-call timeouts NOT added")
        warned.append("batch")
    else:
        start = m.end()
        # Find the matching close of the array: the first line that is exactly "]);"
        # at the same indent as the const statement.
        close = re.search(r"\n[ \t]*\]\);", src[start:])
        if not close:
            print("WARNING: Promise.allSettled close anchor not found - "
                  "per-call timeouts NOT added")
            warned.append("batch")
        else:
            body_start, body_end = start, start + close.start()
            body = src[body_start:body_end]
            lines = body.split("\n")
            wrapped = 0
            already = 0
            skipped = []
            new_lines = []
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    new_lines.append(line)
                    continue
                if "withTimeout(" in line:
                    already += 1
                    new_lines.append(line)
                    continue
                # Bare single-line call: name(args), with balanced parens.
                if (re.match(r"^[A-Za-z_$][\w$]*\(.*\),$", stripped)
                        and stripped.count("(") == stripped.count(")")):
                    indent = line[: len(line) - len(line.lstrip())]
                    inner = stripped[:-1]  # drop trailing comma
                    new_lines.append(indent + "withTimeout(" + inner + "),")
                    wrapped += 1
                else:
                    # Multi-line call or non-call line: leave alone, flag it.
                    if stripped.endswith("(") or "(" in stripped:
                        skipped.append(stripped[:60])
                    new_lines.append(line)
            if wrapped == 0 and already == 0:
                print("WARNING: no entity calls found inside Promise.allSettled - "
                      "per-call timeouts NOT added")
                warned.append("batch")
            else:
                src = src[:body_start] + "\n".join(new_lines) + src[body_end:]
                if wrapped:
                    print(f"MAP_ENTITIES_FAST_BATCH_OK ({wrapped} call(s) wrapped, "
                          f"{already} already wrapped)")
                else:
                    print(f"MAP_ENTITIES_FAST_BATCH_ALREADY_APPLIED ({already} call(s) wrapped)")
                landed.append("batch")
                for s in skipped:
                    print(f"WARNING: multi-line call left unwrapped (still in batch): {s}")
                    warned.append("batch-multiline")

    # ---------- Part 4: entities query retry 2 -> 0 (scoped to useMapEntities) --
    m = re.search(r"export const useMapEntities", src)
    if not m:
        print("WARNING: useMapEntities anchor not found - retry NOT changed")
        warned.append("retry")
    else:
        region_start = m.start()
        region_end = src.find("interface UsePlayerDataOptions", region_start)
        if region_end == -1:
            region_end = len(src)
        region = src[region_start:region_end]
        if re.search(r"retry: 0[,\n]", region):
            print("MAP_ENTITIES_FAST_RETRY_ALREADY_APPLIED")
            landed.append("retry")
        else:
            rm = re.search(r"retry: 2,", region)
            if rm:
                region = (region[: rm.start()]
                          + "retry: 0, // no retry - a slow first load must not be "
                            "retried; the 5-minute refetch is the retry"
                          + region[rm.end():])
                src = src[:region_start] + region + src[region_end:]
                print("MAP_ENTITIES_FAST_RETRY_OK")
                landed.append("retry")
            else:
                print("WARNING: retry: 2 anchor not found inside useMapEntities - "
                      "retry NOT changed")
                warned.append("retry")

    # ---------- Write (balance-guarded) ----------
    # Guard: the patched file must be pairwise balanced, and the change in
    # each bracket count must itself be balanced (balanced code added may
    # legitimately RAISE the counts - e.g. the helper and withTimeout(...)
    # wrappers add brackets - so exact equality with the original is wrong).
    ndelta = delta(src)
    balanced = (
        ndelta[0] == ndelta[1] and ndelta[2] == ndelta[3] and ndelta[4] == ndelta[5]
        and all((ndelta[i] - odelta[i]) == (ndelta[i + 1] - odelta[i + 1])
                for i in (0, 2, 4))
    )
    if not balanced:
        print("WARNING: balance changed - useMapQueries.ts NOT written")
        print("MAP_ENTITIES_FAST_PARTIAL: " + ",".join(landed))
        return 0
    if src != orig:
        HOOK.write_text(src)
    if warned:
        print("MAP_ENTITIES_FAST_PARTIAL: " + ",".join(landed))
    else:
        print("MAP_ENTITIES_FAST_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
