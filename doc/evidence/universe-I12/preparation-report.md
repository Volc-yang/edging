# I12A preparation report

2026-11-02. **CPU preparation complete; real I12/G-B2 not executed.**

Worktree `.worktrees/i12-universe-acceptance`, branch `codex/i12-universe-acceptance`,
base `0a7a0fb4b4f11a70dc2e9157a28673d6f9045dd9`.
Final tool/check source commit `a2b9fa27e7dcdc5c61e2419a89ef2931fc0da755`.
This report and final guard raw are a subsequent evidence-only commit; source is unchanged.

Delivered two stdlib-only scripts, action plan, explicit bundle contract, independent verifier and
synthetic regression checks. Driver defaults to plan, refuses actual run, writes only exclusive
caller-requested evidence files. It cannot launch a process other than explicit read-only `ps`,
provision/sign, send worker requests/UI input, kill anything or acquire writer ownership.
Verifier imports no production codec/getter, solver, UE or signing code. Exact D uses rational
binary64 subtraction and ties-to-even; golden SHA expectations are accepted literal vectors.
The full scope and commands are in [README](README.md).

## Verification and immutable attempts

| Attempt | Pinned source | Outcome / scope |
| --- | --- | --- |
| First check | `check-source-pins.json` | 6 tests: 4 passed, 2 fixture failures; exit1, 0.061s. Full `check-attempt1.log/json` retained. |
| Allowed targeted retry | `check-targeted-source-pins.json` | Only two affected tests; 2 passed, exit0, 0.068s. `check-targeted.log/json` retained. |
| Root-issued I12A-GUARD | final source `a2b9fa2`, `guard-source-pins.json` | Only regular-file/FIFO/descriptor64hex guard and affected synthetic archive test; 2 passed, exit0, 0.078s, raw324B. `guard-attempt.log/json` retained. |

Initial failures were test setup: fixture archive has no top-level world_id (identity belongs to
records), and the private-path case first encountered a leftover intentionally created symlink.
Both fixture errors were corrected; no product changes. Final self-review added refusal of
nonregular hash inputs (including FIFO), and a 64hex descriptor guard before constructing raw
paths. Root explicitly approved the extra ≤10s/raw1MiB card after the ordinary retry allowance.
Source was committed before this extra check. Do not describe the last two tests as a full rerun
of all seven cases: earlier results remain pinned to their original script hashes.

All checks used temporary **synthetic evidence** files only, no ownership registration, keys,
Store/worker runtime, Genesis or renderer. Raw is a few KiB, below local64MiB and guard1MiB caps.
No actual authority, UE/Genesis/CUA instance, DevSSD world or external account was created.
Main workspace dirty changes were not read for implementation or modified.

## Remaining conditions

This is not an autonomous UE action runner yet: real action/console/CUA binding is deliberately
disabled pending final integrated source, actual trusted owner inputs and root R12 card.
No candidate20min/2GiB budget was consumed or treated as permission. At dispatch, normally merge
the exact accepted I10B/I11B tree rather than mixing worktrees or rebasing. Raw world/evidence goes
to DevSSD; keep large raw out of Git and index all bytes/failures. Prefer independent Space and
stable-runtime CUA PNGs, with scripted camera semantics explicitly distinguished from old mouse
evidence. Initialization status allows NOT_READY on registered empty root; prove no HEAD/scratch/
solver before explicit initialize. Existing-root missing startup is UNINITIALIZED.

Verifier's machine checks alone cannot establish human/GPU action authenticity, MAC recovery
(no key access), every schema scalar predicate, executable/source identity, root resource
authorization or G-B2. Required independent review paths are indexed; missing reviews/evidence
remain inconclusive. Even a structurally complete bundle requires root verdict. Actual I12 must
still produce the two UE-owned sessions, same world, exact retry/history, per-action unchanged
maps, Metal originals and distinct worker/UE/launcher real lifecycle evidence.

The independent PR may accompany the later real-run evidence, as permitted by the preparation
card. No implementation fixes or downstream gates have been self-approved.
