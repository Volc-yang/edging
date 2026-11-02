"""CPU-only CLI checks: no live resource dispatch, even with capability assertions."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/run_universe_slice_acceptance.py'


class ReadinessTests(unittest.TestCase):
    def run_cli(self, *args):
        result = subprocess.run([sys.executable, str(RUNNER), *args], capture_output=True, text=True, timeout=5)
        return result, json.loads(result.stdout or result.stderr or '{}')

    def test_i13_plan_composes_three_modules_without_dispatch(self):
        result, value = self.run_cli('i13-plan')
        self.assertEqual(result.returncode, 0)
        self.assertFalse(value['runtime_authorized'])
        self.assertEqual(set(value['module_pins']), {'actions', 'capture', 'lifecycle'})
        self.assertEqual(value['lifecycle']['session_seconds'], 420)
        self.assertEqual(value['actions']['request_counts'], {'initialize': 20, 'existing': 5})

    def test_no_capabilities_produces_auditable_no_go_and_exit_two(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw).resolve()
            spec = root / 'capabilities.json'
            spec.write_text(json.dumps(dict(format='universe-i13-readiness-input.v1', source_sha='a' * 40, capabilities={})))
            output = root / 'result.json'
            result, value = self.run_cli('--output', str(output), 'i13-readiness', '--spec', str(spec), '--accepted-source', 'a' * 40)
            self.assertEqual(result.returncode, 2)
            value = json.loads(output.read_text())
            self.assertEqual(value['status'], 'no_go')
            self.assertFalse(value['runtime_authorized'])
            self.assertEqual(len(value['capability_check']['reasons']), 5)
            self.assertEqual(json.loads(output.read_text()), value)
            original = output.read_bytes()
            result, _ = self.run_cli('--output', str(output), 'i13-readiness', '--spec', str(spec), '--accepted-source', 'a' * 40)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(output.read_bytes(), original)

    def test_wrong_source_or_capability_shape_cannot_start_anything(self):
        with tempfile.TemporaryDirectory() as raw:
            spec = Path(raw).resolve() / 'spec.json'
            for changes in [dict(source_sha='b' * 40), dict(capabilities={'invented': True})]:
                value = dict(format='universe-i13-readiness-input.v1', source_sha='a' * 40, capabilities={})
                value.update(changes)
                spec.write_text(json.dumps(value))
                result, value = self.run_cli('i13-readiness', '--spec', str(spec), '--accepted-source', 'a' * 40)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(value['status'], 'error')

    def test_legacy_plan_and_missing_execute_still_have_no_runtime(self):
        result, plan = self.run_cli('plan')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(plan['format'], 'universe-i12-action-plan.v1')
        result, value = self.run_cli('run')
        self.assertEqual(result.returncode, 1)
        self.assertIn('explicit --execute', value['error'])

    def test_even_reviewed_capabilities_do_not_bypass_missing_live_adapter(self):
        with patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]):
            spec = importlib.util.spec_from_file_location('i13_runner_under_test', RUNNER)
            runner = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(runner)
            from universe_iteration import actions
            with patch.object(runner, 'read_json', return_value=dict(format='universe-i13-readiness-input.v1', source_sha='a' * 40, capabilities={})), \
                 patch.object(actions, 'readiness', return_value=dict(status='ready_for_R_review', reasons=[])):
                value = runner.i13_readiness('unused', 'a' * 40)
            self.assertEqual(value['status'], 'no_go')
            self.assertFalse(value['runtime_authorized'])
            self.assertTrue(any('I13 passive entry cannot dispatch' in b for b in value['blockers']))


if __name__ == '__main__':
    unittest.main()
