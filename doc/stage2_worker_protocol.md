# Stage 2 edgeWorld worker (P3)

Status: finite single-body vertical slice; not a production storage or physics
runtime. Source lives in `engine/edgeworld_worker/` and uses the public Genesis
World 1.4.3 API only.

## Runtime

- Python 3.12 is the verified runtime.
- Install the isolated dependencies with
  `python3.12 -m venv .venv-edgeworld-worker`, then
  `.venv-edgeworld-worker/bin/pip install -r engine/edgeworld_worker/requirements.txt`.
- `requirements.txt` pins `genesis-world==1.4.3`. The delivered configuration
  currently requires the Genesis Metal backend; the supporting API audit was
  performed on Apple Silicon/macOS. Other platforms and backends are unverified.
- Start one process for a world:
  `.venv-edgeworld-worker/bin/python engine/edgeworld_worker/worker.py --state-dir /path/to/world-data --world-id demo`
  Optional startup settings are `--dt` (default `0.01`), `--physical-steps`
  (default `8` per logical tick), and `--seed` (default `7`). A given state
  directory is bound to its world ID and these values; a mismatch fails startup.
- The process reads one JSON object per stdin line and writes one JSON response
  per line to stdout. Genesis diagnostics are configured at warning level.
  Keep only one process writing a world directory; cross-process writer locking
  is not implemented.

## Request mapping to the UE client

Every request includes `protocol_version: 1`, a unique `request_id`, and
`operation`. The field names below match
`EdgeWorldJsonlClient.cpp` in the sibling `stage2-ue-plugin` worktree.

```json
{"protocol_version":1,"request_id":"req-1","operation":"status","world_id":"demo"}
{"protocol_version":1,"request_id":"req-2","operation":"advance","world_id":"demo","expected_revision":0,"target_tick":1,"command_id":"advance-1"}
{"protocol_version":1,"request_id":"req-3","operation":"observe","world_id":"demo","logical_tick":1,"view_spec":{}}
```

`status` returns the current tick/revision and state/event head hashes.
`advance` applies the phase gravity selected by the current tick, executes the
configured fixed Genesis step count, checkpoints the candidate, and atomically
publishes the new manifest. `target_tick` must equal `current_tick + 1`. Revision
starts at zero and increments once for every successful advance. Reusing a
command ID with the same request returns its persisted result without another
Genesis step; using that ID with changed fields returns `command_id_conflict`.
Revision mismatch returns `revision_conflict` with the current head.

`observe` requires an exact retained tick and has no Genesis call or persistent
write. It returns `source_revision`, `body_stable_id`, a transform object with
position and velocity, plus state/event hashes. Unknown historical ticks return
`history_missing`; the current state is never substituted. This prototype
accepts and echoes `view_spec` but does not yet implement view filtering.

Success responses have shape
`{"protocol_version":1,"request_id":"...","ok":true,"result":{...}}`.
Errors have shape
`{"protocol_version":1,"request_id":"...","ok":false,"error":{"code":"...","message":"...","head":{...}}}`.
Startup failures are emitted as one JSON line with `startup_error`, then the
process exits nonzero.

The UE client currently serializes tick/revision through JSON numbers backed by
IEEE-754 doubles. The worker accepts only integral values no larger than
`2^53-1`; this is ample for the finite experiment but not an indefinite world
clock. Use a future protocol revision with decimal strings or another exact
integer encoding before approaching that bound.

## Persistence and recovery

`world.json` is the authoritative commit record. It stores schema/config,
current head, every finite history record and causal event, plus persisted
command results. Each Genesis `.gstraj` checkpoint is saved first as an
immutable SHA-256-addressed file under `checkpoints/`. Only then is a new JSON
manifest fsynced to a temporary file and atomically renamed over `world.json`.
An interrupted write may leave an unreferenced checkpoint, which is ignored.
An unreferenced blob is never treated as a committed tick.

If manifest replacement fails before `os.replace` is attempted, the worker
reloads the prior committed Genesis checkpoint and returns
`persistence_failed`. Once replacement has been attempted, an exception (for
example, directory fsync failure) makes the commit outcome uncertain: the
worker returns `commit_status_uncertain`, rejects all later requests, and the
CLI exits. Restart validates whichever manifest is visible and its checkpoint
before serving requests. The uncertain response intentionally omits a head;
the caller must query status after restart before retrying a command.

Run the focused replacement/fsync fault checks with the isolated environment:
`.venv-edgeworld-worker/bin/python engine/edgeworld_worker/test_commit_boundary.py`.

On startup, the worker validates the schema, contiguous tick sequence, state
hashes, event hash chain, configured world identity, and referenced checkpoint
hash before loading it through `gs.Scene.load_checkpoint(...,
show_viewer=False)`. It rejects unknown/corrupt state rather than silently
creating a fresh world. The Genesis adapter uses
`scene.rigid_solver.set_gravity(...)`,
`scene.step(update_visualizer=False, refresh_visualizer=False)`,
`scene.save_checkpoint(...)`, and `gs.Scene.load_checkpoint(...)`; it does not
use private `_sim` or viewer attributes.

The experiment has one stable body ID (`body-1`), one illustrative four-phase
gravity rule, no external random input after scene initialization, and a finite
history retained in the manifest. Genesis checkpoint continuation has only
been audited for a simple free rigid body on the same machine/runtime/config.
This slice has not verified UE transport wiring, cross-process replay equality,
power-loss durability on every filesystem, multiple worlds in one process,
cross-process locking, arbitrary `view_spec`, or production retention/migration.
