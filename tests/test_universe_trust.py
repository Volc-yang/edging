"""Local POSIX key lifecycle and read-only/signer capability boundaries."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import hashlib
import hmac
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from engine.universe_authority.codec import (
    ContractError, DeploymentContext, OwnerSession, ProvisionSpec, canonical, digest,
)
from engine.universe_authority.trust import LocalTrust, open_trust, provision
from engine.universe_authority.records import validate_record

FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_2'


class UniverseTrustTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='universe-e1-trust-')
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.key_dir = self.base / 'key'
        self.spec = ProvisionSpec('trust-world', self.base / 'world')
        self.session = OwnerSession('owner', True, ('physics_step', 'retain_snapshot'))

    def create(self):
        anchor = provision(self.key_dir, spec=self.spec)
        context = DeploymentContext(anchor.world_id, anchor.authority_root, anchor.trust_anchor, 'a' * 64, 'b' * 64)
        return anchor, context

    def signer(self, context):
        return open_trust(self.key_dir, context=context, signing=True, session=self.session)

    def unsigned(self, kind='approval'):
        return {'domain': 'edgeworld.universe.authority', 'version': '0.2', 'world_id': self.spec.world_id,
                'kind': kind, 'id': kind + '-one',
                'body': {'principal': 'owner', 'receipt_id': 'receipt-one',
                         'expires_revision' if kind == 'approval' else 'evaluated_revision': 0},
                'refs': {'proposal': '1' * 64, 'intent': '2' * 64} if kind == 'approval'
                else {'command': '1' * 64, 'candidate': '2' * 64}}

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def test_provision_returns_only_public_anchor_after_fsync_and_read_reopen(self):
        calls = []
        real_sync = os.fsync
        def sync(fd):
            calls.append(stat.S_ISREG(os.fstat(fd).st_mode))
            return real_sync(fd)
        with patch('engine.universe_authority.trust.os.fsync', side_effect=sync):
            anchor, context = self.create()
        self.assertEqual([True, False, False], calls)
        key = (self.key_dir / 'authority.key').read_bytes()
        self.assertEqual(32, len(key))
        self.assertNotEqual(bytes(range(32)), key)
        expected = hashlib.sha256(b'edgeworld.universe.trust-anchor\0v0.2\0' + self.spec.world_id.encode()
                                  + b'\0' + str(self.spec.authority_root).encode() + b'\0' + key).hexdigest()
        self.assertEqual(expected, anchor.trust_anchor)
        self.assertEqual(0o700, stat.S_IMODE(self.key_dir.stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE((self.key_dir / 'authority.key').stat().st_mode))
        self.assertFalse(self.spec.authority_root.exists())
        verifier = open_trust(self.key_dir, context=context)
        verifier.assert_context(context)
        self.assertFalse(hasattr(verifier, 'key'))
        self.assertFalse(hasattr(verifier, '_tag'))
        self.assertFalse(hasattr(verifier, 'sign_approval'))
        self.assertFalse(hasattr(verifier, 'sign_admission'))
        self.assertFalse(hasattr(verifier, '__dict__'))
        self.assertNotIn(key.hex(), repr(verifier))
        with self.assertRaises(AttributeError):
            verifier._context = replace(context, world_id='other')
        with self.assertRaises(FrozenInstanceError):
            anchor.trust_anchor = '0' * 64

    def test_read_only_operations_create_nothing_and_wrong_key_never_regenerates(self):
        context = DeploymentContext('trust-world', str(self.spec.authority_root), '0' * 64, 'a' * 64, 'b' * 64)
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context)
        self.assertEqual([], list(self.base.iterdir()))
        _, context = self.create()
        before = (self.key_dir / 'authority.key').read_bytes()
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=replace(context, trust_anchor='0' * 64))
        self.assertEqual(before, (self.key_dir / 'authority.key').read_bytes())
        self.assertEqual(['authority.key'], [x.name for x in self.key_dir.iterdir()])
        self.assert_code('NOT_READY', provision, self.key_dir, spec=self.spec)
        self.assertEqual(before, (self.key_dir / 'authority.key').read_bytes())

    def test_mac_matches_independent_framing_for_approval_and_admission(self):
        _, context = self.create()
        signer = self.signer(context)
        self.assertIs(type(signer), LocalTrust)
        reader = open_trust(self.key_dir, context=context)
        key = (self.key_dir / 'authority.key').read_bytes()
        for kind, method in (('approval', signer.sign_approval), ('admission', signer.sign_admission)):
            unsigned = self.unsigned(kind)
            signed = method(unsigned)
            self.assertNotIn('auth_tag', unsigned['body'])
            encoded = json.dumps(unsigned, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()
            message = (b'edgeworld.universe.receipt\0v0.2\0' + context.trust_anchor.encode()
                       + b'\0' + kind.encode() + b'\0' + encoded)
            self.assertEqual(hmac.new(key, message, hashlib.sha256).hexdigest(), signed['body']['auth_tag'])
            validate_record(signed)
            reader(signed)
            self.assertEqual(signed, method(unsigned))
            bad = deepcopy(signed); bad['body']['auth_tag'] = '0' * 64
            self.assert_code('AUTHORIZATION', reader, bad)
            bad = deepcopy(signed); bad['body']['principal'] = 'other'
            self.assert_code('AUTHORIZATION', reader, bad)
        self.assertNotIn(key.hex(), repr(signer))

    def test_signer_requires_owner_session_and_never_derives_principal_from_hash(self):
        _, context = self.create()
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context, signing=True)
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context, signing=1, session=self.session)
        signer = self.signer(context)
        self.assert_code('AUTHORIZATION', signer.authorize_read, 'other', self.spec.world_id)
        self.assert_code('AUTHORIZATION', signer.authorize_read, 'owner', 'other-world')
        wrong = self.unsigned(); wrong['body']['principal'] = 'other'
        self.assert_code('AUTHORIZATION', signer.sign_approval, wrong)
        # A different explicitly injected owner session is supported; no global
        # mutable principal registry is inferred from prior hashes or receipts.
        other = open_trust(self.key_dir, context=context, signing=True,
                           session=OwnerSession('other', False, ()))
        other.sign_approval(wrong)

    def test_session_bound_verify_approval_and_admit_only_bind_existing_inputs(self):
        _, context = self.create()
        signer = self.signer(context)
        archive = json.loads((FIXTURES / 'positive.json').read_text())
        proposal = deepcopy(next(r for r in archive['records'] if r['id'] == 'proposal-1'))
        intent = deepcopy(next(r for r in archive['records'] if r['id'] == 'intent-1'))
        for r in (proposal, intent):
            r['world_id'] = self.spec.world_id
            r['body']['principal'] = 'owner'
        unsigned = self.unsigned()
        unsigned['refs'] = {'proposal': digest(proposal), 'intent': digest(intent)}
        approval = signer.sign_approval(unsigned)
        signer.verify_approval(approval, proposal, intent)
        command = {'domain': 'edgeworld.universe.authority', 'version': '0.2', 'world_id': self.spec.world_id,
                   'kind': 'command', 'id': 'command-one', 'body': {},
                   'refs': {'proposal': digest(proposal), 'intent': digest(intent), 'approval': digest(approval)}}
        candidate = deepcopy(next(r for r in archive['records'] if r['id'] == 'candidate-1'))
        candidate['world_id'] = self.spec.world_id; candidate['refs']['command'] = digest(command)
        admission = signer.admit(command, candidate, current_revision=0, admission_id='new-admission')
        self.assertEqual('owner', admission['body']['principal'])
        self.assertEqual({'command': digest(command), 'candidate': digest(candidate)}, admission['refs'])
        open_trust(self.key_dir, context=context)(admission)
        limited = open_trust(self.key_dir, context=context, signing=True,
                             session=OwnerSession('owner', False, ('physics_step',)))
        self.assert_code('AUTHORIZATION', limited.admit, command, candidate, current_revision=0, admission_id='new-admission')
        self.assert_code('AUTHORIZATION', limited.verify_approval, approval, proposal, intent)
        self.assert_code('INTEGER', signer.admit, command, candidate, current_revision=False, admission_id='x')

    def test_changed_context_root_aliases_and_key_inside_authority_are_rejected(self):
        _, context = self.create()
        verifier = open_trust(self.key_dir, context=context)
        self.assert_code('ROOT_MISMATCH', verifier.assert_context, replace(context, authority_root=str(self.base / 'other')))
        for change in ({'world_id': 'other'}, {'expected_build': 'c' * 64}, {'expected_options': 'c' * 64},
                       {'artifact_class': 'synthetic-contract-only'}, {'trust_anchor': 'c' * 64}):
            self.assert_code('AUTHORIZATION', verifier.assert_context, replace(context, **change))
        alias = self.base / 'alias'; alias.symlink_to(self.key_dir, target_is_directory=True)
        self.assert_code('AUTHORIZATION', open_trust, alias, context=context)
        world = self.base / 'world'; world.mkdir()
        nested = world / 'key'
        self.assert_code('NOT_READY', provision, nested, spec=self.spec)
        self.assertFalse(nested.exists())
        root_alias = self.base / 'world-alias'; root_alias.symlink_to(world, target_is_directory=True)
        self.assert_code('ROOT_MISMATCH', open_trust, self.key_dir, context=replace(context, authority_root=str(root_alias)))

    def test_unsafe_file_types_permissions_links_and_sizes_are_rejected(self):
        _, context = self.create()
        key = self.key_dir / 'authority.key'; original = key.read_bytes()
        key.chmod(0o644)
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context)
        key.chmod(0o600)
        self.key_dir.chmod(0o755)
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context)
        self.key_dir.chmod(0o700)
        for payload in (b'', b'a' * 31, b'a' * 33, bytes(range(32))):
            key.write_bytes(payload)
            self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context)
        key.write_bytes(original)
        link = self.base / 'hardlink'; os.link(key, link)
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context)
        link.unlink()
        key.unlink(); key.symlink_to(self.base / 'absent')
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context)
        key.unlink(); key.mkdir()
        self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=context)

    def test_public_key_is_rejected_even_with_correct_anchor_other_world_and_root(self):
        self.key_dir.mkdir(mode=0o700)
        key = self.key_dir / 'authority.key'; key.write_bytes(bytes(range(32))); key.chmod(0o600)
        for world in ('trust-world', 'another-world'):
            root = str(self.base / world)
            anchor = hashlib.sha256(b'edgeworld.universe.trust-anchor\0v0.2\0' + world.encode()
                                    + b'\0' + root.encode() + b'\0' + bytes(range(32))).hexdigest()
            for artifact in ('genesis-runtime', 'synthetic-contract-only'):
                ctx = DeploymentContext(world, root, anchor, 'a' * 64, 'b' * 64, artifact)
                self.assert_code('AUTHORIZATION', open_trust, self.key_dir, context=ctx)

    def test_partial_provisioning_is_retained_and_cannot_be_overwritten(self):
        with patch('engine.universe_authority.trust.os.fsync', side_effect=OSError('forced sync failure')):
            self.assert_code('NOT_READY', provision, self.key_dir, spec=self.spec)
        key = self.key_dir / 'authority.key'
        self.assertTrue(key.exists())
        retained = key.read_bytes()
        self.assertEqual(32, len(retained))
        self.assert_code('NOT_READY', provision, self.key_dir, spec=self.spec)
        self.assertEqual(retained, key.read_bytes())

    def test_receipt_shape_is_checked_but_policy_is_not_inferred_from_a_mac(self):
        _, context = self.create(); signer = self.signer(context)
        unsigned = self.unsigned()
        # Expiry/head/budget are intentionally not resolved by the signer.
        unsigned['body']['expires_revision'] = 900
        signer.sign_approval(unsigned)
        for field, value, code in (('expires_revision', True, 'INTEGER'), ('receipt_id', '', 'ID')):
            malformed = deepcopy(unsigned); malformed['body'][field] = value
            self.assert_code(code, signer.sign_approval, malformed)
        malformed = deepcopy(unsigned); malformed['body']['auth_tag'] = '0' * 64
        self.assert_code('SCHEMA', signer.sign_approval, malformed)
        malformed = deepcopy(unsigned); malformed['world_id'] = 'other-world'
        self.assert_code('WORLD', signer.sign_approval, malformed)
