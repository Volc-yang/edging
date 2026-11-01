# I10B real CLI / Genesis execution

Status: delivered for independent review and CI; the complete real CLI matrix passed in the explicitly authorized topological rerun. The first real attempt remains a failed attempt. No UE, rendering, realism, I11 or I12 acceptance is claimed.

## Fixed source and identity

Base `0a7a0fb4b4f11a70dc2e9157a28673d6f9045dd9`, branch `codex/i10b-universe-runtime`, worktree `/Users/yangacan/edgeWorld/edge-world/.worktrees/i10b-universe-runtime`. Only `scripts/probe_universe_worker_v0_2.py` and this evidence directory changed. No worker, provider, kernel, contracts or UE source was changed.

- Actual failed runtime source: `572dde14af1e50408564d01b5ad67a0b22644977`.
- Dependency-order fix: `277222dc644da75c5a8b4916945c2ac3fbc452a0`.
- Actual successful runtime source: `c448340ca6623b6da02ef96586a6a97b14bef421`.
- Interpreter: existing `.venv-genesis/bin/python3.12`, Python3.12.14, Genesis1.4.3, Metal precision32, seed7. Invocation files preserve the resolved interpreter binary SHA and actual executable/argv/environment.
- Adapter bytes remained `15f5b96bb0381781d0357eb93510622afe6ec3d5caf60adb5ed8190ff6abb192`.
- Actual measured provider-build for world `edgeworld-universe`: `a1bd8768517734c47f6c3e0c2b532343046733778feaa22201b0d6b1e9b65ee6`.
- Actual independently executed public zero-step post-build options: `ef8d9323a6642c84ec2c788e5b0c542a1705c9d41268bbe5fce18ef3a62f3fd6`. Neither run copied an older resolved record as its actual measurement. All 264 package-source entries and 37 native/METADATA hashes matched the accepted identity; successful run retains unchanged before/after native indexes.

Each real attempt used a distinct explicit authority, private owner directory, random key directory and scratch directory alongside its evidence directory. Owner session was `owner-local`, initialize allowed, actions retain_snapshot/physics_step. Keys remained outside authority/raw; the probe records only key permission metadata and aggregate byte counts, never key content or its hash. Owner files were exact-seven-key private0600 in0700; key files0600/key directory0700. Public pins were independently checked as exact12/canonical+LF, with no authority/scratch creation. Accepted I0A nine-asset body/audit remained pinned inputs; initialization only rebinds world identity.

## First failure and bounded correction

The initial stdlib-only identity check (`f7b63be`) passed without importing Genesis. Static review found pins-timeout and stdin-close cleanup holes; the owned child registry/reap path was corrected and exercised by actual CPU child processes. An independent outer process supervisor now samples aggregate evidence/authority/scratch/owner/key metadata and external logs every0.05s, including bootstrap and pipe waits. Its first CPU test's threshold was below already archived source bytes: despite exit0, it did not prove ongoing growth. That original is retained. A corrected baseline-relative test at `766a8ed` required at least two polls and passed with max0.0604s; both timeout and BrokenPipe children were reaped with original exceptions retained. No GPU was used for those checks.

Runtime attempt1 passed actual B/O measurement, public pins, pre-init status `NOT_READY`, explicit initialization/confirmed commit and fresh status at(0,0), then failed in the probe's offline closure validation. The probe had sorted object filenames by digest, but the public archive validator requires dependency-before-user order. This was a driver defect, not a worker/provider change. Worker32519 closed on EOF with exit0/reaped; pins32518 exit0/reaped; bootstrap runtime destroy succeeded; owned group32489 was empty.

Source277222d now derives a dependency order from HEAD, rejects missing/cyclic/unreachable/duplicate objects, and passes the complete archive to the unchanged public validator. A stdlib-only read of attempt1's original31records and one262460-byte real checkpoint passed full closure/MAC/raw validation, typed36, initial tick/revision0/Dnull and unchanged authority hashes; Genesis was not imported. This offline check does not replace the previously missing physical/transport/restart matrix.

Root explicitly issued R10T for one new complete matrix with fresh root/key/owner paths, retaining attempt1. Inner230s/outer270s/hard250s limits stayed within the original total300s allowance after deducting15.627s. The supervisor counts both attempts, including private-key bytes by stat only, against shared224MiB soft/256MiB hard limits; it does not reset the raw ledger per directory. It terminates only the exact owned driver/group, records original/remaining group membership and reaps owned direct children. No third real matrix was run.

## Successful real matrix

`I10B-20261102-runtime-attempt2-topological`: actual outer33147, owned inner/group33148, two actual worker processes33161 then33199. Pins and both workers exited0/reaped, the parent bootstrap explicitly destroyed its Genesis runtime, and the owned process group was empty with no emergency cleanup. Worker2 stderr was exactly0bytes, consistent with no solver initialization during recovery/history/committed retries. Both worker stdout streams contain only correlated protocol frames; complete stderr is separate.

| Action | tick / revision | budget / cursor | physical steps | independent D mm |
| --- | --- | --- | --- | --- |
| explicit initialize | 0 / 0 | 8 / 0 | 0 | null |
| retain | 0 / 1 | 8 / 0 | 0 | null |
| weak physical | 1 / 2 | 7 / 1 | 8 | -7 |
| strong physical | 2 / 3 | 6 / 2 | 16 | -48 |
| retain | 2 / 4 | 6 / 2 | 16 | -48 |

Each physical D was independently recomputed from exact binary64 positions using Fraction subtraction, multiplication by1000 and half-even rounding; retain preserves D. Full public closure/MAC/reference/raw-SHA validation ran at each state and command preparation. Retained world archive ended with81records/3raw checkpoints. The two physical inputs here are consecutive causal advances, not independent-arm comparisons.

Every command's repeated prepare used identical IDs and returned the same signed closure; repeated advance returned the original committed result and left authority/scratch/raw hashes unchanged. Five exact retained pairs(0,0)/(0,1)/(1,2)/(2,3)/(2,4) passed transport observation and independent proof verification against fresh status HeadBinding/public pins. Wrong principal and wrong watermark were rejected without changing authority/scratch maps. Status/prepare/observe were checked read-only before/after every action.

After normal EOF/exit/reap of worker1, worker2 opened the same authority/key/anchor in explicit existing mode with a fresh PID. Fresh status, all five histories and all original command retries matched the committed world; no new raw/scratch files or physical advances occurred. Final EOF/exit/reap also left authority/scratch unchanged. There is no automatic clock, retry-as-new-intent, hidden fallback root or fake provider in this path.

## Original evidence and resource ledger

All originals are under `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/` using the directory names below; each repository subdirectory contains archive references/index hashes and necessary small logs. Runtime authority/scratch originals and `.inner.stdout/.inner.stderr` remain distinct sibling paths. Complete runtime indexes include those paths and unique content-addressed authority-byte copies. Private owner/key content is excluded from raw indexes. No originals were compressed, truncated, relabelled or deleted.

| Directory | Result |
| --- | --- |
| `I10B-20261102-stdlib-attempt1` | actual stdlib identity, exit0, no Genesis |
| `I10B-20261102-cleanup-check-attempt1` | timeout/BrokenPipe actual CPU children reaped |
| `I10B-20261102-watchdog-check-attempt1` | retained inadequate below-baseline watcher test |
| `I10B-20261102-watchdog-check-attempt2` | corrected growing-output monitor + cleanup checks passed |
| `I10B-20261102-runtime-attempt1` | real init, failed probe ordering; outer15.627s |
| `I10B-20261102-offline-closure-attempt1` | original initial closure validated read-only/no Genesis |
| `I10B-20261102-runtime-attempt2-topological` | full real CLI matrix, outer14.916s |

Actual runtime total30.543s, below300s. Successful supervisor's cumulative peak was7,122,215bytes, max poll interval0.0628s, no budget trigger. Final retained totals grow modestly when indexes/reports are sealed; the aggregate remains far below256MiB. Runtime1 complete-index131entries/1,409,569indexed bytes/SHA`7e94cd7fc978390748edf99ecd70fecdbe3d8c19d4c56a13cb5502065298dd03`; runtime2 complete-index445entries/5,849,079indexed bytes/SHA`dab3c337f56032182f470535acfd337b0d75cd3fabf6e915a11000828d592058`. Counts include preserved duplicate source/evidence copies as actual bytes, while key material is only stat-accounted separately.

Next: root independent source/raw/numeric/transport review and exact-head CI, then integration if accepted. I11/I12 still own the UE/combined visualization and independent final gates; this result alone does not accept those gates.
