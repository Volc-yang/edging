"""Explicit v0.1 recovery confirmation and pure, exact snapshot projections.

No initializer, solver, migration, garbage collection, backup fallback or clock.
Snapshots are trusted in-process values; wire authentication remains its owner's
responsibility. Read functions return payloads, not transport envelopes.
"""
from __future__ import annotations

from dataclasses import dataclass

from .codec import ContractError, MAX_BYTES, canonical, decode, digest
from .records import Record, ValidatedClosure, select, validate_closure, validate_record
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


def _ordered(pinned: PinnedRoot, world_id: str) -> list[Record]:
    """Order the entire raw Mapping by references, never by insertion history."""
    _require(type(pinned) is PinnedRoot and 1 <= len(pinned.objects) <= 256, 'CORRUPT')
    _require(sum(len(raw) for raw in pinned.objects.values()) <= MAX_BYTES, 'CORRUPT')
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
        closure = validate_closure(
            _ordered(pinned, store.world_id), pinned.head,
            world_id=store.world_id, trusted_receipts=store.trusted_receipts,
        )
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


def status(snapshot: Snapshot) -> dict:
    """Return the exact current pinned status payload; never inspect storage."""
    closure, _, head = _view(snapshot)
    body = head['body']
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
    return {'manifest': manifest, 'state': state, 'event': event,
            'watermark': watermark, 'storage_state': snapshot.storage_state}
