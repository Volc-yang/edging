# H1f execution record

Accepted parent card: `doc/evidence/g3-viewport-preflush-followup-plan.md`.
Exact base `12f7fb734c38a0a8de4da158ca6ffae74e43801c`; independent worktree and
branch `codex/g3-preflush-followup`. Prior H1e worktree is read-only and not used
for writes or binaries. Scope: viewport delegate idempotency, lifecycle tests,
new-binary evidence and this report directory. Default synchronization stays off.

Remove any old window delegate before repeated Init, and reuse the same removal
routine on BeginDestroy. Test real repeated Init, removal of the latest handle
without stale bindings, re-registration and destruction. Retain the original
cross-thread lifetime test. Official Editor build and both tests precede all
real samples; all real samples use one frozen source/binary identity.

GPU serial, reporter-free baseline required. Primary A1/B1/A2/B2 use independent
UserDirs, live Genesis, complete causal scene, default rendering thread, valid
tick 0/1/2 and per-action history 0/H/camera authority-file hashes. At least
180 seconds after initialization before the same window-button close. Record
actual exit and only then archive/clean exact per-run reporter/orphan matches;
verify all are gone before the next start. Preserve and redo invalid samples.

Only after B1/B2 succeed, B3 tests window resize and minimize/restore before
close; B4 restores B2's persistent directory and uses CmdQ. These are boundary
samples, not additional primary repetitions. All B samples require registered
default rendering, exact game window and GameThread, non-null unchanged owner,
flush evidence and exit 0. Any valid B failure/hang rejects the candidate.

Retain original failure/tool/cleanup evidence. Do not touch user processes,
send reports, edit UE source, or expand to visitor/lighting work. Product and
global reliability gates remain open; any limited acceptance needs independent
review and a later launcher/default decision.
