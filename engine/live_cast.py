"""Live hexagram casting for animated 1D/2D/3D test cases.

This module provides a small deterministic animation layer on top of the
existing `dayan` casting primitives. It treats 100 fps as a logical clock and
generates three layout styles:

- 1D: 64 hexagrams arranged on a line.
- 2D: 64 hexagrams arranged on an 8x8 grid.
- 3D: 64 hexagrams arranged on a 4x4x4 cube.

Each sample changes with frame index, so the engine can be driven continuously
without depending on wall-clock randomness.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, Sequence, Tuple

from dayan import CastContext, cast_hexagram_fast
from mathEdge import Hexagram


class LiveCastLayout(str, Enum):
    ONE_D = "1d"
    TWO_D = "2d"
    THREE_D = "3d"


@dataclass(frozen=True)
class LiveCastItem:
    index: int
    coord: Tuple[int, ...]
    primary_value: int
    primary_name: str
    changed_value: int
    changed_name: str
    changing_positions: Tuple[int, ...]
    line_values_bottom_to_top: Tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class LiveCastFrame:
    seed: int
    subject: str
    layout: LiveCastLayout
    fps: int
    frame_index: int
    count: int
    items: Tuple[LiveCastItem, ...]


def _layout_coords(layout: LiveCastLayout) -> Tuple[Tuple[int, ...], ...]:
    if layout is LiveCastLayout.ONE_D:
        return tuple((index,) for index in range(64))
    if layout is LiveCastLayout.TWO_D:
        return tuple((y, x) for y in range(8) for x in range(8))
    if layout is LiveCastLayout.THREE_D:
        return tuple((z, y, x) for z in range(4) for y in range(4) for x in range(4))
    raise ValueError(f"Unsupported live cast layout: {layout}")


def _mix_seed(seed: int, frame_index: int, coord: Sequence[int], subject: str, layout: LiveCastLayout) -> int:
    payload = f"{seed}:{frame_index}:{layout.value}:{subject}:{','.join(map(str, coord))}".encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=8).digest(), "big")


class LiveCastEngine:
    def __init__(self, seed: int, subject: str = "live-cast", fps: int = 100):
        if fps <= 0:
            raise ValueError("fps must be positive.")
        self.seed = seed
        self.subject = subject
        self.fps = fps

    def frame_index_for_elapsed(self, elapsed_seconds: float) -> int:
        if elapsed_seconds < 0:
            raise ValueError("elapsed_seconds must be non-negative.")
        return int(elapsed_seconds * self.fps)

    def frame_for_elapsed(self, elapsed_seconds: float, layout: LiveCastLayout) -> LiveCastFrame:
        return self.frame(self.frame_index_for_elapsed(elapsed_seconds), layout)

    def frame(self, frame_index: int, layout: LiveCastLayout) -> LiveCastFrame:
        if frame_index < 0:
            raise ValueError("frame_index must be non-negative.")

        items = []
        for index, coord in enumerate(_layout_coords(layout)):
            mixed_seed = _mix_seed(self.seed, frame_index, coord, self.subject, layout)
            context = CastContext(
                seed=mixed_seed,
                subject=f"{self.subject}:{layout.value}:{frame_index}:{index}",
            )
            result = cast_hexagram_fast(context)
            primary = Hexagram(result.primary_value)
            changed = Hexagram(result.changed_value)
            items.append(
                LiveCastItem(
                    index=index,
                    coord=coord,
                    primary_value=result.primary_value,
                    primary_name=primary.name or f"Hex {result.primary_value:02d}",
                    changed_value=result.changed_value,
                    changed_name=changed.name or f"Hex {result.changed_value:02d}",
                    changing_positions=tuple(result.changing_positions),
                    line_values_bottom_to_top=tuple(result.line_values),
                )
            )

        return LiveCastFrame(
            seed=self.seed,
            subject=self.subject,
            layout=layout,
            fps=self.fps,
            frame_index=frame_index,
            count=len(items),
            items=tuple(items),
        )

    def stream(self, layout: LiveCastLayout, frames: int | None = None) -> Iterable[LiveCastFrame]:
        index = 0
        while frames is None or index < frames:
            yield self.frame(index, layout)
            index += 1

