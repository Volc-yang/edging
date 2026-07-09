"""Image codecs for hexagram cast data.

Two encodings are supported:

- Compact RGB packing: four 6-bit hexagrams are tightly packed into 24 bits.
- High-aligned ARGB packing: one 6-bit hexagram is stored in each channel,
  shifted left by 2 bits so the value occupies the high bits of the byte.

For the ARGB form, the logical channel order is ``A, R, G, B``. PNG files are
stored through Pillow in ``RGBA`` byte order, so the codec swaps channels on
write and read while preserving the logical ARGB mapping.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image


def _validate_hexagram_value(value: int) -> None:
    if not 0 <= value <= 63:
        raise ValueError("hexagram values must be in range 0..63.")


def _validate_byte_value(value: int) -> None:
    if not 0 <= value <= 255:
        raise ValueError("channel values must be in range 0..255.")


def _resolve_image_size(pixel_count: int, width: int, height: int | None = None) -> Tuple[int, int]:
    if width <= 0:
        raise ValueError("image width must be positive.")
    if pixel_count <= 0:
        raise ValueError("At least four hexagrams are required.")
    if height is None:
        if pixel_count % width != 0:
            raise ValueError("Pixel count must divide evenly by image width.")
        return width, pixel_count // width
    if height <= 0:
        raise ValueError("image height must be positive.")
    if width * height != pixel_count:
        raise ValueError("Pixel count must match width * height.")
    return width, height


def pack_four_hexagrams_to_rgb(hexagrams: Tuple[int, int, int, int]) -> Tuple[int, int, int]:
    if len(hexagrams) != 4:
        raise ValueError("Exactly four hexagrams are required per RGB pixel.")
    packed = 0
    for value in hexagrams:
        _validate_hexagram_value(value)
        packed = (packed << 6) | value
    return ((packed >> 16) & 0xFF, (packed >> 8) & 0xFF, packed & 0xFF)


def unpack_rgb_to_four_hexagrams(pixel: Tuple[int, int, int]) -> Tuple[int, int, int, int]:
    if len(pixel) != 3:
        raise ValueError("RGB pixel must contain exactly three channels.")
    red, green, blue = pixel
    packed = (red << 16) | (green << 8) | blue
    return (
        (packed >> 18) & 0x3F,
        (packed >> 12) & 0x3F,
        (packed >> 6) & 0x3F,
        packed & 0x3F,
    )


def align_hexagram_to_channel(value: int) -> int:
    _validate_hexagram_value(value)
    return value << 2


def channel_to_hexagram_value(channel: int) -> int:
    _validate_byte_value(channel)
    return channel >> 2


def pack_four_hexagrams_to_argb(hexagrams: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if len(hexagrams) != 4:
        raise ValueError("Exactly four hexagrams are required per ARGB pixel.")
    return tuple(align_hexagram_to_channel(value) for value in hexagrams)


def unpack_argb_to_four_hexagrams(pixel: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if len(pixel) != 4:
        raise ValueError("ARGB pixel must contain exactly four channels.")
    return tuple(channel_to_hexagram_value(channel) for channel in pixel)


def argb_to_rgba_pixel(pixel: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if len(pixel) != 4:
        raise ValueError("ARGB pixel must contain exactly four channels.")
    alpha, red, green, blue = pixel
    return (red, green, blue, alpha)


def rgba_to_argb_pixel(pixel: Tuple[int, int, int, int]) -> Tuple[int, int, int, int]:
    if len(pixel) != 4:
        raise ValueError("RGBA pixel must contain exactly four channels.")
    red, green, blue, alpha = pixel
    return (alpha, red, green, blue)


def encode_hexagram_png(hexagrams: Iterable[int], path: Path, width: int = 8, height: int | None = None) -> Path:
    values = tuple(hexagrams)
    if len(values) % 4 != 0:
        raise ValueError("Hexagram count must be divisible by 4.")
    for value in values:
        _validate_hexagram_value(value)

    pixel_count = len(values) // 4
    width, height = _resolve_image_size(pixel_count, width, height)

    pixels = [pack_four_hexagrams_to_rgb(values[index:index + 4]) for index in range(0, len(values), 4)]
    image = Image.new("RGB", (width, height))
    image.putdata(pixels)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
    return path


def decode_hexagram_png(path: Path, count: int) -> Tuple[int, ...]:
    if count < 0:
        raise ValueError("count must be non-negative.")
    if count % 4 != 0:
        raise ValueError("count must be divisible by 4.")

    with Image.open(path) as image:
        rgb = image.convert("RGB")
        needed_pixels = count // 4
        available_pixels = rgb.width * rgb.height
        if needed_pixels > available_pixels:
            raise ValueError("Image does not contain enough pixels for requested count.")
        values = []
        for pixel in list(rgb.getdata())[:needed_pixels]:
            values.extend(unpack_rgb_to_four_hexagrams(pixel))
    return tuple(values[:count])


def encode_hexagram_argb_png(
    hexagrams: Iterable[int],
    path: Path,
    width: int,
    height: int | None = None,
) -> Path:
    values = tuple(hexagrams)
    if len(values) % 4 != 0:
        raise ValueError("Hexagram count must be divisible by 4.")
    for value in values:
        _validate_hexagram_value(value)

    pixel_count = len(values) // 4
    width, height = _resolve_image_size(pixel_count, width, height)
    pixels = [
        argb_to_rgba_pixel(pack_four_hexagrams_to_argb(values[index:index + 4]))
        for index in range(0, len(values), 4)
    ]
    image = Image.new("RGBA", (width, height))
    image.putdata(pixels)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG", optimize=True)
    return path


def decode_hexagram_argb_png(path: Path, count: int) -> Tuple[int, ...]:
    if count < 0:
        raise ValueError("count must be non-negative.")
    if count % 4 != 0:
        raise ValueError("count must be divisible by 4.")

    with Image.open(path) as image:
        rgba = image.convert("RGBA")
        needed_pixels = count // 4
        available_pixels = rgba.width * rgba.height
        if needed_pixels > available_pixels:
            raise ValueError("Image does not contain enough pixels for requested count.")
        values = []
        for pixel in list(rgba.getdata())[:needed_pixels]:
            values.extend(unpack_argb_to_four_hexagrams(rgba_to_argb_pixel(pixel)))
    return tuple(values[:count])


def encode_cast_pair_argb_pngs(
    primary_hexagrams: Iterable[int],
    changed_hexagrams: Iterable[int],
    primary_path: Path,
    changed_path: Path,
    width: int,
    height: int | None = None,
) -> Tuple[Path, Path]:
    primary_values = tuple(primary_hexagrams)
    changed_values = tuple(changed_hexagrams)
    if len(primary_values) != len(changed_values):
        raise ValueError("Primary and changed hexagram counts must match.")

    primary_output = encode_hexagram_argb_png(primary_values, primary_path, width=width, height=height)
    changed_output = encode_hexagram_argb_png(changed_values, changed_path, width=width, height=height)
    return primary_output, changed_output


if __name__ == "__main__":
    sample = tuple(range(64)) * 4
    output = encode_hexagram_png(sample, Path("models/sample_hexagram_block.png"), width=8)
    print(output)
    print(decode_hexagram_png(output, len(sample)) == sample)
