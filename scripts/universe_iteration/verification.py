"""I14 public evidence composition; never authorizes execution or grants G-B2.

A/B/C are one-way dependencies. Root supplies fixed reviewed authority/trace
parser CODE, not JSON-selected callbacks or precomputed `passed` declarations.
Public proof checks here are intentionally narrower than UE FValidator parity;
remaining existing-contract checks are named inconclusive, never fabricated.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from . import actions, capture, lifecycle

FORMAT = 'universe-i14-evidence.v1'
POLICY = 'universe-i14-verification-policy.v1'
PREFIX = b'edgeworld.universe.authority\0v0.2\0'
SESSIONS = ('initialize', 'existing')
PUBLIC_PROOF_GAPS = (
    'public Observe FValidator::Record typed body value constraints are not independently complete',
    'public Observe FValidator::Static selected geometry/options/transform constraints are not independently complete',
    'public Observe FValidator::Transition selected-proof semantic parity beyond archive inspection is not independently complete',
)


class Invalid(ValueError):
    pass


class Missing(ValueError):
    pass


def require(value, message):
    if not value:
        raise Invalid(message)


def same(a, b):
    return json.dumps(a, sort_keys=True, allow_nan=False) == json.dumps(b, sort_keys=True, allow_nan=False)


def exact(value, fields, label):
    require(type(value) is dict and set(value) == set(fields), label + ' fields')


def components(value, fields, label):
    require(type(value) is dict,label+' object')
    absent=set(fields)-set(value)
    if absent:raise Missing(label+' missing '+','.join(sorted(absent)))
    require(set(value)==set(fields),label+' unexpected fields')


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def seconds(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


def canonical(value):
    """Independent public record hash codec matching the frozen scalar contract."""
    def visit(x, depth=0):
        require(depth <= 32, 'record depth')
        if x is None or type(x) is bool:
            return
        if type(x) is int:
            require(abs(x) <= 2**53 - 1, 'record integer precision')
        elif type(x) is str:
            require(len(x.encode('utf-8')) <= 4096, 'record string bound')
        elif type(x) is list:
            require(len(x) <= 256, 'record array bound')
            for y in x: visit(y, depth + 1)
        elif type(x) is dict:
            require(len(x) <= 64 and all(type(k) is str for k in x), 'record object bound/keys')
            if '$f64' in x:
                require(set(x) == {'$f64'} and type(x['$f64']) is str and
                        re.fullmatch('[0-9a-f]{16}', x['$f64']), 'f64 bits')
                require(math.isfinite(struct.unpack('>d', bytes.fromhex(x['$f64']))[0]), 'finite f64')
            for k, v in x.items(): visit(k, depth + 1); visit(v, depth + 1)
        else:
            raise Invalid('raw float or unsupported record scalar')
    visit(value)
    return json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(',', ':'), allow_nan=False).encode('ascii')


def digest(record):
    return hashlib.sha256(PREFIX + canonical(record)).hexdigest()


def _ref_shape(ref):
    exact(ref, ('path', 'sha256'), 'public ref')
    require(sha(ref['sha256']), 'public ref SHA64')
    return str(capture._public_path(ref['path']))


class Inventory:
    """Only explicit allowlisted public originals; no private traversal or writes."""
    def __init__(self, paths, storage_root):
        require(type(paths) is list and paths and len(paths) == len(set(paths)), 'external public allowlist')
        self.root = capture._path(storage_root)
        self.allowed = set()
        self.indexed = {}
        for raw in paths:
            path = capture._public_path(raw)
            require(path.is_relative_to(self.root), 'public path outside frozen storage')
            self.allowed.add(str(path))

    def read(self, ref, *, json_value=True, cap=8*1024**2):
        path = _ref_shape(ref)
        require(path in self.allowed, 'ref outside external public allowlist')
        try:
            data, _ = capture._read(path, cap, public=True)
        except capture.CaptureError as error:
            # Missing evidence is not an invented negative observation. Symlinks,
            # replacements and other contradictions are failures.
            if not Path(path).exists() and not Path(path).is_symlink():
                raise Missing('missing public original: ' + path) from error
            raise
        require(hashlib.sha256(data).hexdigest() == ref['sha256'], 'public original digest changed')
        if self.indexed:
            require(path in self.indexed and self.indexed[path] == ref['sha256'], 'ref not in actual inventory')
        if not json_value:return data
        value=capture._json(data)
        def refs(item):
            if type(item) is dict:
                if set(item)=={'path','sha256'}:
                    target=_ref_shape(item)
                    require(target in self.allowed,'nested ref outside public allowlist')
                    if self.indexed:require(self.indexed.get(target)==item['sha256'],'nested ref not exact inventoried original')
                for child in item.values():refs(child)
            elif type(item) is list:
                for child in item:refs(child)
        refs(value)
        return value

    def inventory(self, artifacts, bundle_ref):
        require(type(artifacts) is list and artifacts, 'public inventory required')
        rows = {}
        for entry in artifacts:
            exact(entry, ('path', 'sha256', 'bytes'), 'artifact')
            require(integer(entry['bytes']), 'artifact bytes integer')
            ref = {k: entry[k] for k in ('path', 'sha256')}
            path = _ref_shape(ref)
            require(path not in rows and path != bundle_ref['path'], 'duplicate/self inventory')
            data = self.read(ref, json_value=False, cap=capture.MAX_PNG_BYTES)
            require(len(data) == entry['bytes'], 'artifact byte count changed')
            rows[path] = entry['sha256']
        require(set(rows) | {bundle_ref['path']} == self.allowed, 'inventory/public allowlist coverage')
        self.indexed = rows

    def tree(self, path):
        """Verify all public-copy entries before a fixed trusted parser sees them."""
        directory = capture._path(path)
        require(directory.is_relative_to(self.root), 'parser directory outside public storage')
        capture._parent_identity(directory / '.metadata-check')
        require(directory.is_dir(), 'public parser directory missing')
        for child in directory.rglob('*'):
            require(not child.is_symlink(), 'redirected public parser input')
            if child.is_file():
                require(str(child) in self.indexed, 'unindexed parser input')
                self.read({'path': str(child), 'sha256': self.indexed[str(child)]}, json_value=False,
                          cap=capture.MAX_PNG_BYTES)
            else:
                require(child.is_dir(), 'nonregular public parser input')


def _triple(value):
    exact(value, ('tick', 'revision', 'watermark'), 'selection')
    require(all(integer(x) for x in value.values()) and value['watermark'] == value['revision'], 'exact selection integers')
    return value


def _record(record, records, schema, world):
    exact(record, ('domain', 'version', 'world_id', 'kind', 'id', 'body', 'refs'), 'proof record')
    require(record['domain'] == 'edgeworld.universe.authority' and record['version'] == '0.2' and
            record['world_id'] == world, 'proof record world/domain')
    require(type(record['id']) is str and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',record['id']), 'proof record ID')
    kind = record['kind']
    require(kind in schema['body'] and type(record['body']) is dict and
            set(record['body']) == set(schema['body'][kind]) and type(record['refs']) is dict, 'proof record schema keys')
    encoded = canonical(record)
    require(len(encoded) <= schema['kind_bytes'][kind], 'proof record byte bound')
    key = hashlib.sha256(PREFIX + encoded).hexdigest()
    require(key in records and same(record, records[key]), 'proof record absent/mismatches independently parsed archive')
    declarations=schema['refs'][kind]
    if kind=='route':declarations={'p'+str(i):'place' for i in range(len(record['body']['place_ids']))}
    elif kind=='manifest':
        _triple(record['body'])
        declarations={'state':'state'} if record['body']['revision']==0 else {'state':'state','event':'event','index':'index','prior_manifest':'manifest'}
    allowed={name.rstrip('?'):target for name,target in declarations.items()}
    required={name for name in declarations if not name.endswith('?')}
    require(required<=set(record['refs'])<=set(allowed),'proof reference schema keys')
    for role,target in record['refs'].items():
        require(sha(target) and target in records and records[target]['kind']==allowed[role],'proof reference kind/missing target')
    return key


def verify_public_proof(frame, *, records, schema, binding, public_context):
    """Recompute known record/membership/closure contract; do not claim full parity."""
    request, response = frame['request'], frame['response']
    require(request['operation'] == 'observe' and response['ok'] is True and
            type(request['protocol_version']) is int and request['protocol_version'] == 1 and
            type(response['protocol_version']) is int and response['protocol_version'] == 1 and
            request['request_id'] == response['request_id'], 'observe wire identity')
    result = response['result']
    exact(result, ('domain', 'version', 'world_id', 'operation', 'payload'), 'observe result')
    require(result['domain'] == 'edgeworld.universe.authority' and result['version'] == '0.2' and
            result['world_id'] == binding['world_id'] and result['operation'] == 'observe', 'observe result identity')
    payload = result['payload']
    exact(payload, ('manifest','state','event','watermark','storage_state','artifact_class','head','membership','records','opaque_refs'), 'observe payload')
    selected = {k: request['payload'][k] for k in ('tick','revision','watermark')}; _triple(selected)
    require(type(payload['watermark']) is int and payload['watermark'] == selected['watermark'] and
            payload['storage_state'] == 'ready' and payload['artifact_class'] == 'genesis-runtime' and sha(payload['head']), 'observe selection/profile')
    ms, aux, opaque = payload['membership'], payload['records'], payload['opaque_refs']
    require(type(ms) is list and 1 <= len(ms) <= 64 and type(aux) is list and len(aux) <= 96 and
            type(opaque) is list and len(opaque) <= 256, 'public proof limits')
    all_records = ms + aux + [payload['manifest'],payload['state']] + ([] if payload['event'] is None else [payload['event']])
    local, ids, counts = {}, {}, {}
    for record in all_records:
        key = _record(record,records,schema,binding['world_id']); local[key]=record
        identity=(record['kind'],record['id'])
        require(identity not in ids or ids[identity] == key, 'conflicting proof record identity')
        ids[identity]=key; counts[record['kind']]=counts.get(record['kind'],0)+1
    for kind, count in counts.items():
        require(kind in schema['proof_kind_max'] and count <= schema['proof_kind_max'][kind], 'proof per-kind cap')
    membership=[digest(x) for x in ms]; selected_hash=digest(payload['manifest']); state_hash=digest(payload['state'])
    require(len(set(membership)) == len(membership) and all(x['kind']=='manifest' for x in ms) and
            membership[0] == payload['head'] and membership[-1] == selected_hash, 'membership head/selected/duplicate')
    for a,b in zip(ms,ms[1:]):
        _triple(a['body']); _triple(b['body'])
        require(a['refs'].get('prior_manifest') == digest(b) and a['body']['revision'] == b['body']['revision']+1 and
                a['body']['tick']-b['body']['tick'] in (0,1), 'membership continuity')
    manifest, state = payload['manifest'], payload['state']
    _triple(manifest['body'])
    require(manifest['kind']=='manifest' and state['kind']=='state' and same(manifest['body'],selected) and
            manifest['refs'].get('state') == state_hash, 'selected manifest/state')
    event=payload['event']
    require((selected['revision']==0 and event is None) or
            (selected['revision']>0 and type(event) is dict and event['kind']=='event' and
             manifest['refs'].get('event') == digest(event)), 'selected event')
    explicit=set(membership)|{selected_hash,state_hash}|({digest(event)} if event is not None else set())
    aux_hashes=[digest(x) for x in aux]
    require(len(aux_hashes)==len(set(aux_hashes)) and not (set(aux_hashes)&explicit), 'duplicate/explicit auxiliary record')
    previous=manifest['refs'].get('prior_manifest')
    needed, active, done=set(),set(),set()
    def expand(key, prior=False):
        memo=(key,prior)
        require(key in local and memo not in active, 'missing/cyclic selected closure')
        if memo in done:return
        active.add(memo); needed.add(key); record=local[key]
        for role, target in record['refs'].items():
            if record['kind']=='manifest' and (role=='prior_manifest' or (prior and role!='state')):continue
            if record['kind']=='event' and role=='prior_event':continue
            expand(target)
        active.remove(memo);done.add(memo)
    expand(selected_hash)
    if previous:expand(previous,True)
    require(set(local) <= needed|set(membership), 'unclaimed proof record')
    omitted=set()
    for key, record in local.items():
        for role, target in record['refs'].items():
            require(sha(target), 'proof ref digest')
            if target in local:continue
            allowed=(record['kind']=='event' and role=='prior_event') or (
                record['kind']=='manifest' and key!=selected_hash and role!='state') or (
                record['kind']=='manifest' and key in membership and key not in (selected_hash,previous))
            require(allowed,'unpermitted opaque dependency');omitted.add(target)
    require(opaque == sorted(omitted), 'opaque refs not exact sorted omissions')
    # Original archive parser checks each record's declared reference kind and
    # archive transition; matching its exact records is necessary but not a
    # substitute for UE's additional typed-body/static/selected-proof checks.
    return dict(manifest=selected_hash,state=state_hash,event=None if event is None else digest(event),
                selected_observation=selected,head=payload['head'], semantic_gaps=list(PUBLIC_PROOF_GAPS))


def _phase(result, name, missing):
    require(type(result) is dict and type(result.get('status')) is str, name+' structured validator result required')
    status=result['status']
    if status=='fail':raise Invalid(name+' failed: '+str(result.get('reasons',[])))
    if status in ('inconclusive','no_go'):
        missing.extend(name+': '+str(x) for x in (result.get('reasons') or ['incomplete evidence']))
    else:
        require(status in ('checks_complete_requires_review','consistent_requires_R_and_independent_review','ready_for_R_review'),
                name+' unrecognized validator status')


def verify_evidence(bundle_ref, *, expected_policy, authority_parser, trace_parser):
    """Offline structural report only. Root authenticates policy, fixed code and originals."""
    try:
        return _verify(bundle_ref,expected_policy,authority_parser,trace_parser)
    except Missing as error:
        return {'status':'inconclusive','reasons':[str(error)],'g_b2_granted':False,'runtime_authorized':False}
    except (Invalid,capture.CaptureError,actions.Invalid,lifecycle.Invalid,KeyError,TypeError,ValueError,OSError,OverflowError,RecursionError) as error:
        return {'status':'fail','reasons':[str(error)],'g_b2_granted':False,'runtime_authorized':False}


def _verify(bundle_ref, policy, authority_parser, trace_parser):
    exact(policy, ('format','lifecycle','actual_finalized_monotonic','public_context','schema','manifest_ref',
                   'resource_card_ref','capabilities','session_expectations'), 'external policy')
    require(policy['format']==POLICY and callable(authority_parser) and callable(trace_parser),'fixed code parser API/policy')
    require(policy['actual_finalized_monotonic'] is None or seconds(policy['actual_finalized_monotonic']),'independent actual-finalization time')
    lp=policy['lifecycle'];require(lp['format']=='universe-i14-lifecycle-policy.v1','lifecycle policy version')
    inv=Inventory(lp['public_paths'],lp['storage_root']);bundle=inv.read(bundle_ref)
    components(bundle,('format','artifacts','resource_card_ref','manifest_ref','ledger_ref','sessions'),'bundle')
    require(bundle['format']==FORMAT,'new bundle version required; no captured_at compatibility fabrication')
    inv.inventory(bundle['artifacts'],bundle_ref)
    for name in ('resource_card_ref','manifest_ref'):
        require(same(bundle[name],policy[name]),'external '+name+' mismatch');inv.read(bundle[name])
    expected_sessions=policy['session_expectations']
    exact(expected_sessions,SESSIONS,'external sessions');components(bundle['sessions'],SESSIONS,'bundle sessions')
    exact(lp['session_bindings'],SESSIONS,'lifecycle sessions')
    missing=[];checks={};proof_checks=[];all_capture_ids=set();all_capture_refs=set();all_worker_pids=set();all_host_pids=set()
    validate_ledger=getattr(lifecycle,'validate_ledger_v2',None)
    validate_actions=getattr(actions,'validate_session_v2',None)
    ready=getattr(actions,'readiness_v2',None);manifest_fn=getattr(actions,'manifest_v2',None)
    if not all(callable(x) for x in (validate_ledger,validate_actions,ready,manifest_fn)):
        raise Missing('accepted lifecycle.v2/actions.v2 code not integrated')
    expected_manifest=manifest_fn();require(same(inv.read(policy['manifest_ref']),expected_manifest),'frozen manifest differs from accepted actions.v2')
    for ref in policy['capabilities'].values():inv.read(ref)
    readiness=ready(policy['capabilities'],expected_source_sha=lp['run_binding']['source_sha']);_phase(readiness,'capabilities',missing)
    ledger=inv.read(bundle['ledger_ref'])
    _phase(validate_ledger(ledger,expected_policy=lp,actual_finalized_monotonic=policy['actual_finalized_monotonic']),'lifecycle',missing)
    for session in SESSIONS:
        spec=expected_sessions[session];actual=bundle['sessions'][session];binding=lp['session_bindings'][session]
        exact(spec,('authority_copy','trace_directory','trace_refs','captures'),'external session expectation')
        components(actual,('binding','authority_copy','trace_directory','trace_refs','action_receipt_refs','captures'),'session')
        capture._binding(actual['binding'],binding)
        require({k:binding[k] for k in lp['run_binding']}==lp['run_binding'] and binding['session']==session,'session/run mismatch')
        all_worker_pids.add(binding['worker_pid']);all_host_pids.add(binding['host_pid'])
        for field in ('authority_copy','trace_directory','trace_refs'):
            require(same(actual[field],spec[field]),'external parser path/ref mismatch')
        inv.tree(actual['authority_copy']);inv.tree(actual['trace_directory'])
        for ref in actual['trace_refs']:inv.read(ref,json_value=False)
        authority=authority_parser(actual['authority_copy'],policy['schema'])
        require(type(authority) is dict and type(authority.get('records_by_hash')) is dict and
                authority.get('world_id')==binding['world_id'] and sha(authority.get('head')),'independent authority parser structure/world')
        records=authority['records_by_hash'];require(records,'independent records absent')
        for key,record in records.items():require(key==digest(record),'independent archive record hash mismatch')
        trace=trace_parser(actual['trace_directory'])
        require(type(trace) is dict and set(('frames','worker_exits','transport_count'))<=set(trace) and
                type(trace['frames']) is list and trace['transport_count']==1 and type(trace['transport_count']) is int and
                type(trace['worker_exits']) is list and len(trace['worker_exits'])==1,'independent trace parser structure/one transport')
        exit_event=trace['worker_exits'][0]
        require(type(exit_event) is dict and type(exit_event.get('worker_pid')) is int and
                exit_event['worker_pid']==binding['worker_pid'] and str(exit_event.get('generation'))==str(binding['generation']) and
                all(exit_event.get(k) is True for k in ('return_code_available','reaped','trace_complete')) and
                all(exit_event.get(k) is False for k in ('hard_kill_sent','operational_failure')) and
                type(exit_event.get('exit_code')) is int and exit_event['exit_code']==0 and exit_event.get('stop_kind')=='normal',
                'independent trace worker exit not normal')
        frames=trace['frames'];business=actions.load_trace(actual['trace_refs'],expected_binding=binding)
        require(same([{'request':x['request'],'response':x['response']} for x in frames],business),'independent trace/action parser disagreement')
        for frame in frames:
            require(frame.get('host_pid')==binding['host_pid'] and type(frame.get('host_pid')) is int and
                    frame.get('worker_pid')==binding['worker_pid'] and type(frame.get('worker_pid')) is int and
                    str(frame.get('generation'))==str(binding['generation']),'independent trace process binding')
        if session=='existing':require(all(x['request']['operation'] in ('status','observe') for x in frames),'existing session write/initialize')
        require(authority['head'] in records,'independent archive HEAD missing')
        receipts=[inv.read(ref) for ref in actual['action_receipt_refs']]
        for receipt in receipts:require(same(receipt['clock'],ledger['clock']),'action/lifecycle controller clock mismatch')
        require(receipts and same(records[authority['head']]['body'],receipts[-1]['trusted_head']),'archive final HEAD/action trusted current mismatch')
        checks[session]=validate_actions(receipts,actual['trace_refs'],expected_binding=binding,expected_context=policy['public_context'])
        _phase(checks[session],session+' actions',missing)
        observed={}
        for index,frame in enumerate(frames):
            if frame['request']['operation']=='observe':
                observed[index]=verify_public_proof(frame,records=records,schema=policy['schema'],binding=binding,public_context=policy['public_context'])
                proof_checks.append({'session':session,'frame_index':index,**observed[index]})
        require(type(spec['captures']) is list and type(actual['captures']) is list,'capture lists required')
        for expected_capture in spec['captures']:
            exact(expected_capture,('capture_id','action_id','stage','trace_frame_index','observation_ref','trusted_head','selected_observation',
                  'clock','after_map_ref','after_map_monotonic','before_exit_monotonic','before_exit_ref'),'external capture expectation')
        for actual_capture in actual['captures']:exact(actual_capture,('capture_id','capture_ref'),'capture association')
        expected_by_id={x['capture_id']:x for x in spec['captures']}
        require(len(expected_by_id)==len(spec['captures']),'duplicate external capture expectation')
        actual_by_id={x['capture_id']:x['capture_ref'] for x in actual['captures']}
        require(len(actual_by_id)==len(actual['captures']) and set(actual_by_id)<=set(expected_by_id),'duplicate/unclaimed capture')
        if set(actual_by_id)!=set(expected_by_id):raise Missing('missing expected capture')
        receipt_images={}
        for receipt in receipts:
            for image in receipt['image_checks']:
                exact(image,('capture_id','stage','capture_ref'),'v2 image association')
                key=image['capture_id'];require(key not in receipt_images,'duplicate B image claim')
                receipt_images[key]=(receipt['action_id'],image['stage'],image['capture_ref'])
        require(set(receipt_images)==set(expected_by_id),'B/C image coverage mismatch')
        receipt_by_id={x['action_id']:x for x in receipts}
        for key,spec_capture in expected_by_id.items():
            require(key==spec_capture['action_id']+'/'+spec_capture['stage'],'fixed capture ID/action/stage association')
            require(same(spec_capture['clock'],ledger['clock']),'capture/lifecycle clock mismatch')
            require(key not in all_capture_ids,'capture ID reused across sessions');all_capture_ids.add(key)
            ref=actual_by_id[key];path=_ref_shape(ref);require(path not in all_capture_refs,'capture receipt reused');all_capture_refs.add(path)
            require(same(receipt_images[key],(spec_capture['action_id'],spec_capture['stage'],ref)),'capture action/stage/ref mismatch')
            index=spec_capture['trace_frame_index'];require(integer(index) and index in observed,'capture not bound to actual observe')
            obs=observed[index];frame=frames[index]
            require(same(obs['selected_observation'],spec_capture['selected_observation']),'capture selected observation mismatch')
            wrapper=inv.read(spec_capture['observation_ref'])
            require(same(inv.read(wrapper['verification_ref']),frame['response']),'wrapper verification_ref not actual complete observe response')
            capture._binding(wrapper['binding'],binding)
            require(same(wrapper['trusted_head'],spec_capture['trusted_head']) and
                    same(wrapper['selected_observation'],spec_capture['selected_observation']),'wrapper head/selection mismatch')
            current=records[obs['head']]
            require(same(current['body'],spec_capture['trusted_head']),'trusted head not actual membership root')
            receipt=receipt_by_id[spec_capture['action_id']]
            require(index<receipt['trace_range'][1],'capture observes a future trace frame')
            exit_receipts=[r for r in receipts if r['action_id']==('s1.exit' if session=='initialize' else 's2.exit')]
            require(len(exit_receipts)==1 and exit_receipts[0]['started_monotonic']<=spec_capture['before_exit_monotonic']<=exit_receipts[0]['completed_monotonic'],
                    'capture actual exit boundary detached from action exit receipt')
            stages=[e for e in receipt['checkpoints'] if e['stage']==spec_capture['stage']]
            require(len(stages)==1,'capture stage missing/duplicate checkpoint')
            stage_map=inv.read(stages[0]['map']);after_map=inv.read(spec_capture['after_map_ref'])
            require(same(stage_map,after_map),'image map detached from action checkpoint authority')
            captured=inv.read(ref);prepare=inv.read(captured['preparation_ref']);inv.read(captured['command_receipt_ref'])
            inv.read(captured['original_ref'],json_value=False,cap=capture.MAX_PNG_BYTES)
            for nested_ref in (prepare['before_map_ref'],spec_capture['before_exit_ref']):inv.read(nested_ref)
            log_path=prepare['log']['path']
            require(log_path in inv.indexed,'C log missing from actual inventory')
            inv.read({'path':log_path,'sha256':inv.indexed[log_path]},json_value=False)
            result=capture.verify_native_shot(ref,expected_binding=binding,expected_trusted_head=spec_capture['trusted_head'],
                expected_selected_observation=spec_capture['selected_observation'],expected_observation_ref=spec_capture['observation_ref'],
                expected_clock=spec_capture['clock'],after_map_ref=spec_capture['after_map_ref'],after_map_monotonic=spec_capture['after_map_monotonic'],
                before_exit_monotonic=spec_capture['before_exit_monotonic'],before_exit_ref=spec_capture['before_exit_ref'])
            require(result['phase']=='checks_complete_requires_review','capture structural result missing')
    require(len(all_worker_pids)==len(all_host_pids)==2,'distinct host/worker PIDs required')
    missing.extend(PUBLIC_PROOF_GAPS)
    return dict(format='universe-i14-verification-result.v1',status='inconclusive' if missing else 'checks_complete_requires_review',
                reasons=sorted(set(missing)),checks=checks,proof_checks=proof_checks,
                g_b2_granted=False,runtime_authorized=False,
                note='Known contradictions fail; remaining public proof parity and real policy/source/UI/Metal provenance require independent review')
