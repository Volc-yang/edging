# UE 5.8.3 release plugin slice

`EdgeWorldHost/` is a minimal Unreal host project with the `EdgeWorldRuntime`
plugin enabled. It targets the locally installed UE 5.8.3 release (CL
58210709); no engine source changes are required.

## Scope

- `FEdgeWorldJsonlClient` serializes versioned JSONL `status`, `advance`, and
  `observe` requests. `advance` carries `expected_revision`, `target_tick`, and
  `command_id`; `observe` carries an explicit historical tick and view spec.
- `IEdgeWorldJsonlTransport` is an asynchronous boundary: its implementation
  must return immediately and invoke the callback once. `FEdgeWorldProcessTransport`
  lazily starts one Python worker, serializes requests through stdin, parses and
  correlates JSONL replies from stdout, drains worker diagnostics from stderr,
  times out and stops unhealthy processes, and shuts down the child on teardown.
  `FEdgeWorldUnavailableTransport` remains available when no process is configured.
- `AEdgeWorldObservationActor` only projects a supplied committed stable entity
  ID and transform through UE's regular Actor/Renderer path. It has no tick and
  does not own or advance authoritative state.
- `FEdgeWorldProcessTransport` is configured explicitly by the host. Use one
  transport and one state directory per world; the worker does not implement
  cross-process writer locking. Use the Genesis 1.4.3 Python environment on
  macOS/Apple Silicon for this prototype; other platforms/backends are unverified.

The JSON field names follow `doc/phase1_4d_prototype_contract.md`. Worker tick
and revision values are limited to the exact integer range of JSON numbers
(`2^53-1`). `observe` only reads retained history; the UE observation actor has
no tick and applies supplied committed transforms through the normal Renderer.

Example host setup:

```cpp
FEdgeWorldWorkerLaunchConfig Config;
Config.PythonExecutable = TEXT("/path/to/.venv-edgeworld-worker/bin/python");
Config.WorkerScript = TEXT("/path/to/engine/edgeworld_worker/worker.py");
Config.StateDirectory = TEXT("/path/to/saved-worlds/demo");
Config.WorldId = TEXT("demo");
auto Transport = MakeShared<FEdgeWorldProcessTransport, ESPMode::ThreadSafe>(Config);
FEdgeWorldJsonlClient Client(Transport.ToSharedRef());
Client.Status(Config.WorldId, [](FEdgeWorldResponse&& Response) { /* handle asynchronously */ });
// Call Transport->Shutdown() when the owning world/session ends.
```

## Live integration check

The editor automation test exercises process startup, `status → advance →
observe`, duplicate-command idempotency, read-only observation, and process
restart recovery. Run it with the isolated Genesis environment:

```sh
EDGEWORLD_TEST_PYTHON="/path/to/.venv-edgeworld-worker/bin/python" \
EDGEWORLD_TEST_WORKER="$(pwd)/engine/edgeworld_worker/worker.py" \
"/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd" \
  "$(pwd)/engine_platforms/unreal/EdgeWorldHost/EdgeWorldHost.uproject" \
  -unattended -nop4 -nullrhi \
  -ExecCmds="Automation RunTests edgeWorld.WorkerProtocol; Quit"
```

This test does not claim packaged-game, cross-platform, high-contention, or
production durability coverage.

## Seed-to-tree PIE demonstration

The host's `AEdgeWorldGeneratedWorldGameMode` creates a BasicShapes ground,
directional light, fixed camera, and presentation-only tree actor at runtime;
there is no project map or external art dependency. Configure the separate,
Genesis-free tree worker before launching the editor:

```sh
export EDGEWORLD_TREE_PYTHON="/path/to/python"
export EDGEWORLD_TREE_WORKER="$(pwd)/engine/edgeworld_worker/tree_worker.py"
"/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor" \
  "$(pwd)/engine_platforms/unreal/EdgeWorldHost/EdgeWorldHost.uproject"
```

Enter Play In Editor. The host observes the worker's current exact tick, then
Space issues one explicit `advance` with a fixed environment and observes that
committed tick. Actor, game, and render ticks never advance the worker. The
state directory is under `EdgeWorldHost/Saved/EdgeWorldTree/seed-tree-demo`.
The tree proxy accepts only the frozen `experimental.seed-tree.v1` and
`stylized-tree-ue-v1` versions and rejects mismatched tick/watermark responses.
Its seed, seedling, mature, declining, and dead forms are deterministic
component-scale projections, not botanical geometry.

The `edgeWorld.TreeObservation.ExactTimeSeedSeedlingAndMatureFixtures` Editor
automation test validates pre-germination, seedling, and mature JSON fixtures,
wrong tick/watermark rejection, explicit environment serialization, disabled
actor ticking, and repeatability of the component transforms. This fixture
test works without a live worker. Real-RHI visual acceptance still requires
PIE screenshots at fixed ticks; a `-nullrhi` run is not visual evidence.

## Build

With the UE 5.8.3 release installed at `/Users/Shared/Epic Games/UE_5.8`:

```sh
"/Users/Shared/Epic Games/UE_5.8/Engine/Build/BatchFiles/Mac/Build.sh" \
  EdgeWorldHostEditor Mac Development \
  -Project="$(pwd)/EdgeWorldHost/EdgeWorldHost.uproject" -WaitMutex
```
