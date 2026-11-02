"""I13-B passive action evidence checks. No UI, subprocess, worker or authority imports.

A result is evidence consistency, never runtime authenticity or a G-B2 grant. R must
validate source/bootstrap/proof/PNG/lifecycle and the origin of CUA/log artifacts.
The proposed EW_I13_READBACK marker is NOT implemented by the current UE source.
"""
from copy import deepcopy
from functools import wraps
import hashlib
import json
import math
import os
from datetime import datetime
from pathlib import Path
import re

FORMAT = 'universe-i13-actions.v1'
READBACK_FORMAT = 'universe-i13-readback.v1'
HISTORY_REJECTION_FORMAT = 'universe-i13-history-rejection.v1'
PREFIX = b'edgeworld.universe.authority\0v0.2\0'
CAP = 16 * 1024**2
SHA = re.compile(r'[0-9a-f]{64}\Z')
REQUEST_ID = re.compile(r'u-[0-9a-f]{32}\Z')
BINDING_KEYS = {'run_id', 'session', 'world_id', 'authority_root', 'source_sha',
                'host_pid', 'worker_pid', 'generation'}
READONLY = frozenset({'camera', 'visibility', 'framerate', 'pause', 'history',
                      'history_write_rejected', 'held_input', 'retry', 'revisit'})
DIAGNOSTIC_KINDS = READONLY - {'history', 'retry', 'revisit'} | {'probe', 'final'}
H0 = {'tick': 0, 'revision': 0, 'watermark': 0}
H1 = {'tick': 0, 'revision': 1, 'watermark': 1}
H2 = {'tick': 1, 'revision': 2, 'watermark': 2}


class Invalid(ValueError):
    """Missing, malformed, stale or contradictory evidence; never a silent pass."""


def _boundary(function):
    @wraps(function)
    def checked(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Invalid:
            raise
        except (KeyError, TypeError, IndexError, ValueError, OSError, AttributeError) as error:
            raise Invalid(function.__name__ + ': malformed/missing evidence: ' + str(error)) from error
    return checked


def _same_json(left, right):
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(right, sort_keys=True, allow_nan=False)


def require(test, message):
    if not test:
        raise Invalid(message)


def _keys(value, required, label):
    require(type(value) is dict and set(value) == set(required), label + ': exact fields required')


def _integer(value, minimum=0):
    return type(value) is int and value >= minimum


def _utc(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.tzinfo is not None and parsed.utcoffset() is not None
    except (ValueError, TypeError, AttributeError):
        return False


def _seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def _head(value):
    _keys(value, H0, 'head')
    require(all(_integer(x) and x <= 9007199254740991 for x in value.values()) and
            value['revision'] == value['watermark'], 'invalid head')


def _binding(actual, expected):
    for value in (actual, expected):
        _keys(value, BINDING_KEYS, 'binding')
        require(value['session'] in ('initialize', 'existing'), 'session')
        require(all(type(value[k]) is str and value[k] for k in ('run_id', 'world_id')), 'run/world')
        require(type(value['source_sha']) is str and re.fullmatch('[0-9a-f]{40}', value['source_sha']), 'source SHA')
        require(all(_integer(value[k], 1) for k in ('host_pid', 'worker_pid', 'generation')), 'PID/generation')
        _path(value['authority_root'])
    require(actual == expected, 'binding differs from independent expected_binding')


def _path(raw):
    require(type(raw) is str, 'path string required')
    path = Path(raw)
    require(path.is_absolute() and str(path) == raw and '..' not in path.parts, 'canonical absolute path required')
    require(not any(p.is_symlink() for p in (path, *path.parents)), 'symlink evidence path')
    return path


def _read(path, cap=CAP):
    path = _path(str(path))
    before = path.lstat()
    require(path.is_file() and before.st_size <= cap, 'missing/oversized regular file')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        require((before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino), 'file replaced before read')
        raw = stream.read(cap + 1)
        after = os.fstat(stream.fileno())
    current = path.lstat()
    require(len(raw) <= cap and (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns) ==
            (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) ==
            (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns), 'file changed during read')
    return raw


def _pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, 'duplicate JSON key')
        result[key] = value
    return result


def _json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(Invalid('nonfinite JSON')))
    except (ValueError, UnicodeError) as error:
        raise Invalid('invalid JSON: ' + str(error)) from error


@_boundary
def reference(ref):
    """Read one explicitly named public artifact; no recursive scans or private input API."""
    _keys(ref, {'path', 'sha256'}, 'reference')
    require(type(ref['sha256']) is str and SHA.fullmatch(ref['sha256']), 'reference hash')
    path = _path(ref['path'])
    require(path.name not in {'authority.key', 'owner-initialize.json', 'owner-existing.json'},
            'private file forbidden')
    raw = _read(path)
    require(hashlib.sha256(raw).hexdigest() == ref['sha256'], 'reference hash mismatch')
    return raw


def _map(ref, root):
    value = _json(reference(ref))
    require(type(value) is dict and {'root', 'files'} <= set(value), 'authority map shape')
    require(value['root'] == root and type(value['files']) is dict, 'authority map root/files')
    for name, entry in value['files'].items():
        p = Path(name)
        require(type(name) is str and name and not p.is_absolute() and
                all(x not in ('.', '..') for x in p.parts) and
                type(entry) is dict and set(entry) == {'bytes', 'sha256'} and
                _integer(entry['bytes']) and type(entry['sha256']) is str and SHA.fullmatch(entry['sha256']),
                'authority map entry')
    return value['files']


def _command(text, seconds):
    return {'text': text, 'max_seconds': seconds}


def _item(name, session, kind, seconds, commands, operations=(), heads=(),
          selected=None, trusted=None, stages=('completed',), phase='interaction', image=False):
    # Costs are explicit planning caps, not measurements; command+passive costs sum to max_seconds.
    commands = [_command(text, 2) for text in commands]
    command_seconds = sum(x['max_seconds'] for x in commands)
    require(command_seconds < seconds, 'internal action cost allocation')
    remaining = seconds - command_seconds
    checkpoint_commands = {
        's1.camera': [-1, 0, 1], 's1.visibility': [-1, 0, 1],
        's1.framerate': [0, 2, 4], 's1.pause': [0, 2, 4],
        's1.history': [0, 1, 2], 's1.history_write_rejected': [0, 1, 1],
        's1.held_input': [0, 1, 2], 's2.revisit': [0, 1, 2],
    }.get(name, [len(commands) - 1] * len(stages))
    return {'action_id': name, 'session': session, 'kind': kind, 'commands': commands,
            'max_seconds': seconds, 'phase': phase, 'charged_budget': phase,
            'trusted_head': deepcopy(trusted or H2),
            'selected_observation': deepcopy(selected or trusted or H2),
            'expected_operations': list(operations), 'observation_heads': deepcopy(list(heads)),
            'stages': list(stages), 'checkpoint_commands': checkpoint_commands, 'required_evidence': ['before', 'after', 'log', 'trace', 'cua', 'checkpoints'] +
            (['image_checks'] if image else []),
            'passive_costs': {'maps_seconds': remaining / 3, 'marker_seconds': remaining / 3,
                              'image_restore_seconds': remaining / 3}}


def manifest():
    """Return a new fixed manifest. Command strings are instructions, never executable here."""
    items = [
        _item('s1.initialize', 'initialize', 'initialize', 60, [],
              ('status', 'initialize', 'status', 'observe'), (H0,), H0, H0, phase='startup'),
        _item('s1.probe', 'initialize', 'probe', 15, ['native Shot via C prepare', 'inspect quit guard'],
              trusted=H0, stages=('png_and_guard',), image=True),
        _item('s1.native_ids', 'initialize', 'native', 10,
              ['Automation RunTests edgeWorld.UniverseHost.ProtocolIds'], trusted=H0),
        _item('s1.native_assets', 'initialize', 'native', 10,
              ['Automation RunTests edgeWorld.UniverseHost.StandaloneAssetAudit'], trusted=H0),
        _item('s1.retain', 'initialize', 'retain', 15, ['UniverseRetain'],
              ('prepare', 'advance', 'status', 'observe'), (H1,), H1, H1, image=True),
        _item('s1.physical', 'initialize', 'physical', 20, ['viewport key 1', 'UniverseAdvance'],
              ('prepare', 'advance', 'status', 'observe'), (H2,), image=True),
        _item('s1.retry', 'initialize', 'retry', 10, ['UniverseRetryLastCommitted'],
              ('advance', 'status', 'observe'), (H2,)),
        _item('s1.history', 'initialize', 'history', 25,
              ['UniverseObserveExact 0 1 1', 'UniverseObserveExact 0 0 0', 'UniverseObserveExact 1 2 2'],
              ('observe', 'observe', 'observe'), (H1, H0, H2), stages=('history01', 'history00', 'current12'), image=True),
        _item('s1.history_select', 'initialize', 'history', 6, ['UniverseObserveExact 0 1 1'],
              ('observe',), (H1,), H1, H2, stages=('history01',)),
        _item('s1.history_write_rejected', 'initialize', 'history_write_rejected', 14,
              ['viewport Space press/release in history', 'viewport R press/release in history'],
              selected=H1, stages=('space_rejected', 'retain_rejected', 'released')),
        _item('s1.held_input', 'initialize', 'held_input', 25,
              ['Space down in history; keep held', 'H while Space remains held', 'Space up'],
              ('observe',), (H2,), stages=('held_history', 'held_current', 'released')),
        _item('s1.camera', 'initialize', 'camera', 20,
              ['UniverseCamera 15 0', 'UniverseCamera -15 0'], stages=('before', 'moved', 'restored'), image=True),
        _item('s1.visibility', 'initialize', 'visibility', 20,
              ['UniverseProjectionVisible false', 'UniverseProjectionVisible true'],
              stages=('before', 'hidden', 'restored'), image=True),
        _item('s1.framerate', 'initialize', 'framerate', 15,
              ['t.MaxFPS (read)', 't.MaxFPS 30', 't.MaxFPS (read)', 't.MaxFPS <original>', 't.MaxFPS (read)'],
              stages=('before', 'changed', 'restored')),
        _item('s1.pause', 'initialize', 'pause', 15,
              ['read actual pause state', 'pause', 'read actual pause state', 'pause', 'read actual pause state'],
              stages=('before', 'paused', 'restored')),
        _item('s1.final', 'initialize', 'final', 20, ['release all inputs and verify restored state'],
              stages=('released_and_restored',)),
        _item('s1.exit', 'initialize', 'exit', 40, ['normal quit via CUA'], phase='shutdown'),
        _item('s2.recover', 'existing', 'recover', 60, [], ('status', 'observe'), (H2,), phase='startup'),
        _item('s2.probe', 'existing', 'probe', 20, ['native Shot via C prepare', 'inspect quit guard'],
              stages=('png_and_guard',), image=True),
        _item('s2.revisit', 'existing', 'revisit', 60,
              ['UniverseObserveExact 1 2 2', 'UniverseObserveExact 0 1 1', 'UniverseObserveExact 1 2 2'],
              ('observe', 'observe', 'observe'), (H2, H1, H2), stages=('current12', 'history01', 'restored'), image=True),
        _item('s2.final', 'existing', 'final', 20, ['release all inputs and verify restored state'],
              stages=('released_and_restored',)),
        _item('s2.exit', 'existing', 'exit', 40, ['normal quit via CUA'], phase='shutdown')]
    return {'format': FORMAT, 'items': items, 'request_counts': {'initialize': 20, 'existing': 5},
            'interaction_caps': {'initialize': 240, 'existing': 100},
            'cost_status': 'proposed_not_measured', 'readonly_kinds': sorted(READONLY)}


def _item_for(action_id):
    found = [x for x in manifest()['items'] if x['action_id'] == action_id]
    require(len(found) == 1, 'unknown action_id')
    return found[0]


@_boundary
def readiness(capabilities, *, expected_source_sha):
    """Fail closed: independently reviewed capability/measurement refs, not owner booleans.

    R owns authenticity and review authorization. No missing capability is assumed available.
    """
    required = {'readback_markers', 'cross_call_hold', 'png_contract', 'quit_guard', 'timings'}
    require(type(capabilities) is dict and set(capabilities) <= required, 'capability names')
    require(type(expected_source_sha) is str and re.fullmatch('[0-9a-f]{40}', expected_source_sha), 'expected source SHA')
    reasons = []
    for name in sorted(required):
        if name not in capabilities:
            reasons.append(name + ': missing independent capability evidence')
            continue
        proof = _json(reference(capabilities[name]))
        _keys(proof, {'format', 'source_sha', 'capability', 'reviewer', 'owner', 'decision', 'evidence_refs',
                      'action_upper_seconds'}, 'capability proof')
        require(proof['format'] == 'universe-i13-capability-review.v1' and
                proof['source_sha'] == expected_source_sha and proof['capability'] == name, 'capability binding')
        require(type(proof['reviewer']) is str and proof['reviewer'] and
                type(proof['owner']) is str and proof['owner'] and proof['reviewer'] != proof['owner'], 'independent review')
        require(proof['decision'] in ('pass', 'fail', 'inconclusive'), 'capability decision')
        require(type(proof['evidence_refs']) is list and proof['evidence_refs'], 'capability raw evidence')
        for ref in proof['evidence_refs']:
            reference(ref)
        if proof['decision'] != 'pass':
            reasons.append(name + ': ' + proof['decision'])
        if name == 'timings':
            caps = proof['action_upper_seconds']
            expected = {x['action_id']: x for x in manifest()['items'] if x['phase'] == 'interaction'}
            require(type(caps) is dict and set(caps) == set(expected), 'per-action measured/reviewed timing coverage')
            for action, upper in caps.items():
                if not _seconds(upper) or upper > expected[action]['max_seconds']:
                    reasons.append(action + ': no usable timing upper bound')
        else:
            require(proof['action_upper_seconds'] == {}, 'timings belong only in timing review')
    return {'status': 'no_go' if reasons else 'ready_for_R_review', 'reasons': reasons,
            'runtime_verified': False, 'g_b2_granted': False}


def _wire(raw):
    require(raw.endswith(b'\n') and b'\n' not in raw[:-1] and not raw.endswith(b'\r\n'), 'one LF wire frame')
    return _json(raw)


@_boundary
def load_trace(refs, *, expected_binding):
    """Reassemble explicitly indexed native transport artifacts; preserve actual wire frames.

    Requires one complete normal transport. R still runs the independent authority/proof parser.
    No production imports or operations occur here.
    """
    _binding(expected_binding, expected_binding)
    require(type(refs) is list and refs, 'explicit trace refs required')
    indexed = {}
    for ref in refs:
        require(ref['path'] not in indexed, 'duplicate trace path')
        indexed[ref['path']] = reference(ref)
    parents = {str(Path(p).parent) for p in indexed}
    require(len(parents) == 1, 'one explicit trace directory')
    parent = Path(next(iter(parents)))
    entries, used, prefixes = [], set(), set()
    for path, raw in indexed.items():
        if not path.endswith('.json'):
            continue
        prefixes.add(Path(path).stem.rsplit('-', 1)[0])
        meta = _json(raw)
        require(type(meta) is dict and {'serial', 'direction', 'raw_file', 'byte_count', 'monotonic_seconds',
                                      'host_pid', 'worker_pid', 'generation'} <= set(meta), 'trace metadata')
        require(Path(meta['raw_file']).name == meta['raw_file'], 'raw trace path escape')
        raw_path = str(parent / meta['raw_file'])
        require(_integer(meta['byte_count']) and raw_path in indexed and len(indexed[raw_path]) == meta['byte_count'], 'unindexed/truncated trace raw')
        require(type(meta['serial']) in (int, str) and not isinstance(meta['serial'], bool) and
                re.fullmatch('[1-9][0-9]*', str(meta['serial'])), 'trace serial')
        meta['serial'] = int(meta['serial'])
        require(meta['host_pid'] == expected_binding['host_pid'] and type(meta['host_pid']) is int and
                meta['worker_pid'] == expected_binding['worker_pid'] and type(meta['worker_pid']) is int,
                'trace PID binding')
        # Native trace generation is a decimal FString, normalize only this documented wire field.
        require(type(meta['generation']) in (int, str) and not isinstance(meta['generation'], bool) and
                str(meta['generation']) == str(expected_binding['generation']), 'trace generation binding')
        entries.append((meta, indexed[raw_path]))
        used.update((path, raw_path))
    require(set(indexed) == used and len(prefixes) == 1, 'unowned artifact or multiple transport prefixes')
    entries.sort(key=lambda pair: pair[0]['serial'])
    require([m['serial'] for m, _ in entries] == list(range(1, len(entries) + 1)), 'trace serial gap/duplicate')
    frames, request_ids, pending, chunks, written, exits, last = [], set(), None, bytearray(), False, [], -1
    for meta, raw in entries:
        require(_seconds(meta['monotonic_seconds']) and meta['monotonic_seconds'] >= last, 'trace time reversal')
        last = meta['monotonic_seconds']
        direction = meta['direction']
        require(not exits, 'trace data after final worker exit')
        if direction in ('write-result', 'stdout-chunk', 'response-complete'):
            require(pending is not None and meta.get('request_id') == pending['request_id'] and
                    meta.get('operation') == pending['operation'], 'request-associated trace metadata mismatch')
        if direction == 'request':
            require(pending is None, 'overlapping request')
            pending = _wire(raw)
            _keys(pending, {'protocol_version', 'request_id', 'operation', 'payload'}, 'request envelope')
            rid = pending['request_id']
            require(type(rid) is str and REQUEST_ID.fullmatch(rid) and rid not in request_ids, 'fresh request ID')
            request_ids.add(rid)
            require(pending['protocol_version'] == 1 and type(pending['protocol_version']) is int and
                    pending['operation'] == meta.get('operation') and rid == meta.get('request_id'), 'request metadata/envelope')
            payload = pending['payload']
            require(type(payload) is dict and payload.get('world_id') == expected_binding['world_id'] and
                    payload.get('domain') == 'edgeworld.universe.authority' and payload.get('version') == '0.2', 'request context')
            request_size, written, chunks = len(raw), False, bytearray()
        elif direction == 'write-result':
            require(pending is not None and not written and meta.get('written_bytes') == request_size, 'request write incomplete/duplicate')
            written = True
        elif direction == 'stdout-chunk':
            require(pending is not None and meta.get('request_id') == pending['request_id'], 'unowned stdout')
            chunks.extend(raw)
            require(len(chunks) <= CAP, 'response cap')
        elif direction == 'response-complete':
            require(pending is not None and written and meta.get('request_id') == pending['request_id'], 'response without request')
            response = _wire(bytes(chunks))
            require(response.get('request_id') == pending['request_id'] and type(response.get('ok')) is bool and
                    type(response.get('protocol_version')) is int and response['protocol_version'] == 1, 'response envelope')
            frames.append({'request': pending, 'response': response})
            pending, chunks = None, bytearray()
        elif direction == 'worker-exit':
            require(pending is None, 'unfinished request at exit')
            event = _json(raw)
            require(event.get('worker_pid') == expected_binding['worker_pid'] and
                    str(event.get('generation')) == str(expected_binding['generation']), 'worker-exit binding')
            require(all(event.get(k) is True for k in ('return_code_available', 'reaped', 'trace_complete')) and
                    all(event.get(k) is False for k in ('hard_kill_sent', 'operational_failure')) and
                    type(event.get('exit_code')) is int and event['exit_code'] == 0 and
                    event.get('stop_kind') == 'normal', 'abnormal worker exit')
            exits.append(event)
        else:
            require(direction in ('stderr-chunk', 'stdin-eof', 'shutdown-stdout-chunk', 'shutdown-stderr-chunk'),
                    'unknown trace direction')
    require(pending is None and len(exits) == 1, 'one complete normally exited transport required')
    return frames


def _result(frame, binding, expected_context):
    response, request = frame['response'], frame['request']
    require(response['ok'] is True, 'unexpected failed operation')
    result = response.get('result')
    require(type(result) is dict and result.get('world_id') == binding['world_id'] and
            result.get('domain') == 'edgeworld.universe.authority' and result.get('version') == '0.2' and
            result.get('operation') == request['operation'] and type(result.get('payload')) is dict, 'response context/operation')
    payload = result['payload']
    hb = payload.get('head_binding')
    if hb is not None:
        require(type(hb) is dict and hb.get('authority_root') == binding['authority_root'] and
                hb.get('world_id') == binding['world_id'] and hb.get('storage_state') == 'ready', 'head binding')
        for key in ('trust_anchor', 'expected_build', 'expected_options'):
            require(hb.get(key) == expected_context[key], 'public context binding: ' + key)
    return payload


def _triple(value):
    head = {k: value.get(k) for k in H0}
    _head(head)
    return head


def _check_frames(item, frames, binding, context):
    require([f['request']['operation'] for f in frames] == item['expected_operations'], 'operation sequence/count')
    observations, observed_hashes, prepared = [], [], None
    for index, frame in enumerate(frames):
        op, request, response = frame['request']['operation'], frame['request']['payload'], frame['response']
        if item['kind'] == 'initialize' and index == 0:
            error = response.get('error', {})
            require(response['ok'] is False and error.get('code') in ('NOT_READY', 'UNINITIALIZED') and
                    error.get('commit_status') == 'not_attempted', 'explicit init first status must be uninitialized')
            continue
        payload = _result(frame, binding, context)
        if op == 'initialize':
            require(request.get('test_profile') == 'composite-rigid-support.v0.2' and
                    payload.get('commit_status') == 'confirmed' and payload.get('result') is None, 'initialization confirmation/profile')
        elif op == 'prepare':
            action = 'retain_snapshot' if item['kind'] == 'retain' else 'physics_step'
            intent = request.get('intent', {}).get('body', {})
            require(all(_integer(intent.get(k)) for k in ('expected_revision', 'budget', 'random_cursor', 'tick_delta')), 'integer intent fields')
            require(intent.get('action') == action and intent.get('expected_revision') == (0 if action == 'retain_snapshot' else 1) and
                    intent.get('budget') == (0 if action == 'retain_snapshot' else 1) and
                    intent.get('random_cursor') == 0 and intent.get('principal') == context['principal'], 'prepare intent semantics')
            if action == 'physics_step':
                require(intent.get('case_id') == 'weak' and intent.get('tick_delta') == 1, 'only explicit weak step')
            else:
                require(intent.get('tick_delta') == 0 and intent.get('case_id') is None and
                        'case_id' in intent, 'retain requires tick_delta=0 and explicit case_id=null')
            require(payload.get('committed_result') is None and type(payload.get('command_records')) is list and
                    payload['command_records'] and SHA.fullmatch(str(payload.get('command_digest'))), 'fresh prepare closure')
            prepared = payload
        elif op == 'advance':
            require(request.get('principal') == context['principal'] and payload.get('commit_status') == 'confirmed', 'advance principal/confirmation')
            if prepared is not None:
                require(request.get('command_records') == prepared['command_records'] and
                        request.get('command_digest') == prepared['command_digest'], 'prepare/advance closure mismatch')
            body = payload.get('result', {}).get('body', {})
            require(_triple(body) == item['trusted_head'], 'advance result head')
        elif op == 'status':
            require(_triple(payload) == item['trusted_head'] and payload.get('storage_state') == 'ready', 'trusted current head')
        elif op == 'observe':
            selected = _triple(request)
            require(payload.get('manifest', {}).get('body') == selected and payload.get('watermark') == selected['watermark'], 'selected manifest binding')
            require(payload.get('storage_state') == 'ready' and type(payload.get('records')) is list and
                    payload['records'] and type(payload.get('membership')) is list and payload['membership'], 'observe proof records missing')
            observations.append(selected)
            observed_hashes.append(payload.get('head'))
    require(observations == item['observation_heads'], 'exact observation sequence')
    return observed_hashes


def _log(receipt):
    pin = receipt['log']
    _keys(pin, {'ref', 'device', 'inode', 'before_offset', 'after_offset', 'prefix_sha256'}, 'log pin')
    require(all(_integer(pin[k]) for k in ('device', 'inode', 'before_offset', 'after_offset')) and
            pin['before_offset'] <= pin['after_offset'], 'log offsets/identity')
    path = _path(pin['ref']['path'])
    info = path.stat()
    require((info.st_dev, info.st_ino) == (pin['device'], pin['inode']), 'log replaced')
    raw = reference(pin['ref'])
    require(pin['after_offset'] <= len(raw) and
            hashlib.sha256(raw[:pin['before_offset']]).hexdigest() == pin['prefix_sha256'], 'stale log prefix/offset')
    return raw, pin


def _diagnostic(raw, event, item, receipt):
    # One line of the *bound UE log*, not a receipt's assertion of completed=true.
    start, end = event['log_start'], event['log_end']
    line = raw[start:end]
    marker = b'EW_I13_READBACK '
    require(line.count(marker) == 1 and line.endswith(b'\n'), 'missing complete diagnostic marker')
    value = _json(line.split(marker, 1)[1].strip())
    _keys(value, {'format', 'binding', 'action_id', 'stage', 'trusted_head', 'selected_observation', 'state'}, 'readback marker')
    require(value['format'] == READBACK_FORMAT and value['action_id'] == item['action_id'] and
            value['stage'] == event['stage'], 'readback action/stage')
    _binding(value['binding'], receipt['binding'])
    _head(value['trusted_head'])
    require(value['trusted_head'] == item['trusted_head'], 'readback trusted head')
    _head(value['selected_observation'])
    return value


def _history_rejection(states):
    """Require actual UE handler evidence; unchanged idle state is not a rejection."""
    for state in states:
        _keys(state, {'format', 'space_down', 'r_down', 'can_write', 'handled_input', 'handler_counts'},
              'history rejection state')
        require(state['format'] == HISTORY_REJECTION_FORMAT and
                _same_json({k: state[k] for k in ('space_down', 'r_down', 'can_write')},
                           {'space_down': False, 'r_down': False, 'can_write': False}),
                'history rejection/release readback')
        _keys(state['handler_counts'], {'SpacePressed', 'Retain'}, 'actual handler counters')
        require(all(_integer(v) for v in state['handler_counts'].values()), 'integer handler counters')
    for index, (key, handler) in enumerate((('Space', 'SpacePressed'), ('R', 'Retain'))):
        state, event = states[index], states[index]['handled_input']
        _keys(event, {'key', 'event', 'handler', 'handled', 'rejected', 'reason',
                      'counter_before', 'counter_after'}, 'actual rejected input event')
        require(event['key'] == key and event['event'] == 'pressed' and event['handler'] == handler and
                event['handled'] is True and event['rejected'] is True and event['reason'] == 'history_read_only',
                'input did not reach handler or was not rejected for history')
        require(_integer(event['counter_before']) and _integer(event['counter_after'], 1) and
                event['counter_after'] == event['counter_before'] + 1 and
                state['handler_counts'][handler] == event['counter_after'], 'handler invocation must increment exactly once')
    first, second, released = states
    require(second['handler_counts']['SpacePressed'] == first['handler_counts']['SpacePressed'] and
            second['handled_input']['counter_before'] == first['handler_counts']['Retain'] and
            released['handled_input'] is None and released['handler_counts'] == second['handler_counts'],
            'handler counts changed inconsistently across rejection/release')


def _states(item, diagnostics):
    kind = item['kind']
    states = [x['state'] for x in diagnostics]
    require(all(type(s) is dict for s in states), 'typed readback states required')
    for value in diagnostics:
        expected = H1 if kind == 'history_write_rejected' or (kind == 'held_input' and value['stage'] == 'held_history') else item['selected_observation']
        require(value['selected_observation'] == expected, 'diagnostic selected observation')
    if kind == 'camera':
        for s in states:
            _keys(s, {'camera_id', 'view_target_id', 'rotation'}, 'camera state')
            require(type(s['camera_id']) is str and s['camera_id'] and s['camera_id'] == s['view_target_id'] and
                    type(s['rotation']) is list and len(s['rotation']) == 3 and
                    all(type(x) in (int, float) and math.isfinite(x) for x in s['rotation']), 'actual camera/view target readback')
        require(states[0]['camera_id'] == states[1]['camera_id'] == states[2]['camera_id'] and
                states[0]['rotation'] != states[1]['rotation'] and states[0] == states[2], 'camera move/restore')
    elif kind == 'visibility':
        for s in states:
            _keys(s, {'proxies'}, 'visibility state')
            require(type(s['proxies']) is dict and s['proxies'] and
                    all(type(k) is str and k and type(v) is bool for k, v in s['proxies'].items()), 'proxy visibility readback')
        require(states[0] == states[2] and set(states[0]['proxies']) == set(states[1]['proxies']) and
                all(v is False for v in states[0]['proxies'].values()) and
                all(v is True for v in states[1]['proxies'].values()), 'hidden/restored proxy identity')
    elif kind == 'framerate':
        for s in states:
            _keys(s, {'max_fps'}, 'FPS state')
            require(_seconds(s['max_fps']), 'FPS number')
        require(states[0] == states[2] and states[0] != states[1] and states[1]['max_fps'] == 30, 'FPS changed/restored')
    elif kind == 'pause':
        require(_same_json(states, [{'paused': False}, {'paused': True}, {'paused': False}]), 'actual pause/resume')
    elif kind == 'history_write_rejected':
        _history_rejection(states)
    elif kind == 'held_input':
        require(_same_json(states, [{'space_down': True, 'can_write': False},
                           {'space_down': True, 'can_write': True},
                           {'space_down': False, 'can_write': True}]), 'cross-view hold/release evidence')
    elif kind == 'probe':
        require(_same_json(states, [{'quit_guard_ready': True, 'preflush': True}]), 'quit guard readiness, not actual exit')
    elif kind == 'final':
        require(_same_json(states, [{'space_down': False, 'r_down': False, 'paused': False,
                            'visibility_restored': True, 'fps_restored': True}]), 'final actual restored readback')


RECEIPT_FIELDS = {'format', 'action_id', 'binding', 'trusted_head', 'selected_observation', 'clock',
                  'started_monotonic', 'completed_monotonic', 'before', 'after', 'log', 'trace_range',
                  'cua', 'checkpoints', 'image_checks'}


@_boundary
def validate_receipt(receipt, *, expected_binding, frames, expected_context):
    """Check one fixed action against indexed raw log, maps, CUA record and real trace.

    Called after native transport exit. Does not validate raw authority proofs or C image
    results semantically; R composes those independent checks before granting any gate.
    """
    _keys(receipt, RECEIPT_FIELDS, 'receipt')
    require(receipt['format'] == FORMAT, 'receipt version')
    _binding(receipt['binding'], expected_binding)
    item = _item_for(receipt['action_id'])
    require(item['session'] == expected_binding['session'], 'action/session')
    _head(receipt['trusted_head']); _head(receipt['selected_observation'])
    require(receipt['trusted_head'] == item['trusted_head'] and receipt['selected_observation'] == item['selected_observation'], 'separate trusted/selected head')
    _keys(receipt['clock'], {'id', 'anchor_monotonic', 'anchor_utc'}, 'clock')
    require(type(receipt['clock']['id']) is str and receipt['clock']['id'] and
            _seconds(receipt['clock']['anchor_monotonic']) and type(receipt['clock']['anchor_utc']) is str,
            'controller clock required')
    require(_utc(receipt['clock']['anchor_utc']), 'UTC anchor timezone')
    start, end = receipt['started_monotonic'], receipt['completed_monotonic']
    require(_seconds(start) and _seconds(end) and start <= end and end - start <= item['max_seconds'], 'action deadline')
    before = _map(receipt['before'], expected_binding['authority_root'])
    after = _map(receipt['after'], expected_binding['authority_root'])
    if item['kind'] in READONLY or item['kind'] in ('probe', 'native', 'final', 'exit', 'recover'):
        require(before == after, 'readonly authority changed')
    bounds = receipt['trace_range']
    require(type(bounds) is list and len(bounds) == 2 and all(_integer(i) for i in bounds) and
            bounds[0] <= bounds[1] <= len(frames), 'half-open trace frame range')
    selected = frames[bounds[0]:bounds[1]]
    _check_frames(item, selected, expected_binding, expected_context)
    raw, pin = _log(receipt)
    require(type(receipt['checkpoints']) is list and
            [x.get('stage') for x in receipt['checkpoints']] == item['stages'], 'complete ordered checkpoints')
    last_offset, last_time, diagnostics = pin['before_offset'], start, []
    for index, event in enumerate(receipt['checkpoints']):
        _keys(event, {'stage', 'log_start', 'log_end', 'monotonic', 'map', 'after_command'}, 'checkpoint')
        require(_integer(event['log_start']) and _integer(event['log_end']) and
                last_offset <= event['log_start'] < event['log_end'] <= pin['after_offset'], 'stale/overlapping completion marker')
        require(type(event['after_command']) is int and event['after_command'] == item['checkpoint_commands'][index],
                'checkpoint command association')
        require(_seconds(event['monotonic']) and last_time <= event['monotonic'] <= end, 'checkpoint time/order')
        files = _map(event['map'], expected_binding['authority_root'])
        if item['kind'] in READONLY:
            require(files == before, 'authority changed at subaction checkpoint')
        if item['kind'] in DIAGNOSTIC_KINDS:
            diagnostics.append(_diagnostic(raw, event, item, receipt))
        elif item['kind'] == 'native':
            name = 'ProtocolIds' if item['action_id'] == 's1.native_ids' else 'StandaloneAssetAudit'
            marker = ('Test Completed. Result={Success} Name={' + name + '} Path={edgeWorld.UniverseHost.' + name + '}').encode()
            require(marker in raw[event['log_start']:event['log_end']], 'native actual Success missing')
        elif item['kind'] == 'exit':
            require(b'LogExit: Preparing to exit.' in raw[event['log_start']:event['log_end']], 'quit intent log missing')
        else:
            head = item['observation_heads'][index]
            marker = ('Universe world %s observed tick %d, revision %d' %
                      (expected_binding['world_id'], head['tick'], head['revision'])).encode()
            require(marker in raw[event['log_start']:event['log_end']], 'fresh observed marker missing')
        last_offset, last_time = event['log_end'], event['monotonic']
    if diagnostics:
        _states(item, diagnostics)
    cua = _json(reference(receipt['cua']))
    _keys(cua, {'format', 'binding', 'action_id', 'clock', 'calls'}, 'CUA artifact')
    require(cua['format'] == 'universe-i13-cua.v1' and cua['action_id'] == item['action_id'] and
            cua['clock'] == receipt['clock'], 'CUA identity/clock')
    _binding(cua['binding'], expected_binding)
    require(type(cua['calls']) is list and len(cua['calls']) == len(item['commands']), 'CUA command coverage')
    last_call = start
    for call, command in zip(cua['calls'], item['commands']):
        _keys(call, {'command', 'started_monotonic', 'completed_monotonic', 'raw_tool_ref'}, 'CUA call')
        a, b = call['started_monotonic'], call['completed_monotonic']
        require(call['command'] == command['text'] and _seconds(a) and _seconds(b) and
                last_call <= a <= b <= end and b - a <= min(10, command['max_seconds']), 'CUA step order/deadline')
        require(reference(call['raw_tool_ref']), 'empty raw CUA tool evidence')
        last_call = b
    for event in receipt['checkpoints']:
        index = event['after_command']
        if index >= 0:
            require(event['monotonic'] >= cua['calls'][index]['completed_monotonic'], 'completion predates associated input')
        if index + 1 < len(cua['calls']):
            require(event['monotonic'] <= cua['calls'][index + 1]['started_monotonic'], 'next input preceded required readback')
    map_paths = [receipt['before']['path'], receipt['after']['path']] + [e['map']['path'] for e in receipt['checkpoints']]
    require(len(map_paths) == len(set(map_paths)), 'fresh separate map artifact for every capture required')
    require(type(receipt['image_checks']) is list, 'image check refs')
    if 'image_checks' in item['required_evidence']:
        require(len(receipt['image_checks']) >= len(item['stages']), 'per-stage image evidence missing')
    for ref in receipt['image_checks']:
        reference(ref)  # C/R validates actual image semantics; B never accepts a passed boolean.
    return {'action_id': item['action_id'], 'kind': item['kind'], 'trace_range': bounds,
            'status': 'consistent_requires_R_and_independent_review', 'g_b2_granted': False}


@_boundary
def validate_session(receipts, trace_refs, *, expected_binding, expected_context):
    """Exact complete order/coverage, no hidden frames, same closure retry, all nine pair kinds across sessions."""
    _keys(expected_context, {'principal', 'trust_anchor', 'expected_build', 'expected_options'}, 'public expected context')
    require(type(expected_context['principal']) is str and expected_context['principal'] and
            all(type(expected_context[k]) is str and SHA.fullmatch(expected_context[k])
                for k in ('trust_anchor', 'expected_build', 'expected_options')), 'public expected context fields')
    frames = load_trace(trace_refs, expected_binding=expected_binding)
    items = [x for x in manifest()['items'] if x['session'] == expected_binding['session']]
    require(type(receipts) is list and [r.get('action_id') for r in receipts] == [x['action_id'] for x in items], 'exact action order/coverage')
    require(len(frames) == manifest()['request_counts'][expected_binding['session']], 'session exact request count')
    cursor, previous_time, clock, checks, captured_maps = 0, -1, None, [], set()
    for receipt in receipts:
        require(receipt['trace_range'][0] == cursor, 'trace gap/reuse/out-of-order')
        require(receipt['started_monotonic'] >= previous_time, 'overlapping action intervals')
        if clock is None:
            clock = receipt['clock']
        require(receipt['clock'] == clock, 'different controller clock')
        paths = {receipt['before']['path'], receipt['after']['path']} | {e['map']['path'] for e in receipt['checkpoints']}
        require(not (paths & captured_maps), 'map capture reused across actions')
        captured_maps.update(paths)
        checks.append(validate_receipt(receipt, expected_binding=expected_binding,
                                       frames=frames, expected_context=expected_context))
        cursor, previous_time = receipt['trace_range'][1], receipt['completed_monotonic']
    require(cursor == len(frames), 'unclaimed extra trace requests')
    if expected_binding['session'] == 'initialize':
        physical = frames[9]  # init[0:4], retain[4:8], physical prepare8/advance9
        retry = frames[12]    # retry starts after physical[8:12]
        require(physical['request']['operation'] == retry['request']['operation'] == 'advance' and
                physical['request']['request_id'] != retry['request']['request_id'] and
                physical['request']['payload'] == retry['request']['payload'] and
                physical['response']['result']['payload'] == retry['response']['result']['payload'], 'same-closure retry/original result')
    return {'status': 'consistent_requires_R_and_independent_review', 'checks': checks,
            'request_count': len(frames), 'readonly_kinds': sorted({x['kind'] for x in checks} & READONLY),
            'g_b2_granted': False, 'runtime_authenticity_verified': False}


def schema():
    """JSON Schema 2020-12 receipt shape; cross-artifact semantics remain mandatory code checks."""
    def obj(properties):
        return {'type': 'object', 'required': sorted(properties), 'additionalProperties': False,
                'properties': properties}
    text = {'type': 'string', 'minLength': 1}
    number = {'type': 'number', 'minimum': 0}
    integer = {'type': 'integer', 'minimum': 0}
    ref = obj({'path': {'type': 'string', 'pattern': '^/'},
               'sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}})
    head = obj({k: {'type': 'integer', 'minimum': 0, 'maximum': 9007199254740991} for k in H0})
    binding = obj({**{k: deepcopy(text) for k in ('run_id', 'world_id', 'authority_root')},
                   'source_sha': {'type': 'string', 'pattern': '^[0-9a-f]{40}$'},
                   'session': {'enum': ['initialize', 'existing']},
                   **{k: {'type': 'integer', 'minimum': 1} for k in ('host_pid', 'worker_pid', 'generation')}})
    clock = obj({'id': text, 'anchor_monotonic': number,
                 'anchor_utc': {'type': 'string', 'format': 'date-time'}})
    checkpoint = obj({'stage': text, 'log_start': integer, 'log_end': integer,
                      'monotonic': number, 'map': {'$ref': '#/$defs/reference'},
                      'after_command': {'type': 'integer', 'minimum': -1}})
    receipt = obj({'format': {'const': FORMAT}, 'action_id': {'enum': [x['action_id'] for x in manifest()['items']]},
                   'binding': {'$ref': '#/$defs/binding'},
                   'trusted_head': {'$ref': '#/$defs/head'}, 'selected_observation': {'$ref': '#/$defs/head'},
                   'clock': {'$ref': '#/$defs/clock'}, 'started_monotonic': number, 'completed_monotonic': number,
                   'before': {'$ref': '#/$defs/reference'}, 'after': {'$ref': '#/$defs/reference'},
                   'log': obj({'ref': {'$ref': '#/$defs/reference'}, 'device': integer, 'inode': integer,
                               'before_offset': integer, 'after_offset': integer,
                               'prefix_sha256': {'type': 'string', 'pattern': '^[0-9a-f]{64}$'}}),
                   'trace_range': {'type': 'array', 'minItems': 2, 'maxItems': 2, 'items': integer},
                   'cua': {'$ref': '#/$defs/reference'},
                   'checkpoints': {'type': 'array', 'minItems': 1, 'items': checkpoint},
                   'image_checks': {'type': 'array', 'items': {'$ref': '#/$defs/reference'}}})
    readback = obj({'format': {'const': READBACK_FORMAT},
                    'binding': {'$ref': '#/$defs/binding'}, 'action_id': text,
                    'stage': text, 'trusted_head': {'$ref': '#/$defs/head'},
                    'selected_observation': {'$ref': '#/$defs/head'}, 'state': {'type': 'object'}})
    rejected_input = obj({'key': {'enum': ['Space', 'R']}, 'event': {'const': 'pressed'},
                          'handler': {'enum': ['SpacePressed', 'Retain']},
                          'handled': {'const': True}, 'rejected': {'const': True},
                          'reason': {'const': 'history_read_only'},
                          'counter_before': integer, 'counter_after': {'type': 'integer', 'minimum': 1}})
    rejection_state = obj({'format': {'const': HISTORY_REJECTION_FORMAT},
                           'space_down': {'const': False}, 'r_down': {'const': False},
                           'can_write': {'const': False},
                           'handled_input': {'anyOf': [{'type': 'null'}, {'$ref': '#/$defs/rejected_input'}]},
                           'handler_counts': obj({'SpacePressed': integer, 'Retain': integer})})
    readback['allOf'] = [{'if': {'properties': {'action_id': {'const': 's1.history_write_rejected'}}},
                          'then': {'properties': {'state': {'$ref': '#/$defs/history_rejection_state'}}}}]
    call = obj({'command': text, 'started_monotonic': number, 'completed_monotonic': number,
                'raw_tool_ref': {'$ref': '#/$defs/reference'}})
    cua = obj({'format': {'const': 'universe-i13-cua.v1'}, 'binding': {'$ref': '#/$defs/binding'},
               'action_id': text, 'clock': {'$ref': '#/$defs/clock'},
               'calls': {'type': 'array', 'items': call}})
    receipt.update({'$schema': 'https://json-schema.org/draft/2020-12/schema', 'title': FORMAT,
                    '$defs': {'reference': ref, 'head': head, 'binding': binding, 'clock': clock,
                              'readback': readback, 'cua': cua, 'rejected_input': rejected_input,
                              'history_rejection_state': rejection_state}})
    return deepcopy(receipt)


@_boundary
def action_advice(action_id, *, ui_allowed, quit_due, stop, remaining_seconds):
    """Pure caller guard adapter. A/R authenticates these values; B executes nothing."""
    require(all(type(v) is bool for v in (ui_allowed, quit_due, stop)) and
            _seconds(remaining_seconds), 'explicit lifecycle guard fields')
    item = _item_for(action_id)
    if stop or quit_due or not ui_allowed or remaining_seconds < item['max_seconds']:
        return {'decision': 'release_inputs_then_normal_quit', 'commands': [],
                'reason': 'guard denied or insufficient full-action allowance'}
    return {'decision': 'caller_may_execute_after_identity_check',
            'commands': deepcopy(item['commands']), 'max_tool_wait_seconds': min(10, remaining_seconds)}

# I14 is a separate contract. The I13 entrypoints/schema/caps above remain unchanged.
FORMAT_V2 = 'universe-i14-actions.v1'
READBACK_V2 = 'universe-i14-readback.v1'
CAMERA_TOLERANCE_DEG = 1e-4


def manifest_v2():
    value = manifest()
    value['format'] = FORMAT_V2
    for item in value['items']:
        name = item['action_id']
        kind = item['kind']
        if kind not in DIAGNOSTIC_KINDS:
            item['checkpoint_origins'] = [None] * len(item['stages'])
            continue
        arm, disarm = 'UniverseDiagArm ' + name, 'UniverseDiagDisarm'
        read = lambda stage: 'UniverseDiagReadback ' + name + ' ' + stage
        if kind == 'probe':
            commands = [arm, 'native Shot via C prepare', read('png_and_guard'), disarm]
            checkpoints = [2]
        elif kind == 'final':
            commands = [arm, read('released_and_restored'), disarm]
            checkpoints = [1]
        elif kind == 'held_input':
            commands = [arm, 'viewport chord Space+H durationMs=2000', disarm]
            checkpoints = [1, 1, 1]
        elif kind == 'history_write_rejected':
            commands = [arm, 'viewport Space press/release in history',
                        'viewport R press/release in history', read('released'), disarm]
            checkpoints = [1, 2, 3]
        else:
            changes = {'camera': ['UniverseCamera 15 0', 'UniverseCamera -15 0'],
                       'visibility': ['UniverseProjectionVisible false', 'UniverseProjectionVisible true'],
                       'framerate': ['t.MaxFPS 30', 't.MaxFPS <original>'],
                       'pause': ['pause', 'pause']}[kind]
            commands = [arm, changes[0], read(item['stages'][1]), changes[1], read('restored'), disarm]
            checkpoints = [0, 2, 4]
        item['commands'] = [_command(text, 10 if 'chord' in text else 2) for text in commands]
        item['checkpoint_commands'] = checkpoints
        item['checkpoint_origins'] = (['input', 'verified_observation', 'release'] if kind == 'held_input' else
                                      ['release', 'release', 'query'] if kind == 'history_write_rejected' else
                                      ['query'] * len(item['stages']))
        # Explicit extra query allowances; S2 retains its separately approved 100s proposal.
        if item['session'] == 'initialize':
            item['max_seconds'] += {'probe': 4, 'final': 4, 'camera': 8, 'visibility': 8,
                                    'framerate': 2, 'pause': 2, 'history_write_rejected': 6,
                                    'held_input': 0}[kind]
        remaining = item['max_seconds'] - sum(c['max_seconds'] for c in item['commands'])
        require(remaining > 0, 'v2 internal passive allowance')
        item['passive_costs'] = {'maps_seconds': remaining / 3, 'marker_seconds': remaining / 3,
                                  'image_restore_seconds': remaining / 3}
    # Stage images are real UI calls too, not hidden in passive waiting allowances.
    for item in value['items']:
        if 'image_checks' not in item['required_evidence']:
            continue
        if item['kind'] == 'probe':
            item['commands'][1]['text'] = 'native Shot via C prepare ' + item['action_id'] + '/png_and_guard'
            continue
        original = item['commands']
        mapping, expanded = {}, []
        for index, command in enumerate(original):
            mapping[index] = len(expanded)
            expanded.append(command)
            for stage, associated in zip(item['stages'], item['checkpoint_commands']):
                if associated == index:
                    expanded.append(_command('native Shot via C prepare ' + item['action_id'] + '/' + stage, 2))
        item['commands'] = expanded
        item['checkpoint_commands'] = [mapping[i] for i in item['checkpoint_commands']]
        remaining = item['max_seconds'] - sum(c['max_seconds'] for c in expanded)
        require(remaining > 0, 'v2 image call allowance')
        item['passive_costs'] = {'maps_seconds': remaining / 3, 'marker_seconds': remaining / 3,
                                  'image_restore_seconds': remaining / 3}
    value['interaction_caps'] = {s: sum(i['max_seconds'] for i in value['items']
                                       if i['session'] == s and i['phase'] == 'interaction')
                                 for s in ('initialize', 'existing')}
    value['session_interaction_limits'] = {'initialize': 360, 'existing': 100}
    require(all(value['interaction_caps'][s] <= limit for s, limit in value['session_interaction_limits'].items()),
            'v2 proposed manifest exceeds phase limit')
    value['checkpoint_time_semantics'] = 'controller read time only; raw UE event order is event_serial/log offsets'
    value['camera_tolerance_degrees'] = CAMERA_TOLERANCE_DEG
    return value


def _item_v2(action_id):
    found = [x for x in manifest_v2()['items'] if x['action_id'] == action_id]
    require(len(found) == 1, 'unknown v2 action')
    return found[0]


def _angular(a, b):
    return abs((a - b + 180) % 360 - 180)


def _camera_v2(diagnostics):
    states = [d['state'] for d in diagnostics]
    for state in states:
        _keys(state, {'camera_id', 'view_target_id', 'rotation'}, 'v2 camera state')
        require(type(state['camera_id']) is str and state['camera_id'] and
                state['camera_id'] == state['view_target_id'] and type(state['rotation']) is list and
                len(state['rotation']) == 3 and all(type(x) in (int, float) and math.isfinite(x)
                                                   for x in state['rotation']), 'actual v2 camera state')
    before, moved, restored = states
    require(before['camera_id'] == moved['camera_id'] == restored['camera_id'], 'same camera throughout')
    require(all(_angular(a, b) <= CAMERA_TOLERANCE_DEG for a, b in zip(before['rotation'], restored['rotation'])),
            'camera restore exceeds angular tolerance')
    delta = [_angular(a, b) for a, b in zip(before['rotation'], moved['rotation'])]
    require(delta[0] <= CAMERA_TOLERANCE_DEG and abs(delta[1] - 15) <= CAMERA_TOLERANCE_DEG and
            delta[2] <= CAMERA_TOLERANCE_DEG, 'camera must actually change yaw by 15 degrees')


def _diagnostic_v2(raw, event, item, receipt):
    line = raw[event['log_start']:event['log_end']]
    marker = b'EW_I13_READBACK '
    require(line.count(marker) == 1 and line.endswith(b'\n'), 'complete v2 readback line required')
    value = _json(line.split(marker, 1)[1].strip())
    _keys(value, {'format', 'binding', 'action_id', 'stage', 'trusted_head', 'selected_observation',
                  'state', 'event_serial', 'origin'}, 'v2 readback')
    require(value['format'] == READBACK_V2 and value['action_id'] == item['action_id'] and
            value['stage'] == event['stage'], 'v2 marker action/stage/version')
    _binding(value['binding'], receipt['binding'])
    _head(value['trusted_head']); _head(value['selected_observation'])
    require(value['trusted_head'] == item['trusted_head'] and _integer(value['event_serial'], 1) and
            value['event_serial'] == event['event_serial'], 'v2 marker binding/serial')
    return value


@_boundary
def validate_receipt_v2(receipt, *, expected_binding, frames, expected_context):
    """I14 event order is native serial/log offset; checkpoint time is controller observation only."""
    _keys(receipt, RECEIPT_FIELDS, 'v2 receipt')
    require(receipt['format'] == FORMAT_V2, 'v2 receipt format')
    _binding(receipt['binding'], expected_binding)
    item = _item_v2(receipt['action_id'])
    require(item['session'] == expected_binding['session'], 'v2 action/session')
    _head(receipt['trusted_head']); _head(receipt['selected_observation'])
    require(receipt['trusted_head'] == item['trusted_head'] and receipt['selected_observation'] == item['selected_observation'],
            'v2 distinct trusted/selected head')
    _keys(receipt['clock'], {'id', 'anchor_monotonic', 'anchor_utc'}, 'v2 clock')
    require(type(receipt['clock']['id']) is str and receipt['clock']['id'] and
            _seconds(receipt['clock']['anchor_monotonic']) and _utc(receipt['clock']['anchor_utc']), 'v2 controller clock')
    start, end = receipt['started_monotonic'], receipt['completed_monotonic']
    require(_seconds(start) and _seconds(end) and start <= end and end - start <= item['max_seconds'], 'v2 action cap')
    before = _map(receipt['before'], expected_binding['authority_root'])
    after = _map(receipt['after'], expected_binding['authority_root'])
    if item['kind'] in READONLY or item['kind'] in ('probe', 'native', 'final', 'exit', 'recover'):
        require(before == after, 'v2 readonly changed')
    first, last = receipt['trace_range']
    require(_integer(first) and _integer(last) and first <= last <= len(frames), 'v2 frame range')
    _check_frames(item, frames[first:last], expected_binding, expected_context)
    raw, pin = _log(receipt)
    cua = _json(reference(receipt['cua']))
    _keys(cua, {'format', 'binding', 'action_id', 'clock', 'calls'}, 'v2 CUA')
    require(cua['format'] == 'universe-i14-cua.v1' and cua['action_id'] == item['action_id'] and
            cua['clock'] == receipt['clock'], 'v2 CUA binding')
    _binding(cua['binding'], expected_binding)
    require(type(cua['calls']) is list and len(cua['calls']) == len(item['commands']), 'all v2 queries/calls required')
    call_end, log_end = start, pin['before_offset']
    for call, command in zip(cua['calls'], item['commands']):
        _keys(call, {'command', 'started_monotonic', 'completed_monotonic', 'raw_tool_ref',
                     'log_before_offset', 'log_after_offset'}, 'v2 CUA call')
        a, b = call['started_monotonic'], call['completed_monotonic']
        require(call['command'] == command['text'] and _seconds(a) and _seconds(b) and
                call_end <= a <= b <= end and b-a <= min(10, command['max_seconds']), 'v2 call order/deadline')
        require(_integer(call['log_before_offset']) and _integer(call['log_after_offset']) and
                log_end <= call['log_before_offset'] <= call['log_after_offset'] <= pin['after_offset'], 'v2 call log brackets')
        require(reference(call['raw_tool_ref']), 'actual raw CUA call evidence required')
        call_end, log_end = b, call['log_after_offset']
    events = receipt['checkpoints']
    require(type(events) is list and [e.get('stage') for e in events] == item['stages'], 'v2 complete stage order')
    last_read, last_offset, previous_serial, diagnostics = start, pin['before_offset'], 0, []
    for index, event in enumerate(events):
        _keys(event, {'stage', 'log_start', 'log_end', 'read_monotonic', 'map', 'command_index', 'event_serial'}, 'v2 checkpoint')
        require(_integer(event['log_start']) and _integer(event['log_end']) and
                last_offset <= event['log_start'] < event['log_end'] <= pin['after_offset'], 'v2 event raw log order')
        read_time = event['read_monotonic']
        require(_seconds(read_time) and last_read <= read_time <= end, 'v2 controller read order')
        require(type(event['command_index']) is int and event['command_index'] == item['checkpoint_commands'][index],
                'v2 event/call association')
        call_index = event['command_index']
        if call_index >= 0:
            call = cua['calls'][call_index]
            require(call['log_before_offset'] <= event['log_start'] < event['log_end'] <= call['log_after_offset'] and
                    read_time >= call['started_monotonic'], 'v2 event outside actual input/query bracket')
            # Long chord events may occur before call return. No UE/controller clock subtraction.
            if call_index+1 < len(cua['calls']):
                require(read_time <= cua['calls'][call_index+1]['started_monotonic'], 'required readback omitted before next call')
        files = _map(event['map'], expected_binding['authority_root'])
        if item['kind'] in READONLY:
            require(files == before, 'v2 readonly subaction changed')
        if item['kind'] in DIAGNOSTIC_KINDS:
            value = _diagnostic_v2(raw, event, item, receipt)
            require(value['origin'] == item['checkpoint_origins'][index] and value['event_serial'] > previous_serial,
                    'actual event origin/serial order')
            previous_serial = value['event_serial']; diagnostics.append(value)
        else:
            require(event['event_serial'] is None, 'ordinary log line has no diagnostic serial')
            line = raw[event['log_start']:event['log_end']]
            if item['kind'] == 'native':
                name = 'ProtocolIds' if item['action_id'] == 's1.native_ids' else 'StandaloneAssetAudit'
                marker = ('Test Completed. Result={Success} Name={' + name + '} Path={edgeWorld.UniverseHost.'+name+'}').encode()
            elif item['kind'] == 'exit':
                marker = b'LogExit: Preparing to exit.'
            else:
                head = item['observation_heads'][index]
                marker = ('Universe world %s observed tick %d, revision %d' %
                          (expected_binding['world_id'],head['tick'],head['revision'])).encode()
            require(marker in line, 'fresh actual v2 completion log missing')
        last_read, last_offset = read_time, event['log_end']
    if diagnostics:
        if item['kind'] == 'camera':
            require(all(d['selected_observation'] == item['selected_observation'] for d in diagnostics), 'v2 camera observation')
            _camera_v2(diagnostics)
        else:
            _states(item, diagnostics)
    paths = [receipt['before']['path'], receipt['after']['path']] + [e['map']['path'] for e in events]
    require(len(paths) == len(set(paths)), 'v2 fresh map capture required')
    images = receipt['image_checks']
    require(type(images) is list, 'v2 image checks')
    expected_stages = item['stages'] if 'image_checks' in item['required_evidence'] else []
    require([x.get('stage') for x in images] == expected_stages, 'v2 every image stage consumed exactly once')
    for image in images:
        _keys(image, {'capture_id', 'stage', 'capture_ref'}, 'v2 stage capture')
        require(image['capture_id'] == item['action_id']+'/'+image['stage'], 'v2 globally stable capture_id')
        reference(image['capture_ref'])  # V invokes C; no success inferred from arbitrary bytes.
    return {'action_id': item['action_id'], 'kind': item['kind'], 'trace_range': [first,last],
            'event_serials': [d['event_serial'] for d in diagnostics],
            'status': 'consistent_requires_R_and_independent_review', 'g_b2_granted': False}


@_boundary
def validate_session_v2(receipts, trace_refs, *, expected_binding, expected_context):
    _keys(expected_context, {'principal','trust_anchor','expected_build','expected_options'}, 'v2 context')
    require(type(expected_context['principal']) is str and expected_context['principal'] and
            all(type(expected_context[k]) is str and SHA.fullmatch(expected_context[k])
                for k in ('trust_anchor','expected_build','expected_options')), 'v2 public context fields')
    frames = load_trace(trace_refs, expected_binding=expected_binding)
    items = [x for x in manifest_v2()['items'] if x['session'] == expected_binding['session']]
    require(type(receipts) is list, 'v2 receipt array required')
    require([r['action_id'] for r in receipts] == [x['action_id'] for x in items], 'v2 exact manifest order')
    require(len(frames) == manifest_v2()['request_counts'][expected_binding['session']], 'v2 exact request count')
    cursor, time, clock, serial, map_paths, results = 0, -1, None, 0, set(), []
    for receipt in receipts:
        require(receipt['trace_range'][0] == cursor and receipt['started_monotonic'] >= time, 'v2 overlapping/gapped action')
        if clock is None: clock = receipt['clock']
        require(receipt['clock'] == clock, 'v2 one controller clock')
        result = validate_receipt_v2(receipt, expected_binding=expected_binding,frames=frames,expected_context=expected_context)
        for event_serial in result['event_serials']:
            require(event_serial == serial+1, 'v2 missing/replayed native event'); serial = event_serial
        paths = {receipt['before']['path'],receipt['after']['path']} | {e['map']['path'] for e in receipt['checkpoints']}
        require(not paths & map_paths, 'v2 reused map across actions'); map_paths.update(paths)
        cursor, time = receipt['trace_range'][1], receipt['completed_monotonic']; results.append(result)
    require(cursor == len(frames), 'v2 hidden trace frames')
    if expected_binding['session'] == 'initialize':
        original, retry = frames[9], frames[12]
        require(original['request']['request_id'] != retry['request']['request_id'] and
                original['request']['payload'] == retry['request']['payload'] and
                original['response']['result']['payload'] == retry['response']['result']['payload'], 'v2 exact retry closure/result')
    return {'status':'consistent_requires_R_and_independent_review','checks':results,'request_count':len(frames),
            'g_b2_granted':False,'runtime_authenticity_verified':False}


def schema_v2():
    value = schema()
    value['title'] = FORMAT_V2
    value['properties']['format'] = {'const':FORMAT_V2}
    event = value['properties']['checkpoints']['items']
    event['properties']['read_monotonic'] = event['properties'].pop('monotonic')
    event['properties']['command_index'] = event['properties'].pop('after_command')
    event['properties']['event_serial'] = {'type':['integer','null'],'minimum':1}
    event['required'] = sorted(event['properties'])
    value['properties']['image_checks']['items'] = {
        'type':'object','additionalProperties':False,'required':['capture_id','stage','capture_ref'],
        'properties':{'capture_id':{'type':'string'},'stage':{'type':'string'},'capture_ref':{'$ref':'#/$defs/reference'}}}
    readback = value['$defs']['readback']
    readback['properties']['format'] = {'const':READBACK_V2}
    readback['properties']['event_serial'] = {'type':'integer','minimum':1}
    readback['properties']['origin'] = {'enum':['query','input','verified_observation','release']}
    readback['required'] = sorted(readback['properties'])
    cua = value['$defs']['cua']
    cua['properties']['format'] = {'const':'universe-i14-cua.v1'}
    call = cua['properties']['calls']['items']
    for name in ('log_before_offset','log_after_offset'):call['properties'][name]={'type':'integer','minimum':0}
    call['required']=sorted(call['properties'])
    return value


@_boundary
def readiness_v2(capabilities, *, expected_source_sha):
    # Reuse capability origin/decision checks without silently substituting I13 timing caps.
    copied = deepcopy(capabilities)
    timing = copied.pop('timings',None)
    result = readiness(copied,expected_source_sha=expected_source_sha)
    if timing is not None:
        proof = _json(reference(timing))
        _keys(proof,{'format','source_sha','capability','reviewer','owner','decision','evidence_refs','action_upper_seconds'},'v2 timing review')
        require(proof['format']=='universe-i13-capability-review.v1' and proof['source_sha']==expected_source_sha and
                proof['capability']=='timings' and type(proof['reviewer']) is str and type(proof['owner']) is str and
                proof['reviewer'] and proof['owner'] and proof['reviewer']!=proof['owner'], 'v2 timing review origin fields')
        require(proof['decision'] in ('pass','fail','inconclusive') and proof['evidence_refs'], 'v2 timing review evidence')
        for ref in proof['evidence_refs']:reference(ref)
        expected={x['action_id']:x for x in manifest_v2()['items'] if x['phase']=='interaction'}
        require(set(proof['action_upper_seconds'])==set(expected), 'v2 timing coverage')
        reasons=[r for r in result['reasons'] if not r.startswith('timings:')]
        for name,upper in proof['action_upper_seconds'].items():
            if not _seconds(upper) or upper>expected[name]['max_seconds']:reasons.append(name+': no usable v2 timing bound')
        if proof['decision']!='pass':reasons.append('timings: '+proof['decision'])
        result['reasons']=reasons;result['status']='no_go' if reasons else 'ready_for_R_review'
    return result


@_boundary
def action_advice_v2(action_id, *, ui_allowed, quit_due, stop, remaining_seconds):
    require(all(type(x)is bool for x in (ui_allowed,quit_due,stop)) and _seconds(remaining_seconds), 'v2 guard')
    item=_item_v2(action_id)
    if stop or quit_due or not ui_allowed or remaining_seconds<item['max_seconds']:
        return {'decision':'release_inputs_then_normal_quit','commands':[],'reason':'guard denied or insufficient whole-action allowance'}
    return {'decision':'caller_may_execute_after_identity_check','commands':deepcopy(item['commands']),'max_tool_wait_seconds':min(10,remaining_seconds)}
