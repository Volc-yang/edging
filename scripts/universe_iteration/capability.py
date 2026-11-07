"""I15 capability-only admission and persistent Metal -> Native control.

No import-time IO, no UI, no arbitrary commands, no R12/R13 gate changes. Explicit
card execution launches only the fixed installed UE app against pinned inputs.
"""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import re
import shlex
import signal
import stat
import subprocess
import sys
import threading
import time

from . import capture, lifecycle as lc

FORMAT = 'universe-i15-capability.v1'
SCOPE = 'one-existing-metal-readonly-then-native-replay'
POLICY = {'global_seconds': 900, 'bytes': 2 * 1024**3,
          'metal': {'start':60,'interaction':300,'quit':40,'seal':20,'max':420},
          'native': {'start':60,'tests':60,'quit':40,'seal':20,'max':180},
          'handoff_seconds':120,'final_seal':90,'exception':90}
SELECTORS = ('edgeWorld.UniverseHost.PublicProofReplay',
             'edgeWorld.UniverseHost.Diagnostics.IdentityAndDefaultOff',
             'edgeWorld.UniverseHost.Diagnostics.HandledInputAndOrder',
             'edgeWorld.UniverseHost.Diagnostics.PauseReadWithoutTick')
REPLAY_ENV = ('EDGEWORLD_UNIVERSE_NATIVE_REPLAY','EDGEWORLD_UNIVERSE_REPLAY_MANIFEST',
              'EDGEWORLD_UNIVERSE_REPLAY_MANIFEST_SHA256','EDGEWORLD_UNIVERSE_REPLAY_OUTPUT')
_SEAL = object()


def hash_ref(ref, *, forbidden):
    path=lc.checked_path(ref['path']);lc.require(not path.is_relative_to(forbidden),'key material forbidden')
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno());lc.require(stat.S_ISREG(before.st_mode),'regular hash input required')
        digest=hashlib.sha256()
        for chunk in iter(lambda:stream.read(1024**2),b''):digest.update(chunk)
        after=os.fstat(stream.fileno());current=path.stat()
        signature=lambda st:(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
        lc.require(signature(before)==signature(after)==signature(current),'hash input changed')
    lc.require(digest.hexdigest()==ref['sha256'],'file hash mismatch')


def mac_binary_paths(project):
    """Installed Mac UE module filenames, with no synthetic compatibility aliases."""
    base=Path(project).parent
    return ((base/'Binaries/Mac/libUnrealEditor-EdgeWorldHost.dylib').resolve(),
            (base/'Plugins/EdgeWorldRuntime/Binaries/Mac/libUnrealEditor-EdgeWorldRuntime.dylib').resolve())


def validate_public_export(actual, expected):
    lc.require(actual==expected and actual.endswith(b'\n') and b'\n' not in actual[:-1] and
               not actual.endswith(b'\r\n') and len(actual)<=16385,
               'trusted pure public pins export differs from pinned canonical LF bytes')


def native_test_inventory(source_pins, product_root):
    """Fail closed on ambiguous project registrations; runtime still requires exact four."""
    product=lc.checked_path(str(product_root));rows=[];sources=[]
    registration=re.compile(r'\b(IMPLEMENT_[A-Z_]*AUTOMATION_TEST)\s*\(\s*([A-Za-z_][A-Za-z_0-9]*)\s*,\s*(?:TEXT\s*\(\s*)?"([^"\\]+)"\s*\)?\s*,')
    for pin in source_pins:
        path=lc.checked_path(pin['path'])
        lc.require(path.is_relative_to(product/'engine_platforms/unreal'),'inventory must use pinned project native source')
        if path.suffix not in ('.cpp','.cc','.h','.hpp'):continue
        text=lc.read_ref(pin).decode('utf-8')
        # Retain quoted strings while removing comments, so commented examples
        # cannot create false registrations. Nonliteral macro names fail closed.
        text=re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|//[^\n]*|/\*.*?\*/',
                    lambda m:'' if m.group().startswith(('/',)) else m.group(),text,flags=re.S)
        matches=list(registration.finditer(text))
        lc.require(len(matches)==len(re.findall(r'\bIMPLEMENT_[A-Z_]*AUTOMATION_TEST\s*\(',text)),
                   'nonliteral or unsupported project test registration')
        for match in matches:
            kind,class_name,name=match.groups()
            lc.require(kind=='IMPLEMENT_SIMPLE_AUTOMATION_TEST' or not any(
                name.casefold().startswith(s.casefold()) or s.casefold().startswith(name.casefold()) for s in SELECTORS),
                'dynamic/complex test inventory cannot prove selected prefix unique')
            rows.append(dict(name=name,kind=kind,class_name=class_name,source_ref=pin))
        sources.append(pin)
    lc.require(rows and sources,'complete pinned native test inventory missing')
    for selector in SELECTORS:
        lc.require([r['name'] for r in rows if r['name'].casefold().startswith(selector.casefold())]==[selector],
                   'selected native test prefix missing or ambiguous: '+selector)
    return dict(format='universe-i17-native-test-inventory.v1',sources=sources,
                registrations=sorted(rows,key=lambda r:r['name']),selectors=list(SELECTORS),
                selection='project prefixes proven unique; runtime exact Found4/Path set required')


def native_cache_arguments(output_root, run_id, controller_output):
    """Fixed isolated FileSystem graph; Mac rejects cache roots >=119 chars."""
    root=lc.checked_path(str(output_root))
    lc.require(type(run_id) is str and re.fullmatch('[A-Za-z0-9._-]{1,128}',run_id),'bounded run identity for DDC')
    controller=lc.checked_path(str(controller_output))
    lc.require(controller.is_relative_to(root) and controller!=root,'DDC controller must belong to counted output root')
    binding=(run_id+'\0'+str(controller)).encode()
    path=lc.checked_path(str(root/('ddc-i17-'+hashlib.sha256(binding).hexdigest()[:16])))
    lc.require(len(str(path))<119 and re.fullmatch(r'[A-Za-z0-9_./-]+',str(path)) is not None,
               'DDC path must fit installed Mac limit and literal graph syntax')
    graph='-DDC=(Isolated=(Type=FileSystem,Path='+str(path)+',PromptIfMissing=false,Clean=false,DeleteUnused=false))'
    return path,[graph,'-DDC-NoDefaultGraph']


def file_fingerprint(path):
    """Exact stable bytes for final writer checks, without publishing a false ref."""
    path=lc.checked_path(str(path))
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
    with os.fdopen(fd,'rb') as stream:
        before=os.fstat(stream.fileno())
        lc.require(stat.S_ISREG(before.st_mode) and before.st_size<=16*1024**2,'bounded regular evidence required')
        raw=stream.read(16*1024**2+1);after=os.fstat(stream.fileno())
    current=path.stat()
    identity=lambda st:(st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns,st.st_ctime_ns)
    lc.require(stat.S_ISREG(before.st_mode) and identity(before)==identity(after)==identity(current),'evidence changed during fingerprint')
    return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw),
                device=before.st_dev,inode=before.st_ino,mtime_ns=before.st_mtime_ns,ctime_ns=before.st_ctime_ns)


def sponsored_trace_server(row, sponsor_pid, ue_root=None):
    """Identify only the actual TraceServer executable and one exact sponsor."""
    raw=row.get('argv','')
    if type(raw) is not str or type(sponsor_pid) is not int or sponsor_pid<=0:return False
    try:
        absolute=str(Path(ue_root)/'Engine/Binaries/Mac/UnrealTraceServer') if ue_root else None
        if absolute and raw.startswith(absolute+' '):
            arguments=[absolute]+shlex.split(raw[len(absolute)+1:])
        else:arguments=shlex.split(raw)
    except (TypeError,ValueError):return False
    return bool(arguments and Path(arguments[0]).name=='UnrealTraceServer' and
                [arg for arg in arguments[1:] if arg.startswith('--sponsor=')]==['--sponsor='+str(sponsor_pid)])


def encoded(value):
    return (json.dumps(value, sort_keys=True, indent=2, allow_nan=False)+'\n').encode()


def _common(tool_root):
    scripts = Path(__file__).resolve().parents[1]
    lc.require(scripts.parent == Path(tool_root), 'fixed capability tool root')
    if str(scripts) not in sys.path:
        sys.path.insert(0,str(scripts))
    module = importlib.import_module('run_universe_slice_acceptance')
    lc.require(Path(module.__file__).resolve()==scripts/'run_universe_slice_acceptance.py','fixed common validator module')
    return module


class ValidatedCapability:
    def __init__(self, card, prepared, manifest, token):
        lc.require(token is _SEAL,'capability requires actual admission, never JSON restore')
        self.card, self.prepared, self.manifest = deepcopy(card),deepcopy(prepared),deepcopy(manifest)
        self.token=token


def validate_capability_card(path, *, expected_card_sha256, expected_prepared_sha256,
        expected_probe_manifest_sha256, expected_product_source, expected_tool_source,
        expected_native_source_sha, execute=False):
    """Independent capability admission, not a forged standard readiness review."""
    card = lc.json_ref({'path':str(path),'sha256':expected_card_sha256})
    fields={'format','scope','run_id','issuer','approved','execute','issued_at','expires_at',
            'g_b2_granted','standard_pair','no_retry','prepared_ref','probe_manifest_ref',
            'controller_output','policy','legacy_sources','public_paths'}
    lc.require(set(card)==fields and card['format']==FORMAT and card['scope']==SCOPE and
        card['issuer']=='root' and card['approved'] is True and card['execute'] is True and execute is True and
        card['g_b2_granted'] is False and card['standard_pair'] is False and card['no_retry'] is True,
        'explicit root capability-only scope/execute required')
    now=datetime.now(timezone.utc).timestamp()
    lc.require(lc.utc_seconds(card['issued_at'])<=now<lc.utc_seconds(card['expires_at']),'capability card expired/not issued')
    lc.require(card['policy']==POLICY,'capability resource allocation changed')
    lc.require(card['prepared_ref']['sha256']==expected_prepared_sha256 and
               card['probe_manifest_ref']['sha256']==expected_probe_manifest_sha256,'independent prepared/manifest pins')
    prepared=lc.json_ref(card['prepared_ref'])
    prepared_fields={'format','run_id','product_source_sha','tool_source_sha','native_source_sha','tool_root','product_root','allowed_untracked','output_root','key_directory','authority_root','runtime_files','native_source_pins','source_pins','binary_pins','project','ue_root','python_executable','python_environment_pin','original_owner_ref','readonly_owner_ref','context','inputs','original_inputs','scratch_root','pins_ref','original_pins_ref','before_map_ref','head_ref','key_metadata','probe_manifest_ref','launcher_ref','preparation_ref','build_ref','created_at','helper_ref'}
    lc.require(set(prepared)==prepared_fields,'exact prepared v1 fields')
    lc.require(prepared['format']=='universe-i15-prepared.v1' and prepared['run_id']==card['run_id'] and
        prepared['product_source_sha']==expected_product_source and prepared['tool_source_sha']==expected_tool_source and
        prepared['native_source_sha']==expected_native_source_sha,'prepared source/run binding')
    tool=lc.checked_path(prepared['tool_root']); common=_common(tool)
    common.private_metadata(path); common.private_metadata(Path(path).parent,directory=True)
    product=lc.checked_path(prepared['product_root'])
    lc.require(common.product_identity(product,prepared['allowed_untracked'])==expected_product_source and
               common.product_identity(tool)==expected_tool_source,'actual clean product/tool identities')
    root=common.private_metadata(prepared['output_root'],directory=True)
    lc.require(common.on_devssd(root),'capability output requires DevSSD')
    out=lc.checked_path(card['controller_output'])
    lc.require(out.is_relative_to(root) and out!=root and not out.exists(),'exclusive unused capability controller directory')
    keys=common.private_metadata(prepared['key_directory'],directory=True)
    authority=lc.checked_path(prepared['authority_root'])
    lc.require(authority.is_dir() and not authority.is_relative_to(root) and not root.is_relative_to(authority) and
               not keys.is_relative_to(root) and not root.is_relative_to(keys),'inherited authority/key/output separation')
    def ref(value):
        candidate=lc.checked_path(value['path'])
        lc.require(not candidate.is_relative_to(keys),'key content must never be read or hashed')
        return lc.read_ref(value)
    for name in ('runtime_files','native_source_pins','source_pins'):
        lc.require(type(prepared[name]) is list and prepared[name], 'complete runtime/native/source pins required')
        for item in prepared[name]:hash_ref(item,forbidden=keys)
    for item in prepared['binary_pins'].values():hash_ref(item,forbidden=keys)
    lc.require(set(prepared['binary_pins'])=={'ue','host','plugin'},'exact UE/host/plugin binary pins')
    project=lc.checked_path(prepared['project'])
    lc.require(project.is_file() and project.is_relative_to(product) and project.name=='EdgeWorldHost.uproject','fixed owning UE project')
    ue=lc.checked_path(prepared['ue_root'])
    editor=ue/'Engine/Binaries/Mac/UnrealEditor.app/Contents/MacOS/UnrealEditor'
    lc.require(prepared['binary_pins']['ue']['path']==str(editor) and os.access(editor,os.X_OK),'installed app executable pin')
    version=json.loads((ue/'Engine/Build/Build.version').read_bytes())
    lc.require(tuple(version.get(k) for k in ('MajorVersion','MinorVersion','PatchVersion'))==(5,8,3) and
               (ue/'Engine/Build/InstalledBuild.txt').is_file(),'installed UE5.8.3 required')
    host,plugin=mac_binary_paths(project)
    lc.require(str(host)==prepared['binary_pins']['host']['path'] and str(plugin)==prepared['binary_pins']['plugin']['path'] and
        host.parent.parent.parent==plugin.parent.parent.parent.parent.parent and host.is_relative_to(root),
        'physical Host/plugin project mirror and fixed pins required')
    load=subprocess.run(['/usr/bin/otool','-l',str(host)],capture_output=True,timeout=5,check=True)
    lc.require(b'@loader_path/../../Plugins/EdgeWorldRuntime/Binaries/Mac' in load.stdout,'Host plugin RPATH missing')
    common.validate_python_executable({'python_executable':prepared['python_executable'],
                                     'python_environment_pin':prepared['python_environment_pin']})
    # Private owner bytes are inspected only in memory; never emitted/indexed.
    for name in ('original_owner_ref','readonly_owner_ref'):
        common.private_metadata(prepared[name]['path'])
    original=json.loads(ref(prepared['original_owner_ref']))
    derived=json.loads(ref(prepared['readonly_owner_ref']))
    owner_fields={'config_version','mode','context','session','key_dir','scratch','inputs'}
    lc.require(set(original)==set(derived)==owner_fields and derived['config_version']==original['config_version']=='universe-owner-launch.v0.1' and
        original['mode']==derived['mode']=='existing' and original['context']==derived['context']==prepared['context'] and
        original['key_dir']==derived['key_dir']==str(keys),'same inherited existing owner context/anchor')
    session=derived['session']
    lc.require(set(session)=={'principal','can_initialize','allowed_actions'} and session['can_initialize'] is False and
        session['allowed_actions']==[] and session['principal']==original['session']['principal'],'derived existing false/empty grants required')
    lc.require(derived['inputs']==prepared['inputs'] and original['inputs']==prepared['original_inputs'] and
        set(prepared['inputs'])==set(prepared['original_inputs'])=={'build','options','assets','asset_audit'},'four exact inherited input roles')
    for name,spec in prepared['inputs'].items():
        lc.require(spec['sha256']==prepared['original_inputs'][name]['sha256'],'public inherited input bytes changed')
        ref(spec); ref(prepared['original_inputs'][name])
    scratch=common.private_metadata(derived['scratch'],directory=True)
    lc.require(str(scratch)==prepared['scratch_root'] and scratch.is_relative_to(root) and scratch.is_dir() and
        not scratch.is_relative_to(authority) and not scratch.is_relative_to(keys),'fresh capability scratch location')
    context=prepared['context']
    lc.require(set(context)=={'world_id','authority_root','trust_anchor','expected_build','expected_options','artifact_class',
        'trust_algorithm','domain_version','archive_profile','storage_profile'} and context['authority_root']==str(authority) and
        context['artifact_class']=='genesis-runtime' and context['trust_algorithm']=='local-hmac-sha256.v0.2' and
        context['domain_version']=='0.2' and context['archive_profile']=='composite-rigid-support.v0.2' and
        context['storage_profile']=='local-posix-blob-sync-v0.2','typed inherited world context')
    for role,key in (('build','expected_build'),('options','expected_options')):
        record=json.loads(ref(prepared['inputs'][role]))
        lc.require(hashlib.sha256(common.PREFIX+common.canonical(record)).hexdigest()==context[key],'context public build/options digest')
    pins=json.loads(ref(prepared['pins_ref']))
    old_pins=json.loads(ref(prepared['original_pins_ref']))
    expected_pins=dict(old_pins,allowed_actions=[])
    lc.require(pins==expected_pins and pins['world_id']==context['world_id'] and
        pins['authority_root']==str(authority) and pins['trust_anchor']==context['trust_anchor'],'readonly pins/context cross-check')
    for key in ('expected_build','expected_options'):
        lc.require(pins[key]==context[key],'pins build/options context')
    common.private_metadata(prepared['pins_ref']['path']); common.private_metadata(Path(prepared['pins_ref']['path']).parent,directory=True)
    before=json.loads(ref(prepared['before_map_ref']))
    lc.require(common.authority_map(authority)['files']==before['files'] and before['root']==str(authority),'inherited complete authority map changed')
    ref(prepared['head_ref'])
    lc.require(Path(prepared['head_ref']['path'])==authority/'HEAD.json','exact inherited HEAD pin')
    metadata=prepared['key_metadata']; st=keys.lstat()
    expected_meta=dict(path=str(keys),uid=st.st_uid,gid=st.st_gid,mode=stat.S_IMODE(st.st_mode),nlink=st.st_nlink,
                       device=st.st_dev,inode=st.st_ino,bytes=st.st_size,symlink=keys.is_symlink())
    lc.require(metadata==expected_meta,'key directory metadata changed; contents never inspected')
    manifest=json.loads(ref(card['probe_manifest_ref']))
    lc.require(prepared['probe_manifest_ref']==card['probe_manifest_ref'] and
               manifest['format']=='universe-i15-probe-actions.v1','fixed P probe manifest pin')
    lc.require(type(manifest['items']) is list and manifest['items'],'probe command list missing')
    ids=set()
    for item in manifest['items']:
        lc.require(item['phase'] in ('startup','interaction','shutdown') and item['action_id'] not in ids,'probe manifest phase/identity')
        ids.add(item['action_id'])
        for command in item['commands']:
            lc.require(type(command['step_id']) is str and type(command['text']) is str and
                0<lc.number(command['max_seconds'],'step budget')<=10,'bounded fixed probe command')
    lc.require(len(card['legacy_sources'])<=3 and type(card['public_paths']) is list,'explicit bounded old source catalog')
    ref(prepared['launcher_ref']);ref(prepared['helper_ref']);ref(prepared['preparation_ref'])
    build=json.loads(ref(prepared['build_ref']))
    lc.require(build.get('source_sha')==expected_native_source_sha and build.get('actual_parent_wait_exit')==0 and
        type(build.get('actual_parent_wait_exit')) is int and build.get('build_only') is True and build.get('ue_runtime_started') is False,
        'actual pinned CPU-only official native build required')
    return ValidatedCapability(card,prepared,manifest,_SEAL)


class CapabilityController:
    """One live Python parent/observer for both processes; never reconstructed."""
    def __init__(self, validated, *, clock=time.monotonic):
        self.started=clock()
        lc.require(type(validated) is ValidatedCapability and validated.token is _SEAL,'actual validated capability required')
        self.card,self.prepared,self.manifest=deepcopy(validated.card),deepcopy(validated.prepared),deepcopy(validated.manifest)
        self.clock=clock; self.output=lc.checked_path(self.card['controller_output']); self.output.mkdir(mode=0o700)
        self.common=_common(self.prepared['tool_root'])
        self.clock_binding=dict(id='i15-%d-%d'%(os.getpid(),time.monotonic_ns()),anchor_monotonic=self.started,
                                anchor_utc=datetime.now(timezone.utc).isoformat())
        self.samples=[];self.public_refs={};self.failures=[];self.phases={};self.phase=None
        self.process=None;self.identity=None;self.binding=None;self.observation_ref=None
        self.lock=threading.RLock();self.stop_event=threading.Event();self.observer=None;self.observer_error=None
        self.seq=0;self.pending={};self.active=None;self.receipts={};self.completed_steps=set();self.closed=False;self.closing=False
        self.native_manifest=None;self.current_capture={}
        self._event('dispatch',clock=self.clock_binding)

    def _write(self, path, value):
        reference=lc.exclusive_bytes(path,encoded(value));self.public_refs[reference['path']]=reference;return reference

    def _ref(self,path):
        path=lc.checked_path(str(path))
        lc.require(not path.is_relative_to(Path(self.prepared['key_directory'])),'never read key material')
        reference=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        self.public_refs[str(path)]=reference;return reference

    def _event(self,kind,**fields):
        with self.lock:
            self.seq+=1
            return self._write(self.output/('event-%06d.json'%self.seq),dict(kind=kind,monotonic=self.clock(),**fields))

    def now(self):
        return dict(clock=self.clock_binding,monotonic=self.clock(),elapsed=self.clock()-self.started,
                    remaining_seconds=max(0,900-(self.clock()-self.started)))

    def start_observer(self):
        lc.require(self.observer is None,'one continuous observer only')
        first_sample=threading.Event()
        def sample(value):
            with self.lock:
                prior=self.samples[-1]['monotonic'] if self.samples else self.started
                if value['monotonic']-prior>2:self.observer_error='observer gap exceeds2s'
                self.samples.append(value);self.public_refs[value['raw_ref']['path']]=value['raw_ref']
                self._write(self.output/('sample-%06d.json'%len(self.samples)),value)
                for phase in tuple(self.phases.values()):
                    if not phase.get('skipped') and phase.get('pid') is not None and phase.get('identity') is None:
                        rows=[r for r in value['processes'] if r['pid']==phase['pid']]
                        if rows:phase['identity']=rows[0]
                first_sample.set()
        def run():
            try:lc.record_observer(self.stop_event,self.output,on_sample=sample)
            except BaseException as error:
                self.observer_error=str(error);first_sample.set()
        self.observer=threading.Thread(target=run,name='i15-capability-observer',daemon=False);self.observer.start()
        ready=first_sample.wait(2)
        if not (ready and self.samples and not self.observer_error and self.observer.is_alive()):
            self.stop_event.set();self.observer.join(2)
            self._write(self.output/'observer-start-failure.json',dict(
                format='universe-i15-observer-start-failure.v1',run_id=self.card['run_id'],
                first_sample_signaled=ready,sample_count=len(self.samples),observer_error=self.observer_error,
                stop_requested=True,thread_alive=self.observer.is_alive(),monotonic=self.clock(),
                ue_dispatched=False,normal=False))
            raise lc.Invalid('continuous observer first sample not ready within2s: '+str(self.observer_error))
        return dict(sample_ref=self.samples[0]['raw_ref'],monotonic=self.samples[0]['monotonic'])

    def _private_preflight(self):
        """Pure worker public export: no Lease/open_trust/provider/scene."""
        environment={k:v for k,v in os.environ.items() if k not in ('PYTHONHOME','PYTHONPATH') and not k.startswith('EDGEWORLD_')}
        result=subprocess.run([self.prepared['python_executable'],'-m','engine.universe_authority.worker',
            '--owner-config',self.prepared['readonly_owner_ref']['path'],'--print-public-pins'],
            cwd=self.prepared['product_root'],env=environment,capture_output=True,timeout=15,check=True)
        expected=lc.read_ref(self.prepared['pins_ref'])
        validate_public_export(result.stdout,expected)
        self._write(self.output/'public-export.json',dict(sha256=hashlib.sha256(result.stdout).hexdigest(),
                    exit_code=result.returncode,scope='pure export; no authority/key/provider open'))

    def _spawn(self,name,argv,environment):
        lc.require(self.observer is not None and self.observer.is_alive() and not self.observer_error,'continuous observer required')
        lc.require(name not in self.phases and not self.closed,'no retry or extra phase')
        lc.require(self.process is None or self.process.poll() is not None,'previous process still active')
        lc.require(self.samples and self.clock()-self.samples[-1]['monotonic']<=2,'fresh pre-spawn observer required')
        lc.require(not lc.classify_processes(self.samples[-1]['processes'],[],self.prepared['binary_pins']['ue']['path']),'UE already running before dispatch')
        reserve=POLICY[name]['max']+90
        lc.require(self.clock()-self.started+reserve<900,'not enough complete phase/closing reserve')
        directory=self.output/name
        if getattr(self,'_reserved_directory',None)==directory:
            self._reserved_directory=None
            lc.require(directory.is_dir(),'reserved phase directory missing')
        else:directory.mkdir(mode=0o700)
        self.phase=name;self.closing=False;self.binding=None;self.pending={};self.active=None
        started=self.clock();self.phases[name]={'started':started,'normal':False,'directory':str(directory),'forced_cleanup':[]}
        console=(directory/'console.log').open('xb')
        process=subprocess.Popen(argv,cwd=self.prepared['product_root'],env=environment,stdin=subprocess.DEVNULL,
                                 stdout=console,stderr=subprocess.STDOUT,start_new_session=True)
        self.process=process;self.identity=None
        self.phases[name].update(pid=process.pid,parent_pid=os.getpid(),argv=argv,environment=environment,identity=None)
        self._event('spawn',phase=name,pid=process.pid,argv=argv)
        def supervise():
            try:
                last_bytes_check=0
                while process.poll() is None:
                    if self.clock()-last_bytes_check>=1:
                        last_bytes_check=self.clock()
                        try:
                            if self._storage_bytes()>POLICY['bytes']:self.observer_error='new artifact storage exceeds2GiB'
                        except (OSError,lc.Invalid) as error:self.observer_error=str(error)
                    elapsed=self.clock()-started
                    limit=400 if name=='metal' else 160
                    if name=='metal' and self.binding is None:limit=60
                    if elapsed>=limit or self.clock()-self.started>=870 or self.observer_error:
                        self.phases[name]['forced_cleanup'].append({'kind':'exact-Popen-TERM','monotonic':self.clock()})
                        process.terminate()
                        try:process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.phases[name]['forced_cleanup'].append({'kind':'exact-Popen-KILL','monotonic':self.clock()})
                            process.kill()
                        break
                    time.sleep(.1)
                self.phases[name]['wait_exit']=process.wait()
                self.phases[name]['wait_monotonic']=self.clock()
            finally:
                console.close()
        thread=threading.Thread(target=supervise,name='i15-owned-'+name,daemon=False)
        self.phases[name]['thread']=thread;thread.start()
        return dict(pid=process.pid,phase=name,log_path=str(directory/'ue.log'),clock=self.clock_binding)

    def start_metal(self):
        lc.require(not self.phases,'Metal must be first, once')
        self._private_preflight()
        directory=self.output/'metal'
        trace=directory/'trace'  # created before UE starts; _spawn owns parent creation
        env={k:v for k,v in os.environ.items() if not k.startswith('EDGEWORLD_') and k not in ('PYTHONHOME','PYTHONPATH')}
        env.update(EDGEWORLD_UNIVERSE_PYTHON=self.prepared['python_executable'],
            EDGEWORLD_UNIVERSE_WORKER=str(Path(self.prepared['product_root'])/'engine/universe_authority/worker.py'),
            EDGEWORLD_UNIVERSE_OWNER_CONFIG=self.prepared['readonly_owner_ref']['path'],
            EDGEWORLD_UNIVERSE_INITIALIZE='0',EDGEWORLD_UNIVERSE_PINS=self.prepared['pins_ref']['path'],
            EDGEWORLD_UNIVERSE_PINS_SHA256=self.prepared['pins_ref']['sha256'],EDGEWORLD_UNIVERSE_TRACE=str(trace),
            EDGEWORLD_UNIVERSE_DIAGNOSTICS_V1='1',EDGEWORLD_UNIVERSE_DIAGNOSTIC_RUN_ID=self.card['run_id'],
            EDGEWORLD_UNIVERSE_DIAGNOSTIC_SOURCE_SHA=self.prepared['product_source_sha'],
            EDGEWORLD_UNIVERSE_DIAGNOSTIC_SESSION='existing',EDGEWORLD_UNIVERSE_DIAGNOSTIC_SCOPE='readonly-probe')
        argv=[self.prepared['binary_pins']['ue']['path'],self.prepared['project'],
            '/Engine/Maps/Entry?game=/Script/EdgeWorldHost.EdgeWorldUniverseGameMode','-game','-log','-windowed',
            '-ResX=960','-ResY=600','-EWDiagPreflushViewport','-NoSplash','-NoSound',
            '-UserDir='+str(directory/'user'),'-abslog='+str(directory/'ue.log')]
        # Worker requires a preexisting private trace directory. Create parent
        # exclusively here and let _spawn reuse only this just-reserved phase dir.
        directory.mkdir(mode=0o700);trace.mkdir(mode=0o700);(directory/'user').mkdir(mode=0o700)
        return self._spawn_reserved('metal',argv,env,directory)

    def _spawn_reserved(self,name,argv,env,directory):
        # Reserve marker permits exactly the parent created by this call path.
        # _spawn's exclusive mkdir is bypassed only through a private known path.
        self._reserved_directory=directory
        return self._spawn(name,argv,env)

    def _identity(self,pid):
        rows={lc.process_key(r):r for s in self.samples for r in s['processes'] if r['pid']==pid}
        lc.require(len(rows)==1,'actual PID missing or startup identity reused')
        return next(iter(rows.values()))

    def _trace(self):
        """Reassemble current completed frames; never infer from UI intentions."""
        directory=self.output/'metal/trace';entries=[]
        for path in sorted(directory.glob('*.json')):
            meta=json.loads(lc.read_ref(self._ref(path)))
            lc.require(Path(meta['raw_file']).name==meta['raw_file'],'trace raw escape')
            raw=lc.read_ref(self._ref(directory/meta['raw_file']))
            lc.require(len(raw)==meta['byte_count'] and meta['host_pid']==self.phases['metal']['pid'],'trace host/length binding')
            entries.append((int(meta['serial']),meta,raw))
        entries.sort();frames=[];pending=None;chunks=bytearray();identity=None
        for serial,meta,raw in entries:
            lc.require(meta['operation'] not in ('initialize','prepare','advance','retry'),'forbidden authority write intent')
            candidate=(meta['worker_pid'],int(meta['generation']))
            lc.require(candidate[0]>0 and (identity is None or identity==candidate),'worker identity changed')
            identity=candidate
            if meta['direction']=='request':
                lc.require(pending is None,'overlapping trace request');pending=json.loads(raw);chunks=bytearray()
                lc.require(pending['operation'] in ('status','observe'),'non-readonly request')
            elif meta['direction']=='stdout-chunk':chunks.extend(raw)
            elif meta['direction']=='response-complete':
                lc.require(pending is not None and chunks.endswith(b'\n'),'complete original response missing')
                response=json.loads(chunks)
                lc.require(response['request_id']==pending['request_id'] and response['ok'] is True,'request/response failed identity')
                frames.append(dict(request=pending,response=response,worker_pid=identity[0],generation=identity[1]));pending=None
        return frames

    def register_metal_ready(self):
        lc.require(self.phase=='metal' and not self.closing and self.process.poll() is None,'actual Metal process not active')
        frames=self._trace();lc.require(len(frames)>=2 and frames[0]['request']['operation']=='status','actual startup status required')
        self.binding=dict(run_id=self.card['run_id'],session='existing',world_id=self.prepared['context']['world_id'],
            authority_root=self.prepared['authority_root'],source_sha=self.prepared['product_source_sha'],
            host_pid=self.process.pid,worker_pid=frames[0]['worker_pid'],generation=frames[0]['generation'])
        self.identity=self._identity(self.process.pid);self.worker_identity=self._identity(self.binding['worker_pid'])
        return self.refresh_observation()

    def refresh_observation(self):
        frames=self._trace();status=next(f for f in frames if f['request']['operation']=='status')
        observe=next(f for f in reversed(frames) if f['request']['operation']=='observe')
        current=status['response']['result']['payload'];response=observe['response']['result']['payload']
        trusted={k:current[k] for k in ('tick','revision','watermark')}
        selected={k:observe['request']['payload'][k] for k in ('tick','revision','watermark')}
        context=self.prepared['context'];hb=current['head_binding']
        lc.require(current['storage_state']=='ready' and hb['world_id']==context['world_id'] and
            hb['authority_root']==context['authority_root'] and hb['trust_anchor']==context['trust_anchor'] and
            all(hb[k]==context[k] for k in ('expected_build','expected_options')) and
            {k:response['manifest']['body'][k] for k in selected}==selected,'actual public head/selected manifest context')
        raw=(self.output/'metal/ue.log').read_bytes()
        marker=('Universe world %s observed tick %d, revision %d'%(context['world_id'],selected['tick'],selected['revision'])).encode()
        lc.require(marker in raw,'strict UE accepted-observation marker missing')
        verify=self._write(self.output/('observation-source-%06d.json'%time.monotonic_ns()),dict(status=status,observe=observe,
            ue_log_ref=self._ref(self.output/'metal/ue.log'),scope='actual UE strict parser marker; Native exact proof replay pending'))
        self.trusted_head,self.selected_observation=trusted,selected
        self.seq+=1
        self.observation_ref=self._write(self.output/('observation-%06d.json'%self.seq),dict(binding=self.binding,
            trusted_head=trusted,selected_observation=selected,clock_id=self.clock_binding['id'],
            verified_monotonic=self.clock(),verification_ref=verify))
        return dict(binding=self.binding,trusted_head=trusted,selected_observation=selected,
                    observation_ref=self.observation_ref,clock=self.clock_binding)

    def snapshot(self,label):
        lc.require(re.fullmatch('[A-Za-z0-9._-]{1,96}',label) is not None,'safe snapshot label')
        value=self.common.authority_map(Path(self.prepared['authority_root']))
        before=lc.json_ref(self.prepared['before_map_ref'])
        ref=self._write(self.output/('map-%06d-%s.json'%(self.seq,label)),value)
        lc.require(value['files']==before['files'],'authority changed during readonly capability')
        log=self.output/'metal/ue.log';raw=log.read_bytes();st=log.stat()
        return dict(map_ref=ref,monotonic=self.clock(),clock=self.clock_binding,
            log=dict(path=str(log),device=st.st_dev,inode=st.st_ino,before_offset=len(raw),
                     prefix_sha256=hashlib.sha256(raw).hexdigest()))

    def permit(self,action_id,step_id,timeout):
        lc.require(self.phase=='metal' and self.binding and not self.closing and not self.closed and
                   self.process.poll() is None and not self.active,'no current Metal action permit')
        item=next(x for x in self.manifest['items'] if x['action_id']==action_id)
        command=next(x for x in item['commands'] if x['step_id']==step_id)
        lc.require((action_id,step_id) not in self.completed_steps and 0<lc.number(timeout,'tool timeout')<=min(10,command['max_seconds']),'one bounded execution per step')
        now=self.clock();started=self.phases['metal']['started']
        lc.require(now+timeout<min(started+360,self.started+810),'normal quit reserve reached')
        lc.require(self.samples and 0<=now-self.samples[-1]['monotonic']<=2 and not self.observer_error,'fresh observer required')
        rows=self.samples[-1]['processes'];owned=[self.identity,self.worker_identity]
        lc.require({lc.process_key(p) for p in owned}<={lc.process_key(p) for p in rows},'exact UE/worker no longer live')
        lc.require(all(x['ownership']=='owned' for x in lc.classify_processes(rows,owned,self.prepared['binary_pins']['ue']['path'])),'extra UE contamination')
        self._trace()
        self.seq+=1;token=dict(seq=self.seq,action_id=action_id,step_id=step_id,text=command['text'],binding=self.binding,
            clock=self.clock_binding,issued_monotonic=now,deadline_monotonic=now+timeout,before=self.snapshot('before'))
        self.pending[token['seq']]=deepcopy(token)
        return token

    def consume(self,token):
        lc.require(self.clock()-self.samples[-1]['monotonic']<=2 and not self.observer_error,'fresh consume sample')
        lc.require(not self.closing and self.pending.pop(token['seq'],None)==token and self.clock()<token['deadline_monotonic'] and
                   self.process.poll() is None,'stale/replayed/revoked permit')
        self.active=dict(deepcopy(token),started_monotonic=self.clock());return self.active

    def begin_action(self,action_id,step_id,timeout):
        return self.consume(self.permit(action_id,step_id,timeout))

    def end_action(self,seq,raw_tool_ref):
        lc.require(self.active is not None and self.active['seq']==seq,'no consumed matching action')
        self.read_public(raw_tool_ref)
        value=dict(self.active,completed_monotonic=self.clock(),raw_tool_ref=raw_tool_ref,after=self.snapshot('after'))
        value['status']='recorded' if value['completed_monotonic']<=value['deadline_monotonic'] else 'timeout'
        self._trace();self.completed_steps.add((value['action_id'],value['step_id']));self.active=None
        ref=self._write(self.output/('action-%06d.json'%seq),value);self.receipts[seq]=(ref,value)
        if value['status']=='timeout':self.request_quit('step exceeded bounded tool interval')
        return dict(receipt_ref=ref,**value)

    def read_public(self,ref):
        path=lc.checked_path(ref['path'])
        approved=self.public_refs.get(str(path))
        lc.require(path.is_relative_to(self.output/'controller-inputs') or approved==ref,'explicit controller public input required')
        return lc.read_ref(ref)

    def request_quit(self,reason):
        self.closing=True;self.pending={}
        return self._event('quit_request',phase=self.phase,reason=reason,actual_exit_proven=False)

    def ack_quit(self,raw_cua_ref):
        lc.require(self.closing,'quit not requested');self.read_public(raw_cua_ref)
        return self._event('quit_ack',raw_cua_ref=raw_cua_ref,actual_exit_proven=False)

    def skip_metal(self, evidence_ref):
        """Root's explicit undispatched-Metal exclusion; never a completed session."""
        lc.require(not self.phases and self.process is None,'only undispatched Metal may be skipped')
        path=lc.checked_path(evidence_ref['path'])
        lc.require(not path.is_relative_to(Path(self.prepared['key_directory'])) and
            (str(path) in self.card['public_paths'] or path.is_relative_to(self.output/'controller-inputs')),
            'explicit public skip evidence required; never private/key input')
        evidence=lc.json_ref(evidence_ref)
        reason=evidence.get('reason') if type(evidence) is dict else None
        lc.require(reason in ('ui-controller-unavailable','approved-native-only-iteration') and
            evidence==dict(format='universe-i15-capability-skip.v1',run_id=self.card['run_id'],
            reason=reason,metal_dispatched=False,decision='inconclusive'),
            'explicit root approved undispatched-Metal skip evidence required')
        self.phases['metal']=dict(skipped=True,normal=False,decision='inconclusive',evidence_ref=evidence_ref,
                                  started=self.clock(),sealed_monotonic=self.clock())
        return self._event('metal_not_dispatched',evidence_ref=evidence_ref)

    def _phase_owned(self, name):
        phase=self.phases[name]
        identities={}
        baseline={lc.process_key(row) for sample in self.samples if sample['monotonic']<=phase.get('started',0)
                  for row in sample['processes']}
        for sample in self.samples:
            rows=sample['processes']
            seed=phase.get('identity')
            if seed is None:continue
            for item in lc.classify_processes(rows,[seed],self.prepared['binary_pins']['ue']['path']):
                if item['ownership']=='owned':identities[lc.process_key(item['identity'])]=item['identity']
            for row in rows:
                if (lc.process_key(row) not in baseline and sample['monotonic']>=phase['started'] and
                    sponsored_trace_server(row,phase['pid'],self.prepared.get('ue_root'))):
                    identities[lc.process_key(row)]=row
        return list(identities.values())

    def _quiet(self, name):
        owned={lc.process_key(x) for x in self._phase_owned(name)}
        latest=self.samples[-1] if self.samples else None
        lc.require(latest and 0<=self.clock()-latest['monotonic']<=2,'fresh quiet process sample required')
        rows=latest['processes']
        live=[r for r in rows if lc.process_key(r) in owned]
        extras=[x for x in lc.classify_processes(rows,self._phase_owned(name),self.prepared['binary_pins']['ue']['path'])
                if x['ownership']=='contamination']
        return not live and not extras

    def finish_metal(self, timeout=40):
        lc.require(self.phase=='metal' and self.closing and 0<=timeout<=40,'bounded closing Metal only')
        p=self.phases['metal'];p['thread'].join(timeout)
        lc.require(not p['thread'].is_alive(),'actual parent wait missing')
        # Give the independent observer one new sample; do not query App bindings.
        time.sleep(.6)
        errors=[]
        try:
            self.snapshot('metal-final')
            from .actions import load_trace
            refs=[self._ref(f) for f in sorted((self.output/'metal/trace').iterdir()) if f.is_file()]
            load_trace(refs,expected_binding=self.binding)
        except (lc.Invalid,ValueError,KeyError,TypeError,OSError) as error:errors.append(str(error))
        quiet=self._quiet('metal')
        if not quiet:errors.append('owned descendants or extra UE still alive')
        if self.clock()-p['started']>420:errors.append('Metal phase exceeded420s')
        normal=p['wait_exit']==0 and not p['forced_cleanup'] and not errors and quiet
        p.update(normal=normal,errors=errors,sealed_monotonic=self.clock(),trace_refs=refs if 'refs' in locals() else [])
        self.phase=None;self.closing=True
        return self._write(self.output/'metal-execution.json',self._phase_report('metal'))

    def freeze_native_manifest(self, manifest_ref, expected_sha256):
        lc.require('metal' in self.phases and 'sealed_monotonic' in self.phases['metal'] and
                   self.phase is None and self.native_manifest is None,'finished/skipped Metal must precede one manifest freeze')
        lc.require(self.phases['metal'].get('skipped') or self._quiet('metal'),'previous phase not quiet')
        lc.require(self.clock()-self.phases['metal']['sealed_monotonic']<=120,'raw handoff exceeds120s')
        lc.require(manifest_ref['sha256']==expected_sha256,'external Native manifest SHA required')
        from .native_replay import validate_native_manifest
        sources=deepcopy(self.card['legacy_sources']);public=list(self.card['public_paths'])
        if not self.phases['metal'].get('skipped'):
            frames=self._trace();indices=[i for i,f in enumerate(frames) if f['request']['operation']=='observe']
            refs=self.phases['metal']['trace_refs']
            if indices:
                sources.append(dict(pins_ref=self.prepared['pins_ref'],trace_refs=refs,observe_frame_indices=indices,
                    trace_identity={k:self.binding[k] for k in ('host_pid','worker_pid','generation')}))
                public.extend([r['path'] for r in refs]+[self.prepared['pins_ref']['path']])
        public=list(dict.fromkeys(public+[manifest_ref['path']]))
        result=validate_native_manifest(manifest_ref,expected_run_id=self.card['run_id'],
            expected_product_source_sha=self.prepared['product_source_sha'],expected_tool_source_sha=self.prepared['tool_source_sha'],
            allowed_sources=sources,public_paths=public)
        self.native_manifest=deepcopy(manifest_ref)
        self._event('native_manifest_frozen',manifest_ref=manifest_ref,case_count=len(result['cases']))
        return result

    def start_native(self):
        lc.require(self.native_manifest is not None and 'native' not in self.phases and self.phase is None,
                   'one frozen Native phase only')
        inventory=native_test_inventory(self.prepared['native_source_pins'],self.prepared['product_root'])
        inventory_ref=self._write(self.output/'native-test-inventory.json',inventory)
        ddc,ddc_argv=native_cache_arguments(self.prepared['output_root'],self.card['run_id'],self.output)
        ddc.mkdir(mode=0o700) # exclusive, never reuse another run's cache
        directory=self.output/'native';directory.mkdir(mode=0o700);(directory/'user').mkdir(mode=0o700)
        result_path=directory/'replay-result.json'
        env={k:v for k,v in os.environ.items() if not k.startswith('EDGEWORLD_') and k not in ('PYTHONHOME','PYTHONPATH')}
        env.update(dict(zip(REPLAY_ENV,('1',self.native_manifest['path'],self.native_manifest['sha256'],str(result_path)))))
        argv=[self.prepared['binary_pins']['ue']['path'],self.prepared['project'],
            '/Engine/Maps/Entry?game=/Script/Engine.GameModeBase','-game','-NullRHI','-unattended','-NoSplash','-NoSound','-NoCrashDialog',
            '-notraceserver','-traceautostart=0',
            '-ExecCmds=Automation RunTests '+ '+'.join('^'+s for s in SELECTORS),
            '-TestExit=Automation Test Queue Empty','-UserDir='+str(directory/'user'),'-abslog='+str(directory/'ue.log')]+ddc_argv
        value=self._spawn_reserved('native',argv,env,directory)
        self.phases['native'].update(inventory_ref=inventory_ref,ddc_path=str(ddc),ddc_arguments=ddc_argv)
        return value

    def _native_writer_barrier(self, deadline):
        """Three fresh quiet samples and unchanged logs before any final reference."""
        phase=self.phases['native'];paths=[Path(phase['directory'])/name for name in ('console.log','ue.log','replay-result.json')]
        previous=None;quiet_since=None;consecutive=0;last_sample=None;observations=[]
        while self.clock()<deadline:
            lc.require(not self.observer_error and self.observer is not None and self.observer.is_alive(),
                       'continuous observer required through native writer completion')
            with self.lock:sample=deepcopy(self.samples[-1]) if self.samples else None
            if sample and sample['monotonic']>=phase['wait_monotonic'] and sample['monotonic']!=last_sample:
                last_sample=sample['monotonic'];quiet=self._quiet('native')
                try:fingerprints=[file_fingerprint(path) for path in paths]
                except (OSError,lc.Invalid):fingerprints=None
                observations.append(dict(sample_ref=sample['raw_ref'],monotonic=last_sample,
                                         all_owned_quiet=quiet,files=fingerprints))
                if quiet and fingerprints is not None:
                    if fingerprints==previous:
                        consecutive+=1
                    else:quiet_since=last_sample;consecutive=1
                    if consecutive>=3 and last_sample-quiet_since>=.75:
                        return dict(format='universe-i17-native-writer-barrier.v1',complete=True,
                            confirmed_monotonic=self.clock(),stable_since_monotonic=quiet_since,
                            observations=observations,files=fingerprints)
                    previous=fingerprints
                else:previous=None;quiet_since=None;consecutive=0
            time.sleep(.05)
        return dict(format='universe-i17-native-writer-barrier.v1',complete=False,
                    confirmed_monotonic=self.clock(),observations=observations,files=previous or [])

    def _verify_native_frozen_files(self):
        phase=self.phases['native'];frozen=phase.get('frozen_files',[])
        lc.require(frozen,'native evidence was not frozen after writer completion')
        for expected in frozen:
            lc.require(file_fingerprint(expected['path'])==expected,'native evidence mutated after writer completion')

    def wait_native(self, timeout=180):
        lc.require(self.phase=='native' and 0<=timeout<=180,'one bounded actual Native wait')
        p=self.phases['native'];p['thread'].join(timeout)
        lc.require(not p['thread'].is_alive(),'Native actual parent wait incomplete')
        deadline=min(p['started']+178,self.started+810)
        barrier=self._native_writer_barrier(deadline)
        p['writer_barrier_ref']=self._write(self.output/'native-writer-barrier.json',barrier)
        p['frozen_files']=barrier['files'] if barrier['complete'] else []
        result_path=self.output/'native/replay-result.json';log_path=self.output/'native/ue.log'
        errors=[]
        if not barrier['complete']:errors.append('native writers did not become quiet and stable within phase budget')
        try:
            log=log_path.read_text();found=re.findall(r'Found\s+(\d+)\s+automation tests',log,re.I)
            completed=re.findall(r'Test Completed\. Result=\{([^}]+)\} Name=\{[^}]*\} Path=\{([^}]+)\}',log)
            lc.require(found and found[-1]=='4' and len(completed)==4 and
                {s for _,s in completed}==set(SELECTORS) and all(r=='Success' for r,_ in completed),'four exact Native tests not successful')
            ddc_pattern=r'Isolated:\s+Using data cache path\s+'+re.escape(p['ddc_path'])+r'/?\s*:\s*Writable'
            lc.require(re.search(ddc_pattern,log) is not None,'actual isolated writable filesystem DDC path not confirmed')
            lc.require(re.search(r'LogZenServiceInstance[^\n]*Launching',log) is None,'unexpected Zen service launch in native run')
            result=json.loads(result_path.read_bytes());manifest=lc.json_ref(self.native_manifest)
            lc.require(result['format']=='universe-i15-native-replay-result.v1' and result['host_pid']==p['pid'] and
                result['manifest_sha256']==self.native_manifest['sha256'] and result['case_count']==len(manifest['cases']) and
                len(result['cases'])==result['case_count'],'actual nonzero Native replay result')
        except (lc.Invalid,ValueError,KeyError,TypeError,OSError) as error:errors.append(str(error))
        quiet=self._quiet('native')
        if not quiet:errors.append('Native or extra UE still alive')
        evidence_frozen=barrier['complete']
        if evidence_frozen:
            try:self._verify_native_frozen_files()
            except (lc.Invalid,OSError) as error:errors.append(str(error));evidence_frozen=False
        if self.clock()-p['started']>180:errors.append('Native phase exceeded180s')
        p.update(normal=p['wait_exit']==0 and not p['forced_cleanup'] and not errors and quiet,
                 errors=errors,sealed_monotonic=self.clock())
        self.phase=None;self.closing=True
        identity=p.get('identity')
        lc.require(identity is not None,'actual observed Native identity missing')
        def frozen_ref(name):
            if not evidence_frozen:return None
            row=next(item for item in p['frozen_files'] if Path(item['path']).name==name)
            ref=dict(path=row['path'],sha256=row['sha256']);self.public_refs[ref['path']]=ref;return ref
        base=self._phase_report('native')
        value=dict(base,format='universe-i15-native-execution.v1',host_pid=p['pid'],process_start=identity['start'],
            parent_pid=p['parent_pid'],cwd=self.prepared['product_root'],environment={k:p['environment'][k] for k in REPLAY_ENV},
            selectors=list(SELECTORS),manifest_ref=self.native_manifest,result_ref=frozen_ref('replay-result.json'),
            parent_wait=dict(observed=True,exit_code=p['wait_exit'],host_pid=p['pid'],process_start=identity['start'],parent_pid=p['parent_pid']),
            forced_cleanup=bool(p['forced_cleanup']),started_monotonic=p['started'],ended_monotonic=p['wait_monotonic'],
            controller_run_id=self.card['run_id'],clock_id=self.clock_binding['id'],log_ref=frozen_ref('ue.log'),
            console_ref=frozen_ref('console.log'),evidence_frozen=evidence_frozen,
            deferred_evidence_paths=[] if evidence_frozen else [str(result_path),str(log_path),str(self.output/'native/console.log')],
            resource_elapsed_seconds=self.clock()-self.started,
            time_kind='controller-monotonic-actual-wait')
        return self._write(self.output/'native-execution.json',value)

    def _phase_report(self,name):
        return {k:v for k,v in self.phases[name].items() if k not in ('thread','environment')}

    def _storage_bytes(self):
        total=0
        root=Path(self.prepared['output_root'])
        for parent,dirs,files in os.walk(root,followlinks=False):
            for name in dirs+files:
                p=Path(parent)/name
                lc.require(not p.is_symlink(),'output symlink rejected for resource accounting')
            for name in files:total+=(Path(parent)/name).stat().st_size
        return total

    def seal(self):
        lc.require(not self.closed and self.phase is None and 'native' in self.phases and
                   'sealed_monotonic' in self.phases['native'],'completed phase wait required before seal')
        lc.require(self.clock()-self.phases['native']['sealed_monotonic']<=90,'final seal exceeded90s')
        if self.phases['native'].get('frozen_files'):self._verify_native_frozen_files()
        self.stop_event.set();self.observer.join(3)
        lc.require(not self.observer.is_alive(),'observer final sample not sealed')
        quiet=all(p.get('skipped') or self._quiet(n) for n,p in self.phases.items())
        if self.phases['native'].get('frozen_files'):self._verify_native_frozen_files()
        elapsed=self.clock()-self.started;size=self._storage_bytes()
        value=dict(format='universe-i15-capability-resource.v1',run_id=self.card['run_id'],clock=self.clock_binding,
            elapsed_seconds=elapsed,storage_bytes=size,all_processes_quiet=quiet,observer_error=self.observer_error,
            phases={n:self._phase_report(n) for n in self.phases},g_b2_granted=False,standard_pair=False,
            decision='within_budget' if elapsed<=900 and size<=POLICY['bytes'] and quiet and not self.observer_error else 'fail')
        self.closed=True
        return self._write(self.output/'resource.json',value)

    def abort(self, reason):
        """Failure cleanup of exact observed owned processes; no App lookup."""
        lc.require(not self.closed,'controller already sealed')
        self.closing=True;self.pending={};self.failures.append(str(reason))
        name=self.phase
        if name is not None:
            p=self.phases[name]
            p['forced_cleanup'].append(dict(kind='abort',reason=str(reason),monotonic=self.clock()))
            # Popen owns/reaps its child; other processes require the full observed
            # PID/start/argv identity to still match a fresh passive snapshot.
            known=self._phase_owned(name)
            raw=self.output/('abort-%d.ps'%time.monotonic_ns())
            sample=lc.observe_once(raw);self.public_refs[sample['raw_ref']['path']]=sample['raw_ref']
            current={lc.process_key(row):row for row in sample['processes']}
            for row in reversed(known):
                if row['pid']!=p['pid'] and lc.process_key(row) in current:
                    try:os.kill(row['pid'],signal.SIGTERM)
                    except ProcessLookupError:pass
            if self.process.poll() is None:self.process.terminate()
            try:self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=5)
            p['thread'].join(6)
            p.update(normal=False,sealed_monotonic=self.clock(),errors=[str(reason)])
            self.phase=None
        if self.observer is not None:
            self.stop_event.set();self.observer.join(3)
        quiet=all(p.get('skipped') or self._quiet(n) for n,p in self.phases.items()) if self.samples else False
        self.closed=True
        return self._write(self.output/'abort.json',dict(format='universe-i15-capability-abort.v1',run_id=self.card['run_id'],
            reason=str(reason),normal=False,all_processes_quiet=quiet,elapsed_seconds=self.clock()-self.started,
            storage_bytes=self._storage_bytes(),phases={n:self._phase_report(n) for n in self.phases},g_b2_granted=False))
