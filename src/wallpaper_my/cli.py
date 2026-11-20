"""Render procedural wallpapers and editable timelines for live effects."""

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import re
import tempfile
from typing import Callable

from PIL import Image

from .export import compose, export_tracks, save_gif
from .paint import Canvas
from .scenes import aurora, dunes, garden
from .timeline import EFFECTS, RECIPES, Timeline


@dataclass(frozen=True)
class Scene:
    paint: Callable[[Canvas], dict[str, Image.Image]]
    accent: str
    seed: int


SCENES = {
    "aurora-fjord": Scene(aurora, "#9fffd2", 142),
    "amber-dunes": Scene(dunes, "#f7b287", 208),
    "tidal-garden": Scene(garden, "#80e0da", 417),
}


def render(name, timeline, output, size, seed, accent, animate, gif):
    scene = SCENES[name]
    seed = scene.seed if seed is None else seed
    directory = output / name
    layers = scene.paint(Canvas(*size, seed, accent, scene.accent))
    with tempfile.TemporaryDirectory(dir=output, prefix=".wallpaper-my-") as temporary:
        staging = Path(temporary) / name
        companions = staging / f"{name}.parallax"
        companions.mkdir(parents=True)
        tracks, frames = export_tracks(timeline, layers, size, seed, accent, scene.accent, companions, animate, gif)
        for plane, image in layers.items():
            if plane == "background":
                image = image.convert("RGB")
            image.save(companions / f"{plane}.png", compress_level=4)
        if tracks:
            manifest = {"version": 2, "period": timeline.duration, "frames": timeline.frames, "tracks": tracks}
            (companions / "motion.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        compose(layers, size).save(staging / f"{name}.png", compress_level=4)
        if gif:
            save_gif(frames, timeline.duration, gif)
        staging.rename(directory)
    return directory / f"{name}.png"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--preset", choices=["all", *SCENES], help="scene to render (default: all)")
    selection.add_argument("--recipe", type=Path, help="render a scene with a JSON effects timeline")
    selection.add_argument("--write-recipe", choices=SCENES, help="print a preset's editable JSON timeline")
    selection.add_argument("--list", action="store_true", help="list the available scenes")
    selection.add_argument("--list-effects", action="store_true", help="list the available effects")
    parser.add_argument("--output", type=Path, default=Path("wallpapers"), help="destination directory")
    parser.add_argument("--width", type=int, default=3840, help="canvas width in pixels")
    parser.add_argument("--height", type=int, default=1440, help="canvas height in pixels")
    parser.add_argument("--seed", type=int, help="override the scene's deterministic seed")
    parser.add_argument("--accent", help="recolor a scene around a #RRGGBB accent")
    parser.add_argument("--still", action="store_true", help="export parallax layers at frame zero")
    parser.add_argument("--gif", type=Path, help="export a looping GIF preview of one scene")
    args = parser.parse_args()
    if args.list or args.list_effects:
        print("\n".join(EFFECTS if args.list_effects else SCENES))
        return
    if args.write_recipe:
        print(json.dumps(RECIPES[args.write_recipe], indent=2))
        return
    if not (160 <= args.width <= 8192 and 90 <= args.height <= 8192 and args.width * args.height <= 24_000_000):
        parser.error("canvas must be 160×90 to 8192×8192, with at most 24 megapixels")
    if args.accent is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", args.accent):
        parser.error("accent must be #RRGGBB")
    if args.seed is not None and args.seed < 0:
        parser.error("seed must be non-negative")
    if args.gif and (args.gif.suffix.lower() != ".gif" or (not args.recipe and args.preset in (None, "all"))):
        parser.error("--gif needs a .gif path and one preset or recipe")

    try:
        if args.recipe:
            data = [json.loads(args.recipe.read_text(encoding="utf-8"))]
        else:
            names = SCENES if args.preset in (None, "all") else (args.preset,)
            data = [RECIPES[name] for name in names]
        timelines = [Timeline.read(recipe, SCENES) for recipe in data]
        if args.gif and args.gif.exists():
            raise FileExistsError(f"GIF already exists: {args.gif}")
        args.output.mkdir(parents=True, exist_ok=True)
        for name, _ in timelines:
            if (args.output / name).exists():
                raise FileExistsError(f"wallpaper pack already exists: {args.output / name}")
        for name, timeline in timelines:
            print(render(name, timeline, args.output, (args.width, args.height), args.seed,
                         args.accent, not args.still, args.gif))
    except ValueError as exc:
        parser.error(str(exc))
    except OSError as exc:
        parser.exit(1, f"{parser.prog}: {exc}\n")


if __name__ == "__main__":
    main()
