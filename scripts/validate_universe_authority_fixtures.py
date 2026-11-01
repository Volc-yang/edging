#!/usr/bin/env python3
"""Read-only contract oracle. Never creates or rewrites fixture expectations."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

DOMAIN = 'edgeworld.universe.authority'
VERSION = '0.1'
MAX_INT = 9007199254740991
MAX_BYTES = 1048576
MAX_DEPTH = 32
PREFIX = b'edgeworld.universe.authority\x00v0.1\x00'
KINDS = {
    'proposal': ({'principal', 'output'}, {}),
    'intent': ({'command_id', 'principal', 'expected_revision', 'tick_delta', 'transfer', 'budget', 'random_cursor'}, {}),
    'approval': ({'principal', 'receipt_id', 'expires_revision'}, {'proposal': 'proposal', 'intent': 'intent'}),
    'command': (set(), {'proposal': 'proposal', 'intent': 'intent', 'approval': 'approval'}),
    'candidate': ({'adapter_kind', 'test_profile', 'value', 'tick', 'revision'}, {'command': 'command', 'prior_state': 'state'}),
    'admission': ({'receipt_id', 'principal', 'evaluated_revision'}, {'command': 'command', 'candidate': 'candidate'}),
    'state': ({'tick', 'revision', 'value', 'budget', 'random_cursor'}, {}),
    'event': ({'event_id'}, {'state': 'state', 'admission': 'admission', 'prior_event': 'event'}),
    'result': ({'command_id', 'tick', 'revision', 'watermark'}, {'command': 'command', 'state': 'state', 'event': 'event', 'checkpoint': 'candidate'}),
    'index': ({'command_id', 'fingerprint'}, {'result': 'result'}),
    'manifest': ({'tick', 'revision', 'watermark'}, {'state': 'state', 'event': 'event', 'index': 'index', 'prior_manifest': 'manifest'}),
}
class Invalid(ValueError):
    def __init__(self, code):
        self.code = code
        super().__init__(code)

def fail(code):
    raise Invalid(code)

def pairs(items):
    out = {}
    for key, value in items:
        if key in out:
            fail('DUPLICATE_KEY')
        out[key] = value
    return out

def tree(value, depth=0):
    if depth > MAX_DEPTH:
        fail('LIMIT')
    if value is None or type(value) is bool:
        return
    if type(value) is int:
        if abs(value) > MAX_INT:
            fail('INTEGER')
        return
    if type(value) is str:
        if len(value.encode('utf-8', errors='strict')) > 4096:
            fail('LIMIT')
        if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
            fail('UNICODE')
        return
    if type(value) is list:
        if len(value) > 256:
            fail('LIMIT')
        for item in value:
            tree(item, depth + 1)
        return
    if type(value) is dict:
        if len(value) > 64:
            fail('LIMIT')
        for key, item in value.items():
            tree(key, depth + 1)
            tree(item, depth + 1)
        if '$f64' in value:
            if set(value) != {'$f64'} or type(value['$f64']) is not str or not re.fullmatch('[0-9a-f]{16}', value['$f64']):
                fail('F64')
            number = struct.unpack('>d', bytes.fromhex(value['$f64']))[0]
            if not math.isfinite(number):
                fail('F64')
        return
    fail('NUMBER')

def decode(raw):
    if len(raw) > MAX_BYTES:
        fail('LIMIT')
    try:
        text = raw.decode('utf-8', errors='strict')
        if text.startswith('\ufeff'):
            fail('UNICODE')
        value = json.loads(text, object_pairs_hook=pairs,
                           parse_float=lambda _: fail('NUMBER'),
                           parse_constant=lambda _: fail('NUMBER'))
        tree(value)
        return value
    except (UnicodeError, RecursionError):
        fail('UNICODE')
    except json.JSONDecodeError:
        fail('JSON')

def canonical(value):
    tree(value)
    # ASCII escaping is deliberately frozen; no Unicode normalization.
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')

def digest(record):
    return hashlib.sha256(PREFIX + canonical(record)).hexdigest()

def integer(value):
    if type(value) is not int or not 0 <= value <= MAX_INT:
        fail('INTEGER')

def identity(value):
    if type(value) is not str or not re.fullmatch('[a-z][a-z0-9._-]{0,63}', value):
        fail('ID')

def exact(obj, keys):
    if type(obj) is not dict or set(obj) != set(keys):
        fail('SCHEMA')

def validate_record(record):
    exact(record, {'domain', 'version', 'world_id', 'kind', 'id', 'body', 'refs'})
    if record['domain'] != DOMAIN or record['version'] != VERSION:
        fail('DOMAIN')
    identity(record['world_id']); identity(record['id'])
    kind = record['kind']
    if type(kind) is not str or kind not in KINDS:
        fail('SCHEMA')
    fields, refs = KINDS[kind]
    exact(record['body'], fields)
    allowed_refs = set(refs)
    # Genesis records have no backward edges. Later states still have no
    # current event/manifest edges; their candidate is reached from the event.
    if kind in ('event', 'manifest'):
        allowed_refs.discard('prior_event' if kind == 'event' else 'prior_manifest')
    if kind == 'manifest' and record['body'].get('revision') == 0:
        allowed_refs = {'state'}
        refs = {'state': 'state'}
    if type(record['refs']) is not dict or not allowed_refs <= set(record['refs']) <= set(refs):
        fail('REFERENCE')
    for value in record['refs'].values():
        if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
            fail('REFERENCE')
    b = record['body']
    for key in ('tick', 'revision', 'watermark', 'expected_revision', 'tick_delta', 'budget', 'random_cursor', 'expires_revision', 'evaluated_revision'):
        if key in b:
            integer(b[key])
    if 'tick_delta' in b and b['tick_delta'] not in (0, 1):
        fail('INTEGER')
    for key in ('principal', 'command_id', 'receipt_id', 'event_id'):
        if key in b:
            identity(b[key])
    for key in ('value', 'transfer'):
        if key in b and (type(b[key]) is not dict or set(b[key]) != {'$f64'}):
            fail('F64')
    if kind == 'proposal' and (type(b['output']) is not str or len(b['output']) > 1024):
        fail('SCHEMA')
    if kind == 'candidate' and (b['adapter_kind'], b['test_profile']) != ('fake', 'neutral-transfer-v0.1'):
        fail('PROFILE')
    if kind == 'index' and (type(b['fingerprint']) is not str or not re.fullmatch('[0-9a-f]{64}', b['fingerprint'])):
        fail('REFERENCE')

def validate_archive(value, trusted_receipts):
    tree(value)
    exact(value, {'domain', 'version', 'test_profile', 'records', 'head'})
    if value['domain'] != DOMAIN or value['version'] != VERSION:
        fail('DOMAIN')
    if value['test_profile'] != 'neutral-transfer-v0.1':
        fail('PROFILE')
    if type(value['records']) is not list or not 1 <= len(value['records']) <= 256:
        fail('LIMIT')
    if type(trusted_receipts) is not dict:
        fail('SCHEMA')
    records = {}; identities = set(); world = None
    for record in value['records']:
        validate_record(record)
        if world is None:
            world = record['world_id']
        if world != record['world_id']:
            fail('WORLD')
        key = (record['kind'], record['id'])
        if key in identities:
            fail('ID')
        identities.add(key)
        d = digest(record)
        for name, target in record['refs'].items():
            # Require prior entry: catches forward refs, forged refs and cycles.
            if target not in records or records[target]['kind'] != KINDS[record['kind']][1][name]:
                fail('REFERENCE')
        records[d] = record
    if type(value['head']) is not str or not re.fullmatch('[0-9a-f]{64}', value['head']):
        fail('REFERENCE')
    if value['head'] not in records or records[value['head']]['kind'] != 'manifest':
        fail('REFERENCE')
    commands = {}; retained = set()
    def referenced(record, name):
        return records[record['refs'][name]]
    for d, r in records.items():
        b = r['body']; k = r['kind']
        if k == 'approval':
            i = referenced(r, 'intent')['body']; p = referenced(r, 'proposal')['body']
            receipt = trusted_receipts.get(b['receipt_id'])
            expected = {'kind': 'approval', 'principal': b['principal'], 'intent': r['refs']['intent'], 'proposal': r['refs']['proposal'], 'expires_revision': b['expires_revision']}
            if receipt != expected or b['principal'] != i['principal'] or p['principal'] != i['principal']:
                fail('AUTHORIZATION')
        if k == 'command':
            a = referenced(r, 'approval'); i = referenced(r, 'intent')
            if a['refs'] != {'proposal': r['refs']['proposal'], 'intent': r['refs']['intent']}:
                fail('AUTHORIZATION')
            cid = i['body']['command_id']
            if (i['body']['principal'], cid) in commands and commands[(i['body']['principal'], cid)] != d:
                fail('COMMAND_CONFLICT')
            commands[(i['body']['principal'], cid)] = d
        if k == 'state' and b['revision'] == 0 and (b['tick'] != 0 or b['random_cursor'] != 0):
            fail('HEAD')
        if k == 'candidate':
            command = referenced(r, 'command'); intent = referenced(command, 'intent')['body']
            prior = referenced(r, 'prior_state')['body']
            if intent['expected_revision'] != prior['revision'] or b['revision'] != prior['revision'] + 1 or b['tick'] != prior['tick'] + intent['tick_delta']:
                fail('HEAD')
            number = lambda item: struct.unpack('>d', bytes.fromhex(item['$f64']))[0]
            expected_value = number(prior['value']) + number(intent['transfer'])
            if not math.isfinite(expected_value) or b['value']['$f64'] != struct.pack('>d', expected_value).hex():
                fail('TRANSITION')
        if k == 'admission':
            c = referenced(r, 'candidate'); command = referenced(r, 'command')
            i = referenced(command, 'intent')['body']; approval = referenced(command, 'approval')['body']
            expected = {'kind': 'admission', 'principal': b['principal'], 'command': r['refs']['command'], 'candidate': r['refs']['candidate'], 'evaluated_revision': b['evaluated_revision']}
            if c['refs']['command'] != r['refs']['command'] or trusted_receipts.get(b['receipt_id']) != expected or b['principal'] != i['principal'] or b['evaluated_revision'] != i['expected_revision'] or b['evaluated_revision'] > approval['expires_revision']:
                fail('AUTHORIZATION')
        if k == 'event':
            state = referenced(r, 'state')['body']; a = referenced(r, 'admission'); c = referenced(a, 'candidate'); cb = c['body']
            prior = referenced(c, 'prior_state')['body']; intent = referenced(referenced(a, 'command'), 'intent')['body']
            if any(state[x] != cb[x] for x in ('tick', 'revision', 'value')) or state['budget'] != prior['budget'] - intent['budget'] or state['random_cursor'] != intent['random_cursor'] + 1 or intent['random_cursor'] != prior['random_cursor']:
                fail('TRANSITION')
            if (state['revision'] == 1) != ('prior_event' not in r['refs']):
                fail('REFERENCE')
            if 'prior_event' in r['refs'] and referenced(r, 'prior_event')['refs']['state'] != c['refs']['prior_state']:
                fail('REFERENCE')
        if k == 'result':
            state = referenced(r, 'state')['body']; command = referenced(r, 'command'); event = referenced(r, 'event'); admission = referenced(event, 'admission')
            if b['command_id'] != referenced(command, 'intent')['body']['command_id'] or event['refs']['state'] != r['refs']['state'] or admission['refs']['command'] != r['refs']['command'] or admission['refs']['candidate'] != r['refs']['checkpoint']:
                fail('REFERENCE')
            if b['tick'] != state['tick'] or b['revision'] != state['revision'] or b['watermark'] != b['revision']:
                fail('WATERMARK')
        if k == 'index':
            result = referenced(r, 'result')
            if b['fingerprint'] != result['refs']['command'] or b['command_id'] != result['body']['command_id']:
                fail('COMMAND_CONFLICT')
        if k == 'manifest' and b['revision'] == 0:
            state = referenced(r, 'state')['body']
            if b != {'tick': 0, 'revision': 0, 'watermark': 0} or state['revision'] != 0:
                fail('HEAD')
            continue
        if k == 'manifest':
            state = referenced(r, 'state'); event = referenced(r, 'event'); result = referenced(referenced(r, 'index'), 'result')
            if event['refs']['state'] != r['refs']['state'] or result['refs']['state'] != r['refs']['state'] or result['refs']['event'] != r['refs']['event']:
                fail('REFERENCE')
            if b != {key: state['body'][key] for key in ('tick', 'revision')} | {'watermark': state['body']['revision']}:
                fail('WATERMARK')
            if 'prior_manifest' not in r['refs']:
                fail('REFERENCE')
            if 'prior_manifest' in r['refs']:
                prev = referenced(r, 'prior_manifest')
                candidate = referenced(result, 'checkpoint')
                if b['revision'] != prev['body']['revision'] + 1 or candidate['refs']['prior_state'] != prev['refs']['state'] or event['refs'].get('prior_event') != prev['refs'].get('event'):
                    fail('HEAD')
    # Only roots on the pinned head chain are historical observations.
    current = value['head']
    while current:
        if current in retained:
            fail('REFERENCE')
        retained.add(current)
        current = records[current]['refs'].get('prior_manifest')
    return records, retained

def observe(archive, tick, revision, watermark, *, trusted_receipts):
    for n in (tick, revision, watermark):
        integer(n)
    records, retained = validate_archive(archive, trusted_receipts)
    if watermark != revision:
        fail('WATERMARK')
    for d in retained:
        m = records[d]
        if m['body'] == {'tick': tick, 'revision': revision, 'watermark': watermark}:
            return d
    fail('NOT_FOUND')

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fixtures', type=Path, default=Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_1')
    args = parser.parse_args()
    # Fixture packaging is not a domain record: raw negative archive strings
    # may exceed domain's 4096-byte string limit, but remain bounded by 1 MiB.
    def container(name):
        raw = (args.fixtures / name).read_bytes()
        if len(raw) > 64 * MAX_BYTES:
            fail('LIMIT')
        return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                          parse_float=lambda _: fail('NUMBER'),
                          parse_constant=lambda _: fail('NUMBER'))
    trusted_receipts = container('trusted_receipts.json')
    archive = decode((args.fixtures / 'positive.json').read_bytes())
    records, retained = validate_archive(archive, trusted_receipts)
    golden = decode((args.fixtures / 'golden.json').read_bytes())
    if len(golden) != len(records):
        fail('GOLDEN')
    for record, fixed in zip(archive['records'], golden):
        if canonical(record).hex() != fixed['canonical_hex'] or digest(record) != fixed['sha256']:
            fail('GOLDEN')
    for case in container('negative.json'):
        try:
            obj = decode(case['raw'].encode('utf-8'))
            if case['operation'] == 'archive':
                validate_archive(obj, trusted_receipts)
            elif case['operation'] == 'observe':
                observe(archive, **obj, trusted_receipts=trusted_receipts)
            elif case['operation'] != 'decode':
                fail('SCHEMA')
        except Invalid as exc:
            if exc.code != case['error']:
                raise AssertionError((case['name'], case['error'], exc.code)) from exc
        else:
            raise AssertionError((case['name'], 'unexpected success'))
    for query in ((0, 1, 1), (0, 2, 2)):
        observe(archive, *query, trusted_receipts=trusted_receipts)
    print(f'PASS: {len(records)} fixed records; {len(retained)} retained roots; {len(container('negative.json'))} negative vectors; exact same-tick history')

if __name__ == '__main__':
    main()
