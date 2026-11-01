# H3 visitor HUD and camera probe

Date: 2026-11-01. Parent: `V-HOME/H3`. Base: `db20383` (`codex/plan-consolidation`). Worktree: `.worktrees/home-visitor-hud`, branch `codex/home-visitor-hud`. UE 5.8.3 installed build, Mac Metal SM6, `EdgeWorldCausalGameMode`, fixed `stg-demo`, local Genesis 1.4.3 worker. This task changes the UE presentation layer only. It does not change the worker, 4D contract, Genesis candidate, or authority gate.

## Implementation

- `AEdgeWorldCausalHud` shows world ID, validated latest head tick/revision, currently observed tick, current versus read-only history, Genesis *engineering probe* influence, and controls. Before the first accepted Observe it says no validated observation yet; it never labels an unverified response as committed.
- `GameMode` presents to HUD only after `HeadGate.Accept` or `CheckHistory` returns true. Rejected responses retain the previously presented view. Existing transient debug text was removed after it visibly overlapped the HUD; equivalent observations remain in UE logs.
- `DefaultPawnClass` is invisible `ASpectatorPawn`. The unrelated large white default pawn mesh seen in H2's initial Metal view was absent in H3's own-branch view. Existing camera pose and custom keyboard navigation were preserved; combined H2/H3 view remains to be checked at H4.

## Checks actually run

| Check | Result |
| --- | --- |
| `Build.sh EdgeWorldHostEditor Mac Development` after final source change | Pass, exit 0; final build log SHA256 `e8e58f3f…ec81b8` |
| NullRHI `edgeWorld.CausalObservation.StrictIdentity` | Pass, 1/1, exit 0; log SHA256 `c5f935d5…b58149` |
| Metal, own branch, tick 0→1 via Space | HUD first showed connecting, then head/view 0, then head/view 1 and probe influence `-7 mm`; log confirms observations 0/1 |
| Metal history and camera | Key 0 showed `head tick 1 / viewing tick 0 (history, read only)`; H, 0 and W left `abstract_world.json` SHA256 `b30dcc8f525f5fb6d4d20701fe53f76583d84418153a242b7b5d393622cf1e64` unchanged |
| Metal process exit | `⌘Q` exit code 0, `LogExit: Exiting`; no matching UE/Worker process left |

Raw build, NullRHI and Metal logs are local only at `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/H3-VisitorHud-20261101/`. Final Metal log SHA256 `09d13560…efcb1bb18`. First Metal run showed old transient debug messages overlapping the new HUD; that run's log SHA256 is `36bb5a0c…759df8b74`; the overlap was fixed and the second Metal view was inspected. No durable raw screenshot was captured in this H3 task, so visual legibility is a bounded owner observation; H4 must capture combined H2/H3 raw images and independent review. This test used ⌘Q; the separate G3 window-close assertion remains an open failure and is not resolved by this result.
