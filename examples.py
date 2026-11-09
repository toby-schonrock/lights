import math
import time
import typing

import numpy as np

from lib.arion_lights import LightConfig, LightMode, LightState
from lib.scenes import FrameContext, Layer, Scene, SceneConfig


def arion_panels() -> LightConfig:
    # example background with arion lights
    lights = LightConfig()
    for panel in lights.panels:
        if panel.position[1] < 1.2:
            panel.setLight(0, 255, 0)
        elif panel.position[1] < 2:
            panel.setLight(255, 255, 255)
        else:
            panel.setLight(0, 0, 255)

    lights.overheads.mid_right.setLight(0, 0, 255, LightState.brightness(255))
    lights.overheads.mid_left.setLight(0, 255, 0, LightState.brightness(255))
    return lights


class RainbowPanels(Layer):
    def __init__(self, speed = 1):
        super().__init__()
        self.speed = speed

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights
        for panel in lights.panels:
            r = (math.sin((context.time + panel.position[0] * 0.5) * self.speed) + 1) / 2
            g = (math.sin((context.time + math.pi * 2/3 + panel.position[0] * 0.5) * self.speed) + 1) / 2
            b = (math.sin((context.time + math.pi * 4/3 + panel.position[0] * 0.5) * self.speed) + 1) / 2
            panel.setLight(r * 255, g * 255, b * 255)
        for overhead in lights.overheads:
            r = (math.sin((context.time) * self.speed) + 1) / 2
            g = (math.sin((context.time + math.pi * 2/3) * self.speed) + 1) / 2
            b = (math.sin((context.time + math.pi * 4/3) * self.speed) + 1) / 2
            overhead.setLight(r * 255, g * 255, b * 255, LightState.brightness(120))

        for overhead in lights.moving_heads:
            r = (math.sin((context.time) * self.speed) + 1) / 2
            g = (math.sin((context.time + math.pi * 2/3) * self.speed) + 1) / 2
            b = (math.sin((context.time + math.pi * 4/3) * self.speed) + 1) / 2
            overhead.setLight(r * 255, g * 255, b * 255,0, LightState.brightness(25))
        return context


class DimmerOverlay(Layer):
    def __init__(self):
        super().__init__()
        self.brightness = 255

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights

        scale = self.brightness / 255.0

        for panel in lights.panels:
            panel.r *= scale
            panel.g *= scale
            panel.b *= scale

        for head in lights.overheads:
            if head.brightness_strobe.mode == LightMode.BRIGHTNESS:
                head.brightness_strobe = LightState.brightness(
                    head.brightness_strobe.value * scale
                )
            else:
                head.brightness_strobe = LightState.brightness(255)

        for head in lights.moving_heads:
            if head.brightness_strobe.mode == LightMode.BRIGHTNESS:
                head.brightness_strobe = LightState.brightness(
                    head.brightness_strobe.value * scale
                )
            else:
                head.brightness_strobe = LightState.brightness(255)

        return context


class VolumeDimmer(Layer):
    """
    Set all panels brightness based on the average audio amplitude
    """

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights
        audio_data = context.audio_data

        if audio_data is None:
            raise RuntimeError(
                "No audio data availabe. Do you have the correct scene type?"
            )

        avg_amplitude = np.mean(np.abs(audio_data))
        avg_amplitude = min(avg_amplitude * 10, 1)

        for panel in lights.panels:
            panel.r *= avg_amplitude
            panel.g *= avg_amplitude
            panel.b *= avg_amplitude

        for head in lights.overheads:
            head.brightness_strobe = LightState.brightness(avg_amplitude * 255)

        for head in lights.moving_heads:
            head.brightness_strobe = LightState.brightness(avg_amplitude * 255)

        return context


class PanelCircle(Layer):
    """
    Highligts the panels in a circle pattern.
    Freq is for each rotation. Negative freq is backwards.
    """

    ORDER: typing.ClassVar = [
        ("d", "m"),
        ("c", "n"),
        ("b", "o"),
        ("a", "p"),
        ("g", "v"),
        ("h", "u"),
        ("i", "t"),
        ("f", "q"),
    ]

    def __init__(self, freq=1, base_mult=0.75, high_mult=1):
        super().__init__()
        self.freq = freq
        self.base_mult = base_mult
        self.high_mult = high_mult

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights

        selectedInd = round(context.time * self.freq * 8) % 8
        selected = [
            getattr(lights.panels, self.ORDER[selectedInd][0], None),
            getattr(lights.panels, self.ORDER[selectedInd][1], None),
        ]
        for panel in lights.panels:
            if panel in selected:
                mult = self.high_mult
            else:
                mult = self.base_mult

            panel.r *= mult
            panel.g *= mult
            panel.b *= mult

        return context


class PanelWave(Layer):
    """
    Dims the panels with a sin.
    Freq is for a whole cycle.
    Angle is in degrees. 0 is forwards. 90 downwards
    """

    def __init__(self, freq=1.0, angle=0.0, width=1.0, min_mult=0.75, max_mult=1.0):
        super().__init__()
        self.start_time = None
        self.freq = freq
        self.angle = angle
        self.width = width
        self.min_mult = min_mult
        self.max_mult = max_mult

    def apply(self, context: FrameContext) -> FrameContext:
        if self.start_time is None:
            self.start_time = time.monotonic()

        now = time.monotonic()

        mult_diff = self.max_mult - self.min_mult
        for panel in context.lights.panels:
            x = panel.position[0] * math.cos(math.radians(self.angle))
            y = panel.position[1] * math.sin(math.radians(self.angle))
            func = 0.5 * (1 + math.sin(((x + y) / self.width) + now * self.freq))
            mult = self.min_mult + mult_diff * func
            panel.r *= mult
            panel.g *= mult
            panel.b *= mult

        return context


class WaveMovingheads(Layer):
    def __init__(
        self,
        period: float,
        color_overide: tuple[int, int, int, int, LightState] | None = None,
    ):
        super().__init__()
        self.period = period
        self.color_overide = color_overide
        """Color override for the moving heads. If None, no affect."""

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights
        f = 2 * math.pi / self.period
        for i, head in enumerate(lights.moving_heads):
            if self.color_overide is not None:
                head.setLight(*self.color_overide)

            head.pan = 255 / 1.5 * 0.25  # face forward

            tilt = (1 + math.sin((context.time + i * 0.4) * f)) / 2 * 255
            # value between 0 and 1

            head.tilt = tilt

        return context


VIRTUAL = False
if __name__ == "__main__":
    if VIRTUAL:
        from lib.virtualrig import VirtualRig

        rig = VirtualRig()
        callback = rig.callback
    else:
        from lib.artnetcontroller import ArtNetController

        controller = ArtNetController("192.168.1.169")
        callback = lambda lights: controller.send_packet(lights.get_channel_values())

    overlay = DimmerOverlay()
    overlay.brightness = 230
    scene = Scene(
        SceneConfig.poll(),
        layers=[
            RainbowPanels(speed=1),
            WaveMovingheads(
                period=6,
            ),
            overlay,
        ],
    )
    # scene = Scene(SceneConfig.poll(), layers=[RainbowPanels(), PanelCircle()])
    # scene = Scene(SceneConfig.mic(), background=arion_panels(), layers=[])
    # scene = Scene(
    #     SceneConfig.playback("audio_files/click_80bpm.mp3"),
    #     arion_panels(),
    #     [VolumeDimmer()],
    # )

    scene.start_dispatcher(callback)

    if VIRTUAL:
        rig.run()
    else:
        input()
