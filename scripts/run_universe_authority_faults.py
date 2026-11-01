#!/usr/bin/env python3
"""Independent, bounded POSIX-process acceptance of the neutral authority kernel.

Uses production APIs only in separately executed children. The parent reads raw
disk bytes with its own encoder and lineage checks. No solver or GPU is imported.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import errno
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import signal
import stat
import struct
import subprocess
import sys
import time
import traceback

BASE = '607e5500797854e5026d72e67ae8f45c70454a31'
REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / 'doc/fixtures/universe_authority_v0_1'
PREFIX = b'edgeworld.universe.authority\0v0.1\0'
WORLD = 'fixture-world'
PRINCIPAL = 'fixture-principal'
MAX_RAW = 64 * 1024 * 1024
PHASES = ('W0_LOCKED', 'W1_VALIDATED', 'W2_OBJECT_FILE_SYNCED',
          'W3_OBJECTS_DIR_SYNCED', 'W4_HEAD_FILE_SYNCED', 'W5_BEFORE_REPLACE',
          'W6_AFTER_REPLACE', 'W7_ROOT_SYNCED', 'W8_BEFORE_RESPONSE',
          'RECOVERY_VALIDATED', 'W9_RECOVERY_SYNCED')
SHAPES = {
    'proposal': ('principal output', {}),
    'intent': ('command_id principal expected_revision tick_delta transfer budget random_cursor', {}),
    'approval': ('principal receipt_id expires_revision', {'proposal': 'proposal', 'intent': 'intent'}),
    'command': ('', {'proposal': 'proposal', 'intent': 'intent', 'approval': 'approval'}),
    'candidate': ('adapter_kind test_profile value tick revision', {'command': 'command', 'prior_state': 'state'}),
    'admission': ('receipt_id principal evaluated_revision', {'command': 'command', 'candidate': 'candidate'}),
    'state': ('tick revision value budget random_cursor', {}),
    'event': ('event_id', {'state': 'state', 'admission': 'admission', 'prior_event': 'event'}),
    'result': ('command_id tick revision watermark', {'command': 'command', 'state': 'state',
               'event': 'event', 'checkpoint': 'candidate'}),
    'index': ('command_id fingerprint', {'result': 'result'}),
    'manifest': ('tick revision watermark', {'state': 'state', 'event': 'event',
                 'index': 'index', 'prior_manifest': 'manifest'}),
}


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=True, sort_keys=True, indent=2)


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result, 'duplicate decoded key'
        result[key] = value
    return result


def read_json(raw):
    def bad(token):
        raise AssertionError('non-integer JSON token: ' + token)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_float=bad, parse_constant=bad)


def quoted(value):
    out = bytearray(b'"')
    short = {8: b'\\b', 9: b'\\t', 10: b'\\n', 12: b'\\f', 13: b'\\r'}
    for ch in value:
        cp = ord(ch)
        assert not 0xD800 <= cp <= 0xDFFF
        if cp in short:
            out.extend(short[cp])
        elif cp in (34, 92):
            out.extend(bytes((92, cp)))
        elif 32 <= cp <= 126:
            out.append(cp)
        elif cp <= 0xFFFF:
            out.extend(('\\u%04x' % cp).encode())
        else:
            cp -= 0x10000
            out.extend(('\\u%04x\\u%04x' % (0xD800 + (cp >> 10),
                                             0xDC00 + (cp & 1023))).encode())
    out.append(34)
    return bytes(out)


def encode(value):
    """Independent ASCII JSON; no production codec or json.dumps canonical path."""
    if value is None:
        return b'null'
    if type(value) is bool:
        return b'true' if value else b'false'
    if type(value) is int:
        assert abs(value) <= 9007199254740991
        return str(value).encode()
    if type(value) is str:
        return quoted(value)
    if type(value) is list:
        return b'[' + b','.join(encode(x) for x in value) + b']'
    assert type(value) is dict and all(type(k) is str for k in value)
    return b'{' + b','.join(quoted(k) + b':' + encode(value[k])
                            for k in sorted(value)) + b'}'


def hashed(record):
    return hashlib.sha256(PREFIX + encode(record)).hexdigest()


def number(value):
    assert type(value) is dict and set(value) == {'$f64'}
    bits = value['$f64']
    assert type(bits) is str and len(bits) == 16 and set(bits) <= set('0123456789abcdef')
    result = struct.unpack('>d', bytes.fromhex(bits))[0]
    assert math.isfinite(result)
    return result


def file_map(root):
    """Original bytes, names and inode identity, excluding read-induced atime."""
    result = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        item = {'device': str(info.st_dev), 'inode': str(info.st_ino),
                'mode': info.st_mode, 'nlink': info.st_nlink}
        if stat.S_ISLNK(info.st_mode):
            item['symlink'] = os.readlink(path)
        elif stat.S_ISREG(info.st_mode):
            raw = path.read_bytes()
            item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), raw_hex=raw.hex())
        else:
            assert stat.S_ISDIR(info.st_mode), 'unexpected file type'
        result[str(path.relative_to(root))] = item
    return result


def golden_check():
    rows = read_json((FIXTURES / 'positive.json').read_bytes())['records']
    golden = read_json((FIXTURES / 'golden.json').read_bytes())
    assert len(rows) == len(golden) == 24
    for row, expected in zip(rows, golden):
        assert encode(row).hex() == expected['canonical_hex']
        assert hashed(row) == expected['sha256']
    return {'records': len(rows), 'method': 'independent recursive ASCII encoder'}


def observe_disk(root):
    """Independent complete reachable graph, authorization and state accounting."""
    identity = read_json((root / 'identity.json').read_bytes())
    info = root.stat()
    assert identity == {'domain': 'edgeworld.universe.authority', 'version': '0.1',
                        'world_id': WORLD, 'profile': 'local-posix-sync-v0.1',
                        'root_canonical': str(root.resolve()), 'root_device': str(info.st_dev),
                        'root_inode': str(info.st_ino)}
    head_raw = (root / 'HEAD.json').read_bytes()
    head = read_json(head_raw)
    assert head_raw == encode(head)
    assert set(head) == {'domain', 'version', 'world_id', 'profile', 'manifest'}
    assert head['domain'] == identity['domain'] and head['version'] == '0.1'
    assert head['world_id'] == WORLD and head['profile'] == identity['profile']
    records, active = {}, set()
    def visit(digest):
        assert type(digest) is str and len(digest) == 64 and set(digest) <= set('0123456789abcdef')
        assert digest not in active
        if digest in records:
            return
        assert len(records) + len(active) < 256
        active.add(digest)
        path = root / 'objects' / (digest + '.json')
        info = path.lstat()
        assert stat.S_ISREG(info.st_mode) and info.st_nlink == 1
        raw = path.read_bytes()
        assert len(raw) <= 1048576
        row = read_json(raw)
        assert set(row) == {'domain', 'version', 'world_id', 'kind', 'id', 'body', 'refs'}
        assert row['domain'] == identity['domain'] and row['version'] == '0.1' and row['world_id'] == WORLD
        assert type(row['kind']) is str and row['kind'] in SHAPES
        assert type(row['id']) is str and re.fullmatch('[a-z][a-z0-9._-]{0,63}', row['id'])
        fields, refs = SHAPES[row['kind']]
        assert type(row['body']) is dict and set(row['body']) == set(fields.split())
        assert type(row['refs']) is dict
        expected_refs = dict(refs)
        if row['kind'] == 'manifest' and row['body']['revision'] == 0:
            expected_refs = {'state': 'state'}
        if row['kind'] == 'event' and 'prior_event' not in row['refs']:
            del expected_refs['prior_event']
        assert set(row['refs']) == set(expected_refs)
        assert raw == encode(row) and hashed(row) == digest
        for name, target in row['refs'].items():
            visit(target)
            assert records[target]['kind'] == expected_refs[name]
        active.remove(digest)
        records[digest] = row
    visit(head['manifest'])
    assert sum(len(encode(r)) for r in records.values()) <= 1048576
    anchors = read_json((FIXTURES / 'trusted_receipts.json').read_bytes())
    ids, event_ids = set(), set()
    def ref(row, name, kind):
        target = records[row['refs'][name]]
        assert target['kind'] == kind
        return target
    for row in records.values():
        key = row['kind'], row['id']
        assert key not in ids
        ids.add(key)
        b, kind = row['body'], row['kind']
        for field in ('tick', 'revision', 'watermark', 'expected_revision', 'tick_delta',
                      'budget', 'random_cursor', 'expires_revision', 'evaluated_revision'):
            if field in b:
                assert type(b[field]) is int and 0 <= b[field] <= 9007199254740991
        if kind == 'approval':
            intent, proposal = ref(row, 'intent', 'intent'), ref(row, 'proposal', 'proposal')
            expected = {'kind': kind, 'principal': b['principal'], **row['refs'],
                        'expires_revision': b['expires_revision']}
            assert encode(anchors[b['receipt_id']]) == encode(expected)
            assert b['principal'] == intent['body']['principal'] == proposal['body']['principal']
        elif kind == 'command':
            approval = ref(row, 'approval', 'approval')
            assert approval['refs'] == {k: row['refs'][k] for k in ('intent', 'proposal')}
        elif kind == 'candidate':
            intent = ref(ref(row, 'command', 'command'), 'intent', 'intent')['body']
            prior = ref(row, 'prior_state', 'state')['body']
            assert b['adapter_kind'] == 'fake' and b['test_profile'] == 'neutral-transfer-v0.1'
            assert intent['expected_revision'] == prior['revision']
            assert b['revision'] == prior['revision'] + 1
            assert b['tick'] == prior['tick'] + intent['tick_delta']
            value = number(prior['value']) + number(intent['transfer'])
            assert math.isfinite(value) and b['value']['$f64'] == struct.pack('>d', value).hex()
        elif kind == 'admission':
            command, candidate = ref(row, 'command', 'command'), ref(row, 'candidate', 'candidate')
            intent = ref(command, 'intent', 'intent')['body']
            expected = {'kind': kind, 'principal': b['principal'], **row['refs'],
                        'evaluated_revision': b['evaluated_revision']}
            assert encode(anchors[b['receipt_id']]) == encode(expected)
            assert candidate['refs']['command'] == row['refs']['command']
            assert b['principal'] == intent['principal']
            assert b['evaluated_revision'] == intent['expected_revision']
            assert b['evaluated_revision'] <= ref(command, 'approval', 'approval')['body']['expires_revision']
        elif kind == 'event':
            assert b['event_id'] not in event_ids
            event_ids.add(b['event_id'])
            state = ref(row, 'state', 'state')['body']
            admission = ref(row, 'admission', 'admission')
            candidate = ref(admission, 'candidate', 'candidate')
            prior = ref(candidate, 'prior_state', 'state')['body']
            intent = ref(ref(admission, 'command', 'command'), 'intent', 'intent')['body']
            assert all(state[k] == candidate['body'][k] for k in ('tick', 'revision', 'value'))
            assert state['budget'] == prior['budget'] - intent['budget']
            assert intent['random_cursor'] == prior['random_cursor']
            assert state['random_cursor'] == prior['random_cursor'] + 1
            assert (state['revision'] == 1) == ('prior_event' not in row['refs'])
            if state['revision'] > 1:
                assert ref(row, 'prior_event', 'event')['refs']['state'] == candidate['refs']['prior_state']
        elif kind == 'result':
            event, state = ref(row, 'event', 'event'), ref(row, 'state', 'state')
            command = ref(row, 'command', 'command')
            admission = ref(event, 'admission', 'admission')
            assert event['refs']['state'] == row['refs']['state']
            assert admission['refs']['command'] == row['refs']['command']
            assert admission['refs']['candidate'] == row['refs']['checkpoint']
            assert b['command_id'] == ref(command, 'intent', 'intent')['body']['command_id']
            assert b == {'command_id': b['command_id'], 'tick': state['body']['tick'],
                         'revision': state['body']['revision'], 'watermark': state['body']['revision']}
        elif kind == 'index':
            result = ref(row, 'result', 'result')
            assert b == {'command_id': result['body']['command_id'], 'fingerprint': result['refs']['command']}
    history, current, committed = [], head['manifest'], {}
    while current:
        assert current not in [x['manifest'] for x in history]
        row = records[current]
        assert row['kind'] == 'manifest'
        state = ref(row, 'state', 'state')
        b, s = row['body'], state['body']
        assert b == {'tick': s['tick'], 'revision': s['revision'], 'watermark': s['revision']}
        if s['revision'] == 0:
            assert row['refs'] == {'state': row['refs']['state']}
            assert s == {'tick': 0, 'revision': 0, 'value': {'$f64': '0000000000000000'},
                         'budget': 8, 'random_cursor': 0}
        else:
            previous = ref(row, 'prior_manifest', 'manifest')
            event, index = ref(row, 'event', 'event'), ref(row, 'index', 'index')
            result = ref(index, 'result', 'result')
            candidate = ref(result, 'checkpoint', 'candidate')
            assert s['revision'] == previous['body']['revision'] + 1
            assert candidate['refs']['prior_state'] == previous['refs']['state']
            assert event['refs'].get('prior_event') == previous['refs'].get('event')
            assert event['refs']['state'] == row['refs']['state'] == result['refs']['state']
            assert result['refs']['event'] == row['refs']['event']
            principal = ref(ref(result, 'command', 'command'), 'intent', 'intent')['body']['principal']
            key = principal + '/' + result['body']['command_id']
            assert key not in committed
            committed[key] = index['refs']['result']
        history.append({'manifest': current, 'state': deepcopy(s)})
        current = row['refs'].get('prior_manifest')
    assert [x['state']['revision'] for x in history] == list(range(len(history) - 1, -1, -1))
    return {'head': head['manifest'], 'history': history, 'commands': committed,
            'record_hashes': sorted(records), 'head_raw_hex': head_raw.hex()}


def emit(value):
    print(json.dumps({'pid': os.getpid(), **value}, sort_keys=True), flush=True)


def child(args):
    """Public production API caller, isolated from the independent parent audit."""
    from unittest import mock
    from engine.universe_authority.admission import FixtureTrust
    from engine.universe_authority.codec import ContractError, digest
    from engine.universe_authority.commands import execute
    import engine.universe_authority.commands as commands_module
    from engine.universe_authority.ownership import acquire
    from engine.universe_authority.recovery import recover, status, observe
    from engine.universe_authority.store import Store

    rows = read_json((FIXTURES / 'positive.json').read_bytes())['records']
    by_id = {r['id']: r for r in rows}
    anchors = read_json((FIXTURES / 'trusted_receipts.json').read_bytes())
    armed = args.action in ('recoverkill', 'recover_sync_fail')
    sync_armed = False
    counters = {'solve': 0, 'approval': 0, 'admission': 0}
    root, store, lease = Path(args.root), None, None
    original_candidate = commands_module.neutral_candidate
    def counted(*a, **kw):
        counters['solve'] += 1
        return original_candidate(*a, **kw)
    commands_module.neutral_candidate = counted
    base_trust = FixtureTrust(anchors)
    class Trust:
        def authorize_read(self, *a):
            return base_trust.authorize_read(*a)
        def verify_approval(self, *a):
            counters['approval'] += 1
            return base_trust.verify_approval(*a)
        def admit(self, *a, **kw):
            counters['admission'] += 1
            return base_trust.admit(*a, **kw)
    trust = Trust()
    def hook(phase, context):
        nonlocal sync_armed
        emit({'type': 'phase', 'phase': phase, 'armed': armed, 'context': dict(context)})
        if args.action == 'recover_sync_fail' and phase == 'RECOVERY_VALIDATED':
            sync_armed = True
        if args.action == 'post_sync_fail' and armed and phase == 'W6_AFTER_REPLACE':
            sync_armed = True
        if armed and phase == args.phase:
            if phase == 'W2_OBJECT_FILE_SYNCED' and context['object_digest'] in (
                    hashed(by_id['s0']), hashed(by_id['m0'])):
                return
            emit({'type': 'pause', 'phase': phase, 'context': dict(context)})
            sys.stdin.buffer.read(1)
    def command(step):
        selected = [deepcopy(by_id[f'{k}{step}']) for k in ('p', 'i', 'a', 'c')]
        return execute(store, selected, command_digest=digest(selected[-1]), principal=PRINCIPAL,
                       verifier=trust, candidate_id=f'q{step}', admission_id=f'ad{step}',
                       state_id=f's{step}', event_id=f'event-{step}', result_id=f'r{step}',
                       index_id=f'x{step}', manifest_id=f'm{step}')
    original_sync = os.fsync
    def fail_sync(fd):
        is_dir = stat.S_ISDIR(os.fstat(fd).st_mode)
        eligible = (args.action in ('file_sync_fail', 'dir_sync_fail') and armed
                    and is_dir == (args.action == 'dir_sync_fail')) or sync_armed
        emit({'type': 'fsync', 'directory': is_dir, 'inode': str(os.fstat(fd).st_ino),
              'injected_error': bool(eligible)})
        if eligible:
            raise OSError(errno.EIO, 'I6 bounded injected fsync failure')
        return original_sync(fd)
    try:
        lease = acquire(root, WORLD, initialize=args.action == 'seed')
        if args.action == 'try_lock':
            emit({'type': 'terminal', 'code': 'ACQUIRED'})
            return
        store = Store(lease, trusted_receipts=anchors, fault=hook)
        with mock.patch('os.fsync', side_effect=fail_sync):
            if args.action == 'seed':
                store.initialize(rows[:2], digest(by_id['m0']))
            else:
                report = recover(store)
                emit({'type': 'recovered', 'confirmed': report.confirmed,
                      'storage_state': report.storage_state, 'status': status(report.snapshot)})
            if args.action == 'hold':
                emit({'type': 'pause', 'phase': 'LEASE_HELD'})
                sys.stdin.buffer.read(1)
            elif args.action in ('advance1', 'advance2', 'replace_fail', 'file_sync_fail',
                                 'dir_sync_fail', 'post_sync_fail'):
                armed = True
                if args.action == 'replace_fail':
                    with mock.patch('os.replace', side_effect=OSError(errno.EIO, 'I6 replace failure')):
                        command(1)
                else:
                    command(2 if args.action == 'advance2' else 1)
            elif args.action == 'converge':
                armed = True
                for step in (1, 2):
                    first = command(step)
                    before = file_map(root)
                    repeated = command(step)
                    assert first == repeated and before == file_map(root)
                    emit({'type': 'retry', 'step': step, 'manifest': first.manifest,
                          'unchanged': True, 'counters': dict(counters)})
            elif args.action in ('inspect', 'recover_sync_fail'):
                before = file_map(root)
                snapshot = store.snapshot()
                current = status(snapshot)
                outputs = [observe(snapshot, tick=0, revision=r, watermark=r)
                           for r in range(current['revision'] + 1)]
                for query, expected in ((dict(tick=0, revision=0, watermark=1), 'WATERMARK'),
                                        (dict(tick=1, revision=0, watermark=0), 'NOT_FOUND')):
                    try:
                        observe(snapshot, **query)
                    except ContractError as exc:
                        assert exc.code == expected
                    else:
                        raise AssertionError('invalid observation accepted')
                if args.action == 'recover_sync_fail':
                    try:
                        command(1)
                    except ContractError as exc:
                        assert exc.code == 'NOT_READY'
                    else:
                        raise AssertionError('unconfirmed retry pretended success')
                assert before == file_map(root)
                emit({'type': 'observations', 'status': current, 'history': outputs,
                      'unchanged': True, 'unconfirmed_write_rejected': args.action == 'recover_sync_fail'})
            emit({'type': 'terminal', 'code': 'OK', 'storage_state': store.state,
                  'status': status(store.snapshot()), 'counters': counters})
    except ContractError as exc:
        payload = {'type': 'terminal', 'code': exc.code,
                   'commit_status': getattr(exc, 'commit_status', 'not_attempted'),
                   'phase': getattr(exc, 'phase', None), 'storage_state': store.state if store else None}
        if store:
            try:
                payload['unexpected_snapshot'] = status(store.snapshot())
            except ContractError as view_error:
                payload['snapshot_error'] = view_error.code
        emit(payload)
    finally:
        if store:
            store.close()
        if lease:
            lease.close()


class Child:
    def __init__(self, suite, directory, root, action, phase=''):
        self.suite, self.directory, self.root = suite, directory, root
        directory.mkdir()
        self.command = [sys.executable, '-m', 'scripts.run_universe_authority_faults',
                        '--child', '--root', str(root), '--action', action, '--phase', phase]
        self.started = time.monotonic()
        self.process = subprocess.Popen(self.command, cwd=REPO, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.logs = {'out': (directory / 'stdout.jsonl').open('xb'),
                     'err': (directory / 'stderr.txt').open('xb')}
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ, 'out')
        self.selector.register(self.process.stderr, selectors.EVENT_READ, 'err')
        self.pending = b''
        self.packets, self.paused, self.finished = [], None, False
        self.killed = False
        self.cleanup_kill = False
        suite.children.append(self)
        save(directory / 'command.json', {'argv': self.command, 'cwd': str(REPO),
             'pid': self.process.pid, 'monotonic_start': self.started, 'source_head': suite.source})

    def pump(self, cleanup=False):
        wait = 0.02 if cleanup else min(0.05, self.suite.remaining())
        for key, _ in self.selector.select(wait):
            block = os.read(key.fileobj.fileno(), 65536)
            if not block:
                self.selector.unregister(key.fileobj)
                continue
            self.logs[key.data].write(block)
            self.logs[key.data].flush()
            if key.data == 'out':
                self.pending += block
                while b'\n' in self.pending:
                    raw, self.pending = self.pending.split(b'\n', 1)
                    packet = json.loads(raw)
                    assert packet['pid'] == self.process.pid
                    self.packets.append(packet)
                    if packet.get('type') == 'pause':
                        self.paused = packet

    def wait_pause(self, phase):
        until = time.monotonic() + min(8, self.suite.remaining())
        while self.paused is None:
            assert time.monotonic() < until, 'child pause timeout'
            self.pump()
            assert self.process.poll() is None, 'child exited before phase handshake'
        assert self.paused['phase'] == phase and self.process.poll() is None
        save(self.directory / 'phase-file-map.json', file_map(self.root))
        return self.paused

    def kill(self):
        assert self.paused and self.paused['pid'] == self.process.pid
        assert self.process.poll() is None
        # Popen retains ownership of this unreaped PID; never locate/kill globally.
        os.kill(self.process.pid, signal.SIGKILL)
        self.killed = True

    def abort(self):
        if self.process.poll() is None:
            os.kill(self.process.pid, signal.SIGKILL)
            self.cleanup_kill = True

    def finish(self, allow_failure=False):
        if self.finished:
            return self.packets[-1] if self.packets else None
        cleanup_errors = []
        try:
            # Cleanup has its own short budget even after the run deadline.
            until = time.monotonic() + (2 if allow_failure else min(8, self.suite.remaining()))
            while self.selector.get_map() or self.process.poll() is None:
                assert time.monotonic() < until, 'child completion timeout'
                self.pump(cleanup=allow_failure)
            code = self.process.wait(timeout=1)
            assert not self.pending, 'truncated JSONL line'
            if not allow_failure:
                assert code == (-signal.SIGKILL if self.killed or self.cleanup_kill else 0), ('child exit', code)
                assert not self.logs['err'].tell(), 'child stderr contains failure'
            return self.packets[-1] if self.packets else None
        finally:
            if self.process.poll() is None:
                try:
                    os.kill(self.process.pid, signal.SIGKILL)
                    self.cleanup_kill = True
                    self.process.wait(timeout=1)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    cleanup_errors.append(repr(exc))
            for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
                try:
                    pipe.close()
                except OSError as exc:
                    cleanup_errors.append(repr(exc))
            try:
                self.selector.close()
            except OSError as exc:
                cleanup_errors.append(repr(exc))
            for stream in self.logs.values():
                try:
                    stream.close()
                except OSError as exc:
                    cleanup_errors.append(repr(exc))
            self.finished = True
            self.suite.cleanup_errors.extend(cleanup_errors)
            save(self.directory / 'exit.json', {'pid': self.process.pid,
                 'returncode': self.process.returncode, 'real_sigkill': self.killed,
                 'cleanup_kill': self.cleanup_kill,
                 'cleanup_errors': cleanup_errors,
                 'elapsed_seconds': time.monotonic() - self.started})


class Suite:
    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=False)
        self.deadline = time.monotonic() + 110
        self.children, self.results, self.cleanup_errors = [], [], []
        self.source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=REPO, text=True).strip()
        self.inputs = self.hash_inputs()
        save(self.output / 'inputs-before.json', self.inputs)
        save(self.output / 'environment.json', {'python': sys.version, 'platform': sys.platform,
             'os_release': os.uname().release, 'machine': os.uname().machine,
             'source_head': self.source, 'implementation_base': BASE, 'argv': sys.argv,
             'budget_seconds': 120, 'internal_deadline_seconds': 110, 'raw_limit_bytes': MAX_RAW})

    def remaining(self):
        value = self.deadline - time.monotonic()
        assert value > 0, 'global 110-second deadline'
        return value

    def hash_inputs(self):
        paths = [*sorted((REPO / 'engine/universe_authority').glob('*.py')),
                 *sorted(FIXTURES.glob('*')), Path(__file__),
                 REPO / 'doc/contracts/universe_authority_v0_1.md',
                 REPO / 'tests/test_universe_process_faults.py']
        return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in paths if p.is_file()}

    def call(self, directory, root, action, phase=''):
        worker = Child(self, directory, root, action, phase)
        return worker, worker.finish()

    def seed(self, case, revision=0):
        root = case / 'authority'
        _, terminal = self.call(case / 'seed', root, 'seed')
        assert terminal['code'] == 'OK'
        if revision:
            _, terminal = self.call(case / 'populate', root, 'converge')
            assert terminal['code'] == 'OK'
        return root

    def check_state(self, root, revision):
        observation = observe_disk(root)
        state = observation['history'][0]['state']
        assert (state['tick'], state['revision'], state['budget'], state['random_cursor']) == (0, revision, 8-revision, revision)
        assert number(state['value']) == float(revision)
        return observation

    def inspected(self, case, root, label='fresh-recovery'):
        before = file_map(root)
        worker, terminal = self.call(case / label, root, 'inspect')
        assert terminal['code'] == 'OK' and terminal['storage_state'] == 'ready'
        assert before == file_map(root), 'recovery/observe changed bytes or inode'
        assert any(p.get('type') == 'observations' and p['unchanged'] for p in worker.packets)
        return terminal

    def converge(self, case, root, recovered_revision):
        _, terminal = self.call(case / 'retry-to-two', root, 'converge')
        assert terminal['code'] == 'OK'
        assert terminal['counters'] == {'solve': 2-recovered_revision,
                                        'approval': 2-recovered_revision, 'admission': 2-recovered_revision}
        return self.check_state(root, 2)

    def case(self, name, function):
        directory = self.output / name
        directory.mkdir()
        start = time.monotonic()
        child_start = len(self.children)
        try:
            detail = function(directory)
            self.results.append({'case': name, 'status': 'pass', 'detail': detail,
                                 'seconds': time.monotonic()-start})
        except Exception as exc:
            with (directory / 'failure.txt').open('x') as stream:
                traceback.print_exc(file=stream)
            self.results.append({'case': name, 'status': 'fail', 'error': str(exc),
                                 'seconds': time.monotonic()-start})
            for worker in self.children[child_start:]:
                if not worker.finished:
                    try:
                        worker.abort()
                        worker.finish(allow_failure=True)
                    except Exception as cleanup_error:
                        self.cleanup_errors.append(repr(cleanup_error))
        save(directory / 'result.json', self.results[-1])
        self.remaining()
        assert sum(p.stat().st_size for p in self.output.rglob('*') if p.is_file()) < MAX_RAW

    def kill_case(self, case, phase):
        recovery = phase in ('RECOVERY_VALIDATED', 'W9_RECOVERY_SYNCED')
        root = self.seed(case, 2 if recovery else 0)
        before = self.check_state(root, 2 if recovery else 0)
        save(case / 'before.json', {'observation': before, 'files': file_map(root)})
        worker = Child(self, case / 'killed-child', root, 'recoverkill' if recovery else 'advance1', phase)
        marker = worker.wait_pause(phase)
        worker.kill()
        worker.finish()
        expected = 2 if recovery else (1 if phase in PHASES[6:9] else 0)
        after = self.check_state(root, expected)
        save(case / 'after-kill.json', {'observation': after, 'files': file_map(root)})
        self.inspected(case, root)
        final = self.converge(case, root, expected)
        return {'phase': phase, 'real_sigkill_pid': worker.process.pid,
                'visibility_attempted': marker.get('context', {}).get('visibility_attempted'),
                'recovered_revision': expected, 'final': final}

    def io_case(self, case, action):
        root = self.seed(case)
        before = self.check_state(root, 0)
        worker, terminal = self.call(case / 'fault-child', root, action)
        post = action in ('replace_fail', 'post_sync_fail')
        assert terminal['code'] == ('COMMIT_UNKNOWN' if post else 'SYNC_UNSUPPORTED')
        assert terminal['commit_status'] == ('unknown' if post else 'not_attempted')
        assert terminal['storage_state'] == 'recovering' and terminal['snapshot_error'] == 'NOT_READY'
        expected = 1 if action == 'post_sync_fail' else 0
        after = self.check_state(root, expected)
        if action != 'replace_fail':
            assert any(p.get('type') == 'fsync' and p['injected_error'] for p in worker.packets)
        self.inspected(case, root)
        final = self.converge(case, root, expected)
        return {'before': before, 'after': after, 'terminal': terminal, 'final': final}

    def locks(self, case):
        root = self.seed(case)
        inode = (root / '.authority.lock').stat().st_ino
        holder = Child(self, case / 'holder', root, 'hold')
        holder.wait_pause('LEASE_HELD')
        before = file_map(root)
        alias = case / 'alias'
        alias.symlink_to(root, target_is_directory=True)
        competitors = []
        for label, path in (('direct', root), ('alias', alias)):
            worker, terminal = self.call(case / label, path, 'try_lock')
            assert terminal['code'] == 'LOCKED' and worker.process.pid != holder.process.pid
            competitors.append({'pid': worker.process.pid, 'terminal': terminal})
        assert file_map(root) == before
        holder.kill()
        holder.finish()
        self.inspected(case, root)
        assert (root / '.authority.lock').stat().st_ino == inode
        return {'holder_pid': holder.process.pid, 'competitors': competitors,
                'stable_lock_inode': str(inode), 'release_after_sigkill': True}

    def corruption(self, case, identifier, missing):
        root = self.seed(case, 2)
        self.check_state(root, 2)
        rows = read_json((FIXTURES / 'positive.json').read_bytes())['records']
        target = next(r for r in rows if r['id'] == identifier)
        path = root / 'objects' / (hashed(target) + '.json')
        save(case / 'original-files.json', file_map(root))
        if missing:
            path.unlink()
        else:
            raw = path.read_bytes()
            path.write_bytes(raw[:-1] + b'!')
        before = file_map(root)
        save(case / 'damaged-files.json', before)
        try:
            observe_disk(root)
        except (AssertionError, KeyError, ValueError, OSError):
            pass
        else:
            raise AssertionError('independent observer accepted broken historical closure')
        _, terminal = self.call(case / 'refuse', root, 'inspect')
        assert terminal['code'] == 'CORRUPT' and terminal['storage_state'] == 'corrupt'
        assert terminal['snapshot_error'] == 'NOT_READY'
        assert before == file_map(root)
        return {'target_id': identifier, 'missing': missing, 'terminal': terminal, 'no_fallback_or_writes': True}

    def readonly(self, case):
        root = self.seed(case, 2)
        self.check_state(root, 2)
        before = file_map(root)
        worker, terminal = self.call(case / 'unconfirmed', root, 'recover_sync_fail')
        assert terminal['code'] == 'OK' and terminal['storage_state'] == 'unconfirmed_readonly'
        outputs = next(p for p in worker.packets if p['type'] == 'observations')
        assert outputs['unconfirmed_write_rejected'] and len(outputs['history']) == 3
        assert all(o['storage_state'] == 'unconfirmed_readonly' for o in outputs['history'])
        assert before == file_map(root)
        save(case / 'readonly-map.json', before)
        self.inspected(case, root)
        return {'unconfirmed_then_confirmed': True, 'terminal': terminal}

    def segmented(self, case):
        continuous = self.seed(case)
        first = self.converge(case, continuous, 0)
        second_dir = case / 'segmented'
        second_dir.mkdir()
        segmented = self.seed(second_dir)
        for step in (1, 2):
            _, terminal = self.call(second_dir / f'step-{step}', segmented, f'advance{step}')
            assert terminal['code'] == 'OK'
            self.inspected(second_dir, segmented, f'restart-{step}')
        second = self.check_state(segmented, 2)
        assert first == second
        self.inspected(case, continuous, 'continuous-readonly')
        save(case / 'continuous-files.json', file_map(continuous))
        save(case / 'segmented-files.json', file_map(segmented))
        return {'same_logical_objects_and_head': True, 'observation': first,
                'identity_registration_paths_distinct': True,
                'scope': 'root-scoped neutral fixture; no autonomous clock or multi-root runtime claim'}

    def run(self):
        try:
            goldens = golden_check()
            for phase in PHASES:
                self.case('kill-' + phase.lower(), lambda case, p=phase: self.kill_case(case, p))
            for action in ('replace_fail', 'file_sync_fail', 'dir_sync_fail', 'post_sync_fail'):
                self.case(action, lambda case, a=action: self.io_case(case, a))
            self.case('two-writers-alias-and-release', self.locks)
            self.case('old-state-corruption', lambda case: self.corruption(case, 's0', False))
            self.case('historical-checkpoint-missing', lambda case: self.corruption(case, 'q1', True))
            self.case('unconfirmed-readonly', self.readonly)
            self.case('continuous-segmented-equivalence', self.segmented)
            after = self.hash_inputs()
            save(self.output / 'inputs-after.json', after)
            assert after == self.inputs, 'source/fixture changed during check'
            summary = {'source_head': self.source, 'implementation_base': BASE,
                       'golden_check': goldens, 'cases': self.results,
                       'passed': len(self.results) == 20 and all(r['status'] == 'pass' for r in self.results)
                                 and not self.cleanup_errors and all(c.process.poll() is not None for c in self.children),
                       'real_sigkill_cases': sum(c.killed for c in self.children),
                       'children': len(self.children), 'inputs_unchanged': True,
                       'all_children_reaped': all(c.process.poll() is not None for c in self.children),
                       'cleanup_errors': self.cleanup_errors,
                       'seconds_remaining': self.remaining(),
                       'limits': 'local POSIX process/fault evidence only; no power-loss, GPU, Genesis or UE proof'}
            save(self.output / 'summary.json', summary)
            return summary
        finally:
            for worker in self.children:
                if not worker.finished:
                    try:
                        worker.abort()
                        worker.finish(allow_failure=True)
                    except Exception as cleanup_error:
                        self.cleanup_errors.append(repr(cleanup_error))


def run_suite(output):
    suite = None
    try:
        suite = Suite(output)
        return suite.run()
    except BaseException as exc:
        if Path(output).is_dir():
            save(Path(output) / 'failed-run.json', {'passed': False, 'error': repr(exc),
                 'traceback': traceback.format_exc(), 'cases': suite.results if suite else [],
                 'cleanup_errors': suite.cleanup_errors if suite else []})
        raise


def finalize_index(output):
    output = Path(output)
    # Authority files are already captured verbatim in phase/before/after maps;
    # index them too, including current corrupt/missing-case state, without repair.
    entries = [{'path': str(p.relative_to(output)), 'bytes': p.stat().st_size,
                'sha256': hashlib.sha256(p.read_bytes()).hexdigest()}
               for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink()]
    assert sum(x['bytes'] for x in entries) < MAX_RAW
    save(output / 'raw-index.json', {'files': entries, 'total_bytes': sum(x['bytes'] for x in entries)})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--child', action='store_true')
    parser.add_argument('--root')
    parser.add_argument('--action')
    parser.add_argument('--phase', default='')
    args = parser.parse_args()
    if args.child:
        child(args)
    else:
        parser.error('--output is required') if args.output is None else None
        try:
            summary = run_suite(args.output)
        finally:
            if args.output.is_dir():
                finalize_index(args.output)
        print(json.dumps({'passed': summary['passed'], 'cases': len(summary['cases']),
                          'children': summary['children'], 'output': str(args.output)}))
        raise SystemExit(0 if summary['passed'] else 1)


if __name__ == '__main__':
    main()
