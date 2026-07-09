"""Visualization helpers for batch Dayan cast results.

The current batch sample stores 256 cast points in JSON. This module turns that
payload into two debug-friendly images:

- an atlas that shows primary and changed hexagram structure per sample;
- a change-count heatmap for quickly spotting volatile regions.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

from PIL import Image, ImageColor, ImageDraw, ImageFont

from mathEdge import Hexagram


Color = Tuple[int, int, int]

TRIGRAM_COLORS: Dict[int, Color] = {
    0b000: (125, 107, 82),   # kun / earth
    0b001: (101, 123, 91),   # gen / mountain
    0b010: (65, 111, 156),   # kan / water
    0b011: (96, 145, 116),   # xun / wind
    0b100: (187, 112, 70),   # zhen / thunder
    0b101: (196, 92, 64),    # li / fire
    0b110: (73, 138, 150),   # dui / lake
    0b111: (145, 128, 88),   # qian / heaven
}

BACKGROUND = ImageColor.getrgb("#f2efe8")
PANEL_BG = ImageColor.getrgb("#fbfaf7")
TEXT = ImageColor.getrgb("#1e1d1b")
MUTED = ImageColor.getrgb("#7e7568")
HIGHLIGHT = ImageColor.getrgb("#c4832f")
GRID_LINE = ImageColor.getrgb("#d8d0c3")


@dataclass(frozen=True)
class CastItem:
    index: int
    coord: Tuple[int, ...]
    primary_value: int
    primary_name: str
    changed_value: int
    changed_name: str
    changing_positions: Tuple[int, ...]
    line_values_bottom_to_top: Tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class CastModel:
    seed: int
    subject: str
    dimension: str
    count: int
    items: Tuple[CastItem, ...]


def _load_font(size: int) -> ImageFont.ImageFont:
    for font_name in (
        "/System/Library/Fonts/Supplemental/Songti.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Apple Symbols.ttf",
        "/System/Library/Fonts/Symbol.ttf",
        "Menlo.ttc",
    ):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _load_symbol_font(size: int) -> ImageFont.ImageFont:
    for font_name in (
        "/System/Library/Fonts/Apple Symbols.ttf",
        "/System/Library/Fonts/CJKSymbolsFallback.ttc",
        "/System/Library/Fonts/Symbol.ttf",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ):
        try:
            return ImageFont.truetype(font_name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _parse_item(raw: Dict) -> CastItem:
    line_values = tuple(int(value) for value in raw["line_values_bottom_to_top"])
    if len(line_values) != 6:
        raise ValueError("Each cast item must contain six line values.")
    return CastItem(
        index=int(raw["index"]),
        coord=tuple(int(value) for value in raw["coord"]),
        primary_value=int(raw["primary_value"]),
        primary_name=str(raw["primary_name"]),
        changed_value=int(raw["changed_value"]),
        changed_name=str(raw["changed_name"]),
        changing_positions=tuple(int(value) for value in raw["changing_positions"]),
        line_values_bottom_to_top=line_values,
    )


def load_cast_model(path: Path) -> CastModel:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = tuple(_parse_item(item) for item in payload["items"])
    count = int(payload["count"])
    if count != len(items):
        raise ValueError("count does not match number of items.")
    return CastModel(
        seed=int(payload["seed"]),
        subject=str(payload["subject"]),
        dimension=str(payload["dimension"]),
        count=count,
        items=items,
    )


def grid_side(count: int) -> int:
    if count <= 0:
        raise ValueError("count must be positive.")
    side = math.isqrt(count)
    if side * side != count:
        raise ValueError("count must be a perfect square.")
    return side


def trigram_parts(hexagram_value: int) -> Tuple[int, int]:
    if not 0 <= hexagram_value <= 63:
        raise ValueError("hexagram_value must be in range 0..63.")
    return (hexagram_value >> 3) & 0b111, hexagram_value & 0b111


def _mix(a: Color, b: Color, weight: float) -> Color:
    return tuple(int(round(a[index] * (1.0 - weight) + b[index] * weight)) for index in range(3))


def change_count_color(change_count: int) -> Color:
    if not 0 <= change_count <= 6:
        raise ValueError("change_count must be in range 0..6.")
    cool = ImageColor.getrgb("#d8e6da")
    warm = ImageColor.getrgb("#b5522d")
    return _mix(cool, warm, change_count / 6.0)


def _draw_line_glyph(
    draw: ImageDraw.ImageDraw,
    x0: int,
    x1: int,
    y: int,
    line_value: int,
    highlight_change: bool,
) -> None:
    color = HIGHLIGHT if highlight_change else TEXT
    width = 3 if highlight_change else 2
    if line_value in (7, 9):
        draw.line((x0, y, x1, y), fill=color, width=width)
        return

    gap = max(6, (x1 - x0) // 4)
    mid = (x0 + x1) // 2
    draw.line((x0, y, mid - gap // 2, y), fill=color, width=width)
    draw.line((mid + gap // 2, y, x1, y), fill=color, width=width)


def render_single_cast_card(
    primary: Hexagram,
    changed: Hexagram,
    line_values: Sequence[int],
    changing_positions: Sequence[int],
    seed: int,
    subject: str,
    width: int = 1080,
    height: int = 720,
) -> Image.Image:
    if len(line_values) != 6:
        raise ValueError("line_values must contain exactly six entries.")

    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)

    title_font = _load_font(26)
    subtitle_font = _load_font(14)
    label_font = _load_font(14)
    body_font = _load_font(18)
    symbol_font = _load_symbol_font(44)
    small_font = _load_font(12)

    draw.text((40, 30), "Single Hexagram Cast", fill=TEXT, font=title_font)
    draw.text((40, 66), f"seed={seed}  subject={subject}", fill=MUTED, font=subtitle_font)

    left = (40, 110, 650, 670)
    right = (690, 110, 1040, 670)
    draw.rounded_rectangle(left, radius=24, fill=PANEL_BG, outline=GRID_LINE, width=2)
    draw.rounded_rectangle(right, radius=24, fill=PANEL_BG, outline=GRID_LINE, width=2)

    primary_symbol = primary.symbol or "?"
    changed_symbol = changed.symbol or "?"
    primary_name = primary.name or "Unknown"
    changed_name = changed.name or "Unknown"
    changing_set = {int(value) for value in changing_positions}

    draw.text((70, 136), primary_symbol, fill=TEXT, font=symbol_font)
    draw.text((130, 140), f"{primary_name}", fill=TEXT, font=body_font)
    if primary.sequence is not None:
        draw.text((130, 176), f"序号 {primary.sequence}", fill=MUTED, font=small_font)
    draw.text((70, 225), "Primary Lines", fill=MUTED, font=small_font)

    glyph_left = 110
    glyph_right = 560
    glyph_top = 280
    line_gap = 46
    for index, line_value in enumerate(reversed(tuple(int(value) for value in line_values))):
        line_number = 6 - index
        y = glyph_top + index * line_gap
        _draw_line_glyph(
            draw,
            glyph_left,
            glyph_right,
            y,
            line_value=line_value,
            highlight_change=line_number in changing_set,
        )
        draw.text((70, y - 8), str(line_number), fill=MUTED, font=small_font)

    draw.text((70, 560), "Changing positions", fill=MUTED, font=small_font)
    changing_text = "none" if not changing_set else ", ".join(str(value) for value in sorted(changing_set))
    draw.text((70, 586), changing_text, fill=TEXT, font=label_font)

    draw.text((730, 136), changed_symbol, fill=TEXT, font=symbol_font)
    draw.text((790, 145), changed_name, fill=TEXT, font=body_font)
    if changed.sequence is not None:
        draw.text((790, 181), f"序号 {changed.sequence}", fill=MUTED, font=small_font)

    changed_upper, changed_lower = trigram_parts(changed.value)
    draw.text((730, 245), "Changed Hexagram", fill=MUTED, font=small_font)
    draw.rounded_rectangle((730, 275, 1005, 430), radius=18, fill=BACKGROUND, outline=GRID_LINE, width=2)
    draw.rectangle((745, 292, 990, 342), fill=TRIGRAM_COLORS[changed_upper])
    draw.rectangle((745, 355, 990, 405), fill=TRIGRAM_COLORS[changed_lower])
    draw.text((762, 307), f"upper {changed_upper:03b}", fill=PANEL_BG, font=small_font)
    draw.text((762, 370), f"lower {changed_lower:03b}", fill=PANEL_BG, font=small_font)

    draw.text((730, 470), f"primary {primary.value:02d}", fill=TEXT, font=label_font)
    draw.text((730, 500), f"changed {changed.value:02d}", fill=TEXT, font=label_font)
    draw.text((730, 530), f"line values: {list(int(value) for value in line_values)}", fill=MUTED, font=small_font)

    footer = "Unit image generated from a single deterministic cast."
    draw.text((40, 690), footer, fill=MUTED, font=small_font)

    return image


def render_cast_debug_atlas(
    model: CastModel,
    cell_size: int = 84,
    padding: int = 16,
    gap: int = 8,
) -> Image.Image:
    side = grid_side(model.count)
    title_height = 56
    width = padding * 2 + side * cell_size + (side - 1) * gap
    height = title_height + padding * 2 + side * cell_size + (side - 1) * gap
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    title_font = _load_font(18)
    meta_font = _load_font(12)
    cell_font = _load_font(11)

    draw.text((padding, 12), "Dayan Cast Atlas", fill=TEXT, font=title_font)
    meta = f"{model.dimension}  seed={model.seed}  subject={model.subject}"
    draw.text((padding, 34), meta, fill=MUTED, font=meta_font)

    for offset, item in enumerate(model.items):
        row = offset // side
        col = offset % side
        x = padding + col * (cell_size + gap)
        y = title_height + padding + row * (cell_size + gap)
        x1 = x + cell_size
        y1 = y + cell_size

        change_count = len(item.changing_positions)
        primary_upper, primary_lower = trigram_parts(item.primary_value)
        changed_upper, changed_lower = trigram_parts(item.changed_value)

        draw.rounded_rectangle((x, y, x1, y1), radius=10, fill=PANEL_BG, outline=change_count_color(change_count), width=2)
        draw.rectangle((x + 4, y + 4, x1 - 12, y + cell_size // 2 - 1), fill=TRIGRAM_COLORS[primary_upper])
        draw.rectangle((x + 4, y + cell_size // 2, x1 - 12, y1 - 4), fill=TRIGRAM_COLORS[primary_lower])
        draw.rectangle((x1 - 10, y + 4, x1 - 4, y + cell_size // 2 - 1), fill=TRIGRAM_COLORS[changed_upper])
        draw.rectangle((x1 - 10, y + cell_size // 2, x1 - 4, y1 - 4), fill=TRIGRAM_COLORS[changed_lower])

        glyph_left = x + 16
        glyph_right = x1 - 18
        glyph_top = y + 15
        line_gap = 7
        for index, line_value in enumerate(reversed(item.line_values_bottom_to_top)):
            line_number = 6 - index
            line_y = glyph_top + index * line_gap
            _draw_line_glyph(
                draw,
                glyph_left,
                glyph_right,
                line_y,
                line_value=line_value,
                highlight_change=line_number in item.changing_positions,
            )

        draw.text((x + 8, y1 - 24), f"{item.primary_value:02d}->{item.changed_value:02d}", fill=TEXT, font=cell_font)
        draw.text((x + 8, y1 - 12), f"c{change_count} {item.index:03d}", fill=MUTED, font=cell_font)

    return image


def render_change_count_heatmap(
    model: CastModel,
    cell_size: int = 26,
    padding: int = 14,
    gap: int = 2,
) -> Image.Image:
    side = grid_side(model.count)
    title_height = 38
    width = padding * 2 + side * cell_size + (side - 1) * gap
    height = title_height + padding * 2 + side * cell_size + (side - 1) * gap
    image = Image.new("RGB", (width, height), BACKGROUND)
    draw = ImageDraw.Draw(image)
    title_font = _load_font(16)
    label_font = _load_font(11)

    draw.text((padding, 10), "Changing-Line Heatmap", fill=TEXT, font=title_font)

    for offset, item in enumerate(model.items):
        row = offset // side
        col = offset % side
        x = padding + col * (cell_size + gap)
        y = title_height + padding + row * (cell_size + gap)
        x1 = x + cell_size
        y1 = y + cell_size
        change_count = len(item.changing_positions)
        draw.rectangle((x, y, x1, y1), fill=change_count_color(change_count), outline=GRID_LINE)
        label = str(change_count)
        bbox = draw.textbbox((0, 0), label, font=label_font)
        label_x = x + (cell_size - (bbox[2] - bbox[0])) / 2
        label_y = y + (cell_size - (bbox[3] - bbox[1])) / 2 - 1
        draw.text((label_x, label_y), label, fill=TEXT, font=label_font)

    return image


def export_cast_visual_bundle(
    json_path: Path,
    output_dir: Path | None = None,
) -> Dict[str, Path]:
    model = load_cast_model(json_path)
    out_dir = output_dir or json_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = json_path.stem
    atlas_path = out_dir / f"{stem}_atlas.png"
    heatmap_path = out_dir / f"{stem}_changes.png"

    render_cast_debug_atlas(model).save(atlas_path, format="PNG", optimize=True)
    render_change_count_heatmap(model).save(heatmap_path, format="PNG", optimize=True)

    return {
        "atlas": atlas_path,
        "changes": heatmap_path,
    }


def summarize_change_counts(items: Sequence[CastItem]) -> Dict[int, int]:
    counts = {change_count: 0 for change_count in range(7)}
    for item in items:
        counts[len(item.changing_positions)] += 1
    return counts
