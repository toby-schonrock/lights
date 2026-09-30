import atexit
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from enum import Enum
from typing import NewType

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

    r = DmxByte()
    g = DmxByte()
    b = DmxByte()

    def __init__(self, channel: int):
        if not (1 <= channel <= 509):
            raise ValueError("DMX starting channel must be between 1 and 512.")

        self.channel = channel

    def reset(self):
        self.setLight(0, 0, 0)

    def setLight(self, r: int, g: int, b: int):
        self.r = r
        self.g = g
        self.b = b

    def _apply(self, dmx_data: list[int]):
        '''Called when creating dmx packet'''
        dmx_data[self.channel - 1] = self.r
        dmx_data[self.channel + 0] = self.g
        dmx_data[self.channel + 1] = self.b


class Overhead:
    """
    4 Channel Overhead lamp. 
    """

    r = DmxByte()
    g = DmxByte()
    b = DmxByte()
    brightness_strobe = LightStateField()

    def __init__(self, channel: int):
        if not (1 <= channel <= 509):
            raise ValueError("DMX starting channel must be between 1 and 509.")

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
        '''Called when creating dmx packet'''
        dmx_data[self.channel - 1] = self.r
        dmx_data[self.channel + 0] = self.g
        dmx_data[self.channel + 1] = self.b

        value = 0
        if self.brightness_strobe.mode is LightMode.STROBE:
            # strobe values 190 to 250 incl.
            value = 190 + round(self.brightness_strobe.value * 60 / 255)
        else:
            # project brightness onto rest of range
            value = round(self.brightness_strobe.value * 194 / 255)
            if value >= 190:
                value += 61

        dmx_data[self.channel + 2] = value


class MovingHead:
    """
    Moving head in 9 channel mode.
    """

    r = DmxByte()
    g = DmxByte()
    b = DmxByte()
    w = DmxByte()
    pan = DmxByte()
    '''
        0 = left
        255 = right (1.5 rotations)
    '''
    tilt = DmxByte()
    speed = DmxByte()
    brightness_strobe = LightStateField()

    def __init__(self, channel: int):
        if not (1 <= channel <= 503):
            raise ValueError("DMX starting channel must be between 1 and 512.")

        self.channel = channel
        self.reset()

    def reset(self):
        self.setLight(0, 0, 0)
        self.setDir(42, 15)
        self.speed = 150

    def setLight(self, r: int, g: int, b: int, w: int = 0, brightness_strobe: LightState = None):
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
        '''Called when creating dmx packet'''
        dmx_data[self.channel - 1] = self.pan
        dmx_data[self.channel + 0] = self.tilt

        value = 0
        if self.brightness_strobe.mode is LightMode.STROBE:
            # strobe values 135 - 239 incl.
            value = 135 + round(self.brightness_strobe.value * 104 / 255)
        else:
            # project brightness onto range 8 - 134 incl.
            value = 8 + round(self.brightness_strobe.value * 126 / 255)

        dmx_data[self.channel + 1] = value
        dmx_data[self.channel + 2] = self.r
        dmx_data[self.channel + 3] = self.g
        dmx_data[self.channel + 4] = self.b
        dmx_data[self.channel + 5] = self.w

        # speed is inverted
        dmx_data[self.channel + 6] = 255 - self.speed


class _panels:
    a = Panel(129)
    b = Panel(132)
    c = Panel(135)
    d = Panel(138)
    e = Panel(141)
    f = Panel(144)
    g = Panel(147)
    h = Panel(150)
    i = Panel(153)
    m = Panel(156)
    n = Panel(159)
    o = Panel(162)
    p = Panel(165)
    q = Panel(168)
    r = Panel(171)
    s = Panel(174)
    t = Panel(177)
    u = Panel(180)
    v = Panel(183)

    _ordered = [a, b, c, d, e, f, g, h, i, m, n, o, p, q, r, s, t, u, v]

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
    far_right = Overhead(1)
    mid_right = Overhead(17)
    mid_left = Overhead(33)
    far_left = Overhead(49)

    _ordered = [far_right, mid_right, mid_left, far_left]

    def __iter__(self) -> Iterator[Overhead]:
        return iter(self._ordered)

    def __len__(self) -> int:
        return len(self._ordered)

    def __getitem__(self, index: int) -> Overhead:
        return self._ordered[index]

    def reset(self):
        for o in self._ordered:
            o.reset()


class _moving_heads:
    far_right = MovingHead(401)
    mid_right = MovingHead(415)
    close_right = MovingHead(429)
    close_left = MovingHead(443)
    mid_left = MovingHead(457)
    far_left = MovingHead(471)

    _ordered = [
        far_right,
        mid_right,
        close_right,
        close_left,
        mid_left,
        far_left,
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


panels = _panels()
overheads = _overheads()
moving_heads = _moving_heads()


def reset():
    '''resets all lights to default state'''
    panels.reset()
    overheads.reset()
    moving_heads.reset()


def get_channel_values():
    """
    Generates the 512 0-225 channel values representing the current state
    """
    data = [0] * 512
    for panel in panels:
        panel._apply(data)

    for overhead in overheads:
        overhead._apply(data)

    for head in moving_heads:
        head._apply(data)

    return data


def spawn_update_thread(callback: Callable[[list[int]], None], ms_interval: int = 25) -> Callable[[], None]:
    """
    Starts a thread which calls the callback with the channel values every ms_interval ms.
    Returns a callable to kill the thread.
    """
    def loop():
        interval = ms_interval / 1000.0
        next_frame = time.monotonic()

        while not stop_event.is_set():
            callback(get_channel_values())

            next_frame += interval
            delay = next_frame - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            else:
                next_frame = time.monotonic()  # System lag recovery

    stop_event = threading.Event()
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()

    print(
        f"Callback being called with channel values every {ms_interval}ms")

    # Setup that thread will be closed on exit
    atexit.register(stop_event.set)
    return stop_event.set
