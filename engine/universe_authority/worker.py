"""Owned single-root JSONL boundary. Runtime imports are lazy and owner controlled."""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict, fields
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

from .codec import ContractError, DeploymentContext, OwnerSession, DOMAIN, canonical, decode, digest
from .records import wire, validate_record
from .ownership import acquire
from .store import Store, StoreError
from .trust import open_trust
from .physics import PhysicsIds, PhysicsInitialIds
from .commands import prepare_command, execute
from .recovery import recover, status, observe, head_binding
from .world_initialization import compose_static_world, compose_initial_world

_ID = re.compile(r'[a-z][a-z0-9._-]{0,63}\Z')
_HEX = re.compile(r'[0-9a-f]{64}\Z')
_PAYLOAD = {
 'initialize': {'domain','version','world_id','test_profile'},
 'status': {'domain','version','world_id'},
 'observe': {'domain','version','world_id','tick','revision','watermark'},
 'prepare': {'domain','version','world_id','principal','proposal','intent','approval_id','command_record_id'},
 'advance': {'domain','version','world_id','principal','command_records','command_digest'},
}


def require(value, code='SCHEMA'):
    if not value:
        raise ContractError(code)


def exact(value, keys):
    require(type(value) is dict and set(value) == set(keys))


def absolute(value):
    require(type(value) is str and value.startswith('/') and str(Path(value).resolve()) == value, 'PATH')
    return Path(value)


def secure_read(path, limit, *, private=False):
    """Read once without following aliases, then verify descriptor/path identity."""
    path = absolute(str(path))
    parent = path.parent.stat()
    require(parent.st_uid == os.getuid() and (not private or stat.S_IMODE(parent.st_mode) == 0o700), 'OWNERSHIP')
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        before = os.fstat(fd)
        require(stat.S_ISREG(before.st_mode) and before.st_uid == os.getuid() and before.st_nlink == 1, 'OWNERSHIP')
        require(not private or stat.S_IMODE(before.st_mode) == 0o600, 'OWNERSHIP')
        require(before.st_size <= limit, 'LIMIT')
        chunks, count = [], 0
        while True:
            block = os.read(fd, min(65536, limit + 1 - count))
            if not block:
                break
            chunks.append(block); count += len(block)
            require(count <= limit, 'LIMIT')
        after = os.fstat(fd)
        final = os.stat(path, follow_symlinks=False)
        identity = lambda s: (s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns,s.st_nlink,s.st_uid,s.st_mode)
        require(identity(before) == identity(after) == identity(final), 'OWNERSHIP')
        return b''.join(chunks)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class OwnerConfig:
    context: DeploymentContext
    session: OwnerSession
    mode: str
    key_dir: Path
    scratch: Path
    input_specs: tuple
    path: Path


def load_owner_config(path):
    path = absolute(path)
    value = decode(secure_read(path, 65536, private=True))
    exact(value, {'config_version','mode','context','session','key_dir','scratch','inputs'})
    require(value['config_version'] == 'universe-owner-launch.v0.1')
    require(type(value['mode']) is str and value['mode'] in ('existing','initialize'))
    exact(value['context'], {f.name for f in fields(DeploymentContext)})
    context = DeploymentContext(**value['context'])
    require(context.artifact_class == 'genesis-runtime', 'PROFILE')
    exact(value['session'], {'principal','can_initialize','allowed_actions'})
    require(type(value['session']['allowed_actions']) is list)
    session = OwnerSession(value['session']['principal'],value['session']['can_initialize'],tuple(value['session']['allowed_actions']))
    require(value['mode'] != 'initialize' or session.can_initialize, 'AUTHORIZATION')
    key_dir, scratch = absolute(value['key_dir']), absolute(value['scratch'])
    root = absolute(context.authority_root)
    require(not key_dir.is_relative_to(root) and not root.is_relative_to(key_dir), 'PATH')
    exact(value['inputs'], {'build','options','assets','asset_audit'})
    specs = []
    for name, spec in sorted(value['inputs'].items()):
        exact(spec, {'path','sha256'})
        input_path = absolute(spec['path'])
        require(type(spec['sha256']) is str and _HEX.fullmatch(spec['sha256']), 'SCHEMA')
        specs.append((name,str(input_path),spec['sha256']))
    protected = [root,key_dir,path] + [Path(p) for _,p,_ in specs]
    require(all(not p.is_relative_to(scratch) and not scratch.is_relative_to(p) for p in protected), 'PATH')
    return OwnerConfig(context,session,value['mode'],key_dir,scratch,tuple(specs),path)


def public_pins(owner):
    c = owner.context
    return dict(domain=DOMAIN,version='0.2',profile=c.archive_profile,
        **{key:getattr(c,key) for key in ('world_id','authority_root','trust_algorithm','trust_anchor',
                                         'artifact_class','expected_build','expected_options')},
        principal=owner.session.principal,allowed_actions=list(owner.session.allowed_actions))


def load_inputs(owner):
    result = {}
    for name,path,sha in owner.input_specs:
        raw = secure_read(Path(path), 1048576)
        require(hashlib.sha256(raw).hexdigest() == sha, 'REFERENCE')
        value = decode(raw)
        if name != 'asset_audit':
            validate_record(value)
        result[name] = value
    return result


def runtime_provider(*, context, static, inputs, scratch):
    # Literal trusted dependency; never import a module named by JSON.
    from engine.universe_authority.genesis_adapter import GenesisProvider
    return GenesisProvider(context=context, config=static.by_kind('physics_config'),
                           binding=static.by_kind('physics_binding'), build=inputs['build'],
                           options=inputs['options'], scratch=scratch)


class Runtime:
    def __init__(self, owner, inputs, *, provider_factory=runtime_provider):
        self.owner, self.provider, self.store, self.lease = owner, None, None, None
        self.startup_error = None
        self.static = compose_static_world(owner.context,build=inputs['build'],options=inputs['options'],assets=inputs['assets'])
        try:
            require(not owner.scratch.exists(), 'PATH')
            self.verifier = open_trust(owner.key_dir,context=owner.context)
            self.signer = open_trust(owner.key_dir,context=owner.context,signing=True,session=owner.session)
            self.lease = acquire(Path(owner.context.authority_root),owner.context.world_id,
                initialize=owner.mode == 'initialize',domain_version='0.2',profile=owner.context.storage_profile,context=owner.context)
            self.store = Store(self.lease,context=owner.context,trust_verifier=self.verifier)
            if owner.mode == 'existing':
                recover(self.store)
            self.provider = provider_factory(context=owner.context,static=self.static,inputs=inputs,scratch=owner.scratch)
        except (ContractError,StoreError) as exc:
            self.startup_error = exc

    def binding(self):
        self.lease.check()
        return asdict(head_binding(self.store.snapshot()))

    def close(self):
        first = None
        for resource in (self.provider,self.store,self.lease):
            if resource is not None:
                try:
                    resource.close()
                except Exception as exc:
                    first = first or exc
        if first:
            raise first


def open_runtime(owner, inputs, *, provider_factory=runtime_provider):
    return Runtime(owner,inputs,provider_factory=provider_factory)


def dispatch(runtime, request):
    exact(request, {'protocol_version','request_id','operation','payload'})
    require(type(request['protocol_version']) is int and request['protocol_version'] == 1, 'PROTOCOL')
    require(type(request['request_id']) is str and _ID.fullmatch(request['request_id']), 'ID')
    op, p = request['operation'], request['payload']
    require(type(op) is str and op in _PAYLOAD, 'OPERATION')
    exact(p,_PAYLOAD[op])
    c, session = runtime.owner.context, runtime.owner.session
    require(p['domain'] == DOMAIN and p['version'] == '0.2', 'DOMAIN')
    require(p['world_id'] == c.world_id, 'WORLD')
    if runtime.startup_error:
        raise runtime.startup_error
    runtime.lease.check()
    if op == 'initialize':
        require(p['test_profile'] == c.archive_profile, 'PROFILE')
        require(runtime.owner.mode == 'initialize' and session.can_initialize and runtime.lease.initializing, 'AUTHORIZATION')
        # Store independently refuses a pre-existing HEAD before provider work.
        require(runtime.store.state == 'uninitialized', 'ALREADY_INITIALIZED')
        physics = runtime.provider.initialize(ids=PhysicsInitialIds('sample-0','snapshot-0','checkpoint-0'))
        bundle = compose_initial_world(runtime.static,physics,context=c,verifier=runtime.verifier)
        receipt = runtime.store.initialize(bundle.records,bundle.head,blobs=bundle.blobs)
        payload = dict(manifest=receipt.manifest,result=receipt.result,commit_status=receipt.commit_status,head_binding=runtime.binding())
    elif op == 'status':
        runtime.signer.authorize_read(session.principal,c.world_id)
        payload = status(runtime.store.snapshot())
        runtime.binding()
    elif op == 'observe':
        runtime.signer.authorize_read(session.principal,c.world_id)
        require(all(type(p[k]) is int for k in ('tick','revision','watermark')), 'INTEGER')
        payload = observe(runtime.store.snapshot(),tick=p['tick'],revision=p['revision'],watermark=p['watermark'])
        runtime.binding()
    else:
        require(p['principal'] == session.principal, 'AUTHORIZATION')
        if op == 'prepare':
            prepared = prepare_command(runtime.store,session=session,proposal=p['proposal'],intent=p['intent'],
                approval_id=p['approval_id'],command_record_id=p['command_record_id'],signer=runtime.signer)
            payload = dict(command_records=list(prepared.command_records),command_digest=prepared.command_digest,
                           committed_result=prepared.committed_result,head_binding=runtime.binding())
        else:
            require(type(p['command_digest']) is str and _HEX.fullmatch(p['command_digest']), 'REFERENCE')
            suffix = p['command_digest'][:40]
            names = {key+'_id':key+'-'+suffix for key in ('candidate','admission','state','event','result','index','manifest')}
            receipt = execute(runtime.store,p['command_records'],command_digest=p['command_digest'],principal=p['principal'],
                verifier=runtime.signer,provider=runtime.provider,
                physics_ids=(PhysicsIds('candidate-'+suffix,'sample-'+suffix,'snapshot-'+suffix,'checkpoint-'+suffix)
                    if type(p['command_records']) is list and any(type(r) is dict and r.get('kind') == 'intent'
                        and type(r.get('body')) is dict and r['body'].get('action') == 'physics_step' for r in p['command_records'])
                    else None),**names)
            payload = dict(manifest=receipt.manifest,result=receipt.result,commit_status=receipt.commit_status,head_binding=runtime.binding())
    return dict(protocol_version=1,request_id=request['request_id'],ok=True,
                result=dict(domain=DOMAIN,version='0.2',world_id=c.world_id,operation=op,payload=payload))


def serve(runtime, reader, writer, diagnostics):
    while True:
        raw = reader.readline(1048578)
        if not raw:
            return 0
        request = None
        try:
            request = wire(raw)
            require(type(request) is dict and type(request.get('request_id')) is str and _ID.fullmatch(request['request_id']), 'ID')
            response = dispatch(runtime,request)
            stop = False
        except (ContractError,StoreError) as exc:
            if type(request) is not dict or type(request.get('request_id')) is not str or not _ID.fullmatch(request['request_id']):
                diagnostics.write('invalid uncorrelated frame; channel closed\n'); diagnostics.flush()
                return 2
            response = dict(protocol_version=1,request_id=request['request_id'],ok=False,
                            error=dict(code=exc.code,message=exc.code,commit_status=getattr(exc,'commit_status','not_attempted')))
            stop = getattr(exc,'commit_status','') == 'unknown'
        encoded = json.dumps(response,ensure_ascii=True,separators=(',',':'),sort_keys=True,allow_nan=False).encode('ascii')
        require(len(encoded) <= 1048576, 'LIMIT')
        writer.write(encoded+b'\n'); writer.flush()
        if stop:
            return 3


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--owner-config',required=True)
    parser.add_argument('--print-public-pins',action='store_true')
    args = parser.parse_args(argv)
    owner = load_owner_config(args.owner_config)
    if args.print_public_pins:
        sys.stdout.buffer.write(canonical(public_pins(owner))+b'\n')
        return 0
    # Preserve the sole protocol pipe before any third-party/native runtime imports.
    control_fd = os.dup(1)
    os.set_inheritable(control_fd,False)
    sys.stdout.flush()
    os.dup2(2,1)
    runtime = None
    with os.fdopen(control_fd,'wb',buffering=0) as writer:
        try:
            runtime = open_runtime(owner,load_inputs(owner))
            return serve(runtime,sys.stdin.buffer,writer,sys.stderr)
        finally:
            if runtime:
                runtime.close()


if __name__ == '__main__':
    raise SystemExit(main())
