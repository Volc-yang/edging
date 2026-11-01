"""Pure provider protocols and immutable drafts; no concrete solver import."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import json
import re
from typing import Protocol

from .codec import ContractError, JSON, canonical, digest
from .records import Record, validate_record
from .store import BlobWrite


def _require(value, code):
    if not value:
        raise ContractError(code)


def _id(value):
    _require(type(value) is str and re.fullmatch(r'[a-z][a-z0-9._-]{0,63}', value) is not None, 'ID')


@dataclass(frozen=True)
class PhysicsIds:
    candidate: str
    sample: str
    snapshot: str
    checkpoint_descriptor: str

    def __post_init__(self):
        for value in (self.candidate, self.sample, self.snapshot, self.checkpoint_descriptor):
            _id(value)


@dataclass(frozen=True)
class PhysicsInitialIds:
    sample: str
    snapshot: str
    checkpoint_descriptor: str

    def __post_init__(self):
        for value in (self.sample, self.snapshot, self.checkpoint_descriptor):
            _id(value)


def _draft(records, snapshot_digest, blob, candidate_digest=None):
    expected = {'physics_sample', 'checkpoint_descriptor', 'physics_snapshot'}
    if candidate_digest is not None:
        expected.add('candidate')
    _require(type(records) is tuple and len(records) == len(expected), 'SCHEMA')
    _require(type(blob) is BlobWrite, 'SCHEMA')
    kinds = {}
    world = None
    encoded = []
    for record in records:
        validate_record(record)
        _require(record['version'] == '0.2', 'DOMAIN')
        _require(record['kind'] in expected and record['kind'] not in kinds, 'SCHEMA')
        if world is None:
            world = record['world_id']
        _require(record['world_id'] == world, 'WORLD')
        kinds[record['kind']] = digest(record)
        encoded.append(canonical(record))
    _require(kinds['physics_snapshot'] == snapshot_digest, 'REFERENCE')
    if candidate_digest is not None:
        _require(kinds['candidate'] == candidate_digest, 'REFERENCE')
    return tuple(encoded)


@dataclass(frozen=True, init=False)
class PhysicsDraft:
    candidate_digest: str
    snapshot_digest: str
    blob: BlobWrite
    _record_bytes: tuple[bytes, ...]

    def __init__(self, records: tuple[Record, ...], candidate_digest: str,
                 snapshot_digest: str, blob: BlobWrite):
        _require(type(candidate_digest) is str, 'REFERENCE')
        encoded = _draft(records, snapshot_digest, blob, candidate_digest)
        object.__setattr__(self, 'candidate_digest', candidate_digest)
        object.__setattr__(self, 'snapshot_digest', snapshot_digest)
        object.__setattr__(self, 'blob', blob)
        object.__setattr__(self, '_record_bytes', encoded)

    @property
    def records(self) -> tuple[Record, ...]:
        return tuple(json.loads(raw) for raw in self._record_bytes)


@dataclass(frozen=True, init=False)
class PhysicsInitialDraft:
    snapshot_digest: str
    blob: BlobWrite
    _record_bytes: tuple[bytes, ...]

    def __init__(self, records: tuple[Record, ...], snapshot_digest: str, blob: BlobWrite):
        encoded = _draft(records, snapshot_digest, blob)
        object.__setattr__(self, 'snapshot_digest', snapshot_digest)
        object.__setattr__(self, 'blob', blob)
        object.__setattr__(self, '_record_bytes', encoded)

    @property
    def records(self) -> tuple[Record, ...]:
        return tuple(json.loads(raw) for raw in self._record_bytes)


class PhysicsProvider(Protocol):
    def initialize(self, *, ids: PhysicsInitialIds) -> PhysicsInitialDraft: ...
    def restore(self, snapshot: Record, *, records: Mapping[str, Record],
                read_blob: Callable[[str], bytes]) -> Mapping[str, JSON]: ...
    def propose(self, prior_state: Record, command: Record, intent: Record, *,
                records: Mapping[str, Record], read_blob: Callable[[str], bytes],
                ids: PhysicsIds) -> PhysicsDraft: ...
    def close(self) -> None: ...
