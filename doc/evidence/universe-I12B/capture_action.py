#!/usr/bin/env python3
"""Quiescent passive snapshot for root's future CUA actions. No input/advance.

Use before action, then root CUA, exact marker/readback, then after action.
Independent authority/scratch maps preserve accepted root/files format.
"""
import argparse
import hashlib
import os
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts'))
from run_universe_slice_acceptance import emit, process_snapshot, utc
from verify_universe_slice_evidence import authority_map, require, safe_path


def capture(*, run, action, phase, ue_pid, project, log, authority, scratch, trace, output):
    require(phase in ('before', 'after') and run and action and ue_pid > 0, 'explicit run/action/phase/UE PID required')
    output = safe_path(output)
    require(output.parent.is_dir() and not output.exists(), 'new exclusive snapshot directory required')
    output.mkdir(mode=0o700)
    begin, monotonic_begin = utc(), time.monotonic()
    observed = process_snapshot([ue_pid])
    require(str(safe_path(project)) in observed['raw_stdout'] and 'UnrealEditor' in observed['raw_stdout'],
            'actual requested UE PID/project command does not match')
    emit(observed, output / 'process.json')
    maps = {}
    for role, root in (('authority', authority), ('scratch', scratch)):
        root = safe_path(root)
        value = authority_map(root) if root.is_dir() else {'root': str(root), 'files': {}, 'bytes': 0, 'absent': True}
        maps[role] = value
        emit(value, output / (role + '-map.json'))
    log = safe_path(log)
    with log.open('rb') as stream:
        before = os.fstat(stream.fileno())
        count, h = before.st_size, hashlib.sha256()
        remaining = count
        while remaining:
            block = stream.read(min(remaining, 1024**2))
            require(block, 'log truncated during prefix capture')
            remaining -= len(block); h.update(block)
        after, current = os.fstat(stream.fileno()), log.lstat()
        require((before.st_dev, before.st_ino) == (after.st_dev, after.st_ino) ==
                (current.st_dev, current.st_ino) and after.st_size >= count, 'log replaced/truncated during capture')
    # Quiescence is explicit: a racing commit cannot masquerade as one snapshot.
    for role, root in (('authority', authority), ('scratch', scratch)):
        root = safe_path(root)
        again = authority_map(root) if root.is_dir() else {'root': str(root), 'files': {}, 'bytes': 0, 'absent': True}
        require(again == maps[role], role + ' changed during quiescent snapshot')
    trace = safe_path(trace)
    require(trace.is_dir(), 'explicit actual raw trace directory required')
    value = dict(format='universe-i12-action-snapshot.v1', run_id=run, action=action, phase=phase,
                 ue_pid=ue_pid, project=str(project), captured_begin=begin, captured_end=utc(),
                 monotonic_begin=monotonic_begin, monotonic_end=time.monotonic(),
                 raw_trace=str(trace), authority_map=str(output / 'authority-map.json'),
                 scratch_map=str(output / 'scratch-map.json'), process_evidence=str(output / 'process.json'),
                 log=dict(path=str(log), start_offset=count, prefix_sha256=h.hexdigest(),
                          device=before.st_dev, inode=before.st_ino),
                 note='Passive map/log pins only; caller binds CUA action, transform/readback and screenshot evidence.')
    emit(value, output / 'snapshot.json')
    return value


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'action', 'phase'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--ue-pid', type=int, required=True)
    for name in ('project', 'log', 'authority', 'scratch', 'trace', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = capture(**vars(args))
    print(str(Path(result['authority_map']).parent / 'snapshot.json'))
