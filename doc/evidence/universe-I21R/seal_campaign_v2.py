"""I21 passive final settlement, run after all root phase parents have exited."""
import json
import sys
import time
from pathlib import Path
from run_phase_v2 import ROOT, classify, content_map, lc, prior, sizes, verify


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
    known = {}
    input_errors = []
    for path in sorted(ROOT.glob('supervision-*/execution.json')):
        record = json.loads(path.read_bytes())
        card = json.loads(Path(record['card_ref']['path']).read_bytes())
        verify(record['card_ref'])
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
            forced=record['forced'], normal=record['normal'],
            within_budget_after_execution_saved=json.loads(post.read_bytes())['within_budget_after_execution_saved']))
    final = lc.observe_once(ROOT/'final-processes.ps')
    remaining = classify(final['processes'], list(known.values()))
    reloaded = ROOT/'supervision-reload/execution.json'
    reload_ok = False
    selected_content = None
    if reloaded.exists():
        reload_record = json.loads(reloaded.read_bytes())
        reload_card = json.loads(Path(reload_record['card_ref']['path']).read_bytes())
        selected_content = content_map(Path(reload_card['content_root']))
        before_reload = json.loads((reloaded.parent/'content-before.json').read_bytes())
        after_reload = json.loads((reloaded.parent/'content-after.json').read_bytes())
        native_result = json.loads(Path(reload_card['result_path']).read_bytes())
        reload_ok = (reload_record['normal'] and native_result.get('status') == 'PASS' and
                     selected_content == before_reload == after_reload)
        prior.save(ROOT/'selected-content-final.json', selected_content)
    measured = sizes()
    external_errors = [error for snapshot in (before, after) for data in snapshot['roots'].values() for error in data['errors']]
    resource_ok = (not remaining and not external_errors and not changes and not input_errors and
        all(not p['forced'] and p['within_budget_after_execution_saved'] for p in phase_records))
    result = dict(format='universe-i21-campaign-seal.v1', phase_records=phase_records,
        external_diff_ref=prior.ref(ROOT/'external-diff.json'), final_ps_ref=final['raw_ref'], remaining=remaining,
        input_errors=input_errors, external_errors=external_errors, actual_sizes_before_seal=measured,
        campaign_elapsed_before_seal=time.monotonic()-started, reload_content_and_local_report_pass=reload_ok,
        process_and_declared_domain_check=resource_ok,
        native_acceptance='requires_independent_C2; no runtime, build or visual grant')
    prior.save(ROOT/'campaign-seal.json', result)
    # Deliberately observe after the final fsync; no further run-root write follows.
    observed = sizes()
    elapsed = time.monotonic()-started
    passed = resource_ok and reload_ok and elapsed <= 900 and observed['root_bytes'] <= 4*1024**3 and observed['content_bytes'] <= 512*1024**2
    print(json.dumps(dict(format='universe-i21-post-seal-observation.v1',
        seal_ref=prior.ref(ROOT/'campaign-seal.json'), observed_after_final_fsync=True,
        actual_sizes=observed, continuous_elapsed_seconds=elapsed,
        result='pass_resource_and_package_persistence_requires_C2' if passed else 'partial_or_fail',
        native_runtime_build_visual_acceptance=False), indent=2), flush=True)
    return 0 if passed else 2


if __name__ == '__main__':
    raise SystemExit(main())
