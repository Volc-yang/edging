"""Exact neutral records, trusted reference closure, and retained-only lookup."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import json
import math
import re
from types import MappingProxyType

from .codec import (ContractError, DOMAIN, VERSION, PROFILE, JSON, MAX_INTEGER,
                    canonical, digest, encode_f64, f64)

Record = dict[str, JSON]
_ID = re.compile(r"[a-z][a-z0-9._-]{0,63}\Z")
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_FIELDS = {
    "proposal": {"principal", "output"},
    "intent": {"command_id", "principal", "expected_revision", "tick_delta", "transfer", "budget", "random_cursor"},
    "approval": {"principal", "receipt_id", "expires_revision"},
    "command": set(),
    "candidate": {"adapter_kind", "test_profile", "value", "tick", "revision"},
    "admission": {"receipt_id", "principal", "evaluated_revision"},
    "state": {"tick", "revision", "value", "budget", "random_cursor"},
    "event": {"event_id"},
    "result": {"command_id", "tick", "revision", "watermark"},
    "index": {"command_id", "fingerprint"},
    "manifest": {"tick", "revision", "watermark"},
}
_REFS = {
    "proposal": {}, "intent": {}, "state": {},
    "approval": {"proposal": "proposal", "intent": "intent"},
    "command": {"proposal": "proposal", "intent": "intent", "approval": "approval"},
    "candidate": {"command": "command", "prior_state": "state"},
    "admission": {"command": "command", "candidate": "candidate"},
    "event": {"state": "state", "admission": "admission", "prior_event": "event"},
    "result": {"command": "command", "state": "state", "event": "event", "checkpoint": "candidate"},
    "index": {"result": "result"},
    "manifest": {"state": "state", "event": "event", "index": "index", "prior_manifest": "manifest"},
}
_UINT_FIELDS = {"tick", "revision", "watermark", "expected_revision", "tick_delta",
                "budget", "random_cursor", "expires_revision", "evaluated_revision"}
_ID_FIELDS = {"principal", "command_id", "receipt_id", "event_id"}


def _require(condition: bool, code: str, detail: str = "") -> None:
    if not condition:
        raise ContractError(code, detail)


def _uint(value: JSON) -> None:
    _require(type(value) is int and 0 <= value <= MAX_INTEGER, "INTEGER")


def _identifier(value: JSON) -> None:
    _require(type(value) is str and _ID.fullmatch(value) is not None, "ID")


def _hash(value: JSON) -> None:
    _require(type(value) is str and _HASH.fullmatch(value) is not None, "REFERENCE")


def validate_record(record: Record) -> None:
    canonical(record)  # Includes strict scalar, container, and typed-float limits.
    _require(type(record) is dict and set(record) == {
        "domain", "version", "world_id", "kind", "id", "body", "refs"}, "SCHEMA")
    _require(record["domain"] == DOMAIN and record["version"] == VERSION, "DOMAIN")
    _identifier(record["world_id"])
    _identifier(record["id"])
    kind = record["kind"]
    _require(type(kind) is str and kind in _FIELDS, "SCHEMA")
    body, refs = record["body"], record["refs"]
    _require(type(body) is dict and set(body) == _FIELDS[kind], "SCHEMA")
    required = set(_REFS[kind])
    if kind == "event":
        required.remove("prior_event")
    if kind == "manifest" and body["revision"] == 0:
        required = {"state"}
        allowed = required
    else:
        allowed = set(_REFS[kind])
    _require(type(refs) is dict and required <= set(refs) <= allowed, "REFERENCE")
    for reference in refs.values():
        _hash(reference)
    for name in _UINT_FIELDS & set(body):
        _uint(body[name])
    for name in _ID_FIELDS & set(body):
        _identifier(body[name])
    if kind == "intent":
        _require(body["tick_delta"] in (0, 1), "INTEGER")
    for name in {"value", "transfer"} & set(body):
        _require(type(body[name]) is dict and set(body[name]) == {"$f64"}, "F64")
    if kind == "proposal":
        _require(type(body["output"]) is str and len(body["output"]) <= 1024, "SCHEMA")
    elif kind == "candidate":
        _require(body["adapter_kind"] == "fake" and body["test_profile"] == PROFILE, "PROFILE")
    elif kind == "index":
        _hash(body["fingerprint"])


@dataclass(frozen=True, init=False)
class ValidatedClosure:
    """Internally constructed; immutable bytes prevent aliasing of nested JSON."""

    _head: str
    _world_id: str
    _record_bytes: tuple[tuple[str, bytes], ...]
    _retained: tuple[str, ...]
    _command_items: tuple[tuple[tuple[str, str], str], ...]

    def __init__(self, *args, **kwargs) -> None:
        raise ContractError("SCHEMA", "use validate_closure")

    @property
    def head(self) -> str:
        return self._head

    @property
    def world_id(self) -> str:
        return self._world_id

    @property
    def retained(self) -> tuple[str, ...]:
        return self._retained

    @property
    def records(self) -> Mapping[str, Record]:
        # These bytes are internal validated canonical objects, not new wire input.
        return MappingProxyType({key: json.loads(raw) for key, raw in self._record_bytes})

    @property
    def commands(self) -> Mapping[tuple[str, str], str]:
        return MappingProxyType(dict(self._command_items))


class _Validation:
    def __init__(self, world_id: str, trusted: Mapping[str, JSON]) -> None:
        self.world = world_id
        self.trusted = trusted
        self.records: dict[str, Record] = {}
        self.identities: set[tuple[str, str]] = set()
        self.event_ids: set[str] = set()
        self.fingerprints: dict[tuple[str, str], str] = {}

    def target(self, record: Record, name: str) -> Record:
        return self.records[record["refs"][name]]

    def check_receipt(self, receipt_id: str, expected: dict[str, JSON]) -> None:
        # JSON booleans and integers are distinct even though Python True == 1.
        _require(canonical(self.trusted.get(receipt_id)) == canonical(expected), "AUTHORIZATION")

    def add(self, source: Record) -> None:
        validate_record(source)
        _require(source["world_id"] == self.world, "WORLD")
        identity = (source["kind"], source["id"])
        _require(identity not in self.identities, "ID")
        for name, reference in source["refs"].items():
            _require(reference in self.records, "REFERENCE")
            _require(self.records[reference]["kind"] == _REFS[source["kind"]][name], "REFERENCE")
        # Copy only after rejecting custom types; do not reapply inbound byte caps
        # to ensure_ascii-expanded canonical data already owned by this validator.
        record = deepcopy(source)
        record_hash = digest(record)
        self.check_semantics(record, record_hash)
        self.identities.add(identity)
        self.records[record_hash] = record

    def check_semantics(self, r: Record, record_hash: str) -> None:
        kind, b = r["kind"], r["body"]
        if kind == "approval":
            principal = b["principal"]
            expected = {"kind": kind, "principal": principal,
                        "intent": r["refs"]["intent"], "proposal": r["refs"]["proposal"],
                        "expires_revision": b["expires_revision"]}
            self.check_receipt(b["receipt_id"], expected)
            _require(self.target(r, "intent")["body"]["principal"] == principal
                     == self.target(r, "proposal")["body"]["principal"], "AUTHORIZATION")
        elif kind == "command":
            _require(self.target(r, "approval")["refs"] == {
                "intent": r["refs"]["intent"], "proposal": r["refs"]["proposal"]}, "AUTHORIZATION")
            intent = self.target(r, "intent")["body"]
            key = (intent["principal"], intent["command_id"])
            _require(key not in self.fingerprints or self.fingerprints[key] == record_hash, "COMMAND_CONFLICT")
            self.fingerprints[key] = record_hash
        elif kind == "candidate":
            intent = self.target(self.target(r, "command"), "intent")["body"]
            prior = self.target(r, "prior_state")["body"]
            _require(intent["expected_revision"] == prior["revision"]
                     and b["revision"] == prior["revision"] + 1
                     and b["tick"] == prior["tick"] + intent["tick_delta"], "HEAD")
            value = f64(prior["value"]["$f64"]) + f64(intent["transfer"]["$f64"])
            _require(math.isfinite(value), "TRANSITION")
            _require(b["value"] == encode_f64(value), "TRANSITION")
        elif kind == "admission":
            candidate = self.target(r, "candidate")
            command = self.target(r, "command")
            intent = self.target(command, "intent")["body"]
            approval = self.target(command, "approval")["body"]
            expected = {"kind": kind, "principal": b["principal"],
                        "command": r["refs"]["command"], "candidate": r["refs"]["candidate"],
                        "evaluated_revision": b["evaluated_revision"]}
            self.check_receipt(b["receipt_id"], expected)
            _require(candidate["refs"]["command"] == r["refs"]["command"]
                     and b["principal"] == intent["principal"]
                     and b["evaluated_revision"] == intent["expected_revision"]
                     and b["evaluated_revision"] <= approval["expires_revision"], "AUTHORIZATION")
        elif kind == "state":
            if b["revision"] == 0:
                _require(b["tick"] == b["random_cursor"] == 0, "HEAD")
        elif kind == "event":
            _require(b["event_id"] not in self.event_ids, "ID")
            self.event_ids.add(b["event_id"])
            state = self.target(r, "state")["body"]
            admission = self.target(r, "admission")
            candidate = self.target(admission, "candidate")
            intent = self.target(self.target(admission, "command"), "intent")["body"]
            prior = self.target(candidate, "prior_state")["body"]
            _require(all(state[key] == candidate["body"][key] for key in ("tick", "revision", "value"))
                     and state["budget"] == prior["budget"] - intent["budget"]
                     and intent["random_cursor"] == prior["random_cursor"]
                     and state["random_cursor"] == prior["random_cursor"] + 1, "TRANSITION")
            _require((state["revision"] == 1) == ("prior_event" not in r["refs"]), "REFERENCE")
            if "prior_event" in r["refs"]:
                _require(self.target(r, "prior_event")["refs"]["state"] == candidate["refs"]["prior_state"], "REFERENCE")
        elif kind == "result":
            state = self.target(r, "state")["body"]
            event = self.target(r, "event")
            admission = self.target(event, "admission")
            intent = self.target(self.target(r, "command"), "intent")["body"]
            _require(b["command_id"] == intent["command_id"]
                     and event["refs"]["state"] == r["refs"]["state"]
                     and admission["refs"]["command"] == r["refs"]["command"]
                     and admission["refs"]["candidate"] == r["refs"]["checkpoint"], "REFERENCE")
            _require(b["tick"] == state["tick"] and b["revision"] == state["revision"]
                     and b["watermark"] == b["revision"], "WATERMARK")
        elif kind == "index":
            result = self.target(r, "result")
            _require(b["fingerprint"] == result["refs"]["command"]
                     and b["command_id"] == result["body"]["command_id"], "COMMAND_CONFLICT")
        elif kind == "manifest":
            state = self.target(r, "state")
            if b["revision"] == 0:
                _require(b == {"tick": 0, "revision": 0, "watermark": 0}
                         and state["body"]["revision"] == 0, "HEAD")
                return
            event = self.target(r, "event")
            result = self.target(self.target(r, "index"), "result")
            _require(event["refs"]["state"] == r["refs"]["state"]
                     == result["refs"]["state"] and result["refs"]["event"] == r["refs"]["event"], "REFERENCE")
            _require(b == {"tick": state["body"]["tick"], "revision": state["body"]["revision"],
                           "watermark": state["body"]["revision"]}, "WATERMARK")
            previous = self.target(r, "prior_manifest")
            candidate = self.target(result, "checkpoint")
            _require(b["revision"] == previous["body"]["revision"] + 1
                     and candidate["refs"]["prior_state"] == previous["refs"]["state"]
                     and event["refs"].get("prior_event") == previous["refs"].get("event"), "HEAD")


def validate_closure(records: Sequence[Record], head: str, *, world_id: str,
                     trusted_receipts: Mapping[str, JSON]) -> ValidatedClosure:
    _identifier(world_id)
    _hash(head)
    _require(isinstance(records, Sequence) and not isinstance(records, (str, bytes, bytearray))
             and 1 <= len(records) <= 256, "LIMIT")
    _require(isinstance(trusted_receipts, Mapping), "SCHEMA")
    # Take a validated defensive copy of the injected JSON map before lookup.
    trusted = dict(trusted_receipts)
    canonical(trusted)
    trusted = deepcopy(trusted)
    check = _Validation(world_id, trusted)
    for record in records:
        check.add(record)
    _require(head in check.records and check.records[head]["kind"] == "manifest", "REFERENCE")
    retained: list[str] = []
    committed: dict[tuple[str, str], str] = {}
    current = head
    while current:
        _require(current not in retained, "REFERENCE")
        retained.append(current)
        manifest = check.records[current]
        if "index" in manifest["refs"]:
            index = check.target(manifest, "index")
            result = check.target(index, "result")
            intent = check.target(check.target(result, "command"), "intent")["body"]
            key = (intent["principal"], intent["command_id"])
            _require(key not in committed or committed[key] == index["refs"]["result"], "COMMAND_CONFLICT")
            committed[key] = index["refs"]["result"]
        current = manifest["refs"].get("prior_manifest", "")
    closure = object.__new__(ValidatedClosure)
    object.__setattr__(closure, "_head", head)
    object.__setattr__(closure, "_world_id", world_id)
    object.__setattr__(closure, "_record_bytes", tuple((key, canonical(value)) for key, value in check.records.items()))
    object.__setattr__(closure, "_retained", tuple(retained))
    object.__setattr__(closure, "_command_items", tuple(committed.items()))
    return closure


def validate_archive(archive: JSON, *, world_id: str,
                     trusted_receipts: Mapping[str, JSON]) -> ValidatedClosure:
    """Validate the exact archive wrapper, then its independently pinned closure."""
    canonical(archive)
    _require(type(archive) is dict and set(archive) == {
        "domain", "version", "test_profile", "records", "head"}, "SCHEMA")
    _require(archive["domain"] == DOMAIN and archive["version"] == VERSION, "DOMAIN")
    _require(archive["test_profile"] == PROFILE, "PROFILE")
    _require(type(archive["records"]) is list, "SCHEMA")
    return validate_closure(archive["records"], archive["head"], world_id=world_id,
                            trusted_receipts=trusted_receipts)


def select(closure: ValidatedClosure, *, tick: int, revision: int, watermark: int) -> Record:
    _require(type(closure) is ValidatedClosure and hasattr(closure, "_record_bytes"), "SCHEMA")
    for number in (tick, revision, watermark):
        _uint(number)
    _require(watermark == revision, "WATERMARK")
    records = closure.records
    for reference in closure.retained:
        manifest = records[reference]
        body = manifest["body"]
        if body["tick"] == tick and body["revision"] == revision and body["watermark"] == watermark:
            return manifest  # Fresh decoded tree, not a closure-owned alias.
    raise ContractError("NOT_FOUND", "exact retained tick/revision/watermark is absent")
