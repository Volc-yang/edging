"""Synthetic prepare-only namespace checks. No launcher, UE, GS or actual authority."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import run_universe_slice_acceptance as driver
_spec = importlib.util.spec_from_file_location('i12_metadata_fixture', ROOT / 'doc/evidence/universe-I12/selfcheck.py')
fixture = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(fixture)


class SessionNamespaceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.folder = Path(temporary.name).resolve()
        builder = fixture.RunnerPreparation('test_runner_fixed_full_valid_card_two_session_protocol')
        self.card, self.path, unused = builder.valid_card(self.folder)
        self.storage = Path(self.card['storage_root'])
        for patch in (mock.patch.object(driver, 'on_devssd', return_value=True),
                      mock.patch.object(driver, 'product_identity', return_value='a' * 40),
                      mock.patch.object(driver.subprocess, 'Popen', side_effect=AssertionError('no execution permitted'))):
            patch.start(); self.addCleanup(patch.stop)

    def prepare(self, session):
        self.path.write_text(json.dumps(self.card)); self.path.chmod(0o600)
        return driver.validate_run(self.path, driver.file_hash(self.path), 'a' * 40, session, True)

    def completion(self, namespace, **changes):
        self.path.write_text(json.dumps(self.card)); self.path.chmod(0o600)
        value = dict(card_sha256=driver.file_hash(self.path), accepted_source='a' * 40,
                     normal=True, session='initialize', cumulative_seconds=3)
        value.update(changes)
        path = self.storage / namespace / 'initialize/completion.json'
        path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(value))
        authority = Path(self.card['authority_root']); authority.mkdir(exist_ok=True)
        (authority / 'HEAD.json').write_text('{"synthetic-marker-only":true}')

    def test_default_compatibility_and_same_namespace_revisit(self):
        first = self.prepare('initialize')
        self.assertEqual(self.storage / 'sessions/initialize', first['output'])
        self.completion('sessions')
        revisit = self.prepare('existing')
        self.assertEqual(self.storage / 'sessions/existing', revisit['output'])
        self.assertEqual(3, revisit['prior_seconds'])

    def test_explicit_retry_preserves_old_outputs_and_full_storage_accounting(self):
        old = self.storage / 'sessions/initialize/cache.bin'; old.parent.mkdir(parents=True)
        old.write_bytes(b'old-cache-must-remain' * 50)
        failed = self.storage / 'failedsessions/initialize/failure.bin'; failed.parent.mkdir(parents=True)
        failed.write_bytes(b'failed-original')
        before = driver.tree_bytes(self.storage)
        self.card['session_namespace'] = 'sessions-retry-1'
        prepared = self.prepare('initialize')
        self.assertEqual(self.storage / 'sessions-retry-1/initialize', prepared['output'])
        self.assertFalse(prepared['output'].exists())
        self.assertEqual(before, driver.tree_bytes(self.storage))
        self.assertEqual(b'old-cache-must-remain' * 50, old.read_bytes())
        self.assertEqual(b'failed-original', failed.read_bytes())
        self.card.pop('session_namespace')
        with self.assertRaisesRegex(driver.Invalid, 'session output already exists'):
            self.prepare('initialize')

    def test_invalid_free_path_nonascii_overlong_or_link_namespace_rejected(self):
        for name in ('../outside', '/absolute', 'sessions/child', 'sessions-', 'sessions-A',
                     'sessions-é', 'sessions-' + 'x' * 56, '', None, 7):
            with self.subTest(name=name):
                self.card['session_namespace'] = name
                with self.assertRaisesRegex(driver.Invalid, 'invalid session namespace'):
                    self.prepare('initialize')
        (self.storage / 'sessions-link').symlink_to(self.folder)
        self.card['session_namespace'] = 'sessions-link'
        with self.assertRaisesRegex(driver.Invalid, 'symlink evidence path'):
            self.prepare('initialize')

    def test_existing_cannot_borrow_completion_from_another_namespace(self):
        self.card['session_namespace'] = 'sessions-new'
        self.completion('sessions')  # matching card/source/normal but wrong namespace
        self.completion('sessions-other')
        with self.assertRaisesRegex(driver.Invalid, 'missing regular evidence file'):
            self.prepare('existing')
        self.completion('sessions-new')
        result = self.prepare('existing')
        self.assertEqual(self.storage / 'sessions-new/existing', result['output'])

    def test_same_namespace_still_requires_exact_card_source_and_normal(self):
        self.card['session_namespace'] = 'sessions-verified'
        for change in ({'card_sha256': '0' * 64}, {'accepted_source': 'b' * 40},
                       {'normal': False}, {'session': 'existing'}):
            with self.subTest(change=change):
                self.completion('sessions-verified', **change)
                with self.assertRaisesRegex(driver.Invalid, 'first session not normally completed'):
                    self.prepare('existing')


if __name__ == '__main__':
    unittest.main()
