"""Bounded local immutable JSON/raw objects, HEAD visibility and sync confirmation.

No constructor/import I/O; no commands, recovery module or physical solver.
A successful fsync profile is not a hardware power-loss warranty.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from functools import wraps
import hashlib
import json
import os
import re
import stat
import threading
import weakref
from types import MappingProxyType

from .codec import ContractError, DeploymentContext, ReceiptVerifier, DOMAIN, JSON, MAX_BYTES, canonical, decode, digest
from .ownership import Lease
from .records import BlobMeta, Record, ValidatedClosure, validate_closure, validate_record

_PROFILE = 'local-posix-sync-v0.1'
_BLOB_PROFILE = 'local-posix-blob-sync-v0.2'
_MAX_BLOB = 8_388_608
_MAX_RETAINED_RAW = 536_870_912
_MAX_COMPOSITE = 16_777_216
_HASH = re.compile(r'[0-9a-f]{64}\Z')
_ID = re.compile(r'[a-z][a-z0-9._-]{0,63}\Z')
_FILE_FLAGS = os.O_CLOEXEC | os.O_NOFOLLOW | os.O_NONBLOCK
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW
FaultHook = Callable[[str, Mapping[str, JSON]], None]
_ACTIVE_LOCK = threading.Lock()  # Pure in-memory registry; starts no threads.
_ACTIVE = {}


def _drop_active(key, reference):
    with _ACTIVE_LOCK:
        entry = _ACTIVE.get(key)
        if entry is not None and entry[1] is reference:
            del _ACTIVE[key]


def _operation(function):
    @wraps(function)
    def protected(self, *args, **kwargs):
        if not self._operation_lock.acquire(blocking=False):
            raise StoreError('LOCKED', 'Store operation is already active', phase=function.__name__)
        try:
            return function(self, *args, **kwargs)
        finally:
            self._operation_lock.release()
    return protected


class _SyncFailure(Exception):
    pass


class _FaultFailure(Exception):
    pass


class StoreError(ContractError):
    def __init__(self, code: str, detail: str = '', *,
                 commit_status: str = 'not_attempted', phase: str = '') -> None:
        super().__init__(code, detail)
        self.commit_status = commit_status
        self.phase = phase


def _require(condition: bool, code: str, detail: str = '') -> None:
    if not condition:
        raise ContractError(code, detail)


def _hash(value) -> None:
    _require(type(value) is str and _HASH.fullmatch(value) is not None, 'REFERENCE')


def _identifier(value) -> None:
    _require(type(value) is str and _ID.fullmatch(value) is not None, 'ID')


@dataclass(frozen=True)
class BlobWrite:
    sha256: str
    payload: bytes
    media_type: str
    artifact_class: str = 'genesis-runtime'

    def __post_init__(self) -> None:
        _require(type(self.payload) is bytes, 'SCHEMA', 'raw payload must be immutable bytes')
        BlobMeta(self.sha256, len(self.payload), self.media_type, self.artifact_class)
        _require(hashlib.sha256(self.payload).hexdigest() == self.sha256,
                 'CORRUPT', 'raw payload digest mismatch')


@dataclass(frozen=True)
class CommitBundle:
    expected_head: str
    records: tuple[Record, ...]
    head: str
    principal: str
    command_id: str
    fingerprint: str
    blobs: tuple[BlobWrite, ...] = ()

    def __post_init__(self) -> None:
        _require(type(self.records) is tuple, 'SCHEMA', 'bundle records must be a bounded tuple')
        composite = bool(self.records) and all(type(r) is dict and r.get('version') == '0.2' for r in self.records)
        _require(len(self.records) <= (2048 if composite else 256), 'SCHEMA', 'bundle records must be a bounded tuple')
        total = 0
        for record in self.records:
            total += len(canonical(record))
        _require(total <= (_MAX_COMPOSITE if composite else MAX_BYTES), 'LIMIT')
        _require(type(self.blobs) is tuple and len(self.blobs) <= 2048
                 and all(type(blob) is BlobWrite for blob in self.blobs), 'SCHEMA')
        _require(sum(len(blob.payload) for blob in self.blobs) <= _MAX_RETAINED_RAW, 'BLOB_LIMIT')
        object.__setattr__(self, 'records', deepcopy(self.records))


@dataclass(frozen=True)
class PinnedRoot:
    head: str
    head_bytes: bytes
    objects: Mapping[str, bytes]
    blobs: Mapping[str, bytes] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _hash(self.head)
        _require(type(self.head_bytes) is bytes and isinstance(self.objects, Mapping), 'SCHEMA')
        owned = dict(self.objects)
        for key, value in owned.items():
            _hash(key)
            _require(type(value) is bytes, 'SCHEMA')
        object.__setattr__(self, 'objects', MappingProxyType(owned))
        _require(isinstance(self.blobs, Mapping) and len(self.blobs) <= 2048, 'SCHEMA')
        raw = dict(self.blobs)
        for key, value in raw.items():
            _hash(key)
            _require(type(value) is bytes and 0 < len(value) <= _MAX_BLOB, 'BLOB_LIMIT')
        _require(sum(map(len, raw.values())) <= _MAX_RETAINED_RAW, 'BLOB_LIMIT')
        object.__setattr__(self, 'blobs', MappingProxyType(raw))


@dataclass(frozen=True)
class Snapshot:
    storage_state: str
    closure: ValidatedClosure

    def __post_init__(self) -> None:
        _require(self.storage_state in ('ready', 'unconfirmed_readonly')
                 and type(self.closure) is ValidatedClosure, 'SCHEMA')


@dataclass(frozen=True, init=False)
class CommitReceipt:
    manifest: str
    commit_status: str
    _result_bytes: bytes | None

    def __init__(self, manifest: str, result: Record | None,
                 commit_status: str = 'confirmed') -> None:
        _hash(manifest)
        _require(commit_status == 'confirmed', 'SCHEMA', 'unconfirmed receipt is forbidden')
        if result is not None:
            validate_record(result)
            _require(result['kind'] == 'result', 'SCHEMA')
        object.__setattr__(self, 'manifest', manifest)
        object.__setattr__(self, 'commit_status', commit_status)
        object.__setattr__(self, '_result_bytes', canonical(result) if result is not None else None)

    @property
    def result(self) -> Record | None:
        return json.loads(self._result_bytes) if self._result_bytes is not None else None


class Store:
    def __init__(self, lease: Lease, *, trusted_receipts: Mapping[str, JSON] | None = None,
                 trust_verifier: ReceiptVerifier | None = None,
                 context: DeploymentContext | None = None,
                 fault: FaultHook | None = None) -> None:
        _require(type(lease) is Lease, 'SCHEMA', 'expected authority lease')
        _require((lease.domain_version, lease.profile) in {
            ('0.1', _PROFILE), ('0.2', _BLOB_PROFILE)}, 'PROFILE')
        _require(fault is None or callable(fault), 'SCHEMA')
        self._lease = lease
        self._deployment = context
        self._verifier = trust_verifier
        if lease.domain_version == '0.1':
            _require(context is None and trust_verifier is None, 'PROFILE')
            _require(isinstance(trusted_receipts, Mapping), 'SCHEMA')
            trusted = dict(trusted_receipts)
            canonical(trusted)
            self._trusted = deepcopy(trusted)
        else:
            _require(type(context) is DeploymentContext and context == lease.context,
                     'ROOT_MISMATCH', 'Store deployment context differs from lease')
            _require(trusted_receipts is None and callable(trust_verifier)
                     and callable(getattr(trust_verifier, 'assert_context', None)), 'AUTHORIZATION')
            _require(not any(hasattr(trust_verifier, name) for name in
                             ('sign_approval', 'sign_admission', 'admit')), 'AUTHORIZATION',
                     'Store accepts a read-only verifier, never a signer')
            trust_verifier.assert_context(context)
            self._trusted = None
        self._raw: dict[str, bytes] = {}
        self._fault = fault
        self._state = 'uninitialized' if lease.initializing else 'recovering'
        self._snapshot: Snapshot | None = None
        self._phase = 'constructor'
        self._attempt = 0
        self._operation_lock = threading.Lock()
        key = id(lease)
        with _ACTIVE_LOCK:
            entry = _ACTIVE.get(key)
            active = entry[1]() if entry is not None else None
            if entry is not None and entry[0]() is lease and active is not None and active.state != 'closed':
                raise StoreError('LOCKED', 'Lease already has an active Store', phase='constructor')
            reference = weakref.ref(self, lambda ref: _drop_active(key, ref))
            _ACTIVE[key] = (weakref.ref(lease), reference)

    @property
    def state(self) -> str:
        return self._state

    @property
    def world_id(self) -> str:
        return self._lease.world_id

    @property
    def trusted_receipts(self) -> Mapping[str, JSON]:
        _require(self._lease.domain_version == '0.1', 'PROFILE')
        return MappingProxyType(deepcopy(self._trusted))

    @property
    def trust_verifier(self) -> ReceiptVerifier:
        _require(self._lease.domain_version == '0.2', 'PROFILE')
        return self._verifier

    def _validate(self, records, head, raw=None):
        if self._lease.domain_version == '0.1':
            return validate_closure(records, head, world_id=self.world_id,
                                    trusted_receipts=self._trusted)
        closure = validate_closure(records, head, world_id=self.world_id,
                                   domain_version='0.2', context=self._deployment,
                                   trust_verifier=self._verifier, blobs=raw)
        records_by_hash = closure.records
        reachable = set()
        def visit(reference):
            if reference in reachable:
                return
            reachable.add(reference)
            for child in records_by_hash[reference]['refs'].values():
                visit(child)
        visit(head)
        _require(reachable == set(closure.records), 'REFERENCE', 'unretained records are not Store input')
        _require(set(raw) == set(closure.binary_refs), 'REFERENCE', 'unused raw payload')
        return closure

    def _blob_inputs(self, blobs, retained=None):
        _require(isinstance(blobs, Sequence) and not isinstance(blobs, (str, bytes, bytearray)), 'SCHEMA')
        if self._lease.domain_version == '0.1':
            _require(len(blobs) == 0, 'PROFILE')
            return {}
        _require(len(blobs) <= 2048 and all(type(blob) is BlobWrite for blob in blobs), 'SCHEMA')
        raw = dict(retained or {})
        supplied = {}
        for blob in blobs:
            _require(blob.sha256 not in supplied, 'REFERENCE', 'duplicate supplied raw payload')
            if blob.sha256 in raw:
                _require(raw[blob.sha256] == blob.payload, 'CORRUPT')
            raw[blob.sha256] = blob.payload
            supplied[blob.sha256] = blob
        _require(sum(map(len, raw.values())) <= _MAX_RETAINED_RAW, 'BLOB_LIMIT')
        return raw

    def _check_blob_meta(self, closure, blobs):
        for blob in blobs:
            meta = closure.binary_refs.get(blob.sha256)
            _require(meta is not None, 'REFERENCE', 'unused supplied raw payload')
            _require(meta == BlobMeta(blob.sha256, len(blob.payload), blob.media_type,
                                      blob.artifact_class), 'CORRUPT', 'raw metadata mismatch')

    @_operation
    def close(self) -> None:
        self._state = 'closed'
        self._snapshot = None
        self._raw = {}
        with _ACTIVE_LOCK:
            entry = _ACTIVE.get(id(self._lease))
            if entry is not None and entry[1]() is self:
                del _ACTIVE[id(self._lease)]

    def _guard(self) -> None:
        _require(self._state != 'closed', 'CLOSED')
        try:
            self._lease.check()
        except ContractError as exc:
            self._snapshot = None
            self._raw = {}
            self._state = 'closed' if exc.code == 'CLOSED' else ('corrupt' if exc.code == 'ROOT_MISMATCH' else 'recovering')
            raise

    def _context(self, prior, head, command_id=None, object_digest=None, *, visible=False):
        return MappingProxyType({
            'world_id': self.world_id, 'command_id': command_id,
            'prior_manifest': prior, 'new_manifest': head,
            'object_digest': object_digest, 'visibility_attempted': visible,
        })

    def _notify(self, phase: str, context: Mapping[str, JSON]) -> None:
        self._phase = phase
        self._guard()
        if self._fault is not None:
            try:
                self._fault(phase, context)
            except Exception as exc:
                raise _FaultFailure(phase) from exc

    def _root_fd(self) -> int:
        self._guard()
        return os.open(self._lease.root, _DIRECTORY_FLAGS)

    def _file_fd(self, directory: int, name: str, flags=os.O_RDONLY) -> int:
        self._guard()
        descriptor = os.open(name, flags | _FILE_FLAGS, 0o600, dir_fd=directory)
        try:
            info = os.fstat(descriptor)
            _require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                     'CORRUPT', 'internal object must be regular with one link')
        except BaseException:
            os.close(descriptor)
            raise
        return descriptor

    def _read_fd(self, descriptor: int, maximum: int = MAX_BYTES) -> bytes:
        result = bytearray()
        while True:
            part = os.read(descriptor, min(65536, maximum + 1 - len(result)))
            if not part:
                return bytes(result)
            result.extend(part)
            _require(len(result) <= maximum, 'CORRUPT', 'stored object exceeds byte limit')

    def _read_file(self, directory: int, name: str, maximum: int = MAX_BYTES) -> bytes:
        descriptor = self._file_fd(directory, name)
        try:
            return self._read_fd(descriptor, maximum)
        finally:
            os.close(descriptor)

    def _write_fd(self, descriptor: int, raw: bytes) -> None:
        remaining = memoryview(raw)
        while remaining:
            self._guard()
            count = os.write(descriptor, remaining)
            _require(count > 0, 'IO_BEFORE_VISIBILITY', 'write made no progress')
            remaining = remaining[count:]

    def _head_bytes(self, head: str) -> bytes:
        return canonical({'domain': DOMAIN, 'version': self._lease.domain_version,
                          'world_id': self.world_id, 'manifest': head, 'profile': self._lease.profile})

    def _decode_head(self, raw: bytes) -> str:
        value = decode(raw)
        _require(type(value) is dict and set(value) == {
            'domain', 'version', 'world_id', 'manifest', 'profile'}, 'CORRUPT')
        _require(value['domain'] == DOMAIN and value['version'] == self._lease.domain_version
                 and value['world_id'] == self.world_id and value['profile'] == self._lease.profile, 'CORRUPT')
        _hash(value['manifest'])
        _require(raw == canonical(value), 'CORRUPT', 'HEAD is not exact canonical bytes')
        return value['manifest']

    def _objects_fd(self, root: int, *, create=False) -> int:
        self._guard()
        if create:
            try:
                os.mkdir('objects', 0o700, dir_fd=root)
                self._sync(root)
            except FileExistsError:
                pass
        return os.open('objects', _DIRECTORY_FLAGS, dir_fd=root)

    def _blobs_fd(self, root: int, *, create=False) -> int:
        self._guard()
        if create:
            try:
                os.mkdir('blobs', 0o700, dir_fd=root)
                self._sync(root)
            except FileExistsError:
                pass
        return os.open('blobs', _DIRECTORY_FLAGS, dir_fd=root)

    @staticmethod
    def _blob_name(meta: BlobMeta) -> str:
        return meta.sha256 + ('.static' if meta.artifact_class == 'synthetic-contract-only' else '.gstraj')

    def _sync(self, descriptor: int) -> None:
        self._guard()
        try:
            os.fsync(descriptor)
        except OSError as exc:
            raise _SyncFailure('synchronization call failed') from exc

    def _load(self, root: int) -> tuple[PinnedRoot, ValidatedClosure]:
        raw_head = self._read_file(root, 'HEAD.json')
        head = self._decode_head(raw_head)
        objects_fd = self._objects_fd(root)
        try:
            raw_objects: dict[str, bytes] = {}
            ordered: list[Record] = []
            active: set[str] = set()
            total = 0
            def visit(reference: str) -> None:
                nonlocal total
                _hash(reference)
                _require(reference not in active, 'CORRUPT', 'cyclic object references')
                if reference in raw_objects:
                    return
                _require(len(raw_objects) + len(active) < (2048 if self._deployment else 256), 'CORRUPT', 'closure exceeds record limit')
                active.add(reference)
                raw = self._read_file(objects_fd, reference + '.json')
                total += len(raw)
                _require(total <= (_MAX_COMPOSITE if self._deployment else MAX_BYTES), 'CORRUPT', 'closure exceeds byte limit')
                record = decode(raw)
                validate_record(record)
                _require(raw == canonical(record) and digest(record) == reference
                         and record['world_id'] == self.world_id, 'CORRUPT', 'object name or bytes mismatch')
                for target in record['refs'].values():
                    visit(target)
                active.remove(reference)
                raw_objects[reference] = raw
                ordered.append(record)
            visit(head)
            raw_blobs = {}
            if self._deployment is not None:
                descriptors = {}
                for record in ordered:
                    if record['kind'] == 'checkpoint_descriptor':
                        b = record['body']
                        meta = BlobMeta(b['payload_sha256'], b['byte_count'], b['media_type'], b['artifact_class'])
                        _require(meta.sha256 not in descriptors or descriptors[meta.sha256] == meta, 'CORRUPT')
                        descriptors[meta.sha256] = meta
                _require(sum(meta.byte_count for meta in descriptors.values()) <= _MAX_RETAINED_RAW, 'BLOB_LIMIT')
                directory = self._blobs_fd(root)
                try:
                    for reference, meta in descriptors.items():
                        payload = self._read_file(directory, self._blob_name(meta), meta.byte_count)
                        _require(len(payload) == meta.byte_count and hashlib.sha256(payload).hexdigest() == reference, 'CORRUPT')
                        raw_blobs[reference] = payload
                finally:
                    os.close(directory)
            closure = self._validate(ordered, head, raw_blobs)
            return PinnedRoot(head, raw_head, raw_objects, raw_blobs), closure
        finally:
            os.close(objects_fd)

    @_operation
    def pin(self) -> PinnedRoot:
        self._phase = 'pin'
        try:
            self._guard()
            self._state = 'recovering'
            self._snapshot = None
            self._raw = {}
            self._notify('W0_LOCKED', self._context(None, None))
            root = self._root_fd()
            try:
                pinned, _ = self._load(root)
            finally:
                os.close(root)
            return pinned
        except FileNotFoundError as exc:
            # Only absent HEAD is uninitialized; absent referenced objects corrupt.
            if not (self._lease.root / 'HEAD.json').exists():
                raise StoreError('UNINITIALIZED', 'HEAD is absent', phase=self._phase) from exc
            self._state = 'corrupt'
            raise StoreError('CORRUPT', 'missing referenced storage', phase=self._phase) from exc
        except Exception as exc:
            self._state = 'closed' if isinstance(exc, ContractError) and exc.code == 'CLOSED' else 'corrupt'
            code = exc.code if isinstance(exc, ContractError) and exc.code in ('CLOSED', 'LOCKED', 'ROOT_MISMATCH') else 'CORRUPT'
            raise StoreError(code, 'cannot pin complete authority root', phase=self._phase) from exc

    def _verify_provided(self, pinned: PinnedRoot, closure: ValidatedClosure,
                         actual: PinnedRoot, checked: ValidatedClosure) -> None:
        _require(type(pinned) is PinnedRoot and type(closure) is ValidatedClosure, 'CORRUPT')
        _require(pinned.head == actual.head and pinned.head_bytes == actual.head_bytes
                 and dict(pinned.objects) == dict(actual.objects)
                 and dict(pinned.blobs) == dict(actual.blobs), 'CORRUPT', 'pinned bytes no longer match')
        _require(closure.head == checked.head and closure.world_id == self.world_id
                 and closure.retained == checked.retained
                 and dict(closure.commands) == dict(checked.commands)
                 and closure.domain_version == checked.domain_version
                 and closure.profile == checked.profile and closure.context == checked.context
                 and closure.artifact_class == checked.artifact_class
                 and dict(closure.binary_refs) == dict(checked.binary_refs), 'CORRUPT', 'untrusted closure metadata')
        supplied = {key: canonical(value) for key, value in closure.records.items()}
        _require(supplied == dict(actual.objects), 'CORRUPT', 'closure differs from raw pinned objects')

    @_operation
    def confirm_recovery(self, pinned: PinnedRoot, closure: ValidatedClosure) -> Snapshot:
        self._phase = 'confirm_recovery'
        self._snapshot = None
        self._raw = {}
        if self._state != 'closed':
            self._state = 'recovering'
        try:
            self._guard()
            root = self._root_fd()
            try:
                actual, checked = self._load(root)
                self._verify_provided(pinned, closure, actual, checked)
            finally:
                os.close(root)
        except Exception as exc:
            self._state = 'closed' if isinstance(exc, ContractError) and exc.code == 'CLOSED' else 'corrupt'
            code = exc.code if isinstance(exc, ContractError) and exc.code in ('CLOSED', 'LOCKED', 'ROOT_MISMATCH') else 'CORRUPT'
            raise StoreError(code, 'recovery integrity is not established', phase=self._phase) from exc
        self._state = 'unconfirmed_readonly'
        self._snapshot = Snapshot(self._state, checked)
        self._raw = dict(actual.blobs)
        context = self._context(None, actual.head, visible=True)
        try:
            self._notify('RECOVERY_VALIDATED', context)
            root = self._root_fd()
            try:
                objects_fd = self._objects_fd(root)
                try:
                    for reference, expected in actual.objects.items():
                        descriptor = self._file_fd(objects_fd, reference + '.json')
                        try:
                            _require(self._read_fd(descriptor) == expected, 'CORRUPT')
                            self._sync(descriptor)
                        finally:
                            os.close(descriptor)
                    self._sync(objects_fd)
                finally:
                    os.close(objects_fd)
                if self._deployment is not None:
                    directory = self._blobs_fd(root)
                    try:
                        for reference, meta in checked.binary_refs.items():
                            descriptor = self._file_fd(directory, self._blob_name(meta))
                            try:
                                _require(self._read_fd(descriptor, meta.byte_count) == actual.blobs[reference], 'CORRUPT')
                                self._sync(descriptor)
                            finally:
                                os.close(descriptor)
                            self._notify('RECOVERY_BLOBS_SYNCED', self._context(None, actual.head, object_digest=reference, visible=True))
                        self._sync(directory)
                    finally:
                        os.close(directory)
                descriptor = self._file_fd(root, 'HEAD.json')
                try:
                    _require(self._read_fd(descriptor) == actual.head_bytes, 'CORRUPT')
                    self._sync(descriptor)
                finally:
                    os.close(descriptor)
                self._sync(root)
                self._notify('W9_RECOVERY_SYNCED', context)
            finally:
                os.close(root)
        except Exception as exc:
            if not isinstance(exc, (_SyncFailure, _FaultFailure)):
                code = exc.code if isinstance(exc, ContractError) and exc.code in ('CORRUPT', 'ROOT_MISMATCH', 'CLOSED', 'LOCKED') else 'CORRUPT'
                self._state = 'closed' if code == 'CLOSED' else 'corrupt'
                self._snapshot = None
                self._raw = {}
                raise StoreError(code, 'recovery lost its validated root', commit_status='unknown', phase=self._phase) from exc
            raise StoreError('SYNC_UNSUPPORTED', 'D_recovery not confirmed',
                             commit_status='unknown', phase=self._phase) from exc
        self._state = 'ready'
        self._snapshot = Snapshot('ready', checked)
        return self._snapshot

    def snapshot(self) -> Snapshot:
        # Cache-only read. Caller retains lease through Store.close; no disk probes.
        snapshot, state = self._snapshot, self._state
        if state == 'closed':
            raise StoreError('CLOSED', phase='snapshot')
        if state not in ('ready', 'unconfirmed_readonly') or snapshot is None or snapshot.storage_state != state:
            raise StoreError('NOT_READY', phase='snapshot')
        return snapshot

    @_operation
    def read_blob(self, sha256: str) -> bytes:
        self._phase = 'read_blob'
        _require(self._lease.domain_version == '0.2', 'PROFILE')
        _hash(sha256)
        self._guard()
        closure = self.snapshot().closure
        meta = closure.binary_refs.get(sha256)
        _require(meta is not None and sha256 in self._raw, 'REFERENCE')
        try:
            root = self._root_fd()
            try:
                directory = self._blobs_fd(root)
                try:
                    payload = self._read_file(directory, self._blob_name(meta), meta.byte_count)
                finally:
                    os.close(directory)
            finally:
                os.close(root)
            _require(payload == self._raw[sha256] and len(payload) == meta.byte_count
                     and hashlib.sha256(payload).hexdigest() == sha256, 'CORRUPT')
            return payload
        except Exception as exc:
            self._state = 'corrupt'
            self._snapshot = None
            self._raw = {}
            raise StoreError('CORRUPT', 'pinned raw payload is missing or changed', phase=self._phase) from exc

    def lookup_result(self, principal: str, command_id: str, fingerprint: str) -> Record | None:
        _identifier(principal); _identifier(command_id); _hash(fingerprint)
        if self._state != 'ready':
            raise StoreError('NOT_READY' if self._state != 'closed' else 'CLOSED', phase='lookup_result')
        closure = self.snapshot().closure
        reference = closure.commands.get((principal, command_id))
        if reference is None:
            return None
        result = closure.records[reference]
        if result['refs']['command'] != fingerprint:
            raise StoreError('COMMAND_CONFLICT', phase='lookup_result')
        return result

    @_operation
    def initialize(self, genesis: Sequence[Record], head: str, *,
                   blobs: Sequence[BlobWrite] = ()) -> CommitReceipt:
        self._phase = 'initialize'
        try:
            self._guard()
            _require(self._state == 'uninitialized' and self._lease.initializing, 'NOT_READY')
            raw = self._blob_inputs(blobs)
            closure = self._validate(genesis, head, raw)
            self._check_blob_meta(closure, blobs)
            manifest = closure.records[head]
            _require(manifest['body']['revision'] == 0
                     and (self._deployment is not None or len(closure.records) == 2)
                     and len(closure.retained) == 1, 'SCHEMA', 'initialize accepts only one initial retained root')
        except Exception as exc:
            code = exc.code if isinstance(exc, ContractError) else 'SCHEMA'
            raise StoreError(code, 'initialization input rejected', phase=self._phase) from exc
        return self._publish(closure, prior=None, command_id=None, result=None, initializing=True, raw=raw)

    @_operation
    def commit(self, bundle: CommitBundle) -> CommitReceipt:
        self._phase = 'commit'
        try:
            self._guard()
            _require(self._state == 'ready', 'NOT_READY')
            _require(type(bundle) is CommitBundle, 'SCHEMA')
            _hash(bundle.expected_head); _hash(bundle.head); _hash(bundle.fingerprint)
            _identifier(bundle.principal); _identifier(bundle.command_id)
            previous = self.snapshot().closure
            _require(bundle.expected_head == previous.head, 'HEAD')
            old_records = previous.records
            combined = list(old_records.values()) + list(deepcopy(bundle.records))
            raw = self._blob_inputs(bundle.blobs, self._raw)
            closure = self._validate(combined, bundle.head, raw)
            self._check_blob_meta(closure, bundle.blobs)
            manifest = closure.records[bundle.head]
            _require(manifest['refs'].get('prior_manifest') == previous.head
                     and manifest['body']['revision'] == old_records[previous.head]['body']['revision'] + 1,
                     'HEAD', 'commit must have exactly one successor root')
            result_ref = closure.commands.get((bundle.principal, bundle.command_id))
            _require(result_ref is not None, 'REFERENCE')
            result = closure.records[result_ref]
            index = closure.records[manifest['refs']['index']]
            _require(index['refs']['result'] == result_ref
                     and result['refs']['command'] == bundle.fingerprint, 'COMMAND_CONFLICT')
        except Exception as exc:
            code = exc.code if isinstance(exc, ContractError) else 'SCHEMA'
            raise StoreError(code, 'commit input rejected', phase=self._phase) from exc
        return self._publish(closure, prior=previous.head, command_id=bundle.command_id,
                             result=result, initializing=False, raw=raw)

    def _preserve_old(self, prior: str | None) -> None:
        try:
            root = self._root_fd()
            try:
                if prior is None:
                    try:
                        self._read_file(root, 'HEAD.json')
                    except FileNotFoundError:
                        self._state = 'uninitialized'
                        return
                    raise ContractError('CORRUPT', 'unexpected HEAD during initialize failure')
                actual, _ = self._load(root)
                _require(actual.head == prior and actual.head_bytes == self._head_bytes(prior), 'CORRUPT')
            finally:
                os.close(root)
        except Exception:
            if self._state != 'closed':
                self._state = 'corrupt'
            self._snapshot = None
            self._raw = {}

    def _publish(self, closure: ValidatedClosure, *, prior: str | None,
                 command_id: str | None, result: Record | None, initializing: bool,
                 raw: Mapping[str, bytes]) -> CommitReceipt:
        visible = False
        context = self._context(prior, closure.head, command_id)
        try:
            _require(sum(len(canonical(record)) for record in closure.records.values()) <= (_MAX_COMPOSITE if self._deployment else MAX_BYTES), 'LIMIT')
            self._notify('W0_LOCKED', context)
            root = self._root_fd()
            try:
                if initializing:
                    try:
                        self._read_file(root, 'HEAD.json')
                    except FileNotFoundError:
                        pass
                    else:
                        raise ContractError('NOT_READY', 'HEAD already exists')
                    descriptor = self._file_fd(root, 'identity.json')
                    try:
                        self._sync(descriptor)
                    finally:
                        os.close(descriptor)
                    self._sync(root)
                else:
                    _require(self._read_file(root, 'HEAD.json') == self._head_bytes(prior), 'CORRUPT')
                self._notify('W1_VALIDATED', context)
                objects_fd = self._objects_fd(root, create=initializing)
                try:
                    for reference, record in closure.records.items():
                        expected = canonical(record)
                        try:
                            descriptor = self._file_fd(objects_fd, reference + '.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                        except FileExistsError:
                            descriptor = self._file_fd(objects_fd, reference + '.json')
                            try:
                                _require(self._read_fd(descriptor) == expected, 'CORRUPT', 'existing content-address collision')
                                self._sync(descriptor)
                            finally:
                                os.close(descriptor)
                        else:
                            try:
                                self._write_fd(descriptor, expected)
                                self._sync(descriptor)
                            finally:
                                os.close(descriptor)
                        self._notify('W2_OBJECT_FILE_SYNCED', self._context(prior, closure.head, command_id, reference))
                    self._sync(objects_fd)
                    self._notify('W3_OBJECTS_DIR_SYNCED', context)
                finally:
                    os.close(objects_fd)
                if self._deployment is not None:
                    directory = self._blobs_fd(root, create=initializing)
                    try:
                        for reference, meta in closure.binary_refs.items():
                            expected = raw[reference]
                            try:
                                descriptor = self._file_fd(directory, self._blob_name(meta), os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                            except FileExistsError:
                                descriptor = self._file_fd(directory, self._blob_name(meta))
                                try:
                                    _require(self._read_fd(descriptor, meta.byte_count) == expected, 'CORRUPT', 'existing raw content-address collision')
                                    self._sync(descriptor)
                                finally:
                                    os.close(descriptor)
                            else:
                                try:
                                    self._write_fd(descriptor, expected)
                                    self._sync(descriptor)
                                finally:
                                    os.close(descriptor)
                            self._notify('BLOB_FILE_SYNCED', self._context(prior, closure.head, command_id, reference))
                        self._sync(directory)
                        self._notify('BLOBS_DIR_SYNCED', context)
                    finally:
                        os.close(directory)
                self._attempt += 1
                temporary = f'HEAD.{closure.head}.{os.getpid()}.{self._attempt}.tmp'
                descriptor = self._file_fd(root, temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                try:
                    self._write_fd(descriptor, self._head_bytes(closure.head))
                    self._sync(descriptor)
                finally:
                    os.close(descriptor)
                self._notify('W4_HEAD_FILE_SYNCED', context)
                if prior is not None:
                    _require(self._read_file(root, 'HEAD.json') == self._head_bytes(prior), 'CORRUPT')
                else:
                    _require('HEAD.json' not in os.listdir(root), 'CORRUPT')
                # Invalidate before the public boundary hook and replace attempt.
                visible = True
                self._state = 'recovering'
                self._snapshot = None
                self._raw = {}
                context = self._context(prior, closure.head, command_id, visible=True)
                self._notify('W5_BEFORE_REPLACE', context)
                self._guard()
                os.replace(temporary, 'HEAD.json', src_dir_fd=root, dst_dir_fd=root)
                self._notify('W6_AFTER_REPLACE', context)
                self._sync(root)
                self._notify('W7_ROOT_SYNCED', context)
                self._notify('W8_BEFORE_RESPONSE', context)
            finally:
                os.close(root)
            self._snapshot = Snapshot('ready', closure)
            self._raw = dict(raw)
            self._state = 'ready'
            return CommitReceipt(closure.head, result)
        except Exception as exc:
            if visible:
                self._state = 'recovering'
                self._snapshot = None
                self._raw = {}
                raise StoreError('COMMIT_UNKNOWN', 'visibility attempted; recovery required',
                                 commit_status='unknown', phase=self._phase) from exc
            if isinstance(exc, _SyncFailure):
                self._state = 'recovering'
                self._snapshot = None
                self._raw = {}
                raise StoreError('SYNC_UNSUPPORTED', 'sync failed before visibility; fresh recovery required', phase=self._phase) from exc
            if isinstance(exc, ContractError) and exc.code in ('CORRUPT', 'ROOT_MISMATCH'):
                self._state = 'corrupt'
                self._snapshot = None
                self._raw = {}
            else:
                self._preserve_old(prior)
            code = exc.code if isinstance(exc, ContractError) else 'IO_BEFORE_VISIBILITY'
            raise StoreError(code, 'publication failed before visibility', phase=self._phase) from exc
