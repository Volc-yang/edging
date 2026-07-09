from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageColor, ImageDraw, ImageFont

ENGINE_DIR = Path(__file__).resolve().parents[1] / "engine"
sys.path.insert(0, str(ENGINE_DIR))

from cast_visualization import (
    CastItem,
    CastModel,
    render_cast_debug_atlas,
    render_change_count_heatmap,
)
from dayan import cast_hexagram_batch_fast
from hexagram_image_codec import encode_hexagram_png
from mathEdge import Hexagram


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Render a four-phase four-dimensional cast as one composite image.")
    parser.add_argument("--seed", type=int, default=20260620, help="Deterministic seed for the batch cast.")
    parser.add_argument("--subject", type=str, default="four-phase-4d-unit", help="Deterministic subject string.")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("models/four_phase_4d_unit.png"),
        help="Output PNG path.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=Path("models/four_phase_4d_unit.json"),
        help="Optional JSON output for the generated batch.",
    )
    parser.add_argument(
        "--primary-grid-output",
        type=Path,
        default=Path("models/four_phase_4d_unit_primary_8x8.png"),
        help="Output PNG path for the primary hexagram 8x8 grid.",
    )
    parser.add_argument(
        "--changed-grid-output",
        type=Path,
        default=Path("models/four_phase_4d_unit_changed_8x8.png"),
        help="Output PNG path for the changed hexagram 8x8 grid.",
    )
    return parser


def index_to_coord(index: int, dims: int = 4) -> tuple[int, ...]:
    coords = [0] * dims
    value = index
    for position in range(dims - 1, -1, -1):
        coords[position] = value % 4
        value //= 4
    return tuple(coords)


def batch_to_model(seed: int, subject: str, batch) -> CastModel:
    items = []
    for index, (primary_value, changed_value, line_values, changing_positions) in enumerate(
        zip(batch.primary_values, batch.changed_values, batch.line_values, batch.changing_positions)
    ):
        primary = Hexagram(primary_value)
        changed = Hexagram(changed_value)
        items.append(
            CastItem(
                index=index,
                coord=index_to_coord(index),
                primary_value=primary_value,
                primary_name=primary.name or f"Hex {primary_value:02d}",
                changed_value=changed_value,
                changed_name=changed.name or f"Hex {changed_value:02d}",
                changing_positions=tuple(changing_positions),
                line_values_bottom_to_top=tuple(line_values),
            )
        )
    return CastModel(
        seed=seed,
        subject=subject,
        dimension="4*4*4*4",
        count=len(items),
        items=tuple(items),
    )


def load_font(size: int) -> ImageFont.ImageFont:
    for font_name in (
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Apple Symbols.ttf",
    ):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def compose_poster(model: CastModel):
    atlas = render_cast_debug_atlas(model)
    heatmap = render_change_count_heatmap(model)

    gap = 36
    margin = 48
    header_height = 74
    footer_height = 56
    width = max(atlas.width, heatmap.width) + margin * 2
    height = header_height + atlas.height + gap + heatmap.height + footer_height + margin * 2
    poster = Image.new("RGB", (width, height), ImageColor.getrgb("#f2efe8"))
    draw = ImageDraw.Draw(poster)
    title_font = load_font(28)
    meta_font = load_font(14)

    title = "Four-Phase Four-Dimensional Cast"
    draw.text((margin, 22), title, fill=ImageColor.getrgb("#1e1d1b"), font=title_font)
    draw.text(
        (margin, 54),
        f"seed={model.seed}  subject={model.subject}  samples={model.count}",
        fill=ImageColor.getrgb("#7e7568"),
        font=meta_font,
    )

    atlas_x = margin
    atlas_y = header_height + margin
    heatmap_x = margin
    heatmap_y = atlas_y + atlas.height + gap
    poster.paste(atlas, (atlas_x, atlas_y))
    poster.paste(heatmap, (heatmap_x, heatmap_y))

    footer = "Generated from a deterministic 4x4x4x4 batch cast."
    draw.text((margin, heatmap_y + heatmap.height + 18), footer, fill=ImageColor.getrgb("#7e7568"), font=meta_font)

    return poster


def main() -> int:
    args = build_parser().parse_args()
    batch = cast_hexagram_batch_fast(seed=args.seed, subject=args.subject, count=256)
    model = batch_to_model(args.seed, args.subject, batch)

    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.primary_grid_output.parent.mkdir(parents=True, exist_ok=True)
    args.changed_grid_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        __import__("json").dumps(
            {
                "seed": model.seed,
                "subject": model.subject,
                "dimension": model.dimension,
                "count": model.count,
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
                    for item in model.items
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    poster = compose_poster(model)
    poster.save(args.output, format="PNG", optimize=True)
    encode_hexagram_png(batch.primary_values, args.primary_grid_output, width=8)
    encode_hexagram_png(batch.changed_values, args.changed_grid_output, width=8)

    first = model.items[0]
    print(f"Rendered four-phase 4d image: {args.output}")
    print(f"Saved batch JSON: {args.json_output}")
    print(f"Saved primary 8x8 grid: {args.primary_grid_output}")
    print(f"Saved changed 8x8 grid: {args.changed_grid_output}")
    print(f"First item: {first.primary_name} -> {first.changed_name}, changing={list(first.changing_positions)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
