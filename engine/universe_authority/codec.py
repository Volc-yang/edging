"""Strict, side-effect-free values and bytes for the neutral authority profile."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol, TypeAlias, Union

JSON: TypeAlias = Union[None, bool, int, str, list["JSON"], dict[str, "JSON"]]
Record: TypeAlias = dict[str, JSON]
DOMAIN = "edgeworld.universe.authority"
VERSION = "0.1"
PROFILE = "neutral-transfer-v0.1"
MAX_INTEGER = (1 << 53) - 1
MAX_BYTES = 1 << 20
MAX_DEPTH = 32
_PREFIX = b"edgeworld.universe.authority\x00v0.1\x00"
_BITS = re.compile(r"[0-9a-f]{16}\Z")


class ContractError(ValueError):
    """A stable error code with bounded diagnostic text, never a state snapshot."""

    def __init__(self, code: str, detail: str = "") -> None:
        if type(code) is not str or type(detail) is not str:
            raise TypeError("code and detail must be strings")
        self.code = code
        self.detail = detail.encode("utf-8", "backslashreplace")[:4096].decode("utf-8", "ignore")
        super().__init__(code + (": " + self.detail if self.detail else ""))


def f64(bits: str) -> float:
    """Decode finite binary64 bits without losing signed zero or subnormals."""
    if type(bits) is not str or _BITS.fullmatch(bits) is None:
        raise ContractError("F64", "expected 16 lowercase hexadecimal digits")
    value = struct.unpack(">d", bytes.fromhex(bits))[0]
    if not math.isfinite(value):
        raise ContractError("F64", "non-finite binary64")
    return value


def encode_f64(value: float) -> dict[str, str]:
    if type(value) is not float or not math.isfinite(value):
        raise ContractError("F64", "expected a finite Python float")
    return {"$f64": struct.pack(">d", value).hex()}


def _string(value: str) -> None:
    try:
        size = len(value.encode("utf-8", "strict"))
    except UnicodeError as exc:
        raise ContractError("UNICODE", "not a Unicode scalar string") from exc
    if size > 4096:
        raise ContractError("LIMIT", "string exceeds 4096 UTF-8 bytes")


def _validate_tree(value: JSON) -> None:
    # Iterative traversal also fails closed for in-memory cycles and deep input.
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        if depth > MAX_DEPTH:
            raise ContractError("LIMIT", "value depth exceeds 32")
        kind = type(item)
        if item is None or kind is bool:
            continue
        if kind is int:
            if abs(item) > MAX_INTEGER:
                raise ContractError("INTEGER", "unsafe JSON integer")
        elif kind is str:
            _string(item)
        elif kind is list:
            if len(item) > 256:
                raise ContractError("LIMIT", "array exceeds 256 entries")
            stack.extend((child, depth + 1) for child in item)
        elif kind is dict:
            if len(item) > 64:
                raise ContractError("LIMIT", "object exceeds 64 members")
            for key, child in item.items():
                if type(key) is not str:
                    raise ContractError("SCHEMA", "object keys must be strings")
                stack.append((key, depth + 1))
                stack.append((child, depth + 1))
            if "$f64" in item:
                if set(item) != {"$f64"}:
                    raise ContractError("F64", "typed float has extra fields")
                f64(item["$f64"])
        else:
            raise ContractError("NUMBER", "only JSON primitives and tagged binary64 are allowed")


def _pairs(items: list[tuple[str, JSON]]) -> dict[str, JSON]:
    result: dict[str, JSON] = {}
    for key, value in items:
        if key in result:
            raise ContractError("DUPLICATE_KEY", "duplicate decoded object key")
        result[key] = value
    return result


def _integer_token(token: str) -> int:
    if len(token.removeprefix("-")) > 16:
        raise ContractError("INTEGER", "unsafe JSON integer")
    value = int(token)
    if abs(value) > MAX_INTEGER:
        raise ContractError("INTEGER", "unsafe JSON integer")
    return value


def _number_token(_token: str) -> None:
    raise ContractError("NUMBER", "untyped floating number")


def decode(raw: bytes) -> JSON:
    """Decode archive JSON; JSONL framing belongs to the wire entry point."""
    if type(raw) is not bytes:
        raise ContractError("JSON", "expected bytes")
    if len(raw) > MAX_BYTES:
        raise ContractError("LIMIT", "input exceeds 1 MiB")
    try:
        text = raw.decode("utf-8", "strict")
        if text.startswith("\ufeff"):
            raise ContractError("UNICODE", "BOM is forbidden")
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer_token,
                           parse_float=_number_token, parse_constant=_number_token)
        _validate_tree(value)
        return value
    except UnicodeError as exc:
        raise ContractError("UNICODE", "invalid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContractError("JSON", "invalid JSON") from exc
    except RecursionError as exc:
        raise ContractError("LIMIT", "JSON nesting exceeds parser capacity") from exc


def canonical(value: JSON) -> bytes:
    _validate_tree(value)
    return json.dumps(value, ensure_ascii=True, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def digest(record: dict[str, JSON]) -> str:
    # Full record-kind validation is records.py's job; no sibling import here.
    if type(record) is not dict or record.get("domain") != DOMAIN or record.get("version") not in ("0.1", "0.2"):
        raise ContractError("DOMAIN", "unsupported record domain/version")
    prefix = _PREFIX if record["version"] == "0.1" else b"edgeworld.universe.authority\x00v0.2\x00"
    return hashlib.sha256(prefix + canonical(record)).hexdigest()


def _id(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[a-z][a-z0-9._-]{0,63}", value) is None:
        raise ContractError("ID", "invalid identifier")


def _hash(value: str) -> None:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ContractError("REFERENCE", "invalid digest")


def _root(value: str) -> None:
    if (type(value) is not str or not value.startswith("/") or value.startswith("//")
            or "\x00" in value or ".." in PurePosixPath(value).parts
            or str(PurePosixPath(value)) != value):
        raise ContractError("ROOT_MISMATCH", "expected canonical absolute root")
    _string(value)


def _trust_profile(version: str, algorithm: str) -> None:
    if type(version) is not str or type(algorithm) is not str or version != "0.2" or algorithm != "local-hmac-sha256.v0.2":
        raise ContractError("PROFILE", "unsupported trust profile")


@dataclass(frozen=True)
class ProvisionSpec:
    world_id: str
    authority_root: Path
    domain_version: str = "0.2"
    trust_algorithm: str = "local-hmac-sha256.v0.2"

    def __post_init__(self) -> None:
        _id(self.world_id)
        if not isinstance(self.authority_root, Path):
            raise ContractError("ROOT_MISMATCH", "expected root Path")
        _root(str(self.authority_root))
        _trust_profile(self.domain_version, self.trust_algorithm)


@dataclass(frozen=True)
class TrustAnchor:
    world_id: str
    authority_root: str
    domain_version: str
    trust_algorithm: str
    trust_anchor: str

    def __post_init__(self) -> None:
        _id(self.world_id); _root(self.authority_root); _hash(self.trust_anchor)
        _trust_profile(self.domain_version, self.trust_algorithm)


@dataclass(frozen=True)
class DeploymentContext:
    world_id: str
    authority_root: str
    trust_anchor: str
    expected_build: str
    expected_options: str
    artifact_class: str = "genesis-runtime"
    trust_algorithm: str = "local-hmac-sha256.v0.2"
    domain_version: str = "0.2"
    archive_profile: str = "composite-rigid-support.v0.2"
    storage_profile: str = "local-posix-blob-sync-v0.2"

    def __post_init__(self) -> None:
        _id(self.world_id); _root(self.authority_root)
        for value in (self.trust_anchor, self.expected_build, self.expected_options):
            _hash(value)
        _trust_profile(self.domain_version, self.trust_algorithm)
        if (type(self.artifact_class) is not str or type(self.archive_profile) is not str
                or type(self.storage_profile) is not str
                or self.artifact_class not in ("genesis-runtime", "synthetic-contract-only")
                or self.archive_profile != "composite-rigid-support.v0.2"
                or self.storage_profile != "local-posix-blob-sync-v0.2"):
            raise ContractError("PROFILE", "unsupported deployment profile")


@dataclass(frozen=True)
class HeadBinding:
    head: str
    world_id: str
    authority_root: str
    trust_algorithm: str
    trust_anchor: str
    expected_build: str
    expected_options: str
    artifact_class: str
    domain: str
    version: str
    profile: str
    storage_state: str

    def __post_init__(self) -> None:
        _hash(self.head)
        DeploymentContext(self.world_id, self.authority_root, self.trust_anchor,
                          self.expected_build, self.expected_options, self.artifact_class,
                          self.trust_algorithm, self.version, self.profile)
        if type(self.domain) is not str or type(self.storage_state) is not str or self.domain != DOMAIN or self.storage_state not in ("ready", "unconfirmed_readonly"):
            raise ContractError("PROFILE", "unsupported head binding")


@dataclass(frozen=True)
class OwnerSession:
    principal: str
    can_initialize: bool
    allowed_actions: tuple[str, ...]

    def __post_init__(self) -> None:
        _id(self.principal)
        if (type(self.can_initialize) is not bool or type(self.allowed_actions) is not tuple
                or any(type(x) is not str or x not in ("retain_snapshot", "physics_step")
                       for x in self.allowed_actions)
                or len(set(self.allowed_actions)) != len(self.allowed_actions)):
            raise ContractError("AUTHORIZATION", "invalid owner session")


class ReceiptVerifier(Protocol):
    def assert_context(self, context: DeploymentContext) -> None: ...
    def __call__(self, receipt: Record) -> None: ...


class ApprovalSigner(Protocol):
    def authorize_read(self, principal: str, world_id: str) -> None: ...
    def assert_context(self, context: DeploymentContext) -> None: ...
    def sign_approval(self, unsigned: Record) -> Record: ...


class TrustVerifier(Protocol):
    def authorize_read(self, principal: str, world_id: str) -> None: ...
    def verify_approval(self, approval: Record, proposal: Record, intent: Record) -> None: ...
    def admit(self, command: Record, candidate: Record, *, current_revision: int,
              admission_id: str) -> Record: ...


def _parse_bounded(raw: bytes, maximum: int) -> JSON:
    """Strict parser without applying record-tree caps to packaging arrays."""
    if type(raw) is not bytes:
        raise ContractError("JSON", "expected bytes")
    if len(raw) > maximum:
        raise ContractError("LIMIT", "input byte limit")
    try:
        text = raw.decode("utf-8", "strict")
        if text.startswith("\ufeff"):
            raise ContractError("UNICODE", "BOM is forbidden")
        return json.loads(text, object_pairs_hook=_pairs, parse_int=_integer_token,
                          parse_float=_number_token, parse_constant=_number_token)
    except UnicodeError as exc:
        raise ContractError("UNICODE", "invalid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise ContractError("JSON", "invalid JSON") from exc
    except RecursionError as exc:
        raise ContractError("LIMIT", "JSON nesting exceeds parser capacity") from exc


def decode_archive(raw: bytes, *, domain_version: str = "0.1") -> JSON:
    if domain_version == "0.1":
        return decode(raw)
    if domain_version != "0.2":
        raise ContractError("DOMAIN", "unsupported archive version")
    archive = _parse_bounded(raw, 16 << 20)
    if type(archive) is not dict or set(archive) != {"domain", "version", "test_profile", "artifact_class", "records", "head"}:
        raise ContractError("SCHEMA", "invalid archive packaging")
    if archive["domain"] != DOMAIN or archive["version"] != domain_version:
        raise ContractError("DOMAIN", "archive version mismatch")
    if archive["test_profile"] != "composite-rigid-support.v0.2" or archive["artifact_class"] not in ("synthetic-contract-only", "genesis-runtime"):
        raise ContractError("PROFILE", "unsupported archive profile")
    if type(archive["records"]) is not list or not 1 <= len(archive["records"]) <= 2048:
        raise ContractError("LIMIT", "archive record count")
    _hash(archive["head"])
    for record in archive["records"]:
        _validate_tree(record)
    return archive
