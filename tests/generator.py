"""Check the shipped command and its PNG / companion bundle contract."""

import json
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory

from PIL import Image, ImageChops


with TemporaryDirectory() as directory:
    root = Path(directory)
    command = ["wallpaper-my", "--width", "320", "--height", "180"]
    subprocess.run([*command, "--output", str(root / "first")], check=True)
    subprocess.run([*command, "--output", str(root / "repeat")], check=True)
    subprocess.run([*command, "--output", str(root / "portrait"), "--preset", "tidal-garden",
                    "--width", "180", "--height", "320", "--seed", "0", "--accent", "#d092bf"], check=True)
    assert subprocess.run([*command, "--output", str(root / "first")], capture_output=True).returncode == 1
    assert subprocess.run([*command, "--accent", "red"], capture_output=True).returncode == 2

    def check(directory, size):
        name = directory.name
        static = directory / f"{name}.png"
        pack = directory / f"{name}.parallax"
        layers = [pack / f"{plane}.png" for plane in ("background", "atmosphere", "middle", "foreground", "particles")]
        composition = Image.new("RGBA", size)
        for layer in layers:
            if layer.is_file():
                with Image.open(layer) as image:
                    assert image.size == size
                    assert image.mode == ("RGB" if layer == layers[0] else "RGBA")
                    if image.mode == "RGBA":
                        low, high = image.getchannel("A").getextrema()
                        assert low == 0 and high > 0, layer
                    composition.alpha_composite(image.convert("RGBA"))
        with Image.open(static) as preview:
            assert preview.mode == "RGB" and preview.size == size
            assert ImageChops.difference(preview, composition.convert("RGB")).getbbox() is None
        manifest = json.loads((pack / "motion.json").read_text())
        assert manifest["version"] == 1 and 2 <= manifest["period"] <= 120
        for plane, (x, y, phase) in manifest["layers"].items():
            assert (pack / f"{plane}.png").is_file() and 0 <= x <= 5 and 0 <= y <= 5 and 0 <= phase <= 1

    for scene in ("aurora-fjord", "amber-dunes", "tidal-garden"):
        check(root / "first" / scene, (320, 180))
        for file in (root / "first" / scene).rglob("*"):
            if file.is_file():
                assert file.read_bytes() == (root / "repeat" / file.relative_to(root / "first")).read_bytes()
    check(root / "portrait" / "tidal-garden", (180, 320))
