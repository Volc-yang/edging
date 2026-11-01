"""Exact neutral records, trusted reference closure, and retained-only lookup."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from collections import Counter
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
import hashlib
import json
import math
import re
from types import MappingProxyType

from .codec import (ContractError, DOMAIN, VERSION, PROFILE, JSON, MAX_INTEGER,
                    canonical, digest, encode_f64, f64, DeploymentContext,
                    HeadBinding, ReceiptVerifier, Record, _validate_tree, _parse_bounded)
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


def _validate_record_v01(record: Record) -> None:
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
    _domain_version: str = "0.1"
    _profile: str = PROFILE
    _artifact_class: str | None = None
    _context: DeploymentContext | None = None
    _binary_items: tuple = ()

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

    @property
    def domain_version(self) -> str:
        return self._domain_version

    @property
    def profile(self) -> str:
        return self._profile

    @property
    def artifact_class(self) -> str | None:
        return self._artifact_class

    @property
    def context(self) -> DeploymentContext | None:
        return self._context

    @property
    def binary_refs(self) -> Mapping[str, "BlobMeta"]:
        return MappingProxyType(dict(self._binary_items))


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
        _validate_record_v01(source)
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


def _validate_closure_v01(records: Sequence[Record], head: str, *, world_id: str,
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


def _validate_archive_v01(archive: JSON, *, world_id: str,
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




@dataclass(frozen=True)
class BlobMeta:
    sha256: str
    byte_count: int
    media_type: str
    artifact_class: str = "genesis-runtime"

    def __post_init__(self) -> None:
        _hash(self.sha256)
        _require(type(self.byte_count) is int and 0 < self.byte_count <= 8388608, "BLOB_LIMIT")
        _require((self.artifact_class, self.media_type) in (
            ("synthetic-contract-only", "application/x-edgeworld-static-vector"),
            ("genesis-runtime", "application/x-genesis-gstraj;version=1.4.3")), "PROFILE")


@dataclass(frozen=True, init=False)
class VerifiedObservation:
    manifest: str
    storage_state: str
    artifact_class: str
    scope: str
    bytes: int
    _state_bytes: bytes
    _event_bytes: bytes | None
    _selected_record_bytes: tuple[tuple[str, bytes], ...]

    def __init__(self, manifest: str, state: Record, event: Record | None,
                 storage_state: str, artifact_class: str, scope: str, bytes: int,
                 selected_records: Mapping[str, Record]) -> None:
        _hash(manifest)
        _require(storage_state in ("ready", "unconfirmed_readonly")
                 and artifact_class in CLASSES and scope == _PROOF_SCOPE, "PROFILE")
        _require(type(bytes) is int and 0 < bytes <= 1048576, "PROOF_LIMIT")
        _require(isinstance(selected_records, Mapping) and manifest in selected_records, "PROOF")
        for key, record in selected_records.items():
            _hash(key); validate_record(record)
            _require(digest(record) == key, "PROOF")
        object.__setattr__(self, "manifest", manifest)
        object.__setattr__(self, "storage_state", storage_state)
        object.__setattr__(self, "artifact_class", artifact_class)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "bytes", bytes)
        object.__setattr__(self, "_state_bytes", canonical(state))
        object.__setattr__(self, "_event_bytes", canonical(event) if event is not None else None)
        object.__setattr__(self, "_selected_record_bytes", tuple((k, canonical(v)) for k, v in selected_records.items()))

    @property
    def state(self) -> Record:
        return json.loads(self._state_bytes)

    @property
    def event(self) -> Record | None:
        return json.loads(self._event_bytes) if self._event_bytes is not None else None

    @property
    def selected_records(self) -> Mapping[str, Record]:
        return MappingProxyType({k: json.loads(v) for k, v in self._selected_record_bytes})


CLASSES = ("synthetic-contract-only", "genesis-runtime")
PLACES = ("city", "wildland", "plain", "forest", "river_marsh", "ocean")
MAX_INT = MAX_INTEGER
_PROOF_SCOPE = "selected-slice-membership-only-not-full-history-or-raw-validation"
require = _require
ident = _identifier
hashref = _hash
uint = _uint
scalar = lambda value: f64(value["$f64"]) if type(value) is dict and set(value) == {"$f64"} else _require(False, "F64")


def exact(value, keys):
    _require(type(value) is dict and set(value) == set(keys), "SCHEMA")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _pack(value):
    """Encode validated packaging without changing canonical record-tree caps."""
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("ascii")


def influence(previous, current):
    with localcontext() as ctx:
        ctx.prec = 2000
        ctx.rounding = ROUND_HALF_EVEN
        return int(((Decimal.from_float(current) - Decimal.from_float(previous)) * Decimal(1000))
                   .to_integral_value(rounding=ROUND_HALF_EVEN))


def wire(raw):
    _require(type(raw) is bytes, "JSON")
    _require(len(raw) <= 1048576 + (1 if raw.endswith(b"\n") else 0), "LIMIT")
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    _require(b"\n" not in raw and b"\r" not in raw, "JSON")
    return _parse_bounded(raw, 1048576)


def _context_values(context):
    _require(type(context) is DeploymentContext, "AUTHORIZATION", "owner deployment context is required")
    return {k: getattr(context, k) for k in ("world_id", "authority_root", "trust_algorithm", "trust_anchor",
                                             "artifact_class", "expected_build", "expected_options")}


def bound_head(binding, context):
    # Both are caller-injected public values; neither is read from response.
    exact(binding, set(context) | {"head", "domain", "version", "profile", "storage_state"})
    _require(binding["authority_root"] == context["authority_root"], "ROOT_MISMATCH")
    _require(all(binding[k] == v for k, v in context.items()), "AUTHORIZATION")
    _require(binding["domain"] == DOMAIN and binding["version"] == "0.2"
             and binding["profile"] == "composite-rigid-support.v0.2"
             and binding["storage_state"] in ("ready", "unconfirmed_readonly"), "PROFILE")
    _hash(binding["head"])
    return binding["head"]


# Frozen composite allowlist; no runtime schema/plugin loading.
_COMPOSITE = {'body': {'admission': {'auth_tag': 'hash',
                        'evaluated_revision': 'uint',
                        'principal': 'id',
                        'receipt_id': 'id'},
          'approval': {'auth_tag': 'hash', 'expires_revision': 'uint', 'principal': 'id', 'receipt_id': 'id'},
          'asset_manifest': {'dependency_status': 'declared-static|runtime-resolved', 'entries': 'assets'},
          'candidate': {'adapter_kind': 'genesis|checkpoint_reuse',
                        'influence_mm': 'nullable_mm',
                        'physics_profile': 'genesis-rigid-support.v0.1',
                        'revision': 'uint',
                        'tick': 'uint'},
          'checkpoint_descriptor': {'artifact_class': 'class',
                                    'byte_count': 'blob_size',
                                    'format': 'synthetic-static-bytes|genesis-gstraj',
                                    'genesis_version': '1.4.3',
                                    'media_type': 'media',
                                    'payload_sha256': 'hash'},
          'command': {},
          'event': {'event_id': 'id'},
          'existence': {'category': 'world|place|physical',
                        'existence_id': 'id',
                        'spirit_record': 'not_separately_assigned'},
          'index': {'command_id': 'id', 'fingerprint': 'hash'},
          'intent': {'action': 'physics_step|retain_snapshot',
                     'budget': 'uint',
                     'case_id': 'nullable_case',
                     'command_id': 'id',
                     'expected_revision': 'uint',
                     'principal': 'id',
                     'random_cursor': 'uint',
                     'tick_delta': 'delta'},
          'manifest': {'revision': 'uint', 'tick': 'uint', 'watermark': 'uint'},
          'physics_binding': {'bindings': 'bindings'},
          'physics_config': {'config': 'i7_config'},
          'physics_sample': {'artifact_class': 'class',
                             'bodies': 'bodies',
                             'contacts': 'contacts',
                             'frame_id': 'genesis-world-si-zup.v0.1',
                             'solver_precision': '32'},
          'physics_snapshot': {'case_id': 'initial|weak|strong', 'physical_step_count': 'steps'},
          'place': {'elevation_cm': 'sint',
                    'footprint_cm': 'polygon',
                    'place_id': 'id',
                    'place_kind': 'city|wildland|plain|forest|river_marsh|ocean'},
          'projection': {'decorations': 'decorations',
                         'development_cm_per_mm': 'f64',
                         'development_layout': 'abstract-magnified',
                         'physical_layout': 'versioned-transform',
                         'projection_version': 'basicshapes-proxy.v0.2'},
          'proposal': {'output': 'output', 'principal': 'id'},
          'provider_build': {'adapter_source_sha256': 'nullable_hash',
                             'artifact_class': 'class',
                             'critical_sources': 'sources',
                             'dependencies': 'dependencies',
                             'distribution': 'genesis-world',
                             'metadata_sha256': 'hash',
                             'python_abi': 'cpython-312',
                             'source_file_count': 'uint',
                             'source_tree_sha256': 'hash',
                             'version': '1.4.3'},
          'resolved_options': {'artifact_class': 'class',
                               'declarations': 'json_object',
                               'exports': 'json_object',
                               'normalizer': 'public-model-dump.v0.2',
                               'parameter_hash': 'hash',
                               'resolution': 'static-declared|runtime-exported'},
          'result': {'command_id': 'id', 'revision': 'uint', 'tick': 'uint', 'watermark': 'uint'},
          'route': {'place_ids': 'ids', 'polyline_cm': 'polyline', 'route_id': 'id'},
          'state': {'budget': 'uint',
                    'development_mm': 'nullable_mm',
                    'random_cursor': 'uint',
                    'revision': 'uint',
                    'tick': 'uint'},
          'unit_transform': {'origin_cm': 'vec3',
                             'scale': 'f64',
                             'signs': 'signs',
                             'source_frame': 'genesis-world-si-zup.v0.1',
                             'target_frame': 'ue-world-cm.v0.2',
                             'transform_version': 'si-to-ue.v0.2'},
          'watercourse': {'polyline_cm': 'polyline', 'watercourse_id': 'id'},
          'world_manifest': {'artifact_class': 'class',
                             'extent_cm': 'extent',
                             'geography_version': 'six-place-proxy.v0.2',
                             'physics_rule': 'rigid-support-influence.v0.1',
                             'revision_rule': 'technical-retain-snapshot.v0.2',
                             'world_seed': 'uint'}},
 'kind_bytes': {'admission': 2048,
                'approval': 2048,
                'asset_manifest': 65536,
                'candidate': 2048,
                'checkpoint_descriptor': 2048,
                'command': 2048,
                'event': 2048,
                'existence': 1024,
                'index': 2048,
                'intent': 2048,
                'manifest': 2048,
                'physics_binding': 4096,
                'physics_config': 16384,
                'physics_sample': 8192,
                'physics_snapshot': 2048,
                'place': 4096,
                'projection': 16384,
                'proposal': 16384,
                'provider_build': 8192,
                'resolved_options': 32768,
                'result': 2048,
                'route': 4096,
                'state': 2048,
                'unit_transform': 2048,
                'watercourse': 4096,
                'world_manifest': 4096},
 'limits': {'archive_bytes': 16777216,
            'asset_bytes': 2147483648,
            'assets': 64,
            'blob_bytes': 8388608,
            'current_records': 288,
            'decorations': 1000,
            'geometry_points': 4096,
            'opaque_refs': 256,
            'proof_records': 96,
            'record_array': 256,
            'record_bytes': 65536,
            'record_depth': 32,
            'record_keys': 64,
            'records': 2048,
            'retained_blob_bytes': 536870912,
            'retained_roots': 64,
            'string_bytes': 4096,
            'wire_bytes': 1048576},
 'proof_kind_max': {'admission': 1,
                    'approval': 1,
                    'asset_manifest': 1,
                    'candidate': 1,
                    'checkpoint_descriptor': 2,
                    'command': 1,
                    'event': 1,
                    'existence': 9,
                    'index': 1,
                    'intent': 1,
                    'manifest': 66,
                    'physics_binding': 1,
                    'physics_config': 1,
                    'physics_sample': 2,
                    'physics_snapshot': 2,
                    'place': 6,
                    'projection': 1,
                    'proposal': 1,
                    'provider_build': 1,
                    'resolved_options': 1,
                    'result': 1,
                    'route': 2,
                    'state': 2,
                    'unit_transform': 1,
                    'watercourse': 1,
                    'world_manifest': 1},
 'proof_wrapper_reserve': 65536,
 'refs': {'admission': {'candidate': 'candidate', 'command': 'command'},
          'approval': {'intent': 'intent', 'proposal': 'proposal'},
          'asset_manifest': {},
          'candidate': {'command': 'command', 'prior_state': 'state', 'snapshot': 'physics_snapshot'},
          'checkpoint_descriptor': {'binding': 'physics_binding',
                                    'build': 'provider_build',
                                    'config': 'physics_config'},
          'command': {'approval': 'approval', 'intent': 'intent', 'proposal': 'proposal'},
          'event': {'admission': 'admission', 'prior_event?': 'event', 'state': 'state'},
          'existence': {},
          'index': {'result': 'result'},
          'intent': {'binding': 'physics_binding', 'config': 'physics_config'},
          'manifest': {'event?': 'event', 'index?': 'index', 'prior_manifest?': 'manifest', 'state': 'state'},
          'physics_binding': {'config': 'physics_config',
                              'dynamic_exists': 'existence',
                              'support_exists': 'existence'},
          'physics_config': {'build': 'provider_build', 'options': 'resolved_options'},
          'physics_sample': {'binding': 'physics_binding', 'config': 'physics_config'},
          'physics_snapshot': {'binding': 'physics_binding',
                               'checkpoint': 'checkpoint_descriptor',
                               'config': 'physics_config',
                               'sample': 'physics_sample'},
          'place': {'existence': 'existence'},
          'projection': {'assets': 'asset_manifest', 'transform': 'unit_transform'},
          'proposal': {},
          'provider_build': {},
          'resolved_options': {'build': 'provider_build'},
          'result': {'checkpoint': 'physics_snapshot',
                     'command': 'command',
                     'event': 'event',
                     'state': 'state'},
          'route': {'pN': 'place'},
          'state': {'snapshot': 'physics_snapshot', 'world': 'world_manifest'},
          'unit_transform': {},
          'watercourse': {'marsh': 'place', 'outlet': 'place', 'upstream': 'place'},
          'world_manifest': {'branch_route': 'route',
                             'city': 'place',
                             'dynamic_existence': 'existence',
                             'forest': 'place',
                             'main_route': 'route',
                             'ocean': 'place',
                             'plain': 'place',
                             'projection': 'projection',
                             'river_marsh': 'place',
                             'support_existence': 'existence',
                             'watercourse': 'watercourse',
                             'wildland': 'place',
                             'world_existence': 'existence'}}}
_PHYSICS_CONFIG = b'{"authority_version":"0.2","backend":"metal","cases":[{"case_id":"weak","gravity_m_s2":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"c000000000000000"}]},{"case_id":"strong","gravity_m_s2":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"c0239eb851eb851f"}]}],"dt_s":{"$f64":"3f847ae147ae147b"},"entities":[{"existence_id":"existence-dynamic","fixed":false,"genesis_name":"i7-dynamic","morph":"sphere","physical_id":"body-dynamic","position_m":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"3ff0000000000000"}],"quaternion_wxyz":[{"$f64":"3ff0000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"}],"radius_m":{"$f64":"3fb999999999999a"},"size_m":null},{"existence_id":"existence-support","fixed":true,"genesis_name":"i7-support","morph":"box","physical_id":"body-support","position_m":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"bfb999999999999a"}],"quaternion_wxyz":[{"$f64":"3ff0000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"0000000000000000"}],"radius_m":null,"size_m":[{"$f64":"4010000000000000"},{"$f64":"4010000000000000"},{"$f64":"3fc999999999999a"}]}],"frame":"genesis-world-si-zup.v0.1","genesis_version":"1.4.3","horizon_advances":32,"init_gravity_m_s2":[{"$f64":"0000000000000000"},{"$f64":"0000000000000000"},{"$f64":"c000000000000000"}],"limits":{"angular_velocity_abs_rad_s":{"$f64":"4059000000000000"},"checkpoint_bytes_max":8388608,"contact_force_abs_n":{"$f64":"412e848000000000"},"contacts_max":32,"fixed_pose_error_m":{"$f64":"3eb0c6f7a0b5ed8d"},"ground_gap_max_m":{"$f64":"3f847ae147ae147b"},"ground_gap_min_m":{"$f64":"bf747ae147ae147b"},"influence_mm_abs_max":1000,"linear_velocity_abs_m_s":{"$f64":"4059000000000000"},"position_abs_m":{"$f64":"4024000000000000"},"quaternion_norm_sq_error":{"$f64":"3f1a36e2eb1c432d"},"samples_per_candidate":2,"settled_vz_abs_m_s":{"$f64":"3fa999999999999a"}},"material":{"friction":{"$f64":"3fe0000000000000"},"gravity_compensation":{"$f64":"0000000000000000"},"needs_coup":false,"rho_kg_m3":{"$f64":"408f400000000000"}},"physics_profile":"genesis-rigid-support.v0.1","requires_grad":false,"rigid_options":{"constraint_timeconst_s":{"$f64":"3f847ae147ae147b"},"enable_collision":true,"enable_mujoco_compatibility":false,"enable_rolling_friction":false,"enable_self_collision":true,"enable_torsional_friction":false,"iterations":25,"ls_iterations":50,"max_collision_pairs":16,"max_contacts":32,"use_hibernation":false},"seed":7,"solver_precision":"32","steps_per_advance":8,"substeps":1,"viewer":false}'

class _CompositeValidation:
    def __init__(self, receipt_verifier=None, context=None):
        self.schema = _COMPOSITE
        self.limits = _COMPOSITE["limits"]
        self.receipt_verifier = receipt_verifier
        self.context = context

    def field(self, value, spec):
        if spec == "id":
            ident(value)
        elif spec == "hash":
            hashref(value)
        elif spec == "nullable_hash":
            if value is not None:
                hashref(value)
        elif spec == "uint":
            uint(value)
        elif spec == "sint":
            require(type(value) is int and abs(value) <= MAX_INT, "INTEGER")
        elif spec == "f64":
            scalar(value)
        elif spec == "nullable_mm":
            require(value is None or type(value) is int and abs(value) <= 1000, "PHYSICS_INVALID")
        elif spec in {"delta", "steps", "blob_size"}:
            uint(value)
            require(value in (0, 1) if spec == "delta" else
                    value <= 256 if spec == "steps" else 0 < value <= 8388608,
                    "BLOB_LIMIT" if spec == "blob_size" else "LIMIT")
        elif spec == "nullable_case":
            require(value in (None, "weak", "strong"), "SCHEMA")
        elif spec == "class":
            require(type(value) is str and value in CLASSES, "PROFILE")
        elif spec == "media":
            require(value in ("application/x-edgeworld-static-vector",
                              "application/x-genesis-gstraj;version=1.4.3"), "PROFILE")
        elif spec == "output":
            require(type(value) is str and len(value) <= 1024, "SCHEMA")
        elif spec == "json_object":
            require(type(value) is dict, "SCHEMA")
        elif spec == "i7_config":
            require(canonical(value) == _PHYSICS_CONFIG, "PROFILE")
        elif spec == "signs":
            require(canonical(value) == b"[1,-1,1]", "SCHEMA")
        elif spec == "vec3":
            require(type(value) is list and len(value) == 3, "SCHEMA")
            for x in value:
                scalar(x)
        elif spec == "extent":
            require(type(value) is list and len(value) == 4, "GEOGRAPHY")
            for x in value:
                self.field(x, "sint")
            require(value[0] < value[2] and value[1] < value[3], "GEOGRAPHY")
        elif spec in {"polygon", "polyline"}:
            require(type(value) is list and (4 if spec == "polygon" else 2) <= len(value) <= 256, "GEOGRAPHY")
            for point in value:
                require(type(point) is list and len(point) == 2, "GEOGRAPHY")
                for x in point:
                    self.field(x, "sint")
            if spec == "polygon":
                require(value[0] == value[-1], "GEOGRAPHY")
        elif spec == "ids":
            require(type(value) is list and 2 <= len(value) <= 6, "GEOGRAPHY")
            for x in value:
                ident(x)
            require(len(value) == len(set(value)), "ID")
        elif spec in {"assets", "decorations", "sources", "dependencies", "bindings", "bodies", "contacts"}:
            self.entries(value, spec)
        else:
            require(type(value) is str and value in spec.split("|"), "SCHEMA")

    def entries(self, values, kind):
        require(type(values) is list, "SCHEMA")
        limits = {"assets": 64, "decorations": 1000, "sources": 32, "dependencies": 16,
                  "bindings": 2, "bodies": 2, "contacts": 32}
        require(len(values) <= limits[kind], "LIMIT")
        identities = []
        for item in values:
            if kind == "assets":
                exact(item, {"asset_id", "uri", "content_sha256", "byte_count", "source", "use", "license_status", "dependencies"})
                ident(item["asset_id"]); hashref(item["content_sha256"]); uint(item["byte_count"])
                require(item["source"] == "installed-ue-5.8.3-basicshapes"
                        and item["use"] == "technical-proxy-not-realism"
                        and item["license_status"] == "ue-installed-content-no-shipping-review", "ASSET")
                require(type(item["uri"]) is str and re.fullmatch(r"/Engine/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+", item["uri"]) is not None, "ASSET")
                require(type(item["dependencies"]) is list, "ASSET")
                for x in item["dependencies"]:
                    ident(x)
                require(len(set(item["dependencies"])) == len(item["dependencies"]), "ASSET")
                identities.append(item["asset_id"])
            elif kind == "decorations":
                exact(item, {"instance_id", "place_id", "asset_id", "position_cm", "scale_milli"})
                for key in ("instance_id", "place_id", "asset_id"):
                    ident(item[key])
                for key in ("position_cm", "scale_milli"):
                    require(type(item[key]) is list and len(item[key]) == 3, "SCHEMA")
                    for x in item[key]:
                        self.field(x, "sint")
                require(all(x > 0 for x in item["scale_milli"]), "SCHEMA")
                identities.append(item["instance_id"])
            elif kind == "sources":
                exact(item, {"path", "sha256"}); hashref(item["sha256"])
                require(type(item["path"]) is str and not item["path"].startswith("/")
                        and ".." not in item["path"].split("/"), "BUILD")
                identities.append(item["path"])
            elif kind == "dependencies":
                exact(item, {"name", "version", "metadata_sha256"}); hashref(item["metadata_sha256"])
                require(type(item["name"]) is str and type(item["version"]) is str, "BUILD")
                identities.append(item["name"])
            elif kind == "bindings":
                exact(item, {"physical_id", "existence_id", "genesis_name", "role", "config_entity_index"})
                for key in ("physical_id", "existence_id", "genesis_name"):
                    ident(item[key])
                uint(item["config_entity_index"])
                require(item["role"] in ("dynamic", "support"), "PHYSICS_INVALID")
                identities.append(item["physical_id"])
            elif kind == "bodies":
                exact(item, {"physical_id", "position_m", "quaternion_wxyz", "linear_velocity_m_s", "angular_velocity_rad_s", "mass_kg"})
                ident(item["physical_id"]); identities.append(item["physical_id"])
                for key, length, bound in (("position_m", 3, 10), ("quaternion_wxyz", 4, 1.001),
                                           ("linear_velocity_m_s", 3, 100), ("angular_velocity_rad_s", 3, 100)):
                    require(type(item[key]) is list and len(item[key]) == length, "PHYSICS_INVALID")
                    require(all(abs(scalar(x)) <= bound for x in item[key]), "PHYSICS_INVALID")
                require(abs(sum(scalar(x)**2 for x in item["quaternion_wxyz"]) - 1) <= 1e-4
                        and scalar(item["mass_kg"]) > 0, "PHYSICS_INVALID")
            elif kind == "contacts":
                exact(item, {"pair", "position_m", "force_on_dynamic_n"})
                require(item["pair"] == ["body-dynamic", "body-support"], "PHYSICS_INVALID")
                self.field(item["position_m"], "vec3"); self.field(item["force_on_dynamic_n"], "vec3")
                require(all(abs(scalar(x)) <= 10 for x in item["position_m"])
                        and all(abs(scalar(x)) <= 1e6 for x in item["force_on_dynamic_n"]), "PHYSICS_INVALID")
        if kind != "contacts":
            require(len(identities) == len(set(identities)), "ID")
        if kind in {"bindings", "bodies"}:
            require(identities == ["body-dynamic", "body-support"], "PHYSICS_INVALID")
        if kind == "assets":
            require(identities == sorted(identities)
                    and sum(item["byte_count"] for item in values) <= 2147483648, "ASSET")
        if kind == "contacts":
            require(values == sorted(values, key=lambda x: (x["pair"], [y["$f64"] for y in x["position_m"]],
                                                           [y["$f64"] for y in x["force_on_dynamic_n"]])), "PHYSICS_INVALID")

    def required_refs(self, record):
        kind = record["kind"]
        refs = self.schema["refs"][kind]
        if kind == "route":
            return {"p" + str(i): "place" for i in range(len(record["body"]["place_ids"]))}
        result = {key.rstrip("?"): val for key, val in refs.items()}
        if kind == "manifest" and record["body"]["revision"] == 0:
            return {"state": "state"}
        if kind == "event" and "prior_event" not in record["refs"]:
            result.pop("prior_event")
        return result

    def record(self, record):
        _validate_tree(record)
        exact(record, {"domain", "version", "world_id", "kind", "id", "body", "refs"})
        require(record["domain"] == DOMAIN and record["version"] == "0.2", "DOMAIN")
        ident(record["world_id"]); ident(record["id"])
        k = record["kind"]
        require(type(k) is str and k in self.schema["body"], "SCHEMA")
        exact(record["body"], self.schema["body"][k])
        for name, spec in self.schema["body"][k].items():
            self.field(record["body"][name], spec)
        exact(record["refs"], self.required_refs(record))
        for ref in record["refs"].values():
            hashref(ref)
        require(len(canonical(record)) <= self.schema["kind_bytes"][k], "LIMIT")

    def target(self, records, record, ref):
        value = record["refs"][ref]
        require(value in records, "REFERENCE")
        return records[value]

    def static_record(self, r, records, context):
        b, k = r["body"], r["kind"]
        get = lambda name: self.target(records, r, name)
        if "artifact_class" in b:
            require(b["artifact_class"] == context["artifact_class"], "PROFILE")
        if k == "existence":
            require(r["id"] == b["existence_id"], "ID")
        elif k == "unit_transform":
            require(scalar(b["scale"]) == 100, "PHYSICS_INVALID")
        elif k == "provider_build":
            require(digest(r) == context["expected_build"], "BUILD")
            if context["artifact_class"] == "genesis-runtime":
                require(b["adapter_source_sha256"] is not None, "BUILD")
        elif k == "resolved_options":
            require(digest(r) == context["expected_options"] and r["refs"]["build"] == context["expected_build"], "BUILD")
            require(b["resolution"] == ("static-declared" if context["artifact_class"] == "synthetic-contract-only" else "runtime-exported"), "BUILD")
            if b["resolution"] == "runtime-exported":
                exact(b["exports"], {"sim_options", "rigid_options", "dynamic_morph", "support_morph", "rigid_material"})
                require(all(type(x) is dict and bool(x) for x in b["exports"].values()), "BUILD")
        elif k == "physics_config":
            require(r["refs"]["build"] == context["expected_build"]
                    and r["refs"]["options"] == context["expected_options"]
                    and get("options")["refs"]["build"] == r["refs"]["build"]
                    and get("options")["body"]["parameter_hash"] == sha(canonical(b["config"])), "BUILD")
        elif k == "physics_binding":
            entities = get("config")["body"]["config"]["entities"]
            for i, binding in enumerate(b["bindings"]):
                e = entities[i]
                require(binding == {"physical_id": e["physical_id"], "existence_id": e["existence_id"],
                                    "genesis_name": e["genesis_name"], "role": "dynamic" if i == 0 else "support",
                                    "config_entity_index": i}, "PHYSICS_INVALID")
                existence = get("dynamic_exists" if i == 0 else "support_exists")["body"]
                require(existence["existence_id"] == binding["existence_id"] and existence["category"] == "physical", "REFERENCE")
        elif k in {"physics_sample", "checkpoint_descriptor", "physics_snapshot"}:
            require(get("binding")["refs"]["config"] == r["refs"]["config"], "PHYSICS_INVALID")
            if k == "checkpoint_descriptor":
                synthetic = b["artifact_class"] == "synthetic-contract-only"
                require(b["format"] == ("synthetic-static-bytes" if synthetic else "genesis-gstraj")
                        and b["media_type"] == ("application/x-edgeworld-static-vector" if synthetic else
                                                "application/x-genesis-gstraj;version=1.4.3")
                        and r["refs"]["build"] == get("config")["refs"]["build"], "PROFILE")
            if k == "physics_snapshot":
                require(all(get(name)["refs"]["config"] == r["refs"]["config"] and
                            get(name)["refs"]["binding"] == r["refs"]["binding"] for name in ("sample", "checkpoint")), "PHYSICS_INVALID")
                require((b["case_id"] == "initial") == (b["physical_step_count"] == 0), "PHYSICS_INVALID")
        elif k == "route":
            require([get("p" + str(i))["body"]["place_id"] for i in range(len(b["place_ids"]))] == b["place_ids"], "GEOGRAPHY")
        elif k == "watercourse":
            require(get("upstream")["body"]["place_kind"] == "forest" and get("marsh")["body"]["place_kind"] == "river_marsh"
                    and get("outlet")["body"]["place_kind"] == "ocean", "GEOGRAPHY")
        elif k == "place":
            require(get("existence")["body"]["category"] == "place", "REFERENCE")
        elif k == "asset_manifest":
            entries = {x["asset_id"]: x for x in b["entries"]}
            visiting, visited = set(), set()
            def visit(name):
                require(name in entries and name not in visiting, "ASSET")
                if name in visited:
                    return
                visiting.add(name)
                for dep in entries[name]["dependencies"]:
                    visit(dep)
                visiting.remove(name); visited.add(name)
            for name in entries:
                visit(name)
            require(b["dependency_status"] == ("declared-static" if context["artifact_class"] == "synthetic-contract-only" else "runtime-resolved"), "ASSET")
        elif k == "projection":
            ids = {x["asset_id"] for x in get("assets")["body"]["entries"]}
            require(all(x["asset_id"] in ids for x in b["decorations"]), "ASSET")
        elif k == "world_manifest":
            require(get("world_existence")["body"]["category"] == "world", "GEOGRAPHY")
            place_ids, existence_ids = [], [get("world_existence")["body"]["existence_id"],
                                          get("dynamic_existence")["body"]["existence_id"], get("support_existence")["body"]["existence_id"]]
            bounds = b["extent_cm"]
            for name in PLACES:
                place = get(name)
                require(place["body"]["place_kind"] == name, "GEOGRAPHY")
                place_ids.append(place["body"]["place_id"])
                existence_ids.append(self.target(records, place, "existence")["body"]["existence_id"])
                require(all(bounds[0] <= p[0] <= bounds[2] and bounds[1] <= p[1] <= bounds[3] for p in place["body"]["footprint_cm"]), "GEOGRAPHY")
            require(len(set(place_ids)) == 6 and len(set(existence_ids)) == 9, "ID")
            main = get("main_route")["body"]["place_ids"]
            branch = get("branch_route")["body"]["place_ids"]
            require(main == [get(x)["body"]["place_id"] for x in ("city", "plain", "forest", "river_marsh", "ocean")]
                    and branch == [get(x)["body"]["place_id"] for x in ("forest", "wildland")], "GEOGRAPHY")
            require(all(bounds[0] <= p[0] <= bounds[2] and bounds[1] <= p[1] <= bounds[3]
                        for name in ("main_route", "branch_route", "watercourse")
                        for p in get(name)["body"]["polyline_cm"]), "GEOGRAPHY")
            decorations = get("projection")["body"]["decorations"]
            require(all(x["place_id"] in place_ids for x in decorations), "GEOGRAPHY")
        elif k == "state":
            world = get("world")
            snapshot = get("snapshot")
            binding = self.target(records, snapshot, "binding")
            require(binding["refs"]["dynamic_exists"] == world["refs"]["dynamic_existence"]
                    and binding["refs"]["support_exists"] == world["refs"]["support_existence"], "REFERENCE")
            require(b["revision"] >= b["tick"] and b["random_cursor"] == b["tick"]
                    and snapshot["body"]["physical_step_count"] == b["tick"] * 8
                    and (b["development_mm"] is None) == (b["tick"] == 0), "TRANSITION")
            if b["revision"] == 0:
                require(b == {"tick": 0, "revision": 0, "random_cursor": 0,
                              "development_mm": None, "budget": 8}, "HEAD")
        elif k == "intent":
            require((b["action"] == "retain_snapshot" and b["tick_delta"] == 0
                     and b["case_id"] is None and b["budget"] == 0)
                    or (b["action"] == "physics_step" and b["tick_delta"] == 1
                        and b["case_id"] in ("weak", "strong")), "TRANSITION")
        elif k == "command":
            approval = get("approval")
            require(approval["refs"] == {"intent": r["refs"]["intent"], "proposal": r["refs"]["proposal"]}
                    and approval["body"]["principal"] == get("intent")["body"]["principal"]
                    == get("proposal")["body"]["principal"], "AUTHORIZATION")
        elif k == "candidate":
            previous, snapshot, command = get("prior_state"), get("snapshot"), get("command")
            intent = self.target(records, command, "intent"); ib = intent["body"]
            before = self.target(records, previous, "snapshot")
            require(b["revision"] == previous["body"]["revision"] + 1
                    and ib["expected_revision"] == previous["body"]["revision"]
                    and ib["random_cursor"] == previous["body"]["random_cursor"], "TRANSITION")
            require(intent["refs"]["config"] == snapshot["refs"]["config"] == before["refs"]["config"]
                    and intent["refs"]["binding"] == snapshot["refs"]["binding"] == before["refs"]["binding"], "PHYSICS_INVALID")
            if ib["action"] == "retain_snapshot":
                require(b["adapter_kind"] == "checkpoint_reuse" and r["refs"]["snapshot"] == previous["refs"]["snapshot"]
                        and b["tick"] == previous["body"]["tick"]
                        and b["influence_mm"] == previous["body"]["development_mm"], "TRANSITION")
            else:
                new_sample = self.target(records, snapshot, "sample")
                old_sample = self.target(records, before, "sample")
                require(b["adapter_kind"] == "genesis" and b["tick"] == previous["body"]["tick"] + 1
                        and snapshot["body"]["case_id"] == ib["case_id"]
                        and snapshot["body"]["physical_step_count"] == before["body"]["physical_step_count"] + 8
                        and b["influence_mm"] == influence(scalar(old_sample["body"]["bodies"][0]["position_m"][2]),
                                                          scalar(new_sample["body"]["bodies"][0]["position_m"][2])), "TRANSITION")
        elif k == "admission":
            candidate, command = get("candidate"), get("command")
            intent = self.target(records, command, "intent")
            approval = self.target(records, command, "approval")
            require(candidate["refs"]["command"] == r["refs"]["command"]
                    and b["principal"] == intent["body"]["principal"]
                    and b["evaluated_revision"] == intent["body"]["expected_revision"]
                    <= approval["body"]["expires_revision"], "AUTHORIZATION")
        elif k == "event":
            admission, state = get("admission"), get("state")
            candidate = self.target(records, admission, "candidate")
            previous = self.target(records, candidate, "prior_state")
            command = self.target(records, candidate, "command")
            intent = self.target(records, command, "intent")["body"]
            require(state["refs"]["snapshot"] == candidate["refs"]["snapshot"]
                    and state["refs"]["world"] == previous["refs"]["world"]
                    and all(state["body"][x] == candidate["body"][y] for x, y in
                            (("tick", "tick"), ("revision", "revision"), ("development_mm", "influence_mm")))
                    and state["body"]["budget"] == previous["body"]["budget"] - intent["budget"]
                    and state["body"]["random_cursor"] == previous["body"]["random_cursor"]
                    + (1 if intent["action"] == "physics_step" else 0), "TRANSITION")
            require((state["body"]["revision"] == 1 and "prior_event" not in r["refs"])
                    or (state["body"]["revision"] > 1 and "prior_event" in r["refs"]
                        and get("prior_event")["refs"]["state"] == candidate["refs"]["prior_state"]), "HEAD")
        elif k == "result":
            event = get("event"); admission = self.target(records, event, "admission")
            state = get("state"); candidate = self.target(records, admission, "candidate")
            intent = self.target(records, get("command"), "intent")
            require(r["refs"]["state"] == event["refs"]["state"]
                    and r["refs"]["command"] == admission["refs"]["command"]
                    and r["refs"]["checkpoint"] == candidate["refs"]["snapshot"], "REFERENCE")
            require(b == {"command_id": intent["body"]["command_id"], "tick": state["body"]["tick"],
                          "revision": state["body"]["revision"], "watermark": state["body"]["revision"]}, "WATERMARK")
        elif k == "index":
            result = get("result")
            require(b == {"command_id": result["body"]["command_id"], "fingerprint": result["refs"]["command"]}, "COMMAND_CONFLICT")

    def transition(self, manifest, records, context, authenticate=True):
        get = lambda record, name: self.target(records, record, name)
        body = manifest["body"]; state = get(manifest, "state"); sb = state["body"]
        require(body == {"tick": sb["tick"], "revision": sb["revision"], "watermark": sb["revision"]}, "WATERMARK")
        snapshot = get(state, "snapshot")
        if body["revision"] == 0:
            require(body["tick"] == 0 and sb["development_mm"] is None and sb["random_cursor"] == 0
                    and sb["budget"] == 8
                    and snapshot["body"] == {"case_id": "initial", "physical_step_count": 0}, "HEAD")
            return
        prior = get(manifest, "prior_manifest"); previous = get(prior, "state")
        event = get(manifest, "event"); result = get(get(manifest, "index"), "result")
        admission = get(event, "admission"); command = get(admission, "command")
        candidate = get(admission, "candidate"); intent = get(command, "intent"); ib = intent["body"]
        approval = get(command, "approval"); proposal = get(command, "proposal")
        require(body["revision"] == prior["body"]["revision"] + 1
                and state["refs"]["world"] == previous["refs"]["world"]
                and event["refs"]["state"] == manifest["refs"]["state"] == result["refs"]["state"]
                and result["refs"]["event"] == manifest["refs"]["event"]
                and event["refs"].get("prior_event") == prior["refs"].get("event"), "HEAD")
        require(candidate["refs"]["prior_state"] == prior["refs"]["state"]
                and candidate["refs"]["command"] == admission["refs"]["command"] == result["refs"]["command"]
                and candidate["refs"]["snapshot"] == state["refs"]["snapshot"] == result["refs"]["checkpoint"], "REFERENCE")
        require(approval["refs"] == {"proposal": command["refs"]["proposal"], "intent": command["refs"]["intent"]}
                and proposal["body"]["principal"] == ib["principal"] == approval["body"]["principal"] == admission["body"]["principal"], "AUTHORIZATION")
        require(ib["expected_revision"] == previous["body"]["revision"] == admission["body"]["evaluated_revision"]
                and ib["random_cursor"] == previous["body"]["random_cursor"]
                and admission["body"]["evaluated_revision"] <= approval["body"]["expires_revision"], "AUTHORIZATION")
        if authenticate:
            require(callable(self.receipt_verifier), "AUTHORIZATION")
            self.receipt_verifier(approval)
            self.receipt_verifier(admission)
        require(candidate["body"]["revision"] == sb["revision"]
                and candidate["body"]["tick"] == sb["tick"]
                and candidate["body"]["influence_mm"] == sb["development_mm"], "TRANSITION")
        before = get(previous, "snapshot")
        require(intent["refs"]["config"] == snapshot["refs"]["config"] == before["refs"]["config"]
                and intent["refs"]["binding"] == snapshot["refs"]["binding"] == before["refs"]["binding"], "PHYSICS_INVALID")
        if ib["action"] == "retain_snapshot":
            require(ib["tick_delta"] == 0 and ib["case_id"] is None and ib["budget"] == 0
                    and candidate["body"]["adapter_kind"] == "checkpoint_reuse"
                    and previous["refs"]["snapshot"] == state["refs"]["snapshot"]
                    and sb["tick"] == previous["body"]["tick"]
                    and all(sb[x] == previous["body"][x] for x in ("development_mm", "budget", "random_cursor")), "TRANSITION")
        else:
            current_sample, old_sample = get(snapshot, "sample"), get(before, "sample")
            znew = scalar(current_sample["body"]["bodies"][0]["position_m"][2])
            zold = scalar(old_sample["body"]["bodies"][0]["position_m"][2])
            require(ib["tick_delta"] == 1 and ib["case_id"] in ("weak", "strong")
                    and candidate["body"]["adapter_kind"] == "genesis"
                    and sb["tick"] == previous["body"]["tick"] + 1
                    and snapshot["body"]["case_id"] == ib["case_id"]
                    and snapshot["body"]["physical_step_count"] == before["body"]["physical_step_count"] + 8
                    and sb["development_mm"] == influence(zold, znew)
                    and sb["budget"] == previous["body"]["budget"] - ib["budget"]
                    and sb["random_cursor"] == previous["body"]["random_cursor"] + 1, "TRANSITION")
        require(result["body"] == {"command_id": ib["command_id"], "tick": sb["tick"],
                                   "revision": sb["revision"], "watermark": sb["revision"]}, "WATERMARK")
        index = get(manifest, "index")
        require(index["body"] == {"command_id": ib["command_id"], "fingerprint": result["refs"]["command"]}, "COMMAND_CONFLICT")

    def archive(self, archive, context, blobs):
        require(self.receipt_verifier is not None, "AUTHORIZATION")
        self.receipt_verifier.assert_context(self.context)
        exact(archive, {"domain", "version", "test_profile", "artifact_class", "records", "head"})
        require(archive["domain"] == DOMAIN and archive["version"] == "0.2", "DOMAIN")
        require(archive["test_profile"] == "composite-rigid-support.v0.2"
                and archive["artifact_class"] == context["artifact_class"], "PROFILE")
        require(type(archive["records"]) is list and 1 <= len(archive["records"]) <= 2048, "LIMIT")
        hashref(archive["head"])
        total = 0
        for record in archive["records"]:
            self.record(record)
            total += len(canonical(record))
            require(total <= 16777216, "LIMIT")
        require(len(_pack(archive)) <= 16777216, "LIMIT")
        records, identities, event_ids, commands = {}, set(), set(), {}
        for record in archive["records"]:
            self.record(record)
            require(record["world_id"] == context["world_id"], "WORLD")
            key = (record["kind"], record["id"])
            require(key not in identities, "ID"); identities.add(key)
            for name, reference in record["refs"].items():
                require(reference in records and records[reference]["kind"] == self.required_refs(record)[name], "REFERENCE")
            d = digest(record); records[d] = record
            self.static_record(record, records, context)
            if record["kind"] in {"approval", "admission"}:
                require(callable(self.receipt_verifier), "AUTHORIZATION")
                self.receipt_verifier(record)
            if record["kind"] == "command":
                intent = self.target(records, record, "intent")["body"]
                key = (intent["principal"], intent["command_id"])
                require(key not in commands or commands[key] == d, "COMMAND_CONFLICT"); commands[key] = d
            if record["kind"] == "event":
                require(record["body"]["event_id"] not in event_ids, "ID"); event_ids.add(record["body"]["event_id"])
            if record["kind"] == "manifest":
                self.transition(record, records, context)
        head = archive["head"]; hashref(head)
        require(head in records and records[head]["kind"] == "manifest", "REFERENCE")
        retained, committed, binary_refs, reachable = [], {}, {}, set()
        def reach(d):
            if d in reachable:
                return
            reachable.add(d)
            r = records[d]
            for child in r["refs"].values():
                reach(child)
            if r["kind"] == "checkpoint_descriptor":
                b = r["body"]; h = b["payload_sha256"]
                require(h in blobs and len(blobs[h]) == b["byte_count"] and sha(blobs[h]) == h, "CORRUPT")
                meta = (b["byte_count"], b["media_type"], b["artifact_class"])
                require(h not in binary_refs or binary_refs[h] == meta, "CORRUPT"); binary_refs[h] = meta
        current = head
        while current:
            require(current not in retained, "REFERENCE"); retained.append(current)
            manifest = records[current]
            if "index" in manifest["refs"]:
                index = self.target(records, manifest, "index"); result = self.target(records, index, "result")
                intent = self.target(records, self.target(records, result, "command"), "intent")["body"]
                key = (intent["principal"], intent["command_id"])
                require(key not in committed, "COMMAND_CONFLICT"); committed[key] = index["refs"]["result"]
            current = manifest["refs"].get("prior_manifest")
        require(len(retained) <= 64, "COUNTS"); reach(head)
        require(sum(x[0] for x in binary_refs.values()) <= 536870912, "BLOB_LIMIT")
        return {"records": records, "retained": tuple(retained), "commands": committed,
                "binary_refs": binary_refs, "counts": self.inventory(records, head, retained, binary_refs, blobs)}

    def inventory(self, records, head, retained, binary_refs, blobs):
        current = set()
        def visit(d):
            if d in current:
                return
            current.add(d)
            for child in records[d]["refs"].values():
                visit(child)
        visit(records[head]["refs"]["state"])
        kinds = Counter(records[d]["kind"] for d in current)
        require(len(current) <= 288, "COUNTS")
        assets = next(records[d]["body"] for d in current if records[d]["kind"] == "asset_manifest")
        decorations = next(records[d]["body"]["decorations"] for d in current if records[d]["kind"] == "projection")
        points = sum(len(records[d]["body"]["footprint_cm" if records[d]["kind"] == "place" else "polyline_cm"])
                     for d in current if records[d]["kind"] in {"place", "route", "watercourse"})
        require(points <= 4096 and len(decorations) <= 1000, "COUNTS")
        return {"H": len(retained), "S_current": len(current), "S_by_kind": dict(sorted(kinds.items())),
                "D": len(decorations), "A_declared": len(assets["entries"]),
                "A_actual": len(assets["entries"]) if assets["dependency_status"] == "runtime-resolved" else None,
                "asset_dependency_status": assets["dependency_status"],
                "asset_bytes_declared": sum(x["byte_count"] for x in assets["entries"]),
                "asset_bytes_actual": sum(x["byte_count"] for x in assets["entries"]) if assets["dependency_status"] == "runtime-resolved" else None,
                "geometry_points": points, "json_objects": len(records),
                "json_bytes_by_kind": {k: sum(len(canonical(r)) for r in records.values() if r["kind"] == k)
                                       for k in sorted({r["kind"] for r in records.values()})},
                "all_json_canonical_bytes": sum(len(canonical(r)) for r in records.values()),
                "retained_raw_unique_files": len(binary_refs), "retained_raw_unique_bytes": sum(x[0] for x in binary_refs.values()),
                "all_supplied_raw_bytes": sum(len(x) for x in blobs.values()),
                "unreferenced_raw_bytes": sum(len(v) for k, v in blobs.items() if k not in binary_refs)}

    def proof(self, raw, context, *, expected_request_id, tick, revision, watermark, trusted_head):
        trusted_storage_state = trusted_head["storage_state"] if type(trusted_head) is dict else None
        trusted_head = bound_head(trusted_head, context)
        env = wire(raw)
        exact(env, {"protocol_version", "request_id", "ok", "result"})
        require(type(env["protocol_version"]) is int and env["protocol_version"] == 1
                and type(env["ok"]) is bool and env["ok"] is True, "SCHEMA")
        ident(expected_request_id); require(env["request_id"] == expected_request_id, "PROOF")
        for value in (tick, revision, watermark):
            uint(value)
        require(watermark == revision, "WATERMARK"); hashref(trusted_head)
        result = env["result"]
        exact(result, {"domain", "version", "world_id", "operation", "payload"})
        require(result["domain"] == DOMAIN and result["version"] == "0.2", "DOMAIN")
        require(result["world_id"] == context["world_id"] and result["operation"] == "observe", "WORLD")
        p = result["payload"]
        exact(p, {"manifest", "state", "event", "watermark", "storage_state", "artifact_class",
                  "head", "membership", "records", "opaque_refs"})
        require(p["storage_state"] in ("ready", "unconfirmed_readonly")
                and p["artifact_class"] == context["artifact_class"], "PROFILE")
        require(p["storage_state"] == trusted_storage_state, "PROOF")
        require(type(p["watermark"]) is int and p["watermark"] == watermark, "WATERMARK")
        require(p["head"] == trusted_head, "PROOF")
        require(type(p["membership"]) is list and 1 <= len(p["membership"]) <= 64
                and type(p["records"]) is list and len(p["records"]) <= 96
                and type(p["opaque_refs"]) is list and len(p["opaque_refs"]) <= 256, "PROOF_LIMIT")
        all_records = p["membership"] + p["records"] + [p["manifest"], p["state"]]
        if p["event"] is not None:
            all_records.append(p["event"])
        records, identities = {}, {}
        for r in all_records:
            self.record(r); require(r["world_id"] == context["world_id"], "WORLD")
            d = digest(r); key = (r["kind"], r["id"])
            require(key not in identities or identities[key] == d, "ID"); identities[key] = d
            records[d] = r
        # Type-check every supplied edge before any recursive dependency expansion.
        # Wrong-kind shared DAGs must not amplify traversal before rejection.
        for r in records.values():
            expected_refs = self.required_refs(r)
            for name, ref in r["refs"].items():
                if ref in records:
                    require(records[ref]["kind"] == expected_refs[name], "PROOF")
        counts = Counter(r["kind"] for r in all_records)
        require(all(counts[k] <= n for k, n in self.schema["proof_kind_max"].items()), "PROOF_LIMIT")
        auxiliary = [digest(r) for r in p["records"]]
        explicit = {digest(r) for r in p["membership"] + [p["manifest"], p["state"]]
                    + ([p["event"]] if p["event"] is not None else [])}
        require(len(auxiliary) == len(set(auxiliary)) and not set(auxiliary) & explicit, "PROOF")
        selected = digest(p["manifest"])
        membership = p["membership"]
        require(all(r["kind"] == "manifest" for r in membership)
                and len({digest(r) for r in membership}) == len(membership)
                and digest(membership[0]) == trusted_head and digest(membership[-1]) == selected, "PROOF")
        for a, b in zip(membership, membership[1:]):
            require(a["refs"].get("prior_manifest") == digest(b)
                    and a["body"]["revision"] == b["body"]["revision"] + 1
                    and a["body"]["tick"] - b["body"]["tick"] in (0, 1), "PROOF")
        require(p["manifest"]["body"] == {"tick": tick, "revision": revision, "watermark": watermark}
                and p["manifest"]["refs"]["state"] == digest(p["state"]), "WATERMARK")
        require((p["event"] is None and revision == 0) or (p["event"] is not None and revision > 0
                and p["manifest"]["refs"]["event"] == digest(p["event"])), "PROOF")
        previous_hash = p["manifest"]["refs"].get("prior_manifest")
        needed = {selected}
        if previous_hash:
            require(previous_hash in records, "PROOF"); needed.add(previous_hash)
        expanded, active = set(), set()
        def expand(d, mode="normal"):
            require(d in records, "PROOF")
            key = (d, mode)
            require(key not in active, "PROOF")
            if key in expanded:
                return
            active.add(key)
            needed.add(d); r = records[d]
            for name, ref in r["refs"].items():
                if r["kind"] == "manifest" and (name == "prior_manifest" or mode == "previous" and name != "state"):
                    continue
                if r["kind"] == "event" and name == "prior_event":
                    continue
                expand(ref)
            active.remove(key)
            expanded.add(key)
        expand(selected)
        if previous_hash:
            expand(previous_hash, "previous")
        membership_hashes = {digest(r) for r in membership}
        require(set(records) == needed | membership_hashes, "PROOF")
        opaque = set()
        for d, r in records.items():
            for name, ref in r["refs"].items():
                if ref in records:
                    require(records[ref]["kind"] == self.required_refs(r)[name], "PROOF")
                else:
                    allowed = r["kind"] == "event" and name == "prior_event"
                    allowed |= r["kind"] == "manifest" and d != selected and name != "state"
                    allowed |= r["kind"] == "manifest" and d in membership_hashes - {selected, previous_hash}
                    require(allowed, "PROOF"); opaque.add(ref)
            if r["kind"] not in {"manifest", "event", "candidate", "admission", "command", "approval", "proposal", "result", "index", "intent"}:
                self.static_record(r, records, context)
        require(p["opaque_refs"] == sorted(opaque), "PROOF")
        self.transition(p["manifest"], records, context, authenticate=False)
        require(len(_pack(env)) <= 1048576, "PROOF_LIMIT")
        return {"manifest": selected, "state": p["state"], "event": p["event"],
                "storage_state": p["storage_state"], "artifact_class": p["artifact_class"],
                "scope": "selected-slice-membership-only-not-full-history-or-raw-validation",
                "bytes": len(raw) - (1 if raw.endswith(b"\n") else 0),
                "selected_records": {d: records[d] for d in needed}}



def validate_record(record: Record) -> None:
    canonical(record)  # Preserve v0.1 error order and all record-tree caps.
    if type(record) is dict and record.get("version") == "0.2":
        _CompositeValidation().record(record)
    else:
        _validate_record_v01(record)


def _mode(domain_version, profile, trusted_receipts, trust_verifier, context, blobs, world_id):
    if domain_version == "0.1":
        _require(profile in (None, PROFILE), "PROFILE")
        _require(context is None and trust_verifier is None and (blobs is None or blobs == {}), "AUTHORIZATION")
        _require(trusted_receipts is not None, "AUTHORIZATION")
        return None
    _require(domain_version == "0.2", "DOMAIN")
    _require(profile in (None, "composite-rigid-support.v0.2"), "PROFILE")
    values = _context_values(context)
    _require(world_id == context.world_id, "WORLD")
    _require(trusted_receipts is None and callable(trust_verifier)
             and callable(getattr(trust_verifier, "assert_context", None)), "AUTHORIZATION")
    trust_verifier.assert_context(context)
    _require(isinstance(blobs, Mapping), "CORRUPT", "complete raw mapping is required")
    return values


def _raw_mapping(blobs):
    _require(isinstance(blobs, Mapping) and len(blobs) <= 2048, "BLOB_LIMIT")
    owned = dict(blobs)
    for key, payload in owned.items():
        _hash(key)
        _require(type(payload) is bytes and 0 < len(payload) <= 8388608, "BLOB_LIMIT")
    return owned


def _composite_archive(archive, context, trust_verifier, blobs):
    values = _context_values(context)
    raw = _raw_mapping(blobs)
    check = _CompositeValidation(trust_verifier, context)
    result = check.archive(archive, values, raw)
    # Validate every supplied descriptor, including orphan objects; none may
    # smuggle missing/corrupt payloads through retained-only idempotency indexing.
    for record in result["records"].values():
        if record["kind"] == "checkpoint_descriptor":
            b = record["body"]; payload = raw.get(b["payload_sha256"])
            _require(payload is not None and len(payload) == b["byte_count"]
                     and sha(payload) == b["payload_sha256"], "CORRUPT")
    closure = object.__new__(ValidatedClosure)
    object.__setattr__(closure, "_head", archive["head"])
    object.__setattr__(closure, "_world_id", context.world_id)
    object.__setattr__(closure, "_record_bytes", tuple((k, canonical(v)) for k, v in result["records"].items()))
    object.__setattr__(closure, "_retained", result["retained"])
    object.__setattr__(closure, "_command_items", tuple(result["commands"].items()))
    object.__setattr__(closure, "_domain_version", "0.2")
    object.__setattr__(closure, "_profile", context.archive_profile)
    object.__setattr__(closure, "_artifact_class", context.artifact_class)
    object.__setattr__(closure, "_context", context)
    object.__setattr__(closure, "_binary_items", tuple((k, BlobMeta(k, *v)) for k, v in result["binary_refs"].items()))
    return closure


def validate_closure(records: Sequence[Record], head: str, *, world_id: str,
                     trusted_receipts: Mapping[str, JSON] | None = None,
                     domain_version: str = "0.1", profile: str | None = None,
                     trust_verifier: ReceiptVerifier | None = None,
                     context: DeploymentContext | None = None,
                     blobs: Mapping[str, bytes] | None = None) -> ValidatedClosure:
    _mode(domain_version, profile, trusted_receipts, trust_verifier, context, blobs, world_id)
    if domain_version == "0.1":
        return _validate_closure_v01(records, head, world_id=world_id, trusted_receipts=trusted_receipts)
    _identifier(world_id); _hash(head)
    _require(isinstance(records, Sequence) and not isinstance(records, (str, bytes, bytearray))
             and 1 <= len(records) <= 2048, "LIMIT")
    archive = {"domain": DOMAIN, "version": "0.2", "test_profile": context.archive_profile,
               "artifact_class": context.artifact_class, "records": list(records), "head": head}
    return _composite_archive(archive, context, trust_verifier, blobs)


def validate_archive(archive: JSON, *, world_id: str,
                     trusted_receipts: Mapping[str, JSON] | None = None,
                     domain_version: str = "0.1", profile: str | None = None,
                     trust_verifier: ReceiptVerifier | None = None,
                     context: DeploymentContext | None = None,
                     blobs: Mapping[str, bytes] | None = None) -> ValidatedClosure:
    _mode(domain_version, profile, trusted_receipts, trust_verifier, context, blobs, world_id)
    if domain_version == "0.1":
        return _validate_archive_v01(archive, world_id=world_id, trusted_receipts=trusted_receipts)
    return _composite_archive(archive, context, trust_verifier, blobs)


def verify_observation(raw: bytes, *, context: DeploymentContext,
                       expected_request_id: str, tick: int, revision: int,
                       watermark: int, trusted_head: HeadBinding) -> VerifiedObservation:
    values = _context_values(context)
    _require(type(trusted_head) is HeadBinding, "AUTHORIZATION", "external HeadBinding is required")
    binding = {name: getattr(trusted_head, name) for name in trusted_head.__dataclass_fields__}
    result = _CompositeValidation(context=context).proof(
        raw, values, expected_request_id=expected_request_id, tick=tick,
        revision=revision, watermark=watermark, trusted_head=binding)
    return VerifiedObservation(**result)
