# H1c view-target differential

Base: `6fbfd437a7fb7e66cbecd2c59ec069e65356b36c` (H1b PR #57 integrated).
Owner: `codex/g3-viewtarget-differential`; isolated worktree of the same name.
The original worktree, worker authority and UE installation are read-only inputs.

H1b reproduced the assertion with the causal Actor disabled. H1a predates the
new HUD and explicit SpectatorPawn setting. Test explicit camera view-target
assignment before blaming either newer setting. This is diagnosis, not a fix.

Both arms disable worker environment variables and the causal Actor spawn.
Both retain the camera actor, lights, HUD, controller and pawn. Arm A performs
the original `SetViewTarget(Camera)` call; arm B skips only that call. One
diagnostic binary serves both arms. Temporary switches are removed from source
before delivery; the exact patch and source hashes remain in raw evidence.

Run A1/B1/A2/B2 serially on the GPU. Prebuild the Editor target before launching.
Each run uses an independent UserDir, absolute UE log and stdout log. Record
build result, engine initialization, map/GameMode and scene configuration,
expected worker absence, first observed rendered image, passive interval,
close-call timing, process snapshots, exit code and raw SHA-256 index. Wait at
least 180 seconds after engine initialization before the close attempt. Record
CUA observation timing separately; failed delivery never proves a click.

Existing GameThread stack symbolication places the game thread in
`FSlateRHIRenderer::OnWindowDestroyed` waiting in `FlushRenderingCommands`,
while the assertion stack releases a viewport reference on the rendering
thread. Preserve the original context and symbolication output. This suggests
a lifetime race but does not establish a project cause or validated workaround.

Any failure keeps reliability fail/open. All-clean results remain inconclusive.
If B fails, explicit view-target assignment is not necessary for the observed
assertion. Next compare controller or investigate a public lifecycle adapter
that preserves viewport ownership across rendering teardown. No engine edits.

After the A/B comparison, run one bounded C1 sample matching A with only the
published `-norenderthread` option added. Retain the 180-second passive window
and startup/close evidence. This is an optional temporary-path probe, not a
validated fix, product default or performance measurement. The earlier GQ
numbers cannot be applied to this execution mode.
