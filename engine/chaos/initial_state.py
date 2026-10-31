"""Canonical encoding and geometric validation for the first chaos world slice.

This module has no persistence or clock authority. The origin worker owns the
atomic tick-0 commit described in ``doc/chaos_origin_contract.md``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping

MAX_EXACT_INTEGER = (1 << 53) - 1
PLACE_KINDS = frozenset(
    {"city", "wildland", "plain", "forest", "ocean", "river_marsh"}
)


def canonical_bytes(value: object) -> bytes:
    """Return the P0 canonical JSON encoding; callers validate before hashing."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def initial_manifest_hash(world: Mapping[str, object]) -> str:
    validate_initial_world(world)
    return hashlib.sha256(canonical_bytes(world)).hexdigest()


def _integer(value: object, field: str, *, minimum: int = -MAX_EXACT_INTEGER) -> int:
    if type(value) is not int or not minimum <= value <= MAX_EXACT_INTEGER:
        raise ValueError(f"{field} must be an exact integer in range")
    return value


def _ascii_id(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or not value.isascii():
        raise ValueError(f"{field} must be a nonempty ASCII string")
    return value


def _point(value: object, field: str, extent: tuple[int, int, int, int]) -> tuple[int, int]:
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError(f"{field} must be an XY pair")
    x = _integer(value[0], f"{field}.x")
    y = _integer(value[1], f"{field}.y")
    if not (extent[0] <= x <= extent[2] and extent[1] <= y <= extent[3]):
        raise ValueError(f"{field} lies outside extent_cm")
    return x, y


def _inside(point: tuple[int, int], polygon: list[tuple[int, int]]) -> bool:
    """Boundary-inclusive point-in-polygon for the finite P0 polygon contract."""
    x, y = point
    inside = False
    for (x1, y1), (x2, y2) in zip(polygon, polygon[1:]):
        cross = (x - x1) * (y2 - y1) - (y - y1) * (x2 - x1)
        if cross == 0 and min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
            return True
        if (y1 > y) != (y2 > y):
            left = (x2 - x1) * (y - y1)
            right = (x - x1) * (y2 - y1)
            if (left > right) == (y2 > y1):
                inside = not inside
    return inside


def _polygon(value: object, field: str, extent: tuple[int, int, int, int]) -> list[tuple[int, int]]:
    if not isinstance(value, list) or len(value) < 4:
        raise ValueError(f"{field} must contain at least three vertices and closure")
    points = [_point(raw, f"{field}[{i}]", extent) for i, raw in enumerate(value)]
    if points[0] != points[-1] or len(set(points[:-1])) < 3:
        raise ValueError(f"{field} must be a nondegenerate closed polygon")
    area2 = sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(points, points[1:]))
    if area2 <= 0:
        raise ValueError(f"{field} must have counterclockwise winding and positive area")
    return points


def validate_initial_world(world: Mapping[str, object]) -> None:
    """Reject malformed or falsely connected initial-world manifests."""
    if not isinstance(world, Mapping):
        raise ValueError("InitialWorld must be an object")
    expected = {
        "world_id", "world_seed", "schema_version", "generator_version",
        "ruleset_version", "logical_tick", "state_revision", "phase",
        "random_stream", "extent_cm", "places", "watercourses", "routes",
        "world_spirit_id", "event_watermark",
    }
    if set(world) != expected:
        raise ValueError("InitialWorld fields do not match chaos origin v1")
    _ascii_id(world["world_id"], "world_id")
    _integer(world["world_seed"], "world_seed", minimum=0)
    versions = {
        "schema_version": "edgeworld.chaos-origin.v1",
        "generator_version": "chaos-geography-exp-v1",
        "ruleset_version": "chaos-o1-exp-v1",
    }
    for field, version in versions.items():
        if world[field] != version:
            raise ValueError(f"unsupported {field}")
    for field in ("logical_tick", "state_revision", "event_watermark"):
        _integer(world[field], field, minimum=0)
    if world["logical_tick"] != 0 or world["state_revision"] != 0 or world["event_watermark"] != 0:
        raise ValueError("InitialWorld must be the unadvanced tick-0 state")
    if world["phase"] != "CHAOS" or world["world_spirit_id"] is not None:
        raise ValueError("initial spirit state must be CHAOS/null")
    stream = world["random_stream"]
    if not isinstance(stream, dict) or set(stream) != {"algorithm", "version", "cursor"}:
        raise ValueError("invalid random_stream")
    _integer(stream["version"], "random_stream.version", minimum=0)
    if stream["algorithm"] != "sha256-counter" or stream["version"] != 1:
        raise ValueError("unsupported random_stream")
    _integer(stream["cursor"], "random_stream.cursor", minimum=0)
    raw_extent = world["extent_cm"]
    if not isinstance(raw_extent, list) or len(raw_extent) != 4:
        raise ValueError("extent_cm must have four coordinates")
    extent = tuple(_integer(v, f"extent_cm[{i}]") for i, v in enumerate(raw_extent))
    if extent[0] >= extent[2] or extent[1] >= extent[3]:
        raise ValueError("extent_cm must have positive area")

    places = world["places"]
    if not isinstance(places, list) or len(places) < len(PLACE_KINDS):
        raise ValueError("six place kinds are required")
    by_id: dict[str, tuple[str, list[tuple[int, int]]]] = {}
    kinds: set[str] = set()
    for i, place in enumerate(places):
        if not isinstance(place, dict) or set(place) != {
            "place_id", "kind", "footprint_cm", "elevation_cm", "potential"
        }:
            raise ValueError(f"places[{i}] has invalid fields")
        place_id = _ascii_id(place["place_id"], f"places[{i}].place_id")
        if place_id in by_id:
            raise ValueError("duplicate place_id")
        kind = place["kind"]
        if not isinstance(kind, str) or kind not in PLACE_KINDS:
            raise ValueError(f"places[{i}] has unknown kind")
        polygon = _polygon(place["footprint_cm"], f"places[{i}].footprint_cm", extent)
        _integer(place["elevation_cm"], f"places[{i}].elevation_cm")
        potential = place["potential"]
        if not isinstance(potential, dict) or not potential:
            raise ValueError(f"places[{i}].potential must be nonempty")
        for name, amount in potential.items():
            _ascii_id(name, "potential key")
            _integer(amount, f"potential.{name}", minimum=0)
            if amount > 10000:
                raise ValueError("potential value exceeds fixed-point range")
        by_id[place_id] = (kind, polygon)
        kinds.add(kind)
    if kinds != PLACE_KINDS:
        raise ValueError("InitialWorld must include all six place kinds")

    watercourses = world["watercourses"]
    if not isinstance(watercourses, list) or not watercourses:
        raise ValueError("at least one watercourse is required")
    water_ids: set[str] = set()
    for i, watercourse in enumerate(watercourses):
        if not isinstance(watercourse, dict) or set(watercourse) != {
            "watercourse_id", "polyline_cm", "marsh_place_id", "outlet_place_id"
        }:
            raise ValueError(f"watercourses[{i}] has invalid fields")
        wid = _ascii_id(watercourse["watercourse_id"], "watercourse_id")
        if wid in water_ids:
            raise ValueError("duplicate watercourse_id")
        water_ids.add(wid)
        raw_line = watercourse["polyline_cm"]
        if not isinstance(raw_line, list) or len(raw_line) < 2:
            raise ValueError("watercourse needs at least two points")
        line = [_point(v, "watercourse point", extent) for v in raw_line]
        marsh_id = watercourse["marsh_place_id"]
        outlet_id = watercourse["outlet_place_id"]
        if marsh_id not in by_id or by_id[marsh_id][0] != "river_marsh":
            raise ValueError("watercourse marsh_place_id must name a river_marsh")
        if outlet_id not in by_id or by_id[outlet_id][0] != "ocean":
            raise ValueError("watercourse outlet_place_id must name an ocean")
        if not any(_inside(point, by_id[marsh_id][1]) for point in line):
            raise ValueError("watercourse does not pass through marsh")
        if not _inside(line[-1], by_id[outlet_id][1]):
            raise ValueError("watercourse does not terminate in ocean")

    routes = world["routes"]
    if not isinstance(routes, list) or not routes:
        raise ValueError("at least one observation route is required")
    route_ids: set[str] = set()
    connected = False
    for i, route in enumerate(routes):
        if not isinstance(route, dict) or set(route) != {"route_id", "polyline_cm", "place_ids"}:
            raise ValueError(f"routes[{i}] has invalid fields")
        rid = _ascii_id(route["route_id"], "route_id")
        if rid in route_ids:
            raise ValueError("duplicate route_id")
        route_ids.add(rid)
        raw_line = route["polyline_cm"]
        if not isinstance(raw_line, list) or len(raw_line) < 2:
            raise ValueError("route needs at least two points")
        line = [_point(v, "route point", extent) for v in raw_line]
        ids = route["place_ids"]
        if not isinstance(ids, list) or not ids or any(not isinstance(v, str) for v in ids):
            raise ValueError("route place_ids must be distinct ASCII IDs")
        if len(set(ids)) != len(ids):
            raise ValueError("route place_ids must be distinct")
        cursor = 0
        for place_id in ids:
            if place_id not in by_id:
                raise ValueError("route references unknown place")
            while cursor < len(line) and not _inside(line[cursor], by_id[place_id][1]):
                cursor += 1
            if cursor == len(line):
                raise ValueError("route does not visit places in listed order")
            cursor += 1
        visited_kinds = [by_id[place_id][0] for place_id in ids]
        marsh_index = visited_kinds.index("river_marsh") if "river_marsh" in visited_kinds else -1
        ocean_index = visited_kinds.index("ocean") if "ocean" in visited_kinds else -1
        middle_indices = [i for i, kind in enumerate(visited_kinds) if kind in ("plain", "forest")]
        if (visited_kinds[0] == "city" and marsh_index > 0
                and ocean_index > marsh_index and any(0 < i < marsh_index for i in middle_indices)):
            connected = True
    if not connected:
        raise ValueError("no city-to-marsh-to-ocean observation route")
