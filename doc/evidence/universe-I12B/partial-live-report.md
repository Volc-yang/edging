# I12B final live partial report — G-B2 not passed

The actual finite functional observations below are retained. **G-B2 did not pass;
resource gate FAILED: 2566 conservative charged seconds > 1200 seconds.** This is
neither a complete nor a bounded vertical-slice acceptance. No further runtime is authorized.

Runtime product source was `25abce1700696d33c583120ad1a336ad05753725` for r4.
This evidence commit also changes the offline deployment helper; that later helper HEAD
was not used for these runtime observations. Accepted runner/verifier/launcher and
business code are unchanged by this report.

## Functional evidence and remaining gates

| Item | Observed result |
| --- | --- |
| Actual initialization/projection | UE → owned worker → Genesis; verified r4 head `(0,0)` |
| Explicit retain | `(0,0) → (0,1)`, same snapshot, D=null, budget8/cursor0/steps0 |
| Repair-only recovery | Existing world recovered `(0,1)` without initialization |
| Weak physical action | `(1,2)`, budget7/cursor1/steps8; exact D_mm `−3774875/524288`, ties-to-even rounds to −7 mm |
| Native tests | Same-session `edgeWorld.UniverseHost.ProtocolIds` and `edgeWorld.UniverseHost.StandaloneAssetAudit`: Success |
| Two normal standard sessions | **Unmet**; standard and repair ended at interaction deadlines, both supervisor normal=false |
| Actual retry/history | **Unmet**; no retry or history request in actual traces |
| Readonly matrix | **Incomplete** camera/visibility/pause/framerate/held-input before/after evidence |
| Original PNG | **Unmet**; originals named `.png` contain JPEG/JFIF bytes |
| Overall resource gate | **FAILED**, 2566/1200 seconds |

Repair scope was `existing-world-repair-only`, `forbid_initialize=true`, `g_b2_granted=false`.
Its root wrapper preflighted repair then reused production supervise; it does not grant
P1 normal initialization or substitute for the required standard session pair.
Missing after captures for native-tests, retain and retry are not passes.

## Runs, exits and accounting

Persistent storage root (all paths below relative to it):
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I12B-20261102-world`.

| Run | Source / process identities | Outcome |
| --- | --- | --- |
| Prelaunch expired card | no Popen | charged1s; `prep/prelaunch-expired-card.json` |
| `run-P5MSOCfa` | source01b16d1; launcher53573/UE54070 | Host load failed: flat physical plugin layout broke LC_RPATH; extra plain UE54389 subsequently closed, unknown exit; included conservatively in earlier spent501 subtotal |
| `run-pwU8ijrW` | sourcea7bb2859; launcher93331/UE93505 | StartPlay/Engine initialized, REQUEST rejected, no worker; uppercase FGuid IDs fixed separately in PR104 |
| `run-dG0Gyx4m` | source227a750; launcher23554/UE23984/worker24732 | Old world initialized and proof verified; asset guard rejected game context; startup deadline, cumulative726s; fixed separately by PR105 |
| `run-Kh7Vih9E` | source25abce1; launcher65251/UE65637/worker66291 | r4 initialization, native tests, retain; interaction deadline; charged270s, cumulative996s |
| `run-oKHMYFvE` | source25abce1; launcher99400/UE99598/worker490 | repair recovery and weak action; interaction deadline; charged152s, supervised cumulative1148s |

Raw launcher logs are in `outputs/saved/MacLauncher/`. Standard r4 receipts are in
`sessions-attempt4/initialize/`; repair receipts in `sessions-repair-r4/existing/`.
Standard trace has eight requests: status/initialize/status/observe/prepare/advance/status/observe.
Repair trace has six: status/observe/prepare/advance/status/observe.
The last three workers exited normally with code0, were reaped, had complete traces,
no operational failure and no remaining owned processes. Raw launcher UE exit is0,
but supervisor completion UE exit field is null. Neither is promoted to supervisor normal=true.
Repair and standard actual launcher wait were0; older failed-guard launcher wait was70.

Extra plain editor PID6050/PPID1 had no project. Its ps start was
`2026-11-02T05:29:57+00:00`; after targeted CmdQ it was CLI-confirmed absent at
`2026-11-02T05:53:34.648673+00:00`. Exit code is unknown. Its exact spawning call
was not independently instrumented; no attribution to the user is supported.
Late controller app-state refresh can reopen the editor, but is not a proved cause.
Its nonoverlapping conservative upper bound is1417.648673s. Together with supervised1148s,
rounded conservative charge is2566s. See `prep/controller-extra-selector-budget-failure.json`.
`independent/live-final-partial-summary.json` supersedes the earlier supervised-only
`independent/live-partial-summary.json` for total accounting. Originals remain unchanged.

## Independent authority and physical verification

Old `edgeworld-i12b-20261102` remains at `authority/`, `(0,0)`, D=null,
budget8/cursor0/steps0, 31 records/1 raw; head
`6cdcca228dbb78bb7aa8f209b0a68815abded2b1f8c7c03e551fae049358fed8`.
No reset or overwrite occurred.

Fresh `edgeworld-i12b-20261102-r4` lives at `authority-attempt4/`, with
`scratch-attempt4/` and `deployment/attempt4/`. Initial head was
`e401321f1efb0d9da31764b28a8fc27feaa867ec4a54d0cdb7a2296bfbc16fb7`.
Independent full authority copies and request reassembly are under
`independent/run-{dG0Gyx4m,Kh7Vih9E,oKHMYFvE}/`. Before/after copy maps matched;
selected proofs' record hashes matched full authority copies. Old initialization proof's
31 records exactly matched its copy; r4 initial copy also had31 records/1 raw.

Final r4 authority has56 records, three retained manifests, two raw blobs.
Physical before/after originals are `actions/r4-repair/physical/{before,after}/`.
All old files except HEAD.json were unchanged, 15 files were added (14 records/1 blob),
none removed, and the after map equals final authority. Final verification is
`independent/run-oKHMYFvE/final-authority-physical-report.json`; exact Fraction D was
computed independently. Only one weak prepare/advance is present. No retries/history inferred.

## Image identity and timing

The three `.png` originals remain byte-for-byte unchanged; exact-byte `.jpg` copies
are indexed by `ui/original-format-correction.json`. No conversion or new capture occurred.

| Original | Bytes / SHA256 | Capture timing (host UTC epoch seconds) |
| --- | --- | --- |
| `ui/r4-00-initial.png` | 267628 / `28159922efeac1ef4b3f8f282bed292bf8ef249f1bdc069db7d20185b8ce4488` | recorded1793595463.189..1793595463.257; UE65637, `(0,0)` |
| `ui/r4-01-retain.png` | 267419 / `5e46768a497745e9e5e7562dae9b6e6c4126800d4e310041cde445c2f6146713` | recorded1793595628.05..1793595628.122; UE65637, `(0,1)` |
| `ui/r4-repair-physical.png` | 145713 / `1ffdb388e61e666e6623230a77814175a9fdaab755ab67b74827fba68696cdf6` | inferred1793597284.531..1793597284.5870733; no exact capture timestamp |

Physical timing is inferred from after-event to original file creation/write upper bound.
That event records UE99598, log offset183404, prefix SHA
`86b67ae743cabdcd970c9f1613fc56e2e582186d03bb3d6ab30912008efecf72`.
Independent local image inspection saw HEAD1,2, weak, ready, D−7 and SF_METAL_SM6.
This is a technical proxy scene; no realism conclusion is made.

## Public index, private boundary and offline helper correction

[Final public index](final-public-index.json) is an offline snapshot of1092 public
storage files (including shared caches), with its own index excluded from self-hashing.
SHA256: `45e6b1908c21ddc3b30c9ee41e5cc4a2d4220bace4c988dfd736e004356b8eba`.
Storage bytes at indexing were1436540430, below2GiB; index bytes290293.
Four private owner-config files are excluded from content hashing/index contents,
with metadata only. External old/r4 key paths were stat-only: no key bytes read/copied/hashed.
Large worlds, caches and binaries remain on DevSSD. The index and small final summary
are copied here; the index is a snapshot, not a claim to hash future writes.

Historical build receipts identify binaries at each capture. Mutable official build outputs
were overwritten by subsequent builds; their historical bytes are not claimed to remain
at the same path. The original first flat binaries and current physical mirror are retained.
Six authorized untracked output artifacts remain in the worktree and are not Git additions.

`prepare_deployment.py` now maps Host binaries to `project/Binaries` and plugin binaries
to `project/Plugins/EdgeWorldRuntime/Binaries`, preserving the actual relative Mac RPATH.
Explicit parent mkdir0700 plus target parents=True preserves private directory creation.
A pure layout invariant rejects a broken sibling relationship. The path/AST-only
[check](offline-layout-check.json) passed in0.004s without importing/executing the helper,
provisioning, changing current links or launching UE/Genesis. Actual successful native tests
under the root's repaired physical layout provide the historical regression evidence.
No record bytes, crypto, provisioning or other source logic were changed.
