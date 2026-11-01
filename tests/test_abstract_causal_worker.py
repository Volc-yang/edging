"""State and commit-boundary checks for the abstract causal engineering probe."""

from __future__ import annotations

import json
from decimal import Decimal, ROUND_HALF_EVEN
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from engine.edgeworld_worker.abstract_causal_worker import (
    ManifestWriteFailure, Worker, digest, file_hash, influence_mm,
)


class FakeGenesis:
    calls = 0
    fail = False

    def __init__(self, checkpoint, *, dt, physical_steps, seed):
        if checkpoint is None:
            self.z = 1.0
            self.vz = 0.0
        else:
            body = json.loads(Path(checkpoint).read_text())
            self.z, self.vz = body["z"], body["vz"]

    def observe_body(self):
        return {"position": [0.0, 0.0, self.z], "velocity": [0.0, 0.0, self.vz, 0.0, 0.0, 0.0]}

    def advance(self, phase):
        type(self).calls += 1
        if type(self).fail:
            self.z -= 0.1
            raise RuntimeError("injected Genesis failure")
        self.z -= 0.0072 if phase == "shaoyang" else 0.035316
        self.vz = -0.16 if phase == "shaoyang" else -0.7848
        return self.observe_body()

    def save_checkpoint(self, path):
        Path(path).write_text(json.dumps({"z": self.z, "vz": self.vz}))


class AbstractCausalWorkerTests(unittest.TestCase):
    def test_absolute_script_entrypoint_from_other_directory(self):
        script = Path(__file__).resolve().parents[1] / "engine/edgeworld_worker/abstract_causal_worker.py"
        with tempfile.TemporaryDirectory() as cwd:
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            completed = subprocess.run(
                [sys.executable, str(script), "--help"], cwd=cwd, env=env,
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--state-dir", completed.stdout)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        FakeGenesis.calls = 0
        FakeGenesis.fail = False
        self.worker = Worker(Path(self.temp.name), "stg-demo", adapter_cls=FakeGenesis)

    def req(self, op, **fields):
        return {"protocol_version": 1, "request_id": op + "-request", "operation": op,
                "world_id": "stg-demo", **fields}

    @staticmethod
    def view(tick):
        return {"watermark": tick, "region": "causal-fragment-v1", "observer": "ue-causal-camera-v1",
                "resolution": "causal-graph-proxy-v1",
                "error_budget": {"semantic_state": "exact", "visual_geometry": "unmeasured-proxy"},
                "rules": {"evolution": "abstract-causal-probe.v1", "projection": "causal-graph-ue.v1"}}

    def advance(self, phase="shaoyang", command="one", revision=0, tick=1):
        return self.worker.handle(self.req("advance", command_id=command,
                                           expected_revision=revision, target_tick=tick,
                                           external_inputs={"schema_version": "abstract-causal-input.v1", "phase": phase}))

    def hashes(self):
        root = Path(self.temp.name)
        return {str(path.relative_to(root)): file_hash(path) for path in root.rglob("*") if path.is_file()}

    def test_counterfactual_development_field_and_event_reference(self):
        one = self.advance()
        self.assertTrue(one["ok"], one)
        self.assertEqual(-7, one["result"]["record"]["influence_mm"])
        observed = self.worker.handle(self.req("observe", logical_tick=1, view_spec=self.view(1)))
        self.assertTrue(observed["ok"])
        result = observed["result"]
        node = result["development_structure"]["nodes"][-1]
        edge = result["development_structure"]["edges"][-1]
        self.assertEqual(-7, node["influence_mm"])
        self.assertEqual(result["physics_sample"]["physics_candidate_hash"], node["physics_candidate_hash"])
        self.assertEqual(node["physics_candidate_hash"], edge["physics_candidate_hash"])
        self.assertEqual("stg-demo:node:1", node["node_id"])
        with tempfile.TemporaryDirectory() as other:
            second = Worker(Path(other), "stg-demo", adapter_cls=FakeGenesis)
            req = self.req("advance", command_id="one", expected_revision=0, target_tick=1,
                           external_inputs={"schema_version": "abstract-causal-input.v1", "phase": "taiyang"})
            two = second.handle(req)
            self.assertTrue(two["ok"], two)
            self.assertEqual(-35, two["result"]["record"]["influence_mm"])
            self.assertEqual(one["result"]["record"]["node_id"], two["result"]["record"]["node_id"])
            self.assertNotEqual(one["result"]["head_state_hash"], two["result"]["head_state_hash"])

    def test_idempotence_rejections_and_observation_are_read_only(self):
        first = self.advance()
        before = self.hashes()
        self.assertEqual(first["result"], self.advance()["result"])
        self.assertEqual(1, FakeGenesis.calls)
        bad = [
            self.advance("taiyang"),
            self.advance(command="new", revision=0, tick=2),
            self.worker.handle(self.req("observe", logical_tick=99, view_spec=self.view(99))),
            self.worker.handle(self.req("observe", logical_tick=1, view_spec=self.view(0))),
            self.worker.handle(self.req("observe", logical_tick=1, view_spec={**self.view(1), "rules": []})),
        ]
        self.assertEqual(["command_id_conflict", "revision_conflict", "history_missing", "watermark_mismatch", "invalid_request"],
                         [response["error"]["code"] for response in bad])
        for tick in (0, 1):
            self.assertTrue(self.worker.handle(self.req("observe", logical_tick=tick, view_spec=self.view(tick)))["ok"])
        self.assertEqual(before, self.hashes())

    def test_restart_rechecks_history_and_checkpoint(self):
        self.advance()
        restarted = Worker(Path(self.temp.name), "stg-demo", adapter_cls=FakeGenesis)
        request = self.req("observe", logical_tick=0, view_spec=self.view(0))
        self.assertEqual(self.worker.handle(request)["result"], restarted.handle(request)["result"])
        self.assertEqual(2, restarted.handle(self.req("advance", command_id="two", expected_revision=1,
                                                       target_tick=2, external_inputs={"schema_version": "abstract-causal-input.v1",
                                                                                          "phase": "taiyang"}))["result"]["state_revision"])
        manifest = Path(self.temp.name) / "abstract_world.json"
        data = json.loads(manifest.read_text())
        data["history"][1]["development_structure"]["nodes"][1]["influence_mm"] = 12
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "structure hash mismatch"):
            Worker(Path(self.temp.name), "stg-demo", adapter_cls=FakeGenesis)

    def test_genesis_failure_restores_committed_state(self):
        before = self.hashes()
        FakeGenesis.fail = True
        response = self.advance()
        self.assertEqual("genesis_failed", response["error"]["code"])
        self.assertEqual(before, self.hashes())
        FakeGenesis.fail = False
        self.assertTrue(self.advance()["ok"])

    def test_manifest_uncertainty_fail_stops(self):
        def uncertain(_):
            raise ManifestWriteFailure(True, OSError("injected"))

        self.worker._write_manifest = uncertain
        response = self.advance()
        self.assertEqual("commit_status_uncertain", response["error"]["code"])
        self.assertEqual("worker_stopped", self.worker.handle(self.req("status"))["error"]["code"])

    def test_restart_rejects_tampered_command_retry_result(self):
        self.advance()
        manifest = Path(self.temp.name) / "abstract_world.json"
        data = json.loads(manifest.read_text())
        data["commands"]["one"]["result"]["head_state_hash"] = "0" * 64
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "committed command result or fingerprint mismatch"):
            Worker(Path(self.temp.name), "stg-demo", adapter_cls=FakeGenesis)

    def test_restart_rejects_rewritten_history_prefix(self):
        self.advance()
        self.advance(command="two", revision=1, tick=2)
        manifest = Path(self.temp.name) / "abstract_world.json"
        data = json.loads(manifest.read_text())
        second = data["history"][2]
        second["development_structure"]["nodes"][1]["influence_mm"] = 42
        structure = second["development_structure"]
        structure["structure_hash"] = digest({k: structure[k] for k in ("root_id", "nodes", "edges")})
        second["state_hash"] = self.worker._state_hash(2, second["seed_initial_record"],
                                                        structure["structure_hash"],
                                                        second["physics_sample"]["physics_candidate_hash"])
        data["head_state_hash"] = second["state_hash"]
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "development history prefix mismatch"):
            Worker(Path(self.temp.name), "stg-demo", adapter_cls=FakeGenesis)

    def test_restart_rejects_unsupported_committed_phase(self):
        self.advance()
        manifest = Path(self.temp.name) / "abstract_world.json"
        data = json.loads(manifest.read_text())
        record = data["history"][1]
        sample = record["physics_sample"]
        sample["phase"] = "shaoyin"
        sample["physics_candidate_hash"] = digest({key: sample[key] for key in
                                                   ("physical_probe_id", "position", "velocity", "genesis_config_hash", "phase")})
        structure = record["development_structure"]
        structure["nodes"][-1]["physics_candidate_hash"] = sample["physics_candidate_hash"]
        structure["edges"][-1]["physics_candidate_hash"] = sample["physics_candidate_hash"]
        structure["structure_hash"] = digest({k: structure[k] for k in ("root_id", "nodes", "edges")})
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "invalid committed phase"):
            Worker(Path(self.temp.name), "stg-demo", adapter_cls=FakeGenesis)

    def test_round_half_even_and_bounds(self):
        self.assertEqual(2, int(Decimal("2.5").to_integral_value(rounding=ROUND_HALF_EVEN)))
        self.assertEqual(4, int(Decimal("3.5").to_integral_value(rounding=ROUND_HALF_EVEN)))
        self.assertEqual(-2, int(Decimal("-2.5").to_integral_value(rounding=ROUND_HALF_EVEN)))
        self.assertEqual(3, influence_mm(0.0025, 0.0))  # binary64 input is above the exact decimal tie
        self.assertEqual(64, len(digest({"a": 1})))
        self.assertTrue(self.worker.handle(self.req("observe", logical_tick=0.0, view_spec=self.view(0)))["ok"])
        self.assertEqual("invalid_request", self.worker.handle(self.req("observe", logical_tick=0.5,
                                                        view_spec=self.view(0)))["error"]["code"])


if __name__ == "__main__":
    unittest.main()
