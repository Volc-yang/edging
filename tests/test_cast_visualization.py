import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_visualization import (
    export_cast_visual_bundle,
    grid_side,
    load_cast_model,
    render_cast_debug_atlas,
    render_change_count_heatmap,
    render_single_cast_card,
    summarize_change_counts,
    trigram_parts,
)
from dayan import CastContext, cast_hexagram


class CastVisualizationTests(unittest.TestCase):
    def test_grid_side_requires_perfect_square(self):
        self.assertEqual(grid_side(256), 16)
        with self.assertRaises(ValueError):
            grid_side(255)

    def test_trigram_parts_split_upper_and_lower(self):
        upper, lower = trigram_parts(0b101110)
        self.assertEqual(upper, 0b101)
        self.assertEqual(lower, 0b110)

    def test_render_bundle_for_sample_model(self):
        sample_path = Path(__file__).resolve().parents[1] / "models" / "four_phase_4d_cast_1781927642799684000.json"
        model = load_cast_model(sample_path)

        self.assertEqual(model.count, 256)
        self.assertEqual(len(model.items[0].line_values_bottom_to_top), 6)

        atlas = render_cast_debug_atlas(model)
        heatmap = render_change_count_heatmap(model)

        self.assertGreater(atlas.size[0], 0)
        self.assertGreater(atlas.size[1], 0)
        self.assertGreater(heatmap.size[0], 0)
        self.assertGreater(heatmap.size[1], 0)

        summary = summarize_change_counts(model.items)
        self.assertEqual(sum(summary.values()), model.count)

    def test_export_bundle_writes_pngs(self):
        payload = {
            "seed": 1,
            "subject": "test",
            "dimension": "2*2",
            "count": 4,
            "items": [
                {
                    "index": index,
                    "coord": [index // 2, index % 2],
                    "primary_value": index,
                    "primary_name": f"p{index}",
                    "changed_value": index ^ 1,
                    "changed_name": f"c{index}",
                    "changing_positions": [1] if index % 2 else [],
                    "line_values_bottom_to_top": [7, 8, 7, 8, 7, 8],
                }
                for index in range(4)
            ],
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            json_path = Path(tmpdir) / "sample.json"
            json_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

            outputs = export_cast_visual_bundle(json_path)

            self.assertTrue(outputs["atlas"].exists())
            self.assertTrue(outputs["changes"].exists())

    def test_render_single_cast_card(self):
        result = cast_hexagram(CastContext(seed=20260620, subject="single-card"))
        image = render_single_cast_card(
            primary=result.primary,
            changed=result.changed,
            line_values=[line.value for line in result.lines],
            changing_positions=result.changing_positions,
            seed=20260620,
            subject="single-card",
        )

        self.assertGreater(image.size[0], 0)
        self.assertGreater(image.size[1], 0)


if __name__ == "__main__":
    unittest.main()
