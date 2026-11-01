# I6 independent neutral-kernel process acceptance

Implementation base: `607e5500797854e5026d72e67ae8f45c70454a31`.
Owner is independent of I1–I5 implementation. All cases use the fixed
`fixture-world` / `neutral-transfer-v0.1`; no Genesis, UE, GPU or model is used.

The acceptance script imports production modules only in fresh child processes.
The parent uses a separately written recursive ASCII encoder, fixed golden
bytes, domain hashes and complete reachable-history/accounting checks.

Planned checks, with actual results recorded separately after execution:

- 11 controlled phase handshakes: W0–W8, RECOVERY_VALIDATED and W9. The parent
  captures original files at the pause, checks ownership/liveness of its Popen
  PID, then sends actual SIGKILL and records the real exit status. W2 pauses on
  the first newly written object, rather than an already committed genesis file.
- Actual syscall error injection for replace, pre-V file/directory fsync and
  post-V directory fsync. Unknown outcomes require fresh recovery before retry.
- Two independent writer processes, canonical/symlink alias exclusion, stable
  lock inode and release after a separately recorded SIGKILL.
- Corrupt old state / missing historical checkpoint refuse recovery and reads,
  with no fallback or repair. Original pre-damage bytes remain in evidence.
- Fresh unconfirmed read-only recovery, exact same-tick history and rejected
  watermarks, no fake confirmed retry; complete file maps remain unchanged.
- Continuous and restarted segmented command sequences produce identical
  logical record bytes/HEAD, budgets and cursors. Registration identities have
  distinct paths/inodes and are compared according to that separate scope.

The 20 cases require 12 genuine SIGKILL events including the writer-release
case. Each phase/file map and child command/PID/stdout/stderr/exit is stored in an
exclusive new run directory. Snapshots include referenced and orphan raw file
bytes. Input hashes bind exact source and fixtures before/after. Deadlines are
110 seconds internally and 120 seconds per authorized check, with independent
short cleanup timeouts and a 64 MiB raw budget. Only owned, unreaped child PIDs
are signaled; no global process killing or authority cleanup is performed.

Run the dedicated suite once, optionally setting `EDGEWORLD_I6_OUTPUT` to a
new absolute evidence directory. The CLI equivalent is:

```
python3 scripts/run_universe_authority_faults.py --output /new/absolute/run
```

The directory must not exist. Failures are retained, never converted into
success or repaired by regenerating expectations. A failed run keeps its
failure summary and raw index. One authorized targeted rerun must use a new
attempt directory and preserve the original attempt.

This is a local POSIX process/syscall-fault test. Successful fsync calls and
SIGKILL do not prove hardware power-loss durability, malicious same-UID safety,
cross-machine determinism or production multi-root authorization. G-S1 is
decided independently by the coordinator from exact source and raw evidence.
