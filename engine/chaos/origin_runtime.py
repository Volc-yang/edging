"""Finite, deterministic CHAOS -> ONE authority model for the first PDCA slice.

The InitialWorld JSON is produced by D1. This module deliberately depends on
its frozen P0 fields rather than importing another task's implementation.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


SCHEMA_VERSION = "edgeworld.chaos-origin.v1"
RULESET_VERSION = "chaos-o1-exp-v1"
GENERATOR_VERSION = "chaos-geography-exp-v1"
PROJECTION_VERSION = "chaos-ue-projection-exp-v1"
MAX_SAFE_INTEGER = (1 << 53) - 1
ZERO_HASH = "0" * 64
PLACE_KINDS = {"city", "wildland", "plain", "forest", "ocean", "river_marsh"}


class OriginError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def safe_int(value: Any, name: str) -> int:
    if type(value) is not int or not 0 <= value <= MAX_SAFE_INTEGER:
        raise OriginError(f"invalid_{name}", f"{name} must be a non-negative safe JSON integer")
    return value


def ascii_id(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value or not value.isascii() or any(ord(c) < 33 for c in value):
        raise OriginError(f"invalid_{name}", f"{name} must be a non-empty printable ASCII identifier")
    return value


def _point(value: Any) -> bool:
    return (isinstance(value, list) and len(value) == 2
            and all(type(n) is int and abs(n) <= MAX_SAFE_INTEGER for n in value))


def _finite_integer_json(value: Any) -> bool:
    if value is None or type(value) in (str, bool):
        return True
    if type(value) is int:
        return abs(value) <= MAX_SAFE_INTEGER
    if isinstance(value, list):
        return all(_finite_integer_json(item) for item in value)
    if isinstance(value, dict):
        return all(isinstance(key, str) and key.isascii() and _finite_integer_json(item)
                   for key, item in value.items())
    return False


def validate_initial_world(value: Any) -> dict[str, Any]:
    """Check D2's authority boundary; D1 owns detailed geometry validation."""
    if not isinstance(value, dict):
        raise OriginError("invalid_initial_world", "InitialWorld must be a JSON object")
    if not _finite_integer_json(value):
        raise OriginError("invalid_initial_world", "InitialWorld permits only finite safe integers")
    if value.get("schema_version") != SCHEMA_VERSION or value.get("generator_version") != GENERATOR_VERSION:
        raise OriginError("invalid_initial_world", "InitialWorld schema/generator version mismatch")
    if value.get("ruleset_version") != RULESET_VERSION:
        raise OriginError("invalid_initial_world", "InitialWorld ruleset version mismatch")
    ascii_id(value.get("world_id"), "world_id")
    safe_int(value.get("world_seed"), "world_seed")
    if (value.get("logical_tick"), value.get("state_revision"), value.get("phase"),
            value.get("world_spirit_id"), value.get("event_watermark")) != (0, 0, "CHAOS", None, 0):
        raise OriginError("invalid_initial_world", "InitialWorld must be uncommitted CHAOS at tick zero")
    stream = value.get("random_stream")
    if not isinstance(stream, dict) or stream.get("algorithm") != "sha256-counter" or stream.get("version") != 1:
        raise OriginError("invalid_initial_world", "unsupported random stream")
    safe_int(stream.get("cursor"), "random_cursor")
    extent = value.get("extent_cm")
    if not isinstance(extent, list) or len(extent) != 4 or not all(type(n) is int and abs(n) <= MAX_SAFE_INTEGER for n in extent):
        raise OriginError("invalid_initial_world", "extent_cm must have four integer coordinates")
    if extent[0] >= extent[2] or extent[1] >= extent[3]:
        raise OriginError("invalid_initial_world", "extent_cm has no area")
    places = value.get("places")
    if not isinstance(places, list) or len(places) < 6:
        raise OriginError("invalid_initial_world", "InitialWorld needs six place kinds")
    ids: set[str] = set()
    kinds: set[str] = set()
    for place in places:
        if not isinstance(place, dict):
            raise OriginError("invalid_initial_world", "place must be an object")
        pid = ascii_id(place.get("place_id"), "place_id")
        if pid in ids:
            raise OriginError("invalid_initial_world", "duplicate place_id")
        ids.add(pid)
        kind = place.get("kind")
        if not isinstance(kind, str) or kind not in PLACE_KINDS:
            raise OriginError("invalid_initial_world", "unknown place kind")
        kinds.add(kind)
        footprint = place.get("footprint_cm")
        if not isinstance(footprint, list) or len(footprint) < 4 or not all(_point(p) for p in footprint) or footprint[0] != footprint[-1]:
            raise OriginError("invalid_initial_world", "place footprint must be a closed polygon")
        for px, py in footprint:
            if not (extent[0] <= px <= extent[2] and extent[1] <= py <= extent[3]):
                raise OriginError("invalid_initial_world", "place lies outside extent")
        if type(place.get("elevation_cm")) is not int or abs(place["elevation_cm"]) > MAX_SAFE_INTEGER:
            raise OriginError("invalid_initial_world", "place elevation is invalid")
        potential = place.get("potential")
        if not isinstance(potential, dict) or not potential or any(
            not isinstance(k, str) or not k.isascii() or type(v) is not int or not 0 <= v <= 10000
            for k, v in potential.items()
        ):
            raise OriginError("invalid_initial_world", "place potential is invalid")
    if kinds != PLACE_KINDS:
        raise OriginError("invalid_initial_world", "six place kinds are required")
    for key, id_key in (("watercourses", "watercourse_id"), ("routes", "route_id")):
        records = value.get(key)
        if not isinstance(records, list) or not records:
            raise OriginError("invalid_initial_world", f"{key} must be non-empty")
        seen: set[str] = set()
        for record in records:
            if not isinstance(record, dict):
                raise OriginError("invalid_initial_world", f"{key} record must be an object")
            rid = ascii_id(record.get(id_key), id_key)
            if rid in seen:
                raise OriginError("invalid_initial_world", f"duplicate {id_key}")
            seen.add(rid)
            line = record.get("polyline_cm")
            if not isinstance(line, list) or len(line) < 2 or not all(_point(p) for p in line):
                raise OriginError("invalid_initial_world", f"{key} polyline is invalid")
            if key == "watercourses":
                if record.get("marsh_place_id") not in ids or record.get("outlet_place_id") not in ids:
                    raise OriginError("invalid_initial_world", "watercourse place reference is missing")
            elif not isinstance(record.get("place_ids"), list) or any(p not in ids for p in record["place_ids"]):
                raise OriginError("invalid_initial_world", "route place reference is missing")
    try:
        canonical(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OriginError("invalid_initial_world", f"InitialWorld is not canonical JSON: {exc}") from exc
    return value


def state_hash(state: dict[str, Any]) -> str:
    keys = ("world_id", "initial_manifest_hash", "logical_tick", "state_revision", "phase",
            "world_spirit_id", "event_watermark", "random_cursor")
    return digest({key: state[key] for key in keys})


def initial_manifest(initial_world: dict[str, Any]) -> dict[str, Any]:
    initial_world = validate_initial_world(initial_world)
    initial_hash = digest(initial_world)
    state = {
        "world_id": initial_world["world_id"], "initial_manifest_hash": initial_hash,
        "logical_tick": 0, "state_revision": 0, "phase": "CHAOS",
        "world_spirit_id": None, "event_watermark": 0,
        "random_cursor": initial_world["random_stream"]["cursor"],
    }
    return {
        "schema_version": SCHEMA_VERSION, "world_id": initial_world["world_id"],
        "initial_world": initial_world, "initial_manifest_hash": initial_hash,
        "head": state, "head_state_hash": state_hash(state), "event_head_hash": ZERO_HASH,
        "history": [{"state": state, "state_hash": state_hash(state), "event_hash": ZERO_HASH}],
        "events": [], "commands": {},
    }


def command_input(world_id: str, command_id: str, expected_revision: int,
                  target_tick: int, origin_action: str) -> dict[str, Any]:
    return {"world_id": world_id, "command_id": command_id,
            "expected_revision": expected_revision, "target_tick": target_tick,
            "origin_action": origin_action}


def advance_candidate(manifest: dict[str, Any], command_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    head = manifest["head"]
    initial = manifest["initial_world"]
    world_id = head["world_id"]
    request = command_input(world_id, command_id, 0, 1, "reveal_world_spirit")
    input_hash = digest(request)
    spirit_id = "spirit-" + digest([SCHEMA_VERSION, world_id, initial["world_seed"], RULESET_VERSION])[:16]
    new_state = {**head, "logical_tick": 1, "state_revision": 1, "phase": "ONE",
                 "world_spirit_id": spirit_id, "event_watermark": 1}
    new_state_hash = state_hash(new_state)
    event = {
        "event_id": "event-o1-" + digest([world_id, command_id, 1])[:16],
        "cause_code": "explicit_origin_reveal", "command_id": command_id,
        "logical_tick": 1, "ruleset_version": RULESET_VERSION,
        "input_hash": input_hash, "before_state_hash": manifest["head_state_hash"],
        "after_state_hash": new_state_hash, "previous_event_hash": ZERO_HASH,
        "random_cursor_before": head["random_cursor"],
        "random_cursor_after": head["random_cursor"],
    }
    new_event_hash = hashlib.sha256(bytes.fromhex(ZERO_HASH) + canonical(event)).hexdigest()
    result = {"world_id": world_id, "logical_tick": 1, "state_revision": 1,
              "phase": "ONE", "world_spirit_id": spirit_id, "event_watermark": 1,
              "state_hash": new_state_hash, "event_hash": new_event_hash}
    candidate = {**manifest, "head": new_state, "head_state_hash": new_state_hash,
                 "event_head_hash": new_event_hash,
                 "history": manifest["history"] + [{"state": new_state, "state_hash": new_state_hash,
                                                       "event_hash": new_event_hash}],
                 "events": [event],
                 "commands": {command_id: {"request_fingerprint": input_hash, "result": result}}}
    return candidate, result


def validate_manifest(manifest: Any, expected_initial: dict[str, Any]) -> dict[str, Any]:
    """Recreate every finite committed record; reject damaged or invented history."""
    baseline = initial_manifest(expected_initial)
    if not isinstance(manifest, dict):
        raise OriginError("corrupt_state", "authority manifest is not an object")
    if manifest == baseline:
        return manifest
    if (manifest.get("schema_version") != SCHEMA_VERSION
            or manifest.get("world_id") != expected_initial["world_id"]
            or manifest.get("initial_world") != expected_initial
            or manifest.get("initial_manifest_hash") != baseline["initial_manifest_hash"]):
        raise OriginError("corrupt_state", "authority manifest identity or initial state mismatch")
    events = manifest.get("events")
    if not isinstance(events, list) or len(events) != 1 or not isinstance(events[0], dict):
        raise OriginError("corrupt_state", "authority manifest has invalid event history")
    command_id = events[0].get("command_id")
    if not isinstance(command_id, str) or not command_id:
        raise OriginError("corrupt_state", "authority manifest has invalid command ID")
    expected, _ = advance_candidate(baseline, command_id)
    if manifest != expected:
        raise OriginError("corrupt_state", "authority manifest does not match O1 replay")
    return manifest


def observe_result(manifest: dict[str, Any], tick: int, view_spec: Any) -> dict[str, Any]:
    if tick > manifest["head"]["logical_tick"]:
        raise OriginError("history_missing", "requested logical tick is not retained")
    if not isinstance(view_spec, dict):
        raise OriginError("invalid_view_spec", "view_spec must be an object")
    if set(view_spec) != {"watermark", "region", "observer", "resolution", "error_budget", "rules"}:
        raise OriginError("invalid_view_spec", "view_spec must bind the fixed sampling fields")
    watermark = safe_int(view_spec.get("watermark"), "watermark")
    record = manifest["history"][tick]
    if watermark != record["state"]["state_revision"]:
        raise OriginError("watermark_mismatch", "watermark must match requested tick revision")
    if view_spec.get("region") != "origin-sample":
        raise OriginError("invalid_view_spec", "region must be origin-sample")
    ascii_id(view_spec.get("observer"), "observer")
    if view_spec.get("resolution") != "chaos-proxy-v1":
        raise OriginError("invalid_view_spec", "resolution must be chaos-proxy-v1")
    if view_spec.get("error_budget") != {"semantic_state": "exact", "visual_geometry": "proxy"}:
        raise OriginError("invalid_view_spec", "unsupported error_budget")
    rules = view_spec.get("rules")
    if not isinstance(rules, dict) or rules.get("evolution") != RULESET_VERSION or rules.get("projection") != PROJECTION_VERSION:
        raise OriginError("unsupported_rules", "rules must match the frozen evolution and projection versions")
    try:
        canonical(view_spec)
    except (TypeError, ValueError, OverflowError) as exc:
        raise OriginError("invalid_view_spec", f"view_spec is not finite JSON: {exc}") from exc
    state = record["state"]
    initial = manifest["initial_world"]
    place_ids = [p["place_id"] for p in initial["places"]]
    sample = {
        "world_spirit_id": state["world_spirit_id"], "place_ids": place_ids,
        "watercourse_ids": [w["watercourse_id"] for w in initial["watercourses"]],
        "route_ids": [r["route_id"] for r in initial["routes"]],
        "spirit_boundary_place_ids": place_ids if state["phase"] == "ONE" else [],
    }
    return {"world_id": state["world_id"], "logical_tick": tick,
            "source_revision": state["state_revision"], "watermark": watermark,
            "phase": state["phase"], "sample": sample,
            "projection_version": PROJECTION_VERSION,
            "initial_manifest_hash": manifest["initial_manifest_hash"],
            "state_hash": record["state_hash"], "event_hash": record["event_hash"],
            "view_spec": view_spec}
