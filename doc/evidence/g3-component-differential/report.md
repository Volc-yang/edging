# H1b causal actor shutdown differential

Date: 2026-11-01. Base `0c77e3d`; UE 5.8.3 published Mac build, Metal SM6, same `EdgeWorldHost.uproject`, `/Engine/Maps/Entry`, `-game -log -windowed -ResX=960 -ResY=600`. Both worker environment variables were unset in all four runs. Each run had a unique `-UserDir` and `-abslog` under `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-H1b-20261101/raw/`. No Genesis worker ran. Original raw files are machine-local. `sha256-index.json` covers 40 files and has SHA256 `d3f3d21bbe204ecd369037d76c6196d5094c9d6042a88ba110055bb26432b4cf`.

## Plan and exact variant

Compare current full `EdgeWorldCausalGameMode` with a diagnostic variant that skips **only** its `AEdgeWorldCausalActor` spawn. Camera, directional/sky lights, PlayerController, SpectatorPawn and HUD remained present. The temporary GameMode source patch added `-EWDiagSkipCausalActor` and a variant log line; patch SHA256 `53947dde7b5b6f8ac61841fea5577a9e978279b86bd44139ab94593753fbfaee`. Full and variant Editor builds exited 0. The patch was reversed after runs: GameMode source SHA256 is again `492eb443bb49bd4c0f0a8f66366ce226dc89e2bcec9855036fe1f8f3cd13721b`, and only this report is committed. Diagnostic binary files remain under ignored project output, not a product delivery.

## Do and Check

No CUA accessibility inspection occurred during each passive interval. Shell checks confirmed the UE PID and absence of fatal log messages. Each remained live for more than 180 seconds after `Engine is initialized`; then the agent obtained the window through CUA and attempted its close button. `close-start.utc`, `close-end.utc`, process snapshot and complete UE log preserve the timing. A CUA `App quit` or `procNotFound` response does **not** prove whether the click was delivered before process exit.

| Arm | Variant log | Passive result | Close/exit result |
| --- | --- | --- | --- |
| `full1` | Base GameMode, actor enabled | Live >180 s | Window destroyed 03:33:14 UTC; `RequestExit`, `LogExit: Exiting`, exit 0 |
| `full2` | Base GameMode, actor enabled | Live >180 s | Window destroyed 03:37:31 UTC; `RequestExit`, `LogExit: Exiting`, exit 0 |
| `skip1` | `H1b diagnostic skip causal actor: true` | Live >180 s | Window destroyed 03:42:24 UTC; `RequestExit`, `LogExit: Exiting`, exit 0 |
| `skip2` | `H1b diagnostic skip causal actor: true` | Live >180 s | Close attempt started 03:47:00 UTC; window destroyed 03:47:05.700; `SceneViewport.cpp:196 IsInGameThread()` assertion 12 ms later on render thread; exit 1. CUA returned `procNotFound`; delivery uncertain |

The `skip2` crash context XML and 414 KiB minidump were copied to the raw bundle; no new macOS DiagnosticReports `.ips` file was found in the bounded search. `CrashContext.runtime-xml` repeats the same assertion and includes GameThread and render-thread stacks. The crash log has no normal `RequestExit` or `PreExit`. After the run, no matching UE or causal worker process remained. Full logs and the patch are indexed rather than paraphrased as a code fix.

## Act

The causal Actor, its graph proxies and H2 environment are **not necessary** for this observed assertion: `skip2` crashed while that spawn was disabled. Two full clean exits and one skip clean exit also show the failure is intermittent; they do not establish relative risk or reliability pass. The triggering window-destruction action is still not conclusively known, because the click delivery boundary is unobserved. No actor or UE source change is justified from this sample. The next differential should hold the actor disabled and test camera/`SetViewTarget` versus custom PlayerController/HUD in separately identified variants, or symbolicate the captured game-thread/minidump stack. Keep the shutdown reliability gate `fail/open` and V-HOME unaccepted.
