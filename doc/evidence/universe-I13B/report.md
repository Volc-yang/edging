# I13-B — passive action manifest and evidence validators

Parent I13. Fixed input `60857c04fa13db7b23a1f9f2668dc22842196fe9`.
Worktree `.worktrees/i13-actions`, branch `codex/i13-actions`; implementation delivered
for independent root review, not yet integrated or accepted. No UE/Genesis/worker/UI,
provisioning, real key access or shared runner/verifier modification occurred.

## Outcome and limits

`actions.py` provides a fixed ordered manifest, strict public artifact references,
native raw trace reassembly, per-action evidence checks and an explicit readiness no-go.
S1 has20 actual requests (init4/retain4/physical4/retry3/history3/back-to-history1/held-to-current1).
S2 has5 and is strictly readonly revisit. All nine readonly kinds are covered across the
pair. S1 proposed interaction caps total240s; S2 total100s. Startup and shutdown are
separate phase/charged_budget entries. These caps are proposals, not measurements.
Command and passive map/marker/image/restore allowances are enumerated in the manifest.

**Current readiness is no-go.** `readiness({}, expected_source_sha=...)` reports all five
missing capabilities: readback_markers, cross_call_hold, png_contract, quit_guard,
timings. Current UE source has no proposed structured diagnostic marker. The known CUA
interface offers pressKey with duration, not independently established cross-call
keydown/keyup; a chord is not accepted here as demonstrated hold capability. No240s
feasibility, original-PNG runtime pass or normal UE exit is claimed.

**Evidence consistency is not authenticity.** Capability review files are public
references that R must authenticate against actual evidence and an authorized independent
review. Different owner/reviewer strings alone do not establish independence or truth.
Even with all structurally valid capability proofs, the result is only
`ready_for_R_review`, `runtime_verified=false`, `g_b2_granted=false`. The receipt/session
validators likewise return `consistent_requires_R_and_independent_review`. Hashes detect
changed artifacts, not forged origins; synthetic fixtures are not live proof.

## Frozen machine contract and API

- [Fixed manifest](manifest.json) is emitted by `manifest()`; each call returns fresh data.
  No caller may substitute a custom manifest to remove gates or loosen caps.
- [Receipt JSON Schema](receipt.schema.json), emitted by `schema()`, freezes exact nested
  reference/binding/head/clock/log/checkpoint/CUA shapes. Cross-artifact semantics below
  remain mandatory Python checks; JSON Schema alone is insufficient. `state` is additionally
  checked by action kind. R must review this B schema extension before integration.
- `reference(ref)` reads only one explicitly named public `{path,sha256}` artifact, caps
  reads16MiB, rejects symlinks, changed inode/content, private canonical key/owner filenames,
  duplicate JSON keys and nonfinite JSON. There is no directory-recursive input API.
  R must enumerate only public artifacts; arbitrary naming is not a secret classifier.
- `load_trace(refs, *, expected_binding)` requires one complete native transport with
  raw/meta files explicitly indexed, contiguous serials, fixed host/worker/generation,
  fresh request IDs, full writes, ordered chunk reassembly, exact response association,
  and one normal exit0/reaped/trace-complete worker. Native decimal FString serial/generation
  fields are normalized explicitly; bool is rejected. It returns actual request/response frames.
- `validate_receipt(receipt, *, expected_binding, frames, expected_context)` checks a fixed
  action and referenced raw evidence. `frames` must come from `load_trace`; callers do not
  gain a raw trace validation by passing arbitrary Python frames directly.
- `validate_session(receipts, trace_refs, *, expected_binding, expected_context)` is the
  complete entrypoint: loads raw trace, requires exact manifest order, no missing/extra/reused
  frame ranges, one controller clock, no overlapping action intervals, exact20/5 count,
  and same-closure retry with fresh ID and exact original response result.
- `expected_context` is independently supplied public `{principal,trust_anchor,
  expected_build,expected_options}`. `trusted_head` and `selected_observation` are distinct.
  Full authority/proof/HMAC verification remains the independent existing verifier's job;
  B checks wire context, public head bindings, exact selected triples and closure linkage.
- `readiness(capabilities, *, expected_source_sha)` consumes refs keyed by the five capability
  names above. Each proof has exact fields `format=universe-i13-capability-review.v1`,
  `source_sha,capability,reviewer,owner,decision,evidence_refs,action_upper_seconds`.
  Decision is pass/fail/inconclusive; every proof needs raw refs. Timing proof covers every
  interaction action with a usable upper bound within its fixed cap; other proofs use an
  empty timing dictionary. Missing/failed/inconclusive evidence means no-go.
- `action_advice(action_id, *, ui_allowed, quit_due, stop, remaining_seconds)` is a pure
  guard adapter. Denial/quit_due/stop/insufficient whole-action allowance returns no commands,
  only advice to release inputs then normal quit. A/R authenticates guard inputs; B never
  performs release, quit or any UI operation. Raw tool calls must fit their fixed command
  cap and the frozen10s maximum.

Malformed/missing/contradictory public evidence raises `Invalid`; the module does not
silently downgrade failed evidence to success. No output writer or CLI is introduced.
All import-time operations are definitions/constants only.

## Checkpoint semantics

Every receipt supplies independent expected binding, canonical map refs before/after,
log device/inode/prefix SHA/before-after offsets, a half-open real frame range, CUA raw
call refs, controller timestamps, ordered checkpoints and required C image-check refs.
Every checkpoint references its own complete map. Captures cannot reuse a map path within
or across actions; equal map bytes remain valid. The checkpoint's `after_command` index
links it to a specific CUA command, or-1 for the initial readback. It must follow that
command's completion and precede the next command. Missing after, stale/overlapping log
ranges, wrong world/PID/head, premature completion, extra requests or interior readonly
map changes are rejected. Image-check refs are only integrity checked by B; R must invoke
C to validate their actual PNG/source/time semantics and associate each stage.

Existing observed and exact Automation Success lines are checked against fresh bound UE
log ranges. Observations are additionally linked to exact request/response heads. The
initial status must be NOT_READY/UNINITIALIZED with not_attempted commit, followed by
explicit initialize confirmation, status and observe. Retain/weak intents and prepare→advance
closure binding are checked. Retry has no prepare and no authority change; history targets
are exact, not inferred from directories. Native tests add no Universe requests.

### Proposed read-only diagnostic interface — not implemented

Kinds lacking current machine-verifiable readback require one complete bound UE-log line:

```text
EW_I13_READBACK {"format":"universe-i13-readback.v1","binding":{...},"action_id":"...","stage":"...","trusted_head":{...},"selected_observation":{...},"state":{...}}
```

This is an interface proposal for R to Act into a separate narrow product task. B does
not emit it, install a command, or treat a receipt's completed boolean as this marker.
Its actual origin/UI correctness still needs independent review. Required typed states:

| Kind | Ordered stages and checked state |
| --- | --- |
| probe | png_and_guard: quit_guard_ready=true, preflush=true; never means already exited |
| camera | before/moved/restored: same camera_id=view_target_id, finite rotation[3], actual change then exact restoration |
| visibility | before/hidden/restored: exact same nonempty proxy IDs; bHidden false/true/false |
| framerate | before/changed/restored: finite original max_fps, changed to30 and differs from original, then exact restoration |
| pause | before/paused/restored: actual paused false/true/false |
| history_write_rejected | space_rejected/retain_rejected/released: history01, released keys/can_write=false plus versioned actual handled/rejected input events and continuous handler counters; no prepare/advance in raw interval |
| held_input | held_history/held_current/released: Space true/true/false, can_write false/true/true, selected01/12/12; only one observe, no prepare/advance |
| final | released_and_restored: Space/R released, paused=false, visibility_restored/fps_restored=true |

Booleans are not accepted as integers or vice versa. readonly full files maps, actual
input-origin raw refs and state readbacks are all required; no single one establishes
human input semantics. History/revisit separately require each exact observed marker,
map and image. Exit action's LogExit marker proves intent only: R/A must independently
validate real UE/launcher wait, worker exit, normal completion, observer and seal.

## Do / Check / Act

Changed only `scripts/universe_iteration/actions.py`, its directed unittest file and this
owned evidence directory. [Check summary](check-summary.json) records source/test hashes.
17 synthetic directed tests passed in0.993s. Cases cover exact counts/budgets/order, both
synthetic sessions, missing after/stale marker/wrong identity/head/clock, readonly interior
mutation, per-command ordering/deadlines, raw trace chunking/serial/generation/PID/hash,
unexpected requests, abnormal worker, same-closure retry, altered case/history request,
incomplete release/restore, bool confusion, symlink/private filename guards, readiness
no-go and guard denial. No full suite was run locally; CI/independent root review remains.

A separate readonly compatibility replay of actual retained I12 repair trace reconstructed
six operations: status/observe/prepare/advance/status/observe. This only confirms native
serial/chunk/lifecycle format compatibility. It is not a new runtime or I13 acceptance.
During construction a nested schema literal briefly caused a SyntaxError; splitting it
into named schema records corrected it before the final17-test pass.

Code Complete2 checks applied: requirement/order/interface mapping (Ch5/7), defensive
external-data validation (Ch8/12), negative and boundary cases (Ch22), and explicit
integration limits (Ch29). No unrelated refactoring or new dependency was introduced.

Act: root independently reviews B diff/schema/API, R composes A/B/C, emits honest no-go
for missing actual readback/hold/timing evidence, then opens only the smallest affected
follow-up nodes. I12 resource FAILED2566/1200 remains unchanged. Do not launch solely
because this tool PR merges; no run card is granted by these APIs.

## Root review correction: prove actual rejected input handling

Root identified that released keys/can_write=false plus an empty write trace cannot
prove Space/R actually reached UE. The initial validator was insufficient here. The
corrected state has `format=universe-i13-history-rejection.v1`, the three strict boolean
flags, `handled_input`, and `handler_counts={SpacePressed,Retain}`.

At space_rejected the actual marker must record key=Space/event=pressed/handler=SpacePressed;
at retain_rejected it must record key=R/event=pressed/handler=Retain. Each has
`handled=true,rejected=true,reason=history_read_only,counter_before,counter_after`. Counters
are exact nonnegative integers (no bool), and after must equal before+1 and the state
handler total. Space handler count must stay unchanged across the R action; R's before
count equals the earlier R total. At released, handled_input=null and both totals equal
the preceding stage, with both keys released. The bound UE log, CUA command association,
complete per-stage readonly maps and zero write requests are still required.

The schema now includes rejected_input/history_rejection_state definitions and applies
the latter specifically to the history_write_rejected readback. Same idle key/write
state with no actual handled event is rejected. Negative cases also reject unhandled
or accepted events, wrong key/reason, unchanged/skipped/bool counters and inconsistent
release totals. Five affected directed CPU tests passed in0.205s, including the complete
synthetic pair and schema checks; the earlier17-test pass belongs to the initial
implementation. No full suite or new runtime was run for this correction.

This remains a proposed diagnostic producer contract, not an implemented UE capability.
Current readiness remains no-go; root must authenticate actual producer/readback origins.

## Independent review correction: exact retain intent

u9 found the initial B check only required an integer retain tick_delta, and the
synthetic retain fixture incorrectly used case_id=weak. The validator now requires
exact tick_delta=0 and an explicitly present case_id=null, matching the existing UE
strict parser. The fixture now carries actual null. Separate negative tests reject
nonzero tick_delta and non-null case_id; those tests plus the complete synthetic pair
passed (3 affected tests,0.153s). No protocol relaxation or runtime occurred.
