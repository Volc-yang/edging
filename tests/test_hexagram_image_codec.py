import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from hexagram_image_codec import (
    decode_hexagram_argb_png,
    decode_hexagram_png,
    encode_cast_pair_argb_pngs,
    encode_hexagram_argb_png,
    encode_hexagram_png,
    pack_four_hexagrams_to_argb,
    pack_four_hexagrams_to_rgb,
    unpack_argb_to_four_hexagrams,
    unpack_rgb_to_four_hexagrams,
)


class HexagramImageCodecTests(unittest.TestCase):
    def test_four_six_bit_hexagrams_pack_into_one_rgb_pixel(self):
        hexagrams = (0, 1, 62, 63)

        pixel = pack_four_hexagrams_to_rgb(hexagrams)

        self.assertEqual(pixel, (0x00, 0x1F, 0xBF))
        self.assertEqual(unpack_rgb_to_four_hexagrams(pixel), hexagrams)

    def test_256_hexagrams_round_trip_through_png(self):
        hexagrams = tuple((index * 37 + 11) % 64 for index in range(256))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "cast_block.png"

            encode_hexagram_png(hexagrams, path, width=8)
            decoded = decode_hexagram_png(path, count=256)

        self.assertEqual(decoded, hexagrams)

    def test_four_six_bit_hexagrams_pack_into_one_argb_pixel_with_high_alignment(self):
        hexagrams = (0, 1, 62, 63)

        pixel = pack_four_hexagrams_to_argb(hexagrams)

        self.assertEqual(pixel, (0x00, 0x04, 0xF8, 0xFC))
        self.assertEqual(unpack_argb_to_four_hexagrams(pixel), hexagrams)

    def test_256_hexagrams_round_trip_through_argb_png(self):
        hexagrams = tuple((index * 19 + 7) % 64 for index in range(256))
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "cast_argb.png"

            encode_hexagram_argb_png(hexagrams, path, width=8, height=8)
            decoded = decode_hexagram_argb_png(path, count=256)

        self.assertEqual(decoded, hexagrams)

    def test_primary_and_changed_hexagrams_encode_to_dual_argb_pngs(self):
        primary = tuple((index * 5 + 3) % 64 for index in range(64))
        changed = tuple((index * 7 + 9) % 64 for index in range(64))
        with tempfile.TemporaryDirectory() as tmpdir:
            primary_path = Path(tmpdir) / "primary.png"
            changed_path = Path(tmpdir) / "changed.png"

            encode_cast_pair_argb_pngs(
                primary,
                changed,
                primary_path=primary_path,
                changed_path=changed_path,
                width=4,
                height=4,
            )

            decoded_primary = decode_hexagram_argb_png(primary_path, count=64)
            decoded_changed = decode_hexagram_argb_png(changed_path, count=64)

        self.assertEqual(decoded_primary, primary)
        self.assertEqual(decoded_changed, changed)

    def test_rejects_non_256_count_for_8_by_8_block(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad.png"
            with self.assertRaises(ValueError):
                encode_hexagram_png(tuple(range(63)), path, width=8)

    def test_rejects_argb_size_mismatch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "bad_argb.png"
            with self.assertRaises(ValueError):
                encode_hexagram_argb_png(tuple(range(64)), path, width=8, height=8)


if __name__ == "__main__":
    unittest.main()
