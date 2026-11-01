"""Owner-authenticated deterministic preparation, distinct from admission."""
from copy import deepcopy
from dataclasses import replace, FrozenInstanceError
from unittest import mock

from engine.universe_authority.codec import ContractError, OwnerSession
from engine.universe_authority.commands import PreparedCommand, prepare_command
from engine.universe_authority.trust import open_trust
from test_universe_composite_commands import CompositeCase, CountingTrust


class PrepareCommandTests(CompositeCase):
    def request(self, proposal, intent, **changes):
        arguments = dict(session=self.session, proposal=proposal, intent=intent,
                         approval_id='approval-one', command_record_id='command-record-one', signer=self.signer)
        arguments.update(changes)
        return prepare_command(self.store, **arguments)

    def test_same_head_preparation_is_deterministic_defensive_and_has_no_world_writes(self):
        proposal, intent = self.inputs()
        before = self.capture('before-prepare')
        first = self.request(proposal, intent)
        second = self.request(proposal, intent)
        self.assertEqual(first.command_digest, second.command_digest)
        self.assertEqual(first.command_records, second.command_records)
        self.assertIsNone(first.committed_result)
        self.assertEqual(0, first.command_records[2]['body']['expires_revision'])
        self.assertEqual(2, self.signer.calls.count('sign'))
        self.assertNotIn('admit', self.signer.calls)
        first.command_records[0]['body'].clear(); proposal['body'].clear()
        self.assertTrue(first.command_records[0]['body'])
        with self.assertRaises(FrozenInstanceError):
            first.command_digest = '0' * 64
        self.assertEqual(before, self.capture('after-prepare'))
        self.assertEqual(0, self.state()['body']['revision'])

    def test_committed_retry_authenticates_and_returns_original_without_signing(self):
        first = self.prepared()
        committed = self.advance(first)
        self.advance(self.prepared('two'), 'two')
        session = OwnerSession(self.session.principal, False, ())
        signer = CountingTrust(open_trust(self.key_dir, context=self.context, signing=True, session=session))
        before = self.capture('before-cached-prepare')
        retry = self.request(first.command_records[0], first.command_records[1], session=session, signer=signer)
        self.assertEqual(first.command_records, retry.command_records)
        self.assertEqual(first.command_digest, retry.command_digest)
        self.assertEqual(committed.result, retry.committed_result)
        retry.committed_result['body'].clear()
        self.assertTrue(retry.committed_result['body'])
        self.assertEqual(['read', 'context'], signer.calls)
        self.assertEqual(before, self.capture('after-cached-prepare'))

    def test_committed_conflicts_never_resign_or_rewrite_original(self):
        first = self.prepared(); self.advance(first)
        variants = []
        proposal, intent = first.command_records[:2]
        changed = deepcopy(proposal); changed['body']['output'] = 'different request'
        variants.append((changed, intent, {}))
        changed = deepcopy(intent); changed['body']['budget'] = 1
        variants.append((proposal, changed, {}))
        variants.extend(((proposal, intent, {'approval_id': 'another-approval'}),
                         (proposal, intent, {'command_record_id': 'another-command-record'})))
        before = self.capture('before-conflicts')
        self.signer.calls.clear()
        for p, i, kwargs in variants:
            self.assert_code('COMMAND_CONFLICT', self.request, p, i, **kwargs)
        self.assertNotIn('sign', self.signer.calls)
        self.assertEqual(before, self.capture('after-conflicts'))

    def test_new_policy_and_id_failures_happen_before_signing(self):
        before = self.capture('before-invalid-prepare')
        cases = (({'expected_revision': 1}, 'HEAD'), ({'random_cursor': 1}, 'TRANSITION'),
                 ({'budget': 9}, 'TRANSITION'), ({'tick_delta': 0}, 'TRANSITION'))
        for changes, code in cases:
            proposal, intent = self.inputs(action='physics_step', **changes)
            self.assert_code(code, self.request, proposal, intent)
        proposal, intent = self.inputs()
        intent['refs']['config'] = 'f' * 64
        self.assert_code('PHYSICS_INVALID', self.request, proposal, intent)
        proposal, intent = self.inputs()
        self.assert_code('ID', self.request, proposal, intent, approval_id=True)
        self.assert_code('AUTHORIZATION', self.request, proposal, intent,
                         session=OwnerSession(self.session.principal, False, ()))
        self.assertNotIn('sign', self.signer.calls)
        self.assertEqual(before, self.capture('after-invalid-prepare'))

    def test_read_and_context_authorization_precede_cached_lookup(self):
        first = self.prepared(); self.advance(first)
        proposal, intent = first.command_records[:2]
        other = CountingTrust(open_trust(self.key_dir, context=self.context, signing=True,
                                         session=OwnerSession('another-owner', False, ())))
        with mock.patch.object(self.store, 'lookup_result', side_effect=AssertionError('lookup before auth')):
            self.assert_code('AUTHORIZATION', self.request, proposal, intent, signer=other)
        self.assertEqual(['read'], other.calls)
        wrong = CountingTrust(open_trust(self.key_dir, context=replace(self.context, expected_options='d' * 64),
                                         signing=True, session=self.session))
        with mock.patch.object(self.store, 'lookup_result', side_effect=AssertionError('lookup before context auth')):
            self.assert_code('AUTHORIZATION', self.request, proposal, intent, signer=wrong)
        self.assertEqual(['read', 'context'], wrong.calls)

    def test_uncommitted_preparation_is_not_a_reservation_or_implicit_head_retry(self):
        first = self.prepared()
        second = self.prepared('two')
        self.advance(second, 'two')
        self.signer.calls.clear()
        self.assert_code('HEAD', self.request, first.command_records[0], first.command_records[1])
        self.assertNotIn('sign', self.signer.calls)
        self.assert_code('HEAD', self.advance, first)
        third = self.prepared('three')  # Explicit owner request with new stable IDs.
        self.advance(third, 'three')
        self.assertEqual(2, self.state()['body']['revision'])

    def test_reentrant_preparation_is_locked_without_nested_authority_work(self):
        proposal, intent = self.inputs()
        nested = []
        def callback():
            nested.append(self.assert_code('LOCKED', self.request, proposal, intent).code)
        self.signer.before_sign = callback
        self.request(proposal, intent)
        self.assertEqual(['LOCKED'], nested)
        self.assertEqual(0, self.state()['body']['revision'])

    def test_malformed_signer_output_and_uncertainty_cannot_publish(self):
        proposal, intent = self.inputs()
        before = self.capture('before-bad-signatures')
        actual = self.signer.delegate
        class BadSigner:
            def authorize_read(_, *args): actual.authorize_read(*args)
            def assert_context(_, *args): actual.assert_context(*args)
            def sign_approval(_, unsigned):
                signed = actual.sign_approval(unsigned)
                signed['body']['auth_tag'] = '0' * 64
                return signed
        self.assert_code('AUTHORIZATION', self.request, proposal, intent, signer=BadSigner())
        def uncertain():
            raise ContractError('NOT_READY', 'injected signing uncertainty')
        self.signer.before_sign = uncertain
        self.assert_code('NOT_READY', self.request, proposal, intent)
        self.assertEqual(before, self.capture('after-bad-signatures'))
        self.assertEqual(0, self.state()['body']['revision'])
