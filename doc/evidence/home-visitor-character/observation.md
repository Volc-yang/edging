# H6B / H6C frozen read-only observation interface

Coordinator accepted `VisitorStatus` and `VisitorTrace <seconds>` on 2026-11-01. These are player-controller Exec commands entered through the UE console, not visitor HUD controls. They cannot advance the worker or teleport the visitor. Do not confuse console input time, engine frame/world time and wall-clock capture time.

`VisitorStatus` emits one `Visitor status` line. `VisitorTrace 3` enables status samples every 0.2 world seconds and actual capsule blocking-hit records for that finite interval. Duration is clamped to 0–10 seconds; default argument 3, initial sampling state disabled. `VisitorTrace 0` stops sampling. The command emits `Visitor trace duration=... interval=0.2 max_duration=10`. Paused world time does not consume the remaining interval; the command does not alter pause or authority state.

The following is a **field template, not an observed runtime result**:

```text
Visitor status frame=<engine frame> time=<world seconds> pawn=<actor name> view=<view-target name> position=X=... Y=... Z=... rotation=P=... Y=... R=... velocity=X=... Y=... Z=... mode=<EMovementMode integer> grounded=<0|1> falling=<0|1> capsule=<radius cm>,<half-height cm> floor_blocking=<0|1> floor_walkable=<0|1> floor_dist=<cm> floor_actor=<actor name> floor_component=<component name> blocking_overlap=<0|1>
Visitor blocking hit frame=<engine frame> time=<world seconds> actor=<blocking actor> component=<blocking component> point=X=... Y=... Z=... normal=X=... Y=... Z=... start_penetrating=<0|1> penetration_depth=<cm>
Visitor recovery trigger frame=<engine frame> time=<world seconds> before=X=... Y=... Z=... bounds=x[-430,830],y[-480,550],z>=-300
Visitor local entry restored: X=... Y=... Z=...
Visitor view=<overview|walking> position=X=... Y=... Z=...
```

`mode` comes directly from CharacterMovement (`MOVE_None=0`, `MOVE_Walking=1`, `MOVE_Falling=3`). Floor fields come from its actual `CurrentFloor`, not a substitute ray. `blocking_overlap` is a current-world capsule query against `Pawn`, explicitly ignoring the visitor itself. Hit fields come from capsule `OnComponentHit`; source actor/component names distinguish wall, rail and floor. `pawn` must remain the possessed visitor; walking view must target it, overview view must target the camera. Tab emits the preserved visitor location and stops local movement; it does not repossess another pawn.

For continuous-hold evidence, enable a sufficiently long trace, close console, record input start/end and hold WASD through at least three distinct sample frames with positions and velocities. Stop at a wall/rail while tracing and retain its named blocking hit, normal and penetration fields alongside final support/overlap. Capture each operation's authority file set before/after independently. A camera change, grounded flag alone, or absence of motion alone does not prove collision or continuous movement.

The recovery guard runs during local character Tick at center position x outside [-430,830], y outside [-480,550], or z below -300 cm. In particular walking toward y<-480 should trigger recovery while still near the open floor edge; no intentional fall or debug teleport is required. Pair trigger-before with the next successful entry-after record, then capture actual grounded floor and clear overlap. Entry recomputes floor height and verifies a clear capsule before restoring local position. Cross-process pose persistence is not promised: reopening verifies authority restoration and safe new entry.

## Actual no-UI fixture sample

The final NullRHI test log `H6B-20261101/nullrhi-bchkcP9v/ue.log` contains these movement samples from the same continuous `AddMovementInput` interval, not keyboard/Metal evidence:

| Frame | World seconds | X cm | X velocity cm/s | Floor | Blocking / walkable | Overlap |
| --- | --- | --- | --- | --- | --- | --- |
| 664 | 1.017 | 0.569 | 34.133 | Floor | 1 / 1 | 0 |
| 676 | 1.217 | 32.533 | 180.000 | Floor | 1 / 1 | 0 |
| 688 | 1.417 | 68.533 | 180.000 | Floor | 1 / 1 | 0 |

Later in the same fixture, wall contact at frame 1132 names `EdgeWorldCausalEnvironment_0/LeftWall`, impact x=-390, normal `(1,0,0)`, initial penetration=0 and depth=0. Character center is x=-355.899, z=-49.850 with floor distance=2.150 and clear blocking overlap. Frame 1206 records the natural open-edge guard at y=-482.533 and the following entry record restores `(0,-300,-50)`. These records demonstrate that the instrumentation works against actual CharacterMovement scene queries; H6C still requires a fresh real-input interval at its integrated source/binary.
