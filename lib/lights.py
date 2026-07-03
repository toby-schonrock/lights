import atexit
import threading
import time
from typing import Iterator

from .artnetcontroller import ArtNetController

__all__ = ["panels", "overheads", "moving_heads", "reset", "send_dmx"]


def _clamp255(val: int):
    return max(0, min(255, int(val)))


class Panel:
    """
    3 Channel Panel. 
    All properties are 0-255.
    """

    def __init__(self, channel: int):
        if not (1 <= channel <= 509):
            raise ValueError("DMX starting channel must be between 1 and 512.")

        self.__channel = channel
        self.reset()

    def reset(self):
        self.setLight(0, 0, 0)

    def setLight(self, r: int, g: int, b: int):
        self.r = _clamp255(r)
        self.g = _clamp255(g)
        self.b = _clamp255(b)

    def _apply(self, dmx_data: list[int]):
        '''Called when creating dmx packet'''
        dmx_data[self.__channel - 1] = _clamp255(self.r)
        dmx_data[self.__channel + 0] = _clamp255(self.g)
        dmx_data[self.__channel + 1] = _clamp255(self.b)


class Overhead:
    """
    4 Channel Overhead lamp. 
    All properties are 0-255.
    """

    def __init__(self, channel: int):
        if not (1 <= channel <= 508):
            raise ValueError("DMX starting channel must be between 1 and 512.")

        self.__channel = channel
        self.brightness = 0
        '''Brightness 0-255'''
        self.strobe = 0
        '''
        More = faster, 0 disabled, 255 max.\n
        If enabled brightness ignored
        '''
        self.reset()

    def reset(self):
        self.setLight(0, 0, 0, 0)

    def setLight(self, r: int, g: int, b: int, brightness: int = 255, strobe: int = 0):
        """
        Sets r,g,b, brigthness and strobe 0-255.
        If strobe is set to anything other than 0 brightness will be set to 255
        """
        self.r = _clamp255(r)
        self.g = _clamp255(g)
        self.b = _clamp255(b)
        if strobe:
            brightness = 255

        self.brightness = _clamp255(brightness)
        self.strobe = _clamp255(strobe)

    def _apply(self, dmx_data: list[int]):
        '''Called when creating dmx packet'''
        dmx_data[self.__channel - 1] = _clamp255(self.r)
        dmx_data[self.__channel + 0] = _clamp255(self.g)
        dmx_data[self.__channel + 1] = _clamp255(self.b)

        self.strobe = max(0, min(255, int(self.strobe)))
        self.brightness = max(0, min(255, int(self.brightness)))

        value = 0
        if self.strobe > 0:
            self.brightness = 255  # should be anyway
            # strobe values 190 to 250 incl.
            value = round(self.strobe * 60 / 255)
            value = 190 + value
        else:
            # project brightness onto rest of range
            value = round(self.brightness * 195 / 255)
            if value >= 190:
                value += 60

        dmx_data[self.__channel + 2] = _clamp255(value)


class MovingHead:
    """
    Moving head in 9 channel mode. 
    All properties are 0-255.
    """

    def __init__(self, channel: int):
        if not (1 <= channel <= 503):
            raise ValueError("DMX starting channel must be between 1 and 512.")

        self.channel = channel

        self.brightness = 0
        '''Brightness 0-255'''

        self.strobe = 0
        '''
        More = faster, 0 disabled, 255 max.\n
        If enabled brightness ignored
        '''

        self.pan = 0
        '''
        255 = 1.5 rotations
        0 = left
        '''

        self.speed = 0
        '''0 slow, 255 fast'''

        self.reset()

    def reset(self):
        self.setLight(0, 0, 0, 0, 0)
        self.setDir(42, 15)
        self.speed = 150

    def setLight(self, r: int, g: int, b: int, w: int = 0, brightness: int = 255, strobe: int = 0):
        """
        Sets r,g,b,w, brigthness and strobe 0-255.
        If strobe is set to anything other than 0 brightness will be set to 255
        """
        self.r = _clamp255(r)
        self.g = _clamp255(g)
        self.b = _clamp255(b)
        self.w = _clamp255(w)
        if strobe:
            brightness = 255

        self.brightness = _clamp255(brightness)
        self.strobe = _clamp255(strobe)

    def setDir(self, pan: int, tilt: int):
        self.pan = _clamp255(pan)
        self.tilt = _clamp255(tilt)

    def _apply(self, dmx_data: list[int]):
        '''Called when creating dmx packet'''
        dmx_data[self.channel - 1] = _clamp255(self.pan)
        dmx_data[self.channel + 0] = _clamp255(self.tilt)

        # brightness/strobe
        self.strobe = max(0, min(255, int(self.strobe)))
        self.brightness = max(0, min(255, int(self.brightness)))

        ch3val = 0
        if self.strobe > 0:
            self.brightness = 255  # should be anyway
            # strobe values 135 - 239 incl.
            ch3val = 135 + round(self.strobe * 104 / 255)
        else:
            # project brightness onto range 8 - 134 incl.
            ch3val = 8 + round(self.brightness * 126 / 255)

        dmx_data[self.channel + 1] = _clamp255(ch3val)

        dmx_data[self.channel + 2] = _clamp255(self.r)
        dmx_data[self.channel + 3] = _clamp255(self.g)
        dmx_data[self.channel + 4] = _clamp255(self.b)
        dmx_data[self.channel + 5] = _clamp255(self.w)

        # speed is inverted
        dmx_data[self.channel + 6] = 255 - _clamp255(self.speed)


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


__controller = ArtNetController(target_ip="192.168.1.169")

panels = _panels()
overheads = _overheads()
moving_heads = _moving_heads()


def reset():
    '''resets all lights to default state'''
    panels.reset()
    overheads.reset()
    moving_heads.reset()


def send_dmx():
    """pushes the current state to the controller"""
    data = [0] * 512
    for panel in panels:
        panel._apply(data)

    for overhead in overheads:
        overhead._apply(data)

    for head in moving_heads:
        head._apply(data)

    __controller.buffer = data
    __controller.flush_buffer()


def __start_dmx_stream(ms_interval: int = 25):
    def loop():
        interval = ms_interval / 1000.0
        next_frame = time.monotonic()

        while not stop_event.is_set():
            send_dmx()

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
        f"State is being transmitted over artnet to the controller every {ms_interval}ms")

    # Return the trigger to pass directly into your atexit handler
    return stop_event.set


__stop_dmx = __start_dmx_stream()


def __close():
    __stop_dmx()
    __controller.close()


atexit.register(__close)
