"""Cross-process safe access to the shared Chapter One snapshot.

Both Chapter One frontends (Godot and UE5) and the SceneKit diagnostic preview
invoke ``tools/run_chapter_one.py``, which performs a read-modify-write cycle on
``models/chapter_one_snapshot.json``:

    read current tick  ->  compute the next world state  ->  write the snapshot

The write itself is already atomic (temp file + ``os.replace``), but two
concurrent submissions could still both read tick ``N`` and both write tick
``N + 1``, silently losing one round. This module serialises the whole cycle
with an advisory ``flock`` on a sidecar lock file, so concurrent players
advance the world strictly one round at a time.

This module is deliberately dependency-free (standard library only) so that it
can be imported by the CLI, the runtime and the tests without cycles.
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Optional

SNAPSHOT_SCHEMA_VERSION = "edgeworld.chapter-one-snapshot.v2"

#: How long a caller waits for another process to finish its round.
DEFAULT_LOCK_TIMEOUT_SECONDS = 30.0
#: Poll interval while waiting for the lock.
DEFAULT_LOCK_POLL_SECONDS = 0.05


class SnapshotError(ValueError):
    """Raised when the shared snapshot cannot be used safely."""


class SnapshotLockTimeout(SnapshotError):
    """Raised when another process holds the snapshot lock for too long."""


def lock_path(path: "str | os.PathLike[str]") -> Path:
    """Return the sidecar lock path used to serialise writes for ``path``."""
    snapshot_path = Path(path)
    return snapshot_path.with_name(snapshot_path.name + ".lock")


@contextmanager
def snapshot_lock(
    path: "str | os.PathLike[str]",
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    poll: float = DEFAULT_LOCK_POLL_SECONDS,
) -> Iterator[None]:
    """Hold an exclusive advisory lock covering one full world round.

    The lock is taken on a sidecar ``<snapshot>.lock`` file rather than on the
    snapshot itself, because the snapshot is replaced atomically on every write
    and its inode changes.
    """
    snapshot_path = Path(path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = lock_path(snapshot_path)
    handle = os.open(sidecar, os.O_RDWR | os.O_CREAT, 0o644)
    deadline = time.monotonic() + max(timeout, 0.0)
    try:
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.EAGAIN):
                    raise
                if time.monotonic() >= deadline:
                    raise SnapshotLockTimeout(
                        f"another process held the snapshot lock for longer than {timeout:g}s: {sidecar}"
                    ) from exc
                time.sleep(poll)
        yield
    finally:
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(handle)


def read_snapshot(path: "str | os.PathLike[str]") -> Optional[dict[str, Any]]:
    """Read and validate the shared snapshot.

    Returns ``None`` when the file does not exist yet (first round). Raises
    :class:`SnapshotError` for unreadable, malformed or unsupported snapshots
    so that a damaged file never silently resets world time.
    """
    snapshot_path = Path(path)
    if not snapshot_path.exists():
        return None
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SnapshotError(f"cannot read snapshot: {exc}") from exc
    if not isinstance(payload, Mapping):
        raise SnapshotError("snapshot root must be a JSON object")
    if payload.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotError(
            f"unsupported snapshot schema: {payload.get('schema_version')!r} "
            f"(expected {SNAPSHOT_SCHEMA_VERSION!r})"
        )
    return dict(payload)


def next_tick_from_snapshot(path: "str | os.PathLike[str]") -> int:
    """Return the tick after the one currently stored in the snapshot."""
    payload = read_snapshot(path)
    if payload is None:
        return 1
    current_tick = payload.get("tick")
    if type(current_tick) is not int or current_tick < 1:
        raise SnapshotError("cannot advance from a snapshot without a positive tick")
    return current_tick + 1


def write_snapshot_atomic(path: "str | os.PathLike[str]", payload: Mapping[str, Any]) -> Path:
    """Write ``payload`` to ``path`` atomically (temp file + ``os.replace``)."""
    snapshot_path = Path(path)
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2)
    temporary_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=snapshot_path.parent, delete=False
        ) as temporary:
            temporary.write(serialized)
            temporary.flush()
            os.fsync(temporary.fileno())
            temporary_path = Path(temporary.name)
        temporary_path.replace(snapshot_path)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()
    return snapshot_path
