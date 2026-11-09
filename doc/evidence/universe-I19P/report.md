# I19P — explicit readonly Metal slice actions and evidence

2026-11-09. Status: CPU implementation complete; actual Metal/input/PNG/Native/exit checks remain unexecuted by this task. Base `9162000`, branch `codex/i19-readonly-slice`, dedicated worktree `.worktrees/i19-readonly-slice`. Parent/root and independent reviewer accepted the versioned scope in `doc/design/universe-i19-metal-readonly-plan.md` before implementation.

## Scope and API

Owns only `scripts/universe_iteration/probe_actions.py`, `tests/test_universe_iteration_probe_slice.py`, and this evidence directory. No UE/C++/build, worker/solver/UI process, credential inspection, authority mutation, controller change, or budget expansion. Root/C2 owns controller admission and runtime; reviewer owns independent acceptance.

The new contract is intentionally separate from the old 48-call/8-PNG probe:

- `FORMAT_V2 = universe-i19-probe-actions.v2` is the manifest and receipt version.
- `CUA_FORMAT_V2 = universe-i19-probe-cua.v2`; `STEP_LIMIT_V2 = 20` seconds.
- `probe_manifest_v2()` returns the exact fixed slice, not an arbitrary caller-selected subset.
- `validate_probe_receipt_v2(receipt, *, expected_binding, frames, expected_context)` checks one fixed item against raw log/trace/maps/CUA evidence.
- `validate_probe_evidence_v2(receipts, trace_refs, *, expected_binding, expected_context, expected_before_map_ref, expected_after_map_ref)` additionally requires exact action order, three original frames, contiguous diagnostic event serials, fresh equal authority maps, and the entire interaction wall interval including scheduling gaps to fit 300 seconds. Results report actual logical/physical counts and remain consistency-only, with `runtime_authenticity_verified=false`, `standard_pair=false`, and `g_b2_granted=false`.
- `probe_schema_v2()` describes the distinct receipt/CUA shape. Actual UE markers remain `READBACK_FORMAT = universe-i15-probe-readback.v1`, because the retained C++ producer is unchanged.

Original `probe_manifest()`, `validate_probe_receipt()`, `validate_probe_evidence()` and `probe_schema()` preserve their old full-matrix semantics and 2/10-second call caps. Low-level receipt/evidence code is shared with explicit parameters; no temporary mutation of global versions or limits is used.

## Fixed root execution recipe

Before dispatch, use current source/binary/build pins and independent ready review. Freeze empty-grant existing owner/pins; original authority stays at trusted `(tick,revision,watermark)=(1,2,2)`. Root must use the approved controller with NoTrace, phase-specific isolated DDC, observer, actual wait, and stable writer barrier. P does not implement or certify that admission.

| Action | Ordered logical commands | Action cap |
| --- | --- | --- |
| `p1.startup` | automatic status/current Observe; no UI command | 60s startup |
| `p1.probe` | `UniverseDiagArm p1.probe`; `UniverseDiagReadback p1.probe png_and_guard`; prepared native Shot; `UniverseDiagDisarm` | 90s |
| `p1.history` | `UniverseObserveExact 0 1 1` | 25s |
| `p1.history_write_rejected` | Arm; real Space press/release; real R press/release; `UniverseDiagReadback p1.history_write_rejected released`; Disarm | 110s |
| `p1.final` | `UniverseDiagArm p1.final`; `UniverseDiagReadback p1.final released_and_restored`; Disarm | 70s |
| `p1.exit` | normal quit via CUA, actual parent wait and quiet seal | 40s shutdown |

Each ordinary logical command permits at most 20 seconds from controller begin to end, including all tool round trips, raw result handling, and controller snapshots. The four interaction action caps sum to295 seconds; full interaction wall interval must be≤300 seconds. Metal420/Native180/global900/2GiB remain controller/parent checks. There are exactly14 logical commands, **not14 physical operations**. Missing steps or a late result do not permit retries or retrospective cap increases.

`p1.probe` must read actual renderer `Metal`, `hdr=false`, positive viewport dimensions, preflush and ready quit guard before Shot. Use capture API prepare/collect/verify and its exact `Shot filename="ABS_UNIQUE.png" nosuffix` command only in a stable viewport. Capture ID is `p1.probe/png_and_guard`. No external screenshot, transcode, startup capture, or guessed Retina dimensions. A capture ref is consumed but full PNG validation and independent provenance review remain separate gates.

After `p1.history`, trusted remainsH2 `(1,2,2)` while selected remainsH1 `(0,1,1)` **through final and exit**; this slice never pressesH or returns to latest. The three actual requests must be exactly `status, observe(current), observe(history)`; no prepare/advance/initialize/retry. The two new original Observe responses must be independently replayed/reviewed after Metal. I18's exact3 cannot cover these bytes automatically.

Real Space/R in the active viewport must reach the actual UE handlers exactly once each. The rejection markers require `handled=true`, `rejected=true`, reason `history_read_only`, counters incrementing by1, both keys released and `can_write=false`; final readback requires released keys, unpaused, restored visibility/FPS. Queries or idle unchanged maps cannot stand in for input callbacks. Camera, visibility, FPS changes, pause changes, held chord, full matrix and G-B2 remain deferred.

## Receipt assembly contract

Obtain each action item and command/`step_id` from `probe_manifest_v2()`. Keep logical receipt `command` equal to its fixed manifest template; bind actual expanded native Shot command through capture preparation/command receipt and original CUA evidence. Use one CUA JS bundle per logical command where appropriate; list every physical open-console/type/submit/close/focus/AX operation in actual order. Do not hide extra calls or substitute internal JS duration for the controller interval.

The top-level receipt uses the existing exact fields (`RECEIPT_FIELDS`): format/action/binding, separate trusted/selected triples, one controller clock, begin/end times, unique before/after map refs, pinned raw log with offsets, trace range, CUA ref, ordered checkpoint list, image_checks. The CUA public document is:

```json
{"format":"universe-i19-probe-cua.v2","binding":{},"action_id":"p1.history","clock":{},"calls":[{"step_id":"p1.history/00","command":"UniverseObserveExact 0 1 1","started_monotonic":0,"completed_monotonic":0,"raw_tool_ref":{"path":"ABS-public-original","sha256":"SHA64"},"log_before_offset":0,"log_after_offset":0,"physical_operation_count":3,"physical_operations":[{"operation":"pressKey","arguments":{}},{"operation":"typeText","arguments":{}},{"operation":"pressKey","arguments":{}}]}]}
```

This is a shape example, not runtime evidence. Actual operation names/arguments/results must match real CUA use and be reviewed against the raw bundle; the validator cannot authenticate an author's prose. Physical count must equal a nonempty list's length (bounded32 per logical call); startup has no calls. Full result sums these counts independently from14 logical steps. Actual physical timing may be retained in raw tool output, but receipt ordering/cost always uses the common controller clock.

For each checkpoint preserve `stage/log_start/log_end/read_monotonic/map/command_index/event_serial`; native diagnostics additionally bind origin and increasing native serial. Expected origins are query for probe/final, release/release/query for history rejection. Logs/trace/maps must be actual new originals, not json.dumps replacements of worker responses. Read each required event before the following logical command, with exact fresh log offsets and separate map refs. Do not stamp a guessed event time.

Root may use controller `begin_action/end_action`, `ready/refresh`, and existing capture API directly; no new CLI command is required by P. `raw_tool_ref` covers the actual whole bundle. Refresh observation after current/history changes and use the matching observation ref for capture. Final capture verification additionally requires the actual before-exit receipt and normal wait/quiet evidence; provisional collection is not final acceptance.

## Checks actually run

`PYTHONDONTWRITEBYTECODE=1 python3 -m unittest tests.test_universe_iteration_probe_slice tests.test_universe_iteration_probe -v`:23 tests passed, unittest reported0.460s. Nine new directed tests cover measured-style12-second vs20-second boundary, physical count omissions/mismatch, final selected/trusted distinction, real callback origin/reason/counter evidence, forbidden extra requests/deferred actions/missing stages, scheduling gaps, stale maps/log bounds, explicit schema separation. Fourteen legacy probe/preparation tests also passed. All data were synthetic CPU fixtures, never runtime proof. `git diff --check` passed before delivery.

Recommended next action: independent diff review, C2 admission integration using this exact API/manifest, final CI and root preparation review. Only then dispatch the one bounded Metal+new-response Native run. Keep the original full probe and broader acceptance gates open regardless of this slice's later outcome.
