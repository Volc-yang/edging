# G3 shutdown isolation plan

Task ID: G3-SHUTDOWN-ISOLATION. Parent: G3/V-STG. Base `f5532e6`; branch `codex/g3-shutdown-isolation`; owner path `doc/evidence/g3-shutdown-isolation/`. Execution environment: UE 5.8.3 published Mac build, Metal SM6, repository Genesis 1.4.3 virtual environment. No UE engine source changes.

## Fixed input and hypothesis

The original `G3-lxKhO5/ue_live.log` logged Slate window destruction at 01:51:12 and an `IsInGameThread()` assertion in `FSceneViewport::Destroy()` on the render thread about 6 ms later, before normal `PreExit`/`EndPlay`. Two later close-button runs exited cleanly, including one with a running causal scene, but neither replayed the original tick/history/camera sequence. Ownership is undetermined; the assertion may depend on a viewport lifetime race. Project transport cleanup occurs in game-mode `EndPlay`, later than the observed assertion, so attributing the crash to it would be premature.

## Ordered execution

1. Wait for main coordinator's exclusive GPU signal. Confirm no other UE/worker process. Build only this worktree's UE project modules if necessary.
2. Launch `-game -log -windowed -ResX=960 -ResY=600` with an isolated worktree Saved directory and absolute Genesis Python/worker paths. Save command, build ID, start time and raw logs.
3. Verify tick 0 from a fresh state, then use one Space per confirmed transition to tick 1 and 2. Observe 0/1/2 historical views, move camera W, request H/R; capture the state manifest and its SHA before/after the read-only sequence.
4. Click the macOS game-window close button via CUA after the scene is stable. Record exit code, complete UE log, any crash report, worker PID lifecycle and manifest SHA. Run one controlled repetition if the first result is ambiguous or if the assertion appears; do not infer determinism from one sample.
5. Compare against original crash and the prior clean recheck. Classify as reproduced, not reproduced under sampled conditions, or inconclusive. Propose a local plugin fix only if an attributable project frame or controlled differential appears; keep the gate open otherwise.

Evidence: SHA256 index for all raw files on DevSSD, small report in this directory, explicit commands and timing. UI will be a small window; no primary-display full-screen operation. No user input should be needed.
