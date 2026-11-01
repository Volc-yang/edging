# H6B visitor character implementation record

Status: implementation in progress. Parent V-HOME/H6B; approved implementation card `doc/evidence/home-visitor-implementation-plan.md`. Base `489b97c`; branch `codex/home-visitor-character`; worktree `/Users/yangacan/edgeWorld/edge-world/.worktrees/home-visitor-character`.

## Execution and ownership

1. Implement released UE ACharacter/CharacterMovement/Camera visitor, safe entry and local edge recovery; wire continuous movement/look and Tab overview return into the existing GameMode/controller.
2. Update HUD input guidance and add focused movement/collision/mode checks. Owned paths: new `EdgeWorldVisitorCharacter.{h,cpp}`, `EdgeWorldCausalGameMode.{h,cpp}`, `EdgeWorldCausalHud.cpp`, focused visitor checks and this evidence directory.
3. Build with the installed official editor toolchain, then use this worktree's canonical launcher with `--launch --viewport-preflush`, default render thread, exclusive build/GPU ownership. Verify PID and engine initialization before binding UI.
4. Capture unique run/attempt evidence for walking, support, walls/rails, turning, Tab position retention, edge recovery, history, explicit Space, normal close and same-directory recovery. Compare all authority files independently before/after each read-only operation. Preserve failed attempts and inspect actual processes after tool errors.
5. Commit scoped changes and open an independent PR to `codex/plan-consolidation`; do not merge. H6C independent acceptance remains downstream.

No writes to worker/protocol, causal Actor/environment geometry, viewport or launcher. Space remains the only explicit Advance. Local character motion does not define Genesis character physics or approved world rules. The explicit preflush path is a limited development bypass, not a fix claim for the original default exit path. No validation has been run yet.
