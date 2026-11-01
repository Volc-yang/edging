"""Abstract synthetic provider integration; no Genesis import or GPU use."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest

from engine.universe_authority.codec import (ContractError, DeploymentContext, OwnerSession,
                                             ProvisionSpec, canonical, digest)
from engine.universe_authority.commands import execute, prepare_command
from engine.universe_authority.ownership import acquire
from engine.universe_authority.physics import PhysicsDraft, PhysicsIds, PhysicsInitialDraft, PhysicsInitialIds
from engine.universe_authority.records import validate_closure
from engine.universe_authority.store import BlobWrite, Store, StoreError
from engine.universe_authority.trust import open_trust, provision

FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_2'


class CountingTrust:
    def __init__(self, delegate):
        self.delegate = delegate
        self.calls = []
        self.before_sign = self.before_admit = None

    def authorize_read(self, principal, world_id):
        self.calls.append('read')
        self.delegate.authorize_read(principal, world_id)

    def assert_context(self, context):
        self.calls.append('context')
        self.delegate.assert_context(context)

    def sign_approval(self, unsigned):
        self.calls.append('sign')
        if self.before_sign:
            self.before_sign()
        return self.delegate.sign_approval(unsigned)

    def verify_approval(self, approval, proposal, intent):
        self.calls.append('verify')
        self.delegate.verify_approval(approval, proposal, intent)

    def admit(self, command, candidate, **kwargs):
        self.calls.append('admit')
        if self.before_admit:
            self.before_admit()
        return self.delegate.admit(command, candidate, **kwargs)


class SyntheticProvider:
    def __init__(self, template, raw, mode='valid'):
        self.template, self.raw, self.mode = template, raw, mode
        self.calls = 0
        self.reader = None

    def propose(self, prior_state, command, intent, *, records, read_blob, ids):
        self.calls += 1
        self.reader = read_blob
        old = deepcopy(prior_state)
        previous = deepcopy(records[old['refs']['snapshot']])
        checkpoint = records[previous['refs']['checkpoint']]
        if read_blob(checkpoint['body']['payload_sha256']) != self.raw[checkpoint['body']['payload_sha256']]:
            raise AssertionError('incorrect committed input')
        if self.mode == 'fail':
            raise RuntimeError('synthetic failure')
        if self.mode == 'not-draft':
            return {}
        if self.mode == 'mutate-input':
            prior_state['body']['budget'] = 999
            records[old['refs']['snapshot']]['body']['physical_step_count'] = 999
        config, binding = intent['refs']['config'], intent['refs']['binding']
        sample = deepcopy(next(r for r in self.template if r['id'] == 'sample-1'))
        descriptor = deepcopy(next(r for r in self.template if r['id'] == 'checkpoint-1'))
        for record in (sample, descriptor):
            record['world_id'] = old['world_id']
            record['refs']['config'] = config; record['refs']['binding'] = binding
        sample['id'] = ids.sample
        descriptor['id'] = ids.checkpoint_descriptor
        descriptor['refs']['build'] = records[config]['refs']['build']
        snapshot = {'domain': command['domain'], 'version': '0.2', 'world_id': old['world_id'],
                    'kind': 'physics_snapshot', 'id': ids.snapshot,
                    'body': {'case_id': intent['body']['case_id'],
                             'physical_step_count': previous['body']['physical_step_count'] + 8},
                    'refs': {'config': config, 'binding': binding, 'sample': digest(sample), 'checkpoint': digest(descriptor)}}
        if self.mode == 'wrong-step':
            snapshot['body']['physical_step_count'] -= 1
        if self.mode == 'wrong-case':
            snapshot['body']['case_id'] = 'strong'
        if self.mode == 'wrong-ids':
            descriptor['id'] = 'unexpected-id'
            snapshot['refs']['checkpoint'] = digest(descriptor)
        if self.mode == 'wrong-build':
            descriptor['refs']['build'] = 'f' * 64
            snapshot['refs']['checkpoint'] = digest(descriptor)
        candidate = {'domain': command['domain'], 'version': '0.2', 'world_id': old['world_id'],
                     'kind': 'candidate', 'id': ids.candidate,
                     'body': {'adapter_kind': 'genesis', 'physics_profile': 'genesis-rigid-support.v0.1',
                              'tick': old['body']['tick'] + 1, 'revision': old['body']['revision'] + 1,
                              'influence_mm': -10 if old['body']['tick'] == 0 else 0},
                     'refs': {'command': digest(command), 'prior_state': digest(old), 'snapshot': digest(snapshot)}}
        if self.mode == 'wrong-d':
            candidate['body']['influence_mm'] = -11
        if self.mode == 'wrong-prior':
            candidate['refs']['prior_state'] = next(k for k, r in records.items() if r['kind'] == 'manifest')
        if self.mode == 'wrong-command':
            candidate['refs']['command'] = 'f' * 64
        if self.mode == 'wrong-adapter':
            candidate['body']['adapter_kind'] = 'checkpoint_reuse'
        draft_records = (sample, descriptor, snapshot, candidate)
        if self.mode == 'wrong-world':
            for record in draft_records:
                record['world_id'] = 'other-world'
            snapshot['refs']['sample'] = digest(sample)
            snapshot['refs']['checkpoint'] = digest(descriptor)
            candidate['refs']['snapshot'] = digest(snapshot)
        blob = BlobWrite(descriptor['body']['payload_sha256'], self.raw[descriptor['body']['payload_sha256']],
                         descriptor['body']['media_type'], descriptor['body']['artifact_class'])
        if self.mode == 'wrong-blob':
            payload = b'another public static payload'
            blob = BlobWrite(hashlib.sha256(payload).hexdigest(), payload, blob.media_type, blob.artifact_class)
        return PhysicsDraft(draft_records, digest(candidate), digest(snapshot), blob)


class CompositeCase(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='universe-e4-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.root = self.base / 'world'
        self.key_dir = self.base / 'key'
        self.template = json.loads((FIXTURES / 'positive.json').read_text())['records']
        self.raw = {k: bytes.fromhex(v) for k, v in json.loads((FIXTURES / 'synthetic_blobs.json').read_text())['blobs'].items()}
        constants = json.loads((FIXTURES / 'trust_context.json').read_text())
        anchor = provision(self.key_dir, spec=ProvisionSpec('composite-demo', self.root))
        self.context = DeploymentContext('composite-demo', str(self.root), anchor.trust_anchor,
                                         constants['expected_build'], constants['expected_options'],
                                         artifact_class='synthetic-contract-only')
        self.session = OwnerSession('fixture-principal', True, ('retain_snapshot', 'physics_step'))
        self.signer = CountingTrust(open_trust(self.key_dir, context=self.context, signing=True, session=self.session))
        self.reader = open_trust(self.key_dir, context=self.context)
        self.lease = acquire(self.root, self.context.world_id, initialize=True, domain_version='0.2',
                             profile=self.context.storage_profile, context=self.context)
        self.addCleanup(self.lease.close)
        self.fail_phase = None
        def fault(phase, context):
            if phase == self.fail_phase:
                raise OSError('injected ' + phase)
        self.store = Store(self.lease, context=self.context, trust_verifier=self.reader, fault=fault)
        self.addCleanup(self.store.close)
        initial = self.template[:31]
        descriptor = next(r for r in initial if r['kind'] == 'checkpoint_descriptor')
        blob = BlobWrite(descriptor['body']['payload_sha256'], self.raw[descriptor['body']['payload_sha256']],
                         descriptor['body']['media_type'], descriptor['body']['artifact_class'])
        self.store.initialize(initial, digest(initial[-1]), blobs=(blob,))

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)
        return caught.exception

    def inputs(self, label='one', action='retain_snapshot', **changes):
        closure = self.store.snapshot().closure
        records = closure.records
        prior = records[records[closure.head]['refs']['state']]
        snapshot = records[prior['refs']['snapshot']]
        proposal = {'domain': 'edgeworld.universe.authority', 'version': '0.2', 'world_id': self.context.world_id,
                    'kind': 'proposal', 'id': 'proposal-' + label,
                    'body': {'principal': self.session.principal, 'output': 'explicit abstract action'}, 'refs': {}}
        intent = {'domain': 'edgeworld.universe.authority', 'version': '0.2', 'world_id': self.context.world_id,
                  'kind': 'intent', 'id': 'intent-' + label,
                  'body': {'principal': self.session.principal, 'command_id': 'command-' + label,
                           'expected_revision': prior['body']['revision'], 'random_cursor': prior['body']['random_cursor'],
                           'action': action, 'tick_delta': 0 if action == 'retain_snapshot' else 1,
                           'case_id': None if action == 'retain_snapshot' else 'weak',
                           'budget': 0 if action == 'retain_snapshot' else 1},
                  'refs': {'config': snapshot['refs']['config'], 'binding': snapshot['refs']['binding']}}
        intent['body'].update(changes)
        return proposal, intent

    def prepared(self, label='one', action='retain_snapshot', **changes):
        proposal, intent = self.inputs(label, action, **changes)
        return prepare_command(self.store, session=self.session, proposal=proposal, intent=intent,
                               approval_id='approval-' + label, command_record_id='command-record-' + label,
                               signer=self.signer)

    def output_ids(self, label='one'):
        return dict(candidate_id='candidate-' + label, admission_id='admission-' + label,
                    state_id='state-' + label, event_id='event-' + label, result_id='result-' + label,
                    index_id='index-' + label, manifest_id='manifest-' + label)

    def advance(self, prepared, label='one', provider=None, physics_ids=None, **changes):
        options = self.output_ids(label); options.update(changes)
        return execute(self.store, prepared.command_records, command_digest=prepared.command_digest,
                       principal=self.session.principal, verifier=self.signer,
                       provider=provider, physics_ids=physics_ids, **options)

    def state(self):
        closure = self.store.snapshot().closure
        return closure.records[closure.records[closure.head]['refs']['state']]

    def capture(self, label):
        result = {str(p.relative_to(self.root)): {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                                                  'bytes': p.stat().st_size}
                  for p in sorted(self.root.rglob('*')) if p.is_file()}
        configured = os.environ.get('EDGEWORLD_E4_RAW')
        if configured:
            destination = Path(configured) / (type(self).__name__ + '.' + self._testMethodName) / label
            destination.mkdir(parents=True, exist_ok=False)
            (destination / 'map.json').write_text(json.dumps({'authority_root': str(self.root), 'files': result}, sort_keys=True, indent=2) + '\n')
            for relative in result:
                target = destination / 'files' / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open('xb') as output:
                    output.write((self.root / relative).read_bytes())
        return result

    def recover(self):
        pinned = self.store.pin()
        closure = validate_closure([json.loads(raw) for raw in pinned.objects.values()], pinned.head,
                                   world_id=self.context.world_id, domain_version='0.2', context=self.context,
                                   trust_verifier=self.reader, blobs=pinned.blobs)
        return self.store.confirm_recovery(pinned, closure)


class CompositeCommandsTests(CompositeCase):
    def test_retain_physics_retain_preserves_authority_counters_and_blob_scope(self):
        initial = self.state()
        provider = SyntheticProvider(self.template, self.raw)
        one = self.prepared('one')
        self.advance(one, 'one', provider=provider)
        retained = self.state()
        self.assertEqual(initial['refs']['snapshot'], retained['refs']['snapshot'])
        self.assertEqual({'tick': 0, 'revision': 1, 'development_mm': None, 'budget': 8, 'random_cursor': 0}, retained['body'])
        self.assertEqual(0, provider.calls)
        two = self.prepared('two', 'physics_step')
        ids = PhysicsIds('candidate-two', 'sample-two', 'snapshot-two', 'checkpoint-two')
        receipt = self.advance(two, 'two', provider, ids)
        self.assertEqual({'tick': 1, 'revision': 2, 'development_mm': -10, 'budget': 7, 'random_cursor': 1}, self.state()['body'])
        self.assertEqual(1, provider.calls)
        self.assertEqual(self.state()['refs']['snapshot'], receipt.result['refs']['checkpoint'])
        physical = self.state()
        three = self.prepared('three')
        self.advance(three, 'three', provider=provider)
        self.assertEqual(physical['refs'], self.state()['refs'])
        self.assertEqual(dict(physical['body'], revision=3), self.state()['body'])
        self.assertEqual(1, provider.calls)
        self.assertEqual(2, len(self.store.snapshot().closure.binary_refs))
        self.assertFalse(hasattr(provider.reader, '__self__'))
        self.assertFalse(hasattr(provider.reader, 'commit'))
        self.assertFalse(hasattr(provider.reader, 'sign_approval'))
        self.assertFalse(hasattr(provider.reader, '__dict__'))
        self.assert_code('REFERENCE', provider.reader, 'f' * 64)
        self.capture('final')

    def test_committed_retry_precedes_provider_action_expiry_and_output_id_checks(self):
        prepared = self.prepared('one', 'physics_step')
        provider = SyntheticProvider(self.template, self.raw)
        receipt = self.advance(prepared, provider=provider,
                               physics_ids=PhysicsIds('candidate-one', 'sample-one', 'snapshot-one', 'checkpoint-one'))
        self.advance(self.prepared('two'), 'two')
        before = self.capture('before-retry')
        restricted = open_trust(self.key_dir, context=self.context, signing=True,
                                session=OwnerSession(self.session.principal, False, ()))
        self.signer = CountingTrust(restricted)
        retry = self.advance(prepared, candidate_id=True, state_id='', provider=None, physics_ids=None)
        self.assertEqual(receipt.manifest, retry.manifest)
        self.assertEqual(receipt.result, retry.result)
        self.assertEqual(['read', 'context'], self.signer.calls)
        self.assertEqual(1, provider.calls)
        self.assertEqual(before, self.capture('after-retry'))

    def test_rejected_provider_drafts_never_reach_admission_or_storage(self):
        modes = {'wrong-d': 'TRANSITION', 'wrong-step': 'TRANSITION', 'wrong-case': 'TRANSITION',
                 'wrong-ids': 'ID', 'wrong-build': 'REFERENCE', 'wrong-prior': 'REFERENCE',
                 'wrong-command': 'REFERENCE', 'wrong-adapter': 'TRANSITION', 'wrong-world': 'WORLD',
                 'wrong-blob': 'CORRUPT', 'not-draft': 'PHYSICS_INVALID', 'fail': 'PHYSICS_FAILED'}
        prepared = self.prepared('one', 'physics_step')
        before = self.capture('before-invalid-drafts')
        for mode, code in modes.items():
            with self.subTest(mode=mode):
                self.signer.calls.clear()
                provider = SyntheticProvider(self.template, self.raw, mode)
                self.assert_code(code, self.advance, prepared, provider=provider,
                                 physics_ids=PhysicsIds('candidate-one', 'sample-one', 'snapshot-one', 'checkpoint-one'))
                self.assertNotIn('admit', self.signer.calls)
                self.assertEqual(before, self.capture('after-' + mode))
        self.assertEqual(0, self.state()['body']['revision'])

    def test_input_copies_and_protocol_drafts_are_immutable(self):
        prepared = self.prepared('one', 'physics_step')
        provider = SyntheticProvider(self.template, self.raw, 'mutate-input')
        self.advance(prepared, provider=provider,
                     physics_ids=PhysicsIds('candidate-one', 'sample-one', 'snapshot-one', 'checkpoint-one'))
        self.assertEqual(7, self.state()['body']['budget'])
        initial = tuple(deepcopy(r) for r in self.template if r['id'] in ('sample-0', 'checkpoint-0', 'snapshot-0'))
        descriptor = next(r for r in initial if r['kind'] == 'checkpoint_descriptor')
        blob = BlobWrite(descriptor['body']['payload_sha256'], self.raw[descriptor['body']['payload_sha256']],
                         descriptor['body']['media_type'], descriptor['body']['artifact_class'])
        snapshot = next(r for r in initial if r['kind'] == 'physics_snapshot')
        draft = PhysicsInitialDraft(initial, digest(snapshot), blob)
        draft.records[0]['body'].clear(); initial[0]['body'].clear()
        self.assertTrue(draft.records[0]['body'])
        with self.assertRaises(FrozenInstanceError):
            draft.snapshot_digest = 'f' * 64
        self.assert_code('ID', PhysicsIds, '', 'a', 'b', 'c')
        self.assert_code('ID', PhysicsInitialIds, True, 'b', 'c')
        self.assert_code('SCHEMA', PhysicsInitialDraft, (), 'f' * 64, blob)

    def test_new_action_policy_ids_conflict_and_bad_approval_are_pre_provider(self):
        prepared = self.prepared('one', 'physics_step')
        provider = SyntheticProvider(self.template, self.raw)
        self.assert_code('ID', self.advance, prepared, provider=provider,
                         physics_ids=PhysicsIds('different', 'sample-one', 'snapshot-one', 'checkpoint-one'))
        self.assert_code('ID', self.advance, prepared, provider=provider,
                         physics_ids=PhysicsIds('candidate-one', 'sample-0', 'snapshot-one', 'checkpoint-one'))
        self.assertEqual(0, provider.calls)
        bad = list(prepared.command_records)
        bad[2]['body']['auth_tag'] = '0' * 64
        bad[3]['refs']['approval'] = digest(bad[2])
        self.assert_code('AUTHORIZATION', execute, self.store, bad, command_digest=digest(bad[3]),
                         principal=self.session.principal, verifier=self.signer,
                         provider=provider, physics_ids=PhysicsIds('candidate-one', 'sample-one', 'snapshot-one', 'checkpoint-one'),
                         **self.output_ids())
        self.assertEqual(0, provider.calls)
        self.assertNotIn('admit', self.signer.calls)

    def test_stale_head_and_expired_new_command_reject_before_provider(self):
        stale = self.prepared('one', 'physics_step')
        self.advance(self.prepared('two'), 'two')
        provider = SyntheticProvider(self.template, self.raw)
        ids = PhysicsIds('candidate-one', 'sample-one', 'snapshot-one', 'checkpoint-one')
        self.assert_code('HEAD', self.advance, stale, provider=provider, physics_ids=ids)
        prepared = self.prepared('three', 'physics_step')
        records = list(prepared.command_records)
        unsigned = deepcopy(records[2]); del unsigned['body']['auth_tag']
        unsigned['body']['expires_revision'] = 0
        records[2] = self.signer.sign_approval(unsigned)
        records[3]['refs']['approval'] = digest(records[2])
        before = self.capture('before-expiry')
        self.signer.calls.clear()
        self.assert_code('AUTHORIZATION', execute, self.store, records, command_digest=digest(records[-1]),
                         principal=self.session.principal, verifier=self.signer, provider=provider,
                         physics_ids=PhysicsIds('candidate-three', 'sample-three', 'snapshot-three', 'checkpoint-three'),
                         **self.output_ids('three'))
        self.assertEqual(0, provider.calls)
        self.assertNotIn('admit', self.signer.calls)
        self.assertEqual(before, self.capture('after-expiry'))

    def test_committed_fingerprint_conflict_precedes_new_checks_and_read_auth_is_first(self):
        first = self.prepared(); self.advance(first)
        records = list(first.command_records)
        records[0]['body']['output'] = 'conflicting proposal'
        unsigned = deepcopy(records[2]); del unsigned['body']['auth_tag']
        unsigned['refs']['proposal'] = digest(records[0])
        records[2] = self.signer.sign_approval(unsigned)
        records[3]['refs']['proposal'] = digest(records[0])
        records[3]['refs']['approval'] = digest(records[2])
        self.signer.calls.clear()
        self.assert_code('COMMAND_CONFLICT', execute, self.store, records, command_digest=digest(records[-1]),
                         principal=self.session.principal, verifier=self.signer, **self.output_ids())
        self.assertEqual(['read', 'context'], self.signer.calls)
        self.signer.calls.clear()
        self.assert_code('AUTHORIZATION', execute, self.store, first.command_records,
                         command_digest=first.command_digest, principal='unauthorized',
                         verifier=self.signer, **self.output_ids())
        self.assertEqual(['read'], self.signer.calls)

    def test_expiry_valid_63_external_command_executes_but_is_not_a_prepared_history(self):
        prepared = self.prepared()
        records = list(prepared.command_records)
        unsigned = deepcopy(records[2]); del unsigned['body']['auth_tag']
        unsigned['body']['expires_revision'] = 63
        records[2] = self.signer.sign_approval(unsigned)
        records[3]['refs']['approval'] = digest(records[2])
        execute(self.store, records, command_digest=digest(records[-1]), principal=self.session.principal,
                verifier=self.signer, **self.output_ids())
        self.assertEqual(1, self.state()['body']['revision'])
        self.signer.calls.clear()
        self.assert_code('COMMAND_CONFLICT', prepare_command, self.store, session=self.session,
                         proposal=records[0], intent=records[1], approval_id=records[2]['id'],
                         command_record_id=records[3]['id'], signer=self.signer)
        self.assertNotIn('sign', self.signer.calls)

    def test_unknown_store_boundary_preserves_status_and_retry_recovers_original(self):
        prepared = self.prepared()
        before = self.capture('before-unknown')
        self.fail_phase = 'W8_BEFORE_RESPONSE'
        error = self.assert_code('COMMIT_UNKNOWN', self.advance, prepared)
        self.assertIs(type(error), StoreError)
        self.assertEqual('unknown', error.commit_status)
        self.assertEqual('W8_BEFORE_RESPONSE', error.phase)
        self.capture('after-unknown')
        self.assert_code('NOT_READY', self.advance, prepared)
        self.fail_phase = None
        self.recover()
        self.signer.calls.clear()
        result = self.advance(prepared)
        self.assertEqual(1, result.result['body']['revision'])
        self.assertNotIn('admit', self.signer.calls)
        self.assertNotEqual(before, self.capture('after-recovery'))

    def test_unconfirmed_never_prepares_or_returns_confirmed_retry(self):
        prepared = self.prepared()
        self.advance(prepared)
        self.fail_phase = 'W9_RECOVERY_SYNCED'
        self.assert_code('SYNC_UNSUPPORTED', self.recover)
        self.assertEqual('unconfirmed_readonly', self.store.snapshot().storage_state)
        self.assert_code('NOT_READY', self.advance, prepared)
        self.assert_code('NOT_READY', prepare_command, self.store, session=self.session,
                         proposal=prepared.command_records[0], intent=prepared.command_records[1],
                         approval_id='approval-one', command_record_id='command-record-one', signer=self.signer)
        self.capture('unconfirmed')
