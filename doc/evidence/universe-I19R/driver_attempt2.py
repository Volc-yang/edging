"""Frozen I19 root execution artifact; fixed slice, actual CUA originals, automatic close.

stdin accepts only start/ready/begin/end/abort. It never performs UI operations.
After the one real quit it automatically waits, replays only this run's complete
responses, seals, and records the complete declared resource boundary.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import sys
import time
import threading
from datetime import datetime, timezone

TOOL = Path(__file__).resolve().parents[3]
ROOT = Path('/Volumes/DevSSD/Unreal/Projects/EdgeWorld/I15-20261102-r4-readonly-probe')
OUT = ROOT/'I19-20261109-metal-slice-attempt2'
sys.dont_write_bytecode = True
sys.path.insert(0, str(TOOL/'scripts'))
from universe_iteration import capability as cap, lifecycle as lc, probe_actions as probe, capture, native_replay
import run_universe_slice_acceptance as common
spec = importlib.util.spec_from_file_location('i18_metadata_helpers', TOOL/'doc/evidence/universe-I18R/driver.py')
metadata = importlib.util.module_from_spec(spec); spec.loader.exec_module(metadata)
ref, save = metadata.ref, metadata.save


def reply(value):
    print(json.dumps(value, sort_keys=True, allow_nan=False), flush=True)


class Run:
    def __init__(self, inputs):
        self.inputs = inputs
        self.prepared = lc.json_ref(inputs['prepared_ref'])
        self.card = lc.json_ref(inputs['card_ref'])
        self.manifest = probe.probe_manifest_v2()
        validated = cap.validate_capability_card(inputs['card_ref']['path'],
            expected_card_sha256=inputs['card_ref']['sha256'],
            expected_prepared_sha256=inputs['prepared_ref']['sha256'],
            expected_probe_manifest_sha256=inputs['probe_manifest_ref']['sha256'],
            expected_product_source=inputs['product_source'], expected_tool_source=inputs['tool_source'],
            expected_native_source_sha=inputs['native_source'], execute=True)
        self.external_before = metadata.external_snapshot()
        assert not any(x['errors'] for x in self.external_before['roots'].values())
        self.external_before_ref = save(OUT/'prep/external-before.json', self.external_before)
        self.authority_before = common.authority_map(Path(self.prepared['authority_root']))
        assert self.authority_before['files'] == lc.json_ref(self.prepared['before_map_ref'])['files']
        baseline = lc.observe_once(OUT/'prep/pre-dispatch.ps')
        assert not lc.classify_processes(baseline['processes'], [], self.prepared['binary_pins']['ue']['path'])
        self.campaign_offset=(datetime.now(timezone.utc)-datetime.fromisoformat("2026-11-09T08:53:10.799685+00:00")).total_seconds()
        self.started = time.monotonic()
        self.c = cap.CapabilityController(validated)
        (self.c.output/'controller-inputs').mkdir(mode=0o700)
        self.c.start_observer()
        self.guard_stop=threading.Event()
        def guard():
            if not self.guard_stop.wait(max(0,840-self.campaign_offset)):
                self.c.observer_error="I19 parent deadline closing reserve reached"
        self.guard=threading.Thread(target=guard,daemon=True);self.guard.start()
        self.seq = 0; self.groups = []; self.group = None; self.next_step = 0
        self.steps = [(item, i, command) for item in self.manifest['items'] for i, command in enumerate(item['commands'])]
        self.active = None; self.shot = None; self.capture_ref = None; self.last_capture_map = None
        self.receipts = []; self.finished = False

    def new(self, stem, value=None, *, raw=None):
        self.seq += 1
        return save(self.c.output/'controller-inputs'/('%04d-%s'%(self.seq, stem)), value, raw=raw)

    def amap(self):
        value = common.authority_map(Path(self.prepared['authority_root']))
        assert value['files'] == self.authority_before['files']
        return self.new('map.json', value), time.monotonic()

    def logpin(self, before):
        path = self.c.output/'metal/ue.log'; raw = path.read_bytes(); st = path.stat()
        return dict(device=st.st_dev, inode=st.st_ino,
                    before_offset=before, after_offset=len(raw), prefix_sha256=hashlib.sha256(raw[:before]).hexdigest())

    def raw_cua(self, marker, offset):
        """Copy only matching FUTURE CUA records, preserving original JSONL bytes.

        No historical conversation, other app records, credentials or unrelated
        tool payloads are copied. A missing raw result is a failure, not prose.
        """
        path = Path(self.inputs['session_transcript']); calls = {}; selected = None; original = None
        with path.open('rb') as stream:
            stream.seek(offset)
            for line in stream:
                value = json.loads(line); p = value.get('payload', {})
                if value.get('type') != 'response_item': continue
                if p.get('type') == 'function_call' and p.get('namespace') == 'mcp__cua_repl':
                    arguments = json.loads(p['arguments'])
                    if marker in arguments.get('code', ''):
                        assert selected is None, 'duplicate actual CUA command (no retry)'
                        selected = p['call_id']; calls[selected] = line
                if p.get('type') == 'function_call_output' and p.get('call_id') == selected and selected:
                    assert original is None, 'duplicate CUA result'
                    original = calls[selected]+line
                    outputs = p['output']
        assert original is not None, 'original matching CUA call and result not persisted'
        records = []
        for block in outputs:
            if block.get('type') == 'input_text':
                try: value = json.loads(block['text'])
                except (ValueError, TypeError): continue
                if type(value) is dict and value.get('i19_step') == marker: records.append(value)
        assert len(records) == 1 and records[0].get('success') is True, 'actual CUA operations missing/failed'
        ops = records[0]['physical_operations']
        assert type(ops) is list and 0 < len(ops) <= 32
        return self.new('raw-cua.jsonl', raw=original), ops

    def checkpoints(self, item, command_index, lower, upper):
        raw = (self.c.output/'metal/ue.log').read_bytes(); rows = []
        for index, expected in enumerate(item['checkpoint_commands']):
            if expected != command_index: continue
            stage = item['stages'][index]
            found = []
            offset = lower
            for line in raw[lower:upper].splitlines(keepends=True):
                if item['kind'] in ('probe','history_write_rejected','final'):
                    if b'EW_I13_READBACK ' in line:
                        data = json.loads(line.split(b'EW_I13_READBACK ',1)[1])
                        if data['action_id'] == item['action_id'] and data['stage'] == stage:
                            found.append((offset, offset+len(line), data['event_serial'], data))
                else:
                    marker = b'LogExit: Preparing to exit.' if item['kind'] == 'exit' else (
                        'Universe world %s observed tick %d, revision %d'%(
                            self.c.binding['world_id'], item['observation_heads'][index]['tick'],
                            item['observation_heads'][index]['revision'])).encode()
                    if marker in line: found.append((offset, offset+len(line), None, None))
                offset += len(line)
            assert len(found) == 1, 'missing/ambiguous actual checkpoint '+item['action_id']+'/'+stage
            lo, hi, serial, data = found[0]
            m, now = self.amap()
            rows.append(dict(stage=stage, log_start=lo, log_end=hi, read_monotonic=now,
                             map=m, command_index=command_index, event_serial=serial))
            if item['kind'] == 'probe': self.viewport = data['state']
        return rows

    def close_group(self):
        g = self.group
        if g is None: return
        after, _ = self.amap()
        cua = self.new('cua-group.json', dict(format=probe.CUA_FORMAT_V2, binding=self.c.binding,
            action_id=g['item']['action_id'], clock=self.c.clock_binding, calls=g['calls']))
        images = []
        if g['item']['kind'] == 'probe' and self.capture_ref:
            images = [dict(capture_id='p1.probe/png_and_guard', stage='png_and_guard', capture_ref=self.capture_ref)]
        receipt = dict(format=probe.FORMAT_V2, action_id=g['item']['action_id'], binding=self.c.binding,
            trusted_head=g['item']['trusted_head'], selected_observation=g['item']['selected_observation'],
            clock=self.c.clock_binding, started_monotonic=g['start'], completed_monotonic=time.monotonic(),
            before=g['before'], after=after, log=dict(self.logpin(g['log_before']), ref=None),
            trace_range=[g['frame_before'], len(self.c._trace())], cua=cua,
            checkpoints=g['checkpoints'], image_checks=images)
        # Bind the full live log only after actual wait/writer completion. Prefix
        # and range are recorded now; no mutable full-log ref is published early.
        self.receipts.append(receipt)
        self.group = None

    def step(self, request):
        assert set(request) == {'command'}
        op = request['command']
        if op == 'start':
            assert 900-self.campaign_offset-(time.monotonic()-self.started)>=510, 'parent Metal reserve insufficient'
            assert not self.c.phases
            self.startup_before, self.startup_start = self.amap()
            return self.c.start_metal()
        if op == 'ready':
            window_raw, window_ops = self.raw_cua('I19BIND', self.inputs['transcript_start_offset'])
            self.new('window-preparation.json',dict(raw_tool_ref=window_raw,physical_operations=window_ops,
                scope='startup window binding/focus/fullscreen only; not a business command',
                monotonic=time.monotonic(),charged_to='startup60s/Metal420s/global900s'))
            result = self.c.register_metal_ready()
            item = self.manifest['items'][0]
            self.group = dict(item=item, before=self.startup_before, start=self.startup_start,
                log_before=0, frame_before=0, calls=[], checkpoints=self.checkpoints(item,-1,0,(self.c.output/'metal/ue.log').stat().st_size))
            self.close_group(); return result
        if op == 'begin':
            assert self.active is None and self.next_step < len(self.steps)
            item, index, command = self.steps[self.next_step]
            if self.group is None:
                before, now = self.amap()
                self.group = dict(item=item, before=before, start=now, log_before=(self.c.output/'metal/ue.log').stat().st_size,
                                  frame_before=len(self.c._trace()), calls=[], checkpoints=[])
            assert self.group['item'] == item
            token = self.c.begin_action(item['action_id'], command['step_id'], 20)
            offset = Path(self.inputs['session_transcript']).stat().st_size
            self.active = dict(token=token, offset=offset, item=item, index=index, command=command)
            actual = command['text']
            if actual.startswith('native Shot'):
                s = self.viewport
                assert s['renderer']=='Metal' and s['hdr'] is False and s['quit_guard_ready'] and s['preflush']
                self.shot = capture.prepare_native_shot(target_path=str(OUT/'images/projection.png'),
                    expected_binding=self.c.binding, trusted_head=self.c.trusted_head,
                    selected_observation=self.c.selected_observation, observation_ref=self.c.observation_ref,
                    before_map_ref=token['before']['map_ref'], before_map_monotonic=token['before']['monotonic'],
                    log_path=token['before']['log']['path'], log_offset=token['before']['log']['before_offset'],
                    clock=self.c.clock_binding, expected_width=s['viewport_width'], expected_height=s['viewport_height'])
                self.shot_call_start=time.monotonic()
                actual = self.shot['command']
            if item['kind'] == 'exit':
                self.before_exit = time.monotonic(); self.c.request_quit('fixed slice complete; normal CUA quit')
            return dict(step_id=command['step_id'], text=actual, deadline=token['deadline_monotonic'],
                        pid=self.c.process.pid, remaining=self.c.now()['remaining_seconds'])
        if op == 'end':
            a = self.active; assert a is not None
            token, command, item = a['token'], a['command'], a['item']
            raw, operations = self.raw_cua('I19STEP:'+command['step_id'], a['offset'])
            result = self.c.end_action(token['seq'], raw)
            assert result['status']=='recorded', 'actual whole step exceeded20s'
            lo, hi = token['before']['log']['before_offset'], result['after']['log']['before_offset']
            self.group['calls'].append(dict(step_id=command['step_id'], command=command['text'],
                started_monotonic=token['issued_monotonic'], completed_monotonic=result['completed_monotonic'],
                raw_tool_ref=raw, log_before_offset=lo, log_after_offset=hi,
                physical_operation_count=len(operations), physical_operations=operations))
            self.group['checkpoints'].extend(self.checkpoints(item,a['index'],lo,hi))
            if command['text'].startswith('native Shot'):
                obs = lc.json_ref(self.shot['preparation_ref'])
                cmd = self.new('shot-command.json', dict(format=capture.FORMAT, phase='cua-command',
                    preparation_ref=self.shot['preparation_ref'], command=self.shot['command'],
                    clock_id=self.c.clock_binding['id'], binding=self.c.binding, trusted_head=self.c.trusted_head,
                    selected_observation=self.c.selected_observation, observation_ref=self.c.observation_ref,
                    cua_result_ref=raw, start_monotonic=self.shot_call_start, end_monotonic=result['completed_monotonic'],
                    log=dict(obs['log'],after_offset=hi)))
                collected = capture.collect_native_shot(self.shot['preparation_ref'],cmd,
                    expected_binding=self.c.binding,expected_trusted_head=self.c.trusted_head,
                    expected_selected_observation=self.c.selected_observation,expected_observation_ref=self.c.observation_ref,
                    expected_clock=self.c.clock_binding,receipt_path=str(OUT/'images/capture-collected.json'))
                self.capture_ref = ref(OUT/'images/capture-collected.json'); self.last_capture_map=self.amap()
                self.png_fingerprint=cap.file_fingerprint(str(OUT/'images/projection.png'))
            if item['kind']=='history': self.c.refresh_observation()
            self.next_step+=1; self.active=None
            if a['index']==len(item['commands'])-1: self.close_group()
            if item['kind']=='exit':
                self.exit_ref=self.new('before-exit.json',dict(format=capture.FORMAT,phase='actual-before-exit',
                    binding=self.c.binding,clock_id=self.c.clock_binding['id'],before_exit_monotonic=self.before_exit,
                    exit_evidence_ref=raw))
                return self.finish()
            return dict(step_complete=command['step_id'],next_step=self.steps[self.next_step][2]['step_id'])
        if op=='abort':
            return self.c.abort('explicit root stop; no automatic retry')
        raise ValueError('fixed driver command rejected')

    def finish(self):
        metal_ref=self.c.finish_metal()
        p=self.c.phases['metal']
        assert p['normal'] and p['evidence_frozen'], 'Metal actual wait/quiet/freeze failed'
        log_ref=ref(self.c.output/'metal/ue.log')
        for receipt in self.receipts:
            receipt['log']['ref']=log_ref
            self.new('logical-receipt.json',receipt)
        context={k:lc.json_ref(self.prepared['pins_ref'])[k] for k in ('principal','trust_anchor','expected_build','expected_options')}
        consistency=probe.validate_probe_evidence_v2(self.receipts,p['trace_refs'],expected_binding=self.c.binding,
            expected_context=context,expected_before_map_ref=self.prepared['before_map_ref'],expected_after_map_ref=self.amap()[0])
        self.new('slice-consistency.json',consistency)
        shot=lc.json_ref(self.shot['preparation_ref'])
        capture_check=capture.verify_native_shot(self.capture_ref,expected_binding=self.c.binding,
            expected_trusted_head=shot['trusted_head'],expected_selected_observation=shot['selected_observation'],
            expected_observation_ref=shot['observation_ref'],expected_clock=self.c.clock_binding,
            after_map_ref=self.last_capture_map[0],after_map_monotonic=self.last_capture_map[1],
            before_exit_monotonic=self.before_exit,before_exit_ref=self.exit_ref)
        self.new('capture-check.json',capture_check)
        frames=self.c._trace(); indices=[i for i,f in enumerate(frames) if f['request']['operation']=='observe']
        assert len(indices)==2
        source=dict(pins_ref=self.prepared['pins_ref'],trace_refs=p['trace_refs'],observe_frame_indices=indices,
                    trace_identity={k:self.c.binding[k] for k in ('host_pid','worker_pid','generation')})
        public=[r['path'] for r in p['trace_refs']]+[self.prepared['pins_ref']['path']]
        replay=native_replay.prepare_replay_cases(run_id=self.prepared['run_id'],product_source_sha=self.prepared['product_source_sha'],
            tool_source_sha=self.prepared['tool_source_sha'],selections=[dict(case_id='i19-'+name,pins_ref=source['pins_ref'],
                trace_refs=source['trace_refs'],trace_frame_index=i) for name,i in zip(('current','history'),indices)],
            allowed_sources=[source],public_paths=public,output_dir=str(OUT/'replay-new'))
        self.c.freeze_native_manifest(replay['manifest_ref'],replay['manifest_ref']['sha256'])
        assert 900-self.campaign_offset-(time.monotonic()-self.started)>=270, 'parent Native reserve insufficient; partial/no new window'
        self.c.start_native(); native_ref=self.c.wait_native(timeout=180)
        resource=self.c.seal()
        native=lc.json_ref(native_ref)
        assert native['normal'] and native['evidence_frozen'] and not native['errors'] and not native['forced_cleanup'], 'Native result was not accepted'
        assert lc.json_ref(resource)['decision']=='within_budget', 'controller resource gate failed'
        self.finished=True
        return dict(metal_ref=metal_ref,native_ref=ref(self.c.output/'native-execution.json'),resource_ref=resource,
                    png_ref=ref(OUT/'images/projection.png'),consistency=consistency['status'],all_runtime_closed=True)

    def after(self, error):
        if not self.c.closed: self.c.abort(str(error or 'driver ended before fixed scope completed'))
        after=metadata.external_snapshot(); after_ref=save(OUT/'prep/external-after.json',after)
        changes=[];changed_bytes=0
        for name,before in self.external_before['roots'].items():
            current=after['roots'][name]
            for relative in sorted(set(before['entries'])|set(current['entries'])):
                a,b=before['entries'].get(relative),current['entries'].get(relative)
                if a!=b:
                    changes.append(dict(root=name,relative=relative,before=a,after=b))
                    if b and b['kind']!='directory':changed_bytes+=b['bytes']
        diff_ref=save(OUT/'prep/external-diff.json',dict(before_ref=self.external_before_ref,after_ref=after_ref,
            changes=changes,conservative_current_changed_file_bytes=changed_bytes))
        amap=common.authority_map(Path(self.prepared['authority_root'])); map_ref=save(OUT/'prep/authority-after.json',amap)
        final=lc.observe_once(OUT/'prep/final-processes.ps')
        known={}
        for name,p in self.c.phases.items():
            if not p.get('skipped'):
                for row in self.c._phase_owned(name):known[lc.process_key(row)]=row
        quiet=not lc.classify_processes(final['processes'],list(known.values()),self.prepared['binary_pins']['ue']['path'])
        for p in self.c.phases.values():
            if p.get('pid'):
                quiet=quiet and not any(cap.sponsored_trace_server(row,p['pid'],self.prepared['ue_root']) for row in final['processes'])
        errors=[]
        for name in self.c.phases:
            try:
                if name=='metal' and not self.c.phases[name].get('skipped'):self.c._verify_metal_frozen_files()
                if name=='native':self.c._verify_native_frozen_files()
            except (ValueError,OSError) as e:errors.append(str(e))
        if hasattr(self,'png_fingerprint'):
            try:assert cap.file_fingerprint(str(OUT/'images/projection.png'))==self.png_fingerprint
            except (ValueError,OSError,AssertionError) as e:errors.append('PNG changed after collection: '+str(e))
        if not self.finished:
            self.new('incomplete-receipts.json',dict(scope='provisional/unaccepted; no frozen log ref',receipts=self.receipts))
        size=0;traversal_errors=[]
        for parent,dirs,files in os.walk(ROOT,followlinks=False,onerror=lambda e:traversal_errors.append(str(e))):
            for name in dirs+files:
                path=Path(parent)/name
                try:
                    info=path.lstat()
                    if path.is_symlink():traversal_errors.append('output symlink: '+str(path))
                    elif name in files:
                        import stat
                        if not stat.S_ISREG(info.st_mode):traversal_errors.append('nonregular output: '+str(path))
                        else:size+=info.st_size
                except OSError as e:traversal_errors.append(str(e))
        elapsed=time.monotonic()-self.started;total=size+changed_bytes+65536
        campaign_elapsed=self.campaign_offset+elapsed
        passed=(self.finished and error is None and quiet and not errors and not traversal_errors and
            amap['files']==self.authority_before['files'] and elapsed<=900 and campaign_elapsed<=900 and total<=2*1024**3 and
            not any(x['errors'] for x in after['roots'].values()))
        receipt=dict(format='universe-i19-resource-review.v1',run_id=self.prepared['run_id'],
            elapsed_seconds=elapsed,campaign_elapsed_seconds=campaign_elapsed,parent_deadline_utc="2026-11-09T09:08:10.799685+00:00",
            campaign_observer_gate="fail/inconclusive; attempt1 gap retained",storage_bytes=total,root_bytes_measured=size,
            conservative_external_changed_file_bytes=changed_bytes,seal_allowance_bytes=65536,
            all_processes_quiet=quiet,authority_unchanged=amap['files']==self.authority_before['files'],
            frozen_output_errors=errors,traversal_errors=traversal_errors,error=str(error) if error else None,all_fixed_steps_completed=self.finished,
            external_diff_ref=diff_ref,authority_after_ref=map_ref,final_processes_ref=final['raw_ref'],
            decision='pass_requires_independent_review' if passed else 'fail',g_b2_granted=False,
            scope='whole inherited output root and six declared external metadata domains; not OS-wide I/O audit')
        self.guard_stop.set()
        return save(OUT/'prep/resource-review.json',receipt)


def main(expected_inputs_sha):
    path=OUT/'prep/execution-inputs.json'
    assert ref(path)['sha256']==expected_inputs_sha
    inputs=json.loads(path.read_bytes());assert ref(__file__)==inputs['driver_ref']
    r=Run(inputs);error=None
    try:
        reply(dict(driver_ready=True,controller_pid=os.getpid(),clock=r.c.clock_binding,ue_started=False))
        for line in common.controller_lines(sys.stdin.fileno(), deadline=r.c.started+max(0,840-r.campaign_offset)):
            if line is None:continue
            request=json.loads(line,object_pairs_hook=common.unique_pairs)
            result=r.step(request);reply(dict(status='reply',result=result))
            if r.c.closed:break
    except BaseException as e:
        error=e;reply(dict(status='failure',error=str(e)))
    finally:
        result=r.after(error);reply(dict(resource_review_ref=result,normal=r.finished and error is None))
    return 0 if r.finished and error is None else 2


if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('usage: driver.py EXPECTED_INPUTS_SHA')
    raise SystemExit(main(sys.argv[1]))
