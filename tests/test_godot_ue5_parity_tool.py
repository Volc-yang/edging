import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from validate_godot_ue5_parity import run_and_parse

#: The UE5 project lives outside this repository (external SSD), so any check
#: against it has to tolerate the volume being unmounted.
UE5_READER = Path("/Volumes/DevSSD/Unreal/Projects/EdgeWorldUE/Source/EdgeWorldUE/ChapterOneSnapshot.cpp")


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


class SnapshotRedirectionContractTests(unittest.TestCase):
    """Every consumer must resolve the snapshot through the shared variable.

    Regression guard: the Godot frontend used to read a hardcoded
    project-relative path, so ``validate_godot_ue5_parity.py --snapshot``
    redirected UE5 but not Godot and reported a misleading "mismatch".
    """

    def setUp(self):
        self.godot_script = (ROOT / "engine_platforms" / "godot" / "chapter_one.gd").read_text(encoding="utf-8")
        self.parity_tool = (ROOT / "tools" / "validate_godot_ue5_parity.py").read_text(encoding="utf-8")

    def test_godot_honours_the_shared_snapshot_variable(self):
        self.assertIn("EDGEWORLD_CHAPTER_ONE_JSON", self.godot_script)
        self.assertIn("OS.get_environment(", self.godot_script)

    def test_godot_writes_back_to_the_same_snapshot_it_reads(self):
        self.assertIn('"--output", snapshot_path()', self.godot_script)

    def test_godot_prefers_the_project_virtualenv(self):
        self.assertIn(".venv/bin/python", self.godot_script)

    def test_parity_tool_publishes_the_shared_variable(self):
        self.assertIn('environment["EDGEWORLD_CHAPTER_ONE_JSON"]', self.parity_tool)

    @unittest.skipUnless(UE5_READER.exists(), "the UE5 project is not mounted")
    def test_ue5_consumes_the_same_variable(self):
        ue5_source = UE5_READER.read_text(encoding="utf-8", errors="replace")
        self.assertIn("EDGEWORLD_CHAPTER_ONE_JSON", ue5_source)


if __name__ == "__main__":
    unittest.main()
