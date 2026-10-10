# UE 5.8.3 release plugin slice

`EdgeWorldHost/` is a minimal Unreal host project with the `EdgeWorldRuntime`
plugin enabled. It targets the locally installed UE 5.8.3 release (CL
58210709); no engine source changes are required.

## Scope

- `FEdgeWorldJsonlClient` serializes versioned JSONL `status`, `advance`, and
  `observe` requests. `advance` carries `expected_revision`, `target_tick`, and
  `command_id`; `observe` carries an explicit historical tick and view spec.
- `IEdgeWorldJsonlTransport` is an asynchronous boundary: its implementation
  must return immediately and invoke the callback once. The included
  `FEdgeWorldUnavailableTransport` deliberately answers `worker_unavailable`
  asynchronously. There is no worker process, pipe, or protocol implementation
  in this slice, so this plugin does not claim to connect to Genesis.
- `AEdgeWorldObservationActor` only projects a supplied committed stable entity
  ID and transform through UE's regular Actor/Renderer path. It has no tick and
  does not own or advance authoritative state.

The JSON field names follow `doc/phase1_4d_prototype_contract.md`. This first
slice does not validate worker response parsing, request correlation over a
live transport, startup, rendering content, cook/package, or end-to-end replay.

## Build

With the UE 5.8.3 release installed at `/Users/Shared/Epic Games/UE_5.8`:

```sh
"/Users/Shared/Epic Games/UE_5.8/Engine/Build/BatchFiles/Mac/Build.sh" \
  EdgeWorldHostEditor Mac Development \
  -Project="$(pwd)/EdgeWorldHost/EdgeWorldHost.uproject" -WaitMutex
```
