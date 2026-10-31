# CHAOS-REALISM-01 E1: deterministic ecology layout

## Scope and interface

`FChaosRealismEcologyLayout::Generate` produces a fixed seed-7 vegetation layout in T1 world centimetres. It reads `FChaosRealismTerrain::Sample` for height, slope and water mask, and does not read or advance the authoritative Worker. `AChaosRealismEcology::EnsureInWorld` creates one idempotent presentation actor with HISM batches; the scene assembly task owns the call site.

The layout uses three sample zones: forest grid spacing 11 m, marsh grid spacing 6.5 m, and coastal scrub grid spacing 18 m. Cell hashes add jitter and thin plants. The four plant kinds are conifer, broadleaf, marsh reed and coastal scrub. Terrain slope and water mask filter placement. Repeated generation returns the same locations and kinds.

## Rendering and DevSSD handoff

Current meshes are UE 5.8.3 built-in cylinders, cones and spheres with simple colours. They are technical placement proxies, not realistic plant assets. HISM components let the assembly task replace meshes and materials while retaining the layout. Approved plant assets can be staged under `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/Realism01/Assets/Ecology/`; screenshots and render logs belong under `Renders/Ecology/`. No licensed ecology assets or Metal ecology screenshot were available in this task, so visual realism is unverified.

## Verification

- UE 5.8.3 `EdgeWorldHostEditor Mac Development` build succeeded.
- `edgeWorld.ChaosRealism.EcologyLayout` passed in a NullRHI Editor run on 2026-10-31. It checks deterministic count and positions, T1 sample bounds, and nonempty forest, marsh and coastal groups.
- UE 5.8.3 `EdgeWorldHost Mac Development` Game target build succeeded on 2026-10-31.

## Limits

The zones are fixed to the T1 sample, and plant meshes have no biome-specific art, wind, growth, collision or LOD tuning. This module creates visual geometry only. The final Metal scene capture and realism gate remain with the scene assembly task.
