"""Explicit dual-profile recovery and pure bounded snapshot projections.

No initializer, solver, migration, garbage collection, backup fallback or clock.
Snapshots are trusted in-process values. Public bindings come from the owned
recovery boundary; read functions return payloads, not transport envelopes.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json

from .codec import ContractError, DeploymentContext, DOMAIN, HeadBinding, MAX_BYTES, canonical, decode, digest
from .records import (Record, ValidatedClosure, select, validate_closure, validate_record,
                      verify_observation)
from .store import PinnedRoot, Snapshot, Store, StoreError

_READABLE = ('ready', 'unconfirmed_readonly')


def _require(condition: bool, code: str, detail: str = '') -> None:
    if not condition:
        raise ContractError(code, detail)


@dataclass(frozen=True)
class RecoveryReport:
    storage_state: str
    snapshot: Snapshot | None
    confirmed: bool
    error_code: str | None

    def __post_init__(self) -> None:
        _require(self.storage_state in _READABLE and type(self.snapshot) is Snapshot, 'SCHEMA')
        _require(self.snapshot.storage_state == self.storage_state and type(self.confirmed) is bool, 'SCHEMA')
        if self.storage_state == 'ready':
            _require(self.confirmed and self.error_code is None, 'SCHEMA')
        else:
            _require(not self.confirmed and self.error_code == 'SYNC_UNSUPPORTED', 'SCHEMA')


def _ordered(pinned: PinnedRoot, world_id: str, *, domain_version: str = "0.1") -> list[Record]:
    """Order the entire raw Mapping by references, never by insertion history."""
    _require(type(pinned) is PinnedRoot and 1 <= len(pinned.objects) <= (2048 if domain_version == '0.2' else 256), 'CORRUPT')
    _require(sum(len(raw) for raw in pinned.objects.values()) <= (16_777_216 if domain_version == '0.2' else MAX_BYTES), 'CORRUPT')
    records = {}
    for reference, raw in pinned.objects.items():
        record = decode(raw)
        validate_record(record)
        _require(raw == canonical(record) and digest(record) == reference
                 and record['world_id'] == world_id, 'CORRUPT')
        records[reference] = record
    _require(pinned.head in records and records[pinned.head]['kind'] == 'manifest', 'CORRUPT')
    active, completed, ordered = set(), set(), []
    def visit(reference):
        _require(reference in records and reference not in active, 'CORRUPT')
        if reference in completed:
            return
        active.add(reference)
        for target in sorted(records[reference]['refs'].values()):
            visit(target)
        active.remove(reference)
        completed.add(reference)
        ordered.append(records[reference])
    visit(pinned.head)
    _require(len(completed) == len(records), 'CORRUPT', 'pinned mapping contains unreachable objects')
    return ordered


def recover(store: Store) -> RecoveryReport:
    """Verify the full pinned closure before asking the same Store for D_recovery.

    Pin/integrity/ownership failures propagate. Only an explicit sync failure
    after fresh full validation may yield an unconfirmed read-only report.
    """
    _require(type(store) is Store, 'SCHEMA', 'expected an existing Store')
    pinned = store.pin()
    try:
        ordered = _ordered(pinned, store.world_id, domain_version=store.domain_version)
        if store.domain_version == '0.2':
            context = store.deployment_context
            _require(type(context) is DeploymentContext, 'CORRUPT')
            closure = validate_closure(
                ordered, pinned.head, world_id=store.world_id,
                domain_version='0.2', context=context,
                trust_verifier=store.trust_verifier, blobs=pinned.blobs,
            )
            _require(set(pinned.blobs) == set(closure.binary_refs), 'CORRUPT')
        else:
            _require(not pinned.blobs, 'CORRUPT')
            closure = validate_closure(ordered, pinned.head, world_id=store.world_id,
                                       trusted_receipts=store.trusted_receipts)
    except (ContractError, AttributeError, KeyError, TypeError) as exc:
        # pin has already invalidated any previous cached snapshot. No partial
        # closure or older backup is eligible as an observation result.
        raise StoreError('CORRUPT', 'pinned reference closure rejected',
                         phase='recovery_validate') from exc
    try:
        snapshot = store.confirm_recovery(pinned, closure)
    except StoreError as exc:
        if exc.code != 'SYNC_UNSUPPORTED' or store.state != 'unconfirmed_readonly':
            raise
        snapshot = store.snapshot()
        if snapshot.storage_state != 'unconfirmed_readonly' or snapshot.closure.head != pinned.head:
            raise StoreError('CORRUPT', 'fresh validated snapshot is unavailable', phase='recovery_result')
        return RecoveryReport('unconfirmed_readonly', snapshot, False, exc.code)
    if snapshot.storage_state != 'ready' or store.state != 'ready' or snapshot.closure.head != pinned.head:
        raise StoreError('CORRUPT', 'confirmation returned an inconsistent snapshot', phase='recovery_result')
    return RecoveryReport('ready', snapshot, True, None)


def _record(records, reference: str, kind: str, world_id: str) -> Record:
    _require(type(reference) is str and reference in records, 'REFERENCE')
    record = records[reference]
    validate_record(record)
    _require(record['kind'] == kind and record['world_id'] == world_id
             and digest(record) == reference, 'REFERENCE')
    return record


def _view(snapshot: Snapshot):
    _require(type(snapshot) is Snapshot, 'SCHEMA', 'expected an immutable Snapshot')
    try:
        _require(snapshot.storage_state in _READABLE
                 and type(snapshot.closure) is ValidatedClosure, 'SCHEMA')
        closure = snapshot.closure
        records = closure.records  # Fresh trees from internally validated bytes.
        head = _record(records, closure.head, 'manifest', closure.world_id)
        return closure, records, head
    except (AttributeError, KeyError, TypeError) as exc:
        raise ContractError('SCHEMA', 'invalid snapshot representation') from exc


def head_binding(snapshot: Snapshot) -> HeadBinding:
    """Expose only the public trust anchor of an already recovered snapshot."""
    closure, _, _ = _view(snapshot)
    _require(closure.domain_version == '0.2', 'PROFILE')
    context = closure.context
    _require(type(context) is DeploymentContext and context.world_id == closure.world_id
             and closure.profile == context.archive_profile
             and closure.artifact_class == context.artifact_class, 'PROFILE')
    return HeadBinding(
        head=closure.head, world_id=closure.world_id,
        authority_root=context.authority_root, trust_algorithm=context.trust_algorithm,
        trust_anchor=context.trust_anchor, expected_build=context.expected_build,
        expected_options=context.expected_options, artifact_class=context.artifact_class,
        domain=DOMAIN, version=context.domain_version, profile=context.archive_profile,
        storage_state=snapshot.storage_state,
    )


def status(snapshot: Snapshot) -> dict:
    """Return the exact current pinned status payload; never inspect storage."""
    closure, _, head = _view(snapshot)
    body = head['body']
    if closure.domain_version == '0.2':
        return {'world_id': closure.world_id, 'head': closure.head,
                'tick': body['tick'], 'revision': body['revision'], 'watermark': body['watermark'],
                'state': head['refs']['state'], 'event': head['refs'].get('event'),
                'storage_state': snapshot.storage_state, 'artifact_class': closure.artifact_class,
                'head_binding': asdict(head_binding(snapshot))}
    return {'head': closure.head, 'tick': body['tick'], 'revision': body['revision'],
            'watermark': body['watermark'], 'storage_state': snapshot.storage_state}


def observe(snapshot: Snapshot, *, tick: int, revision: int, watermark: int) -> dict:
    """Select only an exact retained tuple; output mutations never affect authority."""
    closure, records, _ = _view(snapshot)
    manifest = select(closure, tick=tick, revision=revision, watermark=watermark)
    state = _record(records, manifest['refs']['state'], 'state', closure.world_id)
    if manifest['body']['revision'] == 0:
        event = None
    else:
        event = _record(records, manifest['refs']['event'], 'event', closure.world_id)
        _require(event['refs']['state'] == manifest['refs']['state'], 'REFERENCE')
    _require(state['body']['tick'] == tick and state['body']['revision'] == revision
             and manifest['body']['watermark'] == watermark, 'WATERMARK')
    if closure.domain_version == '0.2':
        return _proof(snapshot, closure, records, manifest, state, event, tick, revision, watermark)
    return {'manifest': manifest, 'state': state, 'event': event,
            'watermark': watermark, 'storage_state': snapshot.storage_state}


def _proof(snapshot, closure, records, manifest, state, event, tick, revision, watermark):
    """Build a selective proof with bounded memoized reference expansion.

    Full-history validation belongs to recover(). This follows just the selected
    transition, its immediate previous state, and the HEAD membership path.
    The public independent consumer checks typed targets and exact slice scope.
    """
    selected = digest(manifest)
    membership = []
    membership_hashes = set()
    current = closure.head
    while True:
        _require(current not in membership_hashes and len(membership) < 64, 'PROOF_LIMIT')
        record = _record(records, current, 'manifest', closure.world_id)
        membership.append(record)
        membership_hashes.add(current)
        if current == selected:
            break
        _require('prior_manifest' in record['refs'], 'PROOF')
        current = record['refs']['prior_manifest']

    previous = manifest['refs'].get('prior_manifest')
    needed, active, completed = set(), set(), set()
    def expand(reference, mode='normal'):
        key = (reference, mode)
        _require(reference in records and key not in active, 'PROOF')
        if key in completed:
            return
        # Records are immutable trusted closure trees, not arbitrary wire input.
        # The memoization bounds a shared DAG to at most two visits per record.
        _require(len(needed) < 100 or reference in needed, 'PROOF_LIMIT')
        record = records[reference]
        validate_record(record)
        _require(digest(record) == reference and record['world_id'] == closure.world_id, 'PROOF')
        needed.add(reference)
        active.add(key)
        for name, target in sorted(record['refs'].items()):
            if record['kind'] == 'manifest' and (name == 'prior_manifest'
                    or mode == 'previous' and name != 'state'):
                continue
            if record['kind'] == 'event' and name == 'prior_event':
                continue
            expand(target)
        active.remove(key)
        completed.add(key)
    expand(selected)
    if previous is not None:
        expand(previous, 'previous')
    supplied = needed | membership_hashes
    explicit = membership_hashes | {selected, digest(state)}
    if event is not None:
        explicit.add(digest(event))
    auxiliary = [records[reference] for reference in sorted(needed - explicit)]
    opaque = sorted({reference for key in supplied for reference in records[key]['refs'].values()
                     if reference not in supplied})
    _require(len(auxiliary) <= 96 and len(opaque) <= 256, 'PROOF_LIMIT')
    payload = dict(manifest=manifest, state=state, event=event, watermark=watermark,
                   storage_state=snapshot.storage_state, artifact_class=closure.artifact_class,
                   head=closure.head, membership=membership, records=auxiliary, opaque_refs=opaque)
    # observe() intentionally has no transport request ID. A maximal legal ID
    # bounds the exact success wrapper for every legal caller ID (ASCII <=64).
    request_id = 'observe-' + 'x' * 56
    envelope = dict(protocol_version=1, request_id=request_id, ok=True,
                    result=dict(domain=DOMAIN, version='0.2', world_id=closure.world_id,
                                operation='observe', payload=payload))
    raw = json.dumps(envelope, sort_keys=True, ensure_ascii=True,
                     separators=(',', ':'), allow_nan=False).encode('ascii')
    _require(len(raw) <= MAX_BYTES, 'PROOF_LIMIT', 'actual wrapped observation exceeds wire cap')
    verify_observation(raw, context=closure.context, expected_request_id=request_id,
                       tick=tick, revision=revision, watermark=watermark,
                       trusted_head=head_binding(snapshot))
    return payload
