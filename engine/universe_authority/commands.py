"""Neutral-v0.1 command orchestration; one Store owns all persistence."""
from __future__ import annotations

from collections.abc import Sequence
from copy import deepcopy
from functools import wraps
import threading
from weakref import WeakKeyDictionary

from .admission import TrustVerifier
from .codec import ContractError, DOMAIN, VERSION, digest
from .records import Record, validate_record
from .rules import neutral_candidate, validate_rule_dag
from .store import CommitBundle, CommitReceipt, Store


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
def execute(store: Store, command_records: Sequence[Record], *, command_digest: str,
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
