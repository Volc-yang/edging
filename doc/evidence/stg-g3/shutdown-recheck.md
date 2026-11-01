# G3 macOS window-close recheck

Date: 2026-11-01. UE 5.8.3 installed build, Metal SM6, `-game -log -windowed`, causal game mode, Genesis worker from this integration worktree. The project modules were rebuilt for this worktree before the first run. Both runs used its own ignored Saved state, separate from the original G3 evidence directory. No engine source was changed.

| Run | Close timing | Result | Raw log SHA256 |
| --- | --- | --- | --- |
| 1 | Immediately after engine initialization; scene readiness was not established | macOS close button; exit code 0; `LogExit: Exiting` | `startup_close.log`: `040d5613c9631839c177b517f2c164aa0883a445241a9be7e0f8390bfa1f68f6` |
| 2 | Causal scene visible and running; `Causal world` logged before close | macOS close button; `RequestExit(0, UGameEngine::Tick.ViewportClosed)`, `LogExit: Exiting`, exit code 0 | `steady_close.log`: `74202f421ebe5ab2c1e09725e4cf697b00d9773bd630f122059e3836802edecd` |

Raw logs: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-shutdown-repro/`. After both runs, no matching UE or causal worker process remained. The original failure remains in `G3-lxKhO5/ue_live.log` at lines 1461–1490: `FSceneViewport::Destroy()` asserted `IsInGameThread()` on the render thread immediately after a close-button action. The two clean rechecks do **not** erase that failure or establish its owner. They show that closing is not deterministically broken under these two sampled conditions. The original failure followed tick 0→1→2, historical view changes and camera input; the steady recheck did not repeat that full action sequence.

Act: keep the shutdown gate open as intermittent. Reproduce with the original tick/history/camera action sequence and capture a complete symbolized stack plus a worker lifecycle trace before changing plugin or UE source. Prefer the published UE build and a local adapter fix if project code is implicated.
