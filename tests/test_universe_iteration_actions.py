"""Synthetic offline fixtures; none are UE/runtime acceptance evidence."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from scripts.universe_iteration import actions as a


def encoded(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':')) + '\n').encode()


class Fixture:
    def __init__(self, root, session='initialize'):
        self.root, self.serial, self.counter = root, 0, 0
        self.binding = dict(run_id='synthetic-test', session=session, world_id='test-world',
                            authority_root=str(root / 'authority'), source_sha='a' * 40,
                            host_pid=120, worker_pid=121, generation=1)
        self.context = dict(principal='test-owner', trust_anchor='b' * 64,
                            expected_build='c' * 64, expected_options='d' * 64)
        self.clock = dict(id='synthetic-clock', anchor_monotonic=0, anchor_utc='2026-11-02T00:00:00+00:00')
        self.items = [x for x in a.manifest()['items'] if x['session'] == session]
        self.frames = self.make_frames()
        self.trace_refs = self.write_trace(self.frames)
        self.build_receipts()

    def ref(self, value, suffix='.json'):
        self.counter += 1
        path = self.root / ('evidence-%04d' % self.counter + suffix)
        raw = value if type(value) is bytes else encoded(value)
        path.write_bytes(raw)
        return {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}

    def response(self, rid, op, payload):
        return dict(protocol_version=1, request_id=rid, ok=True,
                    result=dict(domain='edgeworld.universe.authority', version='0.2',
                                world_id=self.binding['world_id'], operation=op, payload=payload))

    def make_frames(self):
        frames, previous_advance, last_prepared = [], None, None
        for item in self.items:
            observe_index = 0
            for index, op in enumerate(item['expected_operations']):
                rid = 'u-%032x' % (len(frames) + 1)
                req = dict(domain='edgeworld.universe.authority', version='0.2', world_id=self.binding['world_id'])
                head = item['trusted_head']
                hb = dict(self.context, world_id=self.binding['world_id'], authority_root=self.binding['authority_root'], storage_state='ready')
                if op == 'status':
                    payload = dict(head, storage_state='ready', head_binding=hb)
                elif op == 'initialize':
                    req['test_profile'] = 'composite-rigid-support.v0.2'
                    payload = dict(commit_status='confirmed', result=None, head_binding=hb)
                elif op == 'prepare':
                    retain = item['kind'] == 'retain'
                    req['intent'] = {'body': dict(action='retain_snapshot' if retain else 'physics_step',
                                                expected_revision=0 if retain else 1, budget=0 if retain else 1,
                                                random_cursor=0, principal=self.context['principal'], case_id='weak', tick_delta=0 if retain else 1)}
                    last_prepared = dict(command_records=[{'synthetic_closure': item['action_id']}], command_digest='e' * 64)
                    payload = dict(last_prepared, committed_result=None, head_binding=hb)
                elif op == 'advance':
                    req.update(last_prepared, principal=self.context['principal'])
                    payload = dict(commit_status='confirmed', result={'body': head}, head_binding=hb)
                    if item['kind'] == 'retry':
                        req, payload = deepcopy(previous_advance)
                    else:
                        previous_advance = deepcopy((req, payload))
                elif op == 'observe':
                    selected = item['observation_heads'][observe_index]
                    observe_index += 1
                    req.update(selected)
                    payload = dict(manifest={'body': selected}, watermark=selected['watermark'],
                                   storage_state='ready', records=[{'synthetic': True}], membership=[{'synthetic': True}])
                request = dict(protocol_version=1, request_id=rid, operation=op, payload=req)
                response = self.response(rid, op, payload)
                if item['kind'] == 'initialize' and index == 0:
                    response = dict(protocol_version=1, request_id=rid, ok=False,
                                    error={'code': 'NOT_READY', 'commit_status': 'not_attempted'})
                frames.append(dict(request=request, response=response))
        return frames

    def write_trace(self, frames):
        directory = self.root / ('trace-%d' % self.counter)
        directory.mkdir()
        refs, serial = [], 0
        def append(direction, raw, request=None, extra=None):
            nonlocal serial
            serial += 1
            path = directory / ('TRACE-%08d' % serial)
            meta = dict(serial=str(serial), direction=direction, raw_file=path.name + '.bin',
                        byte_count=len(raw), monotonic_seconds=serial / 100,
                        host_pid=self.binding['host_pid'], worker_pid=self.binding['worker_pid'], generation='1')
            if request:
                meta.update(request_id=request['request_id'], operation=request['operation'])
            meta.update(extra or {})
            for dest, content in ((path.with_suffix('.bin'), raw), (path.with_suffix('.json'), encoded(meta))):
                dest.write_bytes(content)
                refs.append({'path': str(dest), 'sha256': hashlib.sha256(content).hexdigest()})
        for frame in frames:
            request = frame['request']
            raw = encoded(request)
            append('request', raw, request)
            append('write-result', b'', request, {'written_bytes': len(raw)})
            response = encoded(frame['response'])
            # Reassembly must handle actual chunk boundaries, not only preassembled JSON.
            midpoint = len(response) // 2
            append('stdout-chunk', response[:midpoint], request)
            append('stdout-chunk', response[midpoint:], request)
            append('response-complete', b'', request)
        exit_event = dict(worker_pid=self.binding['worker_pid'], generation='1', return_code_available=True,
                          reaped=True, trace_complete=True, exit_code=0, stop_kind='normal',
                          hard_kill_sent=False, operational_failure=False)
        append('worker-exit', encoded(exit_event))
        return refs

    def states(self, kind):
        return {
            'probe': [{'quit_guard_ready': True, 'preflush': True}],
            'final': [{'space_down': False, 'r_down': False, 'paused': False, 'visibility_restored': True, 'fps_restored': True}],
            'camera': [dict(camera_id='camera1', view_target_id='camera1', rotation=r) for r in ([0, 0, 0], [0, 15, 0], [0, 0, 0])],
            'visibility': [{'proxies': {'proxy1': x, 'proxy2': x}} for x in (False, True, False)],
            'framerate': [{'max_fps': x} for x in (60, 30, 60)],
            'pause': [{'paused': x} for x in (False, True, False)],
            'held_input': [{'space_down': True, 'can_write': False}, {'space_down': True, 'can_write': True}, {'space_down': False, 'can_write': True}],
            'history_write_rejected': [
                dict(format=a.HISTORY_REJECTION_FORMAT, space_down=False, r_down=False, can_write=False,
                     handled_input=dict(key='Space', event='pressed', handler='SpacePressed', handled=True,
                                        rejected=True, reason='history_read_only', counter_before=1, counter_after=2),
                     handler_counts={'SpacePressed': 2, 'Retain': 1}),
                dict(format=a.HISTORY_REJECTION_FORMAT, space_down=False, r_down=False, can_write=False,
                     handled_input=dict(key='R', event='pressed', handler='Retain', handled=True,
                                        rejected=True, reason='history_read_only', counter_before=1, counter_after=2),
                     handler_counts={'SpacePressed': 2, 'Retain': 2}),
                dict(format=a.HISTORY_REJECTION_FORMAT, space_down=False, r_down=False, can_write=False,
                     handled_input=None, handler_counts={'SpacePressed': 2, 'Retain': 2})],
        }.get(kind)

    def build_receipts(self):
        self.receipts, log, cursor, now = [], bytearray(b'synthetic UE log\n'), 0, 10
        def map_ref():
            return self.ref(dict(root=self.binding['authority_root'], files={'HEAD.json': {'bytes': 1, 'sha256': 'f' * 64}}, bytes=1))
        for item in self.items:
            start, checkpoints, before_offset = now, [], len(log)
            for i, stage in enumerate(item['stages']):
                if item['kind'] in a.DIAGNOSTIC_KINDS:
                    selected = a.H1 if item['kind'] == 'history_write_rejected' or (item['kind'] == 'held_input' and stage == 'held_history') else item['selected_observation']
                    value = dict(format=a.READBACK_FORMAT, binding=self.binding, action_id=item['action_id'], stage=stage,
                                 trusted_head=item['trusted_head'], selected_observation=selected, state=self.states(item['kind'])[i])
                    line = b'LogTemp: Display: EW_I13_READBACK ' + encoded(value)
                elif item['kind'] == 'native':
                    name = 'ProtocolIds' if item['action_id'] == 's1.native_ids' else 'StandaloneAssetAudit'
                    line = ('Test Completed. Result={Success} Name={' + name + '} Path={edgeWorld.UniverseHost.' + name + '}\n').encode()
                elif item['kind'] == 'exit':
                    line = b'LogExit: Preparing to exit.\n'
                else:
                    head = item['observation_heads'][i]
                    line = ('Universe world %s observed tick %d, revision %d\n' % (self.binding['world_id'], head['tick'], head['revision'])).encode()
                offset = len(log); log.extend(line)
                checkpoints.append(dict(stage=stage, log_start=offset, log_end=len(log), monotonic=start + max(0, item['checkpoint_commands'][i] + 1) * 2 + .1 + i * .01,
                                        map=map_ref(), after_command=item['checkpoint_commands'][i]))
            end = max(x['monotonic'] for x in checkpoints) + .2
            cua = dict(format='universe-i13-cua.v1', binding=self.binding, action_id=item['action_id'], clock=self.clock,
                       calls=[dict(command=c['text'], started_monotonic=start+2*i+1,
                                   completed_monotonic=start+2*i+1.05,
                                   raw_tool_ref=self.ref(b'synthetic raw CUA result', '.txt')) for i,c in enumerate(item['commands'])])
            receipt = dict(format=a.FORMAT, action_id=item['action_id'], binding=self.binding,
                           trusted_head=item['trusted_head'], selected_observation=item['selected_observation'], clock=self.clock,
                           started_monotonic=start, completed_monotonic=end, before=map_ref(), after=map_ref(),
                           log=dict(ref=None, device=None, inode=None, before_offset=before_offset, after_offset=len(log),
                                    prefix_sha256=hashlib.sha256(log[:before_offset]).hexdigest()),
                           trace_range=[cursor,cursor+len(item['expected_operations'])], cua=self.ref(cua),
                           checkpoints=checkpoints,
                           image_checks=[self.ref({'synthetic_C_result_reference_only': True}) for _ in item['stages']] if 'image_checks' in item['required_evidence'] else [])
            self.receipts.append(receipt)
            cursor += len(item['expected_operations']); now = end + .1
        log_ref = self.ref(bytes(log), '.log')
        st = Path(log_ref['path']).stat()
        for receipt in self.receipts:
            receipt['log'].update(ref=log_ref, device=st.st_dev, inode=st.st_ino)

    def check(self, receipt):
        return a.validate_receipt(receipt, expected_binding=self.binding, frames=self.frames, expected_context=self.context)

    def edit_reference(self, ref, edit):
        value = json.loads(Path(ref['path']).read_bytes())
        edit(value)
        return self.ref(value)


class ActionsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.f = Fixture(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_manifest_exact_counts_order_and_budget(self):
        m = a.manifest()
        for session, count, cap in [('initialize',20,240),('existing',5,100)]:
            items = [x for x in m['items'] if x['session']==session]
            self.assertEqual(sum(len(x['expected_operations']) for x in items),count)
            self.assertEqual(sum(x['max_seconds'] for x in items if x['phase']=='interaction'),cap)
            for x in items:
                self.assertEqual(x['phase'],x['charged_budget'])
                self.assertAlmostEqual(sum(c['max_seconds'] for c in x['commands'])+sum(x['passive_costs'].values()),x['max_seconds'])
        self.assertEqual(set(m['readonly_kinds']),a.READONLY)
        m['items'][0]['trusted_head']['tick']=99
        self.assertEqual(a.manifest()['items'][0]['trusted_head'],a.H0)

    def test_complete_synthetic_session_does_not_grant_acceptance(self):
        result = a.validate_session(self.f.receipts,self.f.trace_refs,expected_binding=self.f.binding,expected_context=self.f.context)
        self.assertEqual(result['request_count'],20)
        self.assertFalse(result['g_b2_granted'])
        self.assertFalse(result['runtime_authenticity_verified'])
        directory=self.root/'existing';directory.mkdir(); f=Fixture(directory,'existing')
        self.assertEqual(a.validate_session(f.receipts,f.trace_refs,expected_binding=f.binding,expected_context=f.context)['request_count'],5)

    def test_required_fields_wrong_binding_heads_times_and_missing_after(self):
        receipt=self.f.receipts[7]
        mutations=[lambda r:r.pop('after'),lambda r:r.update(extra=True),
                   lambda r:r.update(selected_observation=a.H1),lambda r:r.update(trusted_head=a.H1),
                   lambda r:r['binding'].update(host_pid=True),
                   lambda r:r.update(completed_monotonic=r['started_monotonic']+999),
                   lambda r:r['clock'].update(anchor_utc='2026-11-02'),
                   lambda r:r['checkpoints'].pop(),
                   lambda r:r['log'].update(before_offset=r['log']['after_offset']),
                   lambda r:r['log'].update(inode=0),
                   lambda r:r['checkpoints'][0].update(log_start=0),
                   lambda r:r['checkpoints'][0].update(monotonic=0)]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                r=deepcopy(receipt);mutate(r)
                with self.assertRaises((a.Invalid,KeyError)):self.f.check(r)

    def test_map_hash_and_interior_subaction_change_rejected(self):
        r=deepcopy(self.f.receipts[11])
        for location in ('after','checkpoint'):
            bad=self.f.edit_reference(r['before'],lambda v:v['files']['HEAD.json'].update(sha256='0'*64))
            q=deepcopy(r)
            if location=='after':q['after']=bad
            else:q['checkpoints'][1]['map']=bad
            with self.assertRaisesRegex(a.Invalid,'authority changed'):self.f.check(q)
        q=deepcopy(r);q['after']['sha256']='0'*64
        with self.assertRaisesRegex(a.Invalid,'hash mismatch'):self.f.check(q)

    def test_trace_reassembly_rejects_raw_hash_pid_serial_and_extra_artifact(self):
        self.assertEqual(len(a.load_trace(self.f.trace_refs,expected_binding=self.f.binding)),20)
        q=deepcopy(self.f.trace_refs);q[0]['sha256']='0'*64
        with self.assertRaises(a.Invalid):a.load_trace(q,expected_binding=self.f.binding)
        for field,value in [('host_pid',999),('serial','999'),('generation','2'),('written_bytes',0)]:
            q=deepcopy(self.f.trace_refs)
            idx=next(i for i,x in enumerate(q) if x['path'].endswith('.json') and
                     (field!='written_bytes' or json.loads(Path(x['path']).read_bytes())['direction']=='write-result'))
            old_path=q[idx]['path']; saved_raw=Path(old_path).read_bytes(); raw=json.loads(saved_raw);raw[field]=value
            Path(old_path).write_bytes(encoded(raw));q[idx]['sha256']=hashlib.sha256(encoded(raw)).hexdigest()
            with self.assertRaises(a.Invalid):a.load_trace(q,expected_binding=self.f.binding)
            Path(old_path).write_bytes(saved_raw)
        q=self.f.trace_refs+[self.f.ref(b'unclaimed','.bin')]
        with self.assertRaises(a.Invalid):a.load_trace(q,expected_binding=self.f.binding)

    def test_exact_operation_and_retry_result_not_just_count(self):
        for mutate in [lambda f:f[12]['request']['payload'].update(command_digest='0'*64),
                       lambda f:f[12]['response']['result']['payload'].update(result={'body':a.H1}),
                       lambda f:f[16]['request']['payload'].update(revision=2),
                       lambda f:f[8]['request']['payload']['intent']['body'].update(case_id='strong')]:
            frames=deepcopy(self.f.frames);mutate(frames)
            self.f.counter+=1;refs=self.f.write_trace(frames)
            with self.assertRaises(a.Invalid):a.validate_session(self.f.receipts,refs,expected_binding=self.f.binding,expected_context=self.f.context)

    def test_session_rejects_omitted_reordered_and_reused_frames(self):
        for transform in [lambda r:r[:-1],lambda r:list(reversed(r)),lambda r:r[:7]+r[8:]]:
            with self.assertRaises(a.Invalid):a.validate_session(transform(deepcopy(self.f.receipts)),self.f.trace_refs,expected_binding=self.f.binding,expected_context=self.f.context)
        r=deepcopy(self.f.receipts);r[7]['trace_range'][0]-=1
        with self.assertRaises(a.Invalid):a.validate_session(r,self.f.trace_refs,expected_binding=self.f.binding,expected_context=self.f.context)

    def test_no_marker_and_incomplete_release_restore_rejected(self):
        for item in ('s1.held_input','s1.camera','s1.visibility','s1.framerate','s1.pause','s1.history_write_rejected'):
            r=deepcopy(next(x for x in self.f.receipts if x['action_id']==item))
            # Replace one typed state in the underlying bound log, not just the receipt.
            raw=bytearray(a.reference(r['log']['ref']));ev=r['checkpoints'][-1]
            line=bytes(raw[ev['log_start']:ev['log_end']]);data=json.loads(line.split(b'EW_I13_READBACK ')[1]);data['state']={}
            replacement=b'EW_I13_READBACK '+encoded(data)
            new=bytes(raw[:ev['log_start']])+replacement
            ref=self.f.ref(new,'.log');st=Path(ref['path']).stat();r['log'].update(ref=ref,device=st.st_dev,inode=st.st_ino,after_offset=len(new));ev['log_end']=len(new)
            with self.assertRaises(a.Invalid):self.f.check(r)
        r=deepcopy(self.f.receipts[11]);r['checkpoints'][1]['log_start']=r['checkpoints'][0]['log_start']
        with self.assertRaises(a.Invalid):self.f.check(r)

    def test_cua_missing_raw_or_wrong_command_and_tool_timeout(self):
        r=deepcopy(self.f.receipts[5])
        for mutate in [lambda v:v['calls'].pop(),lambda v:v['calls'][0].update(command='not the actual command'),
                       lambda v:v['calls'][0].update(completed_monotonic=999),lambda v:v['calls'][0]['raw_tool_ref'].update(sha256='0'*64)]:
            q=deepcopy(r);q['cua']=self.f.edit_reference(q['cua'],mutate)
            with self.assertRaises(a.Invalid):self.f.check(q)

    def test_private_symlink_duplicate_nonfinite_and_boolean_numbers(self):
        secret=self.root/'authority.key';secret.write_bytes(b'never read')
        with self.assertRaisesRegex(a.Invalid,'private'):a.reference({'path':str(secret),'sha256':hashlib.sha256(secret.read_bytes()).hexdigest()})
        real=self.root/'real';real.write_bytes(b'public');link=self.root/'link';link.symlink_to(real)
        with self.assertRaisesRegex(a.Invalid,'symlink'):a.reference({'path':str(link),'sha256':hashlib.sha256(b'public').hexdigest()})
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}'):
            with self.assertRaises(a.Invalid):a._json(raw)
        expected=deepcopy(self.f.binding);expected['generation']=True
        with self.assertRaises(a.Invalid):a.load_trace(self.f.trace_refs,expected_binding=expected)

    def test_readiness_is_no_go_without_actual_capabilities(self):
        result=a.readiness({},expected_source_sha=self.f.binding['source_sha'])
        self.assertEqual(result['status'],'no_go');self.assertEqual(len(result['reasons']),5)
        capabilities={}
        for name in ('readback_markers','cross_call_hold','png_contract','quit_guard','timings'):
            proof=dict(format='universe-i13-capability-review.v1',source_sha=self.f.binding['source_sha'],capability=name,
                       reviewer='independent',owner='owner',decision='pass',evidence_refs=[self.f.ref(b'synthetic review evidence','.txt')],
                       action_upper_seconds={x['action_id']:x['max_seconds'] for x in a.manifest()['items'] if x['phase']=='interaction'} if name=='timings' else {})
            capabilities[name]=self.f.ref(proof)
        self.assertEqual(a.readiness(capabilities,expected_source_sha=self.f.binding['source_sha'])['status'],'ready_for_R_review')
        capabilities['cross_call_hold']=self.f.edit_reference(capabilities['cross_call_hold'],lambda v:v.update(decision='inconclusive'))
        self.assertEqual(a.readiness(capabilities,expected_source_sha=self.f.binding['source_sha'])['status'],'no_go')
        capabilities['cross_call_hold']=self.f.edit_reference(capabilities['cross_call_hold'],lambda v:v.update(reviewer='owner'))
        with self.assertRaises(a.Invalid):a.readiness(capabilities,expected_source_sha=self.f.binding['source_sha'])

    def test_guard_denial_never_returns_more_ui_commands(self):
        for guard in [dict(ui_allowed=False,quit_due=False,stop=False,remaining_seconds=30),
                      dict(ui_allowed=True,quit_due=True,stop=False,remaining_seconds=30),
                      dict(ui_allowed=True,quit_due=False,stop=True,remaining_seconds=30),
                      dict(ui_allowed=True,quit_due=False,stop=False,remaining_seconds=1)]:
            self.assertEqual(a.action_advice('s1.camera',**guard)['commands'],[])
        self.assertEqual(a.action_advice('s1.camera',ui_allowed=True,quit_due=False,stop=False,remaining_seconds=20)['max_tool_wait_seconds'],10)

    def test_subaction_cannot_precede_input_or_reuse_map_capture(self):
        base=next(r for r in self.f.receipts if r['action_id']=='s1.camera')
        r=deepcopy(base);r['checkpoints'][1]['monotonic']=r['started_monotonic']+.01
        with self.assertRaises(a.Invalid):self.f.check(r)
        r=deepcopy(base);r['checkpoints'][1]['after_command']=1
        with self.assertRaisesRegex(a.Invalid,'association'):self.f.check(r)
        r=deepcopy(base);r['after']=deepcopy(r['before'])
        with self.assertRaisesRegex(a.Invalid,'fresh separate map'):self.f.check(r)
        r=deepcopy(base);r['trusted_head']['tick']=True
        with self.assertRaises(a.Invalid):self.f.check(r)

    def test_diagnostic_boolean_is_not_integer_and_trusted_head_is_distinct(self):
        base=next(r for r in self.f.receipts if r['action_id']=='s1.pause')
        for field in ('boolean','head','marker'):
            r=deepcopy(base);raw=a.reference(r['log']['ref']);event=r['checkpoints'][-1]
            data=json.loads(raw[event['log_start']:event['log_end']].split(b'EW_I13_READBACK ')[1])
            if field=='boolean':data['state']['paused']=0
            if field=='head':data['trusted_head']=deepcopy(a.H1)
            line=(b'not-a-marker ' if field=='marker' else b'EW_I13_READBACK ')+encoded(data)
            new=raw[:event['log_start']]+line;ref=self.f.ref(new,'.log');st=Path(ref['path']).stat()
            r['log'].update(ref=ref,device=st.st_dev,inode=st.st_ino,after_offset=len(new));event['log_end']=len(new)
            with self.assertRaises(a.Invalid):self.f.check(r)

    def test_unexpected_extra_business_request_and_abnormal_worker_rejected(self):
        frames=deepcopy(self.f.frames);extra=deepcopy(frames[-1]);extra['request']['request_id']='u-'+'f'*32
        extra['response']['request_id']=extra['request']['request_id'];frames.append(extra)
        self.f.counter+=1;refs=self.f.write_trace(frames)
        with self.assertRaisesRegex(a.Invalid,'exact request count'):
            a.validate_session(self.f.receipts,refs,expected_binding=self.f.binding,expected_context=self.f.context)
        meta_ref=next(r for r in self.f.trace_refs if r['path'].endswith('.json') and json.loads(Path(r['path']).read_bytes())['direction']=='worker-exit')
        meta=json.loads(Path(meta_ref['path']).read_bytes());raw_path=Path(meta_ref['path']).parent/meta['raw_file']
        event=json.loads(raw_path.read_bytes());event['stop_kind']='forced';changed=encoded(event);raw_path.write_bytes(changed)
        for r in self.f.trace_refs:
            if r['path']==str(raw_path):r['sha256']=hashlib.sha256(changed).hexdigest()
        meta['byte_count']=len(changed);Path(meta_ref['path']).write_bytes(encoded(meta));meta_ref['sha256']=hashlib.sha256(encoded(meta)).hexdigest()
        with self.assertRaisesRegex(a.Invalid,'abnormal worker exit'):a.load_trace(self.f.trace_refs,expected_binding=self.f.binding)

    def test_schema_is_frozen_machine_readable_and_failures_are_typed(self):
        schema=a.schema()
        self.assertEqual(set(schema['required']),a.RECEIPT_FIELDS)
        self.assertFalse(schema['additionalProperties'])
        self.assertEqual(set(schema['$defs']),{'reference','binding','head','clock','readback','cua','rejected_input','history_rejection_state'})
        self.assertEqual(schema['properties']['trace_range']['maxItems'],2)
        for value in (None,{},[],{'format':a.FORMAT}):
            with self.assertRaises(a.Invalid):a.validate_receipt(value,expected_binding=self.f.binding,frames=self.f.frames,expected_context=self.f.context)

    def test_history_idle_state_without_handled_input_is_not_rejection(self):
        r=deepcopy(next(x for x in self.f.receipts if x['action_id']=='s1.history_write_rejected'))
        self.f.check(r)
        raw=a.reference(r['log']['ref']); prefix=raw[:r['log']['before_offset']]; lines=[]
        for event in r['checkpoints']:
            data=json.loads(raw[event['log_start']:event['log_end']].split(b'EW_I13_READBACK ')[1])
            # Same released keys/can_write and no prepare, but neither key reached a handler.
            data['state']={'space_down':False,'r_down':False,'can_write':False}
            line=b'EW_I13_READBACK '+encoded(data);event['log_start']=len(prefix)+sum(map(len,lines))
            event['log_end']=event['log_start']+len(line);lines.append(line)
        new=prefix+b''.join(lines);ref=self.f.ref(new,'.log');st=Path(ref['path']).stat()
        r['log'].update(ref=ref,device=st.st_dev,inode=st.st_ino,after_offset=len(new))
        with self.assertRaisesRegex(a.Invalid,'history rejection state'):self.f.check(r)

    def test_history_requires_handled_rejected_reason_and_counter_increment(self):
        item=next(x for x in a.manifest()['items'] if x['kind']=='history_write_rejected')
        states=self.f.states('history_write_rejected')
        mutations=[lambda s:s[0]['handled_input'].update(handled=False),
                   lambda s:s[1]['handled_input'].update(rejected=False),
                   lambda s:s[0]['handled_input'].update(reason='focus_lost'),
                   lambda s:s[1]['handled_input'].update(key='Space'),
                   lambda s:s[0]['handled_input'].update(counter_after=1),
                   lambda s:s[0]['handled_input'].update(counter_before=True),
                   lambda s:s[1]['handler_counts'].update(SpacePressed=3),
                   lambda s:s[2]['handler_counts'].update(Retain=3),
                   lambda s:s[2].update(handled_input=s[1]['handled_input'])]
        for mutate in mutations:
            values=deepcopy(states);mutate(values)
            diagnostics=[dict(stage=stage,selected_observation=a.H1,state=state) for stage,state in zip(item['stages'],values)]
            with self.subTest(mutation=mutate):
                with self.assertRaises(a.Invalid):a._states(item,diagnostics)

    def test_import_has_no_runtime_side_effects(self):
        # Static boundary plus patched process/UI imports: module has no process launch facilities.
        import ast
        tree=ast.parse(Path(a.__file__).read_text())
        imports={n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)}|{x.name for n in ast.walk(tree) if isinstance(n,ast.Import) for x in n.names}
        self.assertFalse(imports & {'subprocess','socket','engine','universe_authority'})


if __name__=='__main__':unittest.main()
