# I8 — explicit Genesis candidate provider and finite physical probe

Status: isolated physical matrix **PASS** at source `9270349fab51f8495cfc8d39042496ce451a2522`; see [execution report](report.md). Provider.propose/full-world/UE integration remains unexecuted. Base `13899a2`; task ownership is `genesis_adapter.py`, `probe_universe_genesis_v0_1.py` and this evidence directory. E7 fixed-inertia-mass revision was integrated by ordinary merge before physical execution.

## Owner bootstrap and identity

1. Fix the adapter source with a normal commit. Use the installed Genesis venv Python and an explicit worktree `PYTHONPATH`; do not install or upgrade dependencies.
2. `audit` measures installed Genesis1.4.3 METADATA bytes, all installed `.py` path/SHA entries, critical source bytes, NumPy/Pydantic/Quadrants/Torch/Trimesh METADATA/version, Python ABI and the actual adapter SHA. This mode is stdlib-only and never imports Genesis. The package source-list hash encodes an external packaging index, so its >256 files do not bypass any record-array cap.
3. Owner reviews that exact build record and source index. Only after the separate GPU authorization may `options` import/init Genesis, build the exact two named entities through public Scene APIs with zero steps, and export all five complete `model_dump(mode='python', exclude_unset=False, exclude_defaults=False, exclude_none=False)` values. `SceneOptions` resolves inherited dt/gravity; public Scene.build then resolves geometry-dependent contact capacity, precision defaults, material SDF limits and other effective options before measurement. Support material is fully exported and compared to dynamic material. Floats become finite typed binary64, Enum values are explicit, tuples become arrays; unsupported values or an oversized record fail BUILD rather than being dropped or truncated. A zero-step identity Scene is built and destroyed in finally; no Scene.step/checkpoint/world record is created. Values are measured from public post-build objects, not copied from the diagnostic.
4. Owner freezes the actual build/options record digests into a new DeploymentContext, provisions any future authority key separately, and prepares the config/binding records with those pins. No public fixture key or static-declared defaults are used as runtime identity. The options bootstrap can exit before owner review, freeing its GPU window; the physical process remeasures everything independently.

`GenesisProvider(config,binding,*,scratch,context,build,options)` is a pure constructor holding defensive copies. Every initialize/restore/propose operation first remeasures installed source. It then exports all public options/morph/material fields from the current owned built scene; when no scene exists, it builds/destroys a zero-step identity scene to measure them. Every build/load is still followed by strict full public identity comparison before sampling/solving. Scratch must have canonical spelling, mode0700 and an existing parent. One explicit adapter-owned `gs.init(backend=gs.metal,precision='32',seed=7)` is allowed per isolated process; there is no public `gs.is_initialized`, so the adapter never reads `gs._initialized` or adopts an unrelated initialized runtime after an exception.

## Physical candidate boundary

The provider accepts no Store, lease, signer or authority path. It uses public named entities, authored-origin getters, one-link mass getter, pair-filtered live contacts and `.gstraj` save/load. Physical samples are exact float32 results promoted into binary64 containers, not float64 solver claims. `restore` validates raw SHA/length/config/binding/build/options before loading, then checks the returned full physics-sample body against retained bytes. `propose` loads the exact prior checkpoint for every new action, applies the explicit case, performs eight steps, computes strict Decimal half-even F, and returns only a PhysicsDraft/BlobWrite. The coordinator owns admission, budget and the unique world HEAD.

The extra `advance_isolated` probe operation emits only sample/descriptor/snapshot records plus D diagnostics. It does not fabricate State, Command, admission, world assets or a physical HEAD. Full Provider.propose/world integration remains an I10 responsibility even if the isolated physical checks pass. The source does not infer runtime-resolved assets from static declarations.

Initial checkpoint has step count0. Each of weak/strong starts from the same initial bytes and makes at most32 advances (256 steps); every advance loads its predecessor. The initial first-D comparison is `D_strong < D_weak <= 0`. The last four samples in each arm must have gap[-0.005,0.01]m, |vz|<=0.05m/s and at least one actual support contact. One additional tick16→17 restoration branch must match the uninterrupted full sample and D exactly. The approved plan totals520 physics steps, excluding zero-step initialization/calibration. Checkpoint bytes need their own valid hash, not cross-arm file equality.

Fixed support's actual solver-inertia mass must be `+0` (fixed/default inertia sentinel), not its hypothetical rho×volume3200kg. Dynamic Sphere's analytic mass comparison uses rtol1e-6/atol1e-7kg. This follows the audited primitive analytic mass path; mesh mass has a separate unit-density volume-integral path and is not used here. E7 must allow the exact fixed sentinel before execution. Negative, nonfinite, fabricated or silently repaired values are forbidden.

## Approved zero-step pose calibration

After saving the pristine checkpoint, set only dynamic body's authored pose to p=(0.125,-0.25,1.5)m and q=(1,2,4,10)/11, with public `set_pos`/`set_quat` (`zero_velocity=True,relative=True,skip_forward=False`). Read pose/vel/ang and support state without stepping. Limits: position1e-6m, sign-equivalent quaternion component2e-6, norm²1e-6, zero linear/angular velocity1e-6. Restore pristine checkpoint on exit, checking original bits before gravity arms. This is an asymmetric API roundtrip, not proof of nonzero world velocity, all physical frame conventions, or actual UE handedness. No world-velocity setter is assumed from the DOF setter.

## Runtime logging and original evidence

Every explicit runtime operation temporarily routes Python and native fd1 output to stderr and restores descriptors/streams in finally. The trusted worker must serialize protocol writes with provider operations; the scoped process descriptor redirection is not a concurrent worker API. No global permanent stdout reassignment is installed. Future I10 owns the private JSONL channel and must retain stderr logs; probe launchers retain complete stdout and stderr separately.

CLI operations require a unique canonical absolute `--output`. Existing directories are refused. The script retains command/PID/executable/source commit/environment, before/after input SHA indexes, per-family original JSON/raw files, summaries/failures and a final file index. Use a parent supervisor to enforce the separately authorized total GPU deadline (<=10minutes), capture full stdout/stderr/exit and manage only its exact child PID. Internal checkpoints reserve32MiB against the <=1GiB raw cap before each library operation. Timeout/exception never overwrites an attempt or silently retries; all affected checks remain failed/inconclusive. Bootstrap and physical commands share the owner-approved total GPU budget.

Illustrative commands (only `audit` is GPU-free; none implies runtime authorization):

```text
<genesis-venv-python> scripts/probe_universe_genesis_v0_1.py audit --output <unique-audit-dir>
<genesis-venv-python> scripts/probe_universe_genesis_v0_1.py options --approved-build <reviewed-build.json> --parameters <exact-parameters.json> --output <unique-options-dir>
<genesis-venv-python> scripts/probe_universe_genesis_v0_1.py probe --approved-build <build.json> --options <options.json> --context <owner-context.json> --config <config-record.json> --binding <binding-record.json> --output <unique-probe-dir>
```

A static source/grammar result cannot establish any runtime default, Metal initialization, physical sampling, checkpoint restoration, UE, realism, durability or world-integration gate.

## Static review correction

Independent review required two boundary repairs before options execution. The pure constructor now rejects scratch equal to or lexically beneath the registered authority root; operation-time canonical/no-alias checks remain. Input evidence collection records missing/unreadable paths without throwing out of finalization: the original operation exception is retained, changed/unavailable inputs force a nonzero recorded exit, and exit/index files are still emitted. The earlier source audit remains an original measurement of its earlier adapter SHA; it is not eligible as the corrected adapter's build pin. E7 was integrated by ordinary merge at `52dd9646fd9871d164a30ba0c20bac3024845c85`.


## R8B failure and post-build identity correction

The first physical attempt failed closed at `_scene_identity` after Scene.build and before a checkpoint family, frame calibration or any Scene.step. The original pre-build O and owner-freeze1 remain historical measurements, now ineligible for the corrected runtime pins. A separately authorized zero-step public diagnostic found six actual differences: material.sdf_max_res128→32, rigid contact_resolution null→0, contact_patch null→false, impratio null→1, max_contacts input32→actual5, tolerance null→the actual precision-dependent value. Complete expected/actual/support/diff originals are retained, not used as code constants.

The corrected bootstrap measures actual post-build-resolved options through the same public Scene build path. The requested config's max_contacts remains32; the library-derived actual capacity is exported without overriding either value or omitting any field. The two actual resolution source files `collider/gjk.py` and `constraint/solver.py` join critical_sources; the complete installed Python source tree remains measured. New adapter bytes require a newly owner-approved B and freshly measured O/context. No new GPU attempt is implied by this source correction.

Retained actual resource ledger: R8A options3.773s; first physical failure4.642s; zero-step diagnostic4.217s. All failures count against the original total600s/1GiB allowance; no retry resets that ledger. Root must issue the next GPU card explicitly.
