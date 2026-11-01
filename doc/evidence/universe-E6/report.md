# E6 result

Status: partial; first formal Check failed only its offline comparison harness.
G-S1.2 remains pending coordinator adjudication.

Base `a4c86b382df01876a811af771df86af8a2fdb899`; first source
`057fcc27a03c277fc776c72f14b0e27ef419806c`.
First evidence: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/E6-20261102-process-attempt1/`.

The first run executed 3 tests in 14.684s, overall exit1. Output-preservation and
67-golden tests passed. Matrix: 15/16 groups passed, 79 children all reaped,
8 genuine controlled SIGKILLs, 0 cleanup kills/errors. Input/source hashes were
unchanged and Python3.10 grammar checks passed. Actual raw directory bytes,
including runner/index additions: 14,922,214 (below64MiB).

Only segmented-equivalence failed, before its segmented sequence: line911
incorrectly required the rewound HEAD file inode to equal genesis. Store had
legitimately replaced HEAD atomically. Initial root/stable lock inode assertions
passed; all restored names/bytes matched the original genesis-copy. Failure,
continuous result, before/after-rewind maps, child JSONL and exits are preserved.
No production defect was inferred and no product module was changed.

Coordinator approved the sole targeted rerun: only segmented-equivalence, new
`E6-20261102-process-attempt2-targeted/`, within remaining budget. Harness change
ignores **only HEAD.json inode** when comparing rewind; exact bytes/mode/device/
nlink and all other map entries remain required, as do root/stable-lock inode
identity and absence of live children. A genesis map is now explicitly saved.
The target selector does not rerun the passed15 groups, eight kills or goldens.
New source must be committed before that run. Targeted outcome is not yet run.

All provider/raw data is synthetic `.static`, not Genesis/gstraj, UE rendering,
power-loss proof or an OS sandbox. Offline fixture rewind is not a runtime
rollback/backup recovery capability and makes no anti-rollback claim. Original
I6 evidence and all production/fixture files remain untouched.
