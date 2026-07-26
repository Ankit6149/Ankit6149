"""Render the cinematic typographic motion used by Ankit's profile README.

The underlying motion is original. The final frames use ASCILINE's published
character palette and grayscale-to-character mapping.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WIDTH = 900
HEIGHT = 375
SOURCE_WIDTH = 360
SOURCE_HEIGHT = 150
COLUMNS = 90
ROWS = 37
CELL_WIDTH = WIDTH // COLUMNS
CELL_HEIGHT = HEIGHT // ROWS
FPS = 8
DURATION = 10
FRAME_COUNT = FPS * DURATION

BACKGROUND = (4, 6, 10)
IVORY = (239, 234, 222)
TEAL = (82, 222, 205)
BLUE = (103, 160, 235)
GOLD = (233, 185, 88)
MUTED = (135, 146, 158)


def load_font(size: int, *, bold: bool = False, mono: bool = False) -> ImageFont.FreeTypeFont:
    if mono:
        names = [
            "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf",
            "LiberationMono-Bold.ttf" if bold else "LiberationMono-Regular.ttf",
        ]
    else:
        names = [
            "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
            "LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf",
        ]

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
TITLE_FONT = load_font(36, bold=True)
SUBTITLE_FONT = load_font(15)
LABEL_FONT = load_font(14, mono=True, bold=True)
METRIC_FONT = load_font(40, mono=True, bold=True)


def load_asciline_palette(asciline_dir: Path) -> list[str]:
    module_path = asciline_dir / "ascii_video_player2.py"
    if not module_path.exists():
        raise FileNotFoundError(f"ASCILINE mapper not found: {module_path}")

    spec = importlib.util.spec_from_file_location("asciline_mapper", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load ASCILINE mapper")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mapper = module.AsciiMapper()
    return [str(character) for character in mapper._lut]


def smoothstep(value: float) -> float:
    value = max(0.0, min(1.0, value))
    return value * value * (3.0 - 2.0 * value)


def alpha_window(time: float, start: float, end: float, fade: float = 0.6) -> float:
    if time < start or time > end:
        return 0.0
    return min(
        smoothstep((time - start) / fade),
        smoothstep((end - time) / fade),
        1.0,
    )


def glow_line(
    layer: Image.Image,
    points: list[tuple[float, float]],
    color: tuple[int, int, int],
    *,
    width: int = 1,
    blur: int = 5,
    alpha: int = 255,
) -> None:
    sharp = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(sharp)
    draw.line(points, fill=color + (alpha,), width=width, joint="curve")
    layer.alpha_composite(sharp.filter(ImageFilter.GaussianBlur(blur)))
    layer.alpha_composite(sharp)


def project(
    point: tuple[float, float, float],
    rotate_y: float,
    rotate_x: float,
    radius: float,
    center_x: float,
    center_y: float,
) -> tuple[float, float, float]:
    x, y, z = point
    cosine_y, sine_y = math.cos(rotate_y), math.sin(rotate_y)
    cosine_x, sine_x = math.cos(rotate_x), math.sin(rotate_x)

    x, z = x * cosine_y + z * sine_y, -x * sine_y + z * cosine_y
    y, z = y * cosine_x - z * sine_x, y * sine_x + z * cosine_x
    perspective = 1.0 / (2.15 - z * 0.55)
    return (
        center_x + x * radius * perspective,
        center_y + y * radius * perspective,
        z,
    )


random.seed(6149)
SPHERE_POINTS: list[tuple[float, float, float]] = []
for _ in range(480):
    vertical = random.uniform(-1.0, 1.0)
    theta = random.uniform(0.0, math.tau)
    horizontal = math.sqrt(max(0.0, 1.0 - vertical * vertical))
    SPHERE_POINTS.append(
        (horizontal * math.cos(theta), vertical, horizontal * math.sin(theta))
    )

STARS = [
    (
        random.uniform(0.0, SOURCE_WIDTH),
        random.uniform(0.0, SOURCE_HEIGHT),
        random.uniform(0.2, 1.0),
    )
    for _ in range(80)
]


def draw_sculpture(
    layer: Image.Image,
    time: float,
    center_x: float,
    center_y: float,
    radius: float,
    alpha: int,
) -> None:
    draw = ImageDraw.Draw(layer)

    for index, point in enumerate(SPHERE_POINTS):
        x, y, depth = project(
            point,
            time * 0.9,
            0.28 + math.sin(time * 0.45) * 0.16,
            radius,
            center_x,
            center_y,
        )
        strength = (depth + 1.0) / 2.0
        color = TEAL if index % 5 else BLUE
        point_alpha = int(alpha * (0.12 + 0.78 * strength))
        point_radius = 0.4 + strength
        draw.ellipse(
            (
                x - point_radius,
                y - point_radius,
                x + point_radius,
                y + point_radius,
            ),
            fill=color + (point_alpha,),
        )

    for ring_index, tilt in enumerate((0.10, 0.62, -0.48)):
        ring: list[tuple[float, float]] = []
        for step in range(90):
            angle = step / 89 * math.tau
            point = (
                math.cos(angle) * 1.28,
                math.sin(angle) * math.cos(tilt) * 1.28,
                math.sin(angle) * math.sin(tilt) * 1.28,
            )
            x, y, _ = project(
                point,
                time * (0.35 + ring_index * 0.09),
                0.05,
                radius,
                center_x,
                center_y,
            )
            ring.append((x, y))

        glow_line(
            layer,
            ring,
            GOLD if ring_index == 1 else BLUE,
            blur=4,
            alpha=int(alpha * (0.72 if ring_index == 1 else 0.38)),
        )

    nucleus = Image.new("RGBA", layer.size, (0, 0, 0, 0))
    nucleus_draw = ImageDraw.Draw(nucleus)
    nucleus_radius = max(3, int(radius * 0.07))
    nucleus_draw.ellipse(
        (
            center_x - nucleus_radius,
            center_y - nucleus_radius,
            center_x + nucleus_radius,
            center_y + nucleus_radius,
        ),
        fill=IVORY + (alpha,),
    )
    layer.alpha_composite(nucleus.filter(ImageFilter.GaussianBlur(8)))
    layer.alpha_composite(nucleus)


def draw_software_space(layer: Image.Image, time: float, alpha: int) -> None:
    draw = ImageDraw.Draw(layer)
    horizon_x, horizon_y = 308, 75

    for lane in range(-5, 6):
        start_x = horizon_x + lane * 10
        end_x = 12 + (lane + 5) * 34
        glow_line(
            layer,
            [(start_x, horizon_y), (end_x, SOURCE_HEIGHT + 10)],
            BLUE,
            blur=2,
            alpha=int(alpha * 0.32),
        )

    for depth_index in range(9):
        depth = (time * 0.65 + depth_index / 9) % 1.0
        y = horizon_y + depth**1.8 * (SOURCE_HEIGHT - horizon_y)
        half_width = 12 + depth * 180
        glow_line(
            layer,
            [(horizon_x - half_width, y), (horizon_x + half_width, y)],
            TEAL,
            blur=2,
            alpha=int(alpha * (0.14 + 0.45 * depth)),
        )

    for index in range(4):
        phase = (time * 0.35 + index * 0.27) % 1.0
        scale = 0.35 + phase * 1.3
        center_x = horizon_x + math.sin(index * 1.7) * 72 * scale
        center_y = horizon_y + phase * 65
        width = 30 * scale
        height = 14 * scale
        draw.rounded_rectangle(
            (
                center_x - width,
                center_y - height,
                center_x + width,
                center_y + height,
            ),
            radius=3,
            outline=IVORY + (int(alpha * (0.14 + phase * 0.35)),),
            width=1,
        )
        draw.line(
            (
                center_x - width + 4,
                center_y - 4,
                center_x + width - 7,
                center_y - 4,
            ),
            fill=TEAL + (int(alpha * 0.38),),
        )
        draw.line(
            (
                center_x - width + 4,
                center_y + 3,
                center_x + width - 14,
                center_y + 3,
            ),
            fill=BLUE + (int(alpha * 0.28),),
        )


def draw_research_space(layer: Image.Image, time: float, alpha: int) -> None:
    waveform: list[tuple[float, float]] = []
    for x in range(12, SOURCE_WIDTH - 12, 2):
        baseline = math.sin(x / 18 + time * 1.8) * 5
        spike_one = math.exp(-((x - 112) / 14) ** 2) * math.sin((x - 112) * 0.8) * 23
        spike_two = math.exp(-((x - 248) / 19) ** 2) * math.sin((x - 248) * 0.62) * 17
        waveform.append((x, 77 + baseline + spike_one + spike_two))
    glow_line(layer, waveform, TEAL, width=2, blur=5, alpha=alpha)

    draw = ImageDraw.Draw(layer)
    for row in range(6):
        for column in range(14):
            x = 28 + column * 22
            y = 100 + row * 6
            activation = 0.15 + 0.85 * abs(
                math.sin(time * 1.9 + row * 0.58 + column * 0.37)
            )
            color = GOLD if (row + column) % 5 == 0 else BLUE
            draw.rounded_rectangle(
                (x, y, x + 14, y + 3),
                radius=1,
                fill=color + (int(alpha * activation * 0.72),),
            )


def source_frame(time: float) -> Image.Image:
    image = Image.new("RGBA", (SOURCE_WIDTH, SOURCE_HEIGHT), BACKGROUND + (255,))
    draw = ImageDraw.Draw(image)

    fog = Image.new("RGBA", image.size, (0, 0, 0, 0))
    fog_draw = ImageDraw.Draw(fog)
    sweep_x = -80 + (SOURCE_WIDTH + 160) * (time / DURATION)
    fog_draw.ellipse(
        (sweep_x - 90, -40, sweep_x + 90, SOURCE_HEIGHT + 40),
        fill=(65, 115, 145, 45),
    )
    image.alpha_composite(fog.filter(ImageFilter.GaussianBlur(34)))

    for x, y, strength in STARS:
        moved_x = (x - time * strength * 5) % SOURCE_WIDTH
        star_alpha = int(30 + 95 * strength)
        draw.ellipse(
            (moved_x, y, moved_x + 1 + strength, y + 1 + strength),
            fill=IVORY + (star_alpha,),
        )

    identity_alpha = int(255 * alpha_window(time, 0.0, 3.2))
    software_alpha = int(255 * alpha_window(time, 2.3, 6.1))
    research_alpha = int(255 * alpha_window(time, 5.2, 9.0))

    if identity_alpha:
        center_x = 63 + smoothstep(time / 2.6) * 94
        draw_sculpture(image, time, center_x, 75, 89, identity_alpha)

    if software_alpha:
        draw_software_space(image, time, software_alpha)
        center_x = 140 + smoothstep((time - 2.3) / 3.2) * 140
        draw_sculpture(image, time, center_x, 77, 65, software_alpha)

    if research_alpha:
        draw_research_space(image, time, research_alpha)
        center_x = 266 - math.sin(time * 0.6) * 22
        draw_sculpture(image, time, center_x, 68, 47, int(research_alpha * 0.86))

    ending_alpha = int(255 * smoothstep((time - 8.55) / 0.75))
    if ending_alpha:
        veil = Image.new("RGBA", image.size, BACKGROUND + (int(ending_alpha * 0.78),))
        image.alpha_composite(veil)
        draw_sculpture(image, time, 180, 74, 124, ending_alpha)

    return image.convert("RGB")


def render_typographic_frame(source: Image.Image, palette: list[str]) -> Image.Image:
    small = source.resize((COLUMNS, ROWS), Image.Resampling.BILINEAR)
    rgb = np.asarray(small, dtype=np.float32)
    luminance = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]

    canvas = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(canvas)
    palette_length = len(palette) - 1

    for row in range(ROWS):
        y = row * CELL_HEIGHT - 1
        for column in range(COLUMNS):
            brightness = luminance[row, column]
            if brightness < 11:
                continue

            palette_index = int((brightness / 255) ** 0.62 * palette_length)
            palette_index = max(1, min(palette_length, palette_index))
            character = palette[palette_index]
            red, green, blue = rgb[row, column]
            boost = 0.72 + min(0.5, brightness / 210)
            color = tuple(
                int(min(255, channel * boost + 10))
                for channel in (red, green, blue)
            )
            draw.text(
                (column * CELL_WIDTH, y),
                character,
                font=ASCII_FONT,
                fill=color,
            )

    return canvas


def add_overlay(frame: Image.Image, time: float) -> Image.Image:
    image = frame.convert("RGBA")
    draw = ImageDraw.Draw(image)

    identity_alpha = int(255 * alpha_window(time, 0.25, 3.05, 0.55))
    if identity_alpha:
        draw.text((518, 112), "ANKIT BHARDWAJ", font=TITLE_FONT, fill=IVORY + (identity_alpha,))
        draw.text((521, 164), "SOFTWARE ENGINEER", font=LABEL_FONT, fill=TEAL + (identity_alpha,))
        draw.text(
            (521, 194),
            "Applied AI  •  Automation  •  Research",
            font=SUBTITLE_FONT,
            fill=MUTED + (identity_alpha,),
        )

    software_alpha = int(255 * alpha_window(time, 2.7, 5.9, 0.45))
    if software_alpha:
        draw.text((54, 57), "SYSTEMS", font=LABEL_FONT, fill=IVORY + (software_alpha,))
        draw.text((54, 84), "AUTOMATION", font=LABEL_FONT, fill=TEAL + (software_alpha,))
        draw.text((54, 111), "INTERFACES", font=LABEL_FONT, fill=BLUE + (software_alpha,))

    research_alpha = int(255 * alpha_window(time, 5.55, 8.75, 0.5))
    if research_alpha:
        draw.text((68, 46), "86.82%", font=METRIC_FONT, fill=IVORY + (research_alpha,))
        draw.text((72, 98), "ACCURACY", font=LABEL_FONT, fill=MUTED + (research_alpha,))
        draw.text((618, 46), "0.977", font=METRIC_FONT, fill=IVORY + (research_alpha,))
        draw.text((622, 98), "AUROC", font=LABEL_FONT, fill=MUTED + (research_alpha,))

    ending_alpha = int(255 * smoothstep((time - 8.8) / 0.65))
    if ending_alpha:
        draw.rounded_rectangle(
            (190, 262, 710, 315),
            radius=15,
            fill=(7, 9, 13, int(ending_alpha * 0.82)),
            outline=TEAL + (int(ending_alpha * 0.55),),
            width=2,
        )
        draw.text(
            (450, 288),
            "ENGINEERING WITH DEPTH, CLARITY AND INTENT",
            font=LABEL_FONT,
            fill=IVORY + (ending_alpha,),
            anchor="mm",
        )

    draw.rectangle((0, 0, WIDTH, 6), fill=(0, 0, 0, 255))
    draw.rectangle((0, HEIGHT - 6, WIDTH, HEIGHT), fill=(0, 0, 0, 255))
    return image.convert("RGB")


def render(output_path: Path, palette: list[str]) -> None:
    frames: list[Image.Image] = []
    for frame_index in range(FRAME_COUNT):
        time = frame_index / FPS
        frame = render_typographic_frame(source_frame(time), palette)
        frame = add_overlay(frame, time)
        frames.append(
            frame.quantize(colors=56, method=Image.Quantize.MEDIANCUT)
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=round(1000 / FPS),
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--asciline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    render(arguments.output, load_asciline_palette(arguments.asciline))
