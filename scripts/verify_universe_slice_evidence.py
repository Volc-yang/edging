#!/usr/bin/env python3
"""Independent, read-only I12 evidence checks. Never grants G-B2 by itself.

No production imports, signer, solver, subprocesses, network or update mode.
Exit 0 = structural checks complete, 1 = contradiction, 2 = missing evidence.
Runtime authenticity, UI semantics and resource-card authorization need review.
"""
import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import sys

PREFIX = b'edgeworld.universe.authority\0v0.2\0'
HASH = re.compile(r'[0-9a-f]{64}\Z')
REQUIRED_PAIRS = {'camera', 'visibility', 'framerate', 'pause', 'history',
                  'history_write_rejected', 'held_input', 'retry', 'revisit'}
REQUIRED_ARTIFACTS = {'source', 'build', 'public_pins', 'owner_metadata',
                      'asset_export', 'ue_log', 'launcher_log', 'processes'}
MAX_BYTES = 2 * 1024**3


class Invalid(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise Invalid(message)


def unique_pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def read_json(path):
    return json.loads(safe_read(path, 16 * 1024**2).decode('utf-8'),
                      object_pairs_hook=unique_pairs,
                      parse_constant=lambda value: (_ for _ in ()).throw(Invalid(value)))


def safe_path(path):
    path = Path(path).absolute()
    require(not any(p.is_symlink() for p in (path, *path.parents)),
            'symlink evidence path: ' + str(path))
    return path


def safe_read(path, cap=8 * 1024**2):
    path = safe_path(path)
    require(path.is_file(), 'missing regular evidence file: ' + str(path))
    require(path.stat().st_size <= cap, 'file exceeds cap: ' + str(path))
    return path.read_bytes()


def file_hash(path):
    path = safe_path(path)
    require(path.is_file(), 'hash input is not a regular file: ' + str(path))
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            digest.update(block)
    return digest.hexdigest()


def canonical(value):
    """Contract scalar validation, independent of the production codec."""
    def visit(item, depth=0):
        require(depth <= 32, 'record depth')
        if item is None or type(item) is bool:
            return
        if type(item) is int:
            require(abs(item) <= 2**53 - 1, 'record integer precision')
        elif type(item) is str:
            require(len(item.encode('utf-8')) <= 4096, 'record string size')
        elif type(item) is list:
            require(len(item) <= 256, 'record array size')
            for child in item:
                visit(child, depth + 1)
        elif type(item) is dict:
            require(len(item) <= 64, 'record object size')
            if '$f64' in item:
                f64(item)
            for key, child in item.items():
                visit(key, depth + 1)
                visit(child, depth + 1)
        else:
            raise Invalid('raw float or unsupported record scalar')
    visit(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(',', ':'), allow_nan=False).encode('ascii')


def f64(value):
    require(type(value) is dict and set(value) == {'$f64'} and
            type(value['$f64']) is str and re.fullmatch('[0-9a-f]{16}', value['$f64']),
            'invalid f64 bits')
    number = struct.unpack('>d', bytes.fromhex(value['$f64']))[0]
    require(math.isfinite(number), 'nonfinite f64')
    return Fraction.from_float(number)


def influence(before, after):
    """Exact rational subtraction and ties-to-even integer rounding."""
    return round(1000 * (f64(after) - f64(before)))


def authority_map(root):
    """Hashes every file; never follows links or reads a key/config location."""
    root = safe_path(root)
    require(root.is_dir(), 'missing authority directory')
    result = {}
    total = 0
    for path in sorted(root.rglob('*')):
        safe_path(path)
        if path.is_dir():
            continue
        require(path.is_file(), 'nonregular authority entry')
        name = str(path.relative_to(root))
        require(not re.search(r'(^|[/._-])(key|secret|owner)([/._-]|$)', name, re.I),
                'refuse potential private material: ' + name)
        size = path.stat().st_size
        total += size
        require(total <= MAX_BYTES, 'authority map exceeds 2GiB')
        result[name] = {'bytes': size, 'sha256': file_hash(path)}
    return {'root': str(root), 'files': result, 'bytes': total}


def inspect_authority(root, schema):
    root = safe_path(root)
    records = {}
    raw_total = 0
    for path in sorted((root / 'objects').glob('*.json')):
        raw = safe_read(path, 65536)
        record = read_json(path)
        require(set(record) == {'domain', 'version', 'world_id', 'kind', 'id', 'body', 'refs'},
                'record keys')
        require(record['domain'] == 'edgeworld.universe.authority' and record['version'] == '0.2',
                'record domain/version')
        encoded = canonical(record)
        digest = hashlib.sha256(PREFIX + encoded).hexdigest()
        require(raw == encoded and path.name == digest + '.json', 'record bytes/name mismatch')
        require(record['kind'] in schema['body'], 'unknown record kind')
        require(set(record['body']) == set(schema['body'][record['kind']]), 'record body keys')
        require(len(raw) <= schema['kind_bytes'][record['kind']], 'kind size limit')
        records[digest] = record
        require(len(records) <= 2048, 'record count limit')
    require(records, 'no authority records')
    head = read_json(root / 'HEAD.json')
    require(safe_read(root / 'HEAD.json') == canonical(head), 'noncanonical HEAD')
    require(set(head) == {'domain', 'version', 'world_id', 'manifest', 'profile'} and
            head['domain'] == 'edgeworld.universe.authority' and head['version'] == '0.2' and
            head['profile'] == 'composite-rigid-support.v0.2', 'HEAD identity')
    for digest, record in records.items():
        require(record['world_id'] == head['world_id'], 'mixed world')
        declarations = schema['refs'][record['kind']]
        if record['kind'] == 'route':
            declarations = {'p' + str(i): 'place'
                            for i in range(len(record['body']['place_ids']))}
        allowed = {name.rstrip('?'): kind for name, kind in declarations.items()}
        required = {name for name in declarations if not name.endswith('?')}
        require(required <= record['refs'].keys() <= allowed.keys(), 'record refs keys')
        for role, ref in record['refs'].items():
            require(type(ref) is str and HASH.fullmatch(ref) and ref in records,
                    'missing referenced record: ' + str(ref))
            require(records[ref]['kind'] == allowed[role], 'reference kind mismatch')
        if record['kind'] == 'checkpoint_descriptor':
            body = record['body']
            require(type(body['payload_sha256']) is str and HASH.fullmatch(body['payload_sha256']),
                    'invalid raw payload digest')
            suffix = '.static' if body['artifact_class'] == 'synthetic-contract-only' else '.gstraj'
            path = root / 'blobs' / (body['payload_sha256'] + suffix)
            require(path.stat().st_size == body['byte_count'] and
                    file_hash(path) == body['payload_sha256'], 'raw payload hash/size')
            raw_total += body['byte_count']
    visited, active = set(), set()
    def traverse(ref):
        require(ref in records, 'HEAD/closure reference absent')
        require(ref not in active, 'reference cycle')
        if ref in visited:
            return
        active.add(ref)
        for child in records[ref]['refs'].values():
            traverse(child)
        active.remove(ref)
        visited.add(ref)
    traverse(head['manifest'])
    manifests = [r for d, r in records.items() if d in visited and r['kind'] == 'manifest']
    require(len(manifests) <= 64, 'retained root limit')
    chain = []
    ref = head['manifest']
    while True:
        manifest = records[ref]
        require(manifest['kind'] == 'manifest', 'nonmanifest HEAD/history')
        chain.append((ref, manifest))
        if 'prior_manifest' not in manifest['refs']:
            break
        ref = manifest['refs']['prior_manifest']
    chain.reverse()
    states = []
    def snapshot(state):
        return records[state['refs']['snapshot']]
    def dynamic_z(state):
        sample = records[snapshot(state)['refs']['sample']]
        bodies = [b for b in sample['body']['bodies'] if b['physical_id'] == 'body-dynamic']
        require(len(bodies) == 1, 'dynamic sample identity')
        return bodies[0]['position_m'][2]
    for index, (ref, manifest) in enumerate(chain):
        state = records[manifest['refs']['state']]
        body = state['body']
        require(manifest['body'] == {'tick': body['tick'], 'revision': body['revision'],
                                    'watermark': body['revision']}, 'manifest/state time')
        if index == 0:
            require(body == {'tick': 0, 'revision': 0, 'development_mm': None,
                             'budget': 8, 'random_cursor': 0}, 'initial state')
            require(snapshot(state)['body'] == {'case_id': 'initial', 'physical_step_count': 0},
                    'initial physics snapshot')
            world = records[state['refs']['world']]
            places = [records[world['refs'][name]] for name in
                      ('city', 'wildland', 'plain', 'forest', 'river_marsh', 'ocean')]
            require({p['body']['place_kind'] for p in places} ==
                    {'city', 'wildland', 'plain', 'forest', 'river_marsh', 'ocean'}, 'six places')
        else:
            prior = states[-1]
            pb = prior['body']
            event = records[manifest['refs']['event']]
            admission = records[event['refs']['admission']]
            candidate = records[admission['refs']['candidate']]
            command = records[candidate['refs']['command']]
            intent = records[command['refs']['intent']]['body']
            result = records[records[manifest['refs']['index']]['refs']['result']]
            require(candidate['refs']['prior_state'] == chain[index - 1][1]['refs']['state'] and
                    event['refs']['state'] == manifest['refs']['state'] and
                    result['refs']['state'] == manifest['refs']['state'] and
                    result['refs']['checkpoint'] == state['refs']['snapshot'], 'causal links')
            require(body['revision'] == pb['revision'] + 1 and
                    state['refs']['world'] == prior['refs']['world'], 'revision/world continuity')
            if intent['action'] == 'retain_snapshot':
                expected = dict(pb, revision=body['revision'])
                require(body == expected and state['refs']['snapshot'] == prior['refs']['snapshot'] and
                        candidate['body']['adapter_kind'] == 'checkpoint_reuse', 'retain changed authority')
            else:
                require(intent['action'] == 'physics_step', 'unknown action')
                measured = influence(dynamic_z(prior), dynamic_z(state))
                require(body['tick'] == pb['tick'] + 1 and body['random_cursor'] == pb['random_cursor'] + 1 and
                        body['budget'] == pb['budget'] - intent['budget'] >= 0 and
                        body['development_mm'] == candidate['body']['influence_mm'] == measured and
                        abs(measured) <= 1000, 'physical development/budget/cursor')
                require(snapshot(state)['body']['physical_step_count'] ==
                        snapshot(prior)['body']['physical_step_count'] + 8 and
                        candidate['body']['adapter_kind'] == 'genesis', 'physical step count/adapter')
        states.append(state)
    return {'world_id': head['world_id'], 'head': head['manifest'],
            'records': len(records), 'retained_manifests': len(manifests),
            'history': [{'tick': s['body']['tick'], 'revision': s['body']['revision'],
                         'development_mm': s['body']['development_mm']} for s in states],
            'descriptor_bytes_including_reuse': raw_total,
            'records_by_hash': records}


def wire_frame(raw):
    require(len(raw) <= 1024**2 + 1 and raw.endswith(b'\n') and
            b'\n' not in raw[:-1] and b'\r' not in raw and not raw.startswith(b'\xef\xbb\xbf'),
            'invalid JSONL framing')
    return json.loads(raw[:-1].decode('utf-8'), object_pairs_hook=unique_pairs,
                      parse_float=lambda _: (_ for _ in ()).throw(Invalid('wire raw float')),
                      parse_constant=lambda _: (_ for _ in ()).throw(Invalid('wire nonfinite')))


def inspect_trace(directory):
    """Reassemble ordered raw chunks per transport prefix and request serial."""
    directory = safe_path(directory)
    groups = defaultdict(list)
    for path in sorted(directory.glob('*.json')):
        meta = read_json(path)
        require(Path(meta['raw_file']).name == meta['raw_file'], 'trace path escape')
        raw = safe_read(directory / meta['raw_file'], 1024**2 + 1)
        require(len(raw) == meta['byte_count'], 'trace byte count')
        prefix = path.stem.rsplit('-', 1)[0]
        groups[prefix].append((meta, raw))
    require(groups, 'empty trace')
    frames, exits = [], []
    for prefix, entries in groups.items():
        entries.sort(key=lambda item: int(item[0]['serial']))
        require([int(m['serial']) for m, _ in entries] == list(range(1, len(entries) + 1)),
                'trace serial gap/duplicate')
        request, chunks, written = None, bytearray(), False
        request_size = 0
        last_time = -math.inf
        identity = None
        for meta, raw in entries:
            require(meta['monotonic_seconds'] >= last_time, 'trace clock reversal')
            last_time = meta['monotonic_seconds']
            require(meta['worker_pid'] > 0 and meta['host_pid'] > 0 and int(meta['generation']) > 0,
                    'trace process identity unavailable')
            current = (meta['host_pid'], meta['worker_pid'], meta['generation'])
            if identity is None:
                identity = current
            require(identity == current, 'transport identity changed inside prefix')
            direction = meta['direction']
            if direction == 'request':
                require(request is None, 'overlapping requests')
                request = wire_frame(raw)
                request_size = len(raw)
                require(request['request_id'] == meta['request_id'] and
                        request['operation'] == meta['operation'], 'request metadata mismatch')
                chunks.clear()
                written = False
            elif direction == 'write-result':
                require(request is not None and meta['written_bytes'] == request_size,
                        'incomplete request write')
                written = True
            elif direction == 'stdout-chunk':
                require(request is not None and meta['request_id'] == request['request_id'],
                        'unowned stdout')
                chunks.extend(raw)
            elif direction == 'response-complete':
                require(request is not None and written, 'response without written request')
                response = wire_frame(bytes(chunks))
                require(response['request_id'] == request['request_id'] and
                        response['protocol_version'] == request['protocol_version'] == 1,
                        'wire request identity mismatch')
                frames.append({'request': request, 'response': response,
                               'worker_pid': meta['worker_pid'], 'host_pid': meta['host_pid'],
                               'generation': meta['generation'], 'utc': meta['utc']})
                request = None
            elif direction == 'worker-exit':
                event = json.loads(raw, object_pairs_hook=unique_pairs)
                require(event['worker_pid'] == meta['worker_pid'] and
                        event['generation'] == meta['generation'], 'exit identity mismatch')
                require(event['return_code_available'] is True and event['exit_code'] == 0 and
                        event['reaped'] is True and event['trace_complete'] is True and
                        event['stop_kind'] == 'normal' and event['hard_kill_sent'] is False and
                        event['operational_failure'] is False, 'worker abnormal/incomplete exit')
                exits.append(event)
            elif direction not in {'stderr-chunk', 'stdin-eof', 'shutdown-stdout-chunk',
                                    'shutdown-stderr-chunk'}:
                raise Invalid('unknown trace direction: ' + direction)
        require(request is None, 'unfinished request')
    return {'frames': frames, 'worker_exits': exits, 'transport_count': len(groups)}


def verify_bundle(path, schema):
    """Checks supplied evidence; missing requirements remain inconclusive."""
    bundle = read_json(path)
    require(bundle['format'] == 'universe-i12-evidence.v1', 'bundle version')
    missing = []
    artifacts = bundle.get('artifacts', [])
    total, names = 0, set()
    for artifact in artifacts:
        require(artifact['path'] not in names, 'duplicate artifact path')
        names.add(artifact['path'])
        p = safe_path(artifact['path'])
        require(0 <= artifact['bytes'] <= MAX_BYTES and total + artifact['bytes'] <= MAX_BYTES,
                'indexed evidence exceeds byte cap')
        require(p.stat().st_size == artifact['bytes'] and file_hash(p) == artifact['sha256'],
                'artifact hash/size mismatch: ' + str(p))
        total += artifact['bytes']
    require(total <= bundle['budget']['bytes'] <= MAX_BYTES, 'evidence byte budget')
    roles = {a['role'] for a in artifacts}
    missing.extend('artifact:' + role for role in sorted(REQUIRED_ARTIFACTS - roles))
    budget = bundle['budget']
    require(0 <= budget['elapsed_seconds'] <= budget['seconds'] <= 1200, 'elapsed budget')
    if not budget.get('covers_all_attempts'):
        missing.append('all-attempt resource accounting')
    if not bundle.get('resource_card'):
        missing.append('actual root-issued R12 card')
    sessions = bundle.get('sessions', [])
    if len(sessions) != 2:
        missing.append('two complete UE-owned sessions')
    worlds, roots, workers = set(), set(), []
    for session in sessions:
        for directory in ('authority_copy', 'trace_directory'):
            for entry in safe_path(session[directory]).rglob('*'):
                safe_path(entry)
                if entry.is_file():
                    require(str(entry) in names, 'unindexed raw/authority evidence: ' + str(entry))
        authority = inspect_authority(session['authority_copy'], schema)
        trace = inspect_trace(session['trace_directory'])
        worlds.add(authority['world_id'])
        roots.add(session['canonical_authority'])
        workers.extend(e['worker_pid'] for e in trace['worker_exits'])
        if len(trace['worker_exits']) != trace['transport_count']:
            missing.append('one exit per owned transport')
        for role in ('ue', 'launcher'):
            event = session.get(role + '_exit', {})
            if not (event.get('observed') is True and type(event.get('pid')) is int and
                    event['pid'] > 0 and event.get('exit_code') == 0 and
                    event.get('process_evidence') in names):
                missing.append(role + ' actual process/exit evidence')
        screenshots = session.get('screenshots', [])
        if not screenshots:
            missing.append('new Metal screenshot')
        for shot in screenshots:
            require(shot['path'] in names and shot['after_observation'] <= shot['captured_at'] <=
                    shot['before_exit'], 'screenshot chronology/index')
            require(shot['renderer'] == 'Metal', 'screenshot renderer')
            require(safe_read(shot['path'], 64 * 1024**2).startswith(b'\x89PNG\r\n\x1a\n'),
                    'screenshot must be original PNG')
    if sessions:
        require(len(worlds) == len(roots) == 1, 'sessions do not revisit same authority/world')
    if len(workers) != 2 or len(set(workers)) != 2:
        missing.append('two distinct normally exited worker PIDs')
    pairs = bundle.get('readonly_pairs', [])
    covered = set()
    for pair in pairs:
        before, after = read_json(pair['before']), read_json(pair['after'])
        require(before['root'] == after['root'] and before['files'] == after['files'],
                'authority changed during ' + pair['action'])
        require(pair['before'] in names and pair['after'] in names and
                pair.get('action_evidence') in names, 'unindexed map/action evidence')
        covered.add(pair['action'])
    missing.extend('readonly:' + action for action in sorted(REQUIRED_PAIRS - covered))
    # An evidence inventory cannot establish visual/input semantics or authorization.
    missing.extend('review:' + gate for gate in ('causal_chain', 'initial_six_places',
                    'exact_history', 'same_closure_retry', 'input_gates', 'metal_ui',
                    'source_build_identity', 'trusted_bootstrap', 'resource_authorization')
                   if bundle.get('independent_reviews', {}).get(gate) not in names)
    return {'status': 'inconclusive' if missing else 'checks_complete_requires_root_verdict',
            'missing': missing, 'indexed_bytes': total,
            'note': 'Structural evidence checks do not independently grant G-B2.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--schema', type=Path, default=Path(__file__).resolve().parents[1] /
                        'doc/fixtures/universe_authority_v0_2/schema.json')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--bundle', type=Path)
    group.add_argument('--authority', type=Path)
    group.add_argument('--trace', type=Path)
    args = parser.parse_args()
    try:
        if args.bundle:
            result = verify_bundle(args.bundle, read_json(args.schema))
        elif args.authority:
            result = inspect_authority(args.authority, read_json(args.schema))
            result.pop('records_by_hash')
            result['status'] = 'partial_authority_check_only'
        else:
            result = inspect_trace(args.trace)
            result['status'] = 'partial_trace_check_only'
        print(json.dumps(result, sort_keys=True, ensure_ascii=True))
        return 2 if result['status'] == 'inconclusive' else 0
    except (Invalid, OSError, ValueError, KeyError, TypeError, RecursionError) as error:
        print(json.dumps({'status': 'fail', 'error': str(error)}))
        return 1


if __name__ == '__main__':
    sys.exit(main())
