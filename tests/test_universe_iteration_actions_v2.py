"""I14 directed synthetic evidence. No native/UE/input capability is claimed."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.universe_iteration import actions as a
from tests.test_universe_iteration_actions import Fixture, encoded


class V2Fixture(Fixture):
    def __init__(self,root,session='initialize'):
        self.v2=False
        super().__init__(root,session)
        self.v2=True
        self.items=[x for x in a.manifest_v2()['items'] if x['session']==session]
        self.frames=self.make_frames()
        self.trace_refs=self.write_trace(self.frames)
        self.build_receipts()

    def build_receipts(self):
        if not self.v2:return super().build_receipts()
        self.receipts,log,cursor,now,serial=[],bytearray(b'synthetic I14 log\n'),0,10,0
        def mapref():
            return self.ref(dict(root=self.binding['authority_root'],files={'HEAD.json':{'bytes':1,'sha256':'f'*64}},bytes=1))
        for item in self.items:
            start,before_offset,events=now,len(log),[]
            call_times=[(start+i*1.5+.1,start+i*1.5+.15+(1 if 'chord' in c['text'] else 0))
                        for i,c in enumerate(item['commands'])]
            for i,stage in enumerate(item['stages']):
                diagnostic=item['kind'] in a.DIAGNOSTIC_KINDS
                if diagnostic:
                    serial+=1
                    selected=a.H1 if item['kind']=='history_write_rejected' or (item['kind']=='held_input' and stage=='held_history') else item['selected_observation']
                    data=dict(format=a.READBACK_V2,binding=self.binding,action_id=item['action_id'],stage=stage,
                              trusted_head=item['trusted_head'],selected_observation=selected,state=self.states(item['kind'])[i],
                              event_serial=serial,origin=item['checkpoint_origins'][i])
                    line=b'LogTemp: Display: EW_I13_READBACK '+encoded(data)
                elif item['kind']=='native':
                    name='ProtocolIds' if item['action_id']=='s1.native_ids' else 'StandaloneAssetAudit'
                    line=('Test Completed. Result={Success} Name={'+name+'} Path={edgeWorld.UniverseHost.'+name+'}\n').encode()
                elif item['kind']=='exit':line=b'LogExit: Preparing to exit.\n'
                else:
                    head=item['observation_heads'][i]
                    line=('Universe world %s observed tick %d, revision %d\n'%(self.binding['world_id'],head['tick'],head['revision'])).encode()
                lo=len(log);log.extend(line);command=item['checkpoint_commands'][i]
                read=call_times[command][1]+.05+i*.001 if command>=0 else start+.1+i*.001
                events.append(dict(stage=stage,log_start=lo,log_end=len(log),read_monotonic=read,map=mapref(),
                                   command_index=command,event_serial=serial if diagnostic else None))
            calls,offset=[],before_offset
            for i,(command,(lo,hi)) in enumerate(zip(item['commands'],call_times)):
                associated=[e for e in events if e['command_index']==i]
                end_offset=associated[-1]['log_end'] if associated else offset
                calls.append(dict(command=command['text'],started_monotonic=lo,completed_monotonic=hi,
                                  raw_tool_ref=self.ref(b'synthetic raw tool result','.txt'),
                                  log_before_offset=offset,log_after_offset=end_offset))
                offset=end_offset
            end=max([start]+[t[1] for t in call_times]+[e['read_monotonic'] for e in events])+.1
            cua=dict(format='universe-i14-cua.v1',binding=self.binding,action_id=item['action_id'],clock=self.clock,calls=calls)
            self.receipts.append(dict(format=a.FORMAT_V2,action_id=item['action_id'],binding=self.binding,
                                     trusted_head=item['trusted_head'],selected_observation=item['selected_observation'],clock=self.clock,
                                     started_monotonic=start,completed_monotonic=end,before=mapref(),after=mapref(),
                                     log=dict(ref=None,device=None,inode=None,before_offset=before_offset,after_offset=len(log),
                                              prefix_sha256=hashlib.sha256(log[:before_offset]).hexdigest()),
                                     trace_range=[cursor,cursor+len(item['expected_operations'])],cua=self.ref(cua),checkpoints=events,
                                     image_checks=[dict(capture_id=item['action_id']+'/'+stage,stage=stage,
                                                        capture_ref=self.ref({'synthetic_capture_only':True}))
                                                   for stage in item['stages']] if 'image_checks' in item['required_evidence'] else []))
            cursor+=len(item['expected_operations']);now=end+.1
        logref=self.ref(bytes(log),'.log');st=Path(logref['path']).stat()
        for receipt in self.receipts:receipt['log'].update(ref=logref,device=st.st_dev,inode=st.st_ino)

    def check(self,receipt):
        return a.validate_receipt_v2(receipt,expected_binding=self.binding,frames=self.frames,expected_context=self.context)


class ActionsV2Test(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name).resolve();self.f=V2Fixture(self.root)
    def tearDown(self):self.tmp.cleanup()
    def test_manifest_v2_charges_all_extra_queries_and_preserves_legacy(self):
        old,new=a.manifest(),a.manifest_v2()
        self.assertEqual(old['interaction_caps'],{'initialize':240,'existing':100})
        self.assertEqual(new['interaction_caps'],{'initialize':274,'existing':100})
        self.assertEqual(new['request_counts'],{'initialize':20,'existing':5})
        for item in new['items']:
            self.assertAlmostEqual(sum(x['max_seconds'] for x in item['commands'])+sum(item['passive_costs'].values()),item['max_seconds'])
            self.assertTrue(all(x['max_seconds']<=10 for x in item['commands']))
            if 'image_checks' in item['required_evidence']:
                self.assertEqual(sum(c['text'].startswith('native Shot via C prepare ') for c in item['commands']),len(item['stages']))
            if item['kind'] in a.DIAGNOSTIC_KINDS:
                self.assertTrue(item['commands'][0]['text'].startswith('UniverseDiagArm '))
                self.assertEqual(item['commands'][-1]['text'],'UniverseDiagDisarm')
        self.assertNotIn('event_serial',a.schema()['properties']['checkpoints']['items']['properties'])
    def test_full_synthetic_v2_pair_does_not_grant_runtime(self):
        result=a.validate_session_v2(self.f.receipts,self.f.trace_refs,expected_binding=self.f.binding,expected_context=self.f.context)
        self.assertEqual(result['request_count'],20);self.assertFalse(result['g_b2_granted'])
        p=self.root/'existing';p.mkdir();f=V2Fixture(p,'existing')
        self.assertEqual(a.validate_session_v2(f.receipts,f.trace_refs,expected_binding=f.binding,expected_context=f.context)['request_count'],5)
    def test_single_chord_has_one_actual_call_and_ordered_native_events(self):
        receipt=next(r for r in self.f.receipts if r['action_id']=='s1.held_input')
        self.f.check(receipt)
        self.assertEqual([e['command_index'] for e in receipt['checkpoints']],[1,1,1])
        calls=json.loads(a.reference(receipt['cua']))['calls']
        self.assertEqual(sum('chord' in c['command'] for c in calls),1)
        self.assertTrue(all(e['read_monotonic']>=calls[1]['completed_monotonic'] for e in receipt['checkpoints']))
        for change in (lambda r:r['checkpoints'][1].update(command_index=2),
                       lambda r:r['checkpoints'][1].update(event_serial=r['checkpoints'][0]['event_serial']),
                       lambda r:r['checkpoints'][1].update(read_monotonic=0)):
            r=deepcopy(receipt);change(r)
            with self.assertRaises(a.Invalid):self.f.check(r)
    def test_missing_query_and_wrong_raw_call_bracket_rejected(self):
        base=next(r for r in self.f.receipts if r['action_id']=='s1.camera')
        query=base['checkpoints'][1]['command_index']
        for change in (lambda c:c['calls'].pop(query),lambda c:c['calls'][query].update(log_after_offset=c['calls'][query]['log_before_offset'])):
            r=deepcopy(base);r['cua']=self.f.edit_reference(r['cua'],change)
            with self.assertRaises(a.Invalid):self.f.check(r)
    def test_fake_native_origin_and_event_serial_rejected(self):
        base=next(r for r in self.f.receipts if r['action_id']=='s1.held_input')
        for field,value in (('origin','query'),('format',a.READBACK_FORMAT),('event_serial',False)):
            r=deepcopy(base);raw=a.reference(r['log']['ref']);e=r['checkpoints'][-1]
            data=json.loads(raw[e['log_start']:e['log_end']].split(b'EW_I13_READBACK ')[1]);data[field]=value
            line=b'EW_I13_READBACK '+encoded(data);new=raw[:e['log_start']]+line
            ref=self.f.ref(new,'.log');st=Path(ref['path']).stat();r['log'].update(ref=ref,device=st.st_dev,inode=st.st_ino,after_offset=len(new));e['log_end']=len(new)
            cua=json.loads(a.reference(r['cua']));cua['calls'][1]['log_after_offset']=len(new);cua['calls'][2]['log_before_offset']=len(new);cua['calls'][2]['log_after_offset']=len(new);r['cua']=self.f.ref(cua)
            with self.assertRaises(a.Invalid):self.f.check(r)
    def test_camera_shortest_angle_tolerance_without_rounding(self):
        diagnostic=[{'state':dict(camera_id='cam',view_target_id='cam',rotation=r)} for r in ([0,179.999,0],[0,-165.001,0],[.00005,179.99905,-.00005])]
        original=deepcopy(diagnostic);a._camera_v2(diagnostic);self.assertEqual(diagnostic,original)
        for index,rotation in ((2,[0,180.001,0]),(1,[0,-164,0])):
            values=deepcopy(diagnostic);values[index]['state']['rotation']=rotation
            with self.assertRaises(a.Invalid):a._camera_v2(values)
    def test_capture_ids_stage_mapping_is_exact(self):
        base=next(r for r in self.f.receipts if r['action_id']=='s1.camera')
        for change in (lambda r:r['image_checks'].pop(),lambda r:r['image_checks'][0].update(capture_id='another/stage'),
                       lambda r:r['image_checks'][1].update(stage='before')):
            r=deepcopy(base);change(r)
            with self.assertRaises(a.Invalid):self.f.check(r)
    def test_event_replay_across_session_and_stale_maps_rejected(self):
        receipts=deepcopy(self.f.receipts);receipts[11]['before']=receipts[10]['before']
        with self.assertRaises(a.Invalid):a.validate_session_v2(receipts,self.f.trace_refs,expected_binding=self.f.binding,expected_context=self.f.context)
        frames=deepcopy(self.f.frames);frames[12]['request']['payload']['command_digest']='0'*64
        self.f.counter+=1;refs=self.f.write_trace(frames)
        with self.assertRaises(a.Invalid):a.validate_session_v2(self.f.receipts,refs,expected_binding=self.f.binding,expected_context=self.f.context)
    def test_v2_schema_and_readiness_stay_explicit_no_go(self):
        schema=a.schema_v2();event=schema['properties']['checkpoints']['items']['properties']
        self.assertNotIn('monotonic',event);self.assertIn('read_monotonic',event)
        self.assertEqual(schema['properties']['format'],{'const':a.FORMAT_V2})
        self.assertEqual(a.readiness_v2({},expected_source_sha='a'*40)['status'],'no_go')
        self.assertEqual(a.action_advice_v2('s1.camera',ui_allowed=True,quit_due=True,stop=False,remaining_seconds=99)['commands'],[])
    def test_cpp_diagnostics_disabled_default_and_read_only_boundaries(self):
        base=Path(__file__).resolve().parents[1]/'engine_platforms/unreal/EdgeWorldHost/Source/EdgeWorldHost'
        helper=(base/'EdgeWorldUniverseDiagnostics.cpp').read_text()
        mode=(base/'EdgeWorldUniverseGameMode.cpp').read_text()
        self.assertIn('Enable!=TEXT("1")',helper)
        self.assertNotIn('SendControl(',helper);self.assertNotIn('OpenTransport(',helper)
        reader=mode[mode.index('bool AEdgeWorldUniverseGameMode::EmitDiagnostic'):]
        self.assertIn('UGameplayStatics::IsGamePaused(GetWorld())',reader)
        self.assertIn('ReadProjectionHidden',reader);self.assertNotIn('SendControl(',reader)
        self.assertNotIn('bExecuteWhenPaused',mode)

if __name__=='__main__':unittest.main()
