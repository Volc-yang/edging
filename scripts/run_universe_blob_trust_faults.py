#!/usr/bin/env python3
"""E6 synthetic v0.2 acceptance; production imports occur only in children.

The parent has independent ASCII, SHA, HMAC, rational F and graph/proof oracles.
No Genesis, UE, GPU, account service or hostile same-UID isolation is claimed.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from dataclasses import asdict
import errno
from fractions import Fraction
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import selectors
import shutil
import signal
import stat
import struct
import subprocess
import sys
import time
import traceback

BASE='a4c86b382df01876a811af771df86af8a2fdb899'
REPO=Path(__file__).resolve().parents[1]
FIXTURES=REPO/'doc/fixtures/universe_authority_v0_2'
PREFIX=b'edgeworld.universe.authority\0v0.2\0'
WORLD='composite-demo'
PRINCIPAL='fixture-principal'
MAX_RAW=64*1024*1024
PHASES=('BLOB_FILE_SYNCED','BLOBS_DIR_SYNCED','W5_BEFORE_REPLACE',
        'W6_AFTER_REPLACE','W8_BEFORE_RESPONSE','RECOVERY_VALIDATED',
        'RECOVERY_BLOBS_SYNCED','W9_RECOVERY_SYNCED')

def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=True, sort_keys=True, indent=2)


def pairs(items):
    result = {}
    for key, value in items:
        assert key not in result, 'duplicate decoded key'
        result[key] = value
    return result


def read_json(raw):
    def bad(token):
        raise AssertionError('non-integer JSON token: ' + token)
    return json.loads(raw.decode('utf-8'), object_pairs_hook=pairs,
                      parse_float=bad, parse_constant=bad)


def quoted(value):
    out = bytearray(b'"')
    short = {8: b'\\b', 9: b'\\t', 10: b'\\n', 12: b'\\f', 13: b'\\r'}
    for ch in value:
        cp = ord(ch)
        assert not 0xD800 <= cp <= 0xDFFF
        if cp in short:
            out.extend(short[cp])
        elif cp in (34, 92):
            out.extend(bytes((92, cp)))
        elif 32 <= cp <= 126:
            out.append(cp)
        elif cp <= 0xFFFF:
            out.extend(('\\u%04x' % cp).encode())
        else:
            cp -= 0x10000
            out.extend(('\\u%04x\\u%04x' % (0xD800 + (cp >> 10),
                                             0xDC00 + (cp & 1023))).encode())
    out.append(34)
    return bytes(out)


def encode(value):
    """Independent ASCII JSON; no production codec or json.dumps canonical path."""
    if value is None:
        return b'null'
    if type(value) is bool:
        return b'true' if value else b'false'
    if type(value) is int:
        assert abs(value) <= 9007199254740991
        return str(value).encode()
    if type(value) is str:
        return quoted(value)
    if type(value) is list:
        return b'[' + b','.join(encode(x) for x in value) + b']'
    assert type(value) is dict and all(type(k) is str for k in value)
    return b'{' + b','.join(quoted(k) + b':' + encode(value[k])
                            for k in sorted(value)) + b'}'


def hashed(record):
    return hashlib.sha256(PREFIX + encode(record)).hexdigest()


def number(value):
    assert type(value) is dict and set(value) == {'$f64'}
    bits = value['$f64']
    assert type(bits) is str and len(bits) == 16 and set(bits) <= set('0123456789abcdef')
    result = struct.unpack('>d', bytes.fromhex(bits))[0]
    assert math.isfinite(result)
    return result


def file_map(root):
    """Original bytes, names and inode identity, excluding read-induced atime."""
    result = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        item = {'device': str(info.st_dev), 'inode': str(info.st_ino),
                'mode': info.st_mode, 'nlink': info.st_nlink}
        if stat.S_ISLNK(info.st_mode):
            item['symlink'] = os.readlink(path)
        elif stat.S_ISREG(info.st_mode):
            raw = path.read_bytes()
            item.update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(), raw_hex=raw.hex())
        else:
            assert stat.S_ISDIR(info.st_mode), 'unexpected file type'
        result[str(path.relative_to(root))] = item
    return result


class Child:
    def __init__(self, suite, directory, root, action, phase=''):
        self.suite, self.directory, self.root = suite, directory, root
        directory.mkdir()
        self.command = [sys.executable, '-m', 'scripts.run_universe_blob_trust_faults',
                        '--child', '--root', str(root), '--keys', str(suite.key_dir(root)),
                        '--action', action, '--phase', phase]
        self.started = time.monotonic()
        self.process = subprocess.Popen(self.command, cwd=REPO, stdin=subprocess.PIPE,
                                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=0)
        self.logs = {'out': (directory / 'stdout.jsonl').open('xb'),
                     'err': (directory / 'stderr.txt').open('xb')}
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ, 'out')
        self.selector.register(self.process.stderr, selectors.EVENT_READ, 'err')
        self.pending = b''
        self.packets, self.paused, self.finished = [], None, False
        self.killed = False
        self.cleanup_kill = False
        suite.children.append(self)
        save(directory / 'command.json', {'argv': self.command, 'cwd': str(REPO),
             'pid': self.process.pid, 'monotonic_start': self.started, 'source_head': suite.source})

    def pump(self, cleanup=False):
        wait = 0.02 if cleanup else min(0.05, self.suite.remaining())
        for key, _ in self.selector.select(wait):
            block = os.read(key.fileobj.fileno(), 65536)
            if not block:
                self.selector.unregister(key.fileobj)
                continue
            self.logs[key.data].write(block)
            self.logs[key.data].flush()
            if key.data == 'out':
                self.pending += block
                while b'\n' in self.pending:
                    raw, self.pending = self.pending.split(b'\n', 1)
                    packet = json.loads(raw)
                    assert packet['pid'] == self.process.pid
                    self.packets.append(packet)
                    if packet.get('type') == 'pause':
                        self.paused = packet

    def wait_pause(self, phase):
        until = time.monotonic() + min(8, self.suite.remaining())
        while self.paused is None:
            assert time.monotonic() < until, 'child pause timeout'
            self.pump()
            assert self.process.poll() is None, 'child exited before phase handshake'
        assert self.paused['phase'] == phase and self.process.poll() is None
        save(self.directory / 'phase-file-map.json', file_map(self.root))
        return self.paused

    def kill(self):
        assert self.paused and self.paused['pid'] == self.process.pid
        assert self.process.poll() is None
        # Popen retains ownership of this unreaped PID; never locate/kill globally.
        os.kill(self.process.pid, signal.SIGKILL)
        self.killed = True

    def abort(self):
        if self.process.poll() is None:
            os.kill(self.process.pid, signal.SIGKILL)
            self.cleanup_kill = True

    def finish(self, allow_failure=False):
        if self.finished:
            return self.packets[-1] if self.packets else None
        cleanup_errors = []
        try:
            # Cleanup has its own short budget even after the run deadline.
            until = time.monotonic() + (2 if allow_failure else min(8, self.suite.remaining()))
            while self.selector.get_map() or self.process.poll() is None:
                assert time.monotonic() < until, 'child completion timeout'
                self.pump(cleanup=allow_failure)
            code = self.process.wait(timeout=1)
            assert not self.pending, 'truncated JSONL line'
            if not allow_failure:
                assert code == (-signal.SIGKILL if self.killed or self.cleanup_kill else 0), ('child exit', code)
                assert not self.logs['err'].tell(), 'child stderr contains failure'
            return self.packets[-1] if self.packets else None
        finally:
            if self.process.poll() is None:
                try:
                    os.kill(self.process.pid, signal.SIGKILL)
                    self.cleanup_kill = True
                    self.process.wait(timeout=1)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    cleanup_errors.append(repr(exc))
            for pipe in (self.process.stdin, self.process.stdout, self.process.stderr):
                try:
                    pipe.close()
                except OSError as exc:
                    cleanup_errors.append(repr(exc))
            try:
                self.selector.close()
            except OSError as exc:
                cleanup_errors.append(repr(exc))
            for stream in self.logs.values():
                try:
                    stream.close()
                except OSError as exc:
                    cleanup_errors.append(repr(exc))
            self.finished = True
            self.suite.cleanup_errors.extend(cleanup_errors)
            save(self.directory / 'exit.json', {'pid': self.process.pid,
                 'returncode': self.process.returncode, 'real_sigkill': self.killed,
                 'cleanup_kill': self.cleanup_kill,
                 'cleanup_errors': cleanup_errors,
                 'elapsed_seconds': time.monotonic() - self.started})



def constants():
    return read_json((FIXTURES/'trust_context.json').read_bytes())


def golden_check():
    archive=read_json((FIXTURES/'positive.json').read_bytes())
    gold=read_json((FIXTURES/'golden.json').read_bytes())
    assert len(archive['records'])==len(gold)==67
    for row, fixed in zip(archive['records'],gold):
        assert encode(row).hex()==fixed['canonical_hex'] and hashed(row)==fixed['sha256']
    return {'records':67,'method':'independent recursive ASCII encoder, prefixed SHA256'}


def anchor(key, root):
    return hashlib.sha256(b'edgeworld.universe.trust-anchor\0v0.2\0'+WORLD.encode()+b'\0'+str(root).encode()+b'\0'+key).hexdigest()


def check_mac(record,key,ctx):
    unsigned=deepcopy(record); tag=unsigned['body'].pop('auth_tag')
    message=(b'edgeworld.universe.receipt\0v0.2\0'+ctx['trust_anchor'].encode()+b'\0'
             +record['kind'].encode()+b'\0'+encode(unsigned))
    assert hmac.compare_digest(hmac.new(key,message,hashlib.sha256).hexdigest(),tag),'independent MAC mismatch'


def independent_f(before,after):
    return round(1000*(Fraction.from_float(number(after))-Fraction.from_float(number(before))))


def typed(records, schema, *, partial=False):
    def tree(x,depth=0):
        assert depth<=32
        if type(x) is str:assert len(x.encode('utf-8'))<=4096
        elif type(x) is int:assert abs(x)<=9007199254740991
        elif type(x) is list:
            assert len(x)<=256
            for v in x:tree(v,depth+1)
        elif type(x) is dict:
            assert len(x)<=64
            if '$f64' in x:number(x)
            for k,v in x.items():tree(k,depth+1);tree(v,depth+1)
        else:assert x is None or type(x) is bool
    identities=set(); events=set()
    for d,r in records.items():
        tree(r)
        assert set(r)=={'domain','version','world_id','kind','id','body','refs'}
        assert r['domain']=='edgeworld.universe.authority' and r['version']=='0.2' and r['world_id']==WORLD
        assert d==hashed(r) and len(encode(r))<=schema['kind_bytes'][r['kind']]
        assert set(r['body'])==set(schema['body'][r['kind']])
        for name,spec in schema['body'][r['kind']].items():
            value=r['body'][name]
            if spec=='uint':assert type(value) is int and value>=0
            if spec=='f64':number(value)
            if spec=='nullable_mm':assert value is None or type(value) is int and abs(value)<=1000
            if spec in ('hash','nullable_hash') and value is not None:assert type(value) is str and len(value)==64 and set(value)<=set('0123456789abcdef')
            if spec=='json_object':assert type(value) is dict
        ident=(r['kind'],r['id']); assert ident not in identities; identities.add(ident)
        expected={k.rstrip('?'):v for k,v in schema['refs'][r['kind']].items()}
        if r['kind']=='manifest' and r['body']['revision']==0: expected={'state':'state'}
        if r['kind']=='event' and 'prior_event' not in r['refs']: expected.pop('prior_event')
        if r['kind']=='route': expected={'p'+str(i):'place' for i in range(len(r['body']['place_ids']))}
        assert set(r['refs'])==set(expected)
        for name,ref in r['refs'].items():
            assert type(ref) is str and len(ref)==64
            if ref not in records: assert partial
            else: assert records[ref]['kind']==expected[name]
        if r['kind']=='event': assert r['body']['event_id'] not in events; events.add(r['body']['event_id'])


def transition(records,d):
    m=records[d]; b=m['body']; state=records[m['refs']['state']]; sb=state['body']
    assert b=={k:sb['revision'] if k=='watermark' else sb[k] for k in ('tick','revision','watermark')}
    snapshot=records[state['refs']['snapshot']]
    assert sb['random_cursor']==sb['tick'] and snapshot['body']['physical_step_count']==8*sb['tick']
    assert sb['revision']>=sb['tick'] and (sb['development_mm'] is None)==(sb['tick']==0)
    if b['revision']==0:
        assert sb==dict(tick=0,revision=0,budget=8,random_cursor=0,development_mm=None)
        return
    prior=records[m['refs']['prior_manifest']]; old=records[prior['refs']['state']]; ob=old['body']
    event=records[m['refs']['event']]; admission=records[event['refs']['admission']]
    candidate=records[admission['refs']['candidate']]; command=records[admission['refs']['command']]
    intent=records[command['refs']['intent']]; ib=intent['body']; approval=records[command['refs']['approval']]
    proposal=records[command['refs']['proposal']]; index=records[m['refs']['index']]; result=records[index['refs']['result']]
    assert b['revision']==prior['body']['revision']+1
    assert event['refs']['state']==m['refs']['state']==result['refs']['state']
    assert event['refs'].get('prior_event')==prior['refs'].get('event')
    assert result['refs']['event']==m['refs']['event']
    assert candidate['refs']['prior_state']==prior['refs']['state']
    assert candidate['refs']['command']==admission['refs']['command']==result['refs']['command']
    assert candidate['refs']['snapshot']==state['refs']['snapshot']==result['refs']['checkpoint']
    assert state['refs']['world']==old['refs']['world']
    assert approval['refs']=={'proposal':command['refs']['proposal'],'intent':command['refs']['intent']}
    assert all(x==PRINCIPAL for x in (ib['principal'],approval['body']['principal'],proposal['body']['principal'],admission['body']['principal']))
    assert ib['expected_revision']==ob['revision']==admission['body']['evaluated_revision']<=approval['body']['expires_revision']
    assert ib['random_cursor']==ob['random_cursor']
    assert candidate['body']['revision']==sb['revision'] and candidate['body']['tick']==sb['tick']
    assert candidate['body']['influence_mm']==sb['development_mm']
    before=records[old['refs']['snapshot']]
    assert intent['refs']=={k:snapshot['refs'][k] for k in ('config','binding')}
    assert all(before['refs'][k]==snapshot['refs'][k] for k in ('config','binding'))
    if ib['action']=='retain_snapshot':
        assert ib['budget']==ib['tick_delta']==0 and ib['case_id'] is None
        assert candidate['body']['adapter_kind']=='checkpoint_reuse'
        assert old['refs']['snapshot']==state['refs']['snapshot']
        assert all(sb[k]==ob[k] for k in ('tick','budget','random_cursor','development_mm'))
    else:
        assert ib['action']=='physics_step' and ib['tick_delta']==1 and ib['case_id'] in ('weak','strong')
        assert snapshot['body']['case_id']==ib['case_id'] and candidate['body']['adapter_kind']=='genesis'
        assert sb['tick']==ob['tick']+1 and sb['budget']==ob['budget']-ib['budget']>=0
        assert sb['random_cursor']==ob['random_cursor']+1 and snapshot['body']['physical_step_count']==before['body']['physical_step_count']+8
        zold=records[before['refs']['sample']]['body']['bodies'][0]['position_m'][2]
        znew=records[snapshot['refs']['sample']]['body']['bodies'][0]['position_m'][2]
        assert sb['development_mm']==independent_f(zold,znew) and abs(sb['development_mm'])<=1000
    assert result['body']==dict(command_id=ib['command_id'],tick=sb['tick'],revision=sb['revision'],watermark=sb['revision'])
    assert index['body']==dict(command_id=ib['command_id'],fingerprint=result['refs']['command'])


def disk(root,key_dir):
    ctx=read_json((root.parent/'deployment.json').read_bytes())
    key=(key_dir/'authority.key').read_bytes()  # Never returned, serialized or logged.
    assert len(key)==32 and key!=bytes(range(32)) and anchor(key,root)==ctx['trust_anchor']
    identity=read_json((root/'identity.json').read_bytes()); info=root.stat()
    expected={'domain':'edgeworld.universe.authority','version':'0.2','world_id':WORLD,
              'profile':'local-posix-blob-sync-v0.2','root_canonical':str(root),
              'root_device':str(info.st_dev),'root_inode':str(info.st_ino),
              'trust_algorithm':ctx['trust_algorithm'],'trust_anchor':ctx['trust_anchor'],
              'expected_build':ctx['expected_build'],'expected_options':ctx['expected_options'],
              'artifact_class':ctx['artifact_class'],'archive_profile':'composite-rigid-support.v0.2'}
    assert identity==expected
    head=read_json((root/'HEAD.json').read_bytes()); assert encode(head)==(root/'HEAD.json').read_bytes()
    assert head==dict(domain=expected['domain'],version='0.2',world_id=WORLD,profile=expected['profile'],manifest=head['manifest'])
    records={}
    for path in sorted((root/'objects').glob('*.json')):
        raw=path.read_bytes(); row=read_json(raw); assert raw==encode(row)
        assert path.stem==hashed(row); records[path.stem]=row
    assert len(records)<=2048
    fixed={hashed(r) for r in read_json((FIXTURES/'positive.json').read_bytes())['records']}
    immutable={'existence','place','route','watercourse','asset_manifest','projection','unit_transform',
               'world_manifest','provider_build','resolved_options','physics_config','physics_binding'}
    assert all(d in fixed for d,r in records.items() if r['kind'] in immutable)
    schema=read_json((FIXTURES/'schema.json').read_bytes()); typed(records,schema)
    rawmeta={}
    for d,r in records.items():
        if r['kind'] in ('approval','admission'): check_mac(r,key,ctx)
        if r['kind']=='manifest': transition(records,d)
        if r['kind']=='checkpoint_descriptor':
            b=r['body']; assert b['artifact_class']=='synthetic-contract-only' and b['format']=='synthetic-static-bytes'
            path=root/'blobs'/(b['payload_sha256']+'.static'); payload=path.read_bytes()
            assert len(payload)==b['byte_count'] and hashlib.sha256(payload).hexdigest()==b['payload_sha256']
            meta=(b['byte_count'],b['media_type'],b['artifact_class'])
            assert b['payload_sha256'] not in rawmeta or rawmeta[b['payload_sha256']]==meta
            rawmeta[b['payload_sha256']]=meta
        if r['kind']=='provider_build': assert d==ctx['expected_build']
        if r['kind']=='resolved_options': assert d==ctx['expected_options']
    active=set(); reached=set()
    def visit(ref):
        assert ref in records and ref not in active
        if ref in reached:return
        active.add(ref)
        for childref in records[ref]['refs'].values():visit(childref)
        active.remove(ref); reached.add(ref)
    visit(head['manifest'])
    history=[]; commands=set(); current=head['manifest']
    while current:
        m=records[current]; state=records[m['refs']['state']]
        history.append(dict(manifest=current,state=state['body']))
        if 'index' in m['refs']:
            result=records[records[m['refs']['index']]['refs']['result']]
            command=records[result['refs']['command']]; intent=records[command['refs']['intent']]['body']
            ck=(intent['principal'],intent['command_id']); assert ck not in commands; commands.add(ck)
        current=m['refs'].get('prior_manifest')
    assert len(history)<=64
    return dict(head=head['manifest'],records=records,history=history,raw_meta=rawmeta,
                context=ctx,reachable=sorted(reached))


def proof_check(payload,binding,ctx,records):
    assert set(payload)=={'manifest','state','event','watermark','storage_state','artifact_class','head','membership','records','opaque_refs'}
    assert binding==dict(head=binding['head'],world_id=WORLD,authority_root=ctx['authority_root'],
                        trust_algorithm=ctx['trust_algorithm'],trust_anchor=ctx['trust_anchor'],
                        expected_build=ctx['expected_build'],expected_options=ctx['expected_options'],
                        artifact_class='synthetic-contract-only',domain='edgeworld.universe.authority',
                        version='0.2',profile='composite-rigid-support.v0.2',storage_state=binding['storage_state'])
    assert payload['head']==binding['head'] and payload['storage_state']==binding['storage_state']
    assert payload['artifact_class']==ctx['artifact_class']
    assert len(encode(payload))<1048576 and len(payload['membership'])<=64 and len(payload['records'])<=96
    explicit=payload['membership']+[payload['manifest'],payload['state']]+([] if payload['event'] is None else [payload['event']])
    aux=[hashed(r) for r in payload['records']]; ed={hashed(r) for r in explicit}
    assert len(aux)==len(set(aux)) and not set(aux)&ed
    supplied={hashed(r):r for r in explicit+payload['records']}
    assert all(ref in records and records[ref]==row for ref,row in supplied.items())
    typed(supplied,read_json((FIXTURES/'schema.json').read_bytes()),partial=True)
    chain=payload['membership']; selected=hashed(payload['manifest'])
    assert chain and hashed(chain[0])==binding['head'] and hashed(chain[-1])==selected
    assert len(set(hashed(r) for r in chain))==len(chain)
    for a,b in zip(chain,chain[1:]):
        assert a['kind']==b['kind']=='manifest' and a['refs']['prior_manifest']==hashed(b)
        assert a['body']['revision']==b['body']['revision']+1 and a['body']['tick']-b['body']['tick'] in (0,1)
    assert payload['manifest']['refs']['state']==hashed(payload['state'])
    assert payload['watermark']==payload['manifest']['body']['revision']
    assert (payload['event'] is None)==(payload['watermark']==0)
    if payload['event'] is not None:assert payload['manifest']['refs']['event']==hashed(payload['event'])
    needed=set(); done=set(); active=set()
    def expand(d,previous=False):
        assert d in supplied and (d,previous) not in active
        if (d,previous) in done:return
        active.add((d,previous)); needed.add(d); r=supplied[d]
        for name,ref in r['refs'].items():
            if r['kind']=='manifest' and (name=='prior_manifest' or previous and name!='state'):continue
            if r['kind']=='event' and name=='prior_event':continue
            expand(ref)
        active.remove((d,previous));done.add((d,previous))
    expand(selected)
    previous=payload['manifest']['refs'].get('prior_manifest')
    if previous:expand(previous,True)
    assert set(supplied)==needed|{hashed(r) for r in chain}
    opaque=sorted({ref for row in supplied.values() for ref in row['refs'].values() if ref not in supplied})
    assert payload['opaque_refs']==opaque
    transition(supplied,selected)
    return {'selected':selected,'tick':payload['manifest']['body']['tick'],'revision':payload['watermark'],
            'records':len(supplied),'scope':'selected-slice-membership-only-not-full-history-or-raw-validation',
            'storage_state':payload['storage_state']}


def child(args):
    # Only this branch imports production APIs; parent never uses their oracle.
    from engine.universe_authority.codec import ContractError, DeploymentContext, OwnerSession, ProvisionSpec, digest
    from engine.universe_authority.commands import execute, prepare_command
    from engine.universe_authority.ownership import acquire
    from engine.universe_authority.physics import PhysicsDraft, PhysicsIds
    from engine.universe_authority.recovery import recover, status, observe, head_binding
    from engine.universe_authority.records import verify_observation
    from engine.universe_authority.store import BlobWrite, Store
    from engine.universe_authority.trust import provision, open_trust
    root=Path(args.root); keys=Path(args.keys); store=lease=None
    def emit(kind,**values):
        print(json.dumps(dict(type=kind,pid=os.getpid(),**values),sort_keys=True),flush=True)
    counters=dict(sign=0,solve=0,admission=0)
    ctx=None; armed=False; post=False; injected=False
    native_sync=os.fsync; native_replace=os.replace
    initial_blobs={p.name for p in (root/'blobs').glob('*')} if (root/'blobs').exists() else set()
    def sync(fd):
        nonlocal injected
        st=os.fstat(fd); target=None
        if (root/'blobs').exists():
            if stat.S_ISDIR(st.st_mode) and st.st_ino==(root/'blobs').stat().st_ino:target='blob-dir'
            elif stat.S_ISREG(st.st_mode):
                for p in (root/'blobs').glob('*'):
                    if p.stat().st_ino==st.st_ino:
                        target='old-blob' if p.name in initial_blobs else 'new-blob';break
        if stat.S_ISDIR(st.st_mode) and root.exists() and st.st_ino==root.stat().st_ino:target='root-dir'
        fault=(args.action=='io-file' and target=='new-blob' or args.action=='io-dir' and target=='blob-dir'
               or args.action=='io-post' and post and target=='root-dir'
               or args.action=='unconfirmed' and target in ('old-blob','new-blob'))
        if armed and fault and not injected:
            injected=True;emit('actual-io-error',syscall='fsync',fd=fd,target=target,mode=st.st_mode,inode=str(st.st_ino))
            raise OSError(errno.EIO,'E6 controlled actual fsync error')
        return native_sync(fd)
    def replace(src,dst,*a,**kw):
        nonlocal injected
        if armed and args.action=='io-replace' and dst=='HEAD.json' and not injected:
            injected=True;emit('actual-io-error',syscall='replace',target=dst)
            raise OSError(errno.EIO,'E6 controlled actual replace error')
        return native_replace(src,dst,*a,**kw)
    def hook(phase,context):
        nonlocal post
        if phase=='W6_AFTER_REPLACE':post=True
        if armed:emit('phase',phase=phase,context=dict(context))
        match=armed and phase==args.phase
        if match and phase=='BLOB_FILE_SYNCED':
            match=context.get('object_digest','')+'.static' not in initial_blobs
        if match:
            emit('pause',phase=phase,context=dict(context))
            assert sys.stdin.buffer.readline()==b'continue\n'
    class Signer:
        def __init__(self,delegate):self.delegate=delegate
        def authorize_read(self,*a):return self.delegate.authorize_read(*a)
        def assert_context(self,*a):return self.delegate.assert_context(*a)
        def verify_approval(self,*a):return self.delegate.verify_approval(*a)
        def sign_approval(self,*a):
            counters['sign']+=1;emit('sign',count=counters['sign']);return self.delegate.sign_approval(*a)
        def admit(self,*a,**kw):
            counters['admission']+=1;emit('admission',count=counters['admission']);return self.delegate.admit(*a,**kw)
    class Provider:
        def propose(self,old,command,intent,*,records,read_blob,ids):
            counters['solve']+=1;emit('solve',count=counters['solve'])
            # Check only public values reach this honest cooperative provider.
            assert not hasattr(read_blob,'__self__') and not hasattr(read_blob,'__dict__')
            assert not any(hasattr(x,'commit') or hasattr(x,'sign_approval') for x in records.values())
            previous=records[old['refs']['snapshot']]
            checkpoint=records[previous['refs']['checkpoint']]
            assert hashlib.sha256(read_blob(checkpoint['body']['payload_sha256'])).hexdigest()==checkpoint['body']['payload_sha256']
            try:read_blob('f'*64)
            except ContractError:pass
            else:raise AssertionError('unbounded provider raw access')
            emit('provider-capability',raw_reader_bound=False,raw_reader_dict=False,store=False,key=False,signer=False,
                 model='cooperative local public-argument boundary, not OS sandbox')
            sample=deepcopy(next(r for r in template if r['id']=='sample-1'));sample['id']=ids.sample
            z=1.0-0.01*(old['body']['tick']+1)
            sample['body']['bodies'][0]['position_m'][2]={'$f64':struct.pack('>d',z).hex()}
            sample['refs']={k:intent['refs'][k] for k in ('config','binding')}
            payload=('E6 PUBLIC SYNTHETIC STATIC CHECKPOINT tick %d\n'%(old['body']['tick']+1)).encode()
            descriptor=deepcopy(next(r for r in template if r['id']=='checkpoint-1'))
            descriptor['id']=ids.checkpoint_descriptor
            descriptor['body'].update(payload_sha256=hashlib.sha256(payload).hexdigest(),byte_count=len(payload))
            descriptor['refs']={**sample['refs'],'build':records[intent['refs']['config']]['refs']['build']}
            snapshot=dict(domain=command['domain'],version='0.2',world_id=WORLD,kind='physics_snapshot',id=ids.snapshot,
                          body=dict(case_id=intent['body']['case_id'],physical_step_count=previous['body']['physical_step_count']+8),
                          refs={**sample['refs'],'sample':digest(sample),'checkpoint':digest(descriptor)})
            oldz=records[previous['refs']['sample']]['body']['bodies'][0]['position_m'][2]
            candidate=dict(domain=command['domain'],version='0.2',world_id=WORLD,kind='candidate',id=ids.candidate,
                           body=dict(adapter_kind='genesis',physics_profile='genesis-rigid-support.v0.1',tick=old['body']['tick']+1,
                                     revision=old['body']['revision']+1,influence_mm=independent_f(oldz,sample['body']['bodies'][0]['position_m'][2])),
                           refs=dict(command=digest(command),prior_state=digest(old),snapshot=digest(snapshot)))
            return PhysicsDraft((sample,descriptor,snapshot,candidate),digest(candidate),digest(snapshot),
                                BlobWrite(descriptor['body']['payload_sha256'],payload,descriptor['body']['media_type'],'synthetic-contract-only'))
    def inputs(label,action,stored=False):
        snapshot=store.snapshot();records=snapshot.closure.records
        if stored:
            wanted='command-'+label
            found=next((r for r in records.values() if r['kind']=='intent' and r['body']['command_id']==wanted),None)
            if found:
                cmd=next(r for r in records.values() if r['kind']=='command' and r['refs']['intent']==digest(found))
                return deepcopy(records[cmd['refs']['proposal']]),deepcopy(found)
        old=records[records[snapshot.closure.head]['refs']['state']]
        physical=records[old['refs']['snapshot']]
        p=dict(domain='edgeworld.universe.authority',version='0.2',world_id=WORLD,kind='proposal',id='proposal-'+label,
               body=dict(principal=PRINCIPAL,output='E6 synthetic explicit abstract action'),refs={})
        i=dict(domain=p['domain'],version='0.2',world_id=WORLD,kind='intent',id='intent-'+label,
               body=dict(principal=PRINCIPAL,command_id='command-'+label,expected_revision=old['body']['revision'],
                         random_cursor=old['body']['random_cursor'],action=action,tick_delta=int(action=='physics_step'),
                         case_id='weak' if action=='physics_step' else None,budget=int(action=='physics_step')),
               refs={k:physical['refs'][k] for k in ('config','binding')})
        return p,i
    def prepare(label,action='physics_step',stored=True):
        p,i=inputs(label,action,stored)
        return prepare_command(store,session=session,proposal=p,intent=i,approval_id='approval-'+label,
                               command_record_id='command-record-'+label,signer=signer)
    def advance(label,action='physics_step',retry=False):
        prepared=prepare(label,action)
        # A committed retry must ignore even a poison provider and nonsensical output IDs.
        class Poison:
            def propose(self,*a,**kw):raise AssertionError('committed retry/retain called provider')
        physical=PhysicsIds('candidate-'+label,'sample-'+label,'snapshot-'+label,'checkpoint-'+label) if action=='physics_step' else None
        receipt=execute(store,prepared.command_records,command_digest=prepared.command_digest,principal=PRINCIPAL,verifier=signer,
                        candidate_id='candidate-'+label,admission_id='admission-'+label,state_id='state-'+label,event_id='event-'+label,
                        result_id='result-'+label,index_id='index-'+label,manifest_id='manifest-'+label,
                        provider=Poison() if retry or action=='retain_snapshot' else Provider(),physics_ids=physical)
        emit('receipt',label=label,manifest=receipt.manifest,result=receipt.result,commit_status=receipt.commit_status)
        return prepared
    def observations():
        snap=store.snapshot(); binding=asdict(head_binding(snap));emit('status',payload=status(snap),binding=binding)
        for ref in snap.closure.retained:
            b=snap.closure.records[ref]['body'];payload=observe(snap,tick=b['tick'],revision=b['revision'],watermark=b['revision'])
            emit('proof',binding=binding,payload=payload)
            raw=encode(dict(protocol_version=1,request_id='e6-observe',ok=True,
                            result=dict(domain='edgeworld.universe.authority',version='0.2',world_id=WORLD,operation='observe',payload=payload)))
            verified=verify_observation(raw,context=ctx,expected_request_id='e6-observe',tick=b['tick'],revision=b['revision'],
                                        watermark=b['revision'],trusted_head=head_binding(snap))
            assert verified.manifest==ref
            if snap.storage_state=='unconfirmed_readonly':
                bad=deepcopy(payload);bad['storage_state']='ready'
                forged=encode(dict(protocol_version=1,request_id='e6-observe',ok=True,
                                  result=dict(domain='edgeworld.universe.authority',version='0.2',world_id=WORLD,operation='observe',payload=bad)))
                try:verify_observation(forged,context=ctx,expected_request_id='e6-observe',tick=b['tick'],revision=b['revision'],watermark=b['revision'],trusted_head=head_binding(snap))
                except ContractError as e:assert e.code=='PROOF';emit('label-flip-rejected',code=e.code)
                else:raise AssertionError('unconfirmed label upgraded')
    try:
        template=read_json((FIXTURES/'positive.json').read_bytes())['records']
        session=OwnerSession(PRINCIPAL,True,('retain_snapshot','physics_step'))
        if args.action=='seed':
            pub=provision(keys,spec=ProvisionSpec(WORLD,root));pins=constants()
            ctx=DeploymentContext(WORLD,str(root),pub.trust_anchor,pins['expected_build'],pins['expected_options'],artifact_class='synthetic-contract-only')
            save(root.parent/'deployment.json',asdict(ctx))
        else:
            values=read_json((root.parent/'deployment.json').read_bytes())
            if args.action=='public-runtime-key':values['artifact_class']='genesis-runtime'
            ctx=DeploymentContext(**values)
        verifier=open_trust(keys,context=ctx)
        signer=Signer(open_trust(keys,context=ctx,signing=True,session=session))
        lease=acquire(root,WORLD,initialize=args.action=='seed',domain_version='0.2',profile=ctx.storage_profile,context=ctx)
        store=Store(lease,context=ctx,trust_verifier=verifier,fault=hook)
        os.fsync=sync;os.replace=replace
        if args.action=='seed':
            initial=template[:31]; desc=next(r for r in initial if r['kind']=='checkpoint_descriptor')
            payload=bytes.fromhex(read_json((FIXTURES/'synthetic_blobs.json').read_bytes())['blobs'][desc['body']['payload_sha256']])
            store.initialize(initial,digest(initial[-1]),blobs=(BlobWrite(desc['body']['payload_sha256'],payload,desc['body']['media_type'],'synthetic-contract-only'),))
        else:
            armed=args.action in ('recoverkill','unconfirmed')
            report=recover(store)
            emit('recovered',storage_state=report.storage_state,confirmed=report.confirmed,error_code=report.error_code)
            armed=True
            if args.action in ('advance','io-file','io-dir','io-replace','io-post'):advance('one')
            elif args.action=='retry':advance('one',retry=store.snapshot().closure.records[store.snapshot().closure.head]['body']['revision']>0)
            elif args.action=='history':
                advance('retain0','retain_snapshot');advance('one');advance('retain1','retain_snapshot');advance('retain2','retain_snapshot')
            elif args.action.startswith('step-'):
                label,action=args.action[5:].split(':');advance(label,action)
            elif args.action=='prepare-tests':
                before_prepare=file_map(root)
                first=prepare('one'); second=prepare('one');assert first.command_records==second.command_records
                assert counters==dict(sign=2,solve=0,admission=0)
                assert before_prepare==file_map(root)
                emit('prepared',records=first.command_records,digest=first.command_digest,zero_authority_writes=True)
                stale=prepare('stale','retain_snapshot',stored=False)
                advance('one');before=dict(counters);retry=prepare('one');assert retry.committed_result is not None
                assert counters==before;advance('one',retry=True);assert counters==before
                p,i=inputs('one','physics_step',True);p['body']['output']='conflicting'
                try:prepare_command(store,session=session,proposal=p,intent=i,approval_id='approval-one',command_record_id='command-record-one',signer=signer)
                except ContractError as e:assert e.code=='COMMAND_CONFLICT';emit('conflict-rejected',code=e.code)
                else:raise AssertionError('prepare conflict accepted')
                try:prepare_command(store,session=session,proposal=stale.command_records[0],intent=stale.command_records[1],approval_id='approval-stale',command_record_id='command-record-stale',signer=signer)
                except ContractError as e:assert e.code=='HEAD';emit('stale-prepare-rejected',code=e.code)
                else:raise AssertionError('stale uncommitted prepare accepted')
                assert counters==before
            if args.action=='unconfirmed':
                try:prepare('blocked')
                except ContractError as e:assert e.code=='NOT_READY';emit('unconfirmed-write-rejected',code=e.code)
                else:raise AssertionError('unconfirmed write prepared')
        observations()
        emit('terminal',code='OK',storage_state=store.state,counters=counters,injected=injected)
    except ContractError as exc:
        errors={}
        if store is not None:
            for op in ('snapshot','status','observe'):
                try:
                    snap=store.snapshot()
                    if op=='status':status(snap)
                    if op=='observe':observe(snap,tick=0,revision=0,watermark=0)
                except ContractError as read_error:errors[op]=read_error.code
        emit('terminal',code=exc.code,commit_status=getattr(exc,'commit_status','not_attempted'),phase=getattr(exc,'phase',None),
             storage_state=store.state if store else None,counters=counters,read_errors=errors,injected=injected)
    finally:
        os.fsync=native_sync;os.replace=native_replace
        if store:store.close()
        if lease:lease.close()


class Suite:
    def __init__(self,output):
        self.output=Path(output);self.output.mkdir(parents=False)
        self.keybase=self.output.parent/(self.output.name+'-owner-keys')
        self.keybase.mkdir(mode=0o700)
        self.deadline=time.monotonic()+110
        self.children=[];self.results=[];self.cleanup_errors=[]
        self.source=subprocess.check_output(['git','rev-parse','HEAD'],cwd=REPO,text=True).strip()
        self.inputs=self.hash_inputs()
        save(self.output/'inputs-before.json',self.inputs)
        save(self.output/'environment.json',dict(python=sys.version,platform=sys.platform,release=os.uname().release,
             machine=os.uname().machine,source=self.source,base=BASE,budget_seconds=120,internal_deadline=110,
             raw_limit=MAX_RAW,owner_key_directory=str(self.keybase),argv=sys.argv))
    def key_dir(self,root):
        return self.keybase/hashlib.sha256(str(root.parent).encode()).hexdigest()[:16]
    def remaining(self):
        n=self.deadline-time.monotonic();assert n>0,'global 110s deadline';return n
    def hash_inputs(self):
        paths=[*sorted((REPO/'engine/universe_authority').glob('*.py')),*sorted(FIXTURES.glob('*')),
               Path(__file__),REPO/'tests/test_universe_blob_trust_process_faults.py',REPO/'doc/contracts/universe_authority_v0_2.md']
        return {str(p.relative_to(REPO)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths if p.is_file()}
    def call(self,path,root,action,phase=''):
        c=Child(self,path,root,action,phase);end=c.finish();return c,end
    def seed(self,case,history=False):
        root=case/'authority';_,end=self.call(case/'seed',root,'seed');assert end['code']=='OK',end
        if history:
            _,end=self.call(case/'populate',root,'history');assert end['code']=='OK',end
        return root
    def disk(self,root):return disk(root,self.key_dir(root))
    def capture(self,path,root):
        data=self.disk(root);save(path,dict(observation=data,files=file_map(root)));return data
    def inspected(self,case,root,label='recover'):
        before=file_map(root);data=self.disk(root)
        c,end=self.call(case/label,root,'inspect');assert end['code']=='OK' and end['storage_state']=='ready',end
        self.proofs(c,data);assert before==file_map(root),'read/recovery changed authoritative bytes/inodes'
        return end
    def proofs(self,c,data):
        rows=[p for p in c.packets if p['type']=='proof']
        assert len(rows)==len(data['history'])
        verified=[]
        for p in rows:
            assert p['binding']['head']==data['head']
            verified.append(proof_check(p['payload'],p['binding'],data['context'],data['records']))
        assert {(v['tick'],v['revision']) for v in verified}=={(x['state']['tick'],x['state']['revision']) for x in data['history']}
        save(c.directory/'independent-proofs.json',verified)
    def case(self,name,function):
        case=self.output/name;case.mkdir();start=time.monotonic();idx=len(self.children)
        try:
            detail=function(case);row=dict(case=name,status='pass',detail=detail,seconds=time.monotonic()-start)
        except Exception as e:
            (case/'failure.txt').write_text(traceback.format_exc())
            row=dict(case=name,status='fail',error=str(e),seconds=time.monotonic()-start)
            for c in self.children[idx:]:
                if not c.finished:
                    try:c.abort();c.finish(allow_failure=True)
                    except Exception as cleanup:self.cleanup_errors.append(repr(cleanup))
        self.results.append(row);save(case/'result.json',row)
        self.remaining();assert sum(p.stat().st_size for p in self.output.rglob('*') if p.is_file() and not p.is_symlink())<MAX_RAW
    def killcase(self,case,phase):
        recovery=phase.startswith('RECOVERY') or phase=='W9_RECOVERY_SYNCED'
        root=self.seed(case,history=recovery);before=self.capture(case/'before.json',root)
        c=Child(self,case/'killed',root,'recoverkill' if recovery else 'advance',phase)
        marker=c.wait_pause(phase);c.kill();c.finish()
        data=self.capture(case/'after-kill.json',root)
        expected=4 if recovery else int(phase in ('W6_AFTER_REPLACE','W8_BEFORE_RESPONSE'))
        assert data['history'][0]['state']['revision']==expected
        self.inspected(case,root)
        if not recovery:
            c,end=self.call(case/'retry',root,'retry');assert end['code']=='OK',end
            counts=end['counters'];assert counts==dict(sign=1-expected,solve=1-expected,admission=1-expected),counts
            final=self.capture(case/'final.json',root);self.proofs(c,final)
            assert final['history'][0]['state']==dict(tick=1,revision=1,budget=7,random_cursor=1,development_mm=-10)
        return dict(phase=phase,killed_pid=c.process.pid if recovery else marker['pid'],recovered_revision=expected,
                    visibility_attempted=marker['context']['visibility_attempted'],old_head=before['head'],recovered_head=data['head'])
    def iocase(self,case):
        variants=[]
        for action in ('io-file','io-dir','io-replace','io-post'):
            part=case/action;part.mkdir();root=self.seed(part);self.capture(part/'before.json',root)
            c,end=self.call(part/'fault',root,action)
            post=action in ('io-replace','io-post')
            assert end['code']==('COMMIT_UNKNOWN' if post else 'SYNC_UNSUPPORTED'),end
            assert end['injected'] and end['commit_status']==('unknown' if post else 'not_attempted')
            assert end['storage_state']=='recovering' and set(end['read_errors'].values())=={'NOT_READY'}
            assert any(x['type']=='actual-io-error' for x in c.packets)
            expected=int(action=='io-post');assert self.disk(root)['history'][0]['state']['revision']==expected
            self.capture(part/'after-error.json',root);self.inspected(part,root)
            c,retry=self.call(part/'retry',root,'retry');assert retry['code']=='OK'
            assert retry['counters']==dict(sign=1-expected,solve=1-expected,admission=1-expected)
            self.capture(part/'final.json',root)
            variants.append(dict(action=action,error=end['code'],status=end['commit_status'],revision_after_error=expected))
        return variants
    def security(self,case):
        root=self.seed(case);keys=self.key_dir(root);keyfile=keys/'authority.key'
        secret=keyfile.read_bytes();deployment=(case/'deployment.json').read_bytes()
        original=file_map(root);variants=[]
        try:
            for mode,code in (('missing','AUTHORIZATION'),('wrong','AUTHORIZATION'),('public','AUTHORIZATION'),('copy','ROOT_MISMATCH'),('alias','ROOT_MISMATCH')):
                target=root;action='inspect'
                if mode=='missing':keyfile.rename(keys/'held.key')
                elif mode=='wrong':keyfile.write_bytes(b'X'*32)
                elif mode=='public':
                    keyfile.write_bytes(bytes(range(32)));ctx=read_json(deployment)
                    ctx['trust_anchor']=anchor(bytes(range(32)),root);(case/'deployment.json').write_bytes(encode(ctx));action='public-runtime-key'
                elif mode=='copy':
                    target=case/'copy';shutil.copytree(root,target)
                else:target=case/'alias';target.symlink_to(root,target_is_directory=True)
                before=file_map(target) if mode!='alias' else original
                c,end=self.call(case/('reject-'+mode),target,action)
                assert end['code']==code,end
                assert original==file_map(root)
                assert before==(file_map(target) if mode!='alias' else file_map(root))
                variants.append(dict(mode=mode,code=end['code'],zero_authority_writes=True,pid=c.process.pid))
                if mode=='missing':(keys/'held.key').rename(keyfile)
                else:keyfile.write_bytes(secret)
                (case/'deployment.json').write_bytes(deployment)
        finally:
            if (keys/'held.key').exists():(keys/'held.key').rename(keyfile)
            keyfile.write_bytes(secret);(case/'deployment.json').write_bytes(deployment)
        self.inspected(case,root)
        return variants
    def prepared(self,case):
        root=self.seed(case);before=self.capture(case/'before.json',root)
        c,end=self.call(case/'prepare-and-retry',root,'prepare-tests');assert end['code']=='OK',end
        assert end['counters']==dict(sign=4,solve=1,admission=1)
        data=self.capture(case/'after.json',root);self.proofs(c,data)
        assert len(data['history'])==2
        assert sum(x['type']=='conflict-rejected' for x in c.packets)==1
        packet=next(x for x in c.packets if x['type']=='prepared')
        assert len(packet['records'])==4 and before['history'][0]['state']['revision']==0
        key=(self.key_dir(root)/'authority.key').read_bytes()
        check_mac(packet['records'][2],key,data['context'])
        self.inspected(case,root)
        return dict(counters=end['counters'],committed_retry_no_resign_or_solve=True)
    def history(self,case):
        root=self.seed(case);c,end=self.call(case/'history',root,'history');assert end['code']=='OK',end
        assert end['counters']==dict(sign=4,solve=1,admission=4)
        data=self.capture(case/'history.json',root);self.proofs(c,data)
        assert [(x['state']['tick'],x['state']['revision']) for x in data['history']]==[(1,4),(1,3),(1,2),(0,1),(0,0)]
        snapshots=[data['records'][x['manifest']]['refs']['state'] for x in data['history']]
        snaps=[data['records'][s]['refs']['snapshot'] for s in snapshots]
        assert snaps[0]==snaps[1]==snaps[2] and snaps[3]==snaps[4]
        assert len(data['raw_meta'])==2
        self.inspected(case,root)
        return dict(history=[x['state'] for x in data['history']],raw_files=len(data['raw_meta']),counters=end['counters'])
    def rawcorrupt(self,case):
        variants=[]
        for mode in ('missing','corrupt'):
            part=case/mode;part.mkdir();root=self.seed(part,history=True)
            data=self.capture(part/'before.json',root)
            initial=data['records'][data['records'][data['history'][-1]['manifest']]['refs']['state']]
            snapshot=data['records'][initial['refs']['snapshot']]
            desc=data['records'][snapshot['refs']['checkpoint']]
            path=root/'blobs'/(desc['body']['payload_sha256']+'.static')
            assert initial['refs']['snapshot']!=data['records'][data['records'][data['head']]['refs']['state']]['refs']['snapshot']
            if mode=='missing':path.unlink()
            else:path.write_bytes(b'!'+path.read_bytes()[1:])
            damaged=file_map(root);save(part/'damaged.json',damaged)
            try:self.disk(root)
            except (AssertionError,OSError):pass
            else:raise AssertionError('independent raw oracle accepted damage')
            _,end=self.call(part/'refuse',root,'inspect');assert end['code']=='CORRUPT',end
            assert set(end['read_errors'].values())=={'NOT_READY'} and damaged==file_map(root)
            variants.append(dict(mode=mode,code=end['code'],historical_only=True,zero_repair=True))
        return variants
    def maccorrupt(self,case):
        variants=[]
        for kind in ('approval','admission'):
            part=case/kind;part.mkdir();root=self.seed(part,history=True)
            data=self.capture(part/'before.json',root);records=data['records'];changed={};newrows={}
            target=next(d for d,r in records.items() if r['kind']==kind)
            def rewrite(d):
                if d in changed:return changed[d]
                row=deepcopy(records[d]);row['refs']={k:rewrite(v) for k,v in row['refs'].items()}
                if d==target:row['body']['auth_tag']='0'*64
                # Fingerprints are references encoded in an index body as well.
                if row['kind']=='index':row['body']['fingerprint']=rewrite(row['body']['fingerprint'])
                nd=hashed(row);changed[d]=nd;newrows[nd]=row;return nd
            newhead=rewrite(data['head'])
            for d,row in newrows.items():
                path=root/'objects'/(d+'.json')
                if not path.exists():path.write_bytes(encode(row))
            h=read_json((root/'HEAD.json').read_bytes());h['manifest']=newhead;(root/'HEAD.json').write_bytes(encode(h))
            # Confirm exact hashes and typed closure despite the deliberately bad MAC.
            typed(newrows,read_json((FIXTURES/'schema.json').read_bytes()))
            for d,row in newrows.items():assert hashed(row)==d
            try:check_mac(newrows[changed[target]],(self.key_dir(root)/'authority.key').read_bytes(),data['context'])
            except AssertionError:pass
            else:raise AssertionError('independent MAC accepted invalid tag')
            damaged=file_map(root);save(part/'coherent-damage.json',damaged)
            _,end=self.call(part/'refuse',root,'inspect');assert end['code']=='CORRUPT',end
            assert damaged==file_map(root) and set(end['read_errors'].values())=={'NOT_READY'}
            variants.append(dict(kind=kind,hashes_and_typed_graph_valid=True,code=end['code'],no_fallback=True))
        return variants
    def unconfirmed(self,case):
        root=self.seed(case,history=True);before=file_map(root);data=self.disk(root)
        c,end=self.call(case/'unconfirmed',root,'unconfirmed');assert end['code']=='OK' and end['injected'],end
        assert end['storage_state']=='unconfirmed_readonly' and end['counters']==dict(sign=0,solve=0,admission=0)
        self.proofs(c,data)
        rows=[x for x in c.packets if x['type']=='proof'];assert all(x['binding']['storage_state']==x['payload']['storage_state']=='unconfirmed_readonly' for x in rows)
        assert sum(x['type']=='label-flip-rejected' for x in c.packets)==len(rows)
        for row in rows:
            bad=deepcopy(row['payload']);bad['storage_state']='ready'
            try:proof_check(bad,row['binding'],data['context'],data['records'])
            except AssertionError:pass
            else:raise AssertionError('parent accepted ready laundering')
        assert before==file_map(root)
        self.inspected(case,root)
        save(case/'readonly-map.json',before)
        return dict(proofs=len(rows),zero_writes=True,recovery_sync_error_real=True)
    def segmented(self,case):
        # Same registered root/key, branch two histories from the same genesis bytes.
        # Re-creating at a different root would legitimately change MAC/head identity.
        root=self.seed(case);genesis=file_map(root)
        root_inode=root.stat().st_ino;lock_inode=(root/'.authority.lock').stat().st_ino
        backup=case/'genesis-copy';shutil.copytree(root,backup)
        c,end=self.call(case/'continuous',root,'history');assert end['code']=='OK'
        continuous=self.capture(case/'continuous.json',root)
        # Explicit test fixture rewind: keep registered root inode/lock identity; this
        # is not an authorized production migration/rollback capability.
        assert all(c.finished and c.process.poll() is not None for c in self.children)
        save(case/'before-rewind.json',file_map(root))
        for p in sorted(root.rglob('*'),reverse=True):
            rel=str(p.relative_to(root))
            if rel not in genesis:
                if p.is_file():p.unlink()
        for rel,item in genesis.items():
            if 'raw_hex' in item:(root/rel).write_bytes(bytes.fromhex(item['raw_hex']))
        assert root.stat().st_ino==root_inode and (root/'.authority.lock').stat().st_ino==lock_inode
        save(case/'after-rewind.json',file_map(root))
        assert file_map(root)==genesis
        labels=(('retain0','retain_snapshot'),('one','physics_step'),('retain1','retain_snapshot'),('retain2','retain_snapshot'))
        for idx,(label,action) in enumerate(labels):
            _,end=self.call(case/('step-'+str(idx)),root,'step-'+label+':'+action);assert end['code']=='OK',end
            self.inspected(case,root,'restart-'+str(idx))
        segmented=self.capture(case/'segmented.json',root)
        assert continuous==segmented
        return dict(identical_logical_records_head_history_raw=True,same_registered_root_and_key=True,
                    fixture_only_rewind=True,provider_boundary='public args and immutable bounded raw reader; not hostile UID isolation')
    def run(self):
        started=time.monotonic()
        try:
            gold=golden_check()
            for phase in PHASES:self.case('kill-'+phase.lower(),lambda c,p=phase:self.killcase(c,p))
            for name,method in (('actual-io',self.iocase),('key-and-root',self.security),('prepared-retries',self.prepared),
                                ('same-tick-history',self.history),('historical-raw',self.rawcorrupt),('historical-mac',self.maccorrupt),
                                ('unconfirmed-proof',self.unconfirmed),('segmented-equivalence',self.segmented)):
                self.case(name,method)
            after=self.hash_inputs();save(self.output/'inputs-after.json',after);assert self.inputs==after
            keyinfo=[]
            for p in sorted(self.keybase.rglob('*')):
                if p.is_file():
                    info=p.stat();keyinfo.append(dict(path=str(p),mode=stat.S_IMODE(info.st_mode),bytes=info.st_size,nlink=info.st_nlink,
                                                     sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
            save(self.output/'owner-key-public-metadata.json',keyinfo)
            summary=dict(source_head=self.source,base=BASE,goldens=gold,cases=self.results,children=len(self.children),
                         real_sigkills=sum(c.killed for c in self.children),cleanup_kills=sum(c.cleanup_kill for c in self.children),
                         all_children_reaped=all(c.process.poll() is not None for c in self.children),cleanup_errors=self.cleanup_errors,
                         inputs_unchanged=True,seconds=time.monotonic()-started,
                         passed=len(self.results)==16 and all(r['status']=='pass' for r in self.results) and not self.cleanup_errors
                         and sum(c.killed for c in self.children)==8 and not any(c.cleanup_kill for c in self.children),
                         scope='synthetic-only local POSIX process/blob/trust; no power-loss, Genesis, UE or sandbox claim')
            save(self.output/'summary.json',summary);return summary
        finally:
            for c in self.children:
                if not c.finished:
                    try:c.abort();c.finish(allow_failure=True)
                    except Exception as e:self.cleanup_errors.append(repr(e))


def finalize_index(output):
    rows=[dict(path=str(p.relative_to(output)),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
          for p in sorted(output.rglob('*')) if p.is_file() and not p.is_symlink()]
    assert sum(r['bytes'] for r in rows)<MAX_RAW
    save(output/'raw-index.json',dict(files=rows,total_bytes=sum(r['bytes'] for r in rows)))


def run_suite(output):
    output=Path(output)
    # Never touch an existing directory, file, symlink or dangling symlink.
    if output.exists() or output.is_symlink():raise FileExistsError(str(output))
    suite=None
    try:
        suite=Suite(output);return suite.run()
    except BaseException:
        if output.is_dir():save(output/'failed-run.json',dict(traceback=traceback.format_exc(),cases=suite.results if suite else []))
        raise
    finally:
        if output.is_dir():finalize_index(output)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--child',action='store_true')
    p.add_argument('--root');p.add_argument('--keys');p.add_argument('--action');p.add_argument('--phase',default='')
    p.add_argument('--output',type=Path);args=p.parse_args()
    if args.child:child(args)
    else:
        if args.output is None:p.error('--output required')
        result=run_suite(args.output);print(json.dumps(dict(passed=result['passed'],cases=len(result['cases']),children=result['children'])))
        raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
