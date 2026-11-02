#!/usr/bin/env python3
"""I15 root-only metadata preparation. Default audit; no UE, solver or key IO.

prepare_probe executes only when root explicitly passes execute=True. It creates a
new readonly owner, byte-identical public copies and exclusive build mappings.
freeze_prepared runs only AFTER the real official build; missing binaries fail.
No provision, authority migration, reset, credential copy, or system mutation.
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

REPO = Path(__file__).resolve().parents[3]
BASE = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld')
STORAGE = BASE / 'I15-20261102-r4-readonly-probe'
ORIGIN = BASE / 'I12B-20261102-world/deployment/attempt4'
RAW = BASE / 'I10B-20261102-runtime-attempt2-topological'
PYTHON = '/Users/yangacan/edgeWorld/edge-world/.venv-genesis/bin/python3.12'
UE = Path('/Users/Shared/Epic Games/UE_5.8')
OWNER_SHA = 'f5cbc8e93a9b478acd6e701b99996594e34f6f9c0a1351775b7f8284232580df'
HEAD_MANIFEST = 'b82c63a952346132337ac929dbcf334e56e097d2338a4b3ef10410a12e878363'
INI = BASE / 'I11B-20261102-cleanup-preparation/generated-DefaultInput.ini'
INI_SHA = 'e1b7a60e4da1acca28b8540ed7b2746551df9ae1ddc0056eb45a0932ed82ea78'
FORMAT = 'universe-i15-prepared.v1'
FIELDS = frozenset('format run_id product_source_sha tool_source_sha native_source_sha tool_root product_root allowed_untracked output_root key_directory authority_root runtime_files native_source_pins source_pins binary_pins project ue_root python_executable python_environment_pin original_owner_ref readonly_owner_ref context inputs original_inputs scratch_root pins_ref original_pins_ref before_map_ref head_ref key_metadata probe_manifest_ref launcher_ref preparation_ref build_ref created_at helper_ref'.split())
assert len(FIELDS)==36

sys.dont_write_bytecode = True
sys.path.insert(0, str(REPO / 'scripts'))
import run_universe_slice_acceptance as common
from universe_iteration import probe_actions


def require(value, message):
    common.require(value, message)


def pack(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def safe(path):
    return common.safe_path(path)


def read(path, cap=16*1024**2):
    return common.safe_read(safe(path),cap)


def ref(path):
    path=safe(path)
    return dict(path=str(path),sha256=common.file_hash(path))


def load(path):
    return json.loads(read(path),object_pairs_hook=common.unique_pairs)


def write(path,value=None,*,raw=None):
    path=safe(path)
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,'wb') as stream:
        stream.write(pack(value) if raw is None else raw);stream.flush();os.fsync(stream.fileno())
    return ref(path)


def private_dir(path):
    path=safe(path);path.mkdir(mode=0o700)
    return common.private_metadata(path,directory=True)


def key_metadata(path):
    # Only lstat the directory itself. Never enumerate/open/hash its contents.
    path=common.private_metadata(path,directory=True);info=path.lstat()
    return dict(path=str(path),uid=info.st_uid,gid=info.st_gid,mode=stat.S_IMODE(info.st_mode),
                nlink=info.st_nlink,device=info.st_dev,inode=info.st_ino,bytes=info.st_size,symlink=path.is_symlink())


def _no_solver():
    require(not any(x=='genesis' or x.startswith('genesis.') for x in sys.modules),'Genesis imported during metadata preparation')


def derive_owner(original, *, scratch, inputs):
    """Pure limited metadata transformation; original/context/keys stay untouched."""
    require(set(original)=={'config_version','mode','context','session','key_dir','scratch','inputs'} and
            original['config_version']=='universe-owner-launch.v0.1' and original['mode']=='existing','inherited existing owner required')
    require(original['session']==dict(principal='owner-i12b',can_initialize=False,
                                    allowed_actions=['retain_snapshot','physics_step']),'unexpected original grants')
    derived=deepcopy(original)
    derived['session']['allowed_actions']=[]
    derived['scratch']=str(scratch);derived['inputs']=deepcopy(inputs)
    return derived


def _runtime_audit(product, original):
    # Compare existing accepted modules/package/native bytes without loading Genesis.
    provenance=load(RAW/'source-inputs.json')
    authority=[]
    for old,spec in provenance.items():
        if '/engine/universe_authority/' in old:
            p=product/'engine/universe_authority'/Path(old).name
            require(common.file_hash(p)==spec['sha256']==common.file_hash(RAW/spec['copy']), 'accepted authority source changed: '+p.name)
            authority.append(ref(p))
    require(authority,'missing accepted authority source catalog')
    build=load(original['inputs']['build']['path'])['body']
    require(common.file_hash(product/'engine/universe_authority/genesis_adapter.py')==build['adapter_source_sha256'],'accepted adapter source changed')
    native=load(RAW/'native-before.json')
    require(native==load(RAW/'native-after.json'),'accepted native before/after disagreement')
    installed=load(RAW/'installed-sources.json')
    package=Path(next(p for p in native if p.endswith('/genesis_world-1.4.3.dist-info/METADATA'))).parent.parent/'genesis'
    current=[dict(path=p.relative_to(package).as_posix(),sha256=common.file_hash(safe(p))) for p in sorted(package.rglob('*.py'))]
    require(current==installed and len(current)==build['source_file_count']==264 and
            hashlib.sha256(json.dumps(current,sort_keys=True,separators=(',', ':'),ensure_ascii=True).encode('ascii')).hexdigest()==build['source_tree_sha256'],'accepted installed Genesis source tree changed')
    lookup={p['path']:p['sha256'] for p in current}
    require(all(lookup[r['path']]==r['sha256'] for r in build['critical_sources']),'accepted critical source changed')
    pins=[]
    for p,spec in native.items():
        p=safe(p)
        require(p.stat().st_size==spec['bytes'] and common.file_hash(p)==spec['sha256'],'accepted installed native changed')
        pins.append(ref(p))
    pins += [ref(package/r['path']) for r in current]
    return authority,pins


def audit(product_root=REPO):
    """Read-only filesystem audit, including metadata-only key directory identity."""
    _no_solver();product=safe(product_root)
    original_path=common.private_metadata(ORIGIN/'owner-existing.json')
    require(common.file_hash(original_path)==OWNER_SHA,'original owner pinned SHA mismatch')
    original=load(original_path)
    derive_owner(original,scratch=STORAGE/'scratch',inputs=original['inputs'])
    context=original['context'];authority=safe(context['authority_root'])
    require(context['world_id']=='edgeworld-i12b-20261102-r4' and authority==BASE/'I12B-20261102-world/authority-attempt4','wrong inherited world/root')
    before=common.authority_map(authority)
    require(load(authority/'HEAD.json')['manifest']==HEAD_MANIFEST,'inherited HEAD changed')
    require(set(original['inputs'])=={'build','options','assets','asset_audit'},'exact inherited four inputs required')
    for spec in original['inputs'].values():
        require(set(spec)=={'path','sha256'} and common.file_hash(safe(spec['path']))==spec['sha256'],'inherited public input SHA mismatch')
    original_pins=load(ORIGIN/'public-pins.json')
    require(original_pins['allowed_actions']==original['session']['allowed_actions'] and original_pins['principal']==original['session']['principal'],'original public grants mismatch')
    for k in ('world_id','authority_root','trust_anchor','expected_build','expected_options','artifact_class','trust_algorithm'):
        require(original_pins[k]==context[k],'original public context mismatch')
    for role,key in (('build','expected_build'),('options','expected_options')):
        require(hashlib.sha256(common.PREFIX+common.canonical(load(original['inputs'][role]['path']))).hexdigest()==context[key],'context B/O digest mismatch')
    source_pins,runtime_files=_runtime_audit(product,original)
    py=common.collect_python_pin(PYTHON)
    common.validate_python_executable(dict(python_executable=PYTHON,python_environment_pin=py))
    require(common.file_hash(INI)==INI_SHA,'approved DefaultInput.ini bytes changed')
    version=load(UE/'Engine/Build/Build.version')
    require(tuple(version.get(k) for k in ('MajorVersion','MinorVersion','PatchVersion'))==(5,8,3) and (UE/'Engine/Build/InstalledBuild.txt').is_file(),'installed UE5.8.3 required')
    runtime_files += [py['target'],py['pyvenv_cfg'],ref(UE/'Engine/Build/Build.version')]
    _no_solver()
    # Private owner metadata deliberately not returned/logged in public audit summary.
    return dict(original_owner_ref=ref(original_path),original_pins_ref=ref(ORIGIN/'public-pins.json'),
                context=context,original_inputs=deepcopy(original['inputs']),key_directory=original['key_dir'],
                key_metadata=key_metadata(original['key_dir']),before_map=before,head_ref=ref(authority/'HEAD.json'),
                python_executable=PYTHON,python_environment_pin=py,source_pins=source_pins,runtime_files=runtime_files,
                audit_only=True,runtime_started=False,key_contents_read=False)


def prepare_probe(*,product_root=REPO,tool_root=REPO,run_id='i15-20261102',execute=False):
    """Two-stage preparation part 1; default is a non-mutating audit."""
    product=safe(product_root);tool=safe(tool_root)
    require(product.is_dir() and tool.is_dir(),'explicit product/tool directories required')
    checked=audit(product)
    if not execute:return checked
    require(product != tool,'distinct product/tool roots required for clean tool source identity')
    require(not os.path.lexists(STORAGE),'exclusive output root already exists; preserve failed/previous attempt')
    # Check source/output conflicts before creating anything.
    product_sha=common.product_identity(product);tool_sha=common.product_identity(tool)
    project=product/'engine_platforms/unreal/EdgeWorldHost'
    mappings=[('Binaries','project/Binaries'),('Intermediate','host-intermediate'),('Saved','saved'),
              ('Plugins/EdgeWorldRuntime/Binaries','project/Plugins/EdgeWorldRuntime/Binaries'),
              ('Plugins/EdgeWorldRuntime/Intermediate','plugin-intermediate')]
    require(all(not os.path.lexists(project/name) for name,_ in mappings) and not os.path.lexists(project/'Config/DefaultInput.ini'),'product output path exists')
    root=private_dir(STORAGE);prep=private_dir(root/'prep');deployment=private_dir(root/'deployment');scratch=private_dir(root/'scratch')
    copies={}
    for role,spec in checked['original_inputs'].items():
        target=deployment/(role+'.json');copies[role]=write(target,raw=read(spec['path']))
        require(copies[role]['sha256']==spec['sha256'],'byte-identical inherited public input copy required')
    original=load(checked['original_owner_ref']['path'])
    owner=derive_owner(original,scratch=scratch,inputs=copies)
    owner_ref=write(deployment/'owner-readonly.json',owner)
    # Typed owner loading/public_pins is pure; no acquire/open_trust/Store/provision call.
    if str(product) not in sys.path:sys.path.insert(0,str(product))
    import engine.universe_authority.worker as worker
    require(Path(worker.__file__).resolve()==product/'engine/universe_authority/worker.py','worker metadata parser imported from another worktree')
    loaded=worker.load_owner_config(owner_ref['path']);worker.load_inputs(loaded)
    pins=worker.public_pins(loaded);expected=dict(load(checked['original_pins_ref']['path']),allowed_actions=[])
    require(pins==expected,'typed actual public export differs from limited metadata derivation')
    pins_ref=write(deployment/'public-pins.json',raw=common.canonical(pins)+b'\n')
    before_ref=write(prep/'authority-before.json',checked.pop('before_map'))
    manifest_ref=write(prep/'probe-manifest.json',probe_actions.probe_manifest())
    output=private_dir(root/'outputs')
    for relative in ('project','project/Plugins','project/Plugins/EdgeWorldRuntime'):
        private_dir(output/relative)
    allow={}
    for relative,name in mappings:
        target=private_dir(output/name);link=project/relative;link.symlink_to(target)
        allow[str(link.relative_to(product))]=dict(kind='symlink',readlink=str(target),target=str(target),provenance='I15 root-approved readonly probe physical output mapping')
    private_dir(output/'saved/MacLauncher')
    ini=project/'Config/DefaultInput.ini';write(ini,raw=read(INI));allow[str(ini.relative_to(product))]=dict(kind='file',sha256=INI_SHA,provenance='byte-identical approved generated DefaultInput.ini')
    # All returned/public refs contain metadata only, never owner content or secret bytes.
    record=dict(checked,format='universe-i15-preparation.v1',run_id=run_id,product_root=str(product),tool_root=str(tool),
                product_source_sha=product_sha,tool_source_sha=tool_sha,allowed_untracked=allow,output_root=str(root),
                scratch_root=str(scratch),inputs=copies,readonly_owner_ref=owner_ref,pins_ref=pins_ref,
                before_map_ref=before_ref,probe_manifest_ref=manifest_ref,helper_ref=ref(__file__),
                project=str(project/'EdgeWorldHost.uproject'),created_at=datetime.now(timezone.utc).isoformat())
    require(common.product_identity(product,allow)==product_sha,'source changed during preparation')
    require(common.authority_map(safe(checked['context']['authority_root']))['files']==load(before_ref['path'])['files'],'authority changed during metadata preparation')
    _no_solver()
    return write(prep/'preparation.json',record)


def freeze_prepared(*,preparation_ref,build_ref,native_source_sha,tool_root=None):
    """Part 2: pin real built binaries and current clean sources, exclusively publish."""
    require(set(preparation_ref)=={'path','sha256'} and ref(preparation_ref['path'])==preparation_ref,'preparation reference changed')
    prep=load(preparation_ref['path']);root=common.private_metadata(prep['output_root'],directory=True)
    require(root==STORAGE and Path(preparation_ref['path'])==root/'prep/preparation.json','fixed preparation scope')
    product=safe(prep['product_root']);tool=safe(tool_root or prep['tool_root'])
    product_sha=common.product_identity(product,prep['allowed_untracked']);tool_sha=common.product_identity(tool)
    require(product_sha==prep['product_source_sha'],'product source moved since preparation')
    require(ref(build_ref['path'])==build_ref,'build receipt changed');build=load(build_ref['path'])
    require(build.get('source_sha')==native_source_sha and build.get('actual_parent_wait_exit')==0 and
            build.get('build_only') is True and build.get('ue_runtime_started') is False,'actual successful same-native-source CPU-only build receipt required')
    require(len(native_source_sha)==40 and all(x in '0123456789abcdef' for x in native_source_sha),'exact native source git SHA required')
    frozen_refs=[prep[k] for k in ('original_owner_ref','readonly_owner_ref','pins_ref','original_pins_ref','before_map_ref','head_ref','probe_manifest_ref','helper_ref')]
    frozen_refs+=list(prep['inputs'].values())+list(prep['original_inputs'].values())
    for item in prep['runtime_files']+prep['source_pins']+frozen_refs:
        require(ref(item['path'])==item,'runtime/source changed since preparation')
    common.validate_python_executable(dict(python_executable=prep['python_executable'],python_environment_pin=prep['python_environment_pin']))
    require(common.authority_map(prep['context']['authority_root'])['files']==load(prep['before_map_ref']['path'])['files'],'authority changed before freeze')
    require(key_metadata(prep['key_directory'])==prep['key_metadata'],'key directory metadata changed')
    native=[]
    for folder in ('engine_platforms/unreal/EdgeWorldHost/Source','engine_platforms/unreal/EdgeWorldHost/Plugins/EdgeWorldRuntime/Source'):
        native.extend(ref(p) for p in sorted((product/folder).rglob('*')) if p.is_file())
    require(native,'native source pins absent')
    # Bind every native source to the exact committed build source, not a caller label.
    for item in native:
        relative=str(Path(item['path']).relative_to(product))
        committed=subprocess.run(['git','-C',str(product),'show',native_source_sha+':'+relative],capture_output=True,timeout=5,check=True).stdout
        require(hashlib.sha256(committed).hexdigest()==item['sha256'],'native source differs from actual build commit')
    project=Path(prep['project']);host=(project.parent/'Binaries/Mac/UnrealEditor-EdgeWorldHost.dylib').resolve(strict=True)
    plugin=(project.parent/'Plugins/EdgeWorldRuntime/Binaries/Mac/UnrealEditor-EdgeWorldRuntime.dylib').resolve(strict=True)
    require(host.is_relative_to(root) and host.parent.parent.parent==plugin.parent.parent.parent.parent.parent,'physical Host/plugin RPATH mirror changed')
    loadcmd=subprocess.run(['/usr/bin/otool','-l',str(host)],capture_output=True,timeout=5,check=True)
    require(b'@loader_path/../../Plugins/EdgeWorldRuntime/Binaries/Mac' in loadcmd.stdout,'native Host plugin RPATH absent')
    binaries=dict(ue=ref(UE/'Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'),host=ref(host),plugin=ref(plugin))
    value={k:prep[k] for k in ('run_id','product_root','allowed_untracked','output_root','key_directory','runtime_files','source_pins',
                              'python_executable','python_environment_pin','original_owner_ref','readonly_owner_ref','context',
                              'inputs','original_inputs','scratch_root','pins_ref','original_pins_ref','before_map_ref','head_ref',
                              'key_metadata','probe_manifest_ref','project','helper_ref')}
    value.update(format=FORMAT,authority_root=prep['context']['authority_root'],product_source_sha=product_sha,tool_source_sha=tool_sha,
                 native_source_sha=native_source_sha,tool_root=str(tool),native_source_pins=native,binary_pins=binaries,ue_root=str(UE),
                 preparation_ref=preparation_ref,build_ref=build_ref,launcher_ref=ref(product/'scripts/launch_edgeworld_ue_mac.sh'),
                 created_at=datetime.now(timezone.utc).isoformat())
    require(set(value)==FIELDS,'prepared exact36-field interface mismatch')
    _no_solver()
    return write(root/'prep/prepared.json',value)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--product-root',type=Path,default=REPO);parser.add_argument('--tool-root',type=Path,default=REPO)
    parser.add_argument('--run-id',default='i15-20261102');parser.add_argument('--execute',action='store_true')
    parser.add_argument('--freeze',action='store_true');parser.add_argument('--preparation-sha256');parser.add_argument('--build-ref',type=Path)
    parser.add_argument('--build-sha256');parser.add_argument('--native-source-sha')
    args=parser.parse_args()
    if args.freeze:
        require(args.execute and args.preparation_sha256 and args.build_ref and args.build_sha256 and args.native_source_sha,'freeze requires explicit execute and independent prep/build/native-source pins')
        result=freeze_prepared(preparation_ref=dict(path=str(STORAGE/'prep/preparation.json'),sha256=args.preparation_sha256),
                               build_ref=dict(path=str(args.build_ref),sha256=args.build_sha256),native_source_sha=args.native_source_sha,tool_root=args.tool_root)
    else:result=prepare_probe(product_root=args.product_root,tool_root=args.tool_root,run_id=args.run_id,execute=args.execute)
    print(json.dumps(result,sort_keys=True))
