"""I10A CPU-only synthetic transport tests; no real Genesis import or GPU."""
from copy import deepcopy
from dataclasses import asdict, replace
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from engine.universe_authority.codec import ContractError, DeploymentContext, OwnerSession, ProvisionSpec, canonical, digest
from engine.universe_authority.physics import PhysicsInitialDraft
from engine.universe_authority.store import BlobWrite, StoreError
from engine.universe_authority.trust import provision
from engine.universe_authority.worker import OwnerConfig, load_owner_config, load_inputs, public_pins, open_runtime, dispatch, serve, validate_asset_audit, validate_scratch
from engine.universe_authority.world_initialization import physics_parameters, enumerate_world
from tests.test_universe_composite_commands import SyntheticProvider, CompositeCase

FIXTURES = Path(__file__).resolve().parents[1] / 'doc/fixtures/universe_authority_v0_2'


class InitialSyntheticProvider(SyntheticProvider):
    def __init__(self, template, raw, static):
        super().__init__(template,raw)
        self.static = static
        self.initializes = self.closes = 0

    def initialize(self, *, ids):
        self.initializes += 1
        rows = deepcopy(self.template[26:29])
        remap = {}
        for record,identifier in zip(rows,(ids.sample,ids.checkpoint_descriptor,ids.snapshot)):
            original = digest(record)
            record['id'] = identifier
            record['refs'] = {k:remap.get(v,v) for k,v in record['refs'].items()}
            remap[original] = digest(record)
        descriptor = rows[1]
        blob = BlobWrite(descriptor['body']['payload_sha256'],self.raw[descriptor['body']['payload_sha256']],
                         descriptor['body']['media_type'],descriptor['body']['artifact_class'])
        return PhysicsInitialDraft(tuple(rows),digest(rows[-1]),blob)

    def close(self):
        self.closes += 1


class WorkerTests(unittest.TestCase):
    inputs_for = CompositeCase.inputs

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='universe-i10-')
        self.addCleanup(temporary.cleanup)
        self.base = Path(temporary.name).resolve()
        self.root, self.key_dir = self.base/'authority',self.base/'key'
        self.template = json.loads((FIXTURES/'positive.json').read_bytes())['records']
        self.raw = {k:bytes.fromhex(v) for k,v in json.loads((FIXTURES/'synthetic_blobs.json').read_bytes())['blobs'].items()}
        anchor = provision(self.key_dir,spec=ProvisionSpec('composite-demo',self.root))
        self.context = DeploymentContext('composite-demo',str(self.root),anchor.trust_anchor,
            digest(self.template[0]),digest(self.template[1]),artifact_class='synthetic-contract-only')
        self.session = OwnerSession('fixture-principal',True,('retain_snapshot','physics_step'))
        self.owner = OwnerConfig(self.context,self.session,'initialize',self.key_dir,self.base/'scratch',(),self.base/'owner.json')
        assets = deepcopy(self.template[22]); assets['id'] = 'asset-manifest-runtime'
        self.inputs = dict(build=self.template[0],options=self.template[1],assets=assets,asset_audit={})
        self.providers = []
        self.runtime = self.new_runtime(self.owner)
        self.store = self.runtime.store
        self.capture('registered')

    def tearDown(self):
        self.capture('final')
        self.runtime.close()

    def capture(self,label):
        destination = os.environ.get('EDGEWORLD_I10_RAW')
        if destination:
            target = Path(destination)/self._testMethodName/label
            target.mkdir(parents=True,exist_ok=False)
            mapping = {}
            for p in sorted(self.root.rglob('*')):
                if p.is_file():
                    raw = p.read_bytes(); relative = str(p.relative_to(self.root))
                    mapping[relative] = dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
                    f = target/'files'/relative; f.parent.mkdir(parents=True,exist_ok=True); f.write_bytes(raw)
            (target/'map.json').write_text(json.dumps(mapping,sort_keys=True))

    def new_runtime(self,owner):
        def factory(**kw):
            provider = InitialSyntheticProvider(self.template,self.raw,kw['static'])
            self.providers.append(provider)
            return provider
        return open_runtime(owner,self.inputs,provider_factory=factory)

    def request(self,op,**payload):
        p = dict(domain='edgeworld.universe.authority',version='0.2',world_id=self.context.world_id)
        p.update(payload)
        return dict(protocol_version=1,request_id='request-'+op,operation=op,payload=p)

    def call(self,op,**payload):
        return dispatch(self.runtime,self.request(op,**payload))['result']['payload']

    def initialize(self):
        return self.call('initialize',test_profile=self.context.archive_profile)

    def prepare(self,label,action='retain_snapshot'):
        proposal,intent = self.inputs_for(label,action)
        return self.call('prepare',principal=self.session.principal,proposal=proposal,intent=intent,
                         approval_id='approval-'+label,command_record_id='command-record-'+label)

    def advance(self,p):
        return self.call('advance',principal=self.session.principal,command_records=p['command_records'],command_digest=p['command_digest'])

    def test_explicit_initialization_static_inventory_and_readonly(self):
        self.assertIsNone(self.runtime.startup_error)
        with self.assertRaises(StoreError):
            self.call('status')
        self.assertEqual(self.providers[0].initializes,0)
        self.assertFalse((self.root/'HEAD.json').exists())
        initial = self.initialize()
        self.assertEqual(initial['commit_status'],'confirmed')
        before = self.call('status')
        self.assertEqual((before['tick'],before['revision']),(0,0))
        info = enumerate_world(self.store.snapshot().closure)
        self.assertEqual((info['json_records'],info['typed_slots']),(31,36))
        self.assertEqual(info['kinds']['existence'],9)
        self.assertEqual(info['kinds']['place'],6)
        proof = self.call('observe',tick=0,revision=0,watermark=0)
        self.assertIsInstance(proof,dict)
        self.assertEqual(before,self.call('status'))
        with self.assertRaises(ContractError): self.initialize()
        self.assertEqual(self.providers[0].initializes,1)
        config = physics_parameters(); config['seed'] = 42
        self.assertEqual(physics_parameters()['seed'],7)

    def test_retain_physics_history_retry_and_restart(self):
        self.initialize()
        one = self.prepare('one')
        self.assertEqual(one,self.prepare('one'))
        a = self.advance(one); self.assertEqual(a,self.advance(one))
        two = self.prepare('two','physics_step'); b = self.advance(two)
        three = self.prepare('three'); self.advance(three)
        self.assertEqual(self.providers[0].calls,1)
        self.assertEqual(self.call('status')['revision'],3)
        self.assertEqual(one['command_records'],self.call('prepare',principal=self.session.principal,
            proposal=one['command_records'][0],intent=one['command_records'][1],approval_id='approval-one',command_record_id='command-record-one')['command_records'])
        with self.assertRaises(ContractError) as conflict:
            self.call('prepare',principal=self.session.principal,proposal=one['command_records'][0],
                intent=one['command_records'][1],approval_id='other-approval',command_record_id='other-command')
        self.assertEqual(conflict.exception.code,'COMMAND_CONFLICT')
        for tick,revision in ((0,0),(0,1),(1,2),(1,3)):
            self.call('observe',tick=tick,revision=revision,watermark=revision)
        self.assertEqual(b['manifest'],self.advance(two)['manifest'])
        status = self.call('status'); self.runtime.close()
        self.runtime = self.new_runtime(replace(self.owner,mode='existing',scratch=self.base/'scratch-2'))
        self.store = self.runtime.store
        self.assertIsNone(self.runtime.startup_error)
        self.assertEqual(status,self.call('status'))
        self.assertEqual(b['manifest'],self.advance(two)['manifest'])
        self.assertEqual(self.providers[-1].initializes+self.providers[-1].calls,0)

    def test_stale_new_intent_rejected_but_retry_survives_h64(self):
        self.initialize()
        stale = self.prepare('stale')
        first = self.prepare('first')
        original = self.advance(first)
        with self.assertRaises(ContractError): self.advance(stale)
        for index in range(2,64):
            self.advance(self.prepare('retain-'+str(index)))
        self.assertEqual(self.call('status')['revision'],63)
        with self.assertRaises(ContractError): self.prepare('overflow')
        self.assertEqual(self.advance(first)['manifest'],original['manifest'])
        self.assertEqual(self.providers[0].calls,0)

    def test_actual_lost_response_recovery_does_not_reexecute_physics(self):
        self.initialize()
        command = self.prepare('lost','physics_step')
        def fail(phase,context):
            if phase == 'W6_AFTER_REPLACE':
                raise OSError('synthetic lost response')
        self.store._fault = fail
        request = self.request('advance',principal=self.session.principal,
            command_records=command['command_records'],command_digest=command['command_digest'])
        raw = json.dumps(request).encode()+b'\n'
        out = io.BytesIO()
        self.assertEqual(serve(self.runtime,io.BytesIO(raw+raw),out,io.StringIO()),3)
        self.assertEqual(json.loads(out.getvalue())['error']['commit_status'],'unknown')
        self.assertEqual(self.providers[0].calls,1)
        self.runtime.close()
        self.runtime = self.new_runtime(replace(self.owner,mode='existing'))
        self.store = self.runtime.store
        self.assertIsNone(self.runtime.startup_error)
        recovered = self.advance(command)
        self.assertEqual(recovered['commit_status'],'confirmed')
        self.assertEqual(self.call('status')['tick'],1)
        self.assertEqual(self.providers[-1].calls,0)

    def test_existing_head_initialize_mode_rejected_before_provider(self):
        self.initialize()
        def mapping():
            return {str(p.relative_to(self.root)):hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in self.root.rglob('*') if p.is_file()}
        before = mapping()
        self.runtime.close()
        self.runtime = self.new_runtime(self.owner)
        self.store = self.runtime.store
        self.assertEqual(self.runtime.startup_error.code,'NOT_READY')
        self.assertEqual(len(self.providers),1)
        with self.assertRaises(ContractError) as caught: self.initialize()
        self.assertEqual(caught.exception.code,'NOT_READY')
        self.assertEqual(mapping(),before)

    def test_existing_owner_scratch_reused_without_creation_or_cleanup(self):
        self.initialize()
        self.owner.scratch.mkdir(mode=0o700)
        marker = self.owner.scratch/'retained-private-provider-artifact'
        marker.write_bytes(b'retain unchanged')
        self.runtime.close()
        self.runtime = self.new_runtime(replace(self.owner,mode='existing'))
        self.store = self.runtime.store
        self.assertIsNone(self.runtime.startup_error)
        self.assertEqual(self.call('status')['tick'],0)
        self.assertEqual(marker.read_bytes(),b'retain unchanged')
        os.chmod(self.owner.scratch,0o755)
        with self.assertRaises(ContractError): validate_scratch(self.owner.scratch)
        os.chmod(self.owner.scratch,0o700)

    def test_frozen_error_codes_for_protocol_build_and_reinitialize(self):
        self.initialize()
        with self.assertRaises(ContractError) as repeated: self.initialize()
        self.assertEqual(repeated.exception.code,'NOT_READY')
        for change in ({'protocol_version':2},{'operation':'unknown'}):
            request = self.request('status'); request.update(change)
            with self.assertRaises(ContractError) as invalid: dispatch(self.runtime,request)
            self.assertEqual(invalid.exception.code,'SCHEMA')
        invalid = dict(self.inputs,build=deepcopy(self.inputs['build']))
        invalid['build']['id'] = 'different-build'
        with self.assertRaises(ContractError) as build:
            open_runtime(self.owner,invalid,provider_factory=lambda **kw:None)
        self.assertEqual(build.exception.code,'BUILD')

    def test_control_fd_isolated_from_python_and_native_stdout(self):
        code = """
import os,sys
from unittest import mock
from engine.universe_authority import worker
owner=object()
def noisy(*args,**kwargs):
    print('python-noise',flush=True)
    os.write(1,b'native-noise\\n')
    return object()
def clean(runtime,reader,writer,diagnostics):
    writer.write(b'{"protocol":true}\\n');return 0
with mock.patch.object(worker,'load_owner_config',return_value=owner), mock.patch.object(worker,'load_inputs',return_value={}), mock.patch.object(worker,'open_runtime',side_effect=noisy), mock.patch.object(worker,'serve',side_effect=clean):
    try: worker.main(['--owner-config','/unused'])
    except AttributeError: pass
"""
        child = subprocess.run([sys.executable,'-c',code],capture_output=True,timeout=10)
        self.assertEqual(child.returncode,0,child.stderr)
        self.assertEqual(child.stdout,b'{"protocol":true}\n')
        self.assertIn(b'python-noise',child.stderr)
        self.assertIn(b'native-noise',child.stderr)

    def test_channel_errors_unknown_stops_and_no_fallback_id(self):
        self.initialize()
        request = self.request('status')
        out,err = io.BytesIO(),io.StringIO()
        self.assertEqual(serve(self.runtime,io.BytesIO(b'{"request_id":"bad"\n'),out,err),2)
        self.assertEqual(out.getvalue(),b'')
        with mock.patch('engine.universe_authority.worker.dispatch',side_effect=StoreError('IO_AFTER_REPLACE','private path',commit_status='unknown')):
            raw = json.dumps(request).encode()+b'\n'
            self.assertEqual(serve(self.runtime,io.BytesIO(raw+raw),out,err),3)
        replies = out.getvalue().splitlines()
        self.assertEqual(len(replies),1)
        failure = json.loads(replies[0])['error']
        self.assertEqual(failure,dict(code='IO_AFTER_REPLACE',message='IO_AFTER_REPLACE',commit_status='unknown'))

    def test_strict_wire_rejects_malformed_and_bad_business_shapes(self):
        for raw in (b'{}\r\n',b'{"request_id":"a","request_id":"a"}\n',b'\xff\n',b'{"request_id":"A"}\n',b'{}\x00\n',b'x'*1048578):
            out = io.BytesIO()
            self.assertEqual(serve(self.runtime,io.BytesIO(raw),out,io.StringIO()),2)
            self.assertEqual(out.getvalue(),b'')
        for change in ({'protocol_version':True},{'operation':'Status'},{'payload':{}}):
            request = self.request('status'); request.update(change)
            out = io.BytesIO()
            serve(self.runtime,io.BytesIO(json.dumps(request).encode()+b'\n'),out,io.StringIO())
            self.assertFalse(json.loads(out.getvalue())['ok'])

    def test_corruption_existing_fails_without_fallback_or_solver(self):
        self.initialize(); self.runtime.close()
        (self.root/'HEAD.json').write_bytes(b'broken')
        self.runtime = self.new_runtime(replace(self.owner,mode='existing'))
        self.store = self.runtime.store
        self.assertIsNotNone(self.runtime.startup_error)
        self.assertEqual(len(self.providers),1)
        with self.assertRaises((ContractError,StoreError)): self.call('status')


class OwnerConfigTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='universe-i10-owner-'); self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve(); os.chmod(self.base,0o700)
        self.path = self.base/'owner.json'
        context = DeploymentContext('world',str(self.base/'authority'),'a'*64,'b'*64,'c'*64)
        self.value = dict(config_version='universe-owner-launch.v0.1',mode='existing',context=asdict(context),
            session=dict(principal='owner',can_initialize=False,allowed_actions=['retain_snapshot']),
            key_dir=str(self.base/'key'),scratch=str(self.base/'scratch'),
            inputs={k:dict(path=str(self.base/(k+'.json')),sha256='d'*64) for k in ('build','options','assets','asset_audit')})
        self.write()

    def write(self):
        self.path.write_bytes(canonical(self.value)); os.chmod(self.path,0o600)

    def test_public_print_only_reads_owner_and_never_creates(self):
        before = sorted(str(p) for p in self.base.iterdir())
        result = subprocess.run([sys.executable,'-m','engine.universe_authority.worker','--owner-config',str(self.path),'--print-public-pins'],capture_output=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        owner = load_owner_config(str(self.path)); pins = public_pins(owner)
        self.assertEqual(len(pins),12)
        self.assertEqual(result.stdout,canonical(pins)+b'\n')
        self.assertEqual(before,sorted(str(p) for p in self.base.iterdir()))

    def test_owner_alias_permissions_link_and_synthetic_fail_closed(self):
        os.chmod(self.path,0o644)
        with self.assertRaises(ContractError): load_owner_config(str(self.path))
        os.chmod(self.path,0o600)
        alias = self.base/'alias'; alias.symlink_to(self.path)
        with self.assertRaises(ContractError): load_owner_config(str(alias))
        link = self.base/'link'; os.link(self.path,link)
        with self.assertRaises(ContractError): load_owner_config(str(self.path))
        link.unlink()
        self.value['context']['artifact_class'] = 'synthetic-contract-only'; self.write()
        with self.assertRaises(ContractError): load_owner_config(str(self.path))

    def test_approved_runtime_asset_audit_consistency_and_counterexamples(self):
        directory = Path(__file__).resolve().parents[1]/'doc/evidence/universe-I10/approved-asset-inputs'
        audit = json.loads((directory/'collection-first.json').read_bytes())
        assets = json.loads((directory/'candidate-record.json').read_bytes())
        validate_asset_audit(assets,audit)
        rebound = dict(assets,world_id='different-authority-world')
        validate_asset_audit(rebound,audit)
        cases = []
        for field,value in (('resolved',False),('gaps',['missing']),('A_actual',8),('asset_bytes_actual',0)):
            bad = deepcopy(audit); bad[field] = value; cases.append(bad)
        bad = deepcopy(audit); bad['files'][0]['sha256'] = '0'*64; cases.append(bad)
        bad = deepcopy(audit); bad['registry_edges_all_categories'].pop(); cases.append(bad)
        bad = deepcopy(audit); bad['content_nodes'][0]['primary_bytes'] += 1; cases.append(bad)
        bad = deepcopy(audit); bad['candidate_manifest']['id'] = 'different-manifest'; cases.append(bad)
        for bad in cases:
            with self.subTest(field=bad.keys()):
                with self.assertRaises(ContractError): validate_asset_audit(assets,bad)
        wrong = deepcopy(assets); wrong['body']['entries'][0]['byte_count'] += 1
        with self.assertRaises(ContractError): validate_asset_audit(wrong,audit)

    def test_owner_exact_paths_and_missing_inputs(self):
        owner = load_owner_config(str(self.path))
        with self.assertRaises(FileNotFoundError): load_inputs(owner)
        self.value['scratch'] = str(self.base); self.write()
        with self.assertRaises(ContractError): load_owner_config(str(self.path))


if __name__ == '__main__': unittest.main()
