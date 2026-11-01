"""Explicit local authority registration and stable, lifetime fd ownership.

Importing this module performs no filesystem or process operations. This is the
local-posix-sync-v0.1 profile, not an inter-machine lock or power-loss guarantee.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import errno
import fcntl
import os
from pathlib import Path
import re
import stat

from .codec import ContractError, canonical, decode

_DOMAIN = 'edgeworld.universe.authority'
_VERSION = '0.1'
_PROFILE = 'local-posix-sync-v0.1'
_LOCK = '.authority.lock'
_IDENTITY = 'identity.json'
_HEAD = 'HEAD.json'
_MAX_BYTES = 1_048_576
_OPEN_FLAGS = os.O_CLOEXEC | os.O_NOFOLLOW
_DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | _OPEN_FLAGS


def _error(code: str, detail: str, cause: BaseException | None = None) -> None:
    error = ContractError(code, detail)
    if cause is not None:
        raise error from cause
    raise error


def _regular(info: os.stat_result, label: str) -> None:
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        _error('ROOT_MISMATCH', f'{label} must be a regular file with one link')


def _inode(info: os.stat_result) -> tuple[int, int]:
    return info.st_dev, info.st_ino


def _open_regular(root_fd: int, name: str, flags: int = os.O_RDONLY) -> int:
    descriptor = os.open(name, flags | _OPEN_FLAGS | os.O_NONBLOCK, 0o600, dir_fd=root_fd)
    try:
        _regular(os.fstat(descriptor), name)
    except BaseException:
        os.close(descriptor)
        raise
    return descriptor


def _read(descriptor: int) -> bytes:
    os.lseek(descriptor, 0, os.SEEK_SET)
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = os.read(descriptor, min(65536, _MAX_BYTES + 1 - total))
        if not chunk:
            return b''.join(chunks)
        chunks.append(chunk)
        total += len(chunk)
        if total > _MAX_BYTES:
            _error('ROOT_MISMATCH', 'registration exceeds byte limit')


def _sync_directory(descriptor: int) -> None:
    try:
        os.fsync(descriptor)
    except OSError as exc:
        _error('SYNC_UNSUPPORTED', 'directory synchronization failed', exc)


def _expected(root: Path, world_id: str, info: os.stat_result) -> bytes:
    device, inode = str(info.st_dev), str(info.st_ino)
    if any(re.fullmatch(r'0|[1-9][0-9]{0,19}', value) is None
           for value in (device, inode)):
        _error('ROOT_MISMATCH', 'root identity cannot be encoded by this profile')
    return canonical({
        'domain': _DOMAIN, 'version': _VERSION, 'world_id': world_id,
        'profile': _PROFILE, 'root_canonical': str(root),
        'root_device': device, 'root_inode': inode,
    })


def _validate_identity(root_fd: int, expected: bytes) -> tuple[int, int]:
    descriptor = _open_regular(root_fd, _IDENTITY)
    try:
        raw = _read(descriptor)
        try:
            decoded = decode(raw)
        except ContractError as exc:
            _error('ROOT_MISMATCH', 'invalid registration JSON', exc)
        if canonical(decoded) != expected or raw != expected:
            _error('ROOT_MISMATCH', 'registration does not exactly match root')
        return _inode(os.fstat(descriptor))
    finally:
        os.close(descriptor)


def _create_identity(root_fd: int, expected: bytes) -> tuple[int, int]:
    # Never truncate/repair an earlier partial registration. An interrupted
    # exclusive write leaves evidence and causes a subsequent explicit refusal.
    descriptor = _open_regular(root_fd, _IDENTITY,
                               os.O_WRONLY | os.O_CREAT | os.O_EXCL)
    try:
        remaining = memoryview(expected)
        while remaining:
            count = os.write(descriptor, remaining)
            if count == 0:
                _error('IO_BEFORE_VISIBILITY', 'registration write made no progress')
            remaining = remaining[count:]
        os.fsync(descriptor)
        identity = _inode(os.fstat(descriptor))
    except OSError as exc:
        _error('IO_BEFORE_VISIBILITY', 'registration write or file synchronization failed', exc)
    finally:
        os.close(descriptor)
    _sync_directory(root_fd)
    return identity


@dataclass(frozen=True, init=False)
class Lease:
    """Opaque ownership handle; use acquire(), and close deterministically.

    No explicit LOCK_UN is issued: a fork child's inherited open-file-description
    is also the parent's flock. Closing that child's fd must not release it.
    """
    root: Path
    world_id: str
    owner_pid: int
    profile: str
    initializing: bool
    _root_fd: int = field(repr=False)
    _lock_fd: int = field(repr=False)
    _root_identity: tuple[int, int] = field(repr=False)
    _lock_identity: tuple[int, int] = field(repr=False)
    _identity_inode: tuple[int, int] = field(repr=False)
    _identity_bytes: bytes = field(repr=False)
    _closed: bool = field(repr=False)

    def __init__(self) -> None:
        raise TypeError('Lease is created only by acquire()')

    def check(self) -> None:
        if self._closed:
            _error('CLOSED', 'lease is closed')
        if os.getpid() != self.owner_pid:
            _error('LOCKED', 'fork-inherited lease cannot authorize this process')
        try:
            if self.root.resolve(strict=True) != self.root:
                _error('ROOT_MISMATCH', 'registered canonical path changed')
            root_info = os.stat(self.root, follow_symlinks=False)
            if (not stat.S_ISDIR(root_info.st_mode)
                    or _inode(root_info) != self._root_identity
                    or _inode(os.fstat(self._root_fd)) != self._root_identity):
                _error('ROOT_MISMATCH', 'registered root was replaced')
            lock_info = os.stat(_LOCK, dir_fd=self._root_fd, follow_symlinks=False)
            fd_info = os.fstat(self._lock_fd)
            _regular(lock_info, _LOCK)
            _regular(fd_info, _LOCK)
            if (_inode(lock_info) != self._lock_identity
                    or _inode(fd_info) != self._lock_identity
                    or lock_info.st_size != 0):
                _error('ROOT_MISMATCH', 'stable lock was replaced or modified')
            fcntl.flock(self._lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            actual = _validate_identity(self._root_fd, self._identity_bytes)
            if actual != self._identity_inode:
                _error('ROOT_MISMATCH', 'registration inode was replaced')
        except ContractError:
            raise
        except (OSError, ValueError, RuntimeError) as exc:
            code = 'LOCKED' if getattr(exc, 'errno', None) in (errno.EAGAIN, errno.EACCES) else 'ROOT_MISMATCH'
            _error(code, 'lease ownership check failed', exc)

    def close(self) -> None:
        if self._closed:
            return
        object.__setattr__(self, '_closed', True)
        failure = None
        # Closing in a child is allowed and closes only its inherited references.
        # Do not issue LOCK_UN, delete lockfiles, or close any unrelated fd.
        for descriptor in (self._lock_fd, self._root_fd):
            try:
                os.close(descriptor)
            except OSError as exc:
                if failure is None:
                    failure = exc
        if failure is not None:
            _error('CLOSED', 'lease descriptor close failed', failure)

    def __enter__(self) -> Lease:
        self.check()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        self.close()
        return False


def acquire(root: Path, world_id: str, *, initialize: bool = False) -> Lease:
    """Acquire nonblocking exclusive ownership; reads never implicitly initialize.

    Missing registration in read mode creates nothing. Explicit initialization
    may create one root directory (its parent must exist), a stable empty lock,
    and canonical identity only. Existing HEAD requires recovery, not initialize.
    """
    if not isinstance(root, Path) or type(initialize) is not bool:
        _error('SCHEMA', 'root must be Path and initialize must be bool')
    if type(world_id) is not str or re.fullmatch('[a-z][a-z0-9._-]{0,63}', world_id) is None:
        _error('ID', 'invalid world identifier')
    root_fd = None
    lock_fd = None
    try:
        resolved = root.resolve(strict=False)
        created_root = False
        if initialize:
            try:
                resolved.mkdir(mode=0o700)
                created_root = True
            except FileExistsError:
                pass
        try:
            root_fd = os.open(resolved, _DIRECTORY_FLAGS)
        except FileNotFoundError as exc:
            _error('UNINITIALIZED', 'authority directory does not exist', exc)
        info = os.fstat(root_fd)
        if not stat.S_ISDIR(info.st_mode):
            _error('ROOT_MISMATCH', 'authority root is not a directory')
        expected = _expected(resolved, world_id, info)
        entries = set(os.listdir(root_fd))
        if _IDENTITY not in entries:
            if _HEAD in entries:
                _error('CORRUPT', 'HEAD exists without authority registration')
            if not initialize:
                _error('UNINITIALIZED', 'authority registration does not exist')
            if entries - {_LOCK}:
                _error('ROOT_MISMATCH', 'refusing an unregistered nonempty root')
        if _LOCK not in entries and not initialize:
            _error('UNINITIALIZED', 'stable lockfile does not exist')
        if _IDENTITY in entries and _LOCK not in entries:
            _error('ROOT_MISMATCH', 'registered root lost its stable lockfile')
        if created_root:
            parent_fd = os.open(resolved.parent, _DIRECTORY_FLAGS)
            try:
                _sync_directory(parent_fd)
            finally:
                os.close(parent_fd)
        if initialize:
            try:
                lock_fd = _open_regular(root_fd, _LOCK,
                                        os.O_RDWR | os.O_CREAT | os.O_EXCL)
            except FileExistsError:
                lock_fd = _open_regular(root_fd, _LOCK)
        else:
            lock_fd = _open_regular(root_fd, _LOCK)
        lock_info = os.fstat(lock_fd)
        if lock_info.st_size != 0:
            _error('ROOT_MISMATCH', 'stable lockfile must remain empty')
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EACCES):
                _error('LOCKED', 'authority is already owned', exc)
            raise
        # Re-read under the lock: another initializer could win after preflight.
        entries = set(os.listdir(root_fd))
        if _IDENTITY not in entries:
            if _HEAD in entries:
                _error('CORRUPT', 'HEAD exists without authority registration')
            if not initialize:
                _error('UNINITIALIZED', 'authority registration does not exist')
            if entries - {_LOCK}:
                _error('ROOT_MISMATCH', 'refusing unregistered root contents')
            identity_inode = _create_identity(root_fd, expected)
        else:
            identity_inode = _validate_identity(root_fd, expected)
        if initialize and _HEAD in entries:
            _error('NOT_READY', 'existing HEAD requires recovery, not initialization')
        lease = object.__new__(Lease)
        for name, value in {
            'root': resolved, 'world_id': world_id, 'owner_pid': os.getpid(),
            'profile': _PROFILE, 'initializing': initialize,
            '_root_fd': root_fd, '_lock_fd': lock_fd,
            '_root_identity': _inode(info), '_lock_identity': _inode(lock_info),
            '_identity_inode': identity_inode, '_identity_bytes': expected,
            '_closed': False,
        }.items():
            object.__setattr__(lease, name, value)
        lease.check()
        root_fd = lock_fd = None  # The returned lease now owns both fds.
        return lease
    except ContractError:
        raise
    except FileNotFoundError as exc:
        _error('UNINITIALIZED', 'authority component does not exist', exc)
    except (OSError, ValueError, RuntimeError) as exc:
        _error('ROOT_MISMATCH', 'authority acquisition failed', exc)
    finally:
        close_error = None
        for descriptor in (lock_fd, root_fd):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError as exc:
                    if close_error is None:
                        close_error = exc
        if close_error is not None:
            _error('CLOSED', 'failed acquisition descriptor close failed', close_error)
