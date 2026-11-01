"""Real local v0.1 file reads/sync and pure historical payload checks, no solver."""
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
from engine.universe_authority.records import ValidatedClosure
from engine.universe_authority.recovery import RecoveryReport, observe, recover, status
from engine.universe_authority.store import CommitBundle, PinnedRoot, Snapshot, Store, StoreError

_FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_1'
_STORE_MODULE = 'engine.universe_authority.store'


def evidence(case, **data):
    destination = os.environ.get('EDGEWORLD_I5_FAULT_LOG')
    if not destination:
        return
    raw = (json.dumps({'case': case, 'pid': os.getpid(), **data}, sort_keys=True) + '\n').encode('utf-8')
    descriptor = os.open(destination, os.O_WRONLY | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW)
    try:
        remaining = memoryview(raw)
        while remaining:
            count = os.write(descriptor, remaining)
            if count <= 0:
                raise OSError('evidence write made no progress')
            remaining = remaining[count:]
    finally:
        os.close(descriptor)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='universe-i5-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.records = json.loads((_FIXTURES / 'positive.json').read_bytes())['records']
        self.trust = json.loads((_FIXTURES / 'trusted_receipts.json').read_bytes())
        self.hashes = {row['id']: row['sha256'] for row in json.loads((_FIXTURES / 'golden.json').read_bytes())}
        self.world = 'fixture-world'

    def code(self, expected, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, expected)
        return caught.exception

    def files(self, root):
        result = {}
        for path in sorted(root.rglob('*')):
            info = path.lstat()
            row = {'inode': str(info.st_ino), 'bytes': info.st_size, 'links': info.st_nlink}
            if stat.S_ISREG(info.st_mode):
                raw = path.read_bytes()
                row.update(sha256=hashlib.sha256(raw).hexdigest(), raw_hex=raw.hex())
            elif path.is_symlink():
                row['target'] = os.readlink(path)
            result[str(path.relative_to(root))] = row
        return result

    def bundle(self, step=1):
        start = 2 + (step - 1) * 11
        return CommitBundle(self.hashes[f'm{step-1}'], tuple(deepcopy(self.records[start:start+11])),
                            self.hashes[f'm{step}'], 'fixture-principal', f'command-{step}', self.hashes[f'c{step}'])

    def build(self, label='authority', steps=0, fault=None):
        root = self.base / label
        lease = acquire(root, self.world, initialize=True)
        self.addCleanup(lease.close)
        store = Store(lease, trusted_receipts=self.trust, fault=fault)
        self.addCleanup(store.close)
        store.initialize(self.records[:2], self.hashes['m0'])
        for step in range(1, steps+1):
            store.commit(self.bundle(step))
        return root, lease, store

    def reopen(self, root, lease, store, fault=None):
        store.close(); lease.close()
        lease = acquire(root, self.world)
        self.addCleanup(lease.close)
        store = Store(lease, trusted_receipts=self.trust, fault=fault)
        self.addCleanup(store.close)
        return lease, store

    def test_explicit_recover_genesis_after_reopen(self):
        root, lease, store = self.build()
        trace = []
        def hook(phase, context):
            trace.append({'phase': phase, 'context': dict(context)})
        _, reader = self.reopen(root, lease, store, hook)
        before = self.files(root)
        self.assertEqual(reader.state, 'recovering')
        report = recover(reader)
        self.assertIsInstance(report, RecoveryReport)
        self.assertTrue(report.confirmed)
        self.assertIsNone(report.error_code)
        self.assertEqual(report.storage_state, 'ready')
        self.assertEqual([row['phase'] for row in trace], ['W0_LOCKED', 'RECOVERY_VALIDATED', 'W9_RECOVERY_SYNCED'])
        self.assertEqual(status(report.snapshot), {'head': self.hashes['m0'], 'tick': 0, 'revision': 0,
                                                   'watermark': 0, 'storage_state': 'ready'})
        view = observe(report.snapshot, tick=0, revision=0, watermark=0)
        self.assertEqual(set(view), {'manifest', 'state', 'event', 'watermark', 'storage_state'})
        self.assertEqual(view['manifest'], self.records[1])
        self.assertEqual(view['state'], self.records[0])
        self.assertIsNone(view['event'])
        self.assertEqual(self.files(root), before)
        evidence('genesis-recovery', trace=trace, before=before, after=self.files(root), payload=view)

    def test_exact_same_tick_history_and_current_watermark_are_independent(self):
        root, lease, store = self.build(steps=2)
        _, store = self.reopen(root, lease, store)
        before = self.files(root)
        snapshot = recover(store).snapshot
        current = status(snapshot)
        self.assertEqual((current['tick'], current['revision'], current['watermark']), (0, 2, 2))
        first = observe(snapshot, tick=0, revision=1, watermark=1)
        second = observe(snapshot, tick=0, revision=2, watermark=2)
        self.assertEqual(first['manifest'], self.records[12])
        self.assertEqual(first['state'], self.records[8])
        self.assertEqual(first['event'], self.records[9])
        self.assertEqual(second['manifest'], self.records[23])
        self.assertEqual(second['state'], self.records[19])
        self.assertEqual(second['event'], self.records[20])
        self.assertNotEqual(first['state'], second['state'])
        self.assertEqual(first['event']['refs']['state'], first['manifest']['refs']['state'])
        self.assertEqual(status(snapshot), current)
        self.assertEqual(self.files(root), before)
        evidence('same-tick-history', current=current, revision1=first, revision2=second,
                 before=before, after=self.files(root))

    def test_reordered_pinned_mapping_is_equivalent_and_not_assumed_topological(self):
        root, _, store = self.build(steps=2)
        original_pin = store.pin
        observed_order = []
        def reversed_mapping():
            pinned = original_pin()
            mapping = {pinned.head: pinned.objects[pinned.head]}
            mapping.update((key, raw) for key, raw in reversed(list(pinned.objects.items())) if key != pinned.head)
            observed_order.extend(mapping)
            return PinnedRoot(pinned.head, pinned.head_bytes, mapping)
        before = self.files(root)
        with mock.patch.object(store, 'pin', side_effect=reversed_mapping):
            report = recover(store)
        self.assertEqual(observed_order[0], self.hashes['m2'])
        self.assertTrue(report.confirmed)
        self.assertEqual(status(report.snapshot)['head'], self.hashes['m2'])
        self.assertEqual(observe(report.snapshot, tick=0, revision=1, watermark=1)['state'], self.records[8])
        self.assertEqual(self.files(root), before)
        evidence('reordered-pinned-mapping', supplied_order=observed_order,
                 status=status(report.snapshot), map=self.files(root))

    def test_pinned_mapping_rejects_unreachable_or_mismatched_raw_records(self):
        for index, mode in enumerate(('orphan', 'bad-hash', 'missing')):
            root, _, store = self.build('pinned-' + str(index), steps=1)
            original_pin = store.pin
            def modified_mapping():
                pinned = original_pin()
                mapping = dict(pinned.objects)
                if mode == 'orphan':
                    mapping[self.hashes['p2']] = canonical(self.records[13])
                elif mode == 'bad-hash':
                    mapping[self.hashes['s0']] = canonical(self.records[8])
                else:
                    del mapping[self.hashes['s0']]
                return PinnedRoot(pinned.head, pinned.head_bytes, mapping)
            before = self.files(root)
            with mock.patch.object(store, 'pin', side_effect=modified_mapping):
                self.code('CORRUPT', recover, store)
            self.code('NOT_READY', store.snapshot)
            self.assertEqual(self.files(root), before)

    def test_bad_watermark_absent_exact_tuple_and_integer_types_reject(self):
        root, _, store = self.build(steps=2)
        snapshot = recover(store).snapshot
        before = self.files(root)
        queries = [({'tick': 0, 'revision': 1, 'watermark': 0}, 'WATERMARK'),
                   ({'tick': 1, 'revision': 1, 'watermark': 1}, 'NOT_FOUND'),
                   ({'tick': 0, 'revision': 3, 'watermark': 3}, 'NOT_FOUND'),
                   ({'tick': True, 'revision': 1, 'watermark': 1}, 'INTEGER'),
                   ({'tick': 0, 'revision': 1.0, 'watermark': 1}, 'INTEGER'),
                   ({'tick': 0, 'revision': 2**53, 'watermark': 2**53}, 'INTEGER'),
                   ({'tick': 0, 'revision': 0, 'watermark': -1}, 'INTEGER')]
        for query, error in queries:
            with self.subTest(query=query):
                self.code(error, observe, snapshot, **query)
        self.assertEqual(self.files(root), before)
        self.assertEqual(status(snapshot)['revision'], 2)
        evidence('rejected-exact-queries', queries=queries, map=self.files(root))

    def test_status_observe_are_memory_only_and_do_not_advance(self):
        root, _, store = self.build(steps=2)
        snapshot = recover(store).snapshot
        before = self.files(root)
        with mock.patch('builtins.open', side_effect=AssertionError('pure view opened a file')), \
                mock.patch(_STORE_MODULE + '.os.open', side_effect=AssertionError('pure view opened fd')), \
                mock.patch(_STORE_MODULE + '.os.fsync', side_effect=AssertionError('pure view synchronized')):
            for revision in (0, 1, 2, 1):
                view = observe(snapshot, tick=0, revision=revision, watermark=revision)
                self.assertEqual(view['state']['body']['revision'], revision)
                self.assertEqual(status(snapshot)['head'], self.hashes['m2'])
        self.assertEqual(self.files(root), before)
        current = observe(snapshot, tick=0, revision=2, watermark=2)['state']['body']
        self.assertEqual((current['budget'], current['random_cursor']), (6, 2))

    def test_payloads_and_report_are_defensive_immutable_views(self):
        _, _, store = self.build(steps=2)
        report = recover(store)
        view = observe(report.snapshot, tick=0, revision=1, watermark=1)
        view['manifest']['body']['revision'] = 999
        view['state']['body']['value'] = {'$f64': '0000000000000000'}
        view['event']['refs']['state'] = '0'*64
        mutated = status(report.snapshot)
        mutated['revision'] = 999
        report.snapshot.closure.records[self.hashes['s1']]['body']['tick'] = 999
        self.assertEqual(observe(report.snapshot, tick=0, revision=1, watermark=1)['state'], self.records[8])
        self.assertEqual(status(report.snapshot)['revision'], 2)
        with self.assertRaises(AttributeError):
            report.confirmed = False

    def test_uninitialized_recovery_never_creates_head_or_objects(self):
        root = self.base / 'uninitialized'
        lease = acquire(root, self.world, initialize=True)
        self.addCleanup(lease.close)
        store = Store(lease, trusted_receipts=self.trust)
        self.addCleanup(store.close)
        before = self.files(root)
        self.code('UNINITIALIZED', recover, store)
        self.code('NOT_READY', store.snapshot)
        self.assertEqual(self.files(root), before)
        self.assertFalse((root / 'HEAD.json').exists())
        self.assertFalse((root / 'objects').exists())
        evidence('uninitialized', before=before, after=self.files(root), state=store.state)

    def test_historical_corruption_missing_refs_and_backup_never_fall_back(self):
        for index, mode in enumerate(('s0', 'q1', 'm1', 'head')):
            with self.subTest(mode=mode):
                root, lease, store = self.build('corrupt-' + str(index), steps=1)
                backup = (root / 'HEAD.json').read_bytes()
                store.commit(self.bundle(2))
                (root / 'HEAD.backup.json').write_bytes(backup)
                _, store = self.reopen(root, lease, store)
                if mode == 'head':
                    (root / 'HEAD.json').write_bytes(b'{}')
                else:
                    path = root / 'objects' / (self.hashes[mode] + '.json')
                    if mode == 'q1':
                        path.unlink()
                    elif mode == 'm1':
                        path.write_bytes(path.read_bytes() + b'\n')
                    else:
                        path.write_bytes(b'{}')
                before = self.files(root)
                error = self.code('CORRUPT', recover, store)
                self.assertIsInstance(error, StoreError)
                self.assertEqual(store.state, 'corrupt')
                self.code('NOT_READY', store.snapshot)
                self.code('NOT_READY', store.commit, self.bundle())
                self.assertEqual(self.files(root), before)
                evidence('bad-history-' + mode, error=error.code, state=store.state,
                         before=before, after=self.files(root))

    def test_actual_sync_failure_only_returns_fresh_unconfirmed_snapshot(self):
        root, lease, store = self.build(steps=1)
        trace = []
        def hook(phase, context):
            trace.append({'phase': phase, 'context': dict(context)})
        _, store = self.reopen(root, lease, store, hook)
        before = self.files(root)
        with mock.patch(_STORE_MODULE + '.os.fsync', side_effect=OSError(errno.EIO, 'injected fsync failure')):
            report = recover(store)
        self.assertFalse(report.confirmed)
        self.assertEqual(report.error_code, 'SYNC_UNSUPPORTED')
        self.assertEqual(report.storage_state, 'unconfirmed_readonly')
        self.assertEqual(status(report.snapshot)['storage_state'], 'unconfirmed_readonly')
        self.assertEqual(status(report.snapshot)['head'], self.hashes['m1'])
        self.assertEqual(observe(report.snapshot, tick=0, revision=0, watermark=0)['storage_state'], 'unconfirmed_readonly')
        self.assertEqual([row['phase'] for row in trace], ['W0_LOCKED', 'RECOVERY_VALIDATED'])
        self.code('NOT_READY', store.commit, self.bundle(2))
        self.code('NOT_READY', store.lookup_result, 'fixture-principal', 'command-1', self.hashes['c1'])
        self.assertEqual(self.files(root), before)
        evidence('unconfirmed-fsync', trace=deepcopy(trace), before=before,
                 after=self.files(root), status=status(report.snapshot), confirmed=report.confirmed)
        restored = recover(store)
        self.assertTrue(restored.confirmed)
        self.assertEqual(restored.storage_state, 'ready')
        self.assertEqual(report.storage_state, 'unconfirmed_readonly')
        self.assertEqual(self.files(root), before)

    def test_w9_callback_failure_does_not_claim_confirmed(self):
        armed = False
        trace = []
        def hook(phase, context):
            if armed:
                trace.append({'phase': phase, 'context': dict(context)})
            if armed and phase == 'W9_RECOVERY_SYNCED':
                raise OSError(errno.EIO, 'injected W9 failure')
        root, _, store = self.build(steps=2, fault=hook)
        armed = True
        before = self.files(root)
        report = recover(store)
        self.assertFalse(report.confirmed)
        self.assertEqual(report.error_code, 'SYNC_UNSUPPORTED')
        self.assertEqual(status(report.snapshot)['head'], self.hashes['m2'])
        self.assertEqual(status(report.snapshot)['storage_state'], 'unconfirmed_readonly')
        self.code('NOT_READY', store.commit, self.bundle())
        self.assertEqual(self.files(root), before)
        evidence('W9-unconfirmed', trace=trace, status=status(report.snapshot), map=self.files(root))

    def test_reference_lost_after_validation_refuses_readonly_report(self):
        root = None
        armed = False
        def hook(phase, context):
            if armed and phase == 'RECOVERY_VALIDATED':
                (root / 'objects' / (self.hashes['q1'] + '.json')).unlink()
        root, _, store = self.build(steps=2, fault=hook)
        armed = True
        error = self.code('CORRUPT', recover, store)
        self.assertEqual(store.state, 'corrupt')
        self.code('NOT_READY', store.snapshot)
        evidence('lost-during-recovery', error=error.code, state=store.state, map=self.files(root))

    def test_error_code_alone_does_not_establish_unconfirmed_integrity(self):
        root, _, store = self.build()
        before = self.files(root)
        injected = StoreError('SYNC_UNSUPPORTED', 'no validated confirmation', phase='confirm_recovery')
        with mock.patch.object(store, 'confirm_recovery', side_effect=injected):
            error = self.code('SYNC_UNSUPPORTED', recover, store)
        self.assertIs(error, injected)
        self.assertEqual(store.state, 'recovering')
        self.code('NOT_READY', store.snapshot)
        self.assertEqual(self.files(root), before)

    def test_unknown_visibility_recovers_original_result_without_reexecution(self):
        armed = False
        trace = []
        def hook(phase, context):
            if armed:
                trace.append({'phase': phase, 'context': dict(context)})
            if armed and phase == 'W6_AFTER_REPLACE':
                raise OSError(errno.EIO, 'lost commit response')
        root, _, store = self.build(fault=hook)
        armed = True
        self.code('COMMIT_UNKNOWN', store.commit, self.bundle())
        self.code('NOT_READY', store.snapshot)
        armed = False
        before = self.files(root)
        report = recover(store)
        self.assertTrue(report.confirmed)
        self.assertEqual(status(report.snapshot)['head'], self.hashes['m1'])
        self.assertEqual(store.lookup_result('fixture-principal', 'command-1', self.hashes['c1']), self.records[10])
        state = observe(report.snapshot, tick=0, revision=1, watermark=1)['state']['body']
        self.assertEqual((state['budget'], state['random_cursor']), (7, 1))
        self.assertEqual(self.files(root), before)
        evidence('unknown-visibility-recovery', trace=trace, before=before,
                 after=self.files(root), status=status(report.snapshot))

    def test_orphan_results_do_not_become_historical_observations(self):
        root, _, store = self.build()
        for record in self.records[2:]:
            (root / 'objects' / (digest(record) + '.json')).write_bytes(canonical(record))
        before = self.files(root)
        snapshot = recover(store).snapshot
        self.assertEqual(status(snapshot)['head'], self.hashes['m0'])
        self.code('NOT_FOUND', observe, snapshot, tick=0, revision=1, watermark=1)
        self.assertEqual(dict(snapshot.closure.commands), {})
        self.assertEqual(self.files(root), before)
        evidence('orphan-not-visible', status=status(snapshot), map=self.files(root))

    def test_closed_store_or_bad_public_inputs_do_not_initialize(self):
        root, _, store = self.build()
        before = self.files(root)
        store.close()
        self.code('CLOSED', recover, store)
        self.code('SCHEMA', recover, None)
        for value in (None, {}, True, object.__new__(Snapshot)):
            self.code('SCHEMA', status, value)
            self.code('SCHEMA', observe, value, tick=0, revision=0, watermark=0)
        forged = Snapshot('ready', object.__new__(ValidatedClosure))
        self.code('SCHEMA', status, forged)
        self.assertEqual(self.files(root), before)


if __name__ == '__main__':
    unittest.main()
