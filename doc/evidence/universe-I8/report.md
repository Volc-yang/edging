# I8 physical provider — execution report

Status: **isolated physical checks passed** at exact source `9270349fab51f8495cfc8d39042496ce451a2522`. The runtime provider's `propose` through an actual world/command/Store, UE presentation and combined integration gates were not executed. This report does not convert a physical probe into a committed world.

## Fixed inputs and environment

Genesis1.4.3, Python3.12/ABIcpython-312, Apple M4 Pro, Metal, solver precision32, seed7. The exact two-body I7 parameters remain unchanged: one free Sphere, one fixed Box, eight 0.01 s steps per physical advance, weak/strong gravity cases. Public post-build options are measured rather than guessed from pre-build defaults.

- Build record: `289d4f525321297c5fefb0452629ec008d0a39a52cf889da37f357fcc13e2634`.
- Adapter source bytes: `15f5b96bb0381781d0357eb93510622afe6ec3d5caf60adb5ed8190ff6abb192`.
- Post-build options record: `7165e3f027a5d5538e091e8bd48e2a738b7757401aa827a3ff0aacbb454044ed`;4365 canonical bytes, all five public dump groups retained, support material checked equal.
- Owner's seven public inputs: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I8-20261102-owner-freeze-attempt2/`, index SHA `3bffbea2b8ab32e60b9929b17c8b2614a16054dd797a6c219f0a3365c785f3bc`. Owner key stayed external and was never passed to the provider. The registered authority path remains uninitialized; no State/HEAD was created.
- Installed Python tree:264 files;19 critical sources include SceneOptions, fixed/mesh inertia and actual GJK/constraint-default resolution. Runtime evidence independently hashes37 native/METADATA files totaling498,911,852 bytes before/after; hashes and all source/config inputs match. This records the measured installation, not a native ABI portability guarantee.

## Actual checks

The sole corrected physical matrix completed in 80.645 s, exit 0. It generated66 physical families: initial,32 weak,32 strong, and one resume family. Each new advance loaded the exact predecessor checkpoint; all generated files have their own byte SHA/descriptor, with sizes262460…263574 bytes (below8MiB).

| Check | Actual result |
| --- | --- |
| First weak8 steps | D=−7mm |
| First strong8 steps | D=−35mm; `−35 < −7 <= 0` passed |
| Weak last four | gap≈−0.0000139371m; abs(vz)≤2.0e−7m/s; one live support contact each |
| Strong last four | gap≈−0.0000679463m; abs(vz)≤3.0e−7m/s; one live support contact each |
| Dynamic mass |4.188790321350098kg, bits `4010c15240000000`; approved analytic tolerance passed |
| Fixed support inertia sentinel |actual+0, bits `0000000000000000`; not fabricated geometric3200kg |
| Zero-step asymmetric pose calibration |approved position/quaternion/zero-velocity checks passed; pristine checkpoint restored |
| Additional tick16→17 branch |complete restored sample and resumed sample bits plus D matched uninterrupted strong arm exactly |
| Physical step count |520 total:2×32×8 plus one additional8-step recovery branch |

The calibration proves the bounded public pose roundtrip, not nonzero velocity frame semantics or actual UE handedness. Physical samples preserve actual float32 results in binary64 containers. D uses exact separate Decimal conversions, precision2000 and half-even rounding, rather than a binary64 subtraction/multiplication shortcut.

## Preserved attempts and evidence

All paths below are unique original directories under `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/`. Indexed bytes exclude the index file itself. Failures were retained and did not reset the resource allowance.

| Attempt | Outcome | Indexed files/bytes | Index SHA256 |
| --- | --- | --- | --- |
| `I8-20261102-static-attempt1` |old-source grammar + stdlib audit passed; old B now ineligible |17/58566 |`69f926915bcf072e612fc59db4abad8532a261ecc347e8508f16a05b6658f9be` |
| `I8-20261102-static-attempt2` |authority-scratch/input-failure targeted checks + new audit passed; later superseded B |42/92133 |`12faaf1a813d69126d61c4e06cb974648ea62c8879180c5d0cedd6c562aef52d` |
| `I8-20261102-options-attempt1` |pre-build public export passed; actual Scene mismatch later invalidated its runtime use |23/377536 |`3271379233d51a0c9a769f7eed23a6b5599af1ac53fe6ff937006a2799477e4a` |
| `I8-20261102-physics-attempt1` |exit 1, BUILD before sample/checkpoint/step; actual-diff capture missing |23/376236 |`5299d78b920a0a751e0f7b60449cd25ff8991d2f589774b4d986b6836b152cf2` |
| `I8-20261102-diag-attempt1` |separately approved zero-step public diagnostic exposed six differences; not candidate acceptance |22/381749 |`ac05d7a233f7b8e347bd5f860b08a03de74310ee4d283805fd875c6fd78f715c` |
| `I8-20261102-static-attempt3` |corrected post-build source/grammar, unchanged parameters and real build audit passed |17/60306 |`9cf7d2dbb67bc68abad065dd8fd61f82c2d7e2acc1fbad4455612cf5456f29fc` |
| `I8-20261102-options-attempt2-resolved` |real zero-step post-build export passed |23/374067 |`0f479d1bc4b54d81d02806043cdba5a969e721b97c5f99187df3bc62c08b2076` |
| `I8-20261102-physics-attempt2-resolved` |corrected isolated physical matrix passed |292/53119421 |`456195d2ba6a25bba0a60007d5545d7091d02feb9c39e46b0d67c3eb23552e72` |

The first mismatch was not ignored: SDF resolution and five rigid options are resolved during public Scene/build. Corrected code preserves the requested max_contacts32 and exports the actual effective5, without hardcoding the six observed outputs. New B/O were independently reviewed and the owner explicitly issued a fresh context before the corrected matrix.

Every runtime attempt retained argv, PID/process group, exact source/input hashes, complete stdout/stderr, actual exit and explicit `gs.destroy` result. Watchdogs were confined to owned process groups; no unknown UE/worker was terminated. Successful physics child26787 was reaped and runtime destruction succeeded. Total actual GPU windows≈97.687s against600s; retained runtime originals≈55MB against1GiB. The first physical failure and diagnostic remain counted.

## Completion and next handoff

Implementation, source audit, owner identity bootstrap and the bounded isolated physical matrix are delivered for independent review. No provider `propose`/real-world command admission, actual-world genesis initialization, Store commit, UE render, realism, shipping or cross-device repeatability claim is made. I10 must stage the actual resolved asset/world records, then exercise the public provider through the coordinator's single authority root; I12 owns combined acceptance. Normal process cleanup completed. The task worktree remains available until PR review/integration by the coordinator.
