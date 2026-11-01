# H6B visitor character implementation record

Status: implementation in progress. Parent V-HOME/H6B; approved implementation card `doc/evidence/home-visitor-implementation-plan.md`. Base `489b97c`; branch `codex/home-visitor-character`; worktree `/Users/yangacan/edgeWorld/edge-world/.worktrees/home-visitor-character`.

## Execution and ownership

1. Implement released UE ACharacter/CharacterMovement/Camera visitor, safe entry and local edge recovery; wire continuous movement/look and Tab overview return into the existing GameMode/controller.
2. Update HUD input guidance and add focused movement/collision/mode checks. Owned paths: new `EdgeWorldVisitorCharacter.{h,cpp}`, `EdgeWorldCausalGameMode.{h,cpp}`, `EdgeWorldCausalHud.cpp`, focused visitor checks and this evidence directory.
3. Build with the installed official editor toolchain, then use this worktree's canonical launcher with `--launch --viewport-preflush`, default render thread, exclusive build/GPU ownership. Verify PID and engine initialization before binding UI.
4. Capture unique run/attempt evidence for walking, support, walls/rails, turning, Tab position retention, edge recovery, history, explicit Space, normal close and same-directory recovery. Compare all authority files independently before/after each read-only operation. Preserve failed attempts and inspect actual processes after tool errors.
5. Commit scoped changes and open an independent PR to `codex/plan-consolidation`; do not merge. H6C independent acceptance remains downstream.

No writes to worker/protocol, causal Actor/environment geometry, viewport or launcher. Space remains the only explicit Advance. Local character motion does not define Genesis character physics or approved world rules. The explicit preflush path is a limited development bypass, not a fix claim for the original default exit path.

## Read-only observation interface proposal

`VisitorStatus` prints one record with engine frame/world time, pawn/view-target identities, position/control rotation/velocity, movement mode/grounded/falling, capsule dimensions, CurrentFloor blocking/walkable/distance and actor/component identity, and a blocking capsule overlap query that ignores the visitor itself. `VisitorTrace <seconds>` explicitly samples at 0.2-second intervals for a finite duration clamped to 0–10 seconds (default 3); it also logs actual capsule blocking-hit events with actor/component, impact point/normal and initial penetration. Sampling is off by default, has no HUD surface and cannot advance or teleport. Recovery independently records threshold bounds and position before recovery, followed by the entry result. This proposal is supplied for coordinator/H6C format freeze before final runtime evidence.

## Checks actually performed / current limitation

Scoped implementation commit `b1d526e` contains the initial visitor and focused test. Official installed UE 5.8.3 CL 58210709 `EdgeWorldHostEditor Mac Development` builds succeeded: initial build 26.44 seconds, test-inclusive build 8.90 seconds, observation-inclusive build 8.96 seconds, each exit 0. Logs are retained in worktree Saved/MacLauncher runs `run-ncb709Jg`, `run-SHVXOg25`, `run-Cswu6INB`. `git diff --check` passes. The focused `edgeWorld.Visitor.SupportMovementCollisionRecovery` test compiles but has **not run**; no test pass is claimed.

One preliminary canonical live launch used `--launch --viewport-preflush`, default rendering threads and an isolated UserDir. Actual UE PID 50822, worker PID 51016; log records safe entry `(0,-300,-50)`, GameMode StartPlay, engine initialized at 07:12:07.729 UTC and validated tick0 at 07:12:11.466 UTC. Its binary preceded the expanded observation interface. At UI discovery, CUA reported twice that the Mac was locked and automatic unlock failed. No application was bound, no UI input or screenshot was captured, and no interactive evidence is claimed. Source edits resumed only after ending this exact UE PID with SIGTERM; UE and launcher returned 0, and exact process inventory found no UE/worker/reporter remaining. This termination is **not** a normal UI-close acceptance check.

Preliminary raw evidence root `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/H6B-20261101/`: two independently captured locked idle snapshots list both authority files, plus build logs. Idle invariance is not navigation invariance. No Space, walking, collision, Tab, history, edge recovery, lighting UI check, normal close or same-directory restoration has yet been validated. Final runtime binary/provenance will be frozen after observation coordination. Draft status must remain until those checks and independent review complete. Mac unlock is required to continue UI validation; no active UE instance is retained.
