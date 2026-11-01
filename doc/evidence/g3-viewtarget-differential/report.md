# H1c startup classification and view-target differential

Status: diagnosis complete, reliability fail/open, 2026-11-01. Source base `6fbfd43`, installed UE 5.8.3,
Mac Metal SM6. Raw evidence is machine-local at
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-H1c-20261101/raw/`.
This report does not claim a root-cause fix or reliability acceptance.

The checked-in `sha256-index.json` indexes 92 raw files, including failed and
invalid samples. Its SHA-256 is
`4247a63171343dc6d53d3735c9a7f8acb091cbceeb9cebe23af634a293395cb7`.
Large images, native stack sampling and logs remain at the local raw path.
The index excludes generated UserDir caches; original UE logs, stdout, commands,
phase summaries, process inventories and exits are included. All indexed files
were rehashed at delivery. Diagnostic and restored-source Editor builds both
exited 0, and the read-only engine-source hashes matched before and after.

## Startup errors are separate from the viewport assertion

1. A fresh worktree has independent, untracked build outputs. Directly opening
   its project can report incompatible/missing `EdgeWorldHost` and
   `EdgeWorldRuntime` modules. `startup-missing-modules-reference.log` preserves
   this exact warning followed by the official rebuild. Prebuild the exact
   worktree's Editor target before opening it. This prevents the avoidable
   missing-module prompt; it does not repair a runtime viewport race.
2. `startup-metal-missing-reference.log` preserves the earlier fatal missing
   MetalToolchain dialog and `RequestExit(1)`. The current `xcrun metal --version`
   succeeds (exit 0). No toolchain reinstall was performed in this task.
   Missing Win64/Linux SDK messages in Mac validation stdout do not establish
   a Mac startup blocker; subsequent Metal runs initialized successfully.
3. H1b and the new A1 run reached `Engine is initialized` and displayed the
   game viewport before the `SceneViewport.cpp:196` assertion. This is a real
   runtime/window-teardown failure, not a missing-module build prompt.

The independent `codex/ue-mac-launch` worktree owns the prebuild launch entry;
no startup script or runtime authority code is changed by this diagnostic PR.

## GameThread evidence

The H1b skip2 crash context was copied without modification. `atos` was run
against the installed arm64 dylibs, using each recorded image load address and
offset. Commands, exit codes and output are preserved in
`h1b-gamethread-symbolication.txt`. The relevant chain is:

```text
FSlateApplication::OnWindowClose
SWindow::RequestDestroyWindow
FSlateApplication::RequestDestroyWindow / DestroyWindowsImmediately
FSlateApplication::PrivateDestroyWindow
FSlateRHIRenderer::OnWindowDestroyed
FlushRenderingCommands
FFrameEndSync::Sync / FRenderCommandFence::Wait
```

The fatal rendering-thread stack releases a shared viewport reference in
`FSlateRHIRenderer::DrawWindow_RenderThread`, then calls
`FSceneViewport::~FSceneViewport / Destroy`, which requires GameThread.
Read-only inspection of the installed release source shows that
`PrivateDestroyWindow` calls `NotifyWindowBeingDestroyed` before
`Renderer->OnWindowDestroyed`; the game's window-closed callback resets
`SceneViewport` during that notification. The renderer flush therefore happens
after that owner is released. This is evidence for a reference-lifetime race;
it does not prove why this run's native close event occurred or validate a fix.
Source files are read-only and their hashes are retained.

## Protocol and sampling limitations

The diagnostic binary has two temporary command-line switches recorded in
`diagnostic-only.patch`. Both A and B skip the causal Actor and disable the
worker environment. A retains explicit camera target assignment; B skips only
that assignment. The camera actor, lights, controller, HUD and pawn otherwise
remain present. Actual ViewTargets are logged as CameraActor for A and
SpectatorPawn for B.

Each run records commands, PID, process snapshots, timestamped startup phases,
raw stdout/UE log, first observed image, close-call timing and exit code.
Screenshots establish a rendered image by their observation time, not the
timestamp of the first GPU presentation. Worker absence is intentional; the
HUD's connecting message is expected and is not worker readiness evidence.
CUA observes the first image and then leaves the window untouched during the
remaining passive interval. Close is attempted after at least 180 seconds
from engine initialization. Call timing and actual native event delivery must
not be equated.

After A1 crashed, a post-close CUA state read reopened an unconfigured UE
process. This overlapped B1 and its screenshot captured the generic UE home
window. B1 is explicitly invalid for comparison; its files and termination
result are retained under `B1/invalid.json`. Both owned test processes were
stopped with SIGTERM, and B1 was restarted as B1r only after process inventory
confirmed no remaining UE instance. Subsequent post-close checks use process
and raw-log observations to avoid reopening the application.

## Results

The Editor diagnostic build and Metal preflight both exited 0. All five valid
samples initialized the engine, loaded `/Engine/Maps/Entry` with
`EdgeWorldCausalGameMode`, logged their expected configuration and worker
disablement, displayed the HUD, and remained live for over 180 seconds before
the close attempt. Each startup and error timestamp is retained in the raw
UE log; `startup-summary.json` gathers these milestones without substituting
them for the original logs. Times in the following table are UTC.

| Run | Explicit camera target | Extra option | Window destruction / exit | Result |
| --- | --- | --- | --- | --- |
| A1 | enabled | none | 03:58:22; exit 1 | Same RenderThread viewport assertion |
| B1r | disabled | none | 04:03:56; exit 0 | RequestExit and normal LogExit |
| A2 | enabled | none | 04:07:55; exit 1 | Same RenderThread viewport assertion |
| B2 | disabled | none | 04:11:39; exit 1 | Same RenderThread viewport assertion |
| C1 | enabled | `-norenderthread` | 04:15:44; exit 0 | RequestExit and normal LogExit; bounded temporary-path probe |

The invalid B1 is excluded from this table; its SIGTERM cleanup exit 0 does not
count as a successful close-button run. In valid runs, CUA's close call returned
success, but the delivery boundary is still not independently instrumented.
The assertion timestamps lie inside the corresponding recorded call intervals;
do not infer a precise click/native-event ordering from the returned result.

B2 demonstrates that explicit `SetViewTarget(Camera)` is **not necessary** for
this assertion. Together with H1b, neither worker execution, the causal Actor
nor explicit camera assignment is necessary. B1r's clean exit does not establish
a benefit from changing the view target. The proposed camera rewrite is
therefore not justified as a crash fix by this comparison.

C1 differs from A only by the installed engine's `-norenderthread` option.
`C1/threads.sample.txt` (sample tool exit 0) places rendering calls under
GameThread and does not show a separate RenderingThread stack. Sampling itself
is an additional observation in C1, so this is not a statistically controlled
performance or reliability comparison. C1 supports a possible temporary launch
path for further testing, not a root-cause repair or product default. It did
not run live Genesis, navigation, persistence/recovery or a full scene because
the worker and causal Actor were deliberately disabled. Previous GQ measurements
do not apply to this mode.

No UE or worker remained after C1 and GPU use was released. Temporary GameMode
source edits were reversed; no diagnostic switch or product-code change is
delivered by this PR. The restored-source Editor rebuild is recorded separately.

## Next bounded action

Keep reliability fail/open and V-HOME unaccepted. Use the independent prebuild
entry to distinguish module/toolchain readiness from actual runtime readiness.
Before recommending `-norenderthread` to the user, test it on the full scene
with a live worker, input/history/read-only checks, recovery and repeated exits.

For attribution, repeat a stock GameMode comparison or change controller/HUD
individually; do not continue removing already-excluded camera/Actor features.
A release-project lifecycle adapter is another candidate: the public Slate
window-destruction notification occurs before the engine drops its viewport
owner, allowing an early render synchronization to be evaluated. Such an adapter
requires a separate implementation and lifecycle/regression tests; this report
does not claim that synchronization or a custom viewport deleter is validated.
No engine source change is warranted by the present evidence.
