"""Contract checks for the finite chaos world initial-state generator."""

import json
import unittest
from copy import deepcopy
from pathlib import Path

from engine.chaos.initial_state import canonical_bytes, initial_manifest_hash, validate_initial_world
from engine.chaos.world_generation import generate_initial_world


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "models/chaos/initial_world_seed7.json"
P0_HASH = "75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3"


class ChaosWorldGenerationTests(unittest.TestCase):
    def test_seed7_matches_p0_fixture_and_digest(self):
        world = generate_initial_world("chaos-demo", 7)
        fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(world, fixture)
        self.assertEqual(initial_manifest_hash(world), P0_HASH)
        self.assertEqual(canonical_bytes(world), canonical_bytes(fixture))
        self.assertEqual({p["kind"] for p in world["places"]}, {
            "city", "wildland", "plain", "forest", "ocean", "river_marsh"
        })

    def test_seeded_potentials_are_repeatable_without_changing_route(self):
        first = generate_initial_world("chaos-demo", 8)
        second = generate_initial_world("chaos-demo", 8)
        golden = generate_initial_world("chaos-demo", 7)
        self.assertEqual(canonical_bytes(first), canonical_bytes(second))
        self.assertEqual(first["random_stream"]["cursor"], 0)
        self.assertEqual(first["routes"], golden["routes"])
        self.assertEqual(first["watercourses"], golden["watercourses"])
        self.assertNotEqual(first["places"][0]["potential"], golden["places"][0]["potential"])
        self.assertNotEqual(initial_manifest_hash(first), initial_manifest_hash(golden))

    def test_watercourse_must_reach_marsh_and_ocean(self):
        world = generate_initial_world()
        disconnected = deepcopy(world)
        disconnected["watercourses"][0]["polyline_cm"] = [[40000, 55000], [80000, 60000]]
        with self.assertRaisesRegex(ValueError, "marsh"):
            validate_initial_world(disconnected)
        disconnected = deepcopy(world)
        disconnected["watercourses"][0]["polyline_cm"][-1] = [65000, 40000]
        with self.assertRaisesRegex(ValueError, "ocean"):
            validate_initial_world(disconnected)

    def test_route_must_visit_places_in_listed_order(self):
        world = generate_initial_world()
        invalid = deepcopy(world)
        invalid["routes"][0]["place_ids"] = list(reversed(invalid["routes"][0]["place_ids"]))
        with self.assertRaisesRegex(ValueError, "listed order"):
            validate_initial_world(invalid)

    def test_invalid_seed_and_noncanonical_numeric_input_rejected(self):
        for value in (True, -1, 1 << 53, 0.5):
            with self.subTest(value=value), self.assertRaises(ValueError):
                generate_initial_world(world_seed=value)
        invalid = generate_initial_world()
        invalid["places"][0]["potential"]["civilization"] = True
        with self.assertRaises(ValueError):
            validate_initial_world(invalid)

    def test_polygon_must_be_closed_and_counterclockwise(self):
        world = generate_initial_world()
        invalid = deepcopy(world)
        invalid["places"][0]["footprint_cm"].pop()
        with self.assertRaisesRegex(ValueError, "closed polygon"):
            validate_initial_world(invalid)
        invalid = deepcopy(world)
        invalid["places"][0]["footprint_cm"] = list(reversed(invalid["places"][0]["footprint_cm"]))
        with self.assertRaisesRegex(ValueError, "counterclockwise"):
            validate_initial_world(invalid)


if __name__ == "__main__":
    unittest.main()
