"""Frozen I23 artifact: supervise one reviewed, headless import/reload phase.

No stdin protocol, UI, worker or authority access. A failed attempt is retained.
The accepted card pins exact argv and public files; a new card is needed for rework.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I23-20261110-import')
UE = '/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor-Cmd'
OTHER_UE = '/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
spec = importlib.util.spec_from_file_location('i18_readonly_helpers', REPO/'doc/evidence/universe-I18R/driver.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)
sys.path.insert(0, str(REPO/'scripts'))
from universe_iteration import lifecycle as lc


def verify(ref):
    assert prior.ref(ref['path'])['sha256'] == ref['sha256'], ref['path']


def classify(rows, known):
    merged = {}
    for executable in (UE, OTHER_UE):
        for row in lc.classify_processes(rows, known, executable):
            merged[lc.process_key(row['identity'])] = row
    return list(merged.values())


def walk_error(error):
    raise error


def checked_directory(path):
    assert path.is_absolute() and path.is_dir() and path.resolve() == path
    path.relative_to(ROOT)
    for component in (path, *path.parents):
        if component == ROOT.parent:
            break
        assert not component.is_symlink(), str(component)


def sizes():
    checked_directory(ROOT)
    total = content = ddc = 0
    temporary_ipc = []
    for parent, dirs, files in os.walk(ROOT, followlinks=False, onerror=walk_error):
        assert all(not (Path(parent)/name).is_symlink() for name in dirs)
        for name in files:
            path = Path(parent)/name
            s = path.lstat()
            relative = path.relative_to(ROOT)
            temporary_dotnet_socket = (stat.S_ISSOCK(s.st_mode) and len(relative.parts) >= 3 and
                relative.parts[0] in ('p1', 'p2', 'a1', 'a2', 'reload') and relative.parts[1] == 'tmp' and
                path.name.startswith('dotnet-diagnostic-'))
            assert stat.S_ISREG(s.st_mode) or temporary_dotnet_socket, str(path)
            if temporary_dotnet_socket:
                temporary_ipc.append(dict(path=str(path), kind='unix-socket', bytes=s.st_size, mode=s.st_mode))
            total += s.st_size
            if len(relative.parts) >= 3 and relative.parts[1:3] == ('host', 'Content'):
                content += s.st_size
            if len(relative.parts) >= 2 and relative.parts[1] == 'ddc':
                ddc += s.st_size
    return dict(root_bytes=total, content_bytes=content, ddc_bytes=ddc, temporary_ipc=temporary_ipc)


def content_map(root):
    checked_directory(root)
    result = {}
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
        assert all(not (Path(parent)/name).is_symlink() for name in dirs)
        for name in files:
            path = Path(parent)/name
            assert path.is_file() and not path.is_symlink()
            result[str(path.relative_to(root))] = dict(bytes=path.stat().st_size, sha256=prior.ref(path)['sha256'])
    return result


def main(card_path, expected_sha):
    card_path = Path(card_path).resolve()
    assert prior.ref(card_path)['sha256'] == expected_sha
    card = json.loads(card_path.read_bytes())
    assert card['format'] == 'universe-i22-phase-card.v1'
    assert card['run_root'] == str(ROOT) and ROOT.is_dir() and not ROOT.is_symlink()
    verify(card['driver_ref'])
    assert card['driver_ref']['path'] == str(Path(__file__).resolve())
    for ref in card['input_refs']:
        verify(ref)
    assert card['phase'] in ('probe-01', 'probe-02', 'import-01', 'import-02', 'reload')
    phase = card['phase']
    expected_mode = 'probe' if phase.startswith('probe-') else 'reload' if phase == 'reload' else 'import'
    verify(card['job_ref'])
    prepared_job = json.loads(Path(card['job_ref']['path']).read_bytes())
    assert prepared_job['mode'] == expected_mode
    assert prepared_job['output'] == card['result_path']
    assert str(Path(prepared_job['host'])/'Content') == card['content_root']
    if phase.startswith('import-') or phase == 'reload':
        prerequisite = card['prerequisite_ref']
        verify(prerequisite)
        execution_ref, post_ref = card['prerequisite_execution_ref'], card['prerequisite_postwrite_ref']
        verify(execution_ref); verify(post_ref)
        execution = json.loads(Path(execution_ref['path']).read_bytes())
        postwrite = json.loads(Path(post_ref['path']).read_bytes())
        assert execution['actual_parent_wait_exit'] == 0 and execution['normal'] and execution['report_pass']
        assert execution['successful_local_phase'] and not execution['forced']
        assert execution['final_budget_ok'] and not any(s['remaining'] for s in execution['quiet_samples'])
        assert postwrite['execution_ref']['sha256'] == execution_ref['sha256'] and postwrite['within_budget_after_execution_saved']
        assert execution['result_ref']['path'] == prerequisite['path'] and execution['result_ref']['sha256'] == prerequisite['sha256']
        data = json.loads(Path(prerequisite['path']).read_bytes())
        assert data['pid'] == execution['pid']
        assert data['status'] == 'PASS'
        assert data['mode'] == ('probe' if phase.startswith('import-') else 'import')
    out = ROOT/('supervision-'+phase)
    out.mkdir(exist_ok=False)
    argv = card['argv']
    assert argv[0] == UE and '-run=pythonscript' in argv and '-NullRHI' in argv
    for flag in ('-unattended', '-NoSplash', '-NoSound', '-notraceserver', '-traceautostart=0', '-DDC-NoDefaultGraph'):
        assert flag in argv, flag
    assert 0 < card['phase_timeout_seconds'] <= (90 if phase.startswith('probe-') else 180 if phase == 'reload' else 240)
    content = Path(card['content_root'])
    content.relative_to(ROOT)
    system_keys = ('HOME', 'USER', 'LOGNAME', 'LANG', 'LC_ALL', 'LC_CTYPE', '__CF_USER_TEXT_ENCODING')
    env = dict(card['environment'])
    assert all(k in system_keys or k in ('PATH', 'TMPDIR') or (k.startswith('I21_') or k.startswith('I22_')) or (k == 'UE_SKIP_UBT_SDK_SETUP' and env[k] == '1') for k in env)
    assert env['I22_IMPORT_JOB_SHA256'] == card['job_ref']['sha256']
    assert env['PATH'] == '/usr/bin:/bin:/usr/sbin:/sbin'
    assert env['HOME'] == os.environ['HOME'], 'do not repurpose the user home'
    checked_directory(Path(env['TMPDIR']))
    cwd = Path(card['cwd'])
    cwd.relative_to(ROOT)
    start_path = ROOT/'campaign-start.json'
    if start_path.exists():
        started = json.loads(start_path.read_bytes())['started_monotonic']
    else:
        assert phase == 'probe-01'
        prior.save(ROOT/'external-before.json', prior.external_snapshot())
        started = time.monotonic()
        prior.save(start_path, dict(started_monotonic=started, budget_seconds=1200))
    assert time.monotonic()-started + card['phase_timeout_seconds'] + 30 <= 1200, 'insufficient continuous I23 campaign budget'
    readonly_phase = phase.startswith('probe-') or phase == 'reload'
    before = content_map(content) if readonly_phase else None
    if phase.startswith('probe-'):
        assert before == {}, 'probe must start with empty project Content'
    if before is not None:
        prior.save(out/'content-before.json', before)
    pre = lc.observe_once(out/'pre.ps')
    assert not classify(pre['processes'], []), 'another UE process is active'
    prior.save(out/'invocation.json', dict(card_ref=prior.ref(card_path), argv=argv, cwd=str(cwd),
        environment=card['environment'], pinned_system_keys=sorted(k for k in system_keys if k in env),
        fixed_PATH=env['PATH'], fixed_TMPDIR=env['TMPDIR'], all_environment_keys=sorted(env),
        cleared=['EDGEWORLD_*', 'PYTHONHOME', 'PYTHONPATH', 'UE_PYTHONPATH']))
    known, samples = {}, []
    phase_start = time.monotonic()
    forced = False
    error = None
    code = None
    cleanup = []
    with (out/'console.log').open('xb') as console:
        process = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL,
            stdout=console, stderr=subprocess.STDOUT, start_new_session=True)
        print(json.dumps(dict(phase=phase, pid=process.pid, argv=argv)), flush=True)
        try:
            while True:
                sample = lc.observe_once(out/('sample-%04d.ps' % len(samples)))
                rows = sample['processes']
                seed = next((r for r in rows if r['pid'] == process.pid), None)
                if seed:
                    known[lc.process_key(seed)] = seed
                for row in classify(rows, list(known.values())):
                    if row['ownership'] == 'owned':
                        identity = row['identity']
                        known[lc.process_key(identity)] = identity
                measured = sizes()
                samples.append(dict(monotonic=time.monotonic(), ps_ref=sample['raw_ref'], **measured))
                assert measured['root_bytes'] <= 4*1024**3 and measured['content_bytes'] <= 512*1024**2, 'storage budget'
                assert time.monotonic()-started <= 1200, 'continuous campaign budget'
                assert time.monotonic()-phase_start <= card['phase_timeout_seconds'], 'phase budget'
                code = process.poll()
                if code is not None:
                    code = process.wait()
                    break
                time.sleep(1)
        except BaseException as exc:
            error = type(exc).__name__ + ': ' + str(exc)
            forced = True
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                cleanup.append(dict(process_group=process.pid, signal='SIGTERM', reason=error))
                try:
                    code = process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    cleanup.append(dict(process_group=process.pid, signal='SIGKILL', reason='TERM timeout'))
                    code = process.wait(timeout=5)
    # Preserve unexpected survivors, then clean only exact known identities.
    # The intervention remains a failure; forced cleanup cannot grant normal exit.
    cleanup_sample = lc.observe_once(out/'before-cleanup.ps')
    survivors = classify(cleanup_sample['processes'], list(known.values()))
    for row in survivors:
        if row['ownership'] != 'owned':
            continue
        forced = True
        identity = row['identity']
        fresh = lc.observe_once(out/('cleanup-%d.ps' % len(cleanup)))
        same = next((r for r in fresh['processes'] if lc.same_process(r, identity)), None)
        if same:
            try:
                os.kill(same['pid'], signal.SIGTERM)
                cleanup.append(dict(identity=same, signal='SIGTERM'))
            except ProcessLookupError:
                cleanup.append(dict(identity=same, signal='already_exited'))
    # Two passive observations: never bind an app after process exit.
    quiet_samples = []
    for number in range(2):
        sample = lc.observe_once(out/('quiet-%d.ps' % number))
        quiet_samples.append(dict(raw_ref=sample['raw_ref'], remaining=classify(sample['processes'], list(known.values()))))
        time.sleep(0.25)
    for row in quiet_samples[-1]['remaining']:
        if row['ownership'] != 'owned':
            continue
        fresh = lc.observe_once(out/('hard-cleanup-%d.ps' % len(cleanup)))
        identity = row['identity']
        same = next((r for r in fresh['processes'] if lc.same_process(r, identity)), None)
        if same:
            forced = True
            try:
                os.kill(same['pid'], signal.SIGKILL)
                cleanup.append(dict(identity=same, signal='SIGKILL'))
            except ProcessLookupError:
                cleanup.append(dict(identity=same, signal='already_exited'))
    final_quiet = lc.observe_once(out/'quiet-final.ps')
    quiet_samples.append(dict(raw_ref=final_quiet['raw_ref'], remaining=classify(final_quiet['processes'], list(known.values()))))
    final_errors = []
    after = None
    measured = None
    try:
        after = content_map(content)
        prior.save(out/'content-after.json', after)
        measured = sizes()
    except Exception as exc:
        final_errors.append(type(exc).__name__ + ': ' + str(exc))
    for ref in card['input_refs']:
        try:
            verify(ref)
        except Exception as exc:
            final_errors.append('final input check: ' + type(exc).__name__ + ': ' + str(exc))
    elapsed = time.monotonic()-started
    budget_ok = measured is not None and elapsed <= 1200 and measured['root_bytes'] <= 4*1024**3 and measured['content_bytes'] <= 512*1024**2
    readonly_content_ok = before is None or before == after
    if phase.startswith('probe-'):
        readonly_content_ok = readonly_content_ok and before == {} and after == {}
    report_pass = False
    report_identity_ok = False
    result_ref = None
    try:
        result_ref = prior.ref(card['result_path'])
        native = json.loads(Path(card['result_path']).read_bytes())
        verify(card['job_ref'])
        job = json.loads(Path(card['job_ref']['path']).read_bytes())
        report_identity_ok = (native['pid'] == process.pid and
            native['job_sha256'] == card['job_ref']['sha256'] == env['I22_IMPORT_JOB_SHA256'] and
            native['recipe_sha256'] == job['recipe_sha256'] and
            native['source_index_sha256'] == job['source_index_sha256'] and
            native['source_scripts'] == job['source_scripts'])
        report_pass = report_identity_ok and native['status'] == 'PASS' and native['mode'] == expected_mode
    except (OSError, ValueError, KeyError, TypeError):
        pass
    result = dict(format='universe-i22-phase-execution.v1', phase=phase, pid=process.pid, parent_pid=os.getpid(),
        card_ref=prior.ref(card_path), started_monotonic=phase_start, ended_monotonic=time.monotonic(),
        campaign_elapsed_seconds=time.monotonic()-started, actual_parent_wait_exit=code, forced=forced, error=error,
        samples=samples, quiet_samples=quiet_samples, known_owned=list(known.values()), cleanup=cleanup,
        content_unchanged_after_readonly_phase=(before == after) if before is not None else None, readonly_content_ok=readonly_content_ok,
        input_refs_rechecked=not final_errors, actual_sizes=measured, final_errors=final_errors,
        final_budget_ok=budget_ok, report_exists=Path(card['result_path']).is_file(), report_pass=report_pass, report_identity_ok=report_identity_ok, result_ref=result_ref)
    result['normal'] = code == 0 and not forced and not final_errors and budget_ok and not any(s['remaining'] for s in quiet_samples)
    result['successful_local_phase'] = result['normal'] and report_pass and readonly_content_ok
    encoded = (json.dumps(result, sort_keys=True, indent=2)+'\n').encode()
    if measured is None or measured['root_bytes']+len(encoded) > 4*1024**3:
        result['normal'] = False
        result['final_budget_ok'] = False
        result['successful_local_phase'] = False
        encoded = (json.dumps(result, sort_keys=True, indent=2)+'\n').encode()
    prior.save(out/'execution.json', None, raw=encoded)
    # This receipt observes execution.json after it is fully written/fsynced.
    # Final campaign settlement additionally accounts for the receipt itself.
    sealed_sizes = sizes()
    post = dict(format='universe-i22-phase-postwrite.v1', execution_ref=prior.ref(out/'execution.json'),
        observed_after_execution_fsync=True, campaign_elapsed_seconds=time.monotonic()-started,
        actual_sizes=sealed_sizes, execution_json_bytes=len(encoded))
    post['within_budget_after_execution_saved'] = (post['campaign_elapsed_seconds'] <= 1200 and
        sealed_sizes['root_bytes'] <= 4*1024**3 and sealed_sizes['content_bytes'] <= 512*1024**2)
    prior.save(out/'phase-postwrite.json', post)
    print(json.dumps({k:v for k,v in result.items() if k not in ('samples', 'quiet_samples', 'known_owned')}, indent=2), flush=True)
    final_sizes = sizes()
    return 0 if (result['successful_local_phase'] and (before is None or before == after) and
        post['within_budget_after_execution_saved'] and time.monotonic()-started <= 1200 and
        final_sizes['root_bytes'] <= 4*1024**3 and final_sizes['content_bytes'] <= 512*1024**2) else 2


if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:]))
