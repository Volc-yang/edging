# CHAOS-REALISM-01 independent Metal review (V1)

Status: **partial / visual realism gate failed**. UE 5.8.3 Editor compiled and the assembled seed-7 scene rendered on Apple M4 Pro Metal. The forest, marsh, coast and route camera captures are visible, but the ground and water read as a nearly uniform blue surface, and vegetation remains obvious cone/sphere/reed proxies. These images do not establish a realistic world or visually distinguish river, marsh and coast. The earlier all-black standalone terrain preview is resolved for the assembled mode only.

## Run and isolation

- Branch `codex/chaos-realism-v1`, base `95601b6`; project from this worktree using `?game=/Script/EdgeWorldHost.ChaosRealismGameMode`.
- Input `models/chaos/initial_world_seed7.json`: raw SHA-256 `0fa198a9cec8a3cc9b4c5aabba02367e68e05b5e34b144df75882123c8bde629`; canonical initial hash `75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3`.
- Isolated worker state: this worktree's `engine_platforms/unreal/EdgeWorldHost/Saved/EdgeWorldChaos/chaos-demo/world.json`. Existing Chaos preview processes and their state were untouched.
- UE log records Metal on Apple M4 Pro, `land_vertices=46800`, `water_sections=3`, `route_segments=4`, `hidden_proxy_components=203`, terrain/ecology/daylight ready, and committed tick-0 observation.
- Large artifacts: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/Renders/V1/` and `Logs/V1/`. `index.jsonl` records SHA-256 for each capture and log plus before/after worker state digests.

## Authoritative-state checks

Validation commands 1–4 moved the camera through forest, marsh, coast and route. Command 5 observed historical tick 0. Each acknowledgement was `applied=true`; across each operation the raw manifest SHA-256, head state hash, event hash, event count and tick remained identical. Thus these presentation and read-only actions did not advance the worker in this run.

Command 6 explicitly requested O1. The log records committed observation at tick 1; the manifest changed from CHAOS/tick 0/revision 0 to ONE/tick 1/revision 1. Commands 7–8 observed tick 1; again the manifest SHA-256 and all authority fields remained stable. Exact values and action boundaries are in `index.jsonl`; command acknowledgements and full UE log are on DevSSD.

## Visual and performance gates

The Metal screenshots are non-black and show populated geometry. In the marsh camera, individual reeds, trees and flat blue terrain are visible. The coast and route captures likewise fail realistic material and land/water separation. There are no authorized realistic foliage, soil, water or city assets in this run. **Photorealistic acceptance remains failed.**

The validation control supports a frame cap, not actual frame-time measurement. No trustworthy CPU/GPU frame-time trace was captured; **performance acceptance remains unmeasured**. The V1 instance should be profiled after material/asset correction, with the same four cameras and unchanged worker state checks.
