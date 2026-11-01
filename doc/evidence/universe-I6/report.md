# I6 independent process acceptance results

2026-11-02. Parent task I; implementation base
`607e5500797854e5026d72e67ae8f45c70454a31`. Production I1–I5 files were not changed.
The coordinator independently decides G-S1 from this candidate evidence.

## Exact execution and preserved failure

First local implementation source:
`bd9eba91a51331e7293613de895c08f618b92629`.
`python -m unittest tests.test_universe_process_faults -v` ran 2 tests in
5.775 seconds; total exit **1**. The independent golden check and 19/20 matrix
cases passed. The alias-exclusion case failed because the harness tried to use
the same `alias` path for its symlink and its child-log directory. This was a
harness path collision, not a diagnosed authority failure. All 83 children were
reaped: 71 exited 0, 11 phase-handshake SIGKILLs were observed, and one holder
required a separate cleanup SIGKILL. That cleanup is not counted as the missing
twelfth acceptance kill. Original logs and failure remain unchanged.

The only authorized local targeted rerun used source
`140afc08e0dbcf05c2785ffdf3053b905c8cc563`, whose only code change separated the
contender log path. Same command, new attempt directory: **2 tests, 20/20 cases,
85 children, 12 genuine controlled SIGKILLs, exit 0**. Unit duration 5.533 seconds;
outer check duration 5.636 seconds. All 85 children reaped (73 exit 0, 12 exit
-SIGKILL); no cleanup kills, cleanup errors or timeouts. Python 3.10 grammar
parsing passed. Source/contract/fixture hashes before and after were identical.
Runtime was Python 3.14.7, Darwin 25.6.0, arm64.

| Attempt | Raw index SHA-256 | Files / indexed bytes |
| --- | --- | --- |
| `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I6-20261102-process-attempt1/` | `1adebb847047dcdd02c8b2cccc857effc1694f8c82641e64f6bf768febec0342` | 949 / 1,817,265 |
| `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I6-20261102-process-attempt2/` | `e8d31b805728033ed0b9e1f4a20c8b7f0bbf3cee676d27b1ba136c00dc1d44da` | 956 / 1,820,506 |

Each index is `raw-index.json` in its attempt directory. Total raw evidence is
below 4 MiB, within the 64 MiB budget. Final successful summary SHA-256 is
`e19ed0404077c452b6a624d2f67d43f79d68fd03c3df1316a1e7409b3ff1de54`.
Complete original child JSONL/stderr, commands, PID/exits, before/phase/after
files (including raw bytes and orphan objects), input hashes and case outcomes
are retained. Neither attempt nor its index was regenerated or overwritten.

## Observed gates

| Check | Actual result |
| --- | --- |
| Independent bytes/hash observer | Own recursive ASCII encoder matches all 24 fixed canonical byte/hash vectors; does not import production canonical/validator |
| W0/W1/W2-new-object/W3/W4/W5 real SIGKILL | Fresh recovery sees complete old root revision0; retry converges once to revision2, budget6/cursor2 |
| W6/W7/W8 real SIGKILL / response lost | Disk sees complete new revision1; fresh D_recovery confirms it, retry performs no duplicate candidate/A/charge |
| RECOVERY_VALIDATED/W9 real SIGKILL | Existing revision2 remains complete, another fresh recovery required; committed retries solve/admit zero times |
| Actual replace exception | COMMIT_UNKNOWN/unknown, cached ready view rejected; unchanged old root recovered before retry |
| Actual pre-V file and directory fsync failures | SYNC_UNSUPPORTED/not_attempted, recovering/NOT_READY; old root intact, fresh recovery before retry |
| Actual post-V root directory fsync failure | COMMIT_UNKNOWN/unknown, no stale ready view; complete new root independently observed and recovered |
| Two independent writers / alias / inode | Both competitors receive LOCKED while holder lives; holder SIGKILL releases OS lock, original lock inode retained |
| Historical state corruption / missing historical checkpoint | Independent observer rejects; worker returns CORRUPT with no snapshot, no fallback/repair, bytes unchanged during refusal |
| Failed D_recovery / exact historical read-only | Fresh validated snapshot remains explicitly unconfirmed_readonly; three exact same-tick revisions readable, wrong watermark/unknown tuple rejected, execute cannot return fake confirmed retry |
| Continuous vs restarted explicit sequence | Identical logical objects/HEAD and exact history, values/budget/cursor; pure observations do not change full file maps |

The parent independently traverses the entire HEAD reference closure, checks
canonical bytes and names/domain/world/kinds, static trust anchors, all retained
roots, command/result identity, event/prior-state binding, neutral arithmetic,
budgets and cursors. It compares complete phase and recovery file observations;
production `validate_closure()` returning successfully is not its sole oracle.

## Post-run static evidence-preservation fix

After the two authorized local checks, static review found that refusing an
already existing output directory could still attempt failure/index archival
into it. A small subsequent guard now distinguishes preexisting directories and
symlink outputs, refusing them without writing. A dedicated negative unit test
checks names, sentinel bytes and symlink target preservation. No third local
check or matrix was performed. Thus local 20-case evidence is bound to
`140afc08…`; the subsequent code diff is specifically this archival guard, plus
its dedicated test and documentation. The final exact-head CI and independent
coordinator refusal-path review must verify that final delta before acceptance.

## Limits and disposition

Candidate result: I6 checks pass under the bounded neutral POSIX profile, pending
final exact-head CI and independent coordinator review. These are real child
processes and controlled syscall failures, **not hardware power-loss tests**.
No Genesis, UE, GPU, model, external authorization, autonomous universe clock,
production multi-root identity or cross-device determinism was exercised.
The fixed root-scoped fixture is not the future v0.2 rich-world runtime.

Worktree/branch retained clean after scoped ordinary commits and PR submission;
coordinator owns integration and cleanup. Never merge or remove unrelated or
dirty worktrees. If a required final review fails, reopen only this harness or
the evidenced production node, retaining all current attempts.
