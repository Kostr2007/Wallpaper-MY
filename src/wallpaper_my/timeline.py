"""Validate scene recipes and evaluate looping keyframes."""

from bisect import bisect_right
from dataclasses import dataclass
from math import floor
import re

PLANES = ("background", "atmosphere", "middle", "surface", "foreground", "particles")
EFFECTS = ("aurora", "haze", "caustics", "ripples", "particles", "wave", "bloom", "reflection")


def in_range(value, low, high):
    return type(value) in (int, float) and low <= value <= high


def fields(data, allowed, label):
    if not isinstance(data, dict):
        raise ValueError(f"{label} must be an object")
    if unknown := set(data) - set(allowed):
        raise ValueError(f"unknown {label} fields: {', '.join(sorted(unknown))}")


@dataclass(frozen=True)
class Curve:
    values: tuple[float, ...]
    times: tuple[float, ...] = ()
    easing: tuple[str, ...] = ()

    @classmethod
    def read(cls, value, low, high, label):
        if in_range(value, low, high):
            return cls((value,))
        fields(value, ("keys",), label)
        keys = value.get("keys")
        if not isinstance(keys, list) or not 2 <= len(keys) <= 32:
            raise ValueError(f"{label} expects 2–32 keyframes")
        times, values, easing = [], [], []
        for key in keys:
            if not isinstance(key, list) or len(key) not in (2, 3):
                raise ValueError(f"{label} expects [time, value, easing] keyframes")
            t, v = key[:2]
            mode = key[2] if len(key) == 3 else "smooth"
            if not in_range(t, 0, 1) or not in_range(v, low, high) or mode not in ("linear", "smooth", "hold"):
                raise ValueError(f"invalid time, value or easing for {label}")
            if times and t <= times[-1]:
                raise ValueError(f"{label} keyframe times must strictly increase")
            times.append(t)
            values.append(v)
            easing.append(mode)
        if times[0] != 0 or times[-1] != 1 or values[0] != values[-1]:
            raise ValueError(f"{label} must start at 0 and end at 1 with the same value")
        return cls(tuple(values), tuple(times), tuple(easing))

    def at(self, time):
        if not self.times:
            return self.values[0]
        time %= 1
        i = bisect_right(self.times, time) - 1
        amount = (time - self.times[i]) / (self.times[i + 1] - self.times[i])
        if self.easing[i] == "hold":
            return self.values[i]
        if self.easing[i] == "smooth":
            amount *= amount * (3 - 2 * amount)
        return self.values[i] + (self.values[i + 1] - self.values[i]) * amount


@dataclass(frozen=True)
class Effect:
    name: str
    strength: Curve
    scale: Curve
    cycles: int
    color: str | None
    secondary: str | None

    @classmethod
    def read(cls, data):
        fields(data, ("type", "strength", "scale", "cycles", "color", "secondary"), "effect")
        name = data.get("type")
        if name not in EFFECTS:
            raise ValueError(f"unknown effect {name!r}")
        cycles = data.get("cycles", 1)
        if type(cycles) is not int or not -4 <= cycles <= 4:
            raise ValueError("cycles must be an integer between -4 and 4")
        for key in ("color", "secondary"):
            color = data.get(key)
            if color is not None and (not isinstance(color, str) or not re.fullmatch(r"#[\da-fA-F]{6}", color, re.ASCII)):
                raise ValueError(f"{key} must be #RRGGBB")
        return cls(name, Curve.read(data.get("strength", 0.7), 0, 1, "strength"),
                   Curve.read(data.get("scale", 1), .3, 3, "scale"), cycles,
                   data.get("color"), data.get("secondary"))


@dataclass(frozen=True)
class Track:
    base: bool
    effects: tuple[Effect, ...]
    parallax: str
    light: str | None


@dataclass(frozen=True)
class Timeline:
    duration: float
    frames: int
    tracks: dict[str, Track]

    @classmethod
    def read(cls, data, presets):
        fields(data, ("preset", "duration", "fps", "tracks"), "recipe")
        preset = data.get("preset")
        if not isinstance(preset, str) or preset not in presets:
            raise ValueError(f"unknown recipe preset {preset!r}")
        duration, fps = data.get("duration"), data.get("fps")
        if not in_range(duration, 2, 120) or type(fps) is not int or not 1 <= fps <= 24:
            raise ValueError("duration must be 2–120 seconds and fps an integer between 1 and 24")
        frames = floor(duration * fps)
        if not 2 <= frames <= 144:
            raise ValueError("duration × fps must produce 2–144 frames")
        tracks = data.get("tracks")
        if not isinstance(tracks, dict) or not 1 <= len(tracks) <= 3:
            raise ValueError("expected one to three animated overlay tracks")
        parsed = {}
        for name, track in tracks.items():
            if name not in PLANES[1:]:
                raise ValueError(f"unknown overlay {name!r}")
            fields(track, ("base", "effects", "parallax", "light"), f"{name} track")
            base, effects = track.get("base", False), track.get("effects")
            if type(base) is not bool or not isinstance(effects, list) or not 1 <= len(effects) <= 8:
                raise ValueError(f"{name} must have a boolean base and one to eight effects")
            parallax = track.get("parallax", name)
            if parallax not in PLANES:
                raise ValueError(f"{name} has an unknown parallax anchor")
            light = track.get("light")
            if light is not None and (not isinstance(light, str) or light not in PLANES[:PLANES.index(name)]
                                      or light not in tracks):
                raise ValueError(f"{name} light must name an earlier animated plane")
            effects = tuple(Effect.read(effect) for effect in effects)
            if any(effect.name == "reflection" for effect in effects):
                if preset != "aurora-fjord" or name != "surface" or parallax not in ("middle", "surface"):
                    raise ValueError("reflection needs Aurora Fjord's surface track aligned with the lake")
            parsed[name] = Track(base, effects, parallax, light)
        for name, track in parsed.items():
            if track.light is not None and parsed[track.light].parallax != track.parallax:
                raise ValueError(f"{name} and {track.light} need the same parallax anchor")
        return preset, cls(duration, frames, parsed)


def pulse(low, high, peak=.5):
    return {"keys": [[0, low], [peak, high], [1, low]]}


RECIPES = {
    "aurora-fjord": {
        "preset": "aurora-fjord", "duration": 9, "fps": 15,
        "tracks": {
            "surface": {"effects": [
                {"type": "aurora", "strength": pulse(.79, .96, .48)},
                {"type": "bloom", "strength": .23, "scale": .85},
                {"type": "reflection", "strength": .77, "scale": .86},
            ]},
        },
    },
    "amber-dunes": {
        "preset": "amber-dunes", "duration": 8, "fps": 14,
        "tracks": {"atmosphere": {"effects": [
            {"type": "haze", "strength": pulse(.6, .89, .58)},
            {"type": "haze", "strength": .4, "scale": 1.7, "cycles": -1,
             "color": "#ffc699", "secondary": "#b47e9c"},
        ]}},
    },
    "tidal-garden": {
        "preset": "tidal-garden", "duration": 9.5, "fps": 15,
        "tracks": {
            "atmosphere": {"parallax": "surface", "effects": [
                {"type": "caustics", "strength": pulse(.63, .80, .48)},
                {"type": "particles", "strength": .56, "scale": .92},
            ]},
            "surface": {"base": True, "light": "atmosphere", "effects": [
                {"type": "wave", "strength": .94, "scale": .92},
            ]},
        },
    },
}
