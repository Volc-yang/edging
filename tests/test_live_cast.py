import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from live_cast import LiveCastEngine, LiveCastLayout


class LiveCastTests(unittest.TestCase):
    def test_layouts_emit_expected_sample_counts(self):
        engine = LiveCastEngine(seed=20260620, subject="live-test")

        one_d = engine.frame(0, LiveCastLayout.ONE_D)
        two_d = engine.frame(0, LiveCastLayout.TWO_D)
        three_d = engine.frame(0, LiveCastLayout.THREE_D)

        self.assertEqual(one_d.count, 64)
        self.assertEqual(two_d.count, 64)
        self.assertEqual(three_d.count, 64)
        self.assertTrue(all(len(item.coord) == 1 for item in one_d.items))
        self.assertTrue(all(len(item.coord) == 2 for item in two_d.items))
        self.assertTrue(all(len(item.coord) == 3 for item in three_d.items))

    def test_frame_index_uses_hundred_hz_clock(self):
        engine = LiveCastEngine(seed=7, fps=100)

        self.assertEqual(engine.frame_index_for_elapsed(0.0), 0)
        self.assertEqual(engine.frame_index_for_elapsed(0.009), 0)
        self.assertEqual(engine.frame_index_for_elapsed(0.010), 1)
        self.assertEqual(engine.frame_index_for_elapsed(1.234), 123)

    def test_frames_change_over_time(self):
        engine = LiveCastEngine(seed=99, subject="motion")

        first = engine.frame(0, LiveCastLayout.TWO_D)
        second = engine.frame(1, LiveCastLayout.TWO_D)

        first_values = [item.primary_value for item in first.items]
        second_values = [item.primary_value for item in second.items]
        self.assertNotEqual(first_values, second_values)

    def test_frame_for_elapsed_matches_frame_index(self):
        engine = LiveCastEngine(seed=11, fps=100)

        frame = engine.frame_for_elapsed(0.157, LiveCastLayout.THREE_D)
        self.assertEqual(frame.frame_index, 15)
        self.assertEqual(frame.layout, LiveCastLayout.THREE_D)


if __name__ == "__main__":
    unittest.main()
