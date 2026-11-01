# G3 Seed→Tree × Genesis integration probe

Date: 2026-11-01. Source: `87732d3d7456ca86ad03506489ef8defb5913ff6` (`codex/stg-g3-integration`, clean before this report). UE 5.8.3 installed build on macOS Metal SM6; Genesis 1.4.3 in repository `.venv-genesis`. `stg-demo`, seed 7, dt 0.01, eight physical steps, isolated worktree `Saved/EdgeWorldCausal/stg-demo`. These are engineering probes, not a G4 independent product acceptance.

Raw evidence is local only at `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-lxKhO5/`. `sha256-index.json` identifies every raw file; its own SHA256 is `e6e912a33f38af68a1eb64cd5b60bbf2f2579ff58c03b107b46905f8f0333b2a`. The raw directory is not portable to another machine. No user world state or previous Chaos state was changed.

## Do and Check

| Check | Result | Evidence |
| --- | --- | --- |
| Editor build | Pass: 28 actions, exit 0 | `ue_build.log`, `ue_build.exit` |
| Worker process roundtrip | Pass: `status → observe(0) → advance(1) → observe(1) → advance(2) → observe(2)`; all responses `ok`, both processes exit 0 | `first.*`, `restart.*`, `direct_probe.raw.json` |
| Genesis causal counterfactual | Pass as a probe: same tick-0 state hash `3aff0b8b…`; `shaoyang` yields tick-1 `influence_mm=-7`, `taiyang` yields `-35`; physics candidate and tick-1 state hashes differ | `counterfactual_*.jsonl`, `counterfactual_probe.summary.json` |
| Idempotency and worker restart | Pass: repeated tick-2 command returns identical result; history 0/1/2 equal across process restart; restart pure reads leave persisted hashes unchanged | `direct_probe.summary.json`, `direct_probe.raw.json` |
| Live UE ↔ worker ↔ Genesis | Pass for the bounded 0→1→2 path. UE launched a worker via absolute script path from project directory; Space generated two real commits, with tick-1 head `c933ad93…` and tick-2 head `193c4948…`. Metal screenshots show one, two and three abstract nodes respectively | `ue_tick0.png`, `ue_tick1.png`, `ue_tick2.png`, `ue_live.log`, isolated state manifest |
| UE history and camera read-only | Pass for sampled actions: keys 0/1/2 switched three historical renderings, W moved the camera, H and R returned/reconciled head. Before/after tick 2, revision 2, head `193c4948…`, event head `d28b52a6…`, manifest SHA256 `138a7e3f…` were byte-for-byte unchanged | `ue_history0.png`, `ue_history1.png`, `ue_camera_w.png`, `ue_tick2_state.json`, `ue_after_readonly_state.json` |
| UE restart recovery | Pass for sampled restart: after process shutdown, same state dir reloaded tick 2 and same manifest SHA256 `138a7e3f…`; the two-edge view rendered. Normal `⌘Q` on second run exited code 0, with `LogExit: Exiting` | `ue_pre_restart_manifest.json`, `ue_restart_tick2.png`, `ue_restart.log` |
| Window close path | Fail in one observed run: CUA click on the macOS close button at 01:51:12 caused `FSceneViewport::Destroy()` `IsInGameThread()` assertion on render thread, then UE crash. Worker was orphaned and stopped before the recovery run. The same application did exit cleanly via `⌘Q` on the second run. No stack frame implicates the causal callback; ownership remains undetermined | `ue_live.log` lines around 1461–1490; `ue_restart.log` normal exit |

Initial UE launch was blocked by missing Xcode MetalToolchain. Official `xcodebuild -downloadComponent MetalToolchain` installed 27B47; the first failure output is `ue_stdout.log`. Later Metal launch and rendering succeeded.

## Act and limitations

G3 integration is **partial**, not a parent V-STG pass. The bounded live path and recovery have evidence. The close-button crash needs a narrow UE/macOS shutdown investigation, with a second controlled reproduction before assigning it to project code. There is no raw UE transport JSONL capture, so live request/response identity is inferred from the persisted manifest, UE head display, worker process and screenshots. Negative UE identity responses, every camera/pause/visibility action, full performance trace, G0 visual quality threshold, and independent G4 acceptance were not run; their gates remain `inconclusive` or `planned` as applicable. The rendered geometry is an abstract graph proxy, not a realistic world or botanical tree.
