import math
import time

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


if __name__ == "__main__":
    from lib import audio
    from lib.scenes import AudioScene
    from virtualrig import VirtualRig
    from visualiser import VisualiserDimmerOverlay

    audio.select_device(True)

    rig = VirtualRig()

    light_conf = None

    def saveconf(lights):
        global light_conf
        light_conf = lights

    scene = AudioScene(RainbowsPanel(), [VisualiserDimmerOverlay()], saveconf, True)
    scene.start()

    while True:
        if light_conf:
            rig.update_display(light_conf)
        time.sleep(1 / 60)