import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_godot_ue5_parity import run_and_parse


class ParityToolTests(unittest.TestCase):
    def test_run_and_parse_reads_validation_marker_from_file_capture(self):
        marker = (
            "EDGEWORLD_TEST schema=edgeworld.chapter-one-snapshot.v2 spirits=8 "
            "primary=噬嗑 changed=履 houtian=thunder/E/3"
        )
        parsed = run_and_parse(
            "fixture",
            [sys.executable, "-c", f"print({marker!r})"],
            os.environ.copy(),
        )
        self.assertEqual(parsed["primary"], "噬嗑")
        self.assertEqual(parsed["changed"], "履")
        self.assertEqual(parsed["spirits"], 8)
        self.assertEqual(parsed["number"], 3)


if __name__ == "__main__":
    unittest.main()
