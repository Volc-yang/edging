# CHAOS-REALISM-01 V2 independent Metal retest

Status: **technical visual chain passed; realistic art and performance gates open**. Base `93ee1a7` includes the T1 surface-winding correction. From a fresh V2 worktree, UE 5.8.3 Editor built successfully and its assembled seed-7 GameMode rendered on Apple M4 Pro Metal. Unlike V1, the overview and local captures show distinct green land, tan coast, cyan ocean/river/marsh, route and vegetation shadows. The V1 missing-surface failure is fixed in this run. Vegetation and surfaces remain built-in geometric/color proxies, so this is not photorealistic acceptance.

## Isolation and capture

- Branch `codex/chaos-realism-v2`; project `?game=/Script/EdgeWorldHost.ChaosRealismGameMode`, V2 worktree input and V2 worktree `Saved/EdgeWorldChaos/chaos-demo/world.json`. The preexisting UE preview and Worker were untouched. Old V1 worktree was clean and removed; V1 artifacts remain on DevSSD.
- InitialWorld raw SHA-256 `0fa198a9cec8a3cc9b4c5aabba02367e68e05b5e34b144df75882123c8bde629`; canonical hash `75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3`.
- Full-resolution original PNGs: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/Renders/V2/`; acknowledgement, state trace and UE log: adjacent `Logs/V2/`. `retest-index.jsonl` gives SHA-256/size for each artifact and full state digest before/after each control action.
- Captures: `tick0_overview`, `tick0_forest`, `tick0_marsh`, `tick0_route`, `tick1_route`, and `tick1_coast_shore`. The first coast camera `tick0_coast` looked out over open water and is retained as an unsuccessful framing, not evidence of shoreline visibility. The corrected coast camera at tick 1 shows beach, river mouth, marsh and sea in one view.

## State and log checks

The UE log records Metal, terrain assembly (`land_vertices=46800`, three water sections, four route segments), ecology/daylight ready and committed tick-0 observation. Validation sequences 1–4 changed only camera presentation; sequence 5 observed historical tick 0. For each, raw `world.json` SHA-256, head state hash, event hash, event count and tick matched before and after. Sequence 6 explicitly requested O1 and produced a committed tick-1 observation; the manifest moved CHAOS/tick 0/revision 0 to ONE/tick 1/revision 1. Sequences 7–8 observed historical tick 1; sequence 9 reframed the coast. Their manifest and authority fields remained unchanged. The worker therefore advanced only on explicit O1 in this run.

## Remaining gates

The rendered landscape is a colored procedural prototype with conical/spherical trees and flat water. It demonstrates world layout and Metal visibility but does not satisfy realistic assets/materials, water appearance, detailed terrain, or city continuity. No trustworthy CPU/GPU frame-time trace was captured; an FPS cap or static screenshots would not measure actual frame time. Performance remains unmeasured.
