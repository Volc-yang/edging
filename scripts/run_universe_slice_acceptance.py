#!/usr/bin/env python3
"""I12 passive collection driver. Default prints plan; cannot launch a runtime.

Only --output writes, using exclusive creation. Never creates authority, keys,
launcher config or requests; never sends input, signals, or talks to the worker.
Actual orchestration awaits a root-issued R12 card and final integrated source.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

from verify_universe_slice_evidence import (Invalid, authority_map, file_hash,
                                            read_json, require, safe_path)

PLAN = [
    ('bootstrap', 'session1: trusted launcher/worker identity and public pins; registered empty root status may be NOT_READY; no HEAD/scratch/solve before explicit initialize'),
    ('initialize', 'explicit initialize; wait verified observation (0,0), D=null, budget8/cursor0/step0; capture stable Metal image'),
    ('retain', 'UniverseRetain; wait (0,1); same snapshot/tick/D/budget/cursor, no solver'),
    ('physical', 'select weak explicitly; UniverseAdvance; wait (1,2); eight solver steps, independently computed exact D'),
    ('retry', 'UniverseRetryLastCommitted; new request ID, identical closure/digest; original result, no authority change'),
    ('history', 'UniverseObserveExact 0 1 1 then UniverseObserveExact 0 0 0, then latest UniverseObserveExact 1 2 2; exact tick/revision/watermark and screenshot bindings'),
    ('history_write_rejected', 'history Space/R cannot prepare or advance; per-action map and raw request interval'),
    ('held_input', 'held Space across history/current transition cannot create hidden intent; release then inspect'),
    ('camera', 'UniverseCamera scripted local view change, verify actual changed view; no claim of human relative-mouse input'),
    ('visibility', 'UniverseProjectionVisible false/true; capture actual hidden/restored view and map per action'),
    ('framerate', 'standard t.MaxFPS bounded change plus readback and per-action map'),
    ('pause', 'standard pause/resume plus actual state/readback and per-action map'),
    ('exit1', 'normal quit via explicit preflush path; worker EOF/drain/reap exit0, UE exit0, launcher exit0 separately'),
    ('revisit', 'session2 existing mode, same authority/world/anchor, distinct owned PID/pipes; fresh status and recovery, exact 1 2 and 0 1; no initialization/advance'),
    ('exit2', 'normal quit; preserve all raw, maps, actual exits and screenshot timing; account all attempts'),
]


def utc():
    return datetime.now(timezone.utc).isoformat()


def emit(value, output):
    encoded = (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + '\n').encode()
    if output:
        path = safe_path(output)
        require(path.parent.is_dir(), 'output parent must already exist')
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    else:
        sys.stdout.buffer.write(encoded)


def process_snapshot(pids):
    """Read actual process argv/PPID; absence is not an exit status."""
    require(pids and all(type(pid) is int and pid > 0 for pid in pids), 'positive owned PIDs required')
    result = subprocess.run(['/bin/ps', '-ww', '-p', ','.join(map(str, pids)),
                             '-o', 'pid=,ppid=,lstart=,command='],
                            capture_output=True, text=True, timeout=5, check=False)
    require(result.returncode in (0, 1), 'ps failed')
    return {'captured_at': utc(), 'requested_pids': pids, 'ps_returncode': result.returncode,
            'raw_stdout': result.stdout, 'raw_stderr': result.stderr,
            'warning': 'ps absence is not proof of normal exit; retain parent wait/worker-exit trace.'}


def metadata(paths):
    """lstat only: deliberately does not open private owner/key files."""
    rows = []
    for raw in paths:
        path = Path(raw).absolute()
        st = path.lstat()
        rows.append({'path': str(path), 'uid': st.st_uid, 'gid': st.st_gid,
                     'mode': oct(st.st_mode & 0o7777), 'nlink': st.st_nlink,
                     'bytes': st.st_size, 'device': st.st_dev, 'inode': st.st_ino,
                     'symlink': path.is_symlink()})
    return {'captured_at': utc(), 'metadata_only': True, 'entries': rows}


def wait_marker(path, marker, seconds, expected_hash, start_offset=None,
                expected_device=None, expected_inode=None, run_id=None, host_pid=None):
    """Read from an action-before pin, including bytes already appended after it.

    Explicit offset requires caller's before device/inode as well as prefix hash.
    Without offset, preserve the old whole-file pin/current-size behavior.
    Run/PID labels are caller declarations, not process identity authentication.
    """
    path = safe_path(path)
    require(path.is_file() and marker and 0 < seconds <= 60, 'existing log/marker and timeout<=60 required')
    if start_offset is not None:
        require(type(start_offset) is int and start_offset >= 0 and
                type(expected_device) is int and type(expected_inode) is int,
                'explicit start offset requires before device/inode pins')
    deadline = time.monotonic() + seconds
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, 'rb') as stream:
        opened = os.fstat(stream.fileno())
        require(stat.S_ISREG(opened.st_mode), 'log is not a regular file')
        identity = (opened.st_dev, opened.st_ino)
        if expected_device is not None or expected_inode is not None:
            require(identity == (expected_device, expected_inode), 'log replaced since action-before pin')
        start = opened.st_size if start_offset is None else start_offset
        offset, tail = start, b''

        def validate_prefix():
            current = path.lstat()
            retained = os.fstat(stream.fileno())
            require(stat.S_ISREG(current.st_mode) and
                    (current.st_dev, current.st_ino) == identity, 'log replaced during wait')
            require(retained.st_size >= offset and current.st_size >= offset,
                    'log truncated since action-before pin')
            stream.seek(0)
            digest, remaining = hashlib.sha256(), start
            while remaining:
                block = stream.read(min(remaining, 1024**2))
                require(block, 'log prefix truncated')
                digest.update(block)
                remaining -= len(block)
            require(digest.hexdigest() == expected_hash, 'log prefix hash does not match caller before pin')

        validate_prefix()
        while time.monotonic() <= deadline:
            # Validate path identity and prefix before accepting appended evidence.
            validate_prefix()
            stream.seek(offset)
            block = stream.read(1024**2)
            offset += len(block)
            tail += block
            require(len(tail) <= 16 * 1024**2, 'marker observation byte cap')
            if marker.encode() in tail:
                validate_prefix()
                return {'matched': True, 'captured_at': utc(), 'path': str(path), 'marker': marker,
                        'start_offset': start, 'end_offset': offset, 'prefix_sha256': expected_hash,
                        'device': identity[0], 'inode': identity[1],
                        'run_id': run_id, 'host_pid': host_pid,
                        'binding': 'caller-declared run/PID; correlate original process evidence'}
            time.sleep(.1)
        validate_prefix()
        return {'matched': False, 'captured_at': utc(), 'path': str(path), 'marker': marker,
                'start_offset': start, 'end_offset': offset, 'prefix_sha256': expected_hash,
                'device': identity[0], 'inode': identity[1], 'run_id': run_id, 'host_pid': host_pid}


def collect(spec):
    """Pin only explicitly enumerated public evidence; no recursive raw/key scan."""
    value = read_json(spec)
    require(value['format'] == 'universe-i12-evidence.v1', 'bundle format')
    artifacts = []
    seen = set()
    for item in value['artifacts']:
        path = safe_path(item['path'])
        require(str(path) not in seen and path.is_file(), 'duplicate/missing artifact')
        seen.add(str(path))
        require(item['role'] not in {'private_key', 'owner_config'}, 'private contents cannot be indexed')
        artifacts.append({'role': item['role'], 'path': str(path),
                          'bytes': path.stat().st_size, 'sha256': file_hash(path)})
    value['artifacts'] = artifacts
    value['collected_at'] = utc()
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='exclusive new evidence file; parent must exist')
    commands = parser.add_subparsers(dest='command')
    commands.add_parser('plan')
    snapshot = commands.add_parser('snapshot')
    snapshot.add_argument('--authority', type=Path, required=True)
    processes = commands.add_parser('processes')
    processes.add_argument('--pid', type=int, action='append', required=True)
    meta = commands.add_parser('metadata')
    meta.add_argument('paths', nargs='+')
    wait = commands.add_parser('wait-marker')
    wait.add_argument('--log', type=Path, required=True)
    wait.add_argument('--marker', required=True)
    wait.add_argument('--initial-sha256', required=True)
    wait.add_argument('--start-offset', type=int, help='action-before log byte length; hash covers exactly this prefix')
    wait.add_argument('--expected-device', type=int, help='action-before st_dev, required with explicit offset')
    wait.add_argument('--expected-inode', type=int, help='action-before st_ino, required with explicit offset')
    wait.add_argument('--run-id', help='caller-bound run identity; correlate raw process evidence')
    wait.add_argument('--host-pid', type=int, help='caller-bound UE PID; not inferred or authenticated')
    wait.add_argument('--seconds', type=float, default=10)
    collection = commands.add_parser('collect')
    collection.add_argument('--spec', type=Path, required=True)
    commands.add_parser('run', help='reserved, disabled until actual R12 implementation dispatch')
    args = parser.parse_args()
    try:
        if args.command in (None, 'plan'):
            value = {'format': 'universe-i12-action-plan.v1', 'runtime_authorized': False,
                     'candidate_budget': {'seconds': 1200, 'bytes': 2 * 1024**3},
                     'actions': [{'id': key, 'instruction': text} for key, text in PLAN],
                     'lod': 'N/A for this technical proxy; record rationale, do not claim coverage',
                     'pending': ['final merged SHA/build', 'G-P1/I10B/I11B accepted evidence',
                                 'actual root-issued R12', 'trusted owner inputs', 'UI automation binding']}
        elif args.command == 'snapshot':
            value = dict(authority_map(args.authority), captured_at=utc())
        elif args.command == 'processes':
            value = process_snapshot(args.pid)
        elif args.command == 'metadata':
            value = metadata(args.paths)
        elif args.command == 'wait-marker':
            value = wait_marker(args.log, args.marker, args.seconds, args.initial_sha256,
                                args.start_offset, args.expected_device, args.expected_inode,
                                args.run_id, args.host_pid)
        elif args.command == 'collect':
            value = collect(args.spec)
        else:
            raise Invalid('run disabled: requires later root dispatch, final merged tree and actual R12; no process was launched')
        emit(value, args.output)
        return 2 if value.get('matched') is False else 0
    except (Invalid, OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as error:
        print(json.dumps({'status': 'error', 'error': str(error)}), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
