# I11A Universe host construction

Status: CPU and control/parser checks passed; raw transport acceptance pending.
Base `761a967`; this report is not a G-P1/G-B1/I12 acceptance.

## Plan / scope

Frozen v0.2 wire, exact12 public pins and I10 module CLI are consumed explicitly.
Default legacy builder, launcher mode and existing Causal/Chaos files remain.
Owned sources: seven new Host files, JsonlClient h/cpp, UniverseObservation h/cpp,
launcher and existing launcher test file (13), plus this evidence directory.

The owner launcher calls `python -m engine.universe_authority.worker
--owner-config ABS --print-public-pins` from its owning repository. Only the
trusted export reads private config. Canonical public ASCII pins are written
once/noLF/0600/nlink1 into a new0700 viewer directory; their SHA accompanies
UE's file path. UI never reads private owner config contents or key material.
Fresh owned-worker status is the only published HeadBinding source. Explicit
`--universe-initialize` enables a single initialize request after UNINITIALIZED;
worker private permissions/mode still decide. No missing-head auto-init exists.

## Do

Universe transport launches only the owning module plus owner-config, keeps raw
UTF8 with `ReadPipeToArray`, enforces 1MiB framing bounds without CRLF trimming,
labels owned PID/generation and requires first-channel status. The Mac installed
implementation reads at most32768B per call (MacPlatformProcess.cpp:1445).
No FString decoding precedes strict parsing; legacy Exchange remains separate.

New strict control parser shares the existing duplicate-key/UTF8/integer lexer,
checks status/prepare/advance/initialize/error exact envelopes and public pins,
context/IDs/refs/receipt shape, and fixed prepare expiry. It is not a signer or
an independent MAC verifier. Raw selected proofs retain prior (tick,revision)
from validated prior state, rather than guessing a predecessor numerically.

New pure session gate tracks epoch/serial/generation, authoritative head and
selection separately; cached prepare and exact signed closure survive reconnect.
Unknown actions require explicit refresh and exact retry, never replacement IDs.
History/unconfirmed/busy/unknown block new writes; Space is press/release latched.
1/2 choose weak/strong without a request, Space physical, R retain, [ verified
prior, H current; UniverseRefresh/UniverseRetry are explicit console actions.
Camera and HUD never issue simulation requests; Actor has no Tick or UE physics.

Projection applies SI→cm mirrorY, WXYZ→XYZW reflected quaternion, polar linear
and axial angular velocity transforms. Frozen shape dimensions come from the
verified config, never mass. Abstract development is separately labelled in HUD.
Editor-only I0A Collect(world) must return the exact asset-manifest-runtime
canonical bytes/digest with no graph gaps before loading declared proxy assets.
No installation mismatch fallback, cook/package/license/realism claim exists.

## Check plan / boundaries

Authorized CPU batch <=120s/raw16MiB with at most one justified targeted retry:
launcher mocks, shell syntax, existing composite record checks and independent
fixture validator; literal source/fixtures SHA before and after, commands/exits.
Launcher mocks supply public metadata only, not a world or physics record; C++
control/process tests explicitly use synthetic context and isolated mock module,
never a product fake flag or a relabelled Genesis result.

C++ tests prepared: strict public pins/status/control/error, prepare/commit refs
and stable IDs, same-tick distinct revision, old callbacks/unknown closure and
input gating, coordinate transforms, real byte-pipe CRLF/invalidUTF8/oversize.
The test child is a generated, isolated synthetic Python module. It is not I10.

UE build/NullRHI requires a separate root resource card (proposed <=300s/raw128MiB,
one targeted retry). No real Genesis/UE/GPU work has run in this implementation.
G-B1/I11B still needs exact I10B integration; real Metal/combined acceptance belongs
to independent I12. No author display run is part of this task.

## Act

Root reviews exact source/CPU evidence, then releases the compile/NullRHI window.
After PR review/CI/merge, root coordinates I11B/I12 and task cleanup. No self-merge
or worktree cleanup; generated outputs/evidence remain outside source commits.

## I11R capture-interface refinement (root accepted)

Added passive Universe-only trace under launcher-created0700 exclusive run path.
Request bytes, stdout chunks (including partial/malformed), separate raw stderr
chunks and write-result/completion metadata use exclusive0600 files. Metadata
pins UTC/monotonic time, owned PID, transport generation, event/request serial,
operation/request ID and raw byte count. No wire is rewritten or resent by trace.
A shared64MiB run budget survives reconnect; new requests reserve4MiB headroom,
and each pair of32768B reads reserves enough room before consuming bytes. Cap,
unsafe paths or write failures stop the channel; possible submitted commands
retain unknown status/exact closure. Partial trace artifacts are never overwritten.

Last committed closure/digest is retained independently of pending actions.
Owner-console `UniverseRetryLastCommitted` sends that same closure via the normal
current/history/ready/unknown/busy gate. `UniverseObserveExact(tick,revision,watermark)`
selects an exact proof; `UniverseRetain/UniverseAdvance` use existing action gates;
`UniverseProjectionVisible(bool)` and `UniverseCamera(yaw,pitch)` are view-only.
There is no automatic command clock, signer or runtime fake switch.

Places/routes/watercourse now produce bounded thin Cube/BasicShapeMaterial proxies
using only the audited content graph. Derived proxy count is recorded separately
from authoritative decoration D; old actors are replaced, not accumulated. No debug
material/LineBatch is introduced. New-mode movable directional light has no IES
or light-function content. These are technical geography, not realistic water.

CPU first source89dd303: shell syntax exit0, 13/14 launcher tests passed; sole
failure was mock /var vs /private/var path equality on macOS, while launch/pins
succeeded. Sourceadc6fd3 corrected that assertion via resolve(), also added explicit
focus-return gate. Unique targeted test passed, then previously unrun8 composite
record tests and independent67-golden/57-negative/5-proof oracle passed. Combined
CPU15.991s, source/fixture hashes unchanged per attempt. Raw directories:
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I11-20261102-host-cpu-attempt{1,2}`.
I11R adds a separately authorized CPU card<=120s/raw32MiB/one targeted retry;
checks pending. No UE build/window has yet run; final source is still uncompiled.

## Bounded check results and current acceptance split

I11R CPU at `7738638cf48ca325bbfaef22dd3b9150d579c8f0` passed shell syntax and
all15 launcher tests, real exits0/15.769s, no I11R CPU retry. Inputs were stable.
The prior I11A sole targeted retry and original /var canonical-path failure are
retained independently; no old failure was overwritten or called a pass.

Root then granted UE5.8.3 NoUBA plus one compact actual-app NullRHI selector:
`Automation RunTests edgeWorld.UniverseHost+edgeWorld.UniverseObservation.StrictV02; Quit`.
The '+' splitting was verified in installed AutomationCommandline.cpp:135;
this avoids AssetAudit and does not create a Metal/Genesis scene.

- Source7738638 first build PID30423: exit6/46.189s, no editor launch. Two
  construction defects were found: calling ToSharedRef on an existing TSharedRef
  and a missing parenthesis in the request builder. All new Host files compiled.
- Independent i6 review also found cached prepare result lacked exact watermark
  semantics. A shared ResultRecord guard now checks watermark=revision and
  tick<=revision in prepare/advance, retaining valid old-result/current-HEAD
  separation. Added positive/negative control cases passed subsequently.
- Root's I10 integration review required the explicit one-shot initialization
  guard to accept NOT_READY as well as UNINITIALIZED for an owner-registered
  empty root. Readonly/existing mode still never auto-initializes; worker owns
  permissions and existingHEAD refusal. Pure gate tests passed subsequently.
- Corrected source `d145f2f`: unique authorized targeted build PID31281
  exit0/11.383s. Actual UnrealEditor.app process PID31403 initialized and ran:
  `UniverseHost.Protocol` Success; `UniverseObservation.StrictV02` Success;
  `UniverseHost.TransportRaw` Fail. Real app exit3/25.072s. Total original UE
  window224.343s including first attempt/wait, <300s. Source/fixtures and
  pre/post actual binary SHA were unchanged during the targeted checks.
- TransportRaw's synthetic harness used relative ProjectSavedDir-derived paths.
  The production absolute/private trace-path guard rejected all four cases
  before child launch or request transmission (trace_limit_or_unsafe). No claim
  of raw pipe/trace acceptance can be made from this attempt. Exclusive sentinel
  files were preserved, but that alone does not establish transport acceptance.
- Source `24f0637` only changes harness root to ConvertRelativePathToFull; no
  product changes. This latest test source has not yet been compiled or run.
  The unique UE targeted allowance is consumed; no unauthorized third run occurs.

Exact immutable raw directories and raw-index SHA256:

| Directory under /Volumes/DevSSD/Unreal/Projects/EdgeWorld/ | SHA256 |
| --- | --- |
| I11-20261102-host-cpu-attempt1 | 790dedfaf82698b5608cc059dbb4dec4dfdc875fbd8f5a2a2823fcd2ca1fa48d |
| I11-20261102-host-cpu-attempt2 | b4520bf692e74cbe9cda40cb20001aa3ee9c9177623307b57b4f848c7e618b2b |
| I11R-20261102-host-cpu-attempt1 | e1c97a2d3c18c4582c7e0dd6c2909245f79615b1bb17ac1c697228022d75a869 |
| I11-20261102-host-ue-attempt1 | b88bd023ea16875d6b0a7787aeb06effdf73972b6d5cdca04193206cb31c54ae |
| I11-20261102-host-ue-attempt2 | 386584e2a4b1dc9b795c3d3c68566f967e83fdde66e833d405d61b8092123a03 |

UE aggregate raw<2MiB; generated outputs have separate output-links provenance
and produced binary manifests. Five DevSSD output links and generated DefaultInput.ini
remain untracked and excluded from commits. Raw originals include commands/env,
source/fixture/binary SHA, true PIDs/exits, engine/stdout/stderr logs, report and
isolated synthetic test files. No unrelated process was killed. Both actual build
and app processes ended; no third attempt or real world/physics scene ran.

## Open acceptance and next task boundary

I11A is partial pending explicitly scoped TransportRaw recheck and root review/CI.
I11B must additionally record actual worker lifecycle: existing StopProcess closes
pipes/handles without an explicit return-code record or bounded tail drain. PID
absence is not evidence of worker exit0. Root reserved a separate Universe-only
EOF/tail/GetProcReturnCode/exit-trace change and resource card; it is not folded
into this already-consumed check window. Legacy remains outside that change.
No fake/synthetic data can pass I10B/G-B1/I12 real combination acceptance.
