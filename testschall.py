import math
import time

from lib.scenes import Scene, SceneScript
from lib.artnetcontroller import ArtNetController

controller = ArtNetController("192.168.1.169")

class SchallTest(SceneScript):
    def run(self):
        lights = self.lights
        for _ in range(5):
            lights.panels.a.g = 255
            time.sleep(0.5)
            lights.panels.a.g = 0
            time.sleep(0.5)

        while True:
            for i in range(360):
                for panel in lights.panels:
                    r = (math.sin(math.radians(i + panel.channel * 3)) + 1) / 2
                    g = (math.sin(math.radians(i + 120 + panel.channel * 3)) + 1) / 2
                    b = (math.sin(math.radians(i + 240 + panel.channel * 3)) + 1) / 2
                    panel.setLight(r * 255, g * 255, b * 255)
                time.sleep(0.025)

scene = Scene(SchallTest(), [], lambda lights: controller.send_packet(lights.get_channel_values()))

scene.start()

input()