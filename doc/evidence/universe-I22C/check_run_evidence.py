"""Independent passive I22 review. Never dispatch UE or write the sealed run root."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


def run(repo, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    root = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I22-20261110-import')
    evidence = repo/'doc/evidence/universe-I22R'

    def load(path): return json.loads(Path(path).read_bytes())
    def ref(path):
        path = Path(path)
        raw = path.read_bytes()
        return dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    def verify(row):
        actual = ref(row['path'])
        assert actual['sha256'] == row['sha256'], row['path']
        return actual

    # Import passive parsing/classification only; its main() is never called.
    sys.path.insert(0, str(evidence))
    spec = importlib.util.spec_from_file_location('i22_passive_evidence_reader', evidence/'run_phase.py')
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    phases, checked, raw_refs, known = [], {}, [], []
    expected = {'probe-01': ('p1', 255, 'FAIL'), 'probe-02': ('p2', 0, 'PASS')}
    for phase, (session, code, status) in expected.items():
        supervision = root/('supervision-'+phase)
        execution = load(supervision/'execution.json')
        card = load(execution['card_ref']['path'])
        verify(execution['card_ref'])
        for row in card['input_refs']:
            if row['path'] in checked:
                assert checked[row['path']] == row['sha256']
            else:
                verify(row)
                checked[row['path']] = row['sha256']
        result_path = root/session/'result.json'
        result = load(result_path)
        assert execution['result_ref']['sha256'] == ref(result_path)['sha256']
        assert execution['actual_parent_wait_exit'] == code and not execution['forced']
        assert result['status'] == status and result['pid'] == execution['pid']
        assert result['job_sha256'] == card['job_ref']['sha256']
        assert execution['normal'] == (code == 0)
        assert execution['successful_local_phase'] == (status == 'PASS')
        assert not execution['final_errors'] and not execution['cleanup']
        assert execution['input_refs_rechecked'] and execution['report_identity_ok']
        assert execution['final_budget_ok'] and execution['readonly_content_ok']
        assert load(supervision/'content-before.json') == load(supervision/'content-after.json') == {}
        post = load(supervision/'phase-postwrite.json')
        assert post['execution_ref']['sha256'] == ref(supervision/'execution.json')['sha256']
        assert post['observed_after_execution_fsync'] and post['within_budget_after_execution_saved']
        invocation = load(supervision/'invocation.json')
        assert invocation['argv'] == card['argv'] and invocation['environment'] == card['environment']
        assert invocation['cwd'] == card['cwd']
        for sample in execution['samples']:
            verify(sample['ps_ref'])
        quiet = []
        for sample in execution['quiet_samples']:
            verify(sample['raw_ref'])
            rows = helper.lc.parse_ps_snapshot(Path(sample['raw_ref']['path']).read_text())
            assert not helper.classify(rows, execution['known_owned'])
            quiet.append(sample['raw_ref'])
        known.extend(execution['known_owned'])
        console = (supervision/'console.log').read_text(errors='replace')
        ue_log = (root/session/'ue.log').read_text(errors='replace')
        assert 'Running Python script:' in console
        if status == 'FAIL':
            assert result['error'] == 'transient texture flags/dimensions did not restore'
            assert 'I22_NATIVE_RESULT_PASS' not in console
        else:
            # LogPython's ordinary output is in abslog; Display output also reaches console.
            assert 'I22_NATIVE_RESULT_PASS' in ue_log
            assert 'Python script executed successfully' in console
            capability = result['capability']
            assert capability['complete']
            assert capability['mesh_before'] == capability['mesh_restored']
            assert len(capability['texture_restoration']) == 3
            assert all(x['before'] == x['after'] and x['diff'] == {} for x in capability['texture_restoration'])
            assert capability['original_fixture_getters_before'] == capability['original_fixture_getters_after']
            assert capability['actual_alpha_disconnected'] and capability['actual_alpha_restored']
            assert capability['pipeline_observed']['build_nanite'] is False
            assert capability['pipeline_observed']['collision'] is False
            for path, digest in capability['fixture_file_sha256'].items():
                assert ref(path)['sha256'] == digest
            assert result['content_files'] == {}
        phases.append(dict(phase=phase, status=status, actual_parent_wait_exit=code,
            forced=False, normal=execution['normal'], execution_ref=ref(supervision/'execution.json'),
            result_ref=ref(result_path), quiet_raw_ps_independently_parsed=quiet,
            observed_campaign_elapsed=post['campaign_elapsed_seconds']))
        raw_refs.extend(ref(supervision/leaf) for leaf in ('execution.json', 'phase-postwrite.json', 'console.log'))
        raw_refs.extend((ref(result_path), ref(root/session/'ue.log')))

    assert sorted(p.parent.name for p in root.glob('supervision-*/execution.json')) == ['supervision-probe-01', 'supervision-probe-02']
    assert not (root/'supervision-import-01').exists() and not (root/'supervision-import-02').exists()
    assert not (root/'supervision-reload').exists() and not (root/'reload').exists()
    content = {name: helper.content_map(root/name/'host/Content') for name in ('p1', 'p2', 'a1', 'a2')}
    assert all(value == {} for value in content.values())
    assert not (root/'a1/result.json').exists() and not (root/'a2/result.json').exists()
    prepared_card = evidence/'import-02-card.json'
    assert ref(prepared_card)['sha256'] == 'f2eb47cf8a403e7784cf0456f1becb4248d5a4f73bc5ab32e99cc081202ef6a1'
    assert load(prepared_card)['prerequisite_ref']['sha256'] == ref(root/'p2/result.json')['sha256']

    baseline = load(repo/'doc/evidence/universe-I20R/integration-source-index.json')
    for original in baseline['files']:
        actual = ref(original['path'])
        assert actual['bytes'] == original['bytes'] and actual['sha256'] == original['sha256']
    assert len(baseline['files']) == 34

    before, after = load(root/'external-before.json'), load(root/'external-after.json')
    assert before['roots'].keys() == after['roots'].keys() and len(before['roots']) == 6
    for name, previous in before['roots'].items():
        current = after['roots'][name]
        assert not previous['errors'] and not current['errors']
        assert previous['exists'] == current['exists'] and previous['entries'] == current['entries']
    assert load(root/'external-diff.json')['changes'] == []
    seal = load(root/'campaign-seal.json')
    assert ref(root/'campaign-seal.json')['sha256'] == '89c19c9c6b745f41eed7042064515cbd7d4b176f063408235c2dab5df5c9f144'
    assert seal['process_and_declared_domain_check'] and not seal['remaining']
    assert not seal['input_errors'] and not seal['external_errors']
    assert not seal['selected_import_ok'] and not seal['reload_content_and_local_report_pass']
    # selected_probe_ok describes a full reload->import->probe chain, absent this cycle.
    assert not seal['selected_probe_ok']
    verify(seal['final_ps_ref'])
    rows = helper.lc.parse_ps_snapshot(Path(seal['final_ps_ref']['path']).read_text())
    assert not helper.classify(rows, known)

    observation = load(evidence/'post-seal-observation.json')
    assert observation['observed_after_final_fsync']
    assert observation['seal_ref']['sha256'] == ref(root/'campaign-seal.json')['sha256']
    assert observation['result'] == 'partial_or_fail'
    assert observation['continuous_elapsed_seconds'] <= 1200
    assert observation['actual_sizes']['root_bytes'] == 27805158
    files, errors = {}, []
    for parent, dirs, names in os.walk(root, followlinks=False, onerror=errors.append):
        assert all(not (Path(parent)/name).is_symlink() for name in dirs)
        for name in names:
            path = Path(parent)/name
            info = path.lstat()
            assert stat.S_ISREG(info.st_mode)
            files[str(path.relative_to(root))] = info.st_size
    assert not errors and sum(files.values()) == observation['actual_sizes']['root_bytes']
    assert sum(files.values()) <= 4*1024**3
    assert not any(path.endswith(('.uasset', '.ubulk', '.uexp', '.uptnl')) for path in files)
    assert observation['actual_sizes']['content_bytes'] == 0
    raw_refs.extend(ref(root/name) for name in ('campaign-seal.json','external-before.json','external-after.json','external-diff.json','final-processes.ps'))
    result = dict(format='universe-i22-C2-independent-partial-cycle-review.v1',
        decision='accept_bounded_partial_cycle_evidence_reject_complete_D3_IMPORT',
        phases=phases, unique_runtime_input_pins_rehashed=len(checked), original_I20_files_unchanged=34,
        actual_root_file_count=len(files), actual_root_bytes=sum(files.values()),
        actual_project_Content=content, actual_saved_uasset_packages=0,
        import_02_card_ref=ref(prepared_card), import_02_status='prepared_only; not_C1_accepted; NO_GO; not_dispatched',
        import_02_no_go_reason='Remaining 130.8s below 120s phase plus 30s seal reserve; no further reduction or clock reset',
        post_fsync_observation=observation, declared_external_metadata_domains_unchanged=6,
        final_ps_reparsed_relevant=0, final_seal_ref=ref(root/'campaign-seal.json'), raw_refs=raw_refs,
        gates=dict(C0_plan='accepted', C1_source_CPU_probe_cards='accepted',
            probe01_capability='fail_preserved', probe02_native_capability='pass_limited_fixture_scope',
            positive_saved_package_import='not_run_NO_GO', fresh_process_reload='not_run',
            Native_I20_material_and_mesh_negatives='not_run', normal_successful_probe02_exit='pass',
            continuous_wall_and_file_caps='pass_bounded_only', declared_external_write_boundary='pass_six_domains_only',
            D3_IMPORT='not_accepted', runtime_build_Metal_visual='not_run'),
        next_entry='new reviewed bounded import/reload cycle from source877696e with p2 provenance preserved; do not reset/reuse sealed I22 clock or grant import via capability evidence',
        reviewer_UE_GPU_worker_Genesis_UI_executed=False, reviewer_DevSSD_write=False)
    (output/'c2-run-review.json').write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({key: result[key] for key in ('decision','unique_runtime_input_pins_rehashed','actual_root_file_count','actual_root_bytes','actual_saved_uasset_packages','gates')}, indent=2))


if __name__ == '__main__':
    run(*sys.argv[1:])
