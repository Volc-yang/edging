"""Render deterministic Dayan casts into 3D primary/changed volumes."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple

from dayan import CastContext, cast_hexagram_fast
from mathEdge import Hexagram


@dataclass(frozen=True)
class VolumeCastItem:
    index: int
    coord: Tuple[int, int, int]
    primary_value: int
    primary_name: str
    changed_value: int
    changed_name: str
    changing_positions: Tuple[int, ...]
    line_values_bottom_to_top: Tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class CastVolume3D:
    width: int
    height: int
    depth: int
    seed: int
    subject: str
    items: Tuple[VolumeCastItem, ...]
    primary_volume: Tuple[Tuple[Tuple[int, ...], ...], ...]
    changed_volume: Tuple[Tuple[Tuple[int, ...], ...], ...]

    @property
    def count(self) -> int:
        return self.width * self.height * self.depth

    @property
    def dimension(self) -> str:
        return f"{self.depth}*{self.height}*{self.width}"


def _validate_dimensions(width: int, height: int, depth: int) -> None:
    if width <= 0:
        raise ValueError("width must be positive.")
    if height <= 0:
        raise ValueError("height must be positive.")
    if depth <= 0:
        raise ValueError("depth must be positive.")


def _voxel_subject(subject: str, x: int, y: int, z: int) -> str:
    return f"{subject}:x={x}:y={y}:z={z}"


def generate_cast_volume_3d(width: int, height: int, depth: int, seed: int, subject: str) -> CastVolume3D:
    _validate_dimensions(width, height, depth)

    items = []
    primary_layers = []
    changed_layers = []
    index = 0

    for z in range(depth):
        primary_rows = []
        changed_rows = []
        for y in range(height):
            primary_row = []
            changed_row = []
            for x in range(width):
                context = CastContext(
                    seed=seed,
                    subject=_voxel_subject(subject, x, y, z),
                )
                cast = cast_hexagram_fast(context)
                primary = Hexagram(cast.primary_value)
                changed = Hexagram(cast.changed_value)
                items.append(
                    VolumeCastItem(
                        index=index,
                        coord=(z, y, x),
                        primary_value=cast.primary_value,
                        primary_name=primary.name or f"Hex {cast.primary_value:02d}",
                        changed_value=cast.changed_value,
                        changed_name=changed.name or f"Hex {cast.changed_value:02d}",
                        changing_positions=tuple(cast.changing_positions),
                        line_values_bottom_to_top=tuple(cast.line_values),
                    )
                )
                primary_row.append(cast.primary_value)
                changed_row.append(cast.changed_value)
                index += 1
            primary_rows.append(tuple(primary_row))
            changed_rows.append(tuple(changed_row))
        primary_layers.append(tuple(primary_rows))
        changed_layers.append(tuple(changed_rows))

    return CastVolume3D(
        width=width,
        height=height,
        depth=depth,
        seed=seed,
        subject=subject,
        items=tuple(items),
        primary_volume=tuple(primary_layers),
        changed_volume=tuple(changed_layers),
    )


def volume_to_preview_payload(volume: CastVolume3D) -> dict[str, Any]:
    return {
        "seed": volume.seed,
        "subject": volume.subject,
        "dimension": volume.dimension,
        "count": volume.count,
        "layout": "3d",
        "width": volume.width,
        "height": volume.height,
        "depth": volume.depth,
        "primary_volume": volume.primary_volume,
        "changed_volume": volume.changed_volume,
        "items": [
            {
                "index": item.index,
                "coord": list(item.coord),
                "primary_value": item.primary_value,
                "primary_name": item.primary_name,
                "changed_value": item.changed_value,
                "changed_name": item.changed_name,
                "changing_positions": list(item.changing_positions),
                "line_values_bottom_to_top": list(item.line_values_bottom_to_top),
            }
            for item in volume.items
        ],
    }


def save_cast_volume_preview_json(volume: CastVolume3D, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(volume_to_preview_payload(volume), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def save_cast_volume_matrix_json(
    matrix: Tuple[Tuple[Tuple[int, ...], ...], ...],
    *,
    seed: int,
    subject: str,
    kind: str,
    width: int,
    height: int,
    depth: int,
    path: Path,
) -> Path:
    payload = {
        "seed": seed,
        "subject": subject,
        "kind": kind,
        "dimension": f"{depth}*{height}*{width}",
        "width": width,
        "height": height,
        "depth": depth,
        "volume": matrix,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_cast_volume_3d_outputs(
    volume: CastVolume3D,
    *,
    preview_path: Path,
    primary_path: Path,
    changed_path: Path,
) -> Tuple[Path, Path, Path]:
    preview_output = save_cast_volume_preview_json(volume, preview_path)
    primary_output = save_cast_volume_matrix_json(
        volume.primary_volume,
        seed=volume.seed,
        subject=volume.subject,
        kind="primary",
        width=volume.width,
        height=volume.height,
        depth=volume.depth,
        path=primary_path,
    )
    changed_output = save_cast_volume_matrix_json(
        volume.changed_volume,
        seed=volume.seed,
        subject=volume.subject,
        kind="changed",
        width=volume.width,
        height=volume.height,
        depth=volume.depth,
        path=changed_path,
    )
    return preview_output, primary_output, changed_output
