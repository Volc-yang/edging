"""CPU-only independent composition negatives; fake v2 adapters do NOT accept L/D."""
import copy
import hashlib
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest import mock
import zlib

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from universe_iteration import verification as v
from universe_iteration import capture as c


def chunk(kind,data):
    return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)


def png():
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(5)))+chunk(b'IEND',b'')


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve()
        self.authority=self.root/'world';self.authority.mkdir()
        self.now=102.;self.counter=0
        self.patches=[mock.patch.object(c.time,'monotonic',side_effect=lambda:self.now),
                      mock.patch.object(c.time,'sleep',side_effect=lambda t:setattr(self,'now',self.now+t)),
                      mock.patch.object(v.lifecycle,'validate_ledger_v2',return_value={'status':'checks_complete_requires_review'},create=True),
                      mock.patch.object(v.actions,'validate_session_v2',return_value={'status':'consistent_requires_R_and_independent_review'},create=True),
                      mock.patch.object(v.actions,'manifest_v2',return_value={'format':'universe-i14-actions.v1','items':[]},create=True),
                      mock.patch.object(v.actions,'readiness_v2',return_value={'status':'ready_for_R_review'},create=True)]
        for p in self.patches:p.start()
        self.clock={'id':'synthetic','anchor_monotonic':100.,'anchor_utc':'2000-01-01T00:00:00+00:00'}
        self.triple={'tick':0,'revision':0,'watermark':0}
        self.run=dict(run_id='i14-test',source_sha='a'*40,world_id='test-world',authority_root=str(self.authority))
        self.schema={'body':{'manifest':{'tick':'uint','revision':'uint','watermark':'uint'},
                             'state':{'tick':'uint','revision':'uint','budget':'uint','random_cursor':'uint','development_mm':'nullable_mm'}},
                     'kind_bytes':{'manifest':2048,'state':2048},'refs':{'manifest':{'state':'state'},'state':{}},
                     'proof_kind_max':{'manifest':65,'state':2}}
        state=self.record('state','state-0',dict(tick=0,revision=0,budget=2,random_cursor=0,development_mm=None),{})
        manifest=self.record('manifest','manifest-0',self.triple,{'state':v.digest(state)})
        self.records={v.digest(state):state,v.digest(manifest):manifest};self.head=v.digest(manifest)
        self.bindings={};self.expected={};self.sessions={};self.frames={};self.receipt_values={}
        self.card=self.write('card.json',{'public':'synthetic card; no runtime authorization'})
        self.manifest_ref=self.write('manifest.json',v.actions.manifest_v2())
        for i,name in enumerate(v.SESSIONS):self.make_session(name,i)
        self.ledger=self.write('ledger.json',{'clock':self.clock,'sessions':[], 'synthetic':'v2 adapter fixture only'})
        self.lp={'format':'universe-i14-lifecycle-policy.v1','run_binding':self.run,'clock_id':'synthetic',
                 'accepted_executable':'/approved/UE','worker_executable':'/approved/Python','launcher_identities':[],
                 'launcher_source_ref':self.write('launcher-source.py',{'synthetic':'pinned source'}),
                 'session_bindings':self.bindings,'storage_root':str(self.root),'public_paths':[],
                 'global_limit_seconds':1200,'storage_limit_bytes':2147483648,'observer_max_gap_seconds':2,
                 'sessions':{'initialize':{'max_seconds':540},'existing':{'max_seconds':280}}}
        self.policy={'format':v.POLICY,'lifecycle':self.lp,'actual_finalized_monotonic':110.,
                     'public_context':{'principal':'owner','trust_anchor':'b'*64,'expected_build':'c'*64,'expected_options':'d'*64},
                     'schema':self.schema,'manifest_ref':self.manifest_ref,'resource_card_ref':self.card,
                     'capabilities':{},'session_expectations':self.expected}
        self.bundle={'format':v.FORMAT,'artifacts':[],'resource_card_ref':self.card,'manifest_ref':self.manifest_ref,
                     'ledger_ref':self.ledger,'sessions':self.sessions}
        self.trace_patch=mock.patch.object(v.actions,'load_trace',side_effect=lambda refs,expected_binding:[{'request':x['request'],'response':x['response']} for x in self.frames[expected_binding['session']]])
        self.trace_patch.start();self.patches.append(self.trace_patch)
        self.now=120.

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.tmp.cleanup()

    def write(self,name,value):
        path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
        data=json.dumps(value,sort_keys=True).encode()
        with path.open('xb') as f:f.write(data)
        return {'path':str(path),'sha256':hashlib.sha256(data).hexdigest()}

    def record(self,kind,identifier,body,refs):
        return dict(domain='edgeworld.universe.authority',version='0.2',world_id='test-world',kind=kind,id=identifier,body=body,refs=refs)

    def make_session(self,name,i):
        directory=self.root/name;directory.mkdir();archive=directory/'archive';archive.mkdir();trace=directory/'trace';trace.mkdir()
        binding=dict(self.run,session=name,host_pid=10+i,worker_pid=20+i,generation=1);self.bindings[name]=binding
        state=self.records[next(k for k,x in self.records.items() if x['kind']=='state')];manifest=self.records[self.head]
        request=dict(protocol_version=1,request_id='u-'+name,operation='observe',payload=dict(domain='edgeworld.universe.authority',version='0.2',world_id='test-world',**self.triple))
        response=dict(protocol_version=1,request_id=request['request_id'],ok=True,result=dict(domain='edgeworld.universe.authority',version='0.2',world_id='test-world',operation='observe',payload=dict(
            manifest=manifest,state=state,event=None,watermark=0,storage_state='ready',artifact_class='genesis-runtime',head=self.head,membership=[manifest],records=[],opaque_refs=[])))
        frame=dict(request=request,response=response,host_pid=binding['host_pid'],worker_pid=binding['worker_pid'],generation=1)
        self.frames[name]=[frame]
        self.now=102.+i*10
        log=directory/'ue.log';log.write_bytes(b'actual synthetic log\n')
        verification=self.write(name+'/response.json',response)
        obs=self.write(name+'/observation.json',dict(binding=binding,trusted_head=self.triple,selected_observation=self.triple,
            clock_id='synthetic',verified_monotonic=101.+i*10,verification_ref=verification))
        before=self.write(name+'/before.json',dict(root=str(self.authority),files={}))
        after=self.write(name+'/after.json',dict(root=str(self.authority),files={}))
        target=directory/'original.png'
        prep=c.prepare_native_shot(target_path=target,expected_binding=binding,trusted_head=self.triple,selected_observation=self.triple,
            observation_ref=obs,before_map_ref=before,before_map_monotonic=101.+i*10,log_path=log,log_offset=log.stat().st_size,
            clock=self.clock,expected_width=1,expected_height=1)
        p=json.loads(Path(prep['preparation_ref']['path']).read_bytes());self.now=103.+i*10
        cua=self.write(name+'/cua-raw.json',{'synthetic':'raw call'})
        command=self.write(name+'/command.json',dict(format=c.FORMAT,phase='cua-command',preparation_ref=prep['preparation_ref'],
            command=prep['command'],clock_id='synthetic',binding=binding,trusted_head=self.triple,selected_observation=self.triple,
            observation_ref=obs,cua_result_ref=cua,start_monotonic=102.5+i*10,end_monotonic=102.8+i*10,
            log=dict(p['log'],after_offset=p['log']['before_offset'])))
        target.write_bytes(png())
        capture=c.collect_native_shot(prep['preparation_ref'],command,expected_binding=binding,expected_trusted_head=self.triple,
            expected_selected_observation=self.triple,expected_observation_ref=obs,expected_clock=self.clock,receipt_path=directory/'capture.json')
        exitraw=self.write(name+'/exit-raw.json',{'synthetic':'actual quit boundary'})
        exitref=self.write(name+'/before-exit.json',dict(format=c.FORMAT,phase='actual-before-exit',binding=binding,clock_id='synthetic',
            before_exit_monotonic=104.+i*10,exit_evidence_ref=exitraw))
        action='s1.probe' if i==0 else 's2.probe';key=action+'/png_and_guard'
        receipt=dict(action_id=action,binding=binding,clock=self.clock,trusted_head=self.triple,selected_observation=self.triple,
            trace_range=[0,1],started_monotonic=102.+i*10,completed_monotonic=103.8+i*10,
            checkpoints=[{'stage':'png_and_guard','map':after}],image_checks=[{'capture_id':key,'stage':'png_and_guard','capture_ref':capture}])
        exitreceipt=dict(action_id='s1.exit' if i==0 else 's2.exit',binding=binding,clock=self.clock,trusted_head=self.triple,
            selected_observation=self.triple,trace_range=[1,1],started_monotonic=103.9+i*10,completed_monotonic=104.5+i*10,checkpoints=[],image_checks=[])
        self.receipt_values[name]=[receipt,exitreceipt]
        receiptrefs=[self.write(name+'/action.json',receipt),self.write(name+'/exit-action.json',exitreceipt)]
        expected_capture=dict(capture_id=key,action_id=action,stage='png_and_guard',trace_frame_index=0,observation_ref=obs,
            trusted_head=self.triple,selected_observation=self.triple,clock=self.clock,after_map_ref=after,
            after_map_monotonic=103.5+i*10,before_exit_monotonic=104.+i*10,before_exit_ref=exitref)
        self.expected[name]=dict(authority_copy=str(archive),trace_directory=str(trace),trace_refs=[],captures=[expected_capture])
        self.sessions[name]=dict(binding=binding,authority_copy=str(archive),trace_directory=str(trace),trace_refs=[],action_receipt_refs=receiptrefs,
            captures=[dict(capture_id=key,capture_ref=capture)])

    def index(self):
        bundle_path=self.root/'bundle.json'
        if bundle_path.exists():bundle_path.unlink()  # Synthetic reassembly only, never real raw.
        files=[p for p in self.root.rglob('*') if p.is_file() and not p.is_symlink()]
        self.bundle['artifacts']=[dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in files]
        self.lp['public_paths']=[str(p) for p in files]+[str(bundle_path)]
        return self.write('bundle.json',self.bundle)

    def authority_parser(self,path,schema):
        return dict(world_id='test-world',head=self.head,records_by_hash=self.records)

    def trace_parser(self,path):
        name=Path(path).parent.name;binding=self.bindings[name]
        event=dict(worker_pid=binding['worker_pid'],generation=1,return_code_available=True,exit_code=0,reaped=True,trace_complete=True,
            hard_kill_sent=False,operational_failure=False,stop_kind='normal')
        return dict(frames=self.frames[name],worker_exits=[event],transport_count=1)

    def verify(self,**updates):
        args=dict(expected_policy=self.policy,authority_parser=self.authority_parser,trace_parser=self.trace_parser);args.update(updates)
        return v.verify_evidence(self.index(),**args)

    def assert_fail(self,result):self.assertEqual(result['status'],'fail',result)

    def proof(self):
        return v.verify_public_proof(self.frames['initialize'][0],records=self.records,schema=self.schema,binding=self.bindings['initialize'],public_context=self.policy['public_context'])

    def test_complete_structural_fixture_remains_explicit_semantic_inconclusive(self):
        result=self.verify();self.assertEqual(result['status'],'inconclusive',result)
        self.assertEqual(set(result['reasons']),set(v.PUBLIC_PROOF_GAPS));self.assertEqual(len(result['proof_checks']),2)
        self.assertIs(result['g_b2_granted'],False);self.assertIs(result['runtime_authorized'],False)
        self.assertIn('typed body',result['reasons'][0]+' '.join(result['reasons']))

    def test_v2_not_integrated_is_inconclusive_not_fake_pass(self):
        with mock.patch.object(v.lifecycle,'validate_ledger_v2',None):
            self.assertEqual(self.verify()['status'],'inconclusive')

    def test_missing_component_is_inconclusive(self):
        self.bundle.pop('ledger_ref');self.assertEqual(self.verify()['status'],'inconclusive')

    def test_ledger_fail_inconclusive_and_wrong_boolean_result(self):
        for status,expected in [('fail','fail'),('inconclusive','inconclusive')]:
            with mock.patch.object(v.lifecycle,'validate_ledger_v2',return_value={'status':status,'reasons':['fake adapter negative']}):
                self.assertEqual(self.verify()['status'],expected)
        with mock.patch.object(v.lifecycle,'validate_ledger_v2',return_value=True):self.assert_fail(self.verify())

    def test_parsers_cannot_return_passed_boolean(self):
        for name in ('authority_parser','trace_parser'):
            self.assert_fail(self.verify(**{name:lambda *a:True}))
            self.assert_fail(self.verify(**{name:lambda *a:{'passed':True}}))

    def test_wrong_external_source_binding_and_card(self):
        self.lp['run_binding']=dict(self.run,source_sha='f'*40);self.assert_fail(self.verify())
        self.lp['run_binding']=self.run
        self.policy['resource_card_ref']=self.manifest_ref;self.assert_fail(self.verify())

    def test_archive_callback_hash_and_head_cannot_be_forged(self):
        wrong=copy.deepcopy(self.records);wrong[self.head]['body']['tick']=2
        self.assert_fail(self.verify(authority_parser=lambda *a:dict(world_id='test-world',head=self.head,records_by_hash=wrong)))
        self.assert_fail(self.verify(authority_parser=lambda *a:dict(world_id='wrong-world',head=self.head,records_by_hash=self.records)))

    def test_independent_trace_disagreement_pid_or_normalfalse_fails(self):
        baseline=self.trace_parser(self.expected['initialize']['trace_directory'])
        wrong=copy.deepcopy(baseline);wrong['worker_exits'][0]['hard_kill_sent']=True
        self.assert_fail(self.verify(trace_parser=lambda *a:wrong))
        wrong=copy.deepcopy(baseline);wrong['frames'][0]['host_pid']=999
        self.assert_fail(self.verify(trace_parser=lambda *a:wrong))
        wrong=copy.deepcopy(baseline);wrong['frames'][0]['response']['request_id']='u-forged'
        self.assert_fail(self.verify(trace_parser=lambda *a:wrong))

    def test_existing_extra_write_rejected(self):
        self.frames['existing'][0]['request']['operation']='advance';self.assert_fail(self.verify())

    def test_duplicate_missing_unclaimed_capture_and_stage(self):
        row=self.sessions['initialize']['captures'][0]
        self.sessions['initialize']['captures'].append(copy.deepcopy(row));self.assert_fail(self.verify())
        self.sessions['initialize']['captures']=[];self.assertEqual(self.verify()['status'],'inconclusive')
        self.sessions['initialize']['captures']=[dict(row,capture_id='unclaimed')];self.assert_fail(self.verify())

    def test_capture_wrong_clock_or_exit_outside_action(self):
        self.expected['initialize']['captures'][0]['clock']=dict(self.clock,id='wrong');self.assert_fail(self.verify())
        self.expected['initialize']['captures'][0]['clock']=self.clock
        self.expected['initialize']['captures'][0]['before_exit_monotonic']=119.;self.assert_fail(self.verify())

    def test_actual_png_replacement_and_public_digest_change(self):
        ref=self.sessions['initialize']['captures'][0]['capture_ref'];receipt=json.loads(Path(ref['path']).read_bytes())
        path=Path(receipt['original_ref']['path']);path.rename(path.with_suffix('.preserved'));path.write_bytes(png())
        self.assert_fail(self.verify())

    def test_unindexed_redirected_reference_is_failure(self):
        bundle_ref=self.index();self.policy['manifest_ref']=dict(self.manifest_ref,path='/outside/manifest.json')
        self.assert_fail(v.verify_evidence(bundle_ref,expected_policy=self.policy,authority_parser=self.authority_parser,trace_parser=self.trace_parser))

    def test_symlink_artifact_and_changed_hash_rejected(self):
        ref=self.index();target=Path(self.manifest_ref['path']);data=target.read_bytes();target.unlink();other=self.root/'redirect.json';other.write_bytes(data);target.symlink_to(other)
        self.assert_fail(v.verify_evidence(ref,expected_policy=self.policy,authority_parser=self.authority_parser,trace_parser=self.trace_parser))

    def test_missing_original_is_inconclusive(self):
        ref=self.index();Path(self.manifest_ref['path']).unlink()
        result=v.verify_evidence(ref,expected_policy=self.policy,authority_parser=self.authority_parser,trace_parser=self.trace_parser)
        self.assertEqual(result['status'],'inconclusive',result)

    def test_proof_valid_selected_closure_known_checks(self):
        result=self.proof();self.assertEqual(result['manifest'],self.head);self.assertEqual(result['semantic_gaps'],list(v.PUBLIC_PROOF_GAPS))

    def test_proof_hash_membership_selected_and_opaque_forgery(self):
        original=copy.deepcopy(self.frames['initialize'][0]);payload=self.frames['initialize'][0]['response']['result']['payload']
        for name,value in [('head','0'*64),('membership',[]),('opaque_refs',['0'*64]),('watermark',True),('state',dict(payload['state'],id='forged-state'))]:
            self.frames['initialize'][0]=copy.deepcopy(original)
            self.frames['initialize'][0]['response']['result']['payload'][name]=value
            with self.subTest(field=name),self.assertRaises(v.Invalid):self.proof()

    def test_proof_records_aux_identity_ref_schema_and_float(self):
        frame=self.frames['initialize'][0];payload=frame['response']['result']['payload']
        payload['records']=[payload['state']]
        with self.assertRaises(v.Invalid):self.proof()
        payload['records']=[]
        bad=copy.deepcopy(payload['state']);bad['body']['budget']=1.25
        payload['state']=bad
        with self.assertRaises(v.Invalid):self.proof()

    def test_history_membership_closes_selected_prior_and_exact_opaque_ancestors(self):
        schema=copy.deepcopy(self.schema)
        schema['body'].update(event={'event_id':'id'},index={})
        schema['refs'].update(event={'prior_event?':'event'},index={})
        schema['proof_kind_max'].update(event=3,index=3)
        schema['kind_bytes'].update(event=2048,index=2048)
        records=copy.deepcopy(self.records);m0=records[self.head]
        def add(record):records[v.digest(record)]=record;return record
        s1=add(self.record('state','state-1',dict(tick=0,revision=1,budget=2,random_cursor=0,development_mm=None),{}))
        e1=add(self.record('event','event-1',{'event_id':'e-1'},{}));i1=add(self.record('index','index-1',{},{}))
        m1=add(self.record('manifest','manifest-1',dict(tick=0,revision=1,watermark=1),dict(state=v.digest(s1),event=v.digest(e1),index=v.digest(i1),prior_manifest=v.digest(m0))))
        s2=add(self.record('state','state-2',dict(tick=1,revision=2,budget=1,random_cursor=1,development_mm=1),{}))
        e2=add(self.record('event','event-2',{'event_id':'e-2'},{'prior_event':v.digest(e1)}));i2=add(self.record('index','index-2',{},{}))
        m2=add(self.record('manifest','manifest-2',dict(tick=1,revision=2,watermark=2),dict(state=v.digest(s2),event=v.digest(e2),index=v.digest(i2),prior_manifest=v.digest(m1))))
        frame=copy.deepcopy(self.frames['initialize'][0]);selected=dict(tick=0,revision=1,watermark=1)
        frame['request']['payload'].update(selected)
        p=frame['response']['result']['payload'];p.update(manifest=m1,state=s1,event=e1,watermark=1,head=v.digest(m2),membership=[m2,m1],records=[i1,m0,records[m0['refs']['state']]],opaque_refs=sorted([v.digest(s2),v.digest(e2),v.digest(i2)]))
        result=v.verify_public_proof(frame,records=records,schema=schema,binding=self.bindings['initialize'],public_context=self.policy['public_context'])
        self.assertEqual(result['selected_observation'],selected);self.assertEqual(result['head'],v.digest(m2))
        p['opaque_refs']=p['opaque_refs'][:-1]
        with self.assertRaises(v.Invalid):v.verify_public_proof(frame,records=records,schema=schema,binding=self.bindings['initialize'],public_context=self.policy['public_context'])

    def test_wire_request_response_mismatch(self):
        self.frames['initialize'][0]['response']['request_id']='u-other'
        with self.assertRaises(v.Invalid):self.proof()

    def test_public_scalar_codec_rejects_bool_as_counter_nan_and_unbounded(self):
        # Record booleans are legal scalar values, but exact counters are checked
        # by triple validation and remaining typed semantics stay explicit gaps.
        with self.assertRaises(v.Invalid):v._triple(dict(tick=True,revision=0,watermark=0))
        with self.assertRaises(v.Invalid):v.canonical({'raw':float('nan')})
        with self.assertRaises(v.Invalid):v.canonical({'$f64':'7ff0000000000000'})
        with self.assertRaises(v.Invalid):v.canonical({'array':[0]*257})


if __name__=='__main__':unittest.main()
