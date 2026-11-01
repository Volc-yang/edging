"""Finite neutral-v0.1 storage checks; injected faults do not model power loss."""
from copy import deepcopy
from dataclasses import replace
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from engine.universe_authority.codec import (ContractError, DeploymentContext, OwnerSession,
                                              ProvisionSpec, canonical, digest)
from engine.universe_authority.ownership import acquire
from engine.universe_authority.records import validate_closure
from engine.universe_authority.store import BlobWrite, CommitBundle, PinnedRoot, Store, StoreError
from engine.universe_authority.trust import open_trust, provision

_FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_1'
_COMPOSITE = _FIXTURES.parent / 'universe_authority_v0_2'
_MODULE = 'engine.universe_authority.store'


def evidence(case, data):
    """Append original live observations only to the runner's precreated log."""
    destination = os.environ.get('EDGEWORLD_I3_FAULT_LOG')
    if destination:
        raw = (json.dumps({'case': case, 'pid': os.getpid(), **data}, sort_keys=True) + '\n').encode('utf-8')
        descriptor = os.open(destination, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW | os.O_CLOEXEC)
        try:
            remaining = memoryview(raw)
            while remaining:
                count = os.write(descriptor, remaining)
                if count <= 0:
                    raise OSError('evidence append made no progress')
                remaining = remaining[count:]
        finally:
            os.close(descriptor)


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='universe-i3-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.archive = json.loads((_FIXTURES / 'positive.json').read_bytes())
        self.trust = json.loads((_FIXTURES / 'trusted_receipts.json').read_bytes())
        self.hashes = {row['id']: row['sha256'] for row in json.loads((_FIXTURES / 'golden.json').read_bytes())}
        self.records = self.archive['records']
        self.world = 'fixture-world'

    def expect_code(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    def root_map(self, root):
        result = {}
        for path in sorted(root.rglob('*')):
            info = path.lstat()
            item = {'bytes': info.st_size, 'inode': str(info.st_ino), 'links': info.st_nlink}
            if stat.S_ISREG(info.st_mode):
                raw = path.read_bytes()
                item['sha256'] = hashlib.sha256(raw).hexdigest()
                item['raw_hex'] = raw.hex()
            elif path.is_symlink():
                item['target'] = os.readlink(path)
            result[str(path.relative_to(root))] = item
        return result

    def new(self, label='authority', fault=None):
        root = self.base / label
        lease = acquire(root, self.world, initialize=True)
        self.addCleanup(lease.close)
        store = Store(lease, trusted_receipts=self.trust, fault=fault)
        self.addCleanup(store.close)
        return root, lease, store

    def initialized(self, label='authority', fault=None):
        root, lease, store = self.new(label, fault)
        receipt = store.initialize(deepcopy(self.records[:2]), self.hashes['m0'])
        self.assertEqual(receipt.manifest, self.hashes['m0'])
        self.assertIsNone(receipt.result)
        self.assertEqual(receipt.commit_status, 'confirmed')
        self.assertEqual(store.state, 'ready')
        return root, lease, store

    def bundle(self, step=1, **changes):
        start = 2 + (step - 1) * 11
        values = dict(expected_head=self.hashes[f'm{step-1}'], records=tuple(deepcopy(self.records[start:start+11])),
                      head=self.hashes[f'm{step}'], principal='fixture-principal',
                      command_id=f'command-{step}', fingerprint=self.hashes[f'c{step}'])
        values.update(changes)
        return CommitBundle(**values)

    def recover(self, store):
        pinned = store.pin()
        closure = validate_closure([json.loads(raw) for raw in pinned.objects.values()], pinned.head,
                                   world_id=store.world_id, trusted_receipts=store.trusted_receipts)
        return store.confirm_recovery(pinned, closure)

    def test_constructor_and_close_are_no_io_and_do_not_close_lease(self):
        root, lease, store = self.new()
        before = self.root_map(root)
        self.assertEqual(store.state, 'uninitialized')
        with mock.patch(_MODULE + '.os.open', side_effect=AssertionError('constructor performed I/O')):
            self.expect_code('LOCKED', Store, lease, trusted_receipts=self.trust)
            store.close()
            another = Store(lease, trusted_receipts=self.trust)
            self.assertEqual(another.state, 'uninitialized')
            another.close()
        self.assertEqual(self.root_map(root), before)
        lease.check()
        store.close(); store.close()
        self.expect_code('CLOSED', store.snapshot)
        self.expect_code('CLOSED', store.pin)
        lease.check()

    def test_initialize_explicit_exact_genesis_only(self):
        root, _, store = self.new()
        before = self.root_map(root)
        self.expect_code('NOT_READY', store.snapshot)
        self.expect_code('NOT_READY', store.commit, self.bundle())
        self.expect_code('SCHEMA', store.initialize, self.records, self.hashes['m2'])
        self.assertEqual(self.root_map(root), before)
        store.initialize(self.records[:2], self.hashes['m0'])
        self.expect_code('NOT_READY', store.initialize, self.records[:2], self.hashes['m0'])
        self.assertEqual(store.snapshot().closure.retained, (self.hashes['m0'],))

    def test_noninitializing_lease_cannot_initialize(self):
        root, lease, store = self.new()
        store.close(); lease.close()
        read_lease = acquire(root, self.world)
        self.addCleanup(read_lease.close)
        read_store = Store(read_lease, trusted_receipts=self.trust)
        before = self.root_map(root)
        self.expect_code('NOT_READY', read_store.initialize, self.records[:2], self.hashes['m0'])
        self.expect_code('UNINITIALIZED', read_store.pin)
        self.assertEqual(self.root_map(root), before)

    def test_commit_and_lookup_are_exact_and_defensive(self):
        root, _, store = self.initialized()
        bundle = self.bundle()
        original = deepcopy(bundle.records)
        receipt = store.commit(bundle)
        self.assertEqual(receipt.result, self.records[10])
        self.assertEqual(store.snapshot().closure.retained, (self.hashes['m1'], self.hashes['m0']))
        receipt.result['body']['revision'] = 999
        returned = store.lookup_result('fixture-principal', 'command-1', self.hashes['c1'])
        self.assertEqual(returned['body']['revision'], 1)
        returned['body']['revision'] = 999
        snapshot = store.snapshot()
        snapshot.closure.records[self.hashes['s1']]['body']['value'] = {'$f64': '0'*16}
        self.assertEqual(store.lookup_result('fixture-principal', 'command-1', self.hashes['c1']), self.records[10])
        self.assertIsNone(store.lookup_result('fixture-principal', 'absent', self.hashes['c1']))
        self.expect_code('COMMAND_CONFLICT', store.lookup_result, 'fixture-principal', 'command-1', '0'*64)
        self.assertEqual(bundle.records, original)
        head = json.loads((root / 'HEAD.json').read_bytes())
        self.assertEqual(head['manifest'], self.hashes['m1'])
        for record in self.records[:13]:
            self.assertEqual((root / 'objects' / (digest(record) + '.json')).read_bytes(), canonical(record))

    def test_full_assembled_closure_validated_before_writes(self):
        root, _, store = self.initialized()
        before = self.root_map(root)
        self.expect_code('HEAD', store.commit, self.bundle(expected_head='0'*64))
        self.expect_code('COMMAND_CONFLICT', store.commit, self.bundle(fingerprint='0'*64))
        self.expect_code('REFERENCE', store.commit, self.bundle(records=tuple(self.records[3:13])))
        self.assertEqual(self.root_map(root), before)
        self.assertEqual(store.state, 'ready')

    def test_bad_existing_digest_object_is_not_overwritten(self):
        root, _, store = self.initialized()
        target = root / 'objects' / (self.hashes['p1'] + '.json')
        target.write_bytes(b'partial old orphan')
        before = self.root_map(root)
        error = self.expect_code('CORRUPT', store.commit, self.bundle())
        self.assertEqual(error.commit_status, 'not_attempted')
        self.assertEqual(store.state, 'corrupt')
        self.expect_code('NOT_READY', store.snapshot)
        self.assertEqual(self.root_map(root), before)

    def test_existing_exact_uncommitted_objects_can_be_synchronized(self):
        root, _, store = self.initialized()
        target = root / 'objects' / (self.hashes['p1'] + '.json')
        target.write_bytes(canonical(self.records[2]))
        inode = target.stat().st_ino
        store.commit(self.bundle())
        self.assertEqual(target.stat().st_ino, inode)
        self.assertEqual(store.state, 'ready')

    def test_public_fault_matrix_pre_and_post_visibility(self):
        phases = ('W2_OBJECT_FILE_SYNCED', 'W3_OBJECTS_DIR_SYNCED', 'W4_HEAD_FILE_SYNCED',
                  'W5_BEFORE_REPLACE', 'W6_AFTER_REPLACE', 'W7_ROOT_SYNCED', 'W8_BEFORE_RESPONSE')
        for index, target in enumerate(phases):
            with self.subTest(phase=target):
                armed = False
                trace = []
                def hook(phase, context):
                    if armed:
                        trace.append({'phase': phase, 'context': dict(context)})
                    if armed and phase == target:
                        if phase == 'W2_OBJECT_FILE_SYNCED' and context['object_digest'] in (self.hashes['s0'], self.hashes['m0']):
                            return
                        raise OSError(errno.EIO, 'injected ' + phase)
                root, _, store = self.initialized('fault-' + str(index), hook)
                before = self.root_map(root)
                armed = True
                error = self.expect_code('IO_BEFORE_VISIBILITY' if index < 3 else 'COMMIT_UNKNOWN', store.commit, self.bundle())
                self.assertIsInstance(error, StoreError)
                self.assertEqual(error.phase, target)
                self.assertEqual(error.commit_status, 'not_attempted' if index < 3 else 'unknown')
                self.assertEqual(store.state, 'ready' if index < 3 else 'recovering')
                self.assertEqual(trace[-1]['context']['visibility_attempted'], index >= 3)
                after_failure = self.root_map(root)
                if index >= 3:
                    self.expect_code('NOT_READY', store.snapshot)
                    self.expect_code('NOT_READY', store.commit, self.bundle())
                    self.assertEqual(self.root_map(root), after_failure)
                else:
                    self.assertEqual(store.snapshot().closure.head, self.hashes['m0'])
                armed = False
                snapshot = self.recover(store)
                expected = self.hashes['m0' if index < 4 else 'm1']
                self.assertEqual(snapshot.closure.head, expected)
                self.assertEqual(store.state, 'ready')
                result = store.lookup_result('fixture-principal', 'command-1', self.hashes['c1'])
                self.assertEqual(result is None, index < 4)
                evidence(target, {'before': before, 'after_fault': after_failure,
                                  'after_recovery': self.root_map(root), 'trace': trace,
                                  'error': {'code': error.code, 'phase': error.phase, 'commit_status': error.commit_status},
                                  'recovered_manifest': expected, 'result_found': result is not None})

    def test_replace_exception_is_unknown_even_with_unchanged_head(self):
        root, _, store = self.initialized()
        with mock.patch(_MODULE + '.os.replace', side_effect=OSError(errno.EIO, 'injected replace failure')):
            error = self.expect_code('COMMIT_UNKNOWN', store.commit, self.bundle())
        self.assertEqual(error.commit_status, 'unknown')
        self.assertEqual(store.state, 'recovering')
        self.expect_code('NOT_READY', store.snapshot)
        self.assertEqual(json.loads((root / 'HEAD.json').read_bytes())['manifest'], self.hashes['m0'])
        self.recover(store)
        self.assertIsNone(store.lookup_result('fixture-principal', 'command-1', self.hashes['c1']))
        evidence('replace-oserror', {'error': {'code': error.code, 'commit_status': error.commit_status},
                                    'after_recovery': self.root_map(root)})

    def test_actual_file_directory_sync_order_and_recovery_order(self):
        root, _, store = self.initialized()
        calls = []
        real_sync, real_replace = os.fsync, os.replace
        def sync(descriptor):
            calls.append(('sync', str(os.fstat(descriptor).st_ino)))
            return real_sync(descriptor)
        def replace(*args, **kwargs):
            calls.append(('replace', None))
            return real_replace(*args, **kwargs)
        with mock.patch(_MODULE + '.os.fsync', side_effect=sync), \
                mock.patch(_MODULE + '.os.replace', side_effect=replace):
            store.commit(self.bundle())
        boundary = calls.index(('replace', None))
        head_inode = str((root / 'HEAD.json').stat().st_ino)
        root_inode = str(root.stat().st_ino)
        self.assertEqual(calls[boundary-1], ('sync', head_inode))
        self.assertEqual(calls[boundary+1:], [('sync', root_inode)])
        committed_calls = list(calls)
        calls.clear()
        with mock.patch(_MODULE + '.os.fsync', side_effect=sync):
            snapshot = self.recover(store)
        object_inodes = {str((root / 'objects' / (key + '.json')).stat().st_ino)
                         for key in snapshot.closure.records}
        self.assertEqual({inode for _, inode in calls[:-3]}, object_inodes)
        self.assertEqual(len(calls[:-3]), len(object_inodes))
        self.assertEqual(calls[-3:], [('sync', str((root / 'objects').stat().st_ino)),
                                     ('sync', head_inode), ('sync', root_inode)])
        evidence('sync-order', {'commit_calls': committed_calls, 'recovery_calls': calls,
                                'head_inode': head_inode, 'root_inode': root_inode})

    def test_hook_cannot_reenter_write_or_close_active_store(self):
        armed = False
        errors = []
        store = None
        def hook(phase, context):
            if armed and phase == 'W1_VALIDATED':
                for function, args in ((store.commit, (self.bundle(),)), (store.close, ())):
                    error = self.expect_code('LOCKED', function, *args)
                    errors.append({'code': error.code, 'phase': error.phase})
        root, _, store = self.initialized(fault=hook)
        armed = True
        receipt = store.commit(self.bundle())
        self.assertEqual(len(errors), 2)
        self.assertEqual(receipt.manifest, self.hashes['m1'])
        self.assertEqual(store.state, 'ready')
        store.close()
        self.expect_code('CLOSED', store.snapshot)
        evidence('nonreentrant-store', {'errors': errors, 'map': self.root_map(root)})

    def test_actual_sync_failure_stops_writes_before_visibility(self):
        root, _, store = self.initialized()
        before = self.root_map(root)
        with mock.patch(_MODULE + '.os.fsync', side_effect=OSError(errno.EIO, 'injected actual fsync failure')):
            error = self.expect_code('SYNC_UNSUPPORTED', store.commit, self.bundle())
            self.assertEqual(error.commit_status, 'not_attempted')
            self.assertEqual(store.state, 'recovering')
            self.expect_code('NOT_READY', store.snapshot)
            self.expect_code('NOT_READY', store.commit, self.bundle())
            self.expect_code('SYNC_UNSUPPORTED', self.recover, store)
            self.assertEqual(store.snapshot().storage_state, 'unconfirmed_readonly')
            self.expect_code('NOT_READY', store.commit, self.bundle())
        self.assertEqual(self.root_map(root), before)
        self.recover(store)
        self.assertEqual(store.state, 'ready')
        evidence('actual-sync-failure', {'error_code': error.code, 'before': before,
                                        'after': self.root_map(root), 'recovered_state': store.state})

    def test_pin_integrity_does_not_establish_ready_or_write_files(self):
        root, lease, store = self.initialized()
        store.commit(self.bundle()); store.commit(self.bundle(2)); store.close()
        reader = Store(lease, trusted_receipts=self.trust)
        before = self.root_map(root)
        pinned = reader.pin()
        self.assertEqual(pinned.head, self.hashes['m2'])
        self.assertEqual(len(pinned.objects), 24)
        self.assertEqual(reader.state, 'recovering')
        self.expect_code('NOT_READY', reader.snapshot)
        self.assertEqual(self.root_map(root), before)
        closure = validate_closure([json.loads(raw) for raw in pinned.objects.values()], pinned.head,
                                   world_id=self.world, trusted_receipts=reader.trusted_receipts)
        snapshot = reader.confirm_recovery(pinned, closure)
        self.assertEqual(snapshot.storage_state, 'ready')
        self.assertEqual(snapshot.closure.retained, (self.hashes['m2'], self.hashes['m1'], self.hashes['m0']))
        self.assertEqual(self.root_map(root), before)

    def test_malformed_or_wrong_profile_head_is_rejected_without_fallback(self):
        for index, mode in enumerate(('duplicate', 'profile', 'newline', 'unknown')):
            with self.subTest(mode=mode):
                root, _, store = self.initialized('head-' + str(index))
                path = root / 'HEAD.json'
                raw = path.read_bytes()
                if mode == 'duplicate':
                    raw = raw[:-1] + b',"domain":"edgeworld.universe.authority"}'
                elif mode == 'newline':
                    raw += b'\n'
                else:
                    value = json.loads(raw)
                    value['profile' if mode == 'profile' else 'unexpected'] = 'wrong'
                    raw = canonical(value)
                path.write_bytes(raw)
                before = self.root_map(root)
                self.expect_code('CORRUPT', store.pin)
                self.expect_code('NOT_READY', store.snapshot)
                self.assertEqual(self.root_map(root), before)
                evidence('malformed-head-' + mode, {'map': before, 'state': store.state})

    def test_old_history_corruption_or_missing_checkpoint_blocks_all_reads(self):
        for index, (identifier, remove) in enumerate((('s0', False), ('q1', True))):
            with self.subTest(identifier=identifier):
                root, _, store = self.initialized('history-' + str(index))
                store.commit(self.bundle()); store.commit(self.bundle(2))
                target = root / 'objects' / (self.hashes[identifier] + '.json')
                if remove:
                    target.unlink()
                else:
                    target.write_bytes(b'{}')
                before = self.root_map(root)
                error = self.expect_code('CORRUPT', store.pin)
                self.assertEqual(store.state, 'corrupt')
                self.expect_code('NOT_READY', store.snapshot)
                self.expect_code('NOT_READY', store.commit, self.bundle())
                self.assertEqual(self.root_map(root), before)
                evidence('bad-history-' + identifier, {'error_code': error.code, 'map': before, 'state': store.state})

    def test_orphan_result_never_enters_recovered_idempotency_table(self):
        root, _, store = self.initialized()
        for record in self.records[2:]:
            (root / 'objects' / (digest(record) + '.json')).write_bytes(canonical(record))
        before = self.root_map(root)
        snapshot = self.recover(store)
        self.assertEqual(len(snapshot.closure.records), 2)
        self.assertEqual(dict(snapshot.closure.commands), {})
        self.assertIsNone(store.lookup_result('fixture-principal', 'command-1', self.hashes['c1']))
        self.assertEqual(self.root_map(root), before)

    def test_recovery_rechecks_pinned_bytes_and_untrusted_closure(self):
        root, _, store = self.initialized()
        pinned = store.pin()
        closure = validate_closure(self.records[:2], self.hashes['m0'], world_id=self.world, trusted_receipts=self.trust)
        forged = PinnedRoot(pinned.head, pinned.head_bytes + b'\n', pinned.objects)
        self.expect_code('CORRUPT', store.confirm_recovery, forged, closure)
        self.expect_code('NOT_READY', store.snapshot)
        self.recover(store)
        pinned = store.pin()
        (root / 'objects' / (self.hashes['s0'] + '.json')).write_bytes(b'{}')
        self.expect_code('CORRUPT', store.confirm_recovery, pinned, closure)
        self.expect_code('NOT_READY', store.snapshot)

    def test_w9_failure_is_explicit_fresh_unconfirmed_readonly(self):
        armed = False
        trace = []
        def hook(phase, context):
            if armed:
                trace.append({'phase': phase, 'context': dict(context)})
            if armed and phase == 'W9_RECOVERY_SYNCED':
                raise OSError(errno.EIO, 'injected recovery confirmation failure')
        root, _, store = self.initialized(fault=hook)
        store.commit(self.bundle())
        armed = True
        error = self.expect_code('SYNC_UNSUPPORTED', self.recover, store)
        self.assertEqual(error.commit_status, 'unknown')
        self.assertEqual(store.state, 'unconfirmed_readonly')
        self.assertEqual(store.snapshot().closure.head, self.hashes['m1'])
        self.assertEqual(store.snapshot().storage_state, 'unconfirmed_readonly')
        self.expect_code('NOT_READY', store.commit, self.bundle(2))
        self.expect_code('NOT_READY', store.lookup_result, 'fixture-principal', 'command-1', self.hashes['c1'])
        evidence('W9_RECOVERY_SYNCED', {'trace': trace, 'map': self.root_map(root), 'state': store.state,
                                       'error': {'code': error.code, 'commit_status': error.commit_status}})
        armed = False
        self.recover(store)
        self.assertEqual(store.state, 'ready')

    def test_reference_removed_during_recovery_sync_is_corrupt_not_unconfirmed(self):
        root = None
        armed = False
        def hook(phase, context):
            if armed and phase == 'RECOVERY_VALIDATED':
                (root / 'objects' / (self.hashes['s0'] + '.json')).unlink()
        root, _, store = self.initialized(fault=hook)
        armed = True
        self.expect_code('CORRUPT', self.recover, store)
        self.assertEqual(store.state, 'corrupt')
        self.expect_code('NOT_READY', store.snapshot)

    def test_closed_lease_or_replaced_root_invalidates_cached_ready(self):
        root, lease, store = self.initialized()
        lease.close()
        self.expect_code('CLOSED', store.commit, self.bundle())
        self.expect_code('CLOSED', store.snapshot)
        root, _, store = self.initialized('replacement')
        root.rename(self.base / 'moved-root')
        root.mkdir()
        self.expect_code('ROOT_MISMATCH', store.commit, self.bundle())
        self.assertEqual(store.state, 'corrupt')
        self.expect_code('NOT_READY', store.snapshot)

    def test_ready_snapshot_and_lookup_have_no_io_or_mutation(self):
        root, _, store = self.initialized()
        store.commit(self.bundle())
        before = self.root_map(root)
        with mock.patch(_MODULE + '.os.open', side_effect=AssertionError('cache read performed I/O')):
            self.assertEqual(store.snapshot().storage_state, 'ready')
            self.assertIsNotNone(store.lookup_result('fixture-principal', 'command-1', self.hashes['c1']))
            trusted = store.trusted_receipts
            trusted['approval-1']['principal'] = 'mutated'
            self.assertEqual(store.trusted_receipts['approval-1']['principal'], 'fixture-principal')
        self.assertEqual(self.root_map(root), before)

    def test_internal_hardlink_and_symlink_objects_are_rejected(self):
        for index, hard in enumerate((False, True)):
            root, _, store = self.initialized('link-' + str(index))
            path = root / 'objects' / (self.hashes['p1'] + '.json')
            target = self.base / ('target-' + str(index))
            target.write_bytes(canonical(self.records[2]))
            if hard:
                os.link(target, path)
                self.expect_code('CORRUPT', store.commit, self.bundle())
            else:
                path.symlink_to(target)
                self.expect_code('IO_BEFORE_VISIBILITY', store.commit, self.bundle())
            self.assertEqual(target.read_bytes(), canonical(self.records[2]))
            self.assertEqual(json.loads((root / 'HEAD.json').read_bytes())['manifest'], self.hashes['m0'])

class CompositeStoreTests(unittest.TestCase):
    expect_code = StoreTests.expect_code
    root_map = StoreTests.root_map

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='universe-e3-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.template = json.loads((_COMPOSITE / 'positive.json').read_bytes())['records']
        self.template_context = json.loads((_COMPOSITE / 'trust_context.json').read_bytes())
        self.raw = {key: bytes.fromhex(value) for key, value in
                    json.loads((_COMPOSITE / 'synthetic_blobs.json').read_bytes())['blobs'].items()}

    def new(self, label='world', fault=None):
        root = self.base / label
        key_dir = self.base / (label + '-key')
        anchor = provision(key_dir, spec=ProvisionSpec('composite-demo', root))
        context = DeploymentContext(
            'composite-demo', str(root), anchor.trust_anchor,
            self.template_context['expected_build'], self.template_context['expected_options'],
            artifact_class='synthetic-contract-only')
        signer = open_trust(key_dir, context=context, signing=True,
                            session=OwnerSession('fixture-principal', True,
                                                 ('retain_snapshot', 'physics_step')))
        verifier = open_trust(key_dir, context=context)
        remap = {}
        def rewrite(value):
            if type(value) is str:
                return remap.get(value, value)
            if type(value) is list:
                return [rewrite(v) for v in value]
            if type(value) is dict:
                return {key: rewrite(v) for key, v in value.items()}
            return value
        self.records = []
        for original in self.template:
            record = rewrite(original)
            if record['kind'] in ('approval', 'admission'):
                del record['body']['auth_tag']
                record = (signer.sign_approval(record) if record['kind'] == 'approval'
                          else signer.sign_admission(record))
            remap[digest(original)] = digest(record)
            self.records.append(record)
        self.hashes = {r['id']: digest(r) for r in self.records}
        self.context = context
        self.verifier = verifier
        self.signer = signer
        lease = acquire(root, context.world_id, initialize=True, domain_version='0.2',
                        profile=context.storage_profile, context=context)
        self.addCleanup(lease.close)
        store = Store(lease, context=context, trust_verifier=verifier, fault=fault)
        self.addCleanup(store.close)
        return root, lease, store

    def blobs_for(self, records):
        return tuple(BlobWrite(r['body']['payload_sha256'], self.raw[r['body']['payload_sha256']],
                               r['body']['media_type'], r['body']['artifact_class'])
                     for r in records if r['kind'] == 'checkpoint_descriptor')

    def initialized(self, label='world', fault=None):
        root, lease, store = self.new(label, fault)
        receipt = store.initialize(self.records[:31], self.hashes['manifest-0'],
                                   blobs=self.blobs_for(self.records[:31]))
        self.assertEqual(receipt.manifest, self.hashes['manifest-0'])
        return root, lease, store

    def bundle(self, step=1, **changes):
        boundaries = ((31, 42), (42, 56), (56, 67))
        start, end = boundaries[step - 1]
        values = dict(expected_head=self.hashes[f'manifest-{step-1}'],
                      records=tuple(deepcopy(self.records[start:end])),
                      head=self.hashes[f'manifest-{step}'], principal='fixture-principal',
                      command_id=f'command-{step}', fingerprint=self.hashes[f'command-record-{step}'],
                      blobs=self.blobs_for(self.records[start:end]))
        values.update(changes)
        return CommitBundle(**values)

    def validate(self, pinned):
        return validate_closure([json.loads(raw) for raw in pinned.objects.values()],
                                pinned.head, world_id=self.context.world_id,
                                domain_version='0.2', context=self.context,
                                trust_verifier=self.verifier, blobs=pinned.blobs)

    def recover(self, store):
        pinned = store.pin()
        return store.confirm_recovery(pinned, self.validate(pinned))

    def advance_all(self, store):
        for step in (1, 2, 3):
            store.commit(self.bundle(step))

    def test_constructor_capabilities_context_and_no_io(self):
        root, lease, store = self.new()
        store.close()
        before = self.root_map(root)
        with mock.patch(_MODULE + '.os.open', side_effect=AssertionError('constructor I/O')):
            self.expect_code('AUTHORIZATION', Store, lease, context=self.context,
                             trust_verifier=self.signer)
            self.expect_code('AUTHORIZATION', Store, lease, context=self.context,
                             trust_verifier=self.verifier, trusted_receipts={})
            self.expect_code('AUTHORIZATION', Store, lease, context=self.context)
            self.expect_code('ROOT_MISMATCH', Store, lease, trust_verifier=self.verifier,
                             context=replace(self.context, expected_build='d' * 64))
            another = Store(lease, context=self.context, trust_verifier=self.verifier)
            self.addCleanup(another.close)
            self.assertIs(another.trust_verifier, self.verifier)
            self.expect_code('PROFILE', lambda: another.trusted_receipts)
            self.expect_code('LOCKED', Store, lease, context=self.context,
                             trust_verifier=self.verifier)
        self.assertEqual(before, self.root_map(root))

    def test_blobwrite_and_pinnedroot_defensive_defaults(self):
        payload = b'bounded bytes'
        h = hashlib.sha256(payload).hexdigest()
        blob = BlobWrite(h, payload, 'application/x-edgeworld-static-vector', 'synthetic-contract-only')
        with self.assertRaises(AttributeError):
            blob.payload = b'changed'
        self.expect_code('SCHEMA', BlobWrite, h, bytearray(payload), blob.media_type, blob.artifact_class)
        self.expect_code('CORRUPT', BlobWrite, 'a' * 64, payload, blob.media_type, blob.artifact_class)
        self.expect_code('PROFILE', BlobWrite, h, payload, blob.media_type)
        supplied = {h: payload}
        pinned = PinnedRoot('b' * 64, b'head', {}, supplied)
        supplied.clear()
        self.assertEqual(pinned.blobs[h], payload)
        with self.assertRaises(TypeError):
            pinned.blobs[h] = b'other'
        self.assertEqual(dict(PinnedRoot('b' * 64, b'head', {}).blobs), {})

    def test_full_four_root_roundtrip_and_exact_head(self):
        root, _, store = self.initialized()
        self.advance_all(store)
        snapshot = store.snapshot()
        self.assertEqual(snapshot.closure.retained,
                         tuple(self.hashes[f'manifest-{i}'] for i in (3, 2, 1, 0)))
        self.assertEqual(len(snapshot.closure.binary_refs), 2)
        for h, raw in self.raw.items():
            self.assertEqual(store.read_blob(h), raw)
        before = self.root_map(root)
        for step in (1, 2, 3):
            result = store.lookup_result('fixture-principal', f'command-{step}', self.hashes[f'command-record-{step}'])
            self.assertEqual(result['body']['command_id'], f'command-{step}')
            result['body']['command_id'] = 'caller-mutated'
        self.assertEqual(self.root_map(root), before)
        expected = dict(domain='edgeworld.universe.authority', version='0.2',
                        world_id='composite-demo', manifest=self.hashes['manifest-3'],
                        profile='local-posix-blob-sync-v0.2')
        self.assertEqual((root / 'HEAD.json').read_bytes(), canonical(expected))
        pinned = store.pin()
        self.assertEqual(dict(pinned.blobs), self.raw)
        self.expect_code('NOT_READY', store.read_blob, next(iter(self.raw)))
        store.confirm_recovery(pinned, self.validate(pinned))
        self.assertEqual(store.snapshot().storage_state, 'ready')

    def test_initialize_requires_complete_exact_raw_and_no_extras(self):
        root, _, store = self.new()
        initial = self.records[:31]
        h = self.hashes['manifest-0']
        before = self.root_map(root)
        self.expect_code('CORRUPT', store.initialize, initial, h)
        blobs = self.blobs_for(initial)
        self.expect_code('REFERENCE', store.initialize, initial, h, blobs=blobs + blobs)
        extra_raw = b'unused'
        extra = BlobWrite(hashlib.sha256(extra_raw).hexdigest(), extra_raw,
                          'application/x-edgeworld-static-vector', 'synthetic-contract-only')
        self.expect_code('REFERENCE', store.initialize, initial, h, blobs=blobs + (extra,))
        runtime_meta = BlobWrite(blobs[0].sha256, blobs[0].payload,
                                'application/x-genesis-gstraj;version=1.4.3')
        self.expect_code('CORRUPT', store.initialize, initial, h, blobs=(runtime_meta,))
        self.assertEqual(before, self.root_map(root))

    def test_missing_new_payload_and_unused_record_rejected_before_writes(self):
        root, _, store = self.initialized()
        store.commit(self.bundle(1))
        before = self.root_map(root)
        self.expect_code('CORRUPT', store.commit, self.bundle(2, blobs=()))
        extra = deepcopy(self.records[31]); extra['id'] = 'orphan-proposal'
        self.expect_code('REFERENCE', store.commit,
                         self.bundle(2, records=self.bundle(2).records + (extra,)))
        self.assertEqual(before, self.root_map(root))
        self.assertEqual(store.state, 'ready')

    def test_mac_failure_cannot_publish_and_no_fixture_key_fallback(self):
        root, _, store = self.initialized()
        before = self.root_map(root)
        records = list(self.bundle().records)
        approval = next(r for r in records if r['kind'] == 'approval')
        approval['body']['auth_tag'] = '0' * 64
        self.expect_code('AUTHORIZATION', store.commit, self.bundle(records=tuple(records)))
        self.assertEqual(self.root_map(root), before)
        self.assertEqual(store.state, 'ready')

    def test_retained_raw_missing_or_wrong_bytes_blocks_recovery(self):
        for index, missing in enumerate((True, False)):
            root, _, store = self.initialized('history-' + str(index))
            self.advance_all(store)
            h = next(iter(self.blobs_for(self.records[:31]))).sha256
            path = root / 'blobs' / (h + '.static')
            path.unlink() if missing else path.write_bytes(b'corrupted')
            before = self.root_map(root)
            self.expect_code('CORRUPT', store.pin)
            self.expect_code('NOT_READY', store.snapshot)
            self.assertEqual(before, self.root_map(root))

    def test_existing_raw_collision_never_overwrites_or_advances(self):
        root, _, store = self.initialized()
        h = self.blobs_for(self.records[:31])[0].sha256
        path = root / 'blobs' / (h + '.static')
        path.write_bytes(b'collision')
        old = (root / 'HEAD.json').read_bytes()
        self.expect_code('CORRUPT', store.commit, self.bundle())
        self.assertEqual(path.read_bytes(), b'collision')
        self.assertEqual((root / 'HEAD.json').read_bytes(), old)
        self.expect_code('NOT_READY', store.snapshot)

    def test_raw_symlink_hardlink_and_wrong_suffix_never_trusted(self):
        for index, kind in enumerate(('symlink', 'hardlink', 'suffix')):
            root, _, store = self.initialized('links-' + str(index))
            h = self.blobs_for(self.records[:31])[0].sha256
            path = root / 'blobs' / (h + '.static')
            raw = path.read_bytes(); path.unlink()
            target = self.base / ('payload-' + str(index)); target.write_bytes(raw)
            if kind == 'symlink':
                path.symlink_to(target)
            elif kind == 'hardlink':
                os.link(target, path)
            else:
                (root / 'blobs' / (h + '.gstraj')).write_bytes(raw)
            before = self.root_map(root)
            self.expect_code('CORRUPT', store.pin)
            self.assertEqual(before, self.root_map(root))
            self.assertEqual(target.read_bytes(), raw)

    def test_read_blob_is_pinned_bounded_and_detects_disk_changes(self):
        root, _, store = self.initialized()
        self.expect_code('REFERENCE', store.read_blob, 'f' * 64)
        h = self.blobs_for(self.records[:31])[0].sha256
        before = self.root_map(root)
        self.assertEqual(store.read_blob(h), self.raw[h])
        self.assertEqual(self.root_map(root), before)
        (root / 'blobs' / (h + '.static')).unlink()
        self.expect_code('CORRUPT', store.read_blob, h)
        self.expect_code('NOT_READY', store.snapshot)

    def test_raw_fault_boundaries_and_unknown_fail_stop(self):
        phases = ('BLOB_FILE_SYNCED', 'BLOBS_DIR_SYNCED', 'W5_BEFORE_REPLACE',
                  'W6_AFTER_REPLACE', 'W8_BEFORE_RESPONSE')
        for index, target in enumerate(phases):
            armed = False
            trace = []
            def hook(phase, context):
                if armed:
                    trace.append({'phase': phase, 'context': dict(context)})
                if armed and phase == target:
                    raise OSError(errno.EIO, 'injected ' + phase)
            root, _, store = self.initialized('fault-' + str(index), hook)
            before = self.root_map(root)
            armed = True
            unknown = index >= 2
            error = self.expect_code('COMMIT_UNKNOWN' if unknown else 'IO_BEFORE_VISIBILITY',
                                     store.commit, self.bundle())
            after = self.root_map(root)
            self.assertEqual(error.commit_status, 'unknown' if unknown else 'not_attempted')
            if unknown:
                self.expect_code('NOT_READY', store.snapshot)
                self.expect_code('NOT_READY', store.read_blob, self.blobs_for(self.records[:31])[0].sha256)
                self.expect_code('NOT_READY', store.commit, self.bundle())
            else:
                self.assertEqual(store.snapshot().closure.head, self.hashes['manifest-0'])
            self.assertEqual(after, self.root_map(root))
            armed = False
            recovered = self.recover(store)
            expected = self.hashes['manifest-0' if index <= 2 else 'manifest-1']
            self.assertEqual(recovered.closure.head, expected)
            evidence('E3-' + target, {'before': before, 'after_fault': after,
                                     'after_recovery': self.root_map(root), 'trace': trace,
                                     'error': dict(code=error.code, phase=error.phase,
                                                   commit_status=error.commit_status)})

    def test_actual_blob_sync_order_and_complete_recovery_sync(self):
        trace = []
        root, _, store = self.new(fault=lambda phase, context: trace.append(('hook', phase)))
        real_sync = os.fsync
        def sync(fd):
            ino = os.fstat(fd).st_ino
            paths = [p for p in [root, *root.rglob('*')] if p.lstat().st_ino == ino]
            trace.append(('sync', str(paths[0].relative_to(root)) if paths else 'outside'))
            return real_sync(fd)
        with mock.patch(_MODULE + '.os.fsync', side_effect=sync):
            store.initialize(self.records[:31], self.hashes['manifest-0'],
                             blobs=self.blobs_for(self.records[:31]))
            self.advance_all(store)
        first_raw = next(i for i, item in enumerate(trace) if item[0] == 'sync' and item[1].endswith('.static'))
        first_visible = trace.index(('hook', 'W5_BEFORE_REPLACE'))
        self.assertLess(first_raw, first_visible)
        self.assertLess(trace.index(('sync', 'blobs')), first_visible)
        trace.clear()
        pinned = store.pin(); closure = self.validate(pinned)
        with mock.patch(_MODULE + '.os.fsync', side_effect=sync):
            store.confirm_recovery(pinned, closure)
        synced = [item[1] for item in trace if item[0] == 'sync']
        self.assertEqual(synced[-2:], ['HEAD.json', '.'])
        for reference in pinned.objects:
            self.assertIn('objects/' + reference + '.json', synced)
        for reference in pinned.blobs:
            self.assertIn('blobs/' + reference + '.static', synced)
        self.assertIn('objects', synced); self.assertIn('blobs', synced)
        evidence('E3-sync-order', {'root': self.root_map(root), 'trace': trace})

    def test_failed_raw_or_blobdir_recovery_sync_is_unconfirmed_readonly(self):
        for index, directory_failure in enumerate((False, True)):
            root, _, store = self.initialized('recovery-sync-' + str(index))
            self.advance_all(store)
            pinned = store.pin(); closure = self.validate(pinned)
            real_sync = os.fsync
            if directory_failure:
                failed_inodes = {(root / 'blobs').stat().st_ino}
            else:
                failed_inodes = {(root / 'blobs' / (h + '.static')).stat().st_ino for h in pinned.blobs}
            def fail_raw(fd):
                if os.fstat(fd).st_ino in failed_inodes:
                    raise OSError(errno.EIO, 'injected raw/blobdir sync failure')
                return real_sync(fd)
            before = self.root_map(root)
            with mock.patch(_MODULE + '.os.fsync', side_effect=fail_raw):
                error = self.expect_code('SYNC_UNSUPPORTED', store.confirm_recovery, pinned, closure)
            self.assertEqual(error.commit_status, 'unknown')
            self.assertEqual(store.snapshot().storage_state, 'unconfirmed_readonly')
            for h, payload in pinned.blobs.items():
                self.assertEqual(store.read_blob(h), payload)
            self.expect_code('NOT_READY', store.commit, self.bundle(3))
            self.assertEqual(before, self.root_map(root))
            evidence('E3-recovery-raw-or-dir-' + str(index), {
                'before': before, 'after_fault': self.root_map(root),
                'error': dict(code=error.code, phase=error.phase, commit_status=error.commit_status),
                'storage_state': store.snapshot().storage_state})
            self.assertEqual(self.recover(store).storage_state, 'ready')

    def test_tampered_raw_pinned_mapping_refuses_confirmation(self):
        root, _, store = self.initialized()
        pinned = store.pin(); closure = self.validate(pinned)
        bad = PinnedRoot(pinned.head, pinned.head_bytes, pinned.objects, {})
        before = self.root_map(root)
        self.expect_code('CORRUPT', store.confirm_recovery, bad, closure)
        self.assertEqual(self.root_map(root), before)
        self.expect_code('NOT_READY', store.snapshot)

    def test_recovery_hook_removal_of_raw_invalidates_readonly_cache(self):
        armed = False
        def hook(phase, context):
            if armed and phase == 'RECOVERY_VALIDATED':
                next((root / 'blobs').glob('*.static')).unlink()
        root, _, store = self.initialized(fault=hook)
        pinned = store.pin(); closure = self.validate(pinned)
        armed = True
        self.expect_code('CORRUPT', store.confirm_recovery, pinned, closure)
        self.expect_code('NOT_READY', store.snapshot)

    def test_blob_hook_cannot_reenter_or_close_active_store(self):
        armed = False
        seen = []
        def hook(phase, context):
            if armed and phase == 'BLOB_FILE_SYNCED':
                self.expect_code('LOCKED', store.read_blob, context['object_digest'])
                self.expect_code('LOCKED', store.close)
                seen.append(phase)
        _, _, store = self.initialized(fault=hook)
        armed = True
        store.commit(self.bundle())
        self.assertTrue(seen)
        self.assertEqual(store.state, 'ready')

    def test_v01_rejects_raw_inputs_without_creating_blob_directory(self):
        helper = StoreTests('test_initialize_explicit_exact_genesis_only')
        helper.setUp()
        try:
            root, _, store = helper.new()
            blob = BlobWrite(next(iter(self.raw)), next(iter(self.raw.values())),
                             'application/x-edgeworld-static-vector', 'synthetic-contract-only')
            before = helper.root_map(root)
            self.expect_code('PROFILE', store.initialize, helper.records[:2], helper.hashes['m0'], blobs=(blob,))
            self.expect_code('PROFILE', lambda: store.trust_verifier)
            self.assertEqual(before, helper.root_map(root))
        finally:
            helper.doCleanups()


if __name__ == '__main__':
    unittest.main()
