"""Render portable live wallpaper packs with a flat Material You preview."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile
from typing import Callable

from PIL import Image

from .paint import Canvas
from .scenes import aurora, dunes, garden


@dataclass(frozen=True)
class Scene:
    paint: Callable[[Canvas], dict[str, Image.Image]]
    accent: str
    seed: int
    period: float
    motion: dict[str, tuple[float, float, float]]


SCENES = {
    "aurora-fjord": Scene(aurora, "#9fffd2", 142, 12, {"atmosphere": (4.8, 2.8, 0)}),
    "amber-dunes": Scene(dunes, "#f7b287", 208, 16, {"atmosphere": (4.7, 1.2, .5)}),
    "tidal-garden": Scene(garden, "#80e0da", 417, 10, {
        "atmosphere": (4.7, 2.1, .08), "foreground": (.75, .38, .5), "particles": (3.2, 4.1, .5),
    }),
}


def render(name, output, width, height, seed=None, accent=None):
    scene = SCENES[name]
    directory = output / name
    if directory.exists():
        raise FileExistsError(f"wallpaper pack already exists: {directory}")
    canvas = Canvas(width, height, scene.seed if seed is None else seed, accent, scene.accent)
    layers = scene.paint(canvas)
    with tempfile.TemporaryDirectory(dir=output, prefix=".wallpaper-my-") as temporary:
        staging = Path(temporary) / name
        companions = staging / f"{name}.parallax"
        companions.mkdir(parents=True, mode=0o755)
        preview = canvas.transparent()
        for plane, image in layers.items():
            preview.alpha_composite(image)
            if plane == "background":
                image = image.convert("RGB")
            image.save(companions / f"{plane}.png", compress_level=4)
        manifest = {"version": 1, "period": scene.period, "layers": scene.motion}
        (companions / "motion.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        preview.convert("RGB").save(staging / f"{name}.png", compress_level=4)
        staging.rename(directory)
    return directory / f"{name}.png"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preset", choices=["all", *SCENES], default="all", help="scene to render (default: all)")
    parser.add_argument("--output", type=Path, default=Path("wallpapers"), help="destination directory")
    parser.add_argument("--width", type=int, default=3840, help="canvas width in pixels")
    parser.add_argument("--height", type=int, default=1440, help="canvas height in pixels")
    parser.add_argument("--seed", type=int, help="override the scene's deterministic seed")
    parser.add_argument("--accent", help="recolor a scene around a #RRGGBB accent")
    parser.add_argument("--list", action="store_true", help="list the available scenes")
    args = parser.parse_args()
    if args.list:
        print("\n".join(SCENES))
        return
    if not (160 <= args.width <= 8192 and 90 <= args.height <= 8192 and args.width * args.height <= 24_000_000):
        parser.error("canvas must be 160×90 to 8192×8192, with at most 24 megapixels")
    if args.accent is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", args.accent):
        parser.error("accent must be #RRGGBB")
    if args.seed is not None and args.seed < 0:
        parser.error("seed must be non-negative")

    names = SCENES if args.preset == "all" else (args.preset,)
    try:
        args.output.mkdir(parents=True, exist_ok=True)
        for name in names:
            if (args.output / name).exists():
                raise FileExistsError(f"wallpaper pack already exists: {args.output / name}")
        for name in names:
            print(render(name, args.output, args.width, args.height, args.seed, args.accent))
    except OSError as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")


if __name__ == "__main__":
    main()
