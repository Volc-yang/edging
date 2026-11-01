# H1e default-thread viewport preflush candidate

Accepted as diagnostic implementation only by coordination; not a product fix.
Base `006a302598f44c4b247e2811e9c4698ce81b91e2`, independent worktree/branch
`codex/g3-viewport-preflush`. Own new viewport client/test, host private build
dependencies, client configuration and this evidence directory. No GameMode,
worker, input, camera, lighting or engine source changes.

Published Slate broadcasts `OnWindowBeingDestroyed` before notifying the window
of closure; the latter releases the engine's scene viewport owner. Register a
project viewport-client callback filtered to its exact game window. A logs
only; B additionally drains rendering work on GameThread before owner release.
Both use the same configured adapter. The only switch is B's
`-EWDiagPreflushViewport`; synchronization is off by default. Keep default
rendering threads in both arms; reject samples if their logs disagree.

Run a focused lifetime test with a rendering-thread shared reference retained
while the game-thread owner is alive. Verify disabled non-drain, enabled drain,
and final GameThread destruction. Build official Editor target, retaining all
attempts, exit codes and logs.

Run A1/B1/A2/B2 serially, identical full causal scene, live Genesis, independent
UserDir per arm, tick 0/1/2, history and camera actions. Preserve first observed
images, startup stages, per-action authority/checkpoint hashes, at least 180
seconds from initialization to close, close-call intervals, native errors and
actual UE/worker exits or leftovers. Reopen each same arm state for recovery
and record it separately. No concurrent UE or shared-state writers.

Snapshot existing CrashReportClient PIDs before each run. After failure,
identify only new reporters attributable to this run by UE PID/crash identity,
copy their raw context/minidump before cleanup, then TERM those exact PIDs.
Never globally kill reporters or send reports to Epic. Preserve unknown
reporters and report them. After successful exit, still inventory reporters.

Any B failure rejects the candidate. Clean B samples do not prove universal
reliability; default-thread gate remains open pending independent review. Do
not hide warnings or extend to the suspended visitor or lighting tasks.
