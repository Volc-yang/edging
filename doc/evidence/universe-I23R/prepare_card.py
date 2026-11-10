"""Create a new immutable I23 execution card; never execute UE or edit prior cards."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I23-20261110-import')


def ref(path):
    path = Path(path)
    return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def sha_plan():
    return ref(HERE.parents[1]/'design/pr130-merge-validation-plan.md')['sha256']


def main(phase, session, source, prerequisite=None, prerequisite_phase=None):
    session = ROOT/session
    dispatch_path = session/('dispatch-bound.json' if phase.startswith('import-') else 'dispatch.json')
    dispatch = json.loads(dispatch_path.read_bytes())
    job = json.loads(Path(dispatch['job']).read_bytes())
    previous = json.loads((HERE.parent/'universe-I22R/probe-02-card.json').read_bytes())
    pins = {}
    def add(item):
        assert ref(item['path']) == {k:item[k] for k in ('path', 'sha256')}, item['path']
        if item['path'] in pins:
            assert pins[item['path']]['sha256'] == item['sha256'], item['path']
        pins[item['path']] = dict(path=item['path'], sha256=item['sha256'])
    for item in previous['input_refs']:
        add(item)
    pf = job['preflight']
    for item in [pf['binary'], *pf['installed_modules'], *pf['enabled_plugin_closure'].values(),
                 *pf['startup']['scripts'], *job['startup']['scripts']]:
        add(item)
    for path, item in pf['probe_fixtures'].items():
        add(dict(path=path, sha256=item['sha256']))
    index = json.loads(Path(job['source_index']).read_bytes())
    assert ref(job['source_index'])['sha256'] == job['source_index_sha256']
    for item in index['files']:
        relative = Path(item['path'])
        assert not relative.is_absolute() and '..' not in relative.parts
        path = Path(job['source_root'])/relative
        assert path.stat().st_size == item['bytes']
        add(dict(path=str(path), sha256=item['sha256']))
    original_index = HERE.parents[2]/'doc/evidence/universe-I20R/integration-source-index.json'
    add(ref(original_index))
    for item in json.loads(original_index.read_bytes())['files']:
        add(item)
    source_tree = HERE.parents[2].parent/'i21-import'
    for name, expected in job['source_scripts'].items():
        raw = subprocess.check_output(['git', 'show', source+':scripts/realism_import/'+name], cwd=source_tree)
        assert hashlib.sha256(raw).hexdigest() == expected == ref(session/'scripts'/name)['sha256'], name
    prepared = subprocess.check_output(['git', 'show', source+':scripts/realism_import/prepare.py'], cwd=source_tree)
    assert (source_tree/'scripts/realism_import/prepare.py').read_bytes() == prepared
    preparer_snapshot = session/'preparer-source.py'
    if preparer_snapshot.exists():
        assert preparer_snapshot.read_bytes() == prepared
    else:
        with preparer_snapshot.open('xb') as stream:
            stream.write(prepared)
    add(ref(preparer_snapshot))
    # Prior inputs are retained and verified, then the new immutable cohort is added.
    for path in (Path(__file__), HERE/'run_phase.py', HERE/'seal_campaign.py',
                 HERE.parents[1]/'design/pr130-merge-validation-plan.md',
                 HERE/'C0-addendum.json', HERE/'dispatch-templates.json',
                 HERE/'protected-I22-before.json', HERE/'check_parent.py',
                 session/'job.json', session/'dispatch.json', dispatch_path,
                 Path(dispatch['argv'][1]), Path(job['host'])/'Config/DefaultEngine.ini'):
        add(ref(path))
    for path in sorted((session/'scripts').iterdir()):
        assert path.is_file() and not path.is_symlink()
        add(ref(path))
    card = dict(format=previous['format'], phase=phase, run_root=str(ROOT),
                owner_source_commit=source, plan_sha256=sha_plan(),
                driver_ref=ref(HERE/'run_phase.py'), job_ref=ref(dispatch['job']),
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
            add(card[name])
        if phase == 'reload':
            import sys
            sys.path.insert(0, str(HERE))
            from run_phase import content_map
            imported = json.loads(Path(card['prerequisite_ref']['path']).read_bytes())
            assert imported['status'] == 'PASS' and imported['mode'] == 'import'
            assert job['import_result'] == card['prerequisite_ref']['path']
            assert job['import_result_sha256'] == card['prerequisite_ref']['sha256']
            assert job['source_scripts'] == imported['source_scripts']
            actual = content_map(Path(job['host'])/'Content')
            assert actual == imported['content_files']
            for relative, item in actual.items():
                add(dict(path=str(Path(job['host'])/'Content'/relative), sha256=item['sha256']))
            card['saved_package_map'] = actual
    card['input_refs'] = list(pins.values())
    destination = HERE/(phase+'-card.json')
    with destination.open('x') as stream:
        json.dump(card, stream, sort_keys=True, indent=2)
        stream.write('\n')
    print(json.dumps(dict(card_ref=ref(destination), input_count=len(pins))))


if __name__ == '__main__':
    main(*sys.argv[1:])
