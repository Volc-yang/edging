"""Finite neutral-v0.1 storage checks; injected faults do not model power loss."""
from copy import deepcopy
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from engine.universe_authority.codec import ContractError, canonical, digest
from engine.universe_authority.ownership import acquire
from engine.universe_authority.records import validate_closure
from engine.universe_authority.store import CommitBundle, PinnedRoot, Store, StoreError

_FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_1'
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


if __name__ == '__main__':
    unittest.main()
