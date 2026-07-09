"""Render deterministic Dayan casts into paired ARGB PNG images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Tuple

from dayan import CastContext, cast_hexagram_fast
from hexagram_image_codec import encode_cast_pair_argb_pngs

CHANNEL_NAMES = ("A", "R", "G", "B")


@dataclass(frozen=True)
class PixelCast:
    x: int
    y: int
    channel_name: str
    primary_value: int
    changed_value: int
    line_values: Tuple[int, int, int, int, int, int]
    changing_positions: Tuple[int, ...]


@dataclass(frozen=True)
class CastArgbImage:
    width: int
    height: int
    primary_hexagrams: Tuple[int, ...]
    changed_hexagrams: Tuple[int, ...]
    samples: Tuple[PixelCast, ...]


def _validate_dimensions(width: int, height: int) -> None:
    if width <= 0:
        raise ValueError("width must be positive.")
    if height <= 0:
        raise ValueError("height must be positive.")


def _channel_subject(subject: str, x: int, y: int, channel_name: str) -> str:
    return f"{subject}:x={x}:y={y}:c={channel_name}"


def generate_cast_argb_image(width: int, height: int, seed: int, subject: str) -> CastArgbImage:
    _validate_dimensions(width, height)

    primary_hexagrams = []
    changed_hexagrams = []
    samples = []

    for y in range(height):
        for x in range(width):
            for channel_name in CHANNEL_NAMES:
                context = CastContext(
                    seed=seed,
                    subject=_channel_subject(subject, x, y, channel_name),
                )
                cast = cast_hexagram_fast(context)
                primary_hexagrams.append(cast.primary_value)
                changed_hexagrams.append(cast.changed_value)
                samples.append(
                    PixelCast(
                        x=x,
                        y=y,
                        channel_name=channel_name,
                        primary_value=cast.primary_value,
                        changed_value=cast.changed_value,
                        line_values=cast.line_values,
                        changing_positions=cast.changing_positions,
                    )
                )

    return CastArgbImage(
        width=width,
        height=height,
        primary_hexagrams=tuple(primary_hexagrams),
        changed_hexagrams=tuple(changed_hexagrams),
        samples=tuple(samples),
    )


def save_cast_argb_image_pair(
    image: CastArgbImage,
    primary_path: Path,
    changed_path: Path,
) -> Tuple[Path, Path]:
    return encode_cast_pair_argb_pngs(
        image.primary_hexagrams,
        image.changed_hexagrams,
        primary_path=primary_path,
        changed_path=changed_path,
        width=image.width,
        height=image.height,
    )
