import math
import time

from lib import audio
from lib.artnetcontroller import ArtNetController
from lib.scenes import AudioScene, SceneScript
from visuliser import VisualiserDimmerOverlay

controller = ArtNetController("192.168.1.169")

audio.select_device(auto=True)

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

scene = AudioScene(SchallTest(), [VisualiserDimmerOverlay()], lambda lights: controller.send_packet(lights.get_channel_values()))

scene.start()

input()