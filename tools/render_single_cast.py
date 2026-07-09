from __future__ import annotations

import argparse
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_visualization import render_single_cast_card
from dayan import CastContext, cast_hexagram


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a single Dayan cast as one image.")
    parser.add_argument("--seed", type=int, default=20260620, help="Deterministic cast seed.")
    parser.add_argument("--subject", type=str, default="single-card", help="Deterministic cast subject.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/single_cast_unit.png"),
        help="Output PNG path.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = cast_hexagram(CastContext(seed=args.seed, subject=args.subject))
    image = render_single_cast_card(
        primary=result.primary,
        changed=result.changed,
        line_values=[line.value for line in result.lines],
        changing_positions=result.changing_positions,
        seed=args.seed,
        subject=args.subject,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.output, format="PNG", optimize=True)
    print(f"Rendered single cast image: {args.output}")
    print(f"Primary: {result.primary}")
    print(f"Changed: {result.changed}")
    print(f"Changing positions: {result.changing_positions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
