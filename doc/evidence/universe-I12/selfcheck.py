"""Synthetic tool regression checks. No UE/Genesis, signer or registered root."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
import verify_universe_slice_evidence as oracle
import run_universe_slice_acceptance as driver


class EvidenceTools(unittest.TestCase):
    def test_prep2_history_arity_and_post_action_marker(self):
        history = dict(driver.PLAN)['history']
        for selection in ('0 1 1', '0 0 0', '1 2 2'):
            self.assertIn('UniverseObserveExact ' + selection, history)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / 'ue.log'
            prefix = b'observation before action\n'
            path.write_bytes(prefix)
            before = path.stat()
            digest = oracle.hashlib.sha256(prefix).hexdigest()
            # Actual action already completed before helper starts: no waiter-arm sleep.
            with path.open('ab') as stream:
                stream.write(b'new-action-marker\n')
            result = driver.wait_marker(path, 'new-action-marker', 1, digest, len(prefix),
                                        before.st_dev, before.st_ino, 'synthetic-run', 123)
            self.assertTrue(result['matched'])
            self.assertEqual(result['start_offset'], len(prefix))
            self.assertEqual(result['end_offset'], path.stat().st_size)
            self.assertEqual(result['run_id'], 'synthetic-run')
            self.assertEqual(result['host_pid'], 123)

    def test_prep2_prefix_changed_truncated_or_replaced(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            path = folder / 'ue.log'
            prefix = b'action-before\n'
            path.write_bytes(prefix)
            before = path.stat()
            digest = oracle.hashlib.sha256(prefix).hexdigest()
            def wait():
                return driver.wait_marker(path, 'marker', 1, digest, len(prefix),
                                          before.st_dev, before.st_ino)
            path.write_bytes(b'changed-value\nmarker\n')
            with self.assertRaisesRegex(oracle.Invalid, 'prefix hash'):
                wait()
            path.write_bytes(b'x')
            with self.assertRaisesRegex(oracle.Invalid, 'truncated'):
                wait()
            replacement = folder / 'replacement'
            replacement.write_bytes(prefix + b'marker\n')
            replacement.replace(path)
            with self.assertRaisesRegex(oracle.Invalid, 'replaced'):
                wait()
            with self.assertRaisesRegex(oracle.Invalid, 'device/inode'):
                driver.wait_marker(path, 'marker', 1, digest, len(prefix))

    def test_literal_contract_goldens(self):
        goldens = oracle.read_json(ROOT / 'doc/fixtures/universe_authority_v0_2/golden.json')
        for vector in goldens:
            raw = bytes.fromhex(vector['canonical_hex'])
            self.assertEqual(oracle.canonical(json.loads(raw)), raw)
            self.assertEqual(oracle.hashlib.sha256(oracle.PREFIX + raw).hexdigest(), vector['sha256'])

    def test_exact_rounding_and_invalid_numbers(self):
        # This binary64 approximation lies above 0.9925: exact result rounds -7.
        self.assertEqual(oracle.influence({'$f64': '3ff0000000000000'},
                                          {'$f64': '3fefc28f5c28f5c3'}), -7)
        self.assertEqual(oracle.influence({'$f64': '0000000000000000'},
                                          {'$f64': '3f50000000000000'}), 1)
        for invalid in ({'$f64': '7ff0000000000000'}, {'$f64': 'FFF0000000000000'}, 0.1):
            with self.assertRaises((oracle.Invalid, TypeError)):
                oracle.canonical(invalid)
        with self.assertRaises(oracle.Invalid):
            oracle.wire_frame(b'{"x":1,"x":2}\n')
        for raw in (b'{}\r\n', b'{}\n{}\n', b'{}'):
            with self.assertRaises(oracle.Invalid):
                oracle.wire_frame(raw)

    def trace(self, folder):
        request = b'{"protocol_version":1,"request_id":"r1","operation":"status","payload":{}}\n'
        response = b'{"protocol_version":1,"request_id":"r1","ok":true,"result":{}}\n'
        exit_event = {'return_code_available': True, 'exit_code': 0, 'worker_pid': 123,
                      'generation': '1', 'reaped': True, 'trace_complete': True,
                      'stop_kind': 'normal', 'hard_kill_sent': False, 'operational_failure': False}
        events = [('request', request), ('write-result', b''),
                  ('stdout-chunk', response[:25]), ('stdout-chunk', response[25:]),
                  ('response-complete', b''), ('stdin-eof', b''),
                  ('worker-exit', json.dumps(exit_event).encode())]
        for number, (direction, raw) in enumerate(events, 1):
            stem = 'synthetic-transport-' + str(number).zfill(8)
            metadata = {'direction': direction, 'utc': '2026-11-02T00:00:00Z',
                        'monotonic_seconds': number, 'serial': str(number),
                        'request_serial': '1', 'generation': '1', 'worker_pid': 123,
                        'host_pid': 122, 'request_id': 'r1', 'operation': 'status',
                        'raw_file': stem + '.bin', 'byte_count': len(raw),
                        'written_bytes': len(request) if direction == 'write-result' else -1}
            (folder / (stem + '.bin')).write_bytes(raw)
            (folder / (stem + '.json')).write_text(json.dumps(metadata))

    def test_trace_chunks_and_tampering(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            self.trace(folder)
            result = oracle.inspect_trace(folder)
            self.assertEqual(len(result['frames']), 1)
            self.assertEqual(result['worker_exits'][0]['exit_code'], 0)
            path = folder / 'synthetic-transport-00000002.json'
            value = oracle.read_json(path)
            value['written_bytes'] -= 1
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(oracle.Invalid, 'incomplete request write'):
                oracle.inspect_trace(folder)

    def test_synthetic_archive_refs_and_development(self):
        fixtures = ROOT / 'doc/fixtures/universe_authority_v0_2'
        archive = oracle.read_json(fixtures / 'positive.json')
        blobs = oracle.read_json(fixtures / 'synthetic_blobs.json')
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            (folder / 'objects').mkdir()
            (folder / 'blobs').mkdir()
            for record in archive['records']:
                raw = oracle.canonical(record)
                digest = oracle.hashlib.sha256(oracle.PREFIX + raw).hexdigest()
                (folder / 'objects' / (digest + '.json')).write_bytes(raw)
            for digest, payload in blobs['blobs'].items():
                (folder / 'blobs' / (digest + '.static')).write_bytes(bytes.fromhex(payload))
            (folder / 'HEAD.json').write_bytes(oracle.canonical({
                'domain': archive['domain'], 'version': '0.2', 'world_id': archive['records'][0]['world_id'],
                'manifest': archive['head'], 'profile': archive['test_profile']}))
            result = oracle.inspect_authority(folder, oracle.read_json(fixtures / 'schema.json'))
            self.assertEqual([(h['tick'], h['revision']) for h in result['history']],
                             [(0, 0), (0, 1), (1, 2), (1, 3)])
            raw_path = next((folder / 'blobs').iterdir())
            raw_path.write_bytes(b'corrupt')
            with self.assertRaisesRegex(oracle.Invalid, 'raw payload'):
                oracle.inspect_authority(folder, oracle.read_json(fixtures / 'schema.json'))

    def test_missing_bundle_stays_inconclusive(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / 'bundle.json'
            path.write_text(json.dumps({'format': 'universe-i12-evidence.v1', 'artifacts': [],
                'budget': {'bytes': 1024, 'seconds': 1200, 'elapsed_seconds': 0}}))
            result = oracle.verify_bundle(path, {})
            self.assertEqual(result['status'], 'inconclusive')
            self.assertIn('two complete UE-owned sessions', result['missing'])

    def test_hash_and_descriptor_path_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            with self.assertRaisesRegex(oracle.Invalid, 'regular file'):
                oracle.file_hash(folder)
            fifo = folder / 'synthetic-fifo'
            os.mkfifo(fifo)
            with self.assertRaisesRegex(oracle.Invalid, 'regular file'):
                oracle.file_hash(fifo)
            # A deliberately minimal malformed evidence fixture: no Store or signer.
            (folder / 'objects').mkdir()
            record = {'domain': 'edgeworld.universe.authority', 'version': '0.2',
                      'world_id': 'synthetic', 'kind': 'checkpoint_descriptor', 'id': 'bad',
                      'body': {'payload_sha256': '../private-key', 'byte_count': 0,
                               'artifact_class': 'synthetic-contract-only'}, 'refs': {}}
            raw = oracle.canonical(record)
            digest = oracle.hashlib.sha256(oracle.PREFIX + raw).hexdigest()
            (folder / 'objects' / (digest + '.json')).write_bytes(raw)
            (folder / 'HEAD.json').write_bytes(oracle.canonical({
                'domain': record['domain'], 'version': '0.2', 'world_id': 'synthetic',
                'manifest': digest, 'profile': 'composite-rigid-support.v0.2'}))
            schema = {'body': {'checkpoint_descriptor': record['body']},
                      'kind_bytes': {'checkpoint_descriptor': 2048},
                      'refs': {'checkpoint_descriptor': {}}}
            with self.assertRaisesRegex(oracle.Invalid, 'invalid raw payload digest'):
                oracle.inspect_authority(folder, schema)

    def test_exclusive_output_symlink_and_private_metadata(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            output = folder / 'new.json'
            driver.emit({'safe': True}, output)
            with self.assertRaises(FileExistsError):
                driver.emit({'safe': False}, output)
            linked = folder / 'link'
            linked.symlink_to(output)
            with self.assertRaises(oracle.Invalid):
                oracle.safe_read(linked)
            linked.unlink()
            self.assertTrue(driver.metadata([output])['metadata_only'])
            secret = folder / 'private-key'
            secret.write_bytes(b'do-not-hash')
            with self.assertRaisesRegex(oracle.Invalid, 'private material'):
                oracle.authority_map(folder)


if __name__ == '__main__':
    unittest.main(verbosity=2)
