"""Strict, side-effect-free values and bytes for the neutral authority profile."""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from typing import TypeAlias, Union

JSON: TypeAlias = Union[None, bool, int, str, list["JSON"], dict[str, "JSON"]]
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
    if type(record) is not dict or record.get("domain") != DOMAIN or record.get("version") != VERSION:
        raise ContractError("DOMAIN", "unsupported record domain/version")
    return hashlib.sha256(_PREFIX + canonical(record)).hexdigest()
