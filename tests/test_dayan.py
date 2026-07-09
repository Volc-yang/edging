import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from dayan import (
    CastContext,
    cast_change,
    cast_hexagram,
    cast_hexagram_batch_fast,
    cast_hexagram_batch_numpy,
    cast_hexagram_fast,
    line_value_to_phase_code,
    phase_code_to_line_value,
    line_values_to_changed_value,
    line_values_to_primary_value,
    cast_line,
    hexagram_stalk_total,
    line_stalk_count,
)


class DayanCastingTests(unittest.TestCase):
    def test_first_change_removes_five_or_nine_and_keeps_three_talies(self):
        context = CastContext(seed=20260620, subject="first-change")

        result = cast_change(49, context, change_index=0)

        self.assertIn(result.removed_count, (5, 9))
        self.assertEqual(result.human_token, 1)
        self.assertIn(result.left_remainder, (1, 2, 3, 4))
        self.assertIn(result.right_remainder, (1, 2, 3, 4))
        self.assertEqual(
            result.removed_count,
            result.human_token + result.left_remainder + result.right_remainder,
        )
        self.assertEqual(result.remaining_count, 49 - result.removed_count)

    def test_later_changes_remove_four_or_eight(self):
        context = CastContext(seed=20260620, subject="later-change")

        first = cast_change(49, context, change_index=0)
        second = cast_change(first.remaining_count, context, change_index=1)
        third = cast_change(second.remaining_count, context, change_index=2)

        self.assertIn(second.removed_count, (4, 8))
        self.assertIn(third.removed_count, (4, 8))

    def test_three_changes_produce_one_line_value(self):
        line = cast_line(CastContext(seed=7, subject="line"), line_index=0)

        self.assertEqual(len(line.changes), 3)
        self.assertIn(line.value, (6, 7, 8, 9))
        self.assertEqual(line.remaining_count, line.value * 4)
        self.assertEqual(line.is_yang, line.value in (7, 9))
        self.assertEqual(line.is_changing, line.value in (6, 9))

    def test_six_lines_produce_hexagram_and_changed_hexagram(self):
        result = cast_hexagram(CastContext(seed=7, subject="hexagram"))

        self.assertEqual(len(result.lines), 6)
        self.assertGreaterEqual(result.primary.value, 0)
        self.assertLessEqual(result.primary.value, 63)
        self.assertGreaterEqual(result.changed.value, 0)
        self.assertLessEqual(result.changed.value, 63)
        self.assertEqual(
            result.changing_positions,
            [index + 1 for index, line in enumerate(result.lines) if line.is_changing],
        )
        self.assertEqual(result.changed.value, result.primary.change(result.changing_positions).value)

    def test_casting_is_deterministic_for_same_context(self):
        context = CastContext(seed=99, subject="same")

        first = cast_hexagram(context)
        second = cast_hexagram(context)

        self.assertEqual(first.primary.value, second.primary.value)
        self.assertEqual(first.changed.value, second.changed.value)
        self.assertEqual([line.value for line in first.lines], [line.value for line in second.lines])

    def test_line_stalk_count_maps_four_line_values(self):
        self.assertEqual(line_stalk_count(6), 24)
        self.assertEqual(line_stalk_count(7), 28)
        self.assertEqual(line_stalk_count(8), 32)
        self.assertEqual(line_stalk_count(9), 36)

    def test_line_values_map_to_updated_four_phase_codes(self):
        self.assertEqual(line_value_to_phase_code(6), 0)  # 太阴
        self.assertEqual(line_value_to_phase_code(7), 1)  # 少阳
        self.assertEqual(line_value_to_phase_code(8), 2)  # 少阴
        self.assertEqual(line_value_to_phase_code(9), 3)  # 太阳
        self.assertEqual(phase_code_to_line_value(0), 6)
        self.assertEqual(phase_code_to_line_value(1), 7)
        self.assertEqual(phase_code_to_line_value(2), 8)
        self.assertEqual(phase_code_to_line_value(3), 9)

    def test_all_four_phase_line_combinations_form_primary_and_changed_hexagrams(self):
        phase_to_line = {0: 6, 1: 7, 2: 8, 3: 9}
        for raw in range(4 ** 6):
            phase_codes = []
            value = raw
            for _ in range(6):
                phase_codes.append(value % 4)
                value //= 4
            line_values = tuple(phase_to_line[phase_code] for phase_code in phase_codes)

            expected_primary = sum((1 if phase_code in (1, 3) else 0) << index for index, phase_code in enumerate(phase_codes))
            expected_changed = sum((1 if phase_code in (0, 1) else 0) << index for index, phase_code in enumerate(phase_codes))

            self.assertEqual(line_values_to_primary_value(line_values), expected_primary)
            self.assertEqual(line_values_to_changed_value(line_values), expected_changed)

    def test_qian_and_kun_stalk_totals_match_traditional_numbers(self):
        qian_line_values = [9, 9, 9, 9, 9, 9]
        kun_line_values = [6, 6, 6, 6, 6, 6]

        self.assertEqual(hexagram_stalk_total(qian_line_values), 216)
        self.assertEqual(hexagram_stalk_total(kun_line_values), 144)
        self.assertEqual(
            hexagram_stalk_total(qian_line_values) + hexagram_stalk_total(kun_line_values),
            360,
        )

    def test_one_hexagram_uses_eighteen_random_splits(self):
        result = cast_hexagram(CastContext(seed=7, subject="split-count"))

        self.assertEqual(sum(len(line.changes) for line in result.lines), 18)

    def test_fast_cast_matches_full_cast_values(self):
        context = CastContext(seed=12345, subject="fast-match")

        full = cast_hexagram(context)
        fast = cast_hexagram_fast(context)

        self.assertEqual(fast.primary_value, full.primary.value)
        self.assertEqual(fast.changed_value, full.changed.value)
        self.assertEqual(fast.line_values, tuple(line.value for line in full.lines))
        self.assertEqual(fast.changing_positions, tuple(full.changing_positions))

    def test_batch_fast_cast_matches_point_fast_casts(self):
        batch = cast_hexagram_batch_fast(seed=5000, subject="batch", count=256)
        points = [cast_hexagram_fast(CastContext(seed=5000 + index, subject="batch")) for index in range(256)]

        self.assertEqual(batch.primary_values, tuple(point.primary_value for point in points))
        self.assertEqual(batch.changed_values, tuple(point.changed_value for point in points))
        self.assertEqual(batch.line_values, tuple(point.line_values for point in points))
        self.assertEqual(batch.changing_positions, tuple(point.changing_positions for point in points))

    def test_numpy_batch_cast_matches_batch_fast_cast(self):
        expected = cast_hexagram_batch_fast(seed=8000, subject="numpy-batch", count=256)
        actual = cast_hexagram_batch_numpy(seed=8000, subject="numpy-batch", count=256)

        self.assertEqual(actual.primary_values, expected.primary_values)
        self.assertEqual(actual.changed_values, expected.changed_values)
        self.assertEqual(actual.line_values, expected.line_values)
        self.assertEqual(actual.changing_positions, expected.changing_positions)


if __name__ == "__main__":
    unittest.main()
