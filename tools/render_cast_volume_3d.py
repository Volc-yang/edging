from __future__ import annotations

import argparse
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_volume_3d import generate_cast_volume_3d, save_cast_volume_3d_outputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a deterministic 3D Dayan cast volume.")
    parser.add_argument("--seed", type=int, default=20260627, help="Deterministic seed for the cast volume.")
    parser.add_argument("--subject", type=str, default="cast-volume-3d", help="Deterministic subject string.")
    parser.add_argument("--width", type=int, default=4, help="Voxel width.")
    parser.add_argument("--height", type=int, default=4, help="Voxel height.")
    parser.add_argument("--depth", type=int, default=4, help="Voxel depth.")
    parser.add_argument(
        "--preview-output",
        type=Path,
        default=Path("models/cast_volume3d_preview.json"),
        help="Preview-compatible JSON path with items plus primary/changed volumes.",
    )
    parser.add_argument(
        "--primary-output",
        type=Path,
        default=Path("models/cast_volume3d_primary.json"),
        help="Output JSON path for the primary hexagram volume matrix.",
    )
    parser.add_argument(
        "--changed-output",
        type=Path,
        default=Path("models/cast_volume3d_changed.json"),
        help="Output JSON path for the changed hexagram volume matrix.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    volume = generate_cast_volume_3d(
        width=args.width,
        height=args.height,
        depth=args.depth,
        seed=args.seed,
        subject=args.subject,
    )
    save_cast_volume_3d_outputs(
        volume,
        preview_path=args.preview_output,
        primary_path=args.primary_output,
        changed_path=args.changed_output,
    )

    print(f"Rendered 3D preview JSON: {args.preview_output}")
    print(f"Rendered primary volume JSON: {args.primary_output}")
    print(f"Rendered changed volume JSON: {args.changed_output}")
    print(f"Voxels: {args.width}x{args.height}x{args.depth} ({volume.count} casts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
