"""Focused contract checks for the finite chaos origin authority."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from engine.chaos.origin_runtime import OriginError
from engine.chaos.origin_store import ManifestWriteFailure
from engine.chaos.origin_worker import Worker


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "doc" / "chaos_origin_contract.md"
GOLDEN = {
    "initial_manifest_hash": "75f6c3d719e9e0afefb64e582750cf9fcc70e932fe1192886abdc99e78d91da3",
    "state_hash_0": "e2030df396ae7f1f5c1466e475ac467d09daf397be52d3b983386402d88f3d0f",
    "spirit_id": "spirit-597eac36f6d6c494",
    "state_hash_1": "d6b6ec5b7543fe9dfa486708f4013425b4a63c9c734ec8da3720552c552cbb8c",
    "event_hash_1": "3b7a8899f219bde5207c2e754391b54c9212e56b04dece2b4acbb8aa4450548f",
}


def fixture() -> dict:
    blocks = re.findall(r"```json\n(.*?)\n```", CONTRACT.read_text(encoding="utf-8"), re.S)
    return json.loads(blocks[-1])


def request(operation: str, request_id: str, **fields) -> dict:
    return {"protocol_version": 1, "request_id": request_id, "operation": operation,
            "world_id": "chaos-demo", **fields}


def advance(request_id: str = "advance-req", command_id: str = "origin-o1", **fields) -> dict:
    return request("advance", request_id, command_id=command_id,
                   expected_revision=0, target_tick=1,
                   origin_action="reveal_world_spirit", **fields)


def observe(tick: int, watermark: int, request_id: str = "observe-req") -> dict:
    return request("observe", request_id, logical_tick=tick, view_spec={
        "watermark": watermark, "region": "origin-sample", "observer": "ue-camera-v1",
        "resolution": "chaos-proxy-v1",
        "error_budget": {"semantic_state": "exact", "visual_geometry": "proxy"},
        "rules": {"evolution": "chaos-o1-exp-v1", "projection": "chaos-ue-projection-exp-v1"},
    })


class ChaosOriginRuntimeTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state_dir = Path(self.temp.name) / "state"
        self.worker = Worker(self.state_dir, fixture(), world_id="chaos-demo", seed=7)

    def manifest_bytes(self) -> bytes:
        return (self.state_dir / "world.json").read_bytes()

    def test_golden_initial_and_o1_hashes(self) -> None:
        before = self.worker.handle(request("status", "status-0"))["result"]
        self.assertEqual(before["initial_manifest_hash"], GOLDEN["initial_manifest_hash"])
        self.assertEqual(before["state_hash"], GOLDEN["state_hash_0"])
        self.assertEqual((before["logical_tick"], before["phase"]), (0, "CHAOS"))
        result = self.worker.handle(advance())["result"]
        self.assertEqual(result["world_spirit_id"], GOLDEN["spirit_id"])
        self.assertEqual(result["state_hash"], GOLDEN["state_hash_1"])
        self.assertEqual(result["event_hash"], GOLDEN["event_hash_1"])
        self.assertEqual(len(self.worker.store.manifest["events"]), 1)

    def test_idempotency_conflict_and_phase_guard(self) -> None:
        first = self.worker.handle(advance())["result"]
        committed_bytes = self.manifest_bytes()
        repeated = self.worker.handle(advance(request_id="retry"))["result"]
        self.assertEqual(repeated, first)
        self.assertEqual(self.manifest_bytes(), committed_bytes)
        changed = advance(request_id="changed")
        changed["origin_action"] = "another_action"
        self.assertEqual(self.worker.handle(changed)["error"]["code"], "command_id_conflict")
        self.assertEqual(self.worker.handle(advance(command_id="second"))["error"]["code"], "revision_conflict")
        second = advance(command_id="second-valid-revision")
        second["expected_revision"] = 1
        self.assertEqual(self.worker.handle(second)["error"]["code"], "phase_conflict")
        self.assertEqual(self.manifest_bytes(), committed_bytes)

    def test_history_observe_is_exact_and_read_only(self) -> None:
        self.worker.handle(advance())
        committed_bytes = self.manifest_bytes()
        before_hash = hashlib.sha256(committed_bytes).hexdigest()
        zero = self.worker.handle(observe(0, 0))["result"]
        one = self.worker.handle(observe(1, 1))["result"]
        again = self.worker.handle(observe(1, 1, "again"))["result"]
        self.assertIsNone(zero["sample"]["world_spirit_id"])
        self.assertEqual(zero["sample"]["spirit_boundary_place_ids"], [])
        self.assertEqual(one["sample"]["spirit_boundary_place_ids"], one["sample"]["place_ids"])
        self.assertEqual(one, again)
        self.assertEqual(self.worker.handle(observe(0, 1))["error"]["code"], "watermark_mismatch")
        self.assertEqual(self.worker.handle(observe(2, 2))["error"]["code"], "history_missing")
        self.assertEqual(hashlib.sha256(self.manifest_bytes()).hexdigest(), before_hash)

    def test_restart_and_corruption_rejection(self) -> None:
        self.worker.handle(advance())
        restarted = Worker(self.state_dir, fixture(), world_id="chaos-demo", seed=7)
        self.assertEqual(restarted.handle(request("status", "status-1"))["result"]["state_hash"],
                         GOLDEN["state_hash_1"])
        self.assertEqual(restarted.handle(advance(request_id="retry"))["result"]["state_hash"],
                         GOLDEN["state_hash_1"])
        path = self.state_dir / "world.json"
        corrupted = json.loads(path.read_text())
        corrupted["events"][0]["cause_code"] = "fabricated"
        path.write_text(json.dumps(corrupted))
        with self.assertRaisesRegex(OriginError, "does not match O1 replay"):
            Worker(self.state_dir, fixture(), world_id="chaos-demo", seed=7)

    def test_initial_world_and_request_boundaries(self) -> None:
        changed = fixture()
        changed["places"][0]["potential"]["civilization"] = 0.5
        with self.assertRaisesRegex(OriginError, "finite safe integers"):
            Worker(Path(self.temp.name) / "bad", changed, world_id="chaos-demo")
        disconnected = fixture()
        disconnected["watercourses"][0]["polyline_cm"][-1] = [65000, 40000]
        with self.assertRaisesRegex(OriginError, "does not terminate in ocean"):
            Worker(Path(self.temp.name) / "disconnected", disconnected, world_id="chaos-demo")
        with self.assertRaisesRegex(OriginError, "seed differs"):
            Worker(Path(self.temp.name) / "wrong-seed", fixture(), world_id="chaos-demo", seed=8)
        before = self.manifest_bytes()
        self.assertEqual(self.worker.handle(request("status", "wrong-world", world_id="other"))["error"]["code"],
                         "world_mismatch")
        invalid_tick = advance(command_id="invalid")
        invalid_tick["target_tick"] = 2
        self.assertEqual(self.worker.handle(invalid_tick)["error"]["code"],
                         "invalid_target_tick")
        self.assertEqual(self.manifest_bytes(), before)

    def test_mkstemp_failure_is_pre_replacement_persistence_failure(self) -> None:
        initial_bytes = self.manifest_bytes()
        with mock.patch("engine.chaos.origin_store.tempfile.mkstemp", side_effect=OSError("disk full")):
            failed = self.worker.handle(advance())
        self.assertEqual(failed["error"]["code"], "persistence_failed")
        self.assertEqual(self.manifest_bytes(), initial_bytes)
        self.assertEqual(self.worker.handle(request("status", "after-disk-full"))["result"]["logical_tick"], 0)

    def test_commit_failures_do_not_claim_success(self) -> None:
        initial_bytes = self.manifest_bytes()
        with mock.patch.object(self.worker.store, "_write",
                               side_effect=ManifestWriteFailure(False, OSError("before replace"))):
            failed = self.worker.handle(advance())
        self.assertEqual(failed["error"]["code"], "persistence_failed")
        self.assertEqual(self.manifest_bytes(), initial_bytes)
        self.assertEqual(self.worker.handle(request("status", "still-zero"))["result"]["logical_tick"], 0)
        with mock.patch.object(self.worker.store, "_fsync_dir", side_effect=OSError("after replace")):
            uncertain = self.worker.handle(advance())
        self.assertEqual(uncertain["error"]["code"], "commit_status_uncertain")
        self.assertNotIn("head", uncertain["error"])
        self.assertEqual(self.worker.handle(request("status", "blocked"))["error"]["code"], "worker_stopped")
        recovered = Worker(self.state_dir, fixture(), world_id="chaos-demo", seed=7)
        self.assertEqual(recovered.handle(request("status", "recovered"))["result"]["logical_tick"], 1)

    def test_cli_jsonl_roundtrip(self) -> None:
        world_file = Path(self.temp.name) / "initial-world.json"
        world_file.write_text(json.dumps(fixture(), ensure_ascii=False), encoding="utf-8")
        commands = [request("status", "status-cli"), advance("advance-cli"), observe(0, 0, "past-cli"),
                    observe(1, 1, "current-cli")]
        completed = subprocess.run(
            [sys.executable, "-m", "engine.chaos.origin_worker", "--initial-world", str(world_file),
             "--state-dir", str(Path(self.temp.name) / "cli-state"), "--world-id", "chaos-demo",
             "--seed", "7", "--dt", "0.01", "--physical-steps", "8"],
            input="".join(json.dumps(c) + "\n" for c in commands), text=True,
            capture_output=True, check=False, cwd=ROOT,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        responses = [json.loads(line) for line in completed.stdout.splitlines()]
        self.assertEqual(len(responses), 4)
        self.assertTrue(all(response["ok"] for response in responses))
        self.assertEqual(responses[1]["result"]["state_hash"], GOLDEN["state_hash_1"])
        self.assertEqual(responses[2]["result"]["logical_tick"], 0)
        self.assertEqual(responses[3]["result"]["logical_tick"], 1)


if __name__ == "__main__":
    unittest.main()
