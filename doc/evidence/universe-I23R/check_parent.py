"""Passive replay of I23 cards, normal exits, actual packages and saved evidence."""
import hashlib
import json
import os
import stat
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run_phase as driver


def load(path):
    return json.loads(Path(path).read_bytes())


def verify(item):
    driver.verify(item)


def protected_map(root):
    result = {}
    def fail(error):
        raise error
    for parent, directories, files in os.walk(root, followlinks=False, onerror=fail):
        assert all(stat.S_ISDIR(os.lstat(Path(parent)/name).st_mode) for name in directories)
        for name in files:
            path = Path(parent)/name
            assert stat.S_ISREG(os.lstat(path).st_mode)
            raw = path.read_bytes()
            result[str(path.relative_to(root))] = dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    return result


def main():
    root = driver.ROOT
    seal = load(root/'campaign-seal.json')
    observation = load(HERE/'post-seal-observation.json')
    verify(observation['seal_ref'])
    assert observation['observed_after_final_fsync']
    assert observation['continuous_elapsed_seconds'] <= 1200
    assert observation['actual_sizes'] == driver.sizes()
    assert observation['actual_sizes']['root_bytes'] <= 4*1024**3
    assert observation['actual_sizes']['content_bytes'] <= 512*1024**2
    assert not seal['input_errors'] and not seal['external_errors'] and not seal['remaining']
    verify(seal['external_diff_ref']); verify(seal['final_ps_ref'])
    assert load(seal['external_diff_ref']['path'])['changes'] == []
    before, after = load(root/'external-before.json'), load(root/'external-after.json')
    assert set(before['roots']) == set(after['roots']) and len(before['roots']) == 6
    for name, old in before['roots'].items():
        current = after['roots'][name]
        assert old['exists'] == current['exists'] and old['entries'] == current['entries']
        assert not old['errors'] and not current['errors']
    protected = load(HERE/'protected-I22-before.json')
    assert protected_map(Path(protected['root'])) == protected['files']
    originals = load(HERE.parents[2]/'doc/evidence/universe-I20R/integration-source-index.json')
    for item in originals['files']:
        verify(item)
        assert Path(item['path']).stat().st_size == item['bytes']
    phases, pins, known = {}, {}, []
    for path in sorted(root.glob('supervision-*/execution.json')):
        execution = load(path)
        verify(execution['card_ref']); verify(execution['result_ref'])
        card = load(execution['card_ref']['path']); job = load(card['job_ref']['path'])
        native = load(execution['result_ref']['path'])
        for item in card['input_refs']:
            verify(item)
            assert item['path'] not in pins or pins[item['path']] == item['sha256']
            pins[item['path']] = item['sha256']
        assert native['pid'] == execution['pid']
        assert native['job_sha256'] == card['job_ref']['sha256']
        assert native['source_scripts'] == job['source_scripts']
        assert native['recipe_sha256'] == job['recipe_sha256']
        assert native['source_index_sha256'] == job['source_index_sha256']
        assert execution['input_refs_rechecked'] and not execution['final_errors']
        assert not execution['forced'] and not execution['cleanup'] and execution['final_budget_ok']
        assert execution['readonly_content_ok']
        post = load(path.parent/'phase-postwrite.json')
        verify(post['execution_ref']); assert post['within_budget_after_execution_saved']
        assert post['observed_after_execution_fsync']
        for sample in execution['samples']:
            verify(sample['ps_ref'])
        for sample in execution['quiet_samples']:
            verify(sample['raw_ref'])
            rows = driver.lc.parse_ps_snapshot(Path(sample['raw_ref']['path']).read_text())
            assert not driver.classify(rows, execution['known_owned'])
        known.extend(execution['known_owned'])
        if execution['successful_local_phase']:
            assert native['status'] == 'PASS' and execution['actual_parent_wait_exit'] == 0
            cap = native['capability']
            assert cap['complete'] and cap['mesh_before'] == cap['mesh_restored']
            assert cap['original_fixture_getters_before'] == cap['original_fixture_getters_after']
            assert len(cap['texture_restoration']) == 3
            assert all(x['before'] == x['after'] and x['diff'] == {} for x in cap['texture_restoration'])
            assert cap['actual_alpha_disconnected'] and cap['actual_alpha_restored']
        phases[card['result_path']] = (execution, card, job, native)
    final_rows = driver.lc.parse_ps_snapshot(Path(seal['final_ps_ref']['path']).read_text())
    assert not driver.classify(final_rows, known)
    counts = [sum(p[1]['phase'].startswith(prefix) for p in phases.values()) for prefix in ('probe-', 'import-', 'reload')]
    assert counts[0] <= 2 and counts[1] <= 2 and counts[2] <= 1
    passed = all(seal[k] for k in ('process_and_declared_domain_check', 'selected_probe_ok', 'selected_import_ok', 'reload_content_and_local_report_pass'))
    if passed:
        re = next(p for p in phases.values() if p[1]['phase'] == 'reload')
        ie = phases[re[1]['prerequisite_ref']['path']]
        pe = phases[ie[1]['prerequisite_ref']['path']]
        assert all(p[0]['successful_local_phase'] for p in (pe, ie, re))
        assert pe[3]['source_scripts'] == ie[3]['source_scripts'] == re[3]['source_scripts']
        assert ie[3]['native'] == re[3]['native']
        for phase in (ie, re):
            groups = phase[3]['native']['objects']
            assert {k:len(v) for k,v in groups.items()} == {'StaticMesh':5, 'Texture2D':14, 'Material':3}
            assert len(phase[3]['source_mesh_mapping']) == 5
            negatives = phase[3]['negative_checks']
            assert {n['case'] for n in negatives} == {'actual_Alpha_disconnected', 'actual_mesh_slot_material_replaced'}
            assert all(n['rejected'] for n in negatives)
        content = driver.content_map(Path(re[1]['content_root']))
        assert content == ie[3]['content_files'] == re[3]['content_files'] == re[1]['saved_package_map']
        assert content == load(root/'supervision-reload/content-before.json') == load(root/'supervision-reload/content-after.json')
        assert len([p for p in content if p.endswith('.uasset')]) == 22
        assert observation['result'] == 'pass_resource_and_package_persistence_requires_C2'
    print(json.dumps(dict(format='pr130-I23-parent-replay.v1',
        decision='complete_chain_pass_requires_independent_C2' if passed else 'partial_no_merge',
        unique_input_pins=len(pins), phase_counts=counts, protected_I22_unchanged=True,
        I20_originals_unchanged=len(originals['files']), observation=observation,
        visual_or_runtime_acceptance=False), sort_keys=True, indent=2))
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
