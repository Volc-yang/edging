"""I7 static input/source/arithmetic check; never imports Genesis or runs a solver.

Reads fixed expected vectors. It has no rewrite/update-golden option.
"""
from pathlib import Path
import argparse
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import json
import math
import struct


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate key')
        result[key] = value
    return result


def load(path):
    return json.loads(path.read_text(), object_pairs_hook=unique,
                      parse_float=lambda _: (_ for _ in ()).throw(ValueError('bare float')),
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite')))


def scalar(value):
    assert type(value) is dict and set(value) == {'$f64'}
    bits = value['$f64']
    assert type(bits) is str and len(bits) == 16 and set(bits) <= set('0123456789abcdef')
    number = struct.unpack('>d', bytes.fromhex(bits))[0]
    assert math.isfinite(number)
    return number


def half_even_rational(value):
    sign = -1 if value < 0 else 1
    value = abs(value)
    quotient, remainder = divmod(value.numerator, value.denominator)
    doubled = 2 * remainder
    if doubled > value.denominator or doubled == value.denominator and quotient % 2:
        quotient += 1
    return sign * quotient


def influence(previous, current):
    with localcontext() as context:
        context.prec = 2000
        context.rounding = ROUND_HALF_EVEN
        return int(((Decimal.from_float(current) - Decimal.from_float(previous)) * 1000)
                   .to_integral_value(rounding=ROUND_HALF_EVEN))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--installed-source', action='store_true')
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    files = sorted(here.glob('*.json'))
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    config = load(here / 'config.json')
    schema = load(here / 'schema_proposal.json')
    vectors = load(here / 'static_vectors.json')
    record = load(here / 'record_template.json')
    golden = load(here / 'golden_static.json')
    assert schema['status'] == 'proposed-G-C0.2-reopen-required'
    assert record['body'] == config and record['version'] == '0.2'
    assert config['authority_version'] == '0.2' and config['solver_precision'] == '32'
    assert len(config['entities']) == 2
    dynamic, support = config['entities']
    assert (dynamic['fixed'], support['fixed']) == (False, True)
    assert dynamic['morph'] == 'sphere' and support['morph'] == 'box'
    assert len({e['physical_id'] for e in config['entities']}) == 2
    assert len({e['genesis_name'] for e in config['entities']}) == 2
    assert scalar(config['dt_s']) == .01 and config['steps_per_advance'] == 8
    assert config['horizon_advances'] == 32 and config['substeps'] == 1
    top = scalar(support['position_m'][2]) + scalar(support['size_m'][2]) / 2
    assert top == 0 and scalar(dynamic['position_m'][2]) - scalar(dynamic['radius_m']) > top
    assert scalar(config['material']['rho_kg_m3']) == 1000
    assert scalar(config['cases'][1]['gravity_m_s2'][2]) < scalar(config['cases'][0]['gravity_m_s2'][2]) < 0
    assert schema['limits']['raw_payload_bytes_each'] * schema['limits']['retained_roots'] == schema['limits']['raw_payload_bytes_total']
    for case in vectors['rounding_vectors']:
        previous, current = scalar(case['z_previous']), scalar(case['z_new'])
        rational = (Fraction.from_float(current) - Fraction.from_float(previous)) * 1000
        assert influence(previous, current) == half_even_rational(rational) == case['expected_mm']
    for case in vectors['scaled_half_even_vectors']:
        assert half_even_rational(Fraction(case['scaled_decimal'])) == case['expected']
    canonical = json.dumps(record, ensure_ascii=True, sort_keys=True,
                           separators=(',', ':'), allow_nan=False).encode('ascii')
    prefix = b'edgeworld.universe.authority\x00v0.2\x00'
    assert schema['record_prefix_hex'] == prefix.hex()
    assert canonical.hex() == golden['canonical_hex']
    assert hashlib.sha256(prefix + canonical).hexdigest() == golden['record_sha256']
    checked_sources = 0
    if args.installed_source:
        audit = load(here / 'source_audit.json')
        root = Path(audit['package_root'])
        metadata = root.parent / 'genesis_world-1.4.3.dist-info/METADATA'
        assert hashlib.sha256(metadata.read_bytes()).hexdigest() == audit['version_metadata_sha256']
        for entry in audit['sources']:
            data = (root / entry['path']).read_bytes()
            assert len(data) == entry['bytes']
            assert hashlib.sha256(data).hexdigest() == entry['sha256']
            checked_sources += 1
    assert before == {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    print(json.dumps({'status': 'PASS_STATIC_ONLY', 'participants': 2,
                      'rounding_vectors': len(vectors['rounding_vectors']),
                      'scaled_vectors': len(vectors['scaled_half_even_vectors']),
                      'source_files': checked_sources, 'fixture_json_unchanged': True,
                      'genesis_imported': False, 'runtime_physics': 'not_run',
                      'g_c_0_2': 'proposed_not_accepted'}))


if __name__ == '__main__':
    main()
