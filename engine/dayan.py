"""
Dayan yarrow-stalk casting for Edge World.

The implementation models the Great Expansion process as deterministic,
seeded functions:

- one change: split active stalks, hang one, count both sides by four,
  collect the two remainders;
- three changes: produce one line value, 6/7/8/9;
- six lines: produce a primary hexagram and its changed hexagram.
"""

from __future__ import annotations

import functools
import hashlib
from dataclasses import dataclass
from typing import List, Tuple

try:
    import numpy as np
except ImportError:  # pragma: no cover - exercised in environments without numpy
    np = None

from mathEdge import Hexagram

TAIYIN = 0
SHAOYANG = 1
SHAOYIN = 2
TAIYANG = 3

PHASE_CODE_NAMES = {
    TAIYIN: "太阴",
    SHAOYANG: "少阳",
    SHAOYIN: "少阴",
    TAIYANG: "太阳",
}

LINE_VALUE_TO_PHASE_CODE = {
    6: TAIYIN,
    7: SHAOYANG,
    8: SHAOYIN,
    9: TAIYANG,
}

PHASE_CODE_TO_LINE_VALUE = {
    TAIYIN: 6,
    SHAOYANG: 7,
    SHAOYIN: 8,
    TAIYANG: 9,
}


def line_value_to_phase_code(line_value: int) -> int:
    try:
        return LINE_VALUE_TO_PHASE_CODE[line_value]
    except KeyError as exc:
        raise ValueError("line_value must be one of 6, 7, 8, or 9.") from exc


def phase_code_to_line_value(phase_code: int) -> int:
    try:
        return PHASE_CODE_TO_LINE_VALUE[phase_code]
    except KeyError as exc:
        raise ValueError("phase_code must be one of 0, 1, 2, or 3.") from exc


@dataclass(frozen=True)
class CastContext:
    seed: int
    subject: str = ""


@dataclass(frozen=True)
class ChangeCast:
    starting_count: int
    left_count: int
    right_count: int
    human_token: int
    left_remainder: int
    right_remainder: int
    removed_count: int
    remaining_count: int

    @property
    def leap_entropy(self) -> float:
        return self.removed_count / self.starting_count


@dataclass(frozen=True)
class LineCast:
    value: int
    changes: Tuple[ChangeCast, ChangeCast, ChangeCast]

    @property
    def remaining_count(self) -> int:
        return self.changes[-1].remaining_count

    @property
    def is_yang(self) -> bool:
        return self.value in (7, 9)

    @property
    def is_changing(self) -> bool:
        return self.value in (6, 9)

    @property
    def bit(self) -> int:
        return 1 if self.is_yang else 0

    @property
    def changed_bit(self) -> int:
        return 1 - self.bit if self.is_changing else self.bit


@dataclass(frozen=True)
class BatchHexagramCast:
    primary_values: Tuple[int, ...]
    changed_values: Tuple[int, ...]
    line_values: Tuple[Tuple[int, int, int, int, int, int], ...]
    changing_positions: Tuple[Tuple[int, ...], ...]


@dataclass(frozen=True)
class FastHexagramCast:
    primary_value: int
    changed_value: int
    line_values: Tuple[int, int, int, int, int, int]
    changing_positions: Tuple[int, ...]


@dataclass(frozen=True)
class HexagramCast:
    primary: Hexagram
    changed: Hexagram
    lines: Tuple[LineCast, LineCast, LineCast, LineCast, LineCast, LineCast]

    @property
    def changing_positions(self) -> List[int]:
        return [index + 1 for index, line in enumerate(self.lines) if line.is_changing]


_MASK_64 = (1 << 64) - 1


@functools.lru_cache(maxsize=8192)
def _context_seed(seed: int, subject: str) -> int:
    key = f"{seed}:{subject}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(key, digest_size=8).digest(), "big")


def _mix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & _MASK_64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & _MASK_64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & _MASK_64
    return (value ^ (value >> 31)) & _MASK_64


def _mix64_numpy(values):
    values = (values + np.uint64(0x9E3779B97F4A7C15)).astype(np.uint64)
    values = ((values ^ (values >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)).astype(np.uint64)
    values = ((values ^ (values >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)).astype(np.uint64)
    return (values ^ (values >> np.uint64(31))).astype(np.uint64)


def _split_count(active_count: int, context: CastContext, line_index: int, change_index: int) -> int:
    if active_count < 2:
        raise ValueError("active_count must leave room for a non-empty split.")
    base = _context_seed(context.seed, context.subject)
    random_value = _mix64(base ^ (line_index << 16) ^ (change_index << 8) ^ active_count)
    return 1 + (random_value % (active_count - 1))


def _remainder_by_four(count: int) -> int:
    remainder = count % 4
    return 4 if remainder == 0 else remainder


def _change_counts(active_count: int, context: CastContext, line_index: int, change_index: int) -> Tuple[int, int, int, int, int, int]:
    left_count = _split_count(active_count, context, line_index, change_index)
    right_count = active_count - left_count
    if right_count == 0:
        left_count -= 1
        right_count = 1
    right_after_hang = right_count - 1
    left_remainder = _remainder_by_four(left_count)
    right_remainder = _remainder_by_four(right_after_hang)
    removed_count = 1 + left_remainder + right_remainder
    remaining_count = active_count - removed_count
    return left_count, right_count, left_remainder, right_remainder, removed_count, remaining_count


def cast_change(
    active_count: int,
    context: CastContext,
    change_index: int,
    line_index: int = 0,
) -> ChangeCast:
    if active_count <= 1:
        raise ValueError("active_count must be greater than one.")
    if change_index < 0:
        raise ValueError("change_index must be non-negative.")
    if line_index < 0:
        raise ValueError("line_index must be non-negative.")

    left_count, right_count, left_remainder, right_remainder, removed_count, remaining_count = _change_counts(
        active_count,
        context,
        line_index,
        change_index,
    )

    return ChangeCast(
        starting_count=active_count,
        left_count=left_count,
        right_count=right_count,
        human_token=1,
        left_remainder=left_remainder,
        right_remainder=right_remainder,
        removed_count=removed_count,
        remaining_count=remaining_count,
    )


def cast_line_value_fast(context: CastContext, line_index: int) -> int:
    active_count = 49
    for change_index in range(3):
        active_count = _change_counts(active_count, context, line_index, change_index)[5]
    value = active_count // 4
    if value not in (6, 7, 8, 9):
        raise RuntimeError(f"Invalid yarrow line value: {value}")
    return value


def cast_line(context: CastContext, line_index: int) -> LineCast:
    active_count = 49
    changes = []
    for change_index in range(3):
        change = cast_change(active_count, context, change_index, line_index=line_index)
        changes.append(change)
        active_count = change.remaining_count
    value = active_count // 4
    if value not in (6, 7, 8, 9):
        raise RuntimeError(f"Invalid yarrow line value: {value}")
    return LineCast(value=value, changes=tuple(changes))


def line_stalk_count(line_value: int) -> int:
    if line_value not in (6, 7, 8, 9):
        raise ValueError("line_value must be one of 6, 7, 8, or 9.")
    return line_value * 4


def hexagram_stalk_total(line_values: List[int]) -> int:
    if len(line_values) != 6:
        raise ValueError("A hexagram must contain exactly six line values.")
    return sum(line_stalk_count(value) for value in line_values)


def line_values_to_primary_value(line_values: Tuple[int, ...]) -> int:
    if len(line_values) != 6:
        raise ValueError("A hexagram must contain exactly six line values.")
    value = 0
    for index, line_value in enumerate(line_values):
        phase_code = line_value_to_phase_code(line_value)
        bit = 1 if phase_code in (SHAOYANG, TAIYANG) else 0
        value |= bit << index
    return value


def line_values_to_changed_value(line_values: Tuple[int, ...]) -> int:
    if len(line_values) != 6:
        raise ValueError("A hexagram must contain exactly six line values.")
    value = 0
    for index, line_value in enumerate(line_values):
        phase_code = line_value_to_phase_code(line_value)
        bit = 1 if phase_code in (TAIYIN, SHAOYANG) else 0
        value |= bit << index
    return value


def cast_hexagram_batch_numpy(seed: int, subject: str, count: int = 256) -> BatchHexagramCast:
    if np is None:
        raise RuntimeError("NumPy is required for cast_hexagram_batch_numpy().")
    if count < 0:
        raise ValueError("count must be non-negative.")
    if count == 0:
        return BatchHexagramCast((), (), (), ())

    bases = np.empty(count, dtype=np.uint64)
    for index, item_seed in enumerate(range(seed, seed + count)):
        bases[index] = _context_seed(item_seed, subject)

    line_values_matrix = np.empty((count, 6), dtype=np.uint8)
    primary_values = np.zeros(count, dtype=np.uint8)
    changed_values = np.zeros(count, dtype=np.uint8)

    for line_index in range(6):
        active = np.full(count, 49, dtype=np.uint64)
        for change_index in range(3):
            random_value = _mix64_numpy(bases ^ np.uint64(line_index << 16) ^ np.uint64(change_index << 8) ^ active)
            left = np.uint64(1) + (random_value % (active - np.uint64(1)))
            right = active - left
            right_after_hang = right - np.uint64(1)
            left_remainder = left % np.uint64(4)
            left_remainder = np.where(left_remainder == 0, 4, left_remainder)
            right_remainder = right_after_hang % np.uint64(4)
            right_remainder = np.where(right_remainder == 0, 4, right_remainder)
            removed = np.uint64(1) + left_remainder + right_remainder
            active = active - removed
        values = (active // np.uint64(4)).astype(np.uint8)
        line_values_matrix[:, line_index] = values
        bits = np.where((values == 7) | (values == 9), 1, 0).astype(np.uint8)
        changed_bits = np.where((values == 6) | (values == 9), 1 - bits, bits).astype(np.uint8)
        primary_values |= bits << np.uint8(line_index)
        changed_values |= changed_bits << np.uint8(line_index)

    line_values = tuple(tuple(int(value) for value in row) for row in line_values_matrix.tolist())
    changing_positions = tuple(
        tuple(index + 1 for index, value in enumerate(row) if value in (6, 9))
        for row in line_values
    )
    return BatchHexagramCast(
        primary_values=tuple(int(value) for value in primary_values.tolist()),
        changed_values=tuple(int(value) for value in changed_values.tolist()),
        line_values=line_values,
        changing_positions=changing_positions,
    )


def cast_hexagram_batch_fast(seed: int, subject: str, count: int = 256) -> BatchHexagramCast:
    if count < 0:
        raise ValueError("count must be non-negative.")

    primary_values = []
    changed_values = []
    all_line_values = []
    all_changing_positions = []

    for offset in range(count):
        context = CastContext(seed=seed + offset, subject=subject)
        line_values = []
        primary_value = 0
        changed_value = 0
        changing_positions = []
        for line_index in range(6):
            value = cast_line_value_fast(context, line_index)
            line_values.append(value)
            bit = 1 if value in (7, 9) else 0
            changed_bit = 1 - bit if value in (6, 9) else bit
            primary_value |= bit << line_index
            changed_value |= changed_bit << line_index
            if value in (6, 9):
                changing_positions.append(line_index + 1)
        primary_values.append(primary_value)
        changed_values.append(changed_value)
        all_line_values.append(tuple(line_values))
        all_changing_positions.append(tuple(changing_positions))

    return BatchHexagramCast(
        primary_values=tuple(primary_values),
        changed_values=tuple(changed_values),
        line_values=tuple(all_line_values),
        changing_positions=tuple(all_changing_positions),
    )


def cast_hexagram_fast(context: CastContext) -> FastHexagramCast:
    line_values = tuple(cast_line_value_fast(context, line_index) for line_index in range(6))
    primary_value = line_values_to_primary_value(line_values)
    changed_value = line_values_to_changed_value(line_values)
    changing_positions = tuple(index + 1 for index, value in enumerate(line_values) if value in (6, 9))
    return FastHexagramCast(
        primary_value=primary_value,
        changed_value=changed_value,
        line_values=line_values,
        changing_positions=changing_positions,
    )


def cast_hexagram(context: CastContext) -> HexagramCast:
    lines = tuple(cast_line(context, line_index) for line_index in range(6))
    line_values = tuple(line.value for line in lines)
    primary_value = line_values_to_primary_value(line_values)
    changed_value = line_values_to_changed_value(line_values)
    return HexagramCast(
        primary=Hexagram(primary_value),
        changed=Hexagram(changed_value),
        lines=lines,
    )


if __name__ == "__main__":
    result = cast_hexagram(CastContext(seed=20260620, subject="demo"))
    print(result.primary)
    print("changing positions:", result.changing_positions)
    print(result.changed)
    print("lines:", [line.value for line in result.lines])
