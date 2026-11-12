# RCA — Deploy run 75e41d38-ecfd-43b8-baa9-2eeaf2b1cb1d (gta-quest-map)

## Outcome
Deploy failed at `build_image`, in the **EAS OTA update lane** (Metro bundling during `eas update`). Backend docker build is not the culprit. The old backend (run ad929fb6) keeps serving; nothing was promoted.

## Root cause (verified in eph sandbox)
Metro could not resolve a module:

```
[expo-cli] Error: Unable to resolve module ../hooks/useGameStore from /workspace/frontend/app/shootout-simulator.tsx
None of these files exist: ...
Error: update command failed.
```

`frontend/app/shootout-simulator.tsx` line 6 imports:

```ts
import { useGameStore } from '../hooks/useGameStore';
```

That path does not exist. `frontend/hooks/` contains only: `castleLevelsData.ts`, `useCastlePhysics.ts`, `useMapQueries.ts`, `useRunawayGame.ts`, `useSoundEffects.ts` — no `useGameStore`.

`useGameStore` is actually exported from **`frontend/stores/gameStore.ts`** (file present, 7283 bytes). Every other screen that uses it imports from that path, e.g.:
- `frontend/app/runaway-simulator.tsx:14` → `from '../stores/gameStore'`
- `frontend/app/car-chase.tsx:15` → `from '../stores/gameStore'`
- `frontend/app/package-grab.tsx:14` → `from '../stores/gameStore'`
- `frontend/app/casino.tsx:16` → `from '../stores/gameStore'`
- `frontend/app/castle-levels.tsx:19` → `from '../stores/gameStore'`

Only `shootout-simulator.tsx` uses the wrong `../hooks/useGameStore` path. (Note: a stale `shootout-simulator.tsx.bak` is also present in `frontend/app/` — harmless, but worth removing.)

## The fix
In `frontend/app/shootout-simulator.tsx`, change line 6 from:

```ts
import { useGameStore } from '../hooks/useGameStore';
```

to:

```ts
import { useGameStore } from '../stores/gameStore';
```

The usage at line 833 (`const { playerId, refreshPlayer } = useGameStore();`) is unchanged and matches the same destructure used in `package-grab.tsx` and `castle-levels.tsx`, so no further edits are needed.

## Verification
Applied the one-line path change in the eph sandbox (`sed` on the pulled source). Confirmed `frontend/stores/gameStore.ts` exists and exports `useGameStore`, and that the corrected import now matches every sibling screen. The unresolved-module error originates purely from the wrong import path, so this change resolves the Metro bundling failure.

## Next step
Apply the one-line fix in the source environment and re-trigger the deploy.
