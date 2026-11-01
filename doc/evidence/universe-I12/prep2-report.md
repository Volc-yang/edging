# I12A-PREP2

2026-11-02. Parent root source review requested two passive-tool corrections.
New source commit `73bbd2e` (full SHA in `prep2-source-pins.json`) follows original
I12A source `a2b9fa2` and evidence-only `d6e30f7`. This report is evidence-only.

1. PLAN now spells out real three-argument Exec calls: `UniverseObserveExact 0 1 1`,
   `UniverseObserveExact 0 0 0`, `UniverseObserveExact 1 2 2`.
2. Explicit `--start-offset` consumes an action-before log size. `--initial-sha256`
   then covers exactly that prefix, not the larger current file. Explicit mode also
   requires action-before `--expected-device`/`--expected-inode`; metadata output
   includes those lstat values without reading private files. The pinned open fd
   is regular/nofollow; prefix hash, size and path identity are rechecked while
   waiting and before returning. A replacement with identical prefix is rejected
   by device/inode. Marker bytes already appended after the before pin count even
   if the UI action completed before helper invocation. No waiter-arming sleep.

Outputs preserve start/end offsets, prefix hash, device/inode, and optional caller
run_id/host_pid labels. Those labels must be correlated with original owned process
evidence; the helper cannot authenticate them. Without explicit offset, legacy
wholehash/current-end behavior remains and must not be used after action dispatch.

Under root's ≤10s/raw1MiB card, source was committed before running only
`test_prep2_history_arity_and_post_action_marker` and
`test_prep2_prefix_changed_truncated_or_replaced`. Both passed; exact command,
elapsed time/exit and raw output are `prep2-attempt.json/log`. Source hashes are
`prep2-source-pins.json`. Earlier failures and successful checks remain unchanged.
No full old suite rerun, no UE/Genesis/CUA, registered authority, keys or UI input.

Mac lock state and user unlock remain external. No unlock attempt/credentials.
Actual R12 is still unauthorized and run mode remains disabled. The final accepted
normal integration merge, inputs and R12 dispatch are prerequisites for real I12.
These results are CPU tool checks only, never G-B2 or evidence of a real marker/UI.
