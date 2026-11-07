"""Frozen I18 execution artifact: one fixed controller, automatic post-run seal."""
from pathlib import Path
import hashlib
import json
import os
import stat
import subprocess
import sys
import time

TOOL = Path(__file__).resolve().parents[3]
ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe')
OUT = ROOT / 'I18-20261107-native-seal'
EXTERNAL = [
    '/Users/yangacan/Library/Application Support/Epic/UnrealEngine/Common/Zen',
    '/Users/yangacan/Library/Application Support/Epic/UnrealBuildTool',
    '/Users/yangacan/Library/Logs/UnrealBuildTool',
    '/Users/yangacan/Library/Application Support/Epic/UnrealEngine/Common/DerivedDataCache',
    '/Users/yangacan/Library/UnrealEngine/Common/DerivedDataCache',
    '/Users/yangacan/UnrealEngine/UnrealTrace',
]


def ref(path):
    path = Path(path)
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return dict(path=str(path), sha256=h.hexdigest())


def save(path, value, *, raw=None):
    data = raw if raw is not None else (json.dumps(value, sort_keys=True, indent=2)+'\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    return ref(path)


def external_snapshot():
    result = dict(monotonic=time.monotonic(), scope='six declared engine candidates; metadata only', roots={})
    for name in EXTERNAL:
        root = Path(name)
        entries, errors = {}, []
        if root.exists():
            for parent, dirs, files in os.walk(root, followlinks=False, onerror=lambda error: errors.append(str(error))):
                for leaf in dirs+files:
                    path = Path(parent)/leaf
                    try:
                        s = path.lstat()
                        entries[str(path.relative_to(root))] = dict(
                            bytes=s.st_size, inode=s.st_ino, mtime_ns=s.st_mtime_ns,
                            mode=stat.S_IMODE(s.st_mode), kind='symlink' if stat.S_ISLNK(s.st_mode)
                            else 'directory' if stat.S_ISDIR(s.st_mode) else 'file')
                    except OSError as error:
                        errors.append(str(error))
        result['roots'][name] = dict(exists=root.exists(), entries=entries, errors=errors)
    return result


def main(inputs_sha):
    sys.path.insert(0, str(TOOL/'scripts'))
    from universe_iteration import lifecycle as lc, capability as cap
    import run_universe_slice_acceptance as common
    input_path = OUT/'prep/execution-inputs.json'
    assert ref(input_path)['sha256'] == inputs_sha, 'independent inputs SHA'
    inputs = json.loads(input_path.read_bytes())
    assert ref(__file__) == inputs['driver_ref'], 'frozen driver changed'
    card = lc.json_ref(inputs['card_ref'])
    prepared = lc.json_ref(inputs['prepared_ref'])
    assert card['prepared_ref'] == inputs['prepared_ref']
    assert card['controller_output'] == str(OUT/'capability')
    before = external_snapshot()
    assert not any(v['errors'] for v in before['roots'].values())
    before_ref = save(OUT/'prep/external-before.json', before)
    authority_before = common.authority_map(Path(prepared['authority_root']))
    assert authority_before['files'] == lc.json_ref(prepared['before_map_ref'])['files']
    ps = lc.observe_once(OUT/'prep/pre-dispatch.ps')
    assert not lc.classify_processes(ps['processes'], [], prepared['binary_pins']['ue']['path'])
    requests = [
        dict(command='skip_metal', args=dict(evidence_ref=inputs['skip_ref'])),
        dict(command='freeze_native', args=dict(manifest_ref=inputs['manifest_ref'], expected_sha256=inputs['manifest_ref']['sha256'])),
        dict(command='start_native', args={}),
        dict(command='wait_native', args=dict(timeout=180)),
        dict(command='seal', args={}),
    ]
    payload = b''.join((json.dumps(v, sort_keys=True)+'\n').encode() for v in requests)
    save(OUT/'prep/cli-requests.jsonl', None, raw=payload)
    argv = [sys.executable, '-B', str(TOOL/'scripts/run_universe_slice_acceptance.py'), 'i15-controller',
        '--i15-card', inputs['card_ref']['path'], '--card-sha256', inputs['card_ref']['sha256'],
        '--prepared-sha256', inputs['prepared_ref']['sha256'], '--accepted-source', inputs['product_source'],
        '--tool-source', inputs['tool_source'], '--manifest-sha256', inputs['probe_manifest_ref']['sha256'],
        '--native-source', inputs['native_source'], '--execute']
    save(OUT/'prep/cli-argv.json', argv)
    started = time.monotonic()
    with (OUT/'prep/cli-transcript.jsonl').open('xb') as log:
        process = subprocess.Popen(argv, cwd=TOOL, stdin=subprocess.PIPE, stdout=log, stderr=subprocess.STDOUT)
        process.stdin.write(payload)
        process.stdin.close()
        try:
            code = process.wait(timeout=240)
        except subprocess.TimeoutExpired:
            save(OUT/'prep/outer-timeout.json', dict(pid=process.pid, normal=False, timeout=240))
            raise
    outer_ref = save(OUT/'prep/controller-outer.json', dict(controller_pid=process.pid,
        parent_pid=os.getpid(), argv=argv, started_monotonic=started,
        ended_monotonic=time.monotonic(), actual_parent_wait_exit=code))
    resource_path = OUT/'capability/resource.json'
    execution_path = OUT/'capability/native-execution.json'
    execution = json.loads(execution_path.read_bytes()) if execution_path.exists() else {}
    resource = json.loads(resource_path.read_bytes()) if resource_path.exists() else {}
    after = external_snapshot()
    after_ref = save(OUT/'prep/external-after.json', after)
    changes, changed_bytes = [], 0
    for name, prior in before['roots'].items():
        current = after['roots'][name]
        for relative in sorted(set(prior['entries']) | set(current['entries'])):
            a, b = prior['entries'].get(relative), current['entries'].get(relative)
            if a != b:
                changes.append(dict(root=name, relative=relative, before=a, after=b))
                if b and b['kind'] != 'directory':
                    changed_bytes += b['bytes']
    diff_ref = save(OUT/'prep/external-diff.json', dict(before_ref=before_ref, after_ref=after_ref,
        changes=changes, conservative_current_changed_file_bytes=changed_bytes))
    authority_after = common.authority_map(Path(prepared['authority_root']))
    map_ref = save(OUT/'prep/authority-after.json', authority_after)
    final = lc.observe_once(OUT/'prep/final-processes.ps')
    known = {}
    if execution.get('identity'):
        for path in sorted((OUT/'capability').glob('sample-*.json')):
            sample = json.loads(path.read_bytes())
            for row in lc.classify_processes(sample['processes'], [execution['identity']], prepared['binary_pins']['ue']['path']):
                if row['ownership'] == 'owned':
                    known[lc.process_key(row['identity'])] = row['identity']
            for row in sample['processes']:
                if cap.sponsored_trace_server(row, execution['host_pid'], prepared['ue_root']):
                    known[lc.process_key(row)] = row
    late_trace = bool(execution.get('host_pid')) and any(
        cap.sponsored_trace_server(row, execution['host_pid'], prepared['ue_root']) for row in final['processes'])
    quiet = not lc.classify_processes(final['processes'], list(known.values()), prepared['binary_pins']['ue']['path']) and not late_trace
    frozen = execution.get('frozen_files', [])
    frozen_errors = []
    try:
        unchanged = bool(frozen) and all(cap.file_fingerprint(v['path']) == v for v in frozen)
    except (OSError, lc.Invalid) as error:
        unchanged = False
        frozen_errors.append(str(error))
    root_bytes = sum(p.stat().st_size for p in ROOT.rglob('*') if p.is_file())
    elapsed = time.monotonic()-started
    total_bytes = root_bytes+changed_bytes+65536
    readonly = authority_before['files'] == authority_after['files']
    metadata_ok = not any(v['errors'] for v in after['roots'].values())
    passed = (code == 0 and execution.get('normal') is True and resource.get('decision') == 'within_budget'
              and quiet and unchanged and readonly and metadata_ok and elapsed <= 900 and total_bytes <= 2*1024**3)
    review = dict(format='universe-i18-resource-review.v1', run_id=prepared['run_id'],
        elapsed_seconds=elapsed, storage_bytes=total_bytes, root_bytes_measured=root_bytes,
        conservative_external_changed_file_bytes=changed_bytes, seal_allowance_bytes=65536,
        all_processes_quiet=quiet, authority_unchanged=readonly, frozen_outputs_unchanged=unchanged,
        frozen_output_errors=frozen_errors,
        metadata_complete=metadata_ok, decision='pass_requires_independent_review' if passed else 'fail',
        outer_wait_ref=outer_ref, external_diff_ref=diff_ref, authority_after_ref=map_ref,
        final_processes_ref=final['raw_ref'], controller_resource_ref=ref(resource_path) if resource_path.exists() else None,
        scope='full inherited output root + whole current changed files in six declared external candidates; not an OS-wide I/O audit',
        g_b2_granted=False)
    result_ref = save(OUT/'prep/resource-review.json', review)
    print(json.dumps(dict(resource_ref=result_ref, elapsed_seconds=elapsed, bytes=total_bytes,
        phase='checks_complete_requires_independent_review' if passed else 'fail', native_once=True)), flush=True)
    return 0 if passed else 2


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: driver.py INDEPENDENT_INPUTS_SHA256')
    raise SystemExit(main(sys.argv[1]))
