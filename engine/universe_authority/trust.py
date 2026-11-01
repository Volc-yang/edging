"""Explicit local key provisioning and context-bound receipt MACs.

No import/constructor filesystem work, external accounts, provider or writer.
A signature authenticates bytes; prepare/commands owns policy and admission.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import hmac
import os
from pathlib import Path
import stat

from .codec import (
    ApprovalSigner, ContractError, DeploymentContext, DOMAIN, JSON, MAX_INTEGER,
    OwnerSession, ProvisionSpec, Record, ReceiptVerifier, TrustAnchor,
    canonical, digest, _hash, _id, _root,
)

_KEY_NAME = "authority.key"
_PUBLIC_KEY = bytes(range(32))
_ANCHOR_PREFIX = b"edgeworld.universe.trust-anchor\x00v0.2\x00"
_RECEIPT_PREFIX = b"edgeworld.universe.receipt\x00v0.2\x00"
_TOKEN = object()


def _require(condition, code="AUTHORIZATION", detail="invalid local trust input"):
    if not condition:
        raise ContractError(code, detail)


def _anchor(key, world_id, root):
    return hashlib.sha256(_ANCHOR_PREFIX + world_id.encode("ascii") + b"\x00"
                          + root.encode("utf-8") + b"\x00" + key).hexdigest()


def _key_allowed(key):
    _require(type(key) is bytes and len(key) == 32 and key != _PUBLIC_KEY,
             detail="unavailable or forbidden key")


def _flags():
    _require(all(hasattr(os, x) for x in ("O_NOFOLLOW", "O_DIRECTORY", "O_CLOEXEC", "geteuid")),
             detail="safe local key profile unavailable")
    return os.O_NOFOLLOW | os.O_CLOEXEC


def _locations(key_dir, authority_root):
    _require(isinstance(key_dir, Path), detail="key directory must be a Path")
    spelling = str(key_dir)
    try:
        _root(spelling)
    except ContractError as exc:
        raise ContractError("AUTHORIZATION", "unsafe key directory spelling") from exc
    _require(os.path.realpath(spelling) == spelling, detail="key directory aliases are forbidden")
    _require(os.path.realpath(authority_root) == authority_root, "ROOT_MISMATCH", "authority root alias")
    _require(os.path.commonpath((spelling, authority_root)) != authority_root,
             detail="key directory must be outside authority root")
    return spelling


def _directory(fd):
    info = os.fstat(fd)
    _require(stat.S_ISDIR(info.st_mode) and stat.S_IMODE(info.st_mode) == 0o700
             and info.st_uid == os.geteuid(), detail="unsafe key directory")
    return info


def _same(a, b):
    return (a.st_dev, a.st_ino) == (b.st_dev, b.st_ino)


def _close(fd):
    if fd is not None:
        try:
            os.close(fd)
        except OSError:
            pass


def provision(key_dir: Path, *, spec: ProvisionSpec) -> TrustAnchor:
    import secrets  # Entropy is used only by this explicit provisioning operation.
    _require(type(spec) is ProvisionSpec, "SCHEMA", "expected ProvisionSpec")
    directory_fd = parent_fd = key_fd = None
    try:
        flags = _flags()
        spelling = _locations(key_dir, str(spec.authority_root))
        parent_fd = os.open(str(key_dir.parent), os.O_RDONLY | os.O_DIRECTORY | flags)
        parent = os.fstat(parent_fd)
        _require(_same(parent, os.stat(str(key_dir.parent), follow_symlinks=False)),
                 detail="key parent changed")
        if not os.path.lexists(spelling):
            os.mkdir(key_dir.name, 0o700, dir_fd=parent_fd)
        directory_fd = os.open(key_dir.name, os.O_RDONLY | os.O_DIRECTORY | flags, dir_fd=parent_fd)
        directory = _directory(directory_fd)
        _require(_same(directory, os.stat(key_dir.name, dir_fd=parent_fd, follow_symlinks=False)),
                 detail="key directory changed")
        # O_EXCL retains a partial or completed prior key without replacing it.
        key_fd = os.open(_KEY_NAME, os.O_WRONLY | os.O_CREAT | os.O_EXCL | flags,
                         0o600, dir_fd=directory_fd)
        os.fchmod(key_fd, 0o600)
        key = secrets.token_bytes(32)
        _key_allowed(key)
        offset = 0
        while offset < 32:
            written = os.write(key_fd, key[offset:])
            _require(written > 0, detail="short key write")
            offset += written
        os.fsync(key_fd)
        os.fsync(directory_fd)
        os.fsync(parent_fd)
        key_info = os.fstat(key_fd)
        _require(stat.S_ISREG(key_info.st_mode) and stat.S_IMODE(key_info.st_mode) == 0o600
                 and key_info.st_uid == os.geteuid() and key_info.st_nlink == 1 and key_info.st_size == 32
                 and _same(key_info, os.stat(_KEY_NAME, dir_fd=directory_fd, follow_symlinks=False)),
                 detail="provisioned key entry changed")
        _require(_same(directory, os.stat(key_dir.name, dir_fd=parent_fd, follow_symlinks=False)),
                 detail="key directory changed")
        return TrustAnchor(spec.world_id, str(spec.authority_root), spec.domain_version,
                           spec.trust_algorithm, _anchor(key, spec.world_id, str(spec.authority_root)))
    except (OSError, ContractError) as exc:
        if isinstance(exc, ContractError) and exc.code in ("ROOT_MISMATCH", "SCHEMA", "PROFILE"):
            raise
        raise ContractError("NOT_READY", "key provisioning incomplete; retained without overwrite") from exc
    finally:
        _close(key_fd); _close(directory_fd); _close(parent_fd)


def _read_key(key_dir, context):
    directory_fd = key_fd = None
    try:
        flags = _flags()
        spelling = _locations(key_dir, context.authority_root)
        directory_fd = os.open(spelling, os.O_RDONLY | os.O_DIRECTORY | flags)
        directory = _directory(directory_fd)
        _require(_same(directory, os.stat(spelling, follow_symlinks=False)), detail="key directory changed")
        key_fd = os.open(_KEY_NAME, os.O_RDONLY | flags | os.O_NONBLOCK, dir_fd=directory_fd)
        before = os.fstat(key_fd)
        _require(stat.S_ISREG(before.st_mode) and stat.S_IMODE(before.st_mode) == 0o600
                 and before.st_uid == os.geteuid() and before.st_nlink == 1 and before.st_size == 32,
                 detail="unsafe key file")
        key = b""
        while len(key) < 33:
            chunk = os.read(key_fd, 33 - len(key))
            if not chunk:
                break
            key += chunk
        after = os.fstat(key_fd)
        _require(_same(before, after) and before.st_size == after.st_size
                 and before.st_mtime_ns == after.st_mtime_ns and before.st_ctime_ns == after.st_ctime_ns,
                 detail="key file changed")
        _require(_same(after, os.stat(_KEY_NAME, dir_fd=directory_fd, follow_symlinks=False))
                 and _same(directory, os.stat(spelling, follow_symlinks=False)), detail="key entry changed")
        _directory(directory_fd)
        _key_allowed(key)
        _require(hmac.compare_digest(_anchor(key, context.world_id, context.authority_root), context.trust_anchor),
                 detail="key does not match frozen anchor")
        return key
    except OSError as exc:
        raise ContractError("AUTHORIZATION", "local key unavailable") from exc
    finally:
        _close(key_fd); _close(directory_fd)


def _record(record, context, kind):
    canonical(record)
    _require(type(record) is dict and set(record) == {"domain", "version", "world_id", "kind", "id", "body", "refs"}, "SCHEMA")
    _require(record["domain"] == DOMAIN and record["version"] == "0.2", "DOMAIN")
    _require(record["world_id"] == context.world_id, "WORLD")
    _require(record["kind"] == kind and type(record["body"]) is dict and type(record["refs"]) is dict, "SCHEMA")
    _id(record["id"])
    for value in record["refs"].values():
        _hash(value)


def _receipt(record, context, kind, *, signed):
    _record(record, context, kind)
    _require(kind in ("approval", "admission"), "SCHEMA")
    number = "expires_revision" if kind == "approval" else "evaluated_revision"
    fields = {"principal", "receipt_id", number} | ({"auth_tag"} if signed else set())
    refs = {"proposal", "intent"} if kind == "approval" else {"command", "candidate"}
    _require(set(record["body"]) == fields and set(record["refs"]) == refs, "SCHEMA")
    _id(record["body"]["principal"]); _id(record["body"]["receipt_id"])
    value = record["body"][number]
    _require(type(value) is int and 0 <= value <= MAX_INTEGER, "INTEGER")
    if signed:
        _hash(record["body"]["auth_tag"])
    _require(len(canonical(record)) <= 2048, "LIMIT")


def _receipt_mac(key, anchor, unsigned):
    message = (_RECEIPT_PREFIX + anchor.encode("ascii") + b"\x00"
               + unsigned["kind"].encode("ascii") + b"\x00" + canonical(unsigned))
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def _uint(value):
    _require(type(value) is int and 0 <= value <= MAX_INTEGER, "INTEGER")


def _intent_shape(intent):
    body = intent["body"]
    _require(set(body) == {"action", "budget", "case_id", "command_id", "expected_revision",
                           "principal", "random_cursor", "tick_delta"}
             and set(intent["refs"]) == {"config", "binding"}, "SCHEMA")
    _id(body["principal"]); _id(body["command_id"])
    for name in ("budget", "expected_revision", "random_cursor", "tick_delta"):
        _uint(body[name])
    _require(body["action"] in ("retain_snapshot", "physics_step")
             and body["case_id"] in (None, "weak", "strong") and body["tick_delta"] in (0, 1), "SCHEMA")


def _candidate_shape(candidate):
    body = candidate["body"]
    _require(set(body) == {"adapter_kind", "influence_mm", "physics_profile", "revision", "tick"}
             and set(candidate["refs"]) == {"command", "prior_state", "snapshot"}, "SCHEMA")
    _uint(body["revision"]); _uint(body["tick"])
    _require(body["adapter_kind"] in ("genesis", "checkpoint_reuse")
             and body["physics_profile"] == "genesis-rigid-support.v0.1", "PROFILE")
    value = body["influence_mm"]
    _require(value is None or type(value) is int and abs(value) <= 1000, "PHYSICS_INVALID")


class _ReadVerifier:
    __slots__ = ("__key", "_context")

    def __init__(self, key, context, token):
        _require(token is _TOKEN)
        object.__setattr__(self, "_ReadVerifier__key", key)
        object.__setattr__(self, "_context", context)

    def __setattr__(self, name, value):
        raise AttributeError("immutable trust handle")

    def __repr__(self):
        return "<local-hmac-sha256.v0.2 read-only verifier>"

    def assert_context(self, context: DeploymentContext) -> None:
        _require(type(context) is DeploymentContext)
        _require(context.authority_root == self._context.authority_root, "ROOT_MISMATCH")
        _require(context == self._context, detail="deployment context changed")

    def __call__(self, receipt: Record) -> None:
        kind = receipt.get("kind") if type(receipt) is dict else None
        _receipt(receipt, self._context, kind, signed=True)
        unsigned = deepcopy(receipt)
        tag = unsigned["body"].pop("auth_tag")
        _require(hmac.compare_digest(_receipt_mac(self.__key, self._context.trust_anchor, unsigned), tag),
                 detail="receipt MAC mismatch")


class LocalTrust(_ReadVerifier):
    __slots__ = ("__session",)

    def __init__(self, key, context, session, token):
        super().__init__(key, context, token)
        _require(type(session) is OwnerSession)
        object.__setattr__(self, "_LocalTrust__session", session)

    def __repr__(self):
        return "<local-hmac-sha256.v0.2 coordinator signer>"

    def authorize_read(self, principal: str, world_id: str) -> None:
        _id(principal); _id(world_id)
        _require(principal == self.__session.principal and world_id == self._context.world_id)

    def _sign(self, unsigned, kind):
        _receipt(unsigned, self._context, kind, signed=False)
        self.authorize_read(unsigned["body"]["principal"], unsigned["world_id"])
        result = deepcopy(unsigned)
        result["body"]["auth_tag"] = _receipt_mac(self._ReadVerifier__key, self._context.trust_anchor, result)
        return result

    def sign_approval(self, unsigned: Record) -> Record:
        return self._sign(unsigned, "approval")

    def sign_admission(self, unsigned: Record) -> Record:
        return self._sign(unsigned, "admission")

    def verify_approval(self, approval: Record, proposal: Record, intent: Record) -> None:
        self(approval)
        _record(proposal, self._context, "proposal")
        _record(intent, self._context, "intent")
        _require(set(proposal["body"]) == {"principal", "output"} and not proposal["refs"], "SCHEMA")
        _require(type(proposal["body"]["output"]) is str and len(proposal["body"]["output"]) <= 1024, "SCHEMA")
        _id(proposal["body"]["principal"])
        _intent_shape(intent)
        self.authorize_read(intent["body"]["principal"], intent["world_id"])
        _require(approval["body"]["principal"] == proposal["body"]["principal"] == intent["body"]["principal"])
        _require(intent["body"]["action"] in self.__session.allowed_actions)
        _require(approval["refs"] == {"proposal": digest(proposal), "intent": digest(intent)})

    def admit(self, command: Record, candidate: Record, *, current_revision: int,
              admission_id: str) -> Record:
        _record(command, self._context, "command")
        _record(candidate, self._context, "candidate")
        _require(command["body"] == {} and set(command["refs"]) == {"proposal", "intent", "approval"}, "SCHEMA")
        _candidate_shape(candidate)
        adapter = candidate["body"]["adapter_kind"]
        _require(adapter in ("genesis", "checkpoint_reuse"), "PROFILE")
        action = "physics_step" if adapter == "genesis" else "retain_snapshot"
        _require(action in self.__session.allowed_actions)
        _require(candidate["refs"]["command"] == digest(command), "REFERENCE")
        _require(type(current_revision) is int and 0 <= current_revision <= MAX_INTEGER, "INTEGER")
        _id(admission_id)
        unsigned = {"domain": DOMAIN, "version": "0.2", "world_id": self._context.world_id,
                    "kind": "admission", "id": admission_id,
                    "body": {"principal": self.__session.principal, "receipt_id": admission_id,
                             "evaluated_revision": current_revision},
                    "refs": {"command": digest(command), "candidate": digest(candidate)}}
        return self.sign_admission(unsigned)


def open_trust(key_dir: Path, *, context: DeploymentContext, signing: bool = False,
               session: OwnerSession | None = None) -> ReceiptVerifier | LocalTrust:
    _require(type(context) is DeploymentContext)
    _require(type(signing) is bool and (not signing or type(session) is OwnerSession))
    key = _read_key(key_dir, context)
    return LocalTrust(key, context, session, _TOKEN) if signing else _ReadVerifier(key, context, _TOKEN)
