# I11A Universe host construction

Status: implementation prepared; CPU and compile checks pending.
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
