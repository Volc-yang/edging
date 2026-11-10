"""Read-only replay of the sealed I22 attempt; writes only its stdout."""
import hashlib
import json
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(item):
    assert sha(item['path']) == item['sha256'], item['path']


def main():
    observation = load(HERE/'post-seal-observation.json')
    verify(observation['seal_ref'])
    seal = load(observation['seal_ref']['path'])
    assert observation['observed_after_final_fsync']
    assert observation['continuous_elapsed_seconds'] <= 1200
    assert observation['capture']['actual_outer_exit'] == 2
    assert not seal['remaining'] and not seal['input_errors'] and not seal['external_errors']
    assert seal['process_and_declared_domain_check']
    verify(seal['external_diff_ref'])
    verify(seal['final_ps_ref'])
    assert load(seal['external_diff_ref']['path'])['changes'] == []
    assert [p['phase'] for p in seal['phase_records']] == ['probe-01', 'probe-02']
    unique_pins = {}
    rows = []
    for phase, session, expected_wait, expected_status in (
            ('probe-01', 'p1', 255, 'FAIL'), ('probe-02', 'p2', 0, 'PASS')):
        execution_path = ROOT/('supervision-'+phase)/'execution.json'
        execution = load(execution_path)
        verify(execution['card_ref'])
        card = load(execution['card_ref']['path'])
        for item in card['input_refs']:
            verify(item)
            assert item['path'] not in unique_pins or unique_pins[item['path']] == item['sha256']
            unique_pins[item['path']] = item['sha256']
        verify(card['job_ref'])
        verify(execution['result_ref'])
        native = load(execution['result_ref']['path'])
        job = load(card['job_ref']['path'])
        assert native['pid'] == execution['pid']
        assert native['job_sha256'] == card['job_ref']['sha256']
        assert native['recipe_sha256'] == job['recipe_sha256']
        assert native['source_index_sha256'] == job['source_index_sha256']
        assert native['source_scripts'] == job['source_scripts']
        assert native['status'] == expected_status
        assert execution['actual_parent_wait_exit'] == expected_wait
        assert not execution['forced'] and not execution['cleanup']
        assert execution['input_refs_rechecked'] and not execution['final_errors']
        assert not any(s['remaining'] for s in execution['quiet_samples'])
        assert execution['readonly_content_ok']
        assert load(execution_path.parent/'content-before.json') == {}
        assert load(execution_path.parent/'content-after.json') == {}
        post = load(execution_path.parent/'phase-postwrite.json')
        verify(post['execution_ref'])
        assert post['execution_ref']['sha256'] == sha(execution_path)
        assert post['within_budget_after_execution_saved']
        assert execution['successful_local_phase'] == (expected_status == 'PASS')
        rows.append(dict(phase=phase, native_status=expected_status,
                         actual_wait=expected_wait, pid=execution['pid'],
                         result_ref=execution['result_ref'], card_ref=execution['card_ref']))
    capability = load(ROOT/'p2/result.json')['capability']
    assert capability['complete'] and capability['mesh_before'] == capability['mesh_restored']
    assert capability['original_fixture_getters_before'] == capability['original_fixture_getters_after']
    assert capability['actual_alpha_disconnected'] and capability['actual_alpha_restored']
    assert len(capability['texture_restoration']) == 3
    for row in capability['texture_restoration']:
        assert row['before'] == row['after'] and row['diff'] == {}
        assert row['after']['width'] > 0 and row['after']['height'] > 0
    for path, expected in capability['fixture_file_sha256'].items():
        assert sha(path) == expected
    for session in ('p1', 'p2', 'a1', 'a2'):
        entries = list((ROOT/session/'host/Content').rglob('*'))
        assert all(p.is_dir() and not p.is_symlink() for p in entries)
    assert not (ROOT/'a1/result.json').exists() and not (ROOT/'a2/result.json').exists()
    assert not (ROOT/'reload').exists()
    assert not list(ROOT.glob('supervision-import-*'))
    assert load(ROOT/'a2/job.json')['source_scripts'] == load(ROOT/'p2/job.json')['source_scripts']
    bound = load(ROOT/'a2/dispatch-bound.json')
    assert bound['env']['I22_PROBE_RESULT_SHA256'] == sha(ROOT/'p2/result.json')
    originals = load(REPO/'doc/evidence/universe-I20R/integration-source-index.json')['files']
    for item in originals:
        verify(item)
        assert Path(item['path']).stat().st_size == item['bytes']
    logical_bytes = 0
    files = 0
    for parent, directories, filenames in os.walk(ROOT, followlinks=False):
        assert all(not (Path(parent)/name).is_symlink() for name in directories)
        for name in filenames:
            path = Path(parent)/name
            assert path.is_file() and not path.is_symlink()
            logical_bytes += path.stat().st_size
            files += 1
    assert logical_bytes == observation['actual_sizes']['root_bytes']
    assert logical_bytes <= 4*1024**3
    assert observation['actual_sizes']['content_bytes'] == 0
    print(json.dumps(dict(format='universe-i22-parent-replay.v1',
        verdict='partial; capability accepted; actual asset import and reload unexecuted',
        phases=rows, unique_verified_input_pins=len(unique_pins),
        I20_original_files_unchanged=len(originals),
        sealed_file_count=files, sealed_logical_bytes_unchanged=logical_bytes,
        campaign_observation=observation,
        source_integration=False, native_import_acceptance=False,
        build_runtime_visual_acceptance=False), sort_keys=True, indent=2))


if __name__ == '__main__':
    main()
