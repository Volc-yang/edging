"""Standalone JSONL authority for the first CHAOS -> ONE experiment.

Launch from the repository root with::

    python3 -m engine.chaos.origin_worker \
      --initial-world models/chaos/initial_world_seed7.json \
      --state-dir /tmp/edgeworld-chaos-demo --world-id chaos-demo --seed 7

The existing UE process launcher also supplies --dt and --physical-steps;
they are accepted for compatibility and never drive O1. The state directory
must be separate from the tree and Genesis workers. One process is the sole
writer; there is no cross-process lock in this finite prototype.
"""

from __future__ import annotations

import argparse
import copy
import json
import sys
import threading
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from engine.chaos.origin_runtime import (
        MAX_SAFE_INTEGER, PROJECTION_VERSION, RULESET_VERSION, SCHEMA_VERSION,
        OriginError, advance_candidate, ascii_id, command_input, digest,
        observe_result, safe_int, validate_initial_world,
    )
    from engine.chaos.origin_store import ManifestStore, ManifestWriteFailure
else:
    from .origin_runtime import (
        MAX_SAFE_INTEGER, PROJECTION_VERSION, RULESET_VERSION, SCHEMA_VERSION,
        OriginError, advance_candidate, ascii_id, command_input, digest,
        observe_result, safe_int, validate_initial_world,
    )
    from .origin_store import ManifestStore, ManifestWriteFailure


PROTOCOL_VERSION = 1


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def load_initial_world(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise OriginError("invalid_initial_world", f"cannot read InitialWorld JSON: {exc}") from exc
    return validate_initial_world(data)


class Worker:
    def __init__(self, state_dir: Path, initial_world: dict[str, Any], *, world_id: str,
                 seed: int | None = None):
        initial_world = validate_initial_world(initial_world)
        ascii_id(world_id, "world_id")
        if initial_world["world_id"] != world_id:
            raise OriginError("world_mismatch", "InitialWorld world_id differs from worker argument")
        if seed is not None and safe_int(seed, "seed") != initial_world["world_seed"]:
            raise OriginError("invalid_initial_world", "InitialWorld seed differs from worker argument")
        self.world_id = world_id
        self.store = ManifestStore(state_dir, initial_world)
        self._lock = threading.Lock()
        self._fatal = False

    def _response(self, request_id: str, *, result: dict[str, Any] | None = None,
                  error: dict[str, Any] | None = None) -> dict[str, Any]:
        response: dict[str, Any] = {"protocol_version": PROTOCOL_VERSION,
                                    "request_id": request_id, "ok": error is None}
        if error is None:
            response["result"] = copy.deepcopy(result)
        else:
            response["error"] = error
        return response

    def _head(self) -> dict[str, Any]:
        manifest = self.store.manifest
        state = manifest["head"]
        return {"world_id": self.world_id, "logical_tick": state["logical_tick"],
                "state_revision": state["state_revision"], "phase": state["phase"],
                "event_watermark": state["event_watermark"],
                "world_spirit_id": state["world_spirit_id"],
                "state_hash": manifest["head_state_hash"],
                "event_hash": manifest["event_head_hash"],
                "initial_manifest_hash": manifest["initial_manifest_hash"]}

    def _check_world(self, request: dict[str, Any]) -> None:
        if request.get("world_id") != self.world_id:
            raise OriginError("world_mismatch", "request world_id differs from this worker")

    def handle(self, request: Any) -> dict[str, Any]:
        request_id = request.get("request_id", "") if isinstance(request, dict) else ""
        if not isinstance(request_id, str):
            request_id = ""
        try:
            if not isinstance(request, dict):
                raise OriginError("invalid_request", "request must be a JSON object")
            if safe_int(request.get("protocol_version"), "protocol_version") != PROTOCOL_VERSION:
                raise OriginError("unsupported_protocol", "protocol_version must be 1")
            ascii_id(request_id, "request_id")
            with self._lock:
                if self._fatal:
                    return self._response(request_id, error={
                        "code": "worker_stopped", "message": "uncertain commit; restart to recover from disk"})
                self._check_world(request)
                operation = request.get("operation")
                if operation == "status":
                    return self._response(request_id, result={**self._head(),
                        "schema_version": SCHEMA_VERSION,
                        "ruleset_version": RULESET_VERSION,
                        "projection_version": PROJECTION_VERSION})
                if operation == "advance":
                    return self._advance(request, request_id)
                if operation == "observe":
                    tick = safe_int(request.get("logical_tick"), "logical_tick")
                    result = observe_result(self.store.manifest, tick, request.get("view_spec"))
                    return self._response(request_id, result=result)
                raise OriginError("unknown_operation", f"unsupported operation: {operation!r}")
        except OriginError as exc:
            return self._response(request_id, error={"code": exc.code, "message": str(exc),
                                                     "head": self._head()})
        except Exception as exc:
            return self._response(request_id, error={"code": "worker_error", "message": str(exc),
                                                     "head": self._head()})

    def _advance(self, request: dict[str, Any], request_id: str) -> dict[str, Any]:
        command_id = ascii_id(request.get("command_id"), "command_id")
        revision = safe_int(request.get("expected_revision"), "expected_revision")
        target_tick = safe_int(request.get("target_tick"), "target_tick")
        origin_action = request.get("origin_action")
        if not isinstance(origin_action, str):
            raise OriginError("invalid_origin_action", "origin_action must be a string")
        fields = command_input(self.world_id, command_id, revision, target_tick, origin_action)
        fingerprint = digest(fields)
        previous = self.store.manifest["commands"].get(command_id)
        if previous is not None:
            if previous["request_fingerprint"] != fingerprint:
                raise OriginError("command_id_conflict", "command_id was used with different inputs")
            return self._response(request_id, result=previous["result"])
        if origin_action != "reveal_world_spirit":
            raise OriginError("invalid_origin_action", "only reveal_world_spirit is supported")
        if target_tick != 1:
            raise OriginError("invalid_target_tick", "O1 target_tick must be 1")
        head = self.store.manifest["head"]
        if revision != head["state_revision"]:
            raise OriginError("revision_conflict", "expected_revision differs from current head")
        if head["phase"] != "CHAOS" or head["logical_tick"] != 0:
            raise OriginError("phase_conflict", "O1 is only allowed from CHAOS at tick zero")
        candidate, result = advance_candidate(self.store.manifest, command_id)
        try:
            self.store.commit(candidate)
        except ManifestWriteFailure as exc:
            if exc.replacement_started:
                self._fatal = True
                return self._response(request_id, error={
                    "code": "commit_status_uncertain",
                    "message": "manifest replacement was attempted; restart before retry"})
            raise OriginError("persistence_failed", f"manifest write failed before replacement: {exc}") from exc
        return self._response(request_id, result=result)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--initial-world", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--world-id", required=True)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--dt", type=float, default=0.01,
                        help="accepted for UE launcher compatibility; unused by O1")
    parser.add_argument("--physical-steps", type=int, default=8,
                        help="accepted for UE launcher compatibility; unused by O1")
    args = parser.parse_args(argv)
    try:
        worker = Worker(args.state_dir, load_initial_world(args.initial_world),
                        world_id=args.world_id, seed=args.seed)
    except OriginError as exc:
        print(json.dumps({"protocol_version": PROTOCOL_VERSION, "startup_error": {
            "code": exc.code, "message": str(exc)}}, separators=(",", ":")), flush=True)
        return 2
    for line in sys.stdin:
        try:
            request = json.loads(line, object_pairs_hook=_unique_object,
                                 parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (json.JSONDecodeError, ValueError) as exc:
            response = {"protocol_version": PROTOCOL_VERSION, "request_id": "", "ok": False,
                        "error": {"code": "invalid_json", "message": str(exc)}}
        else:
            response = worker.handle(request)
        print(json.dumps(response, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False, allow_nan=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
