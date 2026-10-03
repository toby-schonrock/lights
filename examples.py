import math
import time

from lib.arion_lights import LightConfig, LightState
from lib.scenes import Overlay, SceneScript


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


if __name__ == "__main__":
    from lib.scenes import Scene
    from virtualrig import VirtualRig

    rig = VirtualRig()

    light_conf = None

    def saveconf(lights):
        global light_conf
        light_conf = lights

    scene = Scene(RainbowsPanel(), [DimmerOverlay()], saveconf)
    scene.start()

    while True:
        rig.update_display(light_conf)
        time.sleep(1 / 60)