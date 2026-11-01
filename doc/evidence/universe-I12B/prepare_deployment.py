#!/usr/bin/env python3
"""Explicit I12B-PREP CPU deployment only; never launches solver/UE/launcher.

Audit accepted source/native bytes before provisioning a NEW trust anchor. Keys
are generated/written by provision(), never opened/copied/hashed by this helper.
Output/root names are exclusive; a failure remains for root review, not retry.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

REPO = Path(__file__).resolve().parents[3]
BASE = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld')
APPROVED = BASE / 'I11B-20261102-persistent-owner-bundle'
RAW = BASE / 'I10B-20261102-runtime-attempt2-topological'
WORLD = 'edgeworld-i12b-20261102'
PREFIX = b'edgeworld.universe.authority\0v0.2\0'
START = time.monotonic()


def require(value, message):
    if not value:
        raise RuntimeError(message)


def pack(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024**2), b''):
            h.update(block)
    return h.hexdigest()


def digest(record):
    return hashlib.sha256(PREFIX + pack(record)).hexdigest()


def load(path):
    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, 'duplicate metadata key')
            result[key] = value
        return result
    return json.loads(Path(path).read_bytes(), object_pairs_hook=pairs)


def write(path, value=None, *, raw=None):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(pack(value) if raw is None else raw)
        stream.flush(); os.fsync(stream.fileno())


def metadata(path):
    value = path.lstat()
    return dict(path=str(path), uid=value.st_uid, mode=oct(stat.S_IMODE(value.st_mode)),
                nlink=value.st_nlink, bytes=value.st_size, dev=value.st_dev, inode=value.st_ino,
                symlink=stat.S_ISLNK(value.st_mode))


def no_runtime():
    require(not any(name == 'genesis' or name.startswith('genesis.') for name in sys.modules),
            'Genesis import is forbidden in PREP')


def audit(out):
    no_runtime()
    original = {role: load(APPROVED / (role + '.json')) for role in ('build', 'options', 'assets', 'asset_audit')}
    provenance = load(APPROVED / 'rebind-metadata.json')['sources']
    for role in original:
        require(sha(APPROVED / (role + '.json')) == provenance[role]['sha256'], 'approved origin SHA: ' + role)
    pins = load(APPROVED / 'public-pins.json')
    require(digest(original['build']) == pins['expected_build'] and
            digest(original['options']) == pins['expected_options'], 'approved B/O provenance digests')
    body = original['build']['body']
    require(sha(REPO / 'engine/universe_authority/genesis_adapter.py') == body['adapter_source_sha256'],
            'adapter differs; requires root new-bootstrap decision')
    source_proof = []
    for old, spec in load(RAW / 'source-inputs.json').items():
        if '/engine/universe_authority/' in old:
            path = REPO / 'engine/universe_authority' / Path(old).name
            require(sha(path) == spec['sha256'] == sha(RAW / spec['copy']), 'authority module differs: ' + path.name)
            source_proof.append(dict(path=str(path), sha256=sha(path), accepted_copy=str(RAW / spec['copy'])))
    installed = load(RAW / 'installed-sources.json')
    native = load(RAW / 'native-before.json')
    require(native == load(RAW / 'native-after.json'), 'accepted native before/after conflict')
    package = Path(next(p for p in native if p.endswith('/genesis_world-1.4.3.dist-info/METADATA'))).parent.parent / 'genesis'
    current = [dict(path=p.relative_to(package).as_posix(), sha256=sha(p)) for p in sorted(package.rglob('*.py'))]
    require(current == installed and len(current) == body['source_file_count'] == 264 and
            hashlib.sha256(pack(current)).hexdigest() == body['source_tree_sha256'], 'installed package sources differ')
    lookup = {row['path']: row['sha256'] for row in current}
    require(all(lookup[row['path']] == row['sha256'] for row in body['critical_sources']), 'critical sources differ')
    measured_native = {}
    for path, spec in native.items():
        require(Path(path).is_file() and Path(path).stat().st_size == spec['bytes'] and
                sha(path) == spec['sha256'], 'native/METADATA differs: ' + Path(path).name)
        measured_native[path] = dict(spec)
    invocation = load(RAW / 'invocation.json')
    accepted_executable = Path(invocation['executable'])
    require(sha(accepted_executable.resolve()) == invocation['executable_sha256'],
            'accepted Python canonical binary differs')
    chain = []
    # Record every symlink component, including the Homebrew opt directory.
    path = accepted_executable.absolute()
    for _ in range(20):
        found = False
        for component in reversed((path, *path.parents)):
            if component.is_symlink():
                target = os.readlink(component)
                chain.append(dict(path=str(component), readlink=target))
                replacement = Path(target) if Path(target).is_absolute() else component.parent / target
                path = Path(os.path.normpath(str(replacement / path.relative_to(component))))
                found = True
                break
        if not found:
            break
    require(path == accepted_executable.resolve(), 'interpreter chain incomplete')
    cfg = Path(invocation['executable']).parent.parent / 'pyvenv.cfg'
    cfg_values = dict(line.split(' = ', 1) for line in cfg.read_text().splitlines() if ' = ' in line)
    require(body['python_abi'] == 'cpython-312' and cfg_values['version_info'].startswith('3.12.') and
            invocation['python'].startswith(cfg_values['version_info']), 'accepted Python cfg/ABI provenance')
    identity = dict(adapter_sha256=body['adapter_source_sha256'], package_sources=len(current),
                    critical_sources=len(body['critical_sources']), native_files=len(native),
                    native_bytes=sum(row['bytes'] for row in native.values()),
                    authority_modules=source_proof, python_lexical=invocation['executable'],
                    python_canonical=str(path), python_sha256=sha(path), python_abi_from_accepted_build=body['python_abi'],
                    prep_interpreter=str(Path(sys.executable)), prep_python_version=sys.version,
                    interpreter_chain=chain, pyvenv_cfg=dict(path=str(cfg), sha256=sha(cfg)),
                    source_commit=subprocess.check_output(['git', '-C', str(REPO), 'rev-parse', 'HEAD'], text=True).strip(),
                    helper_sha256=sha(__file__), genesis_imported=False,
                    statement='accepted actual B/O body reuse only; no new options/bootstrap measurement')
    write(out / 'source-installation-identity.json', identity)
    write(out / 'native-current.json', measured_native)
    write(out / 'installed-current.json', current)
    return original, identity


def differences(a, b, path=''):
    if type(a) is dict and type(b) is dict and set(a) == set(b):
        return [p for k in sorted(a) for p in differences(a[k], b[k], path + '/' + k)]
    if type(a) is list and type(b) is list and len(a) == len(b):
        return [p for i, (x, y) in enumerate(zip(a, b)) for p in differences(x, y, path + '/' + str(i))]
    return [] if a == b else [path]


def prepare(storage):
    require(storage.is_absolute() and str(storage).startswith(str(BASE) + '/') and
            storage.resolve() == storage and not storage.exists(), 'new canonical exclusive storage required')
    storage.mkdir(mode=0o700)
    out = storage / 'prep'; out.mkdir(mode=0o700)
    original, identity = audit(out)  # Any identity mismatch stops before provision/mappings.
    deployment = storage / 'deployment'; deployment.mkdir(mode=0o700)
    origins = storage / 'approved-origin'; origins.mkdir(mode=0o700)
    rebound = deepcopy(original)
    for role in ('build', 'options', 'assets'):
        rebound[role]['world_id'] = WORLD
    rebound['options']['refs']['build'] = digest(rebound['build'])
    rebound['asset_audit']['world_id'] = WORLD
    rebound['asset_audit']['candidate_manifest']['world_id'] = WORLD
    rebound['asset_audit']['candidate_digest'] = digest(rebound['assets'])
    allowed = dict(build=['/world_id'], options=['/refs/build', '/world_id'], assets=['/world_id'],
                   asset_audit=['/candidate_digest', '/candidate_manifest/world_id', '/world_id'])
    proof, specs = {}, {}
    for role in original:
        require(differences(original[role], rebound[role]) == allowed[role], 'unexpected rebind changes: ' + role)
        if role != 'asset_audit':
            require(pack(original[role]['body']) == pack(rebound[role]['body']), 'body changed: ' + role)
        write(origins / (role + '.json'), raw=(APPROVED / (role + '.json')).read_bytes())
        target = deployment / (role + '.json'); write(target, rebound[role])
        specs[role] = dict(path=str(target), sha256=sha(target))
        proof[role] = dict(approved_sha256=sha(APPROVED / (role + '.json')), deployed_sha256=sha(target),
                           changed_paths=allowed[role], body_canonical_unchanged=role != 'asset_audit')
    require(rebound['asset_audit']['candidate_manifest'] == rebound['assets'], 'asset candidate disagreement')
    write(out / 'metadata-rebind-proof.json', proof)
    # Only the accepted explicit provision API touches new secret bytes. No open_trust/read_key.
    sys.path.insert(0, str(REPO))
    from engine.universe_authority.codec import ProvisionSpec
    from engine.universe_authority.trust import provision
    authority, scratch = storage / 'authority', storage / 'scratch'
    key_dir = storage.parent / (storage.name + '-keys')
    require(not key_dir.exists(), 'new key directory required; never reuse prior anchor')
    anchor = provision(key_dir, spec=ProvisionSpec(WORLD, authority))
    context = dict(world_id=WORLD, authority_root=str(authority), trust_anchor=anchor.trust_anchor,
                   expected_build=digest(rebound['build']), expected_options=digest(rebound['options']),
                   artifact_class='genesis-runtime', trust_algorithm='local-hmac-sha256.v0.2',
                   domain_version='0.2', archive_profile='composite-rigid-support.v0.2',
                   storage_profile='local-posix-blob-sync-v0.2')
    configs = {}
    for mode in ('initialize', 'existing'):
        owner = dict(config_version='universe-owner-launch.v0.1', mode=mode, context=context,
                     session=dict(principal='owner-i12b', can_initialize=mode == 'initialize',
                                  allowed_actions=['retain_snapshot', 'physics_step']),
                     key_dir=str(key_dir), scratch=str(scratch), inputs=specs)
        path = deployment / ('owner-' + mode + '.json'); write(path, owner)
        configs[mode] = dict(path=str(path), sha256=sha(path))
    from engine.universe_authority.worker import load_owner_config, load_inputs
    for spec in configs.values():
        loaded = load_inputs(load_owner_config(spec['path']))
        require(loaded == rebound, 'actual worker typed metadata/input validation differs')
    permissions = [metadata(p) for p in (storage, deployment, key_dir, key_dir / 'authority.key',
                                        *(Path(s['path']) for s in configs.values()))]
    write(out / 'private-metadata-only.json', permissions)
    # Pure public export through actual owning worker, no runtime/lease/key access.
    public = None
    environment = {k: v for k, v in os.environ.items() if k not in ('PYTHONHOME', 'PYTHONPATH')}
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    for mode in ('initialize', 'existing'):
        argv = [sys.executable, '-B', '-m', 'engine.universe_authority.worker',
                '--owner-config', configs[mode]['path'], '--print-public-pins']
        result = subprocess.run(argv, cwd=REPO, env=environment, capture_output=True, timeout=15)
        write(out / ('pins-' + mode + '.stdout'), raw=result.stdout)
        write(out / ('pins-' + mode + '.stderr'), raw=result.stderr)
        require(result.returncode == 0 and not result.stderr, 'pure public pins export failed')
        value = json.loads(result.stdout)
        if public is None: public = value
        require(value == public and value['world_id'] == WORLD and value['authority_root'] == str(authority) and
                value['trust_anchor'] == anchor.trust_anchor and value['expected_build'] == digest(rebound['build']) and
                value['expected_options'] == digest(rebound['options']), 'public pins mismatch')
    write(deployment / 'public-pins.json', public)
    # Source-side output links are explicit artifacts, never rewrite an existing path.
    project = REPO / 'engine_platforms/unreal/EdgeWorldHost'
    output = storage / 'outputs'; output.mkdir(mode=0o700)
    mappings = [('Binaries', 'host-binaries'), ('Intermediate', 'host-intermediate'), ('Saved', 'saved'),
                ('Plugins/EdgeWorldRuntime/Binaries', 'plugin-binaries'),
                ('Plugins/EdgeWorldRuntime/Intermediate', 'plugin-intermediate')]
    allowlist, links = {}, []
    for relative, target_name in mappings:
        link, target = project / relative, output / target_name
        require(not os.path.lexists(link), 'refuse existing product output path: ' + relative)
        target.mkdir(mode=0o700); link.symlink_to(target)
        relative_repo = str(link.relative_to(REPO))
        allowlist[relative_repo] = dict(kind='symlink', readlink=str(target), target=str(target),
                                       provenance='I12B-PREP authorized exclusive output mapping')
        links.append(dict(path=str(link), readlink=os.readlink(link), target=str(link.resolve()), lstat=metadata(link)))
    launcher_output = output / 'saved/MacLauncher'; launcher_output.mkdir(mode=0o700)
    ini_origin = BASE / 'I11B-20261102-cleanup-preparation/generated-DefaultInput.ini'
    ini = project / 'Config/DefaultInput.ini'
    require(sha(ini_origin) == 'e1b7a60e4da1acca28b8540ed7b2746551df9ae1ddc0056eb45a0932ed82ea78', 'accepted generated ini changed')
    write(ini, raw=ini_origin.read_bytes())
    allowlist[str(ini.relative_to(REPO))] = dict(kind='file', sha256=sha(ini),
        provenance='exact accepted generated I11B ini archive, not a new engine run')
    write(out / 'output-mapping-provenance.json', dict(links=links, ini_origin=str(ini_origin), ini_sha256=sha(ini)))
    ue = Path('/Users/Shared/Epic Games/UE_5.8')
    runtime = [Path(identity['python_canonical']), Path(identity['pyvenv_cfg']['path']),
               ue / 'Engine/Build/Build.version',
               ue / 'Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor']
    runtime += [Path(p).resolve() for p in load(out / 'native-current.json')]
    runtime_pins = [dict(path=str(p.resolve()), sha256=sha(p), bytes=p.stat().st_size) for p in runtime]
    stages = {'initialize': dict(build=240, startup=90, interaction=400, shutdown=50),
              'existing': dict(build=180, startup=90, interaction=80, shutdown=30)}
    now = datetime.now(timezone.utc).isoformat()
    candidate = dict(format='universe-i12-r12.v1', approved=False, issuer='root',
        scope='two-real-ue-owned-sessions', candidate_only=True, allow_forced_cleanup=True,
        issued_at=now, expires_at=now, run_id='i12b-20261102', world_id=WORLD,
        product_source=identity['source_commit'], product_root=str(REPO),
        launcher_sha256=sha(REPO / 'scripts/launch_edgeworld_ue_mac.sh'), allowed_untracked=allowlist,
        accepted_gates={'G-P1': 'PR95/merge51b95de', 'I10B': 'PR98/mergeb1c0371', 'G-B1': 'PR100/merge36d88ec'},
        storage_root=str(storage), deployment_root=str(deployment), authority_root=str(authority),
        key_directory=str(key_dir), context=context, principal='owner-i12b',
        allowed_actions=['retain_snapshot', 'physics_step'], inputs=specs,
        launcher_output_root=str(launcher_output), python_executable=identity['python_lexical'], ue_root=str(ue),
        runtime_files=runtime_pins, budget=dict(seconds=1200, bytes=2 * 1024**3, cleanup_seconds=20,
                                              spent_seconds=0, spent_bytes=0),
        sessions={mode: dict(owner_config=configs[mode], max_seconds=800 if mode == 'initialize' else 400,
                            stage_seconds=stages[mode]) for mode in configs},
        pending=['actual root R12 authorization/times/final merged product SHA',
                 'I12C exact interpreter-chain acceptance; no wrapper or canonical argv substitution',
                 'Host/plugin binary receipts after each actual official build; not immutable input pins'],
        options_reuse='accepted actual body reused with metadata-only newworld rebind; provider initializes/measures strictly')
    write(deployment / 'r12-candidate.json', candidate)
    no_runtime()
    require(not authority.exists() and not scratch.exists(), 'PREP unexpectedly created authority or scratch')
    require(time.monotonic() - START < 120, 'PREP CPU bound exceeded')
    write(out / 'preparation-summary.json', dict(source_commit=identity['source_commit'], helper_sha256=sha(__file__),
        world_id=WORLD, storage=str(storage), authority_absent=True, scratch_absent=True,
        genesis_imported=False, native_files=identity['native_files'], package_sources=identity['package_sources'],
        owner_hashes=configs, public_pins_sha256=sha(deployment / 'public-pins.json'),
        card_candidate_sha256=sha(deployment / 'r12-candidate.json'), body_reuse=True,
        actual_r12_authorized=False, PYTHONHOME_cleared=True, PYTHONPATH_cleared=True,
        elapsed_seconds=time.monotonic()-START))
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--storage', type=Path, required=True)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    require(args.prepare, 'explicit authorized PREP operation required')
    output = prepare(args.storage)
    print(json.dumps(dict(prepared=True, summary=str(output / 'preparation-summary.json'), runtime_started=False)))
