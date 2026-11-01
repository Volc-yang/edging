# H4 combined causal observatory integration

Date: 2026-11-01. Status: **bounded integrated technical path passed; V-HOME parent remains open**. Source commit `cb10df7b85bb46ed70ec0a026b13bbdd4eabb2eb` in isolated `codex/home-integration` worktree, combining GQ/H1/H2/H3 PRs. UE 5.8.3 installed release engine, Mac Development Editor build, Metal SM6, Genesis 1.4.3 worker. This is an abstract causal observatory, not a realistic 4D world or independent H5 visitor acceptance.

## Identity and raw evidence

The published `UnrealEditor` launched this worktree's `EdgeWorldHost.uproject` with `/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode -game -log -windowed -ResX=960 -ResY=600 -UserDir=/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H4/run-user`. `EDGEWORLD_CAUSAL_PYTHON` and `EDGEWORLD_CAUSAL_WORKER` were absolute paths to this repository's Genesis environment and worker. The worker argv confirmed its state directory was `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H4/run-user/Saved/EdgeWorldCausal/stg-demo`, isolated from UE's shared user directory. The same `-UserDir` was used for restart.

All original logs, CUA native window screenshots, snapshots and exit-code files are local only at `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/HOME-H4/raw/`. `sha256-index.json` covers 19 files; index SHA256 `4f235b06e414595632b01ca46ef50899d3b9cb95e69bfb4fced5f329f9a9967f`. The requested UE window was 960×600; captured macOS screenshot pixel dimensions are affected by display scaling and do not establish the internal render resolution.

## Do and Check

| Check | Observed result | Original files |
| --- | --- | --- |
| Exact combined build | `EdgeWorldHostEditor Mac Development` completed, exit 0; build log SHA256 `f51caed4…7abdc0c` | `build.log`, `build.exit` |
| Live UE ↔ worker ↔ Genesis | Isolated authority manifest progressed 0/0 → 1/1 → 2/2 only after two explicit Space presses. Head state at tick 2 was `193c4948…28192`; event head `d28b52a6…ec0b`. HUD showed the Genesis engineering probe at `-7 mm` on tick 1 and `-48 mm` on tick 2 | `first-ue.log`, `tick0.png`, `tick1.png`, `tick2.png`, `head2-before-readonly.json` |
| Combined presentation | Screenshots show H2 observatory geometry and H3 head/view HUD together at all three ticks. At tick 2 three colored causal nodes and two edges are visible. The unrelated white default Pawn sphere from H2's standalone run is absent after H3 selected `ASpectatorPawn` | `tick0.png`, `tick1.png`, `tick2.png` |
| Historical/camera pure reads | Keys 0/1/2 rendered the corresponding historical graph and HUD labels; history 0 displayed `head tick 2 / viewing tick 0 (history, read only)`. H and R returned/refreshed head; W moved camera. Authority manifest SHA256 before and after all sampled read-only actions remained `068c76b503362960ef9de55c2e883396fc35f029b5ac4940099684a256f868e9` | `history0.png`, `history1.png`, `history2.png`, `camera-w.png`, `head2-before-readonly.json`, `head2-after-readonly.json` |
| Restart recovery | First run exited via ⌘Q with exit code 0 and `LogExit: Exiting`; no worker remained. Same `-UserDir` restarted into tick/revision 2/2, same head `193c4948…28192`, same manifest SHA256 `068c76b5…6f868e9`; HUD and three-node graph reappeared. Second ⌘Q exit code 0, `LogExit: Exiting`, no worker remained | `first-exit`, `first-ue.log`, `restart-tick2.png`, `head2-after-restart.json`, `restart-exit`, `restart-ue.log` |

The original screenshot SHA256 values are in the raw index. `tick2.png` SHA256 is `e18365c6198655093a898b3177a132e52cca1593b3ef47e6c6f1b70a14d74123`; `restart-tick2.png` is `0741da59284b9a43a069ffd93c38edbafac504fc40b68f47e0d4324aa375b2de`. Different screenshot hashes reflect capture time/window pixels; recovery is established by manifest/head and visual inspection, not expected pixel equality.

## Act and limitations

This H4 run verifies the finite combined visual, explicit advance, sampled read-only actions and recovery on the exact integrated commit. **V-HOME is not accepted:** G3/H1/H1a separately reproduced the `SceneViewport.cpp:196` render-thread shutdown assertion, including with the worker disabled, while this run's two normal exits do not eliminate intermittent failure. No raw UE transport JSONL was captured. Pause/visibility/frame-cap read-only actions, negative live identity responses, independent H5 visitor review, approved visual reference, asset quality and frozen performance threshold were not checked here. Keep the shutdown reliability gate open and assign the smallest diagnostic/fix after its owner is established; retain this run as positive but bounded evidence.
