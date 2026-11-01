# H1e default-thread viewport preflush experiment

Status: diagnostic implementation and finite checks complete; not a product fix.
Default-thread reliability remains fail/open. Date: 2026-11-01.
Base `006a302598f44c4b247e2811e9c4698ce81b91e2`, branch/worktree
`codex/g3-viewport-preflush`. Installed UE 5.8.3 / CL 58210709, Mac Metal SM6,
live Genesis 1.4.3. Raw evidence is local at
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-H1e-20261101/raw/`.

## Candidate and common baseline

The project config selects a diagnostic `UGameViewportClient` subclass in both
arms. It observes the public Slate window-destruction notification, filters to
the owning game window and requires GameThread. The installed release calls
this notification before the engine's close callback drops its scene viewport
owner. Only B enables `-EWDiagPreflushViewport`, which calls
`FlushRenderingCommands` at this earlier point. A records the notification only.
Default behavior leaves synchronization disabled. Neither arm uses
`-norenderthread` or `-onethread`; each registration log confirms
`threaded_rendering=1`.

The same compiled binary/configuration serves both arms. Camera, GameMode,
worker, input, lights, HUD and world rules are unchanged. Source and binary
hashes identify the candidate actually run. The public extension order and
implementation review are in `implementation-review.md`; independent acceptance
remains coordination's responsibility. No engine source was edited.

The official Editor build succeeded, exit 0. The focused automation
`edgeWorld.ViewportPreflush.DrainBeforeGameThreadOwnerRelease` succeeded, actual
process exit 0. It ran under NullRHI with the default rendering thread present.
Its surrogate shared-reference probe verifies disabled non-drain, enabled drain
while the GameThread owner is alive, and final GameThread destruction. It does
not exercise a native window or prove general viewport reliability.

## Real scene protocol

Run A1/B1/A2/B2 serially, fresh per-arm UserDir, the same `/Engine/Maps/Entry`
and causal GameMode, full scene and live worker. Each explicitly commits tick
0→1→2, then history 0/1/2, H, R, W and Right. Per-action snapshots preserve the
manifest and all checkpoint file hashes; new UE observation acks are required
for historical/head operations. Camera actions have no worker ack and are
checked through screenshots plus unchanged files. First observed images record
when a frame was seen, not when the first GPU presentation occurred.

Each primary run waits at least 180 seconds after engine initialization before
the same close-button attempt. These are active scene tests, not wholly passive
intervals. CUA call intervals and native log times are separate evidence; a
returned click call does not independently establish event-delivery order.
Keep fixed windowed resolution to avoid adding full-screen/Space transitions as
another experiment variable. No second UE world or shared-state writer runs.

## Reporter and evidence-tool handling

A1 reproduced the assertion and left an orphan worker. Its raw crash context
and minidump were archived, and the exact worker state-directory match was
terminated. The first reporter matcher expected an executable path, while this
reporter appeared as the short command `CrashReportClient`. The first cleanup
therefore missed PID 30598, attributable to UE PID 30223. A corrected TERM was
sent, but a subsequent inventory still showed it alive. A further targeted
cleanup verified it absent at 04:59:50 UTC. Original cleanup attempts, process
snapshots and separate archive copies are retained rather than overwritten.
No report-send action or global process kill was performed. Detached reporter/
orphan-worker exit codes are unavailable; signals and later inventories are
recorded instead of inventing exit statuses.

This old A1 reporter overlapped B1 and A2's early runtime. B1 is therefore not
a pristine no-other-reporter startup sample; no performance or failure-rate
comparison is inferred. Its before-close synchronization trace remains
observable. A2's close and B2's startup follow verified reporter cleanup. The
final review must retain this procedural limitation, not silently call all
four environments identical.

An initial attempt to load a local UI helper with string evaluation was blocked
by the tool runtime before any input. `ui-helper-load-error.json` retains that
failure. The literal helper definition then executed successfully; raw helper
source, action logs and images remain available. This was not a UE failure.

## Primary results

Times below are UTC. All primary starts reached engine initialization, the
expected diagnostic-client registration, valid tick 0/1/2, full HUD/scene and
the sampled history/camera operations before the close attempt.

| Arm / UE PID | First observed image | Window destruction | UE exit | Preflush evidence |
| --- | --- | --- | --- | --- |
| A1 / 30223 | 04:49:11.866 | 04:52:09.749 | 1 | Disabled; original RenderThread `SceneViewport.cpp:196` assertion |
| B1 / 30669 | 04:53:48.275 | 04:56:45.086 | 0 | Begin/end before owner release, non-null owner unchanged, 23.938 ms |
| A2 / 31076 | 04:57:41.202 | 05:01:07.982 | 0 | Disabled; normal RequestExit and LogExit |
| B2 / 31560 | 05:02:21.898 | 05:05:34.890 | 0 | Begin/end before owner release, non-null owner unchanged, 23.991 ms |

Both B samples satisfy the candidate's observed ordering conditions: default
rendering thread active, correct game window/GameThread, non-null viewport owner
at callback entry, owner unchanged after flush, then native closure and normal
exit. Neither produced an orphan worker or a new reporter. A2's clean exit
confirms the underlying failure is intermittent; A1 remains a real failure.
The single-close synchronization durations above are not frame-time or general
CPU/GPU performance measurements.

These results support further evaluation of the candidate. They do not prove
root-cause repair, a failure-rate improvement or universal reliability. In
particular, retain the reporter-overlap limitation above: B1 is not a pristine
single-graphics-client startup/close comparison. Only B2 began after verified
reporter removal. Do not silently treat this as a fully controlled statistical
experiment or promote the flag to a product default.

## Recovery, hashes and final lifecycle state

All four arm state directories were reopened with new UE/worker processes and
the same arm's diagnostic setting. Valid initial tick-2 observations and images
were captured. Each recovery performed history 0, H and W without changing any
authoritative file, then used CmdQ rather than the primary close-button path.
These recovery sessions are separate from the four primary window-close
samples and are not counted as additional controlled close repetitions.

| Recovery arm | UE PID | UE exit | Exact persisted-file recovery |
| --- | --- | --- | --- |
| A1 | 31986 | 0 | Pass, including after A1's crash and orphan cleanup |
| B1 | 32220 | 0 | Pass |
| A2 | 32428 | 0 | Pass |
| B2 | 32665 | 0 | Pass; UI observation retries preserved |

Forty completed read-only checks passed: seven per primary and three per
recovery. Eight explicit Advance actions were acknowledged, two per primary;
none occurred during recovery. Within each arm, manifest bytes and all four
checkpoint/authority file hashes match across read-only actions, closure and
recovery. Fresh-arm manifest/checkpoint hashes need not match each other;
compare only each arm's own closed/reopened world. The common final state head
was `193c4948adde95d29e1deef4edafac63abbd61abe0fc47d75000af009bd28192`.
Per-arm manifest/state/event hashes are in the compact evidence index.

B2 recovery briefly exposed a computer-use observation issue: combined AX/
screenshot and coordinate-click calls returned `noWindowsAvailable` while the
UE App/worker remained alive and had logged valid tick 2. Errors are retained
under `B2-recovery/ui-*.json`. A separate screenshot succeeded and was visually
checked; direct keyboard activation then allowed the recorded recovery matrix
and CmdQ exit to complete. No UE failure is inferred from these tool errors.

The final process inventory confirms no test UE, causal worker or
CrashReportClient remains. GPU use is released. Signal requests to detached
processes are not reported as actual child exit codes; only the eight owned UE
processes have the explicit exit codes above. No report-send action was used.
The raw A1 context/minidump and all cleanup attempts remain intact.

`evidence-index.json` is the small checked-in index. It records each run's real
PID/exit, raw UE-log and first-image hashes, and each primary's authority hashes.
It authenticates the full machine-local `sha256-index.json`, covering **396 raw
files**, including failed tooling/cleanup attempts, archived crashes, checkpoint
blobs, all images/logs and automation results. Full raw-index SHA-256:
`09ad773cc9bdddb8bfdeb5b28528bccbdc7b4a33c1dbc3db92e2e489128760d0`.
Compact index SHA-256:
`1230889b5b821ec765d2caa3a6ab40d4c1ac53e3ffe398dbbae5558187fe354a`.
All raw hashes and tested source/binary hashes were verified at delivery;
read-only engine-source hashes matched before/after.

## Gate and recommended Act

Diagnostic implementation/build/lifetime-probe and the listed state/recovery
checks are complete. Candidate B has two finite clean primary exits with the
expected mechanism trace; one has the documented reporter overlap. Default
threaded reliability and product-fix acceptance remain **fail/open/pending**.
The preflush switch remains off by default. This PR does not change the normal
launcher's options or enable the candidate for ordinary users.

Independent review should inspect the notification/owner lifetime assumption,
client lifecycle and native failure evidence, then decide whether to repeat a
fully reporter-free interleaved matrix and broader window/stress cases. Such
testing and any production enablement require a new bounded card/decision;
clean B samples alone are not permission to set the default. The previously
integrated `--no-render-thread` remains a distinct temporary execution path.

No engine-source changes, visitor H6B/H6C work or lighting repair was performed.
The existing unbuilt-lighting warning remains visible in screenshots; it must
not be mistaken for this assertion or hidden to claim an error-free experience.
