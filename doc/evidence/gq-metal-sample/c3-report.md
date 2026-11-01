# GQ C3 Metal CPU/GPU frame-signal probe

Date: 2026-11-01. Status: **C3 signal-export pass for one bounded probe; C4 product performance inconclusive**. This is an abstract three-node Seed→Tree engineering scene, not a frozen product load, visual-quality target or three-run benchmark.

## Run identity and capture

- Integration input `f5532e6e8c301eeccb4df7ab78697611a7890d23`; isolated worktree `codex/gq-metal-sample`. UE installed build `5.8.3-58210709+++UE5+Release-5.8`, Development, Metal SM6; macOS 26.6.2 (25G83), Apple M4 Pro, 48 GiB memory; `/Volumes/DevSSD` had about 722 GiB free. UE project modules were rebuilt for this worktree on launch. Genesis worker script is from the same commit and Python is `.venv-genesis/bin/python`.
- Launch: `UnrealEditor EdgeWorldHost.uproject '/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode' -game -log -windowed -ResX=960 -ResY=600 -csvCaptureFrames=600 -csvGpuStats`, with `EDGEWORLD_CAUSAL_PYTHON` and `EDGEWORLD_CAUSAL_WORKER` set to absolute paths. `csvCaptureFrames` is a **boot capture**; no prewarm interval or repeat count was frozen. Resolution is the requested window size, not independently verified internal render resolution. VSync, effective frame cap, power and thermal state were not recorded.
- UE logs the causal scene at 02:37:53.483 UTC, engine initialization complete at 02:37:54.991, and capture end at 02:38:00.197. The CSV has 600 frame rows and contains both `GameThreadTime` and `GPUTime` in the **same frame rows**, plus `RenderThreadTime` and `FrameTime`. Installed UE source `LaunchEngineLoop.cpp` uses `FPlatformTime::ToMilliseconds` for the core thread and `RHIGetGPUFrameCycles()` GPU columns. Source confirms units; nonzero CSV samples confirm this Metal run exported them.
- Original CSV, UE log and stdout are retained at `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/GQ-20261101-C3/raw/`. SHA256: `profile.csv` `42a9c1952f6876ae2eb86150bb8677dbf7587741d68cd4bea75151dacd2c7516`; `ue.log` `c2db3cefd5741f488edfea4bb63e4ce0d949a4aa76e5e933ae5aceb79ad7bdc0`; `stdout.log` `1b9776560d1f80492b9b967b1d3d6934e2a03da18cae9b37a53f646b53d562c7`. The CSV and stdout are copied from the local UE output paths after capture; no raw row was edited.

## Observed sample counts and descriptive values

Computed by `python3 doc/evidence/gq-metal-sample/summarize_csv.py <raw/profile.csv>` using all 600 frame rows, positive finite samples, and nearest-rank percentiles. Zero and startup samples remain in the raw CSV. Values below describe only this probe.

| CSV column (ms) | Numeric / positive / zero | Positive p50 | Positive p95 | Positive max |
| --- | ---: | ---: | ---: | ---: |
| `FrameTime` | 600 / 600 / 0 | 8.3492 | 10.7645 | 51946.2031 |
| `GameThreadTime` | 600 / 598 / 2 | 0.7803 | 0.9020 | 1553.2863 |
| `RenderThreadTime` | 600 / 599 / 1 | 8.3403 | 10.8035 | 1112.3184 |
| `GPUTime` | 600 / 598 / 2 | 3.9443 | 5.3435 | 56.5967 |

`FrameTime` includes the boot frame, so its maximum is not a steady-scene frame. We did not remove it from the raw export or claim a product p95 result. The `GPUTime` column proves a nonempty UE GPU-frame timing signal; it does not by itself validate an external Metal hardware counter or an independently synchronized trace.

## Exit failure and limits

At 02:39:01.575, about 61 seconds after CSV completion, the log records the game window being destroyed; at 02:39:01.587 `FSceneViewport::Destroy()` asserted `IsInGameThread()` on the render thread. UE exited code 1. During the interval after capture, I made no gameplay input and did not intentionally close the window; I queried the app accessibility state. My subsequent attempt to click its close button returned `procNotFound` because UE was already gone. The reason the window began destruction is unknown from this evidence. The orphaned worker PID 99462 was stopped, and no matching UE/worker process remained. This is another observed instance of the G3 shutdown failure; it cannot be assigned to the CSV profiler, worker or application code without more evidence.

The worker used UE's user-level Saved directory (`~/Library/Application Support/Epic/UnrealEngine/5.8/Saved/EdgeWorldCausal/stg-demo`), not a run-specific state directory. It created tick-0 state in this run; no advance input was sent. A before/after authority hash was not captured, so read-only invariance is not claimed here. That state-directory behavior should be fixed for future GQ runs.

## Act

GQ C3 export feasibility is demonstrated for CPU and GPU frame columns in one 600-frame Metal capture. Before C4: freeze G0 target load, route, window, repetitions, effective rendering resolution, VSync/cap, thermal/electric conditions and validity rules; use an explicit run-specific state directory; capture three separate warmed runs with full traces and independent recomputation. Keep the G3 shutdown gate open and investigate its window-destruction trigger separately.
