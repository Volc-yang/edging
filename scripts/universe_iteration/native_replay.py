"""Public raw replay inputs and source-bound Native execution review, no UE launch.

Native parsing is the accepted C++ parser, never a new Python semantic parity.
A review is meaningful only with independently frozen root policy and originals.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from functools import wraps

from . import actions, capture

MANIFEST='universe-i15-native-replay.v1'
RESULT='universe-i15-native-replay-result.v1'
REVIEW='universe-i15-native-replay-review.v1'
POLICY='universe-i15-native-replay-policy.v1'
SELECTORS=(
 'edgeWorld.UniverseHost.PublicProofReplay',
 'edgeWorld.UniverseHost.Diagnostics.IdentityAndDefaultOff',
 'edgeWorld.UniverseHost.Diagnostics.HandledInputAndOrder',
 'edgeWorld.UniverseHost.Diagnostics.PauseReadWithoutTick',
)
ENV_KEYS={'EDGEWORLD_UNIVERSE_NATIVE_REPLAY','EDGEWORLD_UNIVERSE_REPLAY_MANIFEST',
          'EDGEWORLD_UNIVERSE_REPLAY_MANIFEST_SHA256','EDGEWORLD_UNIVERSE_REPLAY_OUTPUT'}
INPUTS=('pins','status_request','status_response','observe_request','observe_response')
CASE_KEYS={'case_id','origin','source_case_id','pins_ref','status_request_ref','status_response_ref',
           'observe_request_ref','observe_response_ref','trace_refs','trace_frame_index','expected','expected_accept'}


class Invalid(ValueError):pass


def boundary(function):
 @wraps(function)
 def checked(*args,**kwargs):
  try:return function(*args,**kwargs)
  except Invalid:raise
  except (KeyError,TypeError,ValueError,OSError,OverflowError,RecursionError,IndexError,AttributeError) as error:raise Invalid(str(error)) from error
 return checked


def require(test,message):
 if not test:raise Invalid(message)


def exact(value,keys,label):
 require(type(value) is dict and set(value)==set(keys),label+' fields')


def equal(a,b):return json.dumps(a,sort_keys=True,allow_nan=False)==json.dumps(b,sort_keys=True,allow_nan=False)


def sha(value,length=64):return type(value) is str and re.fullmatch('[0-9a-f]{'+str(length)+'}',value) is not None


def integer(value,minimum=0):return type(value) is int and value>=minimum


class Public:
 def __init__(self,paths):
  require(type(paths) is list and len(paths)==len(set(paths)),'external public allowlist required')
  self.paths={str(capture._public_path(p)) for p in paths}
 def read(self,ref,cap=1048577):
  exact(ref,('path','sha256'),'ref');require(sha(ref['sha256']) and ref['path'] in self.paths,'unapproved public ref')
  data,_=capture._read(ref['path'],cap,public=True)
  require(hashlib.sha256(data).hexdigest()==ref['sha256'],'original SHA mismatch');return data
 def json(self,ref,cap=1048577):return capture._json(self.read(ref,cap))
 def hash_file(self,ref):
  exact(ref,('path','sha256'),'binary/source ref');require(ref['path'] in self.paths and sha(ref['sha256']),'unapproved binary/source ref')
  with capture._parent(capture._public_path(ref['path'])) as (path,dfd,parent):
   fd=os.open(path.name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=dfd)
   try:
    first=os.fstat(fd);require(stat.S_ISREG(first.st_mode) and first.st_size<=1024**3,'bounded regular binary/source')
    h=hashlib.sha256()
    while True:
     block=os.read(fd,1024**2)
     if not block:break
     h.update(block)
    last=os.fstat(fd);now=os.stat(path.name,dir_fd=dfd,follow_symlinks=False)
    require(capture._stat_identity(first)==capture._stat_identity(last)==capture._stat_identity(now) and
            capture._parent_identity(path)==capture._identity(parent),'binary/source changed')
    require(h.hexdigest()==ref['sha256'],'binary/source SHA mismatch')
   finally:os.close(fd)


def reassemble_trace(trace_refs, *, trace_identity, public_paths):
 """Keep original LF bytes; completed frames may precede failed/incomplete teardown.

 This is provenance/framing, not a normal-transport or resource acceptance check.
 """
 exact(trace_identity,('host_pid','worker_pid','generation'),'trace identity')
 require(all(integer(x,1) for x in trace_identity.values()),'positive exact trace identity')
 require(type(trace_refs) is list and trace_refs,'raw trace refs required')
 public=Public(public_paths);indexed={}
 for ref in trace_refs:
  require(ref['path'] not in indexed,'duplicate raw trace ref');indexed[ref['path']]=public.read(ref)
 parents={str(Path(p).parent) for p in indexed};require(len(parents)==1,'one trace directory')
 entries=[];used=set();prefixes=set()
 for path,data in indexed.items():
  if not path.endswith('.json'):continue
  meta=capture._json(data);rawname=meta['raw_file'];require(Path(rawname).name==rawname,'raw path escape')
  rawpath=str(Path(path).parent/rawname);require(rawpath in indexed,'missing raw trace chunk')
  raw=indexed[rawpath];require(type(meta['byte_count']) is int and len(raw)==meta['byte_count'],'raw chunk byte count')
  serial=meta['serial'];require(type(serial) in (str,int) and re.fullmatch('[1-9][0-9]*',str(serial)),'trace serial')
  require(type(meta['host_pid']) is int and type(meta['worker_pid']) is int and
          meta['host_pid']==trace_identity['host_pid'] and meta['worker_pid']==trace_identity['worker_pid'] and
          type(meta['generation']) in (str,int) and str(meta['generation'])==str(trace_identity['generation']),'trace identity mismatch')
  prefixes.add(Path(path).stem.rsplit('-',1)[0]);entries.append((int(serial),meta,raw));used.update((path,rawpath))
 require(len(prefixes)==1 and used==set(indexed),'unowned trace files/prefixes')
 entries.sort(key=lambda x:x[0]);require([x[0] for x in entries]==list(range(1,len(entries)+1)),'trace serial gap')
 pending=None;response=bytearray();written=False;frames=[];last=-1;ids=set()
 for serial,meta,raw in entries:
  timestamp=meta['monotonic_seconds'];require(capture._seconds(timestamp) and timestamp>=last,'trace time order');last=timestamp
  direction=meta['direction']
  if direction=='request':
   require(pending is None,'overlapping raw request');request=actions._wire(raw)
   exact(request,('protocol_version','request_id','operation','payload'),'request wire')
   require(type(request['protocol_version']) is int and request['protocol_version']==1 and request['request_id'] not in ids and
           request['request_id']==meta['request_id'] and request['operation']==meta['operation'],'request metadata/ID')
   ids.add(request['request_id']);pending={'request':request,'request_bytes':raw,'request_serial':serial};response.clear();written=False
  elif direction in ('write-result','stdout-chunk','response-complete'):
   require(pending is not None and meta.get('request_id')==pending['request']['request_id'] and
           meta.get('operation')==pending['request']['operation'],'unowned response data')
   if direction=='write-result':
    require(not written and meta['written_bytes']==len(pending['request_bytes']),'partial/duplicate raw write');written=True
   elif direction=='stdout-chunk':
    response.extend(raw);require(len(response)<=1048577,'response byte cap')
   else:
    require(written,'response without completed write');parsed=actions._wire(bytes(response))
    require(parsed['request_id']==pending['request']['request_id'] and type(parsed['protocol_version']) is int and parsed['protocol_version']==1 and
            type(parsed['ok']) is bool,'response wire identity')
    frames.append(dict(pending,response=parsed,response_bytes=bytes(response),response_serial=serial));pending=None
  elif direction in ('stderr-chunk','stdin-eof','shutdown-stdout-chunk','shutdown-stderr-chunk','worker-exit'):pass
  else:raise Invalid('unknown raw trace direction')
 return frames


def _source(case,sources):
 matches=[x for x in sources if equal(x['pins_ref'],case['pins_ref']) and equal(x['trace_refs'],case['trace_refs']) and
          case['trace_frame_index'] in x['observe_frame_indices']]
 require(len(matches)==1,'case not uniquely in independent source catalog');return matches[0]


def _source_case(case,source,public):
 frames=reassemble_trace(source['trace_refs'],trace_identity=source['trace_identity'],public_paths=list(public.paths))
 index=case['trace_frame_index'];require(integer(index) and index<len(frames),'observe frame absent')
 observe=frames[index];require(observe['request']['operation']=='observe','selected frame is not observe')
 statuses=[x for x in frames[:index] if x['request']['operation']=='status' and x['response'].get('ok') is True]
 require(statuses,'original successful status before Observe required');return statuses[-1],observe


def _expected(status,observe):
 p=observe['request']['payload'];values={k:p[k] for k in ('tick','revision','watermark')}
 require(all(integer(x) and x<=2**53-1 for x in values.values()) and values['watermark']==values['revision'],'selection integers')
 return dict(status_request_id=status['request']['request_id'],observe_request_id=observe['request']['request_id'],**values)


@boundary
def validate_native_manifest(manifest_ref, *, expected_run_id, expected_product_source_sha,
                             expected_tool_source_sha, allowed_sources, public_paths):
 public=Public(public_paths);manifest=public.json(manifest_ref,262144)
 exact(manifest,('format','run_id','product_source_sha','tool_source_sha','cases'),'manifest')
 require(manifest['format']==MANIFEST and manifest['run_id']==expected_run_id and
         manifest['product_source_sha']==expected_product_source_sha and manifest['tool_source_sha']==expected_tool_source_sha and
         sha(expected_product_source_sha,40) and sha(expected_tool_source_sha,40),'external replay source/run binding')
 require(type(allowed_sources) is list and allowed_sources,'independent source catalog required')
 for source in allowed_sources:
  exact(source,('pins_ref','trace_refs','observe_frame_indices','trace_identity'),'source catalog')
  require(type(source['observe_frame_indices']) is list and source['observe_frame_indices'] and
          all(integer(x) for x in source['observe_frame_indices']) and len(source['observe_frame_indices'])==len(set(source['observe_frame_indices'])),'source indices')
 require(type(manifest['cases']) is list and 1<=len(manifest['cases'])<=8,'nonempty bounded replay cases')
 ids=set();real=[];negative=[];origins=set()
 for case in manifest['cases']:
  exact(case,CASE_KEYS,'case');identifier=case['case_id']
  require(type(identifier) is str and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',identifier) and identifier not in ids,'unique case ID');ids.add(identifier)
  if case['origin']=='real-trace':
   require(case['source_case_id'] is None and case['expected_accept'] is True,'real case expectation');real.append(case)
   source=_source(case,allowed_sources);status,observe=_source_case(case,source,public)
   origin=(case['pins_ref']['sha256'],tuple((r['path'],r['sha256']) for r in case['trace_refs']),case['trace_frame_index'])
   require(origin not in origins,'same original response relabeled duplicate case');origins.add(origin)
   require(equal(case['expected'],_expected(status,observe)),'request IDs/selection detached from raw trace')
   for name,raw in (('status_request',status['request_bytes']),('status_response',status['response_bytes']),
                    ('observe_request',observe['request_bytes']),('observe_response',observe['response_bytes'])):
    require(public.read(case[name+'_ref'])==raw,'case bytes not original trace LF bytes')
  elif case['origin']=='derived-negative':
   require(case['expected_accept'] is False and type(case['source_case_id']) is str,'negative labeling');negative.append(case)
  else:raise Invalid('unknown case origin')
  pins=public.json(case['pins_ref'],16384)
  require(pins.get('artifact_class')=='genesis-runtime','no fixture-only public pins')
  for name in INPUTS:public.read(case[name+'_ref'],16384 if name=='pins' else 1048577)
 require(1<=len(real)<=6 and len(negative)<=2,'real/derived case bounds')
 real_by_id={x['case_id']:x for x in real}
 for case in negative:
  require(case['source_case_id'] in real_by_id,'negative lacks real source case')
  source=real_by_id[case['source_case_id']]
  for name in ('pins_ref','status_request_ref','status_response_ref','observe_request_ref','trace_refs','trace_frame_index','expected'):
   require(equal(case[name],source[name]),'negative changed original context/request identity')
  require(case['observe_response_ref']['sha256']!=source['observe_response_ref']['sha256'],'negative is unmodified real response')
 return manifest


@boundary
def prepare_replay_cases(*, run_id, product_source_sha, tool_source_sha, selections,
                         allowed_sources, public_paths, output_dir):
 """Write exclusive raw request/response copies and one manifest; no process/UE."""
 public=Public(public_paths);require(type(selections) is list and 1<=len(selections)<=6,'bounded real selections')
 out=capture._public_path(output_dir)
 with capture._parent(out) as (path,fd,parent):os.mkdir(path.name,0o700,dir_fd=fd)
 generated=[];cases=[]
 def save(name,raw):
  path=out/name
  with capture._parent(path) as (p,fd,parent):
   f=os.open(p.name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=fd)
   try:
    view=memoryview(raw)
    while view:
     n=os.write(f,view);require(n>0,'raw evidence write failed');view=view[n:]
    os.fsync(f)
   finally:os.close(f)
  generated.append(str(path));return {'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
 for selection in selections:
  exact(selection,('case_id','pins_ref','trace_refs','trace_frame_index'),'selection')
  require(type(selection['case_id']) is str and re.fullmatch('[a-z0-9][a-z0-9-]{0,63}',selection['case_id']),'safe case ID')
  source=_source(selection,allowed_sources);status,observe=_source_case(selection,source,public)
  case=dict(selection,origin='real-trace',source_case_id=None,expected=_expected(status,observe),expected_accept=True)
  for name,raw in (('status_request',status['request_bytes']),('status_response',status['response_bytes']),('observe_request',observe['request_bytes']),('observe_response',observe['response_bytes'])):
   case[name+'_ref']=save(selection['case_id']+'-'+name+'.jsonl',raw)
  cases.append(case)
 manifest=dict(format=MANIFEST,run_id=run_id,product_source_sha=product_source_sha,tool_source_sha=tool_source_sha,cases=cases)
 ref=save('manifest.json',(json.dumps(manifest,sort_keys=True,indent=2,allow_nan=False)+'\n').encode())
 validate_native_manifest(ref,expected_run_id=run_id,expected_product_source_sha=product_source_sha,expected_tool_source_sha=tool_source_sha,
                          allowed_sources=allowed_sources,public_paths=list(public.paths)+generated)
 return {'manifest_ref':ref,'public_paths':generated,'case_ids':[x['case_id'] for x in cases]}


def _record_hash(record):
 return hashlib.sha256(b'edgeworld.universe.authority\0v0.2\0'+json.dumps(record,sort_keys=True,ensure_ascii=True,separators=(',',':'),allow_nan=False).encode('ascii')).hexdigest()


def _selected_records(payload):
 records=payload['membership']+payload['records']+[payload['manifest'],payload['state']]+([] if payload['event'] is None else [payload['event']])
 local={_record_hash(x):x for x in records};selected=_record_hash(payload['manifest']);previous=payload['manifest']['refs'].get('prior_manifest');needed=set();active=set();done=set()
 def visit(key,prior=False):
  token=(key,prior);require(key in local and token not in active,'selected original closure missing/cyclic')
  if token in done:return
  active.add(token);needed.add(key);record=local[key]
  for role,target in record['refs'].items():
   if record['kind']=='manifest' and (role=='prior_manifest' or (prior and role!='state')):continue
   if record['kind']=='event' and role=='prior_event':continue
   visit(target)
  active.remove(token);done.add(token)
 visit(selected)
 if previous:visit(previous,True)
 return [{'digest':key,'kind':local[key]['kind'],'id':local[key]['id']} for key in sorted(needed)]


def verify_native_replay_review(review_ref, *, expected_policy):
 """Check externally approved source/binary/input/output/wait originals, exact responses only."""
 try:return _review(review_ref,expected_policy)
 except (KeyError,FileNotFoundError) as e:return {'status':'inconclusive','reasons':['missing native replay evidence: '+str(e)],'coverage':[],'g_b2_granted':False}
 except capture.CaptureError as e:
  cause=e
  while cause is not None:
   if isinstance(cause,FileNotFoundError):
    return {'status':'inconclusive','reasons':['missing native replay evidence: '+str(e)],'coverage':[],'g_b2_granted':False}
   cause=cause.__cause__
  return {'status':'fail','reasons':[str(e)],'coverage':[],'g_b2_granted':False}
 except (Invalid,actions.Invalid,ValueError,TypeError,OSError,OverflowError,RecursionError,IndexError,AttributeError) as e:
  return {'status':'fail','reasons':[str(e)],'coverage':[],'g_b2_granted':False}


def _review(review_ref,p):
 required={'format','run_id','product_source_sha','tool_source_sha','allowed_sources','public_paths','approved_review_ref',
           'manifest_ref','result_ref','execution_ref','automation_log_ref','source_refs','binary_refs','resource_ref',
           'expected_host_pid','expected_process_start','expected_parent_pid','expected_ue_version','expected_argv','expected_env','expected_cwd','native_source_sha','build_ref'}
 exact(p,required,'independent native policy');require(p['format']==POLICY and equal(review_ref,p['approved_review_ref']),'independent approved review hash required')
 public=Public(p['public_paths']);review=public.json(review_ref)
 exact(review,('format','decision','owner','reviewer','manifest_ref','result_ref','execution_ref','automation_log_ref','source_refs','binary_refs','resource_ref','build_ref','coverage'),'review')
 require(review['format']==REVIEW and review['decision']=='pass' and type(review['owner']) is str and type(review['reviewer']) is str and
         review['owner'] and review['reviewer'] and review['owner']!=review['reviewer'],'independent review decision required')
 for key in ('manifest_ref','result_ref','execution_ref','automation_log_ref','source_refs','binary_refs','resource_ref','build_ref'):
  require(equal(review[key],p[key]),'frozen native review '+key+' mismatch')
 exact(p['source_refs'],('parser_cpp','parser_h','bridge_cpp'),'actual parser/bridge sources')
 exact(p['binary_refs'],('host','plugin','executable'),'actual native binaries')
 for ref in list(p['source_refs'].values())+list(p['binary_refs'].values()):public.hash_file(ref)
 build=public.json(p['build_ref'])
 require(sha(p['native_source_sha'],40) and build.get('source_sha')==p['native_source_sha'] and
         equal(build.get('source_refs'),p['source_refs']) and equal(build.get('binary_refs'),p['binary_refs']) and
         type(build.get('actual_parent_wait_exit')) is int and build['actual_parent_wait_exit']==0 and
         build.get('build_only') is True and build.get('ue_runtime_started') is False,
         'official actual build source/binary receipt missing or inconsistent')
 manifest=validate_native_manifest(p['manifest_ref'],expected_run_id=p['run_id'],expected_product_source_sha=p['product_source_sha'],
    expected_tool_source_sha=p['tool_source_sha'],allowed_sources=p['allowed_sources'],public_paths=p['public_paths'])
 execution=public.json(p['execution_ref']);result=public.json(p['result_ref']);log=public.read(p['automation_log_ref'],8*1024**2).decode('utf-8')
 fields={'format','host_pid','process_start','parent_pid','argv','cwd','environment','selectors','manifest_ref','result_ref','parent_wait',
         'normal','forced_cleanup','started_monotonic','ended_monotonic'}
 require(type(execution) is dict and fields<=set(execution) and execution['format']=='universe-i15-native-execution.v1','actual native execution receipt')
 require(execution['normal'] is True and execution['forced_cleanup'] is False,'native process not normal')
 for key,external in (('host_pid','expected_host_pid'),('process_start','expected_process_start'),('parent_pid','expected_parent_pid'),
                      ('argv','expected_argv'),('cwd','expected_cwd'),('environment','expected_env')):
  require(equal(execution[key],p[external]),'actual execution '+key+' differs from independent pin')
 require(integer(execution['host_pid'],1) and integer(execution['parent_pid'],1) and type(execution['process_start']) is str and execution['process_start'],'actual process identity')
 require(execution['selectors']==list(SELECTORS) and equal(execution['manifest_ref'],p['manifest_ref']) and equal(execution['result_ref'],p['result_ref']),'exact selectors/input/output binding')
 env=execution['environment'];exact(env,ENV_KEYS,'filtered replay environment')
 require(env['EDGEWORLD_UNIVERSE_NATIVE_REPLAY']=='1' and env['EDGEWORLD_UNIVERSE_REPLAY_MANIFEST']==p['manifest_ref']['path'] and
         env['EDGEWORLD_UNIVERSE_REPLAY_MANIFEST_SHA256']==p['manifest_ref']['sha256'] and env['EDGEWORLD_UNIVERSE_REPLAY_OUTPUT']==p['result_ref']['path'],'native replay environment/input binding')
 wait=execution['parent_wait'];require(type(wait) is dict and wait.get('observed') is True and type(wait.get('exit_code')) is int and wait['exit_code']==0,'actual parent wait0 required')
 for key in ('host_pid','process_start','parent_pid'):require(equal(wait.get(key),execution[key]),'wait process identity')
 require(capture._seconds(execution['started_monotonic']) and capture._seconds(execution['ended_monotonic']) and
         0<=execution['ended_monotonic']-execution['started_monotonic']<=180,'Native phase interval')
 resource=public.json(p['resource_ref']);require(type(resource) is dict and resource.get('run_id')==p['run_id'] and
         capture._seconds(resource.get('elapsed_seconds')) and resource['elapsed_seconds']<=900 and
         type(resource.get('storage_bytes')) is int and 0<=resource['storage_bytes']<=2*1024**3 and
         resource.get('all_processes_quiet') is True,'whole capability resource accounting missing/failed')
 found=re.findall(r'Found\s+(\d+)\s+automation tests',log,re.I);require(found and found[-1]=='4','exact found=4 required')
 completed=re.findall(r'Test Completed\. Result=\{([^}]+)\} Name=\{[^}]*\} Path=\{([^}]+)\}',log)
 require(len(completed)==4 and {path for _,path in completed}==set(SELECTORS) and all(outcome=='Success' for outcome,_ in completed),'four exact Native Success originals required')
 require(result.get('format')==RESULT and result.get('bridge_format')=='strict-public-status-observe.v1' and
         result.get('manifest_sha256')==p['manifest_ref']['sha256'] and type(result.get('host_pid')) is int and
         result['host_pid']==execution['host_pid'] and result.get('ue_version')==p['expected_ue_version'] and
         type(result.get('case_count')) is int and result['case_count']==len(manifest['cases']) and
         type(result.get('cases')) is list and len(result['cases'])==result['case_count'],'actual Native result binding/count')
 rows=result['cases'];require([x['case_id'] for x in rows]==[x['case_id'] for x in manifest['cases']],'exact case output order')
 coverage=[]
 for case,row in zip(manifest['cases'],rows):
  require(row['origin']==case['origin'] and type(row['accepted']) is bool and row['accepted']==case['expected_accept'],'actual Native case expectation')
  require(row['actual_input_sha256s']=={name:case[name+'_ref']['sha256'] for name in INPUTS},'Native did not load exact actual case bytes')
  require(all(equal(row[k],value) for k,value in case['expected'].items()),'Native request IDs/triple mismatch')
  if case['origin']!='real-trace':continue
  require(row['accepted'] is True and row['error']=='','real proof not accepted')
  raw=public.json(case['observe_response_ref']);payload=raw['result']['payload'];pins=public.json(case['pins_ref'])
  status=public.json(case['status_response_ref'])['result']['payload'];head=status['head_binding']['head']
  require(row['manifest']==_record_hash(payload['manifest']) and row['state']==_record_hash(payload['state']) and
          row['event']==('' if payload['event'] is None else _record_hash(payload['event'])) and equal(row['selected_records'],_selected_records(payload)),
          'Native selected output detached from actual response records')
  coverage.append(dict(case_id=case['case_id'],observe_response_sha256=case['observe_response_ref']['sha256'],
      observe_request_sha256=case['observe_request_ref']['sha256'],pins_sha256=case['pins_ref']['sha256'],context=pins,
      trusted_head_hash=head,selected_observation={k:case['expected'][k] for k in ('tick','revision','watermark')},
      manifest=row['manifest'],state=row['state'],event=row['event']))
 require(equal(review['coverage'],[x['observe_response_sha256'] for x in coverage]),'approved coverage not exact real responses')
 return {'status':'checks_complete_requires_review','coverage':coverage,'g_b2_granted':False,
         'note':'Only these exact responses ran the pinned strict Native parser; no Metal/input/runtime-pair/provision authorization is granted'}
