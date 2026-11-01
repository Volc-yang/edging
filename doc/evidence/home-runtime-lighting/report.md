# H-LIGHT-01 runtime directional lighting

Status: scoped lighting checks complete, awaiting independent review.
Date 2026-11-01. Base `e577ac2a2fd28a86c430f156bf0eb5cef32fe000`;
worktree `.worktrees/home-runtime-lighting`, branch `codex/home-runtime-lighting`.
Installed UE 5.8.3 / CL 58210709, Metal SM6, live Genesis 1.4.3.

The runtime directional light now explicitly uses Movable mobility. This
removes a real unmet baked-lighting dependency in the dynamically generated
observatory. Geometry, collisions, light intensity, exposure, material, camera,
HUD, worker and world evolution are unchanged. No screen-message suppression,
global static-lighting disable or engine-source change was used.

## Cause established by runtime evidence

The installed engine's `Light.cpp:244` defaults `ADirectionalLight` to
Stationary. The GameMode previously set only its intensity; the sky light
already explicitly used Movable. The observatory creates Static geometry at
runtime without baked lighting.

The baseline's real `edgeworld.DumpLightingEvidence` output established:

- `NumLightingUnbuiltObjects=16`;
- directional mobility `1` (Stationary), sky mobility `2` (Movable);
- exactly one light with unbuilt interactions: `DirectionalLight_0`;
- precisely sixteen primitives: floor, central walkway, three walls, three
  pedestals/rings/markers each, and two rails, all on the causal environment.

After the single mobility change, the actual world count and the native dump's
unbuilt light/primitive counts are all zero at fixed tick 0, tick 2 and recovered
tick 2. Both actual light mobilities are `2`. The saved Metal images show the
warning before, its absence after, and the same visible floor, graph nodes,
HUD and shadows. The geometry remains the existing BasicShapes technical scene;
this is not a claim of realistic art quality.

`edgeworld.DumpLightingEvidence` is a manually invoked console evidence entry
in the same GameMode translation unit. It logs world count and actual light
identity/mobility, then invokes UE's `DumpUnbuiltLightInteractions`. It never
advances authority. The native dump flushes render commands; these commands
were used only for this lighting card, outside H1f's controlled experiment.

## Build and process evidence

The baseline and candidate have the same evidence entry. The baseline lacks
only the candidate directional `SetMobility(Movable)` line. Both exact source
variants and source/binary SHA-256 maps are archived. This avoids treating an
old H1e binary as evidence for new code. Official Editor builds succeeded for
both variants and their recovery launches; build/launcher logs and exits remain.
The final candidate source and binary still match their captured hashes.

All accepted sessions use the real canonical launcher, owning-worktree worker,
explicit independent UserDir and the **same `--no-render-thread` temporary mode**
(`-norenderthread`). They use the same Entry map, causal GameMode, 960×600
requested window size and fixed camera/exposure. This choice isolates lighting
from the unresolved default-thread close issue; no default-thread reliability
or performance acceptance is claimed.

Times below are UTC. First observed image time is when a visible image was
captured, not the time of the first GPU presentation.

| Run | UE / worker PID | Engine initialized | First observed image | Actual UE/launcher exit |
| --- | --- | --- | --- | --- |
| baseline2 | 42379 / 42502 | 06:36:17.098 | 06:36:34.168 | 0 / 0 |
| baseline recovery | 43640 / 43812 | 06:39:30.653 | 06:41:01.644 | 0 / 0 |
| fixed1 | 44705 / 44863 | 06:44:28.213 | 06:45:21.261 | 0 / 0 |
| fixed recovery | 45445 / 45582 | 06:47:18.686 | 06:48:58.726 | 0 / 0 |

Each accepted primary explicitly advances tick 0→1→2 through two acknowledged
Space actions. Recovery uses the same respective UserDir and new processes;
the initial validated observation is tick 2, with no recovery Advance. Every
accepted session exits via CmdQ. No new UE crash or reporter was produced in
these sessions; final inventory has no test UE, worker, reporter or build task.

## Authority and recovery checks

Twelve accepted per-action checks preserve all four authority/checkpoint file
hashes, with a new matching observation ack for historical/head operations:

- baseline primary: W and S;
- baseline recovery: explicitly repeated history 0, H and W;
- fixed primary: history 0, H, W and S;
- fixed recovery: history 0, H and W.

The index names every accepted record. Primary baseline history/head helper
pairs were damaged by the tooling issue below and are excluded, although UE
logs contain their successful observations. Corrected recovery history/head
checks provide independent complete before/after pairs. Camera checks preserve
visible framing changes and file hashes, not worker acks.

Within each world, all four persisted file hashes match before close, after
recovery, after the accepted read-only matrix and after final shutdown. Final
state files/checkpoints are copied into raw evidence, and the compact index
retains each world's exact file hashes. Fresh baseline/fixed world checkpoint
bytes are not required to match each other. Only explicit primary Advance
changes authority; lighting and observation do not.

## Tool errors and excluded evidence

The first UI bind was attempted before the target had started. `getApp`
automatically launched an empty Editor (PID 41737); its timeout did not mean
the requested process was absent. That short overlap contaminated `baseline1`
(UE PID 41914). The exact two owned PIDs were terminated, both disappeared and
the real launcher recorded exit 0. The original attempt, process inventory and
error note remain; baseline1 is excluded from the comparison. Baseline2 begins
after verified process cleanup. No global termination or report-send was used.

An initial Space was consumed by the open console; its false ack and unchanged
state are retained, followed by a confirmed tick-1 action. A tick-2 console
attempt using CmdA did not execute the evidence command; the baseline's
recovered-tick-2 command supplies the actual second native dump.

The first recovery helper retained its previous arm/log closure across tool
cells. It wrote some recovery records into `baseline2`, overwriting the original
primary `history0-before.json` and `head-before.json`, and polled the wrong log
until the tool reset. Those original before records cannot be recovered; the
affected primary pairs are excluded rather than presented as fully preserved.
Remaining records and their timestamps, the explicit error summary and raw UE
observations remain. The same live UE/worker processes were verified before
rebinding; they were not restarted because of a tooling timeout. A corrected
helper accepts explicit run/log/UserDir context per call and produced the
accepted `baseline-recovery/verified-*` records. No overwritten record is
claimed as an accepted primary baseline before/after pair.

The app bundle ID was ambiguous and one action required refreshing active AX
state; neither is counted as an engine failure. Follow-up operations bound the
verified running full app path, checked the actual PID/log path and used only
new log content after each action's offset. `helper-errors.json` and remaining
partial records retain these limitations.

## Evidence and disposition

Raw root:
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/H-LIGHT-01-20261101/raw/`.
Four primary images are `baseline2/tick0.png`, `baseline2/tick2.png`,
`fixed1/tick0.png`, `fixed1/tick2.png`; recovery images are in each recovery run.
The checked-in `evidence-index.json` authenticates the machine-local full raw
index with **193 files**, including logs, images, remaining failed attempts,
source variants and copied final authority/checkpoint blobs. UserDir generated
caches/configuration are excluded; final authority copies are included.
Full raw-index SHA-256:
`1278252f5a4de80ee196c367f93ea63e1fc387a1a77ababebdb45bc35954b580`.

The lighting warning gate passes for this finite runtime scene in the declared
temporary rendering mode. Independent review and canonical integration remain
coordination's responsibility. No PIE, packaged, cross-platform, asset-scale,
formal visual or performance gate was run. Default-thread viewport reliability
remains separate, with its existing evidence and limitations. GPU/build use is
released; this task will perform no further runtime testing without coordination.
