from __future__ import annotations

import argparse
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_visualization import export_cast_visual_bundle, load_cast_model, summarize_change_counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render debug visuals for a batch Dayan cast JSON model.")
    parser.add_argument("input", type=Path, help="Path to the cast JSON file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional output directory. Defaults to the JSON file directory.",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    model = load_cast_model(args.input)
    outputs = export_cast_visual_bundle(args.input, output_dir=args.output_dir)
    change_summary = summarize_change_counts(model.items)

    print(f"Rendered atlas: {outputs['atlas']}")
    print(f"Rendered heatmap: {outputs['changes']}")
    print(f"Items: {model.count}")
    print("Changing-line counts:")
    for change_count in range(7):
        print(f"  {change_count}: {change_summary[change_count]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
