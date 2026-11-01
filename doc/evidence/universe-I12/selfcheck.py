"""Synthetic tool regression checks. No UE/Genesis, signer or registered root."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

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
                'manifest': archive['head'], 'profile': 'local-posix-blob-sync-v0.2'}))
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
                'manifest': digest, 'profile': 'local-posix-blob-sync-v0.2'}))
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


class RunnerPreparation(unittest.TestCase):
    """Only mocked Popen/ps/git; never invokes a real launcher or runtime."""
    def prepared(self, folder):
        storage = folder / 'synthetic-storage'
        storage.mkdir(mode=0o700)
        launcher_output = storage / 'launcher-output'
        launcher_output.mkdir(mode=0o700)
        run = launcher_output / 'run-mock'
        run.mkdir(mode=0o700)
        slots = {name: {'max_seconds': 50,
                       'stage_seconds': {'build': 20, 'startup': 10, 'interaction': 15, 'shutdown': 5}}
                 for name in ('initialize', 'existing')}
        card = {'run_id': 'synthetic-only', 'world_id': 'synthetic-world', 'product_root': str(folder / 'not-real-product'),
                'storage_root': str(storage), 'launcher_output_root': str(launcher_output),
                'authority_root': str(storage / 'never-created-authority'),
                'ue_root': '/synthetic/no-ue', 'python_executable': '/synthetic/no-python',
                'sessions': slots, 'budget': {'seconds': 100, 'bytes': 32 * 1024**2,
                    'cleanup_seconds': 3, 'spent_seconds': 0, 'spent_bytes': 0}}
        return {'card': card, 'session': 'initialize', 'output': storage / 'sessions/initialize',
                'card_hash': 'b' * 64, 'source': 'a' * 40, 'prior_seconds': 0,
                'argv': ['/bin/bash', '/synthetic/launcher', '--launch', '--viewport-preflush',
                         '--universe', '--owner-config', '/synthetic/private-owner',
                         '--user-dir', str(storage / 'sessions/initialize/user'), '--universe-initialize']}, run

    def process(self, run, *, running=False):
        process = mock.Mock()
        process.pid = 201
        process.poll.return_value = None if running else 0
        process.wait.return_value = -15 if running else 0
        if running:
            process.terminate.side_effect = lambda: setattr(process.poll, 'return_value', -15)
        def spawn(argv, **kwargs):
            self.assertIn('--universe', argv)
            self.assertIn('--owner-config', argv)
            self.assertIn('--viewport-preflush', argv)
            self.assertTrue(kwargs['start_new_session'])
            kwargs['stdout'].write(('[launcher] evidence=' + str(run) + '\n' +
                '[launcher] build_succeeded;\n[launcher] process_spawned pid=202; initialization_pending\n' +
                '[launcher] validated_observation_seen;\n[launcher] ue_exit_code=0\n').encode())
            kwargs['stdout'].flush()
            return process
        return process, spawn

    def owned(self):
        return {pid: {'pid': pid, 'ppid': parent, 'pgid': 201, 'start': 'synthetic-time', 'argv': argv}
                for pid, parent, argv in ((201, 100, 'mock-launcher'), (202, 201, 'mock-UE'),
                                          (203, 202, 'mock-worker'))}

    def test_runner_default_and_authorization_refuse_before_popen(self):
        with mock.patch.object(driver.subprocess, 'Popen') as popen:
            for execute, card, source in ((False, None, None), (True, None, 'a' * 40)):
                with self.assertRaises(oracle.Invalid):
                    driver.validate_run(card, None, source, 'initialize', execute)
            with mock.patch.object(sys, 'argv', ['driver']), mock.patch.object(driver, 'emit') as emit:
                self.assertEqual(driver.main(), 0)
                self.assertFalse(emit.call_args.args[0]['runtime_authorized'])
            popen.assert_not_called()

    def test_runner_mock_launcher_parent_wait_and_seal(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, run = self.prepared(Path(temporary).resolve())
            process, spawn = self.process(run)
            with mock.patch.object(driver.subprocess, 'Popen', side_effect=spawn), \
                 mock.patch.object(driver, 'observed_processes', side_effect=[self.owned(), {}]), \
                 mock.patch.object(driver, 'inspect_trace', return_value={
                     'worker_exits': [{'worker_pid': 203, 'exit_code': 0}],
                     'transport_count': 1, 'frames': [{'host_pid': 202}]}):
                receipt = driver.supervise(prepared)
            self.assertTrue(receipt['normal'])
            self.assertEqual(receipt['launcher_wait_exit'], 0)
            self.assertEqual(receipt['ue_pid'], 202)
            process.wait.assert_called()
            process.terminate.assert_not_called()
            self.assertTrue((prepared['output'] / 'session-seal.json').is_file())
            self.assertFalse(Path(prepared['card']['authority_root']).exists())

    def test_runner_existing_output_refused_without_process(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, _ = self.prepared(Path(temporary).resolve())
            prepared['output'].parent.mkdir(mode=0o700)
            prepared['output'].mkdir(mode=0o700)
            marker = prepared['output'] / 'preserve'
            marker.write_bytes(b'keep')
            with mock.patch.object(driver.subprocess, 'Popen') as popen:
                with self.assertRaises(FileExistsError):
                    driver.supervise(prepared)
                popen.assert_not_called()
            self.assertEqual(marker.read_bytes(), b'keep')

    def test_runner_byte_budget_failure_cleans_only_parent(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, run = self.prepared(Path(temporary).resolve())
            process, spawn = self.process(run, running=True)
            with mock.patch.object(driver.subprocess, 'Popen', side_effect=spawn), \
                 mock.patch.object(driver, 'observed_processes', return_value={}), \
                 mock.patch.object(driver, 'tree_bytes', return_value=prepared['card']['budget']['bytes']), \
                 mock.patch.object(driver, 'inspect_trace', return_value={'worker_exits': [], 'transport_count': 0, 'frames': []}), \
                 mock.patch.object(driver.os, 'kill') as kill:
                receipt = driver.supervise(prepared)
            self.assertFalse(receipt['normal'])
            self.assertIn('byte budget', receipt['failure'])
            process.terminate.assert_called_once()
            self.assertEqual(receipt['launcher_wait_exit'], -15)
            kill.assert_not_called()

    def test_runner_time_budget_failure_uses_actual_wait(self):
        for elapsed, message in ((100, 'time reserve'), (30, 'stage time exhausted: build')):
            with self.subTest(elapsed=elapsed), tempfile.TemporaryDirectory() as temporary:
                prepared, run = self.prepared(Path(temporary).resolve())
                process, spawn = self.process(run, running=True)
                with mock.patch.object(driver.subprocess, 'Popen', side_effect=spawn), \
                     mock.patch.object(driver, 'observed_processes', return_value={}), \
                     mock.patch.object(driver.time, 'monotonic', side_effect=[0, 0] + [elapsed] * 30), \
                     mock.patch.object(driver, 'inspect_trace', return_value={'worker_exits': [], 'transport_count': 0, 'frames': []}):
                    receipt = driver.supervise(prepared)
                self.assertFalse(receipt['normal'])
                self.assertIn(message, receipt['failure'])
                self.assertEqual(receipt['launcher_wait_exit'], -15)

    def test_runner_source_exact_untracked_allowlist_and_mapping_negative(self):
        with tempfile.TemporaryDirectory() as temporary:
            product = Path(temporary).resolve()
            generated = product / 'DefaultInput.ini'
            generated.write_bytes(b'synthetic-generated')
            allowed = {'DefaultInput.ini': {'kind': 'file', 'sha256': oracle.file_hash(generated),
                                            'provenance': 'synthetic source check'}}
            def git(status):
                return mock.patch.object(driver.subprocess, 'run', side_effect=[
                    mock.Mock(stdout='a' * 40 + '\n'), mock.Mock(stdout=status)])
            with git(b'?? DefaultInput.ini\0'):
                self.assertEqual(driver.product_identity(product, allowed), 'a' * 40)
            with git(b'?? other.py\0'), self.assertRaisesRegex(oracle.Invalid, 'unapproved untracked'):
                driver.product_identity(product, allowed)
            with git(b' M tracked.cpp\0'), self.assertRaisesRegex(oracle.Invalid, 'tracked product'):
                driver.product_identity(product, allowed)
            link = product / 'Saved'
            link.symlink_to(product / 'unexpected-target')
            changed = {'Saved': {'kind': 'symlink', 'readlink': '/Volumes/DevSSD/expected',
                                 'target': '/Volumes/DevSSD/expected', 'provenance': 'synthetic'}}
            with git(b'?? Saved\0'), self.assertRaisesRegex(oracle.Invalid, 'mapping changed'):
                driver.product_identity(product, changed)
            with self.assertRaisesRegex(oracle.Invalid, 'symlink'):
                driver.tree_bytes(product)

    def test_runner_cleanup_revalidates_identity_before_signaling(self):
        process = mock.Mock(pid=201)
        process.poll.return_value = 0
        process.wait.return_value = 0
        known = self.owned()
        changed = dict(known[203], start='different-start', argv='unrelated-process')
        with mock.patch.object(driver, 'observed_processes', return_value={203: changed}), \
             mock.patch.object(driver.time, 'monotonic', side_effect=[0, 2]), \
             mock.patch.object(driver.os, 'kill') as kill:
            _, actions = driver.cleanup_owned(process, known, 1)
        self.assertEqual(actions, [])
        kill.assert_not_called()

    def test_runner_wrong_product_sha_refuses_before_launcher(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary).resolve()
            now = datetime.now(timezone.utc)
            card = {'format': 'universe-i12-r12.v1', 'approved': True, 'issuer': 'root',
                    'scope': 'two-real-ue-owned-sessions', 'allow_forced_cleanup': True,
                    'issued_at': (now - timedelta(minutes=1)).isoformat(),
                    'expires_at': (now + timedelta(minutes=1)).isoformat(),
                    'product_source': 'a' * 40, 'run_id': 'synthetic', 'world_id': 'synthetic-world',
                    'accepted_gates': {'G-P1': 'synthetic', 'I10B': 'synthetic', 'G-B1': 'synthetic'},
                    'product_root': str(folder), 'allowed_untracked': {}}
            path = folder / 'synthetic-card.json'
            path.write_text(json.dumps(card))
            path.chmod(0o600)
            with mock.patch.object(driver, 'product_identity', return_value='b' * 40), \
                 mock.patch.object(driver.subprocess, 'Popen') as popen:
                with self.assertRaisesRegex(oracle.Invalid, 'product HEAD'):
                    driver.validate_run(path, oracle.file_hash(path), 'a' * 40, 'initialize', True)
                popen.assert_not_called()

    def valid_card(self, folder):
        prepared, run = self.prepared(folder)
        card = prepared['card']
        product = Path(card['product_root'])
        (product / 'scripts').mkdir(parents=True)
        launcher = product / 'scripts/launch_edgeworld_ue_mac.sh'
        launcher.write_text('# synthetic only, never executed: --universe --owner-config --universe-initialize -NoUBA\n')
        saved = product / 'engine_platforms/unreal/EdgeWorldHost/Saved'
        saved.mkdir(parents=True)
        (saved / 'MacLauncher').symlink_to(card['launcher_output_root'])
        deployment = Path(card['storage_root']) / 'deployment'
        deployment.mkdir(mode=0o700)
        key = folder / 'no-key-files-only-metadata'
        key.mkdir(mode=0o700)
        runtime = folder / 'never-executed-python'
        runtime.write_bytes(b'synthetic not executable code')
        runtime.chmod(0o700)
        ue = folder / 'no-UE-app'
        ue.mkdir()
        inputs = {}
        for role in ('build', 'options', 'assets', 'asset_audit'):
            path = deployment / (role + '.json')
            path.write_text(json.dumps({'domain': 'edgeworld.universe.authority', 'version': '0.2',
                'world_id': card['world_id'], 'kind': role, 'id': role, 'body': {}, 'refs': {}}))
            inputs[role] = {'path': str(path), 'sha256': oracle.file_hash(path)}
        context = {'world_id': card['world_id'], 'authority_root': card['authority_root'],
                   'trust_anchor': 'c' * 64, 'artifact_class': 'genesis-runtime',
                   'trust_algorithm': 'local-hmac-sha256.v0.2', 'domain_version': '0.2',
                   'archive_profile': 'composite-rigid-support.v0.2',
                   'storage_profile': 'local-posix-blob-sync-v0.2'}
        for role, name in (('build', 'expected_build'), ('options', 'expected_options')):
            context[name] = oracle.hashlib.sha256(oracle.PREFIX +
                oracle.canonical(oracle.read_json(inputs[role]['path']))).hexdigest()
        actions = ['retain_snapshot', 'physics_step']
        for mode in ('initialize', 'existing'):
            owner = {'config_version': 'universe-owner-launch.v0.1', 'mode': mode,
                     'context': context, 'session': {'principal': 'synthetic-owner',
                     'can_initialize': mode == 'initialize', 'allowed_actions': actions},
                     'key_dir': str(key), 'scratch': str(Path(card['storage_root']) / 'not-created-scratch'),
                     'inputs': inputs}
            path = deployment / (mode + '-owner.json')
            path.write_text(json.dumps(owner)); path.chmod(0o600)
            card['sessions'][mode]['owner_config'] = {'path': str(path), 'sha256': oracle.file_hash(path)}
        now = datetime.now(timezone.utc)
        card.update(format='universe-i12-r12.v1', approved=True, issuer='root',
                    scope='two-real-ue-owned-sessions', allow_forced_cleanup=True,
                    issued_at=(now - timedelta(minutes=1)).isoformat(),
                    expires_at=(now + timedelta(minutes=5)).isoformat(), product_source='a' * 40,
                    launcher_sha256=oracle.file_hash(launcher), allowed_untracked={},
                    accepted_gates={'G-P1': 'mock', 'I10B': 'mock', 'G-B1': 'mock'},
                    deployment_root=str(deployment), inputs=inputs, context=context,
                    key_directory=str(key), principal='synthetic-owner', allowed_actions=actions,
                    python_executable=str(runtime), ue_root=str(ue),
                    runtime_files=[{'path': str(runtime), 'sha256': oracle.file_hash(runtime)}])
        path = folder / 'synthetic-r12-card.json'
        path.write_text(json.dumps(card)); path.chmod(0o600)
        return card, path, run

    def test_runner_fixed_full_valid_card_two_session_protocol(self):
        with tempfile.TemporaryDirectory() as temporary:
            card, path, run = self.valid_card(Path(temporary).resolve())
            with mock.patch.object(driver, 'on_devssd', return_value=True), \
                 mock.patch.object(driver, 'product_identity', return_value='a' * 40):
                prepared = driver.validate_run(path, oracle.file_hash(path), 'a' * 40, 'initialize', True)
                self.assertIn('--universe-initialize', prepared['argv'])
                process, spawn = self.process(run)
                def initialized(argv, **kwargs):
                    # Stand-in marker only, not a registered or Store-readable authority.
                    authority = Path(card['authority_root']); authority.mkdir(mode=0o700)
                    (authority / 'HEAD.json').write_bytes(b'{"synthetic-only":true}')
                    return spawn(argv, **kwargs)
                with mock.patch.object(driver.subprocess, 'Popen', side_effect=initialized), \
                     mock.patch.object(driver, 'observed_processes', side_effect=[self.owned(), {}]), \
                     mock.patch.object(driver, 'inspect_trace', return_value={
                         'worker_exits': [{'worker_pid': 203, 'exit_code': 0}],
                         'transport_count': 1, 'frames': [{'host_pid': 202}]}):
                    complete = driver.supervise(prepared)
                self.assertTrue(complete['normal'])
                self.assertFalse(oracle.read_json(prepared['output'] / 'supervisor-exit.json')['normal'])
                self.assertEqual(complete['final_bytes_including_completion'], driver.tree_bytes(card['storage_root']))
                existing = driver.validate_run(path, oracle.file_hash(path), 'a' * 40, 'existing', True)
                self.assertNotIn('--universe-initialize', existing['argv'])
                self.assertIn(card['sessions']['existing']['owner_config']['path'], existing['argv'])
                self.assertEqual(existing['prior_seconds'], complete['cumulative_seconds'])

    def test_runner_fixed_stale_owner_inputs_mode_world_root_rejected(self):
        for mutation, message in (('inputs', 'owner inputs'), ('mode', 'session mode'),
                                  ('world_id', 'owner context'), ('authority_root', 'owner context')):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                card, path, _ = self.valid_card(Path(temporary).resolve())
                owner_path = Path(card['sessions']['initialize']['owner_config']['path'])
                owner = oracle.read_json(owner_path)
                if mutation == 'inputs':
                    owner['inputs']['build']['path'] = '/old/deleted-worktree/build.json'
                elif mutation == 'mode':
                    owner['mode'] = 'existing'
                else:
                    owner['context'][mutation] = 'wrong-world' if mutation == 'world_id' else '/wrong/root'
                owner_path.write_text(json.dumps(owner))
                # Both hashes are individually valid: only cross-check can catch stale metadata.
                card['sessions']['initialize']['owner_config']['sha256'] = oracle.file_hash(owner_path)
                path.write_text(json.dumps(card))
                with mock.patch.object(driver, 'on_devssd', return_value=True), \
                     mock.patch.object(driver, 'product_identity', return_value='a' * 40), \
                     mock.patch.object(driver.subprocess, 'Popen') as popen:
                    with self.assertRaisesRegex(oracle.Invalid, message):
                        driver.validate_run(path, oracle.file_hash(path), 'a' * 40, 'initialize', True)
                    popen.assert_not_called()

    def test_runner_fixed_log_io_finally_cleans_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            prepared, run = self.prepared(Path(temporary).resolve())
            process, spawn = self.process(run, running=True)
            original = driver.os.fdopen
            class FailedEvents:
                def __init__(self, stream): self.stream = stream
                def write(self, value): raise OSError('synthetic original disk-full write')
                def flush(self): raise OSError('synthetic flush failure')
                def close(self):
                    self.stream.close()
                    raise OSError('synthetic secondary close failure')
            def fdopen(fd, mode):
                stream = original(fd, mode)
                return FailedEvents(stream) if mode == 'w' else stream
            with mock.patch.object(driver.os, 'fdopen', side_effect=fdopen), \
                 mock.patch.object(driver.subprocess, 'Popen', side_effect=spawn), \
                 mock.patch.object(driver, 'observed_processes', return_value={}), \
                 mock.patch.object(driver.os, 'kill') as kill:
                result = driver.supervise(prepared)
            process.terminate.assert_called_once()
            process.wait.assert_called()
            kill.assert_not_called()
            self.assertFalse(result['normal'])
            self.assertIn('original disk-full write', result['failure'])

    def test_runner_fixed_live_counter_only_tolerates_enoent(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            (root / 'stable').write_bytes(b'ab')
            (root / 'renamed.tmp').write_bytes(b'ignored-after-rename')
            original = Path.lstat
            def renamed(path):
                if path.name == 'renamed.tmp': raise FileNotFoundError(path)
                return original(path)
            with mock.patch.object(Path, 'lstat', renamed):
                self.assertEqual(driver.tree_bytes(root), 2)
            def denied(path):
                if path.name == 'stable': raise PermissionError(path)
                return original(path)
            with mock.patch.object(Path, 'lstat', denied), self.assertRaises(PermissionError):
                driver.tree_bytes(root)

    def test_runner_fixed_seal_time_bytes_prevent_existing_admission(self):
        for kind in ('time', 'bytes'):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temporary:
                card, path, run = self.valid_card(Path(temporary).resolve())
                if kind == 'bytes':
                    card['budget']['bytes'] = 2 * 1024**2
                    path.write_text(json.dumps(card))
                clock = [0]
                emit = driver.emit
                def delayed_emit(value, output):
                    emit(value, output)
                    if output.name == 'session-seal.json':
                        if kind == 'time': clock[0] = 60
                        else: (output.parent / 'synthetic-seal-growth').write_bytes(b'x' * (2 * 1024**2))
                with mock.patch.object(driver, 'on_devssd', return_value=True), \
                     mock.patch.object(driver, 'product_identity', return_value='a' * 40):
                    prepared = driver.validate_run(path, oracle.file_hash(path), 'a' * 40, 'initialize', True)
                    process, spawn = self.process(run)
                    with mock.patch.object(driver.subprocess, 'Popen', side_effect=spawn), \
                         mock.patch.object(driver, 'observed_processes', side_effect=[self.owned(), {}]), \
                         mock.patch.object(driver, 'inspect_trace', return_value={
                             'worker_exits': [{'worker_pid': 203, 'exit_code': 0}],
                             'transport_count': 1, 'frames': [{'host_pid': 202}]}), \
                         mock.patch.object(driver.time, 'monotonic', side_effect=lambda: clock[0]), \
                         mock.patch.object(driver, 'emit', side_effect=delayed_emit):
                        result = driver.supervise(prepared)
                    self.assertFalse(result['normal'])
                    self.assertFalse(oracle.read_json(prepared['output'] / 'supervisor-exit.json')['normal'])
                    with self.assertRaises((oracle.Invalid, FileNotFoundError)):
                        driver.validate_run(path, oracle.file_hash(path), 'a' * 40, 'existing', True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
