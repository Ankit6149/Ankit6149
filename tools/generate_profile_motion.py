"""Render seamless light and dark ASCII profile films.

The motion is designed as a normal high-contrast video first. Typography is
embedded into those source frames and the complete frame is then converted to
ASCII, keeping the words part of the same visual system.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 960, 360
SOURCE_WIDTH, SOURCE_HEIGHT = 320, 120
COLUMNS, ROWS = 96, 36
CELL_WIDTH, CELL_HEIGHT = WIDTH // COLUMNS, HEIGHT // ROWS
FPS = 8
FRAME_COUNT = 72

GITHUB_LIGHT = (246, 248, 250)
GITHUB_DARK = (13, 17, 23)
LIGHT_INK = (31, 35, 40)
DARK_INK = (240, 246, 252)
LIGHT_MUTED = (87, 96, 106)
DARK_MUTED = (139, 148, 158)


def load_font(size: int, *, mono: bool = False, bold: bool = False):
    names = []
    if mono and bold:
        names = ["DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf"]
    elif mono:
        names = ["DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"]
    elif bold:
        names = ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
    else:
        names = ["DejaVuSans.ttf", "LiberationSans-Regular.ttf"]

    roots = [
        Path("/usr/share/fonts/truetype/dejavu"),
        Path("/usr/share/fonts/truetype/liberation2"),
    ]
    for root in roots:
        for name in names:
            path = root / name
            if path.exists():
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


ASCII_FONT = load_font(CELL_HEIGHT + 1, mono=True, bold=True)
PHRASE_FONT = load_font(21, bold=True)
SMALL_FONT = load_font(10, mono=True)
FALLBACK_PALETTE = list(" .,:;irsXA253hMHGS#9B&@")


def load_asciline_palette(directory: Path) -> list[str]:
    module_path = directory / "ascii_video_player2.py"
    if not module_path.exists():
        return FALLBACK_PALETTE
    spec = importlib.util.spec_from_file_location("asciline_mapper", module_path)
    if spec is None or spec.loader is None:
        return FALLBACK_PALETTE
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    values = [str(character) for character in module.AsciiMapper()._lut]
    return values or FALLBACK_PALETTE


def smooth(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def cyclic_weights(theta: float) -> list[float]:
    centers = [0.0, math.tau / 3.0, 2.0 * math.tau / 3.0]
    raw = [((math.cos(theta - center) + 1.0) / 2.0) ** 4 for center in centers]
    total = sum(raw)
    return [value / total for value in raw]


def amoeba_field(theta: float) -> np.ndarray:
    yy, xx = np.mgrid[0:SOURCE_HEIGHT, 0:SOURCE_WIDTH]
    field = np.zeros((SOURCE_HEIGHT, SOURCE_WIDTH), dtype=np.float32)

    blobs = [
        (0.21, 0.26, 58, 37, 0.0),
        (0.63, 0.28, 73, 42, 1.7),
        (0.80, 0.72, 60, 36, 3.1),
        (0.34, 0.78, 76, 43, 4.4),
    ]
    for cx, cy, rx, ry, phase in blobs:
        moving_x = SOURCE_WIDTH * cx + math.cos(theta + phase) * 36
        moving_y = SOURCE_HEIGHT * cy + math.sin(theta * 1.15 + phase) * 20
        distance = ((xx - moving_x) / rx) ** 2 + ((yy - moving_y) / ry) ** 2
        field += np.exp(-distance * 2.1)

    ripple = 0.15 * np.sin(xx / 22.0 + theta) + 0.11 * np.cos(yy / 15.0 - theta * 1.3)
    return field + ripple


def source_frame(theta: float, theme: str) -> Image.Image:
    light_theme = theme == "light"
    background = GITHUB_LIGHT if light_theme else GITHUB_DARK
    foreground = LIGHT_INK if light_theme else DARK_INK
    muted = LIGHT_MUTED if light_theme else DARK_MUTED

    field = amoeba_field(theta)
    threshold = 0.74 + 0.24 * math.sin(theta * 0.7)
    coverage = np.clip((field - threshold + 0.24) / 0.48, 0.0, 1.0)
    coverage = coverage * coverage * (3.0 - 2.0 * coverage)

    bg = np.array(background, dtype=np.float32)
    fg = np.array(foreground, dtype=np.float32)
    if light_theme:
        shape = fg * 0.90
    else:
        shape = fg * 0.82

    pixels = bg[None, None, :] * (1.0 - coverage[..., None]) + shape[None, None, :] * coverage[..., None]
    image = Image.fromarray(np.uint8(np.clip(pixels, 0, 255)), "RGB").convert("RGBA")

    # A continuous filament connects the phases and returns to itself.
    filament = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(filament)
    points = []
    for index in range(180):
        progress = index / 179.0
        angle = progress * math.tau * 1.6 + theta
        radius = 14 + progress * 118
        x = SOURCE_WIDTH / 2 + math.cos(angle + progress * 0.8) * radius * 0.92
        y = SOURCE_HEIGHT / 2 + math.sin(angle + progress * 0.8) * radius * 0.36
        points.append((x, y))
    line_color = muted + (110,)
    draw.line(points, fill=line_color, width=1, joint="curve")
    image.alpha_composite(filament.filter(ImageFilter.GaussianBlur(3)))
    image.alpha_composite(filament)

    phrases = ["I notice patterns.", "I connect ideas.", "I shape systems."]
    weights = cyclic_weights(theta)
    phrase_index = max(range(3), key=lambda index: weights[index])
    phrase = phrases[phrase_index]
    alpha = int(155 + 100 * weights[phrase_index])

    # Establish a quiet contrast zone, then draw the words into the source video.
    # ASCILINE converts this entire frame, so these are not overlay labels.
    text_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    bbox = text_draw.textbbox((0, 0), phrase, font=PHRASE_FONT)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    text_x = (SOURCE_WIDTH - text_width) / 2
    text_y = (SOURCE_HEIGHT - text_height) / 2 - 4

    sample_x = int(SOURCE_WIDTH / 2)
    sample_y = int(SOURCE_HEIGHT / 2)
    local_shape = coverage[sample_y, sample_x] > 0.5
    if light_theme:
        text_color = background if local_shape else foreground
        halo_color = foreground if local_shape else background
    else:
        text_color = background if local_shape else foreground
        halo_color = foreground if local_shape else background

    halo = Image.new("RGBA", image.size, (0, 0, 0, 0))
    halo_draw = ImageDraw.Draw(halo)
    pad_x, pad_y = 13, 8
    halo_draw.rounded_rectangle(
        (text_x - pad_x, text_y - pad_y, text_x + text_width + pad_x, text_y + text_height + pad_y),
        radius=11,
        fill=halo_color + (82,),
    )
    image.alpha_composite(halo.filter(ImageFilter.GaussianBlur(9)))

    text_draw.text((text_x, text_y), phrase, font=PHRASE_FONT, fill=text_color + (alpha,))
    image.alpha_composite(text_layer)

    # Small cyclic marker reinforces the endless flow without adding more copy.
    marker = f"{phrase_index + 1:02d} / 03"
    marker_draw = ImageDraw.Draw(image)
    marker_draw.text((14, SOURCE_HEIGHT - 18), marker, font=SMALL_FONT, fill=muted + (170,))

    return image.convert("RGB")


def render_ascii(source: Image.Image, palette: list[str], theme: str) -> Image.Image:
    light_theme = theme == "light"
    background = GITHUB_LIGHT if light_theme else GITHUB_DARK
    default_ink = LIGHT_INK if light_theme else DARK_INK

    small = source.resize((COLUMNS, ROWS), Image.Resampling.BILINEAR)
    pixels = np.asarray(small, dtype=np.float32)
    bg = np.array(background, dtype=np.float32)
    distance = np.linalg.norm(pixels - bg[None, None, :], axis=2)

    canvas = Image.new("RGB", (WIDTH, HEIGHT), background)
    draw = ImageDraw.Draw(canvas)
    highest = len(palette) - 1

    for row in range(ROWS):
        y = row * CELL_HEIGHT - 1
        for column in range(COLUMNS):
            strength = float(distance[row, column])
            if strength < 7.0:
                continue
            palette_index = int((min(strength, 255.0) / 255.0) ** 0.62 * highest)
            palette_index = max(1, min(highest, palette_index))

            rgb = pixels[row, column]
            luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
            if light_theme:
                shade = max(24, min(110, int(luminance * 0.45)))
            else:
                shade = max(165, min(248, int(luminance + 75)))
            color = (shade, shade, shade)
            if strength > 170:
                color = default_ink

            draw.text(
                (column * CELL_WIDTH, y),
                palette[palette_index],
                font=ASCII_FONT,
                fill=color,
            )
    return canvas


def render_theme(palette: list[str], theme: str, output: Path) -> None:
    frames = []
    for frame_index in range(FRAME_COUNT):
        theta = math.tau * frame_index / FRAME_COUNT
        frames.append(render_ascii(source_frame(theta, theme), palette, theme))

    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        optimize=True,
        disposal=2,
        colors=96,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--asciline", type=Path, required=True)
    parser.add_argument("--light-output", type=Path)
    parser.add_argument("--dark-output", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    palette = load_asciline_palette(args.asciline)
    light_output = args.light_output or args.output
    if light_output is None:
        parser.error("--light-output or --output is required")
    dark_output = args.dark_output or light_output.with_name("ankit-cinematic-ascii-dark.gif")

    render_theme(palette, "light", light_output)
    render_theme(palette, "dark", dark_output)


if __name__ == "__main__":
    main()
