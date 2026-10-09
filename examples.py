import math
import time
import typing

import numpy as np

from lib.arion_lights import LightState
from lib.scenes import FrameContext, Overlay, Scene, SceneConfig


class RainbowsPanel(Scene):
    def run(self):
        lights = self.lights
        while True:
            for i in range(360):
                for panel in lights.panels:
                    r = (math.sin(math.radians(i + panel.position[0] * 15)) + 1) / 2
                    g = (math.sin(math.radians(i + 120 + panel.position[0] * 15)) + 1) / 2
                    b = (math.sin(math.radians(i + 240 + panel.position[0] * 15)) + 1) / 2
                    panel.setLight(r * 255, g * 255, b * 255)
                time.sleep(0.020)


class ArionScene(Scene):
    def run(self):
        lights = self.lights
        for panel in lights.panels:
            if panel.position[1] < 1.2:
                panel.setLight(0, 255, 0)
            elif panel.position[1] < 2:
                panel.setLight(255, 255, 255)
            else:
                panel.setLight(0, 0, 255)


class DimmerOverlay(Overlay):
    def __init__(self):
        super().__init__()
        self.brightness = 255

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights

        for panel in lights.panels:
            panel.r *= self.brightness / 255.0
            panel.g *= self.brightness / 255.0
            panel.b *= self.brightness / 255.0

        for head in lights.overheads:
            head.brightness_strobe = LightState.brightness(self.brightness)

        for head in lights.moving_heads:
            head.brightness_strobe = LightState.brightness(self.brightness)

        return context


class VolumeDimmer(Overlay):
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


class PanelCircle(Overlay):
    """
    Highligts the panels in a circle pattern.
    Freq is for each rotation. Negative freq is backwards.
    """
    ORDER : typing.ClassVar = [("d", "m"), ("c", "n"), ("b", "o"), ("a","p"), ("g","v"), ("h","u"), ("i","t"), ("f","q")]
    def __init__(self, freq = 1, base_mult = 0.75, high_mult = 1):
        super().__init__()
        self.start_time = None
        self.freq = freq
        self.base_mult = base_mult
        self.high_mult = high_mult

    def apply(self, context: FrameContext) -> FrameContext:
        lights = context.lights

        if self.start_time is None:
            self.start_time = time.monotonic()

        now = time.monotonic()
        selectedInd = round((now - self.start_time) * self.freq * 8) % 8
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


class PanelWave(Overlay):
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

VIRTUAL = True
if __name__ == "__main__":
    if VIRTUAL:
        from lib.virtualrig import VirtualRig
        rig = VirtualRig()
        callback = rig.callback
    else:
        from lib.artnetcontroller import ArtNetController
        controller = ArtNetController("192.168.1.169")
        callback = lambda lights: controller.send_packet(lights.get_channel_values())

    from lib.scenes import Scene


    # scene = ArionScene(SceneConfig.poll(), [PanelWave(3, -45, 0.8, 0.6)])
    # scene = RainbowsPanel(SceneConfig.poll(), [PanelCircle()])
    # scene = ArionScene(SceneConfig.mic(), [VolumeDimmer()])
    scene = ArionScene(SceneConfig.playback("audio_files/click_80bpm.mp3"), [VolumeDimmer()])
    scene.start()

    scene.start_dispatcher(callback)

    if VIRTUAL:
        rig.run()
    else:
        input()
