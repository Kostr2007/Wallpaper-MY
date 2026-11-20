"""Render periodic procedural effects as transparent, composable frames."""

from math import cos, pi, sin, tau

import numpy as np
from PIL import Image, ImageChops, ImageFilter

from .paint import bell, u8
from .scenes import Lake


def aurora(c, layer, angle, power, scale, color, secondary, noise, _particles):
    x, y, u = c.x, c.y, c.u
    for i, altitude in enumerate((.30, .414)):
        local = angle + 1.7 * i
        wavelength = x * scale
        folds = np.sin(3.8 * wavelength + .53 * np.sin(2.6 * wavelength + local) + i)
        curl = np.sin(7.3 * wavelength - .43 * np.cos(local) - .7 * i)
        path = altitude + .074 * folds + .030 * curl + .050 * x
        delta = y - path
        ends = bell(u - .46 - .053 * np.sin(local), .36)
        width = .058 + .019 * np.cos(4.3 * wavelength + local)
        curtains = .68 + .20 * np.sin(43 * wavelength + 3 * noise + .9 * np.sin(8 * x + local))
        curtains += .10 * np.sin(91 * wavelength + 5 * noise - local)
        veil = ends * curtains * bell(delta + width, width * 1.25)
        spine = ends * curtains * bell(delta, .012 + .006 * i)
        c.wash(layer, secondary or ("#8f91cb" if i == 0 else "#77bcb7"), power * veil * (.40 - .12 * i))
        c.wash(layer, color or ("#a3e6bc" if i == 0 else "#68cbbb"),
               power * ((.71 - .23 * i) * spine + .28 * veil))


def reflect(c, layer, angle, power, scale, lake):
    """Project the emitted light onto the lake and let the terrain occlude it."""
    water, mountains = lake.water, lake.mountains
    blocked_sky = ImageChops.lighter(water, mountains)
    visible = ImageChops.multiply(layer.getchannel("A"), ImageChops.invert(blocked_sky))
    layer.putalpha(visible)
    emission = np.asarray(layer.convert("RGBa"), dtype=np.float32)

    distance = np.maximum(c.y - lake.horizon, 0)
    wave = np.sin(64 * distance * scale + 4 * c.x - angle)
    wave += .54 * np.sin(103 * distance * scale - 9 * c.x + 2 * angle)
    x = c.u * (c.width - 1) + wave * (1.3 + 11 * distance) * c.height / 200
    y = (lake.horizon - distance * (1.31 + .39 * distance)
         + wave * (.001 + .016 * distance)) * (c.height - 1)
    x = np.clip(x, 0, c.width - 1)
    y = np.clip(y, 0, c.height - 1)
    left, top = x.astype(np.int32), y.astype(np.int32)
    right, bottom = np.minimum(left + 1, c.width - 1), np.minimum(top + 1, c.height - 1)
    sx, sy = (x - left)[..., None], (y - top)[..., None]
    upper = emission[top, left] * (1 - sx) + emission[top, right] * sx
    lower = emission[bottom, left] * (1 - sx) + emission[bottom, right] * sx
    reflected = (upper * (1 - sy) + lower * sy)
    visibility = np.asarray(water, dtype=np.float32) / 255
    falloff = power * visibility * (.86 - .80 * distance) * (.90 + .064 * wave)
    reflected *= falloff[..., None]
    image = Image.frombytes("RGBa", c.size, u8(reflected).tobytes())
    layer.alpha_composite(image.convert("RGBA"))

    # A short falloff down the silhouette keeps the reflected tint on the ridge.
    ridge = np.asarray(mountains, dtype=np.float32) / 255
    thickness = max(1, round(c.height * .018))
    from_above = np.pad(ridge, ((thickness, 0), (0, 0)))[:-thickness]
    slope = np.maximum(ridge - from_above, 0)
    radiance = emission.sum(axis=0, keepdims=True) / c.height
    strength = (slope * power * .64)[..., None]
    tint = Image.frombytes("RGBa", c.size, u8(radiance * strength).tobytes())
    layer.alpha_composite(tint.convert("RGBA"))


def moonlight(c, layer, angle, power, scale, lake, noise, color):
    """Scatter light from the same moon that is painted on the middle plane."""
    moon_u, moon_y = lake.moon
    dx = (c.u - moon_u) * c.width / c.height
    dy = c.y - moon_y
    direction = np.arctan2(dx, dy)
    radius = np.hypot(dx, dy)
    sky = 1 - np.asarray(ImageChops.lighter(lake.water, lake.mountains), dtype=np.float32) / 255
    mist = (.58 + .32 * bell(c.y - .46, .14) + .13 * noise) * np.exp(-radius * 1.43)
    open_air = np.clip((radius - .045) / .092, 0, 1) * np.clip((dy - .005) / .10, 0, 1)
    fan = np.zeros_like(radius)
    for i, (axis, width, level) in enumerate(((-1.08, .060, .88), (-.82, .043, .84),
                                               (-.56, .072, 1), (-.30, .044, .69), (.08, .080, .37))):
        opening = axis + .019 * np.sin(angle + 1.4 * i)
        fan += level * bell(direction - opening, scale * width * (1 + .34 * radius))
    moon_color = color or "#d6e1fa"
    c.wash(layer, moon_color, power * (.30 * fan + .029 * bell(direction + .60, .55)) * sky * mist * open_air)

    distance = np.maximum(c.y - lake.horizon, 0)
    water = np.asarray(lake.water, dtype=np.float32) / 255
    pool = bell(dx + .025 * noise, .019 + .24 * distance) * bell(distance - .16, .18)
    waves = np.sin(171 * distance - 2 * angle + 12 * dx + 2.6 * noise)
    breaks = np.maximum(0, np.sin(50 * dx + 38 * distance + angle + noise * 2))
    chips = np.maximum(waves, 0) ** 7 * (.18 + .82 * breaks)
    c.wash(layer, moon_color, power * water * pool * (.062 + .22 * chips))


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
    focus = x + .19 + .046 * np.sin(angle + y * 4)
    spreading = (focus + .28 * y) / (.36 + y)
    mask = bell(focus, .98) * np.exp(-y * 1.38)
    ray = (.50 + .50 * np.cos(spreading * 12 * scale + .68 * noise
                              + .62 * np.sin(angle + 3.1 * x))) ** 4
    c.wash(layer, color or "#95cfbd", power * ray * mask * .43)
    phase = x * 32 * scale + y * 16 + 2.9 * noise
    interference = np.sin(phase + .67 * np.sin(angle + x * 4)) + np.sin(1.29 * phase - 17 * y - angle)
    web = bell(interference, .32) * (.70 + .30 * np.cos(phase * .7 + angle) ** 2)
    c.wash(layer, secondary or "#79c0b3", power * .24 * web * mask * bell(y - .05, .16))


def current_phase(x, y, angle, scale):
    return (3.8 * x + 3.1 * y) * scale + angle


def motes(c, layer, angle, power, scale, color, secondary, _noise, particles):
    light = layer.getchannel("A")
    lit = light.getbbox() is not None
    light = light.filter(ImageFilter.GaussianBlur(max(.6, c.height * .012)))
    alphas = np.zeros((2, c.height, c.width), dtype=np.float32)
    for i, (x, y, phase, drift, size) in enumerate(particles):
        horizontal = (x - .5) * c.width / c.height
        flow = current_phase(horizontal, y, angle, scale) + .22 * sin(phase)
        px = c.width * (x + (.012 + .023 * drift) * sin(flow) + .006 * sin(phase + angle))
        py = c.height * (y + (.012 + .016 * drift) * cos(flow + phase * .34))
        if not (0 <= px < c.width and 0 <= py < c.height):
            continue
        illumination = min(1, light.getpixel((int(px), int(py))) / 66) if lit else .72
        opacity = power * (.018 + .27 * illumination) * (1 - .65 * y)
        # Fractional positions keep the small particles from blinking as they cross pixels.
        sigma = max(.38, size * c.height * scale)
        radius = max(1, round(3 * sigma))
        ix, iy = int(px), int(py)
        left, right = max(0, ix - radius), min(c.width, ix + radius + 1)
        top, bottom = max(0, iy - radius), min(c.height, iy + radius + 1)
        xx = np.arange(left, right)[None, :] - px
        yy = np.arange(top, bottom)[:, None] - py
        alphas[i % 2, top:bottom, left:right] += opacity * np.exp(-(xx**2 + yy**2) / (2 * sigma**2))
    c.wash(layer, secondary or "#5c9993", alphas[0])
    c.wash(layer, color or "#81bcab", alphas[1])


def wave(c, layer, angle, power, scale, _color, _secondary, noise, _particles):
    sway = .065 * c.width * power * np.maximum(.86 - c.y, 0) ** 1.45
    shift = sway * np.sin(current_phase(c.x, c.y, angle, scale) + .47 * noise)
    layer.paste(shift_rows(layer, shift))


def shift_rows(layer, shift):
    # Resample premultiplied colors so semi-transparent edges retain their hue.
    width, height = layer.size
    row = np.arange(height)[:, None]
    x = np.arange(width, dtype=np.float32)[None, :]
    sample = np.clip(x - shift, 0, width - 1)
    left = sample.astype(np.int32)
    weight = (sample - left)[..., None]
    pixels = np.asarray(layer.convert("RGBa"))
    data = pixels[row, left] * (1 - weight) + pixels[row, np.minimum(left + 1, width - 1)] * weight
    return Image.frombytes("RGBa", layer.size, u8(data).tobytes()).convert("RGBA")


def sway_preview(layer, sway, time):
    amplitude, root, phase = sway
    height = layer.height
    y = (np.arange(height, dtype=np.float32)[:, None] + .5) / height
    angle = 3.1 * y + phase * tau
    envelope = np.maximum((root - y) / root, 0) ** 1.6
    displacement = amplitude * height * envelope * (np.sin(angle + time * tau) - np.sin(angle)) / 2
    return shift_rows(layer, displacement)


def bloom(c, layer, _angle, power, scale, _color, _secondary, _noise, _particles):
    halo = layer.convert("RGBa").filter(ImageFilter.GaussianBlur(c.height * .018 * scale)).convert("RGBA")
    halo.putalpha(halo.getchannel("A").point([round(power * i) for i in range(256)]))
    halo.alpha_composite(layer)
    layer.paste(halo)


def receive_light(layer, source):
    soft = source.convert("RGBa").filter(ImageFilter.GaussianBlur(.8)).convert("RGBA")
    mask = soft.getchannel("A").point([min(76, round(i * 1.35)) for i in range(256)])
    lit = Image.composite(soft.convert("RGB"), layer.convert("RGB"), mask)
    lit.putalpha(layer.getchannel("A"))
    return lit


PAINTERS = {"aurora": aurora, "haze": haze, "caustics": caustics, "ripples": ripples,
            "particles": motes, "wave": wave, "bloom": bloom}


class EffectPainter:
    def __init__(self, canvas, lake=None):
        self.canvas = canvas
        if lake is not None:
            water, mountains = (mask.resize(canvas.size, Image.Resampling.LANCZOS)
                                for mask in (lake.water, lake.mountains))
            lake = Lake(lake.horizon, water, mountains, lake.moon)
        self.lake = lake
        self.noise = canvas.noise(36, 14)
        count = min(120, max(24, round(34 * canvas.width / canvas.height)))
        self.particles = [(canvas.rng.random(), canvas.rng.uniform(.18, .91), canvas.rng.uniform(0, tau),
                           canvas.rng.random(), canvas.rng.uniform(.0013, .0044))
                          for _ in range(count)]

    def frame(self, effects, base, time):
        layer = base.copy() if base is not None else self.canvas.transparent()
        for index, effect in enumerate(effects):
            power = effect.strength.at(time)
            if power > 0:
                angle = tau * (time % 1) * effect.cycles
                if effect.name not in ("particles", "wave"):
                    angle += index * pi * .48
                scale = effect.scale.at(time)
                if effect.name in ("reflection", "moonlight"):
                    if self.lake is None:
                        raise ValueError(f"{effect.name} requires a scene with a lake")
                    if effect.name == "reflection":
                        reflect(self.canvas, layer, angle, power, scale, self.lake)
                    else:
                        moonlight(self.canvas, layer, angle, power, scale, self.lake, self.noise, effect.color)
                else:
                    PAINTERS[effect.name](self.canvas, layer, angle, power, scale,
                                          effect.color, effect.secondary, self.noise, self.particles)
        return layer
