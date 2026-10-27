"""Single-manifest persistence boundary for the finite chaos origin worker."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .origin_runtime import OriginError, canonical, initial_manifest, validate_manifest


class ManifestWriteFailure(Exception):
    def __init__(self, replacement_started: bool, cause: Exception):
        super().__init__(str(cause))
        self.replacement_started = replacement_started


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


class ManifestStore:
    """One process owns one state directory; cross-process locking is not offered."""

    def __init__(self, state_dir: Path, initial_world: dict[str, Any]):
        self.state_dir = state_dir.resolve()
        self.manifest_path = self.state_dir / "world.json"
        self.state_dir.mkdir(parents=True, exist_ok=True)
        if self.manifest_path.exists():
            self.manifest = self._read(initial_world)
        else:
            if any(self.state_dir.iterdir()):
                raise OriginError("corrupt_state", "nonempty state directory has no authority manifest")
            candidate = initial_manifest(initial_world)
            try:
                self._write(candidate)
            except ManifestWriteFailure as exc:
                code = "commit_status_uncertain" if exc.replacement_started else "persistence_failed"
                raise OriginError(code, f"cannot publish initial world: {exc}") from exc
            self.manifest = candidate

    def _read(self, initial_world: dict[str, Any]) -> dict[str, Any]:
        try:
            data = json.loads(self.manifest_path.read_text(encoding="utf-8"),
                              object_pairs_hook=_unique_object,
                              parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise OriginError("corrupt_state", f"cannot read authority manifest: {exc}") from exc
        return validate_manifest(data, initial_world)

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)

    def _write(self, payload: dict[str, Any]) -> None:
        encoded = canonical(payload) + b"\n"
        fd, name = tempfile.mkstemp(prefix="chaos-world-", suffix=".json.tmp", dir=self.state_dir)
        temp_path = Path(name)
        replacement_started = False
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(encoded)
                stream.flush()
                os.fsync(stream.fileno())
            replacement_started = True
            os.replace(temp_path, self.manifest_path)
            self._fsync_dir(self.state_dir)
        except Exception as exc:
            try:
                temp_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise ManifestWriteFailure(replacement_started, exc) from exc

    def commit(self, candidate: dict[str, Any]) -> None:
        """Expose candidate in memory only after the durable replacement completes."""
        self._write(candidate)
        self.manifest = candidate
