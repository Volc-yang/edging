"""E1 production API checks against fixed independently reviewed v0.2 inputs."""
from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
import hashlib
import hmac
import json
from pathlib import Path
import tempfile
import unittest

from engine.universe_authority.codec import (
    ContractError, DeploymentContext, HeadBinding, canonical, decode, decode_archive, digest,
)
from engine.universe_authority.records import (
    BlobMeta, VerifiedObservation, select, validate_archive, validate_closure,
    validate_record, verify_observation,
)
from engine.universe_authority.trust import open_trust

FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_2'


def packed(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':')).encode()


class InjectedSyntheticVerifier:
    """Public fixture key in tests only, not a production trust fallback."""
    def __init__(self, context):
        self.context = context

    def assert_context(self, context):
        if context.authority_root != self.context.authority_root:
            raise ContractError('ROOT_MISMATCH')
        if (context.world_id != self.context.world_id or context.trust_anchor != self.context.trust_anchor
                or context.trust_algorithm != self.context.trust_algorithm
                or context.artifact_class != 'synthetic-contract-only'):
            raise ContractError('AUTHORIZATION')

    def __call__(self, receipt):
        validate_record(receipt)
        unsigned = deepcopy(receipt)
        tag = unsigned['body'].pop('auth_tag')
        message = (b'edgeworld.universe.receipt\0v0.2\0' + self.context.trust_anchor.encode()
                   + b'\0' + receipt['kind'].encode() + b'\0' + packed(unsigned))
        if not hmac.compare_digest(hmac.new(bytes(range(32)), message, hashlib.sha256).hexdigest(), tag):
            raise ContractError('AUTHORIZATION')


class UniverseCompositeRecordsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = json.loads((FIXTURES / 'positive.json').read_text())
        cls.goldens = json.loads((FIXTURES / 'golden.json').read_text())
        cls.negatives = json.loads((FIXTURES / 'negative.json').read_text())
        cls.proofs = json.loads((FIXTURES / 'proof_vectors.json').read_text())
        cls.context = DeploymentContext(**json.loads((FIXTURES / 'trust_context.json').read_text()))
        cls.blobs = {k: bytes.fromhex(v) for k, v in json.loads((FIXTURES / 'synthetic_blobs.json').read_text())['blobs'].items()}
        cls.verifier = InjectedSyntheticVerifier(cls.context)

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaises(ContractError) as caught:
            function(*args, **kwargs)
        self.assertEqual(code, caught.exception.code)

    def full(self, archive=None, context=None, blobs=None, **extra):
        ctx = self.context if context is None else context
        return validate_archive(self.archive if archive is None else archive, world_id=ctx.world_id,
                                domain_version='0.2', context=ctx, trust_verifier=self.verifier,
                                blobs=self.blobs if blobs is None else blobs, **extra)

    def observe(self, case, context=None):
        kwargs = dict(case['expected'])
        kwargs['trusted_head'] = HeadBinding(**kwargs['trusted_head'])
        return verify_observation(case['raw'].encode(), context=self.context if context is None else context, **kwargs)

    def test_all_67_literal_goldens_and_explicit_profile(self):
        archive = decode_archive((FIXTURES / 'positive.json').read_bytes(), domain_version='0.2')
        self.assertEqual(67, len(self.goldens))
        for record, golden in zip(archive['records'], self.goldens):
            with self.subTest(record=record['id']):
                validate_record(record)
                self.assertEqual(bytes.fromhex(golden['canonical_hex']), canonical(record))
                self.assertEqual(golden['sha256'], digest(record))
        closure = self.full(archive)
        self.assertEqual('0.2', closure.domain_version)
        self.assertEqual('composite-rigid-support.v0.2', closure.profile)
        self.assertEqual(self.context, closure.context)
        self.assertEqual(4, len(closure.retained))
        self.assertEqual(3, len(closure.commands))
        self.assertEqual(2, len(closure.binary_refs))
        self.assertEqual(82, sum(x.byte_count for x in closure.binary_refs.values()))
        for meta in closure.binary_refs.values():
            self.assertIs(type(meta), BlobMeta)
            self.assertEqual('synthetic-contract-only', meta.artifact_class)
        for tick, revision in ((0, 0), (0, 1), (1, 2), (1, 3)):
            self.assertEqual(revision, select(closure, tick=tick, revision=revision, watermark=revision)['body']['revision'])

    def test_all_five_proofs_yield_renderer_ready_defensive_dto(self):
        self.assertEqual(5, len(self.proofs))
        for case in self.proofs:
            with self.subTest(case=case['name']):
                result = self.observe(case)
                self.assertIs(type(result), VerifiedObservation)
                self.assertEqual(case['selected_manifest'], result.manifest)
                self.assertEqual(len(case['raw'].encode()), result.bytes)
                selected = result.selected_records[result.manifest]
                state = result.selected_records[selected['refs']['state']]
                world = result.selected_records[state['refs']['world']]
                projection = result.selected_records[world['refs']['projection']]
                sample = result.selected_records[result.selected_records[state['refs']['snapshot']]['refs']['sample']]
                self.assertEqual('unit_transform', result.selected_records[projection['refs']['transform']]['kind'])
                self.assertEqual('physics_sample', sample['kind'])
                result.state['body'].clear()
                result.selected_records[result.manifest]['refs'].clear()
                self.assertIn('tick', result.state['body'])
                self.assertIn('state', result.selected_records[result.manifest]['refs'])
                with self.assertRaises(TypeError):
                    result.selected_records['bad'] = {}
                with self.assertRaises(FrozenInstanceError):
                    result.bytes = 0

    def test_all_57_fixed_rejections_use_production_entry_points(self):
        self.assertEqual(57, len(self.negatives))
        for case in self.negatives:
            with self.subTest(case=case['name']):
                # Typed production context rejects an unknown algorithm before
                # the JSON-only oracle's later AUTHORIZATION comparison.
                expected = ('PROFILE' if case.get('context', {}).get('trust_algorithm', self.context.trust_algorithm)
                            != self.context.trust_algorithm else case['error'])
                with self.assertRaises(ContractError) as caught:
                    ctx = self.context if 'context' not in case else DeploymentContext(**case['context'])
                    operation = case['operation']
                    if operation == 'archive':
                        self.full(decode_archive(case['raw'].encode(), domain_version='0.2'), context=ctx)
                    elif operation == 'proof':
                        self.observe(case, ctx)
                    elif operation == 'blob':
                        supplied = dict(self.blobs)
                        if case['bytes_hex'] is None:
                            supplied.pop(case['sha256'])
                        else:
                            supplied[case['sha256']] = bytes.fromhex(case['bytes_hex'])
                        self.full(blobs=supplied)
                    elif operation == 'runtime_key':
                        with tempfile.TemporaryDirectory() as directory:
                            key_dir = Path(directory).resolve() / 'key'
                            key_dir.mkdir(mode=0o700)
                            key = key_dir / 'authority.key'
                            key.write_bytes(bytes.fromhex(case['key_hex']))
                            key.chmod(0o600)
                            open_trust(key_dir, context=replace(ctx, artifact_class='genesis-runtime'))
                    else:
                        decode(case['raw'].encode())
                self.assertEqual(expected, caught.exception.code)

    def test_complete_raw_and_external_context_are_mandatory(self):
        for blobs in ({}, {next(iter(self.blobs)): b'x'}):
            self.assert_code('CORRUPT', self.full, blobs=blobs)
        self.assert_code('AUTHORIZATION', validate_closure, self.archive['records'], self.archive['head'],
                         world_id=self.context.world_id, domain_version='0.2', context=self.context, blobs=self.blobs)
        self.assert_code('WORLD', validate_closure, self.archive['records'], self.archive['head'],
                         world_id='other-world', domain_version='0.2', context=self.context,
                         trust_verifier=self.verifier, blobs=self.blobs)
        self.assert_code('AUTHORIZATION', self.full, trusted_receipts={})
        self.assert_code('CORRUPT', validate_archive, self.archive, world_id=self.context.world_id,
                         domain_version='0.2', context=self.context, trust_verifier=self.verifier)

    def test_defensive_closure_and_only_retained_results_are_committed(self):
        a = deepcopy(self.archive)
        closure = self.full(a)
        closure.records[closure.head]['body'].clear()
        a['records'].clear()
        self.assertIn('tick', closure.records[closure.head]['body'])
        with self.assertRaises(TypeError):
            closure.binary_refs['x'] = None
        with self.assertRaises(FrozenInstanceError):
            next(iter(closure.binary_refs.values())).byte_count = 0
        old = deepcopy(self.archive)
        old['head'] = closure.retained[-1]
        self.assertEqual({}, dict(self.full(old).commands))
        self.assertEqual(1, len(self.full(old).binary_refs))
        self.assertEqual(67, len(self.full(old).records))

    def test_mixed_version_and_archive_packaging_do_not_relax_record_arrays(self):
        self.assert_code('DOMAIN', validate_closure, self.archive['records'], self.archive['head'],
                         world_id=self.context.world_id, trusted_receipts={})
        large = deepcopy(self.archive)
        proposal = next(r for r in large['records'] if r['kind'] == 'proposal')
        for i in range(250):
            new = deepcopy(proposal); new['id'] = 'extra-' + str(i)
            large['records'].append(new)
        value = decode_archive(packed(large), domain_version='0.2')
        self.assertEqual(317, len(self.full(value).records))
        bad = deepcopy(proposal); bad['body']['output'] = [None] * 257
        large['records'].append(bad)
        self.assert_code('LIMIT', decode_archive, packed(large), domain_version='0.2')
        self.assert_code('NUMBER', self.full, dict(self.archive, records=[dict(proposal, body={'principal': 'x', 'output': 1.0})]))

    def test_wire_lf_raw_bytes_and_context_binding_are_exact(self):
        case = self.proofs[2]
        size = 1048576
        raw = case['raw'].encode()
        padded = raw + b' ' * (size - len(raw))
        kwargs = dict(case['expected']); kwargs['trusted_head'] = HeadBinding(**kwargs['trusted_head'])
        result = verify_observation(padded + b'\n', context=self.context, **kwargs)
        self.assertEqual(size, result.bytes)
        for suffix in (b' \n', b'\r\n', b'\n\n'):
            self.assert_code('LIMIT' if len(padded + suffix) > size + 1 else 'JSON',
                             verify_observation, padded + suffix, context=self.context, **kwargs)
        self.assert_code('JSON', verify_observation, raw + b'\r\n', context=self.context, **kwargs)
        self.assert_code('AUTHORIZATION', verify_observation, raw, context=self.context,
                         **dict(kwargs, trusted_head=kwargs['trusted_head'].head))

    def test_bare_float_and_malformed_public_inputs_fail_closed(self):
        for value in (None, {}, [], True):
            self.assert_code('SCHEMA', validate_record, value)
        self.assert_code('DOMAIN', decode_archive, b'{}', domain_version='9')
        self.assert_code('SCHEMA', decode_archive, b'{}', domain_version='0.2')
