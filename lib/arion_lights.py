from collections.abc import Iterator
from dataclasses import dataclass
from enum import Enum
from typing import NewType

SAFEVALUES = True
"""
If true then descriptors are used to force dmx values to ints between 0-255.
If false then they can be whatever, but this is faster if you enforce yourself.
"""

DmxValue = NewType("DmxValue", int)

def _dmx_value(value: int) -> DmxValue:
    return DmxValue(max(0, min(255, int(value))))


class DmxByte:
    """Descriptor for a value clamped to the DMX range."""

    def __set_name__(self, owner, name: str) -> None:
        self.storage_name = f"_{name}"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return getattr(instance, self.storage_name, DmxValue(0))

    def __set__(self, instance, value: int) -> None:
        setattr(instance, self.storage_name, _dmx_value(value))


class LightMode(Enum):
    BRIGHTNESS = "brightness"
    STROBE = "strobe"


@dataclass(frozen=True)
class LightState:
    mode: LightMode
    value: DmxValue

    def __post_init__(self) -> None:
        if not isinstance(self.mode, LightMode):
            raise TypeError("mode must be a LightMode")
        object.__setattr__(self, "value", _dmx_value(self.value))

    @classmethod
    def brightness(cls, value: int) -> "LightState":
        return cls(LightMode.BRIGHTNESS, _dmx_value(value))

    @classmethod
    def strobe(cls, value: int) -> "LightState":
        return cls(LightMode.STROBE, _dmx_value(value))


class LightStateField:
    """Descriptor that accepts only a LightState."""

    def __set_name__(self, owner, name: str) -> None:
        self.storage_name = f"_{name}"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return getattr(instance, self.storage_name, LightState.brightness(255))

    def __set__(self, instance, value: LightState) -> None:
        if not isinstance(value, LightState):
            raise TypeError("value must be a LightState")
        setattr(instance, self.storage_name, value)


class Panel:
    """
    3 Channel (RGB) Panel.
    """
    if SAFEVALUES:
        r = DmxByte()
        g = DmxByte()
        b = DmxByte()

    def __init__(
        self, name: str, channel: int, position: tuple[float, float, float], is_vertical: bool
    ):
        if not (1 <= channel <= 509):
            raise ValueError("DMX starting channel must be between 1 and 512.")

        if not SAFEVALUES:
            self.r = 0
            self.g = 0
            self.b = 0
        
        self.name = name
        self.channel = channel
        self.position = position
        self.is_vertical = is_vertical

    def reset(self):
        self.setLight(0, 0, 0)

    def setLight(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b

    def _apply(self, dmx_data: list[int]):
        """Called when creating dmx packet"""
        dmx_data[self.channel - 1] = self.r
        dmx_data[self.channel + 0] = self.g
        dmx_data[self.channel + 1] = self.b


class Overhead:
    """
    4 Channel Overhead lamp.
    """

    if SAFEVALUES:
        r = DmxByte()
        g = DmxByte()
        b = DmxByte()
        brightness_strobe = LightStateField()

    def __init__(self, channel: int):
        if not (1 <= channel <= 509):
            raise ValueError("DMX starting channel must be between 1 and 509.")

        if not SAFEVALUES:
            self.r = 0
            self.g = 0
            self.b = 0
            self.brightness_strobe = LightState.brightness(0)
        
        self.channel = channel

    def reset(self):
        self.setLight(0, 0, 0)

    def setLight(self, r: int, g: int, b: int, brightness_strobe: LightState = None):
        if brightness_strobe is None:  # defualt value
            brightness_strobe = LightState.brightness(255)

        self.r = r
        self.g = g
        self.b = b
        self.brightness_strobe = brightness_strobe

    def _apply(self, dmx_data: list[int]):
        """Called when creating dmx packet"""
        dmx_data[self.channel - 1] = self.r
        dmx_data[self.channel + 0] = self.g
        dmx_data[self.channel + 1] = self.b

        value = 0
        bs = self.brightness_strobe
        if bs.mode is LightMode.STROBE:
            # strobe values 190 to 250 incl.
            value = 190 + round(bs.value * 60 / 255)
        else:
            # project brightness onto rest of range
            value = round(bs.value * 194 / 255)
            if value >= 190:
                value += 61

        dmx_data[self.channel + 2] = value


class MovingHead:
    """
    Moving head in 9 channel mode.
    """

    if SAFEVALUES:
        r = DmxByte()
        g = DmxByte()
        b = DmxByte()
        w = DmxByte()
        brightness_strobe = LightStateField()
        pan = DmxByte()
        """
            0 = left
            255 = right (1.5 rotations)
        """
        tilt = DmxByte()
        speed = DmxByte()

    def __init__(self, channel: int, position: tuple[float, float, float]):
        if not (1 <= channel <= 503):
            raise ValueError("DMX starting channel must be between 1 and 512.")

        if not SAFEVALUES:
            self.r = 0
            self.g = 0
            self.b = 0
            self.w = 0
            self.brightness_strobe = LightState.brightness(0)
            self.pan = 0
            """
                0 = left
                255 = right (1.5 rotations)
            """
            self.tilt = 0
            self.speed = 0
        
        self.channel = channel
        self.position = position
        self.reset()

    def reset(self):
        self.setLight(0, 0, 0)
        self.setDir(42, 15)
        self.speed = 255

    def setLight(
        self, r: int, g: int, b: int, w: int = 0, brightness_strobe: LightState = None
    ):
        if brightness_strobe is None:  # defualt value
            brightness_strobe = LightState.brightness(255)

        self.r = r
        self.g = g
        self.b = b
        self.w = w
        self.brightness_strobe = brightness_strobe

    def setDir(self, pan: int, tilt: int):
        self.pan = pan
        self.tilt = tilt

    def _apply(self, dmx_data: list[int]):
        """Called when creating dmx packet"""
        dmx_data[self.channel - 1] = self.pan
        dmx_data[self.channel + 0] = self.tilt

        value = 0
        bs = self.brightness_strobe
        if bs.mode is LightMode.STROBE:
            # strobe values 135 - 239 incl.
            value = 135 + round(bs.value * 104 / 255)
        else:
            # project brightness onto range 8 - 134 incl.
            value = 8 + round(bs.value * 126 / 255)

        dmx_data[self.channel + 1] = value
        dmx_data[self.channel + 2] = self.r
        dmx_data[self.channel + 3] = self.g
        dmx_data[self.channel + 4] = self.b
        dmx_data[self.channel + 5] = self.w

        # speed is inverted
        dmx_data[self.channel + 6] = 255 - self.speed

WALL_TO_WALL = 3.9
CENTER_BETWEEN_WALLS = 0 # in the coord system
LEFT_WALL_X = -1.95
RIGHT_WALL_X = 1.95

class _panels:
    def __init__(self):
        # left side
        self.a = Panel("a", 129, (LEFT_WALL_X, 0.90, 2.90), True)
        self.b = Panel("b", 168, (LEFT_WALL_X, 1.76, 2.86), True)
        self.c = Panel("c", 135, (LEFT_WALL_X, 2.70, 2.96), False)
        self.d = Panel("d", 165, (LEFT_WALL_X, 3.62, 2.95), True)
        self.e = Panel("e", 141, (LEFT_WALL_X, 2.60, 2.15), False)
        self.f = Panel("f", 144, (LEFT_WALL_X, 3.59, 2.14), False)
        self.g = Panel("g", 147, (LEFT_WALL_X, 1.63, 1.59), True)
        self.h = Panel("h", 159, (LEFT_WALL_X, 2.43, 1.38), False)
        self.i = Panel("i", 150, (LEFT_WALL_X, 3.47, 1.38), False)

        # right side
        self.m = Panel("m", 156, (RIGHT_WALL_X, 3.54, 3.00), False)
        self.n = Panel("n", 162, (RIGHT_WALL_X, 2.68, 2.98), True)
        self.o = Panel("o", 180, (RIGHT_WALL_X, 1.80, 3.05), False)
        self.p = Panel("p", 153, (RIGHT_WALL_X, 0.90, 3.00), True)
        self.q = Panel("q", 132, (RIGHT_WALL_X, 3.42, 2.28), False)
        self.r = Panel("r", 171, (RIGHT_WALL_X, 1.96, 2.29), False)
        self.s = Panel("s", 174, (RIGHT_WALL_X, 0.70, 2.14), False)
        self.t = Panel("t", 177, (RIGHT_WALL_X, 3.56, 1.49), False)
        self.u = Panel("u", 138, (RIGHT_WALL_X, 2.67, 1.55), True)
        self.v = Panel("v", 183, (RIGHT_WALL_X, 1.78, 1.54), False)

        self._ordered = [
            self.a,
            self.b,
            self.c,
            self.d,
            self.e,
            self.f,
            self.g,
            self.h,
            self.i,
            self.m,
            self.n,
            self.o,
            self.p,
            self.q,
            self.r,
            self.s,
            self.t,
            self.u,
            self.v,
        ]

    def __iter__(self) -> Iterator[Panel]:
        return iter(self._ordered)

    def __len__(self) -> int:
        return len(self._ordered)

    def __getitem__(self, index: int) -> Panel:
        return self._ordered[index]

    def reset(self):
        for p in self._ordered:
            p.reset()


class _overheads:
    def __init__(self):
        self.far_right = Overhead(1)
        self.mid_right = Overhead(17)
        self.mid_left = Overhead(33)
        self.far_left = Overhead(49)

        self._ordered = [self.far_right, self.mid_right, self.mid_left, self.far_left]

    def __iter__(self) -> Iterator[Overhead]:
        return iter(self._ordered)

    def __len__(self) -> int:
        return len(self._ordered)

    def __getitem__(self, index: int) -> Overhead:
        return self._ordered[index]

    def reset(self):
        for o in self._ordered:
            o.reset()

MOVING_HEADS_Z = 2.5
class _moving_heads:
    def __init__(self):
        self.far_right = MovingHead(401, (RIGHT_WALL_X - 0.63, 0, MOVING_HEADS_Z))
        # self.mid_right = MovingHead(415) # currently broken so not used
        self.close_right = MovingHead(429, (RIGHT_WALL_X - 1.75, 0, MOVING_HEADS_Z))
        self.close_left = MovingHead(443, (LEFT_WALL_X + 1.34, 0, MOVING_HEADS_Z))
        self.mid_left = MovingHead(457, (LEFT_WALL_X + 0.78, 0, MOVING_HEADS_Z))
        self.far_left = MovingHead(471, (LEFT_WALL_X + 0.23, 0, MOVING_HEADS_Z))

        self._ordered = [
            self.far_right,
            # self.mid_right,
            self.close_right,
            self.close_left,
            self.mid_left,
            self.far_left,
        ]

    def __iter__(self) -> Iterator[MovingHead]:
        return iter(self._ordered)

    def __len__(self) -> int:
        return len(self._ordered)

    def __getitem__(self, index: int) -> MovingHead:
        return self._ordered[index]

    def reset(self):
        for m in self._ordered:
            m.reset()


class LightConfig:
    """
    A class to act as an api between lighting and dmx channel values.
    Set the values of the children as you wish and call get channel values to generate
    DMX channels.
    """

    def __init__(self):
        self.panels = _panels()
        self.overheads = _overheads()
        self.moving_heads = _moving_heads()

    def copy(self) -> "LightConfig":
        """Creates a copy of the light config. Faster than deepcopy"""
        new = LightConfig()
        for newp, selfp in zip(new.panels, self.panels):
            newp.setLight(selfp.r, selfp.g, selfp.b)

        for newo, selfo in zip(new.overheads, self.overheads):
            newo.setLight(selfo.r, selfo.g, selfo.b, selfo.brightness_strobe)

        for newm, selfm in zip(new.moving_heads, self.moving_heads):
            newm.setLight(selfm.r, selfm.g, selfm.b, selfm.w, selfm.brightness_strobe)

        return new

    def reset(self):
        """resets all lights to default state"""
        self.panels.reset()
        self.overheads.reset()
        self.moving_heads.reset()

    def get_channel_values(self):
        """
        Generates the 512 0-225 channel values representing the current state
        """
        data = [0] * 512
        for panel in self.panels:
            panel._apply(data)

        for overhead in self.overheads:
            overhead._apply(data)

        for head in self.moving_heads:
            head._apply(data)

        if not SAFEVALUES:
            data = [_dmx_value(d) for d in data]

        return data
