"""Fresh-process E6 acceptance; parent oracle imports no production modules."""
import os
from pathlib import Path
import tempfile
import unittest

from scripts.run_universe_blob_trust_faults import golden_check, run_suite


class UniverseBlobTrustProcessTests(unittest.TestCase):
    def test_independent_encoder_matches_67_fixed_vectors(self):
        self.assertEqual(golden_check()['records'],67)

    def test_existing_and_symlink_output_preserve_original(self):
        with tempfile.TemporaryDirectory(prefix='e6-preserve-') as temporary:
            base=Path(temporary);output=base/'original';output.mkdir()
            sentinel=output/'raw-index.json';sentinel.write_bytes(b'original evidence')
            alias=base/'alias';alias.symlink_to(output,target_is_directory=True)
            for path in (output,alias):
                with self.assertRaises(FileExistsError):run_suite(path)
                self.assertEqual(sentinel.read_bytes(),b'original evidence')
                self.assertEqual(set(base.iterdir()),{output,alias})
                self.assertEqual(list(output.iterdir()),[sentinel])
                self.assertEqual(os.readlink(alias),str(output))

    @unittest.skipUnless(os.name=='posix','POSIX signals/leases required')
    def test_real_blob_trust_process_matrix(self):
        configured=os.environ.get('EDGEWORLD_E6_OUTPUT')
        if configured:
            output=Path(configured);self.assertTrue(output.is_absolute());result=run_suite(output)
        else:
            with tempfile.TemporaryDirectory(prefix='e6-process-') as temporary:
                result=run_suite(Path(temporary)/'evidence')
        self.assertTrue(result['passed'],[r for r in result['cases'] if r['status']!='pass'])
        self.assertEqual(result['real_sigkills'],8)
        self.assertEqual(result['cleanup_kills'],0)
        self.assertTrue(result['all_children_reaped'])
        self.assertTrue(result['inputs_unchanged'])

if __name__=='__main__':unittest.main()
