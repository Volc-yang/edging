import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from world_engine import Era, RegionId, TimePhase, WorldClock, WorldEngine


class WorldEngineTests(unittest.TestCase):
    def test_region_hexagram_uses_x_lower_y_upper_bits(self):
        engine = WorldEngine(seed=1)

        self.assertEqual(engine.region(0, 0).hexagram_value, 0b000000)
        self.assertEqual(engine.region(7, 0).hexagram_value, 0b000111)
        self.assertEqual(engine.region(0, 7).hexagram_value, 0b111000)
        self.assertEqual(engine.region(7, 7).hexagram_value, 0b111111)

    def test_tile_sampling_is_deterministic_for_seed_and_coordinate(self):
        first = WorldEngine(seed=20260620, era=Era.ZHOU).tile(42, 17)
        second = WorldEngine(seed=20260620, era=Era.ZHOU).tile(42, 17)

        self.assertEqual(first, second)

    def test_tile_energy_stays_within_budget(self):
        engine = WorldEngine(seed=99, era=Era.MIESHI)

        for x in range(-16, 80, 11):
            for y in range(-16, 80, 13):
                tile = engine.tile(x, y)
                self.assertGreaterEqual(tile.height, 0)
                self.assertLessEqual(tile.height, 1)
                self.assertGreaterEqual(tile.moisture, 0)
                self.assertLessEqual(tile.moisture, 1)
                self.assertGreaterEqual(tile.temperature, 0)
                self.assertLessEqual(tile.temperature, 1)
                self.assertGreaterEqual(tile.entropy, 0)
                self.assertLessEqual(tile.entropy, 1)
                self.assertLessEqual(tile.yin_qi + tile.yang_qi, 1.0001)

    def test_clock_advances_through_four_phases_and_cycles(self):
        clock = WorldClock()

        clock.advance(1.25)
        self.assertIs(clock.phase, TimePhase.TAIYANG)
        self.assertEqual(clock.phase_progress, 0.25)

        clock.advance(3.0)
        self.assertIs(clock.phase, TimePhase.SHAOYANG)
        self.assertEqual(clock.cycle, 1)

    def test_export_region_summary_writes_json(self):
        engine = WorldEngine(seed=7)
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "summary.json"
            engine.export_region_summary(output, [RegionId(0, 0), RegionId(1, 1)])
            data = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(data["seed"], 7)
        self.assertEqual(len(data["regions"]), 2)
        self.assertEqual(data["regions"][0]["upper_trigram"], "坤")


if __name__ == "__main__":
    unittest.main()
