"""Finite, deterministic geography for the first chaos-origin demonstration.

The calibrated seed-7 sample is the P0 fixture. Other seeds retain the same
connected topology while changing latent place potentials through domain-
separated, stateless SHA-256 derivation. This is a geography proxy, not a
complete procedural planet or an ecological simulation. No sequential random
samples are consumed, so ``random_stream.cursor`` remains zero.
"""

from __future__ import annotations

import hashlib
from copy import deepcopy

from engine.chaos.initial_state import MAX_EXACT_INTEGER, validate_initial_world

_PLACES = [
    {
        "place_id": "city-1", "kind": "city",
        "footprint_cm": [[10000, 10000], [20000, 10000], [20000, 20000], [10000, 20000], [10000, 10000]],
        "elevation_cm": 200, "potential": {"civilization": 8000},
    },
    {
        "place_id": "wildland-1", "kind": "wildland",
        "footprint_cm": [[5000, 70000], [30000, 70000], [30000, 90000], [5000, 90000], [5000, 70000]],
        "elevation_cm": 600, "potential": {"ecology": 4000},
    },
    {
        "place_id": "plain-1", "kind": "plain",
        "footprint_cm": [[20000, 10000], [50000, 10000], [50000, 30000], [20000, 30000], [20000, 10000]],
        "elevation_cm": 150, "potential": {"ecology": 6000},
    },
    {
        "place_id": "forest-1", "kind": "forest",
        "footprint_cm": [[30000, 30000], [60000, 30000], [60000, 60000], [30000, 60000], [30000, 30000]],
        "elevation_cm": 350, "potential": {"ecology": 9000},
    },
    {
        "place_id": "river-marsh-1", "kind": "river_marsh",
        "footprint_cm": [[50000, 30000], [70000, 30000], [70000, 50000], [50000, 50000], [50000, 30000]],
        "elevation_cm": 50, "potential": {"wetness": 9500},
    },
    {
        "place_id": "ocean-1", "kind": "ocean",
        "footprint_cm": [[70000, 0], [100000, 0], [100000, 100000], [70000, 100000], [70000, 0]],
        "elevation_cm": 0, "potential": {"wetness": 10000},
    },
]


def _parameter(seed: int, domain: str) -> int:
    """A stateless seed/domain value; it does not advance the origin RNG."""
    payload = b"edgeworld-chaos-geography-v1\x00" + seed.to_bytes(8, "big") + domain.encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % 201


def generate_initial_world(world_id: str = "chaos-demo", world_seed: int = 7) -> dict:
    """Generate the P0 InitialWorld schema, including six connected places.

    Geometry is deliberately fixed in this first slice. A different seed
    changes each non-ocean place's latent potential by at most 200 points,
    relative to the calibrated seed-7 fixture. The ocean's full wetness stays
    at the fixed-point maximum. These potentials have no approved evolution
    semantics yet.
    """
    if not isinstance(world_id, str) or not world_id or not world_id.isascii():
        raise ValueError("world_id must be a nonempty ASCII string")
    if type(world_seed) is not int or not 0 <= world_seed <= MAX_EXACT_INTEGER:
        raise ValueError("world_seed must be an exact nonnegative integer")

    places = deepcopy(_PLACES)
    if world_seed != 7:
        for place in places[:-1]:
            for name, amount in place["potential"].items():
                domain = f"{place['place_id']}:{name}"
                place["potential"][name] = amount + _parameter(world_seed, domain) - _parameter(7, domain)

    world = {
        "schema_version": "edgeworld.chaos-origin.v1",
        "world_id": world_id,
        "world_seed": world_seed,
        "generator_version": "chaos-geography-exp-v1",
        "ruleset_version": "chaos-o1-exp-v1",
        "logical_tick": 0,
        "state_revision": 0,
        "phase": "CHAOS",
        "random_stream": {"algorithm": "sha256-counter", "version": 1, "cursor": 0},
        "extent_cm": [0, 0, 100000, 100000],
        "places": places,
        "watercourses": [{
            "watercourse_id": "river-1",
            "polyline_cm": [[40000, 55000], [60000, 40000], [80000, 40000]],
            "marsh_place_id": "river-marsh-1", "outlet_place_id": "ocean-1",
        }],
        "routes": [{
            "route_id": "origin-route-1",
            "polyline_cm": [[15000, 15000], [35000, 20000], [45000, 40000], [60000, 40000], [80000, 40000]],
            "place_ids": ["city-1", "plain-1", "forest-1", "river-marsh-1", "ocean-1"],
        }],
        "world_spirit_id": None,
        "event_watermark": 0,
    }
    validate_initial_world(world)
    return world
