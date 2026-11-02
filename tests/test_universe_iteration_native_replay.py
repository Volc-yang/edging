"""CPU synthetic framing/review fixtures; no UE/parity claim or runtime permission."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from universe_iteration import native_replay as n
from universe_iteration import verification as v


class NativeReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.paths = []
        self.counter = 0
        self.identity = dict(host_pid=101, worker_pid=102, generation=1)
        self.pins = self.save('pins.json', dict(artifact_class='genesis-runtime', world_id='test'))
        state = dict(domain='edgeworld.universe.authority', version='0.2', world_id='test', kind='state', id='s0', body={}, refs={})
        manifest = dict(domain='edgeworld.universe.authority', version='0.2', world_id='test', kind='manifest', id='m0', body={}, refs={'state':n._record_hash(state)})
        self.payload = dict(membership=[manifest], records=[], manifest=manifest, state=state, event=None)
        self.frames = [
            (dict(protocol_version=1, request_id='status-1', operation='status', payload={}), dict(protocol_version=1, request_id='status-1', ok=True, result={'payload':{'head_binding':{'head':n._record_hash(manifest)}}})),
            (dict(protocol_version=1, request_id='observe-1', operation='observe', payload={'tick':0,'revision':0,'watermark':0}), dict(protocol_version=1, request_id='observe-1', ok=True, result={'payload':self.payload}))]
        self.trace = []
        serial = 0
        for request, response in self.frames:
            request_raw = self.wire(request)
            response_raw = self.wire(response)
            for direction, raw in [('request',request_raw),('write-result',b''),('stdout-chunk',response_raw[:17]),('stdout-chunk',response_raw[17:]),('response-complete',b'')]:
                serial += 1
                rawref = self.save('trace/fixed-%08d.bin' % serial, raw)
                meta = dict(self.identity, serial=str(serial), direction=direction, monotonic_seconds=float(serial), request_id=request['request_id'], operation=request['operation'], raw_file=Path(rawref['path']).name, byte_count=len(raw), written_bytes=len(request_raw))
                self.trace.extend([rawref,self.save('trace/fixed-%08d.json' % serial,meta)])
        self.source = dict(pins_ref=self.pins,trace_refs=self.trace,observe_frame_indices=[1],trace_identity=self.identity)
        self.selection = dict(case_id='real-0',pins_ref=self.pins,trace_refs=self.trace,trace_frame_index=1)
        self.prepared = n.prepare_replay_cases(run_id='test-run',product_source_sha='a'*40,tool_source_sha='b'*40,selections=[self.selection],allowed_sources=[self.source],public_paths=self.paths,output_dir=str(self.root/'prepared'))
        self.paths += self.prepared['public_paths']
        self.ref = self.prepared['manifest_ref']
        self.manifest = json.loads(Path(self.ref['path']).read_bytes())

    def tearDown(self):
        self.tmp.cleanup()

    def wire(self, value):
        return (json.dumps(value,separators=(',',':'))+'\n').encode()

    def save(self, name, value):
        path = self.root/name
        path.parent.mkdir(parents=True,exist_ok=True)
        raw = value if isinstance(value,bytes) else self.wire(value)
        path.write_bytes(raw)
        self.paths.append(str(path))
        return dict(path=str(path),sha256=hashlib.sha256(raw).hexdigest())

    def validate(self, manifest=None, **updates):
        ref = self.ref if manifest is None else self.save('changed-%d.json' % self.counter,manifest)
        self.counter += 1
        args = dict(expected_run_id='test-run',expected_product_source_sha='a'*40,expected_tool_source_sha='b'*40,allowed_sources=[self.source],public_paths=self.paths)
        args.update(updates)
        return n.validate_native_manifest(ref,**args)

    def test_exact_original_lf_and_chunk_reassembly(self):
        self.assertEqual(self.validate(),self.manifest)
        frame = n.reassemble_trace(self.trace,trace_identity=self.identity,public_paths=self.paths)[1]
        self.assertEqual(frame['response_bytes'],self.wire(self.frames[1][1]))
        case = self.manifest['cases'][0]
        self.assertEqual(Path(case['observe_response_ref']['path']).read_bytes(),frame['response_bytes'])
        with self.assertRaises(n.Invalid):
            n.prepare_replay_cases(run_id='test-run',product_source_sha='a'*40,tool_source_sha='b'*40,selections=[self.selection],allowed_sources=[self.source],public_paths=self.paths,output_dir=str(self.root/'prepared'))

    def test_empty_duplicate_and_relabelled_cases(self):
        for cases in [[],self.manifest['cases']*2,[self.manifest['cases'][0],dict(self.manifest['cases'][0],case_id='relabeled')]]:
            value=copy.deepcopy(self.manifest);value['cases']=cases
            with self.assertRaises(n.Invalid):self.validate(value)

    def test_wrong_source_run_or_selection(self):
        for args in [dict(expected_run_id='other'),dict(expected_product_source_sha='c'*40),dict(expected_tool_source_sha='c'*40),dict(allowed_sources=[])]:
            with self.assertRaises(n.Invalid):self.validate(**args)
        for key,value in [('tick',1),('observe_request_id','other'),('status_request_id','other')]:
            m=copy.deepcopy(self.manifest);m['cases'][0]['expected'][key]=value
            with self.assertRaises(n.Invalid):self.validate(m)

    def test_dumps_copy_or_tamper_is_not_original(self):
        m=copy.deepcopy(self.manifest)
        m['cases'][0]['observe_response_ref']=self.save('reformatted.json',json.dumps(self.frames[1][1],indent=2).encode())
        with self.assertRaises(n.Invalid):self.validate(m)
        m=copy.deepcopy(self.manifest);m['cases'][0]['observe_response_ref']['sha256']='f'*64
        with self.assertRaises(n.Invalid):self.validate(m)

    def test_derived_negative_explicit_and_bound(self):
        m=copy.deepcopy(self.manifest);negative=dict(m['cases'][0],case_id='derived-0',origin='derived-negative',source_case_id='real-0',expected_accept=False)
        negative['observe_response_ref']=self.save('derived.json',dict(protocol_version=1))
        m['cases'].append(negative)
        self.assertEqual(len(self.validate(m)['cases']),2)
        for key,value in [('source_case_id','missing'),('origin','real-trace'),('expected_accept',True)]:
            bad=copy.deepcopy(m);bad['cases'][1][key]=value
            with self.assertRaises(n.Invalid):self.validate(bad)

    def test_path_redirect_and_allowlist_rejected(self):
        alias=self.root/'alias.json';alias.symlink_to(self.ref['path']);self.paths.append(str(alias))
        with self.assertRaises(ValueError):
            n.validate_native_manifest(dict(path=str(alias),sha256=self.ref['sha256']),expected_run_id='test-run',expected_product_source_sha='a'*40,expected_tool_source_sha='b'*40,allowed_sources=[self.source],public_paths=self.paths)
        with self.assertRaises(n.Invalid):self.validate(public_paths=[])

    def test_partial_teardown_preserves_completed_only(self):
        refs=self.trace[:-2]
        frames=n.reassemble_trace(refs,trace_identity=self.identity,public_paths=self.paths)
        self.assertEqual(len(frames),1)
        with self.assertRaises(n.Invalid):n.reassemble_trace(self.trace[2:],trace_identity=self.identity,public_paths=self.paths)
        with self.assertRaises(n.Invalid):n.reassemble_trace(self.trace,trace_identity=dict(self.identity,worker_pid=999),public_paths=self.paths)

    def full_review(self):
        case=self.manifest['cases'][0]
        refs={key:self.save('sources/'+key,b'synthetic-source-'+key.encode()) for key in ('parser_cpp','parser_h','bridge_cpp')}
        bins={key:self.save('binaries/'+key,b'synthetic-binary-'+key.encode()) for key in ('host','plugin','executable')}
        build=self.save('build.json',dict(source_sha='c'*40,source_refs=refs,binary_refs=bins,actual_parent_wait_exit=0,build_only=True,ue_runtime_started=False))
        result=self.save('result.json',dict(format=n.RESULT,bridge_format='strict-public-status-observe.v1',manifest_sha256=self.ref['sha256'],host_pid=201,ue_version='synthetic-ue',case_count=1,cases=[dict(case_id='real-0',origin='real-trace',accepted=True,error='',actual_input_sha256s={name:case[name+'_ref']['sha256'] for name in n.INPUTS},**case['expected'],manifest=n._record_hash(self.payload['manifest']),state=n._record_hash(self.payload['state']),event='',selected_records=n._selected_records(self.payload))]))
        env=dict(EDGEWORLD_UNIVERSE_NATIVE_REPLAY='1',EDGEWORLD_UNIVERSE_REPLAY_MANIFEST=self.ref['path'],EDGEWORLD_UNIVERSE_REPLAY_MANIFEST_SHA256=self.ref['sha256'],EDGEWORLD_UNIVERSE_REPLAY_OUTPUT=result['path'])
        execution=dict(format='universe-i15-native-execution.v1',host_pid=201,process_start='synthetic-start',parent_pid=200,argv=['synthetic-ue'],cwd=str(self.root),environment=env,selectors=list(n.SELECTORS),manifest_ref=self.ref,result_ref=result,parent_wait=dict(observed=True,exit_code=0,host_pid=201,process_start='synthetic-start',parent_pid=200),normal=True,forced_cleanup=False,started_monotonic=1.,ended_monotonic=2.)
        er=self.save('execution.json',execution)
        log=self.save('automation.log',('Found 4 automation tests\n'+''.join('Test Completed. Result={Success} Name={test} Path={'+x+'}\n' for x in n.SELECTORS)).encode())
        resource=self.save('resource.json',dict(run_id='test-run',elapsed_seconds=10.,storage_bytes=1024,all_processes_quiet=True))
        review=dict(format=n.REVIEW,decision='pass',owner='synthetic-owner',reviewer='synthetic-independent',manifest_ref=self.ref,result_ref=result,execution_ref=er,automation_log_ref=log,source_refs=refs,binary_refs=bins,resource_ref=resource,build_ref=build,coverage=[case['observe_response_ref']['sha256']])
        rr=self.save('review.json',review)
        policy=dict(format=n.POLICY,run_id='test-run',product_source_sha='a'*40,tool_source_sha='b'*40,allowed_sources=[self.source],public_paths=self.paths,approved_review_ref=rr,manifest_ref=self.ref,result_ref=result,execution_ref=er,automation_log_ref=log,source_refs=refs,binary_refs=bins,resource_ref=resource,expected_host_pid=201,expected_process_start='synthetic-start',expected_parent_pid=200,expected_ue_version='synthetic-ue',expected_argv=['synthetic-ue'],expected_env=env,expected_cwd=str(self.root),native_source_sha='c'*40,build_ref=build)
        return rr,policy,review,execution

    def test_synthetic_review_accepts_exact_case_only(self):
        rr,p,_,_=self.full_review();result=n.verify_native_replay_review(rr,expected_policy=p)
        self.assertEqual(result['status'],'checks_complete_requires_review',result)
        self.assertEqual([x['observe_response_sha256'] for x in result['coverage']],[self.manifest['cases'][0]['observe_response_ref']['sha256']])
        self.assertFalse(result['g_b2_granted'])

    def test_review_wrong_identity_build_binary_and_approval(self):
        rr,p,review,execution=self.full_review()
        for key,value in [('expected_host_pid',202),('native_source_sha','d'*40),('expected_argv',['other']),('expected_ue_version','other')]:
            bad=copy.deepcopy(p);bad[key]=value
            self.assertEqual(n.verify_native_replay_review(rr,expected_policy=bad)['status'],'fail')
        Path(p['binary_refs']['host']['path']).write_bytes(b'changed')
        self.assertEqual(n.verify_native_replay_review(rr,expected_policy=p)['status'],'fail')

    def test_review_wait_and_missing_evidence(self):
        rr,p,review,execution=self.full_review()
        execution['parent_wait']['exit_code']=9
        p['execution_ref']=self.save('bad-execution.json',execution)
        review['execution_ref']=p['execution_ref']
        rr=self.save('bad-review.json',review);p['approved_review_ref']=rr
        self.assertEqual(n.verify_native_replay_review(rr,expected_policy=p)['status'],'fail')
        Path(p['execution_ref']['path']).unlink()
        # Safe public reader reports unavailable original; never a successful skip.
        self.assertNotEqual(n.verify_native_replay_review(rr,expected_policy=p)['status'],'checks_complete_requires_review')

    def test_review_rejects_selector_case_output_and_resource_tampering(self):
        rr,p,review,execution=self.full_review()
        mutations=[('execution_ref',lambda x:x.update(selectors=list(n.SELECTORS)+['edgeWorld.UniverseHost.LiveReadOnly'])),
                   ('result_ref',lambda x:x.update(case_count=0,cases=[])),
                   ('result_ref',lambda x:x['cases'][0].update(manifest='f'*64)),
                   ('resource_ref',lambda x:x.update(elapsed_seconds=901)),
                   ('build_ref',lambda x:x.update(ue_runtime_started=True))]
        for index,(key,mutate) in enumerate(mutations):
            q=copy.deepcopy(p);r=copy.deepcopy(review)
            value=json.loads(Path(p[key]['path']).read_bytes());mutate(value)
            q[key]=self.save('mutate-%d.json' % index,value);r[key]=q[key]
            ref=self.save('review-%d.json' % index,r);q['approved_review_ref']=ref
            self.assertEqual(n.verify_native_replay_review(ref,expected_policy=q)['status'],'fail',key)

    def test_optin_verifier_discharges_only_exact_matched_response(self):
        raw=n.reassemble_trace(self.trace,trace_identity=self.identity,public_paths=self.paths)[1]
        triple=dict(tick=0,revision=0,watermark=0)
        head=n._record_hash(self.payload['manifest']);state=n._record_hash(self.payload['state'])
        base=dict(status='inconclusive',reasons=list(v.PUBLIC_PROOF_GAPS),proof_checks=[dict(session='existing',frame_index=1,head=head,selected_observation=triple,manifest=head,state=state,event=None)])
        context=dict(world_id='test',authority_root='/synthetic/world',principal='test-owner')
        covered=dict(observe_response_sha256=hashlib.sha256(raw['response_bytes']).hexdigest(),observe_request_sha256=hashlib.sha256(raw['request_bytes']).hexdigest(),context=context,trusted_head_hash=head,selected_observation=triple,manifest=head,state=state,event='')
        bundle_ref=self.save('bundle.json',dict(sessions={'existing':{'trace_refs':self.trace}}))
        policy=dict(lifecycle=dict(public_paths=self.paths,session_bindings={'existing':dict(self.identity,world_id='test',authority_root='/synthetic/world')}),public_context={'principal':'test-owner'})
        def check(coverage):
            with mock.patch.object(v,'verify_evidence',return_value=base), mock.patch.object(n,'verify_native_replay_review',return_value=dict(status='checks_complete_requires_review',coverage=coverage)), mock.patch.object(n,'reassemble_trace',return_value=[None,raw]):
                return v.verify_evidence_with_native_replay(bundle_ref,expected_policy=policy,authority_parser=None,trace_parser=None,native_review_ref={},native_expected_policy={})
        accepted=check([covered]);self.assertEqual(accepted['status'],'checks_complete_requires_review',accepted)
        self.assertEqual(accepted['reasons'],[]);self.assertFalse(accepted['g_b2_granted']);self.assertFalse(accepted['runtime_authorized'])
        uncovered=check([dict(covered,observe_response_sha256='e'*64)])
        self.assertEqual(uncovered['status'],'inconclusive');self.assertTrue(all(x in uncovered['reasons'] for x in v.PUBLIC_PROOF_GAPS))
        self.assertEqual(check([dict(covered,trusted_head_hash='f'*64)])['status'],'fail')

    def test_legacy_verifier_constants_unchanged(self):
        self.assertEqual(len(v.PUBLIC_PROOF_GAPS),3)
        original={'status':'inconclusive','reasons':list(v.PUBLIC_PROOF_GAPS),'proof_checks':[]}
        with mock.patch.object(v,'verify_evidence',return_value=original), mock.patch.object(n,'verify_native_replay_review',return_value={'status':'inconclusive','reasons':['missing'],'coverage':[]}):
            result=v.verify_evidence_with_native_replay({},expected_policy={},authority_parser=None,trace_parser=None,native_review_ref={},native_expected_policy={})
        self.assertEqual(result['status'],'inconclusive')
        self.assertTrue(all(x in result['reasons'] for x in v.PUBLIC_PROOF_GAPS))


if __name__=='__main__':unittest.main()
