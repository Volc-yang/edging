# H6C independent visitor acceptance

Status: bounded independent integration checks passed; ready for coordination
review. Parent V-HOME/H6C, 2026-11-01. Exact base
`f674483db3eec1f8bb71ed00f9e626928ea5de25`, containing H6B merge `a2ae0f1`.
Branch/worktree `codex/home-visitor-independent-acceptance` /
`.worktrees/home-visitor-independent-acceptance`. This owner did not implement
H6B. All new tracked changes belong to this evidence directory; no product,
configuration, world, viewport, worker or launcher source was modified.

## Version and real entry

Installed UE 5.8.3 / CL 58210709, Mac Metal SM6, live Genesis 1.4.3. Both fresh
process sessions used this worktree's canonical `scripts/launch_edgeworld_ue_mac.sh
--launch --viewport-preflush --user-dir <absolute isolated directory>`.
The same explicit project synchronization option retained default rendering
threads; neither session used `-norenderthread`. The shared isolated UserDir is
`/Volumes/DevSSD/Unreal/Projects/EdgeWorld/H6C-20261101/raw/world-user-attempt1`.

The first official Editor build succeeded; recovery's canonical build was up to
date and succeeded. This worktree's host binary SHA-256 was
`34f4567ea4580dfbf8964da170c729fa8684485230795439a2c17e98132c08e5`.
Source/configuration/launcher/binary hashes matched throughout both sessions;
immutable copies are included in raw evidence. An identical source rebuild
need not have H6B's binary hash because its worktree/debug paths differ.

Times below are UTC. Image time means first captured visible image, not first
GPU presentation. Startup/close input return values are separate from actual
process and native-window evidence.

| Session | UE / Worker PID | Engine initialized | First visible image | Close / native window destruction | UE / launcher exit |
| --- | --- | --- | --- | --- | --- |
| primary | 63931 / 64158 | 08:58:07.713 | 08:59:32.554, tick0 | window button / 09:07:02.774 | 0 / 0 |
| recovery | 66073 / 66208 | 09:07:40.189 | 09:09:01.978, restored tick2 | CmdQ / 09:10:22.629 | 0 / 0 |

The actual target PID, command, log, UserDir and initialized observation were
verified before binding the running App. Each action rechecked its explicit
run context and actual PID/command; log slices use byte offsets taken before
the action. No App was opened to inspect an exited reporter. Startup/exit
inventories and the final process inventory contain no test UE/Worker/reporter
or UBT residue. No reporter, new UE error, ensure or assertion was observed in
these sessions. No signal cleanup or UI retry was needed.

## Independent route and checks

The primary session began from a new tick0 world. The following results come
from this independent process, actual input and native CharacterMovement
records, rather than H6B's owner test or changed images alone.

| Check | Evidence and bounded result |
| --- | --- |
| Safe entry / standing | Actual capsule 34/88 cm; standing center `(0,-300,-50)`, floor gap 2 cm over the observatory floor near z=-140; `grounded=1`, walkable/blocking floor and overlap=0 throughout the standing samples |
| Continuous walking | `free-channel-a-attempt1`: five distinct moving frames/positions inside one recorded A hold, nonzero velocity; position x=29.024→205.120, then stopped. This does not infer frame-rate performance |
| Rail blocking | Actual `WalkwayRail-1` hit inside held W interval, impact y=-220 and normal `(0,-1,0)`, no initial penetration; stopped center y=-254.100, then S moved away to y=-377.754 |
| Wall blocking | Actual `LeftWall` hit inside held D interval, impact x=-390 and normal `(1,0,0)`, no initial penetration; center x=-355.900, then A moved away to x=-232.270 |
| Natural edge recovery | Held S crosses y=-481.573 at frame 36672, logging the declared y<-480 guard; same-frame restore `(0,-300,-50)`. Continued held input moves away again; final support/overlap is valid. No debug teleport or induced fall was used |
| Turn | Separate Right/Up holds change yaw 90→120.661278 and pitch 0→12.963567 while retaining position. Physical mouse is evaluated separately below |
| Tab / overview | Same possessed Pawn and pose `(-0,-389.005,-50)` / `(12.963567,120.661278,0)` retained across overview camera navigation, history and return; overview mode None/ViewTarget CameraActor, returned mode Walking/ViewTarget visitor with valid floor |
| Explicit Advance | Walking Space commits exactly 0→1; overview Space commits exactly 1→2. Each manifest gains one command/event; final command set is exactly `causal-1`, `causal-2`. Genesis candidate influences are -7 and -48 mm |
| Historical observation | Separate 0/1/2/H/R actions each have a new matching observation ack and unchanged complete authority-file maps. Head remains 2 while historical viewed tick varies |
| Visible scene | Native JPEG images preserve walking/overview, HUD, history and lighting. A restored overview framing image shows all three nodes/two edges at head2; screen messages remain enabled |
| Same-directory recovery | New UE/Worker start directly observes tick2, no recovery Space/Advance. New safe standing, continuous A navigation, history0/H, Tab/overview turn/history1/2/return and R all preserve authority |

The initial recorded control rotation before the planned route was
`(-27.795097,3.860317,0)`. It was observed, not silently assumed to be entry
heading 90. The first A hold therefore naturally reached the edge guard and
reset heading; that attempt is retained as navigation/guard evidence. A separate
free-channel case and a dedicated S edge case supply the clearly bounded route
checks above. No cause or isolated mouse result is inferred from the initial
heading. A first overview rotation cropped the far graph node; separate
read-only Left/S navigation restored full framing, with all attempts retained.

## Authority boundary and restoration

There are **35 complete independent read-only before/after pairs**: 24 primary
and 11 recovery, including the two lighting-command pairs and standing/status
instrumentation. These are 35 action pairs, not 35 distinct locomotion gates.
Each compares the entire file set and individual SHA-256 values: two files at
tick0, three at tick1 and four at tick2. Only the two explicit Space action
pairs change authority. Every navigation, turn, Tab, guard, history/refresh and
evidence-command action has its own comparison; route-end hashes are not used
as substitutes. Sampling commands are finite and are stopped after each hold.

Primary preclose/postclose, recovery first capture/preclose/postclose and final
persisted entities have identical four-file maps. Final logical tick/revision
is 2/2, state head `193c4948…28192`, event head `d28b52a6…ec0b`.
`checks-attempt2.json` names all pairs, parses sample timestamps against actual
hold intervals, checks named hits, Tab poses, event counts, recovery and actual
exits. `verify_evidence.py` can rerun read-only without writing an output.

Each session also invokes the existing lighting command: actual
`NumLightingUnbuiltObjects=0`, zero unbuilt light and primitive interactions.
This native dump flushes rendering commands. Consequently these sessions are
combined developer-entry checks, not a controlled experiment proving preflush
alone caused clean exit or improved failure rate. Native exit logs do record
`threaded_rendering=1`, opt-in preflush, non-null unchanged viewport owner and
flush end before window destruction (23.060 / 0.149 ms); these durations do not
establish performance targets.

## External physical-mouse case independently reviewed and reused

As authorized by the H6C card, the physical mouse action from H6B recovery PID
57629 is independently reviewed and reused; it is **not a new H6C mouse run**.
The 25 selected original records were freshly checked against H6B's final raw
index. All six archived product source files match this integration; the
configuration and canonical input path diff from `c3a00f8` to `f674483` is empty.
`manual-mouse-reuse-attempt1.json` records those identities and external hashes.

Original native before/after pose, after-image captured before console input,
the user's explicit physical-only confirmation and unchanged authority support
the finite conclusion: deployed physical mouse can turn while presentation is
authority-read-only. Position remained `(-45.460,-254.025,-49.850)`, pitch/yaw
changed `-8.484179/+5.584214` degrees, four authority files stayed identical.
No additional user action was requested.

Original physical-event MouseX/Y were not logged, the event time is only
bounded, and an old fixture reporter appeared during the original interval.
This case does not prove a low-level per-axis trace or clean reliability trial.
Arrow results above do not substitute for that physical mouse evidence.

## Integrity, disposition and remaining gates

Raw root: `/Volumes/DevSSD/Unreal/Projects/EdgeWorld/H6C-20261101/raw/`.
The compact `evidence-index.json` authenticates **455 raw files**, including
actual images, byte-format records, logs, input intervals, snapshots, immutable
product/source/configuration/binary and final authority/checkpoint entities.
Generated UserDir caches are excluded; the final authority copy is included.
Full raw-index SHA-256:
`049fdabc4cfdd29ddad733b67ea9decab4fa8b83a6a086635b5941442efd7104`.
All 455 hashes were independently recomputed. Original H6B mouse files remain
external, explicitly identified and separately hashed; they are not counted
as newly captured H6C files. No raw records were overwritten, lost or decoded
from a fallback serialization during this task. Screenshots are stored with
their actual JPEG extension and magic bytes, unedited.

Accept only the finite local visitor route, state-read-only boundary and
revisit behavior on this exact integrated development path. Coordination must
review this independent PR before integration. Formal realistic art, performance
thresholds, vehicle landing, general world/Genesis avatar physics, broader human
experience, PIE/packaging, other platforms and original default-thread exit
reliability remain open. The earlier reporter's own teardown issue is not
declared fixed. Build/GPU use is released, with no further task runtime planned.
