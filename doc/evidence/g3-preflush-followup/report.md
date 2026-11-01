# H1f delegate idempotency and reporter-free follow-up

Status: implementation and finite runtime checks complete; final independent
evidence/PR acceptance pending, not product/default enablement. Base
`12f7fb734c38a0a8de4da158ca6ffae74e43801c`, branch/worktree
`codex/g3-preflush-followup`. Accepted scope is the parent H1f card; no engine,
GameMode, camera, HUD, light, worker or visitor-path changes.

Raw evidence is local at
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-H1f-20261101/raw/`.
Earlier H1e evidence is historical input only, not acceptance of this binary.

## Delegate change and prerequisite tests

`Init` now removes and invalidates its prior window-destruction handle before
calling the base Init. `BeginDestroy` uses the same idempotent removal routine.
The existing window filter and optional preflush behavior are unchanged, and
the preflush option stays off by default. Header friendship gives only the
focused automation test access to the stored private handle.

The new test uses real client Init calls: initial registration, repeated Init,
removal of the newest handle with no older object binding remaining, another
Init after the handle was already removed, then ConditionalBeginDestroy with
no remaining binding and an invalidated handle. The original rendering-thread
lifetime probe is retained. Tests do not claim broad PIE/multi-window coverage.

The first build succeeded. The first new test fixture incorrectly allocated
the viewport client under a Package rather than its required Engine Outer.
This triggered an ensure and a failed test report; those logs, report, native
context/minidump and reporter cleanup are retained. The fixture was corrected
to create the client/game instance under `GEngine`, and the binary rebuilt.
Build 2 succeeded; test run 2 reports both lifecycle tests Success, with direct
UnrealEditor-Cmd exit artifact 0. There are no test-2 ensure errors. All real
samples use that rebuilt, frozen source/binary identity.

The first exit evidence has an observer discrepancy: coordination reported
reading 1, whereas the captured local file currently contains bytes `30 0a`
(text `0\n`), timestamp and SHA-256 preserved in
`lifecycle-tests1-exit-audit.json`. The direct Cmd executable is a Mach-O binary,
not the earlier App launcher wrapper. Do not infer first-test success from its
exit artifact: its test-report outcome is unambiguously Fail. The discrepancy
is retained rather than rewriting either observation. Only the corrected second
test report/exit is used as a prerequisite gate.

The new fixture ensure came from UE PID 36416; the fresh ensure directory
contains its exact error and test stack. The coordinator identified reporter
PID 36772, whose executable/start information was captured. The ensure directory
was archived, TERM sent to that exact reporter, and KILL used only after the
same PID/executable survived TERM. Its disappearance was verified before the
first real run. Detached reporter exit status is unavailable; signal attempts
and subsequent inventories are recorded instead. No report-send action or
global process termination was used.

## Runtime protocol and decision boundary

Each start inventories UE, causal worker and reporter processes. Any existing
relevant process invalidates the baseline and prevents a new UE launch;
existing user processes are not terminated. Per-arm state directories are
isolated, and every real run uses default rendering threads and the same
complete live Genesis scene. Only B adds `-EWDiagPreflushViewport`. The inherited
`H1e` diagnostic log prefix is intentional; fresh log paths and frozen binary
hashes identify this H1f experiment.

Primary A1/B1/A2/B2 sessions each wait at least 180 seconds after initialization,
explicitly commit tick 0/1/2, and check history 0, H and W against every persisted
authority/checkpoint file. Actual UE PID/return code, startup stages, first
observed image and native window/preflush ordering are retained. A call returning
does not independently establish native input-delivery order. First observed
image timing is not first-GPU-presentation timing.

Only after both primary B samples succeed, B3 resizes and minimizes/restores
its window, and B4 reopens B2's exact state directory and exits via CmdQ.
Boundary samples are not counted as primary repetitions. Any valid B failure,
hang or missing required mechanism evidence rejects candidate passage. Source
and binary remain unchanged throughout; synchronization is not made default.

## Results on the corrected binary

Build 2 completed successfully. `lifecycle-report2/index.json` reports 2 succeeded,
0 failed, 0 not run; `lifecycle-tests2.exit` is 0. Build 1 also succeeded, but
`lifecycle-report1/index.json` reports 1 succeeded and 1 failed and is excluded
from acceptance. No source changes followed build 2.

All times below are UTC on 2026-11-01. Image times are the first captured
observation, not a measurement of first presentation. Native close is the Slate
game-window destruction log; raw `close-call.json` separately records input call
start/end and return. Exact launch/initialization/event/exit observations are
retained in `events.jsonl` and consolidated in raw `summary.json`.

| Sample | Actual UE PID | Launch | Engine initialized | First observed image | Native game-window destruction | UE exit | Minimum interval recorded (s) |
| --- | ---: | --- | --- | --- | --- | ---: | ---: |
| A1 | 37713 | 06:00:17.108 | 06:00:24.852 | 06:01:13.725 | 06:04:04.759 | 0 | 180.741 |
| B1 | 38181 | 06:04:13.493 | 06:04:21.201 | 06:04:50.765 | 06:08:57.125 | 0 | 180.628 |
| A2 | 38614 | 06:09:11.818 | 06:09:19.887 | 06:09:45.999 | 06:13:05.747 | 0 | 180.645 |
| B2 | 39118 | 06:13:24.628 | 06:13:32.211 | 06:14:01.951 | 06:17:34.944 | 0 | 180.646 |
| B3 boundary | 39585 | 06:17:47.051 | 06:17:54.684 | 06:18:18.237 | 06:27:00.266 | 0 | 180.621 |
| B4 boundary | 40395 | 06:27:12.079 | 06:27:19.751 | 06:27:55.788 | 06:28:22.556 | 0 | not a primary repetition |

Every sample logs `threaded_rendering=1`. A1/A2 log `preflush=0`; all B
samples log `preflush=1`, matching their command files. All B notifications
identify the actual game window and `game_thread=1`, with a non-null owner that
matches the owner after flush and `owner_unchanged=1`. Flush completes before
Slate destroys that game window. B1/B2/B3/B4 flush measurements are respectively
23.521/23.965/23.780/0.151 ms; these are individual diagnostic observations,
not performance improvement evidence.

There were 10 explicit Advance actions: two in each of A1/B1/A2/B2/B3. Each
reached valid tick 0/1/2 with acknowledgements. B4 restored tick 2 without
Advance. Nineteen completed read-only comparisons (12 primary, 4 B3 including
H after restore, 3 B4) show all authority/checkpoint file hashes unchanged.
History/head acknowledgements and pure-read camera comparisons remain in the
per-action records. Every sample's preclose/postclose file set matches.

B4 uses B2's exact UserDir. Its restored baseline, preclose and postclose sets
match B2 postclose, including manifest SHA-256
`29dd96d0aeea2c088908cd07776fbd441f62d7527784e2275891d8416bb1d742`.
It exits through CmdQ; B3 exits through the same game-window close button after
the boundary sequence. No valid B failure or hang occurred. All A results are
also clean; this does not establish a frequency benefit or erase historical
default-thread failures.

## B3 boundary and tool limits

AX zoom returned but the screenshot stayed 1920×1264, so that action is not
counted as resize. UE console `r.SetRes 1024x640w` then produced native resolution
metadata 1024×640 and an observed 2048×1344 image including titlebar/Retina.
The raw image-size records and before/after screenshots are retained.

CmdM minimized the game window and left its same-process log window frontmost.
Dock lookup by name and exact path timed out; Bring All to Front did not restore
the window. Re-read CUA documentation supplied no macOS windowId/minimized setter.
These are UI-tool limitations, not UE failure or hang evidence. The coordinator
explicitly authorized a system Accessibility fallback. System Events first read
PID 39585 and the exact game title
`EdgeWorldHost (64-bit Development SF_METAL_SM6) ` (including trailing space),
confirmed AXMinimized=true, then set only that window's AXMinimized=false and
performed AXRaise. `accessibility-restore.json` records true→false on the same
PID. The restored screenshot and a fresh tick-2 H acknowledgement confirm
continued operation; all authority files remain identical. Read/restore source,
stdout/stderr/exit artifacts and failed-tool descriptions are preserved.
Image files named `.png` retain original tool JPEG bytes without re-encoding;
the size records were read from those bytes.

## Sealed evidence and remaining gates

`evidence-index.json` in this directory authenticates the flat raw
`sha256-index.json`, sample logs, first images, exit artifacts and authority
snapshots. The raw index includes 369 files, 34,735,572 bytes, including the
first failed fixture/ensure archive and both automation reports. Its SHA-256 is
`fe9cf5353bf93ca6a6652aa03f6615858180f1cdb116479577f8f7a34a74dfa6`.
Index files and named cache directories are excluded to avoid self-reference;
the exact exclusions are in the compact index. `seal_evidence.py` checks the
source/config/dylib identity, engine-source hashes, actions, B mechanisms,
recovery and exits, then rehashes every indexed raw file. The full raw artifacts
remain local at the path above; the repository contains the compact index.

All six baseline/cleanup records have no reporter interference, no signal
actions and no remaining target PIDs. Final inventory at 06:29:06.581 UTC has no
H1f UE/worker/reporter. GPU/build ownership is released to H-LIGHT-01; no further
UE launch or build is part of this delivery. The untracked DefaultInput.ini was
generated by this worktree's Editor runs (standard serialized input defaults),
removed only here and excluded from the PR; main-workspace files are untouched.

The finite checks are complete. Independent final PR/diff/raw-hash review is
still required before accepting even a limited explicit project bypass.
Preflush remains off by default, with no launcher wiring or product/default
change. No root-cause repair, universal reliability or performance benefit is
claimed. PIE, multi-window, other platforms, production/global reliability and
any future default decision remain open; this report does not release H1g,
H6B or H6C independently of the coordinator.
