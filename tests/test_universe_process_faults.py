"""Independent fresh-process acceptance; no production internals are imported."""
import os
from pathlib import Path
import tempfile
import unittest

from scripts.run_universe_authority_faults import golden_check, run_suite


class UniverseProcessFaultTests(unittest.TestCase):
    def test_independent_encoder_matches_fixed_golden_bytes_and_hashes(self):
        self.assertEqual(golden_check()['records'], 24)

    def test_existing_output_is_rejected_without_modifying_original_evidence(self):
        with tempfile.TemporaryDirectory(prefix='universe-i6-preserve-') as temporary:
            base = Path(temporary)
            output = base / 'existing'
            output.mkdir()
            sentinel = output / 'raw-index.json'
            sentinel.write_bytes(b'original evidence')
            alias = base / 'alias'
            alias.symlink_to(output, target_is_directory=True)
            for candidate in (output, alias):
                with self.subTest(output=candidate):
                    with self.assertRaises(FileExistsError):
                        run_suite(candidate)
                    self.assertEqual(set(base.iterdir()), {output, alias})
                    self.assertEqual(list(output.iterdir()), [sentinel])
                    self.assertEqual(sentinel.read_bytes(), b'original evidence')
                    self.assertTrue(alias.is_symlink())
                    self.assertEqual(os.readlink(alias), str(output))

    @unittest.skipUnless(os.name == 'posix', 'local POSIX profile requires signals/flock')
    def test_real_process_fault_matrix(self):
        configured = os.environ.get('EDGEWORLD_I6_OUTPUT')
        if configured:
            output = Path(configured)
            self.assertTrue(output.is_absolute())
            summary = run_suite(output)
        else:
            with tempfile.TemporaryDirectory(prefix='universe-i6-') as temporary:
                summary = run_suite(Path(temporary) / 'evidence')
        self.assertTrue(summary['passed'], [r for r in summary['cases'] if r['status'] != 'pass'])
        self.assertEqual(summary['real_sigkill_cases'], 12)
        self.assertTrue(summary['inputs_unchanged'])


if __name__ == '__main__':
    unittest.main()
