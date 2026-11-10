"""Bounded I20 parent check: source bytes, reviewed contracts and integration.

Does not import product code, start UE, read owner/key files or write asset inputs.
Run from the integrated repository with a fresh output directory.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    repo = Path(__file__).resolve().parents[3]
    out = Path(sys.argv[1]).resolve()
    out.mkdir(exist_ok=False)
    checks = []

    def git(*args):
        return subprocess.check_output(['git', *args], cwd=repo)

    def record(name, **details):
        checks.append(dict(check=name, result='pass', **details))

    def verify_ref(ref, path_key='repository_path'):
        raw = (repo / ref[path_key]).read_bytes()
        assert sha(raw) == ref['sha256'], ref[path_key]
        if 'bytes' in ref:
            assert len(raw) == ref['bytes'], ref[path_key]

    head = git('rev-parse', 'HEAD').decode().strip()
    # Exact reviewed delivery bytes, including C's original cherry-picked report.
    sources = {
        '30907e8dd645cb1b7c3580cf101f180b77b47865': [
            'doc/design/universe-i20-asset-profile.md', 'doc/evidence/universe-I20A'],
        'd6fe60de9c3ad9fad837841f2bd3bfb027a90896': [
            'doc/design/universe-realistic-presentation-profile.md',
            'doc/evidence/universe-I20B',
            'doc/fixtures/universe_realistic_presentation_profile_v0_1'],
        '3627af2df70bee1b05ab824640e535742f0e7ea9': ['doc/evidence/universe-I20C'],
    }
    counts = {}
    for commit, scopes in sources.items():
        paths = git('ls-tree', '-r', '--name-only', commit, '--', *scopes).decode().splitlines()
        assert paths
        for relative in paths:
            assert (repo / relative).read_bytes() == git('show', commit + ':' + relative), relative
        counts[commit] = len(paths)
    record('reviewed_delivery_bytes_equal', files_by_source=counts)
    changed = git('diff', '--name-only', 'e76f4b6', 'HEAD').decode().splitlines()
    assert all(p.startswith('doc/') for p in changed)
    record('integration_changes_documentation_only', tracked_paths=len(changed))

    plan_review = json.loads((repo / 'doc/evidence/universe-I20C/plan-review.json').read_bytes())
    verify_ref(plan_review['plan_ref'])
    record('frozen_reviewed_plan_bytes_unchanged')
    cross = json.loads((repo / 'doc/evidence/universe-I20C/cross-input-review.json').read_bytes())
    for ref in [cross['A']['evidence'], cross['B']['evidence'], cross['B']['pre_fix_failure'], *cross['evidence']]:
        verify_ref(ref)
    record('independent_review_artifact_hashes')

    index_path = repo / 'doc/evidence/universe-I20A/asset-index.json'
    assert sha(index_path.read_bytes()) == cross['cross_checks']['same_fixed_A_asset_index_sha256']
    phase = json.loads((repo / 'doc/evidence/universe-I20A/phased-source-provenance.json').read_bytes())
    for item in phase['phases']:
        verify_ref(item['immutable_receipt'])
        verify_ref(item['preserved_source'])
        assert sha(git('show', item['preserved_source']['git_object_ref'])) == item['preserved_source']['sha256']
    record('durable_index_and_two_phase_git_provenance')
    prior = json.loads((repo / 'doc/evidence/universe-I20R/integration-source-receipt.json').read_bytes())
    assert sha((repo / 'doc/evidence/universe-I20R/integration-source-check.json').read_bytes()) == prior['raw_output_sha256']
    tree_path = repo / 'doc/evidence/universe-I20R/integration-source-index.json'
    assert sha(tree_path.read_bytes()) == prior['tree_index_sha256']
    tree = json.loads(tree_path.read_bytes())
    source_root = Path(phase['durable_asset_input']['asset_root'])
    assert source_root.is_dir() and not source_root.is_symlink()
    expected_paths = set()
    for item in tree['files']:
        path = Path(item['path'])
        path.relative_to(source_root)
        assert not path.is_symlink() and stat.S_ISREG(path.lstat().st_mode)
        raw = path.read_bytes()
        assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], str(path)
        expected_paths.add(str(path))
    actual_paths = set()
    walk_errors = []
    for parent, dirs, files in os.walk(source_root, followlinks=False, onerror=lambda e: walk_errors.append(str(e))):
        assert all(not (Path(parent) / name).is_symlink() for name in dirs)
        actual_paths.update(str(Path(parent) / name) for name in files)
    assert not walk_errors and actual_paths == expected_paths
    record('all_durable_source_files_still_equal_root_verified_index', files=len(actual_paths))

    owner = json.loads((repo / 'doc/evidence/universe-I20B/cpu-result.json').read_bytes())
    for ref in owner['artifacts']:
        verify_ref(ref, 'path')
    assert sha((repo / 'doc/evidence/universe-I20B/cpu-check.txt').read_bytes()) == owner['stdout_stderr_sha256']
    record('B_final_owner_receipt_matches_integrated_bytes')
    command = ['/private/tmp/edgeworld-i20b-contract-env/bin/python', '-B', 'doc/evidence/universe-I20B/check_contract.py']
    start = time.monotonic()
    child = subprocess.run(command, cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    duration = time.monotonic() - start
    (out / 'contract-check.txt').write_bytes(child.stdout)
    assert child.returncode == 0 and b'Ran 15 tests' in child.stdout and child.stdout.rstrip().endswith(b'OK')
    record('B_integrated_synthetic_contract_15_tests', command=command, actual_parent_wait_exit=child.returncode,
           wall_seconds=duration, raw_output_sha256=sha(child.stdout))
    result = dict(format='universe-i20-parent-integration-check.v1', integration_commit=head,
                  checker_sha256=sha(Path(__file__).read_bytes()), checks=checks,
                  result='pass_bounded_source_and_synthetic_contract_only',
                  actual_UE_import=False, build=False, runtime=False, visual_acceptance=False)
    (out / 'integration-check.json').write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
