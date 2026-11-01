"""E7 signed-zero support mass, fixed identity and rehashed synthetic closures.

Derived inputs are test-only. Frozen positive vectors remain byte-for-byte intact;
none of these fixtures supply an expected runtime Genesis mass.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

from engine.universe_authority.codec import ContractError, DeploymentContext, HeadBinding, digest
from engine.universe_authority.records import validate_archive, validate_record, verify_observation
from test_universe_composite_records import InjectedSyntheticVerifier

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'doc/fixtures/universe_authority_v0_2'
_spec = importlib.util.spec_from_file_location('e7_independent_oracle', ROOT / 'scripts/validate_universe_authority_v0_2_fixtures.py')
oracle = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oracle)


def packed(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':')).encode()


class UniverseSupportMassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = json.loads((FIXTURES / 'positive.json').read_text())
        cls.context_json = json.loads((FIXTURES / 'trust_context.json').read_text())
        cls.context = DeploymentContext(**cls.context_json)
        cls.verifier = InjectedSyntheticVerifier(cls.context)
        cls.blobs = {k: bytes.fromhex(v) for k, v in json.loads((FIXTURES / 'synthetic_blobs.json').read_text())['blobs'].items()}
        cls.checker = oracle.Oracle(json.loads((FIXTURES / 'schema.json').read_text()),
                                   oracle.FixtureVerifier(bytes(range(32)), cls.context_json))
        cls.proof_template = json.loads((FIXTURES / 'proof_vectors.json').read_text())[0]
        cls.sample = next(r for r in cls.archive['records'] if r['id'] == 'sample-0')

    def check_record(self, record, error=None):
        for validate, exception in ((validate_record, ContractError), (self.checker.record, oracle.Invalid)):
            if error is None:
                validate(record)
            else:
                with self.assertRaises(exception) as caught:
                    validate(record)
                self.assertEqual(error, caught.exception.code)

    def with_mass(self, index, value):
        record = deepcopy(self.sample)
        record['body']['bodies'][index]['mass_kg'] = deepcopy(value)
        return record

    def initial(self, mutate):
        """Rehash every edge, retaining only genesis' complete reachable closure.

        Genesis has no approval/admission so no signature is forged/re-signed.
        Digest computation here uses the independent encoder and is cross-checked
        against production for every rebuilt record.
        """
        a = deepcopy(self.archive)
        records, changed = [], {}
        for original in a['records']:
            record = deepcopy(original)
            old_digest = oracle.digest(original)
            mutate(record)
            record['refs'] = {key: changed[ref] for key, ref in original['refs'].items()}
            new_digest = oracle.digest(record)
            self.assertEqual(new_digest, digest(record))
            changed[old_digest] = new_digest
            records.append(record)
            if record['id'] == 'manifest-0':
                break
        a['records'], a['head'] = records, new_digest
        return a

    def proof(self, archive):
        records = {r['id']: r for r in archive['records']}
        raw = json.loads(self.proof_template['raw'])
        p = raw['result']['payload']
        p.update(head=archive['head'], manifest=records['manifest-0'], state=records['state-0'],
                 event=None, membership=[records['manifest-0']], opaque_refs=[],
                 records=[r for r in archive['records'] if r['kind'] not in ('manifest', 'state')])
        expected = deepcopy(self.proof_template['expected'])
        expected['trusted_head']['head'] = archive['head']
        return packed(raw), expected

    def check_closed(self, archive, error=None):
        def production():
            return validate_archive(archive, world_id=self.context.world_id, domain_version='0.2',
                                    context=self.context, trust_verifier=self.verifier, blobs=self.blobs)
        for validate, exception in ((production, ContractError),
                                   (lambda: self.checker.archive(archive, self.context_json, self.blobs), oracle.Invalid)):
            if error is None:
                validate()
            else:
                with self.assertRaises(exception) as caught:
                    validate()
                self.assertEqual(error, caught.exception.code)
        raw, expected = self.proof(archive)
        typed = dict(expected, trusted_head=HeadBinding(**expected['trusted_head']))
        for validate, exception in ((lambda: verify_observation(raw, context=self.context, **typed), ContractError),
                                   (lambda: self.checker.proof(raw, self.context_json, **expected), oracle.Invalid)):
            if error is None:
                validate()
            else:
                with self.assertRaises(exception) as caught:
                    validate()
                self.assertEqual(error, caught.exception.code)

    def test_positive_masses_and_support_signed_zero_preserve_bits(self):
        for index in (0, 1):
            for bits in ('0000000000000001', '3ff0000000000000', '7fefffffffffffff'):
                with self.subTest(index=index, bits=bits):
                    self.check_record(self.with_mass(index, {'$f64': bits}))
        for bits in ('0000000000000000', '8000000000000000'):
            record = self.with_mass(1, {'$f64': bits})
            self.check_record(record)
            self.assertIn(bits.encode(), oracle.canonical(record))
            self.assertEqual(bits, record['body']['bodies'][1]['mass_kg']['$f64'])
        self.assertNotEqual(digest(self.with_mass(1, {'$f64': '0000000000000000'})),
                            digest(self.with_mass(1, {'$f64': '8000000000000000'})))

    def test_dynamic_rejects_both_zero_signs(self):
        for bits in ('0000000000000000', '8000000000000000'):
            with self.subTest(bits=bits):
                self.check_record(self.with_mass(0, {'$f64': bits}), 'PHYSICS_INVALID')

    def test_both_bodies_reject_negative_including_subnormal(self):
        for index in (0, 1):
            for bits in ('8000000000000001', 'bff0000000000000', 'ffefffffffffffff'):
                with self.subTest(index=index, bits=bits):
                    self.check_record(self.with_mass(index, {'$f64': bits}), 'PHYSICS_INVALID')

    def test_both_bodies_reject_nonfinite_and_invalid_f64(self):
        for index in (0, 1):
            for bits in ('7ff0000000000000', 'fff0000000000000', '7ff8000000000001', '7ff0000000000001'):
                with self.subTest(index=index, bits=bits):
                    self.check_record(self.with_mass(index, {'$f64': bits}), 'F64')
            for value in (None, True, 0, '0', {}, {'$f64': '0'}, {'$f64': '3FF0000000000000'},
                          {'$f64': '0000000000000000', 'fixed': True}):
                with self.subTest(index=index, value=value):
                    self.check_record(self.with_mass(index, value), 'F64')

    def test_body_identity_membership_order_and_fields_remain_closed(self):
        record = self.with_mass(1, {'$f64': '0000000000000000'})
        for index in (0, 1):
            bad = deepcopy(record); bad['body']['bodies'][index]['physical_id'] = 'body-unknown'
            self.check_record(bad, 'PHYSICS_INVALID')
        bad = deepcopy(record); bad['body']['bodies'][0]['physical_id'] = 'body-support'
        self.check_record(bad, 'ID')
        bad = deepcopy(record); bad['body']['bodies'].reverse()
        self.check_record(bad, 'PHYSICS_INVALID')
        bad = deepcopy(record); bad['body']['bodies'].pop()
        self.check_record(bad, 'PHYSICS_INVALID')
        bad = deepcopy(record); bad['body']['bodies'].append(deepcopy(bad['body']['bodies'][1]))
        self.check_record(bad, 'LIMIT')
        bad = deepcopy(record); bad['body']['bodies'][0]['fixed'] = True
        self.check_record(bad, 'SCHEMA')

    def test_support_signed_zero_full_closure_and_readonly_proof(self):
        for bits in ('0000000000000000', '8000000000000000'):
            with self.subTest(bits=bits):
                def mutate(r):
                    if r['kind'] == 'physics_sample':
                        r['body']['bodies'][1]['mass_kg'] = {'$f64': bits}
                archive = self.initial(mutate)
                before = packed(archive)
                self.check_closed(archive)
                self.assertEqual(before, packed(archive))
                sample = next(r for r in archive['records'] if r['kind'] == 'physics_sample')
                self.assertEqual(bits, sample['body']['bodies'][1]['mass_kg']['$f64'])

    def test_rehashed_negative_and_dynamic_zero_cannot_hide_behind_valid_edges(self):
        for index, bits in ((0, '0000000000000000'), (0, '8000000000000000'),
                            (1, 'bff0000000000000'), (1, '8000000000000001')):
            with self.subTest(index=index, bits=bits):
                def mutate(r):
                    if r['kind'] == 'physics_sample':
                        r['body']['bodies'][index]['mass_kg'] = {'$f64': bits}
                self.check_closed(self.initial(mutate), 'PHYSICS_INVALID')

    def test_rehashed_binding_cannot_reassign_fixed_identity(self):
        for key, value in (('role', 'dynamic'), ('config_entity_index', 0),
                           ('genesis_name', 'i7-dynamic'), ('existence_id', 'existence-dynamic')):
            with self.subTest(key=key):
                def mutate(r):
                    if r['kind'] == 'physics_sample':
                        r['body']['bodies'][1]['mass_kg'] = {'$f64': '0000000000000000'}
                    elif r['kind'] == 'physics_binding':
                        r['body']['bindings'][1][key] = value
                self.check_closed(self.initial(mutate), 'PHYSICS_INVALID')

    def test_config_fixed_flag_remains_frozen(self):
        r = deepcopy(next(r for r in self.archive['records'] if r['kind'] == 'physics_config'))
        r['body']['config']['entities'][0]['fixed'] = True
        self.check_record(r, 'PROFILE')
        r = deepcopy(next(r for r in self.archive['records'] if r['kind'] == 'physics_config'))
        r['body']['config']['entities'][1]['fixed'] = False
        self.check_record(r, 'PROFILE')


if __name__ == '__main__':
    unittest.main()
