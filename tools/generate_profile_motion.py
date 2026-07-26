"""Generate the animated ASCII signal-core used by the profile README.

The moving object is an original animation. Its character rendering uses
ASCILINE's published AsciiMapper palette and grayscale-to-character mapping.
ASCILINE: https://github.com/YusufB5/ASCILINE
"""

from __future__ import annotations

import argparse
import importlib.util
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

WIDTH = 960
HEIGHT = 280
FPS = 10
SECONDS = 6
FRAME_COUNT = FPS * SECONDS

BACKGROUND = (9, 10, 11)
PANEL = (14, 15, 16)
CREAM = (235, 229, 216)
MUTED = (151, 151, 145)
BRONZE = (204, 177, 128)
TEAL = (103, 200, 192)
GRID = (35, 37, 39)


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


NAME_FONT = load_font(50, bold=True)
ROLE_FONT = load_font(14, mono=True)
META_FONT = load_font(15, mono=True)
TINY_FONT = load_font(12, mono=True)
ASCII_FONT = load_font(9, mono=True, bold=True)


def load_asciline_palette(asciline_dir: Path) -> list[str]:
    module_path = asciline_dir / "ascii_video_player2.py"
    if not module_path.exists():
        raise FileNotFoundError(f"ASCILINE mapper not found: {module_path}")

    spec = importlib.util.spec_from_file_location("asciline_ascii_mapper", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load ASCILINE AsciiMapper")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    mapper = module.AsciiMapper()
    return [str(character) for character in mapper._lut]


def rotation_y(angle: float) -> np.ndarray:
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array([[cosine, 0, sine], [0, 1, 0], [-sine, 0, cosine]], dtype=float)


def rotation_x(angle: float) -> np.ndarray:
    cosine, sine = math.cos(angle), math.sin(angle)
    return np.array([[1, 0, 0], [0, cosine, -sine], [0, sine, cosine]], dtype=float)


def create_sphere_geometry() -> tuple[np.ndarray, list[tuple[int, int]]]:
    random = np.random.default_rng(6149)
    points: list[np.ndarray] = []

    for _ in range(112):
        vertical = random.uniform(-1, 1)
        theta = random.uniform(0, 2 * math.pi)
        radius = math.sqrt(1 - vertical * vertical)
        points.append(
            np.array(
                [radius * math.cos(theta), vertical, radius * math.sin(theta)],
                dtype=float,
            )
        )

    point_array = np.array(points)
    edges: set[tuple[int, int]] = set()
    for index, point in enumerate(point_array):
        distances = np.sum((point_array - point) ** 2, axis=1)
        for neighbour in np.argsort(distances)[1:5]:
            first, second = sorted((index, int(neighbour)))
            edges.add((first, second))

    return point_array, list(edges)


SPHERE_POINTS, SPHERE_EDGES = create_sphere_geometry()


def render_ascii_object(source: Image.Image, palette: list[str]) -> Image.Image:
    columns = 66
    rows = 28
    small = source.resize((columns, rows), Image.Resampling.BILINEAR)
    rgb = np.asarray(small, dtype=np.uint8)
    grayscale = np.asarray(small.convert("L"), dtype=np.uint8)

    # This is the same grayscale-to-character relationship used by ASCILINE.
    indices = (grayscale.astype(np.uint16) * (len(palette) - 1)) // 255

    canvas = Image.new("RGB", source.size, PANEL)
    draw = ImageDraw.Draw(canvas)
    cell_width = source.width / columns
    cell_height = source.height / rows

    for row in range(rows):
        for column in range(columns):
            character = palette[int(indices[row, column])]
            if character == " ":
                continue

            red, green, blue = [int(value) for value in rgb[row, column]]
            if max(red, green, blue) < 18:
                continue

            draw.text(
                (column * cell_width, row * cell_height - 1),
                character,
                font=ASCII_FONT,
                fill=(red, green, blue),
            )

    return canvas


def draw_motion_object(frame_index: int, palette: list[str]) -> Image.Image:
    progress = frame_index / FRAME_COUNT
    angle = 2 * math.pi * progress

    object_width = 440
    object_height = 248
    object_image = Image.new("RGB", (object_width, object_height), (0, 0, 0))
    draw = ImageDraw.Draw(object_image)

    center_x = 220
    center_y = 124
    scale = 136

    draw.ellipse(
        (center_x - 107, center_y - 107, center_x + 107, center_y + 107),
        outline=(29, 35, 36),
        width=2,
    )
    for radius in (68, 96):
        draw.ellipse(
            (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
            outline=(21, 27, 28),
            width=1,
        )

    rotation = rotation_y(angle * 1.2) @ rotation_x(0.42 + 0.12 * math.sin(angle))
    transformed = SPHERE_POINTS @ rotation.T
    depth = transformed[:, 2]
    perspective = 1.0 / (1.55 - 0.30 * depth)
    projected_x = center_x + transformed[:, 0] * scale * perspective
    projected_y = center_y + transformed[:, 1] * scale * perspective

    for first, second in SPHERE_EDGES:
        average_depth = (depth[first] + depth[second]) / 2
        strength = max(0.12, min(1.0, (average_depth + 1.0) / 2.0))
        color = tuple(
            int((1 - strength) * low + strength * high)
            for low, high in zip((43, 55, 56), TEAL)
        )
        draw.line(
            (projected_x[first], projected_y[first], projected_x[second], projected_y[second]),
            fill=color,
            width=2,
        )

    for index in range(len(SPHERE_POINTS)):
        strength = max(0.15, min(1.0, (depth[index] + 1.0) / 2.0))
        radius = 2 + int(strength * 3.2)
        color = tuple(
            int((1 - strength) * low + strength * high)
            for low, high in zip((72, 65, 54), BRONZE)
        )
        draw.ellipse(
            (
                projected_x[index] - radius,
                projected_y[index] - radius,
                projected_x[index] + radius,
                projected_y[index] + radius,
            ),
            fill=color,
        )

    waveform: list[tuple[float, float]] = []
    for coordinate in np.linspace(-1, 1, 120):
        vertical = 0.22 * math.sin(3.2 * math.pi * coordinate + angle * 2.4)
        depth_value = 0.42 * math.cos(1.4 * math.pi * coordinate + angle)
        vector = np.array([coordinate, vertical, depth_value]) @ rotation.T
        perspective_value = 1.0 / (1.55 - 0.30 * vector[2])
        waveform.append(
            (
                center_x + vector[0] * scale * perspective_value,
                center_y + vector[1] * scale * perspective_value,
            )
        )
    draw.line(waveform, fill=(245, 215, 160), width=3)

    orbit_angle = angle * 1.65
    orbit: list[tuple[float, float]] = []
    for coordinate in np.linspace(0, 2 * math.pi, 160):
        vector = np.array(
            [1.22 * math.cos(coordinate), 0.43 * math.sin(coordinate), 0.22 * math.sin(coordinate)]
        )
        vector = vector @ rotation_x(-0.45).T @ rotation_y(orbit_angle * 0.14).T
        orbit.append((center_x + vector[0] * scale, center_y + vector[1] * scale))
    draw.line(orbit, fill=(190, 164, 119), width=2)

    node = np.array(
        [1.22 * math.cos(orbit_angle), 0.43 * math.sin(orbit_angle), 0.22 * math.sin(orbit_angle)]
    )
    node = node @ rotation_x(-0.45).T @ rotation_y(orbit_angle * 0.14).T
    node_x = center_x + node[0] * scale
    node_y = center_y + node[1] * scale
    draw.polygon(
        [(node_x, node_y - 9), (node_x + 9, node_y), (node_x, node_y + 9), (node_x - 9, node_y)],
        fill=CREAM,
    )

    core_radius = 22 + 7 * (0.5 + 0.5 * math.sin(angle * 2.0))
    draw.ellipse(
        (
            center_x - core_radius,
            center_y - core_radius,
            center_x + core_radius,
            center_y + core_radius,
        ),
        outline=(235, 207, 154),
        width=3,
    )

    hexagon = []
    for index in range(6):
        hexagon_angle = angle * 0.65 + index * math.pi / 3
        hexagon.append(
            (
                center_x + math.cos(hexagon_angle) * 34,
                center_y + math.sin(hexagon_angle) * 34,
            )
        )
    draw.line(hexagon + [hexagon[0]], fill=(118, 224, 214), width=2)

    for index in range(16):
        phase = (progress * 1.4 + index / 16) % 1.0
        particle_angle = phase * 2 * math.pi
        particle_radius = 116 + 8 * math.sin(particle_angle * 3 + index)
        particle_x = center_x + math.cos(particle_angle) * particle_radius
        particle_y = center_y + math.sin(particle_angle * 1.3) * 54
        radius = 1 + (index % 3 == 0)
        draw.ellipse(
            (
                particle_x - radius,
                particle_y - radius,
                particle_x + radius,
                particle_y + radius,
            ),
            fill=(74, 120, 117),
        )

    glow = object_image.filter(ImageFilter.GaussianBlur(7))
    object_image = Image.blend(glow, object_image, 0.88)
    object_image = ImageEnhance.Brightness(object_image).enhance(1.45)
    return render_ascii_object(object_image, palette)


def draw_frame(frame_index: int, palette: list[str]) -> Image.Image:
    progress = frame_index / FRAME_COUNT
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle(
        (10, 10, WIDTH - 10, HEIGHT - 10),
        radius=20,
        fill=PANEL,
        outline=(43, 43, 40),
        width=1,
    )

    for x_coordinate in range(30, WIDTH - 20, 36):
        draw.line((x_coordinate, 22, x_coordinate, HEIGHT - 22), fill=GRID, width=1)
    for y_coordinate in range(22, HEIGHT - 20, 36):
        draw.line((22, y_coordinate, WIDTH - 22, y_coordinate), fill=GRID, width=1)

    pulse = 0.65 + 0.35 * math.sin(2 * math.pi * progress)
    pulse_radius = 3 + int(pulse * 2)
    draw.ellipse(
        (42 - pulse_radius, 39 - pulse_radius, 42 + pulse_radius, 39 + pulse_radius),
        fill=BRONZE,
    )
    draw.text((58, 28), "ANKIT / SIGNAL ONLINE", font=TINY_FONT, fill=MUTED)

    draw.text((40, 77), "ANKIT", font=NAME_FONT, fill=CREAM)
    draw.text((40, 126), "BHARDWAJ", font=NAME_FONT, fill=CREAM)
    draw.text(
        (42, 188),
        "FULL-STACK ENGINEERING  /  AUTOMATION  /  APPLIED AI",
        font=ROLE_FONT,
        fill=BRONZE,
    )
    draw.text(
        (42, 218),
        "Software Engineer at Wyrd Media Labs  ·  NSUT '25",
        font=META_FONT,
        fill=MUTED,
    )
    draw.text((42, 240), "Published researcher · Springer LNNS", font=META_FONT, fill=MUTED)

    path_y = 263
    labels = [("INSTRUMENTATION", 42), ("SOFTWARE", 190), ("INTELLIGENCE", 318)]
    for label, x_coordinate in labels:
        draw.text((x_coordinate, path_y - 9), label, font=TINY_FONT, fill=MUTED)
    draw.line((151, path_y, 180, path_y), fill=(77, 75, 69), width=1)
    draw.line((266, path_y, 308, path_y), fill=(77, 75, 69), width=1)

    travel = (frame_index * 6) % 210
    if travel < 29:
        travelling_x = 151 + travel
    elif travel < 105:
        travelling_x = 190 + (travel - 29)
    else:
        travelling_x = 318 + (travel - 105)
    if travelling_x < 423:
        draw.ellipse(
            (travelling_x - 3, path_y - 3, travelling_x + 3, path_y + 3),
            fill=TEAL,
        )

    image.paste(draw_motion_object(frame_index, palette), (505, 18))
    draw.text((755, 252), "ASCII SIGNAL CORE", font=TINY_FONT, fill=(102, 104, 101))
    return image


def generate(output: Path, palette: list[str]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = [draw_frame(index, palette).quantize(colors=64) for index in range(FRAME_COUNT)]
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=int(1000 / FPS),
        loop=0,
        optimize=True,
        disposal=2,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--asciline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    generate(arguments.output, load_asciline_palette(arguments.asciline))
    print(f"Generated {arguments.output} ({arguments.output.stat().st_size} bytes)")
