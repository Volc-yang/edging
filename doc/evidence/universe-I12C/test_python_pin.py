"""Synthetic filesystem-only cases. No interpreter, Genesis, UE or launcher execution."""
from copy import deepcopy
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'scripts'))
import run_universe_slice_acceptance as driver


class PythonPinTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.venv = self.root / 'venv'
        (self.venv / 'bin').mkdir(parents=True)
        self.site = self.venv / 'lib/python3.12/site-packages'
        self.site.mkdir(parents=True)
        self.cfg = self.venv / 'pyvenv.cfg'
        self.cfg.write_text('version_info = 3.12.14\ninclude-system-site-packages = false\n')
        cellar = self.root / 'Cellar/cpython/3.12'
        (cellar / 'bin').mkdir(parents=True)
        (cellar / 'libexec').mkdir()
        self.target = cellar / 'libexec/python3.12'
        self.target.write_bytes(b'synthetic executable; must never run\n')
        self.target.chmod(0o700)
        (cellar / 'bin/python3.12').symlink_to('../libexec/python3.12')
        (self.root / 'opt').mkdir()
        self.parent_link = self.root / 'opt/cpython'
        self.parent_link.symlink_to('../Cellar/cpython/3.12')
        (self.venv / 'bin/python').symlink_to(self.root / 'opt/cpython/bin/python3.12')
        self.entry = self.venv / 'bin/python3.12'
        self.entry.symlink_to('python')
        self.pin = driver.collect_python_pin(str(self.entry))
        self.card = {'python_executable': str(self.entry), 'python_environment_pin': self.pin}
        patch = mock.patch.dict(os.environ, {'PYTHONHOME': '', 'PYTHONPATH': ''})
        patch.start(); self.addCleanup(patch.stop)

    def reject(self, card=None):
        with self.assertRaises(driver.Invalid):
            driver.validate_python_executable(self.card if card is None else card)

    def test_exact_complete_chain_keeps_original_lexical_entry(self):
        original = deepcopy(self.card)
        with mock.patch.object(driver.subprocess, 'Popen', side_effect=AssertionError('must not execute')):
            result = driver.validate_python_executable(self.card)
        self.assertEqual(str(self.entry), result)
        self.assertNotEqual(str(self.target), result)
        self.assertEqual(original, self.card)
        self.assertEqual(4, len(self.pin['links']))

    def test_no_pin_keeps_original_symlink_rejection(self):
        self.reject({'python_executable': str(self.entry)})
        with self.assertRaises(driver.Invalid):
            driver.safe_path(self.entry)  # shared evidence policy is still strict

    def test_legacy_plain_regular_executable_unchanged(self):
        plain = self.root / 'plain-python'
        plain.write_bytes(b'never execute'); plain.chmod(0o700)
        self.assertEqual(str(plain), driver.validate_python_executable({'python_executable': str(plain)}))

    def test_unknown_redirection_rejected_before_target_hash_read(self):
        self.entry.unlink(); self.entry.symlink_to(self.target)
        with mock.patch.object(driver, 'file_hash', side_effect=AssertionError('unexpected target read')):
            self.reject()

    def test_unknown_ancestor_symlink_rejected(self):
        other = self.root / 'other'; other.mkdir()
        self.parent_link.unlink(); self.parent_link.symlink_to('../other')
        self.reject()

    def test_omitted_extra_and_changed_link_pins_rejected(self):
        for links in (self.pin['links'][:-1], self.pin['links'] + [self.pin['links'][-1]],
                      [dict(self.pin['links'][0], readlink='./python')] + self.pin['links'][1:]):
            card = deepcopy(self.card); card['python_environment_pin']['links'] = links
            self.reject(card)

    def test_changed_target_bytes_or_unrelated_target_path_rejected(self):
        self.target.write_bytes(b'changed synthetic bytes'); self.reject()
        self.target.write_bytes(b'synthetic executable; must never run\n')
        card = deepcopy(self.card); card['python_environment_pin']['target']['path'] = str(self.root / 'elsewhere')
        self.reject(card)

    def test_cfg_must_be_same_lexical_venv_not_matching_unrelated_file(self):
        other = self.root / 'unrelated.cfg'; other.write_bytes(self.cfg.read_bytes())
        card = deepcopy(self.card); card['python_environment_pin']['pyvenv_cfg']['path'] = str(other)
        self.reject(card)

    def test_changed_cfg_and_entry_version_mismatch_rejected(self):
        self.cfg.write_text('version_info = 3.13.0\n'); self.reject()
        card = deepcopy(self.card)
        import hashlib
        card['python_environment_pin']['pyvenv_cfg']['sha256'] = hashlib.sha256(self.cfg.read_bytes()).hexdigest()
        self.reject(card)

    def test_site_must_be_same_venv_version_even_if_identity_fields_match(self):
        card = deepcopy(self.card); card['python_environment_pin']['site_packages']['path'] = str(self.root / 'unrelated')
        self.reject(card)

    def test_site_replacement_and_symlink_rejected(self):
        old = self.site.with_name('old-site'); self.site.rename(old); self.site.mkdir(); self.reject()
        self.site.rmdir(); self.site.symlink_to(old); self.reject()

    def test_cycle_is_rejected_without_execution(self):
        self.entry.unlink(); self.entry.symlink_to('python3.12')
        card = deepcopy(self.card); card['python_environment_pin']['links'] = [{'path': str(self.entry), 'readlink': 'python3.12'}]
        self.reject(card)

    def test_dotdot_walk_follows_prior_symlink_before_parent(self):
        (self.root / 'target/deep').mkdir(parents=True)
        result = self.root / 'target/python3.12'; result.write_bytes(b'non-executed')
        (self.root / 'route').symlink_to('target/deep')
        link = self.root / 'entry'; link.symlink_to('route/../python3.12')
        actual, links = driver._python_link_chain(str(link))
        self.assertEqual(result, actual)
        self.assertEqual([str(link), str(self.root / 'route')], [x['path'] for x in links])

    def test_nonempty_pythonhome_or_pythonpath_rejected_only_for_special_pin(self):
        for key in ('PYTHONHOME', 'PYTHONPATH'):
            with mock.patch.dict(os.environ, {key: '/unapproved'}):
                self.reject()

    def test_other_evidence_paths_are_not_relaxed(self):
        evidence = self.root / 'evidence-link'; evidence.symlink_to(self.target)
        with self.assertRaises(driver.Invalid):
            driver.safe_read(evidence)
        with self.assertRaises(driver.Invalid):
            driver.emit({'not': 'allowed'}, str(evidence))


class LauncherEvidencePathTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.product = self.root / 'product'; self.storage = self.root / 'storage'
        self.parent = self.product / 'engine_platforms/unreal/EdgeWorldHost'
        self.parent.mkdir(parents=True); self.storage.mkdir()
        (self.parent / 'Saved').symlink_to(self.storage)
        self.launcher = self.storage / 'MacLauncher'; self.launcher.mkdir()
        self.run = self.launcher / 'run-accepted'; self.run.mkdir()
        self.card = {'product_root': str(self.product), 'launcher_output_root': str(self.launcher)}

    def test_exact_attested_source_prefix_and_canonical_prefix(self):
        logged = self.parent / 'Saved/MacLauncher/run-accepted'
        self.assertEqual(self.run, driver._launcher_evidence_directory(str(logged), self.card))
        self.assertEqual(self.run, driver._launcher_evidence_directory(str(self.run), self.card))
        with self.assertRaises(driver.Invalid):
            driver.safe_path(logged)  # this bridge does not alter the shared evidence rule

    def test_unknown_prefix_rejected_even_if_same_resolved_target(self):
        other = self.root / 'other'; other.symlink_to(self.storage)
        with self.assertRaises(driver.Invalid):
            driver._launcher_evidence_directory(str(other / 'MacLauncher/run-accepted'), self.card)

    def test_leaf_symlink_or_redirected_mapping_rejected(self):
        linked = self.launcher / 'run-link'; linked.symlink_to(self.run)
        with self.assertRaises(driver.Invalid):
            driver._launcher_evidence_directory(str(linked), self.card)
        (self.parent / 'Saved').unlink()
        foreign = self.root / 'foreign/MacLauncher/run-accepted'; foreign.mkdir(parents=True)
        (self.parent / 'Saved').symlink_to(self.root / 'foreign')
        with self.assertRaises(driver.Invalid):
            driver._launcher_evidence_directory(str(self.parent / 'Saved/MacLauncher/run-accepted'), self.card)


if __name__ == '__main__':
    unittest.main()
