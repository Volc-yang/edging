# H-LIGHT-01 preparation

Historical preparation record. Build, Metal and live Genesis checks were
subsequently authorized and completed; current results are in `report.md`.
At preparation time H1f owned build/GPU until coordination explicitly released them.
Base `e577ac2a2fd28a86c430f156bf0eb5cef32fe000`, worktree
`.worktrees/home-runtime-lighting`, branch `codex/home-runtime-lighting`.

The candidate explicitly sets the runtime directional light to Movable before
setting its intensity. Sky light, geometry mobility, collisions, exposure,
materials, world state and viewport synchronization are unchanged.

`edgeworld.DumpLightingEvidence` is an on-demand console evidence entry. It
logs the actual world `NumLightingUnbuiltObjects`, directional/sky light names
and actual mobility, then invokes the engine's `DumpUnbuiltLightInteractions`.
It does not run automatically or advance the world. The native dump flushes
render commands, so it must not be inserted into H1f's controlled matrix.
Run it after a settled visible frame and repeat at tick 0/2 and recovery.
The numeric count and interaction dump supplement visible images; absence of
screen text alone is insufficient. Screen messages must remain enabled.

## Pending sequential evidence protocol

1. Wait for explicit build/GPU release from coordination. Snapshot UE, worker
   and reporter processes; use independent raw evidence/UserDir on DevSSD.
2. Build a baseline with the same read-only evidence command but **without**
   the candidate directional `SetMobility(Movable)` line. This is the approved
   product baseline plus instrumentation, not an old H1e binary. Record exact
   source and binary SHA-256, official build log and exit, command line, real
   UE/worker PIDs, engine initialization and first observed image.
3. Save baseline Metal tick 0/2 images at fixed camera/exposure/resolution;
   invoke the evidence command after frames settle. Confirm actual default
   Stationary directional mobility and identify every primitive in the native
   unbuilt interaction list. If it does not support the hypothesized cause,
   return evidence to coordination before expanding scope.
4. Restore the one candidate line, rebuild and identify the exact new binary.
   Run the same scene and exit mode, using fresh independent state. Capture
   the same images and evidence command at tick 0/2. Require actual unbuilt
   count zero and no remaining unbuilt interactions, with normal HUD, floor,
   nodes and visible lighting; preserve all warnings and failed attempts.
5. Per world, hash all authority files before/after history and camera actions,
   close, reopen the same UserDir and verify recovery with no Advance. Record
   every actual UE exit code and exact process cleanup. Never compare fresh
   worlds' checkpoint bytes as a recovery invariant.
6. Keep default-thread reliability separate. The same declared exit mode
   must be used before/after; no H1f modifications or conclusions are inferred.
   Archive any crash/reporter identity before targeted cleanup.

Only `git diff --check` and installed-source API inspection have been performed
so far. No build success, warning removal, visual result or read-only runtime
pass is claimed. Final scope/PR will include actual evidence and limitations.
