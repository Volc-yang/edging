"""Neutral-v0.1 command orchestration; one Store owns all persistence."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from functools import wraps
from dataclasses import dataclass
import json
import re
from types import MappingProxyType
import threading
from weakref import WeakKeyDictionary

from .admission import TrustVerifier
from .codec import (ApprovalSigner, ContractError, DOMAIN, VERSION, MAX_INTEGER,
                    OwnerSession, canonical, digest)
from .records import Record, validate_closure, validate_record
from .rules import neutral_candidate, retain_candidate, validate_rule_dag
from .store import CommitBundle, CommitReceipt, Store, StoreError
from .physics import PhysicsDraft, PhysicsIds, PhysicsProvider


def _require(condition: bool, code: str, detail: str = '') -> None:
    if not condition:
        raise ContractError(code, detail)


_EXECUTION_LOCKS = WeakKeyDictionary()
_REGISTRY_LOCK = threading.Lock()  # No background thread or import-time I/O.


def _serialized(function):
    @wraps(function)
    def invoke(store, *args, **kwargs):
        _require(type(store) is Store, 'SCHEMA')
        with _REGISTRY_LOCK:
            gate = _EXECUTION_LOCKS.get(store)
            if gate is None:
                gate = threading.Lock()
                _EXECUTION_LOCKS[store] = gate
        _require(gate.acquire(blocking=False), 'LOCKED', 'command execution is already active')
        try:
            return function(store, *args, **kwargs)
        finally:
            gate.release()
    return invoke


@_serialized
def _execute_v01(store: Store, command_records: Sequence[Record], *, command_digest: str,
            principal: str, verifier: TrustVerifier, candidate_id: str, admission_id: str,
            state_id: str, event_id: str, result_id: str, index_id: str,
            manifest_id: str) -> CommitReceipt:
    """Authorize first, lookup committed intent next, and only then attempt new work.

    Output IDs apply only to new work; EventId also supplies the event record ID.
    Errors from Store retain their commit_status/phase and are never relabeled.
    """
    verifier.authorize_read(principal, store.world_id)
    _require(isinstance(command_records, Sequence)
             and not isinstance(command_records, (str, bytes, bytearray))
             and len(command_records) == 4, 'SCHEMA')
    for record, kind in zip(command_records, ('proposal', 'intent', 'approval', 'command')):
        validate_record(record)
        _require(record['kind'] == kind, 'SCHEMA')
        _require(record['version'] == '0.1', 'DOMAIN')
        _require(record['world_id'] == store.world_id, 'WORLD')
    proposal, intent, approval, command = deepcopy(tuple(command_records))
    _require(proposal['body']['principal'] == intent['body']['principal']
             == approval['body']['principal'] == principal, 'AUTHORIZATION')
    _require(approval['refs'] == {'proposal': digest(proposal), 'intent': digest(intent)}, 'REFERENCE')
    _require(command['refs'] == {'proposal': digest(proposal), 'intent': digest(intent),
                                'approval': digest(approval)}, 'REFERENCE')
    fingerprint = digest(command)
    _require(type(command_digest) is str and command_digest == fingerprint, 'REFERENCE')
    snapshot = store.snapshot()
    _require(snapshot.storage_state == 'ready', 'NOT_READY')
    closure = snapshot.closure
    _require(closure.domain_version == '0.1', 'DOMAIN')
    command_id = intent['body']['command_id']
    existing = store.lookup_result(principal, command_id, fingerprint)
    if existing is not None:
        # A direct trusted Store writer may have committed since the first pin.
        current = store.snapshot()
        _require(current.storage_state == 'ready', 'NOT_READY')
        closure = current.closure
        result_digest = digest(existing)
        for root_digest in closure.retained:
            root = closure.records[root_digest]
            if 'index' in root['refs']:
                index = closure.records[root['refs']['index']]
                if index['refs']['result'] == result_digest:
                    return CommitReceipt(root_digest, existing)
        raise ContractError('CORRUPT', 'committed result has no retained manifest')

    root = closure.records[closure.head]
    old = closure.records[root['refs']['state']]
    current_revision = old['body']['revision']
    _require(intent['body']['expected_revision'] == current_revision, 'HEAD')
    _require(current_revision <= approval['body']['expires_revision'], 'AUTHORIZATION')
    _require(intent['body']['budget'] <= old['body']['budget']
             and intent['body']['random_cursor'] == old['body']['random_cursor'], 'TRANSITION')
    verifier.verify_approval(deepcopy(approval), deepcopy(proposal), deepcopy(intent))
    validate_rule_dag({})  # Only this neutral profile has been frozen.

    def make(kind, identifier, body, refs):
        record = {'domain': DOMAIN, 'version': VERSION, 'world_id': store.world_id,
                  'kind': kind, 'id': identifier, 'body': body, 'refs': refs}
        validate_record(record)
        return record

    # Allocate/validate ID shapes and collisions before any candidate or A call.
    planned = (('candidate', candidate_id), ('admission', admission_id), ('state', state_id),
               ('event', event_id), ('result', result_id), ('index', index_id),
               ('manifest', manifest_id))
    known_ids = {(r['kind'], r['id']) for r in closure.records.values()}
    supplied_ids = {(r['kind'], r['id']) for r in command_records}
    for kind, identifier in planned:
        # A minimal valid proposal lets the shared validator enforce the ID grammar.
        make('proposal', identifier, {'principal': principal, 'output': ''}, {})
        _require((kind, identifier) not in known_ids | supplied_ids, 'ID')
    _require(event_id not in {r['body']['event_id'] for r in closure.records.values()
                             if r['kind'] == 'event'}, 'ID')
    for record in (proposal, intent, approval, command):
        for previous in closure.records.values():
            if (previous['kind'], previous['id']) == (record['kind'], record['id']):
                _require(digest(previous) == digest(record), 'ID')

    candidate = neutral_candidate(old, command, intent, candidate_id=candidate_id)
    admission = verifier.admit(deepcopy(command), deepcopy(candidate), current_revision=current_revision,
                               admission_id=admission_id)
    validate_record(admission)
    admission = deepcopy(admission)
    _require(admission['kind'] == 'admission' and admission['id'] == admission_id, 'SCHEMA')
    _require(admission['world_id'] == store.world_id, 'WORLD')
    _require(admission['body']['principal'] == principal
             and admission['body']['evaluated_revision'] == current_revision, 'AUTHORIZATION')
    _require(admission['refs'] == {'command': fingerprint, 'candidate': digest(candidate)}, 'REFERENCE')
    next_tick, next_revision = candidate['body']['tick'], candidate['body']['revision']
    state = make('state', state_id,
                 {'tick': next_tick, 'revision': next_revision, 'value': candidate['body']['value'],
                  'budget': old['body']['budget'] - intent['body']['budget'],
                  'random_cursor': old['body']['random_cursor'] + 1}, {})
    event_refs = {'state': digest(state), 'admission': digest(admission)}
    if 'event' in root['refs']:
        event_refs['prior_event'] = root['refs']['event']
    event = make('event', event_id, {'event_id': event_id}, event_refs)
    result = make('result', result_id,
                  {'command_id': command_id, 'tick': next_tick, 'revision': next_revision,
                   'watermark': next_revision},
                  {'command': fingerprint, 'state': digest(state), 'event': digest(event),
                   'checkpoint': digest(candidate)})
    index = make('index', index_id, {'command_id': command_id, 'fingerprint': fingerprint},
                 {'result': digest(result)})
    manifest = make('manifest', manifest_id,
                    {'tick': next_tick, 'revision': next_revision, 'watermark': next_revision},
                    {'state': digest(state), 'event': digest(event), 'index': digest(index),
                     'prior_manifest': closure.head})
    additions = []
    for record in (proposal, intent, approval, command, candidate, admission, state, event, result, index, manifest):
        if digest(record) not in closure.records:
            additions.append(record)
    return store.commit(CommitBundle(expected_head=closure.head, records=tuple(additions),
                                    head=digest(manifest), principal=principal,
                                    command_id=command_id, fingerprint=fingerprint))


@dataclass(frozen=True, init=False)
class PreparedCommand:
    """An immutable signed intent, not a commit receipt or writer capability."""
    command_digest: str
    _command_bytes: tuple[bytes, ...]
    _result_bytes: bytes | None

    def __init__(self, command_records: tuple[Record, ...], command_digest: str,
                 committed_result: Record | None):
        _require(type(command_records) is tuple and len(command_records) == 4, 'SCHEMA')
        for record, kind in zip(command_records, ('proposal', 'intent', 'approval', 'command')):
            validate_record(record)
            _require(record['kind'] == kind and record['version'] == '0.2', 'SCHEMA')
        _require(digest(command_records[-1]) == command_digest, 'REFERENCE')
        if committed_result is not None:
            validate_record(committed_result)
            _require(committed_result['kind'] == 'result' and committed_result['version'] == '0.2', 'SCHEMA')
        object.__setattr__(self, 'command_digest', command_digest)
        object.__setattr__(self, '_command_bytes', tuple(canonical(r) for r in command_records))
        object.__setattr__(self, '_result_bytes', canonical(committed_result) if committed_result is not None else None)

    @property
    def command_records(self) -> tuple[Record, ...]:
        return tuple(json.loads(raw) for raw in self._command_bytes)

    @property
    def committed_result(self) -> Record | None:
        return json.loads(self._result_bytes) if self._result_bytes is not None else None


def _id(value):
    _require(type(value) is str and re.fullmatch(r'[a-z][a-z0-9._-]{0,63}', value) is not None, 'ID')


def _ready(store):
    snapshot = store.snapshot()
    _require(snapshot.storage_state == 'ready', 'NOT_READY')
    closure = snapshot.closure
    _require(closure.domain_version == '0.2' and closure.context is not None, 'PROFILE')
    _require(closure.world_id == store.world_id, 'WORLD')
    return closure, closure.records


def _context_auth(authority, context):
    _require(callable(getattr(authority, 'assert_context', None)), 'AUTHORIZATION')
    authority.assert_context(context)


def _check_head(store, closure):
    current, _ = _ready(store)
    _require(current.context == closure.context, 'ROOT_MISMATCH')
    _require(current.head == closure.head, 'HEAD')


def _record(kind, identifier, world_id, body, refs):
    record = {'domain': DOMAIN, 'version': '0.2', 'world_id': world_id,
              'kind': kind, 'id': identifier, 'body': body, 'refs': refs}
    validate_record(record)
    return record


def _inputs(proposal, intent, world_id, principal):
    for record, kind in ((proposal, 'proposal'), (intent, 'intent')):
        validate_record(record)
        _require(record['kind'] == kind, 'SCHEMA')
        _require(record['version'] == '0.2', 'DOMAIN')
        _require(record['world_id'] == world_id, 'WORLD')
        _require(record['body']['principal'] == principal, 'AUTHORIZATION')


def _new_policy(closure, records, intent):
    head = records[closure.head]
    old = records[head['refs']['state']]
    snapshot = records[old['refs']['snapshot']]
    body = intent['body']
    _require(body['expected_revision'] == old['body']['revision'], 'HEAD')
    _require(body['random_cursor'] == old['body']['random_cursor']
             and body['budget'] <= old['body']['budget'], 'TRANSITION')
    _require(old['body']['revision'] < MAX_INTEGER, 'INTEGER')
    _require(len(closure.retained) < 64, 'COUNTS')
    _require(intent['refs'] == {'config': snapshot['refs']['config'], 'binding': snapshot['refs']['binding']},
             'PHYSICS_INVALID')
    if body['action'] == 'retain_snapshot':
        _require(body['tick_delta'] == 0 and body['case_id'] is None and body['budget'] == 0, 'TRANSITION')
    else:
        _require(body['action'] == 'physics_step' and body['tick_delta'] == 1
                 and body['case_id'] in ('weak', 'strong'), 'TRANSITION')
        _require(old['body']['tick'] < MAX_INTEGER and old['body']['random_cursor'] < MAX_INTEGER, 'INTEGER')
        _require(snapshot['body']['physical_step_count'] + 8 <= 256, 'LIMIT')
    return old


def _check_ids(records, inputs, planned, event_id=None):
    known = {(r['kind'], r['id']): digest(r) for r in records.values()}
    occupied = set(known)
    for record in inputs:
        key = (record['kind'], record['id'])
        _require(key not in known or known[key] == digest(record), 'ID')
        occupied.add(key)
    for kind, identifier in planned:
        _id(identifier)
        key = (kind, identifier)
        _require(key not in occupied, 'ID')
        occupied.add(key)
    if event_id is not None:
        _require(event_id not in {r['body']['event_id'] for r in records.values() if r['kind'] == 'event'}, 'ID')
    _require(len(records) + len({digest(r) for r in inputs} - set(records)) + len(planned) <= 2048, 'LIMIT')


@_serialized
def prepare_command(store: Store, *, session: OwnerSession, proposal: Record,
                    intent: Record, approval_id: str, command_record_id: str,
                    signer: ApprovalSigner) -> PreparedCommand:
    _require(type(session) is OwnerSession, 'AUTHORIZATION')
    _require(callable(getattr(signer, 'authorize_read', None))
             and callable(getattr(signer, 'sign_approval', None)), 'AUTHORIZATION')
    signer.authorize_read(session.principal, store.world_id)
    _inputs(proposal, intent, store.world_id, session.principal)
    proposal, intent = deepcopy(proposal), deepcopy(intent)
    _id(approval_id); _id(command_record_id)
    closure, records = _ready(store)
    _context_auth(signer, closure.context)
    result_ref = closure.commands.get((session.principal, intent['body']['command_id']))
    if result_ref is not None:
        result = records[result_ref]
        command = records[result['refs']['command']]
        stored_proposal = records[command['refs']['proposal']]
        stored_intent = records[command['refs']['intent']]
        approval = records[command['refs']['approval']]
        _require(canonical(proposal) == canonical(stored_proposal)
                 and canonical(intent) == canonical(stored_intent)
                 and command['id'] == command_record_id and approval['id'] == approval_id
                 and approval['body']['receipt_id'] == approval_id
                 and approval['body']['expires_revision'] == intent['body']['expected_revision'],
                 'COMMAND_CONFLICT')
        current = store.lookup_result(session.principal, intent['body']['command_id'], digest(command))
        _require(current is not None and digest(current) == result_ref, 'CORRUPT')
        return PreparedCommand((stored_proposal, stored_intent, approval, command), digest(command), current)

    _require(intent['body']['action'] in session.allowed_actions, 'AUTHORIZATION')
    _new_policy(closure, records, intent)
    _check_ids(records, (proposal, intent), (('approval', approval_id), ('command', command_record_id)))
    unsigned = {'domain': DOMAIN, 'version': '0.2', 'world_id': store.world_id,
                'kind': 'approval', 'id': approval_id,
                'body': {'principal': session.principal, 'receipt_id': approval_id,
                         'expires_revision': intent['body']['expected_revision']},
                'refs': {'proposal': digest(proposal), 'intent': digest(intent)}}
    approval = signer.sign_approval(deepcopy(unsigned))
    validate_record(approval)
    _require(approval['version'] == '0.2', 'DOMAIN')
    _require(approval['world_id'] == store.world_id, 'WORLD')
    _require(approval['kind'] == 'approval' and approval['id'] == approval_id, 'SCHEMA')
    _require({k: v for k, v in approval['body'].items() if k != 'auth_tag'} == unsigned['body']
             and approval['refs'] == unsigned['refs'], 'AUTHORIZATION')
    store.trust_verifier(approval)
    command = _record('command', command_record_id, store.world_id, {},
                      {'proposal': digest(proposal), 'intent': digest(intent), 'approval': digest(approval)})
    _check_head(store, closure)
    return PreparedCommand((proposal, intent, approval, command), digest(command), None)


class _BlobReader:
    """Only immutable bytes; no bound Store, writer, lease or signer object."""
    __slots__ = ('__values',)

    def __init__(self, values):
        object.__setattr__(self, '_BlobReader__values', MappingProxyType(dict(values)))

    def __setattr__(self, name, value):
        raise AttributeError('immutable read capability')

    def __call__(self, reference):
        _require(type(reference) is str and reference in self.__values, 'REFERENCE')
        return self.__values[reference]


def _ordered_additions(records, additions):
    ordered = list(records.values())
    known = set(records)
    pending = {}
    for record in additions:
        reference = digest(record)
        if reference not in known:
            _require(reference not in pending, 'REFERENCE')
            pending[reference] = record
    while pending:
        ready = sorted(ref for ref, r in pending.items() if all(x in known for x in r['refs'].values()))
        _require(bool(ready), 'REFERENCE')
        for ref in ready:
            record = pending.pop(ref)
            ordered.append(record); known.add(ref)
    return ordered


def _candidate_check(store, closure, records, additions, raw):
    _check_head(store, closure)
    # No new manifest/A is needed: full validator checks all supplied orphan
    # candidate semantics and raw while retained indexing remains the old HEAD.
    validate_closure(_ordered_additions(records, additions), closure.head,
                     world_id=store.world_id, domain_version='0.2', context=closure.context,
                     trust_verifier=store.trust_verifier, blobs=raw)


def _original_receipt(store, existing):
    closure, records = _ready(store)
    result_ref = digest(existing)
    for root_ref in closure.retained:
        root = records[root_ref]
        if 'index' in root['refs'] and records[root['refs']['index']]['refs']['result'] == result_ref:
            return CommitReceipt(root_ref, existing)
    raise ContractError('CORRUPT', 'committed result has no retained manifest')


@_serialized
def _execute_v02(store: Store, command_records: Sequence[Record], *, command_digest: str,
                 principal: str, verifier: TrustVerifier, candidate_id: str, admission_id: str,
                 state_id: str, event_id: str, result_id: str, index_id: str, manifest_id: str,
                 provider: PhysicsProvider | None, physics_ids: PhysicsIds | None) -> CommitReceipt:
    verifier.authorize_read(principal, store.world_id)
    _require(isinstance(command_records, Sequence) and not isinstance(command_records, (str, bytes, bytearray))
             and len(command_records) == 4, 'SCHEMA')
    for record, kind in zip(command_records, ('proposal', 'intent', 'approval', 'command')):
        validate_record(record)
        _require(record['kind'] == kind, 'SCHEMA')
        _require(record['version'] == '0.2', 'DOMAIN')
        _require(record['world_id'] == store.world_id, 'WORLD')
    proposal, intent, approval, command = deepcopy(tuple(command_records))
    _inputs(proposal, intent, store.world_id, principal)
    _require(approval['body']['principal'] == principal, 'AUTHORIZATION')
    _require(approval['refs'] == {'proposal': digest(proposal), 'intent': digest(intent)}
             and command['refs'] == {'proposal': digest(proposal), 'intent': digest(intent), 'approval': digest(approval)}, 'REFERENCE')
    fingerprint = digest(command)
    _require(type(command_digest) is str and command_digest == fingerprint, 'REFERENCE')
    closure, records = _ready(store)
    _context_auth(verifier, closure.context)
    existing = store.lookup_result(principal, intent['body']['command_id'], fingerprint)
    if existing is not None:
        return _original_receipt(store, existing)

    old = _new_policy(closure, records, intent)
    _require(closure.records[closure.head]['body']['revision'] <= approval['body']['expires_revision'], 'AUTHORIZATION')
    verifier.verify_approval(deepcopy(approval), deepcopy(proposal), deepcopy(intent))
    store.trust_verifier(approval)
    planned = [('candidate', candidate_id), ('admission', admission_id), ('state', state_id),
               ('event', event_id), ('result', result_id), ('index', index_id), ('manifest', manifest_id)]
    action = intent['body']['action']
    if action == 'physics_step':
        _require(callable(getattr(provider, 'propose', None)) and type(physics_ids) is PhysicsIds, 'PHYSICS_INVALID')
        _require(physics_ids.candidate == candidate_id, 'ID')
        planned.extend((('physics_sample', physics_ids.sample), ('physics_snapshot', physics_ids.snapshot),
                        ('checkpoint_descriptor', physics_ids.checkpoint_descriptor)))
    else:
        _require(physics_ids is None, 'PHYSICS_INVALID')
    _check_ids(records, (proposal, intent, approval, command), planned, event_id)
    raw = {ref: store.read_blob(ref) for ref in closure.binary_refs}
    blobs = ()
    if action == 'retain_snapshot':
        candidate = retain_candidate(old, command, intent, candidate_id=candidate_id, records=records)
        draft_records = (candidate,)
    else:
        snapshot = records[old['refs']['snapshot']]
        payload_hash = records[snapshot['refs']['checkpoint']]['body']['payload_sha256']
        reader = _BlobReader({payload_hash: raw[payload_hash]})
        try:
            draft = provider.propose(deepcopy(old), deepcopy(command), deepcopy(intent),
                                     records=MappingProxyType(deepcopy(dict(records))), read_blob=reader, ids=physics_ids)
        except ContractError:
            raise
        except Exception as exc:
            raise ContractError('PHYSICS_FAILED', 'candidate provider failed before authority commit') from exc
        _require(type(draft) is PhysicsDraft, 'PHYSICS_INVALID')
        draft_records = draft.records
        expected_ids = {'candidate': physics_ids.candidate, 'physics_sample': physics_ids.sample,
                        'physics_snapshot': physics_ids.snapshot, 'checkpoint_descriptor': physics_ids.checkpoint_descriptor}
        for record in draft_records:
            _require(record['id'] == expected_ids[record['kind']], 'ID')
            _require(record['world_id'] == store.world_id and record['version'] == '0.2', 'WORLD')
        candidate = next(r for r in draft_records if r['kind'] == 'candidate')
        snapshot_record = next(r for r in draft_records if r['kind'] == 'physics_snapshot')
        descriptor = next(r for r in draft_records if r['kind'] == 'checkpoint_descriptor')
        _require(draft.candidate_digest == digest(candidate) and draft.snapshot_digest == digest(snapshot_record)
                 and candidate['refs']['snapshot'] == draft.snapshot_digest, 'REFERENCE')
        b = descriptor['body']
        _require(draft.blob.sha256 == b['payload_sha256'] and len(draft.blob.payload) == b['byte_count']
                 and draft.blob.media_type == b['media_type'] and draft.blob.artifact_class == b['artifact_class']
                 == closure.context.artifact_class, 'CORRUPT')
        if draft.blob.sha256 in raw:
            _require(raw[draft.blob.sha256] == draft.blob.payload, 'CORRUPT')
        raw[draft.blob.sha256] = draft.blob.payload
        _require(sum(map(len, raw.values())) <= 536870912, 'BLOB_LIMIT')
        blobs = (draft.blob,)
        # Detect retained-data loss during provider work before issuing A.
        for ref in closure.binary_refs:
            _require(store.read_blob(ref) == raw[ref], 'CORRUPT')
    _candidate_check(store, closure, records, (proposal, intent, approval, command) + draft_records, raw)
    admission = verifier.admit(deepcopy(command), deepcopy(candidate),
                               current_revision=old['body']['revision'], admission_id=admission_id)
    validate_record(admission)
    _require(admission['version'] == '0.2', 'DOMAIN')
    _require(admission['world_id'] == store.world_id, 'WORLD')
    _require(admission['kind'] == 'admission' and admission['id'] == admission_id, 'SCHEMA')
    _require(admission['body']['principal'] == principal
             and admission['body']['evaluated_revision'] == old['body']['revision']
             and admission['refs'] == {'command': fingerprint, 'candidate': digest(candidate)}, 'AUTHORIZATION')
    store.trust_verifier(admission)
    _check_head(store, closure)
    cb = candidate['body']
    state = _record('state', state_id, store.world_id,
                    {'tick': cb['tick'], 'revision': cb['revision'], 'development_mm': cb['influence_mm'],
                     'budget': old['body']['budget'] - intent['body']['budget'],
                     'random_cursor': old['body']['random_cursor'] + (1 if action == 'physics_step' else 0)},
                    {'world': old['refs']['world'], 'snapshot': candidate['refs']['snapshot']})
    event_refs = {'state': digest(state), 'admission': digest(admission)}
    if 'event' in records[closure.head]['refs']:
        event_refs['prior_event'] = records[closure.head]['refs']['event']
    event = _record('event', event_id, store.world_id, {'event_id': event_id}, event_refs)
    result = _record('result', result_id, store.world_id,
                     {'command_id': intent['body']['command_id'], 'tick': cb['tick'],
                      'revision': cb['revision'], 'watermark': cb['revision']},
                     {'command': fingerprint, 'state': digest(state), 'event': digest(event),
                      'checkpoint': candidate['refs']['snapshot']})
    index = _record('index', index_id, store.world_id,
                    {'command_id': intent['body']['command_id'], 'fingerprint': fingerprint}, {'result': digest(result)})
    manifest = _record('manifest', manifest_id, store.world_id,
                       {'tick': cb['tick'], 'revision': cb['revision'], 'watermark': cb['revision']},
                       {'state': digest(state), 'event': digest(event), 'index': digest(index), 'prior_manifest': closure.head})
    ordered = _ordered_additions(records, (proposal, intent, approval, command) + draft_records
                                 + (admission, state, event, result, index, manifest))
    additions = tuple(r for r in ordered if digest(r) not in records)
    return store.commit(CommitBundle(closure.head, additions, digest(manifest), principal,
                                    intent['body']['command_id'], fingerprint, blobs=blobs))


def execute(store: Store, command_records: Sequence[Record], *, command_digest: str,
            principal: str, verifier: TrustVerifier, candidate_id: str, admission_id: str,
            state_id: str, event_id: str, result_id: str, index_id: str, manifest_id: str,
            provider: PhysicsProvider | None = None, physics_ids: PhysicsIds | None = None) -> CommitReceipt:
    arguments = dict(command_digest=command_digest, principal=principal, verifier=verifier,
                     candidate_id=candidate_id, admission_id=admission_id, state_id=state_id,
                     event_id=event_id, result_id=result_id, index_id=index_id, manifest_id=manifest_id)
    composite = (isinstance(command_records, Sequence) and not isinstance(command_records, (str, bytes, bytearray))
                 and len(command_records) == 4
                 and any(type(r) is dict and r.get('version') == '0.2' for r in command_records))
    if composite:
        return _execute_v02(store, command_records, provider=provider, physics_ids=physics_ids, **arguments)
    _require(provider is None and physics_ids is None, 'PROFILE')
    return _execute_v01(store, command_records, **arguments)
