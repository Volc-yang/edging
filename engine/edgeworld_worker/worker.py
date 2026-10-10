"""Single-body edgeWorld JSONL worker backed by Genesis World 1.4.3.

The process owns the world head. Its JSON manifest is the atomic commit point;
Genesis checkpoints are immutable, content-addressed blobs referenced by it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any


PROTOCOL_VERSION = 1
SCHEMA_VERSION = "edgeworld.worker.single-body.v1"
RULESET_ID = "edgeworld.gravity-phases"
RULESET_VERSION = "1"
BODY_ID = "body-1"
PHASES = ("shaoyang", "taiyang", "shaoyin", "taiyin")
PHASE_GRAVITY_Z = {"shaoyang": -2.0, "taiyang": -9.81, "shaoyin": -5.0, "taiyin": -1.0}
GENESIS_VERSION = "1.4.3"
MAX_SAFE_JSON_INTEGER = (1 << 53) - 1


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _json_integer(value: Any, field: str) -> int:
    # Unreal's current JSON writer stores int64 fields as IEEE-754 doubles.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolError(f"invalid_{field}", f"{field} must be a non-negative safe integer")
    if isinstance(value, float) and not math.isfinite(value):
        raise ProtocolError(f"invalid_{field}", f"{field} must be a non-negative safe integer")
    if isinstance(value, int) and (value < 0 or value > MAX_SAFE_JSON_INTEGER):
        raise ProtocolError(f"invalid_{field}", f"{field} must be a non-negative safe integer")
    integer = int(value)
    if integer < 0 or integer != value or integer > MAX_SAFE_JSON_INTEGER:
        raise ProtocolError(f"invalid_{field}", f"{field} must be a non-negative safe integer")
    return integer


class GenesisAdapter:
    """Narrow adapter that uses public Genesis scene/solver APIs only."""

    _initialized = False

    def __init__(self, checkpoint: Path | None, *, dt: float, physical_steps: int, seed: int):
        try:
            import genesis as gs
        except ImportError as exc:
            raise RuntimeError("Genesis missing; install engine/edgeworld_worker/requirements.txt") from exc
        actual = str(getattr(gs, "__version__", "unknown"))
        if actual != GENESIS_VERSION:
            raise RuntimeError(f"requires genesis-world {GENESIS_VERSION}; found {actual}")
        self.gs = gs
        self.dt = dt
        self.physical_steps = physical_steps
        backend = getattr(gs, "metal", None)
        if backend is None:
            raise RuntimeError("this prototype currently requires the Genesis Metal backend")
        if not GenesisAdapter._initialized:
            gs.init(backend=backend, logging_level="warning", seed=seed)
            GenesisAdapter._initialized = True
        if checkpoint is None:
            self.scene = self._new_scene()
            self.body = self.scene.add_entity(gs.morphs.Sphere(pos=(0.0, 0.0, 1.0), radius=0.1))
            self.scene.build()
        else:
            self.scene = gs.Scene.load_checkpoint(str(checkpoint), show_viewer=False)
            entities = self.scene.entities
            if len(entities) != 1:
                raise RuntimeError(f"checkpoint must contain exactly one entity; found {len(entities)}")
            self.body = entities[0]

    def _new_scene(self):
        return self.gs.Scene(
            show_viewer=False,
            sim_options=self.gs.options.SimOptions(dt=self.dt, gravity=(0.0, 0.0, -9.81)),
        )

    def advance(self, phase: str) -> dict[str, Any]:
        gravity = (0.0, 0.0, PHASE_GRAVITY_Z[phase])
        self.scene.rigid_solver.set_gravity(gravity)
        for _ in range(self.physical_steps):
            self.scene.step(update_visualizer=False, refresh_visualizer=False)
        return self.observe_body()

    def observe_body(self) -> dict[str, Any]:
        position = [float(value) for value in self.body.get_pos().tolist()]
        velocity = [float(value) for value in self.body.get_dofs_velocity().tolist()]
        if len(position) != 3 or len(velocity) not in (3, 6):
            raise RuntimeError("Genesis body returned an unexpected position/velocity shape")
        if not all(math.isfinite(value) for value in position + velocity):
            raise RuntimeError("Genesis body returned non-finite state")
        return {"position": position, "velocity": velocity}

    def save_checkpoint(self, path: Path) -> None:
        self.scene.save_checkpoint(str(path))


class Worker:
    def __init__(self, state_dir: Path, world_id: str, *, dt: float = 0.01, physical_steps: int = 8, seed: int = 7):
        if not world_id:
            raise ValueError("world_id cannot be empty")
        if not math.isfinite(dt) or dt <= 0 or physical_steps < 1:
            raise ValueError("dt and physical_steps must be positive")
        self.state_dir = state_dir.resolve()
        self.blob_dir = self.state_dir / "checkpoints"
        self.manifest_path = self.state_dir / "world.json"
        self.world_id = world_id
        self.config = {"backend": "metal", "dt": dt, "physical_steps": physical_steps, "seed": seed,
                       "genesis_version": GENESIS_VERSION, "ruleset_id": RULESET_ID,
                       "ruleset_version": RULESET_VERSION}
        self._lock = threading.Lock()
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        if self.manifest_path.exists():
            self.manifest = self._read_manifest()
            if self.manifest["world_id"] != world_id or self.manifest["config"] != self.config:
                raise RuntimeError("existing world id/configuration does not match worker arguments")
            blob = self._checkpoint_path(self.manifest["checkpoint_sha256"])
            if not blob.is_file() or self._file_hash(blob) != self.manifest["checkpoint_sha256"]:
                raise RuntimeError("committed Genesis checkpoint is missing or corrupt")
            self.genesis = GenesisAdapter(blob, dt=dt, physical_steps=physical_steps, seed=seed)
            observed = self.genesis.observe_body()
            if _digest(observed) != self.manifest["head_state_hash"]:
                raise RuntimeError("restored Genesis state does not match committed head")
        else:
            self.genesis = GenesisAdapter(None, dt=dt, physical_steps=physical_steps, seed=seed)
            initial_state = self.genesis.observe_body()
            checkpoint_sha = self._save_blob(self.genesis)
            state_hash = _digest(initial_state)
            record = {"logical_tick": 0, "state_revision": 0, "body_stable_id": BODY_ID, "phase": None,
                      "physical_steps": 0, **initial_state, "state_hash": state_hash}
            event = {"event_id": "event-0", "logical_tick": 0, "kind": "world_initialized",
                     "body_stable_id": BODY_ID, "state_hash": state_hash,
                     "previous_event_hash": "0" * 64}
            event["event_hash"] = _digest(event)
            record["event_hash"] = event["event_hash"]
            self.manifest = {
                "schema_version": SCHEMA_VERSION, "world_id": world_id,
                "body_stable_id": BODY_ID, "config": self.config,
                "logical_tick": 0, "state_revision": 0, "head_state_hash": state_hash,
                "event_head_hash": event["event_hash"], "checkpoint_sha256": checkpoint_sha,
                "history": [record], "events": [event], "commands": {},
            }
            self._write_manifest(self.manifest)

    def _read_manifest(self) -> dict[str, Any]:
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"cannot read world manifest: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError("unknown or invalid world manifest schema")
        if data.get("world_id") != self.world_id:
            raise RuntimeError("world id mismatch")
        if data.get("body_stable_id") != BODY_ID:
            raise RuntimeError("world manifest has an unsupported stable body ID")
        if not isinstance(data.get("history"), list) or not isinstance(data.get("events"), list) or not isinstance(data.get("commands"), dict):
            raise RuntimeError("world manifest has invalid history/events/commands")
        if type(data.get("logical_tick")) is not int or data["logical_tick"] < 0 or data.get("state_revision") != data["logical_tick"]:
            raise RuntimeError("world manifest has invalid tick/revision")
        tick = data["logical_tick"]
        history, events = data["history"], data["events"]
        if len(history) != tick + 1 or len(events) != tick + 1:
            raise RuntimeError("world manifest history/event length does not match head tick")
        previous_hash = "0" * 64
        for index, (record, event) in enumerate(zip(history, events)):
            if record.get("logical_tick") != index or record.get("state_revision") != index or event.get("logical_tick") != index:
                raise RuntimeError("world manifest history is not a contiguous tick sequence")
            if record.get("body_stable_id") != BODY_ID or event.get("body_stable_id") != BODY_ID:
                raise RuntimeError(f"world manifest stable body ID mismatch at tick {index}")
            expected_state_hash = _digest({"position": record.get("position"), "velocity": record.get("velocity")})
            if record.get("state_hash") != expected_state_hash or event.get("state_hash") != expected_state_hash:
                raise RuntimeError(f"world manifest state hash mismatch at tick {index}")
            unsigned_event = {key: value for key, value in event.items() if key != "event_hash"}
            if event.get("previous_event_hash") != previous_hash or event.get("event_hash") != _digest(unsigned_event):
                raise RuntimeError(f"world manifest event chain mismatch at tick {index}")
            if record.get("event_hash") != event.get("event_hash"):
                raise RuntimeError(f"world manifest record/event mismatch at tick {index}")
            previous_hash = event["event_hash"]
        if data.get("head_state_hash") != history[-1].get("state_hash") or data.get("event_head_hash") != previous_hash:
            raise RuntimeError("world manifest head hash mismatch")
        return data

    def _checkpoint_path(self, sha: str) -> Path:
        return self.blob_dir / f"{sha}.gstraj"

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _save_blob(self, adapter: GenesisAdapter) -> str:
        with tempfile.NamedTemporaryFile(prefix="checkpoint-", suffix=".gstraj", dir=self.blob_dir, delete=False) as temp:
            temp_path = Path(temp.name)
        try:
            adapter.save_checkpoint(temp_path)
            with temp_path.open("rb") as stream:
                os.fsync(stream.fileno())
            sha = self._file_hash(temp_path)
            final = self._checkpoint_path(sha)
            if not final.exists():
                os.replace(temp_path, final)
                self._fsync_dir(self.blob_dir)
            return sha
        finally:
            temp_path.unlink(missing_ok=True)

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _write_manifest(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        fd, name = tempfile.mkstemp(prefix="world-", suffix=".json.tmp", dir=self.state_dir)
        tmp = Path(name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(tmp, self.manifest_path)
            self._fsync_dir(self.state_dir)
        finally:
            tmp.unlink(missing_ok=True)

    def _response(self, request_id: str, result: dict[str, Any] | None = None, error: dict[str, str] | None = None) -> dict[str, Any]:
        response = {"protocol_version": PROTOCOL_VERSION, "request_id": request_id}
        if error is not None:
            response["ok"] = False
            response["error"] = error
        else:
            response["ok"] = True
            response["result"] = result
        return response

    def _head(self) -> dict[str, Any]:
        return {"world_id": self.world_id, "logical_tick": self.manifest["logical_tick"],
                "state_revision": self.manifest["state_revision"], "head_state_hash": self.manifest["head_state_hash"],
                "event_head_hash": self.manifest["event_head_hash"]}

    def handle(self, request: Any) -> dict[str, Any]:
        request_id = request.get("request_id", "") if isinstance(request, dict) else ""
        if not isinstance(request_id, str):
            request_id = ""
        try:
            if not isinstance(request, dict):
                raise ProtocolError("invalid_request", "request must be a JSON object")
            try:
                protocol_version = _json_integer(request.get("protocol_version"), "protocol_version")
            except ProtocolError:
                protocol_version = -1
            if protocol_version != PROTOCOL_VERSION:
                raise ProtocolError("unsupported_protocol", "protocol_version must be 1")
            if not request_id:
                raise ProtocolError("invalid_request_id", "request_id must be a non-empty string")
            operation = request.get("operation")
            with self._lock:
                if operation == "status":
                    if request.get("world_id") != self.world_id:
                        raise ProtocolError("world_not_found", "world_id does not match this worker")
                    return self._response(request_id, {**self._head(), "schema_version": SCHEMA_VERSION,
                                       "ruleset_id": RULESET_ID, "ruleset_version": RULESET_VERSION,
                                       "genesis_version": GENESIS_VERSION})
                if operation == "observe":
                    return self._observe(request, request_id)
                if operation == "advance":
                    return self._advance(request, request_id)
                raise ProtocolError("unknown_operation", f"unsupported operation: {operation!r}")
        except ProtocolError as exc:
            return self._response(request_id, error={"code": exc.code, "message": str(exc), "head": self._head()})
        except Exception as exc:  # command boundary; preserve worker loop and report failure
            return self._response(request_id, error={"code": "worker_error", "message": str(exc), "head": self._head()})

    def _observe(self, request: dict[str, Any], request_id: str) -> dict[str, Any]:
        if request.get("world_id") != self.world_id:
            raise ProtocolError("world_not_found", "world_id does not match this worker")
        tick = _json_integer(request.get("logical_tick"), "logical_tick")
        view = request.get("view_spec", {})
        if not isinstance(view, dict):
            raise ProtocolError("invalid_view_spec", "view_spec must be a JSON object")
        try:
            json.dumps(view, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("invalid_view_spec", "view_spec must contain only finite JSON values") from exc
        record = next((item for item in self.manifest["history"] if item["logical_tick"] == tick), None)
        if record is None:
            raise ProtocolError("history_missing", f"logical tick {tick} is not retained")
        return self._response(request_id, {"world_id": self.world_id, "logical_tick": tick,
            "source_revision": record["state_revision"], "body_stable_id": BODY_ID,
            "transform": {"position": record["position"], "velocity": record["velocity"]},
            "state_hash": record["state_hash"], "event_head_hash": record["event_hash"], "view_spec": view})

    def _advance(self, request: dict[str, Any], request_id: str) -> dict[str, Any]:
        if request.get("world_id") != self.world_id:
            raise ProtocolError("world_not_found", "world_id does not match this worker")
        command_id = request.get("command_id")
        if not isinstance(command_id, str) or not command_id:
            raise ProtocolError("invalid_command_id", "command_id must be a non-empty string")
        fingerprint = _digest({key: request.get(key) for key in ("world_id", "expected_revision", "target_tick", "command_id")})
        previous = self.manifest["commands"].get(command_id)
        if previous is not None:
            if previous["request_fingerprint"] != fingerprint:
                raise ProtocolError("command_id_conflict", "command_id was already used with a different request")
            return self._response(request_id, previous["result"])
        expected_revision = _json_integer(request.get("expected_revision"), "expected_revision")
        target_tick = _json_integer(request.get("target_tick"), "target_tick")
        if expected_revision != self.manifest["state_revision"]:
            raise ProtocolError("revision_conflict", "expected_revision does not match current head")
        current_tick = self.manifest["logical_tick"]
        if target_tick != current_tick + 1:
            raise ProtocolError("tick_sequence_error", "target_tick must equal current logical_tick + 1")
        phase = PHASES[current_tick % len(PHASES)]
        try:
            body = self.genesis.advance(phase)
            state_hash = _digest(body)
            event = {"event_id": f"event-{target_tick}", "logical_tick": target_tick,
                     "command_id": command_id, "body_stable_id": BODY_ID, "phase": phase,
                     "gravity": [0.0, 0.0, PHASE_GRAVITY_Z[phase]],
                     "physical_steps": self.config["physical_steps"], "ruleset_id": RULESET_ID,
                     "ruleset_version": RULESET_VERSION, "genesis_version": GENESIS_VERSION,
                     "previous_event_hash": self.manifest["event_head_hash"], "state_hash": state_hash}
            event["event_hash"] = _digest(event)
            record = {"logical_tick": target_tick, "state_revision": expected_revision + 1,
                      "body_stable_id": BODY_ID,
                      "phase": phase, "physical_steps": self.config["physical_steps"], **body,
                      "state_hash": state_hash, "event_hash": event["event_hash"]}
            checkpoint_sha = self._save_blob(self.genesis)
            result = {**self._head(), "logical_tick": target_tick, "state_revision": expected_revision + 1,
                      "head_state_hash": state_hash, "event_head_hash": event["event_hash"],
                      "command_id": command_id, "record": record}
            next_manifest = {**self.manifest, "logical_tick": target_tick,
                "state_revision": expected_revision + 1, "head_state_hash": state_hash,
                "event_head_hash": event["event_hash"], "checkpoint_sha256": checkpoint_sha,
                "history": self.manifest["history"] + [record], "events": self.manifest["events"] + [event],
                "commands": {**self.manifest["commands"], command_id: {"request_fingerprint": fingerprint, "result": result}}}
            self._write_manifest(next_manifest)
            self.manifest = next_manifest
            return self._response(request_id, result)
        except Exception:
            self._restore_committed_scene()
            raise

    def _restore_committed_scene(self) -> None:
        blob = self._checkpoint_path(self.manifest["checkpoint_sha256"])
        self.genesis = GenesisAdapter(blob, dt=self.config["dt"], physical_steps=self.config["physical_steps"], seed=self.config["seed"])


class ProtocolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--physical-steps", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    try:
        worker = Worker(args.state_dir, args.world_id, dt=args.dt, physical_steps=args.physical_steps, seed=args.seed)
    except Exception as exc:
        print(json.dumps({"protocol_version": PROTOCOL_VERSION, "request_id": "", "ok": False,
                          "error": {"code": "startup_error", "message": str(exc)}}, allow_nan=False), flush=True)
        return 2
    for line in sys.stdin:
        try:
            request = json.loads(line, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid JSON number {value}")))
            response = worker.handle(request)
        except (json.JSONDecodeError, ValueError) as exc:
            response = {"protocol_version": PROTOCOL_VERSION, "request_id": "", "ok": False,
                        "error": {"code": "invalid_json", "message": str(exc)}}
        except Exception as exc:
            response = {"protocol_version": PROTOCOL_VERSION, "request_id": "", "ok": False,
                        "error": {"code": "worker_error", "message": str(exc)}}
        sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
