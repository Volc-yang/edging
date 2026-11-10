"""Read-only independent review of I21's sealed failed run; never launches UE."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys


def sha(raw): return hashlib.sha256(raw).hexdigest()


def run(repo, output):
    repo, output = Path(repo).resolve(), Path(output).resolve()
    root = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I21-20261110-import')
    evidence = repo/'doc/evidence/universe-I21R'
    def load(path): return json.loads(Path(path).read_bytes())
    def ref(path):
        path = Path(path); raw = path.read_bytes()
        return dict(path=str(path), bytes=len(raw), sha256=sha(raw))
    # Import passive process parsing helpers only. main() is never called.
    spec = importlib.util.spec_from_file_location('i21_passive_evidence_reader', evidence/'run_phase_v2.py')
    helper = importlib.util.module_from_spec(spec); spec.loader.exec_module(helper)
    checked = {}; phases = []; raw_refs = []
    for name in ('import-01', 'import-02'):
        path = root/('supervision-'+name)/'execution.json'; record = load(path)
        card_ref = record['card_ref']; card_path = Path(card_ref['path'])
        assert ref(card_path)['sha256'] == card_ref['sha256']
        card = load(card_path)
        for source in card['input_refs']:
            if source['path'] in checked:
                assert checked[source['path']] == source['sha256']
                continue
            actual = ref(source['path']); assert actual['sha256'] == source['sha256'], source['path']
            checked[source['path']] = actual['sha256']
        quiet = []
        for sample in record['quiet_samples']:
            path_ps = Path(sample['raw_ref']['path']); raw = path_ps.read_bytes()
            assert sha(raw) == sample['raw_ref']['sha256']
            rows = helper.lc.parse_ps_snapshot(raw.decode())
            relevant = helper.classify(rows, record['known_owned']); assert not relevant
            quiet.append(dict(raw_ref=ref(path_ps), independently_parsed_relevant=0))
        assert not record['normal'] and not record['final_errors']
        phases.append(dict(phase=name, actual_parent_wait_exit=record['actual_parent_wait_exit'],
            forced=record['forced'], normal=record['normal'], error=record['error'],
            runtime_seconds=record['ended_monotonic']-record['started_monotonic'],
            input_pins=len(card['input_refs']), quiet=quiet, execution_ref=ref(path)))
        for leaf in ('execution.json','phase-postwrite.json','console.log'):
            raw_refs.append(ref(path.parent/leaf))
    assert phases[0]['actual_parent_wait_exit'] == 0 and phases[0]['forced']
    assert phases[1]['actual_parent_wait_exit'] == 255 and not phases[1]['forced']
    failure = load(root/'a2/result.json')
    assert failure['status']=='FAIL' and failure['pid']==load(root/'supervision-import-02/execution.json')['pid']
    assert failure['error']=="'NoneType' object has no attribute 'enable_section_collision'"
    console = (root/'supervision-import-02/console.log').read_text()
    assert 'line 245, in do_import' in console and 'subsystem.enable_section_collision' in console
    assert 'Running Python script:' in console and 'Commandlet->Main return this error code: -1' in console
    assert 'I21_NATIVE_RESULT_PASS' not in console
    assert 'Trace.uba with size 328b' in (root/'supervision-import-01/console.log').read_text()
    completed_imports = [line for line in console.splitlines() if 'Interchange import completed [' in line]
    assert len(completed_imports)==16
    # Verify the two actual project Content trees; DDC's Content folder is separate.
    project_content = {}
    for attempt in ('a1','a2'):
        content = root/attempt/'host/Content'; assert content.is_dir()
        project_content[attempt] = helper.content_map(content); assert not project_content[attempt]
    regular = {}; named_content = {}; errors = []
    for parent, dirs, files in os.walk(root, followlinks=False, onerror=errors.append):
        for name in dirs: assert not (Path(parent)/name).is_symlink()
        for name in files:
            path = Path(parent)/name; current = path.lstat(); assert stat.S_ISREG(current.st_mode)
            relative = str(path.relative_to(root)); regular[relative]=current.st_size
            if 'Content' in path.relative_to(root).parts: named_content[relative]=current.st_size
    assert not errors
    assert len(named_content)==2 and all(p.startswith('a2/ddc/Content/') and p.endswith('.udd') for p in named_content)
    assert sum(named_content.values())==2679781
    # Compare all 34 original I20 files, including metadata and license evidence.
    baseline = load(repo/'doc/evidence/universe-I20R/integration-source-index.json')
    for original in baseline['files']:
        actual = ref(original['path']); assert actual['bytes']==original['bytes'] and actual['sha256']==original['sha256']
    assert len(baseline['files'])==34
    # Independently reproduce declared-domain metadata differences.
    before, after = load(root/'external-before.json'), load(root/'external-after.json')
    changes = []; existence = []
    for domain, previous in before['roots'].items():
        current = after['roots'][domain]; assert not previous['errors'] and not current['errors']
        if previous['exists'] != current['exists']: existence.append(domain)
        for relative in sorted(set(previous['entries']) | set(current['entries'])):
            a,b=previous['entries'].get(relative),current['entries'].get(relative)
            if a!=b:changes.append(dict(root=domain,relative=relative,before=a,after=b))
    assert not existence and changes==load(root/'external-diff.json')['changes'] and len(changes)==3
    assert all(x['root'].endswith('/UnrealBuildTool') for x in changes)
    seal = load(root/'campaign-seal.json'); assert not seal['process_and_declared_domain_check']
    assert not seal['reload_content_and_local_report_pass'] and not seal['input_errors'] and not seal['external_errors']
    raw = Path(seal['final_ps_ref']['path']).read_bytes(); assert sha(raw)==seal['final_ps_ref']['sha256']
    known = [row for name in ('import-01','import-02') for row in load(root/('supervision-'+name)/'execution.json')['known_owned']]
    assert not helper.classify(helper.lc.parse_ps_snapshot(raw.decode()),known)
    post = load(evidence/'post-seal-tool-observation.json')
    provenance = load(evidence/'post-seal-tool-provenance.json')
    assert post['observed_after_final_fsync'] and post['seal_ref']['sha256']==sha((root/'campaign-seal.json').read_bytes())
    assert post['continuous_elapsed_seconds']<=900 and post['result']=='partial_or_fail' and provenance['actual_exit_code']==2
    assert sum(regular.values())==post['actual_sizes']['root_bytes']<=4*1024**3
    assert sum(named_content.values())==post['actual_sizes']['content_bytes']<=512*1024**2
    copies=load(evidence/'runtime-evidence-index.json')
    for item in copies['files']:
        source=Path(item['source']).read_bytes();copy=(repo/item['repository_path']).read_bytes()
        assert source==copy and len(source)==item['bytes'] and sha(source)==item['sha256']
    assert not (root/'supervision-reload').exists() and not (root/'reload').exists()
    raw_refs.extend(ref(root/p) for p in ('a1/ue.log','a2/ue.log','a2/result.json','campaign-seal.json','external-before.json','external-after.json','external-diff.json','final-processes.ps'))
    result=dict(format='universe-i21-C2-independent-failed-run-review.v1',
        decision='reject_complete_D3_IMPORT_accept_preserved_partial_cycle_evidence',
        runtime_owner_source_commit='3b156d51cc9df110e5ef24e0be82618d54e2eb5b',
        post_run_guard_only_commit='a0ebfbf3c4830b622b63164a3bfee56afbb338d7',
        post_run_guard_native_executed=False, phases=phases, unique_input_pins_rehashed=len(checked),
        original_I20_files_unchanged=34, actual_root_file_count=len(regular),
        actual_root_bytes=sum(regular.values()), actual_saved_project_Content=project_content,
        conservative_named_Content_bytes=sum(named_content.values()), named_Content_files=named_content,
        actual_saved_uasset_packages=0, actual_completed_Interchange_import_logs=16,
        material_and_mesh_gate='not accepted; error before explicit save and Native validation',
        failure=failure, external_metadata_changes=changes,
        external_scope='six declared metadata domains only; no full-system no-write claim',
        final_ps_reparsed_relevant=0, final_seal_ref=ref(root/'campaign-seal.json'),
        actual_post_fsync_observation=post, post_fsync_capture_provenance_ref=ref(evidence/'post-seal-tool-provenance.json'),
        repository_runtime_copies_byte_equal=len(copies['files']), raw_refs=raw_refs,
        gates=dict(C0_plan='accepted',C1_source_CPU_and_cards='accepted',
            positive_saved_package_import='fail',fresh_process_reload='not_run',
            Native_metadata_material_negative_checks='not_run',
            continuous_wall_and_file_byte_caps='pass_bounded_only',
            normal_successful_exit='fail',declared_external_write_boundary='fail',
            D3_IMPORT='not_accepted',D3_ADAPTER_BUILD_D4='not_run'),
        next_entry='new reviewed cycle: activate owning StaticMeshEditor module if appropriate, verify actual subsystem/getter capability before mutation; freeze Nanite source-vs-render-fallback policy and retest saved import plus fresh reload',
        reviewer_UE_GPU_worker_Genesis_UI_executed=False)
    (output/'c2-run-review.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:result[k] for k in ('decision','unique_input_pins_rehashed','original_I20_files_unchanged','actual_root_file_count','actual_root_bytes','actual_saved_uasset_packages','actual_completed_Interchange_import_logs','repository_runtime_copies_byte_equal','gates')},indent=2))


if __name__=='__main__': run(*sys.argv[1:])
