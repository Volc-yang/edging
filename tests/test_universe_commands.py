"""Neutral kernel orchestration checks, not real authorization or physics evidence."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from engine.universe_authority.admission import FixtureTrust
from engine.universe_authority.codec import ContractError, digest, encode_f64
from engine.universe_authority.commands import execute
from engine.universe_authority.ownership import acquire
from engine.universe_authority.records import validate_closure
from engine.universe_authority.rules import neutral_candidate, validate_rule_dag
from engine.universe_authority.store import Store, StoreError

_FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_1'
_COMMANDS = 'engine.universe_authority.commands'


def file_map(root):
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_file():
            raw = path.read_bytes()
            result[str(path.relative_to(root))] = {
                'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'raw_hex': raw.hex()}
    return result


class CountingTrust:
    def __init__(self, base):
        self.base = base
        self.reads = self.approvals = self.admissions = 0
        self.reject_read = self.reject_new = False
        self.callback = None

    def authorize_read(self, principal, world_id):
        self.reads += 1
        if self.reject_read:
            raise ContractError('AUTHORIZATION')
        self.base.authorize_read(principal, world_id)

    def verify_approval(self, approval, proposal, intent):
        self.approvals += 1
        if self.reject_new:
            raise ContractError('AUTHORIZATION', 'new actions revoked')
        if self.callback:
            self.callback()
        self.base.verify_approval(approval, proposal, intent)

    def admit(self, command, candidate, *, current_revision, admission_id):
        self.admissions += 1
        if self.reject_new:
            raise ContractError('NOT_READY')
        return self.base.admit(command, candidate, current_revision=current_revision,
                               admission_id=admission_id)


class CommandsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='universe-i4-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name)
        archive = json.loads((_FIXTURES / 'positive.json').read_bytes())
        self.rows = archive['records']
        self.by_id = {r['id']: deepcopy(r) for r in self.rows}
        self.anchors = json.loads((_FIXTURES / 'trusted_receipts.json').read_bytes())
        self.fault_phase = None
        self.roots = {}
        self.root, self.store = self.new_store('authority', self.anchors)
        self.initial = file_map(self.root)
        self.trust = CountingTrust(FixtureTrust(self.anchors))

    def new_store(self, label, anchors):
        root = self.base / label
        lease = acquire(root, 'fixture-world', initialize=True)
        self.addCleanup(lease.close)
        def fault(phase, context):
            if phase == self.fault_phase:
                raise OSError('bounded I4 injected store fault')
        store = Store(lease, trusted_receipts=anchors, fault=fault)
        self.addCleanup(store.close)
        store.initialize(self.rows[:2], digest(self.by_id['m0']))
        self.roots[label] = root
        return root, store

    def tearDown(self):
        target = os.environ.get('EDGEWORLD_I4_EVIDENCE')
        if target:
            record = {'case': self.id(), 'pid': os.getpid(), 'before': self.initial,
                      'after': {label: file_map(root) for label, root in self.roots.items()},
                      'store_state': self.store.state}
            data = (json.dumps(record, sort_keys=True) + '\n').encode()
            fd = os.open(target, os.O_WRONLY | os.O_APPEND | os.O_CLOEXEC | os.O_NOFOLLOW)
            try:
                remaining = memoryview(data)
                while remaining:
                    count = os.write(fd, remaining)
                    if count <= 0:
                        raise OSError('no evidence write progress')
                    remaining = remaining[count:]
            finally:
                os.close(fd)

    def request(self, step=1):
        return [deepcopy(self.by_id[f'{kind}{step}']) for kind in ('p', 'i', 'a', 'c')]

    def call(self, step=1, *, records=None, verifier=None, store=None, **changes):
        records = self.request(step) if records is None else records
        ids = dict(candidate_id=f'q{step}', admission_id=f'ad{step}', state_id=f's{step}',
                   event_id=f'event-{step}', result_id=f'r{step}', index_id=f'x{step}', manifest_id=f'm{step}')
        ids.update(changes)
        return execute(self.store if store is None else store, records,
                       command_digest=digest(records[-1]), principal='fixture-principal',
                       verifier=self.trust if verifier is None else verifier, **ids)

    def expect(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)
        return caught.exception

    @staticmethod
    def rebind(request):
        proposal, intent, approval, command = request
        approval['refs'] = {'proposal': digest(proposal), 'intent': digest(intent)}
        command['refs'] = {**approval['refs'], 'approval': digest(approval)}
        return request

    def test_two_commands_preserve_same_tick_exact_history_and_budget(self):
        first = self.call()
        second = self.call(2)
        snapshot = self.store.snapshot()
        closure = snapshot.closure
        self.assertEqual(len(closure.retained), 3)
        states = [closure.records[closure.records[h]['refs']['state']]['body'] for h in closure.retained]
        self.assertEqual([(x['tick'], x['revision'], x['budget'], x['random_cursor']) for x in states],
                         [(0, 2, 6, 2), (0, 1, 7, 1), (0, 0, 8, 0)])
        self.assertEqual(states[0]['value'], encode_f64(2.0))
        self.assertEqual(first.result['body']['revision'], 1)
        self.assertEqual(second.result['body']['revision'], 2)
        # API has one event_id argument for both record ID and stable EventId;
        # I0 golden happens to use separate literals, so full heads need not match.
        self.assertNotEqual(first.manifest, digest(self.by_id['m1']))
        self.assertEqual(closure.records[digest(self.by_id['s1'])], self.by_id['s1'])
        self.assertEqual(closure.records[digest(self.by_id['q1'])], self.by_id['q1'])
        self.assertEqual((self.trust.approvals, self.trust.admissions), (2, 2))

    def test_committed_retry_before_current_head_revocation_and_output_ids(self):
        first = self.call()
        self.call(2)
        before = file_map(self.root)
        self.trust.reject_new = True
        with mock.patch(_COMMANDS + '.neutral_candidate', side_effect=AssertionError('retry solved')):
            retried = self.call(event_id='BAD!', candidate_id='BAD!')
        self.assertEqual(retried, first)
        self.assertEqual(file_map(self.root), before)
        self.assertEqual((self.trust.approvals, self.trust.admissions), (2, 2))

    def test_read_authorization_is_required_even_for_committed_retry(self):
        self.call()
        self.trust.reject_read = True
        before = file_map(self.root)
        with mock.patch.object(self.store, 'lookup_result', side_effect=AssertionError('unauthorized lookup')):
            self.expect('AUTHORIZATION', self.call)
        self.assertEqual(file_map(self.root), before)

    def test_fingerprint_conflict_precedes_new_approval_and_never_writes(self):
        self.call()
        request = self.request()
        request[1]['body']['transfer'] = encode_f64(2.0)
        self.rebind(request)
        before = file_map(self.root)
        self.expect('COMMAND_CONFLICT', self.call, records=request)
        self.assertEqual(file_map(self.root), before)
        self.assertEqual(self.trust.approvals, 1)

    def test_stale_head_budget_cursor_and_expiry_reject_before_solve(self):
        with mock.patch(_COMMANDS + '.neutral_candidate', side_effect=AssertionError('rejected request solved')):
            self.expect('HEAD', self.call, 2)
            for name, value in (('budget', 9), ('random_cursor', 1)):
                request = self.request()
                request[1]['body'][name] = value
                self.expect('TRANSITION', self.call, records=self.rebind(request))
        self.assertEqual(file_map(self.root), self.initial)
        self.call()
        request = self.request(2)
        request[2]['body']['expires_revision'] = 0
        with mock.patch(_COMMANDS + '.neutral_candidate', side_effect=AssertionError('expired request solved')):
            self.expect('AUTHORIZATION', self.call, 2, records=self.rebind(request))

    def test_exact_principal_world_input_and_digest_binding(self):
        request = self.request()
        request[0]['world_id'] = 'other-world'
        self.expect('WORLD', self.call, records=request)
        request = self.request()
        request[0]['body']['principal'] = 'other-principal'
        self.expect('AUTHORIZATION', self.call, records=request)
        request = self.request()
        request[3]['refs']['proposal'] = '0' * 64
        self.expect('REFERENCE', self.call, records=request)
        self.assertEqual(file_map(self.root), self.initial)

    def test_fixture_receipts_are_defensive_and_boolean_is_not_integer(self):
        trust = FixtureTrust(self.anchors)
        self.anchors['approval-1']['principal'] = 'changed'
        self.assertIsNone(trust.verify_approval(self.by_id['a1'], self.by_id['p1'], self.by_id['i1']))
        original = json.loads((_FIXTURES / 'trusted_receipts.json').read_bytes())
        original['admission-1']['evaluated_revision'] = False
        self.expect('INTEGER', FixtureTrust, original)
        self.expect('AUTHORIZATION', trust.authorize_read, 'fixture-principal', 'other-world')
        self.expect('AUTHORIZATION', trust.authorize_read, 'untrusted', 'fixture-world')

    def test_forged_approval_and_bad_final_admission_are_rejected(self):
        request = self.request()
        request[2]['body']['receipt_id'] = 'forged'
        self.expect('AUTHORIZATION', self.call, records=self.rebind(request))
        real = self.trust.admit
        def bad_admission(*args, **kwargs):
            record = real(*args, **kwargs)
            record['body']['evaluated_revision'] = False
            return record
        with mock.patch.object(self.trust, 'admit', side_effect=bad_admission):
            self.expect('INTEGER', self.call)
        self.assertEqual(file_map(self.root), self.initial)

    def test_collision_ids_are_rejected_before_candidate_or_admission(self):
        with mock.patch(_COMMANDS + '.neutral_candidate', side_effect=AssertionError('collision solved')):
            self.expect('ID', self.call, state_id='s0')
        self.call()
        before = file_map(self.root)
        with mock.patch(_COMMANDS + '.neutral_candidate', side_effect=AssertionError('EventId reused')):
            self.expect('ID', self.call, 2, event_id='event-1')
        self.assertEqual(file_map(self.root), before)

    def test_shared_identical_proposal_is_not_duplicated_in_store_bundle(self):
        second = self.request(2)
        second[0] = deepcopy(self.by_id['p1'])
        self.rebind(second)
        anchors = deepcopy(self.anchors)
        anchors['approval-2'] = {'kind': 'approval', 'principal': 'fixture-principal',
                                 **second[2]['refs'], 'expires_revision': 4}
        # Author a separate static admission for neutral 1+1=2, without calling
        # the candidate implementation to manufacture the expected receipt.
        candidate = deepcopy(self.by_id['q2'])
        candidate['refs']['command'] = digest(second[-1])
        anchors['admission-2'] = {'kind': 'admission', 'principal': 'fixture-principal',
                                  'command': digest(second[-1]), 'candidate': digest(candidate),
                                  'evaluated_revision': 1}
        root, store = self.new_store('shared', anchors)
        trust = FixtureTrust(anchors)
        self.call(store=store, verifier=trust)
        self.call(2, records=second, store=store, verifier=trust)
        closure = store.snapshot().closure
        self.assertEqual(len(closure.retained), 3)
        proposals = [r for r in closure.records.values() if r['kind'] == 'proposal']
        self.assertEqual(len(proposals), 1)

    def test_reentrant_command_is_locked_not_recursively_submitted(self):
        attempted = []
        def enter_again():
            attempted.append(self.expect('LOCKED', self.call).code)
        self.trust.callback = enter_again
        self.call()
        self.assertEqual(attempted, ['LOCKED'])
        self.assertEqual(self.store.snapshot().closure.records[
            self.store.snapshot().closure.head]['body']['revision'], 1)

    def test_store_unknown_error_is_propagated_and_prevents_fake_retry_success(self):
        self.fault_phase = 'W6_AFTER_REPLACE'
        error = self.expect('COMMIT_UNKNOWN', self.call)
        self.assertIsInstance(error, StoreError)
        self.assertEqual(error.commit_status, 'unknown')
        self.assertEqual(self.store.state, 'recovering')
        with mock.patch(_COMMANDS + '.neutral_candidate', side_effect=AssertionError('unknown state solved')):
            self.expect('NOT_READY', self.call)

    def test_unconfirmed_snapshot_never_returns_confirmed_retry(self):
        self.call()
        pinned = self.store.pin()
        closure = validate_closure([json.loads(raw) for raw in pinned.objects.values()], pinned.head,
                                   world_id=self.store.world_id, trusted_receipts=self.store.trusted_receipts)
        self.fault_phase = 'W9_RECOVERY_SYNCED'
        self.expect('SYNC_UNSUPPORTED', self.store.confirm_recovery, pinned, closure)
        self.assertEqual(self.store.state, 'unconfirmed_readonly')
        before = file_map(self.root)
        with mock.patch(_COMMANDS + '.neutral_candidate', side_effect=AssertionError('unconfirmed solved')):
            self.expect('NOT_READY', self.call)
        self.assertEqual(file_map(self.root), before)

    def test_before_visibility_failure_retries_without_double_budget(self):
        self.fault_phase = 'W1_VALIDATED'
        error = self.expect('IO_BEFORE_VISIBILITY', self.call)
        self.assertIsInstance(error, StoreError)
        self.assertEqual(error.commit_status, 'not_attempted')
        self.assertEqual(self.store.state, 'ready')
        self.assertEqual(file_map(self.root), self.initial)
        self.fault_phase = None
        receipt = self.call()
        self.assertEqual(receipt.result['body']['revision'], 1)
        closure = self.store.snapshot().closure
        state = closure.records[closure.records[closure.head]['refs']['state']]['body']
        self.assertEqual((state['budget'], state['random_cursor']), (7, 1))

    def test_neutral_candidate_is_pure_and_rejects_nonfinite_sum(self):
        before = file_map(self.root)
        request = self.request()
        prior = deepcopy(self.by_id['s0'])
        prior['body']['value'] = encode_f64(-0.0)
        request[1]['body']['transfer'] = encode_f64(-0.0)
        self.rebind(request)
        candidate = neutral_candidate(prior, request[-1], request[1], candidate_id='test-zero')
        self.assertEqual(candidate['body']['value']['$f64'], '8000000000000000')
        largest = float.fromhex('0x1.fffffffffffffp+1023')
        prior['body']['value'] = encode_f64(largest)
        request[1]['body']['transfer'] = encode_f64(largest)
        self.rebind(request)
        self.expect('TRANSITION', neutral_candidate, prior, request[-1], request[1], candidate_id='overflow')
        self.assertEqual(file_map(self.root), before)

    def test_rule_dag_is_deterministic_and_rejects_missing_cycles_and_hidden_inputs(self):
        self.assertEqual(validate_rule_dag({}), ())
        self.assertEqual(validate_rule_dag({'c': ['a', 'b'], 'b': [], 'a': []}), ('a', 'b', 'c'))
        for graph in ({'a': ['missing']}, {'a': ['a']}, {'a': ['b'], 'b': ['a']}, {'a': [], 'b': ['a', 'a']}):
            self.expect('REFERENCE', validate_rule_dag, graph)
        self.expect('SCHEMA', validate_rule_dag, {'a': 'b'})
        self.expect('ID', validate_rule_dag, {True: []})

    def test_uninitialized_store_and_invalid_store_do_not_create_confirmed_result(self):
        lease = acquire(self.base / 'empty', 'fixture-world', initialize=True)
        self.addCleanup(lease.close)
        store = Store(lease, trusted_receipts=self.anchors)
        self.addCleanup(store.close)
        self.expect('NOT_READY', self.call, store=store)
        self.expect('SCHEMA', self.call, store=object())


    def test_neutral_helpers_reject_composite_records_instead_of_coercing_their_bodies(self):
        archive = json.loads((_FIXTURES.parent / 'universe_authority_v0_2/positive.json').read_bytes())
        rows = {r['id']: r for r in archive['records']}
        self.expect('DOMAIN', neutral_candidate, rows['state-0'], rows['command-record-1'], rows['intent-1'],
                    candidate_id='no-neutral-coercion')
        self.expect('DOMAIN', self.trust.base.verify_approval, rows['approval-1'], rows['proposal-1'], rows['intent-1'])


if __name__ == '__main__':
    unittest.main()
