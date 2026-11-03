# I16A — independent Native execution review

2026-11-03; reviewer `/root/i15_native`, separate from root execution owner. **Disposition: partial; the complete four-test/normal/resource evidence gate did not pass.** A real Native run did accept all three original proofs. Those observations are retained; no successful full Native review policy, legacy-gap discharge, Metal acceptance or G-B2 grant is issued.

## Reviewed scope and readiness

Plan53cd344 correctly selected a Native-only iteration while CUA was available. C commit5646124 added the honest `approved-native-only-iteration` reason without changing source/private/admission/one-shot gates; this reviewer independently inspected the diff and reran all18 affected CPU tests successfully. PR122's merged tool source was `4e7a58a0f37b9366d74d51b398c99e9b854fc213`. Product/native source and actual prebuilt binary identity remained `5a6cca0c36b7dc89997d1a0bf35f154346f86e99`; no new product build was needed.

Before dispatch, independently rehashed all public source/native pins and installed UE/real lib-prefixed Host/plugin binaries, verified actual clean tool/product identities with the six approved product output/config exceptions, and revalidated the exact old3 manifest against raw chunks/catalog/public allowlist. Prepared derivation changed only run_id/tool_source_sha/before_map_ref/created_at; all product/native/binary/owner-reference/context/input/scratch/output-root fields were unchanged. No private owner/key contents were read. Current61-file authority map matched; the new controller output did not exist. This justified one Native-only dispatch, not a result pass.

Run root: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe/I16-20261103-native-only`. The inherited I15 output root was retained and fully counted; no binary/scratch location validator was weakened.

## Actual checks and disposition

| Gate | Independent observed evidence | Result |
| --- | --- | --- |
| One actual Native process | PID64536, observed parent64525, start `Tue Nov 3 10:55:34 2026`; original argv selects GameModeBase/NullRHI and four declared selectors, filtered four replay environment fields bind actual manifest/output. Actual Native parent wait0, phase25.245806s; outer controller parent wait0,26.600995s. | pass for one process execution/actual wait only |
| Three exact proof cases | Result PID/manifest hash and ordered cases match. Actual five input SHA per case, request IDs, tick/revision/watermark, manifest/state/event digests and full selected-record outputs independently match originals: old-initial `(0,0)`31 records; old-retain `(0,1)`42; old-physics `(1,2)`45. All acceptedtrue/error empty. The unchanged bridge actually used original PublicPins→strict successful status→trusted head→ObservationParser for these inputs. | observed actual parser acceptance for exactly these old responses; no new solve/history/retry claim |
| Four exact automation tests | Actual UE raw log says Found1 based on PublicProofReplay, and contains only that single Success. IdentityAndDefaultOff, HandledInputAndOrder and PauseReadWithoutTick did not run. A declared selectors list or parent exit0 does not replace missing execution. | fail for required four-test gate |
| Continuous controller observer | Independently rehashed all49 raw process snapshots. First sample gap0.0326335s; maximum successive gap0.5644315s<2. | pass during the controller observation interval only |
| Quiet at original seal | Zen PID64908 was observed as child of UE64536, then reparented to1 and still present at original seal. Original native-execution normalfalse/errors and resource decisionfail/all_processes_quietfalse are correct and unchanged. | fail; parent wait0 is not normal complete cleanup |
| Later cleanup boundary | Cleanup-before, cleanup-final and campaign-final raw snapshots contain no UE or Zen64908. Cleanup record actions=[]/remaining=[]: Zen had self-exited before cleanup-before; no signals were sent. | later quiescence observed; does not repair original seal or prove forced cleanup occurred |
| Original console integrity | Original execution console SHA9d783a… no longer matches the original console path, now2652 bytes / SHA bbae1d…. Current first1802 bytes exactly equal the newly saved, explicitly derived prefix and its SHA matches the former reference. | original-path immutable snapshot gate fail; derived prefix is not an original snapshot restoration |
| Authority boundary maps | Rehashed before/after refs agree on all61 files; an independent fresh authority map also matched all61. No private/key bytes were read. | pass for boundary maps |
| Time/bytes | First outer1235830.355689791→campaign end1236183.785693583 is353.430003792s; summary353.430003917s differs by0.13µs (separate monotonic call precision), immaterial to900s. Independent full-root stat sum1,496,841,720B≤sealed conservative1,496,872,753B<2GiB. Zen used an external shared data/cache directory with no pre-run byte baseline. | local-root measurement/time within budget; complete all-output byte coverage inconclusive |
| Metal / broader universe gates | Metal deliberately not dispatched; no worker/solver, new world mutation, UI/PNG/input matrix or standard double session executed. | skipped/open; G-B2 not granted |

The record of accepted old3 results is a useful bounded fact, distinct from the approved four-test Native-review contract. The existing verifier requires normal execution, complete four-test evidence and whole capability resource evidence; those conditions are absent. Do not silently weaken that contract to discharge the three legacy semantic gaps.

## Reproducible failure diagnosis

The installed source `/Users/Shared/Epic Games/UE_5.8/Engine/Source/Runtime/Launch/Private/Mac/LaunchMac.cpp:116` documents Xcode quote conversion; line117 performs `GSavedCommandLine.Replace(TEXT("$"), TEXT("\""))`. The actual Popen argv contains four `^selector$` expressions joined with `+`, but actual UE command-line originals at log23/403 show each `$` converted to a quote. Automation Found1 at1388 and single Success at1399 confirm only the first selection reached execution. This is observed platform argument handling, not a missing compiled diagnostic test proved by the current run. Do not rerun UE within this one-window card.

Actual UE log885 records launching detached Zen with `--owner-pid 64536`, external Common/Zen/Data and `--detach`. Independent observer snapshots confirm the same PID/start crossing child→detached status. The post-seal console append is consistent with an inherited output stream, but the captured data alone does not attribute every appended byte to a particular writer. The failed original quiet/console gates remain visible.

UE raw log1258/1260 also reports an uninitialized `FDataflowToolNodeSnapshot::Date` property from engine DataflowNodes during startup (LogClass/Automation). This is a retained engine-log risk, separate from the later PublicProofReplay case event; the current evidence does not diagnose a plugin cause or justify engine-source edits.

## Immutable public evidence

All paths are relative to the run root above unless stated otherwise; originals were independently read, not recreated:

- `prep/prepared.json` SHA `27e4642fe5bac4d7dca27b3703fb4d21f42e36a9cd517440c5ffbd1dec4f1a4d`; `prep/capability-card.json` SHA `b75a96d6b58594a36cb17e1e609621d12ebe3c7a92803b23f42668978b309c21`; `replay-old3/manifest.json` SHA `5cb7e97a1fbc2316006388e75537b6e4685b357eddfa45719b28770021208be1`.
- `capability/native-execution.json` SHA `d8a92482d91773550f5d3a1ea43c77e44a4e95a6aa37ceb37df0c9637160ecd0`; `native/replay-result.json` relative to capability SHA `b73e79e528eaf9774964486887f3d2a9121a85ac6f8c622d3e18e28b26b06af0`; `native/ue.log` SHA `7d4019594f92d95562f9ecfcad13fd6fc0c89a2dc055711bfb54361362af5bd7` (both under capability).
- `prep/campaign-summary.json` SHA `27afbf00a0edb8b4f89957992735d0f7f12f65f15dbf86ad7d7a413a33a1005e`; `prep/owned-descendant-cleanup.json` SHA `73c23a4afcf1203582bff31227129c8f3f31e78e649dc7c87dcac12f19ebd8dc`; `prep/console-postseal.json` SHA `13c756de8b8e163e00c88f4076071f9a766aa34ca80c1ef620f6fcb9c7f0f795`. Their authority/process/current-console/derived-prefix refs were independently rehashed; original console receipt remains unchanged and contradictory to the current original path.

## Act and next ready node

Accept I16C code delivery and record the actual three proof acceptances. Settle this execution as partial with explicit four-test/quiet/original-console failures and incomplete external-byte coverage. Preserve I15/I12 failures, all original refs, single-window limit and G-B2 open state.

The next ready task is offline correction/review of actual Mac automation argument encoding plus bounded Zen/output ownership/accounting. It must keep the same exact four-test acceptance requirement, isolate or fully account auxiliary outputs, and finalize console originals only after all relevant writers exit. CPU/source checks and CI finish before a fresh independent runtime card. Then one separately budgeted Native run can verify the corrected dispatch/cleanup, without adding world features, Metal or engine-source changes. Do not overwrite this card/result/resource or rerun within it.

No reviewer UE/build/worker/solver/UI process or runtime-state write occurred. This report is a repository documentation artifact outside the sealed run storage. Its root integration is equivalent independent review; cleanup of this review tree follows the normal clean-worktree/dependency check.
