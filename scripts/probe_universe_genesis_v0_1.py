#!/usr/bin/env python3
"""Owner-dispatched finite identity bootstrap and isolated Genesis probe.

`audit` is stdlib-only. `options` and `probe` explicitly require a separately
approved GPU window; neither creates an authority directory or world HEAD.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback

from engine.universe_authority.codec import DeploymentContext, canonical, decode, digest, encode_f64, f64
from engine.universe_authority.genesis_adapter import (
    GenesisProvider, measure_installed_build, measure_runtime_options,
)
from engine.universe_authority.physics import PhysicsInitialIds


def read(path):
    return decode(path.read_bytes())


def write(path, value):
    # Packaging may exceed record-array caps; individual records are validated
    # at construction. Raw original evidence is never overwritten.
    raw = json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'),
                     allow_nan=False).encode('ascii')
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def file_map(directory):
    return {path.relative_to(directory).as_posix(): dict(bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            for path in sorted(directory.rglob('*')) if path.is_file() and not path.is_symlink()}


def inputs(args):
    repository = Path(__file__).resolve().parents[1]
    paths = [Path(__file__), *sorted((repository / 'engine/universe_authority').glob('*.py'))]
    paths += [repository / 'doc/contracts/universe_authority_v0_2.md',
              repository / 'doc/contracts/universe_physics_v0_1.md']
    for name in ('parameters', 'approved_build', 'context', 'config', 'binding', 'options'):
        value = getattr(args, name, None)
        if value is not None:
            paths.append(value)
    return {str(path.resolve(strict=True)): dict(bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for path in paths}


def budget(output, start, seconds, byte_cap):
    if time.monotonic() - start > seconds:
        raise TimeoutError('bounded I8 time allowance exhausted')
    # Reserve load copy, save original, exported raw and bounded JSON overhead.
    total = sum(path.stat().st_size for path in output.rglob('*') if path.is_file())
    if total + (32 << 20) > byte_cap:
        raise RuntimeError('bounded I8 raw allowance exhausted')


def record_family(output, label, records, blob, development=None):
    write(output / (label + '.json'), dict(scope='isolated-physical-family-not-world-closure',
          records=list(records), snapshot=digest(records[-1]), influence_mm=development,
          raw_sha256=blob.sha256, raw_bytes=len(blob.payload)))
    raw_path = output / (blob.sha256 + '.gstraj')
    if raw_path.exists():
        if raw_path.read_bytes() != blob.payload:
            raise RuntimeError('raw content-address collision')
    else:
        with raw_path.open('xb') as stream:
            stream.write(blob.payload); stream.flush(); os.fsync(stream.fileno())


def probe(args, start):
    output = args.output
    context = DeploymentContext(**read(args.context))
    config, binding = read(args.config), read(args.binding)
    build, options = read(args.approved_build), read(args.options)
    provider = GenesisProvider(config, binding, scratch=output / 'scratch',
                               context=context, build=build, options=options)
    try:
        budget(output, start, args.max_seconds, args.max_bytes)
        initial = provider.initialize(ids=PhysicsInitialIds('sample-initial', 'snapshot-initial', 'checkpoint-initial'))
        record_family(output, 'initial', initial.records, initial.blob)
        seed_records = {digest(record): record for record in (build, options, config, binding, *initial.records)}
        seed_raw = {initial.blob.sha256: initial.blob.payload}
        initial_snapshot = initial.records[-1]
        budget(output, start, args.max_seconds, args.max_bytes)
        frame = provider.calibrate_pose(initial_snapshot, records=seed_records,
                                        read_blob=seed_raw.__getitem__)
        write(output / 'frame-calibration.json', frame)
        first_influence = {}
        arm_results = {}
        recovery_source = None
        for case_id in ('weak', 'strong'):
            records, raw = dict(seed_records), dict(seed_raw)
            snapshot = initial_snapshot
            rows = []
            for tick in range(1, 33):
                budget(output, start, args.max_seconds, args.max_bytes)
                family, blob, development = provider.advance_isolated(
                    snapshot, case_id, records=records, read_blob=raw.__getitem__,
                    ids=PhysicsInitialIds(f'{case_id}-sample-{tick}', f'{case_id}-snapshot-{tick}',
                                          f'{case_id}-checkpoint-{tick}'))
                record_family(output, f'{case_id}-{tick:02d}', family, blob, development)
                records.update((digest(record), record) for record in family)
                raw[blob.sha256] = blob.payload
                snapshot = family[-1]
                sample = family[0]['body']; dynamic, support = sample['bodies']
                p = config['body']['config']
                gap = f64(dynamic['position_m'][2]['$f64']) - f64(p['entities'][0]['radius_m']['$f64']) - (
                    f64(support['position_m'][2]['$f64']) + f64(p['entities'][1]['size_m'][2]['$f64']) / 2)
                rows.append(dict(tick=tick, development_mm=development, gap_m=encode_f64(gap), vz_m_s=dynamic['linear_velocity_m_s'][2],
                    contacts=len(sample['contacts']), sample=sample))
                if tick == 1:
                    first_influence[case_id] = development
                if case_id == 'strong' and tick == 16:
                    recovery_source = (snapshot, dict(records), dict(raw))
            settled = all(-0.005 <= f64(row['gap_m']['$f64']) <= 0.01
                          and abs(f64(row['vz_m_s']['$f64'])) <= 0.05 for row in rows[-4:])
            contact = any(row['contacts'] > 0 for row in rows[-4:])
            arm_results[case_id] = dict(settled=settled, last_four_contact=contact, rows=rows)
            write(output / (case_id + '-summary.json'), arm_results[case_id])
        budget(output, start, args.max_seconds, args.max_bytes)
        snapshot, records, raw = recovery_source
        restored = provider.restore(snapshot, records=records, read_blob=raw.__getitem__)
        if canonical(restored) != canonical(records[snapshot['refs']['sample']]['body']):
            raise RuntimeError('tick16 restored sample mismatch')
        family, blob, development = provider.advance_isolated(
            snapshot, 'strong', records=records, read_blob=raw.__getitem__,
            ids=PhysicsInitialIds('resume-sample-17', 'resume-snapshot-17', 'resume-checkpoint-17'))
        record_family(output, 'resume-17', family, blob, development)
        original = arm_results['strong']['rows'][16]
        exact_resume = (canonical(family[0]['body']) == canonical(original['sample'])
                        and development == original['development_mm'])
        counterfactual = first_influence['strong'] < first_influence['weak'] <= 0
        passed = counterfactual and exact_resume and all(
            arm_results[c]['settled'] and arm_results[c]['last_four_contact'] for c in arm_results)
        summary = dict(scope='isolated-physical-probe-not-world-head-or-ue-integration',
                       passed=passed, first_influence_mm=first_influence,
                       first_counterfactual_passed=counterfactual, exact_tick16_resume=exact_resume,
                       arms={key: {k: v for k, v in value.items() if k != 'rows'}
                             for key, value in arm_results.items()}, provider_propose_world_gate='not-executed',
                       physics_steps=520, frame_scope=frame['scope'])
        write(output / 'summary.json', summary)
        if not passed:
            raise RuntimeError('I8 predeclared physical checks did not pass; originals retained')
    finally:
        provider.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('audit', 'options', 'probe'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--world-id', default='i8-physical-probe')
    parser.add_argument('--build-id', default='provider-build')
    parser.add_argument('--options-id', default='resolved-options')
    parser.add_argument('--parameters', type=Path)
    parser.add_argument('--approved-build', type=Path)
    parser.add_argument('--context', type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--binding', type=Path)
    parser.add_argument('--options', type=Path)
    parser.add_argument('--max-seconds', type=int, default=600)
    parser.add_argument('--max-bytes', type=int, default=1 << 30)
    args = parser.parse_args()
    if not args.output.is_absolute() or args.output.resolve(strict=False) != args.output:
        parser.error('output must be a unique canonical absolute path')
    if not (1 <= args.max_seconds <= 600 and (32 << 20) < args.max_bytes <= (1 << 30)):
        parser.error('resource limits exceed approved I8 bounds')
    needed = {'audit': (), 'options': ('parameters', 'approved_build'),
              'probe': ('context', 'config', 'binding', 'approved_build', 'options')}[args.operation]
    if any(getattr(args, key) is None for key in needed):
        parser.error('missing explicit owner input: ' + ','.join(needed))
    args.output.mkdir(mode=0o700)  # Refuse reuse, aliases and original overwrite.
    start = time.monotonic()
    before = inputs(args)
    write(args.output / 'inputs-before.json', before)
    write(args.output / 'command.json', dict(argv=sys.argv, cwd=os.getcwd(), pid=os.getpid(),
          executable=sys.executable, python=sys.version, operation=args.operation,
          source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
          environment={k: os.environ.get(k) for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','VIRTUAL_ENV')},
          max_seconds=args.max_seconds, max_bytes=args.max_bytes))
    exit_code = 0
    try:
        if args.operation == 'audit':
            build, files = measure_installed_build(world_id=args.world_id, build_id=args.build_id)
            write(args.output / 'provider-build.json', build)
            write(args.output / 'installed-source-index.json', files)
        elif args.operation == 'options':
            options = measure_runtime_options(read(args.parameters), approved_build=read(args.approved_build),
                                              options_id=args.options_id)
            write(args.output / 'resolved-options.json', options)
        else:
            probe(args, start)
    except Exception:
        exit_code = 1
        with (args.output / 'exception.txt').open('x') as stream:
            traceback.print_exc(file=stream)
        traceback.print_exc(file=sys.stderr)
    finally:
        after = inputs(args)
        write(args.output / 'inputs-after.json', after)
        write(args.output / 'exit.json', dict(exit_code=exit_code,
              elapsed_seconds=time.monotonic()-start, inputs_unchanged=before == after))
        write(args.output / 'index.json', file_map(args.output))
    if before != after:
        return 1
    print(json.dumps(dict(operation=args.operation, exit_code=exit_code, evidence=str(args.output))))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
