"""CPU-only integration CLI and fixed-protocol checks; no valid runtime card."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/run_universe_slice_acceptance.py'
VERIFIER = ROOT / 'scripts/verify_universe_slice_evidence.py'


class IntegrationTests(unittest.TestCase):
    def cli(self, script, *args):
        p = subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, timeout=5)
        return p, json.loads(p.stdout or p.stderr)

    def runner(self):
        self.enterContext(patch.object(sys, 'path', [str(ROOT / 'scripts'), *sys.path]))
        spec = importlib.util.spec_from_file_location('i14_runner_under_test', RUNNER)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        return module

    def test_v2_plan_has_real_new_dependencies_but_no_runtime_permission(self):
        p, value = self.cli(RUNNER, 'i14-plan')
        self.assertEqual(p.returncode, 0)
        self.assertEqual(value['manifest']['format'], 'universe-i14-actions.v1')
        self.assertEqual(value['sessions']['initialize']['max_seconds'], 540)
        self.assertEqual(value['sessions']['existing']['max_seconds'], 280)
        self.assertFalse(value['runtime_authorized'])
        self.assertEqual(value['readiness']['status'], 'no_go')
        self.assertTrue(value['public_proof_reviews_pending'])

    def test_controller_without_real_card_fails_before_observer_or_child(self):
        with tempfile.TemporaryDirectory() as raw:
            card = Path(raw).resolve() / 'missing.json'
            p, value = self.cli(RUNNER, 'r13-controller', '--r13-card', str(card), '--card-sha256', '0'*64,
                '--accepted-source', 'a'*40, '--tool-source', 'b'*40, '--manifest-sha256', '0'*64,
                '--runner-sha256', hashlib.sha256(RUNNER.read_bytes()).hexdigest(), '--execute')
            self.assertEqual(p.returncode, 1)
            self.assertEqual(value['status'], 'error')
            self.assertNotIn('controller-ready', p.stdout)
            self.assertFalse(card.exists())

    def test_protocol_is_fixed_and_rejects_arbitrary_command_or_arguments(self):
        module = self.runner(); controller = Mock()
        with self.assertRaises(module.Invalid):
            module.r13_step(controller, dict(command='eval', args={'code':'arbitrary'}))
        with self.assertRaises(module.Invalid):
            module.r13_step(controller, dict(command='begin', args={'session':'initialize','argv':['anything']}))
        controller.begin_session.assert_not_called()
        module.r13_step(controller, dict(command='begin', args={'session':'initialize'}))
        controller.begin_session.assert_called_once_with('initialize')

    def test_controller_public_input_scope_rejects_private_redirect_before_read(self):
        module = self.runner()
        with tempfile.TemporaryDirectory() as raw:
            controller = Mock();controller.output = Path(raw).resolve() / 'controller'
            with self.assertRaises(module.Invalid):
                module.r13_step(controller, dict(command='ready', args={'ready_ref':{
                    'path': str(Path(raw).resolve() / 'outside.json'), 'sha256':'0'*64}}))
            controller.register_ready.assert_not_called()

    def test_quit_ack_accepts_original_non_json_cua_bytes(self):
        module = self.runner()
        with tempfile.TemporaryDirectory() as raw:
            controller = Mock();controller.output = Path(raw).resolve()
            inputs=controller.output/'controller-inputs';inputs.mkdir()
            path=inputs/'raw-cua.txt';data=b'original tool output, not JSON';path.write_bytes(data)
            ref={'path':str(path),'sha256':hashlib.sha256(data).hexdigest()}
            module.r13_step(controller, dict(command='quit_ack',args={'raw_cua_ref':ref}))
            controller.ack_quit.assert_called_once_with(ref)

    def test_new_verifier_requires_external_pins_before_bundle_read(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw).resolve();policy=root/'policy.json';policy.write_text('{}')
            for pins in [[],['--policy-sha256','0'*64,'--bundle-sha256','0'*64]]:
                p,value=self.cli(VERIFIER,'--i14-bundle',str(root/'absent.json'),'--i14-policy',str(policy),*pins)
                self.assertEqual(p.returncode,1)
                self.assertEqual(value['status'],'fail')
                self.assertNotIn('FileNotFoundError',value['error'])


if __name__ == '__main__':unittest.main()
