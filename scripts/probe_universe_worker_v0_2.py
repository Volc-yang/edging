#!/usr/bin/env python3
"""Bounded trusted-owner I10B CLI probe. Runtime is explicit; preflight is stdlib-only."""
from __future__ import annotations
import argparse
from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import select
import signal
import shutil
import stat
import subprocess
import sys
import time
import traceback

from engine.universe_authority.codec import DeploymentContext, HeadBinding, OwnerSession, ProvisionSpec, canonical, decode, digest, f64
from engine.universe_authority.genesis_adapter import measure_installed_build, measure_runtime_options
from engine.universe_authority.records import validate_closure, verify_observation, wire
from engine.universe_authority.trust import provision, open_trust
from engine.universe_authority.worker import load_owner_config, public_pins, validate_asset_audit
from engine.universe_authority.world_initialization import physics_parameters

REPO = Path(__file__).resolve().parents[1]
EXPECTED_ADAPTER = '15f5b96bb0381781d0357eb93510622afe6ec3d5caf60adb5ed8190ff6abb192'
EXPECTED_BUILD = 'a1bd8768517734c47f6c3e0c2b532343046733778feaa22201b0d6b1e9b65ee6'
EXPECTED_OPTIONS = 'ef8d9323a6642c84ec2c788e5b0c542a1705c9d41268bbe5fce18ef3a62f3fd6'
NATIVE_REFERENCE = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I8-20261102-options-attempt2-resolved/native-inputs-before.json')
ASSETS = REPO/'doc/evidence/universe-I10/approved-asset-inputs'
WORLD = 'edgeworld-universe'


def check(value, detail):
    if not value: raise RuntimeError(detail)


def write(path, value):
    raw = json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    with path.open('xb') as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        while block := stream.read(1<<20): h.update(block)
    return h.hexdigest()


def mapping(path):
    return {str(p.relative_to(path)):dict(bytes=p.stat().st_size,sha256=sha(p))
        for p in sorted(path.rglob('*')) if p.is_file() and not p.is_symlink()}


def source_inputs(output):
    paths = [Path(__file__), *sorted((REPO/'engine/universe_authority').glob('*.py')),
             ASSETS/'candidate-record.json', ASSETS/'collection-first.json', NATIVE_REFERENCE]
    result = {}
    for index,path in enumerate(paths):
        raw = path.read_bytes()
        target = output/'source-inputs'/str(index)
        target.parent.mkdir(exist_ok=True)
        target.write_bytes(raw)
        result[str(path)] = dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copy=str(target.relative_to(output)))
    write(output/'source-inputs.json',result)
    return result


def native_inputs():
    reference = json.loads(NATIVE_REFERENCE.read_bytes())
    check(len(reference) == 37,'native reference count drift')
    actual = {}
    for name,expected in reference.items():
        path = Path(name)
        actual[name] = dict(expected,bytes=path.stat().st_size,sha256=sha(path))
        check(actual[name] == expected,'native dependency drift: '+name)
    return actual


def identity(output):
    check(sha(REPO/'engine/universe_authority/genesis_adapter.py') == EXPECTED_ADAPTER,'adapter drift')
    build,files = measure_installed_build(world_id=WORLD,build_id='provider-build')
    write(output/'provider-build.json',build); write(output/'installed-sources.json',files)
    check(build['body']['source_file_count'] == len(files) == 264,'package count drift')
    check(digest(build) == EXPECTED_BUILD,'actual build drift')
    write(output/'native-before.json',native_inputs())
    return build


def preflight(output):
    build = identity(output)
    assets = decode((ASSETS/'candidate-record.json').read_bytes())
    audit = decode((ASSETS/'collection-first.json').read_bytes())
    validate_asset_audit(assets,audit)
    check('genesis' not in sys.modules,'preflight imported solver')
    write(output/'preflight.json',dict(ok=True,solver_imported=False,build=digest(build),artifact_class='genesis-runtime',runtime_gate=False))


def reap_owned(child, timeout, *, close_stdin):
    """Always reap this exact owned PID, even when pipe close or wait fails."""
    outcome = dict(pid=child.pid,cleanup='normal',reaped=False)
    primary = None
    if close_stdin and child.stdin is not None:
        try:child.stdin.close()
        except Exception as exc:
            primary = exc
            outcome['stdin_close_exception'] = traceback.format_exc()
    try:
        code = child.wait(timeout=max(0.01,timeout))
    except subprocess.TimeoutExpired as exc:
        primary = primary or exc
        outcome['wait_exception'] = traceback.format_exc()
        outcome['cleanup'] = 'terminated-after-timeout'
        try:child.terminate()
        except ProcessLookupError:pass
        try:code = child.wait(timeout=5)
        except subprocess.TimeoutExpired:
            outcome['cleanup'] = 'killed-after-timeout'
            try:child.kill()
            except ProcessLookupError:pass
            code = child.wait(timeout=5)
    outcome.update(exit_code=code,reaped=True,end_unix=time.time())
    return outcome,primary


def cleanup_check(output):
    # Actual CPU child processes, no Genesis import/init, no keys or authority.
    argv=[sys.executable,'-c','import time;time.sleep(30)']
    child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    outcome,error=reap_owned(child,0.03,close_stdin=False)
    write(output/'pins-timeout-check.json',dict(outcome,argv=argv,error_type=type(error).__name__))
    check(outcome['reaped'] and outcome['cleanup'] != 'normal' and isinstance(error,subprocess.TimeoutExpired),'pins timeout not reaped')
    argv=[sys.executable,'-c','import time;time.sleep(0.05)']
    child=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    child.stdin.close()
    class BrokenPipe:
        def close(self):raise BrokenPipeError('explicit synthetic stdin close failure')
    child.stdin=BrokenPipe()
    outcome,error=reap_owned(child,2,close_stdin=True)
    write(output/'stdin-close-check.json',dict(outcome,argv=argv,error_type=type(error).__name__))
    check(outcome['reaped'] and outcome['exit_code'] == 0 and isinstance(error,BrokenPipeError),'stdin close skipped reap')
    check('genesis' not in sys.modules,'cleanup check imported solver')
    write(output/'cleanup-check.json',dict(ok=True,solver_imported=False))


class Probe:
    def __init__(self,output,start):
        self.output,self.start = output,start
        self.authority = output.parent/(output.name+'-authority')
        self.scratch = output.parent/(output.name+'-scratch')
        self.owner_dir = output.parent/(output.name+'-owner')
        self.key_dir = output.parent/(output.name+'-keys')
        self.child = None
        self.stderr_file = self.stdout_file = None
        self.buffer = b''
        self.action = 0
        self.commands = []
        self.children = []
        self.owned = []

    def budget(self):
        check(time.monotonic()-self.start < 240,'runtime budget exhausted')
        total = sum(p.stat().st_size for root in (self.output,self.authority,self.scratch)
                    for p in root.rglob('*') if p.is_file())
        check(total < (256<<20)-(32<<20),'raw budget reserve exhausted')

    def capture(self,label):
        self.budget()
        value = dict(authority=mapping(self.authority),scratch=mapping(self.scratch))
        write(self.output/('map-'+label+'.json'),value)
        for root in (self.authority,):
            for p in root.rglob('*'):
                if p.is_file() and not p.is_symlink():
                    target = self.output/'unique-authority-bytes'/sha(p)
                    target.parent.mkdir(exist_ok=True)
                    if not target.exists():
                        with target.open('xb') as stream: stream.write(p.read_bytes())
        return value

    def setup(self,build):
        self.owner_dir.mkdir(mode=0o700)
        anchor = provision(self.key_dir,spec=ProvisionSpec(WORLD,self.authority))
        self.context = DeploymentContext(WORLD,str(self.authority),anchor.trust_anchor,digest(build),EXPECTED_OPTIONS)
        self.session = OwnerSession('owner-local',True,('retain_snapshot','physics_step'))
        input_paths = dict(build=self.output/'provider-build.json',options=self.output/'resolved-options.json',
            assets=ASSETS/'candidate-record.json',asset_audit=ASSETS/'collection-first.json')
        specs = {name:dict(path=str(path),sha256=sha(path)) for name,path in input_paths.items()}
        self.configs = {}
        for mode in ('initialize','existing'):
            config = dict(config_version='universe-owner-launch.v0.1',mode=mode,context=asdict(self.context),
                session=dict(principal=self.session.principal,can_initialize=self.session.can_initialize,allowed_actions=list(self.session.allowed_actions)),key_dir=str(self.key_dir),scratch=str(self.scratch),inputs=specs)
            path = self.owner_dir/(mode+'.json')
            fd = os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'wb') as stream: stream.write(canonical(config))
            self.configs[mode] = path
        # Metadata only: keys are never read/copied/hashed by the driver.
        permissions = {}
        for path in (self.owner_dir,self.key_dir,*self.configs.values(),self.key_dir/'authority.key'):
            info = path.stat()
            permissions[str(path)] = dict(uid=info.st_uid,mode=oct(stat.S_IMODE(info.st_mode)),nlink=info.st_nlink)
            check(info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == (0o700 if path.is_dir() else 0o600),'owner permissions')
        write(self.output/'owner-permissions.json',permissions)
        argv = [sys.executable,'-m','engine.universe_authority.worker','--owner-config',str(self.configs['initialize']),'--print-public-pins']
        with (self.output/'pins.stdout').open('xb') as out,(self.output/'pins.stderr').open('xb') as err:
            child = subprocess.Popen(argv,cwd=REPO,stdout=out,stderr=err)
            registration=dict(child=child,label='pins',reaped=False);self.owned.append(registration)
            outcome,error=reap_owned(child,min(15,240-(time.monotonic()-self.start)),close_stdin=False)
            registration['reaped']=outcome['reaped']
        write(self.output/'pins-process.json',dict(outcome,argv=argv))
        if error:raise error
        code=outcome['exit_code']
        raw = (self.output/'pins.stdout').read_bytes()
        owner = load_owner_config(str(self.configs['initialize']))
        expected = public_pins(owner)
        check(code == 0 and len(expected) == 12 and raw == canonical(expected)+b'\n','public pins')
        check(not self.authority.exists() and not self.scratch.exists(),'pins caused side effect')
        write(self.output/'public-pins.json',expected)
        self.verifier = open_trust(self.key_dir,context=self.context)

    def launch(self,mode):
        self.budget()
        self.buffer = b''
        label = 'worker-'+str(len(self.children)+1)
        argv = [sys.executable,'-m','engine.universe_authority.worker','--owner-config',str(self.configs[mode])]
        self.stderr_file = (self.output/(label+'.stderr')).open('xb')
        self.stdout_file = (self.output/(label+'.stdout')).open('xb')
        self.child = subprocess.Popen(argv,cwd=REPO,stdin=subprocess.PIPE,stdout=subprocess.PIPE,
            stderr=self.stderr_file,start_new_session=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        self.owned.append(dict(child=self.child,label=label,reaped=False))
        row = dict(argv=argv,pid=self.child.pid,mode=mode,start_unix=time.time())
        self.children.append(row); write(self.output/(label+'-start.json'),row)
        if mode == 'initialize':
            while not (self.authority/'identity.json').exists():
                self.budget();check(self.child.poll() is None,'worker exited during registration');time.sleep(0.01)

    def finish(self):
        if self.child is None:return
        child=self.child
        outcome,error=reap_owned(child,max(1,min(20,240-(time.monotonic()-self.start))),close_stdin=True)
        registration=next(row for row in self.owned if row['child'] is child)
        registration['reaped']=outcome['reaped']
        tail=child.stdout.read()
        self.stdout_file.write(tail);self.stdout_file.close();self.stderr_file.close()
        row=dict(self.children[-1],**outcome,trailing_stdout_bytes=len(tail))
        write(self.output/('worker-'+str(len(self.children))+'-exit.json'),row)
        child.stdout.close();self.child=None
        if error:raise error
        check(outcome['exit_code'] == 0 and not tail and not self.buffer,'worker exit/protocol tail')

    def cleanup_remaining(self):
        for registered in self.owned:
            if not registered['reaped']:
                outcome,error=reap_owned(registered['child'],1,close_stdin=True)
                registered['reaped']=outcome['reaped']
                write(self.output/(registered['label']+'-emergency-cleanup.json'),outcome)
        write(self.output/'owned-processes.json',[dict(pid=row['child'].pid,label=row['label'],reaped=row['reaped'],exit_code=row['child'].returncode) for row in self.owned])

    def call(self,operation,*,expected_error=None,**payload):
        self.budget(); self.action += 1
        request_id = 'r'+str(self.action)
        request = dict(protocol_version=1,request_id=request_id,operation=operation,payload=dict(
            domain='edgeworld.universe.authority',version='0.2',world_id=WORLD,**payload))
        prefix = f'{self.action:03d}-{operation}'
        before = self.capture(prefix+'-before')
        raw = json.dumps(request,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')+b'\n'
        with (self.output/(prefix+'.request')).open('xb') as stream:stream.write(raw)
        self.child.stdin.write(raw);self.child.stdin.flush()
        while b'\n' not in self.buffer:
            remaining = 240-(time.monotonic()-self.start)
            check(remaining > 0,'response timeout')
            check(select.select([self.child.stdout],[],[],remaining)[0],'response timeout')
            block = os.read(self.child.stdout.fileno(),65536)
            check(block,'worker EOF before reply')
            self.stdout_file.write(block);self.stdout_file.flush()
            self.buffer += block
            check(len(self.buffer) <= 1048577,'stdout pollution/limit')
        response_raw,self.buffer = self.buffer.split(b'\n',1)
        with (self.output/(prefix+'.response')).open('xb') as stream:stream.write(response_raw+b'\n')
        response = wire(response_raw+b'\n')
        check(response['request_id'] == request_id and response['protocol_version'] == 1,'response correlation')
        after = self.capture(prefix+'-after')
        if expected_error:
            check(response['ok'] is False and response['error']['code'] == expected_error,'unexpected business error')
            check(before == after,'rejected operation changed authority/scratch')
            return response
        check(response['ok'] is True,'operation failed: '+json.dumps(response.get('error')))
        result = response['result']
        check((result['world_id'],result['operation'],result['version']) == (WORLD,operation,'0.2'),'result wrapper')
        if operation in ('status','observe','prepare'):
            check(before == after,'read/prepare mutated authority/scratch')
        if operation == 'observe':
            proof = verify_observation(response_raw+b'\n',context=self.context,expected_request_id=request_id,
                tick=payload['tick'],revision=payload['revision'],watermark=payload['watermark'],trusted_head=self.binding)
            return proof
        result = result['payload']
        if 'head_binding' in result:
            self.binding = HeadBinding(**result['head_binding'])
            for key in ('world_id','authority_root','trust_algorithm','trust_anchor','expected_build','expected_options','artifact_class'):
                check(getattr(self.binding,key) == getattr(self.context,key),'binding pin mismatch')
        return result

    def closure(self,label):
        records = [decode(p.read_bytes()) for p in sorted((self.authority/'objects').glob('*.json'))]
        blobs = {p.stem:p.read_bytes() for p in (self.authority/'blobs').iterdir() if p.is_file()}
        for p in (self.authority/'objects').glob('*.json'):check(digest(decode(p.read_bytes())) == p.stem,'object digest')
        for h,raw in blobs.items():check(hashlib.sha256(raw).hexdigest() == h,'blob digest')
        closure = validate_closure(records,self.binding.head,world_id=WORLD,domain_version='0.2',context=self.context,trust_verifier=self.verifier,blobs=blobs)
        write(self.output/('closure-'+label+'.json'),dict(head=closure.head,records=len(records),raw_blobs={h:len(raw) for h,raw in blobs.items()}))
        return closure

    def state(self,label,*,tick,revision,budget,cursor,steps,prior=None):
        closure = self.closure(label); records = closure.records
        state = records[records[closure.head]['refs']['state']]
        snapshot = records[state['refs']['snapshot']]
        sample = records[snapshot['refs']['sample']]
        check((state['body']['tick'],state['body']['revision'],state['body']['budget'],state['body']['random_cursor'],snapshot['body']['physical_step_count']) == (tick,revision,budget,cursor,steps),'state counters')
        influence = state['body']['development_mm']
        if prior is not None:
            old_state,old_sample = prior
            if tick != old_state['body']['tick']:
                before = Fraction.from_float(f64(old_sample['body']['bodies'][0]['position_m'][2]['$f64']))
                after = Fraction.from_float(f64(sample['body']['bodies'][0]['position_m'][2]['$f64']))
                check(influence == round((after-before)*1000),'independent Fraction D')
            else:check(influence == old_state['body']['development_mm'],'retain changed D')
        else:check(influence is None,'initial D')
        write(self.output/('numerics-'+label+'.json'),dict(state=state,snapshot=snapshot,sample=sample,independent_influence_mm=influence))
        return state,sample

    def command(self,label,action,case=None):
        current = self.call('status')
        closure = self.closure('prepare-'+label); records=closure.records
        prior = records[current['state']]; snapshot=records[prior['refs']['snapshot']]
        proposal=dict(domain='edgeworld.universe.authority',version='0.2',world_id=WORLD,kind='proposal',id='proposal-'+label,
            body=dict(principal=self.session.principal,output='explicit I10B abstract causal action'),refs={})
        intent=dict(domain='edgeworld.universe.authority',version='0.2',world_id=WORLD,kind='intent',id='intent-'+label,
            body=dict(principal=self.session.principal,command_id='command-'+label,expected_revision=prior['body']['revision'],
                random_cursor=prior['body']['random_cursor'],action=action,tick_delta=1 if action=='physics_step' else 0,
                case_id=case,budget=1 if action=='physics_step' else 0),refs=dict(config=snapshot['refs']['config'],binding=snapshot['refs']['binding']))
        payload=dict(principal=self.session.principal,proposal=proposal,intent=intent,approval_id='approval-'+label,command_record_id='command-record-'+label)
        prepared=self.call('prepare',**payload)
        check(prepared == self.call('prepare',**payload),'prepare not deterministic')
        advance=dict(principal=self.session.principal,command_records=prepared['command_records'],command_digest=prepared['command_digest'])
        result=self.call('advance',**advance)
        before=self.capture(label+'-retry-before')
        check(result == self.call('advance',**advance),'advance retry result')
        check(before == self.capture(label+'-retry-after'),'advance retry changed state/raw/scratch')
        self.commands.append((payload,advance,result))
        return result

    def run(self,build):
        self.setup(build);self.launch('initialize')
        self.call('status',expected_error='NOT_READY')
        check(not (self.authority/'HEAD.json').exists() and not self.scratch.exists(),'status initialized solver')
        self.call('initialize',test_profile=self.context.archive_profile)
        self.call('status');prior=self.state('initial',tick=0,revision=0,budget=8,cursor=0,steps=0)
        self.call('observe',tick=0,revision=0,watermark=0)
        for label,action,case,tick,rev,budget,cursor,steps in (
            ('retain-one','retain_snapshot',None,0,1,8,0,0),('weak','physics_step','weak',1,2,7,1,8),
            ('strong','physics_step','strong',2,3,6,2,16),('retain-four','retain_snapshot',None,2,4,6,2,16)):
            self.command(label,action,case);prior=self.state(label,tick=tick,revision=rev,budget=budget,cursor=cursor,steps=steps,prior=prior)
        pairs=((0,0),(0,1),(1,2),(2,3),(2,4))
        for tick,revision in pairs:self.call('observe',tick=tick,revision=revision,watermark=revision)
        self.call('observe',expected_error='WATERMARK',tick=1,revision=2,watermark=1)
        bad=dict(self.commands[0][1],principal='wrong-principal')
        self.call('advance',expected_error='AUTHORIZATION',**bad)
        final=self.call('status');before=self.capture('before-first-exit');self.finish()
        self.launch('existing')
        check(self.children[0]['pid'] != self.children[1]['pid'],'worker PID not fresh')
        check(final == self.call('status'),'restart status drift')
        for tick,revision in pairs:self.call('observe',tick=tick,revision=revision,watermark=revision)
        for prepared,advance,original in self.commands:
            retry=self.call('prepare',**prepared)
            check(retry['command_records'] == advance['command_records'],'committed prepare restart drift')
            result=self.call('advance',**advance)
            check((result['manifest'],result['result']) == (original['manifest'],original['result']),'committed result restart drift')
        check(before == self.capture('after-restart-retries'),'restart/read/retry changed authority/raw/scratch')
        self.finish()
        check(before == self.capture('after-final-exit'),'shutdown changed authority/raw/scratch')
        write(self.output/'accepted.json',dict(ok=True,scope='I10B-real-CLI-Genesis-single-root',pids=[r['pid'] for r in self.children],history_pairs=pairs,physical_steps=16))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('preflight','cleanup-check','runtime'))
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    check(args.output.is_absolute() and args.output.resolve() == args.output,'canonical output required')
    args.output.mkdir(mode=0o700,exist_ok=False)
    start=time.monotonic();probe=None;code=0
    def stop_requested(signum,frame):
        raise TimeoutError('owner watchdog signal '+str(signum))
    signal.signal(signal.SIGTERM,stop_requested)
    signal.signal(signal.SIGALRM,stop_requested)
    signal.alarm(240 if args.operation == 'runtime' else 120)
    write(args.output/'invocation.json',dict(argv=sys.argv,pid=os.getpid(),python=sys.version,executable=sys.executable,
        executable_sha256=sha(Path(sys.executable).resolve()),source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip(),
        cwd=str(REPO),operation=args.operation,start_unix=time.time(),
        environment={k:os.environ.get(k) for k in ('PYTHONPATH','PYTHONDONTWRITEBYTECODE','VIRTUAL_ENV')},runtime_seconds=240,outer_seconds=300,raw_bytes_cap=256<<20))
    try:
        source_inputs(args.output)
        if args.operation == 'preflight':preflight(args.output)
        elif args.operation == 'cleanup-check':cleanup_check(args.output)
        else:
            build=identity(args.output)
            options=measure_runtime_options(physics_parameters(),approved_build=build,options_id='resolved-options')
            write(args.output/'resolved-options.json',options)
            check(digest(options) == EXPECTED_OPTIONS,'actual options drift')
            probe=Probe(args.output,start);probe.run(build)
            check(native_inputs() == json.loads((args.output/'native-before.json').read_bytes()),'native changed during run')
            write(args.output/'native-after.json',native_inputs())
    except Exception:
        code=1
        with (args.output/'exception.txt').open('x') as stream:traceback.print_exc(file=stream)
    finally:
        signal.alarm(0)
        if probe is not None and probe.child is not None:
            try:probe.finish()
            except Exception:
                with (args.output/'cleanup-exception.txt').open('x') as stream:traceback.print_exc(file=stream)
        if probe is not None:
            try:probe.cleanup_remaining()
            except Exception:
                code=1
                with (args.output/'owned-cleanup-exception.txt').open('x') as stream:traceback.print_exc(file=stream)
        write(args.output/'exit.json',dict(exit_code=code,pid=os.getpid(),elapsed_seconds=time.monotonic()-start,end_unix=time.time()))
        write(args.output/'raw-index.json',mapping(args.output))
        signal.alarm(0)
    return code

if __name__=='__main__':raise SystemExit(main())
