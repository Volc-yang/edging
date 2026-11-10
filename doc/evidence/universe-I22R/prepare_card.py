"""Create a new immutable I22 execution card; never execute UE or edit prior cards."""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import')


def ref(path):
    path = Path(path)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def main(phase, session, source, prerequisite=None, prerequisite_phase=None):
    session = ROOT/session
    dispatch_path = session/('dispatch-bound.json' if phase.startswith('import-') else 'dispatch.json')
    dispatch = json.loads(dispatch_path.read_bytes())
    job = json.loads(Path(dispatch['job']).read_bytes())
    previous = json.loads((HERE/'probe-01-card.json').read_bytes())
    pins = {}
    for item in previous['input_refs']:
        assert ref(item['path']) == item, item['path']
        pins[item['path']] = item
    # Prior inputs are retained and verified, then the new immutable cohort is added.
    for path in (Path(__file__), session/'job.json', session/'dispatch.json', dispatch_path,
                 Path(dispatch['argv'][1]), Path(job['host'])/'Config/DefaultEngine.ini'):
        pins[str(path)] = ref(path)
    for path in sorted((session/'scripts').iterdir()):
        assert path.is_file() and not path.is_symlink()
        pins[str(path)] = ref(path)
    card = dict(format=previous['format'], phase=phase, run_root=str(ROOT),
                owner_source_commit=source, plan_sha256=previous['plan_sha256'],
                driver_ref=previous['driver_ref'], job_ref=ref(dispatch['job']),
                argv=dispatch['argv'], environment=dispatch['env'], cwd=dispatch['cwd'],
                content_root=str(Path(job['host'])/'Content'),
                phase_timeout_seconds=dispatch['deadline_seconds'], result_path=dispatch['result'],
                review='Requires independent C1 exact card acceptance before root execution')
    if prerequisite:
        card['prerequisite_ref'] = ref(ROOT/prerequisite/'result.json')
        supervision = ROOT/('supervision-'+prerequisite_phase)
        card['prerequisite_execution_ref'] = ref(supervision/'execution.json')
        card['prerequisite_postwrite_ref'] = ref(supervision/'phase-postwrite.json')
        for name in ('prerequisite_ref', 'prerequisite_execution_ref', 'prerequisite_postwrite_ref'):
            pins[card[name]['path']] = card[name]
    card['input_refs'] = list(pins.values())
    destination = HERE/(phase+'-card.json')
    with destination.open('x') as stream:
        json.dump(card, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(dict(card_ref=ref(destination), input_count=len(pins))))


if __name__ == '__main__':
    main(*sys.argv[1:])
