"""Single-writer abstract causal probe backed by a Genesis 1.4.3 checkpoint.

This is an engineering fixture, not a botanical model or a world law. The
manifest is the only commit point; checkpoint blobs are immutable inputs.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import threading
from typing import Any

from engine.edgeworld_worker.worker import GenesisAdapter

PROTOCOL_VERSION = 1
SCHEMA_VERSION = "abstract-seed-genesis.v1"
INPUT_VERSION = "abstract-causal-input.v1"
RULE_VERSION = "abstract-causal-probe.v1"
PROJECTION_VERSION = "causal-graph-ue.v1"
MAX_SAFE = (1 << 53) - 1
PHASES = ("shaoyang", "taiyang")
ZERO_HASH = "0" * 64


def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class ProtocolError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class ManifestWriteFailure(Exception):
    def __init__(self, replacement_started: bool, cause: Exception):
        super().__init__(str(cause))
        self.replacement_started = replacement_started


def safe_int(value: Any, field: str) -> int:
    if type(value) is int:
        integer = value
    elif type(value) is float and math.isfinite(value) and value.is_integer():
        integer = int(value)
    else:
        raise ProtocolError("invalid_request", f"{field} must be a nonnegative safe integer")
    if integer < 0 or integer > MAX_SAFE:
        raise ProtocolError("invalid_request", f"{field} must be a nonnegative safe integer")
    return integer


def physics_vector(value: Any) -> dict[str, list[float]]:
    if not isinstance(value, dict):
        raise ProtocolError("invalid_physics_result", "Genesis result must be an object")
    position, velocity = value.get("position"), value.get("velocity")
    if not isinstance(position, list) or len(position) != 3 or not isinstance(velocity, list) or len(velocity) not in (3, 6):
        raise ProtocolError("invalid_physics_result", "Genesis returned unexpected vector shape")
    if any(type(v) not in (int, float) or not math.isfinite(v) for v in position + velocity):
        raise ProtocolError("invalid_physics_result", "Genesis returned non-finite vector")
    return {"position": [float(v) for v in position], "velocity": [float(v) for v in velocity]}


def influence_mm(z_new: float, z_previous: float) -> int:
    if not (math.isfinite(z_new) and math.isfinite(z_previous)):
        raise ProtocolError("invalid_physics_result", "position must be finite")
    with localcontext() as context:
        context.prec = 2000
        context.rounding = ROUND_HALF_EVEN
        millimeters = (Decimal.from_float(z_new) - Decimal.from_float(z_previous)) * 1000
        result = int(millimeters.to_integral_value(rounding=ROUND_HALF_EVEN))
    if abs(result) > min(1000, MAX_SAFE):
        raise ProtocolError("invalid_influence_range", "derived probe displacement exceeds 1000 mm")
    return result


def fsync_dir(path: Path) -> None:
    fd = os.open(path, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


class Worker:
    def __init__(self, state_dir: Path, world_id: str, *, adapter_cls=GenesisAdapter,
                 dt: float = 0.01, physical_steps: int = 8, seed: int = 7):
        if not re.fullmatch(r"[A-Za-z0-9._-]{1,64}", world_id):
            raise ValueError("world_id must be 1–64 ASCII letters, digits, dot, underscore or hyphen")
        if (dt, physical_steps, seed) != (0.01, 8, 7):
            raise ValueError("this fixture requires dt=0.01, physical_steps=8, seed=7")
        self.state_dir = state_dir.resolve()
        self.blob_dir = self.state_dir / "checkpoints"
        self.path = self.state_dir / "abstract_world.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        self.world_id = world_id
        self.seed_id = f"{world_id}:seed:0"
        self.probe_id = f"{world_id}:physical:0"
        self.adapter_cls = adapter_cls
        self.adapter_args = {"dt": dt, "physical_steps": physical_steps, "seed": seed}
        self.config_hash = digest({"genesis_version": "1.4.3", "backend": "metal", "dt": dt,
                                   "physical_steps": physical_steps, "seed": seed,
                                   "initial_position": [0, 0, 1], "radius": 0.1})
        self._lock = threading.Lock()
        self._fatal_error: str | None = None
        if self.path.exists():
            self.manifest = self._read_manifest()
            blob = self._blob(self.manifest["checkpoint_sha256"])
            if not blob.is_file() or file_hash(blob) != self.manifest["checkpoint_sha256"]:
                raise RuntimeError("committed Genesis checkpoint is missing or corrupt")
            self.genesis = adapter_cls(blob, **self.adapter_args)
            actual = physics_vector(self.genesis.observe_body())
            latest = self.manifest["history"][-1]["physics_sample"]
            if actual != {"position": latest["position"], "velocity": latest["velocity"]}:
                raise RuntimeError("restored Genesis body does not match committed history")
        else:
            self.genesis = adapter_cls(None, **self.adapter_args)
            vector = physics_vector(self.genesis.observe_body())
            checkpoint = self._save_blob(self.genesis)
            seed_record = {"seed_id": self.seed_id, "seed_payload_schema": "abstract-seed.v1", "seed_payload": {}}
            node = {"node_id": f"{world_id}:node:0", "tick": 0, "influence_mm": None, "physics_candidate_hash": None}
            structure = {"root_id": node["node_id"], "nodes": [node], "edges": []}
            structure_hash = digest(structure)
            sample = self._sample(vector, None)
            state_hash = self._state_hash(0, seed_record, structure_hash, sample["physics_candidate_hash"])
            record = {"logical_tick": 0, "state_revision": 0, "seed_initial_record": seed_record,
                      "development_structure": {**structure, "structure_hash": structure_hash},
                      "physics_sample": sample, "state_hash": state_hash, "event_hash": ZERO_HASH,
                      "checkpoint_sha256": checkpoint}
            self.manifest = {"schema_version": SCHEMA_VERSION, "world_id": world_id,
                             "genesis_config_hash": self.config_hash, "logical_tick": 0,
                             "state_revision": 0, "head_state_hash": state_hash,
                             "event_head_hash": ZERO_HASH, "checkpoint_sha256": checkpoint,
                             "history": [record], "events": [], "commands": {}}
            self._write_manifest(self.manifest)

    def _blob(self, sha: str) -> Path:
        return self.blob_dir / f"{sha}.gstraj"

    def _save_blob(self, adapter: GenesisAdapter) -> str:
        fd, name = tempfile.mkstemp(prefix="checkpoint-", suffix=".gstraj", dir=self.blob_dir)
        os.close(fd)
        path = Path(name)
        try:
            adapter.save_checkpoint(path)
            with path.open("rb") as stream:
                os.fsync(stream.fileno())
            sha = file_hash(path)
            target = self._blob(sha)
            if not target.exists():
                os.replace(path, target)
                fsync_dir(self.blob_dir)
            return sha
        finally:
            path.unlink(missing_ok=True)

    def _write_manifest(self, value: dict[str, Any]) -> None:
        try:
            encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"
            fd, name = tempfile.mkstemp(prefix="abstract-", suffix=".tmp", dir=self.state_dir)
        except Exception as exc:
            raise ManifestWriteFailure(False, exc) from exc
        path = Path(name)
        replacement_started = False
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            replacement_started = True
            os.replace(path, self.path)
            fsync_dir(self.state_dir)
        except Exception as exc:
            raise ManifestWriteFailure(replacement_started, exc) from exc
        finally:
            path.unlink(missing_ok=True)

    def _sample(self, vector: dict[str, list[float]], phase: str | None) -> dict[str, Any]:
        source = {"physical_probe_id": self.probe_id, **vector, "genesis_config_hash": self.config_hash, "phase": phase}
        return {**source, "physics_candidate_hash": digest(source)}

    def _state_hash(self, tick: int, seed_record: dict[str, Any], structure_hash: str, physics_hash: str) -> str:
        return digest({"world_id": self.world_id, "logical_tick": tick, "state_revision": tick,
                       "seed_initial_record": seed_record, "structure_hash": structure_hash,
                       "physics_candidate_hash": physics_hash, "genesis_config_hash": self.config_hash})

    def _result_for_record(self, record: dict[str, Any], command_id: str) -> dict[str, Any]:
        tick = record["logical_tick"]
        node = record["development_structure"]["nodes"][-1]
        edge = record["development_structure"]["edges"][-1]
        return {"world_id": self.world_id, "schema_version": SCHEMA_VERSION,
                "logical_tick": tick, "state_revision": tick, "seed_id": self.seed_id,
                "physical_probe_id": self.probe_id, "head_state_hash": record["state_hash"],
                "event_head_hash": record["event_hash"],
                "checkpoint_sha256": record["checkpoint_sha256"],
                "genesis_config_hash": self.config_hash, "command_id": command_id,
                "record": {"logical_tick": tick, "state_revision": tick,
                           "node_id": node["node_id"], "edge_id": edge["edge_id"],
                           "influence_mm": node["influence_mm"],
                           "physics_candidate_hash": node["physics_candidate_hash"],
                           "checkpoint_sha256": record["checkpoint_sha256"],
                           "state_hash": record["state_hash"], "event_hash": record["event_hash"]}}

    def _read_manifest(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise RuntimeError(f"cannot read abstract world manifest: {exc}") from exc
        if data.get("schema_version") != SCHEMA_VERSION or data.get("world_id") != self.world_id or data.get("genesis_config_hash") != self.config_hash:
            raise RuntimeError("world/schema/Genesis config mismatch")
        tick = data.get("logical_tick")
        if type(tick) is not int or tick < 0 or tick > MAX_SAFE or data.get("state_revision") != tick:
            raise RuntimeError("invalid head tick/revision")
        history, events, commands = data.get("history"), data.get("events"), data.get("commands")
        if not isinstance(history, list) or len(history) != tick + 1 or not isinstance(events, list) or len(events) != tick or not isinstance(commands, dict):
            raise RuntimeError("invalid history/events/commands")
        previous_event = ZERO_HASH
        previous_checkpoint = None
        previous_nodes = None
        previous_edges = None
        expected_commands: dict[str, tuple[str, dict[str, Any]]] = {}
        for index, record in enumerate(history):
            if record.get("logical_tick") != index or record.get("state_revision") != index:
                raise RuntimeError("noncontiguous history")
            seed_record = record.get("seed_initial_record")
            if seed_record != {"seed_id": self.seed_id, "seed_payload_schema": "abstract-seed.v1", "seed_payload": {}}:
                raise RuntimeError("seed initial record mismatch")
            structure = record.get("development_structure")
            if not isinstance(structure, dict) or structure.get("root_id") != f"{self.world_id}:node:0":
                raise RuntimeError("invalid development structure")
            body = {key: structure.get(key) for key in ("root_id", "nodes", "edges")}
            if structure.get("structure_hash") != digest(body):
                raise RuntimeError("structure hash mismatch")
            nodes, edges = body["nodes"], body["edges"]
            if not isinstance(nodes, list) or not isinstance(edges, list) or len(nodes) != index + 1 or len(edges) != index:
                raise RuntimeError("invalid causal graph size")
            if nodes[0] != {"node_id": f"{self.world_id}:node:0", "tick": 0, "influence_mm": None, "physics_candidate_hash": None}:
                raise RuntimeError("invalid root node")
            if index and (nodes[:-1] != previous_nodes or edges[:-1] != previous_edges):
                raise RuntimeError("development history prefix mismatch")
            sample = record.get("physics_sample")
            if not isinstance(sample, dict):
                raise RuntimeError("missing physics sample")
            vector = physics_vector(sample)
            if sample.get("physical_probe_id") != self.probe_id or sample.get("genesis_config_hash") != self.config_hash:
                raise RuntimeError("physics identity mismatch")
            if sample.get("physics_candidate_hash") != digest({"physical_probe_id": self.probe_id, **vector,
                                                                   "genesis_config_hash": self.config_hash, "phase": sample.get("phase")}):
                raise RuntimeError("physics sample hash mismatch")
            if index == 0:
                if sample.get("phase") is not None or record.get("event_hash") != ZERO_HASH:
                    raise RuntimeError("invalid genesis record")
            else:
                event = events[index - 1]
                node = nodes[-1]
                edge = edges[-1]
                if node.get("node_id") != f"{self.world_id}:node:{index}" or node.get("tick") != index or node.get("physics_candidate_hash") != sample["physics_candidate_hash"]:
                    raise RuntimeError("invalid development node")
                if edge.get("edge_id") != f"{self.world_id}:edge:{index}" or edge.get("from_node_id") != f"{self.world_id}:node:{index-1}" or edge.get("to_node_id") != node["node_id"] or edge.get("physics_candidate_hash") != sample["physics_candidate_hash"]:
                    raise RuntimeError("invalid causal edge")
                if sample.get("phase") not in PHASES:
                    raise RuntimeError("invalid committed phase")
                if previous_checkpoint is None:
                    raise RuntimeError("missing previous checkpoint")
                if node.get("influence_mm") != influence_mm(vector["position"][2], history[index - 1]["physics_sample"]["position"][2]):
                    raise RuntimeError("development influence mismatch")
                expected_event = {"previous_event_hash": previous_event, "logical_tick": index,
                                  "command_id": edge.get("command_id"), "physics_candidate_hash": sample["physics_candidate_hash"],
                                  "node_id": node["node_id"], "edge_id": edge["edge_id"],
                                  "influence_mm": node["influence_mm"], "rule_version": RULE_VERSION}
                if event != {**expected_event, "event_hash": digest(expected_event)} or record.get("event_hash") != event["event_hash"]:
                    raise RuntimeError("causal event chain mismatch")
                command_id = event.get("command_id")
                if not isinstance(command_id, str) or not command_id or command_id in expected_commands:
                    raise RuntimeError("duplicate or invalid committed command ID")
                fingerprint = digest({"world_id": self.world_id, "command_id": command_id,
                                      "expected_revision": index - 1, "target_tick": index,
                                      "external_inputs": {"schema_version": INPUT_VERSION,
                                                          "phase": sample["phase"]}})
                expected_commands[command_id] = (fingerprint, self._result_for_record(record, command_id))
                previous_event = event["event_hash"]
            if record.get("state_hash") != self._state_hash(index, seed_record, structure["structure_hash"], sample["physics_candidate_hash"]):
                raise RuntimeError("state hash mismatch")
            checkpoint = record.get("checkpoint_sha256")
            if not isinstance(checkpoint, str) or not self._blob(checkpoint).is_file() or file_hash(self._blob(checkpoint)) != checkpoint:
                raise RuntimeError("checkpoint missing or corrupt")
            previous_checkpoint = checkpoint
            previous_nodes, previous_edges = nodes, edges
        if (data.get("head_state_hash") != history[-1]["state_hash"] or data.get("event_head_hash") != previous_event
                or data.get("checkpoint_sha256") != history[-1]["checkpoint_sha256"]):
            raise RuntimeError("manifest head mismatch")
        if set(commands) != set(expected_commands):
            raise RuntimeError("command index does not match committed events")
        for command_id, item in commands.items():
            fingerprint, result = expected_commands[command_id]
            if item != {"request_fingerprint": fingerprint, "result": result}:
                raise RuntimeError("committed command result or fingerprint mismatch")
        return data

    def _head(self) -> dict[str, Any]:
        return {"world_id": self.world_id, "schema_version": SCHEMA_VERSION,
                "logical_tick": self.manifest["logical_tick"], "state_revision": self.manifest["state_revision"],
                "seed_id": self.seed_id, "physical_probe_id": self.probe_id,
                "head_state_hash": self.manifest["head_state_hash"], "event_head_hash": self.manifest["event_head_hash"],
                "checkpoint_sha256": self.manifest["checkpoint_sha256"], "genesis_config_hash": self.config_hash}

    def _response(self, request_id: str, *, result: dict[str, Any] | None = None,
                  code: str | None = None, message: str = "") -> dict[str, Any]:
        base = {"protocol_version": PROTOCOL_VERSION, "request_id": request_id, "ok": code is None}
        if code is None:
            base["result"] = result
        else:
            base["error"] = {"code": code, "message": message}
        return base

    def handle(self, request: Any) -> dict[str, Any]:
        request_id = request.get("request_id", "") if isinstance(request, dict) else ""
        if not isinstance(request_id, str):
            request_id = ""
        try:
            if not isinstance(request, dict) or request.get("protocol_version") != PROTOCOL_VERSION or type(request.get("protocol_version")) is not int:
                raise ProtocolError("unsupported_protocol", "protocol_version must be 1")
            if not request_id:
                raise ProtocolError("invalid_request", "request_id must be nonempty")
            if request.get("world_id") != self.world_id:
                raise ProtocolError("world_not_found", "world_id does not match worker")
            with self._lock:
                if self._fatal_error:
                    raise ProtocolError("worker_stopped", "worker must restart after uncertain commit")
                operation = request.get("operation")
                if operation == "status":
                    return self._response(request_id, result=self._head())
                if operation == "observe":
                    return self._response(request_id, result=self._observe(request))
                if operation == "advance":
                    return self._response(request_id, result=self._advance(request))
                raise ProtocolError("invalid_request", "unknown operation")
        except ProtocolError as exc:
            return self._response(request_id, code=exc.code, message=str(exc))
        except Exception as exc:
            return self._response(request_id, code="worker_stopped", message=f"unexpected worker failure: {exc}")

    def _observe(self, request: dict[str, Any]) -> dict[str, Any]:
        tick = safe_int(request.get("logical_tick"), "logical_tick")
        view = request.get("view_spec")
        expected_view = {"watermark": tick, "region": "causal-fragment-v1", "observer": "ue-causal-camera-v1",
                         "resolution": "causal-graph-proxy-v1",
                         "error_budget": {"semantic_state": "exact", "visual_geometry": "unmeasured-proxy"},
                         "rules": {"evolution": RULE_VERSION, "projection": PROJECTION_VERSION}}
        if not isinstance(view, dict):
            raise ProtocolError("invalid_request", "view_spec must be an object")
        rules = view.get("rules")
        if not isinstance(rules, dict):
            raise ProtocolError("invalid_request", "view_spec.rules must be an object")
        if view.get("watermark") != tick:
            raise ProtocolError("watermark_mismatch", "watermark must equal requested revision")
        if rules.get("evolution") != RULE_VERSION:
            raise ProtocolError("unsupported_rules", "evolution version is unsupported")
        if rules.get("projection") != PROJECTION_VERSION:
            raise ProtocolError("unsupported_projection", "projection version is unsupported")
        if view != expected_view:
            raise ProtocolError("invalid_request", "view_spec differs from frozen fixture")
        if tick >= len(self.manifest["history"]):
            raise ProtocolError("history_missing", "requested tick is not retained")
        record = self.manifest["history"][tick]
        structure = record["development_structure"]
        return {"world_id": self.world_id, "schema_version": SCHEMA_VERSION, "logical_tick": tick,
                "source_revision": tick, "watermark": tick,
                "seed_identity": {"seed_id": self.seed_id, "initial_state_hash": digest(record["seed_initial_record"])},
                "development_structure": structure, "physics_sample": record["physics_sample"],
                "state_hash": record["state_hash"], "event_hash": record["event_hash"],
                "checkpoint_sha256": record["checkpoint_sha256"], "projection_version": PROJECTION_VERSION,
                "view_spec": view}

    def _advance(self, request: dict[str, Any]) -> dict[str, Any]:
        command_id = request.get("command_id")
        if not isinstance(command_id, str) or not command_id:
            raise ProtocolError("invalid_command_id", "command_id must be nonempty")
        fingerprint = digest({key: request.get(key) for key in ("world_id", "command_id", "expected_revision", "target_tick", "external_inputs")})
        previous = self.manifest["commands"].get(command_id)
        if previous:
            if previous["request_fingerprint"] != fingerprint:
                raise ProtocolError("command_id_conflict", "command_id reused with different input")
            return previous["result"]
        expected = safe_int(request.get("expected_revision"), "expected_revision")
        target = safe_int(request.get("target_tick"), "target_tick")
        if expected != self.manifest["state_revision"]:
            raise ProtocolError("revision_conflict", "expected_revision differs from head")
        if target != self.manifest["logical_tick"] + 1:
            raise ProtocolError("tick_sequence_error", "target_tick must be the next tick")
        inputs = request.get("external_inputs")
        if not isinstance(inputs, dict) or inputs.get("schema_version") != INPUT_VERSION:
            raise ProtocolError("invalid_external_inputs", "external_inputs schema is invalid")
        phase = inputs.get("phase")
        if phase not in PHASES:
            raise ProtocolError("unsupported_phase", "phase must be shaoyang or taiyang")
        if inputs != {"schema_version": INPUT_VERSION, "phase": phase}:
            raise ProtocolError("invalid_external_inputs", "unexpected external_inputs fields")
        old = self.manifest["history"][-1]
        try:
            vector = physics_vector(self.genesis.advance(phase))
            displacement = influence_mm(vector["position"][2], old["physics_sample"]["position"][2])
            sample = self._sample(vector, phase)
            node_id = f"{self.world_id}:node:{target}"
            edge_id = f"{self.world_id}:edge:{target}"
            node = {"node_id": node_id, "tick": target, "influence_mm": displacement,
                    "physics_candidate_hash": sample["physics_candidate_hash"]}
            edge = {"edge_id": edge_id, "from_node_id": f"{self.world_id}:node:{target-1}",
                    "to_node_id": node_id, "command_id": command_id,
                    "physics_candidate_hash": sample["physics_candidate_hash"]}
            prior = old["development_structure"]
            structure = {"root_id": prior["root_id"], "nodes": prior["nodes"] + [node], "edges": prior["edges"] + [edge]}
            structure_hash = digest(structure)
            event = {"previous_event_hash": self.manifest["event_head_hash"], "logical_tick": target,
                     "command_id": command_id, "physics_candidate_hash": sample["physics_candidate_hash"],
                     "node_id": node_id, "edge_id": edge_id, "influence_mm": displacement,
                     "rule_version": RULE_VERSION}
            event["event_hash"] = digest(event)
            state_hash = self._state_hash(target, old["seed_initial_record"], structure_hash, sample["physics_candidate_hash"])
            checkpoint = self._save_blob(self.genesis)
            record = {"logical_tick": target, "state_revision": target,
                      "seed_initial_record": old["seed_initial_record"],
                      "development_structure": {**structure, "structure_hash": structure_hash},
                      "physics_sample": sample, "state_hash": state_hash,
                      "event_hash": event["event_hash"], "checkpoint_sha256": checkpoint}
            next_manifest = {**self.manifest, "logical_tick": target, "state_revision": target,
                             "head_state_hash": state_hash, "event_head_hash": event["event_hash"],
                             "checkpoint_sha256": checkpoint,
                             "history": self.manifest["history"] + [record],
                             "events": self.manifest["events"] + [event]}
            result = self._result_for_record(record, command_id)
            next_manifest["commands"] = {**self.manifest["commands"], command_id: {"request_fingerprint": fingerprint, "result": result}}
            try:
                self._write_manifest(next_manifest)
            except ManifestWriteFailure as exc:
                if exc.replacement_started:
                    self._fatal_error = str(exc)
                    raise ProtocolError("commit_status_uncertain", "manifest replacement attempted; restart required") from exc
                raise ProtocolError("persistence_failed", "manifest not replaced") from exc
            self.manifest = next_manifest
            return result
        except ProtocolError:
            if self._fatal_error is None:
                try:
                    self._restore_committed_scene()
                except Exception as restore_exc:
                    self._fatal_error = str(restore_exc)
                    raise ProtocolError("worker_stopped", "failed to restore committed Genesis scene") from restore_exc
            raise
        except Exception as exc:
            try:
                self._restore_committed_scene()
            except Exception as restore_exc:
                self._fatal_error = str(restore_exc)
                raise ProtocolError("worker_stopped", "failed to restore committed Genesis scene") from restore_exc
            raise ProtocolError("genesis_failed", f"candidate tick failed: {exc}") from exc

    def _restore_committed_scene(self) -> None:
        self.genesis = self.adapter_cls(self._blob(self.manifest["checkpoint_sha256"]), **self.adapter_args)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--dt", type=float, default=0.01)
    parser.add_argument("--physical-steps", type=int, default=8)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    try:
        worker = Worker(args.state_dir, args.world_id, dt=args.dt, physical_steps=args.physical_steps, seed=args.seed)
    except Exception as exc:
        print(json.dumps({"protocol_version": 1, "request_id": "", "ok": False,
                          "error": {"code": "startup_error", "message": str(exc)}}, allow_nan=False), flush=True)
        return 2
    for line in sys.stdin:
        try:
            request = json.loads(line, parse_constant=lambda x: (_ for _ in ()).throw(ValueError(x)))
            response = worker.handle(request)
        except (json.JSONDecodeError, ValueError) as exc:
            response = {"protocol_version": 1, "request_id": "", "ok": False,
                        "error": {"code": "invalid_json", "message": str(exc)}}
        sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":"), allow_nan=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
