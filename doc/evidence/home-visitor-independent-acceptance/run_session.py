import datetime
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

worktree = Path(__file__).resolve().parents[3]
raw = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/H6C-20261101/raw')
run = sys.argv[1]
directory = raw / run
directory.mkdir(parents=True, exist_ok=False)
user = raw / 'world-user-attempt1'
command = ['/bin/bash', str(worktree / 'scripts/launch_edgeworld_ue_mac.sh'),
           '--launch', '--viewport-preflush', '--user-dir', str(user)]
environment = os.environ.copy()
environment['EDGEWORLD_CAUSAL_PYTHON'] = '/Users/yangacan/edgeWorld/edge-world/.venv-genesis/bin/python'

def write(path, value):
    with path.open('x') as out:
        out.write(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')

def inventory(name):
    value = subprocess.check_output(['ps', '-axo', 'pid,ppid,lstart,command'], text=True)
    write(directory / name, value)
    return value

initial = inventory('process-before.txt')
for line in initial.splitlines():
    fields = line.split(None, 7)
    if len(fields) == 8:
        executable = fields[7]
        if executable.startswith(('/Users/Shared/Epic Games/UE_5.8/Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor', 'CrashReportClient')) or 'abstract_causal_worker.py --state-dir' in executable:
            raise RuntimeError('Existing related process; do not launch: ' + line)
write(directory / 'command.json', command)
observed = set()
launcher_dir = None
with (directory / 'launcher.log').open('xb') as output:
    process = subprocess.Popen(command, cwd=worktree, env=environment, stdout=output, stderr=subprocess.STDOUT)
    write(directory / 'launcher-pid.json', {'pid': process.pid, 'utc': datetime.datetime.now(datetime.timezone.utc).isoformat()})
    while process.poll() is None:
        launcher = (directory / 'launcher.log').read_text(errors='replace')
        if launcher_dir is None:
            for line in launcher.splitlines():
                if line.startswith('[launcher] evidence='):
                    launcher_dir = Path(line.split('=', 1)[1])
                    write(directory / 'launcher-dir.txt', str(launcher_dir) + '\n')
        if launcher_dir:
            log_path = launcher_dir / 'ue.log'
            log = log_path.read_text(errors='replace') if log_path.exists() else ''
            for phase, marker in {'build_success': 'build_exit_code=0', 'engine_initialized': 'Engine is initialized. Leaving FEngineLoop::Init()', 'tick0': 'Causal world stg-demo observed tick 0, revision 0', 'tick1': 'Causal world stg-demo observed tick 1, revision 1', 'tick2': 'Causal world stg-demo observed tick 2, revision 2', 'assertion': 'Assertion failed:'}.items():
                source = launcher if phase == 'build_success' else log
                if phase not in observed and marker in source:
                    observed.add(phase)
                    event = {'utc': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'phase': phase, 'line': next(x for x in source.splitlines() if marker in x)}
                    with (directory / 'events.jsonl').open('a') as events: events.write(json.dumps(event) + '\n')
                    print(json.dumps(event), flush=True)
        time.sleep(0.5)
    code = process.wait()
write(directory / 'launcher.exit', str(code) + '\n')
inventory('process-after.txt')
if launcher_dir:
    for name in ['build.log', 'status.log', 'ue.log', 'console.log', 'command.txt']:
        if (launcher_dir / name).exists():
            with (directory / name).open('xb') as out: out.write((launcher_dir / name).read_bytes())
print(json.dumps({'phase': 'launcher_exit', 'code': code}), flush=True)
sys.exit(code)
