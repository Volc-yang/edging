"""Owner-injected trust for the fixed, non-production neutral fixture only."""
from __future__ import annotations

from collections.abc import Mapping
import re
from types import MappingProxyType
from typing import Protocol

from .codec import ContractError, DOMAIN, VERSION, JSON, MAX_INTEGER, canonical, decode, digest
from .records import Record, validate_record

_ID = re.compile(r'[a-z][a-z0-9._-]{0,63}\Z')
_HASH = re.compile(r'[0-9a-f]{64}\Z')
# Literal read from I0 positive.json, not a general multi-world ACL.
_FIXTURE_WORLD = 'fixture-world'


def _require(condition: bool, code: str, detail: str = '') -> None:
    if not condition:
        raise ContractError(code, detail)


def _id(value) -> None:
    _require(type(value) is str and _ID.fullmatch(value) is not None, 'ID')


def _kind(record: Record, kind: str) -> None:
    validate_record(record)
    _require(record['kind'] == kind, 'SCHEMA')


class TrustVerifier(Protocol):
    def authorize_read(self, principal: str, world_id: str) -> None: ...
    def verify_approval(self, approval: Record, proposal: Record, intent: Record) -> None: ...
    def admit(self, command: Record, candidate: Record, *, current_revision: int,
              admission_id: str) -> Record: ...


class FixtureTrust:
    """Fixed fixture-world/principal anchors; no authentication/network claims.

    Other worlds require an explicit owner-supplied verifier. Anchors are copied
    as canonical bytes so callers cannot mutate policy through nested mappings.
    """
    __slots__ = ('_anchors', '_principals')

    def __init__(self, receipts: Mapping[str, JSON]) -> None:
        _require(isinstance(receipts, Mapping), 'SCHEMA')
        values = decode(canonical(dict(receipts)))
        anchors = {}
        principals = set()
        for receipt_id, value in values.items():
            _id(receipt_id)
            _require(type(value) is dict, 'SCHEMA')
            kind = value.get('kind')
            fields = ({'kind', 'principal', 'intent', 'proposal', 'expires_revision'}
                      if kind == 'approval' else
                      {'kind', 'principal', 'command', 'candidate', 'evaluated_revision'}
                      if kind == 'admission' else None)
            _require(fields is not None and set(value) == fields, 'SCHEMA')
            _id(value['principal'])
            number = value['expires_revision' if kind == 'approval' else 'evaluated_revision']
            _require(type(number) is int and 0 <= number <= MAX_INTEGER, 'INTEGER')
            for name in ('intent', 'proposal') if kind == 'approval' else ('command', 'candidate'):
                _require(type(value[name]) is str and _HASH.fullmatch(value[name]) is not None, 'REFERENCE')
            anchors[receipt_id] = canonical(value)
            principals.add(value['principal'])
        self._anchors = MappingProxyType(anchors)
        self._principals = frozenset(principals)

    def authorize_read(self, principal: str, world_id: str) -> None:
        _id(principal)
        _id(world_id)
        _require(world_id == _FIXTURE_WORLD and principal in self._principals,
                 'AUTHORIZATION', 'principal/world is outside fixed fixture trust')

    def verify_approval(self, approval: Record, proposal: Record, intent: Record) -> None:
        _kind(approval, 'approval'); _kind(proposal, 'proposal'); _kind(intent, 'intent')
        principal = intent['body']['principal']
        self.authorize_read(principal, intent['world_id'])
        _require(approval['world_id'] == proposal['world_id'] == intent['world_id'], 'WORLD')
        _require(approval['body']['principal'] == proposal['body']['principal'] == principal,
                 'AUTHORIZATION')
        _require(approval['refs'] == {'proposal': digest(proposal), 'intent': digest(intent)},
                 'AUTHORIZATION')
        expected = {'kind': 'approval', 'principal': principal,
                    'proposal': digest(proposal), 'intent': digest(intent),
                    'expires_revision': approval['body']['expires_revision']}
        _require(self._anchors.get(approval['body']['receipt_id']) == canonical(expected),
                 'AUTHORIZATION', 'approval differs from injected receipt')

    def admit(self, command: Record, candidate: Record, *, current_revision: int,
              admission_id: str) -> Record:
        _kind(command, 'command'); _kind(candidate, 'candidate'); _id(admission_id)
        _require(command['world_id'] == candidate['world_id'], 'WORLD')
        _require(type(current_revision) is int and 0 <= current_revision <= MAX_INTEGER, 'INTEGER')
        _require(candidate['refs']['command'] == digest(command), 'REFERENCE')
        _require(candidate['body']['revision'] == current_revision + 1, 'HEAD')
        matches = []
        for receipt_id, encoded in self._anchors.items():
            anchor = decode(encoded)
            if anchor['kind'] != 'admission':
                continue
            expected = {'kind': 'admission', 'principal': anchor['principal'],
                        'command': digest(command), 'candidate': digest(candidate),
                        'evaluated_revision': current_revision}
            if encoded == canonical(expected):
                matches.append((receipt_id, anchor['principal']))
        _require(len(matches) == 1, 'AUTHORIZATION', 'missing or ambiguous admission receipt')
        receipt_id, principal = matches[0]
        self.authorize_read(principal, command['world_id'])
        result = {'domain': DOMAIN, 'version': VERSION, 'world_id': command['world_id'],
                  'kind': 'admission', 'id': admission_id,
                  'body': {'receipt_id': receipt_id, 'principal': principal,
                           'evaluated_revision': current_revision},
                  'refs': {'command': digest(command), 'candidate': digest(candidate)}}
        validate_record(result)
        return result
