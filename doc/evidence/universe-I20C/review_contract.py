"""Independent directed I20B CPU checks; does not instantiate a runtime renderer."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import time


def sha(raw): return hashlib.sha256(raw).hexdigest()


def run(repo, out, attempt):
    repo, out = Path(repo).resolve(), Path(out).resolve()
    path = repo/'doc/evidence/universe-I20B/check_contract.py'
    head = subprocess.check_output(['git','rev-parse','HEAD'], cwd=repo, text=True).strip()
    started = time.monotonic()
    check = subprocess.run([sys.executable,'-B',str(path)], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    raw = check.stdout
    (out/(attempt+'-owner-checks.txt')).write_bytes(raw)
    spec = importlib.util.spec_from_file_location('i20b_contract', path)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    checks = []
    t = m.ContractChecks('test_positive_real_temp_bytes_and_binding_are_only_consistency'); t.setUp()
    def reject(name, operation):
        try: operation()
        except (m.ContractError, OSError) as error:
            checks.append({'case': name, 'result': 'pass_rejected', 'reason': str(error)})
        else: checks.append({'case': name, 'result': 'FAIL_ACCEPTED'})
    try:
        # State and Event are independently mismatched, in addition to owner time/world checks.
        for field in ('state', 'event'):
            binding = t.binding(); binding[field] = 'a'*64
            reject('mismatched_'+field, lambda b=binding: m.validate_view_binding(
                b, profile_sha256=t.write(), expected_observation=t.expected['observation'],
                expected_renderer_build_sha256=t.expected['renderer_build_sha256']))
        p = deepcopy(t.p); p['evidence_class'] = 'native-observed-proposal'
        # Native-looking metadata remains only a synthetic consistency proposal.
        evidence = b'not genuine UE; synthetic reviewer consistency proposal only'
        (t.root/'native.fixture').write_bytes(evidence)
        for asset in p['assets']:
            asset['native_import'] = dict(status='native-observed', source_unit_cm=None, pivot_cm=None,
                bounds_cm=None, material_slots=[], evidence_ref=dict(path='native.fixture', sha256=sha(evidence)))
            if asset['kind'] == 'static_mesh':
                asset['native_import'].update(source_unit_cm=100, pivot_cm=[0,0,0],
                    bounds_cm=[0,0,0,1,1,1], material_slots=['surface'])
        result = t.check(p)
        assert not result['runtime_authenticity_verified'] and not result['license_authenticity_verified']
        checks.append({'case': 'native_shaped_proposal_is_not_native_authentication', 'result': 'pass', 'observed': result})
        wrong_slots = deepcopy(p); wrong_slots['assets'][0]['native_import']['material_slots'] = ['other-slot']
        reject('native_declared_slot_mismatch', lambda: t.check(wrong_slots))
        # Valid JSON exponent overflow must not become infinite import dimensions.
        overflow = deepcopy(p)
        for asset in overflow['assets']:
            if asset['kind'] == 'static_mesh':
                asset['native_import'].update(source_unit_cm=float('inf'), pivot_cm=[0,0,float('inf')],
                    bounds_cm=[0,0,0,float('inf'),1,1])
        raw_overflow = (json.dumps(overflow, indent=2)+'\n').encode().replace(b'Infinity', b'1e999')
        t.path.write_bytes(raw_overflow)
        (out/(attempt+'-overflow-synthetic.json')).write_bytes(raw_overflow)
        reject('json_exponent_overflow_native_metadata', lambda: m.validate_profile(
            t.path, file_root=t.root, expected_profile_sha256=sha(raw_overflow), expected_authority=t.expected['authority']))
    finally: t.tearDown()
    source_paths = [path, *sorted(m.FIXTURES.glob('*.json'))]
    result = {'format': 'universe-i20-independent-contract-review.v1', 'reviewed_commit': head,
        'attempt': attempt, 'python': sys.executable, 'owner_command_exit': check.returncode,
        'owner_output_sha256': sha(raw), 'elapsed_seconds': time.monotonic()-started,
        'source_sha256': {str(p.relative_to(repo)): sha(p.read_bytes()) for p in source_paths},
        'directed_independent_checks': checks,
        'result': 'pass_design_cpu_only' if check.returncode==0 and all(c['result'].startswith('pass') for c in checks) else 'changes_requested',
        'native_runtime_ue_import_appearance_atomicity_verified': False}
    (out/(attempt+'-independent-review.json')).write_text(json.dumps(result, indent=2, sort_keys=True)+'\n')
    print(json.dumps({'reviewed_commit': head, 'result':result['result'], 'owner_exit':check.returncode,
                      'directed':[(c['case'],c['result']) for c in checks]}, indent=2))


if __name__ == '__main__': run(*sys.argv[1:])
