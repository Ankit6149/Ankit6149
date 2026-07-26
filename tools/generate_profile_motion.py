"""Render Ankit's minimal cinematic profile motion.

The scene is original. ASCILINE supplies the character palette used for the
final typographic frames.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH, HEIGHT = 900, 350
SOURCE_WIDTH, SOURCE_HEIGHT = 360, 140
COLUMNS, ROWS = 90, 35
CELL_WIDTH, CELL_HEIGHT = WIDTH // COLUMNS, HEIGHT // ROWS
FPS, DURATION = 8, 9
FRAME_COUNT = FPS * DURATION

BACKGROUND = (8, 8, 9)
IVORY = (244, 238, 226)
GOLD = (232, 191, 119)
TEAL = (109, 207, 191)
BLUE = (131, 157, 199)
MUTED = (137, 134, 128)


def load_font(size: int, *, bold: bool = False, mono: bool = False):
    names = (
        ["DejaVuSansMono-Bold.ttf", "LiberationMono-Bold.ttf"]
        if mono
        else ["DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"]
    )
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


ASCII_FONT = load_font(CELL_HEIGHT + 1, bold=True, mono=True)
NAME_FONT = load_font(34, bold=True)


def load_asciline_palette(directory: Path) -> list[str]:
    module_path = directory / "ascii_video_player2.py"
    spec = importlib.util.spec_from_file_location("asciline_mapper", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load ASCILINE mapper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return [str(character) for character in module.AsciiMapper()._lut]


def smooth(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def window(time: float, start: float, end: float, fade: float = 0.72) -> float:
    if time < start or time > end:
        return 0.0
    return min(smooth((time - start) / fade), smooth((end - time) / fade), 1.0)


def glow_curve(
    layer: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    alpha: int,
    width: int = 1,
    blur: int = 5,
) -> None:
    sharp = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(sharp)
    draw.line(points, fill=color + (alpha,), width=width, joint="curve")
    layer.alpha_composite(sharp.filter(ImageFilter.GaussianBlur(blur)))
    layer.alpha_composite(sharp)


random.seed(6149)
DUST = [
    (
        random.uniform(0, SOURCE_WIDTH),
        random.uniform(0, SOURCE_HEIGHT),
        random.uniform(0.25, 1.0),
    )
    for _ in range(58)
]


def sculpture_strands(time: float, center_x: float, center_y: float):
    result: list[list[tuple[float, float]]] = []
    for strand_index in range(11):
        phase = strand_index * math.tau / 11
        points: list[tuple[float, float]] = []
        for step in range(105):
            angle = step / 104 * math.tau
            x = math.sin(angle * 1.5 + phase + time * 0.22) * 106
            x *= 0.62 + 0.20 * math.sin(angle * 0.7 + strand_index)
            y = math.cos(angle + phase * 0.55 - time * 0.18) * 47
            x += math.sin(angle * 3.0 + time * 0.35 + strand_index) * 12
            y += math.cos(angle * 2.0 - time * 0.25 + strand_index) * 4
            points.append((center_x + x, center_y + y))
        result.append(points)
    return result


def draw_sketch(layer: Image.Image, time: float, alpha: int) -> None:
    for index in range(9):
        points = []
        phase = index * 0.73
        for x in range(12, SOURCE_WIDTH - 12, 3):
            y = SOURCE_HEIGHT * 0.5
            y += math.sin(x / 24 + phase + time * 0.38) * 25
            y += math.sin(x / 7.5 - phase * 0.6 + time * 0.17) * 4
            y += (index - 4) * 1.1
            points.append((x, y))
        color = IVORY if index in (3, 4, 5) else MUTED
        strength = 0.60 if index in (3, 4, 5) else 0.24
        glow_curve(layer, points, color, int(alpha * strength), blur=3)


def draw_sculpture(layer: Image.Image, time: float, alpha: int) -> None:
    center_x, center_y = SOURCE_WIDTH / 2, SOURCE_HEIGHT / 2
    colors = [TEAL, GOLD, IVORY, BLUE]
    strengths = [0.48, 0.34, 0.55, 0.30]
    for index, points in enumerate(sculpture_strands(time, center_x, center_y)):
        glow_curve(
            layer,
            points,
            colors[index % 4],
            int(alpha * strengths[index % 4]),
            width=2 if index % 4 == 0 else 1,
        )

    orbit = []
    for step in range(120):
        angle = step / 119 * math.tau
        orbit.append(
            (
                center_x + math.cos(angle + time * 0.20) * 123,
                center_y + math.sin(angle + time * 0.20) * 25,
            )
        )
    glow_curve(layer, orbit, GOLD, int(alpha * 0.42))

    core = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    core_draw = ImageDraw.Draw(core)
    core_draw.ellipse(
        (center_x - 5, center_y - 5, center_x + 5, center_y + 5),
        fill=IVORY + (int(alpha * 0.9),),
    )
    layer.alpha_composite(core.filter(ImageFilter.GaussianBlur(10)))
    layer.alpha_composite(core)


def draw_organic(layer: Image.Image, time: float, alpha: int) -> None:
    center_x, center_y = SOURCE_WIDTH / 2, SOURCE_HEIGHT / 2
    for ring in range(6):
        points = []
        for step in range(100):
            angle = step / 99 * math.tau
            radius = (18 + ring * 11) * (
                1.0 + 0.08 * math.sin(time * 0.62 + ring + angle * 3)
            )
            points.append(
                (
                    center_x + math.cos(angle) * radius * 1.55,
                    center_y + math.sin(angle) * radius * 0.78,
                )
            )
        glow_curve(
            layer,
            points,
            TEAL if ring % 2 == 0 else GOLD,
            int(alpha * (0.24 + ring * 0.025)),
            blur=4,
        )

    for branch in range(12):
        angle = branch * math.tau / 12 + time * 0.07
        points = []
        for step in range(40):
            progress = step / 39
            radius = 10 + progress * 98
            points.append(
                (
                    center_x + math.cos(angle + progress * 0.75) * radius,
                    center_y
                    + math.sin(angle + progress * 0.75) * radius * 0.47,
                )
            )
        glow_curve(
            layer,
            points,
            BLUE if branch % 3 else IVORY,
            int(alpha * 0.18),
            blur=3,
        )


def source_frame(time: float) -> Image.Image:
    image = Image.new("RGBA", (SOURCE_WIDTH, SOURCE_HEIGHT), BACKGROUND + (255,))
    draw = ImageDraw.Draw(image)

    fog = Image.new("RGBA", image.size, (0, 0, 0, 0))
    fog_draw = ImageDraw.Draw(fog)
    sweep_x = -60 + (SOURCE_WIDTH + 120) * (time / DURATION)
    fog_draw.ellipse(
        (sweep_x - 90, -35, sweep_x + 90, SOURCE_HEIGHT + 35),
        fill=(120, 94, 70, 36),
    )
    image.alpha_composite(fog.filter(ImageFilter.GaussianBlur(34)))

    for x, y, strength in DUST:
        moved_x = (x - time * strength * 2.4) % SOURCE_WIDTH
        moved_y = y + math.sin(time * 0.4 + x * 0.04) * 0.5
        point_alpha = int(38 + 70 * strength)
        draw.ellipse(
            (
                moved_x,
                moved_y,
                moved_x + 0.7 + strength,
                moved_y + 0.7 + strength,
            ),
            fill=IVORY + (point_alpha,),
        )

    sketch_alpha = int(255 * window(time, 0.0, 2.8))
    sculpture_alpha = int(255 * window(time, 2.0, 5.3))
    organic_alpha = int(255 * window(time, 4.5, 7.4))
    synthesis_alpha = int(255 * window(time, 6.6, 9.0))

    if sketch_alpha:
        draw_sketch(image, time, sketch_alpha)
        draw_sculpture(image, time, int(sketch_alpha * 0.38))
    if sculpture_alpha:
        draw_sculpture(image, time, sculpture_alpha)
    if organic_alpha:
        draw_organic(image, time, organic_alpha)
        draw_sculpture(image, time, int(organic_alpha * 0.35))
    if synthesis_alpha:
        draw_sketch(image, time, int(synthesis_alpha * 0.15))
        draw_organic(image, time, int(synthesis_alpha * 0.24))
        draw_sculpture(image, time, synthesis_alpha)

    return image.convert("RGB")


def render_ascii(source: Image.Image, palette: list[str]) -> Image.Image:
    small = source.resize((COLUMNS, ROWS), Image.Resampling.BILINEAR)
    pixels = np.asarray(small, dtype=np.float32)
    luminance = (
        0.2126 * pixels[:, :, 0]
        + 0.7152 * pixels[:, :, 1]
        + 0.0722 * pixels[:, :, 2]
    )

    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    highest = len(palette) - 1

    for row in range(ROWS):
        y = row * CELL_HEIGHT - 1
        for column in range(COLUMNS):
            brightness = luminance[row, column]
            if brightness < 7:
                continue
            palette_index = int((brightness / 255) ** 0.58 * highest)
            palette_index = max(1, min(highest, palette_index))
            rgb = pixels[row, column]
            boost = 0.88 + min(0.42, brightness / 190)
            color = tuple(int(min(255, channel * boost + 12)) for channel in rgb)
            draw.text(
                (column * CELL_WIDTH, y),
                palette[palette_index],
                font=ASCII_FONT,
                fill=color,
            )
    return canvas


def add_ending_name(frame: Image.Image, time: float) -> Image.Image:
    image = frame.convert("RGBA")
    alpha = int(255 * smooth((time - 7.55) / 0.8))
    if alpha:
        draw = ImageDraw.Draw(image)
        draw.text(
            (WIDTH / 2, HEIGHT - 58),
            "ANKIT BHARDWAJ",
            font=NAME_FONT,
            fill=IVORY + (alpha,),
            anchor="mm",
        )
    return image.convert("RGB")


def render(asciline_directory: Path, output: Path) -> None:
    palette = load_asciline_palette(asciline_directory)
    frames = []
    for frame_index in range(FRAME_COUNT):
        time = frame_index / FPS
        frame = render_ascii(source_frame(time), palette)
        frames.append(add_ending_name(frame, time))

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
    print(f"Rendered {output} ({output.stat().st_size / 1024 / 1024:.2f} MB)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--asciline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    render(arguments.asciline, arguments.output)
