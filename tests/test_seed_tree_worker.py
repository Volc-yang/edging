"""Contract tests for the separate deterministic Seed/tree JSONL worker."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ENGINE_DIR = REPO_ROOT / "engine"
WORKER_SCRIPT = ENGINE_DIR / "edgeworld_worker" / "tree_worker.py"
sys.path.insert(0, str(ENGINE_DIR))

from evolution_4d import EXPERIMENTAL_SEED_TREE_RULE_VERSION  # noqa: E402
from edgeworld_worker.tree_worker import Worker  # noqa: E402


def advance_request(tick: int, *, command_id: str | None = None,
                    moisture: float = 0.9, light: float = 0.9,
                    phase: str = "taiyang", world_id: str = "world-seed-tree") -> dict:
    return {
        "protocol_version": 1,
        "request_id": f"advance-request-{tick}",
        "operation": "advance",
        "world_id": world_id,
        "expected_revision": tick - 1,
        "target_tick": tick,
        "command_id": command_id or f"advance-{tick}",
        "environment": {"phase": phase, "moisture": moisture, "light": light},
    }


def observe_request(tick: int, watermark: int | None = None,
                    world_id: str = "world-seed-tree") -> dict:
    return {
        "protocol_version": 1,
        "request_id": f"observe-request-{tick}",
        "operation": "observe",
        "world_id": world_id,
        "logical_tick": tick,
        "view_spec": {
            "watermark": tick if watermark is None else watermark,
            "region": "single-tree-world",
            "observer": "ue-default-camera-v1",
            "resolution": "single-tree-proxy-v1",
            "error_budget": {"semantic_state": "exact", "visual_geometry": "unmeasured-proxy"},
            "rules": {"evolution": EXPERIMENTAL_SEED_TREE_RULE_VERSION,
                      "projection": "stylized-tree-ue-v1"},
        },
    }


class SeedTreeWorkerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state_dir = Path(self.temp.name)
        self.worker = Worker(self.state_dir, "world-seed-tree", seed=7)

    @staticmethod
    def result(response: dict) -> dict:
        if not response.get("ok"):
            raise AssertionError(response)
        return response["result"]

    @staticmethod
    def error_code(response: dict) -> str:
        if response.get("ok"):
            raise AssertionError(response)
        return response["error"]["code"]

    def test_seed_to_mature_exact_tick_sample_schema_and_watermarks(self) -> None:
        initial = self.result(self.worker.handle({
            "protocol_version": 1, "request_id": "status-0", "operation": "status",
            "world_id": "world-seed-tree",
        }))
        self.assertEqual(initial["logical_tick"], 0)
        before = self.result(self.worker.handle(observe_request(0)))
        self.assertEqual(before["sample"]["stage"], "seed")
        self.assertIsNone(before["sample"]["tree_id"])
        self.assertIsNone(before["sample"]["phase"])

        for tick in range(1, 9):
            self.result(self.worker.handle(advance_request(tick)))
        seedling = self.result(self.worker.handle(observe_request(1)))
        mature = self.result(self.worker.handle(observe_request(8)))
        self.assertEqual(seedling["sample"]["stage"], "seedling")
        self.assertEqual(mature["sample"]["stage"], "mature")
        self.assertEqual(mature["sample"]["tree_id"], seedling["sample"]["tree_id"])
        self.assertEqual(mature["sample"]["seed_id"], "seed-7")
        self.assertEqual(mature["sample"]["ruleset_version"], EXPERIMENTAL_SEED_TREE_RULE_VERSION)
        self.assertEqual(mature["projection_version"], "stylized-tree-ue-v1")
        self.assertEqual(mature["source_revision"], mature["watermark"])
        self.assertEqual(set(mature), {
            "world_id", "logical_tick", "source_revision", "watermark", "sample",
            "projection_version", "state_hash", "event_hash", "view_spec", "sample_hash",
            "event_head_hash",
        })
        self.assertEqual(set(mature["sample"]), {
            "seed_id", "tree_id", "stage", "health", "biomass", "water_reserve",
            "phase", "ruleset_version",
        })

    def test_advance_command_idempotency_conflict_and_revision_guard(self) -> None:
        request = advance_request(1, command_id="same-command")
        first = self.result(self.worker.handle(request))
        duplicate = dict(request, request_id="retry-with-new-request-id")
        second = self.result(self.worker.handle(duplicate))
        self.assertEqual(first, second)
        self.assertEqual(self.worker.manifest["logical_tick"], 1)

        conflict = advance_request(1, command_id="same-command", moisture=0.5)
        self.assertEqual(self.error_code(self.worker.handle(conflict)), "command_id_conflict")
        stale = advance_request(2)
        stale["expected_revision"] = 0
        self.assertEqual(self.error_code(self.worker.handle(stale)), "revision_conflict")
        self.assertEqual(self.worker.manifest["logical_tick"], 1)

    def test_environment_and_tick_gaps_are_rejected_without_commit(self) -> None:
        missing_environment = advance_request(1)
        del missing_environment["environment"]
        self.assertEqual(self.error_code(self.worker.handle(missing_environment)), "invalid_environment")
        invalid_environment = advance_request(1, moisture=1.2)
        self.assertEqual(self.error_code(self.worker.handle(invalid_environment)), "invalid_environment")
        skipped = advance_request(2)
        skipped["expected_revision"] = 0
        self.assertEqual(self.error_code(self.worker.handle(skipped)), "tick_sequence_error")
        self.assertEqual(self.worker.manifest["logical_tick"], 0)

    def test_observe_requires_exact_retained_tick_and_watermark_and_is_read_only(self) -> None:
        self.result(self.worker.handle(advance_request(1)))
        manifest_before = (self.state_dir / "tree_world.json").read_bytes()
        first = self.result(self.worker.handle(observe_request(0)))
        second = self.result(self.worker.handle(dict(observe_request(0), request_id="observe-again")))
        self.assertEqual(first, second)
        self.assertEqual((self.state_dir / "tree_world.json").read_bytes(), manifest_before)
        self.assertEqual(self.error_code(self.worker.handle(observe_request(0, watermark=1))), "watermark_mismatch")
        self.assertEqual(self.error_code(self.worker.handle(observe_request(99, watermark=99))), "history_missing")
        self.assertEqual(self.worker.manifest["logical_tick"], 1)

    def test_restart_recovers_history_and_replays_same_hashes(self) -> None:
        trace = []
        for tick in range(1, 9):
            result = self.result(self.worker.handle(advance_request(tick)))
            trace.append((result["head_state_hash"], result["event_head_hash"]))
        recovered = Worker(self.state_dir, "world-seed-tree", seed=7)
        self.assertEqual(recovered._head(), self.worker._head())
        continued = self.result(recovered.handle(advance_request(9)))

        with tempfile.TemporaryDirectory() as other_dir:
            replay = Worker(Path(other_dir), "world-seed-tree", seed=7)
            replay_trace = []
            for tick in range(1, 9):
                result = self.result(replay.handle(advance_request(tick)))
                replay_trace.append((result["head_state_hash"], result["event_head_hash"]))
            self.assertEqual(trace, replay_trace)
            replay_nine = self.result(replay.handle(advance_request(9)))
            self.assertEqual(continued["head_state_hash"], replay_nine["head_state_hash"])
            self.assertEqual(continued["event_head_hash"], replay_nine["event_head_hash"])
        for index, event in enumerate(recovered.manifest["events"]):
            self.assertEqual(event["logical_tick"], index)
            self.assertEqual(event["previous_event_hash"], "0" * 64 if index == 0 else recovered.manifest["events"][index - 1]["event_hash"])
            self.assertEqual(event["state_hash"], recovered.manifest["history"][index]["state_hash"])

    def test_launcher_compatibility_flags_are_accepted_and_ignored(self) -> None:
        command = [sys.executable, str(WORKER_SCRIPT), "--state-dir", str(self.state_dir / "cli"),
                   "--world-id", "cli-world", "--dt", "0.025", "--physical-steps", "3", "--seed", "9"]
        request = {"protocol_version": 1, "request_id": "cli-status", "operation": "status", "world_id": "cli-world"}
        completed = subprocess.run(command, input=json.dumps(request) + "\n", text=True,
                                   capture_output=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        response = json.loads(completed.stdout)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["result"]["logical_tick"], 0)
        manifest = json.loads((self.state_dir / "cli" / "tree_world.json").read_text())
        self.assertNotIn("dt", manifest["config"])
        self.assertNotIn("physical_steps", manifest["config"])


if __name__ == "__main__":
    unittest.main()
