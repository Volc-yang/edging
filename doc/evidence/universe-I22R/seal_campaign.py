"""I22 passive final settlement, run after all root phase parents have exited."""
import json
import sys
import time
from pathlib import Path
from run_phase import ROOT, classify, content_map, lc, prior, sizes, verify


def main():
    started = json.loads((ROOT/'campaign-start.json').read_bytes())['started_monotonic']
    before = json.loads((ROOT/'external-before.json').read_bytes())
    after = prior.external_snapshot()
    prior.save(ROOT/'external-after.json', after)
    changes = []
    for name, old in before['roots'].items():
        current = after['roots'][name]
        for relative in sorted(set(old['entries']) | set(current['entries'])):
            a, b = old['entries'].get(relative), current['entries'].get(relative)
            if a != b:
                changes.append(dict(root=name, relative=relative, before=a, after=b))
    prior.save(ROOT/'external-diff.json', dict(changes=changes,
        limitation='metadata comparison of six declared domains; changed actors are not inferred'))
    phase_records = []
    by_result = {}
    known = {}
    input_errors = []
    for path in sorted(ROOT.glob('supervision-*/execution.json')):
        record = json.loads(path.read_bytes())
        card = json.loads(Path(record['card_ref']['path']).read_bytes())
        verify(record['card_ref'])
        assert card['result_path'] not in by_result
        by_result[card['result_path']] = (record, card)
        for ref in card['input_refs']:
            try:
                verify(ref)
            except Exception as error:
                input_errors.append(str(error))
        for identity in record['known_owned']:
            known[lc.process_key(identity)] = identity
        post = path.parent/'phase-postwrite.json'
        phase_records.append(dict(execution_ref=prior.ref(path), postwrite_ref=prior.ref(post),
            phase=record['phase'], actual_parent_wait_exit=record['actual_parent_wait_exit'],
            forced=record['forced'], normal=record['normal'], successful_local_phase=record['successful_local_phase'],
            readonly_content_ok=record['readonly_content_ok'],
            within_budget_after_execution_saved=json.loads(post.read_bytes())['within_budget_after_execution_saved']))
    final = lc.observe_once(ROOT/'final-processes.ps')
    remaining = classify(final['processes'], list(known.values()))
    reloaded = ROOT/'supervision-reload/execution.json'
    reload_ok = False
    selected_import_ok = False
    selected_probe_ok = False
    selected_content = None
    if reloaded.exists():
        reload_record = json.loads(reloaded.read_bytes())
        reload_card = json.loads(Path(reload_record['card_ref']['path']).read_bytes())
        selected_content = content_map(Path(reload_card['content_root']))
        before_reload = json.loads((reloaded.parent/'content-before.json').read_bytes())
        after_reload = json.loads((reloaded.parent/'content-after.json').read_bytes())
        native_result = json.loads(Path(reload_card['result_path']).read_bytes())
        import_ref = reload_card['prerequisite_ref']
        verify(import_ref)
        imported = json.loads(Path(import_ref['path']).read_bytes())
        selected_import_ok = imported.get('status') == 'PASS' and imported.get('mode') == 'import'
        if import_ref['path'] in by_result:
            import_execution, import_card = by_result[import_ref['path']]
            selected_import_ok = selected_import_ok and import_execution['successful_local_phase']
            probe_ref = import_card['prerequisite_ref']
            verify(probe_ref)
            probe = json.loads(Path(probe_ref['path']).read_bytes())
            if probe_ref['path'] in by_result:
                probe_execution, probe_card = by_result[probe_ref['path']]
                selected_probe_ok = (probe['status'] == 'PASS' and probe['mode'] == 'probe' and
                    probe_execution['successful_local_phase'] and probe_execution['readonly_content_ok'])
        reload_ok = (reload_record['successful_local_phase'] and native_result.get('status') == 'PASS' and
                     selected_content == before_reload == after_reload)
        prior.save(ROOT/'selected-content-final.json', selected_content)
    measured = sizes()
    external_errors = [error for snapshot in (before, after) for data in snapshot['roots'].values() for error in data['errors']]
    resource_ok = (not remaining and not external_errors and not changes and not input_errors and
        all(not p['forced'] and p['within_budget_after_execution_saved'] and p['readonly_content_ok'] for p in phase_records))
    result = dict(format='universe-i22-campaign-seal.v1', phase_records=phase_records,
        external_diff_ref=prior.ref(ROOT/'external-diff.json'), final_ps_ref=final['raw_ref'], remaining=remaining,
        input_errors=input_errors, external_errors=external_errors, actual_sizes_before_seal=measured,
        campaign_elapsed_before_seal=time.monotonic()-started, reload_content_and_local_report_pass=reload_ok,
        process_and_declared_domain_check=resource_ok, selected_import_ok=selected_import_ok, selected_probe_ok=selected_probe_ok,
        native_acceptance='requires_independent_C2; no runtime, build or visual grant')
    prior.save(ROOT/'campaign-seal.json', result)
    # Deliberately observe after the final fsync; no further run-root write follows.
    observed = sizes()
    elapsed = time.monotonic()-started
    passed = resource_ok and reload_ok and selected_import_ok and selected_probe_ok and elapsed <= 1200 and observed['root_bytes'] <= 4*1024**3 and observed['content_bytes'] <= 512*1024**2
    print(json.dumps(dict(format='universe-i22-post-seal-observation.v1',
        seal_ref=prior.ref(ROOT/'campaign-seal.json'), observed_after_final_fsync=True,
        actual_sizes=observed, continuous_elapsed_seconds=elapsed,
        result='pass_resource_and_package_persistence_requires_C2' if passed else 'partial_or_fail',
        native_runtime_build_visual_acceptance=False), indent=2), flush=True)
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
