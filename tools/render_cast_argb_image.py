from __future__ import annotations

import argparse
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_argb_image import generate_cast_argb_image, save_cast_argb_image_pair


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render deterministic Dayan casts into primary/changed ARGB PNGs.")
    parser.add_argument("--seed", type=int, default=20260627, help="Deterministic seed for the cast image.")
    parser.add_argument("--subject", type=str, default="cast-argb-image", help="Deterministic subject string.")
    parser.add_argument("--width", type=int, default=64, help="Image width in pixels.")
    parser.add_argument("--height", type=int, default=64, help="Image height in pixels.")
    parser.add_argument(
        "--primary-output",
        type=Path,
        default=Path("models/cast_argb_primary.png"),
        help="Output PNG path for the primary hexagram image.",
    )
    parser.add_argument(
        "--changed-output",
        type=Path,
        default=Path("models/cast_argb_changed.png"),
        help="Output PNG path for the changed hexagram image.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    image = generate_cast_argb_image(
        width=args.width,
        height=args.height,
        seed=args.seed,
        subject=args.subject,
    )
    save_cast_argb_image_pair(
        image,
        primary_path=args.primary_output,
        changed_path=args.changed_output,
    )

    print(f"Rendered primary ARGB image: {args.primary_output}")
    print(f"Rendered changed ARGB image: {args.changed_output}")
    print(f"Pixels: {args.width}x{args.height} ({args.width * args.height} samples, 4 casts per pixel)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
