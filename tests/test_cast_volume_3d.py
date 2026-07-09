import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_volume_3d import (
    generate_cast_volume_3d,
    save_cast_volume_3d_outputs,
    volume_to_preview_payload,
)


class CastVolume3DTests(unittest.TestCase):
    def test_generate_cast_volume_3d_has_expected_shape(self):
        volume = generate_cast_volume_3d(width=3, height=2, depth=2, seed=20260627, subject="shape")

        self.assertEqual(volume.width, 3)
        self.assertEqual(volume.height, 2)
        self.assertEqual(volume.depth, 2)
        self.assertEqual(volume.count, 12)
        self.assertEqual(volume.dimension, "2*2*3")
        self.assertEqual(len(volume.items), 12)
        self.assertEqual(volume.items[0].coord, (0, 0, 0))
        self.assertEqual(volume.items[-1].coord, (1, 1, 2))
        self.assertEqual(len(volume.primary_volume), 2)
        self.assertEqual(len(volume.primary_volume[0]), 2)
        self.assertEqual(len(volume.primary_volume[0][0]), 3)

    def test_generate_cast_volume_3d_is_deterministic(self):
        first = generate_cast_volume_3d(width=4, height=4, depth=4, seed=88, subject="same")
        second = generate_cast_volume_3d(width=4, height=4, depth=4, seed=88, subject="same")

        self.assertEqual(first.items, second.items)
        self.assertEqual(first.primary_volume, second.primary_volume)
        self.assertEqual(first.changed_volume, second.changed_volume)

    def test_preview_payload_is_preview_compatible(self):
        volume = generate_cast_volume_3d(width=2, height=2, depth=2, seed=9, subject="payload")
        payload = volume_to_preview_payload(volume)

        self.assertEqual(payload["layout"], "3d")
        self.assertEqual(payload["dimension"], "2*2*2")
        self.assertEqual(payload["count"], 8)
        self.assertEqual(len(payload["items"]), 8)
        self.assertIn("primary_volume", payload)
        self.assertIn("changed_volume", payload)

    def test_save_outputs_writes_preview_and_matrix_json(self):
        volume = generate_cast_volume_3d(width=2, height=2, depth=2, seed=10, subject="save")
        with tempfile.TemporaryDirectory() as tmpdir:
            preview_path = Path(tmpdir) / "preview.json"
            primary_path = Path(tmpdir) / "primary.json"
            changed_path = Path(tmpdir) / "changed.json"

            save_cast_volume_3d_outputs(
                volume,
                preview_path=preview_path,
                primary_path=primary_path,
                changed_path=changed_path,
            )

            preview = json.loads(preview_path.read_text(encoding="utf-8"))
            primary = json.loads(primary_path.read_text(encoding="utf-8"))
            changed = json.loads(changed_path.read_text(encoding="utf-8"))

        self.assertEqual(preview["count"], 8)
        self.assertEqual(preview["primary_volume"][0][0][0], volume.primary_volume[0][0][0])
        self.assertEqual(primary["kind"], "primary")
        self.assertEqual(changed["kind"], "changed")
        self.assertEqual(primary["volume"], json.loads(json.dumps(volume.primary_volume)))
        self.assertEqual(changed["volume"], json.loads(json.dumps(volume.changed_volume)))


if __name__ == "__main__":
    unittest.main()
