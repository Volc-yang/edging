# H1d full live Genesis `-norenderthread` check

Date: 2026-11-01. Base `81bcd792708d1f801dd4f284dd121307b318ad9a`.
Worktree `/Users/yangacan/edgeWorld/edge-world/.worktrees/g3-live-safe-render`,
branch `codex/g3-live-safe-render`. Installed UE 5.8.3 / CL 58210709, Mac Metal
SM6, Genesis 1.4.3 Python. No project C++, worker or engine source changed.

**Result:** two bounded full-scene sessions with live Genesis passed the
sampled startup, tick 0/1/2, historical/camera read-only, restart and window-close
checks using `-norenderthread`. Deliver an explicit temporary launch option,
not a root-cause fix. Default-thread reliability remains **fail/open** and
V-HOME remains unaccepted. CPU/GPU performance and the cost of this mode were
not measured; earlier GQ timings are inapplicable.

Raw evidence is local at
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/G3-H1d-20261101/raw/`.
The checked-in `sha256-index.json` covers 120 raw files, including snapshots,
checkpoint blobs, logs, screenshots, the helper failure and successful repeats.
Index SHA-256:
`5660eec54469f0c19c120b3e1462fa2cbf4ccc26d32982a4a6ad38882b7709fc`.
Generated UserDir caches/configuration are excluded; authoritative state and
checkpoints are included. `summary.json` gathers startup and read-only evidence
without replacing the complete logs. `tested-source-sha256.json` identifies the
launch script and test source actually exercised.

## Change and checks

`scripts/launch_edgeworld_ue_mac.sh --launch --no-render-thread` appends only
the installed UE `-norenderthread` option. Omitting the option preserves the
default threading mode; build-only remains the default command behavior.
Help and launch status explicitly disclose experimental use, lack of root-cause
repair, unmeasured possible performance degradation and invalidity of old GQ
numbers. The project/worker ownership, actual UE App PID, prebuild gate and
explicit UserDir behavior are unchanged. See `doc/ue_mac_launch.md` for usage.

`bash -n` passed. Four focused launcher tests passed (exit 0): default command
builds only; normal launch retains default rendering; explicit workaround
forwards the flag exactly once and prints its limitation; build exit 23 prevents
launch even when the workaround is requested. These mock tests establish script
behavior only; the following real runs establish the finite runtime evidence.

## Real launch and close evidence

Both launches used the owning worktree project and worker through the real
launcher, with `/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldCausalGameMode`,
`-game -log -windowed -ResX=960 -ResY=600 -norenderthread`. Both shared the explicit
isolated UserDir `raw/world-user`, sequentially. Its worker state was exactly
`raw/world-user/Saved/EdgeWorldCausal/stg-demo`; no user world or other worktree
state was reused. Full Actor, environment, camera, HUD and controller remained
enabled, without H1b/H1c diagnostic switches.

Times in this table are UTC; raw logs retain millisecond timestamps.

| Milestone | Run 1 | Run 2, same directory |
| --- | --- | --- |
| Official Editor build | exit 0 | exit 0 |
| Actual UE / worker PIDs | 26583 / 26770 | 27582 / 27736 |
| Engine initialized | 04:25:58.021 | 04:31:43.466 |
| Validated initial observation | tick 0 at 04:26:01.684 | recovered tick 2 at 04:31:46.935 |
| First observed image | 04:28:28.788, tick0.png | 04:32:23.616, recovered-tick2.png |
| Window destroyed | 04:31:17.406 | 04:35:48.393 |
| UE / launcher exits | 0 / 0 | 0 / 0 |

Each log confirms map/GameMode, configured live worker, `Engine is initialized`,
validated observation, native window destruction, `RequestExit` and
`LogExit: Exiting`. Neither run logs the viewport assertion or a missing-module
startup warning. Each was initialized for more than 180 seconds before close;
these are active test sessions, not 180-second passive samples. The screenshots
establish that an image was visible by observation time, not the time of the
first GPU presentation. Close-call intervals are recorded separately from native
log events; CUA returning success does not independently establish delivery order.

After each session the UE App and worker were absent. Shutdown did not change
any authoritative file. Run 2 used new UE/worker PIDs and restored the same
manifest bytes and every checkpoint hash, demonstrating real process recovery.

## Genesis, HUD and read-only boundary

Space was pressed once after each confirmed observation to produce tick 1 and
then tick 2. UE acknowledged both commits, and the captured manifest contains
`causal-1` / `causal-2`, physical phases `shaoyang` / `taiyang`, distinct physical
candidate hashes and saved checkpoints. Event influences in this sequential
run are -7 mm and -48 mm; these are engineering probe values, not world rules.
The images show one, two and three nodes respectively, and the HUD identifies
head/observed tick and the physical probe. Recovery renders the same three-node
head without an additional Advance.

Tick-2 manifest SHA-256 is
`122ac2556d4ce20ade34a906a8f90b3d7bf118299586c26b377d8b1e98908fea`;
state/event heads are
`193c4948adde95d29e1deef4edafac63abbd61abe0fc47d75000af009bd28192` /
`d28b52a610c723ae0538ad9a826052482fed5a649f21ca9b56d248aad3abec0b`.
These and the four persisted files match before/after closing, after recovery
and at final shutdown.

Twelve completed per-action checks preserve before/after manifest bytes and all
four persisted file hashes: run 1 history 0/1/2, H, R, W and Right; run 2 repeated
history 0/1/2, A and Left. History/H/R also have a new matching UE observation
ack; camera checks use the visible framing change rather than a worker ack.
Historical screenshots distinguish viewed time from head time. This checks the
listed actions only; it does not prove every input, FPS, pause or visibility path.

The first run-2 evidence-helper batch timed out after failing to recognize new
acks. UE's raw log actually records successful 0/1/2 observations, and its App
and worker continued running. The tool timeout reset the CUA session. Original
`run2-history0/1` unsuccessful confirmation records and the partial
`run2-history2-before.json` remain; they are excluded from the twelve completed
checks. A fresh helper explicitly referencing run 2's log produced the successful
`run2r-*` records. This is an evidence-tool failure, not a UE crash, and is not
erased by the repeat.

## Limitations and next action

Two clean closes are limited evidence for this temporary execution path, not a
statistical reliability guarantee. The default-thread failures remain real and
unresolved. No PIE, packaged game, cross-platform, stress, performance or raw UE
transport JSONL identity-negative acceptance was run. There is no claim that
the temporary option fixes every UE error.

The images preserve `LIGHTING NEEDS TO BE REBUILT (16 unbuilt objects)` over the
HUD. This presentation warning is still present; it was not hidden or treated
as the viewport assertion. Runtime-light mobility/static-lighting assumptions
need a separate project-layer repair and visual check. Worker stderr also
retains upstream torch deprecation warnings.

Default-thread follow-up is specified in `default-thread-next-card.md`: evaluate
render synchronization before viewport owner release through public project
extension points, with same-adapter A/B gating and lifecycle regression evidence.
It is proposed only, with no engine edits or validated root-cause claim. GPU was
released and no UE/worker remained when this task completed.
