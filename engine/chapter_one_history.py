"""Append-only round history for the Chapter One snapshot (risk R5).

The live snapshot in ``models/chapter_one_snapshot.json`` only ever holds the
*current* round. That makes replay, audit and save migration impossible: once a
frontend advances the world, the previous round is gone.

This module keeps an immutable archive of every round plus a hash-chained
index, so that:

* every round can be loaded again by tick (replay),
* tampering or truncation is detectable (the chain breaks),
* stored rounds carry an explicit schema version and can be migrated
  deliberately instead of being silently reinterpreted.

Layout under the models directory::

    models/
      chapter_one_snapshot.json          live snapshot (schema v2)
      chapter_one_snapshot.json.lock     round lock (see snapshot_store)
      history/
        index.json                       hash-chained manifest
        index.json.lock                  history lock
        rounds/
          tick-000001.json               one archived round, never rewritten

Round files are written once and never modified. The index is written
atomically and is the only mutable part. A crash between the two leaves an
orphan round file, which :meth:`ChapterOneHistory.verify` reports rather than
hides.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Optional

from snapshot_store import (
    SnapshotError,
    read_snapshot,
    snapshot_lock,
    write_snapshot_atomic,
)

HISTORY_SCHEMA_VERSION = "edgeworld.chapter-one-history.v1"

#: Migration registry: ``from_schema -> (to_schema, fn(payload) -> payload)``.
#: There is no legacy data in the repository yet, so the registry starts empty;
#: :func:`register_migration` exists so a real migration can be added and tested
#: the moment an old schema shows up. Unknown or newer schemas are always
#: rejected rather than guessed at.
_MIGRATIONS: dict[str, tuple[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]]] = {}


def register_migration(
    from_schema: str,
    to_schema: str,
    migrate: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> None:
    """Register a deliberate, one-way migration between two schema versions."""
    _MIGRATIONS[from_schema] = (to_schema, migrate)


def migrate_payload(payload: Mapping[str, Any], target_schema: str) -> Mapping[str, Any]:
    """Return ``payload`` upgraded to ``target_schema``.

    Raises :class:`SnapshotError` when no migration path exists, so an
    unsupported save is reported instead of being silently misread.
    """
    seen: list[str] = []
    current = dict(payload)
    while True:
        schema = str(current.get("schema_version", ""))
        if schema == target_schema:
            return current
        if schema in seen:
            raise SnapshotError(f"migration cycle detected for {schema!r}")
        seen.append(schema)
        if schema not in _MIGRATIONS:
            raise SnapshotError(
                f"no migration registered for schema {schema!r}; "
                f"supported targets: {target_schema!r}, known sources: {sorted(_MIGRATIONS)}"
            )
        to_schema, migrate = _MIGRATIONS[schema]
        current = dict(migrate(current))
        current["schema_version"] = to_schema


def _round_filename(tick: int) -> str:
    return f"tick-{tick:06d}.json"


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _entry_hash(prev_hash: Optional[str], tick: int, round_sha256: str) -> str:
    material = f"{prev_hash or ''}|{tick}|{round_sha256}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class ChapterOneHistory:
    """Append-only, hash-chained archive of Chapter One rounds."""

    def __init__(self, models_dir: "str | Path") -> None:
        self.models_dir = Path(models_dir)
        self.history_dir = self.models_dir / "history"
        self.rounds_dir = self.history_dir / "rounds"
        self.index_path = self.history_dir / "index.json"

    # ------------------------------------------------------------------ write
    def append(self, snapshot: Mapping[str, Any], source: str = "unknown") -> dict[str, Any]:
        """Archive one round and extend the index. Idempotent per tick.

        The whole operation runs under the history lock so two frontends
        cannot interleave index updates.
        """
        tick = snapshot.get("tick")
        if type(tick) is not int or tick < 1:
            raise SnapshotError("cannot archive a snapshot without a positive tick")

        with snapshot_lock(self.index_path, timeout=60.0):
            index = self._read_index()
            existing = {entry["tick"]: entry for entry in index["entries"]}
            if tick in existing:
                # The round is already archived; keep the archive immutable.
                return existing[tick]

            self.rounds_dir.mkdir(parents=True, exist_ok=True)
            record = {
                "history_schema_version": HISTORY_SCHEMA_VERSION,
                "tick": tick,
                "source": source,
                "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "snapshot": snapshot,
            }
            encoded = json.dumps(record, ensure_ascii=False, indent=2).encode("utf-8")
            round_path = self.rounds_dir / _round_filename(tick)
            if not round_path.exists():
                round_path.write_bytes(encoded)

            round_sha = _sha256_of_bytes(encoded)
            prev_hash = index.get("chain_head")
            entry = {
                "tick": tick,
                "file": f"rounds/{_round_filename(tick)}",
                "sha256": round_sha,
                "prev_hash": prev_hash,
                "entry_hash": _entry_hash(prev_hash, tick, round_sha),
                "recorded_at": record["recorded_at"],
                "chapter_score": self._dig(snapshot, "validation", "score"),
                "encounter": self._dig(snapshot, "encounter", "primary_hexagram", "name"),
                "changed_hexagram": self._dig(snapshot, "encounter", "changed_hexagram", "name"),
                "decision_source": self._dig(snapshot, "decision", "source"),
                "source": source,
            }
            index["entries"].append(entry)
            index["chain_head"] = entry["entry_hash"]
            index["updated_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
            write_snapshot_atomic(self.index_path, index)
            return entry

    # ------------------------------------------------------------------- read
    def entries(self) -> list[dict[str, Any]]:
        return list(self._read_index()["entries"])

    def index(self) -> dict[str, Any]:
        return self._read_index()

    def load(self, tick: int) -> Mapping[str, Any]:
        """Load the archived snapshot for ``tick``."""
        for entry in self._read_index()["entries"]:
            if entry["tick"] == tick:
                path = self.history_dir / entry["file"]
                if not path.exists():
                    raise SnapshotError(f"archived round {tick} is missing: {path}")
                record = json.loads(path.read_text(encoding="utf-8"))
                return record["snapshot"]
        raise SnapshotError(f"tick {tick} is not in the round history")

    def replay_ticks(self) -> list[int]:
        """Ticks available for deterministic replay, in order."""
        return [entry["tick"] for entry in self._read_index()["entries"]]

    def _read_index(self) -> dict[str, Any]:
        if not self.index_path.exists():
            return {"schema_version": HISTORY_SCHEMA_VERSION, "chain_head": None, "entries": []}
        try:
            payload = json.loads(self.index_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise SnapshotError(f"cannot read round history index: {exc}") from exc
        if payload.get("schema_version") != HISTORY_SCHEMA_VERSION:
            payload = dict(migrate_payload(payload, HISTORY_SCHEMA_VERSION))
        return payload

    # --------------------------------------------------------------- integrity
    def verify(self) -> dict[str, Any]:
        """Recompute the chain and report every inconsistency found."""
        problems: list[str] = []
        index = self._read_index()
        entries = index["entries"]

        prev_hash: Optional[str] = None
        seen_ticks: set[int] = set()
        for entry in entries:
            tick = entry["tick"]
            if tick in seen_ticks:
                problems.append(f"duplicate tick {tick} in index")
            seen_ticks.add(tick)

            path = self.history_dir / entry["file"]
            if not path.exists():
                problems.append(f"tick {tick}: archived file missing ({entry['file']})")
                continue

            actual_sha = _sha256_of_bytes(path.read_bytes())
            if actual_sha != entry["sha256"]:
                problems.append(f"tick {tick}: archived file was modified (sha256 mismatch)")
            if entry["prev_hash"] != prev_hash:
                problems.append(f"tick {tick}: chain link broken (prev_hash mismatch)")
            expected = _entry_hash(entry["prev_hash"], tick, entry["sha256"])
            if expected != entry["entry_hash"]:
                problems.append(f"tick {tick}: entry hash does not match its contents")
            prev_hash = entry["entry_hash"]

        if index.get("chain_head") != prev_hash:
            problems.append("index chain_head does not match the last entry")

        orphans = self._orphan_rounds(seen_ticks)
        for name in orphans:
            problems.append(f"orphan archived round with no index entry: {name}")

        return {
            "ok": not problems,
            "rounds": len(entries),
            "chain_head": index.get("chain_head"),
            "problems": problems,
        }

    def _orphan_rounds(self, indexed_ticks: set[int]) -> list[str]:
        if not self.rounds_dir.exists():
            return []
        orphans = []
        for path in sorted(self.rounds_dir.glob("tick-*.json")):
            try:
                tick = int(path.stem.split("-")[1])
            except (IndexError, ValueError):
                orphans.append(path.name)
                continue
            if tick not in indexed_ticks:
                orphans.append(path.name)
        return orphans

    # -------------------------------------------------------------- migration
    def migrate_round(self, tick: int, target_schema: str) -> Mapping[str, Any]:
        """Return the archived round for ``tick`` migrated to ``target_schema``."""
        return migrate_payload(self.load(tick), target_schema)

    @staticmethod
    def _dig(payload: Mapping[str, Any], *keys: str) -> Any:
        current: Any = payload
        for key in keys:
            if not isinstance(current, Mapping) or key not in current:
                return None
            current = current[key]
        return current

    def iter_rounds(self) -> Iterator[Mapping[str, Any]]:
        for tick in self.replay_ticks():
            yield self.load(tick)


def load_live_snapshot(models_dir: "str | Path") -> Optional[dict[str, Any]]:
    """Convenience wrapper: read the live snapshot from a models directory."""
    return read_snapshot(Path(models_dir) / "chapter_one_snapshot.json")
