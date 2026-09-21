"""Tests for the append-only Chapter One round history (risk R5)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from chapter_one_history import (
    HISTORY_SCHEMA_VERSION,
    ChapterOneHistory,
    migrate_payload,
    register_migration,
)
from snapshot_store import SNAPSHOT_SCHEMA_VERSION, SnapshotError


def round_snapshot(tick, score=0.9, encounter="无妄", changed="讼"):
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "tick": tick,
        "chapter": "第一章·万物有灵",
        "decision": {"source": "rule_fallback"},
        "validation": {"score": score},
        "encounter": {
            "primary_hexagram": {"name": encounter},
            "changed_hexagram": {"name": changed},
        },
    }


class ChapterOneHistoryTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.models = Path(self._tmp.name)
        self.history = ChapterOneHistory(self.models)

    def _seed(self, ticks=3):
        for tick in range(1, ticks + 1):
            self.history.append(round_snapshot(tick, encounter=f"卦{tick}"), source="test")

    # ------------------------------------------------------------- recording
    def test_append_creates_round_file_and_index_entry(self):
        entry = self.history.append(round_snapshot(1), source="godot")
        self.assertEqual(1, entry["tick"])
        self.assertTrue((self.history.history_dir / entry["file"]).exists())
        self.assertEqual([1], self.history.replay_ticks())
        self.assertEqual("godot", self.history.entries()[0]["source"])

    def test_append_is_idempotent_per_tick(self):
        first = self.history.append(round_snapshot(1, encounter="乾"))
        second = self.history.append(round_snapshot(1, encounter="坤"))
        self.assertEqual(first["sha256"], second["sha256"])
        self.assertEqual(1, len(self.history.entries()))
        # The archive stays immutable: the original round wins.
        self.assertEqual("乾", self.history.load(1)["encounter"]["primary_hexagram"]["name"])

    def test_rounds_are_swappable_by_tick(self):
        self._seed(3)
        self.assertEqual([1, 2, 3], self.history.replay_ticks())
        self.assertEqual("卦2", self.history.load(2)["encounter"]["primary_hexagram"]["name"])
        with self.assertRaises(SnapshotError):
            self.history.load(99)

    def test_iter_rounds_replays_in_order(self):
        self._seed(3)
        self.assertEqual([1, 2, 3], [r["tick"] for r in self.history.iter_rounds()])

    def test_rejects_snapshot_without_positive_tick(self):
        for bad in (0, -3, "2", None):
            with self.subTest(tick=bad):
                with self.assertRaises(SnapshotError):
                    self.history.append({"schema_version": SNAPSHOT_SCHEMA_VERSION, "tick": bad})

    # ------------------------------------------------------------- integrity
    def test_verify_accepts_an_untouched_chain(self):
        self._seed(4)
        report = self.history.verify()
        self.assertTrue(report["ok"], report["problems"])
        self.assertEqual(4, report["rounds"])

    def test_verify_detects_a_modified_round_file(self):
        self._seed(3)
        target = self.history.rounds_dir / "tick-000002.json"
        payload = json.loads(target.read_text(encoding="utf-8"))
        payload["snapshot"]["validation"]["score"] = 0.0
        target.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        report = self.history.verify()
        self.assertFalse(report["ok"])
        self.assertTrue(any("tick 2" in p and "modified" in p for p in report["problems"]), report["problems"])

    def test_verify_detects_a_broken_chain_link(self):
        self._seed(3)
        index = json.loads(self.history.index_path.read_text(encoding="utf-8"))
        del index["entries"][1]  # drop the middle round from the manifest
        self.history.index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

        report = self.history.verify()
        self.assertFalse(report["ok"])
        self.assertTrue(any("chain link broken" in p for p in report["problems"]), report["problems"])
        self.assertTrue(any("orphan" in p for p in report["problems"]), report["problems"])

    def test_verify_detects_a_deleted_round_file(self):
        self._seed(2)
        (self.history.rounds_dir / "tick-000001.json").unlink()
        report = self.history.verify()
        self.assertFalse(report["ok"])
        self.assertTrue(any("missing" in p for p in report["problems"]), report["problems"])

    def test_index_schema_is_versioned(self):
        self._seed(1)
        index = json.loads(self.history.index_path.read_text(encoding="utf-8"))
        self.assertEqual(HISTORY_SCHEMA_VERSION, index["schema_version"])

    # ------------------------------------------------------------- migration
    def test_unregistered_schema_migration_is_refused(self):
        with self.assertRaises(SnapshotError) as ctx:
            migrate_payload({"schema_version": "edgeworld.unknown.v0"}, SNAPSHOT_SCHEMA_VERSION)
        self.assertIn("no migration registered", str(ctx.exception))

    def test_registered_migration_upgrades_a_round(self):
        legacy_schema = "edgeworld.chapter-one-snapshot.test-legacy"

        def upgrade(payload):
            migrated = dict(payload)
            migrated["migrated_from_legacy"] = True
            return migrated

        register_migration(legacy_schema, SNAPSHOT_SCHEMA_VERSION, upgrade)
        self.addCleanup(lambda: __import__("chapter_one_history")._MIGRATIONS.pop(legacy_schema, None))

        migrated = migrate_payload({"schema_version": legacy_schema, "tick": 5}, SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(SNAPSHOT_SCHEMA_VERSION, migrated["schema_version"])
        self.assertEqual(5, migrated["tick"])
        self.assertTrue(migrated["migrated_from_legacy"])

    def test_migrate_round_uses_the_live_archive(self):
        self._seed(2)
        # The archived rounds are already v2, so migrating to v2 is a no-op.
        migrated = self.history.migrate_round(1, SNAPSHOT_SCHEMA_VERSION)
        self.assertEqual(SNAPSHOT_SCHEMA_VERSION, migrated["schema_version"])
        self.assertEqual(1, migrated["tick"])


if __name__ == "__main__":
    unittest.main()
