"""Render periodic procedural effects as transparent, composable frames."""

from math import cos, pi, sin, tau

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .paint import bell


def aurora(c, layer, angle, power, scale, color, secondary, noise, _particles):
    x, y, u = c.x, c.y, c.u
    for i, altitude in enumerate((.25, .37, .46)):
        local = angle + 1.9 * i
        wavelength = x * scale
        folds = np.sin(4.7 * wavelength + .83 * np.sin(5 * wavelength + local) + i)
        curl = np.sin(8.4 * wavelength - .93 * np.cos(local) - .7 * i)
        path = altitude + .075 * folds + .043 * curl + .056 * x
        delta = y - path
        ends = bell(u - .5 - .11 * np.sin(local), .39)
        width = .047 + .023 * np.cos(4.3 * wavelength + local)
        curtains = .57 + .26 * np.sin(74 * wavelength + 7 * noise + np.sin(12 * x + local) * 3.2)
        curtains += .16 * np.sin(135 * wavelength + 9 * noise - 2 * local)
        veil = ends * curtains * bell(delta + width, width * 1.3)
        spine = ends * curtains * bell(delta, .011 + .005 * i)
        c.wash(layer, secondary or ("#afa4f4" if i == 1 else "#85a9f6"), power * veil * .48)
        c.wash(layer, color or ("#a5f6cc" if i == 0 else "#78e4d3"), power * (.70 * spine + .30 * veil))


def ripples(c, layer, angle, power, scale, color, secondary, noise, _particles):
    y = c.y
    distance = np.maximum(y - .604, 0)
    path = c.x - .025 + .090 * np.sin(9 * distance + angle)
    center = bell(path, .13 + distance * 1.07)
    depth_mask = np.clip(distance * 48, 0, 1) * bell(distance - .11, .22)
    warp = np.sin(14 * c.x + 23 * distance + angle) * .84 + noise * 2.2
    wave = np.sin(41 * scale * np.log1p(28 * distance) + warp - 2 * angle)
    glitter = np.maximum(wave, 0) ** 3
    c.wash(layer, secondary or "#75accb", power * (.18 * glitter + .06) * depth_mask * center)
    reflected = glitter * (.36 + .64 * np.square(np.cos(c.x * 13 + angle + 4 * noise)))
    c.wash(layer, color or "#b3f4d8", power * .26 * reflected * depth_mask * center)


def haze(c, layer, angle, power, scale, color, secondary, noise, _particles):
    x, y = c.x, c.y
    for i, height in enumerate((.39, .53, .61, .68)):
        local = angle + i * 1.7
        curl = .027 * np.sin(x * (5 + i) * scale + local)
        curl = curl + .019 * np.sin(x * 11 * scale - 2 * local + 2.1 * noise)
        ribbon = y - height - curl + .025 * x
        density = (.6 + .4 * np.sin(x * (7 + i) * scale - local + 3.2 * noise)) ** 2
        taper = bell(x + .48 * np.sin(local), .88)
        alpha = power * .30 * bell(ribbon, .013 + .006 * i) * taper * density
        c.wash(layer, (color or "#ffd7aa") if i > 1 else (secondary or "#f3a5a3"), alpha)


def caustics(c, layer, angle, power, scale, color, secondary, noise, _particles):
    x, y = c.x, c.y
    focus = x + .13 + .055 * np.cos(angle + y * 4)
    spreading = (focus + .31 * y) / (.33 + y)
    mask = bell(focus, .83) * bell(y - .03, .48)
    ray = np.maximum(np.sin(spreading * 15 * scale + 1.6 * noise + .53 * np.sin(angle + 4 * x)), 0) ** 3
    c.wash(layer, color or "#bbffdf", power * ray * mask * .61)
    phase = x * 33 * scale + y * 12 + 3.2 * noise
    interference = np.sin(phase + 1.7 * np.sin(angle + x * 4)) + np.sin(1.28 * phase - 17 * y - angle)
    web = bell(interference, .21) * (.60 + .40 * np.cos(phase * .7 + angle) ** 2)
    c.wash(layer, secondary or "#9beedc", power * .29 * web * mask * bell(y - .10, .19))


def motes(c, layer, angle, power, scale, color, secondary, _noise, particles):
    glow, points = c.transparent(), c.transparent()
    halo, brush = ImageDraw.Draw(glow), ImageDraw.Draw(points)
    bright = c.color(color or "#c6fcf5")
    soft = c.color(secondary or "#76dfd7")
    for x, y, phase, drift, size, speed in particles:
        px = c.width * (x + (.008 + .035 * drift) * sin(angle + phase))
        py = c.height * (y - (.018 + .052 * drift) * cos(angle + phase * .63))
        pulse = (.35 + .65 * (.5 + .5 * sin(angle * speed + phase)) ** 2) * power
        radius = max(.6, size * c.height * scale)
        halo_radius = radius * 2.55
        halo.ellipse((px - halo_radius, py - halo_radius, px + halo_radius, py + halo_radius),
                     fill=(*soft, round(72 * pulse)))
        brush.ellipse((px - radius, py - radius, px + radius, py + radius), fill=(*bright, round(245 * pulse)))
    layer.alpha_composite(glow.filter(ImageFilter.GaussianBlur(max(.7, c.height * .004))))
    layer.alpha_composite(points)


def wave(c, layer, angle, power, scale, _color, _secondary, noise, _particles):
    # Fix the bottom in place and interpolate in premultiplied alpha to avoid dark fringes.
    row = np.arange(c.height)[:, None]
    x = np.arange(c.width, dtype=np.float32)[None, :]
    sway = .04 * c.width * power * ((1 - c.y) ** 1.5)
    shift = sway * np.sin((12 * c.x + 7 * c.y) * scale + .9 * noise + angle)
    sample = np.clip(x - shift, 0, c.width - 1)
    left = sample.astype(np.int32)
    weight = (sample - left)[..., None]
    pixels = np.asarray(layer.convert("RGBa"))
    data = np.rint(pixels[row, left] * (1 - weight) + pixels[row, np.minimum(left + 1, c.width - 1)] * weight)
    layer.paste(Image.frombytes("RGBa", c.size, data.astype(np.uint8).tobytes()).convert("RGBA"))


def bloom(c, layer, _angle, power, scale, _color, _secondary, _noise, _particles):
    halo = layer.convert("RGBa").filter(ImageFilter.GaussianBlur(c.height * .018 * scale)).convert("RGBA")
    halo.putalpha(halo.getchannel("A").point([round(power * i) for i in range(256)]))
    halo.alpha_composite(layer)
    layer.paste(halo)


PAINTERS = {"aurora": aurora, "haze": haze, "caustics": caustics, "ripples": ripples,
            "particles": motes, "wave": wave, "bloom": bloom}


class EffectPainter:
    def __init__(self, canvas):
        self.canvas = canvas
        self.noise = canvas.noise(36, 14)
        count = min(210, max(42, round(61 * canvas.width / canvas.height)))
        self.particles = [(canvas.rng.random(), canvas.rng.uniform(.115, .95), canvas.rng.uniform(0, tau),
                           canvas.rng.random(), canvas.rng.uniform(.0012, .0064), int(canvas.rng.integers(1, 4)))
                          for _ in range(count)]

    def frame(self, effects, base, time):
        layer = base.copy() if base is not None else self.canvas.transparent()
        for index, effect in enumerate(effects):
            power = effect.strength.at(time)
            if power > 0:
                angle = tau * (time % 1) * effect.cycles + index * pi * .48
                PAINTERS[effect.name](self.canvas, layer, angle, power, effect.scale.at(time),
                                      effect.color, effect.secondary, self.noise, self.particles)
        return layer
