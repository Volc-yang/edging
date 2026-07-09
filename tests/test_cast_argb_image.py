import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_argb_image import CHANNEL_NAMES, generate_cast_argb_image, save_cast_argb_image_pair
from hexagram_image_codec import decode_hexagram_argb_png


class CastArgbImageTests(unittest.TestCase):
    def test_generate_cast_argb_image_has_expected_shape(self):
        image = generate_cast_argb_image(width=3, height=2, seed=20260627, subject="shape")

        self.assertEqual(image.width, 3)
        self.assertEqual(image.height, 2)
        self.assertEqual(len(image.primary_hexagrams), 3 * 2 * 4)
        self.assertEqual(len(image.changed_hexagrams), 3 * 2 * 4)
        self.assertEqual(len(image.samples), 3 * 2 * 4)
        self.assertEqual(tuple(sample.channel_name for sample in image.samples[:4]), CHANNEL_NAMES)

    def test_generate_cast_argb_image_is_deterministic(self):
        first = generate_cast_argb_image(width=4, height=4, seed=77, subject="same")
        second = generate_cast_argb_image(width=4, height=4, seed=77, subject="same")

        self.assertEqual(first.primary_hexagrams, second.primary_hexagrams)
        self.assertEqual(first.changed_hexagrams, second.changed_hexagrams)
        self.assertEqual(first.samples, second.samples)

    def test_different_coordinates_produce_nontrivial_variation(self):
        image = generate_cast_argb_image(width=4, height=4, seed=99, subject="variation")

        self.assertGreater(len(set(image.primary_hexagrams)), 8)
        self.assertGreater(len(set(image.changed_hexagrams)), 8)

    def test_save_cast_argb_image_pair_round_trips(self):
        image = generate_cast_argb_image(width=4, height=4, seed=101, subject="roundtrip")
        with tempfile.TemporaryDirectory() as tmpdir:
            primary_path = Path(tmpdir) / "primary.png"
            changed_path = Path(tmpdir) / "changed.png"

            save_cast_argb_image_pair(image, primary_path, changed_path)

            decoded_primary = decode_hexagram_argb_png(primary_path, count=4 * 4 * 4)
            decoded_changed = decode_hexagram_argb_png(changed_path, count=4 * 4 * 4)

        self.assertEqual(decoded_primary, image.primary_hexagrams)
        self.assertEqual(decoded_changed, image.changed_hexagrams)


if __name__ == "__main__":
    unittest.main()
