"""I15 P synthetic CPU checks only. These do not establish real input/PNG/exit."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.universe_iteration import actions as a, probe_actions as p
from tests.test_universe_iteration_actions import Fixture
from tests.test_universe_iteration_actions_v2 import V2Fixture


class ProbeFixture(V2Fixture):
    def __init__(self,root):
        self.root,self.serial,self.counter=root,0,0
        self.binding=dict(run_id='synthetic-i15',session='existing',world_id='test-world',authority_root=str(root/'authority'),
                          source_sha='a'*40,host_pid=120,worker_pid=121,generation=1)
        self.context=dict(principal='test-owner',trust_anchor='b'*64,expected_build='c'*64,expected_options='d'*64)
        self.clock=dict(id='synthetic-i15-clock',anchor_monotonic=0,anchor_utc='2026-11-02T00:00:00+00:00')
        self.items=p.probe_manifest()['items'];self.frames=self.make_frames();self.trace_refs=self.write_trace(self.frames)
        self.v2=True
        with patch.object(a,'READBACK_V2',p.READBACK_FORMAT):self.build_receipts()
        for receipt,item in zip(self.receipts,self.items):
            receipt['format']=p.FORMAT
            cua=json.loads(a.reference(receipt['cua']));cua['format']='universe-i15-probe-cua.v1'
            for call,command in zip(cua['calls'],item['commands']):call['step_id']=command['step_id']
            receipt['cua']=self.ref(cua)
            receipt['image_checks']=[dict(capture_id=item['action_id']+'/'+stage,stage=stage,capture_ref=self.ref({'synthetic':True})) for stage in item['image_stages']]
    def states(self,kind):
        if kind=='probe':return [dict(quit_guard_ready=True,preflush=True,viewport_width=1600,viewport_height=900,renderer='Metal',hdr=False)]
        return Fixture.states(self,kind)
    def check(self,receipt):
        return p.validate_probe_receipt(receipt,expected_binding=self.binding,frames=self.frames,expected_context=self.context)
    def full(self,receipts=None,trace_refs=None):
        return p.validate_probe_evidence(receipts or self.receipts,trace_refs or self.trace_refs,expected_binding=self.binding,
            expected_context=self.context,expected_before_map_ref=self.receipts[0]['before'],expected_after_map_ref=self.receipts[-1]['after'])


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.f=ProbeFixture(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_exact_independent_probe_manifest(self):
        m=p.probe_manifest();self.assertEqual(m['call_count'],48);self.assertEqual(m['image_count'],8)
        self.assertEqual(m['expected_operations'],['status','observe','observe','observe'])
        self.assertEqual(m['interaction_seconds'],210);self.assertLessEqual(m['interaction_seconds'],300)
        self.assertFalse(m['standard_pair']);self.assertFalse(m['g_b2_granted'])
        self.assertEqual(sum(len(i['image_stages']) for i in m['items']),8)
        self.assertEqual(sum(len(i['commands']) for i in m['items']),48)
        for item in m['items']:
            self.assertEqual(item['session'],'existing');self.assertAlmostEqual(sum(c['max_seconds'] for c in item['commands'])+sum(item['passive_costs'].values()),item['max_seconds'])
        self.assertEqual(a.manifest_v2()['request_counts'],{'initialize':20,'existing':5})
    def test_full_synthetic_probe_consistency_never_grants_runtime(self):
        result=self.f.full();self.assertEqual(result['request_count'],4);self.assertFalse(result['runtime_authenticity_verified'])
        self.assertFalse(result['g_b2_granted'])
    def test_every_query_call_and_real_event_is_required(self):
        for name in ('p1.probe','p1.camera','p1.visibility','p1.framerate','p1.pause','p1.history_write_rejected','p1.held_input','p1.final'):
            base=next(r for r in self.f.receipts if r['action_id']==name);self.f.check(base)
            r=deepcopy(base);r['cua']=self.f.edit_reference(r['cua'],lambda c:c['calls'].pop())
            with self.assertRaises(p.Invalid):self.f.check(r)
        held=next(r for r in self.f.receipts if r['action_id']=='p1.held_input')
        self.assertEqual([e['command_index'] for e in held['checkpoints']],[1,1,1])
        self.assertEqual(len(held['image_checks']),1)
    def test_wrong_step_duplicate_serial_or_stale_map_rejected(self):
        base=next(r for r in self.f.receipts if r['action_id']=='p1.camera')
        r=deepcopy(base);r['cua']=self.f.edit_reference(r['cua'],lambda c:c['calls'][0].update(step_id='p1.camera/99'))
        with self.assertRaises(p.Invalid):self.f.check(r)
        for change in (lambda r:r['checkpoints'][1].update(event_serial=r['checkpoints'][0]['event_serial']),
                       lambda r:r['checkpoints'][1].update(map=r['before'])):
            r=deepcopy(base);change(r)
            with self.assertRaises(p.Invalid):self.f.check(r)
    def test_extra_write_operation_and_missing_action_rejected(self):
        receipts=deepcopy(self.f.receipts);receipts.pop(2)
        with self.assertRaises(p.Invalid):self.f.full(receipts)
        frames=deepcopy(self.f.frames);frames[-1]['request']['operation']='prepare';self.f.counter+=1
        with self.assertRaises(p.Invalid):self.f.full(trace_refs=self.f.write_trace(frames))
    def test_actual_viewport_metal_sdr_dimensions_required(self):
        item=p._probe_item('p1.probe');state=self.f.states('probe')[0]
        diagnostic=dict(state=state,selected_observation=a.H2)
        p._states(item,[diagnostic])
        for key,bad in (('renderer','Null'),('hdr',True),('viewport_width',0),('viewport_height',True)):
            values=deepcopy(diagnostic);values['state'][key]=bad
            with self.assertRaises(p.Invalid):p._states(item,[values])
    def test_fps_branch_and_restore(self):
        item=p._probe_item('p1.framerate')
        for values in ([60,30,60],[30,60,30],[0,30,0]):
            p._states(item,[dict(state={'max_fps':v},selected_observation=a.H2) for v in values])
        with self.assertRaises(p.Invalid):p._states(item,[dict(state={'max_fps':v},selected_observation=a.H2) for v in [30,30,30]])
    def test_schema_is_independent_and_step_id_mandatory(self):
        schema=p.probe_schema();self.assertEqual(schema['properties']['format'],{'const':p.FORMAT})
        self.assertIn('step_id',schema['$defs']['cua']['properties']['calls']['items']['required'])
        self.assertEqual(schema['$defs']['readback']['properties']['format'],{'const':p.READBACK_FORMAT})
    def test_cpp_probe_requires_existing_empty_grants_and_actual_metadata(self):
        base=Path(__file__).resolve().parents[1]/'engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost'
        diag=(base/'EdgeWorldUniverseDiagnostics.cpp').read_text();game=(base/'EdgeWorldUniverseGameMode.cpp').read_text()
        self.assertIn('!Initialize&&EmptyActions',diag);self.assertIn('Pins.AllowedActions.IsEmpty()',game)
        for getter in ('GetSizeXY()','GDynamicRHI->GetName()','GetSceneHDREnabled()'):self.assertIn(getter,game)
        self.assertNotIn('SendControl(',diag)


class PreparePureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path=Path(__file__).resolve().parents[1]/'doc/evidence/universe-I15P/prepare_probe.py'
        spec=importlib.util.spec_from_file_location('i15p_prepare_test',path);cls.helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(cls.helper)
    def test_exact_36_fields_and_limited_pure_derivation(self):
        h=self.helper;self.assertEqual(len(h.FIELDS),36)
        owner=dict(config_version='universe-owner-launch.v0.1',mode='existing',context={'unchanged':'context'},
                   session=dict(principal='owner-i12b',can_initialize=False,allowed_actions=['retain_snapshot','physics_step']),
                   key_dir='/never-read/key-dir',scratch='/old/scratch',inputs={'old':'inputs'})
        original=deepcopy(owner);out=h.derive_owner(owner,scratch=Path('/new/scratch'),inputs={'new':'inputs'})
        self.assertEqual(owner,original);self.assertEqual(out['context'],owner['context']);self.assertEqual(out['key_dir'],owner['key_dir'])
        self.assertEqual(out['session'],dict(principal='owner-i12b',can_initialize=False,allowed_actions=[]))
        for field,value in (('mode','initialize'),('config_version','unknown')):
            bad=deepcopy(owner);bad[field]=value
            with self.assertRaises(Exception):h.derive_owner(bad,scratch=Path('/new'),inputs={})
    def test_default_preparation_is_audit_only(self):
        h=self.helper
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();product=root/'product';tool=root/'tool';product.mkdir();tool.mkdir()
            with patch.object(h,'audit',return_value={'audit_only':True}) as audit,patch.object(h,'write',side_effect=AssertionError('unexpected write')):
                self.assertEqual(h.prepare_probe(product_root=product,tool_root=tool),{'audit_only':True});audit.assert_called_once_with(product)
    def test_corrected_preparation_preserves_original_and_protected_inputs(self):
        h=self.helper
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();prepdir=root/'prep';prepdir.mkdir()
            original=dict(output_root=str(root),product_source_sha='a'*40,helper_ref={'path':'/historical/helper','sha256':'b'*64},
                          context={'world':'preserved'},inputs={'public':'preserved'},allowed_untracked={'links':'preserved'})
            original_ref=h.write(prepdir/'preparation.json',original)
            failure_ref=h.write(prepdir/'build-raw.json',dict(source_sha='a'*40,actual_parent_wait_exit=6,build_only=True,ue_runtime_started=False))
            changed=dict(original,product_source_sha='c'*40,helper_ref=h.ref(h.__file__),previous_preparation_ref=original_ref,build_failure_ref=failure_ref)
            path=prepdir/('preparation-corrected-'+('c'*40)+'.json');changed_ref=h.write(path,changed)
            with patch.object(h,'STORAGE',root):
                self.assertEqual(h.load_preparation(changed_ref)[0],changed)
                self.assertEqual(h.load_preparation(original_ref)[0],original)
                # The exact filename remains fixed; mutate only this synthetic test copy.
                for field,value in (('context',{'world':'tampered'}),('product_source_sha','d'*40),
                                    ('helper_ref',original['helper_ref']),('previous_preparation_ref',failure_ref)):
                    bad=deepcopy(changed);bad[field]=value;path.write_bytes(h.pack(bad))
                    with self.assertRaises(Exception):h.load_preparation(h.ref(path))
                path.write_bytes(h.pack(changed))
                failure=h.load(failure_ref['path']);failure['actual_parent_wait_exit']=0
                Path(failure_ref['path']).write_bytes(h.pack(failure));changed['build_failure_ref']=h.ref(failure_ref['path'])
                path.write_bytes(h.pack(changed))
                with self.assertRaises(Exception):h.load_preparation(h.ref(path))
            self.assertEqual(h.ref(original_ref['path']),original_ref)
            self.assertEqual(h.load(original_ref['path']),original)

    def test_mac_real_lib_prefixed_outputs_required_without_alias(self):
        h=self.helper
        with tempfile.TemporaryDirectory() as td:
            root=Path(td).resolve();project=root/'project/EdgeWorldHost.uproject'
            host=project.parent/'Binaries/Mac/libUnrealEditor-EdgeWorldHost.dylib'
            plugin=project.parent/'Plugins/EdgeWorldRuntime/Binaries/Mac/libUnrealEditor-EdgeWorldRuntime.dylib'
            host.parent.mkdir(parents=True);plugin.parent.mkdir(parents=True)
            host.write_bytes(b'synthetic-host');plugin.write_bytes(b'synthetic-plugin')
            self.assertEqual(h.built_binary_paths(project,root),(host,plugin))
            self.assertFalse(host.with_name('UnrealEditor-EdgeWorldHost.dylib').exists())
            host.rename(host.with_name('UnrealEditor-EdgeWorldHost.dylib'))
            with self.assertRaises(FileNotFoundError):h.built_binary_paths(project,root)
            host.with_name('UnrealEditor-EdgeWorldHost.dylib').rename(host)
            plugin.rename(plugin.with_name('UnrealEditor-EdgeWorldRuntime.dylib'))
            with self.assertRaises(FileNotFoundError):h.built_binary_paths(project,root)

    def test_exclusive_output_and_no_key_content_io(self):
        h=self.helper
        with tempfile.TemporaryDirectory() as td:
            path=Path(td).resolve()/'file';h.write(path,{'first':1})
            with self.assertRaises(FileExistsError):h.write(path,{'second':2})
            self.assertEqual(h.load(path),{'first':1})
            keys=Path(td).resolve()/'keys';keys.mkdir(mode=0o700);(keys/'do-not-read').write_bytes(b'synthetic')
            with patch.object(Path,'open',side_effect=AssertionError('key content read')),patch.object(Path,'rglob',side_effect=AssertionError('key enumeration')):
                self.assertEqual(h.key_metadata(keys)['path'],str(keys))


if __name__=='__main__':unittest.main()
