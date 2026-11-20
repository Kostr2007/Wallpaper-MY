"""Verify deterministic recipes, looping effects and the exported bundle."""

import json
from math import ceil
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops

sys.path.insert(0, sys.argv[1])
from wallpaper_my.timeline import Curve, PLANES


def atlas_frames(pack, name, track, count):
    width, height, columns = (track[key] for key in ("width", "height", "columns"))
    stride_x, stride_y = width + 2, height + 2
    with Image.open(pack / f"{name}.loop.png") as atlas:
        assert atlas.size == (stride_x * columns, stride_y * ceil(count / columns))
        assert atlas.mode == "RGBA"
        frames = []
        for index in range(count):
            row, column = divmod(index, columns)
            x, y = column * stride_x + 1, row * stride_y + 1
            frame = atlas.crop((x, y, x + width, y + height))
            assert atlas.getpixel((x - 1, y - 1)) == frame.getpixel((0, 0))
            frames.append(frame)
        return frames


def check(directory, size):
    name = directory.name
    static = directory / f"{name}.png"
    pack = directory / f"{name}.parallax"
    composition = Image.new("RGBA", size)
    for name in PLANES:
        layer = pack / f"{name}.png"
        if layer.is_file():
            with Image.open(layer) as image:
                assert image.size == size
                assert image.mode == ("RGB" if name == "background" else "RGBA")
                composition.alpha_composite(image.convert("RGBA"))
    with Image.open(static) as preview:
        assert preview.mode == "RGB" and preview.size == size
        assert ImageChops.difference(preview, composition.convert("RGB")).getbbox() is None
    return pack


curve = Curve.read({"keys": [[0, 0.2, "hold"], [.25, 0.4, "linear"], [.5, 1], [1, 0.2]]}, 0, 1, "strength")
assert curve.at(.125) == .2 and curve.at(.375) == .7
assert curve.at(1) == curve.at(0) and abs(curve.at(.999) - curve.at(0)) < .001

with TemporaryDirectory() as directory:
    root = Path(directory)
    command = ["wallpaper-my", "--width", "320", "--height", "180"]
    subprocess.run([*command, "--output", str(root / "first")], check=True)
    subprocess.run([*command, "--output", str(root / "repeat")], check=True)
    for scene in ("aurora-fjord", "amber-dunes", "tidal-garden"):
        pack = check(root / "first" / scene, (320, 180))
        manifest = json.loads((pack / "motion.json").read_text())
        assert manifest["version"] == 2 and 2 <= manifest["period"] <= 120
        for name, track in manifest["tracks"].items():
            assert (pack / f"{name}.png").is_file()
            frames = atlas_frames(pack, name, track, manifest["frames"])
            alpha_start = frames[0].getchannel("A")
            alpha_peak = frames[len(frames) // 2].getchannel("A")
            assert alpha_start.histogram() != alpha_peak.histogram(), name
            assert ImageChops.difference(alpha_start, alpha_peak).getbbox() is not None
        for file in (root / "first" / scene).rglob("*"):
            if file.is_file():
                assert file.read_bytes() == (root / "repeat" / file.relative_to(root / "first")).read_bytes()

    template = subprocess.check_output(["wallpaper-my", "--write-recipe", "tidal-garden"], text=True)
    recipe = json.loads(template)
    recipe.update(duration=2, fps=6)
    recipe["tracks"]["foreground"] = {"base": True, "effects": [{"type": "wave", "strength": .8}]}
    recipe_path = root / "custom.json"
    recipe_path.write_text(json.dumps(recipe))
    gif = root / "preview.gif"
    subprocess.run([*command, "--output", str(root / "portrait"), "--recipe", str(recipe_path), "--gif", str(gif),
                    "--width", "180", "--height", "320", "--seed", "0", "--accent", "#d092bf"], check=True)
    pack = check(root / "portrait" / "tidal-garden", (180, 320))
    assert (pack / "foreground.loop.png").is_file()
    with Image.open(gif) as preview:
        assert preview.is_animated and preview.n_frames == 12 and preview.info["loop"] == 0

    subprocess.run([*command, "--preset", "tidal-garden", "--still", "--output", str(root / "still")], check=True)
    still = check(root / "still" / "tidal-garden", (320, 180))
    assert not (still / "motion.json").exists()
    original = root / "first" / "tidal-garden" / "tidal-garden.png"
    assert original.read_bytes() == (still.parent / original.name).read_bytes()

    recipe["tracks"]["atmosphere"]["effects"][0]["strength"] = {"keys": [[0, .2], [1, .9]]}
    recipe_path.write_text(json.dumps(recipe))
    assert subprocess.run([*command, "--recipe", str(recipe_path)], capture_output=True).returncode == 2
    assert subprocess.run([*command, "--output", str(root / "first")], capture_output=True).returncode == 1
