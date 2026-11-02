import importlib.util
import contextlib
import io
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'scripts'
sys.path.insert(0, str(SCRIPTS))
import universe_iteration
SPEC = importlib.util.spec_from_file_location('i15_cli_under_test', SCRIPTS / 'run_universe_slice_acceptance.py')
CLI = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CLI)


class I15ProtocolTest(unittest.TestCase):
    def test_command_cannot_select_python_attribute_or_extra_args(self):
        controller = Mock()
        for request in (
            {'command': '__getattribute__', 'args': {'name': 'process'}},
            {'command': 'start_native', 'args': {'argv': ['sh']}},
            {'command': 'seal', 'args': {}, 'execute': True},
            {'command': 'skip_metal', 'args': {'evidence_ref': {}, 'normal': True}},
        ):
            with self.subTest(request=request), self.assertRaises(CLI.Invalid):
                CLI.i15_step(controller, request)
        self.assertEqual(controller.mock_calls, [])

    def test_native_wait_rejects_unbounded_and_nonfinite_values(self):
        controller = Mock()
        for timeout in (0, -1, 181, float('nan'), float('inf'), True, '180'):
            with self.subTest(timeout=timeout), self.assertRaises(CLI.Invalid):
                CLI.i15_step(controller, {'command': 'wait_native', 'args': {'timeout': timeout}})
        self.assertEqual(controller.mock_calls, [])

    def test_skip_and_manifest_preserve_explicit_evidence(self):
        controller = Mock()
        skip = {'path': '/explicit/skip.json', 'sha256': 'a' * 64}
        manifest = {'path': '/explicit/manifest.json', 'sha256': 'b' * 64}
        CLI.i15_step(controller, {'command': 'skip_metal', 'args': {'evidence_ref': skip}})
        CLI.i15_step(controller, {'command': 'freeze_native', 'args': {
            'manifest_ref': manifest, 'expected_sha256': 'b' * 64}})
        controller.skip_metal.assert_called_once_with(skip)
        controller.freeze_native_manifest.assert_called_once_with(manifest, 'b' * 64)
        controller.start_metal.assert_not_called()
        controller.start_native.assert_not_called()

    def test_actual_wait_precedes_explicit_seal(self):
        controller = Mock()
        CLI.i15_step(controller, {'command': 'wait_native', 'args': {'timeout': 180}})
        controller.wait_native.assert_called_once_with(timeout=180)
        controller.seal.assert_not_called()

    def run_controller(self, *, sealed):
        controller = Mock(started=0, closed=False, clock_binding={})
        def finish(*args):
            controller.closed = True
            return {'normal': False}
        controller.abort.side_effect = finish
        controller.seal.side_effect = finish
        capability = SimpleNamespace(validate_capability_card=Mock(return_value=object()),
                                     CapabilityController=Mock(return_value=controller))
        args = SimpleNamespace(i15_card='card', card_sha256='a', prepared_sha256='b',
            manifest_sha256='c', accepted_source='d', tool_source='e', native_source='f', execute=True)
        lines = [b'{"command":"seal","args":{}}\n'] if sealed else []
        with patch.object(universe_iteration, 'capability', capability, create=True), \
                patch.object(CLI, 'controller_lines', return_value=iter(lines)), \
                contextlib.redirect_stdout(io.StringIO()):
            result = CLI.i15_controller(args)
        return controller, result

    def test_eof_aborts_exactly_once_and_returns_non_normal(self):
        controller, result = self.run_controller(sealed=False)
        controller.abort.assert_called_once()
        self.assertFalse(result['normal'])
        self.assertEqual(result['status'], 'aborted')

    def test_explicit_seal_does_not_abort_on_eof(self):
        controller, result = self.run_controller(sealed=True)
        controller.seal.assert_called_once()
        controller.abort.assert_not_called()
        self.assertEqual(result['status'], 'closed')


if __name__ == '__main__':
    unittest.main()
