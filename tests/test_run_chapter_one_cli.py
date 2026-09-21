import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from run_chapter_one import next_tick_from_snapshot


class ChapterOneCliTickTests(unittest.TestCase):
    def test_missing_snapshot_starts_at_first_tick(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(next_tick_from_snapshot(Path(directory) / "missing.json"), 1)

    def test_existing_v2_snapshot_advances_one_tick(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text(
                json.dumps({"schema_version": "edgeworld.chapter-one-snapshot.v2", "tick": 7}),
                encoding="utf-8",
            )
            self.assertEqual(next_tick_from_snapshot(path), 8)

    def test_invalid_snapshot_does_not_silently_reset_world_time(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "snapshot.json"
            path.write_text("not-json", encoding="utf-8")
            with self.assertRaises(ValueError):
                next_tick_from_snapshot(path)


if __name__ == "__main__":
    unittest.main()
