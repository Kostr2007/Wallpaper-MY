"""Pack alpha frames for XRender, or composite an RGB GIF for inspection."""

from math import ceil, sqrt
import os
from pathlib import Path
import tempfile

from PIL import Image

from .effects import EffectPainter, receive_light
from .paint import Canvas
from .timeline import PLANES


def compose(layers, size):
    image = Image.new("RGBA", size)
    for name in PLANES:
        if name in layers:
            image.alpha_composite(layers[name])
    return image.convert("RGB")


def paste_with_border(atlas, frame, x, y):
    width, height = frame.size
    atlas.paste(frame, (x + 1, y + 1))
    atlas.paste(frame.crop((0, 0, 1, height)), (x, y + 1))
    atlas.paste(frame.crop((width - 1, 0, width, height)), (x + width + 1, y + 1))
    for row, dest_y in ((0, y), (height - 1, y + height + 1)):
        atlas.paste(frame.crop((0, row, width, row + 1)), (x + 1, dest_y))
        atlas.putpixel((x, dest_y), frame.getpixel((0, row)))
        atlas.putpixel((x + width + 1, dest_y), frame.getpixel((width - 1, row)))


def export_tracks(timeline, art, size, seed, accent, anchor, directory, animate, gif):
    layers = art.layers
    width, height = size
    ratio = min(1, 560 / max(size), sqrt(108_000 / (width * height)))
    frame_size = fw, fh = max(1, round(width * ratio)), max(1, round(height * ratio))
    columns = min(timeline.frames, max(1, round(sqrt(timeline.frames * fh / fw))))
    atlas_size = (fw + 2) * columns, (fh + 2) * ceil(timeline.frames / columns)
    if max(atlas_size) > 8192:
        raise ValueError("effect frame geometry exceeds the filmstrip dimensions")
    painter = EffectPainter(Canvas(*frame_size, seed ^ 0xA7F0, accent, anchor), art.lake)
    ordered = [(name, timeline.tracks[name]) for name in PLANES if name in timeline.tracks]
    bases = {name: layers[name].resize(frame_size, Image.Resampling.LANCZOS)
             for name, track in timeline.tracks.items() if track.base and name in layers}
    atlases = {name: Image.new("RGBA", atlas_size) for name in timeline.tracks} if animate else {}
    preview_frames = []
    if gif:
        gif_ratio = min(1, 640 / max(size))
        gif_size = tuple(max(1, round(value * gif_ratio)) for value in size)
        gif_layers = {name: layer.resize(gif_size, Image.Resampling.LANCZOS) for name, layer in layers.items()
                      if name not in timeline.tracks}

    for index in range(timeline.frames if animate or gif else 1):
        lit_frames = {}
        for name, track in ordered:
            frame = painter.frame(track.effects, bases.get(name), index / timeline.frames)
            if track.light is not None:
                frame = receive_light(frame, lit_frames[track.light])
            lit_frames[name] = frame
            if index == 0:
                layers[name] = frame.resize(size, Image.Resampling.BICUBIC)
            if animate:
                row, column = divmod(index, columns)
                paste_with_border(atlases[name], frame, column * (fw + 2), row * (fh + 2))
            if gif:
                gif_layers[name] = frame.resize(gif_size, Image.Resampling.BICUBIC)
        if gif:
            preview_frames.append(compose(gif_layers, gif_size))

    for name, atlas in atlases.items():
        # The transparent frames retain full alpha precision throughout playback.
        atlas.save(directory / f"{name}.loop.png", compress_level=3)
    tracks = {name: {"width": fw, "height": fh, "columns": columns} for name in atlases}
    for name, track in ordered:
        if name in tracks and track.parallax != name:
            tracks[name]["parallax"] = track.parallax
    return tracks, preview_frames


def save_gif(frames, period, path):
    if path.suffix.lower() != ".gif":
        raise ValueError("GIF path must end in .gif")
    width, height = frames[0].size
    samples = frames[::max(1, len(frames) // 8)]
    montage = Image.new("RGB", (width, height * len(samples)))
    for index, frame in enumerate(samples):
        montage.paste(frame, (0, index * height))
    palette = montage.quantize(colors=160)
    frames = [frame.quantize(palette=palette, dither=Image.Dither.NONE) for frame in frames]
    ticks = [round(i * period * 100 / len(frames)) for i in range(len(frames) + 1)]
    duration = [10 * (end - start) for start, end in zip(ticks, ticks[1:])]
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=path.parent, prefix=".wallpaper-my-preview-") as directory:
        temporary = Path(directory) / path.name
        frames[0].save(temporary, save_all=True, append_images=frames[1:], duration=duration, loop=0)
        os.link(temporary, path)
