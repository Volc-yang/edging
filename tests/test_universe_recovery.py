"""Real local v0.1 file reads/sync and pure historical payload checks, no solver."""
from copy import deepcopy
from dataclasses import asdict
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
from engine.universe_authority.records import ValidatedClosure, verify_observation
from engine.universe_authority.recovery import RecoveryReport, head_binding, observe, recover, status
from engine.universe_authority.store import CommitBundle, PinnedRoot, Snapshot, Store, StoreError
from engine.universe_authority.trust import open_trust
from tests import test_universe_store as _store_helpers

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

class CompositeRecoveryTests(unittest.TestCase):
    # Reuse the accepted owner-provisioned synthetic template setup; no copied
    # signer implementation or fixture-key shortcut enters the production path.
    setUp = _store_helpers.CompositeStoreTests.setUp
    new = _store_helpers.CompositeStoreTests.new
    initialized = _store_helpers.CompositeStoreTests.initialized
    blobs_for = _store_helpers.CompositeStoreTests.blobs_for
    bundle = _store_helpers.CompositeStoreTests.bundle
    advance_all = _store_helpers.CompositeStoreTests.advance_all
    code = RecoveryTests.code
    files = RecoveryTests.files

    def build(self, steps=3, label='world', fault=None):
        root, lease, store = self.initialized(label, fault)
        for step in range(1, steps + 1):
            store.commit(self.bundle(step))
        return root, lease, store

    def reopen(self, root, lease, store, fault=None):
        context = self.context
        store.close(); lease.close()
        lease = acquire(root, context.world_id, domain_version='0.2',
                        profile=context.storage_profile, context=context)
        self.addCleanup(lease.close)
        verifier = open_trust(self.base / (root.name + '-key'), context=context)
        store = Store(lease, context=context, trust_verifier=verifier, fault=fault)
        self.addCleanup(store.close)
        return lease, store

    def wire(self, payload, request_id='observe-' + 'x' * 56):
        return json.dumps(dict(protocol_version=1, request_id=request_id, ok=True,
                               result=dict(domain='edgeworld.universe.authority', version='0.2',
                                           world_id=self.context.world_id, operation='observe',
                                           payload=payload)), sort_keys=True, ensure_ascii=True,
                          separators=(',', ':'), allow_nan=False).encode('ascii')

    def verify(self, payload, binding, request_id='observe-' + 'x' * 56):
        b = payload['manifest']['body']
        return verify_observation(self.wire(payload, request_id), context=self.context,
                                  expected_request_id=request_id, tick=b['tick'],
                                  revision=b['revision'], watermark=b['watermark'],
                                  trusted_head=binding)

    def test_public_store_profile_context_getters_are_pure_and_readonly(self):
        root, _, store = self.new()
        before = self.files(root)
        with mock.patch(_STORE_MODULE + '.os.open', side_effect=AssertionError('getter I/O')):
            self.assertEqual(store.domain_version, '0.2')
            self.assertIs(store.deployment_context, self.context)
            with self.assertRaises(AttributeError):
                store.domain_version = '0.1'
            with self.assertRaises(AttributeError):
                store.deployment_context = None
        self.assertEqual(before, self.files(root))

    def test_reopen_recovers_all_retained_records_raw_and_public_status(self):
        root, lease, store = self.build()
        trace = []
        _, reader = self.reopen(root, lease, store,
                                lambda phase, context: trace.append({'phase': phase, 'context': dict(context)}))
        before = self.files(root)
        report = recover(reader)
        self.assertTrue(report.confirmed)
        self.assertEqual(report.snapshot.closure.context, self.context)
        self.assertEqual(len(report.snapshot.closure.records), 67)
        self.assertEqual(len(report.snapshot.closure.binary_refs), 2)
        current = status(report.snapshot)
        self.assertEqual(set(current), {'world_id', 'head', 'tick', 'revision', 'watermark',
                                       'state', 'event', 'storage_state', 'artifact_class', 'head_binding'})
        self.assertEqual((current['tick'], current['revision'], current['watermark']), (1, 3, 3))
        self.assertEqual(current['state'], self.hashes['state-3'])
        self.assertEqual(current['event'], self.hashes['event-record-3'])
        binding = head_binding(report.snapshot)
        self.assertEqual(current['head_binding'], asdict(binding))
        self.assertEqual(binding.authority_root, str(root))
        self.assertEqual(binding.storage_state, 'ready')
        self.assertEqual(binding.trust_anchor, self.context.trust_anchor)
        self.assertEqual(sum(row['phase'] == 'RECOVERY_BLOBS_SYNCED' for row in trace), 2)
        self.assertEqual(trace[-1]['phase'], 'W9_RECOVERY_SYNCED')
        self.assertEqual(before, self.files(root))
        evidence('E5-reopen-complete', before=before, after=self.files(root),
                 status=current, trace=trace)

    def test_all_four_exact_slices_verify_and_remain_selective(self):
        root, _, store = self.build()
        snapshot = recover(store).snapshot
        binding = head_binding(snapshot)
        before = self.files(root)
        views = []
        for revision, tick in ((0, 0), (1, 0), (2, 1), (3, 1)):
            payload = observe(snapshot, tick=tick, revision=revision, watermark=revision)
            self.assertEqual(set(payload), {'manifest', 'state', 'event', 'watermark',
                                           'storage_state', 'artifact_class', 'head',
                                           'membership', 'records', 'opaque_refs'})
            checked = self.verify(payload, binding)
            self.assertEqual(checked.manifest, self.hashes[f'manifest-{revision}'])
            self.assertEqual(checked.scope, 'selected-slice-membership-only-not-full-history-or-raw-validation')
            self.assertEqual(len(payload['membership']), 4 - revision)
            if revision == 0:
                self.assertIsNone(payload['event'])
            else:
                self.assertIsNotNone(payload['event'])
            auxiliary = [digest(record) for record in payload['records']]
            explicit = {digest(record) for record in payload['membership'] + [payload['manifest'], payload['state']]}
            if payload['event'] is not None:
                explicit.add(digest(payload['event']))
            self.assertEqual(auxiliary, sorted(set(auxiliary)))
            self.assertFalse(explicit & set(auxiliary))
            self.assertEqual(payload['opaque_refs'], sorted(set(payload['opaque_refs'])))
            self.assertLess(len(checked.selected_records), 67)
            self.assertLessEqual(len(self.wire(payload)), 1 << 20)
            self.assertEqual(checked.bytes, len(self.wire(payload)))
            kinds = [r['kind'] for r in checked.selected_records.values()]
            self.assertEqual(kinds.count('existence'), 9)
            self.assertEqual(kinds.count('place'), 6)
            self.assertEqual(kinds.count('world_manifest'), 1)
            views.append(payload)
        genesis = views[0]
        self.assertEqual(genesis['state']['body']['development_mm'], None)
        self.assertEqual(views[1]['state']['body']['development_mm'], None)
        self.assertEqual(views[2]['state']['body']['development_mm'], views[3]['state']['body']['development_mm'])
        genesis_refs = {digest(r) for r in genesis['records']}
        self.assertNotIn(self.hashes['state-3'], genesis_refs)
        self.assertIn(self.hashes['state-3'], genesis['opaque_refs'])
        physical = self.verify(views[2], binding).selected_records
        for name in ('state-1', 'state-2', 'snapshot-0', 'snapshot-1', 'sample-0', 'sample-1'):
            self.assertIn(self.hashes[name], physical)
        self.assertEqual(before, self.files(root))
        evidence('E5-four-proofs', status=status(snapshot), payloads=views,
                 wire_bytes=[len(self.wire(p)) for p in views], map=self.files(root))

    def test_same_tuple_proofs_are_deterministic_after_reordered_pin(self):
        root, _, store = self.build()
        expected = observe(recover(store).snapshot, tick=1, revision=2, watermark=2)
        original_pin = store.pin
        def reversed_mapping():
            pinned = original_pin()
            return PinnedRoot(pinned.head, pinned.head_bytes,
                              dict(reversed(list(pinned.objects.items()))),
                              dict(reversed(list(pinned.blobs.items()))))
        before = self.files(root)
        with mock.patch.object(store, 'pin', side_effect=reversed_mapping):
            report = recover(store)
        actual = observe(report.snapshot, tick=1, revision=2, watermark=2)
        self.assertEqual(actual, expected)
        self.assertEqual(before, self.files(root))

    def test_status_observe_binding_are_memory_only_and_defensive(self):
        root, _, store = self.build()
        snapshot = recover(store).snapshot
        current = status(snapshot)
        before = self.files(root)
        with mock.patch('builtins.open', side_effect=AssertionError('pure view file read')), \
                mock.patch(_STORE_MODULE + '.os.open', side_effect=AssertionError('pure view fd')), \
                mock.patch(_STORE_MODULE + '.os.fsync', side_effect=AssertionError('pure view sync')):
            for revision, tick in ((0, 0), (2, 1), (1, 0), (3, 1), (2, 1)):
                payload = observe(snapshot, tick=tick, revision=revision, watermark=revision)
                self.assertEqual(payload['state']['body']['revision'], revision)
                payload['records'][0]['id'] = 'caller-changed'
                payload['membership'][0]['body']['revision'] = 999
                payload['opaque_refs'].append('0' * 64)
                self.assertEqual(status(snapshot), current)
                self.assertEqual(head_binding(snapshot).head, current['head'])
        latest = observe(snapshot, tick=1, revision=3, watermark=3)
        self.assertEqual(latest['state']['body']['budget'], 7)
        self.assertEqual(latest['state']['body']['random_cursor'], 1)
        self.assertEqual(before, self.files(root))
        binding = head_binding(snapshot)
        with self.assertRaises(AttributeError):
            binding.storage_state = 'unconfirmed_readonly'

    def test_exact_query_types_watermark_and_absence(self):
        root, _, store = self.build()
        snapshot = recover(store).snapshot
        before = self.files(root)
        queries = [({'tick': 0, 'revision': 1, 'watermark': 0}, 'WATERMARK'),
                   ({'tick': 1, 'revision': 1, 'watermark': 1}, 'NOT_FOUND'),
                   ({'tick': 1, 'revision': 4, 'watermark': 4}, 'NOT_FOUND'),
                   ({'tick': True, 'revision': 1, 'watermark': 1}, 'INTEGER'),
                   ({'tick': 1, 'revision': 2.0, 'watermark': 2}, 'INTEGER')]
        for query, code in queries:
            self.code(code, observe, snapshot, **query)
        self.assertEqual(before, self.files(root))

    def test_raw_or_json_history_corruption_never_uses_backup(self):
        for index, mode in enumerate(('raw-missing', 'raw-changed', 'old-json')):
            root, lease, store = self.build(label='bad-' + str(index))
            _, store = self.reopen(root, lease, store)
            (root / 'HEAD.backup.json').write_bytes((root / 'HEAD.json').read_bytes())
            if mode == 'old-json':
                (root / 'objects' / (self.hashes['state-0'] + '.json')).write_bytes(b'{}')
            else:
                path = root / 'blobs' / (self.blobs_for(self.records[:31])[0].sha256 + '.static')
                path.unlink() if mode == 'raw-missing' else path.write_bytes(b'bad')
            before = self.files(root)
            self.code('CORRUPT', recover, store)
            self.code('NOT_READY', store.snapshot)
            self.assertEqual(before, self.files(root))
            evidence('E5-bad-' + mode, before=before, after=self.files(root), state=store.state)

    def test_modified_pin_raw_mapping_cannot_become_readonly(self):
        for index, mode in enumerate(('missing', 'extra', 'changed')):
            root, _, store = self.build(label='pin-' + str(index))
            original_pin = store.pin
            def modified():
                pinned = original_pin(); raw = dict(pinned.blobs)
                if mode == 'missing':
                    raw.pop(next(iter(raw)))
                elif mode == 'extra':
                    raw['f' * 64] = b'not referenced'
                else:
                    raw[next(iter(raw))] = b'changed'
                return PinnedRoot(pinned.head, pinned.head_bytes, pinned.objects, raw)
            before = self.files(root)
            with mock.patch.object(store, 'pin', side_effect=modified):
                self.code('CORRUPT', recover, store)
            self.code('NOT_READY', store.snapshot)
            self.assertEqual(before, self.files(root))

    def test_failed_raw_sync_produces_fresh_labeled_proof(self):
        root, lease, store = self.build()
        _, store = self.reopen(root, lease, store)
        raw_inodes = {p.stat().st_ino for p in (root / 'blobs').iterdir()}
        real_sync = os.fsync
        def fail(fd):
            if os.fstat(fd).st_ino in raw_inodes:
                raise OSError(errno.EIO, 'raw sync failure')
            return real_sync(fd)
        before = self.files(root)
        with mock.patch(_STORE_MODULE + '.os.fsync', side_effect=fail):
            report = recover(store)
        self.assertFalse(report.confirmed)
        self.assertEqual(report.error_code, 'SYNC_UNSUPPORTED')
        binding = head_binding(report.snapshot)
        self.assertEqual(binding.storage_state, 'unconfirmed_readonly')
        self.assertEqual(status(report.snapshot)['storage_state'], binding.storage_state)
        payload = observe(report.snapshot, tick=1, revision=2, watermark=2)
        self.assertEqual(self.verify(payload, binding).storage_state, binding.storage_state)
        forged = deepcopy(payload); forged['storage_state'] = 'ready'
        self.code('PROOF', self.verify, forged, binding)
        self.code('NOT_READY', store.commit, self.bundle(3))
        self.assertEqual(before, self.files(root))
        restored = recover(store)
        self.assertTrue(restored.confirmed)
        self.assertEqual(head_binding(restored.snapshot).storage_state, 'ready')
        self.assertEqual(binding.storage_state, 'unconfirmed_readonly')
        evidence('E5-unconfirmed-proof', before=before, after=self.files(root),
                 binding=asdict(binding), payload=payload)

    def test_lost_raw_after_validation_cannot_return_snapshot(self):
        armed = False
        def hook(phase, context):
            if armed and phase == 'RECOVERY_VALIDATED':
                next((root / 'blobs').glob('*.static')).unlink()
        root, _, store = self.build(fault=hook)
        armed = True
        self.code('CORRUPT', recover, store)
        self.code('NOT_READY', store.snapshot)
        evidence('E5-raw-lost-during-sync', state=store.state, map=self.files(root))

    def test_unknown_visibility_recovers_exact_result_without_new_action(self):
        armed = False
        def hook(phase, context):
            if armed and phase == 'W6_AFTER_REPLACE':
                raise OSError(errno.EIO, 'response lost')
        root, _, store = self.build(steps=1, fault=hook)
        armed = True
        error = self.code('COMMIT_UNKNOWN', store.commit, self.bundle(2))
        self.assertEqual(error.commit_status, 'unknown')
        armed = False
        before = self.files(root)
        snapshot = recover(store).snapshot
        self.assertEqual(status(snapshot)['head'], self.hashes['manifest-2'])
        result = store.lookup_result('fixture-principal', 'command-2', self.hashes['command-record-2'])
        self.assertEqual(result['body']['revision'], 2)
        payload = observe(snapshot, tick=1, revision=2, watermark=2)
        self.assertEqual(payload['state']['body']['random_cursor'], 1)
        self.verify(payload, head_binding(snapshot))
        self.assertEqual(before, self.files(root))

    def test_missing_key_open_never_falls_back_or_regenerates(self):
        root, lease, store = self.build()
        store.close(); lease.close()
        path = self.base / (root.name + '-key') / 'authority.key'
        path.unlink()
        before = self.files(root)
        self.code('AUTHORIZATION', open_trust, path.parent, context=self.context)
        self.assertFalse(path.exists())
        self.assertEqual(before, self.files(root))

    def test_v01_binding_rejected_and_public_metadata_defaults_preserved(self):
        helper = RecoveryTests('test_explicit_recover_genesis_after_reopen')
        helper.setUp()
        try:
            _, _, store = helper.build()
            snapshot = recover(store).snapshot
            self.code('PROFILE', head_binding, snapshot)
            with mock.patch(_STORE_MODULE + '.os.open', side_effect=AssertionError('getter I/O')):
                self.assertEqual(store.domain_version, '0.1')
                self.assertIsNone(store.deployment_context)
            self.assertEqual(set(status(snapshot)), {'head', 'tick', 'revision', 'watermark', 'storage_state'})
            self.assertEqual(set(observe(snapshot, tick=0, revision=0, watermark=0)),
                             {'manifest', 'state', 'event', 'watermark', 'storage_state'})
        finally:
            helper.doCleanups()


if __name__ == '__main__':
    unittest.main()
