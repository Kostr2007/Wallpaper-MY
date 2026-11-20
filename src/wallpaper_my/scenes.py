"""Paint the panoramic scenery and the surfaces that receive light."""

from dataclasses import dataclass
from math import cos, pi, sin

import numpy as np
from PIL import Image, ImageChops, ImageDraw

from .paint import bell


@dataclass(frozen=True)
class Lake:
    horizon: float
    water: Image.Image
    mountains: Image.Image


@dataclass(frozen=True)
class SceneArt:
    layers: dict[str, Image.Image]
    lake: Lake | None = None


def aurora(c):
    x, y = c.x, c.y
    w, h = c.size
    mist = c.noise(18, 10)
    glow = bell(x + .23, .75) * bell(y - .49, .36)
    sky = c.tones(y * .74 + .27 * glow + .014 * c.grain(),
                  (0, "#0c102e"), (.28, "#222353"), (.55, "#354777"), (1, "#648b9e"))
    moon_x, moon_y = x[0, int(w * .74)], .27
    radius = np.hypot(x - moon_x, y - moon_y)
    c.wash(sky, "#c1c4f3", .14 * bell(radius, .12))
    c.wash(sky, "#efddef", np.clip((.059 - radius) * h, 0, 1) * (.87 + .10 * mist))
    stars = c.transparent()
    dots = ImageDraw.Draw(stars)
    for _ in range(round(240 * w / h)):
        px, py = c.rng.uniform(0, w), c.rng.uniform(0, .57 * h)
        size = max(.6, c.rng.uniform(.35, 1.25) * h / 720)
        dots.ellipse((px - size, py - size, px + size, py + size),
                     fill=(*c.color("#d2def7"), int(c.rng.integers(28, 165))))
    sky.alpha_composite(stars)

    horizon = .574
    distance = np.maximum(y - horizon, 0)
    grain = c.noise(96, 8)
    water_tone = .62 - .62 * distance + .045 * mist + .012 * grain + c.grain() * .012
    lake = c.tones(water_tone, (0, "#10172e"), (.52, "#23334d"), (.84, "#455d74"),
                   alpha=np.clip((y - horizon) * h, 0, 1))
    mountains = c.transparent()
    contour = c.noise(29, 23)
    rock_detail = c.noise(130, 87)
    for index, (base, lift, dark, bright) in enumerate([
        (.535, .028, "#323c65", "#889db0"), (.574, .060, "#202646", "#637196"),
        (.625, .133, "#151a37", "#4f5b80"),
    ]):
        edge = base - lift * (1.1 - bell(x + .03, .55)) + c.ridge(15 - index * 3, .058 + .019 * index)
        below = y - edge
        strata = np.sin(x * (88 + index * 21) + y * (64 - index * 13) + 5 * contour)
        cracks = np.abs(strata) ** 3 * (.095 + .085 * rock_detail)
        facet = np.tanh(np.gradient(edge[0]) * w * .13)
        value = .25 + (.39 + .17 * facet) * bell(below, .055) + .21 * contour
        value += .13 * rock_detail - cracks + c.grain() * .014
        fade = np.clip((.61 + .012 * index - y) * 100, 0, 1)
        mountain = c.tones(value, (0, dark), (.98, bright),
                           alpha=np.clip(below * h, 0, 1) * fade)
        mountains.alpha_composite(mountain)
    mountain_alpha = mountains.getchannel("A")
    water = ImageChops.multiply(lake.getchannel("A"), ImageChops.invert(mountain_alpha))
    lake.alpha_composite(mountains)

    shore = .975 - .14 * bell(x + .98, .49) - .25 * bell(x - .95, .53) + c.ridge(17, .027)
    land = c.tones(.43 + .17 * mist + .12 * contour - .29 * y + .013 * c.grain(),
                   (0, "#0b142b"), (.52, "#314361"), alpha=np.clip((y - shore) * h, 0, 1))
    trees = ImageDraw.Draw(land)
    for pos in sorted(c.rng.uniform(0, w - 1, round(115 * w / h))):
        ground = shore[0, int(pos)]
        if ground > .943:
            continue
        length = c.rng.uniform(.024, .115) * h * (1 + .8 * (ground - .7))
        base = ground * h + length * .25
        top = base - length
        color = ["#121d32", "#18243d", "#24354e"][int(c.rng.integers(0, 3))]
        c.stroke(trees, [(pos, base), (pos, top)], color, weight=2)
        for level in np.linspace(.12, .91, 14):
            py = top + length * level
            span = length * (.04 + .19 * level) * c.rng.uniform(.6, 1.1)
            trees.polygon([(pos, py - length * .10), (pos - span, py + length * .065),
                           (pos - span * .27, py + length * .044), (pos, py + length * .094),
                           (pos + span * .9, py + length * .085)], fill=(*c.color(color), 255))
    return SceneArt({"background": sky, "middle": lake, "foreground": land},
                    Lake(horizon, water, mountain_alpha))


def dunes(c):
    x, y = c.x, c.y
    haze = c.noise(24, 13)
    silky = c.noise(53, 22)
    glow = bell(x - .33, .54) * bell(y - .48, .40)
    sky = c.tones(y * .83 + glow * .36 + c.grain() * .012,
                  (0, "#332d58"), (.27, "#845a83"), (.55, "#cf8488"), (1, "#f9c69a"))
    distance = np.hypot(x - .31 * min(1, c.width / c.height), y - .37)
    c.wash(sky, "#ffd5ae", .38 * bell(distance, .28))
    c.wash(sky, "#ffe8bd", np.clip((.112 - distance) * c.height, 0, 1) * .96)
    c.wash(sky, "#f3aa89", np.clip((.112 - distance) * c.height, 0, 1) * .35 * bell(y - .464, .07))
    clouds = c.transparent()
    for index, (altitude, color) in enumerate([(.25, "#c398ac"), (.38, "#efada6"), (.52, "#ffcea9"), (.60, "#ffd6ad")]):
        curve = altitude + .065 * np.sin(3.3 * x + index) - .029 * x
        density = np.clip(.34 + c.noise(15, 61) * .65 + .45 * haze, 0, 1)
        c.wash(clouds, color, .49 * bell(y - curve, .012 + .013 * index) * density * bell(x + .25, 1.2))

    middle, foreground = c.transparent(), c.transparent()
    ramps = [
        (.63, .035, 2.3, "#776380", "#bc8597", "#f6bfab"),
        (.69, .075, 3.6, "#85536e", "#cc8b88", "#f7bc9d"),
        (.78, .116, .6, "#703e60", "#bf706d", "#f7b287"),
        (.87, .157, 4.7, "#462d50", "#a35d72", "#e89678"),
        (1.04, .185, 1.8, "#372744", "#854b63", "#cd8172"),
    ]
    for index, (level, amplitude, phase, shadow, warm, bright) in enumerate(ramps):
        crest = level + amplitude * np.sin(x * (3.3 + .17 * index) + phase)
        crest += .018 * np.sin(x * 9 + phase) + .044 * x
        delta = y - crest
        surface = np.maximum(delta, 0)
        ripple = np.sin(64 * np.log1p(surface * 11) + 11 * x + 2.2 * haze + .35 * silky)
        slope = .55 + .28 * np.cos(x * 3.2 + phase - 4.2 * surface)
        texture = (.025 + .047 * np.clip(surface * 5, 0, 1)) * ripple
        value = slope + .45 * bell(delta, .011 + .009 * index) - .20 * bell(delta - .063, .055)
        value += texture + .054 * silky + .024 * c.grain()
        layer = c.tones(value, (0, shadow), (.47, warm), (1.03, bright),
                        alpha=np.clip(delta * c.height, 0, 1))
        (middle if index < 3 else foreground).alpha_composite(layer)
    return SceneArt({"background": sky, "atmosphere": clouds, "middle": middle, "foreground": foreground})


def garden(c):
    x, y = c.x, c.y
    w, h = c.size
    swell = c.noise(15, 14)
    fine = c.noise(52, 34)
    glow = bell(x + .15, .56) * bell(y - .08, .51)
    sea = c.tones(.86 * (1 - y) + .24 * glow + .043 * swell + .014 * c.grain(),
                  (0, "#171c43"), (.34, "#1b3359"), (.71, "#3e7b8f"), (1.12, "#ade7db"))
    reef = c.transparent()
    for index, (level, dark, bright) in enumerate([
        (.75, "#23345b", "#4c6c89"), (.85, "#26284f", "#565781"), (.99, "#1b1e42", "#3c466c"),
    ]):
        line = level + c.ridge(7 + index * 3, .096) - .115 * bell(x - .93, .57)
        delta = y - line
        rock = .35 + .27 * swell + .18 * fine + .23 * bell(delta, .11) + .023 * c.grain()
        reef.alpha_composite(c.tones(rock, (0, dark), (1, bright), alpha=np.clip(delta * h, 0, 1)))

    plants = c.transparent()
    draw = ImageDraw.Draw(plants)
    for index, position in enumerate(np.linspace(.01, .99, max(15, round(w / h * 14)))):
        px = position * w
        outer = np.clip(2.8 * abs(position - .5), .13, 1)
        base = h * c.rng.uniform(.91, 1.08)
        groves = bell(position - .23, .083) + bell(position - .79, .085)
        length = (c.rng.uniform(.12, .54) * outer + .27 * groves) * h
        sway = c.rng.uniform(-.10, .10) * h * outer
        amplitude = c.rng.uniform(.012, .046) * h
        bend = c.rng.uniform(0, 2 * pi)
        left, right, spine = [], [], []
        for step in np.linspace(0, 1, 65):
            center = px + sway * step + .095 * length * sin(step * 6 + bend) * step
            py = base - length * step
            width = amplitude * sin(pi * step) * (.55 + .45 * cos(17 * step + bend))
            spine.append((center, py))
            left.append((center - width, py))
            right.append((center + width, py))
        color = ("#263958", "#2c4561", "#355e71", "#394d6e")[int(c.rng.integers(0, 4))]
        if length > .20 * h:
            for i in range(19, 60, 5):
                pos_x, pos_y = spine[i]
                taper = .64 + .36 * sin(pi * i / 64)
                side = -1 if (i + index) % 2 else 1
                span = length * taper * (.15 + .045 * sin(i + bend))
                dx, dy = side * span, -span * (.63 + .35 * i / 64)
                tips = [(pos_x, pos_y), (pos_x + dx * .40, pos_y + dy * .62),
                        (pos_x + dx * .79, pos_y + dy * .89), (pos_x + dx, pos_y + dy),
                        (pos_x + dx * .64, pos_y + dy * .36), (pos_x + dx * .29, pos_y + dy * .21)]
                draw.polygon(tips, fill=(*c.color(color), 255))
                c.stroke(draw, [tips[0], (pos_x + .53 * dx, pos_y + .52 * dy), tips[3]],
                         "#527e86", opacity=182)
        draw.polygon(left + right[::-1], fill=(*c.color(color), 255))
        c.stroke(draw, spine[2:-5], "#668e96", opacity=171)
        for i in range(7, 58, 4):
            c.stroke(draw, [left[i], spine[i - 4], right[i]], "#58718e", opacity=120)

    corals = c.transparent()
    draw = ImageDraw.Draw(corals)
    for center, base in [(.15, .97), (.28, 1.03), (.71, 1.04), (.86, .98), (.96, .94)]:
        px, py = center * w, base * h
        count = int(c.rng.integers(9, 15))
        for direction in np.linspace(-1.1, 1.1, count):
            length = h * c.rng.uniform(.08, .22)
            branch = [(px + sin(direction) * length * t**1.25,
                       py - cos(direction) * length * t) for t in np.linspace(0, 1, 13)]
            c.stroke(draw, branch, "#674a7b", weight=2.5)
            for bx, by in branch[3:]:
                span = length * c.rng.uniform(.10, .23)
                for sign in (-1, 1):
                    tip = bx + span * sign, by - span * .76
                    c.stroke(draw, [(bx, by), (bx + span * sign * .63, by - span * .40), tip],
                             "#9b79a9", opacity=235)
                    r = max(.6, .0013 * h)
                    draw.ellipse((tip[0] - r, tip[1] - r, tip[0] + r, tip[1] + r),
                                 fill=(*c.color("#e4accd"), 230))

    return SceneArt({"background": sea, "middle": reef, "surface": plants, "foreground": corals})
