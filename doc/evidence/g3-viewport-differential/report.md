# H1a published-UE viewport differential result

Date: 2026-11-01. Base `a421f78`; UE 5.8.3 published Mac build, Metal SM6, same `EdgeWorldHost.uproject`, `/Engine/Maps/Entry`, `-game -log -windowed -ResX=960 -ResY=600`. The only deliberate differences were GameMode and disabled worker environment. Project modules were rebuilt for this worktree on first launch. No UE engine or project source was changed.

Raw evidence: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-H1a-20261101/` (machine-local); `sha256-index.json` SHA256 `9e2905a2e04d010f80e5a7167f17ee4a7d51b12dd455c1120797cde2144e69d8`.

| Arm | Runtime | Observation and exit | Raw log SHA256 |
| --- | --- | --- | --- |
| A | `EdgeWorldCausalGameMode`; both `EDGEWORLD_CAUSAL_PYTHON` and `EDGEWORLD_CAUSAL_WORKER` unset | `Causal world` logged at 02:58:40 and engine ready 02:58:41 UTC. No worker process existed; log warns that the two variables are required. After the planned 180-second passive interval, a CUA close-button call returned `procNotFound`. UE log shows window destruction 03:02:32.593 then `SceneViewport.cpp:196` `IsInGameThread()` assertion 6 ms later on the render thread; exit code 1. **Whether the click event was delivered is unobserved.** | `6ab42df9b9e1df4316413f594e7ea3758f359d7e144e37cdf05e2ef5ed6b3f28` |
| B | `/Script/Engine.GameModeBase`; same project/map; worker variables unset | Game class confirmed `GameModeBase`; engine ready 03:04:50 UTC. Blank viewport remained alive for over 180 seconds without fatal log. After an intentional CUA close at 03:12:11, UE logged `RequestExit(0, UGameEngine::Tick.ViewportClosed)` and `LogExit: Exiting`; exit code 0. | `9ee2a3880988df4a17201a142baf794b321b6f60b1e763dd66f08b643288aa3e` |

Run start/end times and exit codes are in each raw arm directory. No UE or causal worker process remained after the comparison. A had no Genesis worker at any point, so the same assertion can occur without worker process startup, transport requests, or Genesis simulation. B's one clean sample cannot prove that the published UE viewport is generally safe. A and B differ in causal actor, camera/light setup, controller and rendered content; they do not isolate a single project function.

The earlier GQ passive sampling run logged the same assertion before its planned close action; H1 full-sequence logged the same assertion while its attempted close action failed with `procNotFound`. Together with A, this keeps both natural viewport destruction and close-time rendering race hypotheses open. The observed stack contains UE Engine/SlateRHIRenderer render-thread frames and no project frame. The original failure must not be erased by B's successful exit.

**Act:** shutdown reliability remains fail/open; attribution inconclusive. Next differential should keep the causal scene while selectively disabling its actor/camera/controller setup in a task-owned release-plugin branch, or use a symbolized native crash capture, then compare with B. A project or plugin fix must be evidence-led; no UE source change is warranted from this report.
