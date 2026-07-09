import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from mathEdge import Hexagram


class YijingTextTests(unittest.TestCase):
    def test_text_data_uses_upper_then_lower_trigram_key(self):
        tun = Hexagram.from_trigrams(0b010, 0b100)
        xiaoxu = Hexagram.from_trigrams(0b011, 0b111)

        self.assertEqual(tun.text_key, "010100")
        self.assertEqual(tun.name, "屯")
        self.assertEqual(xiaoxu.text_key, "011111")
        self.assertEqual(xiaoxu.name, "小畜")

    def test_all_sixty_four_hexagrams_have_names(self):
        missing = [value for value in range(64) if Hexagram(value).name is None]

        self.assertEqual(missing, [])

    def test_acceptance_cast_hexagrams_have_expected_names(self):
        guan = Hexagram.from_trigrams(0b011, 0b000)
        jin = Hexagram.from_trigrams(0b101, 0b000)

        self.assertEqual(guan.name, "观")
        self.assertEqual(jin.name, "晋")

    def test_qian_and_kun_names_remain_stable(self):
        self.assertEqual(Hexagram.from_trigrams(0b111, 0b111).name, "乾")
        self.assertEqual(Hexagram.from_trigrams(0b000, 0b000).name, "坤")


if __name__ == "__main__":
    unittest.main()
