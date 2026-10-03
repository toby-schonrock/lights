import math
import time
import typing

import numpy as np

from lib.arion_lights import LightConfig, LightState
from lib.scenes import AudioOverlay, Overlay, SceneScript


class RainbowsPanel(SceneScript):
    def run(self):
        lights = self.lights
        while True:
            for i in range(360):
                for panel in lights.panels:
                    r = (math.sin(math.radians(i + panel.channel * 3)) + 1) / 2
                    g = (math.sin(math.radians(i + 120 + panel.channel * 3)) + 1) / 2
                    b = (math.sin(math.radians(i + 240 + panel.channel * 3)) + 1) / 2
                    panel.setLight(r * 255, g * 255, b * 255)
                time.sleep(0.025)

class DimmerOverlay(Overlay):
    def __init__(self):
        self.brightness = 255
    
    def apply(self, lights: LightConfig) -> LightConfig:
        for panel in lights.panels:
            panel.r *= self.brightness / 255.0
            panel.g *= self.brightness / 255.0
            panel.b *= self.brightness / 255.0

        for head in lights.overheads:
            head.brightness_strobe = LightState.brightness(self.brightness)

        for head in lights.moving_heads:
            head.brightness_strobe = LightState.brightness(self.brightness)
        
        return lights

class VolumeDimmer(AudioOverlay):
    def apply(self, lights: LightConfig, audio_data: np.ndarray) -> LightConfig:
        # Example: Set all panels brightness based on the average audio amplitude
        avg_amplitude = np.mean(np.abs(audio_data))
        avg_amplitude = min(avg_amplitude * 10, 1)
        
        for panel in lights.panels:
                    panel.r *= self.brightness
                    panel.g *= self.brightness
                    panel.b *= self.brightness
        
        for head in lights.overheads:
            head.brightness_strobe = LightState.brightness(self.brightness * 255)

        for head in lights.moving_heads:
            head.brightness_strobe = LightState.brightness(self.brightness * 255)
        return lights

class PanelCircle(Overlay):
    """
    Highligts the panels in a circle pattern.
    Freq is for each rotation. Negative freq is backwards.
    """
    ORDER : typing.ClassVar = [("d", "m"), ("c", "n"), ("b", "o"), ("a","p"), ("g","v"), ("h","u"), ("i","t"), ("f","q")]
    def __init__(self, freq = 1, base_mult = 0.5, high_mult = 1):
        self.start_time = None
        self.freq = freq
        self.base_mult = base_mult
        self.high_mult = high_mult

    def apply(self, lights: LightConfig) -> LightConfig:
        if self.start_time is None:
            self.start_time = time.monotonic()

        now = time.monotonic()
        selectedInd = round((now - self.start_time) * self.freq * 8) % 8
        selected = [getattr(lights.panels, self.ORDER[selectedInd][0], None), getattr(lights.panels, self.ORDER[selectedInd][1], None)]
        for panel in lights.panels:
            if panel in selected:
                mult = self.high_mult
            else:
                mult = self.base_mult
            
            panel.r *= mult
            panel.g *= mult
            panel.b *= mult

        return lights

if __name__ == "__main__":
    from lib.scenes import Scene
    from lib.virtualrig import VirtualRig

    rig = VirtualRig()

    light_conf = None

    def saveconf(lights):
        global light_conf
        light_conf = lights

    scene = Scene(RainbowsPanel(), [PanelCircle(-3)], saveconf)
    scene.start()

    # unfortunately we have to block thread instead of just letting the scene handle it
    # this is because pygame has to run on main thread
    while True:
        if light_conf:
            rig.update_display(light_conf)
        time.sleep(1 / 60)