# I14-D: opt-in actual diagnostic producer and separate action contract

Parent I14; fixed input `729dcdcfd907fa8214d544543e413eb27e763daf`. Branch
`codex/i14-diagnostics`, worktree `.worktrees/i14-diagnostics`. Native source was
separately committed as `31e38eb2b4367b272beda92a4b40a98212027468` for root's independent
build. Later Python/report changes do not change those native bytes. Root review,
official compilation and integration remain independent checks.

## Delivered behavior

Diagnostics default off. Explicit opt-in adds only local diagnostic state, read-only
sampling and bounded log records; it does not send worker requests, initialize, mutate
authority or inject UI input. Existing business gate decisions and protocol remain.
Actor changes are one const getter over its actual owned proxy array, not a scene scan.
Invalid identity, unverified projection, stale epoch, busy/unknown or unsupported phase
cannot emit a readback. Reconnect, channel failure and EndPlay clear cached identity;
a same-epoch worker/generation mismatch latches diagnostic failure until a new epoch.

Launch-only environment whitelist for R to map from the validated card:

| Variable | Required value |
| --- | --- |
| `EDGEWORLD_UNIVERSE_DIAGNOSTICS_V1` | exactly `1`; absent or other value disables |
| `EDGEWORLD_UNIVERSE_DIAGNOSTIC_RUN_ID` | 1–128 ASCII alphanumeric, `_` or `-` |
| `EDGEWORLD_UNIVERSE_DIAGNOSTIC_SOURCE_SHA` | exact lowercase40-hex source declaration |
| `EDGEWORLD_UNIVERSE_DIAGNOSTIC_SESSION` | initialize or existing; must agree with actual initialize launch flag |

These are **launch declarations**, not a self-authenticated source/run. R must correlate
card/source/build/binary receipts and actual command/environment. This PR does not change
old R12 environment filtering or add an unreviewed launch route. World/root come from
verified public pins; host PID is `GetCurrentProcessId`; worker PID/generation are saved
only after token/parser/observe/asset/projection validation of the actual response.
Trusted current head comes from fresh status state; selected history comes from the
verified observation. No owner config or key is opened by diagnostics.

Readonly Execs `UniverseDiagArm <action_id>`, `UniverseDiagReadback <action_id> <stage>`,
`UniverseDiagDisarm` accept only whitelisted action/stage labels, never PID/head/state/
counter/rejected values. They change no world or authority state. Arm captures initial
camera/visibility/FPS/pause readbacks. Other query stages read synchronously; pause
sampling uses actual `IsGamePaused` with no dependence on PlayerTick. No input is marked
`bExecuteWhenPaused`, and no transform is rounded or silently restored.

Actual sources: camera rotation plus actual ViewTarget IDs; owned proxy IDs and hidden
flags; `GEngine->GetMaxFPS`; `UGameplayStatics::IsGamePaused`; current key-down state;
preflush command flag plus actual diagnostic viewport/window/Slate delegate binding.
The quit guard is a readiness predicate, never proof of actual normal exit. Final FPS
compares with the initially sampled actual FPS; visibility uses actual current proxies.

### Handler evidence and held transition

Only real controller key binding entrypoints increment SpacePressed/Retain counters.
Console UniverseAdvance/UniverseRetain do not manufacture key events. Each actual press
records handled/rejected/reason and exact counter increment. Real Space and R release
callbacks emit respective history rejection stages; queries cannot fabricate those stages.
The existing `universe-i13-history-rejection.v1` typed state/counter requirements remain.
No input, no release, wrong reason or early stage means missing/contradictory evidence.

For held input: actual history Space handler → held_history; actual H handler follows
existing Latest behavior → verified current observation callback while Space remains
actually down → held_current; actual release → released. Early release cannot skip stages.
The producer does not enforce chord order, extend a hold, synthesize H, or issue a second
observe. An unsupported/wrongly ordered chord can fail and may trigger ordinary business
behavior; actual extra requests must be rejected, not hidden. Tool capability stays no-go.

Markers retain prefix `EW_I13_READBACK ` but explicitly use payload format
`universe-i14-readback.v1`, with the I13 public binding/head/state fields plus
`event_serial` and `origin` (query/input/verified_observation/release). Serial is monotonic
within this producer instance, stages cannot replay/skip, a marker is capped64KiB and
there are at most256 per instance. No controller timestamp is represented as native
event time. Native tests may use synthetic state, which is not runtime proof.

## Python v2 API and evidence contract

Old v1 source prefix, entrypoints, exact camera rule, schema and caps are unchanged.
New exports in `actions.py`:

- `manifest_v2()` / `schema_v2()` return [fixed manifest](manifest-v2.json) and
  [machine schema](receipt-v2.schema.json), format `universe-i14-actions.v1`.
- `validate_receipt_v2(receipt, *, expected_binding, frames, expected_context)`;
  frames must be from `load_trace`, not caller-created evidence.
- `validate_session_v2(receipts, trace_refs, *, expected_binding, expected_context)`
  loads indexed native raw chunks and applies exact session order, full request/frame
  coverage, bindings, original-result same-closure retry, maps, events and command evidence.
- `readiness_v2(capabilities, *, expected_source_sha)` keeps explicit missing capability
  no-go and validates timing reviews against the v2 manifest. Structural review files
  are not authenticated merely by distinct reviewer/owner strings: R must authenticate
  review origin/authorization and its raw evidence against the exact manifest.
- `action_advice_v2(action_id, *, ui_allowed, quit_due, stop, remaining_seconds)` returns
  no further commands on denial/closing/insufficient allowance. No API executes UI.

S1 has17 actions and61 actual CUA calls, business requests20. S2 has5 actions and14
calls, business requests5 and no writes. Each real DiagArm/Readback/Disarm and every
required stage's native Shot is an explicit command with a cap; none is hidden as a
passive wait. Proposed interaction item caps total274s/100s, inside the root's provisional
360s/100s limits. Remaining passive map/marker/image/restore allowances are explicit.
This allocation is **not measured feasibility**, and a larger budget proves no capability.

V2 receipt uses the existing top-level binding/clock/map/log/trace/CUA/image fields.
Checkpoint shape is exactly:

```json
{"stage":"held_current","log_start":100,"log_end":400,"read_monotonic":42.0,
 "map":{"path":"ABS","sha256":"SHA64"},"command_index":1,"event_serial":8}
```

`read_monotonic` is controller time when the event was read, not when UE handled it.
Native chronology comes from serial plus byte offsets in the actual bound UE log.
Long-chord stages all reference one actual call index, with one raw tool record and
before/after log brackets; a marker may occur before the long call returns. No synthetic
three-call sequence or UE/controller clock subtraction is used. Ordinary observed/native
Success/LogExit lines use event_serial=null. Every checkpoint has its own complete map;
reads after a long call do not claim the map was captured at native event emission time.
Actual trace proves whether any write happened in the interval; V/R authenticates sources.

CUA raw artifact format `universe-i14-cua.v1` retains binding/action/clock/calls; each call
has command, started/completed controller times, raw_tool_ref and log_before/after_offset.
All calls obey their cap and10s ceiling. Ordered marker/query association, exact command
coverage, actual observed/native test lines, independent expected binding, full readonly
maps, release/restore and exact trace behavior remain mandatory.

Each required image is exactly `{capture_id,stage,capture_ref:{path,sha256}}`, with
capture_id=`action_id+'/'+stage`. Every required stage consumes exactly one image and
none is inferred from list order alone. V matches independently expected action/stage/
trace/capture and invokes C; B only integrity-checks the reference. Arbitrary capture
bytes or a passed report do not establish original PNG, Metal or proof binding.

Only v2 uses shortest angular distance per axis≤1e-4 degrees for camera restoration.
It requires the same Camera/ViewTarget and yaw movement of15 degrees within1e-4, with
pitch/roll unchanged within that tolerance. Original values remain unrounded; legacy v1
still demands exact equality.

## Check, limits and Act

[Check summary](check-summary.json): initial21 legacy+10 new CPU tests passed (31 total,
1.827s). After making every stage Shot an explicit call,10 affected v2 tests passed
in0.766s. One intermediate negative test used a hardcoded call index invalidated by the
new Shot insertion; it was corrected to read the fixed manifest mapping, then passed.
Directed cases cover exact20/5 and charged queries, complete synthetic sessions, real
single-call event mapping, fake origin/serial, stale raw bracket, missing query, reused
maps/altered closure, capture identity, angular wrap/tolerance and guard no-go. Synthetic
fixtures do not establish actual tool input or UE behavior.

Native test **source only**, not executed here:
`edgeWorld.UniverseHost.Diagnostics.IdentityAndDefaultOff`,
`…HandledInputAndOrder`, `…PauseReadWithoutTick`. They exercise helper default/invalid
configuration/epoch identity/ordered input counters and a synthetic local paused world
without StartPlay, transport, solver or Tick. They do not substitute for real controller
input or the full live GameMode path. Official build is root-owned with independent
receipts; this agent ran no build or Native tests.

No UE, solver, worker, UI, provision or real key access occurred. Current
[readiness](readiness-no-go.json) is no-go: actual readback capability/authorized review,
chord behavior, PNG/quit evidence and timings are not established by source or CPU tests.
Root must inspect native compilation, independently review v2/source/schema and compose
L/V; missing evidence stays inconclusive/no-go. I12 FAILED2566/1200 and I13 no-go remain.

## Root-owned official compilation receipt

Root reports official build attempt2 of native source31e38eb completed with actual
parent wait0 in33.408s. Both attempts totaled52.974s below the180s active-build cap.
Public originals: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I14D-20261102-native-build2`.
Attempt1 exit6/PCH-missing evidence remains retained. Attempt2 used
`--build-only --universe`, passing-NoUBA, but its successful log still reported an
Unreal Build Accelerator local executor. This does not prove UBA was disabled or
establish a unique cause for attempt1. Only compilation is accepted by this receipt.
No UE, Native test, Metal, held-input, PNG or exit runtime gate was executed.
Native source stayed unchanged throughout both attempts and this final report.
