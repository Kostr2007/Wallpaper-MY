"""Shared coordinates, tone gradients and procedural textures."""

import colorsys

import numpy as np
from PIL import Image, ImageColor


def u8(values):
    return np.clip(values + 0.5, 0, 255).astype(np.uint8)


def bell(value, spread):
    return np.exp(-np.square(value / spread))


class Canvas:
    def __init__(self, width, height, seed, accent, anchor):
        self.size = width, height
        self.width, self.height = self.size
        self.rng = np.random.default_rng(seed)
        # One unit is the height; objects stay round at any aspect ratio.
        self.u = np.linspace(0, 1, width, dtype=np.float32)[None, :]
        self.x = (self.u - 0.5) * width / height
        self.y = np.linspace(0, 1, height, dtype=np.float32)[:, None]
        self.hue_shift = 0
        if accent:
            hue = self.hue(ImageColor.getrgb(accent))
            self.hue_shift = (hue - self.hue(ImageColor.getrgb(anchor)) + 0.5) % 1 - 0.5

    @staticmethod
    def hue(rgb):
        return colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))[0]

    def color(self, value):
        rgb = ImageColor.getrgb(value)
        if not self.hue_shift:
            return rgb
        hue, light, saturation = colorsys.rgb_to_hls(*(channel / 255 for channel in rgb))
        return tuple(round(channel * 255) for channel in colorsys.hls_to_rgb(
            (hue + self.hue_shift) % 1, light, saturation,
        ))

    def noise(self, columns, rows):
        grid = self.rng.uniform(-1, 1, (rows, columns)).astype(np.float32)
        return np.asarray(Image.fromarray(grid).resize(self.size, Image.Resampling.BICUBIC))

    def ridge(self, scale, amplitude):
        profile = np.zeros(self.width, dtype=np.float32)
        for octave in range(5):
            count = scale * 2**octave
            knots = self.rng.uniform(-1, 1, count)
            profile += np.interp(self.u[0], np.linspace(0, 1, count), knots) * amplitude * 0.48**octave
        return profile

    def grain(self):
        return self.rng.uniform(-1.4, 1.4, (self.height, self.width)).astype(np.float32)

    def tones(self, field, *stops, alpha=None):
        field = np.broadcast_to(field, (self.height, self.width))
        colors = [self.color(color) for _, color in stops]
        levels = [level for level, _ in stops]
        rgb = np.empty((*field.shape, 3), dtype=np.uint8)
        for channel, values in enumerate(zip(*colors)):
            rgb[:, :, channel] = u8(np.interp(field, levels, values))
        if alpha is None:
            return Image.fromarray(rgb).convert("RGBA")
        coverage = u8(np.broadcast_to(alpha, field.shape) * 255)
        rgb[coverage == 0] = 0
        image = Image.fromarray(rgb).convert("RGBA")
        image.putalpha(Image.fromarray(coverage))
        return image

    def wash(self, layer, color, opacity):
        rgba = Image.new("RGBA", self.size, (*self.color(color), 0))
        rgba.putalpha(Image.fromarray(u8(np.broadcast_to(opacity, (self.height, self.width)) * 255)))
        layer.alpha_composite(rgba)

    def transparent(self):
        return Image.new("RGBA", self.size)

    def stroke(self, draw, points, color, opacity=255, weight=1):
        draw.line(points, fill=(*self.color(color), opacity), width=max(1, round(self.height * weight / 720)))
