# G3 shutdown isolation result

Date: 2026-11-01. Source commit `f5532e6`. UE 5.8.3 installed Mac build, Metal SM6, `-game -log -windowed -ResX=960 -ResY=600`; Genesis 1.4.3 Python; abstract causal worker from this worktree. This is a diagnostic replay, not G4 acceptance.

Raw files: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-shutdown-isolation-20261101/`. `sha256-index.json` SHA256 `f8e35423ff5f09e190dd2845799b6b3643d83945810cf944c6ba34f60786e7ca`. The raw directory is machine-local. UE log SHA256 `f3e38194b6bec13f83f1702525c8dca177a620064e26fc4d2929208a73a66121`.

## Sequence and observations

1. Created a fresh worktree-specific `Saved/EdgeWorldCausal/stg-demo`; initial authority manifest read tick/revision 0/0 and head `3aff0b8b…`.
2. CUA focused the game viewport and pressed Space once per confirmed transition. Manifest reached tick/revision 1/1 (`c933ad93…`) and 2/2 (`193c4948…`).
3. CUA pressed 0, 1, 2; the corresponding one-, two-, and three-node historical views were visually observed. W changed camera framing. H and R were then pressed. The bytewise SHA256 of `abstract_world.json` before and after these read-only actions was identical: `76487f44551a6c6ec824a45bf43a5eab44f4a8d2e0047d5d5690afe5b2d2f043`.
4. **Before the intended close-button click could execute**, UE exited with code 1. CUA's click returned `procNotFound`. In the log, window destruction at 02:43:34.037 was followed 8 ms later by `SceneViewport.cpp:196` `IsInGameThread()` assertion in `FSceneViewport::Destroy()` on the render thread (lines 1527–1558). There is no normal `RequestExit`/`PreExit` in this trace. The worker became orphaned and was explicitly terminated; a subsequent process check found no UE or causal worker.

The preceding GQ Metal sampling run independently logged the same assertion after its profiling capture and before its intended UI close action (`GQ-20261101-C3/raw/ue.log`, lines 1552–1584). The original G3 run had attributed the timing to a close-button click. With two pre-click occurrences, **a close-button action is not a necessary trigger**. The exact reason the viewport window is destroyed remains unknown. No project frame appears in the captured render-thread stack, so assigning ownership to the plugin, worker, UE release build, or macOS is not yet justified.

## Check and Act

- Reproduction of the assertion under the original tick/history/camera sequence: **pass** as a failure reproduction; shutdown reliability gate: **fail/open**.
- Causal state integrity through the sampled read-only inputs: **pass** by manifest SHA; this does not prove state behavior after the UE crash beyond the saved file.
- Worker lifecycle after UE crash: **fail** for automatic cleanup in this observed crash path; orphan manually stopped. Normal `EndPlay` may not run after this fatal assertion.
- Attribution and remedy: **inconclusive**. Next controlled differential: same published UE build with causal worker disabled, and a separate minimal viewport game mode, observing window lifecycle without CUA interaction. Capture a symbolized game-thread stack and native crash report if available. Keep UE source unchanged until a release-plugin workaround is tested against a specific proven contract gap.
