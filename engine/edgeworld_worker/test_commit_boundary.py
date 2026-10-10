"""Focused fault injection for the worker's manifest replacement boundary.

Run with the worker's isolated Genesis environment:
    python engine/edgeworld_worker/test_commit_boundary.py
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import worker as worker_module


class ManifestCommitBoundaryChecks(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory(prefix="edgeworld-worker-fault-")
        self.root = Path(self.tempdir.name)
        self.world_id = "fault-probe"
        self.request = {
            "protocol_version": 1,
            "request_id": "advance-1",
            "operation": "advance",
            "world_id": self.world_id,
            "expected_revision": 0,
            "target_tick": 1,
            "command_id": "cmd-1",
        }

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _worker(self, label: str) -> worker_module.Worker:
        return worker_module.Worker(self.root / label, self.world_id, physical_steps=1)

    def test_replace_error_fail_stops_and_restart_uses_visible_old_manifest(self) -> None:
        worker = self._worker("replace")
        original_replace = worker_module.os.replace

        def fail_manifest_replace(source, destination):
            if Path(destination) == worker.manifest_path:
                raise OSError("injected manifest replace failure")
            return original_replace(source, destination)

        with patch.object(worker_module.os, "replace", side_effect=fail_manifest_replace):
            response = worker.handle(self.request)

        self.assertEqual(response["error"]["code"], "commit_status_uncertain")
        self.assertNotIn("head", response["error"])
        self.assertEqual(worker.manifest["logical_tick"], 0)
        self.assertEqual(json.loads(worker.manifest_path.read_text())["logical_tick"], 0)
        stopped = worker.handle({
            "protocol_version": 1, "request_id": "status", "operation": "status", "world_id": self.world_id,
        })
        self.assertEqual(stopped["error"]["code"], "worker_stopped")
        recovered = worker_module.Worker(worker.state_dir, self.world_id, physical_steps=1)
        self.assertEqual(recovered.manifest["logical_tick"], 0)

    def test_directory_fsync_error_fail_stops_and_restart_validates_visible_new_manifest(self) -> None:
        worker = self._worker("fsync")
        original_fsync_dir = worker._fsync_dir

        def fail_after_manifest_directory_sync(path: Path) -> None:
            original_fsync_dir(path)
            if Path(path) == worker.state_dir:
                raise OSError("injected directory fsync failure after replace")

        with patch.object(worker, "_fsync_dir", side_effect=fail_after_manifest_directory_sync):
            response = worker.handle(self.request)

        self.assertEqual(response["error"]["code"], "commit_status_uncertain")
        self.assertNotIn("head", response["error"])
        self.assertEqual(worker.manifest["logical_tick"], 0)
        self.assertEqual(json.loads(worker.manifest_path.read_text())["logical_tick"], 1)
        stopped = worker.handle({
            "protocol_version": 1, "request_id": "status", "operation": "status", "world_id": self.world_id,
        })
        self.assertEqual(stopped["error"]["code"], "worker_stopped")
        recovered = worker_module.Worker(worker.state_dir, self.world_id, physical_steps=1)
        self.assertEqual(recovered.manifest["logical_tick"], 1)


if __name__ == "__main__":
    unittest.main()
