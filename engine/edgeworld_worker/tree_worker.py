"""Experimental Seed-to-tree JSONL worker; no Genesis dependency or calls.

This worker is intentionally separate from ``worker.py`` and its Genesis
single-body schema. One process is the sole writer for a tree world's state
directory. The accepted ``--dt`` and ``--physical-steps`` flags exist only for
compatibility with the UE process launcher; plant evolution does not use them.
All tree coefficients and the scalar-to-stage model are experimental, not
approved biological laws. UE geometry is a read-only derived projection.
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

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evolution_4d import (
    EXPERIMENTAL_SEED_TREE_RULE_VERSION,
    EnvironmentSample,
    SeedStage,
    SeedTreeRules,
    SeedTreeState,
    TimePhase,
    advance_seed_tree,
    seed_state,
)


PROTOCOL_VERSION = 1
SCHEMA_VERSION = "edgeworld.worker.seed-tree.v1"
RULESET_ID = "edgeworld.experimental.seed-tree"
PROJECTION_VERSION = "stylized-tree-ue-v1"
MAX_SAFE_JSON_INTEGER = (1 << 53) - 1
ZERO_HASH = "0" * 64
PHASES = {phase.value: phase for phase in TimePhase}
_DEFAULT_RULES = SeedTreeRules()


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _json_integer(value: Any, field: str) -> int:
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


def _state_dict(state: SeedTreeState) -> dict[str, Any]:
    return {
        "seed_id": state.seed_id,
        "tree_id": state.tree_id,
        "logical_tick": state.logical_tick,
        "stage": state.stage.value,
        "health": state.health,
        "biomass": state.biomass,
        "water_reserve": state.water_reserve,
    }


def _state_from_dict(data: Any) -> SeedTreeState:
    if not isinstance(data, dict):
        raise RuntimeError("manifest state must be an object")
    try:
        return SeedTreeState(
            seed_id=data["seed_id"], tree_id=data["tree_id"],
            logical_tick=data["logical_tick"], stage=SeedStage(data["stage"]),
            health=data["health"], biomass=data["biomass"],
            water_reserve=data["water_reserve"],
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError(f"manifest contains invalid tree state: {exc}") from exc


def _environment_dict(environment: EnvironmentSample | None) -> dict[str, Any] | None:
    if environment is None:
        return None
    return {"phase": environment.phase.value, "moisture": environment.moisture, "light": environment.light}


def _environment_from_request(value: Any) -> EnvironmentSample:
    if not isinstance(value, dict):
        raise ProtocolError("invalid_environment", "environment must be an object")
    if set(value) != {"phase", "moisture", "light"}:
        raise ProtocolError("invalid_environment", "environment must contain exactly phase, moisture, and light")
    try:
        phase_value = value["phase"]
        phase = PHASES[phase_value]
        return EnvironmentSample(phase, value["moisture"], value["light"])
    except KeyError as exc:
        raise ProtocolError("invalid_environment", f"environment is missing or has unknown field {exc.args[0]!r}") from exc
    except (TypeError, ValueError) as exc:
        raise ProtocolError("invalid_environment", str(exc)) from exc


class Worker:
    """One-world, one-process authoritative Seed/tree state and event history."""

    def __init__(self, state_dir: Path, world_id: str, *, seed: int = 7):
        if not isinstance(world_id, str) or not world_id.strip():
            raise ValueError("world_id cannot be empty")
        if type(seed) is not int or seed < 0 or seed > MAX_SAFE_JSON_INTEGER:
            raise ValueError("seed must be a non-negative safe integer")
        self.state_dir = state_dir.resolve()
        self.manifest_path = self.state_dir / "tree_world.json"
        self.world_id = world_id
        self.seed = seed
        self.seed_id = f"seed-{seed}"
        self.config = {"seed": seed, "ruleset_id": RULESET_ID,
                       "ruleset_version": EXPERIMENTAL_SEED_TREE_RULE_VERSION}
        self._lock = threading.Lock()
        self._fatal_error: str | None = None
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.manifest_path.exists():
            self.manifest = self._read_manifest()
            if self.manifest["world_id"] != world_id or self.manifest["config"] != self.config:
                raise RuntimeError("existing tree world id/configuration does not match worker arguments")
        else:
            initial = seed_state(self.seed_id)
            state_data = _state_dict(initial)
            state_hash = _digest(state_data)
            event = self._make_event(
                logical_tick=0, state_hash=state_hash, previous_event_hash=ZERO_HASH,
                previous_state_hash=None, state=initial,
                command_id=None, environment=None, reasons=("world_initialized",),
            )
            record = {"logical_tick": 0, "state_revision": 0, "command_id": None, "state": state_data,
                      "environment": None, "reasons": ["world_initialized"],
                      "state_hash": state_hash, "event_hash": event["event_hash"]}
            self.manifest = {
                "schema_version": SCHEMA_VERSION, "world_id": world_id,
                "config": self.config, "logical_tick": 0, "state_revision": 0,
                "head_state_hash": state_hash, "event_head_hash": event["event_hash"],
                "history": [record], "events": [event], "commands": {},
            }
            self._write_manifest(self.manifest)

    def _make_event(
        self, *, logical_tick: int, state_hash: str, previous_event_hash: str,
        previous_state_hash: str | None, state: SeedTreeState,
        command_id: str | None, environment: EnvironmentSample | None,
        reasons: tuple[str, ...],
    ) -> dict[str, Any]:
        event = {
            "event_id": f"tree-event-{logical_tick}",
            "logical_tick": logical_tick,
            "state_revision": logical_tick,
            "seed_id": state.seed_id,
            "tree_id": state.tree_id,
            "command_id": command_id,
            "ruleset_id": RULESET_ID,
            "ruleset_version": EXPERIMENTAL_SEED_TREE_RULE_VERSION,
            "environment": _environment_dict(environment),
            "environment_hash": _digest(_environment_dict(environment)) if environment is not None else None,
            "reasons": list(reasons),
            "previous_event_hash": previous_event_hash,
            "previous_state_hash": previous_state_hash,
            "state_hash": state_hash,
        }
        event["event_hash"] = _digest(event)
        return event

    def _read_manifest(self) -> dict[str, Any]:
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"),
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"invalid number {value}")))
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            raise RuntimeError(f"cannot read tree world manifest: {exc}") from exc
        if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
            raise RuntimeError("unknown or invalid tree world manifest schema")
        if data.get("world_id") != self.world_id:
            raise RuntimeError("world id mismatch")
        if not isinstance(data.get("history"), list) or not isinstance(data.get("events"), list) or not isinstance(data.get("commands"), dict):
            raise RuntimeError("tree world manifest has invalid history/events/commands")
        tick = data.get("logical_tick")
        revision = data.get("state_revision")
        if type(tick) is not int or tick < 0 or revision != tick:
            raise RuntimeError("tree world manifest has invalid tick/revision")
        history, events = data["history"], data["events"]
        if len(history) != tick + 1 or len(events) != tick + 1:
            raise RuntimeError("tree world history/event length does not match head tick")
        previous_hash = ZERO_HASH
        previous_state_hash: str | None = None
        previous_state: SeedTreeState | None = None
        expected_commands: dict[str, tuple[int, str]] = {}
        for index, (record, event) in enumerate(zip(history, events)):
            if not isinstance(record, dict) or not isinstance(event, dict):
                raise RuntimeError("tree world history and events must contain objects")
            state = _state_from_dict(record.get("state"))
            state_hash = _digest(_state_dict(state))
            if record.get("logical_tick") != index or record.get("state_revision") != index or state.logical_tick != index:
                raise RuntimeError("tree world history is not a contiguous tick sequence")
            if state.seed_id != self.seed_id:
                raise RuntimeError(f"tree world Seed identity mismatch at tick {index}")
            if record.get("state_hash") != state_hash or event.get("state_hash") != state_hash:
                raise RuntimeError(f"tree world state hash mismatch at tick {index}")

            if index == 0:
                if state != seed_state(self.seed_id):
                    raise RuntimeError("tree world tick-zero state is not the configured un-germinated Seed")
                if record.get("environment") is not None or record.get("command_id") is not None:
                    raise RuntimeError("tree world tick-zero record must not have an environment or command")
                if record.get("reasons") != ["world_initialized"]:
                    raise RuntimeError("tree world tick-zero reasons are invalid")
            else:
                try:
                    environment = _environment_from_request(record.get("environment"))
                except ProtocolError as exc:
                    raise RuntimeError(f"tree world history has invalid environment at tick {index}: {exc}") from exc
                if _environment_dict(environment) != record.get("environment"):
                    raise RuntimeError(f"tree world environment is not canonical at tick {index}")
                command_id = record.get("command_id")
                if not isinstance(command_id, str) or not command_id:
                    raise RuntimeError(f"tree world history has invalid command ID at tick {index}")
                if command_id in expected_commands:
                    raise RuntimeError(f"tree world command ID is reused at tick {index}")
                try:
                    replayed = advance_seed_tree(previous_state, environment, index, _DEFAULT_RULES)
                except Exception as exc:
                    raise RuntimeError(f"cannot replay tree state at tick {index}: {exc}") from exc
                if _state_dict(replayed.state) != _state_dict(state):
                    raise RuntimeError(f"tree world state does not match deterministic replay at tick {index}")
                if record.get("reasons") != list(replayed.reasons):
                    raise RuntimeError(f"tree world reasons do not match deterministic replay at tick {index}")
                expected_fingerprint = _digest({
                    "world_id": self.world_id,
                    "expected_revision": index - 1,
                    "target_tick": index,
                    "command_id": command_id,
                    "environment": _environment_dict(environment),
                })
                expected_commands[command_id] = (index, expected_fingerprint)

            unsigned_event = {key: value for key, value in event.items() if key != "event_hash"}
            if event.get("logical_tick") != index or event.get("previous_event_hash") != previous_hash:
                raise RuntimeError(f"tree world event sequence mismatch at tick {index}")
            if event.get("state_revision") != index or event.get("event_id") != f"tree-event-{index}":
                raise RuntimeError(f"tree world event identity mismatch at tick {index}")
            if event.get("seed_id") != state.seed_id or event.get("tree_id") != state.tree_id:
                raise RuntimeError(f"tree world event Seed/tree identity mismatch at tick {index}")
            if event.get("previous_state_hash") != previous_state_hash:
                raise RuntimeError(f"tree world previous-state hash mismatch at tick {index}")
            if event.get("command_id") != record.get("command_id"):
                raise RuntimeError(f"tree world event command does not match history at tick {index}")
            if event.get("ruleset_id") != RULESET_ID or event.get("ruleset_version") != EXPERIMENTAL_SEED_TREE_RULE_VERSION:
                raise RuntimeError(f"tree world event ruleset mismatch at tick {index}")
            if event.get("environment") != record.get("environment") or event.get("reasons") != record.get("reasons"):
                raise RuntimeError(f"tree world event inputs/reasons do not match history at tick {index}")
            expected_environment_hash = _digest(record["environment"]) if record["environment"] is not None else None
            if event.get("environment_hash") != expected_environment_hash:
                raise RuntimeError(f"tree world event environment hash mismatch at tick {index}")
            if record.get("event_hash") != event.get("event_hash"):
                raise RuntimeError(f"tree world history/event link mismatch at tick {index}")
            if event.get("event_hash") != _digest(unsigned_event) or record.get("event_hash") != event.get("event_hash"):
                raise RuntimeError(f"tree world event hash mismatch at tick {index}")
            previous_hash = event["event_hash"]
            previous_state_hash = state_hash
            previous_state = state
        if data.get("head_state_hash") != history[-1].get("state_hash") or data.get("event_head_hash") != previous_hash:
            raise RuntimeError("tree world head hash mismatch")
        commands = data["commands"]
        if set(commands) != set(expected_commands):
            raise RuntimeError("tree world command index does not match committed history")
        for command_id, (command_tick, request_fingerprint) in expected_commands.items():
            entry = commands.get(command_id)
            if not isinstance(entry, dict) or entry.get("request_fingerprint") != request_fingerprint:
                raise RuntimeError(f"tree world command fingerprint mismatch for {command_id!r}")
            record = history[command_tick]
            event = events[command_tick]
            expected_result = {
                "world_id": self.world_id,
                "logical_tick": command_tick,
                "state_revision": command_tick,
                "head_state_hash": record["state_hash"],
                "event_head_hash": event["event_hash"],
                "command_id": command_id,
                "record": record,
            }
            if entry.get("result") != expected_result:
                raise RuntimeError(f"tree world command result mismatch for {command_id!r}")
        return data

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _write_manifest(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
        fd, name = tempfile.mkstemp(prefix="tree-world-", suffix=".json.tmp", dir=self.state_dir)
        tmp = Path(name)
        replacement_started = False
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            replacement_started = True
            os.replace(tmp, self.manifest_path)
            self._fsync_dir(self.state_dir)
        except Exception as exc:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise ManifestWriteFailure(replacement_started, exc) from exc

    def _response(self, request_id: str, result: dict[str, Any] | None = None,
                  error: dict[str, Any] | None = None) -> dict[str, Any]:
        response: dict[str, Any] = {"protocol_version": PROTOCOL_VERSION, "request_id": request_id}
        if error is not None:
            response["ok"] = False
            response["error"] = error
        else:
            response["ok"] = True
            response["result"] = result
        return response

    def _head(self) -> dict[str, Any]:
        return {"world_id": self.world_id, "logical_tick": self.manifest["logical_tick"],
                "state_revision": self.manifest["state_revision"],
                "head_state_hash": self.manifest["head_state_hash"],
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
            with self._lock:
                if self._fatal_error:
                    return self._response(request_id, error={
                        "code": "worker_stopped",
                        "message": "worker stopped after an uncertain commit; restart to recover from disk",
                    })
                operation = request.get("operation")
                if operation == "status":
                    self._check_world(request)
                    return self._response(request_id, {**self._head(), "schema_version": SCHEMA_VERSION,
                        "ruleset_id": RULESET_ID, "ruleset_version": EXPERIMENTAL_SEED_TREE_RULE_VERSION})
                if operation == "observe":
                    return self._observe(request, request_id)
                if operation == "advance":
                    return self._advance(request, request_id)
                raise ProtocolError("unknown_operation", f"unsupported operation: {operation!r}")
        except ProtocolError as exc:
            return self._response(request_id, error={"code": exc.code, "message": str(exc), "head": self._head()})
        except Exception as exc:
            return self._response(request_id, error={"code": "worker_error", "message": str(exc), "head": self._head()})

    def _check_world(self, request: dict[str, Any]) -> None:
        if request.get("world_id") != self.world_id:
            raise ProtocolError("world_not_found", "world_id does not match this worker")

    def _observe(self, request: dict[str, Any], request_id: str) -> dict[str, Any]:
        self._check_world(request)
        tick = _json_integer(request.get("logical_tick"), "logical_tick")
        view = request.get("view_spec")
        if not isinstance(view, dict):
            raise ProtocolError("invalid_view_spec", "view_spec must be an object")
        required = ("watermark", "region", "observer", "resolution", "error_budget", "rules")
        if any(key not in view for key in required):
            raise ProtocolError("invalid_view_spec", f"view_spec must bind {', '.join(required)}")
        watermark = _json_integer(view["watermark"], "watermark")
        record = next((entry for entry in self.manifest["history"] if entry["logical_tick"] == tick), None)
        if record is None:
            raise ProtocolError("history_missing", f"logical tick {tick} is not retained")
        if watermark != record["state_revision"]:
            raise ProtocolError("watermark_mismatch", "watermark must exactly match the committed revision at logical_tick")
        for name in ("region", "observer", "resolution"):
            if not isinstance(view[name], str) or not view[name]:
                raise ProtocolError("invalid_view_spec", f"{name} must be a non-empty string")
        if view["resolution"] != "single-tree-proxy-v1":
            raise ProtocolError("unsupported_resolution", "resolution must be single-tree-proxy-v1")
        if not isinstance(view["error_budget"], dict) or view["error_budget"].get("semantic_state") != "exact":
            raise ProtocolError("invalid_view_spec", "error_budget.semantic_state must be exact")
        rules = view["rules"]
        if not isinstance(rules, dict) or rules.get("evolution") != EXPERIMENTAL_SEED_TREE_RULE_VERSION:
            raise ProtocolError("unsupported_rules", "rules.evolution must match this worker ruleset")
        if rules.get("projection") != PROJECTION_VERSION:
            raise ProtocolError("unsupported_projection", f"rules.projection must be {PROJECTION_VERSION}")
        try:
            json.dumps(view, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ProtocolError("invalid_view_spec", "view_spec must contain finite JSON values") from exc

        state = _state_from_dict(record["state"])
        environment = record["environment"]
        sample = {
            "seed_id": state.seed_id,
            "tree_id": state.tree_id,
            "stage": state.stage.value,
            "health": state.health,
            "biomass": state.biomass,
            "water_reserve": state.water_reserve,
            "phase": environment["phase"] if environment is not None else None,
            "ruleset_version": EXPERIMENTAL_SEED_TREE_RULE_VERSION,
        }
        result = {
            "world_id": self.world_id,
            "logical_tick": tick,
            "source_revision": record["state_revision"],
            "watermark": watermark,
            "sample": sample,
            "projection_version": PROJECTION_VERSION,
            "state_hash": record["state_hash"],
            "event_hash": record["event_hash"],
            "event_head_hash": record["event_hash"],
            "view_spec": view,
        }
        result["sample_hash"] = _digest(result)
        return self._response(request_id, result)

    def _advance(self, request: dict[str, Any], request_id: str) -> dict[str, Any]:
        self._check_world(request)
        command_id = request.get("command_id")
        if not isinstance(command_id, str) or not command_id:
            raise ProtocolError("invalid_command_id", "command_id must be a non-empty string")
        environment = _environment_from_request(request.get("environment"))
        expected_revision = _json_integer(request.get("expected_revision"), "expected_revision")
        target_tick = _json_integer(request.get("target_tick"), "target_tick")
        fingerprint = _digest({"world_id": self.world_id, "expected_revision": expected_revision,
                               "target_tick": target_tick, "command_id": command_id,
                               "environment": _environment_dict(environment)})
        previous = self.manifest["commands"].get(command_id)
        if previous is not None:
            if previous["request_fingerprint"] != fingerprint:
                raise ProtocolError("command_id_conflict", "command_id was already used with a different request")
            return self._response(request_id, previous["result"])
        if expected_revision != self.manifest["state_revision"]:
            raise ProtocolError("revision_conflict", "expected_revision does not match current head")
        current_tick = self.manifest["logical_tick"]
        if target_tick != current_tick + 1:
            raise ProtocolError("tick_sequence_error", "target_tick must equal current logical_tick + 1")

        old_state = _state_from_dict(self.manifest["history"][-1]["state"])
        transitioned = advance_seed_tree(old_state, environment, target_tick, _DEFAULT_RULES)
        state_data = _state_dict(transitioned.state)
        state_hash = _digest(state_data)
        event = self._make_event(
            logical_tick=target_tick, state_hash=state_hash,
            previous_event_hash=self.manifest["event_head_hash"],
            previous_state_hash=self.manifest["head_state_hash"], state=transitioned.state,
            command_id=command_id, environment=environment, reasons=transitioned.reasons,
        )
        revision = expected_revision + 1
        record = {"logical_tick": target_tick, "state_revision": revision,
                  "command_id": command_id,
                  "state": state_data, "environment": _environment_dict(environment),
                  "reasons": list(transitioned.reasons), "state_hash": state_hash,
                  "event_hash": event["event_hash"]}
        result = {
            "world_id": self.world_id, "logical_tick": target_tick,
            "state_revision": revision, "head_state_hash": state_hash,
            "event_head_hash": event["event_hash"], "command_id": command_id,
            "record": record,
        }
        next_manifest = {**self.manifest, "logical_tick": target_tick,
            "state_revision": revision, "head_state_hash": state_hash,
            "event_head_hash": event["event_hash"],
            "history": self.manifest["history"] + [record],
            "events": self.manifest["events"] + [event],
            "commands": {**self.manifest["commands"], command_id: {
                "request_fingerprint": fingerprint, "result": result,
            }}}
        try:
            self._write_manifest(next_manifest)
        except ManifestWriteFailure as exc:
            if exc.replacement_started:
                self._fatal_error = str(exc)
                return self._response(request_id, error={
                    "code": "commit_status_uncertain",
                    "message": "manifest replacement was attempted but durability could not be confirmed; restart the worker",
                })
            raise ProtocolError("persistence_failed", "manifest failed before replacement; tick was not committed") from exc
        self.manifest = next_manifest
        return self._response(request_id, result)


class ProtocolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ManifestWriteFailure(Exception):
    def __init__(self, replacement_started: bool, cause: Exception):
        super().__init__(str(cause))
        self.replacement_started = replacement_started


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--world-id", required=True)
    # These flags are deliberately accepted for compatibility with the shared
    # UE launcher. They have no effect on discrete tree ticks or saved config.
    parser.add_argument("--dt", type=float, default=0.01, help="accepted for launcher compatibility; ignored by tree worker")
    parser.add_argument("--physical-steps", type=int, default=8, help="accepted for launcher compatibility; ignored by tree worker")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    try:
        worker = Worker(args.state_dir, args.world_id, seed=args.seed)
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
        if worker._fatal_error is not None:
            return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
