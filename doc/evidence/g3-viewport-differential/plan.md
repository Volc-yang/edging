# H1a published-UE viewport differential

Base `a421f78`; branch `codex/g3-viewport-differential`; published UE 5.8.3 Mac Metal SM6. This is a diagnostic comparison for the observed `FSceneViewport::Destroy()` render-thread assertion. No runtime, plugin, or engine source changes are authorized in this task.

## Controlled inputs

Both arms use this worktree's `EdgeWorldHost.uproject`, `/Engine/Maps/Entry`, `-game -log -windowed -ResX=960 -ResY=600`, the same published UE build, and a fresh worktree-specific Saved directory. Only the game-mode and worker configuration differ:

- A: `/Script/EdgeWorldHost.EdgeWorldCausalGameMode`, with both `EDGEWORLD_CAUSAL_PYTHON` and `EDGEWORLD_CAUSAL_WORKER` unset. It still spawns the causal actor, camera, light, and viewport, but cannot launch the worker.
- B: `/Script/Engine.GameModeBase`, with worker variables unset. It keeps the same project module loaded while avoiding the causal game mode and its actor.

Run each arm alone. Record start/ready/end timestamps, exact invocation, UE and worker PIDs, state of the game window, complete `EdgeWorldHost.log`, stdout, exit code and SHA256. The fixed observation interval is 180 seconds after `Engine is initialized` and game-window readiness. If the window disappears or UE exits before the planned close action, mark it a natural/pre-click event. If still alive at 180 seconds, click the game-window close button via CUA, then record its exit. Do not count a planned close as a spontaneous crash.

## Check and Act

Compare the two arms with the original G3, GQ passive, and full-sequence H1 logs. A repro in B would weaken causal-component attribution; a repro only in A would narrow the suspect scope but still require stack/lifecycle evidence. No repro in two finite samples is inconclusive. If the UE build requests module rebuilding in this worktree, use the official UE prompt and record that setup step. Avoid running concurrently with H2 or another Metal process; wait for the lead's GPU signal.
