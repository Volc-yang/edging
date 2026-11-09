"""I15 readonly capability probe. No UI, worker, solver, process launch or G-B2 grant.

Shared low-level I13/I14 readers are reused without changing their contracts. This
manifest/evidence path is independent of standard initialize/existing session acceptance.
"""
from copy import deepcopy
from . import actions as a

FORMAT = 'universe-i15-probe-actions.v1'
READBACK_FORMAT = 'universe-i15-probe-readback.v1'
# Explicit I19 slice. The old full-matrix entrypoints and caps stay unchanged.
FORMAT_V2 = 'universe-i19-probe-actions.v2'
CUA_FORMAT_V2 = 'universe-i19-probe-cua.v2'
STEP_LIMIT_V2 = 20
Invalid = a.Invalid
_keys, require, _head, _binding = a._keys, a.require, a._head, a._binding
_integer, _seconds, _utc = a._integer, a._seconds, a._utc
_map, reference, _json = a._map, a.reference, a._json
_log, _check_frames = a._log, a._check_frames
READONLY = a.READONLY
DIAGNOSTIC_KINDS = a.DIAGNOSTIC_KINDS
RECEIPT_FIELDS = a.RECEIPT_FIELDS


def _step(text):
    return {'text':text,'max_seconds':10 if 'chord' in text else 2}


def probe_manifest():
    old = {x['action_id']:x for x in a.manifest_v2()['items']}
    items=[]
    pairs=[('s2.recover','p1.startup',60),('s2.probe','p1.probe',20),
           ('s1.camera','p1.camera',35),('s1.visibility','p1.visibility',35),
           ('s1.framerate','p1.framerate',20),('s1.pause','p1.pause',20),
           ('s1.history_select','p1.history',10),('s1.history_write_rejected','p1.history_write_rejected',25),
           ('s1.held_input','p1.held_input',30),('s2.final','p1.final',15),('s2.exit','p1.exit',40)]
    for original,name,cap in pairs:
        item=deepcopy(old[original]);item['action_id']=name;item['session']='existing';item['max_seconds']=cap
        item['commands']=[_step(c['text'].replace(original,name)) for c in item['commands']]
        item['image_stages']=item['stages'][:] if 'image_checks' in item['required_evidence'] else []
        if name=='p1.probe':
            item['commands']=[_step('UniverseDiagArm p1.probe'),_step('UniverseDiagReadback p1.probe png_and_guard'),
                              _step('native Shot via C prepare p1.probe/png_and_guard'),_step('UniverseDiagDisarm')]
            item['checkpoint_commands']=[1]
        if name=='p1.framerate':
            item['commands'][1]['text']='t.MaxFPS 30 (or 60 only if original=30)'
        if name=='p1.held_input':
            item['commands'].insert(2,_step('native Shot via C prepare p1.held_input/released'))
            item['image_stages']=['released']
        if item['image_stages'] and 'image_checks' not in item['required_evidence']:
            item['required_evidence'].append('image_checks')
        for index,command in enumerate(item['commands']):command['step_id']=name+'/%02d'%index
        remaining=cap-sum(c['max_seconds'] for c in item['commands'])
        require(remaining>0,'probe passive allowance')
        item['passive_costs']={key:remaining/3 for key in ('maps_seconds','marker_seconds','image_restore_seconds')}
        items.append(item)
    require(sum(len(x['commands']) for x in items)==48,'fixed probe actual call count')
    return {'format':FORMAT,'scope':'existing-readonly-capabilities','session':'existing','items':items,
            'request_count':4,'expected_operations':['status','observe','observe','observe'],
            'image_count':8,'call_count':48,'interaction_seconds':sum(x['max_seconds'] for x in items if x['phase']=='interaction'),
            'interaction_limit_seconds':300,'optional_actions':[],
            'cost_status':'proposal_not_measured','standard_pair':False,'g_b2_granted':False}


def _probe_item(action_id):
    found=[x for x in probe_manifest()['items'] if x['action_id']==action_id]
    require(len(found)==1,'unknown probe action')
    return found[0]


def probe_manifest_v2():
    """One fixed readonly slice; these costs are proposals, never timing evidence."""
    old = {item['action_id']: item for item in probe_manifest()['items']}
    items = []
    for action_id, cap in (('p1.startup', 60), ('p1.probe', 90), ('p1.history', 25),
                           ('p1.history_write_rejected', 110), ('p1.final', 70), ('p1.exit', 40)):
        item = deepcopy(old[action_id])
        item['max_seconds'] = cap
        for command in item['commands']:
            command['max_seconds'] = STEP_LIMIT_V2
        if action_id in ('p1.final', 'p1.exit'):
            item['selected_observation'] = deepcopy(a.H1)
        remaining = cap - sum(command['max_seconds'] for command in item['commands'])
        item['passive_costs'] = {name: remaining / 3 for name in
                                ('maps_seconds', 'marker_seconds', 'image_restore_seconds')}
        items.append(item)
    return {'format': FORMAT_V2, 'scope': 'existing-readonly-history-input-slice', 'session': 'existing',
            'items': items, 'request_count': 3, 'expected_operations': ['status', 'observe', 'observe'],
            'image_count': 1, 'logical_step_count': 14, 'new_observe_response_count': 2,
            'physical_operation_count': 'recorded_per_actual_call', 'step_limit_seconds': STEP_LIMIT_V2,
            'interaction_seconds': 295, 'interaction_limit_seconds': 300,
            'deferred_actions': ['camera', 'visibility', 'framerate', 'pause', 'held_input'],
            'optional_actions': [], 'cost_status': 'proposal_not_measured',
            'standard_pair': False, 'g_b2_granted': False}


def _probe_item_v2(action_id):
    found = [item for item in probe_manifest_v2()['items'] if item['action_id'] == action_id]
    require(len(found) == 1, 'unknown fixed I19 slice action')
    return found[0]


def _diagnostic(raw,event,item,receipt):
    line=raw[event['log_start']:event['log_end']];marker=b'EW_I13_READBACK '
    require(line.count(marker)==1 and line.endswith(b'\n'),'actual complete probe readback required')
    value=_json(line.split(marker,1)[1].strip())
    _keys(value,{'format','binding','action_id','stage','trusted_head','selected_observation','state','event_serial','origin'},'probe marker')
    require(value['format']==READBACK_FORMAT and value['action_id']==item['action_id'] and value['stage']==event['stage'],'probe marker version/action/stage')
    _binding(value['binding'],receipt['binding']);_head(value['trusted_head']);_head(value['selected_observation'])
    require(value['trusted_head']==item['trusted_head'] and _integer(value['event_serial'],1) and value['event_serial']==event['event_serial'],'probe marker actual identity/order')
    return value


def _states(item,diagnostics):
    if item['kind']=='probe':
        state=diagnostics[0]['state']
        _keys(state,{'quit_guard_ready','preflush','viewport_width','viewport_height','renderer','hdr'},'actual viewport state')
        require(state['quit_guard_ready'] is True and state['preflush'] is True and
                _integer(state['viewport_width'],1) and _integer(state['viewport_height'],1) and
                state['viewport_width']<=16384 and state['viewport_height']<=16384 and
                state['renderer']=='Metal' and state['hdr'] is False,'unknown/non-Metal/HDR viewport cannot satisfy SDR probe')
    elif item['kind']=='camera':a._camera_v2(diagnostics)
    elif item['kind']=='framerate':
        states=[x['state'] for x in diagnostics]
        for state in states:
            _keys(state,{'max_fps'},'probe FPS');require(_seconds(state['max_fps']),'finite actual FPS')
        expected=60 if states[0]['max_fps']==30 else 30
        require(states[1]['max_fps']==expected and states[2]==states[0],'fixed actual-original FPS branch/restore')
    else:a._states(item,diagnostics)
    for value in diagnostics:
        selected=a.H1 if item['kind']=='history_write_rejected' or (item['kind']=='held_input' and value['stage']=='held_history') else item['selected_observation']
        require(value['selected_observation']==selected,'probe selected observation')


def _validate_probe_receipt(receipt, *, expected_binding, frames, expected_context,
                            item, receipt_format, cua_format, step_limit, physical_details=False):
    _keys(receipt, RECEIPT_FIELDS, 'v2 receipt')
    require(receipt['format'] == receipt_format, 'v2 receipt format')
    _binding(receipt['binding'], expected_binding)
    require(receipt['action_id'] == item['action_id'], 'fixed slice action identity')
    require(item['session'] == expected_binding['session'], 'v2 action/session')
    _head(receipt['trusted_head']); _head(receipt['selected_observation'])
    require(receipt['trusted_head'] == item['trusted_head'] and receipt['selected_observation'] == item['selected_observation'],
            'v2 distinct trusted/selected head')
    _keys(receipt['clock'], {'id', 'anchor_monotonic', 'anchor_utc'}, 'v2 clock')
    require(type(receipt['clock']['id']) is str and receipt['clock']['id'] and
            _seconds(receipt['clock']['anchor_monotonic']) and _utc(receipt['clock']['anchor_utc']), 'v2 controller clock')
    start, end = receipt['started_monotonic'], receipt['completed_monotonic']
    require(_seconds(start) and _seconds(end) and start <= end and end - start <= item['max_seconds'], 'v2 action cap')
    before = _map(receipt['before'], expected_binding['authority_root'])
    after = _map(receipt['after'], expected_binding['authority_root'])
    if item['kind'] in READONLY or item['kind'] in ('probe', 'native', 'final', 'exit', 'recover'):
        require(before == after, 'v2 readonly changed')
    first, last = receipt['trace_range']
    require(_integer(first) and _integer(last) and first <= last <= len(frames), 'v2 frame range')
    _check_frames(item, frames[first:last], expected_binding, expected_context)
    raw, pin = _log(receipt)
    cua = _json(reference(receipt['cua']))
    _keys(cua, {'format', 'binding', 'action_id', 'clock', 'calls'}, 'v2 CUA')
    require(cua['format'] == cua_format and cua['action_id'] == item['action_id'] and
            cua['clock'] == receipt['clock'], 'v2 CUA binding')
    _binding(cua['binding'], expected_binding)
    require(type(cua['calls']) is list and len(cua['calls']) == len(item['commands']), 'all v2 queries/calls required')
    call_end, log_end = start, pin['before_offset']
    for call, command in zip(cua['calls'], item['commands']):
        fields = {'command', 'started_monotonic', 'completed_monotonic', 'raw_tool_ref',
                  'log_before_offset', 'log_after_offset', 'step_id'}
        if physical_details:
            fields |= {'physical_operations', 'physical_operation_count'}
        _keys(call, fields, 'v2 CUA call')
        call_start, call_stop = call['started_monotonic'], call['completed_monotonic']
        require(call['step_id']==command['step_id'] and call['command'] == command['text'] and _seconds(call_start) and _seconds(call_stop) and
                call_end <= call_start <= call_stop <= end and call_stop-call_start <= min(step_limit, command['max_seconds']), 'v2 call order/deadline')
        if physical_details:
            operations = call['physical_operations']
            require(type(operations) is list and 1 <= len(operations) <= 32 and
                    type(call['physical_operation_count']) is int and
                    call['physical_operation_count'] == len(operations), 'actual physical operation list/count required')
            for operation in operations:
                _keys(operation, {'operation', 'arguments'}, 'physical operation')
                require(type(operation['operation']) is str and 0 < len(operation['operation']) <= 128 and
                        type(operation['arguments']) is dict, 'actual operation and argument object required')
        require(_integer(call['log_before_offset']) and _integer(call['log_after_offset']) and
                log_end <= call['log_before_offset'] <= call['log_after_offset'] <= pin['after_offset'], 'v2 call log brackets')
        require(reference(call['raw_tool_ref']), 'actual raw CUA call evidence required')
        call_end, log_end = call_stop, call['log_after_offset']
    events = receipt['checkpoints']
    require(type(events) is list and [e.get('stage') for e in events] == item['stages'], 'v2 complete stage order')
    last_read, last_offset, previous_serial, diagnostics = start, pin['before_offset'], 0, []
    for index, event in enumerate(events):
        _keys(event, {'stage', 'log_start', 'log_end', 'read_monotonic', 'map', 'command_index', 'event_serial'}, 'v2 checkpoint')
        require(_integer(event['log_start']) and _integer(event['log_end']) and
                last_offset <= event['log_start'] < event['log_end'] <= pin['after_offset'], 'v2 event raw log order')
        read_time = event['read_monotonic']
        require(_seconds(read_time) and last_read <= read_time <= end, 'v2 controller read order')
        require(type(event['command_index']) is int and event['command_index'] == item['checkpoint_commands'][index],
                'v2 event/call association')
        call_index = event['command_index']
        if call_index >= 0:
            call = cua['calls'][call_index]
            require(call['log_before_offset'] <= event['log_start'] < event['log_end'] <= call['log_after_offset'] and
                    read_time >= call['started_monotonic'], 'v2 event outside actual input/query bracket')
            # Long chord events may occur before call return. No UE/controller clock subtraction.
            if call_index+1 < len(cua['calls']):
                require(read_time <= cua['calls'][call_index+1]['started_monotonic'], 'required readback omitted before next call')
        files = _map(event['map'], expected_binding['authority_root'])
        if item['kind'] in READONLY:
            require(files == before, 'v2 readonly subaction changed')
        if item['kind'] in DIAGNOSTIC_KINDS:
            value = _diagnostic(raw, event, item, receipt)
            require(value['origin'] == item['checkpoint_origins'][index] and value['event_serial'] > previous_serial,
                    'actual event origin/serial order')
            previous_serial = value['event_serial']; diagnostics.append(value)
        else:
            require(event['event_serial'] is None, 'ordinary log line has no diagnostic serial')
            line = raw[event['log_start']:event['log_end']]
            if item['kind'] == 'native':
                name = 'ProtocolIds' if item['action_id'] == 's1.native_ids' else 'StandaloneAssetAudit'
                marker = ('Test Completed. Result={Success} Name={' + name + '} Path={edgeWorld.UniverseHost.'+name+'}').encode()
            elif item['kind'] == 'exit':
                marker = b'LogExit: Preparing to exit.'
            else:
                head = item['observation_heads'][index]
                marker = ('Universe world %s observed tick %d, revision %d' %
                          (expected_binding['world_id'],head['tick'],head['revision'])).encode()
            require(marker in line, 'fresh actual v2 completion log missing')
        last_read, last_offset = read_time, event['log_end']
    if diagnostics:
        _states(item,diagnostics)
    paths = [receipt['before']['path'], receipt['after']['path']] + [e['map']['path'] for e in events]
    require(len(paths) == len(set(paths)), 'v2 fresh map capture required')
    images = receipt['image_checks']
    require(type(images) is list, 'v2 image checks')
    expected_stages = item['image_stages']
    require([x.get('stage') for x in images] == expected_stages, 'v2 every image stage consumed exactly once')
    for image in images:
        _keys(image, {'capture_id', 'stage', 'capture_ref'}, 'v2 stage capture')
        require(image['capture_id'] == item['action_id']+'/'+image['stage'], 'v2 globally stable capture_id')
        reference(image['capture_ref'])  # V invokes C; no success inferred from arbitrary bytes.
    result = {'action_id': item['action_id'], 'kind': item['kind'], 'trace_range': [first,last],
            'event_serials': [d['event_serial'] for d in diagnostics],
            'status': 'consistent_requires_R_and_independent_review', 'g_b2_granted': False}
    if physical_details:
        result.update(logical_step_count=len(cua['calls']),
                      physical_operation_count=sum(call['physical_operation_count'] for call in cua['calls']))
    return result


@a._boundary
def validate_probe_receipt(receipt, *, expected_binding, frames, expected_context):
    """Old full probe; its 2/10-second per-call contract is unchanged."""
    return _validate_probe_receipt(receipt, expected_binding=expected_binding, frames=frames,
                                  expected_context=expected_context, item=_probe_item(receipt['action_id']),
                                  receipt_format=FORMAT, cua_format='universe-i15-probe-cua.v1', step_limit=10)


@a._boundary
def validate_probe_receipt_v2(receipt, *, expected_binding, frames, expected_context):
    """I19 slice only: full controller bracket includes CUA round trips and maps."""
    return _validate_probe_receipt(receipt, expected_binding=expected_binding, frames=frames,
                                  expected_context=expected_context, item=_probe_item_v2(receipt['action_id']),
                                  receipt_format=FORMAT_V2, cua_format=CUA_FORMAT_V2,
                                  step_limit=STEP_LIMIT_V2, physical_details=True)



def _validate_probe_evidence(receipts,trace_refs,*,expected_binding,expected_context,
                             expected_before_map_ref,expected_after_map_ref,manifest,validator):
    """Consistency only; C/R authenticates actual UI, source, captures, waits and full resource ledger."""
    require(expected_binding['session']=='existing','probe never impersonates initialize')
    frames=a.load_trace(trace_refs,expected_binding=expected_binding)
    require([f['request']['operation'] for f in frames]==manifest['expected_operations'],'probe forbids every write/retry/extra request')
    _keys(expected_context,{'principal','trust_anchor','expected_build','expected_options'},'independent public context')
    require(type(expected_context['principal']) is str and expected_context['principal'] and
            all(type(expected_context[k]) is str and a.SHA.fullmatch(expected_context[k]) for k in ('trust_anchor','expected_build','expected_options')),'public context pins')
    baseline=_map(expected_before_map_ref,expected_binding['authority_root'])
    require(baseline==_map(expected_after_map_ref,expected_binding['authority_root']),'inherited authority changed during probe')
    require(type(receipts) is list and [r['action_id'] for r in receipts]==[x['action_id'] for x in manifest['items']],'complete exact probe action order')
    cursor,serial,last_time,clock,paths,results=0,0,-1,None,set(),[]
    for receipt in receipts:
        require(receipt['trace_range'][0]==cursor and receipt['started_monotonic']>=last_time,'probe action time/frame gap or overlap')
        if clock is None:clock=receipt['clock']
        require(clock==receipt['clock'],'one controller clock')
        for ref in [receipt['before'],receipt['after']]+[e['map'] for e in receipt['checkpoints']]:
            require(ref['path'] not in paths and _map(ref,expected_binding['authority_root'])==baseline,'probe map reused or inherited bytes changed')
            paths.add(ref['path'])
        result=validator(receipt,expected_binding=expected_binding,frames=frames,expected_context=expected_context)
        for value in result['event_serials']:
            require(value==serial+1,'missing/replayed native diagnostic event');serial=value
        cursor,last_time=receipt['trace_range'][1],receipt['completed_monotonic'];results.append(result)
    require(cursor==manifest['request_count'],'unclaimed probe trace frames')
    return {'status':'checks_complete_requires_independent_review','checks':results,'request_count':manifest['request_count'],
            'standard_pair':False,'g_b2_granted':False,'runtime_authenticity_verified':False}


@a._boundary
def validate_probe_evidence(receipts,trace_refs,*,expected_binding,expected_context,
                            expected_before_map_ref,expected_after_map_ref):
    """Old full probe; not fulfilled by the I19 subset."""
    return _validate_probe_evidence(receipts, trace_refs, expected_binding=expected_binding,
                                    expected_context=expected_context,
                                    expected_before_map_ref=expected_before_map_ref,
                                    expected_after_map_ref=expected_after_map_ref,
                                    manifest=probe_manifest(), validator=validate_probe_receipt)


@a._boundary
def validate_probe_evidence_v2(receipts,trace_refs,*,expected_binding,expected_context,
                               expected_before_map_ref,expected_after_map_ref):
    """Finite slice consistency; full matrix/Metal/PNG/Native acceptance stays external."""
    manifest = probe_manifest_v2()
    result = _validate_probe_evidence(receipts, trace_refs, expected_binding=expected_binding,
                                      expected_context=expected_context,
                                      expected_before_map_ref=expected_before_map_ref,
                                      expected_after_map_ref=expected_after_map_ref,
                                      manifest=manifest, validator=validate_probe_receipt_v2)
    interaction = receipts[1:-1]
    elapsed = interaction[-1]['completed_monotonic'] - interaction[0]['started_monotonic']
    require(elapsed <= manifest['interaction_limit_seconds'], 'slice interaction wall interval exceeds300s')
    require(sum(check['logical_step_count'] for check in result['checks']) == manifest['logical_step_count'],
            'all fourteen logical steps required')
    result.update(scope=manifest['scope'], logical_step_count=manifest['logical_step_count'],
                  physical_operation_count=sum(check['physical_operation_count'] for check in result['checks']),
                  new_observe_response_count=2, image_count=1, interaction_wall_seconds=elapsed,
                  deferred_actions=manifest['deferred_actions'])
    return result


def probe_schema():
    value=a.schema_v2();value['title']=FORMAT;value['properties']['format']={'const':FORMAT}
    value['properties']['action_id']={'enum':[x['action_id'] for x in probe_manifest()['items']]}
    readback=value['$defs']['readback'];readback['properties']['format']={'const':READBACK_FORMAT}
    readback['allOf'][0]['if']['properties']['action_id']['const']='p1.history_write_rejected'
    call=value['$defs']['cua']['properties']['calls']['items'];call['properties']['step_id']={'type':'string','minLength':1};call['required']=sorted(call['properties'])
    value['$defs']['cua']['properties']['format']={'const':'universe-i15-probe-cua.v1'}
    return value


def probe_schema_v2():
    """Distinct slice receipt schema; UE producer readbacks retain their original version."""
    value = probe_schema()
    value['title'] = FORMAT_V2
    value['properties']['format'] = {'const': FORMAT_V2}
    value['properties']['action_id'] = {'enum': [item['action_id'] for item in probe_manifest_v2()['items']]}
    cua = value['$defs']['cua']
    cua['properties']['format'] = {'const': CUA_FORMAT_V2}
    call = cua['properties']['calls']['items']
    call['properties'].update(
        physical_operation_count={'type': 'integer', 'minimum': 1, 'maximum': 32},
        physical_operations={'type': 'array', 'minItems': 1, 'maxItems': 32, 'items': {
            'type': 'object', 'additionalProperties': False, 'required': ['operation', 'arguments'],
            'properties': {'operation': {'type': 'string', 'minLength': 1, 'maxLength': 128},
                           'arguments': {'type': 'object'}}}})
    call['required'] = sorted(call['properties'])
    return value
