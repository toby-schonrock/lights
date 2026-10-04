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
                    r = (math.sin(math.radians(i + panel.position[0] * 15)) + 1) / 2
                    g = (math.sin(math.radians(i + 120 + panel.position[0] * 15)) + 1) / 2
                    b = (math.sin(math.radians(i + 240 + panel.position[0] * 15)) + 1) / 2
                    panel.setLight(r * 255, g * 255, b * 255)
                time.sleep(0.020)

class Arion(SceneScript):
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
    """
    Set all panels brightness based on the average audio amplitude
    """
    def apply(self, lights: LightConfig, audio_data: np.ndarray) -> LightConfig:
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
    def __init__(self, freq = 1, base_mult = 0.75, high_mult = 1):
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

class PanelWave(Overlay):
    def __init__(self, freq = 1.0, angle = 0.0, width = 1.0, min_mult = 0.75, max_mult = 1.0):
        """
        Dims the panels with a sin.
        Freq is for a whole cycle.
        Angle is in degrees. 0 is forwards. 90 downwards
        """
        self.start_time = None
        self.freq = freq
        self.angle = angle
        self.width = width
        self.min_mult = min_mult
        self.max_mult = max_mult

    def apply(self, lights: LightConfig) -> LightConfig:
        if self.start_time is None:
            self.start_time = time.monotonic()

        now = time.monotonic()

        mult_diff = self.max_mult - self.min_mult
        for panel in lights.panels:
            x = panel.position[0] * math.cos(math.radians(self.angle))
            y = panel.position[1] * math.sin(math.radians(self.angle))
            func = 0.5 * (1 + math.sin(((x + y) / self.width) + now * self.freq))
            mult = self.min_mult + mult_diff * func
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

    scene = Scene(Arion(), [PanelWave(3)], saveconf)
    scene.start()

    # unfortunately we have to block thread instead of just letting the scene handle it
    # this is because pygame has to run on main thread
    while True:
        if light_conf:
            rig.update_display(light_conf)
        time.sleep(1 / 60)